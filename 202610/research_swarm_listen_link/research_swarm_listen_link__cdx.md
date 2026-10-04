---
title: Research audio playback links that survive publication and Highlights
author: cdx
research_date: 2026-10-04
status: independent-research
---

# Research audio playback links that survive publication and Highlights

> **Research query:** How should `#research_swarm` attach its narrated audio summary to the linker’s published research report, with an intuitive, reliable, attractive experience through `bob highlights create`?

## Assessment

**Yes: this is a good feature.** Research reports and their narrations already exist; connecting them where the reader starts removes an unnecessary hunt through completion notifications or a podcast queue. The useful product is a small listening affordance, not a second reading system.

My recommended direction is **a normal Markdown link near the top of the report, backed by an immutable MP3 permalink on a private, durable audio archive**. Keep the podcast feed and Telegram delivery as distribution channels. Use a structured audio handoff rather than asking the linker to discover a filename or reconstruct a feed URL. Make `audio=true` imply the linker, and publish the canonical report after the selected media have a truthful terminal result.

Two findings materially change the implementation:

- The current linker can finish before audio, and Highlights runs on **ADD**, not on subsequent edits. Adding the link later is unreliable and replacing an annotated PDF would be disruptive.
- The existing feed’s MP3 URL contains the feed-wide secret and is subject to retention. Committing that URL into durable reports would disclose the credential and eventually leave broken links.

A plain playback link already survives Bob’s actual PDF renderer. Changing Bob is optional for the first usable version; a small metadata extension becomes worthwhile if the generated Obsidian reference note should also expose listening.

## Evidence and investigation boundary

