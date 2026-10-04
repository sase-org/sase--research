# A "Listen" Link From Published Research Reports to Their Narrated Audio

> **Research query:** Add a link from the `#research_swarm` linker's published report to
> the MP3 that the swarm's audio agent generates, so the reader can play the narrated
> summary while reading. It should work well with the `bob highlights create` file
> hook, which may be improved if needed. The design should be intuitive, reliable, and
> beautiful. Critique the plan, call out any requirement adjustments, and end with a
> recommended solution.

## Bottom line

**This is a good idea, but three things the plan takes for granted are not true today,
and the most visible reading surface (the Highlights PDF) cannot play a plain Markdown
link.** Concretely:

1. **The linker does not always run when audio runs.** `audio=true` explicitly "does
   not imply the linker" (`research_swarm.md:109`, `run_linker = linker or image` at
   `:130`). Even when the linker runs, it does not wait for audio: the two run in
   parallel after the lead (`:385-386`, `:514`).
2. **The PDF is rendered exactly once.** The `research-highlights` hook only fires on
   `ADD` (`provider.py:123`), i.e. when the linker first commits `<name>.md`. Editing
   the file later does not re-render it, and `bob highlights create` refuses to replace
   a PDF that has already been archived to `lib/`, even with `--force`. So the link has
   to be in the linker's first commit, which means **the linker must wait for audio**.
3. **The MP3 is not in the research repo.** It lives in the host-local sase-listen
   library (`~/.local/share/sase-listen/library/<episode-id>/<slug>.mp3`), plus a
   tokened, tailnet-only, 90-day-retained feed copy. Neither is a good link target.
4. **A relative link to an `.mp3` is dead in the PDF.** I rendered one through bob's
   exact pandoc/xelatex flags. The result is a PDF `/URI (x_narration.mp3)` action with
   no base. PDFKit viewers like Preview and Highlights don't resolve these, and nothing
   copies the MP3 next to the PDF anyway.

**Recommendation:** make the MP3 a committed sibling of the report and let each surface
resolve the link the way it needs:

- **Swarm topology:** `audio=true` implies the linker. The order becomes lead →
  {image ∥ audio} → linker.
- **Audio agent:** renders straight into the research directory as
  `<name>_narration.mp3` (`sase-listen render -o`, which already exists).
- **Linker:** adds one fixed-format line to the research-query blockquote:
  `▶ **Listen:** [4-minute narrated brief](<name>_narration.mp3)`.
- **`bob highlights create`:** learns a small, generic feature: *local audio links
  become playable*. It carries the MP3 into the Highlights queue alongside the PDF,
  rewrites the PDF's link to an `obsidian://` URI that resolves on the Mac, and `scan`
  embeds a native audio player in the Obsidian reference note.

The Markdown stays portable. The PDF link works. The reading-queue note gets an inline
player, and that is where "beautiful" really lands. No new server, token, or feed
dependency is needed.

One requirement I would reframe. A 4-minute *brief* is not a read-along of a 45 KB
report, so it is better as "listen first (or instead), then read" than as "listen
while reading". This changes the link's placement and wording (top of the report,
labelled with its length), not the feature.

## How it works today

| Stage                 | What happens                                                                                                                                                          | Evidence                                                                         |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Lead                  | Writes `<name>/<name>__final.md` when the linker runs, else `<name>/<name>.md`                                                                                        | `research_swarm.md:131`                                                          |
| Image (opt-in)        | Waits on the lead; writes `<name>_infographic.png`                                                                                                                    | `research_swarm.md` image segment                                                |
| Audio (opt-in)        | Waits **only** on the lead; writes `<name>_narration.md` (committed), renders the MP3 into the sase-listen library, registers it with `sase artifact create`          | `research_audio.md:35-66`; plan `202610/research_audio_after_lead.md`            |
| Linker (opt-in/image) | Waits on the lead (+ image). Publishes `<name>.md` in a fixed opening order: title, research query, infographic, bottom line                                          | `research_swarm.md:385-386,435`                                                  |
| `research-highlights` | Fires on the **ADD** of `20*/**/*.md` (drafts, `__final`, `_narration`, `_infographic` excluded) from commit/sdd/finalizer producers. Gets only the absolute path     | `provider.py:99-127`; sase `file_hooks/runner.py:160`                            |
| `bob highlights create` | pandoc → xelatex (`--toc --number-sections`, DejaVu fonts, `--resource-path=<source dir>`), stamps a marker, installs `xlib/chat/<stem>.pdf`                       | bob `create.rs:459-490`                                                          |
| Transport             | The Mac's 15-minute cron runs `bob highlights scan`, whose pre-scan hook `bob_xlib_pull` rsyncs **all** of apollo's/athena's `xlib/` to the Mac                       | bob `docs/vault-git-sync.md:175-216`; chezmoi `bin/executable_bob_xlib_pull:177` |
| Scan                  | Moves the PDF (and only a same-stem `.md`/`.textbundle` companion) from `xlib/` to `lib/`; writes `ref/chat/<stem>.md` with `[[lib/chat/<stem>.pdf]]`                 | bob `doctor.rs:300-332`, `note.rs:60-98`                                         |
| Reading               | Highlights Pro on the MacBook, from the Obsidian reading queue                                                                                                         | bob `docs/highlights-ref-sync.md:892-913`                                        |

