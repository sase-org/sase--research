---
title: "Blank pages before research Mermaid diagrams: a Bob PDF pagination defect"
date: 2026-10-24
status: final
tags: [research, bob, pdf, mermaid, pagination]
---

# Blank pages before research Mermaid diagrams

The immediate cause is **the Markdown-to-PDF layout used by `bob ref create`**.
The research swarm supplies a tall diagram, but it does not insert the blank page.
Bob places the rendered diagram directly after a heading and sizes the image against
the entire page's text height. The heading and return-link controls need additional
space. That combination becomes too tall to fit, producing both a blank page and an
overflowing diagram page.

This is confirmed by reproducing the supplied PDF: **25 pages, page 9 containing only
its page number, and the first diagram on page 10**. All 25 pages of extracted text
matched the original, page by page. In a controlled rendering, reserving 15% of the
text height above/below images produced **24 pages, no blank pages, and no vertical
overflow warning**. The first diagram and its explanatory caption then fit together
on page 9.

The durable fix belongs in Bob's rendering pipeline. The swarm's diagram validation
should also check composed pages, because its current size check can accept the
diagram that triggers this defect. No production code or vault files were changed
during this investigation.

## Evidence from the supplied PDF

Inspected file: `~/bob/lib/chat/pomodoro_theme_catalog.pdf`.

SHA-256: `a51ea985e812ec7a94920b5cde2a67f71d1a6bf58315f52e310a00a16aff1879`.

The PDF identifies its creator as **LaTeX via pandoc** and its producer as
**xdvipdfmx (20260317)**. Its pages are US Letter, 612 × 792 PDF points.

| Page | Observed content |
| --- | --- |
| 8 | Ends with four proposed decision names and a link to rejected alternatives; much of the page is unused. |
| 9 | Only the page number `9`; no diagram, body text, or drawing content. |
| 10 | “Data model and ownership,” two return-link pills, and the first Mermaid diagram. The diagram runs into the footer/bottom margin. |
| 11 | The first diagram's explanatory caption, followed by the data-model discussion. |
| 15 | The second Mermaid diagram, introduced by a return-link pill. It does not have an entirely blank preceding page. |

Thus the supplied example has **one completely empty body page**, not an empty page
before every Mermaid diagram. There is also excessive whitespace from normal
attempts to move a large, unsplittable block to the next page.

The exact published Markdown was read through the audited artifact interface:

- `file:explicit:d74a2d9b550524b4b8c68ce2`, labeled
  `research:202610/pomodoro_theme_catalog/pomodoro_theme_catalog.md`, produced by
  `research.2c.linker`.
- The companion proposal manifest was also read:
  `file:explicit:e8d58b953650e9e660c67339`.

The first diagram immediately follows `### Data model and ownership` in ordinary
Markdown. It has no surrounding figure-anchor div. The second diagram is inside
`<div id="figure-hide-lifecycle">`. The report contains no explicit `\newpage`,
`\clearpage`, or page-break instruction. The problematic first diagram was already
in the lead's report; the companion manifest proposes only the second diagram.

## Which component renders the PDF

The path in this configuration is:

```text
research_swarm authors/publishes Markdown
  → research-highlights file hook selects the final report
  → bob ref create --include-id -P "$SASE_FILE_HOOK_PROJECT"
  → Bob renders Mermaid blocks to individual vector PDFs
  → Bob swaps each block for a Pandoc image
  → Pandoc + XeLaTeX lay out the complete document
  → Bob files the resulting reference PDF
```

