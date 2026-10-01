# Markdown research to commute audio

- **Researcher:** grk (`research.z.grk`)
- **Date:** 2026-10-01
- **Question:** What is the best way to turn SASE research-sidecar markdown into audio that is actually pleasant to listen to while commuting or walking?
- **Depends on:** none. Related prior art: `research:202606/sase_audio_generation_consolidated.md` (PDF-to-podcast / NotebookLM-style two-host overviews). This request is a different job: **verbatim-enough narration of markdown**, delivered into a phone player, offline.

## Recommended solution

Build a small SASE-owned **listen pipeline** with three stages, and reuse existing commute players for everything after the file exists.

1. **Markdown → spoken script.** Deterministic rewrite: drop YAML frontmatter and source-index URL dumps; speak heading text as chapter titles; speak link labels and skip raw URLs; replace fenced code with a one-line omission; turn small tables into sentences and skip large ones; apply a SASE pronunciation lexicon (`xprompt`, `stitch`, `bead`, `ACE`, `TUI`, …).
2. **Script → chaptered audio.** Default engine: local **Kokoro-82M** (Apache-2.0, ~327 MB, CPU, $0, private). Cloud upgrade: **Gemini 3.8 Flash-Lite TTS** (`gemini-3.8-flash-lite-tts`) for nicer long-form recitation at about **$0.54 per hour** of audio through 2026-12-31. Pack as **M4B with chapters from `##` headings**, plus MP3 for podcast apps.
3. **File → phone.** Write into a local listen library **outside git**. Publish a **private RSS** of the same files over Tailscale, and/or drop M4Bs into **Audiobookshelf** / a **Syncthing** folder. Listen in AntennaPod, Pocket Casts, or the Audiobookshelf app, which already have lock-screen controls, 1.5–2× speed, chapter skip, sleep timer, and offline download.

Ship the first version as an xprompt workflow (`#!listen`) plus a Python helper, not a Rust-core feature and not a first-class `sase audio` CLI. Keep audio as artifact kind `file`. Add modes later: `narrate` (default, this request), `brief` (5–8 minute LLM summary then TTS), `overview` (two-host Gemini dialogue, the 202606 design).

Validate commute UX this weekend with **abogen** (Kokoro + markdown chapters + M4B + Audiobookshelf push) on one real research file. Keep abogen as a spike. Do not take it as a SASE runtime dependency.

---

## 1. What the job actually is

The user already has markdown: agent research in the research sidecar (`sase/repos/research/<YYYYMM>/*.md`). The missing piece is **getting that content into the ears during dead time** (walk, commute, dishes), with enough fidelity that the listen replaces a later read.

That splits into four independent decisions:

| Decision | What it controls | What it does not |
| --- | --- | --- |
| Spoken-script rewrite | Whether code, URLs, and tables ruin the listen | Voice quality |
| TTS engine | Naturalness, cost, privacy, hardware | Phone UX |
| Container (M4B / MP3 / RSS) | Chapters, resume, podcast-app compatibility | Script quality |
| Delivery path | Whether the file is on the phone before you leave | Synthesis |

A two-host “Audio Overview” (NotebookLM, Podcastfy, the 202606 SASE recommendation) is a **summary product**. It is entertaining and short. It also throws away the tables, the dissenting alternatives, and the recommendation nuance that make research worth listening to. For this request, treat overview-style audio as an optional `overview` mode, not the default.

A corpus check of 27 research markdown files in `202609/` (peer-swarm `__cdx/__cld/__mus/__gem` names excluded) gives the listening budget:

| | Words | ~1.0× at 150 wpm | ~1.5× | ~1.75× |
| --- | --- | --- | --- | --- |
| Median | 2,490 | 17 min | 11 min | 9.5 min |
| p90 | 4,624 | 31 min | 21 min | 18 min |
| Max | 12,824 | 86 min | 57 min | 49 min |

Median reports fit a one-way commute at 1.5×. The p90 still fits a round trip. The tail needs chapter skip or a `brief` mode. The same corpus is **table-heavy** (median ~24 table-row markers) and **code-light** (median one fence pair). The rewrite step that handles tables and links will do more for listenability than a more expensive voice.

