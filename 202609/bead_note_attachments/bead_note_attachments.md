# Bead Note Attachments — Consolidated Research, Critique, and Recommended Design

_Lead researcher: cld (consolidating cdx, cld, grk, mus, gem, plus independent verification) ·
2026-09-29_

Sibling reports in this directory: `bead_note_attachments__{cdx,cld,grk,mus,gem}.md`.
This report merges them, settles where they disagree, and adds facts none of them
checked. Claims marked **(verified)** were re-checked against the tree, sase-core, GitHub,
or the live bead corpus while this report was being written.

## TL;DR

- **Build it.** Beads are SASE's evidence record, and that evidence is disappearing. Of
  90 concrete local evidence paths (`.png`, `.log`, `.json`, …) cited in bead
  descriptions and notes, **45 no longer exist, even on athena (verified)**. cld counted
  29 of 94 with a stricter pattern. None of them can be read from apollo or mac.
- **One premise is wrong, and the design depends on it.** A whole-note `@<path>` does
  not attach anything today. `read_at_path_value()` **reads the file's text into the
  note** (curl-style `-d @file`). The same rule covers about ten CLI flags (verified).
  All five researchers found this independently. Attaching is a different operation:
  keep a pointer, and snapshot the bytes somewhere else.
- **Don't make every literal `@` into `@@`.** 920 of 11,902 notes (7.7%) contain `@`
  (verified). With the boundary + path-shape grammar below, **only about 0.3%** would
  change meaning (cld: 35 notes; my re-run: 39). Only a *reference-shaped* `@` needs
  escaping.
- **Snapshot on write. Keep the bytes out of the beads repo.** Store the bytes in a
  content-addressed store (CAS). The bead event records only a small descriptor
  `{name, sha256, size, media_type}` — no paths, no bytes, no machine-local ids. Default
  shared tier: a new **private `attachments` sidecar**, reusing the existing
  prompt-archive object publisher. Large tier: optional (e.g. rclone → athena SFTP or
  R2). Past that, **local-only is an explicit, labeled choice.**
- **Images are optional in every sense.** `sase bead show` gets `-i/--images
  auto|always|never`. By default it shows half-block thumbnails, which survive the pager,
  tmux, and ssh. Full pixels open through the existing `kitten icat` viewer. **`sase
  bead read` (agents) never draws images.** It prints absolute paths that **keep the
  original extension**, because both the SASE viewer and agent Read tools pick a
  file's type from its extension (verified for SASE).
- **Two changes to the literal plan:**
  1. A whole-argument `@file` keeps meaning "read this text from a file", for every
     flag.
  2. A new `sase bead attach` covers "attach only this file".

  Also note that **`-a` on `sase bead note` is already taken by `--author` (verified)**,
  so the `-a/--attach` flag three reports proposed cannot ship as written.

---

## 1. Verified ground truth

| Area | Fact | Source |
| --- | --- | --- |
| `@<path>` today | A whole value `@<path>` is read as UTF-8 text. `@@` strips one `@`. A bare `@` stays literal. Missing or non-UTF-8 files error, with no fallback. Added 2026-08-18 (`771454166c`) for `create/update -d`, `update -n`, single-token `bead note`, and `-f k=@path`, then extended to `close`, `+1`, and `snooze`. | `src/sase/cli_file_values.py` |
| `bead note` | Expands only when the text is exactly **one argv token**. Otherwise the tokens are joined and stored literally. No size cap: a 2 GB log would be slurped into the note. | `src/sase/bead/cli_crud_evidence.py` |
| Short flags | `bead note` uses `-a/--author`, `-e/--edit`, and `-x/--remove`. On `bead show`/`read`, **`-i` and `-d` are free**. Every public long option needs a short alias. | `sase bead note -h`, `cli_rules.md` |
| Rust fast path | Every note-bearing surface runs in Python today. The Rust bead CLI doesn't dispatch `note`, `+1`, or `snooze`. `close` and `update -n/--note` are routed to Python explicitly. The `@` guard only catches a token that *starts with* `@`, so any future Rust arm that accepts note text must run the core grammar, or it will store raw `@path` tokens. | `src/sase/main/bead_fast_path.py`, sase-core `bead/cli/dispatch.rs` |
| Wire compatibility | Event payloads are serde-tagged with **no `deny_unknown_fields`**, so an optional field on `NoteAppended`/`NoteEdited` is ignored by old readers. An **unknown event operation is a hard read error** ("run `just install`"). | sase-core `bead/events/wire.rs`, `bead/jsonl.rs` |
| `issues.jsonl` | A generated projection that each writer **regenerates and commits**. An old client writing to a mixed fleet will drop the new fields from the projection (the canonical events keep them). | `docs/beads.md` |
| Repo visibility | `sase--beads`, `--agents`, `--plans`, and `--research` are all **PUBLIC**. The beads sidecar is cloned into 35 of 47 workspaces. | `gh repo view`, `sase repo list` |
| CAS precedent | The public agents sidecar already publishes prompt-cited local file bytes at `files/objects/sha256/<xx>/<sha256>`. Objects are append-only and digest-verified, they commit before rebase, and malformed files are quarantined. Sidecar roles support `visibility: private` and a hidden host-owned clone (`hidden_sidecar_clone_dir`). | `docs/agents_sidecar.md`, `docs/configuration.md` |
| Explicit artifacts | `sase artifact create` refuses to run unless `SASE_AGENT=1` and `SASE_ARTIFACTS_DIR` are set. It stores bytes under an **agent-run association**, and its ids come from the association, path, and label, not from content. The index is **machine-local**. Hash and copy are two passes. So a `file:explicit:` ref cannot be a cross-machine identity. | `src/sase/artifact_cli/create.py`, `src/sase/core/artifact_file_explicit.py` |
| Pager | `sase bead show` pages through SASE's in-process Textual pager (`PagerOrigin.BEAD`). Following a link to image, video, or PDF **suspends the pager and opens the artifact viewer** (`kitten icat`, mpv, pdftoppm). Other binaries open a `binary_card_document`. | `src/sase/pager/_resolve_common.py`, `_screen_actions.py` |
| Viewer typing | `artifact_file_view_mode()` picks the mode **by file suffix** (or an explicit kind). An extensionless CAS path would open as text. | `src/sase/ace/tui/graphics/_viewer_render.py` |
| Image rendering | Pillow is already a dependency. `CellImageRenderable` draws half-block truecolor (256-color fallback) and caps input at 25 MiB / 40 MP. `ImageFallbackRenderable` shows a card instead. `sase doctor` detects kitty graphics (kitty, Ghostty, WezTerm) and tmux passthrough. No OSC 8 hyperlinks exist anywhere yet. `src/sase/bead/note_presentation.py` is the natural home for chips. | `src/sase/ace/tui/graphics/*`, `src/sase/doctor/checks_deep_terminal.py` |
| show vs read | `show` is the human command and refuses to run inside agents (exit 2). `read -r` is the audited agent command, and its output is "identical to show". | `sase bead show -h`, `sase bead read -h` |

