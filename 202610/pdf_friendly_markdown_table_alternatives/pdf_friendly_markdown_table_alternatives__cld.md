# What the Research-Swarm Linker Should Use Instead of Markdown Tables

> **Question:** The `#research_swarm` linker agent should stop leaving Markdown tables
> in the final research report, because the report is converted into a PDF and tables
> render badly there. What should the linker convert tables into so the PDF looks good?

## Bottom line

**Convert every table into a "record list": one bullet per table row.** The bullet opens
with the row's identifying cell in bold. The other cells follow either on the same line
(two-column tables) or as nested bullets labelled in italics with their column header
(three or more columns). Rows that have an order become a numbered list, and rows whose
cells are all a few words long become a single line joined with ` · `. This format is
the "description list that uses bulleted run-in headings" that the Google developer
documentation style guide already describes. It is plain CommonMark, so it renders the
same on GitHub, in Obsidian, and through bob's pandoc→XeLaTeX PDF pipeline.

I rendered the same content in seven formats through a replica of the command that
`bob ref create` runs (see [how the PDF is produced](#how-the-pdf-is-produced)):

- **Record lists** were clean, compact, and easy to scan.
- **The original table** gave a two-character `#` column the same width as a prose
  column, so its four rows filled most of a page and split across a page break.
- **Definition lists and per-row headings** both rendered badly in this pipeline, and
  **HTML, grid, and code-block tables** each fail in their own way (see
  [rejected alternatives](#rejected-alternatives)).

The instruction also has to cover two pandoc details, or the lists will break
silently:

- **Put a blank line before every list.** bob uses pandoc's `markdown` reader, which
  treats a list with no blank line before it as part of the paragraph above. GitHub
  does not.
- **Indent nested bullets 3 spaces under `1.` items**, or the numbered list splits in
  two.

The linker can check its own output mechanically with
`pandoc <file> -f markdown -t json | grep -o '"t":"Table"' | wc -l`, which must print `0`.
Paste-ready instruction text is in [the recommended solution](#recommended-solution).

## How the PDF is produced

The chain, traced through the code:

- The linker publishes `<YYYYMM>/<name>/<name>.md`. The `research-highlights` file hook
  in `sase-research-artifacts` (`provider.py`) fires on that file. It skips every
  `__<suffix>.md` draft, including the lead's `__final.md`, so **only the linker's
  output is ever rendered**.
- The user's `sase.yml` (chezmoi) binds that hook to
  `bob ref create --include-id -P "$SASE_FILE_HOOK_PROJECT"`.
- `bob ref create` (bob-cli, `src/native/highlights_ref/create.rs`, `render_temp_pdf`)
  runs pandoc with: `--standalone --toc --toc-depth=3 --number-sections
  --pdf-engine=xelatex --highlight-style=tango`, two Lua filters (inline-code break
  points plus listen cards, and same-document return links), 0.85in margins, 10pt
  DejaVu Serif/Sans/Sans Mono, `linestretch=1.08`, and `fvextra` line-wrapping for code
  blocks.
- No `--from` is passed, so the input format is **pandoc's own `markdown` reader**, not
  `gfm`. That one detail explains most of the formatting rules below.
- On athena this is pandoc 3.1.11.1 with XeTeX from TeX Live 2025 (Debian). Pandoc
  writes every table as a `longtable` with `booktabs` rules.

## Why tables render badly

### The corpus is full of wide tables

I counted pipe tables (not their content) in the 213 published reports in the research
repo, meaning files of the form `<month>/<name>/<name>.md`, with drafts excluded:

- **208 of the 213 reports contain at least one table**: 1,204 tables in all, about 5.7
  per report.
- **Column counts:** 2 columns in 320 tables, 3 in 494, 4 in 252, 5 in 96, 6 in 21,
  and 7 or more in 21.
- **Body rows:** median 6, 90th percentile 12, maximum 30.
- **Cell content:** 3,793 rows have at least one cell over 80 characters, and 5,690 rows
  contain inline code.
- **Most common first-column headers:** `#` (103), Question (66), Phase (49), Option
  (35), an empty header (33), Claim (25), Fact (19), Risk (16), Key (16).

In other words, the swarm uses tables mostly as **records with prose cells**: a question
with its answer, a phase with its scope and exit criterion, a claim with its evidence.
It rarely uses them for numeric grids.

### Pandoc sizes those tables by dash count, and the agents write equal dashes

The pandoc manual's `pipe_tables` section says that when any source line is longer than
`--columns` (72 by default), "the table will take up the full text width and the cell
contents will wrap, with the relative cell widths determined by the number of dashes in
the line separating the table header from the table body."

- **1,108 of the 1,204 tables (92%) have a source line longer than 72 characters**, so
  all of them take this path.
- **1,107 (92%) use the same number of dashes for every column** (`| --- | --- | --- |`),
  so **every column gets the same width**, whatever it holds.

The manual also says pipe-table cells "cannot contain block elements like paragraphs and
lists". A multi-part answer therefore has to be packed into one wrapped cell.

### What that looks like on the page

I re-rendered `research:202610/update_skew_agent_auto_restart/update_skew_agent_auto_restart.md`
(17 tables, 22 pages) and inspected the table pages as images:

- **Wasted width.** In its requirement-changes table (`# | Your requirement | Adjusted
  requirement | Why`), the `#` column holds only `A1` to `A6` but takes a quarter of the
  text width. The two prose columns are each about 1.5 inches wide and wrap after three
  to five words.
- **Wasted height.** Four rows of that table took about 430 px of page height at 80 dpi
  and split across a page break. The same four rows as a record list took about 245 px
  (57%) and stayed on one page.
- **Rows blur together.** Booktabs draws no rules between rows, so short rows such as
  `A3` and `A4` read as one block.
- **Code and grouped rows suffer most.** In the signature-catalog table, code signatures
  break every two or three tokens inside narrow columns. Grouped rows (a blank first cell
  meaning "same group as above") leave a ragged empty column.

There is one honest exception. **Tables whose every source line fits in 72 characters
render well**: pandoc sizes those columns to their content and centres the table. Only
about 8% of the corpus is like that (96 tables), and the one-line record form below
renders them nearly as well, so a blanket "no tables" rule loses very little.

## The recommended format in detail

### Two-column tables: run-in bullets

Use this for a term with its explanation, a label with its value, or an alternative
with the reason it was rejected.

```markdown
- **In-process `importlib.reload`:** Old references and extension modules survive
  reload (cdx experiment).
- **Lock updates for an agent's lifetime:** Stalls updates for hours.
```

This is the Google style guide's "description list that uses bulleted run-in headings".
The guide's rules for that format: start the heading with a capital letter; end it with
a period or a colon, consistently within a list; and do not set off the description with
a dash.

### Three or more columns: records with labelled fields

```markdown
- **A1. Restart exactly once**
  - *Adjusted:* **at most one automatic restart per lineage,** claimed in a durable
    ledger before any mutation.
  - *Why:* true exactly-once is impossible across crashes without risking duplicates.
```

- The lead line is the cell a reader scans to find the row. Merge an ID column with its
  name column, as in `A1. Restart exactly once`.
- Each remaining non-empty cell becomes a nested bullet labelled with its column header,
  in the table's column order.
- **Labels go in italics, not bold.** With bold labels, a value that starts in bold
  (like "**Phase-aware.**") merges with its label into one bold run. This was visible in
  the render. Italic labels keep the two apart.

### Ordered rows: numbered records

Use this for phases, steps, ranks, and tiers. Keep the source's numbering and put any
nested bullets **3 spaces** in.

```markdown
1. **Phase 0: P0 refresh fix plus import-firewall test.** *Exit:* today's incident
   cannot recur for newly booted runners.
```

### Grouped rows: nest under the group

A row with a blank first cell continues the group above it. Make the group a bullet and
nest its rows beneath it. A small numeric column can become a parenthetical:

```markdown
- **Tier 1: Torn Python code**
  - `ModuleNotFoundError: No module named '<managed mod>'` (corpus 2): recover.
```

### Short-value matrices: one line per row

Use this when every cell is a few words, such as `Low`/`High` or `Yes`/`No`.

```markdown
- **Out-of-process healer:** effort high · risk medium · reversible · covers today
```

### Key-value tables

Use one bullet per field, with the key in bold, for example
``- **`sender`:** `agent.auto-restart` ``. Long code inside a cell goes in a fenced code
block inside the list item, indented to the item's content.

## Pandoc details the instruction must cover

I verified each of these with `pandoc -t native` on pandoc 3.1.11.1:

- **A blank line before every list.** `pandoc --list-extensions=markdown` shows
  `-lists_without_preceding_blankline`. The input `Intro sentence:` followed directly by
  `- item one` parses as a single paragraph containing literal hyphens, while `-f gfm`
  parses it as a list. A linker that writes "Two alternatives were rejected:" with the
  list on the next line would get a correct GitHub view and a broken PDF.
- **Nested indentation.** Under `1.` items, nested bullets indented 2 spaces split the
  ordered list into two lists, in both pandoc `markdown` and `gfm`. With 3 spaces it
  stays one list. Under `- ` items, 2 spaces nest correctly.
- **No headings per row.** Because of `--number-sections`, a `####` heading renders as a
  run-in "1.1.0.1"-style heading glued to the following text. With `--toc-depth=3`, a
  `###` per row would flood the table of contents.
- **No definition lists.** `+definition_lists` is on in pandoc, but the LaTeX output
  runs the bold term straight into the definition. In the test, "Restart exactly once"
  ran into "Adjusted: At most one…" as one bold run. GitHub and other GFM renderers do
  not support the syntax and show it as plain paragraphs.
- **Keep links working.** bob's return-links filter tags and pairs same-document links in
  list items, just as it does in table body cells, so in-document links keep their return
  pills.

## Rejected alternatives

- **Bold-lead paragraphs** (one paragraph per row, with the fields inline). These
  rendered cleanly and work for two-column rows with long explanations. Multi-field rows
  become dense blocks that are harder to scan than nested fields. They are acceptable,
  but using one list family keeps the linker's output consistent.
- **Definition lists:** they render badly in the PDF and not at all on GitHub (see
  [pandoc details](#pandoc-details-the-instruction-must-cover)).
- **A heading per row:** it produces numbered run-in headings and clutters the table of
  contents.
- **Grid, simple, or multiline tables:** these are still tables and still `longtable`
  output. Their widths come from the source column widths, and GitHub does not render
  grid tables at all.
- **HTML `<table>`:** pandoc's `markdown` reader keeps the tags as raw HTML, which the
  LaTeX writer drops. The cell text survives as a run-on paragraph ("Cell A Cell B"), so
  all structure disappears from the PDF.
- **An ASCII table in a code block:** at 10pt DejaVu Sans Mono with 0.85in margins, wide
  rows hit the `fvextra` `breaklines,breakanywhere` wrapping and break mid-row.
- **Tables as images:** the text cannot be searched, highlighted, or annotated in
  Highlights; it cannot be diffed or link-checked; and it adds an image-generation step.
- **Styled cards** (fenced divs such as `::: {.card}` plus a LaTeX box). These need new
  converter code, and GitHub shows `:::` literally. The listen card's `<div class="listen">`
  is the precedent if a styled variant is ever wanted, but it is not needed here.
- **Keeping tables and fixing the converter.** This is the main alternative to banning
  tables, and it works partly. A prototype Lua filter that set column widths in
  proportion to content length (`min(max_chars, 70)^0.8`) and set tables in `\small`
  fixed the wasted `#` column and roughly halved the table's height. Rows still blurred
  together and the type was smaller, and it does nothing for 6- and 7-column tables. It
  is a reasonable **safety net** in bob-cli for tables that slip through, but it is not
  as readable as record lists.

## Why the linker should convert, not a filter

I also prototyped a fully automatic Lua filter that turns every pandoc `Table` into a
record list: lead from the first column, nested `*Header:*` fields, and blank-first-cell
rows nested under the row above.

- **It works.** The 22-page sample shrank to 20 pages with no tables left.
- **It is clearly worse than hand conversion.**
  - The lead line was a bare "A1", because the filter cannot know that the ID and
    requirement columns belong together.
  - Every record repeated "*Your requirement:*" and "*Adjusted requirement:*".
  - The signature catalog flattened into long runs of repeated
    Signature/Corpus/v1-action triplets.

The linker can make the judgment calls a filter cannot: which cell is the lead, when a
count reads better as a parenthetical, and how to nest a group. The hand-converted
version of the same signature catalog read much better. A filter belongs only behind the
instruction, as an optional bob-cli safety net. That would be a bob-cli change, which I
have not filed. It is a follow-up for the user to decide on.

## Recommended solution

Add a **"No tables"** bullet to step 3 of the linker segment in
`sase-research-artifacts/src/sase_research_artifacts/xprompts/research_swarm.md`, next
to the existing "Never number headings" bullet, and add a check to step 6.

Suggested step 3 bullet:

```markdown
   - **No Markdown tables.** The PDF renderer (pandoc → XeLaTeX) gives every column of
     a wide table the same width, so tables print cramped and split across pages.
     Convert every table in the lead's report (pipe, grid, simple, multiline, or HTML)
     into a list, one row per item, keeping every cell's content:
     - Two columns: `- **<first cell>:** <second cell>`.
     - Three or more columns: a bullet whose first line is the row's identifying
       cell(s) in bold (merge an ID column with its name, e.g.
       `- **A1. Restart exactly once**`), then one nested bullet per remaining
       non-empty cell, `- *<Column header>:* <cell>`, in column order.
     - Ordered rows (phases, steps, ranks, tiers): the same shapes as a numbered list,
       keeping the original numbers.
     - Grouped rows (a blank first cell continues the group above): nest them under one
       bullet for the group.
     - Short-value rows (every cell a few words, like `Low` or `Yes`): one line,
       `- **<row>:** <header> <value> · <header> <value> · …`.
     - Long code in a cell: a fenced code block inside the list item.
     Put a blank line before every list (pandoc otherwise merges it into the paragraph
     above). Indent nested bullets 2 spaces under `- ` and 3 spaces under `1. `. Put
     field labels in italics so bold inside a value still shows. Do not use a heading
     per row, a definition list (`Term` then `: definition`), an HTML table, or a table
     inside a code block. You may add a one-line lead-in that says what the list holds.
     Never drop a cell, merge two rows, or add totals, rankings, or conclusions the
     table did not state.
```

Suggested additions to step 6:

```markdown
   Confirm no table survives: `pandoc <file> -f markdown -t json | grep -o '"t":"Table"' | wc -l`
   prints `0`, and `grep -n '<table' <file>` prints nothing. Confirm every table cell
   from the lead's report appears in the new file.
```

In step 2, change "table" to "table (each one is converted in step 3)", so that the
inventory keeps tracking the content of every cell.

This keeps the linker's editor-only contract: the conversion changes layout, not meaning.
The lead's `__final.md` and the researcher drafts can keep their tables, because neither
is rendered to PDF.

## Method and sources

- **Pipeline:** the code and configuration that define the PDF render:
  - bob-cli `src/native/highlights_ref/create.rs` (`render_temp_pdf`,
    `PANDOC_HEADER_INCLUDES`, `PANDOC_CODE_BREAK_FILTER`)
  - bob-cli `render_tex.rs`, `return_links.lua`, `return_links.tex`, and
    `docs/highlights-create.md`
  - sase-research-artifacts `provider.py` and `xprompts/research_swarm.md`
  - chezmoi `home/dot_config/sase/sase.yml`
- **Experiments:** I extracted bob's filters and header verbatim and replayed its pandoc
  arguments on athena. I rendered seven variants of the same content (the original
  tables, bold-label records, bold-lead paragraphs, definition lists, per-row headings,
  italic-label records, and a content-width table fix) plus the full sample report, two
  ways. I rasterised the pages with `pdftoppm` and inspected them. These were scratch
  files and were not kept.
- **Corpus statistics:** aggregate counts over the published reports in the research repo,
  computed by script without reading individual reports. The one report used as a render
  sample was read with `sase artifact read`.
- **External sources:**
  - [Pandoc User's Guide: Tables, `pipe_tables`, `definition_lists`, `--columns`](https://pandoc.org/MANUAL.html)
  - [Google developer documentation style guide: Tables](https://developers.google.com/style/tables)
    ("Use tables only to present two-dimensional data"; the list-or-table rule that
    gives pairs of data to description lists)
  - [Google developer documentation style guide: Lists](https://developers.google.com/style/lists)
    (description lists with bulleted run-in headings)
  - [Some Markdown parsers support definition lists (TIL)](https://til.codeinthehole.com/posts/some-markdown-parsers-support-definition-lists/)
    (GFM does not support definition lists)
