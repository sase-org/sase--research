# Claude Design vs. `#research_swarm` for SASE UX Work

> **Research query:** I currently use the `#research_swarm` macro swarm to design the UX
> for sase (e.g. the TUI). I would like to learn more about Claude Design and what
> benefits I would gain from using it instead of, or in addition to, research swarms.
> End with a ranked list of the Claude Design features and functionality I am likely to
> find useful.

**Researcher:** `cld` · 2026-10-26 · sase baseline `49b1b9088b` · Claude Code 2.1.310

---

## 1. Bottom line

**Use Claude Design alongside research swarms. It should not replace them.** The two
tools are good at opposite halves of UX design:

- **Claude Design is good at diverging and deciding.** It drafts several directions as
  artboards on one canvas. You react by clicking an element and commenting, editing the
  canvas directly, or dragging sliders and toggles that Claude generates for the design.
  Today's swarms are weakest here. They converge on one recommendation, and the choices
  left to you arrive as text ("Open questions for Bryan").
- **Research swarms are good at grounding and converging.** They trace a visual bug to
  the Textual source, take a census of real data, and build a real Textual prototype.
  That prototype is rendered through sase's own screenshot renderer at five terminal
  sizes, cross-checked by five independent model families, and committed as durable
  files. Claude Design can do none of that for a Textual TUI.

Three facts set how far Claude Design can go for you:

1. **The medium doesn't match.** Claude Design renders HTML, CSS, and JS in a browser,
   and its design-system code sync is React-based. The sase TUI is a grid of monospace
   cells in Textual (`textual==8.0.1`), styled by a 10,935-line `styles.tcss`. Every
   Claude Design TUI mockup is a *picture of intent*, never a buildable artifact. It
   stays faithful only if you teach Claude Design the terminal's constraints (§5).
2. **It can't run inside your swarm today.** Claude Code's artifact docs say artifact
   publishing, which `/design` depends on, is *"Off by default in the Agent SDK … and
   when you run Claude Code with `-p`."* SASE launches Claude agents exactly that way. I
   checked this session (sase-launched, Claude Code 2.1.310,
   `CLAUDE_CODE_ENTRYPOINT=sdk-cli`): it offers the `DesignSync` tool, which is reserved
   for the user-started `/design-sync` flow, but no `Artifact` tool. Design is therefore
   a human-in-the-loop step you run from an interactive session, and it reaches swarm
   agents only through exported files.
3. **Timing.** The standalone site at `claude.ai/design` **closes December 14, 2026.**
   Claude Design now lives inside ordinary Claude conversations, the Artifacts tab, and
   Claude Code's `/design`. Start there, not in the standalone app. Since June 17,
   Design also **draws from the same usage pool as Claude Code**, so every design
   iteration competes with your Claude agent fleet.

**Recommended pattern: diverge in Claude Design, converge in the swarm.** First, spend
one session building a "sase terminal" design system in Claude Design (§7.1). Then, for
open-ended new views, explore and decide on the canvas, and give the exported artboards
to `#research_swarm` as the chosen direction for feasibility checking, Textual
prototyping, and the plan. For bugs and "this looks bad" diagnoses, keep starting with
the swarm. Use Claude Design as the primary tool for the surfaces that *are* web-shaped:
sase.sh, the sase-android client, launch and blog visuals, and slides.

---

## 2. What Claude Design is (as of late October 2026)

### 2.1 Timeline

