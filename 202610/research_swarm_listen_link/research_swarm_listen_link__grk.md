---
create_time: 2026-10-04
updated_time: 2026-10-04
status: draft
tags:
  - research_swarm
  - audio
  - linker
  - highlights
  - sase-listen
  - bob-cli
---

# A listen card for research-swarm finals

**Question.** How should `#research_swarm` put a playable link to the audio agent's MP3 on the canonical report the linker publishes, so the Highlights reading queue can play the narrated edition while the report is open? Is that plan sound? What should change?

**Sources.** Independent research against:

- `sase-research-artifacts` (`research_swarm.md`, `research_audio.md`, `provider.py`, `docs/macros.md`, `tests/test_macro_loading.py`)
- `sase-listen` (`library.py`, `pipeline.py` `render --json`, `docs/sase-integration.md`, `docs/podcast-feed.md`)
- `bob-cli` (`highlights_ref/create.rs`, `highlights_ref/note.rs`, `docs/highlights-ref-sync.md`)
- SASE file hooks (`docs/configuration.md` `file_hooks`, `src/sase/core/artifact_file_types.py`)
- Prior research: `research:202609/research_swarm_linker_agent/research_swarm_linker_agent.md`, `research:202610/commute_audio_from_markdown/commute_audio_from_markdown.md`, `research:202610/sase_listen_antennapod_setup.md`
- Live corpus: research sidecar, `~/bob/ref/chat/commute_audio_from_markdown.md`, `~/.local/share/sase-listen/library/`

## Bottom line

**Yes: ship a listen card. Treat audio like the infographic: `audio=true` implies the linker, the linker waits on the audio agent, and only then is the one hook-eligible `<name>.md` written.** That is the only ordering that gets audio metadata into the Highlights PDF on the hook's single `ADD`.

Do **not** put the MP3 in the research git repo, and do **not** put a relative `.mp3` or a podcast-feed URL in the public markdown. The sidecar is public; the feed token has already leaked once; prior commute-audio research already ruled generated audio out of git.

The playable surface is the **Highlights vault**, which is where the report is actually read:

1. The linker writes a compact **listen card** plus `audio:` frontmatter on `<name>.md`.
2. `bob highlights create` copies the library MP3 next to the intake PDF, paints a banner in the PDF, and stamps an `audio` marker.
3. `bob highlights scan` moves that companion MP3 with the PDF and puts a native Obsidian `![[lib/chat/<stem>.mp3]]` player on the ref note, above the managed Highlights region.

That is intuitive (one card, one player, one file stem), reliable (convention plus `wait.artifacts`, no secret URLs), and beautiful (a quiet line in markdown, a painted banner in the PDF, a real player in the note).

The naive reading of the request — “paste a link to the audio file into the report” — is the wrong artifact. A file path is not a listening UX.

## Critique of the plan

The plan is the right *shape*. The linker exists so the hook-eligible file is written after optional companions exist. Image already proved that. Audio is the same publication-barrier problem: `research-highlights` fires only on `ADD` of `<name>.md`, timeout 120s, producers `commit`/`sdd`/`finalizer`. `MODIFY` was considered and rejected when the linker was designed, because Bob refuses an existing PDF without `--force` and a second render does not restructure prose.

Three parts of the plan as stated would make the feature worse.

**1. “A link that targets the audio file” is too literal.** The MP3 does not live next to the report. `sase-listen` commits it to `$XDG_DATA_HOME/sase-listen/library/<episode-id>/<slug>.mp3` (a 12-minute commute-audio episode on this machine is 5.8 MB). `#research/audio` then copies it into SASE artifact storage as kind `file` with label `Audio edition: <title>` so Telegram can `sendAudio`. None of those locations is a git-relative path from `<name>.md`. A markdown link to `foo.mp3` is a 404 on GitHub and a 404 in the research checkout. A markdown link to the Funnel enclosure URL embeds the feed token in a public repo — the AntennaPod setup report already recorded that leak.

