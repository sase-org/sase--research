# Listening To Research: A Markdown-To-Audio Pipeline For Commutes And Walks

**Research question:** What is the best way to turn Markdown files, first of all the research
reports in the `research` sidecar (`sase-org/sase--research`), into audio worth listening
to while commuting or walking? Which pieces should SASE build, which should it buy, and how
should the result reach the phone?

**Scope and method:** Measured the shape of the research corpus (word counts, Markdown
feature density, publication rate). Benchmarked an open-weight TTS model (Kokoro-82M via
`kokoro-onnx`) on **apollo** (16-core Xeon, no GPU) and **athena** (Threadripper 3970X +
RTX 3080 Ti). Ran an ASR round-trip (faster-whisper `base.en`) to check intelligibility.
Read the existing SASE integration points: the `research-highlights` file hook, the
`#research/image` swarm stage, the `sase-telegram` outbound path, `sase notify`, the mobile
gateway, and apollo's Tailscale Serve config. Surveyed current (October 2026) TTS pricing
and Speech Arena rankings, podcast-delivery mechanics, and prior art. No paid API was
called; the cloud-engine numbers come from published pricing and leaderboards, and §9 lists
the validation steps that still need a live call.

---

## Executive summary

1. **The hard part is not text-to-speech. It is turning a research report into something
   meant to be heard.** The reports are written for reading with a code index open. In the
   626 reports from July to September, 575 contain tables, 452 contain fenced code, and the
   average report has about **133 inline code spans**. Reading one aloud verbatim is
   unlistenable. One paragraph containing four `file.py:NNN` citations took **35.9 s** to
   speak as-is versus **23.3 s** without the citations, 54% of extra airtime spent on lines
   like "S-R-C slash sase slash ace slash tui slash modals…". Whisper transcribed the
   citations back as *"Plugins browser agent clives actions. Pi, 87."* So an **LLM
   adaptation step that writes a spoken-word script** is required, not optional. SASE
   agents are already good at exactly this work.
2. **Volume forces a selection design.** The sidecar holds **438 consolidated reports**
   (drafts excluded), with a median of 3,065 words, which is about 19 minutes read
   verbatim. **117 of them landed in September alone, about 4 per day.** That is around 37
   hours of verbatim audio per month, more than a full commute budget. Narrating everything
   at full length is the wrong product. The right shape is a **daily digest**, about 2
   minutes per new report, plus **full "audio editions" on demand**.
3. **TTS engine: default to Gemini 3.8 Flash TTS, and keep Kokoro as a free local
   fallback.**
   - **Gemini 3.8 Flash TTS** is GA, ranks in the top three of the Artificial Analysis
     Speech Arena (Elo ≈ 1270), and costs about **$0.014 per audio minute** through
     2026-12-31 (about $0.027 from 2027-01-01, half price on Batch). A credential is already
     in `pass` (`gemini_cli_api_key`).
   - **Kokoro-82M** is Apache-2.0 with Elo ≈ 1064, which means listeners prefer Gemini in
     about 77% of blind pairs. It ran at **28.7× realtime on athena's GPU** and **1.7×
     realtime on apollo's loaded CPU**, with a 3.3% ASR word error rate.
   - **ElevenLabs** (v4 Elo ≈ 1320) is about 5–7× the price for a margin listeners notice
     only 57% of the time. It is not worth it for this use.
4. **Delivery: Telegram first, then a private podcast feed.**
   - **Telegram** is already wired to the phone. Bot `sendAudio` puts MP3s in Telegram's
     music player, with 0.2–2.5× speed, background play and saved position.
     `sase-telegram` currently sends an `.mp3` attachment through the document/PDF fallback,
     so a roughly 20-line `send_audio` branch is the only change needed.
   - **A private RSS feed** subscribed in **AntennaPod** on the Pixel 10 Pro XL adds
     offline auto-download, a queue and ID3 chapters. Serve it from apollo through
     **Tailscale Funnel on port 8443** under a secret path. Port 443 is already taken by the
     tailnet-only Serve for `sase_gateway`, and Funnel and Serve cannot share a port.
     Tailnet-only serving is not enough, because the phone's Tailscale node was last seen
     11 days ago.
5. **Keep audio out of git.** The research repo is **public** and already ~357 MB on GitHub
   (279 PNGs). A full backfill would add about 2.7 GB of MP3. Commit only the small,
   reviewable **narration script** (`<stem>_narration.md`) next to the report. MP3s go to a
   regenerable media directory on apollo that backs the feed.

**Recommendation (§9):** build a small **`sase-listen` plugin**. It contains a
deterministic renderer: narration script → chaptered, loudness-normalized MP3, with
pluggable `gemini | kokoro | openai` engines. It also writes the feed and sends a
notification. Agent-facing pieces go in `sase-research-artifacts`:
- a `#research/audio` xprompt, mirroring `#research/image`;
- an `audio=true` stage in `#research_swarm` that forks the lead;
- a `#research/digest` xprompt for the daily digest.

