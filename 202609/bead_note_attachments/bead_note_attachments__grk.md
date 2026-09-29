# Bead file attachments: research and recommended design

Author: grk (independent swarm researcher)
Date: 2026-09-29
Status: recommended solution

## Verdict

Do this. Inline `@<path>` in bead notes is the right authoring gesture, and SASE
already has most of the display and blob machinery. The plan as stated mixes three
different features and over-constrains the `@` grammar. Ship attachments as
**capture-on-write into the existing artifact-file store**, with the note keeping a
durable `file:` pointer, and treat inline terminal images as an opt-in rendering
mode on top of the pager — not as the storage model.

Do not put bytes in the bead event JSONL. Do not invent a third identity system
beside `file:` artifacts and bead `refs`. Do not require `@@` for every literal
`@`.

## What the request actually contains

The request names four things that look like one feature:

1. **CLI whole-argument `@<path>`** — today, `sase bead note <id> @notes.md` (a
   single token whose entire contents are `@<path>`) reads the file as UTF-8 and
   stores that text as the note. `@@` escapes a leading `@`. Binary files fail.
2. **In-note `@<path>` tokens** — a path reference anywhere in note prose, with
   `@@` as an escape.
3. **Optional image viewing** in `sase bead show`, off for agents and for
   terminals that cannot draw images.
4. **Large and arbitrary binary files** as first-class attachments.

(1) already exists in `src/sase/cli_file_values.py` and
`src/sase/bead/cli_crud_evidence.py`. (2)–(4) are new. Treating (1) as "we already
have attachments" is the main source of confusion: that path is a quoting
convenience for long text, not a blob store.

## Current state (what we already have)

### Notes are UTF-8 records in a git-native event log

A bead note is `BeadNoteWire { id, timestamp, author, text, edited_at?, edited_by? }`.
`note_appended` carries only `{ entry: String }`. The canonical store is append-only
JSONL under the beads sidecar (`events/streams/*.jsonl`), with `issues.jsonl` as a
projection. Notes are searched, flattened to `notes_text`, rendered on bead pages,
shown in the TUI Beads pane, and replayed by `sase bead history`.

Bytes do not belong here. A 20 MiB PNG base64'd into an event would bloat git,
break `bead search`, poison bead pages, and make every `show` expensive.

### Whole-argument `@<path>` is text inlining

```python
# src/sase/cli_file_values.py
# leading @@ → strip one @
# bare @ → stay literal
# @<path> → Path.expanduser().read_text(encoding="utf-8")
```

`handle_bead_note` applies this **only when the note is a single argv token**.
`sase bead note id @notes.md` inlines the file. `sase bead note id "see @shot.png"`
stores the string unchanged. A PNG as the whole token exits 1 with `file is not
valid UTF-8`.

That is the "only contents of the note" behavior. It is not an attachment.

### The pager already follows path-shaped `@` tokens

`sase bead show` builds a `PagerDocument` with `PagerOrigin.BEAD`.
`scan_artifact_ref_document` (Rust) already classifies:

| Authored token | `target_kind` |
| --- | --- |
| `@plan:202609/x.md` | `artifact_ref` |
| `@src/app.py:7` | `file_path` |
| `#skill/sase_plan` | `xprompt_skill` |

Following a `file_path` that is an image/video/PDF opens the existing artifact
viewer (`kitten icat` / `mpv` / `pdftoppm`). An unrecognized binary opens a
`binary_card_document` (kind, mime, path). So **display of a still-live path
already works** if you put `@src/foo.png` in a note and the file is still there.

What does not work: the file going away with the agent workspace, another
machine pulling the bead store, a bare `@fail.png` (the path grammar requires a
slash), or a binary whole-argument `@shot.png`.

### Artifact files are the blob store

`sase artifact create` copies a file into `~/.sase/artifacts/`, hashes SHA-256,
records mime/size/kind (`image` / `markdown` / `pdf` / `file`), and can
`sase bead ref add file:explicit:…`. Explicit artifacts are permanent.
Referenced files are protected from prune. Clean tracked repo files can be
stored as byte-free VCS locators (`vcs_repo` / `vcs_sha` / `vcs_relpath`) and
materialized on demand.

Limits that already exist:

- `artifacts.capture.max_file_size_bytes` = 100 MiB (hash-and-record above that)
- `artifacts.capture.pool_max_bytes` = 1 GiB
- `artifacts.capture.max_stored_per_agent` = 50 byte-copies per run