## 2. Prior SASE research, and what changed

`research:202606/sase_audio_generation_consolidated.md` (2026-06-14) recommended a SASE-native `audio_overview` xprompt that writes a two-host transcript, renders with Gemini TTS, falls back to OpenAI, and stores MP3 + transcript + manifest as `file` artifacts. That design still holds **for overview mode**.

Four months later, the TTS landscape and this use case have both moved:

- Gemini TTS left preview. **Gemini 3.8 Flash TTS** and **Flash-Lite TTS** shipped 2026-09-23 as generally-available recitation models, with native two-speaker staging, voice design, and (claimed) long-form timbre stability across concatenated requests.
- Local narration quality settled on **Kokoro-82M** as the default Apache-2.0 CPU model (Hugging Face downloads in the tens of millions per month; ONNX runners exist).
- **abogen** grew from “EPUB/PDF GUI” into markdown-in, M4B-with-chapters-out, plus Audiobookshelf upload. That is the commute-shaped container this request needs.
- xAI now has a standalone TTS API (`POST https://api.x.ai/v1/tts`, `$15 / 1M` characters, 60k character cap).
- This request names **markdown research + commute/walking**, so delivery and markdown hygiene outrank podcast-scriptwriting.

Keep the 202606 pipeline shape (extract → script → validate → synthesize → artifact). Change the default script from “two hosts riff” to “cleaned narration,” and add a phone-delivery stage the 202606 report left open.

## 3. Markdown is a hostile TTS input

Feeding raw `.md` to any engine produces a bad walk:

- YAML frontmatter and HTML comments spoken as words.
- ATX hashes, emphasis markers, and pipe tables read as punctuation salad.
- `[label](https://very-long-url)` spoken as the URL.
- Fenced code (CLI flags, JSON, Python) read character-by-character.
- Artifact refs (`research:202609/foo.md`, `bead:sase-19x`, `plan:202609/bar.md`) spoken as `research colon`.
- SASE jargon mispronounced (`xprompt`, `stitch`, `ACE`, `TUI`, `axe`).
- Trailing “Source Index” sections that are nothing but URLs.

A commute listen needs a **deterministic spoken-script pass** before any model sees the text. Suggested rewrite rules, in order:

1. Strip YAML frontmatter; lift `title` / `author` into M4B tags if present.
2. Drop HTML comments and image syntax; speak alt text only when it is a real sentence.
3. Headings: emit a chapter marker at each `##` (and optionally `###` when the section is long). Speak “Section: {title}.”
4. Links: speak the label; omit the destination. Autolinks and bare URLs become silence.
5. Inline code: speak the identifier if it is a word (`sase listen`); omit punctuation-heavy spans.
6. Fenced blocks: replace with “Code sample omitted.” (or “Command omitted.”). Never read the fence.
7. Tables: if ≤ 6 rows and ≤ 4 columns, speak as “{header}: {cell}; …”. Otherwise “Table of N rows omitted. See the markdown.”
8. Footnotes, citation keys, and a trailing Source Index / URL list: omit.
9. Apply a pronunciation lexicon (SSML `phoneme` / Kokoro overrides / a plain replacement table). Start with SASE terms; let the user extend it.
10. Collapse wrapping newlines inside paragraphs; keep blank lines as short pauses.

This pass is the SASE-specific work. Off-the-shelf audiobook tools (abogen, ebook2audiobook) parse markdown headings into chapters; they do not know SASE refs or this corpus’s table density. Own the rewrite. Call someone else’s TTS.

Keep the spoken script as a first-class artifact (`listen.md` or `listen.json` with chapter timestamps). Regenerating audio from an edited script is cheap; regenerating from raw markdown after a rewrite-bug is not.

## 4. TTS engines, ranked for this job

### 4.1 Local: Kokoro-82M (default)

Kokoro-82M is an 82-million-parameter StyleTTS-2-lineage model, Apache-2.0, ~327 MB (`kokoro-v1_0.pth`) or ~300 MB ONNX (~80 MB quantized). It ships 54 preset voices across 8 languages, no cloning, speed control, no GPU required.

