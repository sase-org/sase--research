# What the Research-Swarm Linker Should Use Instead of Markdown Tables

Consolidated report, 14 October 2026. It merges four independent researcher reports
(cdx, cld, grk, gem) with the lead's own verification renders through the real PDF
pipeline.

## Bottom line

**Tell the linker to convert every table into a "record list": one bullet per table
row, in plain CommonMark.** The shapes are:

- **Two-column tables** become run-in bullets: `- **Term:** explanation`.
- **Tables with three or more columns** become a bullet per row with the row's
  identifying cell in bold. Each remaining cell becomes a nested bullet labelled with
  its column header in *italics*: `- *Main risk:* …`.
- **Ordered rows** (phases, steps, ranks) use the same shapes as a numbered list.
- **Rows of short values** collapse to one line: `- **Healer:** effort high · risk
  medium · reversible`.
- **A handful of major named options** that the report discusses at length may instead
  become one `###` section per option, using the same labelled bullets. A row never
  becomes a `####` heading.

The rule needs three pandoc details, or the lists break silently in the PDF:

- Put a **blank line before every list**.
- Indent nested bullets **3 spaces under `1.`** items.
- Write URLs as **`[text](url)` or `<url>`, never bare**.

The linker can check its output mechanically: pandoc's AST must contain no `Table`
node and no raw HTML `<table>` block.

All four researchers, and the lead's own renders, agree on two points:

- A single-column, list-based form is the right replacement.
- Every other candidate is worse in this pipeline: definition lists, HTML, grid tables,
  code-block ASCII tables, callouts, and images.

