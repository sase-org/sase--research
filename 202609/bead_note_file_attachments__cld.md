# Bead File Attachments — Research, Critique, and Recommended Design (cld)

_Researcher: cld · 2026-09-29 · scope: `sase bead note` attachments, image viewing, large and
binary files_

## TL;DR

- **The goal is good. Beads are SASE's evidence record, and today evidence gets lost.**
  Notes already cite local screenshots and logs by path. Of 94 such paths in bead
  descriptions and notes, **29 are already gone even on athena.** The rest exist only on
  athena, and some point at files that keep changing (`~/.sase/logs/tui.log`). For
  example, `sase-133.5.4` compared `/tmp/local.png` with `/tmp/apollo.png`, and both files
  are gone.
- **The plan as written mixes up two different features.** Today a note of exactly
  `@<path>` does **not** attach anything. It **reads the note's text from that file**
  (`src/sase/cli_file_values.py`), curl-style. About ten CLI flags share that behavior.
  "Attach a file anywhere in a note" is a new feature, and it should live in a different
  layer.
- **Requiring `@@` for every literal `@` would break too much.** 920 of 11,902 existing
  notes (7.7%) contain `@`. Most of those are mid-word: email-style author stamps,
  `claude@xhigh`, `repo@sha`, `builtin@commit`. I recommend a grammar where `@` only
  matters at a word boundary and only in front of a path-shaped token. Under that
  grammar, **only 35 notes (0.29%) would have needed an escape.**
- **Never store a path. Store a snapshot of the bytes when the note is written.** Keep
  the bytes **out of the beads git repo**. That repo is written to constantly, is
  **public**, is already 140 MiB with 18k commits, and every bead write takes its lock.
  Put the bytes in a content-addressed attachment store behind a small `BlobStore` seam:
  - **Default backend:** a private `<repo>--attachments` git repo, kept as a hidden,
    host-owned partial clone, with a 50 MiB per-file cap.
  - **Large files:** an optional backend (via `rclone`, for R2/S3/an SFTP folder on
    athena) handles files up to GiBs.
- **Upload the bytes before writing the note** (the same rule git-LFS uses for pointers).
  A crash can then leave unused bytes behind, but never a note that points at missing
  bytes.
- **Images are a `sase bead show`-only layer, off unless it can work.** `sase bead read`,
  the agent command, never draws images. It prints real local paths that end in the
  original file extension, so agents can open them with their own Read tools. The image
  layer tries, in order: kitty graphics → iTerm2 → sixel → the truecolor half-block
  renderer SASE already has (`CellImageRenderable`, which survives pagers) → nothing.