Ship in three slices:
1. On-demand editions delivered via Telegram.
2. The podcast feed plus the swarm stage.
3. The daily digest and an ASR quality gate.

---

## 1. What the input actually looks like

### 1.1 Corpus shape (measured 2026-10-01)

| Measure                                             | Value                                   |
| --------------------------------------------------- | --------------------------------------- |
| All `.md` files in the sidecar (Feb–Sep 2026)       | 874 (3.19 M words)                      |
| Consolidated reports (no `__<suffix>` drafts)       | **438**, median **3,065** words, p90 5,696 |
| Consolidated reports per month (Jul / Aug / Sep)    | 34 / 49 / **117**                       |
| Jul–Sep reports containing a table                  | 575 of 626 (~34 table lines per report) |
| Jul–Sep reports containing fenced code              | 452 of 626                              |
| Inline code spans, Jul–Sep                          | 83,023 (~133 per report)                |
| Reports with external `](http…)` links              | 185 of 626                              |
| Mermaid diagrams                                    | 43 blocks in 27 reports                 |

A representative report (`research:202609/admin_center_updates_tab_unification.md`) has
6,073 words, **579 inline code spans, 161 file:line citations, 74 table lines and 11 code
blocks**. Read verbatim it runs about **38 minutes**.

### 1.2 Why naive conversion fails

`pandoc -t plain` produces text like this (actual output):

> One load already produces all three. load_plugins_catalog_for_pane
> (src/sase/ace/tui/modals/plugins_browser_loading.py:99) returns core versions, …

Kokoro's phonemizer turns that citation into *"ess-ar-see slash sase slash ace slash tooey
slash modals slash plugins browser loading dot pie: ninety-nine"*. Measured (rows 1–2 are
the same paragraph of that report; row 3 is a separate hand-written narration of its summary):

| Variant                                | Words | Audio  | Whisper `base.en` WER vs. source |
| -------------------------------------- | ----- | ------ | -------------------------------- |
| pandoc plain text (4 citations)        | 70    | 35.9 s | 9.4% (citations came back as "Plugins browser agent clives actions. Pi, 87.") |
| same paragraph, citations regex-removed | 67    | 23.3 s | —                                |
| hand-written narration (262 words)     | 262   | 94.1 s | **3.3%**                         |

Regex stripping helps with citations. It cannot fix tables (a 6-column comparison read row
by row is noise), code blocks, `§`-cross-references, or the report's visual structure.
Reports are written as *reference documents*: an executive summary, then evidence indexed by
file and line. A listener needs a *narrative*: the question, the answer, the three reasons,
what it costs, and what to do. That restructuring is an editorial job for an LLM.

### 1.3 Volume versus listening capacity

At 117 reports a month and a median of 3,065 words, verbatim audio would be about **37 hours
per month**. A one-hour daily commute is about 22 hours per month, and that is before any
other podcasts. Even good 12-minute "audio editions" of everything would be about 23 hours
per month. So the product needs two tiers:

- a **digest tier** that covers *everything new*, briefly (question, finding,
  recommendation, about 90–150 s per report); and
- a **deep-dive tier** for the reports actually worth 10–20 minutes, chosen by you.

---

## 2. The pipeline, decomposed

```
select ──► adapt (LLM) ──► synthesize (TTS) ──► package ──► deliver
  │            │                 │                  │           │
  digest /     narration         engine per         MP3 + ID3   Telegram /
  on-demand /  script .md        chapter chunk,     chapters,   private RSS
  swarm stage  (in git)          QA + retry         −16 LUFS    (AntennaPod)
```

Each stage has an independent choice. The rest of this report takes them in order and then
assembles a recommendation.

---

## 3. Adaptation: Markdown → spoken script

### 3.1 Options

| Option | How | Fidelity | Listenability | Cost | Verdict |
| --- | --- | --- | --- | --- | --- |
| **A. Deterministic normalizer** | Markdown AST (markdown-it/mistune): drop citations and code, links → text, lists → "first… second…", tables → "a table compares N options" | Exact for what it keeps | Poor for these reports (dense, table-driven) | Free | Good **fallback** for non-research Markdown and for when the LLM path fails |
| **B. LLM single-narrator "audio edition"** | Agent rewrites the report as a spoken script with chapter headings | High if constrained (no new claims, keep numbers) | **High** | Agent run (subscription) or ~$0.01–0.20 via API | **Default** |
| **C. LLM two-host dialogue** (NotebookLM style) | Agent writes a 2-speaker script; Gemini TTS renders both speakers natively in one request (2-speaker cap) | Lower: banter adds words, invites paraphrase drift | Engaging | ~1.5–2× the minutes of B | Optional flavor later, e.g. for digests or a "swarm roundtable" of researcher disagreements |
| **D. External summarizer** | Chrome Android "Listen to this page" → *AI playback* on the GitHub-rendered report; or upload to Gemini Notebook (ex-NotebookLM) | Opaque, uncontrolled | High | Free / manual | **Phase-0 calibration only**: no automation, no queue, online-only, and Gemini Notebook has no consumer API (enterprise API is preview, the standalone Podcast API is deprecated) |

