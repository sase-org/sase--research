# sase-listen: User Capabilities, Deliverables, and Operational Architecture

**Date:** 2026-10-01  
**Researcher:** `research.38.gem`  
**Context:** SASE Epic Bead `sase-1e3` · Plan `plan:202610/sase_listen.md`  
**Status:** Independent Swarm Research Report (`__gem`)

---

## Executive Summary

The new **`sase-org/sase-listen`** repository delivers a standalone, broadcast-quality audio production engine and mobile delivery pipeline that converts Markdown documents into chaptered, loudness-normalized MP3 audio editions.

Designed principally for engineers and researchers who consume technical material during commutes, walks, or workouts, `sase-listen` solves the fundamental barrier of technical audio: **raw Markdown read verbatim by text-to-speech (TTS) engines is unlistenable**. By coupling an intelligent narration script contract with studio-grade audio mastering, multi-engine TTS orchestration, and automated mobile distribution (via private podcast RSS feeds and Telegram), `sase-listen` transforms silent, dense documentation into high-fidelity audio briefings.

Crucially, **`sase-listen` is a standalone open-source Python tool (`uv tool install sase-listen`)**, completely decoupled from SASE's core Rust backend. It requires no SASE installation to deliver value to external users, while simultaneously offering first-class, turnkey integration with SASE research swarms and Telegram bots.

```
                              ┌─────────────────────────────────────────────────────────┐
                              │                   INPUT MARKDOWN                        │
                              │  (SASE Research Report, Technical Doc, or Notes)        │
                              └───────────────────────────┬─────────────────────────────┘
                                                          │
                                         ┌────────────────┴────────────────┐
                                         ▼                                 ▼
                              ┌────────────────────┐            ┌────────────────────┐
                              │   AGENT SCRIPT     │            │   DETERMINISTIC    │
                              │   (LLM Audio Ed.)  │            │   AST NORMALIZER   │
                              └──────────┬─────────┘            └──────────┬─────────┘
                                         │                                 │
                                         └────────────────┬────────────────┘
                                                          ▼
                                      ┌───────────────────────────────────────┐
                                      │      NARRATION SCRIPT CONTRACT v1     │
                                      │  (Clean prose, ## chapters, metadata) │
                                      └───────────────────┬───────────────────┘
                                                          ▼
                                      ┌───────────────────────────────────────┐
                                      │         TTS SYNTHESIS ENGINE          │
                                      │  Gemini 3.8 Flash (default) / OpenAI /│
                                      │  Kokoro-82M / Offline Tone (testing)  │
                                      │  [Content-Addressed Chunk Cache]      │
                                      └───────────────────┬───────────────────┘
                                                          ▼
                                      ┌───────────────────────────────────────┐
                                      │       STUDIO AUDIO MASTERING          │
                                      │  • Bundled static FFmpeg 7.0.2        │
                                      │  • Two-pass EBU R128 (-16 LUFS)       │
                                      │  • Dynamic silence compression        │
                                      │  • ID3v2.3 CHAP/CTOC chapter tagging  │
                                      │  • Generated 1400x1400 Cover Art      │
                                      └───────────────────┬───────────────────┘
                                                          ▼
                                      ┌───────────────────────────────────────┐
                                      │        OUTPUT: 64 kbps CBR MP3        │
                                      └───────────────────┬───────────────────┘
                                                          │
                                         ┌────────────────┴────────────────┐
                                         ▼                                 ▼
                              ┌────────────────────┐            ┌────────────────────┐
                              │  PRIVATE PODCAST   │            │  TELEGRAM AUDIO    │
                              │  (RSS 2.0 Feed /   │            │  (Native sendAudio │
                              │   AntennaPod)      │            │   player & speed)  │
                              └────────────────────┘            └────────────────────┘
```

---

## 1. What Users Actually Receive Upon Installation

When a user installs `sase-listen` (via `uv tool install sase-listen` or `pip install sase-listen`), they receive a complete suite of CLI commands, rendering utilities, and distribution services.

### Key Capabilities at a Glance