**2. Audio must not wait on the linker if the linker waits on audio.** Today the packaged xprompt has audio wait only on the lead and explicitly does not imply the linker (`test_research_swarm_audio_does_not_imply_linker`, `test_research_swarm_audio_opt_in_waits_only_for_lead`). Plugin docs and `sase-listen`’s SASE-integration page say the opposite: audio waits on the linker when it runs, so the edition narrates the published file. Those two sentences cannot both be true once the linker also needs the MP3. Waiting both ways deadlocks. Swarm audio should narrate the lead’s `<name>__final.md`, the same way the image agent reads `__final.md`. A brief edition is already a rewrite; the linker’s heading cleanup does not change what 4 minutes of speech should say. Direct `#research/audio @research:…` of an already-published file still prefers `<name>.md`.

**3. A failed TTS run must not park the Highlights PDF.** Image already has this failure mode: a crashed image agent leaves the linker on a named wait that never resolves, and there is no `<name>.md` and no PDF. TTS is worse. A brief edition is several Gemini requests; the AntennaPod setup report found the key on the free tier (10 requests/day) and a real render dying mid-episode. If `audio=true` implies linker and linker waits on audio, a quota miss delays the reading queue for an optional listen affordance. The audio agent must **complete** on render failure, publish `audio_ok=false` through `sase var set`, and let the linker publish without a card — the same “completed but produced nothing” path the linker already has for a missing PNG.

Those are the justified requirement changes. The rest of the request — imply linker, put a listen affordance on the canonical report, make Highlights the reading surface, improve `bob highlights create` if needed — should be kept.

## How the system works today

### Swarm topology

`#research_swarm` in `sase-research-artifacts` authors up to nine segments. Defaults: cdx + cld + lead. Opt-in: grok, muse, gemini, image, linker, audio.

```text
researchers ──► lead (.final)
                  ├─ image?     waits on lead, forks lead, writes <name>_infographic.png
                  ├─ linker?    waits on lead [+ image], publishes <name>.md
                  └─ audio?     waits on lead only, forks lead, #research/audio
```

`run_linker = linker or image`. Audio is **not** in that or-expression. When audio runs without a linker, the lead writes hook-eligible `<name>.md` itself, the hook fires, and the MP3 arrives later — too late for the PDF, and there is no second shot.

When a linker *does* run, it still does not wait on audio and its prompt has no audio artifact loop. The published file cannot mention an episode that the linker has not seen.

There is a live docs/code split:

| Claim | Packaged xprompt + tests | `docs/macros.md` and sase-listen integration docs |
| --- | --- | --- |
| `audio=true` implies linker | No | No (agrees) |
| Audio waits on linker when linker runs | No (`%wait:research.{@1}.linker` is asserted absent) | Yes (“so the edition narrates the published `<name>.md`”) |
| Cover waits on image | No (“Do not wait for the image or linker”) | Yes (“can use the infographic as cover”) |

The implementation is the one that launches. The docs describe a pipeline that was never wired.

### What the audio agent actually produces

`#research/audio` writes `<stem>_narration.md` next to the report (`__final` stripped, same stem rule as the infographic), lints it, renders with `sase-listen render --json`, and registers the MP3. The JSON object includes `episode_id`, `audio_path`, `duration_s`, `chapters[]`, `published`, narrator, and cost. The library layout is `<episode-id>/{<slug>.mp3, manifest.json, script.md, cover.jpg, chapters.json}`.

The narration script is git’s companion. It is already excluded from the `@research` inventory and the Highlights hook, like `*_infographic.md`. Five narration scripts exist in the sidecar today. Twelve library episodes exist on this machine. The commute-audio report has both a Highlights PDF and a 12-minute library MP3, and **neither the published markdown nor the ref note points at the audio**. The gap is exactly this feature.

### What Highlights actually does

`bob highlights create --include-id` (the configured file-hook command) runs pandoc/xelatex with `--toc --number-sections --resource-path=<report dir>`, stamps a page-1 marker (`status`, `parent`, `title`, `id` = markdown stem), and writes `~/bob/xlib/chat/<stem>.pdf`. A same-stem `.md` beside that PDF is **refused**, because Highlights would treat it as an annotation sidecar. A same-stem `.mp3` is unused today and would not collide with that guard.

`bob highlights scan` moves the PDF to `lib/chat/<stem>.pdf` and writes `ref/chat/<stem>.md`:

```markdown
# Title

- [ ] #task #ref [[lib/chat/<stem>.pdf]] #hide ^ref

## Highlights

<!-- highlights:begin -->
…annotations…
<!-- highlights:end -->
```

Manual body outside `<!-- highlights:begin -->` / `<!-- highlights:end -->` is preserved. The generated skeleton has no audio slot. Sidecar image selections already copy bytes into `ref/<type>/<stem>.assets/` and embed them with `![[…]]`. Audio can follow that copy-and-embed pattern.

Obsidian plays `![[file.mp3]]` natively. Obsidian’s PDF.js viewer does **not** play embedded PDF rich media. Adobe `media9` / `run:` launch actions are a dead end for this reading queue. The PDF banner should be a visual claim plus a relative file hyperlink; the **player** belongs on the ref note, sitting next to the PDF task.

`highlights://<id>#page=N` already addresses a PDF by marker id. Extending that scheme to `#audio` is the natural click target from both the markdown card and the PDF banner. The Highlights plugin does not handle `#audio` yet; that is phase-2 plugin work, not a blocker, because the ref-note embed plays without it.

## Why a naive MP3 link fails

| Target | What breaks |
| --- | --- |
| Relative `<name>.mp3` in the research sidecar | File is not in git; GitHub 404; checkout 404; public repo would grow by ~0.5 MB per minute of audio |
| `file://` path into `sase-listen/library/` | Machine-local, breaks on the Mac vault vs apollo render host |
| Funnel / AntennaPod enclosure URL | Secret token in a public markdown file; feed was already leaked in a bead note |
| SASE `file:<id>` artifact ref | Meaningless outside a SASE agent; the Highlights PDF is read in Obsidian |
| PDF-embedded audio (`media9`) | Not played by PDF.js, Android, or Highlights |
| Patch `<name>.md` after audio finishes | Hook is ADD-only; `MODIFY` was rejected for this exact reason when the linker landed |

The infographic works as a relative `![](<name>_infographic.png)` because the PNG **is** a git sibling and pandoc’s `--resource-path` bakes it into the PDF. Audio does not have that property. Pretending it does copies the pre-linker infographic failure: 228 sibling PNGs, zero markdown embeds, PDFs with no figure.

## Requirement adjustments

Each of these is a change to the request. Kept requirements are listed after.

1. **`audio=true` implies the linker**, the way `image=true` already does. `run_linker = linker or image or audio`. Without this, the lead’s `<name>.md` is hook-eligible before the MP3 exists. **Keep, and make it the flag coupling.**

2. **The linker waits on the audio agent** (and on image when `image=true`). It finds the episode through `wait.artifacts` plus `sase var` facts, then writes the listen card. **Keep the wait. Change what gets linked.**

3. **Swarm audio narrates `<name>__final.md`**, not the published file. It waits on the lead, and on the image agent when `image=true` so the cover can be the infographic. It does **not** wait on the linker. **This overrides the current integration docs.** Direct `#research/audio` of a published report is unchanged.

4. **The git report never contains the MP3, a relative `.mp3` href, or a feed URL.** It contains a listen card (human + `highlights://<id>#audio`) and `audio:` frontmatter (machine). The vault copy of the MP3 is the playable file. **This overrides “a link that targets the audio file” as a git-relative path.**

5. **Audio failure must not block publication.** On render failure the audio agent still exits successfully with `audio_ok=false`. The linker publishes without a card and says so, matching a missing PNG. A *crashed* audio agent still parks the linker; document the same recovery as image (rerun the named audio agent, or kill the parked linker). **New, justified by TTS quota risk.**

6. **`bob highlights create` and `scan` grow companion-audio support.** The file hook command stays `bob highlights create --include-id`; the 120s timeout stays (TTS is not in the hook). **This is the invited Highlights improvement, and it is required, not optional.** A markdown card alone will not play in the reading queue.

7. **Do not enable `MODIFY` on `research-highlights` for this.** Backfill of already-published reports is `bob highlights create --force` after audio exists, or a later `bob highlights attach-audio`. **Keeps the linker-era hook policy.**

8. **Do not default `audio=true`.** Listening time is the scarce resource (September’s corpus was estimated at 37 hours of full editions). `rsa` already opts into image, not audio. **Unchanged.**

