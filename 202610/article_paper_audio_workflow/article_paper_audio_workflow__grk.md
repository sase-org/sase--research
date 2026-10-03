# Listen to web articles and papers in AntennaPod

**Date:** 2026-10-03 · **Author:** research.3i.grk · **Type:** independent swarm report

## Bottom line

The idea is good. The instinct to reuse `sase-listen` plus AntennaPod is also good. The mistake would be treating a web article or a research PDF as if it were already a Markdown research report.

`sase-listen` is a **renderer**: Markdown or a narration script in, chaptered MP3 out, private RSS feed for AntennaPod. It does not fetch URLs, parse PDFs, skip citations, or speak math. `load_source()` accepts a local file or a `kind:path` artifact ref and nothing else. Pointing it at `https://arxiv.org/pdf/2511.04427` fails with "Source not found."

Build a thin **ingest + edition** layer in front of the renderer you already have. Do not grow `sase-listen` into a scraper, and do not adopt Speechify / Audemic / NotebookLM as the commute player.

Split the corpus. Industry HTML posts on the follow-up reading list are commute-native. Academic PDFs are not. For papers, write the same kind of audio edition `#research/audio` already writes for SASE reports (brief ~4 min, full ~16 min). Do not "transcribe" them.

Finish the AntennaPod feed rollout (`sase-1ej`) before adding ingest. Without a served feed, new source types have nowhere to land on the phone.

---

## Question

How should Bryan turn recommended **web articles and research papers** — the mix in `research:202609/sase_paper_followup_reading_list/sase_paper_followup_reading_list.md` — into audio he can listen to in **AntennaPod** while walking or commuting?

Existing pieces:

- `sase-listen` 0.1.0 on PATH, Markdown → chaptered MP3, private podcast feed
- `#research/audio` and `#research_swarm audio=true` for SASE research reports
- AntennaPod on `pixel-10-pro-xl`, Tailscale, feed config on apollo (feed not yet served)

This is a different problem from `research:202610/commute_audio_from_markdown`, which solved **Markdown already in the research sidecar**. The new sources are HTML pages and PDFs that `sase-listen` cannot open.

---

## Critique of the implied plan

The implied plan is: take an article or paper, get it into `sase-listen`, publish to the private feed, listen in AntennaPod.

**Keep:** AntennaPod as the only commute player. One voice, one feed, chapters, 1.5×, offline download, queue. Delivery is already designed. Telegram `sendAudio` is a bonus path, not the walk path.

**Reject:** "transcribe" as the product. A commute is eyes-busy. PaperWave (CHI EA 2025, arXiv:2410.15023) spent two months watching 11 people listen to LLM-scripted paper podcasts on trains, walks, and chores, and the design lesson is the listener's environment, not the TTS engine. You cannot glance at a figure, a two-column methods table, or a citation cluster while walking. Verbatim paper TTS fails that environment even when the voice is good.

**Reject:** teaching `sase-listen` to fetch the web and parse PDFs. The tool's contract, docs, and `pipeline.load_source()` are Markdown-in. Marker / MinerU / Docling pull in GPU weights, OCR models, and layout pipelines. That would wreck a standalone `uv tool install` CLI whose whole point is "no sase imports, bundled ffmpeg, render a script." June 2026 audio research already said PDF extraction is workflow glue, not core.

**Reject:** a second commercial listen-to-papers app as the primary surface. Audemic, Listening.com, Speechify, ResearchBunny, ResearchPod, NotebookLM, and Google Illuminate all solve some slice of this. None of them publishes into the AntennaPod feed you are already standing up, none of them shares the Charon / −16 LUFS / ID3-chapter contract, and several are two-host "podcast about the paper" products that `commute_audio_from_markdown` already set aside as a different product.

**The plan is a good idea once the requirement is restated:** produce commute-ready **audio editions** of recommended reading, delivered through the feed you already have, with ingest sitting **in front of** `sase-listen` rather than inside it.

---

## Requirement adjustments (called out)

These change the request. They are intentional.

