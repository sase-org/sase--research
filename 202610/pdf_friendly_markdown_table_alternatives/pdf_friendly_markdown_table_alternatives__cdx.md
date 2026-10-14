# PDF-friendly replacements for Markdown tables in research reports

Independent research by **cdx**, 14 October 2026. Scope: recommend an output convention for the `#research_swarm` linker; no macro or converter changes were made. No reports or findings from the other researchers in this swarm were consulted.

**Recommendation:** use ordinary Markdown in one column: a short heading for each compared subject, followed by bullets with bold field labels in a consistent order. For simple two-column mappings, use compact `- **Label:** explanation` lists. This preserves the useful structure of a table while allowing text to use the page width. Treat this as a writing convention, rather than requiring a special rendering extension.

## What the existing PDF pipeline changes about the decision

I inspected the SASE implementation rather than assuming an A4 document or a particular Markdown engine. The relevant local sources are `src/sase/attachments/_markdown_pdf_rendering.py`, `src/sase/attachments/markdown_pdf.py`, `src/sase/attachments/markdown_pdf.css`, and the “Markdown PDF Attachment Contract” in `docs/agent_images.md`.

The built-in profile is **4.25 × 7 inches**, with **0.22-inch margins**. That leaves about **3.81 inches of text width** before element padding. The HTML route uses 16-pixel body text and 1.32 line height; the LaTeX routes request 12-point text and the same line-stretch value. The engine preference is **wkhtmltopdf, XeLaTeX, then pdfLaTeX**. The stylesheet already styles headings, lists, bold text, and wrapping links. Its table rule sets full width and fixed layout.

A four-column comparison therefore divides a very small width between four cells. Longer explanations become stacks of short lines. Replacing those cells with full-width labeled text addresses the layout constraint directly. That is a design inference from the inspected dimensions and the rendering probe below, not a claim that every Markdown table necessarily fails.

