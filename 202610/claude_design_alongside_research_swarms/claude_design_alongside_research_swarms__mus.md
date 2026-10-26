# Claude Design vs. `#research_swarm` for SASE TUI/UX Design

**Researcher:** mus (independent swarm report, `__mus`)
**Date:** 2026-10-26
**Question:** What is Claude Design, and what would I gain using it instead of / in addition to the `#research_swarm` macro swarm I currently use to design sase UX (e.g. the TUI)?

## Bottom line

Claude Design is a conversational **visual** workspace (chat on the left, live canvas on the right) that turns
prompts plus brand/code context into **see-it-immediately interactive prototypes, mockups, decks, and landing
pages**, which you then refine by chatting, pinning inline comments, dragging elements, or moving generated
adjustment sliders. It is a genuine complement to `#research_swarm`, not a replacement: the swarm gives you
**multi-model independent analysis consolidated into durable, audited text reports** grounded in the repo; Claude
Design gives you **fast visual drafts and stakeholder-testable prototypes** that text reports cannot provide. The
single biggest caveat for your use case: Claude Design outputs **web artifacts (HTML/CSS/JS)** — it has no notion
of Textual widgets, terminal constraints, keybindings, or focus models, so everything it makes for the sase TUI is
an **approximation to react to, not a spec to build from**. Use the swarm to decide what to build; use Claude
Design to see candidate directions quickly and to get buy-in. Details and a ranked feature list are at the end.

## 1. What Claude Design is (verified facts)

- **Product:** A separate workspace from regular Claude chat, at `claude.ai/design` (also in the Claude Desktop/Mac
  app), built by **Anthropic Labs** (the experimental-products team) and launched **17 April 2026** as a research
  preview; described as in beta after the June 2026 overhaul.
- **Model:** Powered by **Claude Opus 4.7** (released ~16 April 2026), framed by Anthropic around vision work and
  agentic coding. Hit a reported **1M+ users in its first week**.
- **Access:** Paid plans only (**Pro, Max, Team, Enterprise**; no Free tier). Web-only (plus Mac app). Enterprise has
  it off by default (admin enables it under Organization Settings → Capabilities → Anthropic Labs).
- **Usage:** Metered **separately from chat and Claude Code at launch** with restrictive weekly caps (reviewers
  reported burning a Pro weekly allowance in under an hour; each prompt ~5–10% of Pro weekly usage on Sonnet-class
  models). The **June 17, 2026 overhaul** moved it to **shared usage limits** with chat/Cowork/Code plus doubled
  weekly token limits (May 19, 2026 change), fixing the worst "token-burning" complaints.
- **Positioning:** Explicitly **not a Figma/Canva replacement** — Anthropic calls it a complement, with handoffs to
  Canva (and later Adobe, Miro, Vercel, Replit, Lovable, Base44, Gamma, Wix) rather than native `.fig` interop.

## 2. How the loop works

The documented five-step loop is: (1) create a project with context, (2) describe what you want, (3) review the
output, (4) iterate through chat and comments, (5) export or share.

- **Two-pane UI:** chat left, live canvas right. Vague prompts trigger **clarifying questions** (goal, layout,
  content, audience) before drawing — a behavior reviewers single out as surfacing forgotten requirements.
- **Inputs:** plain-text prompts; screenshots/images/mockups; slide decks showing a liked style; `DOCX`/`PPTX`/`XLSX`
  documents; **code repository link or local folder import**; Figma references (not native `.fig`); voice input;
  hand **sketches**; and a **web-capture bookmarklet** that approximates elements of an existing site as JSON context.
- **Design-system grounding (the load-bearing setup step):** once per organization you upload brand/product assets
  (code, design files, decks, fonts, palettes) plus an instruction prompt; after ~5 minutes Claude returns colors,
  typography scale, components (buttons, cards, navigation), and layout patterns for manual approve/downvote review,
  then you **Publish** it so new projects inherit it. Multiple systems (sub-brands) supported; **Remix** re-opens a
  system for chat edits. Anthropic warns that without a published system, output is **"functional but generic"** —
  reviewers confirm a recognizable house style (serif fonts, yellowed palettes, card layouts, accent bars) when
  ungrounded.

- **Iteration modalities:** broad changes via chat ("darker theme", "three layout alternatives"); **inline comments**
  pinned to a canvas element (doubles as team collaboration via a Comments tab); **direct text edits** for copy;
  generated **Tweaks cards / adjustment sliders** (form style, input style, width, spacing, color) that update the
  preview live; a **draw tool** for marking regions; background/font/base-size selectors; wireframe-vs-high-fidelity
  starting fidelity; and version branching by telling Claude to "save what we have and try a completely different
  approach."
- **Outputs:** realistic interactive prototypes; product wireframes/mockups; multi-screen flows (e.g. onboarding);
  pitch decks/presentations (presentable in place); marketing collateral, landing pages, microsites; and experimental
  **frontier design** (voice, video, shaders, 3D, built-in-AI prototypes; nine Examples-tab starters cover
  animations/particles/shaders). Everything is stored as real files in a per-project workspace (HTML, CSS, SVGs,
  pasted image references) downloadable at any time.