1. **Replace "transcribe" with "audio edition."** The output is a chaptered spoken argument (recommendation first, then reasons, then a recap), not a word-for-word reading of the PDF. This is already the contract in `sase-listen guide` and `#research/audio`.
2. **Split article vs paper.** HTML industry posts may go through the deterministic normalizer (verbatim). Academic papers always go through an agent-written `brief` or `full` edition. Never verbatim papers.
3. **Do not auto-queue the whole reading list.** The list has 48 URLs, 38 unique arXiv IDs, and 9 industry HTML URLs. A full edition of every paper is on the order of ten hours of audio you will not finish. Generate on demand, same rule as `audio=true` being opt-in for research swarms.
4. **Do not commit extracted paper Markdown or MP3s to the public research sidecar.** Extracts live under `$XDG_DATA_HOME/sase-listen/sources/`. Commit only a narration script if you want a reviewable artifact, and even that can stay in the listen library. The research git repo is public.
5. **Finish feed serving before building ingest.** `research:202610/sase_listen_antennapod_setup.md` is still the blocker: nothing listens on `:8443`, the Gemini key was free-tier, the feed token leaked and must be rotated. Ingest without delivery is a folder of MP3s on apollo.
6. **Personal-use, private-feed copyright posture.** TTS of legally obtained papers and posts for a locked private feed (`itunes:block yes`, `podcast:locked yes`) is a personal copy. Do not Funnel the feed to the public internet if it contains third-party papers. Prefer Tailscale Serve, which the setup note already recommends because the Pixel is on the tailnet.
7. **Default paper edition is `brief` (~4 min), not `full`.** Walking is a first pass that decides whether the paper deserves a desk read. `full` (~16 min) is opt-in. Verbatim of the CMU HTML paper I fetched is ~23k words including chrome, citations, and methods — about **152 minutes** at 150 wpm. That is not a commute object.

---

## What the reading list actually is

I counted the URLs in the published follow-up list (not the swarm drafts).

| Kind | Count | Examples |
| --- | ---: | --- |
| arXiv URLs | 39 (38 unique IDs) | MAGE, Gorinova, He et al., Tang, Wang et al., Edwards & Schuster, Ye et al., plus companions |
| Industry / lab HTML | 9 | OpenAI, Anthropic (4), Martin Fowler (2), METR, Spotify Honk |

The **ten picks**, classified for listening:

| # | Item | Source class | Commute fit |
| --- | --- | --- | --- |
| 1 | OpenAI *Harness engineering* | HTML article, ~20 min read | Verbatim or full edition. Best first episode. |
| 2 | Anthropic harness pair | Two HTML articles | Verbatim. Two episodes, or one full edition covering both. |
| 3 | MAGE | arXiv PDF / HTML | Brief or full edition. Dense framework paper. |
| 4 | Gorinova position | arXiv | Brief. Position papers compress well. |
| 5 | He et al. (CMU / MSR) | arXiv HTML available | Brief. The numbers (+281% lines, +42% complexity) are the episode. Methods are un-listenable while walking. |
| 6 | METR note | HTML research note | Verbatim-if-cleaned, or full. I fetched ~4.8k words of page text (~32 min raw, less after dropping nav). |
| 7 | Tang et al. | arXiv | Brief. The taxonomy table is the payload. |
| 8 | *Humans are Missing* | arXiv | Brief. Agenda paper. |
| 9 | *Ask or Assume* | arXiv | Brief. One table of resolve rates. |
| 10 | *Coding with "Enemy"* | arXiv | Brief. 94% / 56% are the episode. |

Suggested-order "one evening" from the list is OpenAI → Anthropic → METR → Tang: **three HTML items and one paper**. That is the right dogfood set. Do not start with MAGE.

I fetched three live sources this turn:

- **OpenAI HTML** rendered as a long prose post with headings. Already written to be read. `sase-listen script` would drop figures and keep the argument. Good verbatim candidate.
- **METR HTML** is a research note with figures and an appendix. After dropping nav, it is commute-length. The appendix can be omitted.
- **arXiv HTML for 2511.04427** (He et al.) exists and is usable as an extract source (`https://arxiv.org/html/2511.04427`). The page I fetched is 22,816 words with 245 citation-like fragments and substantial LaTeX residue. Feeding that to `sase-listen script` would produce a very long, citation-noisy episode. An agent edition is the only listenable path.

arXiv's own HTML pipeline (LaTeXML) now produces some HTML for about 97% of new TeX submissions, with roughly 75% called error-free as of mid-2026 (Ginev et al., arXiv:2605.16562). Historical papers still go through ar5iv. Prefer `arxiv.org/html/{id}` before touching a PDF.

---

## What `sase-listen` will and will not do today

Verified against the linked checkout `sase/repos/linked/sase-listen` and the installed CLI.

**Will do**

- Render a narration script or any local Markdown
- Resolve `research:…` via `sase artifact read`
- Deterministic normalizer: drop fences, mermaid, math, HTML comments, footnotes, `Sources`/`References`, large tables; speak small tables; strip URLs and `file:line`
- Chaptered 64 kb/s mono MP3 at −16 LUFS, ID3 chapters, Podcasting 2.0 chapters JSON
- Publish `kind: research` automatically when `auto_publish: true`; `kind: document` needs `--publish`
- Private RSS 2.0 feed with `itunes:block` / `podcast:locked`