Facts that shape the design:

- **Timing (real swarms, 2026-10-04).** On `toobig_split_beyond_python`:
  - lead 13:01
  - audio commit 13:10
  - image 13:11
  - linker publish 13:20

  On `sase_rename_new_name_shortlist`:
  - lead 14:40
  - audio 14:52
  - image 14:52
  - linker 15:03

  Audio finishes at about the same time as the image. So with `image=true`, making the
  linker wait for audio costs about **0 extra minutes**. With `image=false` it delays
  publication by about 10 minutes.
- **`%wait` only unblocks on success.** Failed, killed, or crashed dependencies leave
  the waiter parked forever, and the waiter raises a "terminally blocked wait"
  notification (sase `docs/axe.md:249-257`, `docs/notifications.md:740-746`). The
  linker already has this exposure to the image agent; audio adds a second, more
  failure-prone dependency (an external TTS API).
- **MP3 sizes.** Output is 64 kb/s mono CBR:
  - brief edition: about 2.2–2.3 MB (4.3–4.6 min)
  - full edition: about 7.4–8.9 MB (15–18 min)

  For comparison, the research repo is a 374 MiB pack, and its 296 infographics have a
  median size of 1.3 MB.
- **Feed links are a trap.** The per-episode feed URL is
  `https://apollo.<tailnet>.ts.net:8443/<token>/episodes/<id>/<slug>.mp3`.
  - The token is the feed password (`feed.py:555`).
  - Feed copies are pruned after 90 days or 200 episodes.
  - The episode ID hashes the script's *absolute workspace path*, so it changes when
    you re-render from another workspace.
  - `render --json` does not even return it.
- **Fonts.** 🎧 (U+1F3A7) renders as an empty box in the PDF; xelatex reports "Missing
  character … in font DejaVu Serif". ▶ (U+25B6) and ♫ render correctly. I verified
  this by rendering.
- **Companion collision hazard.** SASE lazily creates a `<stem>.md` companion for a
  non-Markdown sidecar file on its first artifact link. If that path exists, it uses
  `<stem>.<ext>.md` instead.
  - An MP3 named `<name>.mp3` could therefore claim **the canonical report path**
    `<name>.md` if it gets linked before the linker publishes.
  - `<name>_narration.mp3` is safe: its natural companion path is already the
    narration script, so a companion would land at `<name>_narration.mp3.md`.
  - The `research-highlights` and `research` inventory globs do not exclude
    `*.mp3.md` today.

## Critique of the plan

### What is right about it

- **Discoverability.** Today the audio reaches Telegram and AntennaPod (research
  scripts auto-publish), but nothing in the report says audio exists. One clearly
  labelled link at the top fixes that.
- **Durable pairing.** Report and narration become one unit in one directory. That
  matches how the infographic already works, and it survives feed pruning and episode
  ID churn.
- **It fits existing machinery.** The linker already embeds a sibling asset (the
  infographic) under strict rules ("embed only a file you have confirmed exists"), and
  the file hook already renders whatever the linker publishes.

### What is wrong or risky

1. **"While reading" is the wrong mental model.** The brief is a 4-minute spoken summary
   with 2–3 generic chapters ("The question and short answer", "The deciding evidence",
   "What to do next"). It is not the report read aloud.
   - Listening to a summary while reading the same report in detail splits attention
     between two different texts.
   - The natural uses are *listen first, then read the parts that matter* and *listen
     instead* (away from the desk, where Telegram and AntennaPod already serve).
   - So the link belongs at the top, labelled with its length, and nobody should spend
     effort on read-along features like per-section timestamp links.