**Corpus (verified with `sase bead list -s all -n 0 -f json`: 6,587 beads, 11,902 notes):**

- **Cited evidence is small today:** 70 `.json`, 13 `.log`, 7 `.txt`, and 7 `.png` paths.
- **So the corpus justifies screenshots, logs, and traces now.** The need for
  multi-GB files is stated by the user but not yet shown in the corpus. That shapes the
  phasing in §6.8.
- **`@` at a word boundary, outside code:**
  - 234 bare words (`@large`, `@epic`, `@default`, …)
  - 26 `@kind:` citations
  - 36 bare `@`
  - ~50 path-shaped tokens, mostly model-alias lists like `@medium_worker/@other`, plus
    a few `@/tmp/x.md` mentions of the CLI convention.

## 2. Is this a good idea?

Yes. Bug reports, CI-failure evidence, TUI perf investigations, and `+1` repros all
depend on screenshots, traces, and logs. SASE agents already produce them (TUI
screenshot tooling, `~/.sase/perf/*-shots/`). Today, if that evidence lives outside
a workspace's lifetime, it goes to `/tmp`, and half of it is already gone. A bead that
can't show its evidence can't prove anything.

What needs to change is the plan's *shape*, not its goal. As written, it:

1. Mixes up **transclusion** (where the note's text comes from) with **attachment**
   (what the note points at).
2. Doesn't say **where the bytes live**, and that is the hard part.
3. Makes the `@@` rule too broad.
4. Leaves out privacy, purging, cross-machine availability, and size policy.

## 3. Requirement adjustments (explicit)

| # | As requested | Adjusted to | Why |
| --- | --- | --- | --- |
| R1 | `@<path>` anywhere in a note | `@<path>` **at a word boundary**, **path-shaped**, **outside code spans and fences**, attaches a **snapshot** of the file. It never transcludes. | Transcluding binaries is impossible. Transcluding large text bloats the event log and search. A path is not an identity. |
| R2 | `@@` for any literal `@` | `@@` is needed **only where a single `@` would start a reference**. Mid-word `@` (`me@host`, `repo@sha`, `claude@xhigh`) and non-path words (`@large`, `@pytest.mark.asyncio`) stay literal with no escape. A path-shaped token that doesn't resolve is a **hard error**, never silently kept as text. | This affects 0.3% of notes instead of 7.7%. It keeps the strictness the user wants (nothing is quietly misread) without taxing SASE's own `@` vocabulary. |
| R3 | Extend the whole-note `@<path>` form | A whole-argument `@file` **keeps** meaning "read the text from this file", for every flag. That text is **then scanned** for attachments. A new **`sase bead attach`** covers attaching files with no prose. A whole-argument `@file` that isn't UTF-8 fails with the exact `attach` command to run. | One rule across ~10 flags and existing skills (`-d @<path>` in `sase_new_task`). "Where the text comes from" and "what the text says" stay separate layers. |
| R4 | Robust, optional image viewing | A **`show`-only** image layer: `-i/--images auto\|always\|never` plus a config field. It is **never** used by `read`, `--format json`, pages, gates, or piped output. It degrades from thumbnails to cards to chips. | Agents get paths; humans get pictures where the terminal can draw them. |
| R5 | Large and arbitrary binaries | **Any bytes, any size, day one:** captured into the local CAS by a streaming, one-pass ingest. **Cross-machine** availability is tiered: a shared git sidecar up to 50 MiB, an optional large store above that, and otherwise an explicit **local-only** mode with an honest badge. | GitHub warns at 50 MiB and blocks at 100 MiB. The beads repo is hot and public. A silent "only on athena" is the failure this feature exists to remove. |
| R6 | (new) | Attachments get their **own store with its own visibility, private by default**. Every write prints where the bytes went. Sensitive paths are refused unless overridden. | Every SASE sidecar is public. A leaked secret in a public git repo cannot be taken back. |
| R7 | (new) | **Purge** must work without rewriting bead history (tombstones). | Accidentally attaching a secret is inevitable. |
| R8 | (new, later phase) | The grammar lives in core and is field-agnostic. Ship it on notes first (`note`, `close --note`, `update --note`), then `+1` evidence, then descriptions. | Descriptions mutate a whole field. That work can wait. |

## 4. Where the reports disagreed, and the resolution

| Question | Positions | Resolution |
| --- | --- | --- |
| Meaning of a whole-argument `@file` | **cdx:** deprecate it, add `-F/--from-file`, then `@` always means attach. **cld, mus:** keep it. **grk:** keep it for small UTF-8 text and attach binaries. **gem:** explicit `--transclude`/`--file`. | **Keep it (cld).** cdx's flip is the most uniform grammar for *notes*, but `@file` would then mean different things on `note` and on `-d`/`-f`/`--reason`, or all ~10 flags and the skills would have to migrate. grk's "attach if binary" makes the meaning depend on file contents: `@crash.log` would be inlined but `@crash.log.gz` attached. Instead, the non-UTF-8 error names the `attach` command. |
| Include small text inline? | **mus:** yes, dispatch by kind (text under 64 KiB is spliced in). **Everyone else:** no. | **No.** One syntax with two storage behaviors that depend on size is not deterministic from the user's point of view. `show` can *preview* small text attachments instead, so nothing is baked into the note. |
| Wire change now or later | **grk:** v1 has no wire change (rewrite to `@file:explicit:` + bead refs). **mus:** a hidden manifest block in the text. **cdx, cld, gem:** an optional wire field now. | **Wire field now.** It is additive and safe (old readers ignore unknown fields, verified). A text-embedded manifest or a `file:explicit` rewrite becomes a format that has to be supported forever. And `file:explicit` ids are machine-local, so the v1 note would be dead on apollo, which is the failure the feature is meant to fix. |
| Token stored in the text | **cdx:** `[name](file:explicit:…)` Markdown link. **cld:** `@attachment:<name>`. **grk:** `@file:explicit:<id>`. | **`@attachment:<name>` (cld).** It stays readable on old clients, is bead-scoped so a later note can refer back, and fits the `@kind:` citation grammar. Its canonical ref is `attachment:<bead-id>/<name>`. |
| Where the bytes live | **cdx:** a shared artifact CAS, refactoring explicit artifacts onto it; remote later. **grk:** the existing artifact store; beads-sidecar CAS for ≤ 2 MiB in v2. **cld:** a separate `~/.sase/attachments` + private `--attachments` git repo + rclone. **gem:** artifact CAS; remote via machine transport. | **cld's topology with cdx's location-free descriptor:** a local CAS under `~/.sase/attachments/`, using core `artifact_object_relpath`, and a private `attachments` sidecar role. **Never the beads sidecar:** it is cloned into 35 workspaces. Unifying explicit artifacts onto the same byte layer is a useful follow-up, not a prerequisite. gem's `sase machine rsync` does not exist. |
| Store recorded in the event? | **cld:** `"store": "attachments"`. **cdx:** location belongs in config. | **Not in the event.** Stores are an ordered config list, looked up by digest, so a local-only object can be uploaded later without changing the note. The event records `origin` (machine name) only, for the "only on athena" badge. |
| Upload failure | **cld:** fail the command unless `--local-only`. **cdx:** block only when a remote is configured as required. | **Capture always; upload synchronously; queue on failure.** Bead writes already work offline (commit now, push later). Failing the command could lose `/tmp` evidence at the moment it exists. Bytes land in the local CAS first. A failed upload goes to a durable outbox and renders **`⇡ pending upload (athena)`** until it drains. Config `bead.attachments.require_upload: true` restores cld's fail-closed behavior. |
| Bare `@name.ext` | **cld:** any 1–8-character extension is path-shaped, so it must resolve. **grk, gem:** attach only if the file exists, otherwise literal. | **Path-shaped only if the extension is in a curated core table**, then it must resolve. `@pytest.mark.asyncio`, `@app.route`, and `@research.2w.cdx` stay literal. `@AGENTS.md` and `@shot.pgn` (a typo) fail loudly. The table lives in core, not the OS MIME database, so parsing is identical on every machine. |
| Image protocol ladder | **cld:** kitty → iTerm2 → sixel → half-block. **gem:** kitty → half-block → card. **grk, mus:** half-block by default, kitty via the viewer. | **v1: half-block thumbnails plus the kitty viewer on follow.** In `--pager never` TTY mode, `always` may emit kitty graphics when detected. iTerm2 and sixel wait for a real user on those terminals ("mechanism follows corpus"). |

## 5. Mental model (the one paragraph users read)

> **Where the text comes from:** type it, or pass a whole argument `@file` to read it from
> a file, as with every SASE flag. **What the text says:** an `@path` inside the note
> text *attaches a snapshot* of that file. The bead keeps the bytes as they were at that
> moment, on every machine, even after the file is gone. Use `@@` only if you want the
> literal text `@./something`. To attach without prose, use `sase bead attach`.

## 6. Recommended design

### 6.1 Authoring grammar (sase-core)

The scanner walks the note text left to right. It extends `scan_artifact_refs` and the
`fenced_code` literal zones, so the CLI, TUI, editor highlighting, and future web clients
all agree.

| Rule | Behavior |
| --- | --- |
| Literal zones | Inline code spans and fenced code blocks are never scanned. |
| Boundary | `@` counts only at the start of the text, after whitespace, or after `( [ { < " '`. |
| Escape | `@@` at a boundary gives one literal `@`, and scanning resumes after it. |
| Citation | `@<kind>:<arg>` for a registered kind (`research`, `plan`, `bead`, `file`, …) stays a citation. |
| Reuse | `@attachment:<name>` reuses an attachment this bead already has. Nothing is uploaded. |
| Path forms | `@/…`, `@~/…`, `@./…`, `@../…`, any token containing `/`, `@"quoted path.png"`, or bare `name.ext` with `ext` in the core extension table. TLD-shaped tokens (`@google.com`) never qualify. Trailing `.,;:!?)` is trimmed. |
| Resolution | Resolved against the **invocation cwd**, with `~` expanded, even for text read from `@file`. It must be a readable **regular file**; a symlink is followed once. Directories get a `tar` hint. FIFOs, devices, and sockets are refused. |
| Failure | Any bad token fails the **whole command before anything is written**, with carets. |
| Other `@word` | Literal. If `./word` exists, the CLI adds a hint: "write `@./word` to attach it". |

```text
$ sase bead note ab "Crash after login @./shots/login.png — see @AGENTS.md"
Error: 1 attachment problem in note text — nothing was written.
  Crash after login @./shots/login.png — see @AGENTS.md
                                             ^^^^^^^^^^
  @AGENTS.md: file not found (resolved to /home/bryan/…/sase_14/AGENTS.md).
    Write @@AGENTS.md or `@AGENTS.md` for literal text, or fix the path.
```

### 6.2 CLI surface

Commands are alphabetical, with a short alias for every long option:

```text
sase bead attach <id> <file|->... [-m/--message TEXT] [-n/--name NAME] [-L/--local-only] [-S/--allow-sensitive]
sase bead attachment list  <id>                # bare `sase bead attachment` delegates to list
sase bead attachment open  <id> [<name>]       # existing viewer; n/p across all when name omitted
sase bead attachment path  <id> <name>         # materialize + print absolute, extension-preserving path
sase bead attachment purge <id> <name> -r WHY  # confirmed; bytes deleted where the backend allows
sase bead attachment push  [<id>]              # drain the upload outbox / promote local-only objects
sase bead note|close --note|update --note ...  [-L/--local-only] [-S/--allow-sensitive]
sase bead show ... [-i/--images auto|always|never] [-d/--download]
sase bead read ... [-d/--download]             # never draws images
sase bead doctor --attachments                 # dangling, orphaned, pending, tombstoned, digest mismatch
```

- **`attach` instead of an `-a/--attach` flag:** `-a` is `--author` on `note`. A verb
  also reads better (`sase bead attach sase-ab shot.png`) and takes stdin
  (`journalctl … | sase bead attach sase-ab - -n journal.log`).
- **Check collisions per parser.** The short letters above are free on `note`, `show`,
  and `read`. Check them again on `close` and `update`.
- **Help and completion:** replace the note help's "a single-token `@<path>` is read from
  that file" with the two-sentence model in §5. Shell completion should complete
  `@<path>` inside note text.

### 6.3 Data model (sase-core wire; additive, no new operation)

```json
{"kind": "note_appended",
 "entry": "Crash right after login @attachment:login.png — full log: @attachment:crash.log",
 "attachments": [
   {"name": "login.png", "sha256": "9f2c…e1", "size": 188416, "media_type": "image/png",
    "image": {"width": 1280, "height": 720}, "origin": "athena"},
   {"name": "crash.log", "sha256": "41aa…07", "size": 2202009, "media_type": "text/plain",
    "origin": "athena"}]}
```

- **Wire shape.** `NoteAppended` and `NoteEdited` each gain an optional `attachments`,
  and so does `BeadNoteWire` (`skip_serializing_if = Vec::is_empty`). Existing notes
  serialize byte-identically, and the 11,902 existing notes need **no migration**.
- **What's excluded.** No absolute source paths (they leak `/home/<user>` into a public
  repo). No store locations. No machine-local `file:explicit` ids.