| Date | Change |
| --- | --- |
| 2026-04-17 | Launched by Anthropic Labs as a research preview, *"powered by our most capable vision model, Claude Opus 4.7"*, for Pro, Max, Team, and Enterprise. |
| 2026-06-17 | Design-system import rebuilt (GitHub repo, design files, uploads) with self-checking against the system. New admin role, new canvas editor, nine export connectors, `/design-sync` and `/design` for Claude Code. **Usage moved into the shared Claude pool.** Anthropic says over one million people used it in its first week. |
| 2026-08-17 to 21 | Claude Code week 34: the **`/design` artboard skill** ships in research preview in the CLI and Claude Code Desktop, built on artifacts. |
| 2026-09-16 | Design works inside any Claude conversation, including Claude Code and the Artifacts tab. Slide decks move to their own Claude Slides entry point. |
| 2026-10-08 | Docs, Slides, and Design leave beta **on every plan, including Free**. Dashboards and Motion launch in beta. |
| 2026-10-15 | Enterprise default-on date. |
| **2026-12-14** | **Standalone `claude.ai/design` closes.** It becomes read-only. Chats and comments are not migrated and are deleted some time later. Public project links stop working. |

### 2.2 Where you can use it now

- **In a Claude conversation:** ask for a design, or choose **Output → Design**. The
  canvas opens beside the chat as an artifact.
- **From the Artifacts tab:** choose the Design template.
- **In Claude Code:** run `/design <brief>` from the CLI or Desktop. *"Claude prints a
  link to the published canvas. Open it, pick an artboard, and tell Claude which option
  to implement."* The canvas is a private claude.ai page that opens in your browser. It
  is not a terminal UI.
- **In the iOS and Android apps:** create, view full screen, and edit designs. Sharing
  settings can only be changed on web or desktop.

### 2.3 Feature inventory