2. **The linker becomes mandatory.** `audio=true` now costs an extra `@xlarge` linker
   turn (about 9 minutes of agent time in the timelines above) and switches the lead to
   `__final.md`. That is the price of having a publication step after the audio exists,
   and there is no cheaper correct option (see "Rejected alternatives").
3. **Publication gains a TTS dependency.** If the audio *agent* crashes, the linker
   parks and **the report never gets published or rendered**. That is worse than
   "no audio". A failed *render* is harmless: the audio prompt already says to report
   the error, so the agent still completes. The real risk is a provider crash or kill.
   I accept it for v1 because the image path already has the same exposure and the
   blocked-wait notification makes it visible. A host feature that removes it is listed
   as a follow-up.
4. **Repo growth.**
   - At September's rate (91 report directories), audio on a third of swarms adds about
     70 MB a month, roughly 19% of today's pack each month.
   - Every swarm with audio would add about 210 MB a month.
   - Every research checkout pays this (12 of 21 workspaces have one).

   This is acceptable because audio is opt-in and the MP3 is the same order of
   magnitude as an infographic. Watch it, though: Git LFS or partial clones are the
   escape hatch.
5. **The PDF is a hostile medium for audio.** PDFs can't play audio portably. Relative
   links are dead in PDFKit. `file://` URLs need the Mac's absolute path and open MP3s
   in Music.app, which *imports them into the library*. The link must be rewritten for
   the PDF, and the inline player belongs in Obsidian, not the PDF.

### Rejected alternatives