The hook command is configured in
[the dotfiles SASE configuration](https://github.com/bbugyi200/dotfiles/blob/1da17c915d8e1113f12f49801c4f10e86b5c9589/home/dot_config/sase/sase.yml#L17-L19).
The research plugin's
[hook specification](https://github.com/sase-org/sase-research-artifacts/blob/133326168f8d5810a0b7e7f94191bf3111b3a6c1/src/sase_research_artifacts/provider.py#L102-L133)
selects published reports and excludes swarm drafts and companion manifests.

Bob's
[generic Markdown renderer](https://github.com/bobs-org/bob-cli/blob/c7e0dab6903008ef80a979980446503761bb38cb/src/native/highlights_ref/create.rs#L3366-L3443)
explicitly invokes Pandoc with XeLaTeX, 0.85-inch margins, 10-point DejaVu Serif,
1.08 line spacing, a table of contents, numbered sections, and its Lua filters.
The SASE attachment renderer is a separate path; it is not responsible for the
examined Bob library PDF.

## Why the layout fails

There are three interacting behaviors.

1. **The graphic can consume the whole text height.** Bob's Mermaid
   [swap filter](https://github.com/bobs-org/bob-cli/blob/c7e0dab6903008ef80a979980446503761bb38cb/src/native/highlights_ref/diagrams.lua#L63-L67)
   returns a bare image paragraph without width or height attributes:

   ```lua
   return pandoc.Para{
     pandoc.Image({}, pdf, "", pandoc.Attr(ident))
   }
   ```

   The installed Pandoc 3.1.3 LaTeX template therefore supplies these defaults:

   ```tex
   \def\maxwidth{\ifdim\Gin@nat@width>\linewidth\linewidth\else\Gin@nat@width\fi}
   \def\maxheight{\ifdim\Gin@nat@height>\textheight\textheight\else\Gin@nat@height\fi}
   \setkeys{Gin}{width=\maxwidth,height=\maxheight,keepaspectratio}
   ```

   Those limits describe an image alone, not the image plus its heading, pills,
   caption, and paragraph spacing. They also do not describe the remaining space
   on the current page. This template was inspected locally with `pandoc -D latex`;
   it is a version-specific observation, not a claim about every Pandoc release.

2. **The preceding content resists being separated from the image.** The section
   heading keeps with following material. Bob also inserts
   [return-link rows](https://github.com/bobs-org/bob-cli/blob/c7e0dab6903008ef80a979980446503761bb38cb/src/native/highlights_ref/return_links.lua#L405-L421),
   whose [TeX definition](https://github.com/bobs-org/bob-cli/blob/c7e0dab6903008ef80a979980446503761bb38cb/src/native/highlights_ref/return_links.tex#L15)
   uses `\nopagebreak[4]` and `\@afterheading`. These enlarge and strengthen the
   grouping, but are **not necessary** for the failure: disabling return links
   still reproduced a blank page and vertical overflow.

3. **The first diagram is height-limited.** Bob's renderer reported a natural size
   of 514.5 × 714.75 PDF points, approximately 686 × 953 CSS pixels. The actual
   embedded PDF bounds were 515.04 × 714.96 points after browser output rounding.
   The available text area is 489.6 × 669.6 PDF points. Fitting the diagram alone
   consumes essentially all 669.6 points of height, leaving no room for the
   heading and return pills. The reproduction logged:

   ```text
   Overfull \vbox (56.08157pt too high) has occurred while \output is active
   ```

The blank page and overflowing next page are two symptoms of that oversized
heading/graphic grouping. This is not a blank page contained inside a Mermaid PDF:
Bob's
[browser renderer](https://github.com/bobs-org/bob-cli/blob/c7e0dab6903008ef80a979980446503761bb38cb/scripts/web_clip/diagram_render.py#L192-L237)
exports the diagram as a fitted vector PDF with `page_ranges="1"`, and the final
document contains it as a page-local PDF form.

The second diagram is smaller: the renderer reported 465.75 × 605.25 points,
with embedded bounds of 466.08 × 606. It leaves more vertical space and did not
produce the same entirely blank preceding page.

## Controlled experiments

All experiments used scratch files. They called the checked-out Bob renderer and
filters directly; they did not invoke a vault-writing `bob ref create` operation.

| Experiment | Result | What it establishes |
| --- | --- | --- |
| Original published source, original infographic extracted from the PDF, Bob renderer and filters | 25 pages; page 9 footer-only; diagram on page 10; all 25 pages' extracted text identical to the original | The inspected pipeline reproduces the user's actual defect. |
| Small document with one inbound link, a heading, the first real diagram, and a caption | 4 pages; page 2 footer-only; vertical overflow of 56.08 TeX points | The swarm's long report and overall structure are not required. |
| Same small document with `bob-return-links: false` | 4 pages; page 2 footer-only; vertical overflow of 25.87 TeX points | Return-link controls aggravate the problem but are not the sole cause. |
| Same small document, heading changed to ordinary text | 3 pages; no blank page or vertical overflow | Keeping the heading with the tall image is part of the trigger. |
| Same small document, allowing breaks around the return row | 3 pages; no blank page; heading/pills separated from diagram | Breaking the grouping avoids the failure, at the cost of a disconnected heading. |
| Same small document, replacing Mermaid with an ordinary vector PDF of the same natural size | 4 pages; page 2 footer-only; vertical overflow of 56.11 TeX points | Mermaid syntax, rendering, and the macro are not required; the image layout is sufficient. |
| Full report, maximum image height capped at 85% of text height | 24 pages; no blank pages or vertical overflow; first diagram and caption together on page 9 | Reserving vertical space fixes this document while preserving its content and links. |

For the full report, the bottommost drawing on the first diagram page moved from
786.48 to 686.63 PDF points from the top. The normal content boundary is 730.8
points. Visual inspection confirmed the original overlaps the footer and the
experimental version stays within the body area.

The experiment changed the maximum-height definition to:

```tex
\makeatletter
\def\maxheight{\ifdim\Gin@nat@height>.85\textheight
  .85\textheight\else\Gin@nat@height\fi}
\makeatother
```

This was a diagnostic override, not an installed fix. It changes the default for
all images. A fixed 85% limit is not a proof that arbitrary headings, many backlink
rows, and long captions will fit. Other existing horizontal code-block overflow
warnings remained; they are separate from this pagination defect.

## Recommended correction

**Fix the composed layout in Bob.** Give a diagram a height budget that leaves
space for adjacent material, and ensure the content kept together cannot exceed a
fresh page. Put that policy in Bob's diagram/image rendering and TeX integration,
where it also protects standalone `bob ref create` users. A smaller diagram cap is
a useful initial correction, but it should be paired with an explicit policy for
long headings, multiple rows of return pills, and captions. If a grouping cannot
fit, allow a deliberate break or require a smaller/split diagram instead of forcing
an impossible unbroken block. Preserve figure IDs and return-link destinations.

The warning calculation should use the same effective height budget as the final
layout. Currently Bob's
[scale estimate](https://github.com/bobs-org/bob-cli/blob/c7e0dab6903008ef80a979980446503761bb38cb/src/native/highlights_ref/diagrams.rs#L805-L822)
and generic page constants consider the full text box. They can predict readable
labels while missing the heading/graphic overflow.

**Improve the swarm's validation as a second layer.** Its
[Mermaid guide](https://github.com/sase-org/sase-research-artifacts/blob/133326168f8d5810a0b7e7f94191bf3111b3a6c1/src/sase_research_artifacts/skills/mermaid_diagrams.md#L59-L66)
already recommends roughly 650 × 700 pixels, but the acceptance calculation is
`min(1, 652.8 / width, 892.8 / height)` with a 75% floor. The first diagram's fit
is approximately 93.7%, so it passes despite filling the page vertically. Reviewing
an isolated PNG/SVG does not exercise its actual heading, return links, or caption.
Validate at least the composed page containing each large diagram, using Bob's
rendering profile. The first diagram being inherited from the lead also means
checking only newly proposed companion diagrams is insufficient.

**Add rendering regression coverage.** The existing
[diagram replacement test](https://github.com/bobs-org/bob-cli/blob/c7e0dab6903008ef80a979980446503761bb38cb/src/native/highlights_ref/create.rs#L4582-L4627)
checks that Mermaid source and an implicit “Figure 1” caption disappear. Its PDF
fixture is only 200 × 80 points; it does not test this tall-image case. Cover a
height-limited image after a heading, with and without return links, plus an
anchored figure div and a normal small diagram. Check for body-empty pages,
vertical overflow, clipped content, readable sizing, and valid link destinations.
Successful TeX exit status alone is insufficient: all the failing reproductions
completed successfully.

For an immediate document-specific workaround, shorten or split the first diagram
so it leaves space for its heading and caption. Disabling return links is not a
reliable workaround. Deleting blank pages after rendering would leave the overflow
in place and invalidate printed page references unless the document were rebuilt.

## Reproduction notes and scope

Inspected revisions:

- `bob-cli`: `c7e0dab6903008ef80a979980446503761bb38cb`.
- `sase-research-artifacts`: `133326168f8d5810a0b7e7f94191bf3111b3a6c1`.
- `dotfiles`: `1da17c915d8e1113f12f49801c4f10e86b5c9589`.

Runtime tools were Pandoc 3.1.3, XeTeX from TeX Live 2026, Bob's vendored Mermaid
12.2.0, Playwright 1.62.0, and Chromium 156.0.8078.4. The installed Bob command
reports 0.3.1; the controlled rendering used the source revision above rather than
assuming the binary's version identifies its exact commit.

To repeat the investigation:

1. Read the published source with `sase artifact read` using the explicit file
   reference above. Use a short scratch directory for browser work: Chromium's
   Unix-domain socket path limit prevents a long nested workspace path from working.
2. Collect the two Mermaid block texts and their Pandoc-compatible SHA-1 IDs. Call
   `scripts/web_clip/web_clip_adapter.py` via `uv run --script` with protocol 1,
   `op: diagrams`, an absolute scratch `workdir`, `items: [{id, source}, ...]`, and
   `item_timeout_s: 30`. Map successful outputs into `{"diagrams": {id: {"pdf": path}}}`.
3. Provide the original infographic alongside the source. For this investigation,
   its PNG bytes were extracted from image object 49 of the supplied PDF.
4. Run Pandoc with `create.rs::render_temp_pdf`'s arguments and headers, applying
   `diagrams.lua`, the embedded code-break filter, and `return_links.lua` in that
   order. Write the intermediate `.tex` and compile it with XeLaTeX until the
   contents and page references settle; three passes were used for the full report.
5. Extract page text and inspect the pages around the first diagram. Recompile with
   the maximum-height override above and compare both the pages and the TeX log.

Pandoc's official documentation recommends inspecting generated TeX when debugging
PDF production; its PDF engine and template determine the final layout.
[Pandoc User's Guide: creating a PDF](https://pandoc.org/MANUAL.html#creating-a-pdf).

The minimal input used to isolate the layout was a short link to
`#data-model-and-ownership`, the `### Data model and ownership` heading, the first
diagram fence copied unchanged from the published source, and one caption paragraph.
The generic-image control replaced only that fence with `![](tall.pdf)`, where
`tall.pdf` was a one-page 514.5 × 714.75-point rectangle with a text label, rendered
under the same Bob profile and filters.

This report establishes the cause for the supplied example and a reproducible class
of similarly tall diagrams. It does not claim every large figure, every Mermaid
diagram, or every PDF engine has the same behavior. It records an experimentally
verified correction direction; it does not claim a production fix has been applied.