| Pillar | What the User Gets | Why It Matters |
| :--- | :--- | :--- |
| **1. Listenability Engine** | AST normalizer, narration script validator (`lint`), and agent authoring guide (`guide`). | Eliminates syntax noise (code fences, raw URLs, hex SHAs, table pipe syntax) that ruins raw TTS. |
| **2. Audio Mastering** | Bundled static FFmpeg (via `imageio-ffmpeg`), two-pass EBU R128 loudness normalization (−16 LUFS), and micro-timing pause insertion. | Produces professional, broadcast-consistent audio without requiring system-level `sudo apt install ffmpeg`. |
| **3. True Chapter Support** | ID3v2.3 `CHAP` and `CTOC` frames mapped directly to Markdown `##` sections. | Enables mobile skipping, chapter scrubbing, and visual progress in podcast players. |
| **4. Visual Identity** | Automated 1400×1400 cover art generation (Pillow) with deterministic gradient palettes and typography. | Ensures every track looks like a polished podcast episode on phone lock screens. |
| **5. Flexible TTS Backends** | Google Gemini 3.8 Flash TTS (default), OpenAI-compatible TTS (OpenAI, Kokoro-82M), and offline synthetic `tone`. | Balances studio naturalness, privacy, zero-cost offline development, and low cost. |
| **6. Mobile Delivery** | Private RSS podcast feed (Tailscale Funnel-ready) with QR setup, plus native Telegram `sendAudio` routing. | Seamlessly delivers audio to everyday mobile listening apps (AntennaPod, Telegram) with zero manual file transfers. |
| **7. Resilient Orchestration** | Content-addressed chunk caching, atomic library writes, quality validation gates, and dry-run cost previews. | Network or process crashes never waste API credits; re-runs resume instantaneously. |

---

## 2. Deep Dive: The Core Deliverables

### 2.1 The Listenability Engine: The Narration Script Contract

The central insight of `sase-listen` is that **text preparation decides audio quality**. Reading raw Markdown aloud produces terrible results: Whisper and human listeners alike stumble over table pipes, file line citations (`utils.py:142`), hex SHAs, math formulas, and code snippets.

`sase-listen` introduces a formal, validated interface: **Narration Script Contract v1**:
- **Frontmatter Schema:** Defines metadata including title, source ref, blob SHA, date, edition (`full`, `brief`, `digest`, `verbatim`), and producer (`agent` or `deterministic`).
- **Body Semantics:** Enforces a clean structure where only `##` headings (chapters) and plain spoken paragraphs exist. All raw Markdown syntax (bolding, backticks, bullet symbols, raw links) is purged.
- **Automated Intro/Outro Injection:** The renderer automatically synthesizes standard spoken disclosures ("*This is an AI-narrated audio edition of...*") and endings, ensuring legal and ethical compliance without cluttering source scripts.
- **Dual Producer Model:**
  1. **Agent Producer (`producer: agent`):** For deep research reports, an LLM agent writes a listenable narrative. It translates complex tables into verbal comparisons (highlighting the winner, runner-up, and deciding metrics) and retains core argument numbers while omitting visual noise.
  2. **Deterministic AST Normalizer (`producer: deterministic`):** Invoked via `sase-listen script <file.md>`, this parser uses `markdown-it-py` to mechanically strip code fences, URLs, and footnotes, humanize identifiers (e.g. converting `snake_case` to "snake case"), speak small tables row-by-row, and emit an omissions report (`omissions.json`).
- **Tooling Support:**
  - `sase-listen guide`: Prints the packaged authoring guide and listenability rules directly to stdout.
  - `sase-listen lint`: Validates scripts before synthesis. Checks for structural violations, leftover residue, pacing budgets (flags paragraphs over 180 words or sentences over 45 words), and number fidelity against the source document.
- **Pronunciation Lexicon (`lexicon.yml`):** Bundles a phonetic mapping for technical jargon (`TUI` → "too-ee", `chezmoi` → "shay-mwah", `LUFS` → "loofs", `xprompt` → "ex-prompt"), expandable via user configuration.

