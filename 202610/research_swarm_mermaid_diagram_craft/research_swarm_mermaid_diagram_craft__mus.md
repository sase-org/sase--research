# Making the research swarm's Mermaid diagrams useful, self-contained, and beautiful

> **Research query:** The Mermaid diagrams the `#research_swarm` image agent
> recommends are hard to understand in isolation, not very useful, and not very
> visually appealing. How should we improve that agent's instructions — e.g. with
> Mermaid advice factored out into its own macro — and is that plan even the
> right approach?

## Bottom line

Yes, improve the instructions, but **do not create a new macro**. The Mermaid
advice is *already* factored out into its own macro — `#research/diagrams`
(`research_diagrams.md`, 208 lines, invoked as a separate block in the swarm's
image segment). The problem is not factoring; it is the content of that advice.
Three rules inside it directly produce the three complaints:

| Complaint | Rule that causes it |
|---|---|
| Hard to understand in isolation | Diagrams carry no in-fence title; all context lives in linker-placed captions and reference sentences |
| Not very useful | Type whitelist (`flowchart`, `sequenceDiagram`, `stateDiagram-v2`, `classDiagram`, `erDiagram`) excludes the types that fit surveys and comparisons, then concedes "zero is right" for exactly those reports |
| Not very visually appealing | Blanket ban on `init`, `style`, `classDef`, HTML, and icons mandates monochrome boxes |

