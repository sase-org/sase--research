# A Listen Link From Research-Swarm Reports to Their Narrated Audio

> **Research query:** How should the final report published by the `#research_swarm`
> linker agent (which should always run when the audio agent runs) link to the narrated
> audio file the swarm's audio agent generates, so the reader can quickly play the
> summary while reading, in a way that works well with the `bob highlights create` file
> hook (which may be improved) and is intuitive, reliable, and beautiful? Is this a good
> idea, would a different approach be better, which requirement adjustments are
> justified, and what solution is recommended?

![Infographic of the recommended listen-link design: the lead report fans out to parallel audio and infographic agents, the linker waits for audio before the first publication and the PDF hook, the MP3 is committed beside the report, and the reader journey runs from a "Listen: 4-minute narrated brief" line through Bob carrying the MP3 with the PDF to a native Obsidian player](research_swarm_listen_link_infographic.png)

## Bottom line

**Build it. It is a good idea, but the plan only works if the link is in place before
the PDF is rendered, and the playable surface is Bob's Obsidian vault, not the PDF.**
The design has four parts (detailed in the
[recommended solution](#recommended-solution)):

1. **Topology.** `audio=true` implies the linker, and the linker waits for the audio
   agent before it writes `<name>.md`. The `research-highlights` hook fires exactly once,
   on the `ADD` of `<name>.md`, so the link must be in the linker's first commit. Audio
   still starts right after the lead and runs in parallel with the image agent.
2. **Storage.** The audio agent writes the MP3 beside the report as
   `<name>_narration.mp3`, and it is committed like the infographic. This makes one
   relative link valid in every checkout, on GitHub, and at hook time, with no servers,
   tokens, or host paths.
3. **Markdown.** The linker adds one fixed-format line as the last paragraph of the
   research-query blockquote:
   `▶ **Listen:** [4-minute narrated brief](<name>_narration.mp3)`.
4. **Bob.** `bob highlights create` and `scan` learn a small, generic feature:
   *local audio links become playable*.
   - `create` copies the linked MP3 into the intake queue beside the PDF.
   - It rewrites the PDF's link to an `obsidian://` URI. The URI comes from a
     configurable template.
   - `scan` carries the MP3 into `lib/` and puts a native Obsidian audio player in the
     reference note, directly under the "open PDF" task.

**Two requirement changes (called out).** The narrated *brief* is a 4-minute spoken
summary, not the report read aloud. So it works best as "listen first, then read", not
as a read-along. And committing MP3s reverses the earlier commute-audio rule, "keep
generated audio out of the research repo", for swarm-linked editions only. Both are
[justified below](#requirement-adjustments).

## How it works today

Verified behavior, stage by stage:

| Stage | Today's behavior | Evidence |
| --- | --- | --- |
| Flags | `run_linker = linker or image`. Audio "does not imply the linker". | `research_swarm.md` frontmatter and the `run_linker` set line |
| Lead | Writes `<name>__final.md` when a linker runs; otherwise writes the hook-eligible `<name>.md` itself | `lead_report` in `research_swarm.md` |
| Audio | Waits only on `.final` and forks the lead. Writes the committed `<name>_narration.md` script, renders into the host-local sase-listen library, and registers the MP3 as a `file` artifact labelled `Audio edition: <title>` | `research_audio.md`; plan `202610/research_audio_after_lead.md` |
| Linker | Waits on `.final` (plus `.image`). Opening order is title → research query → infographic → `## Bottom line`. Has no audio input. | linker segment of `research_swarm.md` |
| Hook | `research-highlights` runs `bob highlights create --include-id <abs-path>` with `cwd` = the committing checkout. It fires on `ADD` only, for `commit`/`sdd`/`finalizer` producers. Drafts, `__final.md`, `_narration.md`, and `_infographic.md` are excluded. | `provider.py`; sase `file_hooks/runner.py`; chezmoi `sase.yml` |
| Bob create | pandoc → xelatex (default pandoc Markdown reader, DejaVu fonts, `--resource-path` = report dir). Stamps the page-1 marker and writes `~/bob/xlib/chat/<stem>.pdf` | `create.rs` |
| Transport | The Mac's 15-minute cron pulls apollo's and athena's whole `xlib/` with `rsync -a --remove-source-files --ignore-existing` | `vault-git-sync.md`; chezmoi `bob_xlib_pull` |
| Scan | Moves the PDF plus only a same-stem `.md`/`.textbundle` companion into `lib/`, then writes `ref/chat/<stem>.md` (title, `[[lib/chat/<stem>.pdf]]` task, managed Highlights region) | `doctor.rs` `intake_companion_moves`; `note.rs` `default_note_body` |

### Facts that decide the design

- **The research repo is public.** `gh repo view sase-org/sase--research` reports
  `PUBLIC`. It holds a 375 MiB pack and 297 committed infographics (about 50 added in
  September, median about 1.3 MB).
  - Anything in a report is published, so the cdx report's assumption of "private
    research Git history" is wrong.
  - Bob's vault, `bobs-org/bob`, is `PRIVATE`.
- **The vault already accepts audio.** `~/bob/.gitignore` un-ignores `*.mp3`, `*.m4a`,
  `*.ogg`, and similar formats. `lib/` is tracked (372 files under `lib/chat/`), and
  only `xlib/` and `lit_review/` are ignored. An MP3 beside a library PDF therefore
  syncs and is backed up like the PDF, with no config change.
- **Audio can only play on the MacBook or phone.** Research checkouts live on headless
  apollo and athena. On apollo there are 12 full research clones with no alternates,
  on a 193 GB disk with 52 GB free. A link only matters where the reader is: the
  Highlights PDF and the Obsidian vault on the Mac.
- **Timing.** On real swarms the audio agent finishes about when the image agent does:
  - `toobig_split_beyond_python`: lead 13:01, audio 13:10, image 13:11, linker 13:20.
  - `sase_rename_new_name_shortlist`: lead 14:40, audio 14:52, image 14:52, linker
    15:03.

  With `image=true`, making the linker wait for audio costs about nothing. With
  `image=false` it delays publication by about 10 minutes. The gem report's claim that
  TTS takes 2–5 minutes "versus 15–30 seconds" for the image is contradicted by these
  timelines.
- **MP3 sizes.** Output is 64 kb/s mono:
  - brief: 2.2–2.3 MB (about 4.5 minutes)
  - full: 5.5–8.6 MB (12–18 minutes)
- **`%wait` releases only on success.** Failed, killed, or crashed dependencies leave
  the waiter parked. AXE posts one red "Wait dependency can never self-resolve"
  notification, and a later *successful* run of the same dependency name releases the
  wait (sase `docs/macros.md`, `docs/axe.md`). The linker already has this exposure to
  the image agent.
- **The feed URL is unusable as a link.**
  - The feed is served by **Tailscale Funnel (public)** on `:8443`, behind a
    `--set-path=/<token>` secret.
  - Episodes are pruned after 90 days or 200 episodes.
  - The episode ID hashes the script's absolute workspace path, and `render --json`
    does not return a URL.
- **Rendering, verified with pandoc 3.1.3 and Bob's flags:**
  - `▶` and `♫` render in DejaVu. `🎧` renders as an empty box ("Missing character…
    in font DejaVu Serif").
  - `obsidian://open?vault=bob&file=lib%2Fchat%2Ftopic.mp3` survives as a PDF `/URI`.
  - A relative `topic_narration.mp3` link survives as a base-less `/URI`. PDFKit
    viewers (Preview, Highlights) do not resolve these.
  - A pandoc fenced div (`::: listen`) under a GFM reader renders as literal
    `::: listen … :::` text.
  - A `> [!AUDIO]` callout stays literal `[!AUDIO]` text in pandoc 3.1.3. It is not
    one of GitHub's five alert types either.
- **No duration probe on the host.** `ffprobe` is not installed on apollo, and
  sase-listen has no inspect command. The linker cannot measure the MP3 itself, so the
  audio agent must hand off the duration.
- **Lazy companion hazard.** SASE creates a `<stem>.md` companion for a non-Markdown
  file on its first artifact link (sase `docs/artifact_links.md`).
  - `<name>_narration.mp3` is safe: its natural companion path is the existing script.
  - A companion that does land as `*.mp3.md` would match the hook's `20*/**/*.md` glob
    and produce a spurious PDF. Exclude it.
- **Doc drift.** sase-listen `docs/sase-integration.md` still says swarm audio runs
  "after the linker when it runs… and can use the infographic as cover". The packaged
  macro and its tests deliberately do the opposite. The plugin's own `docs/macros.md`
  matches the code.

## Critique of the plan

### What is right

- **Discoverability.** Today audio reaches Telegram and AntennaPod, but nothing in the
  report says audio exists. For example, `commute_audio_from_markdown` has both a
  Highlights PDF and a library MP3, and neither its report nor its ref note points at
  the audio.
- **The linker is the right owner.** It exists so the one hook-eligible file is written
  after optional companions exist. The infographic already proved this pattern, and
  audio has the same publication-barrier problem.
- **Inviting Bob changes is necessary, not optional.** No Markdown link alone can play
  audio from a Highlights PDF.

### What is wrong or risky

1. **"The linker always runs when audio runs" is false today.** Nor does the linker
   wait for audio. Without both changes, the PDF renders before the MP3 exists, and
   there is no second chance: the hook is `ADD`-only, and Bob refuses to replace a PDF
   already in the library.
2. **"While reading" is the wrong mental model for a brief.** The brief is about 4
   minutes in 2–3 generic chapters ("The question and short answer", "The deciding
   reasons", "The recommended solution"). Listening to a summary while reading a 40 KB
   report in detail splits attention between two different texts. The natural uses are
   *listen first, then read what matters*, or *listen instead* (where Telegram and
   AntennaPod already serve). This changes
   [placement (top) and labelling (length shown)](#what-the-reader-sees). It also rules
   out read-along features like per-section timestamp links.
3. **"A link that targets the audio file" is underspecified.** The MP3 lives in a
   host-local library, a host-local artifact store, and a token-gated, pruned feed. None
   of these is a valid link target from a public Markdown file or a PDF on the Mac.
4. **Publication gains a TTS dependency.**
   - If the audio *agent* crashes, the linker parks and the report never publishes. That
     is worse than "no audio".
   - A failed *render* is harmless: the audio prompt already reports the error and
     completes.
   - v1 accepts the crash risk, matching the image agent. A host-level fix is
     [a follow-up](#follow-ups).
5. **The PDF is a hostile medium for audio.**
   - Embedded media (`media9`, RichMedia, attachments) does not play in PDFKit or
     Highlights.
   - Relative links are dead.
   - `file://` needs the Mac's absolute path. It also opens MP3s in Music.app by
     default, which imports them into the library.

   The PDF link must be rewritten, and the player belongs in Obsidian.

## Requirement adjustments

These changes to the request's requirements are called out explicitly.

1. **Audio implies the linker.** This is assumed by the request but false today. Set
   `run_linker = linker or image or audio`. `audio_edition` alone still launches
   nothing.
2. **The linker waits for audio; audio still waits only for the lead.** This is new.
   Image and audio stay parallel. The order becomes lead → {image ∥ audio} → linker →
   `ADD` hook.
3. **"Listen first", not "listen while reading".** This reframes the request. Use one
   line at the top, labelled with edition and length. Read-along sync and per-section
   timestamp links are out of scope.
4. **The MP3 is a committed research artifact,
   `<YYYYMM>/<name>/<name>_narration.mp3`.** This reverses the commute-audio report's
   "keep generated audio out of git" rule, for swarm-linked editions only. The reasons:
   - Once the report links to it, the narration is part of the report, exactly like the
     infographic. The sidecar's stated purpose is "research reports and generated media".
   - Git is the only transport that reaches the linker's workspace, the hook's `cwd`,
     GitHub, and future readers while keeping one *relative* link valid.
   - The "regenerable" argument is weak. Re-rendering costs TTS quota, and a re-render
     is not byte-identical to what was linked.
   - The cost is bounded. Audio is opt-in, a brief is about 2.2 MB (about 1.7
     infographics), and no tokens or host paths enter the repo.

   **Reopen if** the research pack passes about 1 GB, or audio becomes default-on. Then
   move `*.mp3` to Git LFS, or switch Bob's link template to a tailnet archive. Neither
   change touches what the reader sees.
5. **Degrade, never block, on render failure.** No MP3 means no listen line; the report
   still publishes. This mirrors the infographic rule. A *crashed* audio agent parks the
   linker as image already can. Recover by re-running the audio agent under the same
   name, or by killing the parked linker.
6. **No secrets, host paths, or private URLs in the public report.** That includes feed
   URLs, tailnet hostnames, `~/.sase/...` paths, and `file:` refs.
7. **Bob changes are part of v1, and generic.** Bob learns "local audio links", not SASE
   naming. The playable surface is the Obsidian note's native player plus a PDF link
   into Obsidian.
8. **Unchanged:** no `MODIFY` trigger on `research-highlights`, no `audio=true` by
   default, and swarm audio keeps narrating the lead's `__final.md`.

## Recommended solution

### What the reader sees

**Markdown** (GitHub, editors, sase pager). The listen line closes the research-query
blockquote, so "what was asked" and "how to listen" form one header card:

```markdown
# Running `toobig_split` Beyond Python: Line Limits for Rust, JavaScript, and Swift

> **Research query:** I'm thinking about running the `toobig_split` job on …
>
> ▶ **Listen:** [4-minute narrated brief](toobig_split_beyond_python_narration.mp3)

![Infographic …](toobig_split_beyond_python_infographic.png)

## Bottom line
```

Fixed format, so every report looks the same:

- **Glyph.** Use `▶` (U+25B6); it renders in DejaVu and on GitHub. Never `🎧`.
- **Link text by edition.**
  - brief: `<N>-minute narrated brief`
  - full: `<N>-minute narrated edition`. Don't imply a verbatim reading.

  `N` is the real duration rounded to the nearest minute (minimum 1). If the duration
  is unknown, drop the number.
- **Target.** Always the relative `<name>_narration.mp3`.
- **Not a heading.** No TOC entry and no section number, the same as the research
  query.

On GitHub the link opens the file page (play via Raw or download). GitHub has no inline
blob player, and that degradation is acceptable.

**PDF (Highlights).**

- Page 2 opens with the title, the research query, and then a blue
  `▶ Listen: 4-minute narrated brief` link directly above the bottom line. That is
  exactly where reading starts.
- Bob rewrites the target to
  `obsidian://open?vault=bob&file=lib%2Fchat%2F<stem>.mp3`, which opens Obsidian's
  audio player on the vault copy.
- No banner and no embedded media. Restraint is the beautiful choice here.

**Obsidian reference note** (`ref/chat/<stem>.md`, written by `scan`):

```markdown
# Running toobig_split Beyond Python

- [ ] #task #ref [[lib/chat/toobig_split_beyond_python.pdf]] #hide ^ref

![[lib/chat/toobig_split_beyond_python.mp3]]

## Highlights

<!-- highlights:begin -->
<!-- highlights:end -->
```

Obsidian renders `![[….mp3]]` as a native inline player, right under the task that
opens the PDF: press play, then open the PDF in Highlights.

- The embed sits outside the managed Highlights region, so annotation syncs preserve it.
- An `audio: lib/chat/<stem>.mp3` frontmatter field lets Dataview list "reading-queue
  items with audio".

### Changes by repository

**1. `bob-cli`: ship first, because it is inert until a report contains an audio link.**

`bob highlights create`:

- Find Markdown links whose target is a relative path with an audio extension (`mp3`,
  `m4a`, `ogg`, `opus`, `wav`, `flac`) that resolves inside the source directory and
  exists.
- Copy the first such file atomically to `<target-dir>/<stem>.<ext>` *before*
  installing the PDF. The PDF install stays the commit point. rsync's sorted transfer
  also moves `<stem>.mp3` before `<stem>.pdf`.
- In the existing Lua filter, rewrite every link to that file using
  `highlights.audio_link_template`. The default is
  `obsidian://open?vault={vault}&file={lib_path}`, where:
  - `{vault}` defaults to the `BOB_DIR` basename;
  - `{lib_path}` is the URL-encoded future `lib/<ref-type>/<stem>.<ext>`.

  With a custom `-o` outside the intake queue, leave the link unchanged and warn.
- Stamp the marker key `audio: <stem>.<ext>`, and print an `audio:` line beside `pdf:`.
  `--dry-run` shows the planned copy.
- Handle problems without failing the render, because file hooks are non-gating:
  - missing file or path outside the source tree: un-link the text and print `warning:`;
  - a second distinct audio file: same handling.
- Refuse a colliding non-identical `<stem>.mp3` without `--force`, matching the PDF
  collision guard.

`bob highlights scan`:

- `intake_companion_moves` carries a same-stem audio file with its PDF.
- **Order-independent pairing.** When a same-stem audio file sits in `xlib/` and its PDF
  is already in `lib/`, move the audio next to it. Then insert the embed into the
  existing note once, if missing. This replaces any "defer the PDF until its MP3
  arrives" logic. It also makes later backfill ([follow-up 2](#follow-ups)) free.
- An orphan audio file with no PDF anywhere is left in `xlib/` and reported by `doctor`.
  It is not an error.

`note.rs`:

- When an audio companion exists, `default_note_body` writes
  `![[lib/<ref-type>/<stem>.<ext>]]` between the PDF task and `## Highlights`.
- The projected frontmatter gains `audio`.

Other Bob work:

- **Vault git.** Keep the existing policy: `*.mp3` is already tracked, which gives
  backup and multi-machine copies. Ignore `lib/**/*.mp3` only if vault size becomes a
  concern.
- **Docs.** Add an "Audio companions" section to `docs/highlights-ref-sync.md`.
- **Tests.** Cover link rewrite, copy-before-PDF, missing file, traversal rejection,
  scan carry, late pairing, and the note embed.

**2. `sase-research-artifacts` (macros, provider, tests, docs).**

`research_swarm.md`:

- Set `run_linker = linker or image or audio`.
- Linker header: `{% if audio %}%wait:research.{@1}.audio {% endif %}`. The audio
  segment is unchanged; it waits only on `.final`.
- Add `<name>_narration.mp3` to both layout trees.
- Rewrite the `audio` description ("Implies the linker, which links the narration from
  the published report"), the top-level description, and the `linker` description.

Linker prompt, when `audio`:

- *"If `<name>_narration.mp3` exists beside the report in your research checkout, add
  the listen line as the final paragraph of the research-query blockquote, in exactly
  this format… If it is missing, publish without it and say so in the final response."*
- Take `N` and the edition from the audio agent's variables. Read them in a
  `{% raw %}` block via `agents["research.{@1}.audio"]`, and guard against missing
  keys.
- Extend the step-3 opening-order rule and the step-6 re-check to cover the line.
- The step-4 rule "relative links must resolve" then holds naturally, because the MP3
  is committed.

`research_audio.md`:

- Render with `sase-listen render <script> --json -o <report-dir>/<stem>_narration.mp3`.
  Strip `__final` from the stem, as for the script. `-o` already copies atomically via
  a temp file, and the library copy stays.
- Register *that* copy with `sase artifact create -p … -l "Audio edition: <title>"`.
  Telegram delivery is unchanged.
- Hand off the facts the linker needs (there is no `ffprobe` on the host):
  `sase var set audio_file=<stem>_narration.mp3 audio_duration_s=<duration_s> audio_edition=<edition>`.
- On render failure: leave no MP3 (or `.tmp-*`) behind, report the error code, and
  complete normally.

Everything else:

- **`provider.py`.** Add `!20*/**/*.mp3.md` (and `.m4a.md`, `.ogg.md`, `.opus.md`,
  `.wav.md`, `.flac.md`) to `_COMPANION_MARKDOWN_EXCLUDE_GLOBS`. This guards both the
  hook and the `@research` inventory against lazy companions.
- **Tests (`tests/test_macro_loading.py`).**
  - Flip `test_research_swarm_audio_does_not_imply_linker` and
    `test_research_swarm_audio_opt_in_adds_segment_without_linker`.
  - Keep "audio waits only on the lead".
  - Add "the linker waits on audio iff `audio`", "`audio_edition` alone launches
    nothing", and the new provider globs.
- **Docs.** Update `docs/macros.md` (the "never implies the linker" row) and `README.md`.

**3. `sase-listen` (docs only).** Fix `docs/sase-integration.md`. Swarm audio waits
only on the lead, and the linker waits on audio. This drift exists today regardless of
this feature.

**No changes** are needed to sase core, the sase-listen code, or the chezmoi hook
command. The existing `bob highlights create --include-id` picks up the new behavior.

### Failure modes

| Failure | Result |
| --- | --- |
| TTS render fails (quota, API error) | The audio agent completes and reports the error. No MP3 and no line; the report and PDF publish normally. |
| Audio agent crashes or is killed | The linker parks, and a red "can never self-resolve" notification names it. Re-run the audio agent under the same name (a later success releases the wait), or kill the linker. This is the same as image today. |
| Linker forgets the line | The step-6 re-check catches it. Worst case: the MP3 still sits beside the report, with no link. |
| PDF reaches the Mac before its MP3 | The note is written without the embed. The next scan pairs the late MP3 and inserts the embed. The PDF link is dead for at most one cron tick. |
| `rewrite=true` re-render later | The repo MP3 is replaced in place, so the Markdown link stays valid. The vault keeps the original. That is acceptable, because the PDF was read against it. |
| Highlights won't open `obsidian://` | Switch `highlights.audio_link_template` (for example, to a tailnet `https` archive). No code change. |
| Vault or research size growth | Watch the pack size. LFS, or a switch to a link template, is the escape hatch ([adjustment 4](#requirement-adjustments)). |

### Acceptance test

Run one real swarm. `#research_swarm(prompt=…, audio=true)`, with image off to exercise
the new wait, should produce:

- the lead's `__final.md`;
- `<name>_narration.md` and `<name>_narration.mp3`, committed by the audio agent;
- `<name>.md` with the listen line, committed by the linker *after* audio;
- `xlib/chat/<name>.pdf` and `xlib/chat/<name>.mp3` on the render host.

Then, on the MacBook after `scan`:

- clicking the PDF link in Highlights opens Obsidian on the MP3;
- the ref note shows an inline player;
- audio keeps playing while the PDF is open in Highlights.

**Verify first:** two Mac-side behaviors could not be checked from apollo. They are
whether Highlights hands custom-scheme URIs to macOS, and how Obsidian's audio view and
background playback behave. If the click is clunky, swap the template instead of
changing the design. Also confirm that opening the PDF from the note does not replace
the pane holding the player.

## Alternatives considered

### How the four reports were reconciled

| Question | cdx | cld | grk | gem | Verdict |
| --- | --- | --- | --- | --- | --- |
| Audio implies linker; linker waits on audio | yes | yes | yes | yes | **Yes** (unanimous) |
| Audio waits on image for cover art | no | no | **yes** | no | **No.** It serializes about 10 minutes and reverses the deliberate `research_audio_after_lead` decision. Cover art stays opportunistic. |
| Where the MP3 lives | content-addressed tailnet archive | **committed sibling** | library → vault via Bob | tailnet URL on `:8443` | **Committed sibling + vault companion** (see [adjustment 4](#requirement-adjustments)) |
| Link target in Markdown | `https://` archive | relative `.mp3` | `highlights://<stem>#audio` | `https://…:8443/audio/<id>` | **Relative `<name>_narration.mp3`** |
| Link target in PDF | unchanged `https://` | `obsidian://` rewrite | `highlights://` + relative | unchanged | **`obsidian://` from a configurable template** (an `https` archive stays a template swap) |
| Markup | separate blockquote | last paragraph of the query blockquote | `::: listen` div | `> [!AUDIO]` + tcolorbox | **Last paragraph of the query blockquote, `▶`** |
| Crash/failure | settlement coordinator | park (like image) + "settled wait" follow-up | complete on failure + `sase var` | soft fallback | **Complete on render failure; gate on file existence; crash parks in v1; settled wait as follow-up** |
| Bob change | optional | required, generic | required, library lookup | Lua banner | **Required, generic "local audio links"** |

Why the losing options lost:

- **gem's `https://apollo…:8443/audio/<episode_id>` is unsafe.**
  - `:8443` is the *public Funnel* port.
  - Serving a token-free path there would expose every library episode by a guessable
    slug, including non-research personal audio such as `pre-and-post-for-the-morning-review`.
  - Its `🎧` banner glyph also renders as a blank box.
- **grk's `::: listen` breaks on GitHub,** which shows literal `:::` lines.
  `highlights://<stem>#audio` has no handler: Highlights' scheme addresses PDF pages, so
  the "Play" link is dead in v1. Having Bob find MP3s through sase-listen episode IDs
  couples Bob to sase-listen internals, and those IDs cannot be recomputed from another
  workspace.
- **cdx's archive is sound engineering for a problem we do not have yet.**
  - It needs a new serving surface, cross-host transfer for athena-dispatched swarms,
    retention policy, and a connected tailnet.
  - Its "no secret, so safe in private history" argument rests on the repo being
    private. The repo is public.
  - Its strongest point survives: keep the PDF's link target swappable, which the Bob
    template provides.
- **The cdx and grk objection that MP3s don't belong in git** is weighed in
  [adjustment 4](#requirement-adjustments). Their best alternatives either put a dead or
  private URL in the public report, or need a SASE-aware resolver between the hook and
  Bob.

### Rejected alternatives

| Alternative | Why not |
| --- | --- |
| Linker publishes immediately with a link to a not-yet-existing MP3 | The PDF renders before the MP3 exists, so Bob can't carry it. If audio fails, the report ships a dead link. |
| Patch the link in after audio and re-render (`MODIFY` hook or `--force`) | The hook is `ADD`-only by design. Bob refuses to replace a library PDF, and the reader may already be annotating it. |
| Podcast feed enclosure URL | Leaks the feed token into a public repo, dies after 90 days, and isn't stable across workspaces. |
| Token-free path on the Funnel port (`:8443`) | Publicly exposes the whole library, including personal non-research episodes. |
| Content-addressed tailnet archive as v1 (cdx) | New serving surface, cross-host transfer, retention, and a private URL in a public report, with no extra reader value over the vault copy. Kept as a template swap. |
| `highlights://<stem>#audio` (grk) | No handler exists; Highlights' scheme opens PDF pages. Dead link. |
| Bob locates the MP3 via sase-listen episode ID or a SASE `file:` ref | Couples Bob to sase-listen/SASE internals. Episode IDs hash a workspace path. |
| Untracked or gitignored MP3 staged in the linker's checkout | The link is dead on GitHub and in every other checkout, and fragile if the workspace is cleaned before the hook runs. |
| Embed audio in the PDF (`media9`, attachments, RichMedia) | Not played by PDFKit or Highlights; bloats the PDF. |
| `::: listen` div or `> [!AUDIO]` callout | Renders as literal syntax on GitHub and in pandoc 3.1.3. |
| Audio waits on image for cover art | Adds about 10 minutes of serial time and reverses `research_audio_after_lead`. The title card is fine. |
| Name the file `<name>.mp3` | Its lazy companion could claim the canonical `<name>.md` path, and the name implies "the report as audio". |

## Follow-ups

None of these is needed for v1.

1. **Settled wait (sase-core).** Add a `%wait` mode that releases on any terminal
   outcome. The linker's file-existence gate then turns a crashed audio *or* image agent
   into "publish without it". This belongs in Rust per the core-backend boundary, and it
   fixes an exposure that already exists for image.
2. **Backfill.** Add a `bob highlights attach-audio <mp3> --id <stem>` that drops a
   companion into `xlib/`. Late pairing gives existing notes a player (for example,
   `commute_audio_from_markdown`). A PDF already read is never re-rendered.
3. **Tailnet `https` template.** Use this only if `obsidian://` proves clunky. Serve
   with Tailscale Serve (tailnet-only) on a separate private port, never the Funnel
   port. It would give one-click Safari playback and phone access.
4. **Close the loop in show notes.** Map the narration script's `source` to the
   published report so AntennaPod episodes link back to the written report.
5. **Repo growth guardrails.** Track the research pack size. Consider partial-clone
   (`--filter=blob:none`) research workspaces. This already matters for PNGs.

## The request as briefed

The lead researcher's restatement of the request:

> **Research request:** Add a link from the `#research_swarm` linker's published report
> to the MP3 the swarm's audio agent generates, so the reader can quickly play the
> narrated summary while reading. It should work well with the `bob highlights create`
> file hook, which may be improved. Lead the design so it is intuitive, reliable, and
> beautiful. Critique the plan, call out justified requirement changes, and end with a
> recommended solution.

## Sources

Local code and data (repo-relative):

- `sase-research-artifacts` @ `e26ee6a`:
  - `xprompts/research_swarm.md` (`run_linker`, the linker and audio segments,
    opening-order rule)
  - `xprompts/research_audio.md`
  - `provider.py`
  - `docs/macros.md`
- `sase-listen` @ `3037d60`:
  - `cli/render.py` (`-o`)
  - `pipeline.py` (atomic copy)
  - `docs/podcast-feed.md` (Funnel `:8443`, `--set-path=/<token>`, retention)
  - `docs/sase-integration.md` (stale ordering)
  - library manifests on apollo
- `bob-cli` @ `4e510cf`:
  - `highlights_ref/create.rs` (pandoc flags, Lua filter)
  - `stamp.rs`
  - `doctor.rs` (`intake_companion_moves`)
  - `note.rs` (`default_note_body`)
  - `docs/vault-git-sync.md`
  - `docs/highlights-ref-sync.md`
- chezmoi:
  - `dot_config/sase/sase.yml` (hook command)
  - `bin/executable_bob_xlib_pull` (rsync flags)
- sase @ `aeccf84`:
  - `src/sase/file_hooks/runner.py` (command + abs path, `cwd` = repo root)
  - `docs/macros.md` and `docs/axe.md` (wait semantics, `wait.artifacts`, `agents[...]`
    variables)
  - `docs/artifact_links.md` (lazy companions)
- Plan `202610/research_audio_after_lead.md` (why audio waits only on the lead).
- Vault: `~/bob/.gitignore`, the `lib/chat` tracking, and the
  `ref/chat/commute_audio_from_markdown.md` note.
- `gh repo view` visibility: `sase-org/sase--research` PUBLIC, `bobs-org/bob` PRIVATE.
- Prior research `202610/commute_audio_from_markdown/commute_audio_from_markdown.md`
  ("keep generated audio out of the research git repo").
- Empirical checks (pandoc 3.1.3 + xelatex, Bob's flags, `mutool`):
  - glyph coverage;
  - `/URI` targets;
  - GFM rendering of a fenced div and an alert callout.
- Commit timelines (from the cld report).

Web (cited by the researchers):

- [Obsidian: embed files](https://obsidian.md/help/embeds): audio embeds render a player.
- [Obsidian URI](https://obsidian.md/help/Extending+Obsidian/Obsidian+URI): vault-path
  `file`; non-Markdown files need their extension.
- [Pandoc manual, raw HTML](https://pandoc.org/MANUAL.html#raw-html): raw HTML is
  dropped in LaTeX output.
- [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve) and
  [Funnel](https://tailscale.com/docs/features/tailscale-funnel): tailnet-only vs public
  exposure per port.
- [Apple Community: Preview and links to local files](https://discussions.apple.com/thread/251142029):
  only full file URIs work.
- [GitHub community discussion #22174](https://github.com/orgs/community/discussions/22174):
  no inline audio player for blobs.