- **Stored text.** It holds the display form with escapes collapsed. The renderer
  substitutes **only** `@attachment:<name>` tokens that appear in that note's manifest.
  An editor round-trip goes through a core `note_source_text()` that re-escapes boundary
  `@`s, so `parse(source(display)) == display`.
- **Names are unique per bead.** The core sanitizes names to `[A-Za-z0-9._-]` and keeps
  `original_name` for display. The same name with the same digest reuses the
  attachment. The same name with a different digest becomes `login-2.png`, and the CLI
  says so. The reducer keeps a bead **attachment roster**.
- **Identity** is the SHA-256 of the original bytes. `media_type` comes from magic bytes,
  falling back to the extension, and finally to `application/octet-stream`. MIME is
  metadata, never an admission control.
- **Edit (`-e N`)** re-runs the grammar. **Remove (`-x N`)** hides the attachments from
  the roster. Historical descriptors stay in history, and their bytes stay pinned.

### 6.4 Bytes: ingest, stores, and large files

**Ingest.** Ingest happens in core, over a Python I/O adapter:

1. Open the source once and `fstat` it. Refuse non-regular files, and check free space.
2. Stream fixed-size chunks to a `0600` temp file on the CAS filesystem, hashing and
   sniffing as it goes, with a progress line above 1 MiB. This is **one read**, not
   today's hash-then-copy.
