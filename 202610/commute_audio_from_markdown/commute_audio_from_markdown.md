# Commute Audio From Markdown

**Date:** 2026-10-01 · **Type:** consolidated research (lead researcher), merging five
independent reports ([`__cdx`](commute_audio_from_markdown__cdx.md),
[`__cld`](commute_audio_from_markdown__cld.md), [`__grk`](commute_audio_from_markdown__grk.md),
[`__mus`](commute_audio_from_markdown__mus.md), [`__gem`](commute_audio_from_markdown__gem.md))
with the lead's own verification.

## Bottom line

**Build a small `sase-listen` renderer that turns a *narration script* into a chaptered,
loudness-normalized MP3. For research reports, a SASE agent writes that script (an
["audio edition"](#resolution)). For any other Markdown, a deterministic AST normalizer
writes it.**

- **[Voice](#synthesis-engine):** synthesize with **Gemini 3.8 Flash TTS** by default. Keep
  **Kokoro-82M** (through Kokoro-FastAPI on athena's GPU) as the free local engine for
  private or offline Markdown.
- **[Delivery](#delivery-to-the-phone):** first via **Telegram `sendAudio`**, which needs a
  roughly 20-line change in `sase-telegram`. Then via a **private podcast feed** from apollo
  that **AntennaPod** subscribes to.
- **[When](#triggers):** generate on demand (`#research/audio @research:<path>`, launchable
  from Telegram), plus an opt-in `audio=true` stage in `#research_swarm`. Do not narrate
  every report automatically.
- **[Storage](#storage):** keep audio out of git. Commit only the small narration script next
  to its report.

Expected cost is [a few dollars a month](#monthly-cost). How much you can listen to limits
this far more than money does.

![Infographic: from Markdown to commute audio. A five-step pipeline (select a report, an
agent-written audio edition script, one consistent voice, a chaptered MP3, then Telegram and
a podcast app), the corpus figures behind the script choice, the recommended voice, format,
delivery and storage stack, and the four-step rollout](commute_audio_from_markdown_infographic.png)

## Question and scope

- **Question:** What is the best way to turn Markdown, starting with the agent research in the
  `research` sidecar, into audio worth listening to while commuting or walking? What should be
  built, what should be borrowed, and how does the audio reach the phone?
- **Prior SASE work:**
  [`research:202606/sase_audio_generation_consolidated.md`](../../202606/sase_audio_generation_consolidated.md)
  recommended a NotebookLM-style two-host `audio_overview` xprompt using Gemini TTS, with
  OpenAI as fallback. That design still holds for an optional "overview" mode. This report
  adds three things it left open: listening to the report itself rather than a podcast about
  it, getting the file onto the phone, and choosing which reports to narrate.

### What the lead verified this turn

- **Corpus:** measured the published research corpus with a CommonMark-AST prototype
  normalizer (see [the corpus measurement](#the-corpus-measurement)).
- **Machines:** apollo has no `ffmpeg` or `ffprobe`. The phone is `pixel-10-pro-xl`
  (Android) and has been offline on Tailscale for 11 days. apollo's `tailscale serve`
  occupies `:443` tailnet-only, proxying to `127.0.0.1:7629`.
- **Repo:** `sase-org/sase--research` is **public** and about 357 MB on GitHub.
- **Keys:** `pass` already holds `gemini_cli_api_key` and `chatgpt_sase_api_key`.
- **Code:** read the `sase-telegram` outbound attachment loop and inbound launch path, and the
  `sase-research-artifacts` provider and swarm xprompt.
- **Docs:** a verification pass over the vendor documentation behind every price, limit and
  ranking cited below. The corrections it produced are folded in.
- **Not done:** no paid TTS API was called. The
  [live validation section](#live-validation-still-owed) lists the live checks still owed.

## Where the five reports agreed

These points had no real dissent, so they are settled:

- **It is a pipeline, and text preparation decides quality.** The stages are select → script
  → synthesize → package → deliver. Raw Markdown read aloud fails with every engine. Code
  fences, pipe tables, URLs, `file.py:NNN` citations and SASE refs turn into noise.
- **Keep generated audio out of the research git repo.** It is large and can be regenerated.
- **Use a long-form player you already have, not a new SASE player.** Long-form listening
  needs chapters, saved position, 1.5–2× playback speed and offline download. Existing
  phone apps already do all of that.
- **Build the renderer reliably:**
  - chunk on structural boundaries;
  - cache rendered chunks by content hash;
  - retry transient failures;
  - normalize loudness once, after concatenation;
  - turn headings into chapters;
  - keep a manifest recording source, rewrite version, engine, model, voice and chunk IDs;
  - write output atomically.
- **[Kokoro-82M is the right local engine](#local-and-private-engine)**, and Kokoro-FastAPI
  is the cleanest adapter for it: OpenAI-compatible `/v1/audio/speech`, CPU/GPU containers,
  latest release v0.9.0.
- **No `sase-core` work for v1.** Nothing here is shared domain behavior that another
  frontend must match. Revisit only if an `audio` artifact kind or a gateway "listen" API
  appears.
- **NotebookLM-style two-host audio is a different product.** It is a summary, not the
  report. Keep it optional.

## The corpus decides the script question

The sharpest disagreement was how to produce the spoken text:

| Position | Reports |
| --- | --- |
| Deterministic, faithful narration by default; LLM summary as a later, separate mode | cdx, grk, mus |
| LLM-written spoken script required by default | cld, gem |

### The corpus measurement

The lead measured the corpus to settle it. Published reports exclude swarm drafts, infographic
pages and highlights. A CommonMark AST normalizer was applied to each: it drops YAML, code
fences, tables, URLs and path/`file:line` citations, and keeps prose, list items and heading
text.

| Published reports | Sept 2026 (117) | Jul–Sep 2026 (200) |
| --- | --- | --- |
| Raw words: median / p90 / max | 3,736 / 6,250 / 12,499 | 3,872 / 6,049 / 12,499 |
| Words left after deterministic cleanup: median | 2,808 (≈ 18.7 min at 150 wpm) | 2,884 (≈ 19.2 min) |
| Deterministic narration: p90 / max | 29 min / 70 min | 30 min / 70 min |
| Reports with at least one table | 109 of 117 | 184 of 200 |
| Share of words inside tables: median / p90 | 18% / 35% | 13% / 30% |
| Inline code spans per report (median) | 160 | 178 |
| Total deterministic narration for the set | **37 hours** | 67 hours |

Two findings settle the question.

**1. The recommendation is often in a table.** Of the 97 September reports with a
recommendation-like `##` section, **50 (52%) put a table inside that section**. A
deterministic narrator drops tables, so it would omit the recommendation itself about half
the time. Speaking tables cell by cell (grk's "≤ 6 rows" rule) does not rescue the large
comparison tables that carry the argument.

**2. Even a careful AST cleanup leaves fatiguing residue.** The prototype's actual output for
[`research:202609/admin_center_updates_tab_unification.md`](../../202609/admin_center_updates_tab_unification.md)
reads:

> …two mark sets that share the Space key with different meanings (), and hint lines the
> source comments themselves describe as out of room… Recommendation (§6): one master/detail
> list… `]` / `[` is repurposed… i / I / A / U collapse into Space / Enter / u…
> [code omitted] —

Empty "()" are left where citations were stripped. Keybindings are spoken as letters. "§6"
cross-references remain, and code-omitted markers interrupt mid-argument. cld measured the
same effect on that report: one paragraph with four `file:line` citations took 35.9 s
verbatim against 23.3 s without them, and Whisper transcribed the citations back as
*"Plugins browser agent clives actions. Pi, 87."*

### Resolution

For research reports, the default is an **LLM-written audio edition**. The deterministic
camp's faithfulness concern is real, so it is handled by design rather than by choosing the
weaker transcript:

- **Narrator choice.** The script is written by a SASE agent that already holds the report.
  In a swarm, it forks the lead (`#fork:research.{@1}.final`), exactly like the existing
  `image=true` stage. Ad hoc, it reads the report with `sase artifact read`.
- **Hard rules.** No new claims. Keep every number that carries the argument. Preserve stated
  uncertainty. Say tables as comparisons ("the winner, the runner-up, the deciding
  numbers"). Never say paths, SHAs, line numbers or URLs.
- **Reviewable output.** The script is committed next to the report as
  [`<stem>_narration.md`](#the-narration-script-contract), so it can be reviewed, diffed and
  regenerated.
- **Spoken intro.** Each episode opens with: "AI-narrated audio edition of *Title*, research
  from *date*." This also covers OpenAI's usage-policy disclosure requirement if that engine
  is used.

### The deterministic normalizer is still required

The deterministic normalizer is still required, for three reasons:

- it is the script producer for arbitrary Markdown (plans, docs, Obsidian notes);
- it is the fallback when no agent is available;
- it is a final safety-net pass that strips any Markdown left in an LLM script.

Both producers emit the same narration-script format, so the renderer never needs to know
which one wrote the script.

Length is *not* the reason to prefer the LLM path. Deterministic narration of a median report
is already about 19 minutes, which is commute-sized at 1.25–1.5×. The reason is fidelity to
what matters (tables and recommendations) and listenability.

## The narration-script contract

The script is the interface between agents and the renderer:

```markdown
---
title: "One Updates Tab"
source: research:202609/admin_center_updates_tab_unification.md
source_blob: 3f9c2e1…   # git blob the script was written from
edition: full           # full | brief | digest | verbatim
producer: agent         # agent | deterministic
target_minutes: 12
---

## The question
…plain spoken prose, no Markdown inside paragraphs…

## The short answer
…
```

Rules for the renderer and the xprompt:

- **Chapters.** Every `##` is an ID3 chapter and a synthesis boundary. Split chapters longer
  than about 700 words at paragraph boundaries. Attach heading text to the following body
  rather than sending tiny heading-only requests.
- **Shape.** Put the recommendation first, then the reasons, then a recap: the listener
  cannot glance back. Signpost structure ("three reasons; first…") and expand acronyms on
  first use.
- **Length budget** at about 150 wpm:

  | Edition | Words | About |
  | --- | --- | --- |
  | `full` | ≤ ~2,400 | 16 min |
  | `brief` | ~600 | 4 min |
  | `digest` item | ~250 | 2 min |

  `verbatim` is the deterministic output.
- **Pronunciation lexicon.** A user-editable YAML file applied before synthesis and included
  in the chunk cache key. Seed it with SASE jargon: `TUI`, `xprompt` → "ex-prompt", `chezmoi`
  → "shay-mwah", `uv`, `ACE`, `bead`, `stitch`, and however "SASE" should be said. Grow it
  from actual listening failures.
- **Research-inventory exclusion.** `sase-research-artifacts` must add
  `!20*/**/*_narration.md` to `_COMPANION_MARKDOWN_EXCLUDE_GLOBS` in `provider.py`, alongside
  the existing `*_infographic.md` entry. Otherwise scripts become "reports" in the `@research`
  inventory and trigger Highlights PDFs.

## Synthesis engine

Figures below were verified on 2026-10-01 against vendor pages and the Artificial Analysis
Speech Arena. Elo values drift by a few points.

| Engine | Arena rank / Elo | ≈ $ per audio hour | Per-request limit | Notes |
| --- | --- | --- | --- | --- |
| ElevenLabs Eleven v4 | #1 / 1320 | ~$4.80 (list $0.08 per 1K chars; launch promo $0.022 until Oct 12) | — | Best voice. Listeners prefer it over Gemini Flash only ~57% of the time |
| Cartesia Sonic 3.6 | #2 / 1275 | ~$2.80 | — | Realtime-oriented |
| **Gemini 3.8 Flash TTS** | **#3 / 1270** | **$0.81 → $1.62 from 2027-01-01** (Batch half) | 8,192 tokens in / 16,384 out ≈ **10.9 min** | GA 2026-09-22/23. 30 studio voices plus an extended library. Natural-language style control. Native 2-speaker |
| Gemini 3.8 Flash-Lite TTS | #6 / 1240 | $0.54 → $1.08 | same | Good for digests and batch |
| OpenAI `gpt-4o-mini-tts-2025-12-15` | **not ranked** | ~$0.90 (launch estimate; token prices $0.60 / $12 per 1M) | **4,096 chars** (and 2,000 input tokens) ≈ 4 min | 13 voices (`marin`/`cedar`). `instructions` prompt. AI disclosure required |
| Kokoro-82M v1.0 | #49 / 1064 | $0 marginal | none | Apache-2.0, 54 voices (`af_heart`). Local |
| `edge-tts` | — | "free" | — | Unofficial Edge endpoint. Broke Dec 2025 (7.2.4–7.2.7 hotfixes); 403s Jan 2026 closed "not planned"; intermittent failures open since Apr 2026 |

### Cloud default

**Default: Gemini 3.8 Flash TTS.** It ranks near the top for the same price as OpenAI's mini
model, which is not ranked. A 206-point Elo gap over Kokoro means listeners prefer Gemini in
about 77% of blind pairs. It is GA, which removes the "Preview" risk the 202606 report
flagged. A key already exists.

- Use one fixed style prompt for consistency, for example: *"calm, clear technical-briefing
  narrator; moderate pace; slight emphasis on numbers; read the text exactly"*.
- Gemini treats `text` as a verbatim transcript, so keep stage directions out of the text.
- Chunk per chapter, well under the ~10.9-minute output cap. Earlier Gemini TTS versions
  degraded on long single requests and billed for silent stretches; 3.8 claims timbre
  stability across concatenated requests.
- Request raw PCM for stitching.

### Local and private engine

**Kokoro-82M on athena.** cld measured `kokoro-onnx` on a 262-word narration:

| Host | Realtime factor |
| --- | --- |
| athena RTX 3080 Ti | **28.7×** (a 15-min episode in ~31 s) |
| apollo CPU, at load ~14 alongside agents | 1.7× |

ASR word error rate on the output was 3.3%. Run Kokoro-FastAPI on athena, bound to the
tailnet only, and call it from apollo. Gotcha: current `onnxruntime-gpu` targets CUDA 13, but
athena's driver 550 tops out at CUDA 12.4. Pin `onnxruntime-gpu[cuda,cudnn]==1.22.0` or
upgrade the driver.

### Why not the other defaults

The other reports' defaults, and why they were not chosen:

- **grk's Kokoro default.** Its case rested on privacy, and the research repo is already
  public, so cloud TTS reveals nothing new for research. On apollo, Kokoro competes with
  agents for CPU.
- **mus's and gem's `edge-tts`.** Its 2025–2026 breakage history makes it unfit as a
  foundation, and it is a ToS-gray scrape. It is fine for a personal spike only.
- **cdx's OpenAI default.** Similar price, unranked quality, and a cap 2.7× smaller per
  request. Keep it as a secondary adapter behind the same interface.
- **ElevenLabs.** About 6× Gemini's list price for a margin most listeners do not notice.

### Engine rules

- **Never mix engines within an episode.** If Gemini fails mid-render, retry Gemini or
  re-render the whole episode on Kokoro.
- **Never fall back silently from local to cloud** for Markdown marked private.

### Monthly cost

Gemini Flash, 2026 → 2027 prices:

| Scenario | Audio min / month | Cost |
| --- | --- | --- |
| On demand, 10 full editions | ~150 | $2.0 → $4.1 |
| Daily digest (~4 reports/day × 2 min) + 10 full editions | ~390 | $5.3 → $10.5 |
| Full edition of every new report (117 × 15 min) | ~1,755 | $24 → $47 |

Cost is not the constraint. September's reports alone would be
[37 hours of narration](#the-corpus-measurement).

## Packaging

### Audio format

Use **MP3, mono, 64 kb/s, 24 kHz, with ID3v2 CHAP/CTOC chapters**, normalized once after
concatenation to about **−16 LUFS integrated, −1.5 dBTP**. Add title, artist and album tags,
and the report's `_infographic.png` as cover art when one exists. A 15-minute episode is about
7 MB.

This settles the format split (cdx and mus: M4B; cld: MP3 with chapters; gem: 128 kb/s MP3;
grk: both):

- **Telegram `sendAudio`** accepts MP3 or M4A.
- **AntennaPod** reliably reads ID3 CHAP in MP3. It reads only *Nero-style* MP4 chapters:
  support arrived in 3.5.x via PR #7159, QuickTime chapter tracks are not read, and issue
  #4311 is only partly fixed. An M4B's chapters may therefore silently disappear.
- **M4B's advantage is Audiobookshelf's**, whose FAQ admits problems seeking in very long
  MP3s. Audiobookshelf is not the recommended player, and 15–20-minute episodes are not
  "very long".
- **128 kb/s (gem)** doubles the size with no audible gain for mono speech.
- Optionally, also publish Podcasting 2.0 `<podcast:chapters>` JSON in the feed. AntennaPod
  reads it, which gives chapters a second path.

### Mastering

Use ffmpeg `loudnorm` (two-pass), concatenate with short gaps (about 0.6 s between paragraphs
and 1.2 s between chapters), trim silences over 1.5 s, and write ID3 chapters with `mutagen`.
apollo has no ffmpeg. Either install it once through a reviewed sudo gate
(`apt install ffmpeg`), or pull a static build with `static-ffmpeg` under `uv` (gem's no-root
route).

### Quality gates before publishing

- every chunk is present and decodes;
- each chapter's duration falls within 0.7–1.5× of words ÷ 150 wpm;
- total duration ≈ the sum of chunks plus gaps;
- chapter titles and order match the script;
- optional, phase 3: an ASR gate. faster-whisper `base.en` on CPU costs about 6% of audio
  duration (cld's measurement); re-synthesize a chapter whose word error rate exceeds ~10%.

## Delivery to the phone

### Verified constraints

The lead verified the facts that shape this choice:

- The phone is a **Pixel 10 Pro XL (Android)**. Its Tailscale node was **offline, last seen
  11 days ago**, so anything that needs the phone on the tailnet will silently fail to sync.
- **apollo is an always-on DigitalOcean server with a public IP.** Its `:443` is already a
  *tailnet-only* Serve for `sase_gateway`.
- Tailscale Funnel listens only on 443, 8443 or 10000, and a port cannot be both Serve and
  Funnel. Funnel also needs the `funnel` node attribute in the tailnet policy.
- `sase-telegram` has no audio branch. Its outbound loop handles images, animations, videos
  and PDFs. Anything else goes through `md_to_pdf` and then `send_document`, so an `.mp3`
  arrives as a plain file.

### Delivery options

| Option | Phone experience | Effort | Verdict |
| --- | --- | --- | --- |
| **Telegram `sendAudio`** | Music player, 0.2–2.5× speed, background play, **resumes files longer than 20 min**, next-audio autoplay. No chapters. 50 MB bot limit, about 100 min at 64 kb/s | `_is_audio_file` → `send_audio(title, performer, duration, thumbnail)` in `scripts/sase_tg_outbound.py` and `telegram_client.py`. No new infrastructure | **Phase 1** |
| **Private RSS → AntennaPod** | Real podcast app: queue, auto-download on Wi-Fi, skip-silence, Android Auto, ID3 chapters | Static directory plus generated `feed.xml` (`<itunes:block>yes`). Serve from apollo at an unguessable path via `tailscale funnel --bg --https=8443`, or Caddy on the public IP | **Phase 2** |
| Same feed, tailnet-only | Same | Least exposure | Rejected as default: the phone is usually off the tailnet. gem's and grk's tailnet-only design fails here |
| Audiobookshelf | Polished library, progress sync | Docker plus a database. Android app still `0.14.2-beta` (2026-09-28) | Viable if you want an audiobook library; overkill for briefings (cdx's choice) |
| Syncthing / manual copy | File-manager playback | Fiddly, no queue | No |

### Feed notes

- AntennaPod fetches feeds **on the device**, so pairing it with a feed from apollo works
  whenever the phone has internet. Pocket Casts and Overcast fetch on their own servers, so
  they need a publicly reachable feed.
- Prefer a secret path over HTTP basic auth: AntennaPod's basic auth has had download-401
  and special-character bugs.
- Leaking the feed token only exposes narration of an already-public repo. Narrations of
  *private* Markdown must not go into this feed. Use Telegram or a separate token.

## Where the code lives and how it is triggered

| Piece | Home | Why |
| --- | --- | --- |
| Renderer (script → MP3), engine adapters (`gemini`, `kokoro`, `openai`), deterministic Markdown → script normalizer, lexicon, cache, manifest, feed writer | **new plugin repo `sase-listen`** (Python, uv) | Keeps `google-genai`, `mutagen`, ffmpeg and optional ONNX dependencies out of sase. Reusable for any Markdown. Follows the `sase-telegram` / `sase-github` plugin precedent |
| `#research/audio` xprompt, `audio=true` / `audio_model` swarm inputs, narration exclude glob, later `#research/digest` and a `research-audio` file hook | `sase-research-artifacts` | Mirrors `#research/image` and `research-highlights` |
| `send_audio` branch | `sase-telegram` | Delivery adapter |
| Nothing for v1 | `sase`, `sase-core` | If a first-class `sase listen` subcommand is ever added in-tree, follow the project's CLI rules memory first |

### Interface

**Generic CLI, research-specific xprompt.** The 202606 report and grk wanted an xprompt first
and a CLI later. cdx, mus and gem wanted a CLI. The two are not in conflict:

- The plugin ships a small `sase-listen script|render|publish` CLI, because the renderer must
  be invokable and unit-testable on its own.
- The research-specific orchestration is an xprompt.
- Skip a top-level `sase audio` command until real use justifies one.

### Triggers

1. **On demand.** `#research/audio @research:<path> [edition=full|brief]` from the TUI or CLI,
   or as a Telegram text message. `sase-telegram` already launches agents from text and
   normalizes `@` refs through `normalize_launch_xprompt_at_refs`. The agent:
   - writes `<stem>_narration.md`;
   - runs `sase-listen render` under `sase tool run`, or `/sase_monitor` if it is long;
   - creates a notification with the MP3 attached, which Telegram delivers and the feed
     picks up.
2. **Swarm stage.** `#research_swarm audio=true` adds `<clan>.audio`:
   `%wait:research.{@1}.final #fork:research.{@1}.final #research/audio`. The forked narrator
   inherits the lead's full context, which makes it the most faithful writer available. It is
   off by default.
3. **Daily digest ([phase 3](#phase-3-digest-and-hardening)).** A `research-audio` file hook
   (`sidecars: [research]`, `ops: [ADD]`, drafts excluded) only appends paths to a queue. A
   morning scheduler job launches `#research/digest`, which produces one episode with about 2
   minutes per new report and ends each item with "ask for the full edition".

**Do not auto-narrate every report.** At September's rate, even 12-minute editions of
everything would be about 23 hours a month, more than a one-hour daily commute. The feed
would become a guilt pile. (The 37 hours in [the corpus measurement](#the-corpus-measurement)
is full deterministic narration.)

### Storage

- Narration scripts go in the research repo as companions.
- MP3s go in a media directory on apollo that backs the feed, with retention such as 90 days.
- Optionally register an MP3 as a `file` artifact. No `audio` kind exists today; add one only
  if ACE needs playback.
- Committing audio would add about 190 MB a month to a public repo forever, and about 2.7 GB
  for a full backfill (cld's estimate).

## Existing tools to borrow from

Borrow ideas, keep ownership.

| Tool | Use it for | Why not as the foundation |
| --- | --- | --- |
| **Chrome Android "Listen to this page"** (standard plus *AI playback*) on the GitHub-rendered report; **ElevenReader** app | **[Phase-0 calibration](#phase-0-calibrate) today**, with no code | No automation, queue or chapters; content goes to a third party (research is public anyway) |
| **AudioPapers** (MIT, v0.1.0, 2 commits) | Closest Markdown → chaptered M4B reference | Too young. Regex Markdown handling, `tts-1`/`alloy` defaults, no durable cache |
| **Text2Audio** (v1.3.0) | Cache keys, retries, manifests, remastering patterns | Browser studio plus PyTorch; overlaps the player and library |
| **abogen** 1.3.x | Kokoro + Markdown headings → M4B + Audiobookshelf push; a weekend spike | GUI/web-first; brings its own orchestration |
| **hansharhoff/podcastfeeds** | Same shape: private feed over Tailscale into AntennaPod, spoken intros, chapter art | Built on `edge-tts` |
| **Podcastfy** / Gemini Notebook (ex-NotebookLM) | Reference for an optional two-host mode | Bypasses SASE agents and the audit trail. Gemini Notebook has no consumer API |

## Phased plan

### Phase 0 Calibrate

30 minutes, no code.

- On the Pixel, open one report on GitHub in Chrome and compare *Listen to this page → AI
  playback* against *Standard*. If the summary is all you want, prioritize digests; if you
  keep wanting the detail, prioritize full editions.
- In Google AI Studio, render one chapter with Gemini voices `Kore`, `Charon` and `Iapetus`,
  and compare them with Kokoro `af_heart`. Listen at your real commute speed with traffic
  noise. Arena Elo is measured on short clips, and long-form fatigue may rank voices
  differently.

### Phase 1 On-demand audio editions over Telegram

About 1–2 days.

1. `sase-listen render <script.md>`:
   - parse the frontmatter and chapters, apply the lexicon;
   - synthesize per chunk with Gemini, using a content-hash cache and bounded retries;
   - run the duration gate, concatenate, `loudnorm`;
   - encode MP3 with ID3 tags and chapters, and write the manifest.
2. `sase-listen script --deterministic <any.md>` as the generic and fallback producer, with
   golden tests against real research files covering tables, fences, citations, refs and a
   source index.
3. `#research/audio` xprompt and the `_narration.md` exclude glob in
   `sase-research-artifacts`.
4. The `send_audio` branch in `sase-telegram`.
5. ffmpeg on apollo, via the sudo gate or `static-ffmpeg`.

### Phase 2 Podcast feed swarm stage and local engine

About 1–2 days.

6. `sase-listen publish`: copy into the media directory, regenerate `feed.xml`, apply
   retention. Serve with Funnel on `:8443` under a secret path, and subscribe in AntennaPod
   with auto-download.
7. Add `#research_swarm audio=true` and an `@audio` model alias.
8. Run Kokoro-FastAPI on athena (pinned image, tailnet-only bind) as the `kokoro` engine for
   private Markdown.

### Phase 3 Digest and hardening

9. Digest file hook, scheduler job and `#research/digest`, using Flash-Lite or Batch for
   cost.
10. ASR quality gate, `brief` editions, and a selective backfill.
11. Optionally, a two-host `overview` mode, reusing the 202606 design.

### Live validation still owed

- Render one 12-minute script with `gemini-3.8-flash-tts`. Check wall time, consistency
  across chapter chunks, billed silence, and the real cost against about $0.16.
- Confirm the billing tier of `gemini_cli_api_key`; free-tier TTS quotas are too low for
  daily use.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Narration distorts the report: dropped caveats, invented claims | Hard xprompt rules. Forked-lead narrator. Committed, diffable script. Section names spoken so details can be found in the text. Optional second-agent fidelity check for `full` editions |
| TTS artifacts: skipped words, long or billed silences, voice drift | Per-chapter chunks. Duration gate. Silence trim. ASR gate in phase 3. One engine per episode |
| Gemini price doubles on 2027-01-01, or quota runs out | Engine is configuration. Flash-Lite and Batch halve cost. Kokoro is always available |
| Too much audio | On demand by default. Digest is opt-in. Feed retention |
| Feed exposure | Port 8443 only (443 stays tailnet-only). One static directory. Unguessable path. `<itunes:block>`. Private Markdown never goes in this feed |
| Jargon mispronounced | Lexicon from day one, in the cache key. Fix after the first listen |
| GPU path breaks on CUDA/driver drift (seen on athena) | Pin `onnxruntime-gpu==1.22.*` or upgrade the driver. Cloud default is unaffected |
| Wasted paid synthesis after a crash | Content-addressed chunk cache, atomic job state, `--dry-run` showing chapters, omissions, duration and cost |

## Open questions for you

1. **Listening budget.** How many minutes a day do you actually commute or walk? That decides
   whether the digest ([phase 3](#phase-3-digest-and-hardening)) should move ahead of the
   feed ([phase 2](#phase-2-podcast-feed-swarm-stage-and-local-engine)).
2. **Default edition.** `full` (about 16 min) or `brief` (about 4 min) when you just say "make
   audio of this"?
3. **Scope beyond research.** Should plans and Obsidian notes be included? If so, they render
   on Kokoro (athena) and go only to Telegram or a separate feed token.
4. **Narrator style.** One narrator (recommended, denser) or an optional two-host flavor for
   digests?

## Corrections to individual reports

- **cdx:**
  - `gpt-4o-mini-tts` is not on the Speech Arena, while Gemini 3.8 Flash ranks #3 at a
    similar price.
  - M4B chapters are only partly supported in AntennaPod.
  - Audiobookshelf's apps are still beta and need Docker plus a database.
  - Otherwise its renderer engineering (cache keys, gates, manifest, dry run) is the strongest
    of the five and is adopted above.
- **cld:**
  - Its local claims all checked out: corpus counts, Telegram fallback path, Serve on `:443`,
    phone offline, public repo.
  - Gemini has 30 studio voices *plus* an extended library, not just 30.
  - Its pipeline is the backbone of this recommendation.
- **grk:**
  - The local-by-default case rests on privacy, which does not apply to an already-public
    repo.
  - For OpenAI, the 4,096-character cap (about 4 min) binds before the 2,000-token limit; it
    is not "~10 min per request".
  - Its tailnet-only RSS fails while the phone is off the tailnet.
  - Its ideas of a lexicon on day one and a special case for recommendation tables are both
    adopted.
- **mus:**
  - `edge-tts` as default is contradicted by its 2025–2026 breakage history.
  - "5,000–13,000 words per report" overstates the corpus: the median is 3,736, measured.
  - ElevenReader remains a good zero-build calibration tool.
- **gem:**
  - The `tts-1` voice list and prices are stale. ElevenLabs is $0.08 per 1K characters, not
    $0.15–0.30.
  - "Kokoro 3–5× realtime on CPU" was 1.7× when measured on loaded apollo.
  - 128 kb/s MP3 is wasteful.
  - Its tailnet-only feed fails for the same reason as grk's.
  - A dual-host default trades away fidelity.
  - Its [mastering details](#mastering) (−16 LUFS, −1.5 dBTP, pause lengths) are adopted.

## Sources

**Vendors and services:**

- Gemini API: [pricing](https://ai.google.dev/gemini-api/docs/pricing),
  [speech generation](https://ai.google.dev/gemini-api/docs/speech-generation),
  [3.8 Flash TTS model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash-tts),
  [3.8 Flash-Lite TTS model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash-lite-tts),
  [changelog](https://ai.google.dev/gemini-api/docs/changelog),
  [launch post](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-8-text-to-speech/)
- OpenAI: [TTS guide](https://developers.openai.com/api/docs/guides/text-to-speech),
  [`gpt-4o-mini-tts`](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts),
  [speech endpoint](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create),
  [pricing](https://developers.openai.com/api/docs/pricing),
  [data controls](https://developers.openai.com/api/docs/guides/your-data)
- [Artificial Analysis TTS leaderboard](https://artificialanalysis.ai/text-to-speech/leaderboard)
- [ElevenLabs API pricing](https://elevenlabs.io/pricing/api) and
  [models](https://elevenlabs.io/docs/overview/models)
- Kokoro: [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M),
  [Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI),
  [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx)
- edge-tts: [PyPI](https://pypi.org/project/edge-tts/), issues
  [#443](https://github.com/rany2/edge-tts/issues/443),
  [#458](https://github.com/rany2/edge-tts/issues/458),
  [#473](https://github.com/rany2/edge-tts/issues/473)
- Telegram: [`sendAudio`](https://core.telegram.org/bots/api#sendaudio),
  [resume over 20 min](https://telegram.org/blog/verifiable-apps-and-more),
  [0.2–2.5× speed](https://telegram.org/blog/power-saving)
- Tailscale: [Funnel](https://tailscale.com/kb/1223/funnel),
  [Serve](https://tailscale.com/kb/1312/serve)
- AntennaPod: [chapter docs](https://forum.antennapod.org/t/chapter-marks-documentation/1193),
  [PR #5630 (P2.0 chapters)](https://github.com/AntennaPod/AntennaPod/pull/5630),
  [PR #7159 (Nero M4A chapters)](https://github.com/AntennaPod/AntennaPod/pull/7159),
  [issue #4311](https://github.com/AntennaPod/AntennaPod/issues/4311),
  [issue #6669 (basic auth)](https://github.com/AntennaPod/AntennaPod/issues/6669),
  [on-device fetching](https://antennapod.org/documentation/general/central-distributed)
- Audiobookshelf: [server FAQ](https://audiobookshelf.org/docs/faq/server/),
  [app beta FAQ](https://audiobookshelf.org/docs/faq/app-beta/)
- FFmpeg: [metadata/chapters](https://ffmpeg.org/ffmpeg-formats.html#Metadata-1),
  [`loudnorm`](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)

**Prior art:** [AudioPapers](https://github.com/adamsconchallos/audiopapers),
[Text2Audio](https://github.com/mooja77/Text2Audio),
[abogen](https://github.com/denizsafak/abogen),
[hansharhoff/podcastfeeds](https://github.com/hansharhoff/podcastfeeds),
[Podcastfy](https://github.com/souzatharsis/podcastfy).

**Local evidence:**

- A corpus measurement using a `markdown-it-py` AST normalizer over the published 202607–202609
  reports.
- `sase-telegram`: `scripts/sase_tg_outbound.py` and `inbound_handlers/text_messages.py`.
- `sase-research-artifacts`: `provider.py` and `xprompts/research_swarm.md`.
- `tailscale status` / `tailscale serve status` on apollo; `gh repo view` for repo
  visibility; the tailnet memory note;
  [`research:202606/sase_audio_generation_consolidated.md`](../../202606/sase_audio_generation_consolidated.md).
- cld's Kokoro and Whisper benchmarks on apollo and athena.
- Researcher reports in this directory: [`commute_audio_from_markdown__cdx.md`](commute_audio_from_markdown__cdx.md),
  [`commute_audio_from_markdown__cld.md`](commute_audio_from_markdown__cld.md),
  [`commute_audio_from_markdown__grk.md`](commute_audio_from_markdown__grk.md),
  [`commute_audio_from_markdown__mus.md`](commute_audio_from_markdown__mus.md) and
  [`commute_audio_from_markdown__gem.md`](commute_audio_from_markdown__gem.md).