I independently inspected the opened checkouts of `sase`, `sase-research-artifacts`, `sase-listen`, `bob-cli`, and the chezmoi configuration. I did not consult any peer swarm report or peer findings. Repository observations below refer to pinned revisions listed under [Sources](#sources). I also consulted official Pandoc, Obsidian, Tailscale, and MDN documentation.

This is a design investigation. I changed no product code, deployed no server, generated no paid narration, exposed no feed token, and did not test the Mac’s Highlights UI or mobile Obsidian. Where client behavior needs a live acceptance check, I identify it explicitly.

## How the current system behaves

### Swarm orchestration

In the plugin’s `research_swarm.md`:

- `run_linker = linker or image`; audio explicitly does **not** imply the linker.
- With a linker, the lead writes `<name>__final.md`; the linker creates `<name>.md` without overwrite.
- Audio waits for `.final`, forks its context, and narrates the lead’s report. It deliberately does not wait for image or linker. Cover art is opportunistic.
- The linker waits for `.final` and, when selected, `.image`. It has no audio dependency or audio input inventory.
- The linker’s opening order is currently title → query → optional infographic → bottom line. Its editorial contract allows only the query as new prose. Adding a listening row requires an explicit presentation exception and an updated opening order. [Swarm macro](https://github.com/sase-org/sase-research-artifacts/blob/e26ee6afda1c6c0dc09944e6fd6d46d1b5b9978e/src/sase_research_artifacts/xprompts/research_swarm.md)

The audio macro already writes a narration script, records `source` and `source_blob`, lints number fidelity, renders JSON, and registers the MP3. However, the artifact label is just `Audio edition: <title>`; that is not a complete report-to-audio contract. MP3s are generic `file` artifacts in SASE’s current kind vocabulary, not an `audio` kind. A linker must not assume `a.kind == "audio"`. [Audio macro](https://github.com/sase-org/sase-research-artifacts/blob/e26ee6afda1c6c0dc09944e6fd6d46d1b5b9978e/src/sase_research_artifacts/xprompts/research_audio.md)

### Highlights publication

The effective hook on this machine is `bob highlights create --include-id`, with `ops: [ADD]` and producers `commit`, `sdd`, and `finalizer`. It excludes researcher drafts, `__final.md`, narration companions, and image companions. Thus the linker’s first canonical report publication is the important boundary. The installed provider agrees with these defaults. [Hook provider](https://github.com/sase-org/sase-research-artifacts/blob/e26ee6afda1c6c0dc09944e6fd6d46d1b5b9978e/src/sase_research_artifacts/provider.py)

Bob runs Pandoc with XeLaTeX, a TOC, section numbering, colored links, and a resource path rooted at the Markdown’s directory. It copies only selected marker metadata into the PDF, currently status, parent, title, and optional filename-derived ID. Arbitrary report frontmatter is not automatically transferred into the eventual reference note. [Bob create implementation](https://github.com/bobs-org/bob-cli/blob/4e510cf50c3d11908e0b858520958e24a6d76abe/src/native/highlights_ref/create.rs)

PDFs travel from the servers’ `xlib` queues to the Mac and then into `lib`. `bob_xlib_pull` transfers files recursively, but Bob’s intake moves a PDF with only its recognized Markdown/TextBundle companions. A loose sibling MP3 is not currently a managed intake companion. Generated reference notes contain their own PDF task and Highlights section; they are not copies of the full research report. Consequently, “put an MP3 next to the report” does not by itself deliver an Obsidian player or a portable PDF link. [Intake implementation](https://github.com/bobs-org/bob-cli/blob/4e510cf50c3d11908e0b858520958e24a6d76abe/src/native/highlights_ref/doctor.rs), [Highlights bridge](https://github.com/bobs-org/bob-cli/blob/4e510cf50c3d11908e0b858520958e24a6d76abe/docs/vault-git-sync.md)

### Audio storage and distribution

`sase-listen render --json` already returns an episode ID, local audio and manifest paths, actual duration, chapters, costs, and a `published` boolean. It does **not** return the playback URL. `publish --json` does return an `item_url`, but that URL embeds the feed token. [Render serialization](https://github.com/sase-org/sase-listen/blob/3037d60800299eda8d7d43d1da6fcb4cb208779c/src/sase_listen/pipeline.py), [Feed publisher](https://github.com/sase-org/sase-listen/blob/3037d60800299eda8d7d43d1da6fcb4cb208779c/src/sase_listen/feed.py)

The managed configuration enables auto-publication and targets Apollo’s feed on port 8443. I inspected only nonsecret configuration values. The current default retention is 90 days and 200 episodes; pruning removes feed copies while retaining the library. Re-rendering a library episode can replace its MP3, because its identity derives from title and source key, not the audio content hash. A raw library path is therefore not an immutable publication identity either. [Feed documentation](https://github.com/sase-org/sase-listen/blob/3037d60800299eda8d7d43d1da6fcb4cb208779c/docs/podcast-feed.md), [Library identity](https://github.com/sase-org/sase-listen/blob/3037d60800299eda8d7d43d1da6fcb4cb208779c/src/sase_listen/library.py)

A further provenance trap: when rendering the authored script, the manifest’s `source.sha256` hashes that input script. Do not assume it hashes the original research report. Carry the report’s own immutable artifact identity and content identity explicitly; `source_blob` records the original report relationship. The published linker report will legitimately have different bytes after restructuring.

The `sase-listen` integration documentation still describes audio waiting for the linker and preferring the published report, whereas the current macro and its tests deliberately do the opposite. Update that documentation with this change; use executable source and tests as the current behavior witness.

## What readers should see

Place a single quiet line immediately after the query and before the infographic or first answer section:

```markdown
# Report title

> **Research query:** How should we ...?

> **[Listen to the summary](https://audio-host.example/audio/immutable-audio-hash.mp3)** · 4:12 · AI narration

![Descriptive infographic](report_infographic.png)

## Bottom line
```

The host above is illustrative; the real URL comes from the publisher. Use the **actual** duration, not the guide’s approximate four-minute target. For `full`, say “Listen to the audio edition”; do not imply verbatim reading. Keep technical IDs, source hashes, costs, and processing status out of this row.

This is visually subordinate to the title and answer, easy to find, and valid without special Markdown extensions. Avoid a numbered Audio heading, a TOC entry, a large cover image, or a second infographic. Use text as the accessible link label. A small play glyph may be added after verifying the PDF font supports it; the design must remain complete without it. Never rely on emoji to communicate the action.

For a PDF, clicking opens the browser’s MP3 playback view while the document remains available. That meets quick access, but it is not an inline player inside Highlights. A browser may require another deliberate play gesture. Promise easy access, not guaranteed autoplay. An actual inline player belongs in a capable Markdown/Obsidian view, not the PDF.

For an optional HTML player, native `<audio controls preload="none">` provides a small, familiar control surface. Add a visible download/playback link outside the element as a fallback. Playback rate and chapters can be enhancements if the chosen client supports them; avoid building a custom player for the first release. [MDN audio element](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/audio)

## Rendering experiment

I used a temporary synthetic report, a harmless `https://example.com/...mp3` URL, the installed Pandoc 3.1.3, and the real `bob highlights create --include-id` command. Output went to isolated temporary paths; no production reading queue was changed.

| Check | Observed result |
| --- | --- |
| Plain Markdown MP3 link → Pandoc LaTeX | A `\\href` with the exact URL survived |
| Raw HTML `<audio>` → Pandoc HTML | The player element survived |
| Raw HTML `<audio>` → Pandoc LaTeX | The element disappeared |
| Actual Bob PDF generation | Exit 0; PDF created |
| PDF inspection with `mutool` | Exact MP3 URL present as a URI link annotation |
| Bob marker inspection | Filename-derived ID remained present |

This proves the existing PDF pipeline can carry the proposed link. It does not prove a particular PDF viewer’s launch behavior, actual MP3 hosting headers, seek performance, or Obsidian mobile rendering. Pandoc also documents that raw HTML is suppressed in non-HTML output formats. [Pandoc raw HTML](https://pandoc.org/MANUAL.html#raw-html)

## Options and tradeoffs

| Approach | Strength | Practical problem | Assessment |
| --- | --- | --- | --- |
| Relative link to a sibling MP3 | Simple; useful in the research checkout | PDF moves; Bob does not transfer a loose MP3 as an intake companion | Good supplemental export, insufficient primary target |
| Absolute `file://` or workspace path | Works on the generating machine | Ephemeral checkout and different Mac paths | Reject |
| SASE `file:` artifact reference alone | Durable identity and audit trail | Not a general browser/PDF playback address | Keep in metadata, not the user-facing target |
| Existing podcast enclosure URL | Already hosted; direct MP3 | Feed-wide credential, retention, rerender replacement | Reject as a committed report permalink |
| Telegram message/audio link | Existing playback channel | Requires Telegram; message association and lifetime need management | Keep delivery, not canonical report access |
| Obsidian URI plus copied vault MP3 | Native playback; can work offline | New binary transfer and companion lifecycle; application-specific PDF action | Strong alternate if offline listening is a primary requirement |
| Private immutable HTTPS MP3 | Works across Markdown and PDF; no token in report | Requires Tailscale and an available audio host | Recommended for Bryan’s present setup |
| Dedicated web reader with text/audio synchronization | Rich integrated experience | New application, timing alignment, and substantially larger scope | Defer until usage demonstrates need |

Obsidian officially supports embedded vault audio with `![[audio.mp3]]` and URI actions that open vault-relative files, including a split pane option. Those are useful tools if local attachments become necessary, but require that the attachment actually reaches every reading device. [Obsidian embeds](https://obsidian.md/help/embeds), [Obsidian URI](https://obsidian.md/help/Extending+Obsidian/Obsidian+URI)

## Durable playback without the feed credential

Use a **dedicated archive of report-linked MP3s**, populated from completed render output or its durable SASE snapshot. Do not serve the entire library or artifact store. Copy only the MP3 and any deliberately selected public-facing playback assets.

Prefer content-addressed storage, such as `audio/<full-audio-sha256>.mp3`. A rerender writes a new object and leaves the old one intact. The report therefore keeps pointing to the edition it received, rather than silently changing audio later. Verify the copy’s hash, install atomically, and only then expose the URL as ready. Referenced audio remains retained for the report’s lifetime; feed prune/unpublish must not remove it. Backup and explicit deletion policy are part of this archive’s small operational contract.

For Bryan’s existing tailnet, Apollo is a reasonable always-on serving host. Use **Tailscale Serve**, not the public Funnel feed, for this archive. A path with no bearer secret is safe to record in private research Git history: authorization comes from the tailnet’s access policy. A content hash provides identity, not authorization. Tailscale documents Serve as tailnet-only and supports serving a dedicated file directory. [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve)

Select and configure a free private port or a suitable existing private route. Do not casually add it to port 8443: that is the configured Funnel feed. Serve and Funnel cannot provide separate private/public access on the same port; the last configuration controls the port’s visibility. [Tailscale Funnel](https://tailscale.com/docs/features/tailscale-funnel)

If rendering occurs on Athena or another dispatch host, transfer the completed immutable asset to the chosen archive host before returning a ready URL. A same-host implementation must not accidentally publish paths that only exist on the producer. Keep the archive base URL configurable; the linker should not hard-code Apollo or guess an MP3’s path.

Serve `Content-Type: audio/mpeg`, an inline disposition, real byte length, and support byte-range requests. Test `Range: bytes=0-1023` and the returned `206`/`Content-Range`, then seek near the end from the Mac browser. These are acceptance requirements, not claims about an untested current server. Range support makes remote seeking practical. [MDN range requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Range_requests)

A tailnet link requires Tailscale to be connected; it does not work offline or for an arbitrary external recipient. If those become requirements, add a local attachment export or deliberately authorized sharing mechanism. Do not silently fall back to a public feed credential.

## A structured audio handoff

Treat association and link creation as deterministic integration work. The audio agent should author narration; code should package and validate its output. Never select `--latest`, infer identity from title alone, scan other swarms’ files, or ask the linker to reverse-engineer feed configuration.

After rendering and registering the MP3, produce a small versioned descriptor. The following is a proposed schema, not an existing command contract:

```json
{
  "schema_version": 1,
  "status": "ready",
  "source_report_ref": "research:202610/topic/topic__final.md",
  "source_report_blob": "<exact report Git blob>",
  "source_report_snapshot_ref": "file:explicit:<lead-snapshot-id>",
  "edition": "brief",
  "audio_artifact_ref": "file:explicit:<audio-snapshot-id>",
  "audio_sha256": "<full MP3 SHA-256>",
  "duration_s": 252.4,
  "chapter_count": 6,
  "playback_url": "https://configured-private-host/audio/<full-sha256>.mp3"
}
```

When Git blob provenance is unavailable, use the immutable snapshot plus an explicit report SHA-256 field; do not invent a blob. Keep hash algorithms named distinctly. The report ref comes from the lead’s actual registered output, including its original month. The source snapshot identifies the input to narration; the linker’s rearranged output need not have the same hash.

Register the descriptor as a generic file artifact, for example `<name>_audio.json`, with a label such as `Audio handoff: <source-report-ref>`. Its durable identity is the returned `file:` ref; do not pretend the research Markdown provider accepts JSON documents. Select it from the exact waited audio stage’s `wait.artifacts` metadata, then read it with `sase artifact read`. Validate exactly one descriptor, matching source identity, supported schema/edition, and a verified asset. Zero or multiple matches must never trigger a guessed link.

A typed unavailable result should contain a safe reason code and the source identity, but no fabricated playback URL. Keep detailed diagnostics in the tool/agent evidence, not the report’s listening row. If the audio macro hands rendering to a monitor, the eventual completion stage must perform registration and descriptor creation before satisfying the publication dependency. The handoff itself does not mean audio is ready.

This contract avoids needing Bob to understand SASE artifact resolution, narration engines, or agent scheduling. `sase-listen` remains standalone; SASE-specific association belongs in `sase-research-artifacts` or a thin integration helper.

## Publication order and failure semantics

For successful selected media, the intended flow is:

```text
independent reports
        |
    lead __final.md
        |
        +---- image, when requested -----+
        |                                |
        +---- audio preparation ---------+-- media settlement
                                             |
                                       linker <name>.md
                                             |
                                      ADD Highlights hook
```

Change `run_linker` to `linker or image or audio`. Keep audio and image parallel after the lead. On the successful path, make the linker join the selected media results before its one canonical write. Add the audio stage before the linker segment for clarity, and update launch-expansion tests. `audio_edition` alone must still not launch either stage.

**Do not ship a bare `%wait:.audio` as the whole reliability story.** SASE’s named waits require a successful `done.json`; failed or killed predecessors leave the waiter parked. The current documentation and runner adapters explicitly describe this behavior. A global change to `%wait` would affect unrelated workflows and is not justified by this feature. [Wait contract](https://github.com/sase-org/sase/blob/aeccf843574ee08293b8fbf71e8b56a676debaa4/docs/macros.md), [Wait adapter](https://github.com/sase-org/sase/blob/aeccf843574ee08293b8fbf71e8b56a676debaa4/src/sase/axe/run_agent_wait_deps.py)

I recommend an explicit **media settlement boundary**: publication waits for a completed orchestration result, whose payload can honestly say `ready` or `unavailable`. A handled synthesis or archive failure can produce `unavailable`, notify the user, and let the linker publish the text without an audio link. The failed render retains its actual nonzero exit and error evidence; successful handling of that failure is a different operation.

Hard crashes, cancellation, and timeout also need settlement. They cannot be solved just by adding instructions telling the audio agent to write a descriptor before exiting. Use a host/workflow completion callback or equivalent durable coordinator with a bounded timeout to record the unavailable outcome and release publication. That is a proposed integration requirement, not a currently verified settlement API. If shared lifecycle or dependency semantics need extending, implement them in `sase-core` and bind them into SASE according to the project’s Rust boundary; do not create a competing Python scheduler in the plugin.

A smaller first increment can implement the successful dependency join and a visible blocked/retry outcome, but **it does not satisfy graceful failure or “always runs” guarantees**. State that limitation explicitly if choosing it. My preferred complete behavior is text publication after terminal media settlement, with no placeholder or dead listening link.

Once a report and Highlights PDF are published without audio because of a failure, a later audio retry should not automatically overwrite the annotated PDF. Offer a deliberate new export/revision or update a separately managed reference-note listening affordance. Automatic ADD/MODIFY hook expansion is not a substitute for defining this lifecycle.

## How much Bob should change

### First usable release

No Bob change is necessary to put a working MP3 link in the PDF: the rendering experiment verifies that directly. Keep the existing ADD-only hook and `--include-id`. The canonical Markdown must contain the complete link when its initial commit triggers the hook.

Do not add unconditional `--force`, reinterpret source `file:` references as local paths, or make `highlights create` wait for TTS. Bob should remain a document importer. A dead or unsupported audio target must not prevent a normal report without audio from rendering.

### Optional improvement for Obsidian reference notes

If Bryan commonly starts from Bob’s generated reference note, add a small generic media projection:

```yaml
audio_url: https://configured-private-host/audio/immutable-hash.mp3
audio_duration_s: 252.4
audio_edition: brief
```

Have `create` validate and copy this narrow allowlist into the PDF’s metadata marker. Extend the marker/frontmatter projection and the reference-note renderer so `scan`/`sync` carry those values and show a small listening row. The current create function passes no extra fields to marker composition, so simply adding report frontmatter will not accomplish this.

Keep the human-visible report row and metadata consistent through one deterministic packaging function. Preserve the required `parent`, the existing marker ID, reference-note tasks, lifecycle properties, and user-authored text. Do not write a same-stem Markdown companion into `xlib`: Bob deliberately refuses that during create because Highlights treats it as its exported annotation sidecar. [Bob reference-note renderer](https://github.com/bobs-org/bob-cli/blob/4e510cf50c3d11908e0b858520958e24a6d76abe/src/native/highlights_ref/note.rs)

Start with a portable Markdown link in the reference note too. If in-note playback is valuable, verify sanitized remote `<audio>` rendering on the actual Mac and mobile Obsidian before adding it as an optional view. Obsidian’s documented vault-file embed is established; identical behavior for a remotely hosted HTML player must be tested rather than assumed.

## Requirement adjustments I recommend

1. **Audio implies linker.** Change the current macro behavior and descriptions. Preserve ordinary report-only swarms and edition-only invocations.
2. **The link belongs to a specific verified edition.** Carry the actual source snapshot, report content identity, edition, duration, and audio artifact/hash. “Latest audio” is not acceptable.
3. **Durable means report lifetime.** Separate report-linked archive retention from the podcast queue; never commit the feed credential.
4. **Quick playback means easy access, not mandatory inline PDF playback.** Use the normal browser player first. Inline Obsidian playback is an enhancement, and offline audio is a separate requirement.
5. **Text must survive optional-media failure.** Publish without the row after a truthful terminal failure; notify the user. A bounded settlement path is required for crashes, not merely successful renders.
6. **Publish once with complete available media.** Accept some final-export latency to avoid stale ADD-only PDFs. The lead’s durable draft still provides the research while media runs.
7. **Keep the existing narration semantics.** Narrate the immutable lead source; the linker preserves its meaning. Do not introduce a dependency cycle by requiring narration of a file that must itself contain the completed audio link. Do not rerender just to acquire a late infographic cover.
8. **Avoid an audio platform project.** No synchronized highlighting, bespoke player, transcript timestamps, or new public sharing surface in the initial feature.

The tradeoff in item 6 is real: waiting for rendering increases time to the canonical report and PDF. If early PDF access matters more after real use, revisit a stable player-page URL with explicit pending/failed states. That progressive-publication design would be an intentional requirement change and needs a durable status service; it is not a simple link patch.

## Implementation sequence and acceptance checks

Implement in small, independently reviewable slices:

- **Archive and descriptor:** immutable MP3 installation, source association, ready/unavailable schema, durable registration, and configurable private serving. Keep feed behavior independent.
- **Swarm publication:** audio-implies-linker, successful media join, descriptor validation, placement exception, and settlement/recovery behavior. Update docs that still describe the old audio order.
- **Bob projection, if desired:** narrow generic audio marker properties and a generated reference-note listening row. Add inline controls only after client validation.

The useful verification matrix is:

| Scenario | Required result |
| --- | --- |
| Audio only, linker flag false | Linker requested; canonical report contains exactly one verified audio row |
| Image and audio | Media run in parallel; linker publishes one final file with both |
| No audio; edition supplied alone | Existing publication behavior; no audio stage or row |
| Render failure, archive failure, crash, cancellation, timeout | Truthful diagnostics and bounded text-publication outcome; no dead link or endless silent wait |
| Monitor handoff | Publication waits for actual rendered/registered output, not the initial audio turn’s handoff |
| Two swarms with similar titles | Correct source association; no `--latest` or filename collision |
| Month rollover or moved source | Use registered source provenance, not the current date or another checkout’s path |
| Rerender or brief/full switch | New immutable media object; old published report still targets its original edition |
| Feed prune or token rotation | Report-linked playback still works; no feed token appears in Git/PDFs |
| PDF created on Apollo, moved to Mac library | MP3 URI remains intact and opens from the actual Highlights app |
| Real server/browser seek | Correct MIME and range response; playback and seeking work |
| Optional Bob metadata | Marker → reference-note round trip preserves audio fields, ID, parent, tasks, and authored content |

Use a fake/tone renderer and isolated directories for integration tests. One real desktop end-to-end check should finish the release acceptance: successful audio swarm → canonical report → actual Highlights PDF on the Mac → click → playback. Add mobile testing only for the promised mobile surface.

## Sources

Local repository observations were pinned to these independently opened revisions:

| Repository | Revision | Key sources |
| --- | --- | --- |
| `sase-research-artifacts` | `e26ee6afda1c6c0dc09944e6fd6d46d1b5b9978e` | `research_swarm.md`, `research_audio.md`, `provider.py`, `tests/test_macro_loading.py` |
| `sase-listen` | `3037d60800299eda8d7d43d1da6fcb4cb208779c` | `pipeline.py`, `library.py`, `feed.py`, `manifest.py`, `config.py`, podcast and integration docs |
| `bob-cli` | `4e510cf50c3d11908e0b858520958e24a6d76abe` | `highlights_ref/create.rs`, `doctor.rs`, `note.rs`, Highlights and vault-sync docs |
| `sase` | `aeccf843574ee08293b8fbf71e8b56a676debaa4` | `docs/macros.md`, `run_agent_wait_deps.py`, effective `sase file-hook list --json` |
| `chezmoi` | `06eb7965501411d6d99461a9be6c6a358d8f4f08` | `home/dot_config/sase-listen/config.yml` nonsecret values; `home/bin/executable_bob_xlib_pull` |

The effective hook and managed configuration are observations from this research run, not a claim that every installation has identical configuration. Serving health, a free private port, ACL access, and live client playback remain acceptance checks. Official external documentation is linked beside the claims it supports.

## Recommended solution

Build **one compact Markdown listening row, an immutable private MP3 archive, and a structured audio descriptor joined before publication**. Make audio imply the linker, keep image and audio parallel, and give optional media a truthful bounded failure path so research remains available. Preserve the existing ADD-only Highlights workflow; the actual Bob renderer already carries the link correctly. Add generic audio metadata to Bob only when access from its generated reference notes is worth the extra slice of work. This delivers the requested experience with a small visible feature and an explicit, reliable lifecycle underneath it.