3. Before installing, compare the source's size and mtime with the pre-copy `fstat`,
   and fail if the file changed. `fsync`.
4. Under a **per-digest lock**, rename into `objects/sha256/<xx>/<sha256>`, or discard
   the temp file if the object already exists (global dedup). `fsync` the directory.
5. Hard-link a **named view** at `files/<sha256[:16]>/<name>`, so every path shown to a
   human, the viewer, or an agent ends in the real filename and extension.
6. Only then append the note event.

A crash between steps 4 and 6 leaves a harmless orphan for grace-period GC. **A note that
points at bytes that were never captured cannot happen.**

**Stores.** Stores are an ordered, digest-keyed config list behind a `BlobStore` seam
(`has / put / get / delete / describe`). Policy lives in core; I/O adapters live in
Python.

| Tier | Default | Cap | Notes |
| --- | --- | --- | --- |
| Local CAS | `~/.sase/attachments/` (never in a workspace) | disk | Always written. It is also the read cache. |
| Shared (git) | A new reserved sidecar role **`attachments`**, `visibility: private`: a hidden, host-owned **bare partial clone** (`--filter=blob:none`) at `~/.sase/projects/<key>/repos/attachments` | **50 MiB** per file (cannot be set above 95 MiB) | Written with plumbing (`hash-object`, temp index, `commit-tree`, push with retry). It reuses the prompt-archive publisher's rules: append-only, digest-verified, quarantine, commit-before-rebase. Content-addressed paths never conflict. Reads fetch **one blob** on demand. |
| Large (optional) | `bead.attachments.large_store`: an **rclone** remote. Recommended: **SFTP to athena over the tailnet** (private, free, unlimited). Alternative: R2/S3 | configurable (default 2 GiB) | Resumable multipart uploads with checksums, and `delete` for purge. rclone is one optional binary, like `kitten`, `mpv`, and `pdftoppm`. |
| Local-only | Explicit: `-L`, or a y/N prompt on a TTY | disk | Renders **`⚠ only on athena`** everywhere. `attachment push` promotes it later **without editing the note**. |

