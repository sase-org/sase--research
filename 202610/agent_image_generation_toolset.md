# Image models paint, code writes the words

**Bottom line:** standardize on one generator and a small deterministic kit, and teach both with a short skill. The generator is the official OpenAI CLI (`openai` 1.38.0) calling **`gpt-image-2.5-flare` with `--model`, `--quality`, and `--size` always passed explicitly**. As of 2026-10-07 that model family tops every text-to-image, text-rendering, and image-editing leaderboard, and it supports transparent backgrounds natively. Google's **Nano Banana 2.1** through `gemini-api` is the cheaper second opinion, not a co-default. Everything that has to be exact (labels, numbers, arrows, layout) stays in code: your proven pipeline of a no-text GPT background with ImageMagick labels for house infographics, **D2 0.9.0** for architecture diagrams, HTML/CSS screenshotted by **Playwright** for bespoke layouts, and Typst, already on athena, for print. A thin finishing and verification layer (`resvg`, `oxipng`, `tesseract`, `magick identify/compare`) closes the loop. The ChatGPT report got the backbone right: Playwright, D2, the OpenAI CLI, and the Flare/Sunburst model names all check out. But it promoted AntV Infographic and Sharp too far, left out Typst, ImageMagick's real role, and any way to verify output, and understated what ComfyUI costs on a shared box that is already swapping, runs driver 550, and would expose an unauthenticated port. Two practical surprises: apollo runs **Ubuntu 24.04, not Debian**, and its apt ImageMagick is still 6.9.12; and **no image API key reaches any agent yet**, so step one is an `OPENAI_API_KEY` in the environment SASE agents actually inherit.

_Checked 2026-10-09 · athena: Debian 13.7, RTX 3080 Ti, driver 550, ImageMagick 7.1.1-43 · apollo: Ubuntu 24.04.3, checked live over SSH · MacBook: chip and RAM unknown · model IDs, prices, and versions are dated and change monthly_

---

## Where the earlier ChatGPT report stands

The 2026-10-08 report was mostly accurate on facts but tiered several tools wrongly. Every claim it made was re-checked against package registries, release notes, vendor docs, or a local checkout.

| ChatGPT claim | Verdict | What this report does instead |
|---|---|---|
| Playwright CLI (`@playwright/cli`) plus its skills is "the first thing I would install" | Facts verified: v0.1.22 (2026-09-28), headless, screenshot/eval/pdf | **Departs.** The core renderer is Playwright's stateless `playwright screenshot`. The agent CLI moves to add-when-needed, because it shares one default browser session across agents, blocks `file://` by default, and is pre-1.0. |
| AntV Infographic: ~200 templates, MIT, Claude/Codex skills, browser-free `renderToString` | **Partly true.** The features exist, but SSR pulls fonts and icons from remote services and defaults to a CJK font | **Departs.** Skip for now. |
| D2 v0.9.0 bundles open-source TALA and exports PNG/GIF/PDF/PPTX natively | Verified. That the PDF is raster is inferred from the docs. | **Agrees.** Core, with TALA seeds pinned and SVG kept as the vector source. |
| Mermaid CLI renders SVG/PNG/PDF and handles Markdown | Verified, but v12.0.0 (2026-09-24) changed flags, and athena's copy is 11.4.2 | **Corrects.** Prefer inline Mermaid; upgrade `mmdc` only after auditing scripts. |
| OpenAI CLI with Flare for everyday work and Sunburst for precise edits; keeps existing files | Verified | **Agrees, with corrections.** The CLI's own default is Sunburst at automatic quality, and `go install` needs Go ≥ 1.26, so always pass flags and use the `.deb` on Linux. |
| Codex built-in `$imagegen` bills against plan limits | Verified. It also uses gpt-image-2 (not 2.5), burns limits 3–5× faster, and takes no size or quality parameters | **Narrows.** Use it for in-Codex drafts only. |
| Google's `gemini-api-cli` is experimental | Verified, and it now has an `image` command for Nano Banana 2.1 | **Agrees.** Add-when-needed second backend. |
| Sharp for conversion and finishing | Verified (prebuilt binaries, no system libvips) | **Departs.** Skip; ImageMagick already does this with better text and inspection. |
| Altair + vl-convert, no browser or Node | Verified | **Agrees.** Add-when-needed for data charts. |
| ComfyUI + comfy-cli optional for local generation | Verified (JSON envelope, skills, MCP, `COMFY_LOCAL_URL`) | **Agrees, with large caveats.** athena only, on demand, never network-exposed. |
| pen.dev, draw.io, and Satori as optional extras | pen.dev requires login to export; draw.io and Satori verified | **Skip all three.** |
| _Not mentioned_ | — | Typst, ImageMagick labels, OCR and diff verification, resvg, oxipng, rembg's license trap, Nano Banana 2.1, sidecars, timeouts |

## GPT Image 2.5 through the official CLI should be the one generator