## Alternatives considered

| Alternative | Verdict | Why |
| --- | --- | --- |
| Linker waits on audio, writes listen card + frontmatter; Highlights binds the MP3 into the vault | **Recommended** | Same publication barrier as image; playable where the report is read; audio stays out of git |
| Relative `.mp3` in the research repo, gitignored | Rejected | Dead on GitHub; research sidecar is not the Obsidian vault; easy to commit by accident |
| Commit the MP3 next to the report | Rejected | Public repo, 5–8 MB per full edition, regenerable, already decided against |
| Audio waits on linker, then patches `<name>.md` | Rejected | Deadlock with a linker wait; ADD-only hook; `--force` re-render is a backfill tool, not the swarm path |
| Fire the hook on `MODIFY` | Rejected | Same reasons as the linker report: double-render, `--force`, host change, no extra editorial value |
| Linker writes a predicted path without waiting | Weak | Duration and chapter count would be lies or blanks; Highlights would have to probe the library on every create anyway. Waiting a completed audio agent is cheaper than a missing card |
| Fold the card into the lead | Rejected | Lead cannot wait on a child it has not launched (same as image) |
| Audio agent writes `<name>.md` | Rejected | Mixes narration with editing; `linker=true, audio=false` still needs a publisher |
| PDF-only attachfile / rich media | Rejected as the player | PDF.js will not play it. Keep a banner, put the player on the ref note |
| Feed URL on the card | Rejected | Secret in a public file; commute listening is already AntennaPod’s job |

## Recommended solution

### 1. Flag coupling and waits

In `research_swarm.md`:

```jinja
{%- set run_linker = linker or image or audio -%}
```

Audio segment:

```text
%wait:research.{@1}.final
{% if image %}%wait:research.{@1}.image {% endif %}
#fork:research.{@1}.final #research/audio(edition={{ audio_edition }})
```

Linker segment:

```text
%wait:research.{@1}.final
{% if image %}%wait:research.{@1}.image {% endif %}
{% if audio %}%wait:research.{@1}.audio {% endif %}
```

No `#fork` on the linker (unchanged: the file is the contract, not the lead’s transcript).

Update the input description for `audio`: it implies the linker; it no longer claims to run “in parallel with optional linker work.” Update `docs/macros.md` and sase-listen `docs/sase-integration.md` so they stop promising that swarm audio waits on the linker.

Flip the tests that currently lock the old graph:

- `test_research_swarm_audio_does_not_imply_linker` → implies linker
- `test_research_swarm_audio_opt_in_waits_only_for_lead` → waits on lead, and on image when `image=true`
- `test_research_swarm_audio_opt_in_adds_segment_without_linker` → adds both audio and linker
- planner-edge test: linker gains an audio wait; audio does not gain a linker wait

Execution matrix (default researchers cdx + cld):

| `audio` | `image` | `linker` arg | Agents | Lead writes | Hook-eligible file |
| --- | --- | --- | --- | --- | --- |
| false | false | false | 3 | `<name>.md` | lead’s `<name>.md` |
| false | false | true | 4 | `__final.md` | linker’s `<name>.md` |
| false | true | (implied) | 5 | `__final.md` | linker’s `<name>.md` + infographic |
| true | false | (implied) | 5 | `__final.md` | linker’s `<name>.md` + listen card |
| true | true | (implied) | 6 | `__final.md` | both companions |

### 2. Audio agent contract

After a successful `sase-listen render --json`:

```bash
sase var set --json audio --value-file - <<'JSON'
{
  "ok": true,
  "episode_id": "…",
  "title": "…",
  "edition": "brief",
  "duration_s": 247.1,
  "chapter_count": 5,
  "chapter_titles": ["…"],
  "audio_path": "/home/…/library/<episode-id>/<slug>.mp3",
  "published": false
}
JSON

sase artifact create -p "<audio_path>" -k file -l "audio:<episode_id>"
```

Keep Telegram delivery: sase-telegram already routes `.mp3` through `sendAudio` from the completion attachment. Prefer the structured label `audio:<episode_id>` over `Audio edition: <title>` so the linker’s `wait.artifacts` filter is exact (`kind == "file"` and `label.startswith("audio:")`), not a title guess. If a compatibility alias is wanted, set the human title as the artifact’s display via a second convention later — do not make the linker parse English.