**Upload and fetch.**

- **Upload:** tried synchronously, never under the bead lock. On failure the object goes
  to a durable outbox (the same pattern as `agents-publication-outbox.json`) and shows
  `⇡ pending upload`. The bead push pipeline drains that outbox *before* pushing beads,
  but a failed drain doesn't block bead publication.
- **Fetch:** a local CAS hit comes first, then a lazy `get` from the stores. Automatic
  fetching is capped at **25 MiB** (`bead.attachments.auto_fetch_max_bytes`). Anything
  larger renders `not downloaded (1.8 GiB) — sase bead attachment path ab dump.core`,
  and `-d/--download` forces it. Offline, cached attachments still render, and missing
  ones say `unavailable offline`.

**Safety and lifecycle.**

- **Sensitive paths:** `~/.ssh/**`, `**/.env*`, `*.pem`, `*id_rsa*`, `credentials.json`,
  and similar are refused unless `-S`.
- **Write echo:** every write prints its destination and visibility.
- **Pinning:** objects stay pinned while any current *or historical* event references
  them. Orphans go through the existing preview → restorable trash → purge flow.
- **Purge** writes a store-side tombstone and deletes the bytes where the backend
  allows. On the isolated attachments repo that means a documented `filter-repo` pass,
  which is tolerable because the repo is append-only and separate. The note then renders
  `📎 login.png (purged)`, with no event-schema change.