The full recommendation is in [§9](#9-recommended-solution).

---

## 1. What exists today (ground truth)

| Area | Finding | Where |
| --- | --- | --- |
| `@<path>` values | `read_at_path_value()` is used when the **whole CLI value** is `@path`. It reads the file as UTF-8 text. A leading `@@` escapes one `@`, a bare `@` stays literal, and a missing or non-UTF-8 file is an error. Used by `note`, `update --note/--description`, `create --description/--reason`, `close --note/--reason`, `+1 --note`, `snooze --reason`, task-type `-f k=@path`, and `sase flag new` prose. | `src/sase/cli_file_values.py`, `src/sase/bead/cli_crud_*.py`, `src/sase/task_types/fields.py` |
| `sase bead note` | `@path` counts only when it is the **single** argv token (`len(text) == 1`). With several tokens, the tokens are joined with spaces and taken literally. | `src/sase/bead/cli_crud_evidence.py:136` |
| Note storage | Notes are a structured, append-only log. The event is `NoteAppended { entry }`, plus `NoteEdited { note_id, text }` and `NoteRemoved`. The reducer stamps id, timestamp, and author. | `sase-core: crates/sase_core/src/bead/events/wire.rs` |
| Forward compatibility | An **unknown event operation is a hard read error** ("just install"). Serde **ignores unknown fields** (no `deny_unknown_fields`). So new data can safely go in *optional fields on existing events*. A new operation cannot be added safely while other machines may run older SASE. | `sase-core: bead/jsonl.rs` tests |
| Prompt `@` grammar | Core `scan_artifact_refs()` already has the rules for where `@` counts: after whitespace, a quote, or `(`; trailing punctuation trimmed; quoted payloads. Prompt `@path` parsing skips bare words, URLs, and TLD-shaped tokens. Core also has a shared fenced-code scanner for literal zones. | `sase-core: artifact_ref/scanner.rs`, `fenced_code.rs`; `src/sase/file_references.py` |
| Existing "attach" | `sase artifact create -p F --bead ID` copies F into `~/.sase/artifacts` (**local to one machine**) and adds a typed `related` artifact link to the bead. It only runs inside agents (`SASE_AGENT=1`) and is never shown inline in notes. | `src/sase/artifact_cli/create.py` |
| Content-addressed precedent | The agents sidecar stores prompt-archive bytes at `files/objects/sha256/<xx>/<sha256>`. Those objects are append-only, their hashes are checked, and bad files are quarantined. Core has `artifact_object_relpath()`. | `docs/agents_sidecar.md`, `sase-core: artifact_object_store.rs` |
| Machine write lane | Accepted decision: machine writes go to a hidden, host-owned clone at `~/.sase/projects/<key>/repos/<role>`. They never go to primary-nested clones or to workspace clones that can be evicted. | decision `machine-link-writes-off-primary` |
| Image rendering | Two paths already exist. (1) The Pillow **half-block** `CellImageRenderable` works in any truecolor terminal and is plain SGR text. (2) The full-screen **artifact viewer** uses `kitten icat` (kitty graphics), handles tmux passthrough, and pages images, PDFs, and Markdown with n/p. `sase doctor` has `terminal.kitty_graphics` and tmux-passthrough checks. | `src/sase/ace/tui/graphics/*`, `src/sase/doctor/checks_deep_terminal.py` |
| Show vs read | `sase bead show` is the human command and refuses to run inside agents. `sase bead read -r` is the audited agent command and currently prints output "identical to show". Long output goes to an **in-process Textual pager**, not `less`. | `sase bead show -h`, `src/sase/cli_pager.py` |
| Beads repo | `sase-org/sase--beads` is **PUBLIC**. On the primary it is a 140.6 MiB pack with 18,280 commits, and it is materialized lazily in each workspace. The plans repo is 127 MiB and also public. | `gh repo view`, `git count-objects` |
| Dependencies | Pillow is already a runtime dependency. SASE does not emit OSC 8 hyperlinks anywhere yet. `PATH_COLOR = #87AFFF`. | `pyproject.toml`, `src/sase/cli_show_palette.py` |

## 2. Evidence from the real corpus

I pulled all 6,575 beads and 11,902 notes with `sase bead list -s all -n 0 -f json`. Then I
simulated the grammar options against them. Code spans and fences were excluded where
noted.

**How `@` is used today**

| Measure | Count |
| --- | --- |
| Notes containing any `@` | 920 / 11,902 (7.7%) |
| Mid-word `@` outside code (emails/author stamps, `claude@xhigh`, `builtin@commit`, `git@github.com`, `master@<sha>`) | 859 occurrences |
| Word-boundary `@` outside code | 301 occurrences in 157 notes |
| …of which bare words or placeholders (`@epic`, `@large`, `@default`, `@sase-44.6`, `@<size>`) | 244 |
| …of which artifact citations (`@research:…`, `@plan:…`, `@agent:…`, `@file:…`) | 21 |
| …of which bare `@` / `@@` | 35 |
| …of which **path-shaped** (`@AGENTS.md`, `@medium_worker/@other`, `@src/`) | 48 tokens in **35 notes (0.29%)** |

**What this means:**

- A literal "every `@` must be `@@`" rule would affect **7.7%** of notes. Most of that
  comes from mid-word uses that nobody would read as a file reference.
- The recommended grammar in §5.1 affects **0.29%**. Nearly all of those are SASE
  model-alias paths like `@medium_worker/@other`, which belong in backticks anyway.

**Local evidence files cited today**

- There are 94 absolute, `~`, or `/tmp` paths with evidence-like extensions (`.png`, `.log`,
  `.json`, `.txt`, `.gz`) in descriptions and notes.
- **29 of them no longer exist, even on athena.**
- None of the 94 can be read from apollo or mac.
- Some of them point at files that keep changing (`~/.sase/logs/tui.log`), so the
  citation no longer shows what the author saw.

This is the strongest argument for the feature, and for **capturing a snapshot when the
note is written** rather than storing the path.

## 3. Critique of the plan

### 3.1 Is this a good idea?

Yes. Beads carry bug reports, `+1` reproductions, CI-failure evidence, TUI perf
investigations, and close notes. The evidence behind them is often a screenshot, a trace,
a log, or a repro bundle. SASE's own agents produce many screenshots (the TUI snapshot
tooling, the `~/.sase/perf/*-shots/` directories). If that evidence isn't durable and
readable from every machine, the bead can't really prove anything. The user should build
this. What I'd change is the plan's shape, not its intent.

### 3.2 Problems with the plan as written

1. **Semantic collision.** Today, whole-note `@path` means "take my text from this file",
   not "attach this file". If `@path` inside prose meant *transclusion* (paste the file's
   text in), the image and binary requirements would make no sense. If it means
   *attachment*, then `sase bead note X @/tmp/n.md` and `sase bead note X "see @/tmp/n.md"`
   do different things. The rule that separates them has to be stated in one sentence and
   enforced, or it becomes a trap. §5.1 handles this with two explicit layers.
2. **`@@` everywhere is too broad** (see §2). It also clashes with SASE's own vocabulary:
   size aliases (`@large`), `%model:@xhigh`, `repo@sha`, and `@kind:` artifact
   citations.
3. **A path is not an attachment.** A path means something only on one machine and only
   until the file changes or is deleted. Paths must be resolved and snapshotted **when the
   note is written**, and rendering must never depend on the reader's cwd or filesystem.
4. **Where the bytes live is the real design problem, and the plan doesn't address it.**
   The obvious place, the beads git repo, is the worst one:
   - It is hot: every bead write rebases and pushes under a lock.
   - It is public.
   - It is materialized lazily into every workspace.
   - GitHub warns at 50 MiB and blocks at 100 MiB per file, and it can't forget an
     accidentally attached secret without rewriting 18k commits of shared history.