| Alternative                                                                                   | Why not                                                                                                                                                                                          |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Linker publishes immediately with a link to the not-yet-existing MP3                          | The PDF renders before the MP3 exists, so bob can't carry it. If audio then fails, the report ships a dead link.                                                                                 |
| Patch the link in after audio finishes and re-render                                          | MODIFY doesn't re-fire the hook, bob refuses to overwrite an archived PDF, and the user may already be annotating it.                                                                            |
| Link the podcast feed URL                                                                     | Leaks the feed token into git, GitHub, and every agent that reads the report. Dies after 90 days. Not stable across workspaces. Depends on apollo being up.                                      |
| Link the `~/.sase/artifacts/...` stored copy or `file:explicit:` ref                          | Machine-local, not a URL, means nothing on GitHub or the Mac.                                                                                                                                    |
| Embed the MP3 inside the PDF (attachment, RichMedia, Sound annotation)                        | Poor and inconsistent viewer support (Highlights/PDFKit don't play them); bloats every PDF.                                                                                                     |
| bob silently injects audio into the PDF from a naming convention (no link in the Markdown)    | Misses the stated goal (a link *in the report*), couples bob to SASE naming, and leaves the Markdown surfaces (GitHub, editors) without it.                                                      |
| Name the file `<name>.mp3`                                                                    | Companion hazard: it can claim `<name>.md`. It also implies "the report as audio" when it is a brief.                                                                                           |

## Requirement adjustments (called out)

- **R1 (from the request, today false) — Audio implies the linker.** Set
  `run_linker = linker or image or audio`. Update the `audio` input description
  ("Implies the linker, which links the narration from the published report").
  `audio_edition` alone still launches nothing.
- **R2 (new) — The linker waits for audio.** Add `%wait:research.{@1}.audio` when
  `audio`. Audio itself still waits only for the lead, which keeps the
  `research_audio_after_lead` decision intact.
- **R3 (reframed) — "Listen first", not "listen while reading".** Put one link at the
  top, labelled with edition and length. Explicitly out of scope: read-along sync and
  per-section timestamp links.
- **R4 (new) — The MP3 is a committed research artifact.** It lives at
  `<YYYYMM>/<name>/<name>_narration.mp3`, beside its script. Git is the only transport
  that reaches the linker's workspace, GitHub, and future readers while keeping a
  *relative* link valid.
- **R5 (new) — Degrade, never block, on render failure.** No MP3 means no listen line,
  and the report still publishes. This mirrors the infographic rule.
- **R6 (new) — No secrets or servers in links.** A link must never carry the feed
  token or depend on a feed's retention.
- **R7 (new, the "beautiful" part) — The reading-queue note gets an inline player.**
  The Obsidian reference note for the PDF embeds the MP3. This is the best "press play,
  then open the PDF" experience on the Mac.
- **Scope note.** v1 covers swarm runs only. A standalone `#research/audio` run on an
  already-published report puts the MP3 beside it but does not edit the report: its PDF
  already exists and cannot be re-rendered (see above).

## Recommended solution

### What the reader sees

**In the Markdown (GitHub, editors, sase pager).** The listen line is the last
paragraph of the research-query blockquote, so "what was asked" and "how to listen"
form one header card:

```markdown
# Running `toobig_split` Beyond Python: Line Limits for Rust, JavaScript, and Swift

> **Research query:** I'm thinking about running the `toobig_split` job on …
>
> ▶ **Listen:** [4-minute narrated brief](toobig_split_beyond_python_narration.mp3)

![Infographic …](toobig_split_beyond_python_infographic.png)

## Bottom line
```

Fixed wording rules, so every report looks the same:

- Use `▶` (U+25B6). It renders in DejaVu (PDF) and on GitHub. Never `🎧`, which
  renders as an empty box in the PDF.
- Link text by edition:
  - brief: `<N>-minute narrated brief`
  - full: `<N>-minute full narration`

  `N` is the duration rounded to the nearest minute (minimum 1). If the duration is
  unknown, use `narrated brief` or `full narration`.
- The target is always the relative `<name>_narration.mp3`.

On GitHub the link opens the file page; play it via Raw or download. GitHub has no
inline audio player for blobs, which is an acceptable degradation.

**In the PDF.** I rendered the real `toobig_split_beyond_python.md` with this line
through bob's exact flags.
- Page 1 is the title and TOC.
- Page 2 opens with the numbered title, the research query, then
  `▶ Listen: 4-minute narrated brief` as a blue link, directly above "Bottom line".
- That is exactly where reading starts. The infographic floats to its own page 3, so
  the listen line sits right above the bottom line.
- bob rewrites the link to
  `obsidian://open?vault=bob&file=lib%2Fchat%2F<stem>.mp3`. I confirmed that pandoc
  and hyperref carry this URI through intact.

**In the Obsidian reference note** (`ref/chat/<stem>.md`, written by `scan`):

```markdown
# Running toobig_split Beyond Python

- [ ] #task #ref [[lib/chat/toobig_split_beyond_python.pdf]] #hide ^ref

![[lib/chat/toobig_split_beyond_python.mp3]]

## Highlights
```

Obsidian renders `![[….mp3]]` as a native inline audio player. Pressing play and then
opening the PDF in Highlights keeps the audio playing. The marker key `audio:` also
round-trips into the note frontmatter, so Dataview can query "reading-queue items with
audio".

### Changes by repository

**1. `sase-research-artifacts` (macros, provider, tests, docs)**

- `research_swarm.md`:
  - `run_linker = linker or image or audio`.
  - Linker header gains `{% if audio %}%wait:research.{@1}.audio {% endif %}`.
  - Linker and lead layout lines list `<name>_narration.mp3`.
  - Update the top-level and `audio` input descriptions.
- Linker prompt, when `audio`:
  - Add a `wait.artifacts` listing for the audio agent's file artifacts (MP3s are kind
    `file`; filter by the `Audio edition` label).
  - Add a step: *"Link the narration. If `<name>_narration.mp3` exists beside the
    report in your research checkout, add the listen line as the final paragraph of
    the research-query blockquote, in exactly this format … Take the duration from the
    audio artifact's label. If the file is missing, publish without the line and say so
    in the final response."*
  - Extend the opening-order rule (`:435`) and the step-6 re-check to cover it.
- `research_audio.md`:
  - Render with `-o <report-dir>/<stem>_narration.mp3` (same `__final` stem stripping
    as the script). `-o` already copies atomically and leaves the library copy in
    place.
  - Register *that* copy as
    `sase artifact create -p <report-dir>/<stem>_narration.mp3 -l "Audio edition (M:SS): <title>"`.
    The duration comes from `render --json`'s `duration_s`, which the agent already
    reports.
  - On render failure, leave no MP3 behind.
  - Telegram delivery is unchanged (it uses the stored copy).