`sase artifact create` is **agent-only** (`SASE_AGENT=1`). Humans attaching a
screenshot from the shell cannot use it today.

### Prompt-archive objects are the cross-machine CAS precedent

The agents sidecar already publishes content-addressed bytes at
`files/objects/sha256/<hex-prefix>/<sha256>`, committed next to the prompt that
links them, with identical-bytes-publish-once semantics. That is the right
shape for bead-synced attachments. It is not wired to beads.

### Image rendering already has two layers

| Surface | Mechanism | Needs graphics protocol? |
| --- | --- | --- |
| TUI panel preview | Pillow → Unicode block cells | no |
| Artifact viewer / pager follow | `kitten icat`, `mpv --vo=kitty` | yes (`kitten`, Kitty/Ghostty/WezTerm) |
| Doctor | warns if `kitten` missing | n/a |

`sase bead show` is a Textual pager. Kitty graphics sequences and a Textual
screen fight each other. The pager already **suspends and launches the viewer**
for media. That is the correct full-fidelity path. Inline `icat` belongs only
in `--pager never` / plain stdout, and never in `sase bead read`.

### Structured bead `refs` already attach durable context

```bash
sase bead ref add sase-ab file:explicit:0123…
sase bead ref list sase-ab --resolve
```

Refs are ordered, deduplicated, stored without the prompt-time `@`, and allowed
to be unresolved on this machine. That is the identity plane. Notes are the
prose plane. Attachments should write both: a `file:` ref for identity and
retention, and an in-note token for placement.

## Critique of the stated plan

### The idea is good

Bug work is visual. Agents already produce screenshots, traces, and tarballs
that die with the workspace unless someone runs `sase artifact create`. GitHub
just shipped `gh issue comment --attach` for this exact agentic gap: write the
markdown with local paths, upload, rewrite to durable URLs. Fossil (the
inspiration for beads) stores a content blob plus an attachment control
artifact (A-card) pointing at a ticket. We should do the analogue.

### The plan overfits the CLI accident

"We already support `@<path>` as the only contents of the note" describes
`read_at_path_value`, which **destroys the path and stores the bytes as UTF-8
text**. Extending that to "anywhere in a note" without changing the meaning
would try to splice file contents into the middle of a sentence, and would
fail on binaries. The feature we want is the opposite: keep a pointer, snapshot
the bytes elsewhere.

### `@@` for every literal `@` is too aggressive

**Requirement adjustment.** Do not require `foo@@bar.com`, `@@bead:sase-ab`, or
`@@sase-1` to write an email, an artifact ref, or an agent mention. SASE notes
already contain `@kind:arg` citations, and the document scanner already
distinguishes those from file paths.

`@@` should escape **only a token that would otherwise parse as a file
attachment ref**. That matches today's CLI `@@` (escape a leading `@<path>`
value) and the prompt-file-ref parser (skip emails, TLDs, bare identifiers).

### Inline images in `sase bead show` must not be the default contract

**Requirement adjustment.** `sase bead show` pages through Textual. Dumping
Kitty graphics into that buffer is unreliable (tmux, SSH, redirected stdout,
`SASE_AGENT`, missing `kitten`). The beautiful path is:

- default `show`: painted, followable attachment chips + Unicode-block
  thumbnails for images (the TUI preview layer, works everywhere)
- label / Enter: existing artifact viewer (`kitten icat`)
- `--images` / `bead.show.inline_images: auto`: plain-stdout `icat` only when
  a graphics-capable TTY is detected
- `sase bead read` (agents): paths, digest, mime, size. Never image protocols.

The request already suspects agents will prefer paths. Make that the agent
contract, not a footnote.

### "Support large arbitrary binaries" is not "put them in git"

**Requirement adjustment.** Arbitrary binaries yes. Unbounded git blobs no.
GitHub's own issue attachments cap images at 10 MiB and use a separate blob
store, not the git object database. SASE has no git-lfs. A 100 MiB core dump
in the beads sidecar would make every clone and every `bead sync` worse.

The durable identity is a digest. The bytes go to a content-addressed store
with a size policy. Git holds the pointer.

### Do not grow a parallel attachment type

**Requirement adjustment.** A `BeadAttachment` that is neither a `file:`
artifact nor a bead `ref` would have to reimplement identity, retention,
doctor, pager follow, TUI open, mobile download, and prune protection. Reuse
`file:` + `refs`. Notes are where the human points at the file.