5. **"Images optional for agents" is mostly solved by an existing split.** `show` is for
   humans and `read` is for agents. The plan should say so explicitly: `read` never
   emits graphics and always emits usable file paths. (Claude Code's Read tool and
   similar agent tools view images from a path, and they infer the type from the file
   extension. So the path the agent gets must end in `.png`, not in a bare hash.)
6. **Two attachment concepts is a design smell.** `sase artifact create --bead` already
   "attaches" a file to a bead. It is agent-only, local to one machine, not shown in
   notes, and doesn't sync. Adding bead attachments without folding that in leaves users
   with two meanings of "attached".
7. **Privacy is missing.** Screenshots and logs leak tokens, emails, and paths. With a
   public beads repo, "attach" means "publish to the internet" unless the attachment store
   has its own, private visibility. The command output should always say where the bytes
   went.
8. **Missing requirements:** purging (removing an accidentally published secret), size
   policy, offline behavior, what happens to attachments when a note is edited or
   removed, dedup, cross-machine availability, and whether descriptions and `+1` evidence
   can carry attachments too.

## 4. Requirement adjustments (explicit)

| # | Original requirement | Adjusted to | Why |
| --- | --- | --- | --- |
| A1 | "`@<path>` anywhere in a note" | `@<path>` **at a word boundary**, only when the token is **path-shaped**, and **outside code spans and fences**, attaches the file. Mid-word `@` is always literal. | Drops breakage from 7.7% to 0.29% of notes (§2). Matches the existing prompt `@` rules and core `scan_artifact_refs`, so the TUI, LSP, and CLI agree. |
| A2 | "Require `@@` for a literal `@`" | `@@` is the escape **at a word boundary**. A path-shaped token that can't be resolved is a **hard error** (never silently kept as text), and the error says to use `@@` or backticks. A bare word like `@large` is literal. If a file with that name exists in cwd, the CLI warns: "write `@./large` to attach it". | Keeps the strictness the user wants, so nothing is quietly misread, without breaking SASE vocabulary. |
| A3 | Implied: `@path` whole-note form continues/extends | The whole-argument `@path` form **keeps** meaning "read the text from this file", for every flag. Text read that way is then scanned for attachments. A new `sase bead attach` covers "attach just this file". Pointing whole-argument `@path` at a binary file gets a specific error that suggests `attach`. | Leaves ~10 flags, agent skills, and docs unchanged. Separates *where the text comes from* (argument layer) from *what the text says* (content layer). |
| A4 | "Robust support for viewing images" | An image layer that only `show` uses (`--images auto\|always\|never`). It **never** appears in `read`, JSON, pages, or gates. It uses a protocol ladder with a half-block fallback that works through pagers. | Agents get file paths. Humans get pictures when the terminal can draw them. Persisted bytes stay stable. |
| A5 | "Large and arbitrary binary files" | Any byte content is allowed from day one. **Size is tiered:** ≤ 50 MiB in the default git store; larger files need a configured large store (up to 2 GiB by default); otherwise the write fails clearly or the user chooses `--local-only`. Files are never inlined, never printed raw to a terminal, and never put in the beads repo. | GitHub limits, a hot repo, and purging secrets make "unlimited in git" wrong. A seam lets large files work without making every user run a blob service. |
| A6 | (new) | Attachments live in a **separate store with its own visibility, private by default**. Every write prints the destination and its visibility. | The beads repo is public. |
| A7 | (new) | **Purging must be possible** without rewriting bead history. | Accidentally attaching a secret is inevitable. |
| A8 | (new) | Fold `sase artifact create --bead` into bead attachments, keeping the old path behind a sunset flag during migration. | One concept of "attached". |
| A9 | (new, later phase) | The grammar is field-agnostic and lives in core. Ship it on notes first (including `close --note`), then `+1` evidence, then descriptions. | A bug's screenshot really belongs in the description, but that change mutates a whole field and can wait. |

## 5. Design

### 5.1 Authoring grammar (two layers)

**Layer 1: argument source (unchanged).** An argument that is exactly `@<path>` is read
as the text. A leading `@@` escapes. This is today's `read_at_path_value`, and it applies
to every flag that supports it now.

**Layer 2: note content (new).** Every note text is scanned for attachments, whether it
was typed or read from a file. The scanner runs in sase-core, as an extension of
`scan_artifact_refs` plus the fenced-code literal zones. It walks the text left to right:

| Rule | Behavior |
| --- | --- |
| Literal zones | Inline code spans and fenced code blocks are never scanned. |
| Word boundary | `@` counts only at the start of the text, after whitespace, or after `( [ { < " '`. `me@host`, `repo@sha`, `claude@xhigh` are always literal. |
| Escape | `@@` at a boundary → one literal `@`. |
| Quoted path | `@"My Screenshot.png"` → attach (same quoting as `@file:"…"`). |
| Citation | `@<kind>:<arg>` with a registered artifact kind (`research`, `plan`, `bead`, `agent`, `file`, `stitch`, …) → kept as a citation, not an attachment. |
| Existing attachment | `@attachment:<name>` → reuses an attachment this bead already has (by name). No upload. |
| Path-shaped | The token contains `/`, starts with `~` or `.`, or ends in a file extension (a dot followed by 1–8 alphanumerics, at least one of them a letter). Trailing `.,;:!?)` is trimmed. The file **must** resolve (relative to cwd, with `~` expanded) to a readable **regular file**, or the command fails. |
| Bare word | `@large`, `@sase-44.6`, `@epic` → literal. If `./<word>` exists, the CLI warns: "kept as text; write `@./<word>` to attach". |