- `provider.py`: add `!20*/**/*.mp3.md` (and `.m4a`, `.ogg`, `.opus`, `.wav`, `.flac`)
  to `_COMPANION_MARKDOWN_EXCLUDE_GLOBS`. This is defense in depth against the lazy
  companion path landing in the hook or the research inventory.
- Tests (`tests/test_macro_loading.py`):
  - Audio implies the linker.
  - The linker waits on audio iff `audio`.
  - Audio still waits only on the lead.
  - `audio_edition` alone launches nothing.
  - Add the new glob to the provider-spec tests.

  Docs: `docs/macros.md` (the "never implies the linker" row) and `README.md`.

**2. `bob-cli` (`bob highlights create` / `scan`)**: a generic "local audio links"
feature, not SASE-specific.

- `create`:
  - Find Markdown links whose target is a relative path with an audio extension
    (`mp3, m4a, ogg, opus, wav, flac`) that resolves *inside* the source directory and
    exists.
  - Copy the first such file atomically to `<target-dir>/<stem>.<ext>` **before**
    installing the PDF. The PDF install is the commit point, and rsync's sorted
    transfer moves `.mp3` before `.pdf`.
  - Rewrite every link to it, via the existing Lua filter, to a URI from a configurable
    template. The default is `obsidian://open?vault={vault}&file={lib_path_urlencoded}`,
    where `{vault}` defaults to the `BOB_DIR` basename and `{lib_path}` is the future
    `lib/<ref-type>/<stem>.<ext>` that `create` already computes.
  - Stamp the marker key `audio: <stem>.<ext>`, and print an `audio:` line beside
    `pdf:`.
  - Missing file, out-of-tree path, or a second distinct audio file: un-link the text
    and print `warning:`. Never fail the render, because file hooks are non-gating.
  - `--dry-run` shows the planned copy.
- `scan`:
  - `intake_companion_moves` (`doctor.rs:300`) carries a same-stem audio file with the
    PDF.
  - If the marker declares `audio:` but the companion hasn't arrived yet, defer that
    PDF to the next scan. After a cap (say 1 hour), proceed and warn.
  - An orphan audio file in `xlib/` is ignored, not an error.
- `note`: when an audio companion exists, `default_note_body` (`note.rs:60`) writes
  `![[lib/<ref-type>/<stem>.<ext>]]` below the `^ref` line. Only new notes are affected.
- Config: `highlights.audio_link_template` in `~/.config/bob/config.yml`. This makes the
  PDF link target swappable without code changes, for example to an `https://` template
  later.
- Vault git: keep `*.mp3` out of the vault repo. The Mac is the only machine that plays
  it, and the research repo is the durable copy.
- Docs: a short "Audio companions" section in `docs/highlights-ref-sync.md`. Tests
  cover link rewrite, copy, missing file, traversal rejection, scan carry and deferral,
  and the note embed.

**3. No changes required** in sase core, sase-listen, or the chezmoi hook config. The
existing command `bob highlights create --include-id` picks up the new behavior.

### Failure modes

| Failure                                     | Result                                                                                                       |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| TTS render fails                            | The audio agent completes and reports the error. No MP3, no listen line; report and PDF publish normally.    |
| Audio agent crashes or is killed            | The linker parks; a "terminally blocked wait" notification fires. Relaunch audio or clear the wait. (Same as image today.) |
| Linker forgets the line                     | Its step-6 re-check catches it. Worst case: no link, but the MP3 is still beside the report.                 |
| MP3 committed but the Mac pull splits it from the PDF | The marker's `audio:` key makes `scan` defer the PDF until its companion arrives.                    |
| Narration re-rendered later (`rewrite=true`) | The repo MP3 is replaced in place, so the Markdown link stays valid. The vault copy stays the original (acceptable). |
| `obsidian://` blocked by a viewer           | Change `highlights.audio_link_template`; no code change.                                                    |

### Acceptance test (one real swarm)

`#research_swarm(prompt=…, audio=true)` (no image) should produce:

- the lead's `__final.md`;
- `<name>_narration.md` and `<name>_narration.mp3` committed by the audio agent;
- `<name>.md` with the listen line, committed by the linker *after* audio;
- `xlib/chat/<name>.pdf` and `xlib/chat/<name>.mp3` on apollo.

Then on the MacBook, after `scan`:

- clicking the link in Highlights opens Obsidian on the MP3;
- the reference note shows an inline player.