Why it wins as the SASE default:

- **$0 and private.** Research markdown stays on the machine. That matches a sidecar full of unpublished design notes.
- **CPU-real.** Independent M3 Pro measurement: ~0.16× RTF (6× faster than playback) with `kokoro-onnx`. Xeon-class 16-thread boxes are slower than Apple Silicon; still fine as a batch job. A 17-minute median report is a few minutes of CPU.
- **CLI already exists.** `python3 -m kokoro -i spoken.txt -o out.wav --voice af_heart`. `kokoro-onnx`, `pykokoro`, and `stackvox` wrap the same weights. `remsky/kokoro-fastapi` exposes an OpenAI-compatible `/v1/audio/speech`, which is a convenient provider adapter.
- **License is clean for a tool SASE might ship.** Piper’s engine is GPL-3.0 (voices MIT). XTTS-v2 is CPML non-commercial and the Coqui org is gone.

Limits: English-first presets, no emotion dial, quality below Gemini 3.8 / ElevenLabs / Cartesia on blind tests. For a walk with 1.5× speed, it is good enough. Voice `af_heart` / `am_michael` / `bf_emma` are the usual narration picks.

Piper remains the fallback if Kokoro is too heavy on a tiny host: ~63 MB per English voice, GPL engine, more robotic, extremely fast (RTF ~0.03 on M5 Max in one 2026 bench). KittenTTS and Kyutai Pocket TTS are smaller 2026 CPU options; they do not yet have Kokoro’s tooling or voice set.

Heavier local models (Chatterbox MIT + cloning + watermark, Qwen3-TTS Apache-2.0 0.6B/1.7B, Fish S2 Pro, Dia2, VibeVoice) want a GPU and solve cloning or multi-speaker drama. They are a later `sase_tts` provider tier, not the commute MVP.

### 4.2 Cloud recitation: Gemini 3.8 Flash-Lite TTS (upgrade)

Google’s Gemini API TTS is built for **exact text recitation** (audiobooks, podcasts), distinct from the Live API. Current models, docs last updated 2026-09-30:

| Model | Role | Input / output tokens | Languages |
| --- | --- | --- | --- |
| `gemini-3.8-flash-tts` | Studio narration, two-speaker, dialects | 8,192 / 16,384 | 130 |
| `gemini-3.8-flash-lite-tts` | Bulk read-aloud, cheaper | 8,192 / 16,384 | 101 |

Important serving limit: Google bills audio at **25 tokens per second**, and the published output cap is 16,384 tokens ≈ **11 minutes of audio per request**. The “hours of continuous audio” claim is about **timbre stability across concatenated requests**, not a single-call hour. Chunk the spoken script on chapter or sentence boundaries into ≤10-minute pieces, request raw PCM (`audio/l16`) when stitching, keep the same prebuilt voice (`Kore` / `Charon` are the “informative” pair).

Launch pricing through 2026-12-31, then doubles on 2027-01-01:

| | Flash TTS | Flash-Lite TTS |
| --- | --- | --- |
| Text in | $0.50 / 1M tokens | $0.50 / 1M tokens |
| Audio out | $9 / 1M tokens | $6 / 1M tokens |
| ≈ per hour of audio | $0.81 | $0.54 |
| Batch audio out | $4.50 / 1M | $3.00 / 1M |

A median 17-minute narration is about **$0.15** on Flash-Lite at launch rates, **$0.30** after the 2027 doubling. Free-tier exists with low rate limits.

Gemini 3.8 treats `text` as a **verbatim transcript**. Style goes in `speech_metadata.style`; laughs and pauses go in `<laugh>` / `<short pause>` tags. Stage directions left in the text get spoken. That is exactly what a cleaned narration script wants, and exactly why the rewrite pass must strip markdown syntax first.

Native two-speaker mode is capped at two **prebuilt** voices per request. Custom designed/replicated voices have to be synthesized per turn and stitched. Use this for `overview` mode; skip it for `narrate`.

### 4.3 Cloud fallbacks

