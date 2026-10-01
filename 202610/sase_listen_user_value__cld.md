# sase-listen: What You Actually Get When You Install It

**Date:** 2026-10-01 · **Researcher:** cld · **Inputs:** epic `sase-1e3` and its plan
`plan:202610/sase_listen.md`, the originating research
`research:202610/commute_audio_from_markdown/commute_audio_from_markdown.md`, the
`sase-org/sase-listen` repo at `c35e6e2`, and live GitHub, PyPI, and sase-telegram state.

## Bottom line

> **sase-listen is a renderer, not a writer.** It gives you one command,
> `sase-listen render`, which turns a _narration script_ into a podcast-quality MP3. The
> MP3 is chaptered, loudness-normalized, tagged, and has cover art. You can optionally add
> it to a private podcast feed. The tool never asks an LLM to rewrite your text.

- **"Listen to my research on a walk" takes three packages.**
  - sase-listen makes the MP3.
  - **sase-research-artifacts** (`#research/audio`) has a SASE agent write the condensed
    16-minute _audio edition_.
  - **sase-telegram** delivers the episode as a playable track.

  With sase-listen alone you get MP3 files and a feed. You do not get Telegram delivery or
  agent-written editions.
- **Without an agent, you get a verbatim reading.** `sase-listen render notes.md` first
  runs a deterministic cleanup. It then reads the whole document and lists what it left
  out (code, large tables, URLs, citations). The condensed `full` and `brief` editions need
  a script written by an agent, or by you following `sase-listen guide`.