The researchers disagreed on two details: whether rows should become headings or
nested bullets, and whether field labels should be bold or italic. Both were settled
by rendering through the real pipeline (see
[resolving the disagreements](#resolving-the-disagreements)). The paste-ready prompt
text is in [the recommended solution](#recommended-solution).

## How the PDF is produced

The published research PDF comes from Bob, not from SASE's attachment converter. The
chain, verified in code by cld, grk, and the lead:

- The linker publishes `<YYYYMM>/<name>/<name>.md`. The `research-highlights` file hook
  (`sase-research-artifacts` `src/sase_research_artifacts/provider.py`) fires on `ADD`
  and excludes `__<suffix>.md` files, so researcher drafts and the lead's `__final.md`
  are never rendered. **Only the published file reaches the PDF.**
- The hook's command is user-configured. In Bryan's chezmoi `sase.yml` it is
  `bob ref create --include-id -P …` (cld).
- `bob ref create` (`bob-cli` `src/native/highlights_ref/create.rs`, `render_temp_pdf`)
  runs pandoc with these settings:
  - `--standalone --toc --toc-depth=3 --number-sections --pdf-engine=xelatex`;
  - 0.85 in margins on US Letter, which leaves about 6.8 in of text width;
  - 10 pt DejaVu Serif, Sans, and Sans Mono, with `linestretch=1.08`;
  - two Lua filters: one adds break points in inline code and draws the listen card,
    and the other adds same-document return-link pills;
  - `fvextra` line wrapping for fenced code blocks.
- No `--from` is passed, so the input goes through **pandoc's own `markdown` reader,
  not GFM**. That one detail explains the list rules below.
- On athena this is pandoc 3.1.11.1 with XeTeX from TeX Live 2025. Pandoc writes every
  table as a LaTeX `longtable` with `booktabs` rules.

A second, narrower converter exists: SASE's agent-attachment renderer
(`src/sase/attachments/markdown_pdf.py`, `markdown_pdf.css`). It uses a 4.25 × 7 in
page with 0.22 in margins (about 3.8 in of text width) and tries wkhtmltopdf first,
then XeLaTeX, then pdfLaTeX. cdx's experiments used this path, so its "narrow page"
framing does not describe the Highlights PDF. Its conclusion still holds, and the same
list format renders well on both paths: cdx's probe on one, the lead's and cld's on
the other.

**One scope gap.** The linker only runs when `linker`, `image`, or `audio` is true
(`linker` defaults to `false`). Without a linker, the lead publishes `<name>.md`
directly and its tables reach the PDF. If table-free PDFs should hold for every swarm,
the lead's segment needs the same rule when `run_linker` is false.

## Why tables render badly

### The corpus uses tables as records with prose cells

The lead recounted cld's corpus statistics over the published reports
(`<month>/<name>/<name>.md`, drafts excluded) and got nearly the same figures:

- **208 of 213 published reports contain at least one table.** There are about 1,200
  tables in all: cld counted 1,204 and the lead 1,201.
- **Column counts:** 2 columns in 319 tables, 3 in 493, 4 in 252, 5 in 95, and 6 or
  more in 42.
- **Rows and cells (cld):** the median table has 6 body rows and the 90th percentile
  has 12. 3,793 rows have a cell longer than 80 characters.
- **Most common first-column headers (cld):** `#`, Question, Phase, Option, an empty
  header, Claim, and Fact.

The swarm rarely writes numeric grids. It writes records: a question and its answer, a
phase and its exit criterion, an option and its risk.

### Pandoc gives every column the same width

The pandoc manual (`pipe_tables`) says that when any source line is longer than
`--columns` (72 by default), the table takes the full text width and its cells wrap.
The "relative cell widths [are] determined by the number of dashes in the line
separating the table header from the table body."

- **1,106 of the 1,201 tables have a source line over 72 characters**, so they take
  this path.
- **Nearly all of them use equal dashes** (`| --- | --- |`), so every column gets the
  same width. cld counted 92% of tables; the lead's stricter check found 1,007 of
  1,201.

A two-character `#` column therefore takes as much space as a prose column. At four
columns, each gets about 1.6 in on Letter, and cells wrap after three to five words.

### Other failures

- **Cells cannot hold block content.** Pipe-table cells "cannot contain block elements
  like paragraphs and lists" (pandoc manual). Multi-part answers are packed into one
  wrapped cell.
- **Pagination.** `longtable` breaks only between rows. A tall row jumps to the next
  page, and a table can separate from its lead-in sentence. In the lead's render, the
  sentence introducing a short table was stranded at the bottom of one page and the
  table started the next.
- **Rows blur together.** `booktabs` draws no rules between body rows (cld; visible in
  the lead's render).
- **Unbreakable tokens.** A bare URL in a cell runs off the right margin. grk and the
  lead reproduced this. Inline code wraps, because Bob's code-break filter inserts break
  points.
- **Downstream readers.** grk and gem note that row-major cells read poorly as narrated
  audio, and that narrow columns make highlighting clumsy. These are plausible but were
  not tested.

There is one honest exception: **a table whose every source line fits in 72 characters
renders acceptably.** Pandoc then sizes its columns to their content. Only about 8% of
the corpus looks like that (cld), and the one-line record form renders those rows
nearly as well, so a blanket "no tables" rule loses very little.

## The recommended format in detail

### Two-column tables become run-in bullets

Use this shape for a term and its explanation, a key and its value, or an alternative
and why it was rejected:

```markdown
- **In-process `importlib.reload`:** Old references and extension modules survive
  reload (cdx experiment).
- **Lock updates for an agent's lifetime:** Stalls updates for hours.
```

The Google developer documentation style guide calls this a "description list that
uses bulleted run-in headings". It also recommends tables "only to present
two-dimensional data", and lists for pairs.

### Three or more columns become records with labelled fields

```markdown
- **Out-of-process healer**
  - *How it works:* A separate supervisor notices the version skew and restarts the
    agent once.
  - *Main risk:* Restarting mid-turn can duplicate side effects.
  - *Verdict:* **Recommended.** At most one automatic restart per lineage.
```

- **The lead line** holds the cell a reader scans to find the row. Merge an ID column
  into it, as in `**A1. Restart exactly once**`. A one-line summary or verdict may
  follow the bold key.
- **Each remaining non-empty cell** becomes a nested bullet labelled with its column
  header, in the table's column order. Drop empty cells rather than writing blank
  fields.
- **Field labels go in italics.** The bold row key and the italic field labels form a
  visible two-level hierarchy. Italics also stop a label from merging with a value that
  starts in bold (see [label style](#label-style)).

### Ordered rows become numbered records

Use this for phases, steps, ranks, and tiers. Keep the source's numbering, and indent
nested bullets **3 spaces**:

```markdown
1. **Phase 0: refresh fix plus import-firewall test**
   - *Exit:* today's incident cannot recur for newly booted runners.
2. **Phase 1: durable restart ledger**
   - *Exit:* at most one automatic restart per lineage.
```

### Short values and numbers

When every cell is a few words, such as `Low`/`High` or `Yes`/`No`, use one line per
row:

```markdown
- **Out-of-process healer:** effort high · risk medium · reversible · covers today
```

For measurements, follow gem and cdx:

- State the metric, current value, baseline, and delta explicitly, as in
  `- **Tracked files:** 12,994 (from 5,728 in July; 2.3× growth).`
- Keep units, periods, denominators, and conditions.
- Keep the distinction between zero, unknown, and not applicable.

### Grouped rows nest under the group

A row with a blank first cell continues the group above it. Make the group a bullet
and nest its rows beneath it. A small numeric column can become a parenthetical
(cld):

```markdown
- **Tier 1: Torn Python code**
  - `ModuleNotFoundError: No module named '<managed mod>'` (corpus 2): recover.
```

### Decision matrices can be grouped by criterion

When the reader's question is "how do all candidates compare on X?", grouping by
candidate forces backtracking. Group by criterion instead (cdx, gem):

```markdown
- **Portability**
  - *Record lists:* render in pandoc `markdown`, GFM, and Obsidian.
  - *Definition lists:* need a pandoc extension; GitHub shows plain paragraphs.
```

Choose one orientation, based on the decision the report supports. Never reproduce
the matrix in both orientations.

### Long code in a cell

Put long code in a fenced code block inside the list item, indented to the item's
content. Bob's `fvextra` setup wraps fenced code.

### When a row may become a heading

Use one `###` section per row only when both conditions hold:

- the rows are a small set (about six or fewer) of major named options; and
- the report discusses each option enough that a reader will jump to it.

The section then holds the same italic-labelled bullets. Each heading becomes a
numbered TOC entry and a link target (the lead's render, grk), so it must follow the
linker's existing heading rules: start with a letter, be unique, and contain no code
or punctuation.

## Resolving the disagreements

### Heading per row or nested list

cdx and gem proposed one heading per row as the default ("Fielded Data Cards"). cld
and grk proposed a nested list, with grk allowing headings for short option sets. **The
nested list is the default.** The evidence:

- **Rows flood the table of contents.** Bob renders with `--toc --toc-depth=3`, and the
  report's `#` title becomes section 1, so `###` headings are TOC entries. In the
  lead's render, three `###` rows produced TOC entries 1.2.1 to 1.2.3. With a median of
  6 rows and a 90th percentile of 12 (cld), headings per row would flood the TOC. grk
  adds that they could also flood the narrated chapters, if audio chapters follow
  headings.
- **`####` headings are worse.** Pandoc's LaTeX template renders level-4 headings as
  `\paragraph`. In the lead's render, a `####` heading followed by a paragraph ran into
  that paragraph ("1.2.1.1 Run-in check A paragraph…"). Directly under a `##` section,
  it was numbered "1.2.0.1". When a list followed, it stood alone. cld reported the
  run-in case; both observations hold.
- **cdx's evidence favouring headings came from the 3.8 in attachment page.** That is
  not the Highlights pipeline. cdx itself rated bold-lead records as also readable.

Headings still look good for a few major options. That is why the recommendation
keeps them as a narrow exception.

### Label style

cdx, grk, and gem used bold labels (`- **Verdict:** …`). cld used italic labels.
**Italics win.** In the lead's render, `- **Verdict:** **Rejected.** Unsafe…` printed
"Verdict: Rejected." as one indistinguishable bold run. The italic version printed
"*Verdict:* **Rejected.**" clearly. This case is common: in 2,493 of the corpus's 9,651
table rows (header rows included, so about a quarter), a cell after the first one
starts in bold. Bold stays on the row key and on two-column run-in labels,
where the label is the row key.

### A code-block grid for numeric matrices

grk allowed a short monospaced grid in a fenced code block as a last resort for true
numeric matrices. cdx, cld, and gem rejected code-block tables. **Rejected here.** A
grid in a code block is still a table:

- Wide rows hit `fvextra`'s `breakanywhere` wrapping and break mid-row (cld, gem).
- Links inside it do not work.
- It reads as code.

The corpus has almost no numeric matrices. The one-line `·` form or metric bullets
cover them without an exception the linker has to judge.

### Definition lists

All four reports rejected definition lists as the universal format, for different
reasons. The lead's render confirms cld's observation: in the XeLaTeX `description`
environment, the bold term runs straight into the definition on the same line. They
also fail outside pandoc:

- cdx parsed a sample with pandoc's `commonmark` and `gfm` readers. Only `markdown`
  produced a `DefinitionList`.
- GitHub shows colon syntax as plain paragraphs (GFM spec; rustler PR #689).
- gem reports that Obsidian does not render them either.

The research repo is public on GitHub, so a PDF-only format is a poor default.

### Fixing the converter instead of banning tables

cld prototyped two Bob-side alternatives:

- **A content-proportional column-width filter.** It removed the wasted `#` column and
  roughly halved table height, but rows still blurred together and 6- and 7-column
  tables stayed cramped.
- **A fully automatic table-to-list filter.** It worked: the 22-page sample shrank to
  20 pages with no tables. But it produced worse output than hand conversion. The
  filter cannot tell which cells form the row key, repeats long header labels
  mechanically, and flattens grouped rows.

grk adds that a filter cannot keep GitHub and the PDF in agreement. **The linker
should convert.** A Bob filter is a reasonable later safety net for tables that slip
through and for old reports. That would be a `bob-cli` change, and no one has filed
it.

## Pandoc details the instruction must cover

The lead verified each of these on pandoc 3.1.11.1 with Bob's exact flags and filters:

- **A blank line before every list.** Pandoc's `markdown` reader does not let a list
  interrupt a paragraph. In the lead's render, `The next list has no blank line before
  it:` followed by two bullets printed as one paragraph: "…before it: - item one - item
  two". GitHub renders the same source as a list, so the error is invisible until the
  PDF.
- **Nested indentation.** Under `1.` items, nested bullets indented 2 spaces fell out
  of the item. They became top-level bullets between two separate numbered lists.
  Indented 3 spaces, the list stayed intact. Under `- ` items, 2 spaces nest correctly
  (cld).
- **URLs in link syntax.** A bare `https://…` is plain text to pandoc's `markdown`
  reader, which has no `autolink_bare_uris`. A long bare URL ran off the right margin
  both in a table cell and in a list item. `<https://…>` became a breakable `\url`
  and wrapped. `[text](https://…)` printed only its link text. GitHub renders all three
  forms as links. Long bare URLs are rare in the corpus (19 lines, all in one report),
  so this rule costs little.
- **Return links still work.** Bob's return-links filter tags same-document links in
  list items, just as it does in table cells (cld, grk; `docs/highlights-create.md`).

## Rejected alternatives

Each of these was evaluated by at least two researchers. The lead re-rendered the ones
marked "verified".

- **Bold-lead paragraphs** (one paragraph per row with inline italic labels). They
  render cleanly but form dense blocks that are harder to scan than nested fields
  (cdx, cld; verified). They are acceptable for two-field rows with long prose, but one
  list family keeps output consistent.
- **Definition lists:** the term runs into the definition in the PDF, and the syntax
  is not supported on GitHub (verified).
- **Grid, simple, multiline, or "wider" pipe tables:** these are still `longtable`, and
  GitHub does not render grid tables.
- **HTML `<table>` or `<dl>`:** pandoc's `markdown` reader keeps the tags as raw HTML,
  and the LaTeX writer drops them. The cells print as loose, run-on lines (cdx, cld,
  grk, gem). They also evade a check that looks only for `Table` nodes, because
  pandoc parses them as `RawBlock` (verified). The step-6 check therefore matches raw
  HTML `<table>` blocks too. A plain `grep '<table'` would be wrong: it also matches
  reports that mention HTML tables in inline code, such as this one.
- **ASCII or Unicode tables in a code block:** see
  [the numeric-matrix discussion](#a-code-block-grid-for-numeric-matrices).
- **GitHub alerts (`> [!NOTE]`), fenced `:::` divs, styled cards:** they print as
  literal syntax in pandoc 3.1 and on GitHub without new filter code. Blockquotes also
  narrow the measure. The listen card's `<div class="listen">` is the only
  special-cased HTML, and it needed a dedicated filter.
- **Raw LaTeX `tabular`:** invisible on GitHub, and it bypasses Bob's filters.
- **Tables as images:** the text cannot be searched, highlighted, diffed, or
  link-checked, and the narrow-column problem remains.

## What the conversion must preserve

The linker is an editor. Changing layout must not change meaning (cdx, cld, grk):

- Keep every non-empty cell's text, with its links, code spans, and emphasis.
- Turn the header row into the field labels, and the naming column into the row key.
- Give every value enough context to stand alone. For a cell under "2025" and
  "Revenue", a bare "12" is not enough; carry the period, measure, and unit.
- Turn a caption into a one-line lead-in sentence above the list. Carry footnotes,
  sources, merged-header context, and conflicting evidence.
- Never drop a cell, merge two rows, fill in missing cells, or add totals, rankings, or
  conclusions the table did not state.

A tidy linear document is not automatically an accessible tagged PDF. Nobody audited
PDF tagging (cdx).

## Recommended solution

Edit the linker segment of
`sase-research-artifacts/src/sase_research_artifacts/xprompts/research_swarm.md` in
three places. This follows cld's placement, with grk's and gem's shapes and the lead's
render findings folded in.

**Step 3 (Restructure):** add this bullet next to the existing "Never number headings"
bullet:

```markdown
   - **No tables.** The PDF renderer (pandoc → XeLaTeX) prints tables with
     equal-width columns, cramped wrapped cells, and rows that jump pages. Convert
     every table in the lead's report (pipe, grid, simple, multiline, or HTML) into
     a list with one item per row, keeping every cell's content:
     - Two columns: `- **<first cell>:** <second cell>`.
     - Three or more columns: a bullet whose first line is the row's identifying
       cell in bold (merge an ID column into it, e.g.
       `- **A1. Restart exactly once**`), then one nested bullet per remaining
       non-empty cell, `- *<Column header>:* <cell>`, in column order. Labels go in
       italics so bold inside a value stays distinct.
     - Ordered rows (phases, steps, ranks, tiers): the same shapes as a numbered
       list, keeping the original numbers.
     - Grouped rows (a blank first cell continues the group above): nest them under
       one bullet for the group.
     - Rows whose cells are all a few words: one line,
       `- **<row>:** <header> <value> · <header> <value> · …`.
     - Numbers: keep units, periods, denominators, and the difference between zero,
       unknown, and not applicable.
     - Long code in a cell: a fenced code block inside the list item.
     - Only when the rows are about six or fewer major named options the report
       discusses at length: one `###` section per option holding the same
       italic-labelled bullets. Never turn a row into a `####` heading.
     Turn a table caption into a one-line lead-in sentence. Put a blank line before
     every list (pandoc otherwise merges it into the paragraph above). Indent nested
     bullets 2 spaces under `- ` and 3 spaces under `1. `. Write URLs as
     `[text](url)` or `<url>`, never bare. Do not substitute a definition list
     (`Term` then `: definition`), an HTML table, a grid or simple table, a table in
     a code block, a callout or `:::` div, raw LaTeX, or an image. Never drop a
     cell, merge two rows, or add totals, rankings, or conclusions the table did
     not state.
```

**Step 6 (Re-check):** add:

```markdown
   Confirm no table survives:
   `pandoc <file> -f markdown -t json | grep -o -i -E '"t":"Table"|"t":"RawBlock","c":\["html","<table' | wc -l`
   prints `0`. Confirm every cell of every table in the lead's report appears in
   the new file.
```

**Step 2 (Inventory):** change "table" to "table (record its cells; step 3 converts
each one into a list)", so the inventory tracks cell content rather than table
objects.

Three follow-ups, all optional:

- **No-linker swarms.** Add the same rule to the lead segment when `run_linker` is
  false, because the lead then publishes the rendered `<name>.md`.
- **Prompt tests.** Extend the prompt-loading test (`tests/test_macro_loading.py`) to
  assert that the linker segment contains the new rule. Then expand a
  `#research_swarm(linker=true)` and render one real report through
  `bob ref create` before relying on the new rule.
- **Bob safety net.** A `bob-cli` Lua filter (content-proportional table widths, or
  table-to-list) could catch tables in old reports and in anything that slips through.
  It is a separate decision, and nothing has been filed for it.

The lead's `__final.md` and the researcher drafts can keep their tables, because the
hook never renders them.

## Method and sources

### Code and configuration inspected

- `sase-research-artifacts`:
  - `xprompts/research_swarm.md`: the linker steps, the `run_linker` condition, and
    input defaults;
  - `provider.py`: the hook's include and exclude globs.
- `bob-cli` `src/native/highlights_ref/create.rs`: `render_temp_pdf`,
  `PANDOC_HEADER_INCLUDES`, and `PANDOC_CODE_BREAK_FILTER`. Also `return_links.lua`
  and `return_links.tex`, inspected by the lead and by cld and grk.
- SASE `src/sase/attachments/markdown_pdf.py`, `_markdown_pdf_rendering.py`, and
  `markdown_pdf.css` (cdx, grk, gem).
- chezmoi `home/dot_config/sase/sase.yml` for the hook binding (cld).

### Lead renders

The lead extracted Bob's header includes and both Lua filters verbatim and replayed
its exact pandoc arguments on athena (pandoc 3.1.11.1, XeLaTeX). The same content was
rendered as:

- a four-column pipe table;
- bold-label records and italic-label records;
- `###` and `####` row headings;
- bold-lead paragraphs;
- run-in, one-line, and numbered records (2- and 3-space indents);
- a list with no preceding blank line;
- a compact two-column table;
- bare, angle-bracket, and Markdown links;
- a definition list;
- an HTML table, checked through `-t native`.

Pages were rasterised with `pdftoppm` and inspected. These were scratch files and
were not kept.

### Researcher experiments

- **cdx:** probes on SASE's attachment converter (wkhtmltopdf and XeLaTeX), plus
  reader-portability parses.
- **cld:** a seven-format render of a real 17-table report through a Bob replica, a
  column-width filter prototype, and an automatic table-to-list filter prototype.
- **grk:** overflow and clipping renders on both converters.
- **gem:** pipeline analysis and conversion archetypes. Its claims about annotation
  and TTS were not tested.

### Corpus statistics

Aggregate counts of pipe tables across the published reports (cld, recounted by the
lead), computed by script without reading individual reports.

### External sources

- [Pandoc User's Guide: tables, `pipe_tables`, definition lists, raw HTML, creating a PDF](https://pandoc.org/MANUAL.html)
- [Pandoc Lua filters](https://pandoc.org/lua-filters.html)
- [jgm/pandoc#4239: long pipe-table text does not wrap in PDF](https://github.com/jgm/pandoc/issues/4239)
- [jgm/pandoc#7393: table cell overflow past page borders](https://github.com/jgm/pandoc/issues/7393)
- [GitHub Flavored Markdown spec](https://github.github.com/gfm/)
- [CommonMark spec 0.31.2](https://spec.commonmark.org/0.31.2/)
- [rusterlium/rustler#689: GFM renders colon definition lists as paragraphs](https://github.com/rusterlium/rustler/pull/689)
- [Google developer documentation style guide: Tables](https://developers.google.com/style/tables)
- [Google developer documentation style guide: Lists](https://developers.google.com/style/lists)
- [W3C WAI tables tutorial](https://www.w3.org/WAI/tutorials/tables/)
- [wkhtmltopdf project status](https://wkhtmltopdf.org/status.html)
- Prior research
  `research:202610/research_swarm_listen_link/research_swarm_listen_link.md`, which
  covers the same Highlights pipeline and found that `::: listen` and GitHub alerts
  print literally in pandoc (cited by grk).