The recommended fix is a focused revision of `#research/diagrams` §3–§4
(candidate bar + type allowlist) and §4 (a restrained, print-safe styling
allowlist plus mandatory in-diagram titles), keeping everything else —
validation, anchoring, manifest shape, linker placement, fail-open semantics —
exactly as it is. Details in [Recommended solution](#recommended-solution).

## 1. What the "image agent" actually is

Reading the current swarm template and the plugin source (via `sase repo open
sase-research-artifacts`) shows the image agent is one agent running **two**
macro blocks in sequence on a fork of the lead:

```text
%id(image, clan=research.{@1}) %m:{{ image_model }}
%wait:research.{@1}.final #_queue #fork:research.{@1}.final
  [#research/image]                      ← 10 lines: PNG infographic only
  [#research/diagrams]                   ← 208 lines: Mermaid drill-downs
```

Standalone `#research/image` is PNG-only by documented contract and never
produces diagrams. All Mermaid behavior — candidate selection, drawing rules,
`mmdc` validation, the `.diagrams.md` manifest, the `diagrams` status variable —
lives in `#research/diagrams`. Any "mermaid diagram advice factored out to its
own macro" already exists; a second advice macro would split one coherent
procedure across two files and force the image agent to reconcile them.

SASE macro composition supports both patterns, and the swarm already uses both:
file-local Jinja fragments (`macros: _queue:`, invoked as `#_queue`) for shared
boilerplate, and `#macro` invocation for whole-macro reuse (the image segment
invokes `#research/image` and `#research/diagrams`). A pure-advice fragment
with no invocation of its own would be the worst of both: untestable by the
macro-loading tests and invisible in the macro catalog.

**Adjustment 1: revise `#research/diagrams`; do not add a macro.**

## 2. Diagnosis: each symptom traces to a specific rule

### 2.1 "Difficult to understand in isolation" — no self-containment

A published diagram is surrounded by three layers of context, and **all three
live outside the fence**: the linker's italic caption underneath, the linker's
12–30-word reference sentence above (`the publication-order diagram traces
why…`), and the anchor passage in the body. The fence itself contains bare node
labels of "about four words or fewer" with no title. Anyone who encounters the
diagram alone — the SVG from the `mmdc` check, the fence quoted in chat, the
manifest entry — gets unlabeled boxes and arrows.

Mermaid has a native remedy the instructions never mention: an in-diagram title
(frontmatter-style `title:`) plus `accTitle`/`accDescr` accessibility lines.
These render *inside* the diagram image, travel with the fence wherever it is
copied, and cost two lines. The current §4 neither requires nor forbids them;
agents therefore omit them.

**Adjustment 2: require every proposed fence to carry its own title and
`accTitle` (one line each, drawn from the existing caption/`illustrates`
text so no new claims are introduced).**

Labels should also stay in the report's terms (already required — keep that),
and subgraph titles should be mandatory whenever a `subgraph` is used: an
untitled grouping box is the single most common "what am I looking at" failure
in flowcharts surveyed across public Mermaid agent skills.

### 2.2 "Not very useful" — the type whitelist mismatches the report genre

Section 4 allows five types: `flowchart`, `sequenceDiagram`,
`stateDiagram-v2`, `classDiagram`, `erDiagram`. Every one of them draws a
*mechanism* (flows, exchanges, lifecycles, structures). Meanwhile §3's pass/fail
bar concedes that "zero is right … common for surveys and recommendation
lists, where no panel hides a mechanism."

That concession is the tell: research reports are frequently surveys,
comparisons, and prioritizations, and the allowed types cannot express those.
The broader Mermaid ecosystem (convergent guidance across a dozen public
diagramming skills surveyed for this report) maps those genres to types this
macro forbids:

| Report content | Fitting type | Currently |
|---|---|---|
| Part-to-whole breakdown | `pie` | forbidden |
| Topic hierarchy, option tree | `mindmap` | forbidden |
| 2×2 tradeoff / prioritization | `quadrantChart` | forbidden |
| Chronology, roadmap, history | `timeline` | forbidden |
| Schedule with durations | `gantt` | forbidden |

Two further rules compound the problem. "Never turn a table into a diagram"
is overbroad: the linker already converts every table into a list because
pandoc/XeLaTeX mangles tables, so a comparison that survives only as a long
bullet list is precisely where a `quadrantChart` or `pie` would "read faster
than the prose" — the macro's own stated test. And the drill-down-only framing
("each one opens a single panel") forbids the one diagram readers of a survey
most need: a synthesis/overview map of the option space.

**Adjustment 3: widen the allowlist to `pie`, `mindmap`, `quadrantChart`,
and `timeline` (defer `gantt`, `journey`, `gitGraph`, `xychart-beta` —
rare in research reports and weaker in `mmdc`/PDF paths), each gated to its
genre, and narrow "never turn a table into a diagram" to "never redraw a
table one-to-one; diagram the comparison the table supports."** Keep the
three/five cap, the anchor rule, and the zero-is-legitimate outcome.

### 2.3 "Not very visually appealing" — the styling ban

Section 4 bans "init directives, `click`, `style`, `classDef`, HTML, or icons"
in one breath. That mixes three different risk classes:

- **Genuinely dangerous in this pipeline:** `click` (javascript URLs — an
  injection vector in a macro that copies report text into labels), raw HTML
  (breaks the pandoc → XeLaTeX PDF path the linker targets).
- **Safe and load-bearing for beauty:** `classDef`/`style` fills and strokes,
  `linkStyle`, named subgraph titles, and a single `%%{init}%%` theme block.
  These are core documented Mermaid syntax, parse under the same `mmdc`
  validation the macro already runs, and are the *only* lever that makes one
  diagram look different from another.

The ban is presumably why every swarm diagram looks identical: default-theme
monochrome boxes. Public styling guidance converges on a small, safe subset —
a `base` theme with a few `themeVariables`, plus two or three `classDef`
roles (e.g. terminal/decision/store) applied consistently — and explicitly
warns against per-node rainbow styling. That matches this pipeline's needs:
GitHub renders Mermaid natively with theme support, and `mmdc` SVG output
embeds the same fills, so both reading surfaces (GitHub page, Highlights PDF)
benefit.

One real constraint favors restraint over the ban: the PDF column is ~650 px
and the macro already rejects SVGs wider than ~1300 px natural width. Dark,
saturated fills that look fine on GitHub's dark mode print as muddy blobs in
a monochrome-printed PDF. So the fix is an allowlist with a print-safe palette,
not a free-for-all.

**Adjustment 4: replace the ban with a fixed styling snippet — one `init`
theme block plus at most three `classDef`s in a light print-safe palette —
pasted verbatim, with `click`/HTML/icons still forbidden.** (Concrete snippet
in the recommendation below.)

## 3. Critique of the proposed plan

**What is good.** Factoring diagram guidance out of the image agent is
correct: the infographic job (pick a model, draw a PNG) and the diagram job
(validate candidates, emit a manifest the linker places) have different
inputs, different validation, and different failure modes, and the current
split already reflects that. The manifest/linker contract — byte-identical
fences, verbatim anchors, `illustrates` as fidelity check — is well designed
and should not be reopened.

**What to change.**

1. **No new macro** (see §1). The deliverable is a revision of
   `research_diagrams.md` §§2–4 plus its `docs/macros.md` mirror, not a new
   file.
2. **Budget the token cost.** The image agent already carries both `#research/image`
   and the full 208-line `#research/diagrams`. A styling allowlist and genre
   table add ~40 lines to every image-agent invocation. Keep the addition to a
   fixed snippet plus a compact table; put rationale and examples in
   `docs/macros.md`, not the prompt.
3. **Do not chase beauty past the PDF.** The Highlights PDF path (pandoc →
   XeLaTeX, ~650 px column, tables already banned for renderer limits) is the
   binding constraint. Any styling that cannot survive `mmdc` SVG → PDF
   embedding must stay banned. Verify the new snippet through the real hook
   once, not just `mmdc`.
4. **Keep fail-open and the caps.** The `diagrams` status variable
   (`ready`/`none`/`failed`), the five-round fix cap, the 5-diagram ceiling,
   and "diagram failure never fails this agent" are load-bearing protections
   for the publication barrier. Styling additions must not add new
   must-succeed steps.

**What I would not do.** Three alternatives considered and rejected:

- *Generate diagrams inside the infographic PNG instead.* Image models mangle
  text and arrows; the output is undiffable, unlinkable, and unvalidatable.
  Mermaid's text-first nature (grep-able anchors, byte-identical placement,
  `mmdc` parse checks) is exactly what the linker contract needs.