- **Viewing:** preview decoding runs bounded (the existing 25 MiB / 40 MP caps; no
  automatic SVG or EPS decoding), and a preview failure never fails `show`. Attachment
  text is **never** written raw to a terminal, because it may contain escape sequences.

**Why not the alternatives:** see §7. In short: Git LFS on GitHub can't purge without
deleting the repo and has 10 GiB quotas. Blobs in the beads repo hit the hot, public
repo cloned into 35 workspaces. Base64 in events adds 33%+ and poisons search. Paths
alone are what's failing today. git-annex is the closest prior art (location tracking,
special remotes), but it is too heavy a dependency. Borrow its concepts, not the tool.

### 6.5 Presentation — intuitive, reliable, beautiful

**One presentation module** (`src/sase/bead/note_presentation.py`) owns chips, glyphs,
and badges, so CLI, TUI, and pages agree. Glyphs: `🖼` image, `🎞` video, `≡` text, `📕`
PDF, `▤` archive, `◇` other binary. Chips use `PATH_COLOR #87AFFF`. Widths are measured
with `rich.cells.cell_len`, and filenames are stripped of control and bidi characters.

**`sase bead show`** on a TTY, with `--images auto` (the default):

```text
NOTES (3)

  #3 · 2026-09-29 06:12 EDT · 3m ago · bryan · 📎 2
     Crash right after login 🖼 login.png — full log: ≡ crash.log

     🖼 login.png   image/png · 1280×720 · 184 KiB                    [a] view
        ▗▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▖
        ▐  half-block thumbnail, ≤ 10 rows    ▌
        ▝▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▘
     ≡ crash.log    text/plain · 2.1 MiB · 18,204 lines               [b] view
```

- **Thumbnails** are pure SGR text, so they survive the Textual pager, tmux, ssh, and
  `NO_COLOR` (which falls back to the card). There are at most 4 per note; the rest
  render as chips.
- **Pager labels** (`[a]`, `[b]`) are a new attachment link kind. It resolves to the
  materialized named-view path and then reuses `link_target_for_existing_path`: images,
  video, and PDF suspend into the kitten viewer (n/p between them), text opens in a
  pager section, and other binaries open the existing binary card.
- **Badges** replace the thumbnail line when needed: `⇡ pending upload (athena)`,
  `⚠ only on athena`, `not downloaded (1.8 GiB)`, `unavailable offline`, `(purged)`,
  `digest mismatch`. **Prose always renders.**
- **Images control.** `-i/--images auto|always|never` plus the config
  `bead.show.images`: a permanent user choice, so a config field, not a feature flag.
  - `auto` means thumbnails only when stdout is a TTY, color is allowed, `SASE_AGENT` is
    unset, and Pillow can decode the file.
  - `always` in `--pager never` TTY mode may emit kitty graphics (Unicode placeholders
    under tmux) when doctor-style detection passes.
  - Redirected output never gets graphics, and `always` on a pipe is an error.

**`sase bead read`** (agents), and `show` when piped or with `-i never`:

```text
  #3 · 2026-09-29 06:12:40 EDT · bryan · 2 attachments
     Crash right after login [login.png] — full log: [crash.log]
     ATTACHMENTS
       login.png   image/png · 1280×720 · 184 KiB · sha256:9f2c1e…
         /home/bryan/.sase/attachments/files/9f2c1e0b77aa4c10/login.png
       crash.log   text/plain · 2.1 MiB · sha256:41aa07…
         /home/bryan/.sase/attachments/files/41aa07c3e9b1d2f0/crash.log
```

Agents get real, extension-preserving paths that they open with their own Read tools. The
output contains no escape codes and no expanded file contents. A later opt-in,
`bead.read.expand_text_attachments_under`, could inline tiny logs; it stays off by
default.

**Other surfaces:**

- **`--format json`:** `issue.notes[].attachments[]` holds the full descriptor, the
  availability state, and `local_path` only if the file is already cached. No relative
  ages, no bytes.
- **TUI Beads pane:** an *Attachments* block in note detail with half-block thumbnails.
  A new key `beads_open_attachments` (for example `a`; check the Beads-pane scope in
  `src/sase/default_config.yml` and update it there) opens the viewer. The Add-Note modal
  (`N`) reuses `@` file completion, so dragging a file into the terminal pastes a path
  that just works.
- **Bead pages** are public: they render `🔒 login.png (private attachment)` unless the
  store is public.
- **Write-time echo** shows what was captured and where it went:

```text
$ sase bead note ab "Crash right after login @./shots/login.png — log: @/tmp/crash.log"
  🖼 login.png  image/png · 1280×720 · 184 KiB   ⇡ sase-org/sase--attachments (private) 0.8s
  ≡ crash.log   text/plain · 2.1 MiB             ⇡ sase-org/sase--attachments (private) 0.4s
Noted: sase-ab — Login crashes on fresh profile  (#3 · 📎 2)
```

### 6.6 Rust / Python boundary

This follows `rust_core_backend_boundary`: a web or mobile frontend would need the same
grammar, manifest, and policy, so those belong in core.

