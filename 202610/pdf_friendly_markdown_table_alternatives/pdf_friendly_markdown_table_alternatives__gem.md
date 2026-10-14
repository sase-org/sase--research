# Beautiful Alternatives to Markdown Tables for PDF Generation

> **Research query:** Recommend the best alternative to Markdown tables that renders beautifully when converting research Markdown documents to PDF, and formulate actionable instructions for the `#research_swarm` linker agent to eliminate Markdown tables from consolidated reports.

## Bottom line

**Do not replace Markdown tables with another 2D grid syntax; replace them with Fielded Data Cards.** 

When Markdown is rendered to PDF—especially via Pandoc + XeLaTeX in `bob ref create` (used for Bryan's Obsidian reading queue and Highlights app annotation) and Pandoc in SASE's mobile attachment profile (4.25" × 7")—Markdown pipe tables break down catastrophically. They suffer from rigid column width starvation, overfull `\hbox` margin clipping, truncated multi-sentence prose, awkward page-breaking where tall rows refuse to split across pages, and frustrating text-selection behavior in PDF annotation apps. Raw HTML tables are even worse: Pandoc's LaTeX writer strips HTML `<table>` tags entirely, dumping naked cell text onto successive lines.

The optimal, battle-tested solution is **Fielded Data Cards (Subheadings + Labeled Bullet Fields)**, paired with a small set of semantic conversion archetypes for specific data shapes:

1. **Option & Alternative Comparisons:** Convert to **Entity Data Cards** (`### [Entity Name]` followed by bolded attribute keys `- **Key:** Value`).
2. **Multi-Agent Debates & Question Syntheses:** Convert to **Structured Issue Breakdowns** (`### Issue [N]: [Topic]` with nested `- **Question:**`, `- **Positions:**`, and `- **Resolution:**` blocks).
3. **Configurations, Parameters & Properties:** Convert to **Fielded Bullet Items** (`- `param` (*type*, default `val`): Description`).
4. **Metrics & Quantitative Benchmarks:** Convert to **Progression Bullets** (`- **Metric:** Current (vs Baseline; Delta) — Context`).
5. **Phased Roadmaps & Execution Sequences:** Convert to **Numbered Milestones with Nested Fields** (`1. **Phase:** ...` with indented objective and deliverables).

This approach delivers full-width text reflow, flawless LaTeX page pagination, rich multi-line content formatting (including code blocks and sub-lists), effortless single-column highlighting in the Highlights app, natural text-to-speech cadence for `sase-listen`, and 100% deterministic generation reliability from LLM linker agents.

The exact linker prompt snippet to add to `src/sase_research_artifacts/xprompts/research_swarm.md` is provided in [Actionable linker agent instructions](#actionable-linker-agent-instructions).

---

## Why Markdown tables fail in PDF pipelines

To select the best alternative, we must first diagnose why Markdown tables fail so severely when transformed into PDFs. In the SASE ecosystem, research Markdown files undergo two primary PDF compilation workflows:

1. **The Highlights / Reading Queue Pipeline (`bob ref create`)**:
   - Engine: `pandoc` using `--pdf-engine=xelatex`, `--geometry:margin=0.85in`, 10pt base font, and `fvextra`.
   - Output target: Standard US Letter format (`8.5in × 11in`).
   - Printable width: `8.5 - (2 × 0.85) = 6.8 inches`.
   - Primary consumption: iPad and macOS via the **Highlights app** for deep reading, highlighting, and marginal notes.
2. **SASE Agent Run Attachments (`sase.attachments.markdown_pdf`)**:
   - Engine: `pandoc` with `wkhtmltopdf` (or `xelatex`/`pdflatex` fallback), styled via `markdown_pdf.css`.
   - Output target: Mobile / pocket reading profile (`4.25in × 7in`, `0.22in` margins).
   - Printable width: `4.25 - (2 × 0.22) = 3.81 inches`.

Both pipelines expose the fundamental structural impedance mismatch between Markdown pipe tables and fixed-geometry paginated PDF documents.

### Horizontal space starvation and rigid column widths

In web browsers, tables reflow responsively or scroll horizontally (`overflow-x: auto`). In a PDF, pages have unyielding physical boundaries. 

When Pandoc parses CommonMark or GFM pipe tables into LaTeX, it utilizes the `longtable` environment. To calculate column widths, Pandoc analyzes the relative character count of the delimiter row dashes (`|---|---|`). Because LLM agents almost universally emit arbitrary, uniform delimiter lengths, Pandoc defaults to assigning each column an equal fraction of the text width.

- On US Letter (`6.8in` printable width), a 4-column table gives each column approximately `1.6 inches` (~25 characters in 10pt font).
- In the mobile PDF profile (`3.81in` printable width), a 4-column table gives each column less than `0.9 inches` (~14 characters in 12pt font).

When complex technical prose is forced into a 14-to-25 character column, words wrap every 2 to 3 words. A single paragraph stretches vertically into an absurdly elongated, unreadable ribbon.

### Overfull margins and token clipping

In technical research, table cells frequently contain unbroken alphanumeric tokens:
- File paths (e.g., `sase/repos/linked/sase-research-artifacts/src/...`)
- Fully qualified plugin hooks (e.g., `sase_research_artifacts@research-highlights`)
- CLI command invocations (e.g., `sase artifact read research:202610/...`)
- External URLs and commit hashes

LaTeX does not hyphenate or wrap inline code spans or unbroken strings inside `p{width}` boxes by default. When a token exceeds the column width, LaTeX produces an `Overfull \hbox` warning and draws the text straight across column borders or off the right margin of the physical PDF page, rendering the text invisible or illegible.

### The cell expressiveness ceiling

Standard Markdown pipe tables do not permit block-level formatting within cells. Authors and agents cannot cleanly include:
- Nested bullet points or sub-checklists
- Numbered sequential sub-steps
- Fenced code blocks (` ```python `)
- Multiple distinct paragraphs
- Blockquotes or callouts

When agents attempt to force rich information into tables, they either produce unformatted run-on text, rely on awkward `<br>` tags that break portability across Markdown renderers, or lose crucial nuances (caveats, code snippets, edge cases).

### Row-level pagination pathologies

In LaTeX `longtable`, page breaks can occur *between* rows, but never *within* an individual table row. If an agent writes a thorough comparative row containing 5–6 sentences across columns, that row can easily require 3 to 4 vertical inches.

If the page reaches the top of that row with only 2 inches of vertical clearance remaining, LaTeX cannot split the row across the page boundary. Instead, it forces the entire row to the next page. This leaves a gaping empty white hole at the bottom of the preceding page, creating disjointed, amateurish pagination.

### Annotation friction in the Highlights app

The primary consumer of these research PDFs is human review via the Highlights app on iPad and Mac. PDF text-selection engines map bounding boxes across spatial coordinates. Selecting text within narrow table columns frequently drags the selection box into neighboring cells, highlights column border artifacts, or scrambles copied text into interleaved fragments. By contrast, linear full-width text highlights smoothly and exports cleanly into research synthesis notes.

### Audio and screen-reader degradation (`sase-listen`)

SASE features integrated audio narration via `sase listen render` and `bob ref create --listen`. Text-to-speech engines cannot navigate two-dimensional tables intelligently. They either recite delimiter noise ("pipe dash dash pipe") or read row-by-row in a disjointed stream that strips values of their header context. Replacing tables with semantic headings and fielded bullets produces natural, fluent spoken audio editions.

---

## Evaluation of candidate table alternatives

We evaluated six candidate formatting alternatives against seven critical criteria:
- **PDF Visual Quality:** Freedom from margin clipping, graceful typography, and balanced layout.
- **Pagination & Reflow:** Clean page breaks without orphaned content or large blank gaps.
- **Expressiveness:** Full support for code snippets, nested bullets, and multi-paragraph nuance.
- **Raw Markdown Readability:** Clean, scannable presentation in Obsidian, GitHub, and terminal pagers.
- **Annotation Usability:** Ease of highlighting and extracting clean text in the Highlights app.
- **Audio / TTS Compatibility:** Fluent, coherent narration when rendered with `sase-listen`.
- **LLM Conversion Reliability:** Consistency with which a linker agent can execute the transformation without losing data.

### Fielded Data Cards (Subheadings + Labeled Bullets)
- **Structure:** `### [Entity Name]` followed by indented `- **[Field]:** [Value]`.
- **PDF Quality:** Flawless. Utilizes 100% of the printable text width (6.8" on Letter, 3.8" on mobile).
- **Pagination:** Excellent. Pages break naturally between items or between lines of text.
- **Expressiveness:** Unlimited. Any field can host sub-bullets, blockquotes, or fenced code blocks.
- **Annotation & Audio:** Outstanding. Natural rectangular highlights and fluent TTS narration.
- **LLM Reliability:** Very high. LLMs follow key-value schemas with exceptional fidelity.
- **Verdict:** **Recommended Primary Solution.**

### Dimension-First / Criteria-Grouped Lists
- **Structure:** `### [Criterion Name]` followed by `- **[Entity A]:** ...` and `- **[Entity B]:** ...`.
- **PDF Quality:** Flawless reflow and typography.
- **Pagination:** Clean page breaks.
- **Expressiveness:** High, though deeply nested lists can become visually heavy.
- **Drawback:** Becomes unwieldy when comparing more than 2–3 entities or when entities have differing attributes.
- **Verdict:** Recommended as a secondary pattern specifically for tight 2-option head-to-head comparisons.

### Native Markdown Definition Lists (`Term : Definition`)
- **Structure:** Pandoc-style definition lists (`Term\n: Definition`).
- **Failure Mode:** Portability failure. GitHub Flavored Markdown (GFM) and Obsidian do not natively render colon-based definition lists; they appear as raw plain text with dangling colons.
- **Verdict:** **Rejected.** Violates portability across Obsidian and GitHub.

### Blockquote Cards (`> [!NOTE]` or `> **Item**`)
- **Structure:** Markdown blockquotes containing bolded attributes.
- **Failure Mode:** In LaTeX output, blockquotes are wrapped in `\begin{quote}`, which indents both left and right margins, further constricting printable width. GitHub alert syntax (`[!NOTE]`) is unsupported in standard Pandoc LaTeX templates without custom filters and renders as literal raw text.
- **Verdict:** **Rejected.** Restricts horizontal width and introduces template dependencies.

### Preformatted ASCII / Box-Drawing Blocks (` ```text `)
- **Structure:** Text-based grid tables inside fenced code blocks.
- **Failure Mode:** Catastrophic in PDF. In `create.rs`, Pandoc configures `fvextra` with `breakanywhere` to prevent code overflow. When an ASCII table wraps, box lines fracture across lines into illegible character soup. Furthermore, links inside code blocks are unclickable, text cannot be formatted, and annotation in Highlights is crippled.
- **Verdict:** **Rejected.**

### Raw HTML Tables (`<table>...</table>`)
- **Structure:** Standard HTML table markup.
- **Failure Mode:** Fatal in Pandoc LaTeX. As verified directly on Pandoc 3.1.11, Pandoc's LaTeX writer silently strips HTML `<table>`, `<tr>`, and `<td>` tags, dumping the naked contents of every cell onto sequential plain lines.
- **Verdict:** **Rejected.**

---

## The recommended solution: Fielded Data Cards

The recommended solution is to establish **Fielded Data Cards** as the standard structural pattern for multi-attribute information in research reports. 

Because research reports contain diverse information architectures, the linker agent should be instructed on **Five Semantic Conversion Archetypes**.

### Archetype 1: Option and alternative comparisons

Used when comparing competing architectures, naming options, tools, or strategies (e.g., comparing candidate names in `sase_rename_new_name_shortlist`).

#### Before (Markdown Table)

```markdown
| Option | PyPI Name | Crates.io | Meaning & Tone | Verdict |
| --- | --- | --- | --- | --- |
| `handful` | Clean | Clean | Evokes human directing a small team of agents; grounded | **Top pick (Rank 1)** |
| `baste` | Taken (dormant) | Clean | Sewing metaphor: light temporary stitching before final seam | Runner-up (Rank 2) |
| `crewrail` | Clean | Clean | Evokes structured tracks for an autonomous crew | Runner-up (Rank 3) |
```

#### After (Entity Data Cards)

```markdown
### `handful`
- **Namespace clearance:** PyPI is clean; crates.io is clean; no GitHub org collision.
- **Meaning & tone:** Evokes a single human directing a capable team; grounded, non-corporate, memorable.
- **Length:** 7 characters.
- **Verdict:** **Top pick (Rank 1).** Strongest semantic match for SASE's multi-agent directing model.

### `baste`
- **Namespace clearance:** Crates.io clean; PyPI taken by an abandoned 2011 package (reclaimable).
- **Meaning & tone:** Sewing metaphor representing temporary stitches holding pieces until final stitching.
- **Length:** 5 characters.
- **Verdict:** **Runner-up (Rank 2).** Elegant metaphor matching SASE's "stitch" workflow, but requires namespace recovery.

### `crewrail`
- **Namespace clearance:** PyPI is clean; crates.io is clean.
- **Meaning & tone:** Evokes structured guardrails and repeatable tracks for an autonomous agent crew.
- **Length:** 8 characters.
- **Verdict:** **Runner-up (Rank 3).** Clear meaning, but approaches the 8-character length boundary.
```

### Archetype 2: Multi-agent debates and question syntheses

Used when resolving architectural questions where researchers held divergent views (as seen in `sase_listen_plugin_commands` and `#research_swarm` lead syntheses).

#### Before (Markdown Table)

```markdown
| # | Architectural Question | Researcher Positions | Lead Resolution |
| --- | --- | --- | --- |
| 1 | Who parses args after `sase listen`? | **mus, gem:** Sase subparsers parse and dispatch `args.func`.<br>**cdx, cld, grk:** Plugin parses its own argv. | **Plugin parses.** Subparser sharing triggers `dest="command"` collisions and bypasses listen's signal and environment handlers. |
| 2 | In-process execution vs subprocess exec? | **cld, cdx:** In-process `main()`.<br>**grk:** Exec standalone console script. | **In-process.** Eliminates ~50ms Python startup penalty and preserves environment fidelity. |
```

#### After (Structured Issue Breakdowns)

```markdown
### Decision 1: Who parses arguments after `sase listen`?
- **Core question:** Should SASE core register CLI subparsers and dispatch execution, or should the plugin parse its own argv?
- **Researcher positions:**
  - `mus`, `gem`: SASE subparsers should parse everything and dispatch to `args.func`.
  - `cdx`, `cld`, `grk`: The plugin should parse its own argv.
- **Resolution:** **Plugin parses.** Reproducible `dest="command"` collisions occurred when attempting to share subparsers. Furthermore, delegating to the plugin's own parser preserves critical `BrokenPipeError` handling and environment checks that SASE's wrapper would otherwise bypass.

### Decision 2: In-process execution versus subprocess exec
- **Core question:** Should plugin commands run in-process or via an external subprocess?
- **Researcher positions:**
  - `cld`, `cdx`: In-process call to `main(argv, prog)`.
  - `grk`: Docker-style exec of the standalone console script.
- **Resolution:** **In-process execution.** In-process dispatch eliminates the ~50ms interpreter bootstrap latency. Because SASE commands are executed frequently in developer loops, sub-millisecond response is critical. Subprocess execution remains an isolated fallback if memory isolation is ever required.
```

### Archetype 3: Configuration parameters and property catalogs

Used when documenting API inputs, frontmatter keys, CLI flags, or schema definitions.

#### Before (Markdown Table)

```markdown
| Flag / Input | Type | Default | Description |
| --- | --- | --- | --- |
| `image` | boolean | `false` | Enables infographic generation via `#research/image`. Implies `linker=true`. |
| `image_model` | word | `"@image"` | Model alias used by the infographic generation agent. |
| `linker` | boolean | `false` | Enables post-lead restructuring and link validation. |
| `linker_model` | word | `"@xlarge"` | Model tier assigned to the linker agent. |
```

#### After (Fielded Bullet Items)

```markdown
- `image` (*boolean*, default `false`): Enables infographic generation via `#research/image`. Note that enabling `image` automatically implies `linker=true`.
- `image_model` (*word*, default `"@image"`): Model alias used by the infographic generation agent. Defaults to the multi-provider image fallback chain.
- `linker` (*boolean*, default `false`): Enables the post-lead restructuring and link-validation agent that publishes the canonical `<name>.md` report.
- `linker_model` (*word*, default `"@xlarge"`): Model tier assigned to the linker agent to ensure zero loss of nuance during document synthesis.
```

### Archetype 4: Quantitative metrics and comparative benchmarks

Used when presenting growth statistics, benchmark timings, or resource measurements.

#### Before (Markdown Table)

```markdown
| Metric | 2026-07-28 | 2026-10-04 | Growth |
| --- | ---: | ---: | ---: |
| Tracked files | 5,728 | 12,994 | 2.3× |
| Files mentioning `sase` | 4,610 | 10,762 | 2.3× |
| Total occurrences of `sase` | 59,130 | 141,784 | 2.4× |
| Distinct `SASE_*` identifiers | 360 | 703 | 2.0× |
```

#### After (Metric Progression Bullets)

```markdown
- **Tracked repository files:** 12,994 (expanded from 5,728 in July; **2.3× growth**).
- **Files referencing `sase`:** 10,762 (expanded from 4,610 in July; **2.3× growth**).
- **Total `sase` token occurrences:** 141,784 (expanded from 59,130 in July; **2.4× growth**).
- **Distinct `SASE_*` identifiers:** 703 (expanded from 360 in July; **2.0× growth**).
```

### Archetype 5: Phased roadmaps and execution sequences

Used when detailing implementation phases, release plans, or sequential migration milestones.

#### Before (Markdown Table)

```markdown
| Phase | Focus Area | Deliverables | Target Timeline |
| --- | --- | --- | --- |
| 1 | Core Specifications | Update `provider.py`, adjust file-hook filters | Days 1–2 |
| 2 | Prompt Integration | Implement linker prompt in `research_swarm.md` | Days 3–4 |
| 3 | Verification & CI | Pass `just check` and verify PDF generation | Day 5 |
```

#### After (Numbered Milestones with Nested Fields)

```markdown
1. **Phase 1: Core Specifications & Hook Filters**
   - **Focus:** Update plugin metadata and file-hook exclusion rules.
   - **Deliverables:** Modify `provider.py` and `default_config.yml` in `sase-research-artifacts`.
   - **Timeline:** Days 1–2.
2. **Phase 2: Prompt Engineering & Linker Integration**
   - **Focus:** Integrate restructuring instructions into the macro swarm definition.
   - **Deliverables:** Update `src/sase_research_artifacts/xprompts/research_swarm.md` and expand unit test assertions in `test_xprompt_loading.py`.
   - **Timeline:** Days 3–4.
3. **Phase 3: End-to-End Verification & Validation**
   - **Focus:** Execute end-to-end swarm tests and inspect Highlights PDF rendering.
   - **Deliverables:** Validate `just check` across repositories and confirm zero table artifacts in generated PDFs.
   - **Timeline:** Day 5.
```

---

## Actionable linker agent instructions

To implement this recommendation across the `#research_swarm` macro swarm, update the linker agent prompt in `src/sase_research_artifacts/xprompts/research_swarm.md`.

Specifically, modify **Step 2 (Inventory)** and **Step 3 (Restructure)** of the linker segment.

### Linker prompt diff specification

#### In Step 2 (Inventory what must survive)

Append the following instruction to Step 2:

> When inventorying tables from the lead's report, extract all raw data points, entity names, comparative attributes, metrics, and resolutions into a structured list so that no information is dropped when converting tables in Step 3.

#### In Step 3 (Restructure)

Add a prominent instruction under the restructuring rules:

```text
- **No Markdown tables.** Never output Markdown pipe tables (`|---|`) or HTML `<table>` blocks. Research reports are compiled into Highlights PDFs and mobile editions, where tables break margins, truncate text, and impair iPad annotations. Convert all tabular data from the lead's report into full-width **Fielded Data Cards**:
  - **Comparisons & Alternatives:** Convert each row into a `### [Entity Name]` subheading followed by bulleted attributes (`- **[Key]:** [Value]`).
  - **Architectural Questions & Positions:** Convert each row into a `### Issue [N]: [Topic]` section with nested `- **Question:**`, `- **Positions:**` (listing researcher stances), and `- **Resolution:**` (with bold takeaway and rationale).
  - **Properties, Flags & Parameters:** Convert into fielded bullet items (`- `name` (*type*, default `val`): [Description]`).
  - **Metrics & Benchmarks:** Convert into progression bullets (`- **[Metric]:** [Current] (vs [Baseline]; [Delta]) — [Context]`).
  - **Phases & Milestones:** Convert into numbered items with nested objective, deliverable, and timeline fields.
  Keep all caveats, metrics, notes, and links from the original table intact.
```

---

## Verification and transition strategy

1. **Prompt Template Integration:**
   - Update `src/sase_research_artifacts/xprompts/research_swarm.md` in the `sase-research-artifacts` repository.
   - Update `tests/test_xprompt_loading.py` to assert that the linker segment contains `"No Markdown tables"` and `"Fielded Data Cards"`.
2. **Automated Verification:**
   - Run `sase tool run check` in `sase-research-artifacts` to verify prompt parsing and tests.
   - Expand a test research swarm with `sase xprompt expand '#research_swarm(linker=true):: test'` and confirm the instruction renders cleanly without template syntax leakage.
3. **PDF Visual Inspection:**
   - Run a test research report through `bob ref create <report>.md -P sase -d` and inspect the generated PDF. Confirm that all converted Fielded Data Cards wrap at full margin width (6.8"), break pages cleanly between cards, and highlight seamlessly.