### 2.2 Studio-Grade Media Production (Zero-Dependency Audio)

Users do not need to install system audio packages, configure codecs, or tune audio normalization parameters:
- **Hermetic FFmpeg Engine:** Bundles static FFmpeg 7.0.2 via `imageio-ffmpeg` (with `libmp3lame`, `loudnorm`, `silenceremove`, and `ebur128`). It runs reliably across Linux and macOS environments with zero system `sudo` requirements.
- **Two-Pass EBU R128 Mastering:** Applies two-pass `loudnorm` targeting **−16 LUFS integrated loudness** and **−1.5 dBTP true peak**. Volume remains consistent between whisper-quiet paragraphs and louder headings across all episodes.
- **Micro-Timing & Pacing Control:**
  - Trims chunk silence to 80 ms.
  - Automatically compresses internal silences exceeding 1.5s down to 0.7s (preventing awkward TTS pauses).
  - Injects calibrated pauses: 0.5s between paragraph chunks, 1.2s between chapters, and 0.9s after intros.
- **Format Specification:** Emits mono MP3 encoded at **24 kHz, 64 kb/s CBR** with Xing VBR/CBR headers. This produces compact files (~7 MB for a 15-minute report), well beneath Telegram's 50 MB bot limit and light on mobile data plans.
- **ID3v2.3 Chapters & Metadata:** Writes ID3 frames (`TIT2`, `TPE1`, `TALB`, `TDRC`, `COMM`) and embeds a `CTOC` table of contents with `CHAP` frames for every chapter heading.

### 2.3 Automated Visual Cover Art System

Every generated episode includes high-resolution embedded cover art (1400×1400 progressive JPEG, Pillow-generated):
- **Deterministic Color Theming:** Extracts a color palette from the SHA-256 hash of the title, creating consistent, distinctive visual themes.
- **Typography & Layout:** Uses a bundled Open Font License typeface (Inter SemiBold & Regular) to auto-fit titles up to 5 lines, formatted with date badges and a small-caps category label (`SASE RESEARCH · AUDIO EDITION`).
- **Waveform Motif:** Renders a clean, mathematical waveform bar design along the bottom derived from the document hash.
- **Custom Image Handling:** If an infographic or custom image exists (e.g. `--cover` or sibling `<stem>_infographic.png`), `sase-listen` centers and letterboxes the graphic over a blurred, darkened background of itself to preserve the 1:1 aspect ratio.

### 2.4 Multi-Engine TTS Backends & Resilient Caching

Users are not locked into a single AI provider:
- **Gemini 3.8 Flash TTS (Default):** Utilizes Google's `gemini-3.8-flash-tts` with voice `Charon` (or alternatives `Sadaltager`, `Kore`, `Iapetus`). Delivers high conversational cadence, natural inflection, and rapid synthesis at an affordable price point.
- **OpenAI-Compatible Engine:** Connects via `httpx` to OpenAI (`gpt-4o-mini-tts-2025-12-15`) or self-hosted, private local models such as **Kokoro-82M** via Kokoro-FastAPI (`base_url`).
- **Offline Synthetic Tone Engine (`tone`):** Generates deterministic tone bursts at conversational speeds (~150 wpm). Enables full local end-to-end testing, CI verification, and UI demonstrations without API credentials or network traffic.
- **Content-Addressed Chunk Cache:**
  - Chunks are hashed by canonical JSON: `sha256(engine, model, voice, style, speed, sample_rate, text)`.
  - Stored in `$XDG_CACHE_HOME/sase-listen/chunks/`.
  - Atomic file writes and LRU eviction (configurable cap, default 2 GB).
  - **Crash Resilience:** If a render fails midway (e.g. rate limit, laptop lid closed), rerunning the command reuses all completed chunks, paying only for the remaining sections.

### 2.5 Frictionless Mobile Delivery: How the Audio Reaches Earbuds

A major design triumph of `sase-listen` is recognizing that users do not want another desktop audio player; they listen on phones during commutes.