- **sase-core:**
  - the grammar scanner and the extension table
  - `note_source_text()`
  - name sanitization and uniquing
  - `AttachmentWire` and the optional event fields
  - the roster reducer
  - size-tier and auto-fetch policy
  - object relpaths and the tombstone format
  - JSON wire

  Then move sase's `sase-core-revision.txt` pin forward.
- **Python:**
  - streaming I/O adapters and MIME/Pillow sniffing
  - `BlobStore` adapters (git plumbing, rclone)
  - the outbox and terminal detection/rendering
  - the CLI, the pager link kind, and the TUI

  Keep note-bearing verbs on the Python path (§1) until a Rust arm calls the core
  grammar.

### 6.7 Rollout and phases

Everything sits behind a `beta` flag, `bead_note_attachments`. This is epic scaffolding,
created with `sase flag new` and removed when the epic lands. Both flag states get tests.
**Upgrade athena, apollo, and mac before the first attachment write lands.** Otherwise an
old writer regenerates `issues.jsonl` without the new fields, and the projection
flip-flops.

1. **P0 — core.**
   - Grammar, wire fields, roster reducer, and `note_source_text`.
   - A golden corpus test that replays the §1 simulation against a fixture, pinning the
     ~0.3% blast radius.
2. **P1 — useful end to end.**
   - Local CAS, streaming ingest, and the `attachments` sidecar role (`sase repo init`,
     hidden clone, publisher).
   - The commands: `note` / `close --note` / `update --note`, `attach`, and
     `attachment list|path`.
   - Text rendering in show/read/JSON, the write echo, the outbox, `bead doctor
     --attachments`, and a `sase doctor` store-reachability check.
   - Docs (`docs/beads.md`), the `sase_beads.md` memory, and note-related skills, updated
     via `/sase_memory_write` and the generated-skills flow.
3. **P2 — beautiful and large.**
   - Thumbnails, the pager attachment link kind, and `attachment open`.
   - The TUI Beads pane and keymap.
   - The rclone large store, `-L` local-only, `attachment push`, and `-d/--download`.
