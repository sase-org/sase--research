# What installing `sase-listen` actually gives you

**Date:** 2026-10-01 · **Researcher:** grk · **Epic:** [sase-1e3](https://github.com/sase-org/sase--beads/blob/main/pages/sase-1e3/README.md) · **Plan:** `plan:202610/sase_listen.md`

`uv tool install sase-listen` puts a **standalone CLI named `sase-listen` on PATH**. After the epic ships 0.1.0, that CLI turns any Markdown file — a SASE research report, a notes dump, a hand-written narration script — into a **chaptered, loudness-normalized MP3** you can play on a commute. It also writes a private podcast feed you can subscribe to in AntennaPod.

It is a Python tool. It is not a SASE plugin. It never imports `sase`. Telegram delivery and the `#research/audio` xprompt live in sibling packages that *call* this CLI.

> **Today, 2026-10-01:** the public repo exists and the scaffold is on `master` (`c35e6e2`). PyPI has no published version (HTTP 404). `--version`, `--help`, `doctor`, and `config` work. Every other command prints “not implemented yet” and exits 1. The rest of this report describes the 0.1.0 product the epic is building, then the gap between that and what an installer would get this afternoon.

---

## The listening product

One render produces one episode. Default target is a **full edition of about 16 minutes** (≤ 2,400 words at 150 wpm).

| Property | Value |
| --- | --- |
| File | MP3, mono, 24 kHz, 64 kb/s CBR |
| Size | ~7 MB per 15 minutes (Telegram bot limit is 50 MB ≈ 100 min) |
| Loudness | Two-pass `loudnorm` to −16 LUFS integrated, −1.5 dBTP |
| Chapters | One ID3v2.3 CHAP/CTOC chapter per `##` heading |
| Cover | Generated title card, or a supplied infographic letterboxed into 1400×1400 JPEG |
| Tags | Title, performer, album “Audio Editions”, date, genre “Podcast”, plus SASE episode/source frames |
| Intro | Spoken AI disclosure the renderer adds; scripts must not write it |
| Outro | “That's the end of this audio edition of *Title*.” |
| Voice | One narrator per episode. Default: Gemini 3.8 Flash TTS, voice `Charon`, calm technical-briefing style |
| Cost | Packaged estimate **$0.0135 / audio minute** for Gemini Flash TTS in 2026 ($0.027 from 2027-01-01). A 12-minute edition is about **$0.16**. Ten full editions a month is about **$2**. |

Playback is meant to happen in apps the user already has: Telegram’s music player (speed, background, resume) and AntennaPod (queue, Wi-Fi auto-download, skip-silence, Android Auto, chapters). `sase-listen` writes the files those apps consume. It does not ship a player.

---

## What the wheel puts on PATH

Install:

```bash
uv tool install sase-listen
sase-listen doctor
sase-listen render notes.md
```

Python **≥ 3.12**. Console script `sase-listen`; `python -m sase_listen` also works. Runtime deps that come along for the ride: `rich`, `rich-argparse`, `PyYAML`, `markdown-it-py`, `google-genai`, `httpx`, `mutagen`, **`imageio-ffmpeg`** (bundled static ffmpeg 7.x with `libmp3lame` and `loudnorm` — no sudo, no system ffmpeg), `numpy`, `Pillow`, `segno`.

### Commands

| Command | What an installer uses it for |
| --- | --- |
| `render SOURCE` | The product. Accepts a narration script, plain Markdown, or a `kind:path` artifact ref. Writes the MP3. `--dry-run` prints the plan and cost. `--json` is the agent contract. |
| `script SOURCE` | Deterministic Markdown → narration script (`edition: verbatim`) plus an omissions report. Fallback when no agent wrote a script. |
| `lint SCRIPT` | Contract + listenability check. `--source REPORT` also checks number fidelity. |
| `guide [--edition full\|brief]` | Prints the packaged authoring rules agents follow. Same package as the parser, so the rules cannot drift. |
| `audition` | Renders a built-in ~45 s sample once per voice, so you can pick Charon / Kore / Iapetus / Sadaltager by ear. |
| `ls [EPISODE]` | Local library table, or one episode’s chapters. |
| `doctor [--online]` | Config, ffmpeg source, credentials presence, writable dirs, disk, version. Feed checks land with the feed phase. |
| `cache [prune]` | Chunk-cache size and LRU prune. A killed render re-run only pays for missing chunks. |
| `config [init\|path]` | Effective config with origins; secrets masked. `init` writes a commented starter and refuses to overwrite. |
| `feed init / rebuild / prune` | Private RSS 2.0 + iTunes + Podcasting 2.0 feed, QR code, subscribe URL. |
| `publish` / `unpublish` | Copy an episode into the served-only feed directory and regenerate `feed.xml`. |

Exit codes are part of the contract: 0 ok, 2 usage, 3 config/credentials, 4 synthesis failed, 5 quality gate, 6 structural lint (`render` refuses unless `--force`).

### Files it writes on the machine

XDG on every POSIX platform, including macOS.

| Kind | Default path |
| --- | --- |
| Config | `~/.config/sase-listen/config.yml` (`$SASE_LISTEN_CONFIG` overrides) |
| Library | `~/.local/share/sase-listen/library/<episode-id>/` — `<slug>.mp3`, `manifest.json`, `script.md`, `cover.jpg`, `chapters.json` |
| Feed | `~/.local/share/sase-listen/feed/` — **the only directory ever served** |
| Chunk cache | `~/.cache/sase-listen/chunks/` (default cap 2 GB, LRU) |
| Locks / logs | `~/.local/state/sase-listen/` |

Re-rendering the same source atomically replaces that episode. Audio never goes into git. Agent-written scripts are committed next to reports as `<stem>_narration.md`.

---

## What you still bring after install

The wheel is the renderer. An installer still needs:

1. **Python 3.12+** and `uv` (or pip) to install it.
2. **A TTS credential** for real speech. Default looks for `SASE_LISTEN_GEMINI_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_API_KEY`, then `engines.gemini.api_key_command` (e.g. `pass show gemini_cli_api_key`). OpenAI is the same pattern. The offline **`tone`** narrator needs no key and is for tests, CI, and demos.
3. **`sase` on PATH**, only if you pass a `research:…` artifact ref. Missing `sase` is exit 3 with a hint. Ordinary file paths need no SASE.
4. **A place to listen.** Telegram delivery is a `sase-telegram` change (`sendAudio` with ID3 title/performer/duration). The AntennaPod path is `sase-listen feed init` plus **Tailscale Funnel on `:8443`** at a secret path — rollout proposes that Funnel command through a gate, so nothing goes public until confirmed. Port 443 stays tailnet-only for `sase_gateway`.

Starter config after `sase-listen config init`:

```yaml
narrator: gemini
engines:
  gemini:
    api_key_command: pass show gemini_cli_api_key
```

Switching voices is one line: `narrators.gemini.voice: Kore` (or `--voice` on `render` / `audition`).

---

## Two ways to produce the spoken text

The renderer always consumes the **same narration-script v1**. Installers get both producers:

| Producer | When | What you hear |
| --- | --- | --- |
| **Agent script** | SASE research. An agent writes `<stem>_narration.md` from `sase-listen guide`. | An “audio edition”: question first, then signposted reasons, costs, recap. 4–8 spoken chapters. Numbers kept in digits. Tables spoken as comparisons. |
| **Deterministic normalizer** | Any other Markdown, and as a safety-net pass on agent scripts. `sase-listen script`. | Headings become chapters; lists become sentences; links become anchor text; fences/math/Mermaid dropped and recorded as omissions. `edition: verbatim`. |

Edition budgets at 150 wpm: **full** ≤ 2,400 words (~16 min), **brief** ~600 words (~4 min), **digest** ~250 words per item, **verbatim** unbounded.

A packaged lexicon rewrites jargon in the spoken text only (TUI, xprompt, chezmoi, uv, PyPI, mypy, LUFS). **“SASE” is omitted until the user picks a pronunciation.**

---

## Same epic, different install

The sase-1e3 epic lands three packages. Only the first is this repo.

| Package | Install | What the user gains |
| --- | --- | --- |
| **`sase-listen`** | `uv tool install sase-listen` | The CLI, the MP3, the library, the feed files, the docs site. |
| **`sase-telegram`** | `sase plugin` update (already in SASE’s tool env) | Completion-notification MP3s play in Telegram’s music player instead of arriving as a document. |
| **`sase-research-artifacts`** | same plugin update | `#research/audio @research:…` from the TUI or a Telegram message, and `#research_swarm audio=true`. The xprompt calls `sase-listen` (or `uvx sase-listen`) at runtime. |

The plugin must not depend on `sase-listen` as a Python import. Agents that cannot find the binary fall back to `uvx`.

Out of this epic, and therefore out of the 0.1.0 wheel: daily digest, Whisper ASR gate, two-host “overview” mode, Kokoro on athena, special handling for plans/Obsidian, an `audio` artifact kind, registering sase-listen as a linked SASE repo.

---

## Honest status of the installable tree

Repo: [sase-org/sase-listen](https://github.com/sase-org/sase-listen) (public, created 2026-10-01). Homepage: <https://sase-org.github.io/sase-listen/>. Description and topics already match the product. License MIT. Version **0.0.0**; release-please is bootstrapped for **0.1.0**.

| Surface | Now (`c35e6e2`) | 0.1.0 (sase-1e3) |
| --- | --- | --- |
| PyPI `sase-listen` | 404 | Trusted-publishing wheel after the release-please PR merges |
| `--version` / `--help` | Works | Works |
| `doctor` (offline) | Works: config, ffmpeg via imageio-ffmpeg, writable dirs | Adds `--online` synth check and feed checks |
| `config` / `config init` / `config path` | Works; secrets masked | Same |
| `render` / `script` / `lint` / `guide` | Stub, exit 1 | Full pipeline, tone-engine smoke in publish CI |
| `audition` / `ls` / `cache` / `feed` / `publish` | Stub, exit 1 | Rich UX + RSS |
| Packaged data | Placeholder guide, seed lexicon, pricing YAML, sample passage, `OFL.txt` | Real guide, Inter fonts, sample MP3 on the docs home page |
| Docs | mkdocs-material stubs, CI-built | Filled README (also the PyPI page), SVG terminal captures, provenance links |
| CI | Green on Ubuntu 3.12–3.14 and macOS 3.12 | Same, plus install-smoke that renders a chaptered MP3 with `-n tone` |

A user who `uv tool install`s from git master today gets a command that can diagnose the machine and write a config file. They cannot yet produce an MP3.

---

## Typical installer loop, once 0.1.0 is out

```bash
uv tool install sase-listen
sase-listen config init
# add engines.gemini.api_key_command (or export SASE_LISTEN_GEMINI_API_KEY)
sase-listen doctor --online
sase-listen audition --voices Charon,Kore,Iapetus,Sadaltager
sase-listen render notes.md                  # any Markdown
sase-listen render my_script.md --json       # agent-written edition
sase-listen ls
sase-listen feed init --base-url https://<host>:8443 --qr
sase-listen publish --latest
```

SASE users who already have Telegram and the research plugin add one more sentence in chat: `#research/audio @research:202610/some_report.md`. The agent writes the script, lints it, renders, and registers the MP3; the outbound bot sends it as audio.

---

## Sources

- Epic bead `sase-1e3` and children `.1`–`.12` (all in_progress as of this write).
- Approved plan `plan:202610/sase_listen.md`.
- Originating research `research:202610/commute_audio_from_markdown/commute_audio_from_markdown.md` (corpus, format, cost, delivery).
- Live checkout `gh:sase-org/sase-listen` at `c35e6e2` (`README.md`, `pyproject.toml`, `src/sase_listen/cli/`, `config.py`, `paths.py`, `data/`, workflows).
- GitHub repo metadata (`gh repo view`): public, description set, topics `tts markdown podcast audiobook gemini cli python sase`, homepage Pages URL, no release.
- PyPI JSON for `sase-listen`: 404.
- GitHub Actions on that commit: CI success, Docs success, Publish failure (no release created, expected at 0.0.0).