**What gets rejected, all before anything is written:** missing files, directories (the
hint suggests `tar czf`), FIFOs and devices, unreadable files, files over the size cap,
and denylisted sensitive paths (`~/.ssh/**`, `**/.env*`, `*.pem`, `*id_rsa*`, and similar;
overridable with `--allow-sensitive`). Every problem is reported in one batch, with a caret
under the offending token:

```text
Error: 2 attachment problems in note text — nothing was written.
  Crash right after login @./shots/login.png — see @AGENTS.md
                                                    ^^^^^^^^^^
  @AGENTS.md: file not found (relative to /home/bryan/…/sase_14).
    Write @@AGENTS.md or `@AGENTS.md` for literal text, or fix the path.
  @./dump.core: 1.8 GiB exceeds bead.attachments.max_file_bytes (50 MiB) for store 'attachments'.
    Configure bead.attachments.large_store, compress it, or pass --local-only.
```

**The new `attach` verb** (convenience; it creates one note):

```bash
sase bead attach sase-ab ./login.png /tmp/crash.log -m "Repro on fresh profile"
journalctl -u sase | sase bead attach sase-ab - -n journal.log   # stdin
sase bead note sase-ab "Before @./before.png, after @./after.png"   # inline, in prose
```

### 5.2 Stored representation

The text is stored in its **display form**. Each attachment appears in it as a canonical
token, and the note carries a manifest:

```json
{"kind":"note_appended",
 "entry":"Crash right after login @attachment:login.png — full log: @attachment:crash.log",
 "attachments":[
   {"name":"login.png","sha256":"9f2c…e1","size":188416,"media_type":"image/png",
    "image":{"width":1280,"height":720},"store":"attachments"},
   {"name":"crash.log","sha256":"41aa…07","size":2202009,"media_type":"text/plain",
    "store":"attachments"}]}
```

- **Wire changes:** `NoteAppended` and `NoteEdited` each gain an optional
  `attachments: Vec<AttachmentWire>`, and `BeadNoteWire` gains a matching optional field
  (`skip_serializing_if = Vec::is_empty`). There is **no new event operation**. Older
  clients ignore the field and show the readable `@attachment:login.png` text, which
  degrades gracefully instead of failing to read the stream.
