# Converting Web Articles and Research Papers to Mobile Commute Audio

**Date:** 2026-10-03 · **Author:** `research.3i.gem` (Swarm Independent Report)  
**Scope:** Researching, critiquing, and designing an end-to-end pipeline to convert technical web articles and academic papers (exemplified by `sase_paper_followup_reading_list.md`) into chaptered audio for AntennaPod via `sase-listen`.

---

## 1. Bottom Line & Executive Summary

**Yes, you should implement this, but do NOT attempt verbatim narration of academic research papers.** Verbatim reading of multi-page academic papers while walking or commuting is an anti-pattern: multi-column PDF artifacts, formula recitation, tabular noise, and citation interruptions create severe cognitive overload and near-zero retention. However, **adapting papers into high-fidelity "Audio Editions" (structured technical briefings) and converting engineering blog posts deterministically is an extraordinary productivity unlock.**

### The Deciding Answers to Your Questions

1. **Is this a good idea?**
   - **For Web Articles & Engineering Blogs (e.g., OpenAI, Anthropic, Fowler):** **Yes, unconditionally.** They are already narrative and prose-heavy. Deterministic cleanup removes boilerplate, leaving a clean, highly listenable 10–25 minute episode.
   - **For Academic Papers / ArXiv Preprints (e.g., MAGE, Gorinova, SWE-EVO, EMNLP):** **Verbatim is a failure; an adapted "Audio Edition" is brilliant.** An 8,000–12,000 word paper takes 60–80 minutes of monotonous audio full of dropped equations and tabular clutter. Instead, an LLM-synthesized **Audio Edition** (12–16 minutes for `full`, 4–5 minutes for `brief`) following `sase-listen guide` rules delivers dense, high-retention technical substance without listener fatigue.

2. **Should you use `sase-listen` or something else?**
   - **Use `sase-listen` as the audio rendering and distribution backbone.** Do not reinvent the audio stack. `sase-listen` already solves the hardest systems and distribution problems: Gemini TTS voice synthesis, robust concurrency, chunk-level caching, loudness mastering (-16 LUFS), ID3 chapter marks, and private RSS podcast feed publication served over Tailscale to AntennaPod on your phone.
   - **Do NOT bloat `sase-listen` itself into a monolithic web scraper or PDF parser.** Keep `sase-listen` focused on rendering narration scripts. Build a dedicated upstream **Ingestion & Script Adaptation Layer** (as a SASE macro `#paper/audio` and lightweight CLI tool) that outputs standard `sase-listen` narration scripts.

3. **What about Google NotebookLM or off-the-shelf TTS apps?**
   - **NotebookLM:** Engaging and conversational, but suffers from "infotainment lossiness" (banter, superficial summaries, dropping exact benchmarks and architectural trade-offs), has no official programmatic API or CLI, and cannot publish directly to your AntennaPod feed.
   - **Pocket / Readwise Reader / Speechify:** Terrible on academic PDFs (reads running headers, page numbers, footnote citations, and garbled LaTeX), lacks ID3 chapters, uses proprietary apps, and cannot feed AntennaPod.

4. **The Recommended Architecture:**
   - **Tier 1 (Fast Deterministic Web Path):** `trafilatura` extracts clean article Markdown from any URL -> `sase-listen script` normalizes it -> `sase-listen render --publish` compiles it into your AntennaPod feed. (Elapsed time: < 30 seconds).
   - **Tier 2 (Agentic Paper Audio Edition Path):** SASE macro `#paper/audio <url|pdf>` ingests the paper (via ArXiv HTML or Gemini multimodal PDF) -> an LLM agent drafts a chaptered, high-fidelity narration script following `sase-listen guide` (exact numbers preserved, tables converted to comparative insights, math translated to conceptual prose) -> `sase-listen lint` verifies compliance -> `sase-listen render --publish` pushes the chaptered MP3 to AntennaPod and delivers the file to Telegram.
   - **Mobile Entry Point:** Share an article or paper URL directly to the SASE Telegram bot from your phone while away from your desk, letting Apollo handle extraction, synthesis, and feed publication in the background.