- **You cannot install it yet.** Only the scaffold has landed, and PyPI has no release.
  Every subcommand except `config` is a stub. The 0.1.0 release PR also failed to open
  (see [Status](#status-on-2026-10-01)).

## How it fits together

```text
 any Markdown ─────────────► sase-listen script ─────┐  verbatim (deterministic)
 SASE research ─► agent + sase-listen guide ─────────┤  full ≈16 min · brief ≈4 min
                                                     ▼
                             narration script  <stem>_narration.md
                                                     │  sase-listen lint [--source report]
                                                     ▼
        sase-listen render:  lexicon → chunks → TTS → quality gates → master → tag
                                                     │
               ┌─────────────────────────────────────┼──────────────────────────────┐
               ▼                                     ▼                              ▼
     local library + manifest            private RSS → AntennaPod          Telegram music player
     (sase-listen ls)                    (sase-listen publish)             (sase-telegram plugin)
```

The narration script is the contract between writer and renderer. It has YAML
frontmatter, and its body contains only `##` chapters and plain spoken paragraphs. The
renderer never knows whether an agent, a human, or the normalizer wrote it.

## Who gets what

| You install…                           | You get                                                                                                                                         | You still need                                                                                   |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `uv tool install sase-listen`          | The standalone CLI (no `sase` dependency): render, script, lint, guide, audition, library, doctor, config, cache, feed                            | A Gemini or OpenAI API key, plus somewhere to host the feed directory                            |
| plus upgraded **sase-research-artifacts** | `#research/audio @research:…` from the TUI or a Telegram message, and `#research_swarm audio=true`. The agent writes, lints, renders, and registers the edition | `sase-listen` on `PATH` (the xprompt falls back to `uvx sase-listen`)                            |
| plus upgraded **sase-telegram**        | MP3 and M4A attachments arrive as playable tracks with title, performer, and duration, not as a document. Files over 50 MB get a text note instead | The MP3 must ride a notification, which `#research/audio` handles with `sase artifact create`    |
| Bryan on apollo, after rollout         | All of the above, configured through chezmoi with a `pass`-backed key. Voice auditions arrive in Telegram, and a feed is served on Funnel `:8443` with `auto_publish` on | Approving the gated Funnel exposure                                                              |

## The CLI at a glance

| Command                                                | What it does for you                                                                                                                                                                                  |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `render SOURCE`                                        | Turns a script, a plain Markdown file, or a `research:…` ref into an episode. `--dry-run` shows chapters, words, ≈ minutes, and ≈ cost before spending anything. `-n`/`--voice` pick the narrator and voice, `--publish` adds the episode to the feed, and `--json` returns one object for agents |
| `script FILE`                                          | Writes the deterministic `verbatim` script so you can edit it before rendering, plus an omissions report                                                                                              |
| `lint SCRIPT --source REPORT`                          | Checks the contract and listenability: no residual Markdown, sentence and chapter lengths, and edition budget. With `--source`, it flags **any number in the script that the report does not contain** |
| `guide [--edition full\|brief]`                        | Prints the authoring rules for whoever writes the script, whether agent or human. The rules ship with the code that enforces them, so they cannot drift                                               |
| `audition --voices A,B,…`                              | Renders the same ~45 s sample passage in each voice so you can choose by ear (≈ 1¢ per voice on Gemini)                                                                                               |
| `ls [EPISODE]`                                         | Lists your episode library, or shows one episode's chapters, narrator, size, and feed status                                                                                                         |
| `doctor [--online]`                                    | Checks config, ffmpeg, credentials (`--online` adds a one-word live synth), writable dirs, disk, and the feed                                                                                        |
| `config [init\|path]`                                  | Shows the effective config and where each value came from, with secrets masked. `init` writes a commented starter file                                                                              |
| `cache [prune]`                                        | Shows chunk-cache size and prunes it (LRU, capped at 2 GB by default)                                                                                                                                |
| `feed init --base-url URL`, `publish`, `unpublish`     | Manages the private podcast feed. `feed init` creates a secret-path URL, a terminal QR code for the phone, and the exact `tailscale funnel` command. Episodes are kept for 90 days or 200 episodes   |

Distinct exit codes make it scriptable: 3 for credentials, 4 for failed synthesis, 5 for a
failed quality gate, and 6 for a malformed script.

## What an episode is

|                 |                                                                                                                                                                                                                                                                 |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Voice**       | One narrator per episode: Gemini 3.8 Flash TTS with voice `Charon` (until auditions pick one) and a fixed calm technical-briefing style. A failure never silently switches engines                                                                                  |
| **Shape**       | Opens with a spoken AI disclosure: _"This is an AI-narrated audio edition of Title, SASE research from September 14, 2026."_ Chapter headings are spoken, with 0.5 s between chunks and 1.2 s between chapters. Long silences are compressed, and a short outro closes |
| **Format**      | MP3, mono, 24 kHz, 64 kb/s CBR, with two-pass loudness to −16 LUFS and −1.5 dBTP. That is ≈ 0.5 MB per minute, so a 16-minute edition is ≈ 7.7 MB. Telegram's 50 MB bot limit fits ≈ 100 minutes                                                           |
| **Chapters**    | One per `##`, written both as ID3 CHAP/CTOC and as Podcasting 2.0 JSON, so AntennaPod gets chapters by either path. Telegram's player resumes position but has no chapters                                                                                        |
| **Cover**       | 1400×1400. When the report has an infographic, it is letterboxed over a blurred copy of itself. Otherwise you get a generated title card with a gradient, the title, `SASE RESEARCH · AUDIO EDITION`, the date, and a waveform motif                            |
| **Paper trail** | `library/<episode>/` holds the MP3, the exact script rendered, the cover, chapters JSON, and `manifest.json`. The manifest records the source hash, narrator, per-chunk cache keys, loudness, gate results, and ≈ cost                                        |

## Editions: who writes the words

| Edition                 | Length                                                        | Written by                                                                           | Standalone user?                     |
| ----------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------ |
| **`full`** (SASE default) | ≤ 2,400 words ≈ 16 min                                        | A SASE agent via `#research/audio`. In a swarm, it is a fork of the lead, so it holds the full context | Only if you write it, following `guide` |
| `brief`                 | ≈ 600 words ≈ 4 min                                           | Same, with `edition=brief`                                                           | Same                                 |
| `verbatim`              | The whole document: a median research report is ≈ 19 min, p90 ≈ 30 min | The deterministic normalizer                                                         | ✓ automatic for any Markdown         |
| `digest`                | ≈ 250 words per item                                          | **Nobody yet.** The daily-digest workflow is out of scope for this epic               | A valid schema value only            |

**Why the agent edition matters.** In the originating research, **52%** of September
reports put their recommendation inside a table. A deterministic reading drops large
tables, so it would skip the recommendation about half the time. The agent's script must
instead:

- keep every argument-carrying number;
- preserve stated uncertainty;
- say tables as "the winner, the runner-up, and the deciding numbers".

`lint --source` checks the number rule mechanically.

**What the normalizer does with plain Markdown:**

- **Structure:**
  - `##` headings become chapters, and deeper headings are spoken.
  - Lists become sentences.
  - Links are read as their anchor text, and images become "Figure: …".
- **Tables:** tables up to 6 rows × 4 columns are read row by row. Larger ones become one
  sentence naming their columns and row count.
- **Dropped, and listed in the omissions report:** code fences, math, Mermaid, footnotes,
  and "Sources" sections.
- **Humanized:** identifiers like `snake_case`, and `§6`, which becomes "section 6".

## Cost and requirements

**Requirements:**

- Python ≥ 3.12 on Linux or macOS. CI covers Ubuntu with 3.12–3.14 and macOS with 3.12.
  Windows is not targeted.
- **No system ffmpeg and no sudo.** The `imageio-ffmpeg` dependency bundles a static
  ffmpeg 7.0.2 with `libmp3lame` and `loudnorm`.
- **One API key.** The Gemini key comes from `SASE_LISTEN_GEMINI_API_KEY`,
  `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or `api_key_command: pass show …`. OpenAI works with
  `-n openai`.
  - The built-in `tone` engine needs no key, but it makes **tone bursts, not speech**. It
    exists for tests and demos.
- **`sase` on `PATH`**, only for `research:…` refs. sase-listen shells out to
  `sase artifact read` and never imports sase.

**Cost per episode** with Gemini 3.8 Flash TTS ($0.0135 per audio minute, doubling to
$0.027 on 2027-01-01):

| Episode                             | Today     | From 2027-01-01 |
| ----------------------------------- | --------- | --------------- |
| `brief`, 4 min                      | $0.05     | $0.11           |
| `full`, 16 min                      | $0.22     | $0.43           |
| `verbatim`, median report (≈ 19 min) | $0.26     | $0.52           |
| `verbatim`, p90 report (≈ 30 min)   | $0.41     | $0.81           |
| 10 `full` editions a month          | **≈ $2**  | **≈ $4**        |

- These figures exclude the agent tokens spent writing the script.
- **Re-renders are cheap.** The chunk cache is content-addressed:
  - a crashed render resumes and pays only for the missing chunks;
  - editing a paragraph re-synthesizes only the affected chunks in that chapter;
  - changing the voice or style pays for the whole episode again.
- The research flagged that free-tier Gemini TTS quotas are too low for daily use. Confirm
  that the key is on a billed tier.

## Deliberately not in v1

- **Writing:** no LLM rewrite step inside the tool. Agents, or you, write the scripts.
- **Delivery:** no Telegram code; that lives in sase-telegram. No feed _server_ either:
  sase-listen writes files, and Tailscale Funnel or any static server serves them.
- **Local voice:** no bundled local voice. Kokoro is reachable as a narrator profile on the
  OpenAI-compatible engine with a custom `base_url`, but you run Kokoro-FastAPI yourself.
- **Later ideas:**
  - a two-host "podcast" mode;
  - the daily digest;
  - a Whisper (ASR) quality gate;
  - special handling for plans or Obsidian notes;
  - an `audio` artifact kind.
- **Audio in git:** only the small `<stem>_narration.md` is committed next to its report.

## Status on 2026-10-01

| Piece              | State                                                                                                                                                                                                                                                                  |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| sase-listen master | Only the scaffold (`c35e6e2`): packaging, the config loader, and a docs skeleton. `--version` and `config` work; the other 11 subcommands print "not implemented yet" and exit 1. The CI and Docs workflows are green                                                  |
| PyPI               | No release, so `uv tool install sase-listen` fails today                                                                                                                                                                                                                |
| Release automation | **The Publish run failed.** release-please could not open the 0.1.0 PR because the repo still has `can_approve_pull_request_reviews: false`. The scaffold phase was meant to flip that. A release-please branch with a scaffold-only 0.1.0 commit exists without a PR |
| sase-telegram      | No `send_audio` yet (master is at 0.4.23)                                                                                                                                                                                                                               |
| Epic `sase-1e3`    | All 12 phases are `IN_PROGRESS`. Release, then rollout on apollo, come last                                                                                                                                                                                             |

## Worth deciding

1. **Standalone value.** Outside SASE, sase-listen is a strong verbatim reader with podcast
   packaging. But the condensed edition, the thing the research showed makes reports
   listenable, needs an agent. A documented "bring your own LLM" recipe would give PyPI
   users `full` editions with no new code: paste `sase-listen guide` into any chat model,
   save the result, then run `lint --source` and `render`.
2. **Private Markdown.** Every render except `tone` sends the text to Google or OpenAI.
   `render --publish` will put _any_ episode into a feed protected only by a secret path.
   The research said private notes must stay out of that feed and off cloud engines, but
   the script contract has no `private:` marker to enforce it. Either add one or document
   the rule prominently.
3. **The plan's open decisions:**
   - how "SASE" is pronounced (it is left out of the lexicon);
   - the default voice (`Charon` until auditions);
   - the public Funnel exposure, which is proposed through a gate.
4. **Release plumbing.** Flip the workflow permission, or add `SASE_RELEASE_TOKEN`, before
   the release phase. Otherwise there is no release PR to merge.

## Sources

- Epic bead `sase-1e3` (12 phase beads) and `plan:202610/sase_listen.md`: the shared
  contracts, CLI surface, engines, config, feed, and rollout.
- `research:202610/commute_audio_from_markdown/commute_audio_from_markdown.md`: the corpus
  measurements, engine ranking, prices, delivery options, and format rationale.
- `gh:sase-org/sase-listen` at `c35e6e2`: `pyproject.toml`, `AGENTS.md`, `cli/`,
  `config.py`, `data/pricing.yml`, and `data/lexicon.yml`.
- `gh run view 36910709733` for the release-please failure;
  `gh api …/actions/permissions/workflow`; and the PyPI JSON API (no releases).
- The sase-telegram master log (no audio branch yet).