## Recommended solution: capture on write, pointer in the note

GitHub CLI's `--attach` is the right product shape, translated into SASE
vocabulary.

### Authoring

```bash
# long text note, unchanged
sase bead note sase-ab @~/drafts/repro.md

# whole-argument binary: attach, don't try to UTF-8 it
sase bead note sase-ab @~/shots/fail.png

# mixed prose: snapshot each path-shaped @token
sase bead note sase-ab "wrap breaks here @~/shots/fail.png logs @/tmp/pytest.log"

# escape a path-shaped token
sase bead note sase-ab "the token is @@~/shots/fail.png (not a file)"

# explicit, human-callable (new)
sase bead attach sase-ab ~/shots/fail.png -n "the failing frame"
```

`sase bead attach` exists because `sase artifact create` is agent-only and
because humans will drag a screenshot onto a bead without wanting to become an
agent. Internally it is the same capture pipeline.

Whole-argument `@<path>` keeps today's meaning **when the file is valid UTF-8
and at most 256 KiB**: inline as the note body. If the file is binary, empty,
or larger than that cap, treat the token as an attachment instead of erroring.
That is the one behavior change to (1), and it is what people already expect
when they write `@shot.png`.

### Grammar

Reuse the document-scan file-path grammar, with three additions.

A file-ref token is `@` plus a path that is one of:

- absolute (`/…`, `~/…`)
- explicit relative (`./…`, `../…`)
- slashy relative (`dir/file.ext`)
- **new:** a bare filename with a suffix (`fail.png`) when it names an
  existing file at write time
- **new:** quoted for spaces (`@"/tmp/my shot.png"`)

Precedence, highest first:

1. Fenced code, inline code, disabled xprompt regions — literal
2. `@@` immediately before a file-ref-shaped token — emit one `@`, do not
   capture
3. Well-formed `@<kind>:<argument>` — existing artifact ref, not a file
4. File-ref token — capture

Do not match `user@host`, `@google.com`, or `@IgnoreForDiff`. That is already
how prompt `@file` parsing and the document scanner behave.