- **Names are unique per bead.**
  - They are sanitized to `[A-Za-z0-9._-]`, and `original_name` is kept for display.
  - Same name with the same sha reuses the attachment.
  - Same name with a different sha becomes `login-2.png`, and the CLI says so.
  - Because names are bead-scoped, a later note can write `@attachment:login.png` to
    refer back to an earlier one (Jira's `!file.png!` model).
- **Identity is the sha256 of the original bytes**, no matter how a backend encodes them
  (compression, chunking). `media_type` comes from magic bytes, with the extension as a
  fallback, never the extension alone.
- **The manifest has no absolute source paths.** They leak `/home/<user>/…` into a public
  repo and mean nothing on other machines. This matches the agents-sidecar allowlist.
- **Rendering substitutes only tokens whose name is in that note's manifest.** Legacy
  notes have no manifest, so they render byte-for-byte as they do today, and the 11,902
  existing notes need **no migration**.
- **Edit and remove:**
  - `--edit` re-runs the grammar. `@attachment:<name>` keeps an existing attachment, and
    a new `@path` adds one.
  - `--remove` hides the note's attachments from the roster. Their bytes remain in
    history, like the note text does.
  - Because stored text has escapes collapsed, any "edit in `$EDITOR`" flow must call a
    core `note_source_text()` that re-escapes boundary `@`s, so that
    `parse(source(display)) == display`.

### 5.3 Storage architecture

```
            write path (objects before pointers)
 note text ──► core scan/validate ──► stream-hash + sniff ──► local CAS ──► BlobStore.put + verify ──► bead event ──► bead publish
                     (no side effects until all tokens pass)        ~/.sase/attachments        (outside bead lock)
```

**Local CAS (always present).**
- Objects: `~/.sase/attachments/objects/sha256/<xx>/<sha256>`, written atomically (temp
  file, fsync, rename).
- A **named view** hard-links `~/.sase/attachments/files/<sha256[:16]>/<name>`, so every
  path handed to a person or an agent ends in the real filename and extension.
- The local CAS is also the read cache. It lives in `~/.sase`, not in a workspace, so
  workspace eviction can't destroy it.

**The `BlobStore` seam.**
- Policy lives in core: validation, size tiers, object relpaths, and the manifest.
- I/O lives in Python adapters, loaded as entry points so plugins can add backends. This
  follows the `git_object_sharing.rs` precedent ("Python owns host-coupled Git
  subprocesses").
- Operations: `put(sha, src)`, `has(sha)`, `get(sha, dst)`, `delete(sha)` (optional),
  `describe()` (URL template, visibility).

**Default backend: `git`, a dedicated attachments repo.**
- **Repo:** `<owner>/<repo>--attachments`, **private by default**, created by
  `sase repo init` like other sidecars.
- **Clone:** a hidden, host-owned **bare partial clone** (`--filter=blob:none`) at
  `~/.sase/projects/<key>/repos/attachments`, per the accepted machine-write-lane
  decision. It is never cloned into workspaces or under the primary, and nobody browses
  it.
- **Writes use git plumbing, not a worktree:** `hash-object -w`, a temporary index, then
  `commit-tree`, and `push` with fetch/retry.
  - The layout is `objects/sha256/<xx>/<sha256>`, which reuses core
    `artifact_object_relpath` semantics.
  - Paths are content-addressed and append-only, so **concurrent writers can never
    conflict**. Adding the same file twice gives identical bytes, and different files get
    different paths.
- **Reads** go through `git cat-file blob <commit>:objects/…`, which lazily fetches
  **only that blob**. A new machine downloads commits and trees, never the whole archive.
- **Cap:** `max_file_bytes` defaults to 50 MiB, the point where GitHub starts warning,
  and can't be set above 95 MiB (GitHub blocks at 100 MiB).

**Large files: optional `large_store`.** Files above the git cap go to a second backend.
My recommended single implementation is **`rclone`**:
- It is one optional external binary, the same way SASE already shells out to `git`,
  `gh`, `kitten`, `pdftoppm`, and `mpv`.
- It covers Cloudflare R2 (10 GB-month free, egress free), S3/B2, Google Drive, WebDAV,
  and **SFTP to athena over the tailnet**. The athena option is private, free, and
  unlimited — the most natural fit for this user's fleet.
- It does resumable multipart uploads and checksums, and it supports `delete`, which
  makes purging possible.
- Default ceiling: 2 GiB per file (`large_max_file_bytes`).

**Backends considered:**

| Backend | Max file | Cross-machine | Purge | Hot-repo impact | Verdict |
| --- | --- | --- | --- | --- | --- |
| Blobs in the beads repo | 100 MiB (warns at 50) | ✓ | ✗ (rewrite 18k commits) | **Severe:** bloats every bead clone; uploads under the bead lock | Reject |
| **Dedicated attachments git repo, partial clone** | 50 MiB policy | ✓ | ~ (isolated append-only repo; rewrite is tolerable) | none | **Default** |
| Git LFS on GitHub | 2 GB (Free/Pro) | ✓ | **✗ — LFS objects can only be removed by deleting the repo** | none | Reject as default: 10 GiB storage and 10 GiB bandwidth quota; needs `git-lfs` on every machine |
| GitHub release assets | < 2 GiB, 1,000 per release | ✓ | ✓ (delete asset) | none | Viable plugin. Odd semantics, and visibility follows the repo |
| `rclone` → R2/S3/SFTP(athena) | ~unbounded | ✓ | ✓ | none | **Recommended large tier** |
| Local only (`~/.sase`) | disk | ✗ | ✓ | none | Only with explicit `--local-only`; rendered as "⚠ only on athena" |
| Fixed-size chunking in git | unbounded | ✓ | ✗ | repo grows without bound | Reject: it sidesteps the file limit but not repo-size guidance (< 1 GB ideal, < 5 GB strongly recommended) |

**Write ordering and failure modes.**
1. Validate every token. Any failure means no side effects.
2. Write to the local CAS.
3. `BlobStore.put` and verify (`has`), **without holding the bead lock**, showing a
   progress line for anything over 1 MiB.
4. Append the note event.
5. Run the existing bead publication verification.

What can go wrong:
- **A crash between steps 3 and 4** leaves an unreferenced blob. That's harmless, and
  `sase bead doctor --attachments` reports it.
- **The store is unreachable in step 3:** the command fails and says so. `--local-only`
  is the explicit, labeled way out. I considered a deferred-upload outbox and rejected it
  for v1: it reintroduces "a note that points at nothing on other machines", which is
  exactly the failure this feature exists to remove.
- **The bytes are never read into memory whole:** hashing streams, and so does upload.

**Purge.**
- Command: `sase bead attachment purge <id> <name> -r "<why>"`, with confirmation.
- It deletes the bytes wherever the backend allows (rclone or release: `delete`; git:
  write a tombstone, then run a documented `filter-repo` pass on the *isolated*
  attachments repo) and clears the local caches.
- It appends the sha to a store-side `tombstones` list. Renderers then show
  `📎 login.png (purged)`. **The bead event schema doesn't change.**

**Dedup.** Identical bytes are stored once per store, across beads and projects that
share the store.

### 5.4 Reading and materialization

- **Every surface resolves an attachment to a local path.** The chain is: local CAS hit →
  lazy `get` from the manifest's `store` → named-view hard link.
- **Automatic fetching is capped:**
  - `bead.attachments.auto_fetch_max_bytes` defaults to 25 MiB.
  - Anything larger renders as `not downloaded (1.8 GiB) — sase bead attachment path
    sase-ab dump.core`.
  - `--fetch` on show/read forces the download.
- **Offline:** already-cached attachments still render. Missing ones render as
  `unavailable offline`, not as an error.

### 5.5 Presentation

**`sase bead show`, rich style, kitty-capable terminal, images `auto`**
(chips use `PATH_COLOR #87AFFF`, underlined as OSC 8 `file://` hyperlinks):

```text
NOTES (3)

  #3 · 2026-09-29 06:12:40 EDT · 3m ago · bryan · 📎 2
     Crash right after login 📎login.png — full log: 📎crash.log

     📎 login.png  image/png · 1280×720 · 184 KiB
        ┌──────────────────────────────────────────┐
        │   (thumbnail, ≤ 12 rows, aspect-correct)  │
        └──────────────────────────────────────────┘
     📎 crash.log  text/plain · 2.1 MiB · 18,204 lines
        ~/.sase/attachments/files/41aa07c3e9b1d2f0/crash.log
```

**`sase bead read` (agents), and `show` with `--images never` or when piped.**
The text is identical to what `show` prints. It contains no graphics, and it always
includes a path:

```text
  #3 · 2026-09-29 06:12:40 EDT · 3m ago · bryan · 2 attachments
     Crash right after login [📎 login.png] — full log: [📎 crash.log]
     📎 login.png  image/png · 1280×720 · 184 KiB
        /home/bryan/.sase/attachments/files/9f2c1e0b77aa4c10/login.png
     📎 crash.log  text/plain · 2.1 MiB
        /home/bryan/.sase/attachments/files/41aa07c3e9b1d2f0/crash.log
```

**How the image layer decides what to draw**

- **Controls:**
  - `-i/--images {auto,always,never}` (the `-i` short flag is free on show/read).
  - Config `bead.show.images: auto`, `bead.show.image_protocol: auto` (or `kitty`,
    `iterm2`, `sixel`, `blocks`), and `bead.show.image_max_rows: 12`. These are
    permanent user choices, so they're config fields, not feature flags.
- **`auto` turns the layer on only when all of these hold:** stdout is a TTY,
  `SASE_AGENT` is unset, color is allowed, and some protocol is available. So `read`
  resolves to off in practice. `--images always` inside an agent is honored but warns.
- **Protocol ladder:** detection uses env markers first (the existing
  `_kitty_graphics_support` markers for kitty, Ghostty, and WezTerm, plus
  `TERM_PROGRAM=iTerm.app`). If none match, it sends a single bounded query of about
  100 ms (kitty `a=q`, then DA1 for sixel), and caches the answer for each terminal
  session.
  1. **kitty graphics** (kitty, Ghostty, WezTerm). Inside tmux, it uses **Unicode
     placeholders** plus `allow-passthrough`, so images scroll with the text. This reuses
     `_viewer_tmux*.py` and the existing doctor checks.
  2. **iTerm2 inline images**, OSC 1337 (iTerm2, WezTerm).
  3. **sixel** (foot, xterm, WezTerm, recent Windows Terminal, Konsole, …).
  4. **half-block truecolor**, the existing `CellImageRenderable`. It is pure SGR text, so
     it **survives the pager, tmux, ssh, and `> file`**.
  5. **none:** only the chip.
- **Pager:** when output is paged, the ladder starts at half-blocks. A later version can
  add real graphics to the in-process Textual pager through `textual-image`.
- **Non-image previews:**
  - GIFs show their first frame.
  - Video shows a poster frame if `ffmpeg` is present, and otherwise a chip.
  - PDFs show page 1 via the existing `pdftoppm` path.
  - Text shows a line count and **never the raw content**, since attachment bytes can hold
    escape sequences. `sase bead attachment cat` prints text with control characters
    stripped.
- **Type glyphs** reuse one presentation module, the way `bead_time_presentation` does,
  so the CLI, TUI, and pages agree. Proposed glyphs: `🖼` image, `🎞` video, `≡` text,
  `📕` PDF, `▤` archive, `◇` other binary. Widths are measured with `rich.cells.cell_len`.
- **Safety:** filenames are sanitized for display (control characters and bidi overrides
  removed).

**Other surfaces**

- **`--format json`:** `issue.notes[].attachments[]`. It includes `local_path` only if the
  file is already cached. It never includes relative ages or image escapes, following the
  live-vs-persisted rule.
- **ACE TUI Beads pane:**
  - An *Attachments* block in the note detail, with half-block thumbnails.
  - New key `beads_open_attachments: "a"` (free in the Beads sub-tab) opens the existing
    kitty artifact viewer on the bead's attachments, with n/p to move between them.
    Update `src/sase/default_config.yml` per the keymap gotcha.
  - The Add-Note modal (`N`) reuses the existing `@` file-completion widgets. Dropping a
    file onto the terminal pastes its path, so `@` plus drag-and-drop just works.
- **Bead pages:** render `![login.png](<attachments-url>)` when the attachments store is
  public, and `🔒 login.png (private attachment)` otherwise. Pages stay byte-stable (no
  local paths).
- **Notifications (later):** TaskTriage and other bead-bearing gates add image
  attachments to `Notification.files`, so the Telegram plugin can deliver them as photos
  with no new contract.

### 5.6 CLI surface

Kept alphabetical, with a short alias for every long option, per `cli_rules.md`:

```text
sase bead attach <id> <file|->... [-m/--message TEXT] [-n/--name NAME] [-L/--local-only]
sase bead attachment cat   <id> <name>           # text only; control chars stripped
sase bead attachment list  <id>                  # default when bare (central list convention)
sase bead attachment open  <id> [<name>]         # kitty artifact viewer; all when name omitted
sase bead attachment path  <id> <name>           # materialize + print absolute path
sase bead attachment purge <id> <name> -r WHY    # confirmed, irreversible
sase bead note/+1/close ... [-L/--local-only] [--allow-sensitive]
sase bead show/read ... [-i/--images auto|always|never] [--fetch]
sase bead doctor --attachments                   # dangling, orphaned, tombstoned, digest-mismatch
```

Other CLI details:
- The note-text help changes from "a single-token `@<path>` is read from that file" to a
  two-line explanation of both layers.
- Shell completion should complete `@<path>` inside note arguments. The completion
  grammar already knows which values accept `@path`.
- **Write-time echo**, so the user sees what was captured and where it went:

```text
$ sase bead note ab "Crash right after login @./shots/login.png — log: @/tmp/crash.log"
  📎 login.png  image/png · 1280×720 · 184 KiB   sha256:9f2c1e…
  📎 crash.log  text/plain · 2.1 MiB             sha256:41aa07…
  ↑ 2 attachments → sase-org/sase--attachments (private) in 1.2s
Noted: sase-ab — Login crashes on fresh profile  (#3 · 📎 2)
```

### 5.7 Rust/Python boundary

This follows `rust_core_backend_boundary`. A web or mobile front end would need to match
the scanner, manifest, names, and size policy, so those belong in core.

- **sase-core:**
  - The content-grammar scanner. It extends `scan_artifact_refs` and uses the
    `fenced_code` literal zones.
  - `note_source_text()` re-escaping.
  - Name sanitization and uniquing.
  - `AttachmentWire` and the optional fields on `NoteAppended`, `NoteEdited`, and
    `BeadNoteWire`, plus the reducer that maintains the bead's attachment roster.
  - Size-tier policy, object relpaths, the tombstone format, and JSON wire.
  - Afterward, move sase's `sase-core-revision.txt` pin forward.
- **Python:**
  - Streaming hash and stat, and MIME sniffing (Pillow for image dimensions).
  - `BlobStore` adapters: git plumbing subprocesses and rclone.
  - The local CAS, terminal capability detection and rendering, the CLI, and the TUI.

## 6. Alternatives I considered and rejected

- **Transclusion** (`@path` anywhere splices in the file's text). It has no meaning for
  binaries, it bloats notes, it loses provenance, and it is already covered by the
  whole-argument form.
- **Markdown image syntax** (`![](path)`) as the authoring syntax. It's familiar, but it
  goes against the user's `@` request and SASE's `@` vocabulary (prompts, Claude Code,
  artifact refs). Bead *pages* still render it as Markdown.
- **Obsidian `![[name]]`** as the stored token. SASE memory uses it, but `@attachment:`
  fits artifact-ref citations and a future prompt kind, `@attachment:<bead>/<name>`, that
  launches agents with the bead's evidence.
- **Storing the manifest in a side table keyed by text offsets.** Offsets are fragile
  under edits, and old clients would show the raw path instead of a readable name.
- **A new `attachment_added` event operation.** A machine still on an older SASE
  (apollo, mac) would hard-fail reading that bead's stream.
- **Reusing `~/.sase/artifacts` as the store.** It is local to one machine, and its
  lifecycle is about retention and pruning, not durable evidence. Keep it as a sibling;
  unify the *concept* through A8.

## 7. Rollout

The whole feature sits behind a `beta` feature flag, `bead_note_attachments`, created
with `sase flag new`. It is removed when the epic lands. Both flag states get tests.

1. **P0, core:** grammar scanner and wire fields, reducer, `note_source_text`, and a
   golden corpus test that replays the §2 simulation against a fixture. This protects the
   0.29% number from regressions.
2. **P1, useful end to end:** local CAS, git backend, `attachments` sidecar
   init/materialization, `note`, `attach`, `attachment list/path/cat`, text rendering in
   show/read/JSON, write-time echo, `bead doctor --attachments`, `sase doctor` store
   reachability. Update the docs (`docs/beads.md` Notes and CLI sections), the
   `sase_beads.md` memory, and the note-related skills (through `/sase_memory_write` and
   the generated-skills flow).
3. **P2, beautiful and large:** the image ladder in `show`, `attachment open`, the TUI
   Beads pane and keymap, and the `rclone` large store. The user explicitly asked for
   large files, so this ships with the images rather than waiting. Also here: fold
   `artifact create --bead` into bead attachments behind a `sunset` flag.
4. **P3:** purge and tombstones, bead-page embeds, gate and Telegram delivery, `+1`
   evidence attachments, then descriptions, then the `@attachment:` prompt kind.

**Rollout note:** upgrade every machine before P1 writes land. An old client that
regenerates `issues.jsonl` will drop the attachment fields from that *projection* (the
canonical event stream is unaffected). The next write from a new client restores them,
so a mixed fleet would flip-flop the projection.

## 8. Open questions for the user

1. Should the attachments store default to **private** even though beads and pages are
   public? I recommend yes, which means bead pages show a 🔒 label instead of the image.
2. For the large tier: **SFTP on athena** (free, private, needs the tailnet) or
   **Cloudflare R2** (reachable from anywhere, free up to 10 GB-month)? rclone supports
   both, so this is only a question of the default.
3. Are the caps right: 50 MiB for git, 2 GiB for large files, 25 MiB for automatic
   fetching?
4. Should attachments reach **descriptions** in this epic, or later (P3 as proposed)?
5. Do you accept keeping the whole-argument `@path` = "read text" meaning (A3)? The
   alternative is a sunset migration to a `-F/--file` flag, after which `@path` would
   mean "attach" everywhere. That's more uniform, but it affects ~10 flags and every
   agent skill that uses `@path`.

## 9. Recommended solution

Build **bead attachments** as immutable, content-addressed snapshots, taken when the note
is written and kept outside the bead store:

1. **Grammar (core).** Inside note text, `@<path>` attaches a file when it sits at a word
   boundary, is path-shaped, and is outside code. `@@` escapes, `@kind:arg` stays a
   citation, `@attachment:<name>` reuses an existing attachment, and bare words stay
   literal. A path that doesn't resolve fails the whole command before anything is
   written, with a pointed fix. The whole-argument `@path` keeps meaning "read the text
   from this file". `sase bead attach` attaches files without prose.
2. **Wire.** Add an optional `attachments` manifest (name, sha256, size, media type,
   image dimensions, store) to `NoteAppended`, `NoteEdited`, and `BeadNoteWire`. The
   stored text holds readable `@attachment:<name>` tokens. There is no new event
   operation and no migration.
3. **Storage.** A local CAS in `~/.sase/attachments`, with a named view that keeps file
   extensions. Behind a `BlobStore` seam:
   - Default: a **private `--attachments` git repo** as a hidden, host-owned, bare
     partial clone. Append-only, never conflicts, 50 MiB cap.
   - Large: an **`rclone` backend** (R2/S3/SFTP to athena) for files up to 2 GiB.
   - `--local-only` as an explicit, labeled escape hatch.
   - Bytes are uploaded and verified before the note event is written, never under the
     bead lock. Purging works through tombstones.
4. **Viewing.** `read` prints paths for agents and never draws images. `show` adds an
   `--images auto` layer: kitty (tmux-safe Unicode placeholders) → iTerm2 → sixel →
   half-block → none. It includes OSC 8 file links, type glyphs, and dimensions and
   sizes, and it never dumps raw bytes to the terminal. `sase bead attachment open` and
   the TUI's `a` key reuse the existing kitty artifact viewer.
5. **Housekeeping.** Destination and visibility are printed on every write, and sensitive
   paths are refused by default. `bead doctor --attachments` finds problems.
   `sase artifact create --bead` is folded into this feature. Descriptions and `+1`
   evidence adopt the same core grammar in a later phase.

This keeps what the user asked for — `@path` anywhere, `@@` escapes, optional image
viewing, and binaries of any size — while avoiding the traps the corpus exposes: breaking
7.7% of notes, citing dead paths, bloating a public and heavily written repo, and having
no way to take back a leaked secret.

---

## Sources

- GitHub, [About large files on GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github): warns at 50 MiB, blocks at 100 MiB, repos ideally < 1 GB and strongly recommended < 5 GB.
- GitHub, [About Git Large File Storage](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage): LFS max file size 2 GB on Free/Pro, 4 GB on Team, 5 GB on Enterprise Cloud.
- GitHub, [Git LFS billing](https://docs.github.com/en/billing/concepts/product-billing/git-lfs): 10 GiB storage and 10 GiB bandwidth free on personal plans, metered after that.
- GitHub, [Removing files from Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/removing-files-from-git-large-file-storage): LFS objects can only be removed by deleting and recreating the repo.
- GitHub, [About releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases): each asset < 2 GiB, 1,000 assets per release, no total-size or bandwidth limit.
- GitHub, [Attaching files](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files): issue attachment limits (10 MB images, 10/100 MB video, 25 MB other files).
- Git, [partial-clone documentation](https://git-scm.com/docs/partial-clone), and the GitHub Blog, [Get up to speed with partial clone and shallow clone](https://github.blog/open-source/git/get-up-to-speed-with-partial-clone-and-shallow-clone/).
- KDAB, [State of Native Big File Handling in Git](https://www.kdab.com/native-big-file-handling-in-git/).
- Kitty, [Terminal graphics protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/): `a=q` detection query, Unicode placeholders for tmux, and `t=f`/`t=d` transmission.
- [Chafa](https://hpjansson.org/chafa/): kitty, iTerm2, sixel, and symbol output, with Python bindings.
- Cloudflare, [R2 pricing](https://developers.cloudflare.com/r2/pricing/): 10 GB-month free, free egress.
- git-bug, [issue #10: media embedding](https://github.com/git-bug/git-bug/issues/10): blobs in git referenced by hash from operations, and Markdown reference style.
- Internal: `src/sase/cli_file_values.py`, `src/sase/bead/cli_crud_evidence.py`, `src/sase/artifact_cli/create.py`, `src/sase/ace/tui/graphics/*`, `src/sase/doctor/checks_deep_terminal.py`, `docs/beads.md`, `docs/agents_sidecar.md`, `docs/artifact_references.md`, and sase-core `bead/events/wire.rs`, `artifact_ref/scanner.rs`, `artifact_object_store.rs`, `git_object_sharing.rs`; decisions `machine-link-writes-off-primary`, `corpus-before-mechanism`, and `rust-core-required`; the corpus analysis over `sase bead list -s all -n 0 -f json` (6,575 beads, 11,902 notes, run 2026-09-29).