- *A shared "mermaid advice" skill/memory used by all agents.* No other
  in-repo consumer exists today; a second discovery mechanism for one macro's
  prompt fragment adds indirection without reuse. Revisit only when a second
  macro needs the same snippet.
- *Letting the linker restyle diagrams.* The linker contract forbids editing
  fences ("never edit, redraw, merge, or invent"). Restyling at publish time
  would void the `mmdc` validation the manifest certifies. Style at proposal
  time, validate once.

## 4. Recommended solution

Revise `#research/diagrams` as follows (all section references are to
`research_diagrams.md`):

1. **§4, replace the type list** with a genre table:

   ```text
   - flowchart (TD default; LR only for ≤5 short nodes), sequenceDiagram
     (≤4 participants), stateDiagram-v2, classDiagram, erDiagram — mechanisms.
   - pie — part-to-whole the report quantifies. mindmap — hierarchies and
     option trees. quadrantChart — 2×2 tradeoffs/prioritizations.
     timeline — chronologies and roadmaps.
   - Nothing else (no gantt, journey, gitGraph, xychart-beta).
   ```

2. **§4, replace the styling ban** with a verbatim snippet agents paste
   unchanged (light fills, dark text, print-safe; role names fixed so all
   swarm diagrams share one visual language):

   ```mermaid
   %%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#eff6ff', 'primaryTextColor': '#1e3a8a', 'primaryBorderColor': '#93c5fd', 'lineColor': '#64748b'}}}%%
   flowchart TD
     A["Start"] --> B["Finish"]
     classDef team fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#1e3a8a
     classDef out fill:#f0fdf4,stroke:#22c55e,stroke-width:2px,color:#14532d
     classDef risk fill:#fef2f2,stroke:#ef4444,stroke-width:2px,color:#7f1d1d
   ```

   Keep forbidden: `click`, raw HTML, icons/emoji-as-syntax, per-node hex
   values outside the three roles, additional `init` keys. Subgraph titles
   required when `subgraph` is used.

3. **§4, require in-fence self-containment**: a `title:` line and an
   `accTitle` line on every fence, copied from the caption/`illustrates`
   text (no new claims). The fence must read sensibly with caption and
   reference sentence removed.

4. **§3, narrow the table rule** to "never redraw a table one-to-one;
   diagram the comparison the table supports, and only when the picture
   reads faster than the list the linker will publish." Keep the
   three-or-more-connected-parts bar and the no-invented-actors rule.

5. **§5, extend validation minimally**: after the existing `mmdc` + width
   checks, grep the fence for the required `title:`/`accTitle` lines and the
   absence of `click`/`<` in labels. No new tools, no new rounds.

6. **Tests**: extend the plugin's macro-loading tests with a fixture fence
   per allowed type containing the snippet, asserting the fences parse
   (pure string checks — `mmdc` needs Chrome, which agents' hosts may lack,
   so keep render checks fail-open as today). Mirror the new table and
   snippet in `docs/macros.md`.

7. **Rollout**: land behind no flag (prompt-template change in the plugin,
   same as prior `#research/diagrams` iterations); confirm on one
   `image=true diagrams=true` swarm by checking the Highlights PDF renders
   the styled SVGs legibly in the ~650 px column before treating this as
   done.

## 5. Evidence and verification notes

- Current-state claims (§1) were read directly from
  `xprompts/research_swarm.md` (image segment, lines ~279–288; linker
  placement rules, lines ~477–536; `macros: _queue` fragment pattern),
  `xprompts/research_image.md` (10 lines, PNG-only), `xprompts/research_diagrams.md`
  (§§2–8, including the §4 ban and §3 survey concession), `docs/macros.md`,
  and `provider.py` (hook globs, researcher-suffix vetoes).
- Styling-safety claims rest on Mermaid's documented syntax (`init` theme
  blocks, `classDef`, `linkStyle`, subgraph titles, `title`/`accTitle`) and
  convergent public agent-skill guidance; I attempted an `mmdc` render check
  on this host but its Chrome binary is absent (`Could not find Chrome …
  131.0.6778.204`), so render validation here was impossible and the
  snippet above is docs-grounded, not render-proven — the rollout step (§4.7)
  is where it must pass `mmdc` for real.
- Peer reports from this swarm (`__cdx`, `__cld`, `__grk`, `__gem`) were
  deliberately not opened; filename existence only was checked to avoid
  overwriting this report.