Engine fallback also matters. Pandoc can generate PDFs through HTML or LaTeX intermediates; CSS controls the HTML path, while LaTeX variables and templates control the other path. A structure that looks good only because of HTML styling is a weaker default here. [Pandoc PDF documentation](https://pandoc.org/MANUAL.html#creating-a-pdf).

These implementation findings apply to SASE's built-in attachment converter. If your final research file is also exported through a separate tool, that tool still needs a preview check; I did not assume its settings match SASE's.

## Evidence from a small rendering probe

I authored one synthetic comparison with three subjects and three descriptive fields per subject. I rendered the same field content four ways: a four-column pipe table, headings with field bullets, bold subject paragraphs with field bullets, and Pandoc definition lists with the fields combined into each definition.

The probe used the actual command-building helper from the inspected checkout and its default stylesheet and mobile page profile. Tools installed here were **Pandoc 3.1.11.1** and **wkhtmltopdf 0.12.6 with patched Qt**. I also rendered all four samples through the installed XeLaTeX fallback. I disabled the automatically generated title block for the probe and used no frontmatter, keeping those decorations out of the comparison.

**Results:**

- **All eight conversions succeeded.** Each HTML-engine sample occupied one page; each XeLaTeX sample occupied two. This probe does not establish a page-count advantage for any candidate.
- **Headings with field bullets produced the clearest grouping in my visual inspection.** Labels were easy to locate, explanations had useful line lengths, and the section hierarchy separated the subjects.
- **Bold subject paragraphs with field bullets were also readable.** They offer a more compact visual hierarchy for short records, but they do not create actual heading nodes in the document outline.
- **The table rendered, but its narrow cells made reading noticeably harder.** In the HTML output, “measurements” even broke with its final letter on a separate line. Successful conversion is therefore an insufficient acceptance criterion for this problem.
- **Definition lists preserved term-and-explanation grouping, but the combined fields became dense paragraphs.** In the XeLaTeX sample, the second page contained only the final word, “workflow.” This is a result of this sample and template, not an inherent defect in definition lists.
- **A basic geometric check found no extracted word boxes outside the physical page bounds.** I checked `pdftotext -bbox` output. This is a useful sanity check, not proof against overlap, awkward breaks, or other visual defects.

I also parsed a separate two-term definition-list sample with Pandoc's `markdown`, `commonmark`, and `gfm` readers. Only `markdown` produced a `DefinitionList` node; the other two produced ordinary paragraphs. This directly demonstrates why colon-style definition lists are less portable as a universal linker convention.

The aesthetic judgment is mine, based on a small synthetic sample. It is not a user study, and I did not exhaustively test every engine, font, page size, or long-report scenario.

## Alternatives and when they make sense

### Headings followed by labeled bullets: best default for comparisons

Each subject gets an appropriately nested heading. Its attributes become bullets whose bold labels repeat in the same order for every subject. This provides both a readable vertical structure and enough consistency to compare items mentally.

Use it for approaches, products, architectural options, evidence summaries, tradeoffs, and recommendations that have several explanatory fields. Keep the heading short and each field focused. If a field requires substantial explanation, use a short paragraph or a small sublist rather than squeezing it into one enormous bullet.

The tradeoff is length: repeated labels may increase the report's word count and the reader loses immediate horizontal cell alignment. A short comparison summary, or a criterion-oriented section, can recover that overview. This recommendation is my synthesis of the pipeline constraints and probe results.

### Compact labeled lists: best for mappings and brief facts

Use `- **Term:** explanation` for glossaries, configuration descriptions, dates, measurements, and simple name-to-value material. This uses familiar Markdown syntax, needs little indentation, and has less visual overhead than one heading per fact.

Headings, paragraphs, lists, links, and strong emphasis are established CommonMark structures. That makes this approach a safer shared convention across Markdown consumers. [CommonMark specification](https://spec.commonmark.org/0.31.2/).

### Definition lists: a good specialized option, not the universal rule

A definition list is semantically natural for a glossary or term-and-description pair. Pandoc supports colon-marked definitions through its `definition_lists` extension, and Markdown Extra documents the corresponding term/definition structure. [Pandoc definition lists](https://pandoc.org/MANUAL.html#definition-lists), [Markdown Extra definition lists](https://michelf.ca/projects/php-markdown/extra/#def-list).

For a controlled Pandoc-only workflow, this is a reasonable optional format. For the linker's general research output, its advantage is too small to justify the portability cost demonstrated above. The current stylesheet also has no explicit `dl`, `dt`, or `dd` rules, so its HTML appearance depends on default browser styling. A carefully styled definition list could look excellent; that styling was not implemented or tested here.

### Short comparative prose: best for the takeaway

When a table contains only a few simple distinctions, two or three sentences can explain the relationship more clearly than a repeated schema. Use this for the conclusion or executive overview. Do not turn a detailed evidence table into prose that silently drops inconvenient cells, qualifications, or citations.

### Charts and diagrams: useful supplements for genuinely visual relationships

For trends, magnitudes, or dependencies, a deliberately designed figure may communicate the pattern well. It should supplement a readable explanation and any exact values the reader needs. Converting the original table to a screenshot merely preserves the small text and width problem while making the text harder to search and copy.

Charts also introduce an asset and rendering requirement. They should not be mandatory for an ordinary linker pass, and a Markdown diagram fence should not be assumed to become a figure without a renderer that supports it.

### HTML cards, custom callouts, ASCII grids, and raw LaTeX: poor defaults here

Custom HTML can produce attractive blocks in a controlled HTML-to-PDF pipeline. However, Pandoc suppresses raw HTML in other output formats, so content placed only inside raw HTML is a risky fit for a LaTeX fallback. [Pandoc raw HTML documentation](https://pandoc.org/MANUAL.html#raw-html).

HTML/CSS grids, renderer-specific callout syntax, and raw LaTeX also make the report depend on particular tooling. ASCII or Unicode box tables inside code fences retain the wide-grid problem and use a code presentation for ordinary prose. Blockquotes add indentation and quotation styling, which the inspected stylesheet renders with a gray border and muted text. None is preferable to normal headings and lists for the default output contract.

The wkhtmltopdf maintainer's status page documents its old Qt/WebKit base. I infer that conservative block layout is a better choice than relying on modern browser layout features in this installed engine. That is a compatibility consideration, not a recommendation to migrate converters as part of this task. [wkhtmltopdf project status](https://wkhtmltopdf.org/status.html).

## Concrete conversion patterns

The following examples are illustrative. Their values and recommendations are not empirical findings about particular products.

### A multi-column comparison becomes one section per subject

Imagine a source table with the headers “Approach,” “Strength,” “Limitation,” and “Best use.” Convert the approach into a heading and preserve the other headers as field labels:

```markdown
## Comparison of approaches

### Approach A

- **Strength:** Handles long explanations without narrow columns.
- **Limitation:** Repeats labels and can make the report longer.
- **Best use:** Research comparisons with several descriptive fields.

### Approach B

- **Strength:** Keeps simple mappings compact.
- **Limitation:** Offers less structure for complex evidence.
- **Best use:** Brief term-to-description material.
```

Preserve the same field order for every subject. Use the correct heading level for the surrounding document; do not promote every former row into a top-level section.

### A two-column glossary becomes a labeled list

```markdown
- **Definition list:** A term followed by its explanation.
- **Labeled bullet:** A bullet whose bold label identifies the value.
- **Comparison section:** A heading followed by consistently labeled fields.
```

For a short row with several tiny values, one bullet can still work: `- **Sample A:** median latency 120 ms; p95 latency 300 ms; sample size 50.` Use separate fields when that sentence becomes difficult to scan.

### A decision matrix becomes criterion-oriented comparisons

If the reader's question is “How do all candidates compare on portability?”, grouping by candidate alone forces too much backtracking. Group the content by the criterion instead:

```markdown
### Portability

- **Approach A:** Supported in the tested Markdown readers.
- **Approach B:** Requires an additional syntax extension.

### Reading long explanations

- **Approach A:** Gives each explanation the full text width.
- **Approach B:** Groups several fields into a denser paragraph.
```

Choose one main orientation based on the decision the report supports. Do not duplicate the whole matrix in both orientations. A short overview can highlight the winner on each important criterion.

### A numerical table becomes explicit measurements

```markdown
### Dataset A

- **Median latency:** 120 ms.
- **95th percentile latency:** 300 ms.
- **Sample size:** 50 observations.
- **Conditions:** Warm cache; one worker.
- **Source:** [Measurement notes](https://example.org/notes).
```

Repeat units and conditions where needed. Preserve exact values, uncertainty intervals, denominators, time periods, and the distinction between zero, unknown, and not applicable. For a large dataset, group labeled records in an appendix; a separate CSV can be useful additional material, but it should not replace exact values the final report promises to contain.

### A timeline or procedure becomes an ordered list

```markdown
1. **Preparation:** Gather evidence and record sources.
2. **Synthesis:** Compare findings and resolve disagreements.
3. **Review:** Preserve qualifications and check the PDF preview.
```

Use numbering when sequence or ranking matters, and bullets when it does not.

## Preserve the table's meaning, not just its text

A grid communicates associations through its row and column headers. W3C's table guidance emphasizes those relationships and warns that format conversion can lose structural markup. [W3C tables tutorial](https://www.w3.org/WAI/tutorials/tables/).

My implication for this task is that every retained value should acquire enough context to stand on its own. A converted row needs its subject; each field needs its label. Carry over captions, footnotes, sources, merged-header context, exceptions, and conflicting evidence. For a cell beneath “2025” and “Revenue,” a bare “12” is insufficient; the resulting field should specify the period, measure, value, and unit.

A nice-looking linear document is not automatically an accessible tagged PDF. This research did not audit PDF tagging or screen-reader behavior. The goal here is clear reading order and preserved meaning in the authored content.

## Suggested instruction for the linker agent

The following is ready to add to the linker's prompt. It asks for the output format directly and leaves the choice of grouping responsive to the content:

```text
Write the final research Markdown for a narrow, single-column PDF.
Do not include Markdown tables, including pipe, grid, or aligned-column
forms. Do not substitute HTML tables, ASCII/Unicode box tables, or images
of tables.

For comparisons with several fields, use a short heading for each subject
and bullets with bold field labels, preserving the same field order across
subjects. For simple mappings, use compact "- **Label:** explanation"
lists. When comparison by criterion is more useful, group by criterion and
list each subject underneath. Use numbered lists for sequences or rankings.

Preserve all substantive values, units, qualifications, row/column context,
footnotes, citations, and disagreements. Do not invent information to fill
missing cells. Keep explanations concise, nesting shallow, and heading
levels consistent with the document. Put a blank line before each list.

Use ordinary Markdown headings, paragraphs, lists, emphasis, and links.
Avoid renderer-specific cards or callouts. Before saving, check the entire
final document for table structures and make sure every important original
relationship remains explicit in the replacement text.
```

“Several fields” is deliberately a writing judgment. Three or more columns is a useful starting heuristic for choosing sections, but a three-column table of tiny values may still become a compact labeled list. The important constraint is readable, full-width text with explicit associations.

## Verification and optional rendering polish

For the initial prompt change, the minimum review is practical:

1. Parse the output and confirm there are no table nodes. A Markdown-aware parser is more reliable than searching for `|`, which can occur in code and prose. Disabling table parsing would merely hide the problem by leaving table-like source as ordinary text.
2. Review that every meaningful subject, field, numeric value, qualification, and citation survived the conversion. A table-node check cannot establish completeness.
3. Render through the real preferred engine and a fallback. Inspect a long comparison, a short mapping, a numerical example, and a page boundary. A successful exit code alone says nothing about readability.

If enforcing this automatically later, a Pandoc filter can act on `Table` nodes, and a block filter can replace a block with a sequence of blocks. That gives an implementation route for a structural guard or converter, but complex headers, spans, notes, and multi-paragraph cells need explicit preservation rules. The default linker policy should still be authored synthesis rather than a blind cell-to-bullet rewrite. [Pandoc Lua filter documentation](https://www.pandoc.org/lua-filters.html).

For additional polish, keep headings with the following text, use comfortable list spacing, and discourage orphaned paragraph lines. The existing HTML stylesheet already applies `page-break-after: avoid` to headings. Further CSS could add `widows` and `orphans` settings, or prevent a short field bullet from splitting. These controls are engine-dependent and need previewing. Avoid declaring every complete comparison section unbreakable: a long section must be able to flow across pages. The CSS fragmentation specification describes both break controls and relaxation when content cannot otherwise fit. [CSS Fragmentation Level 3](https://www.w3.org/TR/css-break-3/).

No rendering-style changes were made for this report. The recommendation works with the inspected default stylesheet; optional polish belongs in the conversion template, rather than custom markup repeated in every research file.

## Recommended solution

**Tell the linker to replace tables with single-column Markdown: headings plus consistently labeled bullets for comparisons, and compact bold-label lists for simple mappings.** Choose criterion-oriented grouping when the reader needs to compare one dimension across all candidates. Preserve every substantive value and qualification, use ordinary Markdown, and preview the actual PDF before accepting the format. Definition lists are a useful optional convention for a controlled Pandoc glossary, but they are not the best universal replacement for this swarm's research output.