On render failure: `sase var set --json audio --value '{"ok": false, "error": "…"}'`, no artifact, successful agent completion, report the error code and hint, never switch narrators (already in `#research/audio`).

When `image=true`, wait for the PNG and pass it as `cover` so the episode art matches the report. When the PNG is missing, omit cover and let the renderer make the title card — do not fail the edition.

### 3. Listen card the linker writes

Opening stack, nothing else between these parts:

1. frontmatter (existing fields, plus `audio:` when the episode exists)
2. one `#` title
3. research-query blockquote (unchanged)
4. infographic, when present (unchanged)
5. **listen card, when present**
6. `## Bottom line` / `## Overview`

The listen card is **not a heading**. It must not enter the PDF TOC. It is not a second blockquote — two stacked `>` callouts next to the research query would look like a duplicate question.

Exact form:

```markdown
::: listen
♫ **Brief audio edition** · 4 min · 5 chapters. [Play](highlights://<stem>#audio) · [Script](<name>_narration.md)
:::
```

Rules:

- Inner sentence is the GitHub/pager fallback. GitHub ignores the unknown `listen` fenced div and still shows the line.
- Duration is `round(duration_s/60)` minutes, never a marketing “about 4 min” when the JSON has a real length.
- Edition is `brief` or `full`, matching the script frontmatter.
- `highlights://<stem>#audio` uses the same stem `bob highlights create --include-id` will stamp as marker `id`. That is the markdown filename stem of `<name>.md`, which is `<name>`.
- The script link is a real git-relative href. It always resolves in the sidecar.
- If `audio.ok` is false or no audio artifact exists, skip the card and the `audio:` frontmatter entirely. Do not write “audio pending.”

Frontmatter the linker adds only when audio succeeded:

```yaml
audio:
  edition: brief
  duration_s: 247.1
  chapter_count: 5
  episode_id: commute-audio-from-markdown-fa2598
```

No library path, no Funnel URL, no artifact id. `episode_id` is the lookup key `bob highlights create` uses against the local sase-listen library. Unknown keys already round-trip in Highlights frontmatter; add `audio` to the standard synced field list so it reaches the ref note.

The linker remains an editor. It does not re-research. It does not invent duration. It copies numbers from `wait.artifacts` / `agents["research.{@1}.audio"].audio`.

Validate the new card the way it already validates the infographic: confirm the fenced div sits in the opening stack, the script href resolves, and `highlights://` uses the published stem.

### 4. `bob highlights create`

Discover companion audio, in this order, first hit wins:

1. `--audio PATH` (explicit, tests and backfill)
2. Report frontmatter `audio.episode_id` → `$XDG_DATA_HOME/sase-listen/library/<id>/` + `manifest.json` `audio.file`
3. Sibling `<stem>_narration.md` (with `__final` already stripped by convention) → title + source key → the same `compute_episode_id` rule sase-listen uses

If none of those resolve to an existing MP3, create behaves exactly as today. Missing audio is not an error.

When an MP3 is found:

- Copy it to `<pdf-dir>/<pdf-stem>.mp3` (intake: `xlib/chat/<stem>.mp3`). Refuse a colliding non-identical file without `--force`, matching the PDF collision guard. A same-stem `.md` sidecar remains refused; a same-stem `.mp3` is the companion.
- Stamp marker field `audio: <stem>` (bare, like `id`). Scan will turn it into ref-note frontmatter.
- Run a small Lua filter in addition to the existing inline-code break filter: a `Div` with class `listen` becomes a colored quote-like banner (DejaVu, existing geometry, `colorlinks=true`). Inner links stay hyperlinks. The `highlights://…#audio` URI is preserved for a future plugin handler. Also emit `\href{<stem>.mp3}{Play}` as a relative file link so desktop readers that resolve siblings can open the MP3.
- Do not try to embed playback with `media9`.

`create --include-id` is unchanged as the hook command. Discovery is automatic from frontmatter the linker just wrote, so the hook needs no extra flags. Copying 8 MB is well inside the 120s timeout; TTS already finished in the audio agent.

