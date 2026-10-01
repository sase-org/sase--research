# sase-listen: What Installers Actually Get

**Epic:** `sase-1e3` · *sase-listen: narrated, chaptered audio editions of Markdown for the commute*
**Plan:** `plan:202610/sase_listen.md` · **Repo:** `sase-org/sase-listen` (public, MIT)
**Status as of 2026-10-01:** scaffold only — the value below is the planned `0.1.0`, not what's on disk today.

## TL;DR

Installing `sase-listen` gives you **one command that turns any Markdown file into a
chaptered, loudness-normalized, phone-ready MP3**, plus everything around it: a
narration-script contract with lint and authoring guide, pluggable TTS voices, studio
mastering with cover art, an on-disk episode library with manifests, a private podcast
feed for AntennaPod, and a polished CLI with machine-readable `--json` for agents.

It is a **standalone tool** (`uv tool install sase-listen`), not a SASE plugin. It never
imports `sase`, needs no Rust checkout, and bundles its own `ffmpeg` — no sudo required.

> The flagship use case: SASE research reports become ~16-minute narrated editions you
> listen to on a commute or walk.

## The core promise

```bash
uv tool install sase-listen
sase-listen doctor
sase-listen render notes.md          # any Markdown → MP3
sase-listen render my_script.md      # hand-written narration script → MP3
```

| Input | What happens |
|---|---|
| Hand-written **narration script** (`*_narration.md`) | Rendered as written (editions: `full` ≤ 2,400 words / ~16 min, `brief` ~600 words, `digest`, `verbatim`) |
| Plain Markdown | Deterministically normalized to a lint-clean `verbatim` script first, with an omissions report (fences, tables, math, URLs recorded, not silently dropped) |
| `research:202610/x.md` artifact ref | Resolved via `sase artifact read` (audited, link tables stripped) — needs `sase` on `PATH` |

## What ships in the package

### 1. Narration-script system (the contract)

- A versioned frontmatter contract (`narration: 1`, title, source, date, kind, edition, producer, cover).
- Body rule: only `##` chapters + plain paragraphs. Every `##` becomes an ID3 chapter and a synthesis boundary.
- `sase-listen guide` prints the agent authoring rules; `sase-listen lint` checks them with line-numbered errors, severities, and fix hints — including a `--source` number-fidelity check so narrations never invent statistics.
- A packaged **lexicon** (`TUI`, `xprompt` → "ex-prompt", `chezmoi` → "shay-mwah", `uv` → "you-vee", `PyPI`, `mypy`, `LUFS`…) applied to speech only, never to chapter titles; users merge their own file over the default.

### 2. Voices and TTS engines

| Narrator | Engine | Model | Notes |
|---|---|---|---|
| `gemini` (default) | Gemini | `gemini-3.8-flash-tts`, voice `Charon`* | Calm technical-briefing style via the API style channel |
| `gemini-lite` | Gemini | flash-lite variant | Cheaper, faster |
| `openai` | OpenAI-compatible | `gpt-4o-mini-tts-2025-12-15` | `base_url` override admits a future self-hosted Kokoro |
| `tone` | Synthetic | — | Deterministic speech-paced tones; free; powers CI, tests, demos |

\* Default voice pending rollout auditions; switching is one config line. One narrator per episode — failures never silently fall back to another voice.

- `sase-listen audition` renders a ~45 s sample passage per voice so you can *hear* the choice before committing.
- Secrets via env (`SASE_LISTEN_GEMINI_API_KEY`, `GEMINI_API_KEY`, …) or `api_key_command` (e.g. `pass show …`); secrets never appear in logs, manifests, or `config` output.
- Chunk cache (sha256 of engine + model + voice + style + text) doubles as resume: a killed render re-run pays only for missing chunks. Pricing table (`data/pricing.yml`) labels every estimate "≈" — a full edition costs on the order of **~$0.16**.

### 3. Studio mastering and packaging

Every episode is finished identically, regardless of engine:

- **MP3, mono, 24 kHz, 64 kb/s CBR** (~7 MB per 15 min — well under Telegram's 50 MB bot limit).
- **Two-pass `loudnorm`** to −16 LUFS / −1.5 dBTP, so episodes match each other at 1.25–1.5× speed.
- Spoken AI-disclosure intro + outro, spoken chapter headings, measured pauses (0.5 s chunks, 1.2 s chapters), long silences compressed.
- **ID3v2.3**: title, performer, chapters (CHAP/CTOC, one per `##`), duration, episode/source tags, embedded cover.
- **Cover art**: deterministic generated title card (gradient + bundled OFL font + waveform motif) or your infographic letterboxed into 1400×1400 JPEG.
- **Quality gates**: per-chunk speech-rate checks with automatic re-synthesis, episode loudness/duration/chapter assertions, and precise exit codes (3 config, 4 synthesis, 5 gate, 6 lint).

### 4. Library, manifest, and companion CLI

- Library at `$XDG_DATA_HOME/sase-listen/library/<episode-id>/`: MP3 + `manifest.json` (source sha, narrator, lexicon sha, per-chunk attempts, gates, cost, loudness) + exact `script.md` + `cover.jpg` + Podcasting-2.0 `chapters.json`.
- Commands: `render` (plan panel → live per-chapter progress → summary), `script`, `lint`, `guide`, `audition`, `ls`, `doctor` (ffmpeg, credentials, disk, feed), `cache prune`, `config init`, `feed / publish / unpublish`.
- Every command supports `--json` emitting exactly one object — the agent contract (`render --json` returns paths, duration, chapters, cost, cache stats, warnings).
- Beautiful terminal by requirement: rich tables/panels/progress, `NO_COLOR`- and pipe-safe.

### 5. Private podcast feed (in the box)

- `feed init --base-url …` mints a secret token, prints the exact `tailscale funnel … :8443` command and a terminal QR code for the phone.
- `publish` / `unpublish` / `render --publish` manage `feed.xml` (RSS 2.0 + iTunes/Podcast namespaces, chapter JSON, GUIDs that refresh on re-render, retention caps) plus AntennaPod setup docs.
- Security model: secret path, `itunes:block`, only published episodes exposed.

### 6. Docs, config, and install footprint

- Styled mkdocs site (getting started, scripts, CLI, narrators, pronunciation, feed, SASE integration, reliability, troubleshooting) with real terminal SVG captures and an embedded sample episode; README doubles as the PyPI page.
- XDG paths on every POSIX platform, YAML config with CLI > env > file > defaults precedence, unknown-key errors with did-you-mean, `config` shows each value's origin.
- Runtime deps declared up front (rich, PyYAML, markdown-it-py, google-genai, httpx, mutagen, imageio-ffmpeg, numpy, Pillow, segno); `uv.lock` committed; CI on Ubuntu + macOS, release-please + PyPI trusted publishing.

## Where sase-listen ends and SASE begins

Phone delivery is a three-repo story; only the middle box is the install:

- **sase-listen (this repo):** render pipeline + feed hosting. This is what you install.
- **sase-telegram:** `sendAudio` delivery of the MP3 through the completion notification (lands with the plugin upgrade, not this install).
- **sase-research-artifacts:** `#research/audio` xprompt + `#research_swarm audio=true` stage that writes the script, lints it, renders with `--json`, and registers the MP3 as an artifact.

## Explicitly out of scope

Daily digest + file hook, Whisper/ASR quality gate, two-host dialogue mode, hosted Kokoro, special handling for plans/Obsidian notes (CLI still accepts any file), an `audio` artifact kind, and linked-repo registration — each a separate follow-up, not this epic.

## Bottom line

| Persona | Value |
|---|---|
| Commuter / walker | Every research report as a consistent, chaptered ~16-min episode in AntennaPod or Telegram's player |
| Report author / agent | `guide` + `lint --source` loop guarantees a faithful, listenable script; manifest proves what was rendered, with what voice, at what cost |
| SASE operator | One `uv tool install`, one config file, `doctor --online`, feed on Tailscale Funnel — no daemons, no git-borne audio, no secret leakage |

Install it for the commute; keep it for the contract — the script format, lint, gates, and manifests are what make machine-narrated research trustworthy rather than merely audible.