OpenAI shipped **`gpt-image-2.5-flare`** ("fast, high-quality everyday image generation") and **`gpt-image-2.5-sunburst`** ("where editing precision matters most") in the API on 2026-09-08. Both add `xhigh` and `max` quality, custom sizes up to 3840 px per edge, and **reliable native transparency** ([OpenAI image guide](https://developers.openai.com/api/docs/guides/image-generation); [model page](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst)). Independent boards agree they lead. On Arena's 2026-10-07 text-rendering board, Sunburst is #1 at 1472, Flare #2 at 1433, and gpt-image-2 #3, with Nano Banana 2.1 fifth at 1363 ([Arena text rendering](https://arena.ai/leaderboard/text-to-image/text-rendering)). Artificial Analysis ranks the same three OpenAI models first on text-to-image and puts Sunburst and Flare first and second on editing ([AA text-to-image](https://artificialanalysis.ai/image/leaderboard/text-to-image); [AA editing](https://artificialanalysis.ai/image/leaderboard/editing)). The ratings for 2.5 and Nano Banana 2.1 are still marked preliminary, so the order among close neighbors could shift.

| Model (ID) | Arena text rendering, 2026-10-07 | AA text-to-image | Price (2026-10-09) | Native alpha | Agent CLI |
|---|---|---|---|---|---|
| `gpt-image-2.5-sunburst` | #1 (1472) | #1 (1198, max) | $30/M image-output tokens; ≈ $0.21 per 1024² at `max` | Yes | `openai` |
| `gpt-image-2.5-flare` | #2 (1433) | #2 (1191, max) | Same token rate; no official per-image table | Yes | `openai` |
| `gpt-image-2` | #3 (1425) | #3 (1172, high) | $0.006 / $0.053 / $0.211 (low/med/high, 1024²) | **No, since ~2026-10-01** | `openai`, Codex built-in |
| `gemini-nano-banana-2.1` (GA 2026-10-06) | #5 (1363, prelim.) | #4 (1160) | $0.0336 (1K) / $0.0504 (2K) / $0.113 (4K) | No | `gemini-api` |
| `gemini-3-pro-image` (Nano Banana Pro) | #15 | #12 (1102) | $0.134 (1K/2K) | No | `gemini-api` |
| Recraft V4.1 vector | — | #28 (Utility) | $0.08, returns real SVG | — | MCP only |
| Best local open model, Qwen-Image-2.1 | — | 1035 | Free, but research license | RGBA | ComfyUI |

Sources for the table: [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [Recraft pricing](https://www.recraft.ai/docs/api-reference/pricing), and the two leaderboards above.

Price is the least settled number. OpenAI bills 2.5 by token at the same rates as gpt-image-2, and the model page says the calculator "does not estimate GPT Image 2.5 usage" ([model page](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst)). Artificial Analysis lists both 2.5 models at **$210.7 per 1,000 images at `max`**, the same as gpt-image-2 at `high`. One third-party estimate puts 2.5 `high` at about **$0.053** for a 1024² image ([tokencost.app](https://tokencost.app/blog/gpt-image-2-5-pricing-cost-per-image)). That fits a forum report that the quality ladder was "remapped to five options at the same cost" ([OpenAI community](https://community.openai.com/t/is-transparent-background-support-broken-in-gpt-image-2/1402707)). Treat these per-image figures as unverified and check the usage dashboard after the first batch. The direction is clear, though: Flare at `low` for drafts and `high` for finals should cost less than the gpt-image-2 `high` calls your existing images probably used.

The **official CLI** is the right shared interface for Claude, Codex, Gemini, and SASE scripts. `openai/openai-cli` is OpenAI's Go client for the whole REST API, released almost daily, at **v1.38.0 (2026-10-08)**. `openai images generate` and `openai images edit` save files, print every saved path, and **never overwrite**: collisions get a `-2` suffix ([OpenAI CLI reference](https://developers.openai.com/api/reference/cli); [openai-cli docs/image-generation-saving.md](https://github.com/openai/openai-cli/blob/main/docs/image-generation-saving.md)). A local checkout confirms `--prompt @file`, a repeatable `--image`, `--mask`, `--background`, `--size`, `--quality`, `--name`, and `--output-dir`, which "must already exist". It also shows two traps. **With no model given, the CLI requests `gpt-image-2.5-sunburst` with automatic size, quality, and background.** And running `openai images generate` with no flags in a terminal opens an interactive picker that an agent with a PTY could hang on. The skill therefore makes every flag explicit. `go install` needs Go ≥ 1.26 (the repo's `go.mod` says `go 1.26.0`), so on Linux install the `.deb` package from the release. GoReleaser builds it into `/usr/bin` with a man page. On the Mac, `openai` is a Homebrew cask in `openai/tools`.

Transparency is now a model-choice issue. gpt-image-2 has rejected `background=transparent` since about 2026-10-01 ("Transparent background is not supported for this model"), and the 2.5 models support it with PNG or WebP ([OpenAI community thread](https://community.openai.com/t/is-transparent-background-support-broken-in-gpt-image-2/1402707); [OpenAI image guide](https://developers.openai.com/api/docs/guides/image-generation)). OpenAI's own Codex `$imagegen` skill still uses a chroma-key workaround because its fallback script defaults to gpt-image-2. That is a live example of why skills should not hardcode model IDs ([Codex imagegen skill](https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/imagegen)).

**Codex's built-in generator is a convenience, not the default.** It uses gpt-image-2. On a ChatGPT login it "use[s] included limits 3–5x faster", it is unavailable on the Free plan, and **API pricing applies instead if `OPENAI_API_KEY` is set** ([Codex pricing](https://learn.chatgpt.com/docs/pricing); [Codex image generation](https://learn.chatgpt.com/docs/image-generation)). It takes no size, quality, or transparency parameters, and it writes to `$CODEX_HOME/generated_images/`. This matters for SASE today. The research swarm's `#research/image` prompt is ten lines long and names no tool. Its `@image` alias round-robins across Codex, Grok, and Antigravity Gemini (sase-research-artifacts @ `555a0ad`, `xprompts/research_image.md` and `default_config.yml`), so each infographic depends on whatever generator that provider's harness has built in. Once a key and the CLI exist on apollo, where swarms launch, the `/image` skill gives that pool one consistent path and lets Claude join it.

**Google is the second backend, not a co-default.** Nano Banana 2.1 (`gemini-nano-banana-2.1`) went GA on **2026-10-06** at **$0.0336 per 1K image**, half the price of Nano Banana 2 ([Gemini image docs](https://ai.google.dev/gemini-api/docs/image-generation); [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)). Imagen 4 was shut down on 2026-08-17, and every `*-preview` image ID died on 2026-06-25 ([Gemini deprecations](https://ai.google.dev/gemini-api/docs/deprecations)). Two consequences follow. The Gemini CLI `nanobanana` extension, last committed 2026-03-06, still defaults to a dead model ([nanobanana](https://github.com/gemini-cli-extensions/nanobanana)). And `gemini-api-cli` v0.4.1 (2026-10-08) is now the clean path: `gemini-api image "<prompt>" --out f.png` defaults to Nano Banana 2.1, even though its README still says "not yet ready for production use" ([gemini-api-cli](https://github.com/google-gemini/gemini-api-cli)). Nano Banana has **no free API tier for image output, no alpha channel, a SynthID watermark on every image, and one image per call**. Use it for a second opinion, for multi-reference composition (up to 10 object references on 2.1), or when OpenAI is down. For a single-key fallback across vendors, OpenRouter's `/api/v1/images` adds no inference markup, only a 5.5% fee when buying credits ([OpenRouter comparison](https://openrouter.ai/blog/insights/image-generation-models-compared/); [OpenRouter FAQ](https://openrouter.ai/docs/faq)). Recraft V4.1's vector models are the only mainstream API that returns real SVG, at $0.08 each. FLUX, Ideogram, fal, Replicate, and Simon Willison's `llm` (which has no image output as of 0.36) add nothing to this setup.

## Exact words belong to code, which is what your workflow already does

Even the 2.5-era OpenAI guide still lists the limitation: "the model can still struggle with precise text placement and clarity" and "may have difficulty placing elements precisely in structured or layout-sensitive compositions" ([OpenAI image guide](https://developers.openai.com/api/docs/guides/image-generation)). Google says the same about Nano Banana: "Small text, fine details, and spelling may not always be accurate" ([Google](https://blog.google/products/gemini/prompting-tips-nano-banana-pro/)). Research prototypes such as DiagrammerGPT render labels separately because text-to-image models "produce unreadable text labels" ([arXiv 2310.12128](https://arxiv.org/pdf/2310.12128)). The best counterpoint is GDELT's experiments: Nano Banana Pro's infographic text was "nearly flawless" at 2K–4K, yet asking it to translate the text changed the whole layout ([GDELT](https://blog.gdeltproject.org/addressing-the-text-rendering-translation-issues-of-our-nano-banana-pro-experiments-by-changing-the-resolution-prompt/)). Arena's text-rendering scores measure human preference, not character-exact correctness on twelve small stage chips. Your **no-text background plus deterministic labels** is therefore the right default for documentation, not a workaround to retire. OpenAI's own hero-image templates default to `no text; no logos; no watermark; leave room for UI` ([Codex imagegen sample prompts](https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/imagegen)).

| Situation | Who writes the text |
|---|---|
| Doc diagrams, four or more labels, small type, numbers, exact project terms, labels likely to change | **Code.** A no-text background plus an ImageMagick or SVG overlay, or no image model at all (D2, HTML, Typst) |
| One or two large, stylized strings that are part of the art (poster title, mockup UI) | **The model**, verbatim, at `medium` or `high`, then OCR-checked. Fall back to compositing on any mismatch. |
| Pure illustration or atmosphere | **Nobody.** "No text, no letters, no logos, no watermark." |

Three upgrades make the existing pipeline sturdier without changing it. First, **request exact 16:9 sizes the 2.5 API accepts**. Custom sizes must be multiples of 16 with an aspect ratio no wider than 3:1, and anything above 2560×1440 is experimental, so use **1536×864 for drafts and 2048×1152 for finals**. Second, **reserve label zones in the prompt** ("leave the left third calm and low-detail for labels") and composite labels at the final resolution. Third, **keep editable sources**: the unlabeled `*.base.png` and the label layer (an SVG or the exact `magick` command in the `.prompt.md` "Required Post-Processing Notes"), so a stale label like `Stop hook` can be fixed without spending a generation. Your critiques of the commit-workflow image show how often that happens.

ImageMagick stays the label tool, and tests on athena turned up four details the skill has to encode. Debian's policy denies `@*` path reads, so **`caption:@file.txt` and `caption:@-` fail, and label text that begins with `@` is read as a file name**. That matters for labels like `@research:` refs, so pass text as an argument and route `@`-prefixed labels through an SVG layer ([ImageMagick security policy](https://imagemagick.org/security-policy/)). A PNG built from `xc:` with `-annotate` came out **16-bit** until `-depth 8` was added. `caption:` with `-size WxH` and no `-pointsize` auto-fits, and `%[caption:pointsize]` reports the size it chose. An `-annotate`d "Exact Label 42" read back exactly with `tesseract --psm 7`. Pass fonts **by file path**. Homebrew's plain `imagemagick` has no fontconfig or pango, and **`imagemagick-full` is keg-only**, so the Mac needs it prepended to `PATH`. Watch out that `brew install vips` pulls in the plain formula, which would win on `PATH` otherwise ([imagemagick-full formula](https://formulae.brew.sh/formula/imagemagick-full)). Finally, Debian's ImageMagick rasterizes SVG with its own internal MSVG renderer, and **resvg** passes 89% of the SVG text-category tests where librsvg passes 45% ([resvg support table](https://linebender.org/resvg-test-suite/svg-support-table.html)). Any SVG label layer should go through `resvg --skip-system-fonts --use-fonts-dir`, so glyphs match on every host.

```bash
FONT=$(fc-match -f '%{file}' 'Inter:style=Bold')   # athena: /usr/share/fonts/opentype/inter/Inter-Bold.otf
magick base.png \
  \( -size 1100x220 -background none -fill '#1f2937' -font "$FONT" -gravity center caption:"$LABEL" \) \
  -gravity northwest -geometry +120+80 -composite -depth 8 labeled.png
```

## D2, Playwright, and Typst cover the layout work AntV promised

**D2 0.9.0 is the strongest single-binary diagram tool, and it now needs nothing else.** The 2026-09-07 release says "TALA is now open source and bundled with D2", adds "PNG, GIF, PDF, and PPTX with the built-in renderer", and makes SVG rendering about 10× faster ([D2 v0.9.0](https://github.com/d2lang/d2/releases/tag/v0.9.0)). The docs say "PNG exports have no external dependencies", whereas 0.8.2 still prompted for a Chromium download ([D2 exports](https://d2lang.com/tour/exports/)). TALA is MPL-2.0 and came out of Terrastruct's shutdown, with D2 moving to nonprofit stewardship under Hack Club. Its search is randomized (3 seeds by default), and adding one node can reorganize much of a diagram ([runtimewire](https://runtimewire.com/article/terrastruct-open-sources-tala-alexander-wang-winds-down-business)). Agents should therefore pin `--tala-seeds` or use `--layout=elk`, so re-renders stay stable in git diffs. PDF export is built from PNG pages, so keep the `.d2` and SVG as the vector source.

**Mermaid needs no rendering when GitHub is the destination**, since GitHub renders fenced blocks natively. For other destinations, `mmdc` v12.0.0 (2026-09-24) replaced `--width/--height` with `--size`, removed `--pdfFit`, requires Node ≥ 22.13, and changed the default themes ([mermaid-cli releases](https://github.com/mermaid-js/mermaid-cli/releases)). athena's `/usr/local/bin/mmdc` is 11.4.2 from 2024-12. Upgrade it only after grepping your scripts and skills for the removed flags.

**HTML/CSS in a headless browser is the most fluent layout engine an agent has**, and practitioners agree it beats image models for anything with real text and numbers ([phalkmin.me](https://phalkmin.me/en/blog/claude-code-infographics/)). The ChatGPT report chose Microsoft's agent-facing `@playwright/cli`. It is real and well documented: `install --skills`, `screenshot [ref]`, `--hires`, `eval`, and `pdf`, headless by default, and its docs make a credible case that a CLI plus a skill costs fewer tokens than Playwright MCP ([Playwright agent CLI](https://playwright.dev/agent-cli/introduction)). But it is a poor fit for producing images. It keeps a **stateful default browser session that concurrent agents would share** unless each passes `-s=<name>`. The playwright-core 1.64.0 bundle it runs on **throws `Access to "file:" protocol is blocked`** unless `allowUnrestrictedFileAccess` is set. It is pre-1.0, with releases every one to four weeks ([npm @playwright/cli](https://www.npmjs.com/package/@playwright/cli)). Plain Playwright's built-in `playwright screenshot <url> <file>` is stateless, accepts `--viewport-size`, `--full-page`, and `--wait-for-timeout` (read from the same 1.64.0 bundle), and installs its own Chromium on all three machines. It loads pages with an ordinary navigation, so `file://` artboards should work; that was not separately tested here. Make it the core renderer. On athena, the installed Chrome 155 one-liner is a verified zero-install fallback. Both browsers hit the same athena trap: under SASE's long agent `TMPDIR`, Chromium dies with **"Socket path too long"**, because Linux limits socket paths to 108 bytes and a typical agent TMPDIR alone is 73 characters ([Chromium bug](https://phabricator.wikimedia.org/T93330)). The fix is to prefix every browser call with a short `TMPDIR=$(mktemp -d /tmp/br.XXXX)`. That fix is verified for Chrome; for Playwright's Chromium the trap is assumed but untested.

**Typst is the omission that matters most.** It is already installed on athena (0.15.1), compiles straight to PNG, SVG, or PDF ([Typst PNG export](https://typst.app/docs/reference/png/)), and rendered a 1200×630-pt grid card cleanly in a local smoke test. It is the deterministic, offline answer for print one-pagers, PDF handouts, and cards whose bytes must not drift. The trade-off is that models know Typst less well than HTML, so examples in the skill's references would help.

**AntV Infographic drops to "skip".** Every feature the ChatGPT report named exists. But reading the v0.2.20 package source shows that `renderToString` runs on a linkedom DOM shim with a **hard 10-second timeout**, fetches its default font (Alibaba PuHuiTi, a CJK face) from `assets.antv.antgroup.com`, resolves icons through `weavefox.cn`, and prepends remote `<?xml-stylesheet?>` instructions that lightweight rasterizers ignore ([npm @antv/infographic](https://www.npmjs.com/package/@antv/infographic)). The official skill writes an HTML page that loads `@latest` from unpkg for a human to export by hand ([infographic-creator skill](https://github.com/antvis/Infographic/tree/main/skills/infographic-creator)). There has been only one release since early May (0.2.20, 2026-08-19), and the docs are Chinese-first. Its template catalog (lists, steps, timelines) also fits your architecture-style infographics worse than D2 plus your style brief does. **Sharp drops too.** It is excellent inside Node code, but ImageMagick is already installed, has better text and inspection, and the agent never needs a Node build step to resize a PNG ([sharp install](https://sharp.pixelplumbing.com/install/)). **Altair with vl-convert** is the right add-on when charts come from real data. It is self-contained, with no browser or Node, and runs with no install via `uv run --with "altair[save]"` ([Altair saving](https://altair-viz.github.io/user_guide/saving_charts.html)). Satori (no grid, superseded by Takumi), pen.dev (proprietary, login required to export, Node ≥ 22.19), draw.io (needs the Electron desktop app), the day-old official Excalidraw CLI, the public Kroki instance (it ships your source to a third party), and the archived wkhtmltoimage can all wait.

## Verification is a loop of looking, cropping, and reading back

All three agents can see local images: Claude Code through Read, Codex through `view_image`, and Gemini CLI when the file is named explicitly. **Claude cannot generate images at all**, so it needs the CLI ([Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)). The reviewer side shapes the loop. Claude 4.7+ sees up to a **2576 px long edge (about 4,784 visual tokens)**, older models 1568 px, at a cost of ⌈w/28⌉ × ⌈h/28⌉ tokens. Downscaling "might … make text less legible." So view a **display-size preview** (1000×563 costs about 756 tokens) plus **crops of every text region**, not the 2048×1152 original (about 3,108 tokens). Claude "does not parse or receive any metadata from images", so provenance checks have to be scripted.

The cheap, deterministic half of the loop is already installed on athena and was verified there. `magick identify -format '%wx%h %[channels] depth=%z'` asserts size, alpha, and bit depth. `magick compare -metric AE|SSIM` exits **0 when identical and 1 when different**, which makes it usable as a regression gate ([ImageMagick compare](https://usage.imagemagick.org/compare/)). `tesseract crop.png - --psm 7` read a composited label back character-exact ([tessdoc](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)). None of the vendor skills reviewed (Codex `$imagegen`, AntV, nanobanana, Anthropic's canvas-design) uses OCR. They all stop at "inspect and validate", so OCR is where the `/image` skill adds real rigor. Keep the critique pass separate: a fresh reviewer writing `.critique.md` plays the auditor role DiagrammerGPT relies on, and it is less biased than the agent that wrote the prompt.

Finishing tools earn their place one job at a time. **`oxipng -o 4 --strip safe --alpha`** shrinks PNGs losslessly. It is not packaged in Debian trixie, so install it with cargo or the upstream `.deb` ([oxipng](https://crates.io/crates/oxipng)). `pngquant` is the lossy step when size matters more than crisp text edges. Its exit codes 98 and 99 mean "keep the lossless file" ([pngquant(1)](https://manpages.debian.org/trixie/pngquant/pngquant.1.en.html)). OpenAI says ChatGPT, Codex, and API images carry **C2PA metadata plus a SynthID watermark** (from a search snippet; the help page returned 403), and Google says the same of Nano Banana. Compositing re-encodes the file and breaks or drops the manifest, while SynthID stays in the pixels. If provenance matters, `exiftool -jumbf:all -G3 -b -j -u -struct gen.png` records it before editing ([ExifTool JUMBF tags](https://exiftool.org/TagNames/Jpeg2000.html)). Otherwise, say "AI-generated background, labels added in code" in the sidecar and alt text. **`rembg`'s default model is now `bria-rmbg` (RMBG-2.0), whose weights are CC BY-NC 4.0**, so a bare `rembg i in out` silently uses a non-commercial model. Always pass `-m birefnet-general -dc`, which uses MIT weights and adds edge decontamination ([rembg](https://pypi.org/project/rembg/); [RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0)). With GPT Image 2.5's native transparency, rembg is only needed for cut-outs of images you already have. Upscaling is rarely needed now that 2.5 renders up to 3840 px. When it is, `upscayl-bin` (ncnn-vulkan, built 2025-12-07) runs headless on athena's GPU only with `env -u DISPLAY` and `-g 0`, because `vulkaninfo` failed under the forwarded X display and llvmpipe also appears as a device ([upscayl-ncnn releases](https://github.com/upscayl/upscayl-ncnn/releases)).

## Local generation on athena is a hobby tier, not a default

The quality gap is the first problem. On Artificial Analysis, the best open-weight model, **Qwen-Image-2.1 (1035), loses to GPT Image 2.5 (1198) about 72% of the time head to head**. The commercially usable models that fit 12 GB (Z-Image Turbo and FLUX.2 klein at 941) lose about 81% of the time ([AA open weights](https://artificialanalysis.ai/image/leaderboard/text-to-image?open-weights=true)). Qwen-Image-2.1 is also under a research license that bars commercial use ([HF Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1)). The commercially safe stack is Z-Image Turbo, FLUX.2 klein 4B, and Qwen-Image-Edit-2511, all Apache 2.0 ([Z-Image](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo); [FLUX.2 klein](https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence); [Qwen-Image-Edit-2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511)). No source measured any of them on a 3080 Ti. Estimates from neighboring cards put the 4-to-8-step models at a few seconds per 1024² image. With cloud images at roughly $0.03–$0.21 each, local only pays off for privacy, very high volume, or work that has no API key.

athena's own constraints make it worse. ComfyUI's documented Linux install uses CUDA 13.0 (`cu130`) PyTorch wheels, which need **driver ≥ 580**. athena runs **550.163.01**, so it would need cu128 wheels (an untested pairing) or a driver upgrade on a shared server ([ComfyUI manual install](https://docs.comfy.org/installation/manual_install); [CUDA 13.0 notes](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-toolkit-release-notes/index.html)). On 2026-10-09 athena had **17 GB of RAM available and 14 GB of swap in use**. Running the bigger models on 12 GB of VRAM means offloading 8B text encoders into exactly that RAM. ComfyUI's API also **has no authentication**. In March 2026 attackers hit more than 1,000 exposed instances by posting crafted workflows to `/prompt` and installing malicious nodes through ComfyUI-Manager ([Censys](https://censys.com/blog/comfyui-servers-cryptomining-proxy-botnet/)). CVE-2025-67303 allowed unauthenticated node installation until Manager v3.38 ([Tencent Xuanwu Lab](https://xlab.tencent.com/en/2026/01/06/xlab-26-001/)).

If a concrete need appears, the safe shape is on demand and private. Use a `uv` venv with cu128 torch, verified with `torch.cuda.is_available()`, plus `comfy-cli` ≥ 1.22, whose `--json` envelope, `run --wait`, `validate`, and `download` suit agents ([comfy-cli](https://docs.comfy.org/comfy-cli/getting-started)). Run it as a memory-capped systemd unit that is not enabled at boot, bound to `127.0.0.1`, and reached from apollo or the Mac with `ssh -L 8188:localhost:8188 athena`. Install only GGUF and Nunchaku custom nodes, and call `POST /free` after each batch. On the Mac, **mflux** (0.22.0, 2026-10-08) is the agent-friendly route, with one CLI per model. FLUX.2 klein 4B took about 31 s per 1024² image on an M1 Max and peaked at 14 GB of memory, or 7.2 GB with tiled decode ([mflux releases](https://github.com/mflux-community/mflux/releases); [mflux #817](https://github.com/mflux-community/mflux/issues/817)). The Mac is only online when its lid is open, so it is a personal tool, not a server. apollo has no GPU and only ever acts as a client.

## A light skill plus CLIs beats MCP for a single-turn, multi-provider fleet

The vendors' own guidance converges. Anthropic's skill rules load only a skill's name and description until it is needed, run scripts "without loading their full contents into context", and say to keep SKILL.md under 500 lines and "avoid time-sensitive information" ([Claude skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)). Playwright explains its CLI plus skills by saying they "avoid loading large tool schemas and verbose accessibility trees into the model context" ([playwright-cli README](https://github.com/microsoft/playwright-cli)). Anthropic measured code-API access to MCP tools cutting one workflow "from 150,000 tokens to 2,000" ([Anthropic engineering](https://www.anthropic.com/engineering/code-execution-with-mcp)). Images add another reason. An MCP tool that returns image bytes puts them into context and keeps resending them on later turns ([Claude vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)). A CLI writes a file, and the agent decides when to look and at what size. For SASE, which runs single-turn agents concurrently across Claude, Codex, Gemini, Grok, and Antigravity, one CLI on `PATH` plus one SKILL.md deploys the same way everywhere. If you adopt it, author it as a source template in `src/sase/macros/skills/` so `sase skill init` renders it for each provider.

The skill's shape comes from the best existing example, OpenAI's Codex `$imagegen` skill. Its description says when to use it and when not to ("better produced directly in SVG, HTML/CSS, or canvas"). It has a short decision tree, a labeled prompt schema (`Use case:`, `Asset type:`, `Primary request:` … `Avoid:`), which your sidecars already follow; "change only X; keep Y unchanged" for edits; never overwrite; and "iterate with a single targeted change, then re-check" ([Codex imagegen SKILL.md](https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/imagegen)). The prompting rules are consistent across OpenAI, Google, and BFL. Write a scene brief in sentences and lead with the intended use. Quote exact text and say it appears once. Set size and quality with parameters, not prose. Repeat the list of things to keep on every edit, and draft low before finalizing high ([OpenAI cookbook](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide); [Google Cloud](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana); [BFL FLUX.2](https://docs.bfl.ai/guides/prompting_guide_flux2)). The one disagreement is negatives. OpenAI's skill uses `Avoid:` lines, while Google and BFL want exclusions phrased positively. Model drift is the strongest argument for keeping IDs out of skill prose. In 2026 alone, OpenAI's default image model went from gpt-image-1.5 to gpt-image-2 to 2.5, and the `openai/skills` copy of imagegen still defaults to 1.5. So the skill names today's defaults once and tells agents how to check them.

The skill should stay light. If agents keep skipping sidecars or timeouts, move those steps into a small wrapper (for example `image gen --draft|--final`) that writes the `.prompt.md`, enforces its own 300-second timeout and no-overwrite rule, writes a preview, and runs a `doctor` check for keys. The research notes recommend exactly that once real usage shows where agents slip. Don't build it first.

## Conclusion

The hard part of agent image work is no longer generation. Every top model now produces usable art at a few cents an image. What fails is **checking the output and keeping it reproducible**: labels nobody OCR'd, files overwritten by a concurrent agent, prompts lost, and a 120-second shell timeout killing a two-minute generation. Your docs pipeline already has the most important property, because code owns the words. The toolset below mostly adds the verification and file hygiene around it, plus one explicit, flag-pinned generator that every provider can call. That is also why the ChatGPT report's emphasis on composition engines (AntV, Sharp, Satori) misses: those tools solve layout, which HTML, D2, and Typst already cover, while the gaps that actually cost time are verification, provenance, and keys.

Two operational facts decide whether any of this works. The key has to reach agents: no image key is set today, and a stale `GEMINI_API_KEY` frozen in `~/.sase/service/env` already broke a host-only workflow on 2026-10-05. OpenAI may also require Organization Verification before GPT Image calls succeed. And apollo, where research swarms and their `.image` agents launch, is the machine most in need of the core kit, yet it is also the one whose distro (Ubuntu 24.04) ships neither ImageMagick 7 nor resvg.

## Recommended toolset

Versions are as of 2026-10-09. "Installed" means verified present on that host today.

### Core: install now

| Tool (version) | Job | athena (Debian 13) | apollo (Ubuntu 24.04) | MacBook (Homebrew) |
|---|---|---|---|---|
| OpenAI CLI `openai` (1.38.0) | Generate and edit raster art (GPT Image 2.5) | Install `.deb` | Install `.deb` | Cask |
| ImageMagick 7 | Labels, compositing, crops, `identify`, `compare` | Installed (7.1.1-43) | **Add the IM7 AppImage** (apt has only 6.9.12) | `imagemagick-full`, first on PATH |
| tesseract | OCR read-back of labels | Installed (5.5.0, eng) | apt (5.3.4) | brew |
| D2 (0.9.0) | Architecture, workflow, and dependency diagrams | install.sh | install.sh | brew |
| Playwright (1.64.0) + Chromium | HTML/CSS to PNG via stateless `playwright screenshot` | npm (nvm Node 22.14) | npm (nvm Node 24.15, **not** `/usr/bin/node` 18) | npm (brew Node) |
| resvg (0.48.1) | SVG to PNG with pinned fonts | cargo | cargo | brew |
| oxipng (10.2.1) | Lossless PNG shrink for repos | cargo | cargo | brew |
| A pinned label font file (Inter 4.1, OFL) | Identical glyphs on all hosts | Commit it to the repo (e.g. `docs/images/fonts/`) | Comes with the repo (apt has Inter 4.0) | Comes with the repo |

Already present and kept on athena: Typst 0.15.1, Inkscape, `rsvg-convert`, ffmpeg, and Chrome 155 (the zero-install browser fallback).

**athena, Debian 13:**

```bash
# OpenAI CLI: official .deb (go install would need Go >= 1.26)
gh release download v1.38.0 -R openai/openai-cli -p '*amd64.deb' -D /tmp/openai-cli
sudo apt install /tmp/openai-cli/openai_*amd64.deb
openai images models --offline            # lists the image model IDs this CLI knows

# D2 0.9.0 with bundled TALA
curl -fsSL https://d2lang.com/install.sh | sh -s -- --dry-run
curl -fsSL https://d2lang.com/install.sh | sh -s --
d2 --version && d2 layout                 # 'tala' should be listed

# Playwright library CLI + its Chromium (Chrome's system deps are already present)
npm install -g playwright@1.64.0
playwright install chromium

# Finishing kit (cargo gives the same resvg/oxipng versions as Homebrew)
cargo install resvg oxipng

# Pin the label font in the repo you produce images for
mkdir -p docs/images/fonts && cp /usr/share/fonts/opentype/inter/Inter-{Bold,Regular}.otf docs/images/fonts/
```

**apollo, Ubuntu 24.04** (agents need nvm's Node on `PATH`; the system `/usr/bin/node` is 18.19):

```bash
gh release download v1.38.0 -R openai/openai-cli -p '*amd64.deb' -D /tmp/openai-cli
sudo apt install /tmp/openai-cli/openai_*amd64.deb tesseract-ocr libfuse2t64
curl -fsSL https://d2lang.com/install.sh | sh -s --
npm install -g playwright@1.64.0 && playwright install --with-deps chromium
cargo install resvg oxipng

# ImageMagick 7: Ubuntu 24.04 apt only offers 6.9.12, which has no `magick` binary.
# IM's portable AppImage. NOT tested on apollo for this report; confirm the URL on imagemagick.org/script/download.php.
curl -fsSL -o ~/.local/bin/magick https://imagemagick.org/archive/binaries/magick
chmod +x ~/.local/bin/magick && magick -version | head -1
# Fallback if the AppImage misbehaves: sudo apt install imagemagick   (IM6; use convert/identify/compare)
```

**MacBook, Homebrew:**

```bash
brew install openai/tools/openai
brew install d2 imagemagick-full tesseract resvg oxipng node
echo 'export PATH="$(brew --prefix imagemagick-full)/bin:$PATH"' >> ~/.zshrc   # keg-only; must win over plain imagemagick
npm install -g playwright@1.64.0 && playwright install chromium
magick -version | grep -i delegates      # should list fontconfig
```

**Keys, on every host.** Store the key once with `pass insert openai_api_key` and export `OPENAI_API_KEY` from the shell environment agents inherit. After changing it, make sure SASE's frozen service env (`~/.sase/service/env`) picks up the new value. Complete OpenAI's Organization Verification if the first call asks for it. Remember that a set `OPENAI_API_KEY` also switches Codex's built-in image generation from plan billing to API billing.

### Add when needed

| Tool | Add it when | Machines | Install (Linux / macOS) |
|---|---|---|---|
| `gemini-api` (v0.4.1), Nano Banana 2.1 | You want a second opinion, multi-reference composition, or OpenAI is down | All | `GOTOOLCHAIN=go1.26.8 go install github.com/google-gemini/gemini-api-cli/cmd/gemini-api@v0.4.1` (Mac: `brew install go` first). Needs a paid `GEMINI_API_KEY`. |
| Altair + vl-convert | Charts from real data | All | No install: `uv run --with "altair[save]" python chart.py` |
| Typst | PDF/print one-pagers off athena | apollo, Mac | `cargo install --locked typst-cli` / `brew install typst` |
| mermaid-cli 12 | Mermaid to an image outside GitHub | athena | First grep your scripts and skills for `--pdfFit` and `mmdc` calls using `-w`/`-H`, then `npm install -g @mermaid-js/mermaid-cli@12` |
| `@playwright/cli` (0.1.22) | Interactive inspection of live pages | All | `npm install -g @playwright/cli@0.1.22`. Use `-s=<run>` per agent; `file://` needs `PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS=true`. |
| rembg (2.0.85) | Cut-outs of existing images | All (CPU is fine) | `uv tool install --python 3.12 "rembg[cpu,cli]"`, always with `-m birefnet-general -dc` |
| exiftool | Recording C2PA provenance before compositing | All | `sudo apt install libimage-exiftool-perl` / `brew install exiftool` |
| pngquant | Lossy PNG when size beats crisp edges | All | `sudo apt install pngquant` / `brew install pngquant` |
| libvips | Batch resize or convert of many large images | athena, Mac | `sudo apt install libvips-tools` / `brew install vips` (then re-check that `magick` resolves to imagemagick-full) |
| upscayl-bin (20251207) | Upscaling an existing small raster | athena | Unzip `upscayl-bin-20251207-174704-linux.zip` from its GitHub release into its own directory; run with `env -u DISPLAY … -g 0` |
| vtracer, potrace, svgo | Raster-to-vector tracing and SVG cleanup | athena, Mac | `cargo install vtracer`, `sudo apt install potrace`, `npm i -g svgo` / `brew install potrace svgo` plus `cargo install vtracer` |
| Recraft V4.1 vector API | Native SVG icons or spot illustrations | Any (API) | Official MCP `https://mcp.recraft.ai/mcp`, or REST with a key |
| OpenRouter `/api/v1/images` | One key across vendors | Any (API) | `curl` with an OpenRouter key; check `/api/v1/images/models` for supported params |
| ComfyUI + comfy-cli | Private, bulk, or offline generation with Apache-licensed models | **athena only** | `uv venv` + cu128 torch + `uv pip install "comfy-cli>=1.22"`; bind to `127.0.0.1`, reach it via `ssh -L`, memory-capped systemd unit, not enabled at boot |
| mflux (0.22.0) | Offline generation on the Mac | Mac only | `uv tool install mflux` (add `--vae-tiling` on 16–24 GB Macs) |

### Skip

AntV Infographic (remote fonts and icons, CJK default, 0.x and quiet), **Sharp** as a standalone tool (ImageMagick covers it), Satori (no grid; Takumi if ever), pen.dev (proprietary, login to export), draw.io (unless humans must hand-edit the diagram), the one-day-old Excalidraw CLI, public Kroki (sends your source to a third party), wkhtmltoimage (archived), GraphicsMagick, ImageSorcery or ImageMagick MCP servers (OpenCV text, no real fonts), the `nanobanana` Gemini extension (defaults to a shut-down model), fal and Replicate CLIs, `llm` for images (no image output), FLUX and Ideogram APIs, `transparent-background` and `backgroundremover`, `dssim` (AGPL), chaiNNer, DiffusionKit, InvokeAI and SD.Next, and Codex's built-in generator as a scripted default.

## The `/image` skill

A complete SKILL.md. It names current defaults once and tells agents how to check them, so it does not age with model IDs.

````markdown
---
name: image
description: >-
  Generate, edit, compose, and verify image files from the shell: GPT Image art via the
  openai CLI, exact labels via ImageMagick, diagrams via D2, layouts via HTML/CSS and
  Playwright, print via Typst, charts via Altair. Use when a task needs a new or changed
  PNG/SVG/WebP (illustration, background, infographic, diagram image, cut-out) or a
  review of one. Do not use when an inline Mermaid block GitHub renders is enough, when
  the deliverable is HTML/UI code, or for real people's likenesses, logos, or trademarks.
---

# Image

Image models paint; code writes the words. Text beyond a short title, any number, and
any exact project term comes from code (D2, HTML, Typst, ImageMagick), never from the
image model. Follow `docs/images/infographic-style-brief.md` when the repo has one.

## 1. Pick the tool by job

| Job | Tool |
| --- | --- |
| Illustration, background, texture, hero art | `openai images generate` |
| Change part of an existing raster | `openai images edit` (always a new file) |
| Infographic with exact labels (house style) | no-text GPT background, then `magick` labels |
| Architecture / workflow / dependency diagram | `d2 --layout=elk in.d2 out.svg` (`tala` with seeds pinned) |
| Diagram inside GitHub-rendered Markdown | inline mermaid block; no image file |
| Bespoke layout, cards, comparison panels | HTML/CSS, then `playwright screenshot` |
| PDF or print one-pager | `typst compile page.typ page.pdf` |
| Chart from real data | `uv run --with "altair[save]" python chart.py` |
| SVG to PNG | `resvg --skip-system-fonts --use-fonts-dir <fonts> in.svg out.png` |
| Transparent cut-out | GPT Image 2.5 `--background transparent`; else `rembg` |
| Shrink a final PNG | `oxipng -o 4 --strip safe --alpha out.png` |

## 2. Generate

    RUN=$(mktemp -d "${TMPDIR:-/tmp}/image.XXXXXX")     # this run only; never shared
    cat > "$RUN/prompt.txt" <<'EOF'
    ...prompt from the template below...
    EOF
    timeout 300 openai images generate --prompt "@$RUN/prompt.txt" \
      --model gpt-image-2.5-flare --quality low --size 1536x864 \
      --output-dir "$RUN" --name draft-01 --inline off

- Defaults as of Oct 2026: `gpt-image-2.5-flare`; `low` for drafts, `high` at `2048x1152`
  for finals. `gpt-image-2.5-sunburst` with `xhigh`/`max` only for hero art or hard edits.
  Sizes must be multiples of 16, aspect at most 3:1.
- IDs go stale. Check first: `openai images models`, `openai images generate --help`.
- Always pass `--prompt --model --quality --size`. No flags opens an interactive picker;
  no model means Sunburst at automatic quality.
- Second opinion or OpenAI outage: `gemini-api image "<prompt>" --out "$RUN/alt-01.png"`
  (defaults to Nano Banana 2.1; see `gemini-api image --help`; experimental CLI, no
  alpha, SynthID watermark). In Codex with
  no API key, built-in drafts are fine; copy them from `$CODEX_HOME/generated_images/`.

Prompt template. Use only the lines that help, and write sentences, not tag lists:

    Use case: infographic-diagram | illustration-story | stylized-concept | ...
    Asset type: <what and where, e.g. 16:9 infographic for docs/foo.md>
    Primary request: <one or two sentences>
    Subject: <main elements, most important first>
    Style/medium: <from the style brief>
    Composition/framing: <flow direction; empty zones reserved for labels, and where>
    Color palette: <colors tied to named objects; hex where it matters>
    Text (verbatim): none, labels are composited later  [or "EXACT", once, font, place]
    Constraints: no text, no letters, no logos, no watermark
    Avoid: <failure modes seen in the previous draft>

Use flags, not prose, for size, quality, and background. Never add people, brands,
slogans, or named artists' styles that the request did not imply.

## 3. Edit

    timeout 300 openai images edit --image base.png [--image ref.png] [--mask m.png] \
      --prompt "@$RUN/edit.txt" --model gpt-image-2.5-sunburst --quality high \
      --output-dir "$RUN" --name edit-01 --inline off

- Name inputs by index and role: "Image 1: edit target. Image 2: style reference only."
- Write "Change only X. Keep Y unchanged." and repeat the whole keep-list on every pass.
- One change per iteration. Masks guide the model and are not pixel-exact (same size
  and format as image 1, with alpha).
- Wrong or stale labels: rerun the overlay from source. Never ask the model to fix text.

## 4. Exact labels and code-native renders

    FONT=$(fc-match -f '%{file}' 'Inter:style=Bold')   # or the repo's pinned font file
    magick "$RUN/base.png" \
      \( -size 1100x220 -background none -fill '#1f2937' -font "$FONT" \
         -gravity center caption:"$LABEL" \) \
      -gravity northwest -geometry +120+80 -composite -depth 8 "$RUN/labeled.png"
    TMPDIR=$(mktemp -d /tmp/br.XXXX) playwright screenshot --viewport-size "1600, 900" \
      --wait-for-timeout 1000 "file://$RUN/card.html" "$RUN/card.png"

Resize the background first, then label at final size. Past ~10 labels or chips, write
`labels.svg`, rasterize it with resvg and the same font dir, composite, keep the SVG.

## 5. Verify before you call it done

1. `magick identify -format '%wx%h %[channels] depth=%z\n' out.png` matches the spec.
2. Open a display-size copy, not the original (`magick out.png -resize 1000x
   "$RUN/preview.png"`), then a crop of every text region at 200%
   (`magick out.png -crop WxH+X+Y +repage -resize 200% "$RUN/crop-1.png"`).
3. Read each crop back with `tesseract "$RUN/crop-1.png" - --psm 7` and diff against the
   exact label list. OCR of the label layer alone is the strict check.
4. Walk the spec: subject, composition, empty zones, spelling, stray text, logos,
   watermarks, palette, artifacts.
5. Fix one thing, then recheck. After ~3 drafts, change strategy (simplify, composite
   more text, switch tool) instead of rerolling.
6. Finalize at `high` only after a `low` draft passes. Record the review in
   `<name>.critique.md`, ideally written by a fresh reviewer.

## 6. Files

- Work only in `$RUN`. Never write into another agent's run dir or `~/Downloads`.
- Never overwrite. Test `[ -e "$DST" ]` before promoting; on a collision use `-v2` or
  stop and report it.
- Beside each promoted PNG, write `<name>.prompt.md`: frontmatter `pdf: false`, then
  `## Target` (doc, insertion point, image path, alt text), `## Final GPT Image Prompt`,
  `## Generation` (CLI and version, model, size, quality, background, date, inputs), and
  `## Required Post-Processing Notes` (the exact overlay commands).
- Keep editable sources next to it: `<name>.base.png` (unlabeled), `labels.svg` or the
  overlay script, and any `.d2`, `.html`, `.typ`, or chart script. Run `oxipng` on finals.

## 7. Cost

- Draft at `low` and a small size; finalize at `high`; `--count 1` unless asked. Never
  regenerate to fix text; fix the overlay.
- Sunburst, `xhigh`, and `max` need a stated reason (`max` ran about $0.21 per 1024²
  image in Oct 2026). 2.5 is token-billed with no official per-image table: point to
  the usage dashboard instead of quoting prices.

## 8. Gotchas

- No `OPENAI_API_KEY`: stop and say so. Never ask anyone to paste a key into chat.
- Generation can take ~2 minutes. Wrap calls in `timeout 300` and give your shell tool
  at least 300000 ms (Claude Code's Bash default is 120 s). Batch via `/sase_monitor`.
- Browsers under a long agent TMPDIR die with "Socket path too long". Prefix every
  browser call with `TMPDIR=$(mktemp -d /tmp/br.XXXX)`.
- ImageMagick reads label text that starts with `@` as a file name, and Debian's policy
  blocks it (`caption:@file` too). Put such labels in the SVG layer. Always add
  `-depth 8`, or the PNG comes out 16-bit. Rasterize SVG with resvg, not ImageMagick.
  On macOS, `imagemagick-full` must come first on PATH. Only `convert` present = IM6.
- rembg's default model (`bria-rmbg`) is CC BY-NC. Always run
  `rembg i -m birefnet-general -dc in.png out.png`.
- Image models still misspell small or dense text; OCR anything a model rendered.
- `gpt-image-2` rejects transparent backgrounds; use a 2.5 model. Nano Banana has no
  alpha: generate on a flat chroma color and key it out.
- Vulkan tools over SSH (upscalers) need `env -u DISPLAY` and `-g 0`.
- Generated images carry C2PA and SynthID. Compositing drops C2PA, so the sidecar and
  alt text should say "AI-generated background, labels added in code".

Report the final paths, the final prompt, model/quality/size, and what verification found.
````