**OpenAI `gpt-4o-mini-tts`.** Streaming MP3, 13 voices (`marin` / `cedar` recommended), `instructions` for delivery. **2,000 input tokens** per request (~1,500 words, ~10 minutes), so a median report is two chunks and the tail is ~9. Pricing is token-based ($0.60 / 1M input, $12 / 1M audio output). Policy requires disclosing that the voice is AI-generated. Fine as “user already has an OpenAI key” fallback. No native two-speaker.

**xAI Grok TTS.** `POST https://api.x.ai/v1/tts`, voices include Eve / Ara / Rex / Sal / Leo plus a larger 2026 roster, speech tags (`[laugh]`, `<whisper>`, `<pause>`), MP3/WAV/PCM/μ-law/A-law, **60,000 character** cap (covers every report in the 202609 corpus in one call). Price: **$15 / 1M characters**. A median ~15k-character spoken script is ~$0.23; a max report is ~$0.80–1.20. Roughly 8–10× Gemini Flash-Lite per hour of audio. Attractive only because SASE already speaks xAI, not because it is the right default.

**ElevenLabs / Cartesia Sonic.** Best blind-test quality (Cartesia Sonic 3.6 led one 2026 arena; Gemini 3.8 Flash TTS was second). ElevenLabs Text-to-Dialogue and Studio podcast APIs exist; Studio podcast create is allowlisted. Cost and voice-cloning policy are heavier than this feature needs. Premium opt-in later.

**edge-tts (Microsoft Edge Read Aloud).** MIT wrapper, 400+ neural voices, no API key, broadcast-quality `en-US-AvaNeural`. It is an unofficial scrape of a browser endpoint. Quality and price ($0) are excellent for a personal spike. It is a poor default for a tool SASE might ship: ToS, breakage, and text leaving the machine toward Microsoft with no contract.

**NotebookLM Audio Overviews.** Still the quality benchmark for *overview* mode. Free tier: 3 generations / rolling day; Pro: 20. Download MP3 or share a link. **No RSS, no editable transcript, no SASE artifact graph, source leaves the machine, daily quota.** The NotebookLM Enterprise Podcast API remains a Google Cloud product with a separate allowlist history; the 202606 report already rejected it as a SASE backend. Keep NotebookLM as a manual “I want a fun summary of this PDF tonight” workaround.

### 4.4 Cost sketch for this corpus

Spoken-script length is a bit under raw word count after dropping tables/URLs/code. Using raw words as an upper bound:

| Engine | Median report | p90 | Max |
| --- | --- | --- | --- |
| Kokoro local | $0 | $0 | $0 |
| Gemini 3.8 Flash-Lite (launch) | ~$0.15 | ~$0.28 | ~$0.77 |
| Gemini 3.8 Flash-Lite (2027) | ~$0.30 | ~$0.56 | ~$1.54 |
| Grok TTS | ~$0.23 | ~$0.42 | ~$1.20 |
| OpenAI mini-TTS | a few cents (chunked) | similar | similar |
| ElevenLabs ballpark | $0.75–1.50 | $1.40–2.80 | $4–8 |

Volume is tens of reports a month, not thousands. Cost is not the constraint. **Privacy, markdown hygiene, and phone UX are.**

## 5. Off-the-shelf pipelines (steal ideas, keep ownership)