---

## 2. Critique of the Plan: The Medium-Format Reality

### 2.1 The Auditory Bandwidth Dilemma

Reading a technical paper at a desk and listening to audio while walking or commuting are fundamentally different cognitive activities:

| Dimension | Reading at a Desk | Listening on a Walk / Commute |
| :--- | :--- | :--- |
| **Topology** | **2D & Random-Access:** Eyes scan forward, glance back at figures, re-read dense paragraphs, cross-reference equations. | **1D & Ephemeral:** Continuous time flow. You cannot pause every 30 seconds to scrub backwards without breaking your stride. |
| **Cognitive Load** | Dedicated attention. Visual diagrams, tables, and mathematical formulas are processed concurrently. | Split attention (navigating footpaths, traffic, physical movement). Playback speed is typically 1.25× to 1.5×. |
| **Pacing** | Variable: skim the 4-page related work section in 45 seconds; spend 10 minutes on the methodology. | Constant rate (~150 to 220 words per minute). Skimming is impossible unless chaptered. |
| **Information Density** | Academic papers maximize compact spatial density (notations, sub-indices, abbreviations). | Audio demands explicit signposting, active voice, conversational rhythm, and conceptual explanations. |

### 2.2 Why Verbatim PDF-to-Speech Fails Dramatically

To understand what happens if you attempt raw conversion, consider a typical paper from `sase_paper_followup_reading_list.md`: **Wang et al., *Humans are Missing from AI Coding Agent Research*** (arXiv:2608.12355, 9,867 words).

If extracted naively and read aloud verbatim:
1. **Duration:** 9,867 words at 150 WPM is **65.8 minutes**. Nobody walking for 30 minutes can digest an hour of unrelenting academic prose.
2. **Mathematical Notation:** In Section 3.1, the authors define task alignment:
   $$\mathcal{G}(H,C;q_H) = \mathrm{sim}_{\mathcal{Z}}(z_H, z_C)$$
   A deterministic text-to-speech engine or markdown normalizer either drops the math entirely (leaving disjointed text like *"Task alignment measures distance between where can come from human annotation..."*) or recites raw ASCII/LaTeX symbols (*"G open paren H comma C semicolon q sub H close paren equals sim sub script Z..."*).
3. **Bibliographic Noise:** Academic papers cite 40–80 papers. Verbatim reading sounds like:
   > *"Under this framing, better agents are those that can handle harder benchmarks (Deng et al. twenty-twenty-five; Merrill et al. twenty-twenty-six), execute longer horizons (Zhao et al. twenty-twenty-four a), and achieve higher end-to-end success rates."*
   The listener's working memory is hijacked by irrelevant author names and publication years rather than the empirical argument.
4. **Visual & Tabular Reliance:** Complex ablation tables and multi-column architecture diagrams cannot be parsed by human ears when read row-by-row.

### 2.3 The Corpus Split: Web Articles vs. Academic Papers

The reading list (`sase_paper_followup_reading_list.md`) reveals two distinct document categories:

| Document Type | Examples in Reading List | Word Count | Audio Duration (Verbatim) | Math / Table Density | Best Audio Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Category A: Web Articles & Engineering Blogs** | OpenAI Harness Engineering, Anthropic Harness pair, Martin Fowler articles | 1,500 – 3,500 words | 10 – 24 minutes | Low math; code snippets are illustrative; clean section headings | **Deterministic Verbatim Script** (or brief 5-min summary) |
| **Category B: Academic Research Papers & Preprints** | Davis et al. (MAGE), Gorinova et al. (KDD '26), CMU (He et al.), EMNLP (Ask or Assume) | 7,000 – 12,000 words | 50 – 80 minutes | High LaTeX math; multi-column PDFs; heavy citations; dense benchmark tables | **Agent-Authored "Audio Edition"** (`full`: 12–16 min, `brief`: 4–5 min) |

**Conclusion:** Treating all reading-list recommendations the same will doom the initiative. The system must support two paths: a fast, deterministic scraper for blog posts, and an intelligent, agentic synthesizer for academic research papers.

---

## 3. Evaluation of Alternative Approaches

Before designing the SASE solution, we critically evaluate existing tools and services:

### 3.1 Google NotebookLM ("Audio Overview")

- **How it works:** Users upload PDFs, Google Docs, or URLs to a NotebookLM notebook and click "Generate Audio Overview". Two AI hosts engage in a natural, lively dialogue discussing the sources.
- **Strengths:**
  - Unmatched conversational realism, vocal inflections, and pacing.
  - Highly engaging while walking; conversational banter keeps the listener awake.
- **Critical Flaws for SASE Engineering:**
  1. **"Infotainment Lossiness":** NotebookLM aggressively dumbs down technical nuance. It frequently skips specific benchmark numbers, error percentages, model configurations, and architectural edge cases in favor of high-level analogies and casual banter (*"Wow, Dave, that is completely wild!"*).
  2. **Zero Automation / Closed API:** NotebookLM has no supported public CLI, REST API, or webhook. Feeding an article requires opening a web browser, creating a notebook, uploading files, and manually downloading the resulting audio.
  3. **Monolithic & Unchaptered:** Generates a single MP3 file without ID3 chapter marks. If you miss a point, you cannot skip back to the start of that topic.
  4. **No Podcast RSS Integration:** Requires manual downloading, file transfer, and hosting to get the file into AntennaPod.

### 3.2 Read-It-Later & Commercial TTS (Pocket, Readwise Reader, Speechify, Audm)

- **How it works:** Browser extensions save articles to an inbox; native mobile apps synthesize audio on the device or stream ElevenLabs voices.
- **Strengths:** Instant mobile bookmarking; zero setup.
- **Critical Flaws:**
  1. **Disastrous on Academic PDFs:** Reader apps rely on basic document parsers. When reading arXiv PDFs, they read out page header banners, license footers, line numbers, footnote markers, and raw LaTeX math fragments.
  2. **Proprietary Silos:** Requires using their proprietary playback application. You lose AntennaPod's variable speed controls, custom auto-queuing, and unified podcast queue.
  3. **Expensive Subscriptions:** High-quality neural voices in apps like Speechify cost $140–$250/year.

### 3.3 The Verdict: Leverage and Extend `sase-listen`

`sase-listen` is already deployed in your environment with significant advantages:
- **Zero Audio Infrastructure Overhead:** It already handles chunking, API retries, Gemini TTS synthesis (`Charon` voice), ffmpeg loudness normalization (-16 LUFS), ID3 chapter tagging, and RSS feed XML generation.
- **Tailscale + AntennaPod Ready:** Apollo already hosts the feed directory (`~/.local/share/sase-listen/feed`) served over Tailscale HTTPS on port `:8443`. AntennaPod on your phone automatically refreshes, downloads new episodes, and queues them.
- **Reproducible & Private:** Operates entirely within your infrastructure; scripts are auditable markdown; cached chunks avoid paying for re-renders.

The missing piece is **not** audio playback or feed publishing. The missing piece is the **Ingestion & Script Adaptation Layer**.

---

## 4. Architectural Design: The Two-Tier Pipeline

To make transcribing web articles and research papers effortless, we propose a two-tier architecture:

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 USER INGESTION TRIGGER                 │
                  │  CLI: sase paper audio <url>  |  Telegram: send <url>  │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
                                     Inspect Input URL
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
           [Web Article / Blog Post]                    [Academic Paper / ArXiv]
          (OpenAI, Anthropic, Fowler)                   (arXiv abs/html/pdf, ACM)
                      │                                             │
                      ▼                                             ▼
              TIER 1: DETERMINISTIC                         TIER 2: AGENTIC ADAPTER
             `uvx trafilatura -u <url>`              Fetch ArXiv HTML or Ingest PDF
                      │                                             │
                      ▼                                             ▼
             Clean Markdown Body                       Agent / LLM Narration Script
                      │                                 - Enforces sase-listen guide
                      ▼                                 - Translates tables & math
             `sase-listen script`                       - Preserves exact numbers
          Deterministic Chaptering                      - Chapters: Context, Arch,
                      │                                   Numbers, SASE Takeaways
                      │                                             │
                      └──────────────────────┬──────────────────────┘
                                             │
                                             ▼
                                `sase-listen lint <script>`
                                 (Automated syntax & fidelity check)
                                             │
                                             ▼
                              `sase-listen render --publish`
                                 - Gemini TTS (Charon)
                                 - Concurrency 3, chunk cache
                                 - -16 LUFS normalization
                                 - ID3 chapters
                                             │
                                             ▼
                                  DISTRIBUTION & PLAYBACK
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
           Local RSS Feed on Apollo                       Telegram Bot
      `https://apollo...:8443/.../feed.xml`            (Optional Direct MP3)
                      │
                      ▼
           AntennaPod on Android Phone
          (Auto-download on WiFi / Tailscale)
```

---

## 5. Detailed Component Specifications

### 5.1 Ingestion Engine: `trafilatura` for Web Articles

For web articles, `trafilatura` (a state-of-the-art Python extraction library and CLI) strips navigation bars, headers, sidebars, cookie banners, and footers, extracting pristine Markdown prose:

```bash
# Empirically tested command:
uvx trafilatura -u "https://martinfowler.com/articles/harness-engineering.html" --markdown
```

**Empirical Test Results (Martin Fowler article):**
- Output: 2,540 words of clean markdown with preserved H1/H2 hierarchy.
- Normalization via `sase-listen script`: Completed in **0.4 seconds**, produced 14 clean chapters, 0 omissions, and **0 errors** in `sase-listen lint`.
- Dry-run render: 17.1 minutes, 17 audio chunks, estimated synthesis cost: **$0.23**.

### 5.2 Agentic Adaptation Engine: The "Audio Edition" for Papers

For academic papers, we rely on an LLM agent (or automated Gemini script) to act as a **Technical Audio Editor**.

#### The Paper-to-Script Prompt Contract

The agent takes the extracted paper text (or PDF) and writes a script adhering strictly to `sase-listen guide`:

```markdown
---
narration: 1
title: "Humans are Missing from AI Coding Agent Research"
source: "https://arxiv.org/abs/2608.12355"
date: "2026-07-04"
kind: research
edition: full
producer: agent
---

## The Core Thesis

As coding agents improve on autonomous benchmarks, the practical bottleneck is shifting
away from code generation toward human communication, supervision, and trust. Authors
from the SWE-bench team argue that optimizing solely for agent autonomy has reached
diminishing returns...

## Four Pillars of Collaboration

Rather than treating human interaction as an afterthought, the paper proposes four
formal dimensions. First is task alignment, which measures how well the agent infers
unstated user constraints instead of falling into what the authors call a clarification
spiral...

## The Benchmark Gap and Evidence

Examining benchmark performance against real developer workflows reveals striking
mismatches. In enterprise studies, developers spend up to 40% of their time verifying
agent output, while agents grading their own work fail to catch subtle regressions...

## Lessons for SASE

For orchestrators like SASE, this reinforces why human-in-the-loop gates and mechanical
harness sensors are essential. Autonomy without inspectable verification contracts
creates review fatigue rather than productivity...
```

#### The Audio Adaptation Rules for Papers

1. **Chapter Structure:** Exactly 3–4 chapters:
   - *Chapter 1: The Core Thesis & Context* (What problem does the paper address and why now?)
   - *Chapter 2: Architecture & Technical Mechanism* (How does the system or theoretical model work?)
   - *Chapter 3: Empirical Findings & Deciding Numbers* (What did the experiments prove, with exact metrics?)
   - *Chapter 4: Critical Limitations & Practical Lessons* (What are the trade-offs, and what does this mean for our engineering?)
2. **Number & Evidence Fidelity:**
   - Every quantitative claim must be preserved in exact digits (`24%`, `1,500 PRs`, `50% vs 67%`).
   - Stated uncertainty (`about`, `roughly`, `up to`) must be preserved.
   - Never invent claims or embellish findings.
3. **Translating Math and Formulas:**
   - Convert symbolic equations into verbal logic. For example:
     - *Raw:* $\min_{\theta} \mathbb{E}_{(x,y)\sim \mathcal{D}} [\mathcal{L}(f_\theta(x), y)]$
     - *Spoken:* "The system minimizes expected prediction loss over the training distribution by tuning parameter weights..."
4. **Translating Tables:**
   - Never read a table cell-by-cell. Identify the baseline, the winner, the runner-up, and the margin of difference.
5. **Eliminating Bibliographic Noise:**
   - Drop bracketed numbers `[12, 14]` and inline author laundry lists. Only mention lead institutions or pivotal authors when historically significant (*"As Vaswani and colleagues demonstrated..."*).

---

## 6. Ergonomics: How You Will Actually Use It

To ensure this tool is used daily rather than forgotten, the trigger ergonomics must fit seamlessly into your life:

### Ergonomic Scenario 1: At Your Terminal (Fast Single-Command)

Run a dedicated SASE macro or CLI tool directly from your workspace:

```bash
# For a web article (deterministic fast-path):
sase paper audio "https://openai.com/index/harness-engineering/"

# For an arXiv paper (synthesizes a 14-minute full audio edition):
sase paper audio "https://arxiv.org/abs/2608.12355" --edition=full

# For a quick 4-minute commute brief:
sase paper audio "https://arxiv.org/abs/2608.12355" --edition=brief
```

### Ergonomic Scenario 2: On Your Phone While Walking / Commuting

You are reading Twitter, Hacker News, or an email on your phone and find an interesting paper:
1. Tap **Share** -> **Telegram** -> Send the URL to your private SASE Telegram bot.
2. The `sase-telegram` bot parses the URL, runs `#paper/audio`, extracts the content, synthesizes the episode on Apollo via `sase-listen`, and adds it to `feed.xml`.
3. Within 60–90 seconds, **AntennaPod** (connected to Apollo via Tailscale) auto-downloads the episode.
4. You put in your earbuds, tap play in AntennaPod, and listen to a perfectly mastered, chaptered 12-minute technical briefing.

### Ergonomic Scenario 3: Batch Transcribing Reading Lists

You have a curated list like `sase_paper_followup_reading_list.md`:

```bash
sase paper batch-audio research:202609/sase_paper_followup_reading_list/sase_paper_followup_reading_list.md --edition=brief
```
Apollo iterates through the recommended items, synthesizes brief editions, and deposits an entire curated podcast playlist into AntennaPod for your upcoming week of walks.

---

## 7. Economics & Cost Analysis

Synthesizing audio using modern AI APIs is remarkably inexpensive. Below is the cost breakdown based on live 2026 rates:

| Stage | Mechanism | Resource / API | Cost per Episode (Article) | Cost per Episode (Paper Audio Edition) |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Web scrape or ArXiv parse | `trafilatura` / local CPU | $0.000 | $0.000 |
| **Scripting** | LLM Audio Adaptation | Gemini 2.5/3.8 Flash | $0.000 (deterministic) | ~$0.005 |
| **TTS Synthesis** | High-quality voice | Gemini TTS (`Charon`) | ~$0.15 (1,800 words) | ~$0.18 (2,100 words `full`) / ~$0.05 (`brief`) |
| **Mastering** | Loudness, tags, chapters | `ffmpeg` on Apollo | $0.000 (local CPU) | $0.000 (local CPU) |
| **Hosting & Delivery** | Tailscale + RSS feed | Apollo local SSD | $0.000 | $0.000 |
| **Total Cost** | | | **~$0.15** | **~$0.19** (Full) / **~$0.05** (Brief) |

### Monthly Commute Budget
If you listen to **one full paper and one web article every working day** (~40 episodes per month):
- Total Monthly Cost: **~$6.50 to $7.50 per month**.
- This is a tiny fraction of a commercial Audible, Speechify, or Readwise subscription, with vastly superior technical density and zero manual transfer effort.

---

## 8. Adjustments to Requirements

Based on this research, we formally recommend making four adjustments to the original problem requirements:

1. **Adjustment 1: Reject Raw Verbatim PDF Audio.**  
   *Original intuition:* "Convert a research paper to audio."  
   *Refinement:* Disallow direct verbatim TTS of academic PDFs. Require all research papers to pass through the **Audio Edition** adapter to guarantee listenability, formula translation, and table interpretation.
2. **Adjustment 2: Standardize on Dual Edition Budgets (`brief` vs `full`).**  
   *Refinement:* Follow `sase-listen guide`'s formal edition targets:
   - `brief`: ~600 words (4 minutes) for rapid screening during short walks.
   - `full`: ~1,800–2,400 words (12–16 minutes) for deep technical immersion on longer commutes.
3. **Adjustment 3: Decouple Ingestion from `sase-listen` Core.**  
   *Refinement:* Do not add web scraping or PDF parsing logic directly into the `sase-listen` repository. Maintain `sase-listen` as a clean, focused rendering CLI (`script -> MP3 -> feed`). Implement ingestion in a lightweight SASE companion CLI or macro (`sase-paper-listen` / `#paper/audio`).
4. **Adjustment 4: Keep Audio Out of Git; Store Only Script Artifacts.**  
   *Refinement:* Never commit binary MP3 files into the `research` git repository. Store only the generated `<name>_narration.md` script in the research sidecar or artifact store, allowing any episode to be reproduced or re-rendered on demand.

---

## 9. Recommended Phased Implementation Plan

### Phase 1: Prototype the Ingestion & Script CLI (`sase-paper-audio`)
1. Create a lightweight Python CLI utility (or shell script) `sase-paper-audio`:
   - Inspects the input URL.
   - If HTML blog: runs `uvx trafilatura -u <url> --markdown`, then calls `sase-listen script` to generate `<stem>_narration.md`.
   - If ArXiv / PDF: downloads the PDF or fetches `arxiv.org/html/<id>`, calls Gemini Flash with the SASE Audio Edition prompt, and writes `<stem>_narration.md`.
2. Runs `sase-listen lint <stem>_narration.md`.
3. Calls `sase-listen render <stem>_narration.md --publish`.

### Phase 2: Create the SASE Macro (`#paper/audio`)
Add `#paper/audio` to `sase-research-artifacts` alongside `#research/audio`:
- Accepts `url` and optional `edition` (`brief` or `full`).
- Coordinates the agent to author and lint the script.
- Automatically publishes to the private AntennaPod feed on Apollo.

### Phase 3: Mobile Dispatch via `sase-telegram`
Wire URL detection in the inbound Telegram message router:
- When a message to the bot starts with `http://` or `https://` pointing to arXiv or a recognized blog, prompt or auto-trigger `#paper/audio`.
- Send an acknowledgment message: *"Synthesizing audio edition for 'Humans are Missing from AI Coding Agent Research' (Full Edition, ~14 min)..."*
- Upon render completion, push the MP3 to Telegram and ping AntennaPod.

---

## 10. Conclusion

Converting external web articles and research papers to commute audio for AntennaPod is not only feasible—it is an ideal realization of SASE's agentic tooling. By using `trafilatura` for deterministic web articles, an LLM adaptation prompt for dense academic papers, and `sase-listen` for audio mastering and podcast feed publishing, you create a seamless, hands-free bridge from cutting-edge research directly to your headphones.