At **write** time, a file-ref whose path does not exist is a hard error (same
as today's missing `@<path>`), unless `--allow-missing` is passed for a
deliberate dangling pointer. At **read** time, resolution uses the captured
`file:` identity, not the original live path.

### Capture pipeline (the important part)

On `note` / `note --edit` / `--note` on close·update·+1, after the note text is
assembled:

1. Scan file-ref tokens.
2. For each existing regular file:
   - If it is a **clean tracked file** in a known repo at a durable commit:
     record a VCS locator (`vcs_repo` / `vcs_sha` / `vcs_relpath` / sha256 /
     size / mime). Copy nothing. This is the existing artifact VCS-backed row.
   - Else **copy** into the explicit artifact-file store (SHA-256,
     `infer_artifact_file_kind`, mime, size, original filename as label).
3. `sase bead ref add <id> file:…` for each new identity (dedup, retention).
4. Rewrite each authored token in the stored note to the canonical
   `@file:explicit:<id>` or `@file:default:<id>` form, the way `gh --attach`
   rewrites `![alt](./shot.png)` to the uploaded URL. The artifact label keeps
   `fail.png`, so display can pretty-print the basename.
5. Refuse directories, unreadable paths, and files above
   `bead.attachments.max_bytes` (default: reuse
   `artifacts.capture.max_file_size_bytes` = 100 MiB) unless `--force`.

Identical bytes already in the index reuse the existing row (the store is
digest-aware). `--edit` may add new captures; it never deletes blobs.
`--remove` retracts the note; the `file:` ref and bytes stay. That matches
Fossil (delete is a new control artifact; the blob remains).

### Storage tiers

| Tier | When | Where bytes live | What git holds |
| --- | --- | --- | --- |
| VCS-backed | clean tracked file at a durable SHA | the repo | locator in the `file:` row |
| Local explicit | everything else, v1 | `~/.sase/artifacts/` | `file:` id + sha256 + size + mime on the bead `refs` / rewritten note token |
| Sidecar CAS | v2, files ≤ `bead.attachments.max_git_bytes` (default **2 MiB**) | beads sidecar `files/objects/sha256/<aa>/<sha256>` | the object, same layout as the agents prompt archive |
| Local-only large | 2 MiB < size ≤ 100 MiB | `~/.sase/artifacts/` only | pointer + digest; other machines see a "bytes not on this machine" card until they have the object |

v1 can ship **without** the beads-sidecar CAS. Cross-machine durability for
screenshots is the v2 increment, copied from prompt-archive publication:
append-only objects, prefix-matches-digest, quarantine anything else, commit
objects before rebase so identical blobs from another machine merge cleanly.

Do not introduce git-lfs. SASE has no lfs usage, and a 2 MiB git cap plus a
local CAS already covers screenshots, logs, and small traces.

### What is stored on the bead

v1, **no Rust wire change:**

- note `text` contains rewritten `@file:…` tokens (and remaining prose)
- bead `refs` contains the same `file:` ids
- the artifact index holds sha256, size, mime, kind, label, path or VCS locator

v1.5, additive core change when we are ready:

```rust
NoteAppended {
    entry: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    attachments: Vec<BeadNoteAttachmentWire>,
}

struct BeadNoteAttachmentWire {
    token_span: (usize, usize), // into entry, for pretty rendering
    label: String,              // fail.png
    reference: String,          // file:explicit:…
    sha256: String,
    size_bytes: u64,
    mime_type: String,
}
```

Old events deserialize with `attachments: []`. This is the Fossil A-card:
metadata on the ticket, bytes in the blob store. It is worth doing, but it is
not required to make v1 excellent. Rewritten `@file:` tokens plus `refs` are
enough for pager follow, doctor, retention, and agent paths.

### Display: make it beautiful without making it fragile

**`sase bead show` (human, default pager)**

Each attachment renders as a compact chip in the note body, not a dumped path:

```
#2  2026-09-29 14:02 EDT · 3h ago · grk
     wrap breaks on the Plans pane
     ┌──────────────────────────────────────────┐
     │ 🖼  fail.png   48.2 KiB  image/png   [a]  │
     │  ▓▓░░  unicode thumbnail, 8×4 cells      │
     └──────────────────────────────────────────┘
     raw log
     ┌──────────────────────────────────────────┐
     │ 📦  pytest.log  1.1 MiB  text/plain  [b] │
     └──────────────────────────────────────────┘
```

- `[a]` follows into the existing Kitty viewer (suspend pager, `kitten icat`)
- `[b]` follows a text file into a pager section, or a binary into the existing
  binary card (kind / mime / path / sha256 / size, `y` copies the path, `E`
  opens `$EDITOR` only for text)
- Thumbnails reuse `src/sase/ace/tui/graphics/` (Pillow, Unicode blocks). They
  work over SSH, in tmux, and in 256-color terminals. Missing Pillow or a
  decode error falls back to the chip with no thumbnail.

**`--images` / `bead.show.inline_images`**

- `never` (default for agents, and whenever stdout is not a TTY)
- `always` — plain-stdout `kitten icat` for each image, skip with a one-line
  reason if `kitten` or protocol support is missing
- `auto` — `always` only when all of: stdout TTY, `SASE_AGENT` unset, pager
  not used, `kitten` on PATH, and (`KITTY_WINDOW_ID` or `TERM=xterm-kitty` or
  `GHOSTTY_RESOURCES_DIR` or `TERM_PROGRAM` in `{WezTerm, iTerm.app, ghostty}`).
  Use `kitten icat --detect-support` as a secondary check; env-only detection
  is the fast path (this is what Codex/iris.c do).

Never emit graphics protocols into a pipe. `page_or_print` already refuses the
pager when stdout is redirected; `--images auto` must do the same.

**`sase bead read` (agents)**

Print a structured ATTACHMENTS block:

```
ATTACHMENTS (2)
  fail.png  image/png  48.2 KiB  sha256:abcd…  path: /home/bryan/.sase/artifacts/…/fail-abcd1234ef56.png  ref: file:explicit:…
  pytest.log  text/plain  1.1 MiB  sha256:…  path: …  ref: file:explicit:…
```

The note body keeps the `@file:…` tokens so an agent can `sase artifact path`
or open the path with its own Read tool. Do not inline image bytes, do not run
`icat`, do not expand text-file contents into the bead read (the agent can
read the path; expanding a 1 MiB log into every `bead read` is hostile).

Optional later: `bead.read.expand_text_attachments_under: 16KiB` for tiny
logs. Default off.

**TUI Beads pane**

Same chips + thumbnails as `show`. Enter / `a` opens the artifact viewer.
This is the surface that should feel gorgeous.

**Bead pages**

For image kinds whose bytes are in a published sidecar CAS, emit
`![fail.png](../../files/objects/sha256/ab/<sha256>)`. For local-only bytes,
emit a filename + digest + size, not a broken image. Do not embed 100 MiB
objects in hosted HTML.

**JSON**

`--format json` on `show`/`read` includes `attachments: [{label, ref, mime,
size_bytes, sha256, kind, resolved_path?}]` derived from the note's `file:`
tokens plus the artifact index. Agents that want structure should use this,
not scrape chips.

### Binary files

A file that is not image/video/pdf/markdown is `kind=file`,
`mime=application/octet-stream` (or the guessed type). Show it as a binary
card. Offer:

- copy path (`y`)
- `sase artifact path file:explicit:…` (already exists)
- `sase artifact open …` which for unknowns should `xdg-open` / `open` rather
  than trying to page bytes

Do not hexdump. Do not base64 into the note. Do not special-case zip/tar
beyond mime + size; if we later want a tar listing, that is a viewer plugin,
not a store change.

Symlinks: snapshot the target, record the source path as `source_path`. Refuse
to follow a symlink out of a configured deny-list (`.ssh`, `.gnupg`,
credential files) the way prompt `@file` refuses `..` escapes.

Secrets: refuse well-known names (`.env`, `id_rsa`, `*.pem`, `credentials.json`)
with an override `--i-mean-it`. Attachments are copied into a store that may
later be git-pushed.

### Doctor and missing bytes

`sase bead doctor` gains:

- note `@file:` token whose id is not in the artifact index
- ref without a matching note token (informational; refs can be added by hand)
- digest mismatch
- VCS locator that cannot materialize
- sidecar object whose path does not hash to its name
- local-only large object not present on this machine (warning, not error)

`sase bead attach materialize <id>` copies missing sidecar objects from a
reachable clone, or prints the digest and size so the user can fetch them.

### Config surface

```yaml
bead:
  attachments:
    max_bytes: 104857600          # refuse above this (100 MiB)
    max_git_bytes: 2097152        # v2 sidecar CAS commit cap (2 MiB)
    max_inline_text_bytes: 262144 # whole-argument UTF-8 inlining cap
    inline_images: auto           # never | auto | always  (plain show only)
  show:
    thumbnails: auto              # never | auto | always  (pager/TUI)
```

Agents never honor `inline_images: always`. `sase bead read` ignores it.

## Alternatives considered

| Approach | Why not (as the v1 design) |
| --- | --- |
| Inline file contents into the note for every `@path` | Destroys binaries; blows up search; current CLI accident, not a model |
| Path pointers only, no snapshot | Agent workspaces are ephemeral; other machines see dead paths |
| Bytes in `note_appended.entry` (base64) | Git-native JSONL is the wrong blob store |
| git-lfs in the beads sidecar | New dependency, none in tree, overkill under a 2 MiB git cap |
| New `BeadAttachment` type beside `file:` | Duplicates identity, retention, doctor, pager, TUI |
| Require `@@` for every literal `@` | Breaks emails, `@kind:` refs, agent names |
| Default Kitty `icat` in `sase bead show` | Fights the Textual pager; fails on tmux/SSH/agents |
| Markdown `![alt](path)` as the authoring syntax | SASE's existing language is `@path`; pager already scans it; keep one gesture |
| Allow-listed `@file:` roots from `sase.yml` | Fine for prompt expansion; too strict for "attach this screenshot from `/tmp`" |
| `sase artifact create` as the only door | Agent-only today; humans need `sase bead attach` |

The Fossil model (blob + A-card) and the GitHub CLI model (upload + rewrite
in place) both map onto **artifact file + rewritten `@file:` token + bead
ref**. That is the SASE-native translation.

## What I would change in the requirements (summary)

Call these out as intentional deltas from the prompt:

1. **Keep whole-argument `@<path>` as UTF-8 inlining for small text files.**
   Extend it so a binary (or oversize) whole-argument `@<path>` attaches
   instead of erroring. Mixed notes never inline file contents.
2. **`@<path>` anywhere means "attach this file", not "splice its bytes".**
3. **`@@` escapes a file-ref token only.** Emails and `@kind:` citations stay
   unescaped.
4. **Snapshot on write** into the existing artifact-file store; rewrite the
   token to `@file:…`; also `bead ref add`. Live paths are an authoring
   convenience, not the stored identity.
5. **Inline images are opt-in and pager-hostile.** Default beauty is chips +
   Unicode thumbnails + follow-to-`kitten icat`. Agents get paths.
6. **Large binaries are pointers + local/sidecar CAS**, with a 100 MiB refuse
   cap and a 2 MiB git-commit cap. No JSONL blobs, no git-lfs in v1.
7. **Add `sase bead attach`** so humans can do this without `SASE_AGENT=1`.
8. **Defer the Rust `attachments` field** until v1.5. v1 is rewrite + refs +
   artifact index.

## Implementation sketch (epic, first tale is shippable)

This is an epic. The first tale is enough to use daily.

### Tale A — capture and follow (medium)

- Shared scanner: file-ref tokens in note text, `@@` escape, quoted paths,
  bare `file.ext` at write time if the file exists.
- Whole-argument `@<path>`: UTF-8 inline if small text, else attach.
- Capture into `store_explicit_artifact_file` from a **human-callable**
  `sase bead attach` and from `sase bead note`.
- Rewrite to `@file:…`, `bead ref add`, refuse missing/oversize/secret names.
- `show`/`read`: pager already follows `file:`; add an ATTACHMENTS section and
  JSON field. Agents: paths only.
- Tests: grammar, binary whole-argument, mixed prose, `@@`, missing file
  mutates nothing, UTF-8 inlining still works, prune protection via refs.

### Phase B — beautiful show (small)

- Unicode-block thumbnails in pager note chips and the Beads pane.
- Binary cards with size/mime/sha and copy-path.
- `--images auto|always|never` for plain stdout, with env +
  `kitten icat --detect-support`.
- Screenshot goldens for the Beads pane chips.

### Phase C — sidecar CAS (medium)

- Beads sidecar `files/objects/sha256/` publication for files ≤ 2 MiB,
  copied from the prompt-archive object publisher (lock, digest-path,
  quarantine, commit-before-rebase).
- Doctor + `attach materialize`.
- Bead pages: markdown images for published objects.

### Phase D — core wire (small, after C)

- Optional `attachments` on `note_appended` / `BeadNoteWire` for precise
  spans and so a note can name files even if someone hand-edits the prose.

Dependencies: A blocks B and C. C and B can run in parallel. D needs A and a
sase-core bump.

## Risks

- **Grammar false positives.** Mitigate with the existing path-shaped scanner
  plus write-time existence check. Log every capture in the CLI output
  (`attached fail.png → file:explicit:… (48.2 KiB)`) so a mistaken match is
  obvious and `--edit` can fix the prose.
- **Dual meaning of `@<path>`.** Document it in `sase bead note -h` as two
  sentences: whole-argument small text inlines; any other `@<path>` attaches.
  Add a one-line example of each.
- **Workspace-local artifacts vs synced beads.** v1 attachments are durable on
  the writing machine and via `file:` identity; they are not automatically on
  every clone. Say so in help. Phase C closes the gap for small files.
- **Secret leakage.** Deny-list + `--i-mean-it`. Attachments that later land
  in a private agents/beads sidecar are still copies.
- **Core schema.** v1 avoids it. Do not sneak `attachments` onto the wire
  until the sase-core minor window is planned.
- **Pager vs Kitty.** Do not try to paint `icat` inside Textual. Thumbnails
  are Unicode; full images suspend into the viewer that already exists.

## Recommended solution (one paragraph)

Keep today's whole-argument `@<path>` as a small-text inlining convenience;
make every other `@<path>` in a bead note a **capture-on-write attachment**.
Snapshot the file into the existing SHA-256 artifact store (VCS locator when
the bytes already live in a known commit), rewrite the token to `@file:…`,
and `sase bead ref add` so retention, doctor, pager follow, and TUI open all
fall out of systems we already have. Add `sase bead attach` for humans.
Render notes with chips and Unicode thumbnails; open full images through the
existing `kitten icat` viewer; give agents materialized paths. Store large
binaries as digest-addressed objects with a 100 MiB refuse cap, and only
commit sub-2 MiB objects into a beads-sidecar CAS in a follow-up. Escape
with `@@` only when the token would otherwise be a file ref.

That is intuitive (`@shot.png` in the sentence where you talk about it),
reliable (the bead holds a digest, not a `/tmp` path), and beautiful (chips,
thumbnails, one-key follow) without teaching a second attachment system or
fighting the pager.