| Tool | What it is | Markdown | Chapters / M4B | Commute delivery | SASE fit |
| --- | --- | --- | --- | --- | --- |
| **abogen** 1.3.x (MIT, Kokoro, optional Supertonic) | GUI + `abogen-web` Flask + queue | Yes (PR #75: headers → chapters, YAML metadata) | M4B, MP3, OPUS, SRT | **Pushes to Audiobookshelf** | Best **spike**. GUI/web-first, PyQt, LLM normalization, overlapping orchestration. Do not vendor. |
| **ebook2audiobook** (DrewThomasson, 20k★) | CPU/GPU ebook → M4B, many TTS backends including Kokoro | EPUB/PDF/TXT/HTML; markdown is not a first-class input | Yes | Folder of M4Bs | Useful engine list; Calibre-shaped, not markdown-shaped. |
| **Podcastfy** 0.4.3 | URL/PDF/text → two-host MP3 | Text, not research-sidecar aware | MP3 | Download | The 202606 spike. Overview mode only. |
| **podvoice** | Markdown speaker blocks → XTTS | Script format, not reports | WAV/MP3 | File | Wrong input dialect. |
| **bb-chiefofstaff `md2podcast.py`** | Strip markdown, chunk 4k chars, edge-tts, ffmpeg, optional RSS | Yes | MP3 + RSS | Exactly the commute RSS idea | Tiny and copyable. Edge-tts ToS. |
| **OpenAI-agents markdown→podcast blogs** | LLM scriptwriter + OpenAI TTS stitch | Yes | MP3 | File | Overview mode. |
| Phone readers (@Voice, Voice Dream, Speechify, Android Select to Speak) | On-device TTS of EPUB/HTML | After `pandoc` | App-dependent | Already on the phone | **Zero-build workaround.** Poor on tables/code/SASE terms. |

**Weekend spike (no SASE code):** install abogen or `kokoro` + ffmpeg on the workstation, convert `research:202606/sase_audio_generation_consolidated.md` (2.3k words, 15 minutes) to M4B, copy to the phone, walk. That single listen will decide voice, speed, and whether tables-omitted is acceptable.

## 6. Delivery is the commute feature

Synthesis that leaves a WAV on the workstation is unfinished. Walking needs:

- File already on the phone (or streamable on Tailscale with a download-for-offline button).
- Lock-screen / Bluetooth / Android Auto controls.
- Speed 1.5–2× without chipmunk artifacts (player-side time-stretch, not TTS-speed, so one file serves every pace).
- Chapter skip aligned to `##` headings.
- Resume across headphone disconnects.
- Sleep timer.

Existing apps already do this. SASE should not grow a player, and the Android mobile gateway (`docs/mobile_gateway.md`) is an agent-control surface, not an audiobook client.

### 6.1 Ranked delivery paths

**A. Private RSS over Tailscale (best everyday UX).** Generate `feed.xml` + `*.mp3` in a listen directory. Serve with Caddy/nginx bound to the Tailscale IP. Subscribe once in AntennaPod (Android) or Pocket Casts. New episodes appear on the next feed refresh; download on Wi-Fi before leaving. Chapters in RSS 2.0 are weaker than M4B, so also attach a chaptered M4B enclosure or a `psc:chapters` block. A 40-line `feedgen` script is enough. This is how “it shows up in the podcast app I already open on the train” works.

**B. Audiobookshelf library (best chapter/progress UX).** Drop M4Bs into an ABS “Research” library, or let abogen-web push via API token. Official Android app: offline download, speed, sleep timer, progress sync. ABS can also **host an RSS feed** of a library item for other clients. Extra moving part (Docker on a home box). Worth it if the user already wants an audiobook server.

**C. Syncthing / folder sync (simplest ops).** Write M4Bs to `~/Listen/research/`. Syncthing to `/storage/emulated/0/Audiobooks/research/`. Smart Audiobook Player or Listen Audiobook Player scan the folder. No server. Chapters work. Feed/auto-download does not.

**D. Telegram audio send (one-off).** Convenient for “make this one now.” Telegram’s in-app player is a weak commute client (speed, chapters, resume). Keep as a `--notify telegram` side path after the file exists.

**E. SASE artifact only.** `sase artifact create -k file` stores an immutable snapshot for the Agents tab. It does not get the file onto the phone. Do this **in addition** to A–C, never instead.

Do not commit M4B/MP3 into the research git sidecar. A 17-minute 64 kbps MP3 is ~8 MB; a month of research would bloat the sidecar and the clone. Artifacts store + a local listen directory are the right homes.

### 6.2 Zero-build workaround (today)

```text
pandoc report.md -t epub -o report.epub
# or: pandoc report.md -t html -o report.html
```

Copy to the phone and open in @Voice Aloud / Voice Dream / Speechify. Works this afternoon. Tables and code will be ugly. Use it only to confirm that listening to research is something the user actually does more than twice.

## 7. SASE implementation shape

Match the 202606 recommendation on **where** the code lives, and specialize the **what**.

### 7.1 First interface: xprompt, then CLI

```text
#!listen(source=research:202610/markdown_research_to_commute_audio__grk.md, mode=narrate, voice=af_heart, out=m4b)
```

Later, if the workflow is used:

```bash
sase listen research:202610/foo.md --mode narrate --provider kokoro --voice af_heart
sase listen research:202610/foo.md --mode brief --minutes 6 --provider gemini
```

A first-class CLI before a handful of real listens violates `corpus-before-mechanism`. An xprompt plus a helper module is enough to generate, attach artifacts, and copy into `listen_dir`.

### 7.2 Pipeline

```text
source.md
  → resolve artifact ref (sase artifact path / sase repo)
  → spoken script + chapter map          [SASE-owned, snapshot-tested]
  → optional LLM brief/overview pass     [existing sase_llm]
  → TTS chunks (kokoro | gemini | openai | grok)
  → ffmpeg: concat, loudnorm, chaptered M4B + MP3
  → artifacts: audio, listen.md, chapters.json, generation_manifest.json
  → copy to listen_dir; append RSS item; optional ABS/Telegram
```

Implementation notes:

- Cache on `(source hash, rewrite version, provider, model, voice, speed)`. Editing the rewrite should not resynthesize unchanged chapters.
- Generate at TTS speed 1.0. Let the phone player do 1.5–2×. One file, every pace.
- ffmpeg is required for M4B/MP3/loudnorm. It is a workstation dependency, not a Python extra of the SASE runtime. The 202606 report already wanted to keep audio deps off the default install; keep it that way (optional extra or an external helper venv).
- `generation_manifest.json` records provider, model, voice, source hash, rewrite version, chunk IDs. No API keys.
- Artifact kind stays `file` until ACE actually needs playback chrome.
- This is Python + xprompt glue. It does not belong in `sase-core` until a second frontend needs the same job state.
- Pronunciation lexicon as YAML under user config (`listen.lexicon`), not hardcoded only in the helper.

### 7.3 Modes

| Mode | Script | Engine | When |
| --- | --- | --- | --- |
| `narrate` | Deterministic rewrite of the full markdown | Kokoro default, Gemini Flash-Lite upgrade | Default; this request |
| `brief` | LLM 5–8 min spoken summary, then TTS | Same engines | p90/max reports, or “give me the rec on the walk to the station” |
| `overview` | Two-host grounded transcript (202606 design) | Gemini 3.8 Flash TTS two-speaker | When the user wants a podcast, not the paper |

`brief` is the important second mode. A 86-minute max report at 1.5× is still an hour. Many commutes are not that.

### 7.4 What not to build in v1

- A SASE audio player, ACE waveform widget, or Android-gateway playback.
- Vendor of abogen, Podcastfy, or ebook2audiobook.
- Voice cloning / “sound like me.”
- Committing audio into the research sidecar.
- Auto-synthesizing every research file on stitch. Queue or explicit `#!listen` until the user is in the habit. Overnight batch on an allowlist of paths is a v2 ops story.

### 7.5 Suggested rollout

**Week 0 (personal, no SASE PR).** ffmpeg + `uv tool install` kokoro or abogen. One real report → M4B → phone folder or AntennaPod local file. Walk. Write down: voice, omitted-table tolerance, whether 1.5× is enough.

**v1 (SASE).** Spoken-script rewrite with tests against a fixture of research markdown (heading, table, fence, link, artifact ref, source index). Kokoro provider. M4B + MP3. `sase artifact create -k file`. Copy to configured `listen.dir`. xprompt `#!listen`.

**v1.1.** Private RSS writer. Gemini Flash-Lite provider. `brief` mode. Chapter-level cache.

**v2.** `overview` mode (reuse 202606). `sase listen` CLI. Optional Audiobookshelf push. Optional `audio` artifact kind if ACE grows a preview. Piper/Qwen3-TTS as offline alternatives.

## 8. Risks

- **Kokoro quality at 1.5×.** If the walk test says the voice is tiring, switch the default provider to Gemini Flash-Lite without changing the rest of the pipeline. The rewrite and M4B layers stay.
- **Gemini 11-minute output cap.** Any cloud path must chunk. Chapter boundaries from `##` are the right cut points.
- **Gemini price doubles 2027-01-01.** Local default plus a cloud upgrade ages well.
- **edge-tts breakage / ToS.** Keep it out of shipped SASE.
- **Table omission hiding the recommendation.** Many SASE reports put the decision in a table at the top. The rewrite should special-case a leading “Recommended solution” table: speak it, even if large.
- **Binary bloat.** Listen library and artifact store only.
- **Pronunciation.** Wrong SASE jargon will annoy more than a slightly robotic vowel. Ship the lexicon on day one.
- **Auto-generation surprise.** Synthesizing a 12k-word report unattended is 50 minutes of audio and minutes-to-tens of CPU. Explicit invoke until proven.

## 9. Source index

- SASE prior art: `research:202606/sase_audio_generation_consolidated.md`
- Gemini TTS guide (3.8 Flash / Flash-Lite, recitation vs Live API, two-speaker, limitations): https://ai.google.dev/gemini-api/docs/speech-generation
- Gemini 3.8 Flash TTS model card (8,192 / 16,384 tokens, audiobook role): https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash-tts
- Gemini 3.8 Flash-Lite TTS model card: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash-lite-tts
- Gemini 3.8 TTS launch: https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-8-text-to-speech/
- OpenAI TTS guide (`gpt-4o-mini-tts`, 2,000-token input, disclosure): https://developers.openai.com/api/docs/guides/text-to-speech
- OpenAI `gpt-4o-mini-tts` model page: https://developers.openai.com/api/docs/models/gpt-4o-mini-tts
- xAI TTS (`POST /v1/tts`, 60k chars, $15/1M chars): https://docs.x.ai/developers/model-capabilities/audio/text-to-speech
- xAI pricing (Voice API): https://docs.x.ai/developers/pricing
- Kokoro-82M model card: https://huggingface.co/hexgrad/Kokoro-82M
- Kokoro CLI: https://github.com/hexgrad/kokoro
- kokoro-onnx: https://github.com/thewh1teagle/kokoro-onnx
- Piper current repo (GPL-3.0 engine): https://github.com/OHF-Voice/piper1-gpl
- abogen (markdown, M4B, Audiobookshelf): https://github.com/denizsafak/abogen
- abogen PyPI 1.3.1: https://pypi.org/project/abogen/
- abogen markdown PR: https://github.com/denizsafak/abogen/pull/75
- ebook2audiobook: https://github.com/DrewThomasson/ebook2audiobook
- Podcastfy: https://github.com/souzatharsis/podcastfy
- Audiobookshelf RSS hosting: https://www.audiobookshelf.org/guides/rss_feeds/
- NotebookLM Audio Overviews help: https://support.google.com/notebooklm/answer/16212820
- Hume multi-speaker eval of Gemini TTS (2026-09-29): https://hume.ai/blog/evaluating-multi-speaker-tts
- Local TTS licence/size roundup (2026-09-23): https://www.bestfreewebresources.com/best-local-text-to-speech-2026

## Recommended solution (restated)

Implement **cleaned narration of research markdown into a chaptered M4B**, defaulting to **local Kokoro-82M**, delivered by **private RSS and/or a Syncthing/Audiobookshelf listen library** into a phone app the user already uses on walks.

Own three things in SASE: the markdown→speech rewrite (including a SASE lexicon and table rules), a thin TTS provider adapter (Kokoro, then Gemini 3.8 Flash-Lite, then OpenAI), and artifact + listen-dir + RSS publishing. Borrow commute playback from AntennaPod / Audiobookshelf. Spike with abogen this week to prove the walk is worth the build. Keep NotebookLM-style two-host audio as an opt-in `overview` mode on top of the 202606 design, and add a `brief` mode for reports that overrun a commute.

The first concrete artifact of a later implementation should be a golden-test of the rewrite against a real research file, not a new TUI surface.