**Will not do**

- HTTP URLs (non-ref sources are `Path(source)` and must exist on disk)
- PDF, HTML files, arXiv IDs
- Citation skipping, math speech, figure descriptions
- Writing the audio edition (that is `#research/audio` or a human following `sase-listen guide`)

The normalizer dropping math and References is the right behavior for an edition. It is the wrong behavior to rely on for a "read me the paper" product — those products (Listening.com, Audemic) exist because academic TTS is a specialized skip-list problem. You do not want that product in AntennaPod. You want the edition.

`#research/audio` is also the wrong entry point as-is: it wants a `@research:` report (or a swarm-lead fork), writes `<stem>_narration.md` next to that report, and registers an artifact. A random OpenAI URL is not a research sidecar document. Do not copy extracted papers into `sase--research` to reuse the xprompt.

---

## Alternatives

| Option | What you get | Why it loses as the primary path | When it is still useful |
| --- | --- | --- | --- |
| **A. Hand pipeline into current `sase-listen`** | `uvx trafilatura` or `pdftotext` → Markdown → `sase-listen render --publish` | Manual, but unblocks this weekend | **Spike / Phase 0.** Do this for OpenAI + METR now. |
| **B. Grow `sase-listen render` to accept URLs and PDFs** | One command | Pulls scraper + PDF-layout deps into a renderer; papers still need an agent edition | Later, HTML-only `sase-listen fetch` as a convenience. Not v1. |
| **C. New `#listen` xprompt in sase-research-artifacts** | `sase run '#listen URL\|arxiv:ID\|file.pdf'` writes extract + edition + render + publish | Needs a small xprompt and a fetch recipe | **Recommended v1 for papers, and the unified UX.** |
| **D. Speechify / NaturalReader / ElevenReader** | Fast PDF/web TTS on the phone | Second library, no private feed, no shared chapters/voice, subscription | Accessibility fallback, not the commute system. |
| **E. Audemic / Listening.com** | Academic TTS with citation skip and section jump | Same split-library problem; verbatim papers while walking still fail PaperWave's environment test | Desk listening with the PDF on screen. |
| **F. NotebookLM / Illuminate / ResearchBunny / ResearchPod** | Two-host or 3–9 min summary of a paper | Already classified as a different product in commute-audio research; no AntennaPod; weaker number fidelity than `lint --source` | Occasional "podcast about a paper" treat, not the reading-list pipeline. |
| **G. AntennaPod "Add local folder"** | Play MP3s without RSS | No auto-download of new episodes, no remote publish from apollo | Fallback if Serve/Funnel is down. |
| **H. Phone read-aloud of arXiv HTML** | Zero pipeline | Chrome TTS quality, no chapters, no queue, no feed | Emergency only. |

I would not take D–F as the architecture. I would take **A this week, C as the feature, B only if C gets annoying.**

---

## Ingest tools (the actual gap)

### HTML articles

Trafilatura 2.3.0 (PyPI 2026-10-02) is the default: CLI, Markdown output, metadata, F1 around 0.94–0.96 on standard article corpora, CPU, permissive license. Mozilla Readability is close on fidelity and better in-browser; Newspaper4k leaks less boilerplate. Jina Reader (`r.jina.ai/<url>`) and Firecrawl exist for JS-heavy pages.

Not installed on this workspace. `pandoc` and `pdftotext` are on PATH. `beautifulsoup4` is importable. A spike can be `uvx trafilatura` with no project dep.