The two Mac-side behaviors are the only parts I could not verify from apollo:
Highlights' handling of `obsidian://` and Obsidian's audio view. Check them first. If
the click is clunky, switch the template (below).

### Optional follow-ups (not needed for v1)

1. **Settled wait** (sase core). Add a `%wait` mode that releases on any terminal
   outcome, so a crashed audio or image agent can't strand publication. The linker
   would then just see "no MP3".
2. **Tailnet `https` listen endpoint.** A token-free, tailnet-only path keyed by the
   research path would autoplay in Safari, work on the phone, and enable `#t=` chapter
   deep links. Browsers have partial support for media fragments on direct media URLs, so verify this in Safari before relying on it.
   Adopt it only if `obsidian://` proves clunky; it's a template change in bob.
3. **Close the loop in podcast show notes.** sase-listen already supports a "Read the
   written report" link, but only for ref sources. Map the script's `source` to the
   published report's URL.
4. **Audio in sase's pager and TUI.** There is no `audio` artifact kind or player today
   (MP3s go to `xdg-open`).
5. **Repo growth guardrails.** Track the research pack size. Consider Git LFS for
   `*.mp3`, or partial-clone workspaces, if audio becomes the default.
6. **Unrelated rendering nit spotted while testing.** Full-page infographics float to
   their own page, and the figure caption overlaps the page-number footer.

## Sources

Local code and data (repo-relative):

- `sase-research-artifacts`:
  - `src/sase_research_artifacts/xprompts/research_swarm.md` (`:109`, `:130-131`,
    `:385-386`, `:435`, `:514`)
  - `src/sase_research_artifacts/xprompts/research_audio.md`
  - `src/sase_research_artifacts/provider.py` (`:36-46`, `:99-127`)
  - `tests/test_macro_loading.py`
  - `docs/macros.md`
- Plan `plans:202610/research_audio_after_lead.md`: why audio waits only on the lead.
- `sase-listen`:
  - `src/sase_listen/library.py` (episode ID = slug + sha256 of the script path)
  - `cli/render.py` (`-o` copy; `--json` fields)
  - `feed.py` (tokened item URLs, retention)
  - `config.py` (64 kb/s mono)
  - live library manifests on apollo
- `bob-cli`:
  - `src/native/highlights_ref/create.rs:459-490` (pandoc/xelatex flags)
  - `stamp.rs` (collision rules)
  - `doctor.rs:300-332` (intake companions)
  - `note.rs:60-98` (note body)
  - `docs/vault-git-sync.md:175-216`
  - `docs/highlights-ref-sync.md`
- chezmoi:
  - `home/dot_config/sase/sase.yml:17-19` (hook command)
  - `home/bin/executable_bob_xlib_pull:177` (unfiltered rsync)
- sase:
  - `src/sase/file_hooks/{runner,dispatch,commit}.py`
  - `src/sase/config/file_hooks.py`
  - `docs/axe.md:249-257`, `docs/notifications.md:740-746` (wait semantics)
  - `docs/artifact_links.md:148-150` (lazy companions)
  - `src/sase/core/artifact_file_types.py` (no `audio` kind)
- Research repo:
  - commit timelines for `toobig_split_beyond_python` and
    `sase_rename_new_name_shortlist`
  - pack size and PNG statistics
  - narration script frontmatter
- Empirical: pandoc 3.1.3 + xelatex renders with bob's flags. These showed the missing
  🎧 glyph, the `/URI` targets (relative, `obsidian://`, `https`), and the page layout
  of the real `toobig_split_beyond_python.md` with a mock listen line.

Web:

- [Obsidian — Accepted file formats](https://obsidian.md/help/file-formats) and
  [Embed files](https://obsidian.md/help/How+to/Embed+files): MP3 embeds render as an
  audio player.
- [Obsidian URI](https://obsidian.md/help/uri): `file` may be a vault path; non-Markdown
  files need their extension.
- [Apple Community — Preview and links to local files](https://discussions.apple.com/thread/251142029):
  Preview supports only explicit full file URIs, not relative ones.
- [MDN — Media fragments](https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Fragment/Media_fragments)
  and [IndieWeb — media fragment](https://indieweb.org/media_fragment): `#t=` on media
  URLs.
- [GitHub community discussion #22174](https://github.com/orgs/community/discussions/22174):
  GitHub's blob view has no inline audio player; use Raw or download.