1. **Private Podcast Feed (AntennaPod & Standard Podcatchers):**
   - Implements a Podcasting 2.0 / RSS 2.0 feed generator (`feed.xml`) supporting `itunes:duration`, `itunes:image`, and `podcast:chapters`.
   - Built-in feed management CLI: `sase-listen feed init`, `publish`, `unpublish`, `prune`, and `status`.
   - Security & Privacy: Designed to be served via Tailscale Funnel on `:8443` at an unguessable secret URL token (`tailscale funnel --bg --https=8443 --set-path=/<token> <feed-dir>`). Enforces `<itunes:block>yes</itunes:block>` and `<podcast:locked>yes</podcast:locked>` to prevent crawler indexing.
   - **QR Code Setup:** `sase-listen feed --qr` prints an ANSI QR code directly in the terminal, allowing users to scan with AntennaPod and immediately subscribe with auto-download enabled.
2. **Native Telegram Audio Integration:**
   - In SASE environments, `sase-telegram` routes generated MP3s through Telegram's `sendAudio` API (rather than generic document downloads).
   - Audio tracks arrive in Telegram with metadata tags (title, author, cover art) intact, playing seamlessly in Telegram's built-in background media player with lock-screen controls and 1.5×–2× speed adjustments.

### 2.6 Human- & Machine-First CLI Experience

The CLI is engineered with Rich formatting, clear error remediation hints, and full automation parity:
- **`sase-listen render SOURCE [-o PATH]`**: Main workhorse command. Displays rich plan panels (title, narrator, word count, estimated duration, estimated cost), live per-chapter synthesis progress bars, and completion summaries.
- **`sase-listen audition [--voices A,B]`**: Synthesizes a packaged ~45-second benchmark passage across multiple voices, allowing users to audition and select preferred narrators without spending money on full reports.
- **`sase-listen doctor [--online]`**: Diagnostic command checking config validity, FFmpeg capabilities, credential status, directory permissions, disk space, and podcast feed health.
- **`sase-listen ls [EPISODE]`**: Displays an interactive table of all rendered library episodes, chapters, and publish states.
- **`sase-listen script SOURCE`**: Converts raw Markdown into a validated narration script.
- **`sase-listen config [init|path]`**: Displays effective configuration values with their origin (CLI, env, file, default) with secrets automatically masked.
- **`--json` Everywhere:** Every command supports strict, single-object JSON output on stdout for clean machine-to-machine interop and agent consumption.

---

## 3. SASE Ecosystem Integration (For SASE Users)