- **Sharing & export:** org-scoped URL sharing (private / view-only / comment / edit; edit lets a teammate chat with
  Claude in the same conversation); `PDF`/`PPTX`; **standalone single-file HTML** (a functional prototype, not a
  production scaffold); Canva/Adobe/Miro/Vercel/Replit/Lovable/Base44/Gamma/Wix connectors; and the **Claude Code
  handoff**, which packages design intent plus a system prompt into a bundle the coding agent picks up with one
  instruction.
- **Claude Code bridge (post-June):** bidirectional `/design-sync` (pull design systems into Code, keep canvas and
  code in sync rather than copy-paste-stale) and `/design` (create/edit/sync design projects from the terminal).
  Reporting from August 2026 describes `/design` becoming a **research-preview skill that brings the artboard
  workflow into the Claude Code CLI/desktop app on top of artifacts** ("pick one, tweak it, then have Claude
  implement it") — the most terminal-relevant development for a CLI-first workflow like yours.
- **Known rough edges (documented):** occasionally **dropped inline comments** (workaround: paste into chat);
  compact-view save errors; **large-codebase lag** (workaround: link a subdirectory, not a monorepo); chat upstream
  errors; **no native Figma import or export** (exports are HTML/PDF/PPTX/Canva/URL — Figma requires an HTML-import
  workaround such as Anima/Buddy, treated as the *start* of a cleanup pass); no pixel-perfect manual editor; and, on
  governance, **no audit logs or admin usage reporting, no data-residency support**, persistent uploaded-asset
  storage, and a still-early multiplayer story.

## 3. What `#research_swarm` does today (baseline for comparison)

Verified against the live macro (`sase macro show research_swarm`; definition in the
`sase-research-artifacts` plugin's `xprompts/research_swarm.md`, dispatched through the macro-swarm expansion in
`src/sase/agent/macro_swarm.py` and documented under `docs/reference/macros/multi-agent-prompts.md`):

- Fans out **N independent per-provider researchers** (defaults: codex + claude on; grok/muse/gemini opt-in, each
  pinned to an `@xhigh`-class model), each writing a **self-named text report** (`<stem>__cdx.md`, `__cld.md`, …)
  under the research repo without seeing peers' work; a **lead researcher** (`@xlarge` default) then researches
  further and **consolidates** everything into one report.
- Optional companions: **infographic image**, **validated Mermaid diagrams**, **narrated audio edition** (brief/full
  via `sase-listen`), and a **linker** that publishes the canonical report — all registered as **durable, audited
  artifacts** (`sase artifact create/read`) with bead/task integration.
- Strengths that matter for TUI design: **multi-model independence** (divergent framings, not one model's house
  style); **repo-grounded** (agents read the actual Textual code, beads, memory, and prior research); **terminal-
  and constraint-aware** (keyboard flows, focus, layout-lock, pane semantics — the vocabulary your TUI reports use);
  durable prose rationale a future agent can build on. Weakness: **everything is prose** — no stakeholder can *see*
  or *click* a proposal, and comparing three layout directions means reading three documents.

## 4. Head-to-head: swarm vs. Claude Design for sase UX work

| Dimension | `#research_swarm` (today) | Claude Design |
|---|---|---|
| Primary artifact | Consolidated prose report + optional diagrams/audio | Live interactive visual prototype on canvas |
| Divergence | N independent models, enforced blindness | One model; branches via "try a different approach" |
| Repo grounding | Reads code, beads, memory directly | Codebase import as brand/context; no bead/memory notion |
| TUI fidelity | Native (Textual, keymaps, focus, panes) | None — web approximation only |
| Iteration | New prompts / follow-up agents | Chat, inline comments, drag, sliders, sketch |
| Stakeholder testing | Not possible from a report | Shareable URL / standalone HTML, no PR needed |
| Handoff to build | Plan → coder agents in-repo | Handoff bundle → Claude Code (`/design`, `/design-sync`) |
| Auditability | Artifact reads audited, bead-linked | No audit logs; usage reporting absent |
| Cost shape | Normal agent/model spend | Weekly caps; Pro burns fast; Max/shared pool better |
| Late-stage precision | Exact (specs, keymaps, `default_config.yml`) | Weak (no Figma-native round-trip, no pixel editor) |

## 5. The TUI-fit caveat (read before spending)

Your TUI is a **Textual terminal UI** (per project memory, presentation-only Textual state lives in this repo), and
none of Claude Design's output formats speak that language: no Textual widgets, no CSS-for-terminal constraints, no
keybinding/focus/overlay semantics, no 80×24 layout discipline. Treat every Claude Design mock of an agents-tab
redesign, deck/pager split, or frontmatter panel as a **directional sketch of hierarchy, density, and flow** — the
translation to keymaps, widgets, and `default_config.yml` still happens in-repo, best via the swarm → plan → coder
path you already use. A practical bridge: screenshot the current TUI (or a Textual web-export approximation) and
feed it as image context alongside a goal/layout/content/audience prompt, then carry the winning direction back as
reference images attached to the swarm prompt or plan file.

## 6. Verdict: in addition, not instead

- **Instead: no.** Claude Design cannot do what the swarm does — independent multi-model analysis, repo/bead/memory
  grounding, Textual-accurate specs, audited durable artifacts. Replacing the swarm would trade decisions for
  pictures.
- **In addition: yes, for three jobs the swarm is bad at:** (a) **exploring several visual directions in one
  sitting** instead of rationing exploration; (b) **showing** a flow to yourself/teammates and user-testing it
  without code review or a PR; (c) **producing decks/one-pagers/landing visuals** around a release without slide
  labor. The June Code-bridge work (`/design-sync`, `/design`, CLI artboard skill) is what makes the combination
  practical rather than a side toy: prototype visually, sync the system, hand a bundle to the coder that already
  implements from it.

## 7. Ranked list: Claude Design features likely most useful to you

Ordered by expected value for someone who designs sase UX via research swarms today:

1. **Live canvas + conversational iteration** — see a first draft immediately and refine in words; the single biggest
   gap in prose-only swarm reports.
2. **Inline element comments + direct manipulation + Tweaks sliders + draw/sketch input** — precise, low-verbal-
   overhead refinement, including by non-prompt-expert collaborators.
3. **Shareable interactive prototypes (URL / standalone HTML)** — hallway-test a flow or get buy-in with zero code
   review, PR, or local build; present decks in place.
4. **Design-system import from your GitHub repo + published org system** — keeps explorations on-brand (colors, type,
   components) instead of defaulting to the generic house style; multiple systems for sub-brands.
5. **Claude Code handoff bundle + `/design` + `/design-sync` (incl. CLI artboard skill)** — the prototype-to-code
   bridge that mirrors your plan→coder flow; bidirectional sync keeps canvas and code from drifting.
6. **Cheap divergent exploration** — clarifying-question behavior plus "save this, try a completely different
   approach" versioning; several directions per session where designers normally ration exploration.
7. **Multi-screen flow prototyping + Examples starters (incl. motion/shader skills)** — onboarding flows, feature
   flows, dashboards, animated concepts for demos and release visuals.
8. **Decks, one-pagers, and marketing/landing output (PPTX/PDF/Canva/Adobe/Gamma connectors)** — release
   communication without slide labor.
9. **Rich multimodal inputs (screenshots, DOCX/PPTX/XLSX, web-capture bookmarklet, voice)** — feed TUI screenshots
   and existing docs as starting context for grounded first drafts.
10. **Org sharing with comment/edit roles + persistent per-project workspace files** — async review where teammates
    chat with Claude inside the same design conversation.

**Explicit non-recommendations:** do not expect Textual-faithful output, Figma-native round-trips, late-stage
component precision, audit-logged governance, or data-residency compliance — all documented gaps. Start on a paid
plan with shared-pool limits (not Pro-constrained weekly caps), publish a design system *before* inviting broader
use, and keep the swarm as the decision-making and spec-authoring layer with Claude Design as its visual sketchbook.

## Sources

- Anthropic launch announcement, "Introducing Claude Design by Anthropic Labs" (17 Apr 2026):
  <https://www.anthropic.com/news/claude-design-anthropic-labs>
- DataCamp explainer incl. workflow walkthrough, design-system setup, export/handoff, limits, admin gaps (accessed
  2026-10-26): <https://www.datacamp.com/blog/claude-design>
- Zapier guide incl. workspace layout, Tweaks, web capture, export options, usage caps (accessed 2026-10-26):
  <https://zapier.com/blog/claude-design/>
- StudioMeyer/DEV "What It Is, Where It Fits, and When to Skip It" (19 Jun 2026):
  <https://dev.to/studiomeyer_io/claude-design-what-it-is-where-it-fits-and-when-to-skip-it-593d>
- Crypto Briefing June-overhaul report (17 Jun 2026):
  <https://cryptobriefing.com/anthropic-claude-design-overhaul/>
- Mike Gingerich June-update summary (`/design-sync`, `/design`, GitHub design-system import):
  <https://www.mikegingerich.com/blog/anthropics-claude-design-adds-direct-code-handoff/>
- Sparkone timeline (Apr preview → Jun beta → Aug CLI-artboard skill) and Anima/UXPilot/Flowstep Figma-limitation
  writeups (accessed 2026-10-26): <https://sparkone.nl/en/blog/artboards-in-your-terminal/>,
  <https://www.animaapp.com/blog/ai-design-en/claude-design-review-features-pros-cons-and-best-alternatives/>,
  <https://uxpilot.ai/blogs/claude-design-review>, <https://flowstep.ai/blog/claude-design-review/>
- SASE baseline: `sase macro show research_swarm` output and `src/sase/agent/macro_swarm.py`,
  `docs/reference/macros/multi-agent-prompts.md` in this workspace (read 2026-10-26).

