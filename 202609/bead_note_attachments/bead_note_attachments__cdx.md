# Bead file attachments: syntax, storage, and terminal presentation

**Researcher:** cdx  
**Date:** 2026-09-29  
**Scope:** Independent design research for first-class file attachments on bead notes.

## Executive summary

This is a good feature, but the premise needs one correction: SASE does not currently
attach the file named by a whole-note `@<path>` value. It opens that file as UTF-8 and
stores its **contents as note text**. Binary input fails, the source path is not retained,
and no durable artifact reference is created. The relevant code is
`src/sase/cli_file_values.py:read_at_path_value`; `handle_bead_note` invokes it only when
the note text is exactly one argv token. A multi-token note such as
`"See @./screenshot.png"` is currently stored literally.

The best design is therefore not “make the text-file macro accept binaries.” It is to
give notes structured attachment descriptors whose bytes live in SASE's artifact store.
The bead event stream should contain only small metadata and durable `file:` references;
it should never contain base64 or arbitrary binary bytes. The underlying object store
should be content-addressed by SHA-256, streamed, atomic, and deduplicated. This matches
both SASE's emerging digest-addressed artifact architecture and the widely used
descriptor pattern of `{mediaType, digest, size}`. OCI explicitly recommends such
descriptors for securely referencing external content and verifying it before use
([OCI descriptor specification](https://specs.opencontainers.org/image-spec/descriptor/?v=v1.1.1)).

For presentation, every `show`/`read` format should expose a useful attachment card or
structured JSON record. Image decoding should remain opt-in. In the interactive pager,
an attachment should be selectable and open through the existing artifact viewer; an
explicit preview mode may add thumbnails. Raw stdout should never emit image-control
sequences by default.

The feature should land with a migration away from the overloaded whole-token syntax:

- `-F/--from-file PATH` should become the unambiguous way to load note prose from a
  file.
- `@path` within note prose should mean “snapshot and attach this regular file.”
- `@{path with spaces}` should be the canonical complex-path form.
- `-a/--attach PATH` should provide a reliable, repeatable automation path and support
  an attachment-only note.
- `@@` should produce a literal `@` where a reference could otherwise begin.

I would not permanently preserve the rule that an exact `@path` means “read text” while
the same token embedded in a sentence means “attach bytes.” That context-dependent
meaning would be surprising forever. Preserve it only during a warned transition.

## What exists today

### Bead notes

The current bead note model is intentionally small. `BeadNote` / `BeadNoteWire` contain
an event id, timestamp, author, text, and optional edit provenance. Notes are serialized
into the bead event stream and projected to `issues.jsonl`. Human rendering treats the
body as prose; JSON output includes structured note records plus the legacy flattened
`notes_text` projection.

The current CLI behavior is:

1. `sase bead note ID @/tmp/note.md` reads `/tmp/note.md` as UTF-8 and stores the bytes
   as note text.
2. `sase bead note ID @@literal` stores `@literal`.
3. `sase bead note ID 'See @/tmp/note.md'` stores the token literally because it is not
   the only argv token.
4. A missing, directory, unreadable, or non-UTF-8 whole-token source fails before the
   bead mutation.

This is command-line file indirection, not attachment support. The distinction matters:
trying to extend `read_at_path_value()` would still erase the attachment's identity and
cannot represent arbitrary binary data.

### Artifact storage and viewing

SASE already has most of the adjacent machinery:

- `sase artifact create` creates immutable explicit snapshots and returns a durable
  `file:explicit:<id>` reference. It can associate that reference with a bead.
- Artifact records already carry `sha256`, `size_bytes`, `mime_type`, label, and source
  provenance.
- `sase artifact path/open/show` resolve and view file artifacts.
- The terminal artifact viewer handles image, video, PDF, Markdown, and text modes. The
  TUI also has a Pillow-backed cell renderer with a text fallback.
- Prompt artifact staging already copies and hashes an `@file:<path>` stream in chunks,
  and the agents sidecar already uses extensionless
  `files/objects/sha256/<prefix>/<digest>` object paths.
- Artifact lifecycle tooling already has stats, verification, protection, reclaim,
  restorable trash, and explicit-snapshot retention concepts.

There are also material gaps:

- Explicit artifact files are stored under an agent-run directory, so identical bytes
  created by different runs are not globally deduplicated.
- The explicit store first hashes and then copies, causing two full source reads.
- `sase artifact create` is agent-gated and requires `SASE_ARTIFACTS_DIR`, while humans
  may add bead notes outside any agent run.
- A `--bead` association is bead-wide and uses a generic `related` artifact link. It
  does not identify which note and which inline occurrence introduced the attachment.
- Image type selection is largely extension-driven in existing viewer paths.
- Launch-time prompt staging deliberately skips copied bytes above 100 MiB. That policy
  is reasonable for automatic prompt capture, but it must not become the ceiling for an
  explicit bead attachment.

The right implementation should reuse the artifact resolver, viewer, integrity fields,
and lifecycle tooling while replacing the per-agent physical-copy layout with a shared
content-addressed byte layer.

## Critique of the requested plan

### What is strong

The request correctly treats prose and evidence as one workflow. Screenshots, traces,
core dumps, packet captures, and generated reports are often the most useful evidence
on a task. Making them discoverable from the note that explains them is materially
better than a detached file list or a path that dies with a workspace.

The request also correctly insists on optional image support. A terminal capability is
not a property of the file alone: it depends on the emulator, multiplexer, remote
transport, pager, and output destination. Kitty defines a queryable graphics protocol
and Unicode-placeholder placement intended to cooperate with host applications and
multiplexers ([Kitty graphics protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/)),
while iTerm2 documents a different inline-image protocol and also supports Kitty's
protocol ([iTerm2 images](https://iterm2.com/documentation-images.html)). There is no
sound basis for unconditional image escape sequences in ordinary CLI output.

Finally, requiring arbitrary binaries is the forcing function that prevents a bad
“just inline the file” design. It pushes identity, integrity, lifecycle, and retrieval
into the artifact layer, where they belong.

### What should change

#### 1. Do not conflate CLI text indirection with attachment syntax

The current exact-token behavior consumes a UTF-8 file to form the note body. The new
behavior snapshots a file and leaves a reference in the note. These are different user
intents and deserve different syntax. Keeping an exact `@path` as text indirection
forever, while an embedded `@path` is an attachment, would create a permanent trap:
adding two words to a command would change what gets stored.

**Adjustment:** add `-F/--from-file PATH` (and optionally stdin via `--from-file -`) for
prose. Make inline `@path` consistently mean attachment after a deprecation window.

#### 2. Do not require `@@` for every at-sign in all contexts

Requiring `alice@@example.com` and `@@alice` everywhere would make ordinary notes
unpleasant. The scanner should recognize a reference only at a lexical boundary and
only when what follows has a valid reference shape. An email's interior `@` is not at a
boundary and remains literal. A literal reference-shaped token such as `@./example.png`
must be written `@@./example.png`.

**Adjustment:** `@@` is mandatory only where a single `@` would start a valid path or
artifact reference. This keeps parsing deterministic without taxing normal prose.
Attachment recognition should also be disabled inside fenced/indented code blocks and
inline code spans, where path-looking examples must remain literal. That follows
Markdown's broader rule that code spans bind more tightly than ordinary inline syntax
([CommonMark specification](https://spec.commonmark.org/0.31.2/)).

#### 3. “Large” cannot mean “silently copy without policy”

An explicit attachment should have no small hard limit, but a 200 GiB typo can exhaust a
host. Large-file support needs progress, free-space checks, cancellation, configurable
soft confirmation thresholds, quotas, resumable remote transfer, and clear retention.
That is support, not rejection.

**Adjustment:** allow any regular file representable by the platform's `u64` size, but
require confirmation above a configurable soft threshold in an interactive shell and a
noninteractive opt-in such as `-L/--allow-large`. No limit should be borrowed from the
automatic prompt-capture policy.

#### 4. A local source path is not an attachment identity

Paths change, workspaces disappear, and absolute paths disclose machine-specific
information. A path is input to the snapshot operation, not durable bead state.

**Adjustment:** replace the authored path with a durable artifact ref at mutation time.
Store only a sanitized display name in the bead. Keep the original absolute path, if it
is useful for local audit, in machine-local artifact provenance rather than the synced
bead event.

## Proposed user experience

### Authoring grammar

The final grammar should be small and shared by CLI, TUI, editors, and future web
clients:

```text
sase bead note sase-a1 'See @./failure.png and @./trace.bin'
sase bead note sase-a1 'See @{./screenshots/failure at 09-20.png}'
sase bead note sase-a1 'The literal token is @@./failure.png'
sase bead note sase-a1 -F ./diagnosis.md
sase bead note sase-a1 'Full dump attached' -a ./core.12947
sase bead note sase-a1 -a ./evidence.tar.zst
```

Rules:

1. Parse enough Markdown structure to exclude fenced/indented code blocks, inline code
   spans, existing link destinations, and raw HTML from attachment recognition.
2. Scan artifact refs such as `@file:explicit:...` before path refs, matching SASE's
   existing prompt preprocessing precedence.
3. `@@` is an escaped literal at-sign and is decoded after reference scanning.
4. `@{...}` is the canonical path form when whitespace or punctuation occurs in the
   path. Backslash-escaping should not be invented; braces plus normal shell quoting are
   easier to reason about.
5. Bare `@path` remains convenient for simple paths and ends at a documented delimiter.
6. A path is resolved relative to the invocation CWD. References loaded through
   `--from-file` should resolve relative to that file's parent, like Markdown assets.
7. `-a/--attach` is repeatable, bypasses the inline lexer, and appends attachment chips
   after the prose. It is the preferred automation API.
8. Directories, sockets, devices, and FIFOs are refused. A symlink is dereferenced once
   and the target regular file is snapshotted.
9. Repeated references within a note are allowed. They render as repeated mentions but
   share one descriptor and one CAS object.
10. A note is valid when it has nonblank prose, at least one attachment, or both.

Malformed reference-shaped tokens should fail the mutation rather than quietly become
literal text. This turns missing-file typos into immediate errors. The error should show
the exact span and remind the user about `@@`.

### Migration from whole-token `@path`

Use a two-step transition:

1. Introduce `-F/--from-file` immediately. Continue the exact-token UTF-8 behavior for
   one release, but warn that it is deprecated and show the equivalent command.
2. At the announced compatibility boundary, make exact-token `@path` an attachment like
   every other occurrence. `--from-file` remains the prose-loading mechanism.

During the transition, `-a/--attach` and the braced form can express an attachment-only
note without ambiguity. Documentation and completions should lead with those forms
until the migration finishes.

### Display

Full human output should always show lightweight, stable metadata. For example:

```text
NOTES (1)
  #1 · 4m ago · bryan
     The crash occurs after reconnect.  [1: failure.png]

     ATTACHMENTS
       1  failure.png   image/png   1.8 MiB   sha256:8bc3…d219
          file:explicit:31a7…   v to view · y to copy ref
```

Important properties:

- The card is useful over SSH, in logs, with `NO_COLOR`, and when the object is missing.
- The original absolute source path is not printed.
- Missing, remote-only, corrupt, or unsupported-preview objects get explicit badges;
  the prose still renders.
- `--format json` emits the full structured descriptor and never embeds bytes.
- Compact bead listings should show an attachment count badge, not filenames.

The interactive pager should make attachment chips focusable. `v` opens the selected
attachment through the existing artifact viewer, `y` copies the ref, and `p`/`P` moves
between attachments. This is more reliable and more discoverable than printing a raw
command hint alone.

### Optional images

Add one shared option (with the project's required short alias) to `show` and audited
`read`:

```text
-I/--images never|auto|inline
```

Recommended defaults:

- `sase bead show`: `never` initially, configurable to `auto` by humans.
- `sase bead read`: always `never` unless explicitly overridden. Agents normally want
  refs and materialized paths, not terminal pixels.
- `--format json`, non-TTY stdout, `--pager never`, and redirected output: never emit
  image controls regardless of configuration; an explicit `inline` on redirected output
  should error rather than corrupt a file or pipe.

In `auto`, the pager may show a bounded thumbnail only after capability and dependency
checks succeed. Otherwise the attachment card is the fallback. `v` remains available
in either mode. This lets SASE reuse its existing `ImageFallbackRenderable`, cell-image
renderer, and artifact viewer instead of building a second viewing stack in bead code.

Previewing is a different security boundary from storing. Arbitrary files may be
attached, but only a narrow raster allowlist should be decoded automatically. Pillow's
security guidance notes that a small compressed image may expand to gigabytes and
recommends treating decompression-bomb warnings as errors, retaining pixel limits, and
sandboxing image processing ([Pillow security guidance](https://pillow.readthedocs.io/en/stable/handbook/security.html)).
Therefore preview workers should be subprocesses with memory/CPU/time limits, strict
pixel/frame limits, and no SVG/EPS automatic rendering. A preview failure must never
make `bead show` fail.

## Durable data model

### Note wire shape

Extend the Rust-owned note wire additively:

```json
{
  "id": "01…",
  "timestamp": "2026-09-29T14:02:00Z",
  "author": "bryan",
  "text": "The crash is visible in [failure.png](file:explicit:31a7…)",
  "attachments": [
    {
      "ref": "file:explicit:31a7…",
      "name": "failure.png",
      "media_type": "image/png",
      "size_bytes": 1872031,
      "digest": "sha256:8bc3…d219"
    }
  ]
}
```

`attachments` defaults to an empty list, so old events continue to deserialize. The
descriptor intentionally mirrors OCI's minimum useful content descriptor: media type,
digest, and byte size. The `ref` identifies SASE's logical snapshot record; the digest
identifies the bytes and enables deduplication and verification. `name` is presentation
metadata and must never be used as a storage path.

The normalized `text` should replace source-path tokens with a CommonMark link whose
destination is the canonical artifact identity, for example
`[failure.png](file:explicit:31a7…)`. Stored artifact identities do not include the
authoring `@` sigil. This keeps plain projections portable, preserves inline placement,
and lets the pager resolve the destination without retaining a local path. The
structured list is still authoritative: renderers should not have to rescan prose, and
an attachment-only note can consist of one canonical link rather than a synthetic
sentence.

Old readers see a valid note body containing a durable ref. New readers render that ref
as a friendly chip using the descriptor. `notes_text` should include a stable
`[attachment: <name> · <ref>]` projection when a note has no prose, so legacy surfaces
do not make an attachment-only note disappear.

Note edit and removal events must retain historical descriptors. Editing creates the
new current attachment list; removed/replaced objects remain protected while history
can still expose them. This preserves the existing append-only evidence model.

### Relationship model

Note-scoped attachment membership belongs in the note event, not solely in the general
artifact-link graph. The graph should receive a derived `attached-to` relation (inverse
`has-attachment`) so bead-wide browsing and artifact pages work, but that projection is
repairable secondary state. A graph write failure must not produce a note that points
at absent bytes, and the generic `related` relation currently used by
`artifact create --bead` is too weak to express this feature.

### Object storage

Store bytes once under a shared CAS:

```text
~/.sase/artifacts/objects/sha256/8b/8bc3…d219
```

The exact root can be configured, but the digest path must be stable and extensionless.
Multiple logical `file:` rows—different notes, names, or agent runs—may point at the
same object. Git LFS validates this broad architecture: it keeps small pointer files in
Git and stores large object bytes separately
([Git LFS overview](https://git-lfs.com/)). SASE should use its own artifact model rather
than require Git LFS, because it already has refs, viewers, lifecycle rules, and a
digest-addressed sidecar object layout.

Do **not** put the object bytes in bead JSONL, SQLite, or normal Git objects:

- Base64 adds roughly 33% size overhead before JSON escaping.
- Every read, merge, clone, and projection pays for irrelevant bytes.
- Bead event conflicts become enormous and opaque.
- Git history retains every version even after the working copy is cleaned.
- Arbitrary multi-gigabyte files would make routine bead operations unsafe.

Do **not** store only the source path either. That is cheap but neither immutable nor
portable, and it leaks machine topology into durable state.

## Correct ingestion of large and arbitrary files

### One-pass local snapshot

The ingestion primitive should live in `sase_core` and accept an already-open regular
file where possible:

1. Open the source once and `fstat` it. Refuse non-regular files.
2. Check available space and policy before copying.
3. Stream fixed-size chunks to a mode-`0600` temp file on the same filesystem as the CAS
   while updating SHA-256 and progress counters.
4. `fsync` the temp file. Compare source identity, size, and timestamps before/after;
   fail (or retry once) if it changed during capture.
5. Derive the digest path. Under a per-digest lock, verify an existing object's size or
   atomically install the temp object and `fsync` the parent directory.
6. Append/fsync the artifact metadata row.
7. Only then append the bead event. If event creation fails, the unreferenced object is
   a harmless orphan eligible for grace-period collection. The reverse ordering could
   leave a durable dangling attachment and is unacceptable.

This is O(file size) time, O(chunk size) memory, and one full source read. The current
explicit-artifact path is O(file size) memory-safe but performs a hash pass and a copy
pass; prompt `@file:` capture already demonstrates the desired hash-while-copy loop.

If bytes already exist at the digest, discard the temp file and reuse the object. If the
candidate is exactly reproducible from a durable, pushed VCS revision, SASE may reuse
the existing byte-free VCS-backed artifact mechanism instead of copying. The descriptor
still records digest and size.

### Type handling

Attachment acceptance must be content-agnostic. MIME is descriptive metadata, never an
admission control for storage. Determine it best-effort from content magic plus filename
and fall back to `application/octet-stream`; the freedesktop shared-MIME specification
likewise combines glob matching and magic, with octet-stream as the binary fallback
([Shared MIME-info specification](https://specifications.freedesktop.org/shared-mime-info/latest-single/)).

Storage must never decode, decompress, execute, index, or normalize the attachment.
Preserve the exact bytes. Parsing happens only in an explicit viewer with a restricted
type allowlist.

### Remote durability and portability

Local CAS support is sufficient to replace fragile paths on one host, but synced beads
need a way to fetch objects elsewhere. Define a byte-store interface from the start:

```text
has(digest, size) -> bool
put_stream(stream, descriptor) -> locator
open_stream(descriptor) -> stream
materialize(descriptor) -> local_path
verify(descriptor) -> result
```

Ship the local filesystem implementation first. Add an optional durable remote backend
(S3-compatible storage or an OCI/distribution registry) without changing bead wire
data. Remote location and credentials belong in local/project configuration, not in
the note.

Large remote writes must be resumable, checksummed, and deduplicated. The CNCF
Distribution API provides useful precedent: it supports digest existence checks,
deduplicated blobs, chunked/resumable uploads, range-based resumption, and final digest
validation ([Distribution HTTP API V2](https://distribution.github.io/distribution/spec/api/)).
S3 multipart upload similarly supports per-part or whole-object checksums
([AWS multipart upload](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)).

When a remote backend is configured as required, do not commit the bead event until the
remote upload has completed and verified. When only local storage is configured, render
a `LOCAL` availability badge so cross-machine limitations are honest rather than
silent. A later replication command can upload all pinned local objects and clear that
badge without changing the note.

### Quotas, retention, and recovery

Large-file support requires explicit economics:

- Attachment objects are pinned while referenced by current or historical bead events.
- CAS deduplication is by full digest, not filename or truncated prefix.
- `sase artifact stats` reports logical bytes, physical bytes, dedupe savings, local-only
  bytes, and remote bytes.
- Soft attach thresholds prompt; store quotas refuse before copying unless explicitly
  overridden.
- Orphans and unreferenced objects go through the existing preview → restorable trash →
  purge lifecycle. No automatic hard delete.
- `sase artifact doctor --verify` checks size and digest and identifies missing pinned
  objects. Opens from untrusted/remote storage verify size and digest before decoding.
- Interrupted uploads and local temps are resumable or removable after a grace period.

## Reliability and security details

- **TOCTOU:** open once; hash the bytes actually copied; compare source metadata after
  the stream. Never hash by path and later copy a potentially different file.
- **Atomicity:** object first, metadata second, bead event third. Make every step
  idempotent and make graph projection replayable.
- **Concurrency:** lock by digest, not globally. Concurrent attaches of identical bytes
  should converge on one object.
- **Integrity:** use a full `sha256:<64 lowercase hex>` descriptor. Verify size before
  expensive processing and digest before trusting downloaded bytes, as OCI recommends.
- **Filename safety:** keep only a Unicode display label, bounded in length and escaped
  for Rich/ANSI/Markdown/JSON. Never join it into a storage path and never pass it
  through a shell. Treat MIME and extensions as hints rather than trust boundaries and
  keep stored objects outside any executable or web-served tree, consistent with the
  [OWASP file-upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
- **Permissions:** local objects and temps should be private by default. Remote access
  should use authenticated fetches or short-lived tokens, never durable public URLs in
  bead text.
- **No implicit execution:** `open` chooses a viewer through argv arrays. Unknown binary
  types get path/ref/copy actions, not an executed “default handler,” unless the user
  explicitly requests the OS opener.
- **Untrusted previews:** isolate image/PDF/video decoding. Bound dimensions, frame
  count, memory, CPU, and elapsed time; retain a metadata-only fallback.
- **Content leakage:** a plain content digest reveals equality across attachments. This
  is normal for a CAS but should be documented. Projects needing stronger isolation can
  use a separate encrypted backend namespace.
- **Availability:** a missing object must degrade to a clear card and nonzero result for
  explicit `attachment path/open`; it must not erase or hide the note.

## Alternatives considered

| Approach | Advantages | Problems | Verdict |
| --- | --- | --- | --- |
| Inline/base64 bytes in bead events | One apparent transaction; no second store | 33%+ overhead, huge Git/events, poor merges, high memory, no dedupe | Reject |
| Copy raw files into the bead Git repo | Portable with ordinary Git | Repository bloat and permanent history; slow clones; bad for multi-GB binaries | Reject |
| Keep only source paths | Almost free | Mutable, missing after cleanup, leaks paths, not portable | Reject |
| Require Git LFS | Mature pointer/remote model | New mandatory service/tooling; not all repos/remotes support it; duplicates SASE artifact APIs | Optional backend at most |
| One ZIP/archive per bead | Few objects | Rewrites whole archive, hides individual identity, poor random access, archive-bomb risk | Reject |
| SASE artifact refs + shared CAS | Small bead events, exact snapshots, dedupe, viewers/lifecycle already exist | Requires coordinated artifact-store refactor and remote-backend story | Recommend |

## Implementation outline

### Phase 1: core attachment and CAS primitives

- In `sase_core`, add the attachment descriptor wire, strict validation, note projection,
  and shared inline-reference lexer.
- Add a Rust streaming CAS ingest/materialize/verify API and PyO3 bindings.
- Move explicit artifact byte placement onto the shared digest-addressed store while
  keeping existing `file:explicit:<id>` refs valid.
- Allow artifact snapshots owned by a bead/note operation, not only by an agent run.
- Test huge sparse files without allocating huge fixtures, non-UTF-8 contents,
  concurrent identical writes, source mutation, disk-full cleanup, and crash boundaries.

### Phase 2: bead schema and mutation

- Add `attachments` with a default empty list to `BeadNoteWire` and Python mirrors.
- Extend append/edit reducers and JSON/event projections; preserve historical refs on
  edit/remove.
- Implement “stage all attachments, then one note event” as a single public operation.
  If any source fails, mutate nothing.
- Derive `attached-to` graph links and add doctor repair/checks.
- Ratchet `sase-core-revision.txt` past the core commit before Python callers land.

### Phase 3: CLI and migration

- Add `-F/--from-file`, repeatable `-a/--attach`, inline path parsing, `@@`, and complex
  braced paths.
- Keep the exact-token text macro for one warned transition and then remove it.
- Ensure the Rust bead fast path either implements attachments or deliberately routes
  these calls through the full path; never let the two paths disagree.
- Add shell completion and precise diagnostics.

### Phase 4: presentation and access

- Render attachment cards and counts in full/compact/plain/rich/JSON outputs.
- Add note-aware attachment navigation to the pager and reuse `artifact open/path`.
- Add `sase bead attachment list|path|open|verify` convenience commands only if user
  testing shows that copying the displayed `file:` ref is too cumbersome. The canonical
  implementation should remain artifact-based.
- Add opt-in bounded image thumbnails and preserve text fallbacks in every mode.

### Phase 5: remote store and operations

- Add optional S3/OCI-compatible remote CAS with existence checks and resumable uploads.
- Add replication status, offline/local badges, quota reporting, and repair workflows.
- Measure ingest throughput, duplicate attach latency, `bead show` latency, and index
  growth with 1 KiB, 100 MiB, multi-GiB, and highly duplicated fixtures.

## Acceptance criteria

The feature is ready when all of the following are true:

1. A note may contain prose plus multiple inline attachments in any position, including
   repeated mentions and paths with spaces.
2. `@@` escaping and malformed-token diagnostics are deterministic across CLI, TUI, and
   core tests.
3. Text-file input is explicit and cannot be confused with attachment creation.
4. Any regular file, including NUL-filled and non-UTF-8 multi-gigabyte data, is ingested
   in bounded memory and preserved byte-for-byte.
5. Identical bytes occupy one CAS object while distinct logical attachments retain their
   own labels and note provenance.
6. A failed attachment in a multi-file note leaves no bead mutation; a failed bead event
   leaves at most a reclaimable unreferenced object.
7. Plain and JSON outputs are stable and useful without an image-capable terminal.
8. No image bytes or escape sequences are emitted by default, especially from audited
   `bead read`, redirected output, or agent runs.
9. Explicit preview gracefully falls back when the protocol, dependency, file, or
   decoder is unavailable.
10. Doctor detects missing/corrupt pinned objects, and lifecycle tools never prune a
    current or historical note attachment.
11. A source path can disappear immediately after a successful note command without
    harming the attachment.
12. Synced metadata clearly distinguishes locally available, remote available,
    VCS-backed, and missing bytes.

## Recommended solution

Implement bead attachments as **structured note-scoped `file:` artifact references
backed by a shared, streaming, SHA-256 content-addressed store**. Keep only descriptors
(`ref`, safe name, media type, size, digest) in bead events; never store file bytes or
absolute source paths there. Ingest regular files atomically in one pass, deduplicate
globally, verify on retrieval, and pin objects for as long as current or historical bead
events reference them. Define a storage backend interface now, ship the local CAS first,
and add resumable remote replication for cross-machine durability.

Adopt inline `@path` and `@{path with spaces}` attachment syntax, with `@@` escaping at
reference-shaped lexical boundaries, plus repeatable `-a/--attach` for automation.
Ignore attachment syntax in Markdown code spans/blocks. Replace the current overloaded
whole-token UTF-8 macro with explicit `-F/--from-file` after one warned compatibility
release. At note creation, normalize authored paths into Markdown links whose
destinations are canonical `file:` identities; never persist the authoring path or its
leading `@` sigil.

Always render beautiful metadata cards and structured JSON. Keep image decoding opt-in;
make attachments focusable in the interactive bead pager and open them through SASE's
existing artifact viewer, with a bounded thumbnail mode and a robust text fallback.
This approach is intuitive at the command line, reliable under crashes and workspace
cleanup, efficient for huge or duplicate binaries, honest about portability, and
consistent with SASE's existing Rust-core, artifact-reference, viewer, and lifecycle
architecture.
