# From agent Markdown to commute-ready audio

**Research date:** 2026-10-01  
**Researcher:** cdx  
**Decision sought:** the best practical way to turn Markdown documents, especially SASE research artifacts, into audio that is pleasant and convenient to consume while walking or commuting.

## Executive conclusion

Build a small, provider-neutral **Markdown-to-M4B** command, use **OpenAI `gpt-4o-mini-tts-2025-12-15`** as the initial quality-first renderer, offer a **local Kokoro-82M endpoint** for private/offline material, and place completed M4B files in an **Audiobookshelf** library for offline phone playback, chapter navigation, and synchronized progress.

The important product is not a call to a TTS API. It is a reproducible narration pipeline: parse Markdown semantically, remove visual-only material, preserve a faithful spoken transcript, split at safe structural boundaries, cache every rendered chunk, validate the audio, assemble headings into chapters, and retain a manifest linking the listening copy to its source artifact. This is small enough to own, while speech synthesis itself should remain swappable.

For an immediate experiment, AudioPapers is almost exactly the desired workflow. It is useful as a reference implementation and perhaps a disposable trial, but its current repository is too young to make it the durable foundation. Text2Audio is a stronger reference for local rendering, caching, retries, mastering, and resumability, but its browser studio and GPU-oriented dependency set are more than this workflow needs.

## What the solution needs to optimize

The real requirements are broader than “read a file aloud”:

1. **Low-friction capture.** A path or SASE artifact reference should become a listening item with one command. Re-running it should be cheap and safe.
2. **Good long-form listening.** The output needs chapter seeking, persistent position, speed control, offline download, and acceptable voices for 30–90 minute sessions.
3. **Faithfulness.** Research claims must not silently change. A concise “audio briefing” can be added later, but it must be a distinct derivative, not the default conversion path.
4. **Markdown-aware speech.** URLs, source lists, code blocks, tables, footnotes, YAML, and punctuation need explicit policies; naïvely stripping Markdown produces tiring or misleading narration.
5. **Resumability and provenance.** A network failure near the end of a long report must not restart the whole job. The output should record exactly which source, cleaning rules, provider, model, voice, and instructions produced it.
6. **Replaceable economics and privacy.** Ordinary research can use a high-quality hosted voice; sensitive material or disconnected operation needs a local route.
7. **A commute-grade delivery experience.** A generated file on a server is not yet a usable product.

## Provider findings

### OpenAI: best initial default