Risk: some industry blogs (OpenAI's page included a "Loading…" shell in the fetch) are JS-heavy. Recipe: try trafilatura; if extracted word count is under ~400, retry via `r.jina.ai` or a headless fetch. Do not start with a headless browser.

### Academic PDFs

2026 converter comparisons (olmOCR-bench, pdfmarkdown.app's 9-tool test) converge on:

| Tool | Role here |
| --- | --- |
| **arXiv HTML** | First choice when the ID is on arXiv. Free, already structured. |
| **pdftotext** | First PDF fallback. Already installed. Good enough for an agent writing a brief edition. Ugly for verbatim. |
| **Marker** | Best all-round OSS PDF→Markdown if you later want higher-fidelity extracts. GPU helps; CPU works. License watch on model weights. |
| **MinerU** | Highest paper/formula scores in several tests; heavier; GPU for the VLM path. Overkill. |
| **Docling** | MIT, CPU, honest gaps (drops formulas rather than inventing them). Fine if Marker is awkward. |
| **PyMuPDF4LLM / MarkItDown** | Fast and shallow. Fine for born-digital text PDFs, weak on two-column academic layout. |

**Extraction quality tracks the edition.** A brief agent edition is robust to a messy `pdftotext` dump: the agent is writing spoken prose and `lint --source` only requires that numbers in the script appear in the source. Verbatim needs Marker-class layout. Because verbatim papers are rejected above, **do not install Marker/MinerU for v1.**

### Why not put this in `sase-listen`

`sase-listen` AGENTS.md: no `sase` imports, no plugin topic, phases own disjoint modules, `pyproject.toml` is scaffold-owned. A PDF stack is a second product. Keep the renderer boring.

---

## Recommended solution

### Architecture

```
URL | arxiv:ID | PDF
        │
        ▼
  ingest (xprompt / uvx recipe)
        │  HTML: trafilatura → markdown
        │  arXiv: html.arxiv.org then trafilatura; else pdftotext
        │  PDF: pdftotext
        ▼
  $XDG_DATA_HOME/sase-listen/sources/<slug>.md     (not git)
        │
        ├── article, short enough → sase-listen script (verbatim)
        └── paper, or long article → agent writes *_narration.md
                (reuse sase-listen guide + lint --source)
        ▼
  sase-listen render [--publish]
        ▼
  library + private feed → AntennaPod
        └── Telegram sendAudio (already wired)
```

`sase-listen` stays Markdown-in. The new work is classification, fetch, and (for papers) the same audio-edition agent you already have.

### v1 interface

```bash
sase run '#listen https://openai.com/index/harness-engineering/'
sase run '#listen(edition=brief) arxiv:2511.04427'
sase run '#listen(edition=full) https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/'
sase run '#listen ~/papers/mage.pdf'
```

Launchable from Telegram the same way `#research/audio` is.

Behavior:

- Detect source class (http(s), `arxiv:` / bare `NNNN.NNNNN`, `.pdf` path).
- Fetch to `sources/`.
- **Article:** if cleaned word count ≤ ~3,000 (~20 min), deterministic script + `render --publish`. If longer, agent `full` edition.
- **Paper:** always agent edition, default `brief`. `lint --source` against the extract so numbers stay honest.
- Frontmatter: `kind: document` is enough for v1 if you pass `--publish`. Later, `kind: article` and `kind: paper` let the feed and `auto_publish` treat them like research. Do not invent those kinds until the happy path works.
- Cover: a generated title card is fine. Do not steal publisher art.
- Spoken intro should name the real work: "AI-narrated audio edition of *Harness engineering* by Ryan Lopopolo, OpenAI, February 2026," not "SASE research."

Put `#listen` in **sase-research-artifacts**, next to `#research/audio`. It is an xprompt, not a sase-core feature, and not a `sase-listen` subcommand. The xprompt may `uvx trafilatura` / `pdftotext` / `sase-listen` at runtime, same as `#research/audio` already shells out to `sase-listen`.

### What not to build in v1

- PDF layout models
- Two-host NotebookLM mode (keep as a later optional `#audio_overview` if you still want it; June 2026 research covered that)
- Reading-list batch queue
- A second RSS feed
- Citation-skipping verbatim engine
- Changes to `sase-core`

### Phase 0 — this weekend, no code

Unblocks the actual walk.

1. Close out `sase_listen_antennapod_setup.md`: billing or OpenAI narrator, rotate the leaked feed token into `pass`, serve `:8443` on the tailnet, subscribe in AntennaPod, delete the tone-engine placeholder.
2. Hand-convert the three HTML "evening" items:

```bash
uvx trafilatura -u 'https://openai.com/index/harness-engineering/' \
  --markdown -o /tmp/harness.md
sase-listen render /tmp/harness.md --dry-run    # minutes, chunks, $
sase-listen render /tmp/harness.md --publish
```

Repeat for the two Anthropic posts and the METR note. Listen to one on a walk. If trafilatura returns a stub, retry through `https://r.jina.ai/` + the URL.

3. One paper, as an edition, not a transcription: fetch `https://arxiv.org/html/2511.04427`, save markdown, run `sase-listen guide --edition brief`, write (or have an agent write) a lint-clean script, render, publish. Confirm the 42% / 281% / 24-point-gap class of numbers survive `lint --source`.

If Phase 0 is not pleasant in AntennaPod, stop. The rest of the work will not fix a feed or a voice you do not want to hear.

### Phase 1 — `#listen` for URLs (articles)

Xprompt + a short fetch helper. No `sase-listen` source change. Articles only. `--publish` on `kind: document`.

### Phase 2 — papers

`arxiv:` and PDF paths. Default `brief`. Reuse the `#research/audio` write → lint → render → `sase artifact create` loop, pointed at the extract instead of a research report. Narration scripts live beside the extract in the listen library, not in git.

### Phase 3 — only after you are actually listening

- `kind: article` / `kind: paper` and auto-publish
- Optional `sase-listen fetch URL` convenience command (HTML only, trafilatura extra)
- A queue that reads a reading-list Markdown and enqueues the **picks**, not every companion
- Optional `digest` edition (~2 min/item) for a stack of honorable mentions
- Marker as an opt-in PDF backend if pdftotext extracts are too lossy for lint

### Cost and volume

Same TTS meter as research episodes. Field notes: a linted ~11 min research edition was about **$0.15** on Gemini Flash TTS. A 4-minute brief paper is a few cents. A 152-minute verbatim CMU paper would be ~$1.50 and unlistenable — another reason the edition is the product.

How much you can walk still dominates money. A week of commuting might absorb two articles and two briefs. Generate against that budget.

---

## Is this a good idea?

Yes, with the adjustments above.

Walking time is wasted on a reading list that is 80% PDFs you will not open on a phone. The HTML posts (#1, #2, #6, the Fowler and Spotify companions) are exactly the thing a private podcast feed is for. The papers become useful on a walk only as **first-pass editions** that tell you whether to sit down with the PDF.

I would not build a paper-verbatim product. I would not switch commute listening to NotebookLM. I would not wait for a perfect PDF parser. I would listen to the OpenAI post in AntennaPod this week, then decide whether `#listen` is worth a bead.

---

## Recommended decision

1. **Keep `sase-listen` as the renderer and AntennaPod as the player.**
2. **Add ingest in front of it**, as `#listen` in sase-research-artifacts, not as PDF support inside `sase-listen`.
3. **Articles:** cleaned verbatim (trafilatura → `sase-listen script` → render).
4. **Papers:** agent `brief` edition from arXiv HTML or `pdftotext`, linted against the extract.
5. **Do Phase 0 by hand first.** If the three HTML evening items are not something you replay, do not automate.

---

## Sources

- Reading list: `research:202609/sase_paper_followup_reading_list/sase_paper_followup_reading_list.md` (URL census this turn: 48 URLs, 38 arXiv IDs, 9 industry HTML).
- `sase-listen` linked checkout: `README.md`, `docs/cli.md`, `docs/narration-scripts.md`, `docs/sase-integration.md`, `docs/podcast-feed.md`, `docs/field-notes.md`, `src/sase_listen/pipeline.py` (`load_source`, `read_artifact_ref`), `src/sase_listen/normalize/normalizer.py`.
- `#research/audio`: `sase-research-artifacts` `xprompts/research_audio.md`.
- Prior SASE research: `research:202610/commute_audio_from_markdown/commute_audio_from_markdown.md`, `research:202610/sase_listen_antennapod_setup.md`, `research:202610/sase_listen_what_you_get/sase_listen_what_you_get.md`, `research:202606/sase_audio_generation_consolidated.md`.
- Live fetches this turn: OpenAI harness-engineering HTML; METR 2026-03-10 note (~4.8k words page text); arXiv HTML `2511.04427` (~22.8k words, 245 citation-like hits).
- arXiv HTML: Ginev et al., *Scaling Accessible Mathematics on arXiv* (arXiv:2605.16562); ar5iv labs (sources through Aug 2026).
- HTML extraction: Trafilatura 2.3.0; 2026 comparisons of Trafilatura vs Readability vs Newspaper4k vs Jina ReaderLM.
- PDF→Markdown: 2026 Marker / MinerU / Docling / PyMuPDF4LLM comparisons (olmOCR-bench Marker 2 balanced 76.0; pdfmarkdown.app 9-tool test).
- Paper-to-audio products: Audemic, Listening.com, Speechify, ResearchBunny, ResearchPod, NotebookLM Audio Overviews, Google Illuminate.
- PaperWave: Yahagi et al., arXiv:2410.15023 / CHI EA 2025, DOI 10.1145/3706599.3706664.
- AntennaPod 3.12.x: subscribe-by-RSS, Podcasting 2.0 JSON chapters, "Add local folder" as a virtual podcast (since 2.x).
- Local machine this turn: `sase-listen` on PATH; `pandoc` and `pdftotext` on PATH; trafilatura / marker / docling **not** installed.