4. **P3.**
   - Purge and tombstones, and page embeds.
   - `+1` evidence, then descriptions.
   - The `@attachment:<bead>/<name>` prompt kind (launch agents with a bead's evidence).
   - Folding `sase artifact create --bead` into bead attachments behind a `sunset` flag.
   - Gate/Telegram photo delivery, and OSC 8 links.

**Acceptance criteria:**

- Prose with any number of inline or quoted attachments works.
- `@@` and the error diagnostics behave identically in core, CLI, and TUI tests.
- Byte-exact round trips for non-UTF-8 and NUL-filled multi-GiB (sparse) fixtures, in
  bounded memory.
- A failed attachment mutates nothing.
- The source file can be deleted right after the command without harming the note.
- No image bytes or escape codes appear in `read`, JSON, or piped output.
- Every availability state has a badge on a machine that lacks the bytes.

## 7. Alternatives rejected

| Approach | Why not |
| --- | --- |
| Transclusion everywhere (`@path` splices text) | Impossible for binaries. Bloats events and search. Loses provenance. The whole-argument form already covers the useful case. |
| Base64 or bytes in bead events / `issues.jsonl` | 33%+ overhead, poor merges, and a permanent blob in a public repo that every write rebases. |
| Blobs in the beads sidecar (grk v2) | A hot, public repo cloned into 35 workspaces. Purging means rewriting 18k+ commits. |
| Git LFS | GitHub LFS objects can only be removed by deleting the repo. 10 GiB storage and bandwidth quotas. Needs `git-lfs` on every machine. |
| `file:explicit` refs + bead refs as the identity (grk v1) | Machine-local, agent-run-scoped, not content-addressed. Dead on apollo and mac. |
| Hidden manifest block in the note text (mus) | Parse-on-render. A forever format that is worse than an additive wire field. |
| Markdown `![](path)` as the authoring syntax (gem) | Clashes with the user's `@` request and SASE's `@` vocabulary. Pages can still render Markdown. |
| New `attachment_added` event operation | Older SASE on another machine would **hard-fail** reading the bead stream (verified). |
| Kitty graphics inside the Textual pager / by default | Fights the pager and breaks on tmux, ssh, pipes, and agents. Suspend into the existing viewer instead. |
| A universal `@@` | Changes 7.7% of notes and SASE's own `@large`, `repo@sha`, and `@kind:` vocabulary. |

## 8. Risks

- **Grammar false positives.** Mitigated by the curated extension table, the failure
  carets, the corpus golden test, and the write echo, which makes an unintended capture
  obvious.
- **The two layers of `@`.** Mitigated by the one-paragraph model (§5) in help and docs,
  and by the non-UTF-8 error that names `attach`.
- **Growth of the private attachments repo.** GitHub guidance is < 5 GB. The 50 MiB tier
  cap and the large store absorb heavy files. `sase artifact stats`-style reporting
  should show logical vs physical bytes. Because the event is location-free, a store can
  be rotated or migrated without touching beads.
- **Mixed fleet** (see §6.7): upgrade every machine first. The event store is always
  authoritative, and `bead doctor --fix-projection` repairs the projection.
- **Scope.** This is an epic (4 phases). P1 alone fixes the dead-evidence problem for
  screenshots and logs.

## 9. Open questions for the user

1. **Visibility.** Should attachments default to **private**, even though every other
   sidecar, including the agents sidecar that already publishes prompt-cited files, is
   public? I recommend private: a published screenshot cannot be un-published.
2. **Large-store default.** **SFTP to athena** (private, free, needs the tailnet), or
   **Cloudflare R2** (reachable from anywhere, 10 GB-month free)? rclone supports both.
3. **Caps.** 50 MiB for the git tier, 2 GiB for the large tier, 25 MiB for auto-fetch,
   and 4 thumbnails per note. Are these right?
4. **Whole-argument `@file`.** Do you accept R3 (keep "read text"; add `attach`)? The
   alternative is cdx's `-F/--from-file` migration, after which `@` would mean attach
   everywhere. It is more uniform for notes, but it changes about 10 flags and existing
   skills.
5. **Upload failure policy.** Is the default queue-and-badge right, or do you want
   fail-closed (`require_upload: true`)?

## 10. Recommended solution

Build **bead note attachments as immutable, content-addressed snapshots taken when the
note is written, with the bytes kept outside the bead store**:

1. **Grammar (sase-core).**
   - Inside note text, `@path` attaches a file when it is at a word boundary, outside
     code, and path-shaped: `/`, `~/`, `./`, `../`, contains `/`, quoted, or `name.ext`
     with a known extension.
   - `@@` escapes only where a reference would otherwise start. `@kind:arg` stays a
     citation. `@attachment:<name>` reuses an existing attachment. Other `@words` stay
     literal.
   - An unresolvable path fails the whole command before anything is written, with
     carets and a fix.
   - A whole-argument `@file` keeps reading text from the file, and that text is then
     scanned. `sase bead attach` attaches files without prose.
2. **Wire.**
   - An optional `attachments` manifest on `NoteAppended`, `NoteEdited`, and
     `BeadNoteWire`: name, sha256, size, media type, image dimensions, origin machine.
     No paths, no stores, no machine-local ids.
   - Readable `@attachment:<name>` tokens in the text.
   - No new event operation and no migration.
3. **Bytes.**
   - A one-pass streaming ingest into a local CAS with extension-preserving named views,
     written before the event.
   - Shared by default through a new **private `attachments` sidecar** (hidden bare
     partial clone, prompt-archive publisher semantics, 50 MiB cap).
   - An optional **rclone large store** above that. **Local-only** is an explicit,
     badged choice that can be promoted later.
   - Uploads are synchronous with an outbox fallback. Fetches are lazy with a cap.
   - Sensitive paths are refused. Destination and visibility are echoed. Purging works
     through tombstones. Objects stay pinned while any event references them.
4. **Viewing.**
   - `show` renders chips, cards, and badges everywhere, adds half-block thumbnails
     under `-i/--images auto`, and opens full pixels through the existing kitten viewer
     from pager labels, `attachment open`, and the TUI Beads pane.
   - `read` and JSON never draw. They give agents absolute, extension-preserving paths
     plus digests.
5. **Rollout.** Ship behind a `bead_note_attachments` beta flag, in phases P0 → P3.
   Upgrade the fleet before the first write. Descriptions and `+1` evidence come later
   through the same core grammar.

This keeps everything the user asked for: `@path` anywhere, `@@`, optional images, and
any binary at any size. It avoids the traps the evidence exposes: rewriting 7.7% of notes,
citing paths that die, bloating a hot public repo, silently machine-local "attachments",
and no way to take back a leaked secret.

---

### Provenance

- **cdx:** the registration lists two snapshots of the same canonical report from one
  run. The earlier draft (`file:explicit:9606ed8da54f33ce9c2b9a9a`, 587 lines) was
  superseded by the final version, which is byte-identical to the moved file
  (`file:explicit:318cae903eefec1fe910a7a4`, 603 lines). That is one report, not two.
- **All five reports** were read through their canonical `research:` references.
- **Independent checks:**
  - source reads in sase and sase-core (`cli_file_values.py`, `cli_crud_evidence.py`,
    `bead_fast_path.py`, `artifact_file_explicit.py`, `artifact_cli/create.py`, pager
    resolve/actions, `_viewer_render.py`, `graphics/cell.py`, `checks_deep_terminal.py`,
    `bead/events/wire.rs`, `bead/jsonl.rs`, `bead/cli/dispatch.rs`)
  - `sase bead note|show|read -h`
  - `gh repo view` visibility for five repos
  - `docs/agents_sidecar.md`, `docs/configuration.md`, `docs/beads.md`, and
    `docs/artifact_references.md`
  - a fresh corpus export and re-simulation (6,587 beads, 11,902 notes)
- **External facts carried over from cld and cdx:** GitHub's large-file, LFS, and
  partial-clone docs; the kitty graphics protocol; Pillow's security guidance; the OCI
  descriptor spec. These were not re-fetched.