Standalone `#research/audio` of an old report, then `bob highlights create --force`, is the backfill path. The commute-audio PDF in `lib/chat/` plus library episode `commute-audio-from-markdown-fa2598` is the first backfill candidate.

### 5. `bob highlights scan`

When moving `xlib/chat/<stem>.pdf` to `lib/chat/<stem>.pdf`, also move `xlib/chat/<stem>.mp3` if present. Refuse an occupied destination the same way as the PDF. After the move, the ref-note skeleton becomes:

```markdown
# Title

- [ ] #task #ref [[lib/chat/<stem>.pdf]] #hide ^ref

![[lib/chat/<stem>.mp3]]

## Highlights

<!-- highlights:begin -->
<!-- highlights:end -->
```

The embed sits **outside** the managed Highlights region, so later annotation syncs preserve it. Put it between the PDF task and `## Highlights` so opening the note shows: title, open-PDF task, player, then annotations. That is the “play while reading” layout: PDF in the Highlights pane, player on the note.

For existing notes, if frontmatter gains `audio` and the companion MP3 now sits next to the library PDF, insert the embed once if missing; do not duplicate it.

Do not put the MP3 in `ref/chat/<stem>.assets/` unless scan’s image-asset machinery is reused. Sibling-to-PDF is simpler and keeps player and document together when the PDF is opened from the vault file browser.

### 6. Beauty notes (the card should look like it belongs)

- One speaker glyph, one line, no second H2, no table, no badge PNG.
- Edition as a word (`brief` / `full`), duration as `N min`, chapter count as `N chapters`.
- The research query stays a blockquote; the listen card stays a fenced div. They must not be the same visual sentence.
- PDF banner uses the same DejaVu stack and the existing `0.85in` geometry. A light fill and a left rule are enough; it should look like a callout, not a poster.
- Ref-note player is Obsidian’s native widget. Do not invent a custom HTML audio tag in the note.

### 7. What not to build in v1

- Highlights plugin `#audio` handler (nice; the embed already plays)
- `bob highlights attach-audio` (nice for backfill without `--force`; create `--force` is enough to start)
- Defaulting `audio=true` on `rs` / `rsa`
- Changing `research-highlights` `ops` to include `MODIFY`
- Serving the MP3 from the public research repo

## Implementation order

1. **sase-research-artifacts** swarm graph + linker prompt + audio vars/label + tests. This is the feature. A listen card with real numbers in `<name>.md` is already useful in the pager and on GitHub even before Highlights grows a banner.
2. **bob-cli** `create` discovery + companion copy + Lua banner + marker field. This is what makes the PDF honest.
3. **bob-cli** `scan` moves the MP3 and inserts the note embed. This is what makes playback one click in the reading queue.
4. Backfill: `bob highlights create --force` on reports that already have a library episode (start with `commute_audio_from_markdown`).
5. Optional: Highlights plugin `highlights://id#audio` opens the companion MP3.

## Risks

- **TTS quota parks the linker if the audio agent crashes instead of completing.** Mitigate with the complete-on-failure rule; keep the image recovery docs for a hard crash.
- **Render host vs vault host.** `create` must run where the sase-listen library is. That is already true of the file hook (apollo). The Mac vault receives the PDF (and, after this, the MP3) through the existing `bob_xlib_pull` / git-sync path. Scan has to treat the companion MP3 as part of intake, or the player never arrives on the Mac.
- **Same-stem `.mp3` collision** with some future sidecar format. None exists today. Guard with the identical-bytes `--force` rule.
- **Fenced `::: listen` in GitHub** shows the inner paragraph only. That is the intended fallback.
- **`wait.artifacts` for kind `file`.** Confirm the lazy namespace includes non-markdown, non-image artifacts (the docs say “non-chat artifact metadata”). Filter on `wait_name` + `label` prefix, not on list order.

## Verdict

Build it. The user’s instinct to route this through the linker is the same instinct that made infographics show up in Highlights, and it is correct. The adjustment is to treat the listen card as *metadata in git* and the MP3 as *a Highlights companion*, not as a git-relative audio file. That is the version of the idea that is intuitive, reliable, and beautiful.