| Area | What it does (from Anthropic's pages unless noted) |
| --- | --- |
| **Inputs** | A text prompt; images and screenshots; DOCX, PPTX, and XLSX files; a linked repo or local codebase; a web-capture tool that grabs elements from a live site (launch post). |
| **Generation** | Multiple directions on request (*"Show me 2–3 alternative layouts"*, *"Ask for three directions … and pick the one worth refining"*). Clarifying questions up front (reviewers). A design is *"a canvas of artboards"* made of nested layers. |
| **Refinement** | Chat for broad changes. **Inline comments**: *"click directly on a specific part of the canvas and request a targeted change"*. **Direct canvas editing**: drag, resize, align, and edit text in place. **Custom sliders "made by Claude"** and adjustment knobs for *"spacing, color, and layout"*. Reviewers saw generated controls such as density, formality, contrast, a dark-mode toggle, and a font switcher. |
| **Design systems** | Built from a GitHub repo, design files, raw uploads, or a local codebase (through `/design-sync`). Claude *"checks its own output against your design system, and makes corrections before you see them."* You can keep several systems. Admins can lock one standard system. |
| **Review aids** | Claude can review a design for accessibility and contrast. Full keyboard and screen-reader support exists, but placing new layers needs a mouse. |
| **Export** | `.zip`, PDF, PPTX, Google Slides, standalone HTML, and PNG per artboard (in `/design`). Connectors to Canva, Adobe, Gamma, Miro, Vercel, Replit, Lovable, Base44, Wix, and others. |
| **Code bridge** | A handoff bundle to Claude Code (*"Send to local coding agent"* or *"Send to Claude Code Web"*) that *"continues from your existing work instead of starting over from a screenshot."* `/design-sync` brings a component library into a design-system project. A remote **Claude Design MCP** at `https://api.anthropic.com/v1/design/mcp` (third-party documented, 23 tools) can pull artboards into a local folder as `.dc.html` files. |
| **Sharing** | Designs start private. Shared viewers can view, comment, or edit. |

### 2.4 Documented limitations

- **No version history.** The official workaround is to tell Claude *"Save what we have
  and try a completely different approach."*
- Inline comments *"occasionally don't appear on the page."* Multi-person editing is
  *"still basic and may not work reliably."* In the `/design` canvas, *"whoever saves
  second gets a conflict: nothing is merged"* (wmedia).
- A design-system import is *"only as good as its source."*
- An artifact is one self-contained page with no backend. Claude Code's docs limit
  external loads to Google Fonts and a few CDNs, and cap the page at 16 MiB.
- The `/design` preview in Claude Code is *"not at parity with claude.ai/design."*
  According to wmedia, the canvas has no design-system color tokens and no
  ask-for-tweaks loop, because both depend on the web backend.
- `/design-sync` reportedly needs **a React design system with a published `dist/` or a
  Storybook**. Vue, Angular, Svelte, and server-side templates are not supported
  (wmedia; Anthropic's pages don't say).
- Early reviews, from April and May, called the output a generic "house style" (*"serif
  headings, accent bars … container soup"*) unless a design system steers it. They also
  said a design system yields *"approximation, not usage"* of real components.

---

## 3. What `#research_swarm` already gives you for UX

Your October TUI UX swarms show what the current tool does well. The clearest example is
`gate_panel_decision_cards` from 2026-10-12:

- **Code-grounded root cause.** The cut-off decision text was traced to Textual's
  `Button.get_content_width()`. The focused row came out 103 cells wide inside a 44-cell
  viewport. The ragged highlight was traced to `button-focus-text-style` in Textual's
  `design.py`. These are implementation bugs. No canvas tool would find them.
- **Real-data census.** The lead re-ran `cld`'s decision-size census on real plans.
- **Terminal-faithful prototypes.** `cld` wrote a real Textual prototype
  (`plan_gate_decision_cards__cld_prototype.py`) and rendered it at 90×40, 120×40,
  160×48, 200×56, and 262×72 through the same SVG-to-PNG path `sase screenshot` uses.
  The lead built a variant to prove that every decision stays on screen at 90×40.
- **Independence and adjudication.** Five model families reported independently, and a
  lead settled their disagreements (§4 of that report).
- **Durable output.** The reports, PNGs, prototypes, and infographic are committed to
  the research repo and registered as artifacts.
- **Speed.** About **70 minutes** from the screenshot named in the query (07:40) to the
  published canonical report (08:48), with no attention from you along the way.

The other October swarms (`clan_waves_in_agents_tab`,
`agents_tab_inbox_and_history_views`, `plan_decisions_cross_surface_ux`,
`projects_tab_add_project_wizard`) follow the same shape. They add real-render mockups
and cross-surface reasoning (TUI, CLI, and Telegram in one study).

**Where swarms are weak for *design*, as distinct from diagnosis:**

1. **Narrow visual exploration.** Each alternative costs a hand-written prototype, so
   reports usually show one proposal next to the current state. Rejected alternatives
   appear as prose (§8, "Rejected alternatives").
2. **Text-mediated decisions.** Taste questions reach you as markdown, for example
   *"Rail cap: 84 or 100?"* or *"Focus colour: the modal's cyan (`#5FD7FF`) or the gate
   accent?"* You answer them without seeing the options side by side.
3. **A slow feedback loop.** A follow-up means another prompt and another swarm or
   agent run. You can't point at a pixel and say "this, smaller."
4. **High cost per question.** Five researchers plus a lead and an optional
   image/linker pair is overkill when the question is "which of these three looks
   better?"

---

## 4. Head-to-head comparison

| Dimension | `#research_swarm` | Claude Design |
| --- | --- | --- |
| **Fidelity to a Textual TUI** | Exact. Real Textual code, sase's renderer, real terminal sizes. | Approximate. A browser canvas imitating cells, and only as faithful as your design system (§5). |
| **Grounding in code and data** | Strong. Reads sase and Textual source, measures, censuses. | Weak. Reads a repo for tokens, components, and nearby screens, but doesn't debug or measure a Textual layout. |
| **Exploration breadth** | Low. About one proposal per report. | High. Several directions on one canvas, cheap to fork. |
| **How you decide** | Answer text questions after reading. | Click, comment, drag a slider, edit in place. |
| **Model diversity** | Five families (codex, claude, grok, muse, gemini). | Claude only, with one shared "house style." |
| **Runs unattended** | Yes, by design. | No. Artifacts are off by default in `-p` and Agent SDK runs, and the canvas needs you in a browser. |
| **Auth** | Every sase provider. | A first-party claude.ai login only, on the Anthropic API. Not API key, Bedrock, or Vertex. |
| **Durability** | Git plus artifact registration, permanent. | No version history. Artifact retention policies can delete unopened work. Standalone chats and comments will be deleted. |
| **Cost** | 5 to 8 agents per question. | Shares the Claude Code pool. Styled pages *"use more tokens than terminal text"* (Claude Code docs). Reviewers called the old separate allowance "brutal." |
| **Best surfaces** | TUI, CLI, Telegram, cross-surface flows. | Web (sase.sh), mobile (sase-android), slides, one-pagers, launch visuals. |

---

## 5. The medium mismatch, and how to blunt it

A Textual screen is a grid of cells. It has no sub-cell padding, no proportional type,
no rounded radii or drop shadows, and no hover. Navigation is by keyboard, colors come
from a 256-color or truecolor palette, borders are box-drawing characters, and the
layout reflows with terminal size. Claude Design's defaults (cards, shadows, serif
headings, accent bars, generous whitespace) will propose things Textual can't render. A
mockup that looks better because it breaks the medium is worse than no mockup.

To keep Claude Design honest, give it a **"sase terminal" design system** built from raw
uploads. `/design-sync` doesn't apply here, because the TUI isn't a React library.

1. **A `design.md` of rules.** Everything is drawn on a cell grid. The font is
   **Fira Code**, the same font sase's renderer bundles, and it is on Google Fonts,
   which artifacts are allowed to load. Artboards are sized in cells (90×40, 120×40,
   200×56). Borders and focus use box-drawing characters and a left accent bar, never
   reverse video, matching the gate-panel finding. Every screen ends with a key-hint
   footer. The glyph vocabulary is `★ ⊙ ○ ✓ ✗ · →`.
2. **Palette tokens taken from the code.** The TCSS uses Textual theme variables heavily
   (`$text-muted` ×248, `$secondary` ×201, `$surface` ×161, `$primary` ×104,
   `$accent` ×44, `$error` ×30, `$warning` ×28). It also hard-codes **58 distinct hex
   colors**, led by xterm-256 values such as `#FFAF5F`, `#87D7FF`, `#FFD700`, `#FF5F5F`,
   `#FF87D7`, `#00D7AF`, and `#5FD7FF`. Turning these into a named token sheet is useful
   to the swarms as well (§7.3).
3. **Reference screenshots.** Use `sase screenshot` PNGs of each tab at your standard
   sizes. They are real renders with the real font.
4. **Explicit anti-patterns.** For example: "no card grids, no shadows, no rounded
   corners, no proportional text, no hover states." Reviewers report that explicit
   anti-patterns are what break the house style.

Even with all of this, treat a Claude Design TUI artboard as a **spec of intent**: the
hierarchy, grouping, density, copy, and what is pinned versus what scrolls. A Textual
prototype from the swarm is still what proves the design can be built.

---

## 6. Can Claude Design plug into SASE's agent machinery?

**Not directly, today.**

- **Headless.** Claude Code's artifact docs say publishing is *"Off by default in the
  Agent SDK, the GitHub Action, and MCP-server contexts, when you run Claude Code with
  `-p`."* This sase-launched session matches: there is no `Artifact` tool. A
  `#research_swarm` member therefore can't publish a design canvas as things stand. The
  docs don't say whether this can be turned on. That is an open experiment (§7.3).
- **Providers.** It needs a claude.ai login and the Anthropic API. The codex, grok,
  muse, and gemini members can't use it. The Claude Design MCP is an HTTP server on
  `api.anthropic.com` bound to claude.ai consent. Whether a non-Claude MCP client can
  complete that consent flow is **unverified**.
- **Fit with SASE's turn model.** Design is inherently a pause for human taste. That
  fits SASE's rule that a gate never blocks an agent. A swarm or agent ends its turn
  with a design brief. You resolve the brief in a Claude Design session, and a follow-up
  agent (or `#research_swarm`) picks up the exported artboards.
- **Bridges that work today:**
  - Export PNGs per artboard, a PDF, standalone HTML, or a `.zip` into the topic's
    research directory, where every swarm member can read them.
  - Optionally, pull `.dc.html` artboards through the Claude Design MCP:
    `claude mcp add --scope user --transport http claude-design
    https://api.anthropic.com/v1/design/mcp`, then `/design-consent` (wmedia, Aug 24).
- **Durability.** Design has no version history, and artifact retention can delete work
  nobody opens. Treat the canvas as scratch space. Commit the exported artboards and a
  short decision log ("chose B; rail 84; cyan focus") to the research repo. That is
  where decisions already live.
- **Usage.** Since June 17, design work draws from the same limits as Claude Code. On a
  busy day of Claude agents, a long canvas session costs agent capacity. Keep design
  sessions short and targeted.

---

## 7. Recommended workflow

### 7.1 One-time setup (one interactive session)

Create a **sase terminal design system** in Claude, from the Artifacts tab or a chat,
using the four inputs in §5. Verify it before trusting it. Ask for a redraw of one
existing screen, such as the gate panel at 120×40, and compare it with a
`sase screenshot` PNG. If the redraw doesn't look like your TUI, the system isn't done.
Don't do this in standalone `claude.ai/design`, which closes December 14.

### 7.2 Choosing a tool for each UX question

| Kind of question | Start with | Then |
| --- | --- | --- |
| "This looks bad or is cut off" (diagnosis) | `#research_swarm`. The cause is usually in code. | Optionally, take the swarm's recommendation to Claude Design and settle its open questions on the canvas. |
| A new view, tab, or wizard (open-ended) | Claude Design. `/design three directions for <view> at 120×40 cells` in an interactive Claude Code session in the sase repo, so it reads `styles.tcss` and nearby screens. | Export the chosen artboards, then run `#research_swarm` on feasibility, a Textual prototype of the chosen direction, and an implementation plan. |
| Taste decisions left open by a swarm | Paste the final report's open questions into a Claude conversation and ask for one design with a **tweak control per open question** (rail width slider, focus color picker, density toggle). | Record the chosen values in the research directory. Implement them. |
| Web and mobile surfaces (sase.sh, sase-android, launch and blog visuals, slides) | Claude Design as the primary tool. Here its HTML output *is* the medium. | Use a swarm for the research-heavy content, such as the Diátaxis IA in `sase_sh_docs_redesign`. |

### 7.3 Possible SASE follow-ups (proposals only)

I did not file beads for these, to avoid five researchers filing duplicates. The lead
can file any that survive synthesis.

1. **A design-brief output for swarms.** Have the `#research_swarm` lead (or a small
   `#design_brief` macro) write a Claude-Design-ready brief. It would cover artboard
   sizes in cells, constraints, and one tweak spec per open question. This works
   headless today and makes the human canvas step cheap to start.
2. **Extract a token sheet from `styles.tcss`.** Name the 58 hard-coded hex colors and
   map them onto theme variables. Claude Design's design system needs this, and so do
   swarm prototypes.
3. **A screenshot preset.** Have `sase screenshot` emit the standard size set (90×40,
   120×40, 200×56) in one call, for uploading as references.
4. **An artifacts-in-SDK experiment.** Test whether artifact publishing can be enabled
   for sase-launched Claude sessions. If it can, a `design=true` swarm option could
   publish a canvas link in a gate for you to resolve.

---

## 8. Ranked: Claude Design features you are likely to find useful

Ranked by expected value for a solo developer whose main UX surface is a Textual TUI,
who already runs code-grounded research swarms, and who also owns a docs site, an
Android client, and launch material.

1. **Several directions as artboards on one canvas.** For example,
   `/design three directions for the Agents tab inbox`. It gives you the breadth swarms
   lack: three or more options side by side in minutes, with no prototype written per
   option. This is the single biggest gain over swarms.
2. **Generated tweak controls (sliders, toggles, color pickers).** These turn a swarm's
   "Open questions for Bryan" (rail cap 84 or 100, focus color, collapsed-row density)
   into knobs you drag and see. You decide by looking instead of reading. *Caveat:* the
   full tweak loop is in Claude Design inside Claude. The Claude Code `/design` preview
   reportedly offers per-artboard tweaks only.
3. **`/design` in Claude Code, run from the sase repo.** It reads your tokens,
   components, and closest existing screens before drawing, prints a canvas link, and
   lets you say "implement artboard 2" in the same session. It fits your terminal-first
   workflow. *Caveats:* research preview, interactive sessions only (not `-p` or SASE
   agents), and claude.ai login only.
4. **Inline comments pinned to canvas elements.** Point and comment instead of
   describing where something is. Use these for targeted fixes like "this footer hint is
   too long." Reviewers say comments cost fewer tokens than long prompts. *Caveat:*
   comments occasionally vanish. Paste the text into the chat as a fallback.
5. **A custom design system with self-checking.** This is the only lever that makes TUI
   mockups faithful (§5) and keeps out the generic house style. Claude checks its own
   output against the system before showing it. Building it also produces a written
   design language for the TUI, which the swarms can use too.
6. **Direct canvas editing.** Drag, resize, align, and edit text in place. Best for
   copy, labels, key hints, and nudging what gets pinned or grouped, all without a
   prompt round-trip.
7. **Exports: PNG per artboard, PDF, standalone HTML, `.zip`.** These carry a decision
   into the research repo, where it becomes durable and readable by every swarm member
   of every provider. They also make up for the missing version history.
8. **Designs viewable and editable in the iOS and Android apps.** You can review and
   comment on mockups away from the desk, as you already do with Telegram gates and the
   mobile gateway.
9. **Accessibility and contrast review.** Use it to sanity-check palette pairs such as
   `$text-muted` on `$surface` (248 uses) and the xterm-256 accent colors. Verify any
   finding in a real render.
10. **Web, mobile, and slide output for non-TUI surfaces.** Claude Design is the right
    primary tool for the sase.sh redesign, the sase-android client screens, launch-post
    and blog visuals, and talks. Here its HTML output is the actual medium, and
    connectors such as Canva and Google Slides finish the job.
11. **The Claude Design MCP and Claude Code handoff bundle.** These pull `.dc.html`
    artboards or a handoff bundle into a repo for implementation. Most valuable for web
    surfaces. For the TUI, they carry design intent only.
12. **Motion.** Code-built animated explainers for launch or demo material. *Caveat:*
    per unite.ai, the beta is Team and Enterprise only.

**Likely not useful to you:** `/design-sync`, which reportedly needs a React component
library, and sase has none. Dashboards, which connect to data warehouses. Org admin
locks and sharing controls, which matter little for a solo developer.

---

## 9. What I could not verify

- **No hands-on use.** Artifacts are not available in this SDK-launched session.
  `DesignSync` is reserved for a user-started `/design-sync`, so I deliberately did not
  call it. The feature claims above come from Anthropic's pages and third-party
  reviews, not my own trial.
- **The current model behind Claude Design.** The launch named Opus 4.7. Later pages
  name no model.
- **The React-only requirement for `/design-sync`.** This comes from one third-party
  source (wmedia). Anthropic's pages don't state it.
- **Claude Design MCP tool names, and whether non-Claude MCP clients can consent.**
  wmedia gives only a count of 23 tools.
- **Version requirements for `/design` and artifacts conflict across Anthropic's
  pages:** 2.1.234, 2.1.265, and 2.1.281. The installed 2.1.310 satisfies all three.
- **Reviewer usage-burn anecdotes** ("3–4 prompts per week" on Pro) predate the June 17
  move to shared limits. Treat them only as evidence that design work is token-heavy.
- **Motion and Dashboards plan availability.** unite.ai's claim conflicts with
  orcarouter's statement that it is unpublished.

---

## Sources

**Anthropic (primary)**

- Claude Design launch, Apr 17, 2026: <https://www.anthropic.com/news/claude-design-anthropic-labs>
- "Claude Design now stays on brand for daily work," Jun 17, 2026: <https://claude.com/blog/claude-design-stays-on-brand-for-daily-work>
- Get started with Claude Design (help center): <https://support.claude.com/en/articles/14604416-get-started-with-claude-design>
- Move from standalone Claude Design to Claude (help center): <https://support.claude.com/en/articles/17440474-move-from-standalone-claude-design-to-claude>
- Claude Code what's new, week 34 (`/design`): <https://code.claude.com/docs/en/whats-new/2026-w34>
- Claude Code artifacts docs (availability, headless default-off, limits): <https://code.claude.com/docs/en/artifacts>
- The usage-and-pricing help article (14667344) now returns 404. Its content is superseded by the "Usage and pricing" section of the getting-started article.

**Third-party (secondary; dates noted)**

- the-decoder, `/design` in Claude Code (Aug 18): <https://the-decoder.com/claude-code-gets-a-design-command-that-lets-developers-create-ui-mockups-right-in-the-terminal/>
- Pasquale Pillitteri, `/design` artboards (Aug 18): <https://pasqualepillitteri.it/en/news/11689/claude-code-design-skill-artboards>
- Pasquale Pillitteri, `/design-sync` (Jun 18): <https://pasqualepillitteri.it/en/news/5308/claude-code-claude-design-two-way-sync-design-sync>
- wmedia, `/design-sync` requirements (Aug 25): <https://wmedia.es/en/tips/claude-code-design-sync-your-components>
- wmedia, Claude Design MCP (Aug 24): <https://wmedia.es/en/tips/claude-code-claude-design-mcp-connect>
- wmedia, `/design` editable canvas (Aug 23): <https://wmedia.es/en/tips/claude-code-design-editable-canvas>
- unite.ai, Dashboards, Motion, and Docs out of beta (Oct 9): <https://www.unite.ai/anthropic-launches-claude-dashboards-and-motion-takes-docs-out-of-beta/>
- aimaker, October 2026 walkthrough (Oct 25): <https://aimaker.substack.com/p/claude-code-updates-october-2026>
- orcarouter, October 2026 recap (Oct 23): <https://www.orcarouter.ai/blog/claude-news-what-anthropic-shipped-in-october-2026>
- memorylake, standalone closure (Oct 12): <https://www.memorylake.ai/en/blogs/claude-design-standalone-site-closing>
- Reviews from April and May 2026, which predate the shared-limits change:
  - alexcloudstar: <https://alexcloudstar.com/blog/claude-design-review-developer-first-look-2026/>
  - eesel: <https://www.eesel.ai/blog/claude-design-review-2026>
  - Flowstep (a competitor): <https://flowstep.ai/blog/claude-design-review/>
  - Karo Zieminski: <https://karozieminski.substack.com/p/claude-design-review-prompts-figma>

**Local evidence**

- `202610/gate_panel_decision_cards/`: the final report, the `cld` prototype, and
  real-render PNGs at five terminal sizes. Git timestamps give the 70-minute figure.
- `202610/{clan_waves_in_agents_tab,agents_tab_inbox_and_history_views,plan_decisions_cross_surface_ux,projects_tab_add_project_wizard,sase_sh_docs_redesign}/`
- `src/sase/ace/tui/styles.tcss`: 10,935 lines, theme-variable counts, 58 distinct hex
  colors.
- `sase macro show research_swarm`, and the `tui_screenshot` reference memory
  (renderer, font stack, capture workflow).
- This session's environment: Claude Code 2.1.310, `CLAUDE_CODE_ENTRYPOINT=sdk-cli`,
  the `DesignSync` tool present, and no `Artifact` tool.
