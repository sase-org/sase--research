# Markdown to Audio for Commuting and Walking

- **Researcher:** `mus` (5-researcher swarm, independent report)
- **Date:** 2026-10-01
- **Context:** audio versions of markdown files such as agent research stored in the
  research sidecar repo, for listening while commuting / walking
- **Workspace:** `sase-org/sase`

## 1. Executive summary

Turning research markdown into listenable audio is a four-stage pipeline, and the
stages matter more than the voice engine:

1. **Extract** markdown to *speakable text* (strip/summarize code, tables, links).
2. **Synthesize** speech with a TTS engine.
3. **Package** as chapterized audio (MP3 chapters or a single M4B audiobook).
4. **Deliver** to the phone with offline playback (audiobook app or private feed).

The uncomfortable finding is that stage 1 dominates quality: research markdown
(code fences, pipe tables, bare URLs, `[[links]]`) sounds terrible when read
literally by any engine, however natural its voice. Any implementation that skips
the cleanup step will produce unlistenable output regardless of engine choice.

**Recommendation (two tiers):**

- **Today, zero build:** use the free **ElevenReader** mobile app (paste or upload
  the markdown) for commute listening. If the content is sensitive, use offline
  phone TTS instead (Voice Dream Reader on iOS, @Voice Aloud on Android).
- **Durable solution:** build a small `md2audio` script in this repo that runs
  `markdown → pandoc plain text → speakable-text cleanup → edge-tts (free,
  verified working, §6) → chapterized MP3/M4B → Audiobookshelf or a private
  podcast RSS feed`. Keep a local-engine fallback (**Piper** for speed, **Kokoro**
  for quality) for sensitive or offline use. Details in §7.

## 2. Source material profile

To ground the recommendation I measured the actual corpus rather than guessing:

- The `202609/` research month holds dozens of reports; sampled word counts run
  roughly **5,000–13,000 words** per report (112,405 words total across that
  month's files), i.e. roughly **30–90 minutes of audio each** at conversational
  pace (~800–900 chars/min, ~150 wpm).
- Reports are documentation-shaped markdown: H1–H4 headings, bullet lists, fenced
  code blocks, GFM pipe tables, markdown links, and SASE `[[memory links]]`.
- I verified `pandoc -f markdown -t plain` converts this shape to clean
  paragraphs on this machine, but it keeps tables as ASCII grids and code as
  literal text — acceptable as a first pass, not as narration-ready output.

Implication: headings map naturally to **audio chapters**, and the content volume
(30+ min per report) justifies chapter marks and 1.2–1.5x playback support
rather than one flat MP3 per file.

## 3. The pipeline and why each stage exists

| Stage | Job | Failure mode if skipped |
|---|---|---|
| Extract → speakable text | Headings to chapter breaks; code fences to "code omitted, see report" or a one-line gloss; tables to sentences; links to link text only | Listener hears "vertical bar dash dash vertical bar" and raw URLs |
| Synthesize | Chunk text at sentence boundaries (~1–2k chars) for engine limits and retries | One giant request fails or bills badly; no resume |
| Package | Join chunks; embed chapter marks (MP3 ID3 chapters or M4B) | No navigation on a 60-minute walk |
| Deliver | Offline files on the phone (audiobook app, private RSS) | Commute dead zones kill streaming |

A published preprocessing checklist for exactly this problem (markdown → TTS)
confirms the pattern: remove non-speech characters, convert tables to spoken
sentences, and never feed raw markdown to the engine
([clean_tts_text prompt](https://github.com/luizomf/dotfiles/blob/HEAD/prompts/clean_tts_text.md),
[tts preprocessing rules](https://github.com/arunskiorg/benarunskiutils/blob/HEAD/skills/tts/reference/preprocessing-rules-1.md)).

## 4. Options evaluated

### A. Zero-setup phone apps (no implementation)

- **ElevenReader** (free, iOS/Android, 32+ languages): upload docs, paste text, or
  open links; narrates with ElevenLabs voices. Explicitly positioned as a commute
  companion
  ([Play Store listing](https://play.google.com/store/apps/details?id=io.elevenlabs.readerapp&hl=en_SG)).
  Best voice quality for zero effort; content passes through ElevenLabs servers.
- **Speechify** (~$139/yr reported in 2026,
  [review](https://www.fahimai.com/speechify)): imports files/links, offline
  caching on paid tier, AI summaries. Good but paid and weaker voices than
  ElevenReader per comparative reviews
  ([review](https://memeburn.com/speechify-review/)).
- **Voice Dream Reader** (iOS, one-time purchase): offline, highlighting, best
  for Apple users who want on-device privacy.
- **Pocket / Readwise Reader**: fine for articles, awkward for local markdown
  files; not recommended as the primary path.

Verdict: fastest route to value, but no automation, no chapters from markdown
structure, and cloud processing of possibly-sensitive research.

### B. edge-tts: free neural voices, scriptable (verified)

`edge-tts` drives Microsoft's Edge Read-Aloud voices: no API key, no quota,
quality close to paid neural TTS. It is the default engine in several
markdown/PDF-to-audiobook projects
([pdf-to-audiobook](https://github.com/lakens/pdf-to-audiobook),
[audiobook-manager](https://github.com/theboscoclub/audiobook-manager/blob/HEAD/docs/MULTI-LANGUAGE-SETUP.md),
[doc2audibook](https://github.com/raymondariwoola/doc2audibook)).

**I verified this path on this machine (2026-10-01):** `pip install edge-tts`,
`--list-voices` returned hundreds of voices, and a sample synthesis produced a
valid 18 KB MP3. Exact commands in §6.

Caveats: it is an *unofficial* endpoint — Microsoft rate-limits datacenter IPs
and could break it at any time (a hosted audiobook service reports exactly this
and retries/falls back,
[note](https://github.com/sriramvsharma/audiobook-maker/blob/HEAD/skill/audiobook-narrator/SKILL.md)).
Fine as the default; not as the only engine. Also note one implementation
detail: edge-tts takes plain text, not SSML prosody tags
([reference](https://github.com/arunskiorg/benarunskiutils/blob/HEAD/skills/tts/reference/preprocessing-rules-1.md)).

### C. Local/offline engines: Piper vs Kokoro

For sensitive research (unpublished findings, private sidecar content) or fully
offline use, synthesize on-device:

- **Piper** (VITS-based): tiny, CPU-friendly, many voices/languages; roughly
  **7–9x faster than real time on CPU** in independent measurements
  ([benchmark](https://dev.to/obole/kokoro-82m-computed-slower-than-it-spoke-piper-tts-was-87-to-93-times-faster-3lgh),
  [voicebox](https://github.com/mdwoicke/local-jarvis-voicebox)). Quality is
  "clear but not human-like"
  ([engine guide](https://github.com/ireaderorg/ireader/blob/HEAD/docs/guides/tts.md)).
- **Kokoro-82M** (Apache-2.0): the most natural open-weight TTS at this size, but
  heavier (~300 MB+ download) and around real-time-or-slower on CPU
  ([engine guide](https://github.com/ireaderorg/ireader/blob/HEAD/docs/guides/tts.md),
  [dotnet-local-voice notes](https://github.com/blakehastings/claude-code-artifacts/blob/HEAD/dotnet-local-voice/SKILL.md)).

Verdict: Kokoro for quality, Piper for speed/batch. Either is the right fallback
when content should not leave the machine. Check per-voice licenses before
redistributing audio.

### D. Paid cloud APIs

For reference, using ~50k characters ≈ 1 hour of audio as the yardstick:

- **OpenAI TTS** (~$0.015/1k chars,
  [comparison](https://github.com/aiwolfie/text-to-speech-studio/blob/HEAD/README.md)):
  ≈ **$0.75/hr** — cheapest paid neural option, good quality, simple API.
- **ElevenLabs**: best voices, but subscription plus materially higher
  per-character pricing than OpenAI (multiples higher in published comparisons:
  [2026 comparison](http://dev.to/voice_developer/ai-voice-generators-in-2026-complete-comparison-guide-4m7j),
  [cost research](https://github.com/adrian333dev/flow/blob/HEAD/lab/research/tts.md)).
- **AWS Polly / Google Cloud TTS**: Polly Long-Form ≈ $100/1M chars and standard
  neural ≈ $16/1M; Google ≈ $16–20/1M
  ([comparison](http://dev.to/voice_developer/ai-voice-generators-in-2026-complete-comparison-guide-4m7j),
  [TTS price comparison](https://tech-insider.org/text-to-speech-api-gemini-vs-elevenlabs-2026/)).
  Solid but no advantage over OpenAI for this use case.

Verdict: only worth it if edge-tts reliability or local quality proves
insufficient. OpenAI TTS would be the paid pick.

### E. Verbatim vs digest ("podcast") mode

Two distinct products are being conflated in "listen to research":

1. **Verbatim narration** — the full report, cleaned. Best for deep material;
   code-heavy sections still listen poorly.
2. **Digest/briefing** — an LLM summarizes the report to ~5 minutes (or a
   two-host "podcast" script in the NotebookLM style), then TTS reads the
   summary. Best for triage on a short walk and for code-dense reports.

The durable script should support both: narrate the cleaned full text by
default, with a `--digest` flag that first summarizes via the agent's own LLM
and narrates the summary. Digest mode also sidesteps the worst preprocessing
problems (tables/code get summarized away).

### F. Getting audio onto the phone for offline walks

- **Audiobook apps with offline files** (Voice Dream, Smart Audiobook Player,
  Apple Books): accept M4B with chapters; simplest, most reliable offline story.
- **Audiobookshelf** (self-hosted): point it at a folder of generated M4B/MP3;
  phone app syncs and remembers position per report. Best if this becomes a
  habit across many reports.
- **Private podcast RSS**: a static feed of generated MP3s subscribed to in any
  podcast app gives auto-downloads, but requires hosting and authentication
  hygiene for private research. Only worth it at multi-report scale.
- **MP3 chapters vs M4B**: M4B (AAC + chapter marks) is the audiobook standard
  and bookmarks position; needs `ffmpeg` (not currently installed here — one
  `apt install ffmpeg`).

## 5. Comparison matrix

| Approach | Voice quality | Cost | Privacy/offline | Effort | Chapters |
|---|---|---|---|---|---|
| ElevenReader app | Excellent | Free | Cloud; online | None | No |
| edge-tts script | Very good | Free* | Cloud (unofficial); needs net | Small script | Yes (build it) |
| Piper (local) | Good/clear | Free | Fully offline | Small script | Yes (build it) |
| Kokoro (local) | Excellent | Free | Fully offline | Medium (300 MB+, slower) | Yes (build it) |
| OpenAI TTS | Very good | ~$0.75/hr | Cloud; billed | Small script | Yes (build it) |
| ElevenLabs | Best | $$ | Cloud; billed | None (app) or API | Via app: no |

*Free but unofficial; treat as volunteer infrastructure with a fallback.

## 6. Verified building blocks (ran on 2026-10-01)

```bash
pip install edge-tts            # --break-system-packages on this PEP-668 box
edge-tts --list-voices | head   # hundreds of voices (e.g. en-US-AvaNeural)
echo '# T ...' | pandoc -f markdown -t plain > clean.txt
edge-tts --voice en-US-AvaNeural --text "Hello world." --write-media out.mp3
```

Observed: `out.mp3` was a valid 18 KB MP3 for one sentence; long documents
must be chunked at sentence boundaries and concatenated (existing projects do
exactly this, e.g.
[pdf-to-audiobook](https://github.com/lakens/pdf-to-audiobook/blob/HEAD/README.md)).
Missing pieces on this box: `ffmpeg` (for M4B chapters), Piper/Kokoro voices
(not installed; no install attempted to keep this turn read-mostly).

## 7. Recommended solution

**Tier 1 — start listening today (no code):** install **ElevenReader**, upload or
paste the research markdown before leaving. Zero implementation, best voices,
works for the commute use case as-is. Don't use it for sensitive unpublished
research; use the phone's offline TTS for that.

**Tier 2 — durable `md2audio` pipeline (the actual implementation, small):**
a script, e.g. `sase research listen <artifact-ref> [--digest]`, that does:

1. Resolve the markdown via `sase artifact read` (audited, works for sidecar
   content) or a file path.
2. Convert with pandoc to plain text, then apply speakable-text cleanup:
   headings → chapter breaks; fenced code → kept only if short, else replaced
   with "code example omitted, see the report"; tables → sentence form or
   dropped with a pointer; links/`[[memory links]]` → link text only; strip
   `^ ~ | \` and similar TTS-hostile symbols (the same strip-list used by
   [pdf-to-audiobook](https://github.com/lakens/pdf-to-audiobook/blob/HEAD/README.md)).
3. Chunk at sentence boundaries (~1,500 chars), synthesize with **edge-tts**
   default and **Piper** fallback for sensitive/offline content, concatenate.
4. Emit **one M4B with chapter marks per H2** (needs `ffmpeg`); fall back to
   chapterized MP3s if ffmpeg is absent.
5. Drop output into an **Audiobookshelf** library (or a synced folder the
   phone's audiobook app reads). Add `--digest` to narrate an LLM summary
   instead of the full text for code-dense reports or short walks.
6. Optionally add a private RSS only once the library habit sticks.

Why this shape: the cleanup stage (§3) is where quality is won; edge-tts gives
near-paid quality free with a verified working path (§6); Piper covers the
privacy/offline gap cheaply; M4B+Audiobookshelf solves position memory and
offline playback, which is what commuting actually needs. Paid APIs add nothing
until free quality proves insufficient — then OpenAI TTS is the upgrade, not a
redesign, since only the synthesis call changes.

Estimated build: a day for the edge-tts + MP3 path, another day for M4B
chapters, cleanup tuning, and the `--digest` mode.

## 8. Risks and open questions

- edge-tts is unofficial and rate-limited from datacenters; the Piper fallback
  is load-bearing, not decorative.
- Sidecar research may be private: default cloud synthesis leaks content to a
  third party. The script should warn (or refuse) on cloud engines for
  non-public paths unless `--allow-cloud` is passed.
- Voice cloning / personalized voices deliberately out of scope.
- Phone OS unknown: exact Tier-1 app pick (Voice Dream vs @Voice vs stock)
  depends on iOS vs Android; ElevenReader covers both.

## Sources

All links above were fetched during this research. Pricing figures are
third-party reported 2026 numbers and should be rechecked at build time; the
per-hour math assumes ~50k chars/hour. Benchmarks (Piper 7–9x realtime, Kokoro
heavier/slower) come from the cited independent measurements, not from this
box — the only claims verified locally are the pandoc conversion and the
edge-tts sample synthesis in §6.