### 3.2 Recommended script format

The narration script is the contract between the agent and the renderer. It should be
committed next to the report, so it can be reviewed, diffed, regenerated and cited.

```markdown
---
title: "One Updates Tab"
source: research:202609/admin_center_updates_tab_unification.md
source_blob: 3f9c2e1…          # git blob of the report the script was written from
edition: full                  # full | brief | digest
target_minutes: 12
---

## The question
Today's report asks a simple question. …

## The short answer
…

## Why the three sub-tabs are really one
…

## What to build
…
```

Renderer rules: every `##` heading becomes an **ID3 chapter** and a TTS chunk boundary. A
chapter longer than about 700 words is split at paragraph boundaries. Body text is plain
prose, with no Markdown inside paragraphs, and the renderer strips any leftovers as a safety
net.

### 3.3 Adaptation rules (the xprompt's core)

- **Recommendation first, then reasons, then a recap.** The listener cannot glance back.
- **No file paths, line numbers, SHAs or URLs.** Refer to code by role ("the pane's
  loader"), and name an identifier only when the name itself matters, spoken naturally
  ("the `UpdateStatus` model" → "the update-status model").
- **Tables become spoken comparisons.** Name the winner and the one or two runner-ups with
  the deciding numbers; never read rows. **Code** becomes one sentence of purpose, or is
  dropped.
- **Keep every number that carries the argument, exactly.** No new claims. Uncertainty
  stays as the source states it.
- **Signpost structure** ("three reasons; first…") and expand acronyms on first use.
- **Length budget:** about 150 words per minute. `full` caps at about 2,400 words
  (~16 min), `brief` at about 600 words (~4 min), and a `digest` item at about 250 words.
- **Pronunciation lexicon:** a user-editable map applied before TTS (e.g. `TUI` → "tooey",
  `xprompt` → "ex-prompt", `chezmoi` → "shay-mwah", `uv` → "you-vee", plus however you
  want "SASE" said). Gemini also accepts pronunciation hints in its style prompt, and
  Kokoro accepts phoneme overrides.

### 3.4 Who writes the script

Use a **SASE agent**, not an API call buried in a script:

- **Inside a swarm,** the narrator can `#fork` the lead (`research.N.final`). It inherits
  the full report and the reasoning behind it, so it is cheap and the most faithful writer
  available. This is the same pattern `#research_swarm` already uses for `image=true`
  (`%wait:research.{@1}.final … #fork:research.{@1}.final #research/image`).
- **Ad hoc,** `#research/audio @research:<path>` can be launched from the TUI, the CLI, or
  **from Telegram**: `sase-telegram` already turns text messages into agent launches and
  normalizes `@research:` refs (`inbound_handlers/text_messages.py`).
- Agent runs are audited (`sase artifact read`), use existing subscriptions, and keep the
  host-owned completion model.

The renderer stays deterministic and agent-free, so it is unit-testable and reusable for any
Markdown.

---

## 4. Synthesis: choosing the TTS engine

### 4.1 Landscape (Artificial Analysis Speech Arena, fetched 2026-10-01)

| Engine | Arena Elo | ≈ $ / audio min | Per-request limits | Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| ElevenLabs **Eleven v4** | **1320** (#1) | ~$0.076 ($80 / 1M chars) | — | cloud | Best quality; ~5.6× Gemini |
| Cartesia Sonic 3.6 | 1275 | ~$0.047 | — | cloud | Realtime-oriented |
| **Gemini 3.8 Flash TTS** | **1270** (#3) | **~$0.014** ($9 / 1M audio tokens × 25 tok/s; input negligible) → **~$0.027 from 2027-01-01**; Batch −50% | 8,192 input tokens; 16,384 output tokens ≈ **10.9 min max** per call | cloud | GA Sept 2026; 30 prebuilt voices + voice design; natural-language style control; native 2-speaker dialogue |
| Gemini 3.8 Flash-Lite TTS | 1240 | ~$0.009 (→ $0.018 in 2027) | same | cloud | Cheaper fallback |
| Breeze TTS 2 (open weights, 3B) | 1209 | self-host | — | GPU | Highest open-weight model, but **non-commercial weights** and very new; 7.7 GB of weights is tight on a 12 GB 3080 Ti |
| ElevenLabs Eleven v3 / Multilingual v2 | 1170 / 1092 | ~$0.095 ($0.10 / 1k chars) | — | cloud | Expensive for what it adds |
| OpenAI `gpt-4o-mini-tts` (2025-12-15 snapshot) | not ranked | ~$0.015 | **4,096 chars** (~4 min) per call | cloud | 13 voices (`marin`/`cedar` recommended); `instructions` style prompt; key exists (`chatgpt_sase_api_key`) |
| OpenAI `tts-1` / `tts-1-hd` | — / 1101 | ~$0.014 / ~$0.029 | 4,096 chars | cloud | Legacy |
| **Kokoro-82M v1.0** | **1064** | **$0** marginal | none (library chunks internally) | **CPU or GPU** | Apache-2.0; 54 voices (`af_heart` best); deterministic, no long-form drift |
| Chatterbox (Resemble) | 1023 | self-host | — | GPU | MIT; voice cloning; slower |
| VibeVoice 1.5B (Microsoft) | 955 | self-host | — | GPU | Long-form multi-speaker, but low preference and a research-only license |
| `edge-tts` (unofficial) | — | "free" | — | cloud | Uses Edge's read-aloud endpoint; has been blocked before, SSML locked down; ToS-gray. Avoid as a foundation |

How to read the Elo gaps: under the Elo model, a 206-point gap (Gemini Flash over Kokoro)
means listeners prefer Gemini in about **77%** of blind pairs. A 50-point gap (Eleven v4
over Gemini Flash) is only about **57%**, at roughly 5.6× the price.

### 4.2 Local engine, measured

Same 262-word narration, voice `af_heart`, `kokoro-onnx` 0.6.1 with the v1.0 ONNX weights:

| Host | Backend | Load avg during run | Synthesis time for 94.1 s of audio | Realtime factor |
| --- | --- | --- | --- | --- |
| apollo (Xeon 8168, 16 vCPU, no GPU) | CPU | ~14 | 56.2 s | **1.7×** |
| athena (Threadripper 3970X, 64 threads) | CPU | ~23 | 40.0 s | 2.3× |
| athena (RTX 3080 Ti, 12 GB) | CUDA, warm | — | 3.3 s | **28.7×** |

Kokoro spoke at about 167 words/min at speed 1.0. Whisper `base.en` transcribed the clip
back at **3.3% WER** in 5.4 s of CPU, so an automated ASR check per chapter costs almost
nothing (§8).

**Operational gotcha:** the current `onnxruntime-gpu` (1.30) is built against **CUDA 13**,
and athena's NVIDIA driver 550 tops out at **CUDA 12.4**, so CUDA failed with
`CUDA driver version is insufficient`. Pinning `onnxruntime-gpu[cuda,cudnn]==1.22.0`
(CUDA 12 wheels) worked. Either pin it or upgrade the driver (≥ 580) before relying on
athena's GPU.

At 28.7×, a 15-minute episode renders in about 31 s on athena. Backfilling every
consolidated report as a 13-minute edition (~5,700 min) would take about **3.3 GPU-hours**.
On apollo's CPU, a 15-minute episode takes about 9 minutes and competes with agents for
cores.

### 4.3 Monthly cost scenarios (TTS only)

| Scenario | Audio min / month | Gemini Flash 2026 → 2027 | Flash-Lite 2026 → 2027 | OpenAI mini | ElevenLabs v3 | Kokoro |
| --- | --- | --- | --- | --- | --- | --- |
| Digest only (~4 reports/day × 2 min) | ~240 | $3.3 → $6.5 | $2.2 → $4.3 | $3.6 | $23 | $0 |
| Digest + 10 full editions (15 min) | ~390 | **$5.3 → $10.6** | $3.5 → $7.0 | $5.9 | $37 | $0 |
| Full edition of every new report | ~1,755 | $24 → $48 | $16 → $32 | $26 | $167 | $0 |
| One-time backfill of all 438 reports (13 min) | ~5,700 | $77 → $155 (Batch: half) | $51 → $103 | $86 | $540 | $0 (3.3 GPU-h) |

### 4.4 Engine recommendation

- **Default: Gemini 3.8 Flash TTS.** Near-top quality, GA, and expressive style control:
  one fixed style prompt like *"calm, clear technical-podcast narrator; moderate pace;
  slight emphasis on numbers"* keeps every episode consistent. It costs single-digit
  dollars a month for the recommended scenario. Chunk per chapter: the API caps output at
  about 10.9 minutes, and earlier Gemini TTS versions were widely reported to degrade on
  single requests past one or two minutes. 3.8 claims to fix that drift, but per-chapter
  chunks also make retries cheap.
- **Fallback, and the engine for private notes: Kokoro-82M.** It costs nothing, sends no
  text off-box, and is deterministic. Use it when the Gemini key or quota fails, and for
  Markdown that should not leave your machines (Obsidian notes, private plans). The
  research repo is already public, so cloud TTS raises no new privacy issue for research.
- **Secondary cloud engine: OpenAI `gpt-4o-mini-tts`.** Similar price, a key already
  exists, but the 4,096-character cap forces about 4-minute chunks and it is unranked on
  the Arena. Keep it behind the same interface; no need to build it first.
- **Skip ElevenLabs.** It is the best-sounding option, but the margin over Gemini Flash
  does not justify a 5–7× price for personal technical listening.
- **Do not mix engines within one episode.** If Gemini fails mid-episode, retry Gemini, or
  re-render the *whole* episode on Kokoro. A voice change in the middle is jarring.

---

## 5. Delivery: getting audio onto the phone

Facts that shape this choice:
- The phone on the tailnet is a **Pixel 10 Pro XL (Android)**, and its Tailscale node was
  "offline, last seen 11d ago". Anything that needs the phone on the tailnet will
  silently fail to sync.
- apollo already runs `tailscale serve` on **:443** (tailnet-only) → `127.0.0.1:7629`
  (`sase_gateway`). Funnel can only listen on 443, 8443 or 10000. A Funnel'd port is
  *entirely* public, and Serve and Funnel cannot use the same port.
- Telegram Bot API `sendAudio` accepts **MP3/M4A up to 50 MB** and shows the file in the
  in-app **music player**. Telegram supports 0.2–2.5× playback for long audio and voice,
  and remembers progress. At 64 kbps mono (0.48 MB/min), 50 MB is about 104 minutes.
- `sase-telegram`'s outbound attachment loop (`scripts/sase_tg_outbound.py`) has branches
  for image, animation, video and PDF. **Anything else goes through `md_to_pdf` and then
  `send_document`**, so an `.mp3` arrives as a plain file.

| Option | Phone UX | Offline / queue / chapters | Infra & effort | Verdict |
| --- | --- | --- | --- | --- |
| **Telegram `send_audio`** via `sase notify create` with `files:[…mp3]` | Music player, speed, background, saved position; plays the next audio in the chat | Manual or auto-download; chat acts as a queue; no chapters | ~20 lines in `sase-telegram` (`_is_audio_file` → `send_audio(title, performer, duration, thumbnail)`); zero new infra | **Phase 1** |
| **Private RSS feed → AntennaPod**, served by Tailscale **Funnel on :8443** at `/<secret-token>/feed.xml` | Real podcast app: queue, auto-download on Wi-Fi, skip-silence, speed, Android Auto, **ID3 chapter navigation** | Yes / yes / yes | Static files + generated `feed.xml` (iTunes tags, `<itunes:block>yes`); one `tailscale funnel --bg --https=8443 …` command; Funnel node attribute in the tailnet policy | **Phase 2** |
| Same feed, tailnet-only `serve` | Same as above | Only while the phone's Tailscale is on | Least exposure | Rejected as the default (phone usually off-tailnet) |
| GitHub Pages feed + Release assets in the public research repo | Any podcast app (Pocket Casts/Overcast need public feeds; their servers fetch) | Yes | Free CDN, no self-hosting | Viable for research-only, but couples to GitHub and cannot carry private Markdown |
| Audiobookshelf on apollo | Polished apps, progress sync | Yes | Docker + DB to run and maintain | Overkill versus static feed + AntennaPod |
| SASE Android app via the mobile gateway | Native and integrated | Would need a Media3 player, background service, downloads | Large build; gateway is tailnet-only | Later, if the app becomes the daily driver |
| Syncthing / manual copy | File-manager playback | Offline | Fiddly | No |

Recommended feed details:
- **MP3, mono, 64 kbps, 24 kHz.** Every podcast app and Telegram's `sendAudio` accept
  MP3; Opus is not universal.
- **Loudness normalized to about −16 LUFS** with an ffmpeg `loudnorm` pass. Note that
  **apollo has no `ffmpeg`** (athena does). Install it, or use a bundled static binary.
- **ID3 cover art:** the report's `_infographic.png` when one exists.
- **CHAP/CTOC chapter frames** built from the script's `##` headings. AntennaPod reads ID3
  chapters.
- The narration script linked from the episode description, or as a
  `<podcast:transcript>`.
- Keep the token-protected feed separate from anything private, and rotate the token if
  it leaks.

---

## 6. Triggering and selection inside SASE

Three entry points, all ending in the same renderer:

1. **On demand: `#research/audio`** (new, in `sase-research-artifacts`, mirroring
   `#research/image`). Input is a research ref or path plus an optional
   `edition=full|brief`. The agent:
   - reads the report with `sase artifact read`;
   - writes `<stem>_narration.md` next to it;
   - runs the renderer under `sase tool run`, or `/sase_monitor` if it is slow;
   - creates a notification with the MP3 attached. `sase-telegram` then delivers it, and
     the feed picks it up.

   Launch it from the phone by sending
   `#research/audio @research:202609/<report>.md` to the SASE Telegram bot.
2. **Swarm stage: `#research_swarm audio=true`.** Adds `<clan>.audio` with
   `%wait:research.{@1}.final … #fork:research.{@1}.final #research/audio`, exactly
   parallel to the `image` stage. The narrator inherits the lead's full context. The
   linker can list the narration script among the companions, like it does for
   `<name>_infographic.png`.
3. **Daily digest: `#research/digest`.** One episode per morning covering every new
   consolidated report, about 2 minutes each:
   - A **`research-audio` file hook** uses the same filters as `research-highlights`
     (`sidecars: [research]`, `ops: [ADD]`, drafts and swarm researchers excluded). Its
     command only **appends the report path to a pending queue**, which is instant and well
     inside the hook's 120 s default.
   - A **scheduler job** (a routine on a morning cadence) drains the queue. Its
     structured result requests a follow-up launch of `#research/digest` with the queued
     refs, which the runner performs.
   - Each digest item ends with the line "say the word for the full edition". The full
     edition is one Telegram message away.

**Where the code lives:**

| Piece | Home | Why |
| --- | --- | --- |
| Renderer, feed writer, engines, lexicon, generic `#listen <any.md>` xprompt | **new plugin repo `sase-listen`** (Python, uv) | Keeps the heavy optional dependencies (`google-genai`, `mutagen`, `kokoro-onnx`/`onnxruntime`, ffmpeg) out of sase core. Usable for plans, docs and Obsidian notes, not only research. Follows the `sase-telegram` / `sase-github` plugin precedent. |
| `#research/audio`, `#research/digest`, swarm `audio` / `audio_model` inputs, an `@audio` model alias, `research-audio` hook provider | `sase-research-artifacts` | Research-specific orchestration belongs beside `#research/image` and `research-highlights` |
| `send_audio` branch | `sase-telegram` | Delivery adapter |
| Nothing | `sase-core` | Not shared domain behavior that another frontend must match. Revisit only if an `audio` artifact kind or a gateway "listen" API is added, at which point the Rust wire records change |

**Storage and linking:**
- The narration script is **committed** in the research repo as a companion
  (`<stem>_narration.md`). Add `!20*/**/*_narration.md` to the
  `_COMPANION_MARKDOWN_EXCLUDE_GLOBS` in `sase_research_artifacts/provider.py`. Otherwise
  it becomes a "report" in the `@research` inventory and triggers a Highlights PDF.
- If MP3s are ever registered as artifacts (`sase artifact create -k file`; there is no
  `audio` kind today), also add `!20*/**/*.mp3.md` for their sibling artifact Markdown.
- The MP3 lives in a media directory on apollo that backs the feed, with retention such as
  "last 90 days". Scripts are in git, so any episode can be regenerated.
- Why not commit audio: the repo is public and ~357 MB today. A full backfill would add
  about 2.7 GB; even the recommended steady state adds about 190 MB a month, forever, to
  every clone.

---

## 7. Prior art worth borrowing from

- **`hansharhoff/podcastfeeds`** (read via `sase repo open`) is the closest match:
  RSS/articles → `edge-tts` → MP3 → private feeds over **Tailscale Serve/Funnel** behind a
  secret path token, listened to in **AntennaPod**. Ideas worth borrowing:
  - an LLM `narrate_mode: summary` for changelog-like sources;
  - spoken intros ("Title. From Source, date.");
  - images → **ID3 chapter art**;
  - per-source fixed voices;
  - a phone "share URL → inbox feed" shortcut.

  Its choice of `edge-tts` is the part *not* to copy, for the reasons in §4.1.
- **Podcastfy** is an open-source NotebookLM-style two-host generator with many LLM and
  TTS backends. It is a useful reference for dialogue prompts if option C is ever wanted.
  Its transcript generation would bypass SASE's agents and audit trail, so borrow ideas,
  not the dependency.
- **Kokoro-FastAPI** is an OpenAI-compatible HTTP server for Kokoro (Docker, CPU/GPU).
  Worth using if athena should serve Kokoro to apollo over the tailnet rather than apollo
  rendering on its CPU.
- **Chrome Android "Listen to this page"** now offers *AI playback*, a podcast-like summary,
  as well as standard read-aloud, with background and lock-screen playback. **Gemini
  Notebook** (renamed from NotebookLM in July 2026) makes high-quality two-host overviews
  but has no consumer API. Both are good *zero-build calibration* tools. Neither automates
  or queues.

---

## 8. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Narration distorts the report (dropped caveats, invented claims) | Hard rules in the xprompt (§3.3). Script committed and reviewable. Forked-lead narrator for swarms. Spoken section names so a detail can be found later in the text. Optional second-agent fidelity check for `full` editions |
| LLM-TTS artifacts: skipped or repeated words, long silences (reported and *billed* on Gemini 3.1), voice drift | Chunk per chapter (≤ ~5 min). Duration sanity check (expected words ÷ 150 wpm, reject outside ~0.7–1.5×). Trim silences > 1.5 s. **ASR gate**: faster-whisper per chapter, re-synthesize when WER > ~10% (measured cost ~6% of audio duration on CPU) |
| Price change (Gemini TTS doubles on 2027-01-01) or quota exhaustion | Engine is configuration. Kokoro is always available locally. Batch API for the non-urgent digest halves the cost |
| Too much audio, so the feed becomes a guilt pile | Digest by default, full editions opt-in, retention window |
| Funnel exposes more than intended | Dedicated port **8443** (443 stays tailnet-only for `sase_gateway`). Serve one static directory. Unguessable path token. `<itunes:block>` |
| Pronunciation of project jargon | Shared lexicon file. Listen to one episode, fix the lexicon, done |
| GPU path breaks on driver/CUDA drift (seen on athena) | Pin `onnxruntime-gpu==1.22.*` or upgrade the driver. The CPU path still works at 1.7–2.3× realtime |

---

## 9. Recommendation

**Build `sase-listen` (a deterministic renderer plus feed) and drive it with SASE agents that
write spoken-word scripts. Use Gemini 3.8 Flash TTS by default and Kokoro locally as the
fallback. Deliver over Telegram first, then over a Funnel-served private podcast feed in
AntennaPod. Narrate everything new as a daily digest and narrate in full only what you ask
for.**

### Phase 0: calibrate (15 minutes, no code)

On the Pixel, open one report on GitHub in Chrome and try **Listen to this page →
AI playback**, then *Standard*. If the AI summary is all you ever want, the digest tier is
the priority. If you keep wanting the details, prioritize full editions.

### Phase 1: on-demand editions via Telegram (~1–2 days)

1. `sase-listen render <script.md>`:
   - parse frontmatter and `##` chapters;
   - apply the lexicon;
   - run the engine per chunk (`gemini` first, `kokoro` second);
   - duration sanity check, concatenate with short gaps, `loudnorm` to −16 LUFS;
   - MP3 64 kbps mono with title, artist, cover and CHAP frames (`mutagen`).
2. `#research/audio` xprompt in `sase-research-artifacts`: write `<stem>_narration.md`,
   render, then `sase notify create` with the MP3 in `files`.
3. `sase-telegram`: add `_is_audio_file` → `send_audio`, with title, performer, duration
   and the infographic as thumbnail.
4. Companion exclude glob for `_narration.md`, so the research inventory and Highlights
   ignore scripts.

### Phase 2: podcast feed and swarm stage (~1–2 days)

5. `sase-listen publish`: copy into the media directory on apollo, regenerate `feed.xml`,
   apply retention.
6. `tailscale funnel --bg --https=8443` serving only that directory under a secret path.
   Subscribe in AntennaPod with auto-download and add-to-queue.
7. `#research_swarm audio=true` stage (fork the lead), and `audio_model` defaulting to a new
   `@audio` alias.

### Phase 3: daily digest and hardening

8. A `research-audio` file hook that enqueues new reports, a morning scheduler job, and
   the `#research/digest` xprompt.
9. ASR quality gate, `brief` editions, a selective backfill (e.g. "the last 30 days I
   starred"), and an optional two-host flavor for digests.

### Validation still owed (needs live API calls I did not make)

- Render one 12-minute narration with `gemini-3.8-flash-tts`. Measure wall time, check for
  drift or silences across chapter chunks, and confirm the real cost against the ~$0.16
  estimate.
- Confirm which billing tier the `gemini_cli_api_key` uses. Free-tier TTS request caps are
  too low for daily use.
- A/B one chapter on Gemini `Charon`/`Kore`/`Iapetus` versus Kokoro `af_heart` on the actual
  commute (with traffic noise). Arena Elo is measured on short clips, and long-form fatigue
  may rank them differently.

### Open questions for you

- Should the digest also cover **plans** (`plans` sidecar) and **Obsidian notes**? If so,
  route private sources to Kokoro and a separate feed token.
- Two-host conversational digests (more fun on a walk), or one narrator (denser)? This
  report recommends one narrator and adding the dialogue flavor later.

---

## Appendix A: Benchmark reproduction

```bash
uv venv .venv && VIRTUAL_ENV=$PWD/.venv uv pip install kokoro-onnx soundfile
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
# bench.py: Kokoro("kokoro-v1.0.onnx","voices-v1.0.bin").create(text, voice="af_heart",
#           speed=1.0, lang="en-us"); report synth seconds vs len(samples)/sr
# GPU on driver 550 / CUDA 12.4:
VIRTUAL_ENV=$PWD/.venv uv pip install "onnxruntime-gpu[cuda,cudnn]==1.22.0"
ONNX_PROVIDER=CUDAExecutionProvider python bench.py …   # call onnxruntime.preload_dlls() first
# ASR gate prototype: faster-whisper base.en (int8, CPU) + jiwer WER
```

The corpus statistics came from `find 2026* -name '*.md'` over the research sidecar
(drafts excluded with `__<suffix>.md`), `grep -c` for Markdown features, and `wc -w`.

## Sources

- Artificial Analysis, Text to Speech leaderboard (incl. open-weights filter): <https://artificialanalysis.ai/text-to-speech/leaderboard>
- Gemini API pricing (TTS models, 25 audio tokens/s, Batch −50%, 2027 price step): <https://ai.google.dev/gemini-api/docs/pricing>
- Gemini 3.8 Flash TTS model card (8,192 in / 16,384 out, GA, long-form stability claim): <https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash-tts>
- Gemini speech generation guide (2-speaker cap, WAV 24 kHz, style control, 30 voices): <https://ai.google.dev/gemini-api/docs/speech-generation>
- Reports of long-form degradation and billed silence on Gemini 3.1 Flash TTS: <https://ttsaudit.com/blog/gemini-3-1-flash-tts-long-form-quality>, <https://discuss.ai.google.dev/t/gemini-3-1-flash-tts-bills-audio-tokens-for-minutes-of-digital-silence/183200>
- OpenAI API pricing (tts-1, tts-1-hd, gpt-4o-mini-tts): <https://developers.openai.com/api/docs/pricing>
- OpenAI speech API reference (4,096-char input, speed 0.25–4.0, formats): <https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create>
- OpenAI TTS guide (voices, `instructions`): <https://developers.openai.com/api/docs/guides/text-to-speech>
- OpenAI audio model update (gpt-4o-mini-tts-2025-12-15): <https://developers.openai.com/blog/updates-audio-models>
- ElevenLabs API pricing breakdowns: <https://flexprice.io/blog/elevenlabs-pricing-breakdown>, <https://www.cloudzero.com/blog/elevenlabs-pricing/>
- Breeze TTS 2 (3B, non-commercial weights): <https://www.mindstudio.ai/blog/breeze-tts-2-open-weight-model>, <https://www.stork.ai/blog/this-ai-beats-elevenlabs-dont-use-it>
- Open-source TTS overviews (Kokoro, Chatterbox, VibeVoice): <https://www.tryspeakeasy.io/blog/open-source-text-to-speech-2026>, <https://ocdevel.com/blog/20250720-tts>
- Kokoro-FastAPI: <https://github.com/remsky/Kokoro-FastAPI>
- kokoro-onnx model files: <https://github.com/thewh1teagle/kokoro-onnx/releases>
- edge-tts (status, SSML restrictions, past blocks): <https://github.com/rany2/edge-tts>
- Telegram Bot API `sendAudio` / `sendVoice` (MP3/M4A, 50 MB, music player): <https://core.telegram.org/bots/api#sendaudio>
- Telegram playback speeds for long audio: <https://x.com/telegram/status/1427981735044677638>, <https://telegram.tips/blog/granular-playback-speed/>
- Tailscale Funnel (ports 443/8443/10000; per-port public; no shared Serve/Funnel port): <https://tailscale.com/kb/1223/funnel>
- Private feeds and app fetch behavior (Pocket Casts/Overcast server-side; AntennaPod device-side): <https://www.thepodcasthost.com/publishing/which-podcast-apps-support-private-rss-feeds/>, <https://support.pocketcasts.com/knowledge-base/about-pocket-casts-feed-parser/>
- AntennaPod chapter support: <https://forum.antennapod.org/t/chapters-support/453>, <https://github.com/AntennaPod/AntennaPod/pull/5630>
- Prior art, hansharhoff/podcastfeeds (opened locally via `sase repo open gh:hansharhoff/podcastfeeds`): <https://github.com/hansharhoff/podcastfeeds>
- Podcastfy: <https://pypi.org/project/podcastfy/>
- NotebookLM / Gemini Notebook API status: <https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-audio-overview>, <https://autocontentapi.com/blog/does-notebooklm-have-an-api>
- Chrome Android "Listen to this page" AI playback and background play: <https://www.itechguides.com/chromes-listen-to-this-page-just-got-a-major-upgrade-on-android/>, <https://phonearena.com/news/chrome-for-android-adds-background-playback-for-listen-to-this-page-feature_id163926>
- Local SASE sources: `sase-research-artifacts` (`provider.py`, `xprompts/research_image.md`, `xprompts/research_swarm.md`, `default_config.yml`), `sase-telegram` (`telegram_client.py`, `scripts/sase_tg_outbound.py`, `inbound_handlers/text_messages.py`), `docs/configuration.md#file_hooks`, `docs/mobile_gateway.md`, `~/.config/sase/sase.yml` (`research-highlights` → `bob highlights create`), and `tailscale serve status` / `tailscale status` on apollo.