OpenAI describes `gpt-4o-mini-tts` as its newest and most reliable speech model. It supports delivery instructions for accent, intonation, speed, and tone, exposes 13 built-in voices, and recommends `marin` or `cedar` for best quality. The endpoint can return MP3, Opus, AAC, FLAC, WAV, or PCM. The API reference limits one request to 4,096 characters, while the model page reports a 2,000-input-token limit, so a robust client should obey the tighter limit in practice and target roughly 3,000–3,500 characters per request. The model has a dated `2025-12-15` snapshot, which is preferable to a moving alias for reproducible audiobooks. [OpenAI TTS guide](https://developers.openai.com/api/docs/guides/text-to-speech), [model page](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts), [speech endpoint](https://developers.openai.com/api/reference/cli/resources/audio/subresources/speech/methods/create)

Published pricing is $0.60 per million text-input tokens and $12 per million generated audio tokens. That has historically worked out to roughly **$0.015 per generated minute**, so a 10,000-word report at 150 spoken words per minute is about 67 minutes and approximately **$1**. Treat this as an estimate and record actual billing because output duration, pauses, and delivery speed affect audio-token usage. The text-input charge is negligible relative to the generated audio. [OpenAI model pricing](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts)

Privacy is good enough for non-sensitive research but is not equivalent to local execution. OpenAI says API inputs and outputs are not used to train models by default. `/v1/audio/speech` has no application-state retention, but abuse-monitoring logs may retain customer content for up to 30 days unless the organization qualifies for modified abuse monitoring or zero data retention. [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)

Why it wins the default slot:

- Quality, steerability, and English optimization fit technical research.
- The per-document cost is small enough that engineering around a lower-priced but weaker voice is unlikely to pay back.
- WAV/PCM output, a stable snapshot, and a simple API make chunk caching and assembly straightforward.
- It avoids installing and operating a model on the first iteration.

The main risks are sending the document to a cloud provider, provider drift if an alias is used, and occasional chunk-level pronunciation or prosody differences. Pinning the snapshot, retaining the narration transcript, validating durations, and keeping a local alternative address these risks.

### Kokoro-82M: the right local/offline backend

Kokoro is an 82-million-parameter, Apache-2.0-licensed open-weight TTS model. Its model card lists 54 voices across eight release languages (the current voice inventory also includes Brazilian Portuguese), with multiple American and British English voices. The author warns that voices tend to perform best on chunks of about 100–200 tokens, may be weak below 10–20 tokens, and may rush above 400 tokens. Those constraints strongly favor paragraph-aware chunking instead of sending whole chapters. [Kokoro model card](https://huggingface.co/hexgrad/Kokoro-82M), [voice notes](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)

Kokoro has no per-use fee when self-hosted and keeps the document local. It is a sensible fallback for private notes, high volume, or no-network use. Its tradeoffs are operational dependencies (`espeak-ng`, a model runtime, and preferably acceleration), less reliable technical pronunciation, and less natural long-form expression than the strongest hosted voices. “Free” also excludes server power and maintenance.

[Kokoro-FastAPI at inspected commit `b4ef64b`](https://github.com/remsky/Kokoro-FastAPI/tree/b4ef64b1ce60682debda4fe0a066259e284eb1b4) is the cleanest adapter. At inspection it had 661 commits and tagged release 0.9.0, provides CPU/GPU multi-architecture containers, and exposes the same `/v1/audio/speech` shape as OpenAI. The renderer can therefore switch between hosted OpenAI and local Kokoro with configuration rather than a second orchestration pipeline. Pin an image version, bind it only to localhost or a private network, and do not expose the unauthenticated example endpoint to the public Internet.

### ElevenLabs and Google: viable, not first choices

ElevenLabs remains attractive when the narrator’s expressiveness is the priority. Its current v4 model supports 90+ languages and 10,000 characters per request; Multilingual v2 is explicitly positioned as stable for long-form generation. On 2026-10-01 its API page showed a temporary v4 promotion around $0.022 per 1,000 characters (roughly a minute) against an $0.08 list price. That can be competitive during the promotion, but it creates subscription/promotion coupling and offers little value for factual research narration beyond voice preference. [ElevenLabs models](https://elevenlabs.io/docs/overview/models), [API pricing](https://elevenlabs.io/pricing/api)

Google Cloud offers a broad voice/language catalog, SSML, and asynchronous long-audio synthesis up to one million input bytes. Chirp 3 HD is $30 per million characters after a one-million-character free tier; Neural2 is $16 per million and standard/WaveNet pricing is lower. The ordinary synchronous endpoint is limited to 5,000 bytes, so structural chunking is still needed. It is a sound enterprise alternative, but GCP project, IAM, bucket, and voice selection add setup without a clear advantage for this personal English narration workflow. [Google TTS pricing](https://cloud.google.com/text-to-speech/pricing), [quotas](https://docs.cloud.google.com/text-to-speech/quotas), [long-audio synthesis](https://docs.cloud.google.com/text-to-speech/docs/create-audio-text-long-audio-synthesis)

### Provider decision matrix

| Option | Long-form quality | Marginal cost | Privacy | Operations | Role |
|---|---:|---:|---:|---:|---|
| OpenAI `gpt-4o-mini-tts` | High, steerable | About $0.015/min estimate | Cloud; default monitoring retention | Low | Default |
| Local Kokoro-82M | Good enough after voice/chunk tuning | Near zero | Fully local | Medium | Private/offline fallback |
| ElevenLabs v4/v2 | Potentially highest expressiveness | Promo-dependent; list materially higher | Cloud | Low–medium | Optional premium voice |
| Google Chirp/Neural2 | High, broad language support | Low–moderate | Cloud | Medium | Enterprise/multilingual alternative |
| OS voices / eSpeak | Functional | Zero | Local | Low | Emergency fallback only |

No documentation can choose the most comfortable narrator for a particular listener. Before fixing a default voice, render the same representative five minutes with OpenAI `marin`, `cedar`, and Kokoro `af_heart` or `af_bella`, then listen at the intended walking/driving speed. This small subjective bake-off is more useful than generic voice rankings.

## Output and delivery findings

### Use a chaptered M4B, not a pile of MP3 chunks

M4B is an MP4 container convention for audiobooks, normally carrying AAC audio, metadata, cover art, and chapters. One file per report is easy to download and archive. H1/H2 headings map naturally to chapters, so the listener can skip “Sources,” revisit a recommendation, or jump between alternatives. MP3 remains the widest compatibility fallback, but Audiobookshelf documents outstanding seeking problems with very long MP3 files and calls M4B convenient for one-file books. [Audiobookshelf format guidance](https://audiobookshelf.org/docs/faq/server/)

The assembly path is standard and does not require custom media code. FFmpeg’s metadata format supports global tags and `[CHAPTER]` sections with explicit time bases, start/end times, and titles; `loudnorm` provides EBU R128 normalization in one- or two-pass modes. [FFmpeg metadata format](https://ffmpeg.org/ffmpeg-formats.html#Metadata-1), [FFmpeg `loudnorm`](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)

Recommended output settings are mono AAC-LC at 64 kb/s, 24 or 48 kHz according to source, `faststart`, embedded title/author/narrator/source reference, and chapter markers for H1/H2 sections. Sixty-four kb/s mono uses about 29 MB per listening hour. Master once after concatenation; do not independently normalize every chunk because that can make adjacent paragraphs sound unnaturally different.

### Audiobookshelf solves the actual commute problem

Audiobookshelf is an open-source, self-hosted audiobook and podcast server. Its documented features include offline mobile listening, per-user progress sync, chapters, metadata, cover art, and automatic library scanning. Docker is its recommended installation. Its first-party apps are still described as beta, but its ecosystem includes clients with offline download, CarPlay, Android Auto, sleep timers, and chapter navigation. [Audiobookshelf introduction](https://audiobookshelf.org/docs/documentation/introduction/), [Docker installation](https://audiobookshelf.org/docs/documentation/install/docker/), [client catalog and cautions](https://audiobookshelf.org/docs/documentation/community/community-apps/)

The renderer should atomically publish into a watched layout such as:

```text
Audiobooks/Agent Research/<YYYY-MM>/<document-title>/
  document-title.m4b
  manifest.json
  desc.txt
```

Download on Wi-Fi before leaving. This avoids depending on mobile connectivity and preserves position across phone, web, and car playback.

If running another service is undesirable, the same M4B can be imported manually into a phone audiobook player. A private podcast RSS feed is tempting, but authentication compatibility, enclosure hosting, retention, and feed cleanup are additional machinery. It is worth adding only if an existing podcast player is strongly preferred over an audiobook library.

## Markdown must become a narration plan before it becomes audio

Regex-only Markdown stripping is the most likely source of a disappointing system. Use a CommonMark-capable AST parser and emit an explicit intermediate **narration plan**. The plan should contain ordered chapters, spoken blocks, pauses, omissions, and source positions. Save both the plan and its rendered plain-text transcript so the listening copy is inspectable.

Recommended deterministic defaults:

| Markdown construct | Spoken behavior |
|---|---|
| YAML front matter | Use title/author as metadata; do not speak the block |
| H1/H2 | Speak heading and create a chapter |
| H3–H6 | Speak with a short preceding pause; no chapter by default |
| Paragraph | Speak faithfully |
| Bulleted/numbered list | Preserve item order with short pauses; do not say “bullet” repeatedly |
| Emphasis | Speak text without markup |
| Link | Speak anchor text; omit destination URL |
| Bare URL | Say “link omitted” only if semantically important; otherwise omit |
| Footnote/citation marker | Omit marker; optionally include notes in a separate final chapter |
| `Sources`/`References` section | Skip by default but record the omission in the transcript |
| Image | Speak useful alt text prefaced by “Figure”; otherwise omit |
| Code fence | Say “code example omitted” by default; `--technical` may read a cleaned form |
| Table | Do not flatten cells blindly; say “table omitted” or use an optional generated summary |
| HTML/comment | Strip safely |

The default must not use an LLM to rewrite prose. A deterministic transcript maintains trust and makes source-to-audio differences reviewable. A later `--brief` mode may generate a shorter walking summary, but it should save the generated script, label the result as a derivative, link it to the source, and never replace faithful narration.

Pronunciation needs a user-editable dictionary applied after Markdown normalization and before chunk hashing. Seed it with local vocabulary only after listening reveals failures: “SASE,” “M4B,” repository names, acronyms, and recurring people or product names. Avoid silently expanding ambiguous abbreviations.

## Proposed architecture

```text
path or artifact ref
        |
        v
audited source resolver -> CommonMark AST -> narration plan + transcript
                                            |
                                            v
                                  structural chunker
                                            |
                         +------------------+------------------+
                         |                                     |
                 OpenAI renderer                    local Kokoro renderer
                         |                                     |
                         +---------- content cache ------------+
                                            |
                                  WAV/PCM chunk validation
                                            |
                         ordered concat -> loudness master -> M4B
                                            |
                         manifest + atomic Audiobookshelf publish
```

### Source resolver

Accept ordinary Markdown paths and SASE artifact references. Artifact reads should go through the audited SASE artifact interface rather than directly opening sidecar storage. Record the canonical reference, content hash, and VCS revision when available. Never put the generated media back into the Git-tracked research repository; audio is large, derivative, and reproducible. Store it in the audiobook library and optionally register/link it as a file artifact only when durable SASE discovery is worth the storage cost.

### Chunker and cache

Split first at chapter/paragraph boundaries and then at sentence boundaries. Provider profiles decide the target size: roughly 3,000–3,500 characters for OpenAI and 100–200 tokens for Kokoro. Do not make tiny heading-only API calls; attach a heading to nearby body text for synthesis while keeping its chapter timestamp.

Every chunk cache key should hash:

```text
normalizer-version + transcript-text + provider + model-snapshot
+ voice + speed + delivery-instructions + response-format
```

Writes must be atomic. Keep a job manifest after each successful chunk so a killed process resumes. Retry transient 429/5xx/timeouts with bounded exponential backoff and jitter; do not retry authentication or invalid-input errors. Two to four concurrent hosted requests should reduce wall time without making rate-limit handling complicated. Kokoro may perform best with concurrency one per loaded model.

### Renderer contract

A provider adapter needs only capabilities, limits, `render(chunk) -> audio`, and usage metadata. OpenAI-compatible HTTP covers OpenAI, Kokoro-FastAPI, and several gateways, but preserve provider-specific fields: OpenAI’s `instructions` are valuable and should not be discarded merely to enforce a lowest-common-denominator schema.

For OpenAI, request WAV or PCM, pin the dated model snapshot, begin with `cedar` or `marin`, and use a restrained instruction such as:

> Narrate as a calm, clear technical briefing. Maintain an even pace, pause briefly after headings and list items, pronounce acronyms distinctly, and do not add, omit, or paraphrase content.

The generated audiobook should begin with a short disclosure that the narration is AI-generated, as OpenAI’s TTS usage guidance requires.

### Quality gates

Before publishing, automatically verify:

- every planned chunk has a nonempty cached result;
- decoded duration and sample format are valid;
- word-count-derived speaking rate is within a broad range, for example 90–230 words/minute;
- no chunk contains an implausibly long terminal silence;
- final duration approximately equals the sum of chunks and pauses;
- chapter count, names, ordering, and boundaries match the narration plan;
- FFmpeg/ffprobe can decode and seek the final M4B;
- the output and manifest are renamed into place only after all checks pass.

Keep failed job state and logs, but never log full private text or API keys. A `--dry-run` should print the planned omissions, chapter list, word count, duration estimate, and cost estimate before any paid request.

## Existing software: adopt ideas, not the whole product

### AudioPapers

[AudioPapers at inspected commit `6b27819`](https://github.com/adamsconchallos/audiopapers/tree/6b27819a20b9dc3577a23fb69a908b4d3e12efeb) is the closest conceptual match: Markdown/EPUB/URL/text in, OpenAI-compatible speech, and a chaptered M4B out. It has a small dependency set and MIT license. Its public blog explicitly describes the walking/listening use case and acknowledges weak results on dense citations and inline math. [Project announcement](https://adamsceballos.com/blog/2026/06/audiopapers/index.html)

At inspection, however, the repository was version 0.1.0 with only two commits. It defaults to `tts-1`/`alloy`, uses regex-based Markdown handling, lacks GPT-4o Mini TTS delivery instructions, has only index-based temporary-segment reuse rather than a durable content-addressed cache, and does not expose the validation/resume controls proposed above. Its README also claims 48 kb/s is about 3.5 MB/hour, whereas the bitrate alone implies roughly 21.6 MB/hour. It is excellent for a one-evening proof of concept and as code to learn from, but a weak long-term dependency today.

### Text2Audio

[Text2Audio at inspected commit `e7dfb36`](https://github.com/mooja77/Text2Audio/tree/e7dfb36550b35cc80e2a7d66ea19139511c272c5) was version 1.3.0 with 77 commits. It already implements local Kokoro, chunk retries, a persistent content cache, progress/cancel handling, pronunciation rules, chaptered M4B assembly, loudness normalization, manifests, and remastering. Those are valuable implementation patterns.

Its center of gravity is a local browser audiobook studio with optional voice cloning, multiple document formats, a library UI, PyTorch/model dependencies, and retained source WAVs. Its Markdown cleanup is still regex-based, and its built-in pronunciation dictionary contains manuscript-specific place names. Installing the entire application would create overlapping library/UI concerns once Audiobookshelf is used. Borrow or upstream its reliability ideas; use the application directly only if “fully local immediately” matters more than a focused SASE/artifact workflow.

### Kokoro-FastAPI

Kokoro-FastAPI is mature enough to use as the local provider boundary rather than embedding PyTorch in the Markdown command. Its pinned containers, OpenAI-compatible endpoint, format support, and CPU/GPU variants isolate the heaviest dependencies. This also lets the same narration pipeline compare hosted and local voices without code changes.

## Implementation sequence

### Phase 0: a listening bake-off

Use two representative reports: one prose-heavy and one with lists, citations, tables, and code. Produce a five-minute sample with OpenAI `marin`, OpenAI `cedar`, and Kokoro `af_heart` or `af_bella`. Listen at 1.0× and the expected commute speed. Score fatigue, technical pronunciation, chunk-boundary continuity, and intelligibility in road noise. Pick a default voice from evidence rather than taste by proxy.

AudioPapers can accelerate this trial, but override its older defaults and inspect its cleaned transcript first. Do not spend time deploying Audiobookshelf until at least one voice proves comfortable over 20–30 minutes.

### Phase 1: focused CLI and M4B output

Implement a standalone Python package rather than placing model/runtime dependencies inside the SASE process. The CLI can remain generic, for example:

```text
mdlisten build <path-or-artifact-ref> [--provider openai|kokoro]
mdlisten plan  <path-or-artifact-ref>
mdlisten retry <job-id>
```

Python is pragmatic for API clients and audio orchestration; FFmpeg remains the media engine. If this later becomes a first-class SASE command used by multiple frontends, shared artifact/job-domain behavior should move behind the Rust core boundary while the synthesizer remains an external worker.

Deliver in this order:

1. narration-plan schema and CommonMark transformation tests;
2. dry-run transcript, omission report, duration/cost estimate;
3. OpenAI adapter with pinned snapshot, content cache, retries, and manifest;
4. FFmpeg M4B assembly, chapters, metadata, mastering, and quality gates;
5. Kokoro-FastAPI adapter using the same renderer contract;
6. Audiobookshelf atomic publish.

### Phase 2: convenient SASE integration

Add an explicit action from a research artifact, not an automatic conversion of every report. Automatic generation would create unwanted cost and a crowded listening queue. Good triggers are a small wrapper that accepts `research:...`, a UI action, or opt-in front matter/tagging. Register provenance from the audio manifest back to the source reference. If synthesis may outlast an agent turn, run it as a host-owned background job with visible progress rather than inside the producing researcher’s turn.

### Phase 3: optional briefing mode

Only after faithful narration is trusted, add a separate two-stage mode that converts a report into a 10–15 minute spoken briefing and then synthesizes it. Store the generated script, cite the source artifact, disclose that it is a summary, and offer “faithful” and “brief” as distinct library items. This is especially useful for tables and comparison reports, but it introduces summarization error and should never be implicit.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Hallucinated or changed research | Deterministic faithful mode; saved transcript; briefing mode clearly separate |
| Irritating URLs, citations, or code | AST policies and a dry-run omission report |
| Inconsistent voice across chunks | Pinned model/voice/instructions; paragraph-sized chunks; small concurrency; spot checks |
| Wasted paid synthesis after failure | Content-addressed chunk cache, atomic job state, bounded retries |
| Sensitive material sent to cloud | Explicit local provider/profile; dry-run shows selected provider; no silent fallback to cloud |
| Bad pronunciation of local terms | Editable pronunciation dictionary included in cache key |
| Huge Git/media growth | Keep audio outside research Git; retain compact manifests; prune reproducible caches by policy |
| Service exposed publicly | Private bind/authenticated proxy; local Kokoro endpoint not Internet-facing |
| Provider or price changes | Adapter contract, pinned snapshots/images, manifest metadata, periodic five-minute regression sample |
| Mobile friction | Audiobookshelf offline download and chapters; manual M4B import as fallback |

## Recommended solution

Implement `mdlisten` as a small owned pipeline whose stable product boundary is **narration plan → cached speech chunks → validated chaptered M4B**, not a dependency on one voice vendor. Start with a one-report bake-off; if the hosted voices are comfortable, ship OpenAI `gpt-4o-mini-tts-2025-12-15` with `cedar` or `marin` as the default because it offers the best quality-to-effort ratio and costs roughly a dollar per 10,000-word report. Add a pinned Kokoro-FastAPI 0.9.x profile for private/offline work. Publish finished M4Bs atomically into Audiobookshelf for offline phone, car, and walking playback.

Use AudioPapers to validate the experience quickly and as a compact reference, but do not anchor the permanent workflow to its current 0.1.0 implementation. Reuse Text2Audio’s proven ideas for cache keys, resumability, retries, manifests, and mastering without adopting its entire studio. Keep the first release deterministic and faithful; defer LLM-generated podcast/summary narration until the basic long-form listening loop is demonstrably useful.