While `sase-listen` functions completely independently for general Markdown authors, SASE users benefit from deep, automated pipeline hooks:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             SASE SWARM WORKFLOW                             │
│                                                                             │
│  1. Swarm Research: Agents investigate topic (e.g. #research_swarm)         │
│  2. Lead Synthesis: Lead writes final report (<stem>__final.md)             │
│  3. Linker Stage: Linker publishes clean report (<stem>.md)                 │
│  4. Audio Stage (#research/audio, audio=true):                              │
│     • Forks lead agent context                                              │
│     • Writes & lints narration script (<stem>_narration.md)                 │
│     • Invokes `sase-listen render`                                          │
│     • Registers artifact via `sase artifact create`                         │
│  5. Telegram Outbound: Bot delivers MP3 track directly to user's phone      │
│  6. Feed Auto-Publish: Episode added to private AntennaPod RSS feed         │
└─────────────────────────────────────────────────────────────────────────────┘
```

1. **`#research/audio` Xprompt:** Users can type `#research/audio @research:202610/report.md` in the SASE TUI or send it as a Telegram message. A dedicated agent drafts the script, runs `sase-listen lint`, invokes `sase-listen render`, and registers the resulting artifact.
2. **`#research_swarm audio=true` Stage:** Swarms can automatically spawn an audio authoring stage following the research lead and linker stages.
3. **Artifact Integrity:** Companion narration scripts (`*_narration.md`) are automatically excluded from the primary `@research` documentation inventory to avoid cluttering human-readable knowledge indices.

---

## 4. Operating Footprint & Economics

Understanding resource utilization and operational costs is vital for planning regular consumption:

### 4.1 Cost Model per Episode

| Synthesis Engine | Model | Unit Rate (per audio min) | Typical 16-min Episode | 20 Episodes/Month |
| :--- | :--- | :--- | :--- | :--- |
| **Gemini Flash TTS** | `gemini-3.8-flash-tts` | $0.0135 ($0.027 in 2027) | **$0.22** ($0.43 in 2027) | **$4.40** ($8.60) |
| **Gemini Flash-Lite**| `gemini-3.8-flash-lite-tts` | $0.0090 ($0.018 in 2027) | **$0.14** ($0.29 in 2027) | **$2.80** ($5.80) |
| **OpenAI Mini TTS**  | `gpt-4o-mini-tts-2025-12-15`| $0.0150 | **$0.24** | **$4.80** |
| **Kokoro Local**     | `Kokoro-82M` (self-hosted)  | $0.0000 | **$0.00** | **$0.00** |
| **Synthetic Tone**   | `tone` (offline mock)       | $0.0000 | **$0.00** | **$0.00** |

*Key Takeaway:* A heavy commuter listening to an edition every workday spends less than $5.00 a month on cloud TTS API usage. For private or unbudgeted workloads, Kokoro-82M provides a completely free alternative.

### 4.2 Storage and Bandwidth Footprint

- **Mastered Audio:** ~0.45 MB per minute of audio (~7 MB per 15-minute report).
- **Disk Caching:** Configurable LRU cache (default: 2 GB in `$XDG_CACHE_HOME/sase-listen/chunks/`).
- **Episode Library:** Stored in `$XDG_DATA_HOME/sase-listen/library/<episode-id>/` (containing MP3, manifest JSON, script Markdown, cover JPEG, and chapter JSON).
- **Feed Retention:** Automatic pruning configurable by age (default 90 days) and count (default 200 episodes).

---

## 5. Scope Boundaries: What `sase-listen` Does NOT Provide

To avoid misconceptions, `sase-listen` has several intentional non-goals:
1. **Not a Two-Host Banter Simulator:** Unlike NotebookLM or Podcastfy "deep dive" modes, `sase-listen` deliberately implements single-narrator technical briefings. It prioritizes fidelity to complex technical decisions, numbers, and recommendations over conversational banter.
2. **Not a SASE Rust Subsystem:** It does not modify `sase-core` or implement Rust bindings. Media rendering is decoupled from core SASE orchestrations.
3. **No Audio Stored in Git:** MP3 binaries are strictly excluded from git repositories; only lightweight narration scripts (`*_narration.md`) are version-controlled alongside reports.
4. **No Custom Mobile GUI:** It deliberately delegates playback to mature third-party mobile applications (AntennaPod and Telegram) that already provide battle-tested background audio services, Bluetooth integration, car head-unit controls, and playback speed persistence.
5. **No Automatic Whisper ASR Transcription Gate in v1:** Audio quality is validated using duration, silence, and word-per-minute heuristics. Automated Whisper back-transcription was deemed non-essential for v1 and deferred.

---

## 6. Synthesis & Conclusion

The `sase-listen` repository provides users with a complete, end-to-end bridge between written technical documentation and mobile auditory learning. 

By installing `sase-listen`, users receive:
1. An **intelligent normalizer and script contract** that turns syntactically noisy Markdown into natural, spoken technical prose.
2. A **zero-dependency mastering pipeline** that guarantees consistent loudness (−16 LUFS), ID3 chapter markers, and elegant cover art.
3. A **multi-engine synthesis harness** offering top-tier Gemini voices, local private Kokoro generation, and cost-free offline testing.
4. **Frictionless phone delivery** via private podcast feeds (AntennaPod QR setup) and Telegram audio playback.
5. A **rich, user-friendly CLI** equipped with diagnostic health checks, voice auditions, and full programmatic JSON interfaces.

For individual developers, it turns personal Markdown notes into personalized audio feeds. For teams utilizing SASE, it unlocks an automated medium where every research report lands in their earbuds before the morning commute.
