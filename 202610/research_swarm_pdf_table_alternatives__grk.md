# PDF-Friendly Substitutes for Markdown Tables in Research-Swarm Linker Output

> **Research query:** What should the `#research_swarm` linker agent convert markdown tables into, so the canonical research file it publishes still carries the same facts and renders beautifully when that file is turned into a PDF?

## Bottom line

Tell the linker to convert every markdown table into **labeled lists**: a bullet whose lead-in is the row key in bold, with nested `**Column:** value` bullets for the remaining cells.

That is the substitute that is beautiful in the Highlights PDF, readable on GitHub, narratable as audio, and mechanical for an editor agent to emit. Use a `###` heading per row only when there are a handful of distinct options a reader will jump to. Do not keep two-column pipe tables as an exception. Do not convert tables into HTML, definition-list colon syntax, fenced `:::` divs, GitHub alerts, ASCII art, or raw LaTeX.

The rest of this report is the evidence, the rejected substitutes, and a copy-paste instruction for the linker prompt.

## The PDF the linker is writing for

The file the linker publishes, `<name>.md`, is the one SASE renders into a Highlights PDF. The `research-highlights` file hook runs `bob highlights create --include-id` on that `ADD`. `bob ref create` then renders Markdown with pandoc and XeLaTeX. Verified from `bob-cli` `src/native/highlights_ref/create.rs` (`render_temp_pdf`) and `docs/highlights-create.md`:

- `--standalone --toc --toc-depth=3 --number-sections`
- `--pdf-engine=xelatex`
- `--highlight-style=tango`
- Lua filters: code-break plus listen-card rewrite, then return-link pills
- `geometry:margin=0.85in`, `fontsize=10pt`, `linestretch=1.08`
- DejaVu Serif / Sans / Sans Mono
- US Letter (612 × 792 pt)
- Raw HTML is suppressed in LaTeX output ([Pandoc User's Guide, Raw HTML](https://pandoc.org/MANUAL.html#raw-html)); the only HTML the Bob Lua filter special-cases is `<div class="listen">`

A second, narrower path exists for agent-attachment Markdown: SASE's `markdown_pdf.py` uses pandoc with **wkhtmltopdf** on a **4.25 in × 7 in** page and `markdown_pdf.css` (`table-layout: fixed; overflow-wrap: anywhere`). That is not the Highlights hook, but the same source file can be paged in the TUI, so a substitute that only works at Letter width is not enough.

The linker prompt already knows this pipeline. It forbids hand-numbered headings because `--number-sections` would double-number them, forbids an in-file TOC because the PDF already gets one, and inventories every table in the lead's report. It does not yet say what to turn those tables into.

## Why pipe tables fail in this pipeline

Pandoc maps pipe, grid, and simple tables to LaTeX `longtable` plus `booktabs`. Wrapping is conditional ([Pandoc User's Guide, pipe tables](https://pandoc.org/MANUAL.html#extension-pipe_tables); [jgm/pandoc#4239](https://github.com/jgm/pandoc/issues/4239); [jgm/pandoc#7393](https://github.com/jgm/pandoc/issues/7393)):

- If **no** source line is wider than `--columns` (default 72), column widths stay `ColWidthDefault`. XeLaTeX emits `l`/`c`/`r` columns. Cell text does not wrap. Unbreakable tokens (URLs, identifiers, paths) run off the page or are clipped.
- If some source line **is** wider than `--columns`, pandoc assigns relative widths and wraps. A five-column comparison then becomes five cramped minipages. Headers repeat across page breaks. The table is technically on the page and still ugly.
- Compact two-column tables are centered (`longtable` with `[c]`), so a short Field/Value block sits as an island instead of using the text measure.
- Underscores in identifiers disable TeX hyphenation unless extra packages are loaded. Bob's header-includes wrap **code** (`fvextra` / `Highlighting`) and **listen cards**. They do not wrap table cells.

Empirical check, 2026-10-14, pandoc 3.1.11.1 + XeLaTeX (TeX Live 2025/dev/Debian), Bob's page/font/margin flags, no extra table filter:

- A five-column comparison whose source lines exceeded `--columns` wrapped, but the Audio column hyphenated into fragments (`confusi / ng row- / major`) and the table split across pages with a repeated header.
- A compact two-column table with a long URL and `SOME_LONG_VARIABLE_NAME_THAT_CANNOT_HYPHENATE` **clipped** in the PDF extract: the URL ended at `utm_source=re`, the identifier at `HYPHEN`.
- The same compact table through SASE's wkhtmltopdf 4.25 × 7 in profile wrapped the URL (CSS `overflow-wrap: anywhere`) and still produced an unreadable five-column grid, with words split mid-token (`definitio / n`).

That is the failure mode the linker is being asked to prevent: not "pandoc cannot emit a table," but "the table that lands in Highlights is clipped, cramped, or both."

## What "beautiful" has to mean here

The canonical file is public GitHub Markdown **and** a Highlights PDF **and** (when `audio=true`) the sibling of a narrated edition. A substitute has to satisfy all four:

1. **XeLaTeX Highlights PDF.** Full text measure, wrapping at 10 pt DejaVu, no clipped URLs, no five-column squeeze, compatible with `--toc` / `--number-sections` and the return-link filter.
2. **GitHub.** The research sidecar is public. GFM must render the substitute as structure, not as literal punctuation.
3. **Audio.** A brief edition is a spoken summary of the published report's ideas. Row-major table cells become soup; labeled lists read as "term, then value."
4. **Linker-mechanizable.** An editor agent, not a researcher, has to rewrite tables without adding claims. The pattern has to be one rule with a small number of shapes, not a typesetting hobby.

## Alternatives

### Labeled lists (recommended)

Markdown:

```markdown
- **Pipe tables.** Pandoc emits `longtable` plus `booktabs`. Wrapping only happens
  when a source line is wider than `--columns`.
  - **PDF:** Overflow and cramped columns.
  - **GitHub:** Native GFM.
  - **Audio:** Confusing row-major reading.
  - **Verdict:** Fail.
```

Pandoc emits nested `itemize`. Definitions occupy the full measure. Bold labels replay the old column headers. Bob's return-link filter tags list items. GitHub, CommonMark, Obsidian, and the TUI pager all render this as a list.

On the same XeLaTeX run as the overflowing pipe table, this shape wrapped URLs and identifiers instead of clipping them, and it did not enter the TOC.

**Use this as the default conversion.**

### Per-row headings, then labeled bullets

Markdown:

```markdown
### Pipe tables

- **PDF wrap:** Cells overflow when source lines are short.
- **GitHub:** Native GFM.
- **Audio:** TTS reads cells in confusing row-major order.
- **Verdict:** Fail.
```

Same wrapping as labeled lists, plus a numbered TOC entry and a return-link target on the heading. That is the right shape when each row is a **named option** a reader will jump to from the bottom line (a handful of alternatives, a decision among tools).

It is the wrong shape for a twenty-row property dump. The PDF TOC is generated with `--toc --toc-depth=3`; twenty `###` rows become twenty numbered entries and, if audio chapters follow headings, twenty tiny chapters.

**Use this only for a short option set (about six rows or fewer), each with a stable name.**

### Pandoc definition lists

Markdown:

```markdown
Pipe tables
: Pandoc emits `longtable` plus `booktabs`. Wrapping only happens when a
  source line is wider than `--columns`.
```

Pandoc emits a LaTeX `description` environment. On the empirical PDF this wrapped at full measure and looked like a glossary. Bob's return-link docs explicitly treat definition lists as taggable.

GFM does not implement definition lists ([GFM is CommonMark plus tables, task lists, strikethrough, autolinks, tag filter](https://github.github.com/gfm/); confirmed by flavor matrices through 2025–2026 and by GitHub PRs that replace colon syntax because it renders as a single mashed paragraph). On the public research sidecar the source would look broken.

Long terms in `\item[…]` also wrap worse than a bold lead-in inside a paragraph.

**Do not tell the linker to emit this.** It is the prettiest *PDF-only* glossary, and the report is not PDF-only.

### HTML `<dl>`, `<table>`, or styled cards

GitHub will render `<dl>` and `<table>`. Pandoc's LaTeX writer suppresses raw HTML. In the empirical file, an HTML description list became two loose paragraphs ("HTML term" then the definition) with no list structure. A styled card would need a new Lua filter, the way `<div class="listen">` already has one. Inventing a second special-case HTML dialect for tables is a Bob change, not a linker instruction.

**Reject.** The linker is an editor of Markdown, not of Bob's renderer.

### Grid tables, simple tables, and "just make the pipe table wider"

These are still `longtable`. Grid tables in the empirical PDF rendered as a centered island, same family as compact pipe tables. Asking the linker to pad separator lines so `--columns` wrapping kicks in is fragile (agents emit short lines with long tokens, which is the overflow case) and still yields cramped multi-column minipages.

**Reject.** The request is to stop emitting tables, not to tune them.

### ASCII / Unicode tables in fenced code

Bob's `fvextra` header wraps Highlighting environments, so a short monospaced matrix will stay on the page. It will also look like a code sample, skip return-link pairing (CodeBlock targets are untagged), and read badly in audio. Use this only for a true numeric matrix that must stay column-aligned (a 3×3 of numbers, a tiny truth table). Research-swarm comparison tables are almost never that.

### GitHub alerts, fenced `:::` divs, raw LaTeX `tabular`

Prior swarm research on listen links already measured these under Bob's flags: `> [!AUDIO]` and `::: listen` survive as **literal syntax** in pandoc 3.1.x and on GitHub. Raw `\begin{tabular}` is invisible on GitHub and bypasses Bob's filters. None of these is a table substitute.

## What the conversion preserves

The linker is an editor. The lead's meaning stays. The rewrite is structural:

- Every non-empty cell's text is kept.
- The header row becomes the bold labels (`**PDF wrap:**`, `**GitHub:**`, …).
- The first column, or the column that names the option, becomes the parent bullet's lead-in (or the `###` heading).
- Empty cells are omitted, not emitted as blank bullets.
- Links, code spans, and emphasis inside cells stay as inlines in the new bullets.
- A caption under the table (`: Some caption` / `Table: …`) becomes a one-line paragraph immediately above the list.

## Copy-paste instruction for the linker agent

Add this as a numbered step in the linker prompt, next to the existing inventory of tables and the heading/TOC rules. Suggested placement: after "Inventory what must survive" and inside "Restructure", so conversion happens before link validation.

````markdown
**No markdown tables.** The published file is rendered to a Highlights PDF
with pandoc and XeLaTeX (`--toc --number-sections`, Letter, 10 pt, 0.85 in
margins). Pipe, grid, and simple tables become `longtable`: compact tables
clip unbreakable URLs and identifiers; wide tables squeeze into cramped
columns. Convert every table in the lead's report before writing `<name>.md`.
Do not leave a pipe table in, including two-column Field/Value tables.

Convert using **labeled lists** as the default:

- Parent bullet: `**Row key.**` plus any one-line summary or verdict.
- Nested bullets: `**Column header:** cell text`, one per remaining
  non-empty cell, using the header row as the labels.
- Keep every cell's wording, links, and code spans. Drop empty cells.

Example, from a four-column comparison:

```markdown
- **Labeled lists.** Default conversion; wraps at full measure.
  - **PDF:** Full-width nested `itemize`; return-link filter tags items.
  - **GitHub:** Native GFM.
  - **Audio:** Reads as term, then value.
```

**Per-row headings** (`### Row key`, then the same nested `**Column:**`
bullets) only when every row is a named option a reader will jump to
**and** there are about six rows or fewer. Headings enter the PDF TOC
and must still start with a letter, stay unique, and contain only
letters, digits, spaces, and hyphens.

**Last resort, numeric matrices only:** a fenced code block containing a
short monospaced grid (3×3 of numbers, a tiny truth table). Not for
prose comparisons.

**Do not convert tables into any of these:**

- HTML `<table>`, `<dl>`, or styled cards (raw HTML is dropped or
  flattened in XeLaTeX; only `<div class="listen">` is special-cased)
- Pandoc definition-list colon syntax (beautiful in PDF, plain text on
  GitHub; the sidecar is public)
- Grid or simple tables, or "wider" pipe tables
- GitHub alerts (`> [!NOTE]`) or fenced `::: … :::` divs (literal in
  pandoc and on GitHub)
- Raw LaTeX `tabular` / `longtable`

Re-check the step-2 inventory after conversion: every table cell's text
must appear in the new lists.
````

That is the whole instruction. It does not ask the linker to restyle Bob, add a Lua filter, or keep a "simple tables are fine" escape hatch.

## Why not a Bob-side table fixer instead

A Lua filter that turns every Table into a definition list, or header-includes that load `tabularx` / `underscore`, would make *existing* reports prettier without a linker rule. That is a reasonable follow-up in `bob-cli`. It is the wrong answer to this question.

- The user asked what to **tell the linker to convert tables into**.
- A filter cannot invent row keys a reader can jump to, and it cannot keep GitHub and PDF in agreement if it emits definition lists.
- The linker already restructures headings, listen cards, and the bottom line. Table shape belongs in that same editorial pass.
- Even a wrapping `longtable` is still a cramped five-column object on a 4.25 in TUI page and still a poor audio script.

Fix Bob later if old reports with tables need a second chance. Teach the linker now so new canonical files never contain the construct.

## Recommended solution

Instruct the `#research_swarm` linker to **strip every markdown table and rewrite it as a labeled list**: parent bullet `**row key.**`, nested `**column:** value` bullets, all cell text preserved. Promote a row to `### Row key` only for a short set of named options. Leave numeric matrices in a fenced code block. Forbid HTML, definition-list colons, grid tables, alerts, fenced divs, and raw LaTeX as substitutes.

That conversion is native `itemize` in the Highlights PDF, native GFM on GitHub, readable in a narrated brief, and a single mechanical rule an editor agent can follow without researching or changing conclusions.

## Sources

Local, verified this turn:

- `sase-research-artifacts` linker segment in `src/sase_research_artifacts/xprompts/research_swarm.md` (inventory of tables, `--number-sections` / TOC rules, listen-card HTML, Highlights PDF as the published file)
- `sase-research-artifacts` `provider.py` (`research-highlights` hook, `bob highlights create --include-id`)
- `bob-cli` `src/native/highlights_ref/create.rs` (`render_temp_pdf`, `PANDOC_HEADER_INCLUDES`, listen-card Lua filter)
- `bob-cli` `docs/highlights-create.md` (XeLaTeX prerequisites, return-link eligibility including definition lists and table body cells)
- SASE `src/sase/attachments/markdown_pdf.py`, `_markdown_pdf_rendering.py`, `markdown_pdf.css` (4.25 in × 7 in wkhtmltopdf profile)
- Empirical renders of a fixture covering pipe tables, definition lists, HTML `<dl>`, labeled lists, per-row headings, ASCII fences, grid tables, and an overflow compact table: pandoc 3.1.11.1, XeLaTeX TeX Live 2025/dev/Debian, Bob's geometry/font flags; and the same fixture through SASE's wkhtmltopdf CSS

Web:

- [Pandoc User's Guide: creating a PDF, pipe tables, definition lists, raw HTML](https://pandoc.org/MANUAL.html)
- [jgm/pandoc#4239](https://github.com/jgm/pandoc/issues/4239) — long pipe-table text does not wrap in PDF
- [jgm/pandoc#7393](https://github.com/jgm/pandoc/issues/7393) — table cell overflow past page borders
- [GitHub Flavored Markdown spec](https://github.github.com/gfm/) — tables yes, definition lists no
- [rusterlium/rustler#689](https://github.com/rusterlium/rustler/pull/689) — GFM renders colon definition lists as mashed paragraphs
- Prior research `research:202610/research_swarm_listen_link/research_swarm_listen_link.md` — same Highlights pipeline; `::: listen` and GitHub alerts are literal in pandoc; raw HTML dropped in LaTeX
