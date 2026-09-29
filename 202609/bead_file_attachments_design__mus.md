# Bead file attachments: design research (`mus`)

Researcher: `mus` (independent swarm member; peer reports not consulted).
Date: 2026-09-29. Scope: how to add excellent `@<path>` attachment support to
bead notes: inline references anywhere in a note, `@@` escaping, optional image
viewing in `sase bead show`, and large/arbitrary binary support. Ends with a
recommended solution and explicit adjustments to the stated requirements.

## 1. What exists today (verified in tree)

### 1.1 Whole-value `@<path>` expansion only

`src/sase/cli_file_values.py` (`read_at_path_value`) is the single shared
expander. Verified behavior (`tests/test_cli_file_values.py` confirms each):

- `hello` / `""` pass through unchanged.
- `@<path>` (entire value starts with one `@`) is read as UTF-8 verbatim, with
  `~` expansion. Exact bytes kept, including trailing newline.
- `@@...` strips exactly one leading `@` (escape). `@@name` -> `@name`,
  `@@@name` -> `@@name`. Bare `@` stays literal.
- Missing path, directory, `OSError`, and non-UTF-8 bytes **raise**
  `CliFileValueError` (message includes the target flag and a "use `@@`"
  hint). There is deliberately **no** fallback to the raw token.

Call sites: bead create/update/close-note/snooze/`+1`/task-type fields route
through it (`src/sase/bead/cli_crud_{create,update,lifecycle,evidence,snooze}.py`,
`src/sase/task_types/fields.py`).

Critically, `handle_bead_note` (`src/sase/bead/cli_crud_evidence.py:119-144`)
expands **only when the note is a single argv token**:

```python
text = read_at_path_value(text[0], ...) if len(text) == 1 else " ".join(text)
```

So today `@path` works only when it is the *entire* note (matching the request's
"only contents of the note" description), and multi-word notes never touch the
filesystem. `sase bead show` renders notes as plain prose lines
(`render_bead_note_lines` in `src/sase/bead/cli_detail_sections.py`); there is
no attachment concept, no image path, no binary card.

### 1.2 The Rust boundary owns the note shape

`BeadNote` (`src/sase/bead/model.py:106-140`) mirrors `BeadNoteWire` in
sase-core: `{id, timestamp, author, text, edited_at?, edited_by?}`. The codec
(`src/sase/bead/note_codec.py`) is byte-identical to the Rust writer by design.
`src/sase/main/bead_fast_path.py:25,47-51,406-415` routes any `@`-carrying
invocation **away from the Rust fast path** to the Python handlers, with the
comment "a future Rust arm must not store the raw token." Any design that adds
fields (e.g. a structured attachment list) therefore requires a coordinated
sase-core wire/API/binding change plus moving the `sase-core-revision.txt` pin
(see `AGENTS.md` §1.3 and `docs/rust_backend.md`). Designs that stay within
`text`-only need no Rust change; designs that add `attachments: [...]` do.

### 1.3 `@` is already a crowded namespace

`@` prefixes are load-bearing elsewhere, so inline `@path` scanning cannot be a
naive substring replace:

- Artifact refs: `@stitch:<sha>`, `@file:…`, `goal:<id>` interplay
  (`src/sase/artifact_ref_prompt.py`, `src/sase/artifact_providers/`).
- Model aliases `@…`, agent tribes `@…`, agent-session suffixes, notification
  gate `@…` values, xprompt `@…` directives and file completion.
- Ordinary prose: `user@example.com`, Python decorators, SQL, Twitter handles.

The current design sidesteps all of this by expanding only when the *whole
value* starts with `@`. Inline expansion reintroduces every collision at once.

### 1.4 Image machinery already exists — but not in `bead show`

- Portable terminal image rendering exists: `CellImageRenderable`
  (`src/sase/ace/tui/graphics/cell.py`) paints Pillow-decoded rasters with
  adaptive half-block cells, truecolor with 256-color fallback, EXIF handling,
  LRU-cached, capped at **25 MiB file / 40 MPixels**. `renderable.py` adds an
  `ImageFallbackRenderable` (path, size, reason, "open with A") so failure is a
  legible card, never a traceback. Capability detection is env-based
  (`capability.py`: `COLORTERM`/`TERM` truecolor sniffing).
- Supported image extensions today: `.png .jpg .jpeg .webp .gif`
  (`graphics/images.py`). Video (`.mp4 .m4v .mov .webm`) goes through an
  mpv/kitty-placement path (`_viewer_loop_media.py`), not half-blocks.
- The agent-attachment contract (`docs/agent_images.md`,
  `src/sase/axe/image_attachments.py`) caps generated-media attachments at 10
  images + 10 PDFs; prompt-referenced media are persisted as artifact rows.
- `sase bead show` / `read` share `_run_bead_view` (`src/sase/bead/cli_query.py`)
  rendering plain/Rich text through a pager. No graphics, no Kitty protocol, no
  sixel, no external-opener hook. Note also the deliberate human/agent split:
  `show` **refuses** inside agent runs (exit 2, redirecting to audited
  `sase bead read -r "<why>"`); agents never see `show` output. This is
  directly relevant to the "agents may not want images" concern: they already
  cannot use `show` at all, and `read` is the machine surface.

### 1.5 Binary/large-file handling today: reject, don't store

`read_at_path_value` rejects non-UTF-8 with "file is not valid UTF-8". There is
no size cap in that function (a 2 GB log would be slurped into a note string,
then into `issues.jsonl`, git sync, search indexes, and wrapped prose). The
artifact subsystem, by contrast, already handles non-text gracefully:
`artifact_cli/read.py:_binary_card` renders a `kind / reference / mime_type /
path` pointer card instead of bytes. Prompt staging already uses a
content-addressed pool (`<workspace>/.sase/artifacts/pool/<sha12>-<basename>`,
per `docs/agent_images.md`), i.e. the repo already has the pattern for
keeping big bytes out of prose stores. The mobile gateway caps downloadable
attachments at 20 MiB (`_mobile_notification_attachments.py`).

## 2. Critique of the plan as stated

**Is it a good idea? Yes, with a structural correction.** File references in
notes are clearly valuable (logs, diffs, screenshots, specs attached to the
bead they evidence). But as literally specified — "expand `@path` anywhere in
the note text, bake the bytes in, `@@` for every literal `@`" — it has four
problems:

1. **`@@`-for-every-`@` is user-hostile and unnecessary.** Emails,
   decorators, and existing `@ref` prose would all need rewriting. The escape
   should be required only where a reference would actually parse, not for
   every `@` in existence. The current leading-only `@@` rule already teaches
   the wrong muscle memory for an inline world; broadening it to "all `@`s"
   makes it worse, not better.
2. **Bake-in vs. link is the load-bearing decision, and the plan picks the
   worse default for binaries.** Inlining file *bytes* into note `text` at
   write time means: the bead store (jsonl + SQLite mirror + git sync) gains a
   copy that rots when the file changes; search indexes ingest log dumps;
   `wrap_markdown` reflows them; sync payloads balloon; secrets in pasted files
   become permanent bead history; and anything non-UTF-8 fails outright (the
   current `UnicodeDecodeError` path). References (store the pointer, resolve
   at view time) avoid all of this and are what the artifact subsystem already
   does.
3. **"Robust image support in `show`" needs an opt-in, not a default.**
   Terminal graphics are capability-dependent (truecolor, Kitty/sixel, tmux
   passthrough, pager interactions). Auto-emitting half-block art or Kitty
   escape sequences into piped/pager/agent-consumed output will produce garbage
   on exactly the setups the request worries about. The existing codebase
   already solved this once (fallback cards, capability sniffing, explicit
   viewer keypress); `bead show` should reuse that posture, not invent
   auto-detect-and-spray.
4. **Agents don't need this surface at all.** Agents are refused from `show`
   and use `read` (JSON or full text) plus direct file reads. Giving them
   rendered thumbnails burns tokens to convey less information than the path
   they can already open. The agent surface should stay machine-readable paths
   and metadata.

**Would I take a different approach?** Keep the request's spirit (one obvious
`@` syntax, beautiful `show` output) but split the feature into two verbs with
different storage, which the plan conflates:

- **Include** (text, small): inline the file's text at write time. For logs,
  configs, short specs. Bounded, UTF-8, truncated with a marker.
- **Attach** (anything, any size): store a *reference*; never the bytes.
  Resolved at view time into a beautiful card / thumbnail / opener action.

One syntax can offer both (`@path` vs. a marked variant), but the storage must
differ. Everything below follows from that split.

## 3. Design space

### 3.1 Grammar for inline references

Requirements: unambiguous token boundaries, spaces in paths, no breakage of
emails/decorators/refs, composable with shell quoting.

Candidate tokens (all require the `@` to start the token, i.e. preceded by
start-of-string, whitespace, or `([{"'` — this single rule eliminates the
email/decorator problem without any escaping):

| Syntax | Meaning |
|---|---|
| `@path/to/file` | include (text) or attach by kind (see §3.2) |
| `@"path with spaces.md"` / `@'...'` | quoted path; also allows `@`, `]` etc. inside |
| `@@` | literal `@` — but **only required where a reference would otherwise parse** (i.e. `@` at a token start followed by a path char or quote). `a@b`, `@` alone, `@` mid-token stay literal with no escape. |
| `@{…}` / `@[label](path)` | rejected — do not invent a second markdown-link syntax; `@`-token plus label inference at render is enough |

Path resolution: `~` expansion, relative to invocation cwd (document it;
bead commands already resolve design paths against cwd), then absolute
display. Globs: do not expand (explicit is better; glob surprises in
append-only history are forever). `@{revision}:path` version pinning: defer.

Backward compatibility: whole-value `@path` keeps today's exact semantics
(read UTF-8 verbatim or error). Whole-value `@@…` keeps today's strip-one
rule. The only behavior change is that `@`-tokens *inside* longer notes now
parse; under the token-start rule, existing prose without such tokens is
unaffected. A `--no-expand` (or `--literal`) flag covers the paranoid case.

### 3.2 Include vs. attach: the kind rule

At write time, classify each referenced path:

- **Text under the text cap** (default e.g. 64 KiB, configurable): *include* —
  splice decoded text into the note with fenced delimiters recording the
  source (` ``` — @path (1,234 bytes, sha12:abc…) `). Truncate with an
  explicit `… [truncated: N more bytes; sase bead show --open …]` marker
  rather than erroring.
- **Images by extension** (reuse `SUPPORTED_IMAGE_EXTENSIONS`, add `.svg` as
  card-only since Pillow rasterization of SVG needs conversion): *attach* —
  store reference, never pixels.
- **Everything else** (binaries, large text, missing-at-show files, videos):
  *attach* — store reference.

Error policy at write: missing/unreadable path → hard error naming the path
(preserves today's fail-closed behavior; silent literal fallback would corrupt
evidence). Oversize text → truncation marker, not error. Binary where include
was explicitly forced (`@!path`? see below) → error suggesting attach.

Whether one sigil or two: I recommend **one default sigil with kind dispatch**
(`@path` does the right thing) plus an explicit override prefix for the rare
cases (`@!path` = force include-as-text, `@^path` or `@>path` = force
attach-as-reference). Keep the override set to exactly one extra form if
possible; two is the maximum before the syntax stops being intuitive.

### 3.3 Storage: reference, not bytes (the core recommendation)

Two options:

**Option A — text-only (no Rust change).** The stored note `text` contains the
prose plus deterministic attachment manifest blocks (fenced, machine-parseable,
rendered beautifully by `show`). References are `content-hash + original path +
size + mime`, e.g. a trailing `<!-- sase:attachments […]-->` JSON block or a
visible `Attachments:` section. Pros: ships Python-only; no wire migration;
old clients still read the prose. Cons: manifest is parse-on-render (needs a
stable grammar + tests); bytes live outside the store so GC/repair story must
be explicit.

**Option B — structured `attachments: [...]` on `BeadNote` (Rust change).**
Add an optional attachments array to `BeadNoteWire`, the Python dataclass, the
codec (omitted-when-absent like `edited_at`), search-text policy, and JSON
envelope; move the pin. Pros: queryable, typed, clean `read --format json` for
agents. Cons: cross-repo migration, old readers ignore the field, fast-path
audit.

Recommendation: **ship A first, design the manifest grammar as the wire subset
of B** (same field names/keys), so B becomes a lossless promotion later.
Concretely: the note text ends with a stable, documented, hidden-or-shown
manifest block; `show` parses it with a strict parser and ignores
unparseable blocks (render as plain text — never crash on history).

Where do the bytes live? **Do not put them in `issues.jsonl`.** Reuse the
existing content-addressed pool pattern (`pool/<sha256>-<basename>`, plus the
artifact index via `sase artifact create`-equivalent internal API) so identical
files dedupe, the store stays small, and retention/GC can follow the artifact
retention story. Small text includes are the only bytes that live in the note
itself (they already do today). This directly answers "large and arbitrary
binary": the answer is *never inline them*; store once by hash, reference from
the note, resolve lazily.

### 3.4 Rendering in `show`: beautiful, optional, degradable

`show` gains three orthogonal controls (names bikesheddable, semantics not):

- `--attach={auto,inline,off}` (default `auto`): `auto` = text includes render
  inline + images/binaries render as cards; `inline` = also render image
  thumbnails via the existing `CellImageRenderable` path; `off` = paths only.
  Plus `--no-images` shorthand and `SASE_BEAD_IMAGES={auto,inline,off}`
  override. Piped output forces card-or-path mode (never emit graphics or
  Kitty sequences into a pipe).
- Text includes: fenced block with header (`@path · 1,234 bytes · sha
  abc123…`), line-count cap with `… N lines omitted`, existing prose-wrap
  rules respected.
- Images: thumbnail (bounded rows, aspect-preserved — reuse `ImageOps.contain`
  semantics), caption with path/size/dimensions, and a hint line
  (`sase artifact open …` / `--save-to …`). Failure → the existing
  `ImageFallbackRenderable` card (reason + size + opener hint), never a stack
  trace. Non-supporting terminals get the card automatically via the
  capability sniff.
- Binaries/large: pointer card (name, mime, size, sha12, stored ref), with
  `--open` (hand to `sase artifact open` viewer dispatch) and `--save-to DIR`
  actions. Videos reuse the existing mpv/kitty path or card.
- JSON format (`show`/`read --format json`): expose `attachments: [{path,
  stored_ref, size, mime, sha256, kind}]` structured, and keep rendered prose
  out of the machine contract. Agents get paths + hashes, zero thumbnails.

Pager interaction: render thumbnails only when stdout is a TTY and pager mode
will preserve them; otherwise cards. Document that `less` needs `-R` (the
pager path already handles color intact).

### 3.5 Safety, integrity, and lifecycle

- **Fail closed at write, degrade open at read.** Write: missing/unreadable →
  error. Read/show: missing/evicted bytes → card stating so, exit 0 for the
  beads that resolved (consistent with today's per-ID failure reporting).
- **Size caps with names and numbers:** text-include cap (~64 KiB default),
  thumbnail source cap (reuse 25 MiB / 40 MP), attachment action cap (refuse to
  materialize >N MiB to stdout; require `--save-to`). All caps configurable,
  all fallbacks card-shaped.
- **No secret laundering surprises:** including a file bakes its bytes into
  permanent, git-synced bead history. `show` the byte count + sha at write
  confirmation ("Noted … + 2 attachments (14 KiB)"), and document that
  credentials don't belong in notes. Reads of beads stay audited (`read`
  records *why*; attachment opens should log through the same read-link path).
- **Sync/merge:** hashes make concurrent attaches of the same file commute;
  divergent attaches are both kept (append-only log — never last-writer-wins).
  Edits of a note (`--edit`) re-resolve references at edit time and record a
  new manifest; history of the old text is preserved by the existing edit
  trail.
- **Search:** index original prose + attachment *paths/names*, not included
  file bytes (avoids log-dump pollution) — or index bytes only under the text
  cap with a marker. Decide once, document it.
- **TUI future:** the bead detail view can reuse `image_preview()` /
  `CellImageRenderable` in-panel and the `a` artifact viewer for opens. Out of
  scope for v1, but the storage design already serves it.

## 4. Alternatives considered and rejected

- **Base64 blobs in note text:** bloats jsonl/SQLite/git, breaks search/wrap,
  unrenderable in diffs, permanent bloat. Rejected except as a transport detail
  inside the artifact pool (never in notes).
- **Git-LFS / git-annex for attachments:** heavyweight dependency, fights the
  existing pool + artifact-index story, complicates the SQLite mirror and
  cross-project reads. Rejected; reuse the pool.
- **Kitty graphics protocol as the primary image path:** higher fidelity but
  terminal-specific, pager-hostile, and a new dependency surface. Rejected as
  primary; keep half-block cells (universal) with Kitty/mpv only for the
  existing video path.
- **Auto-render images by default in all `show` output:** breaks pipes,
  agents, and dumb terminals. Rejected; `auto` = cards, `inline` = explicit.
- **Requiring `@@` for every literal `@`:** mass breakage of emails,
  decorators, existing notes. Rejected; token-start parsing + escape-only-
  where-ambiguous (see §5, adjustment 1).

## 5. Adjustments to the requirements (explicit)

1. **`@@` scope narrowed.** Require `@@` only where a reference would
   otherwise parse (`@` at token start + path char/quote). Mid-token `@`
   (`a@b`, `user@host`), lone `@`, and non-path `@refs` need no escape. This
   supersedes "require `@@` if a literal `@` is needed" as stated.
2. **Image rendering is opt-in (`--attach=inline` / env), default `auto`
   renders cards.** Supersedes any reading of "robust support" as "always
   render pixels." Robustness here means *correct degradation*, not maximum
   pixels.
3. **Agents get paths, not pictures.** No image work targets the agent surface;
   `read --format json` exposes structured attachment metadata and agents read
   files directly. This scopes the "not sure agents want this" aside into a
   decision: they don't, and the existing `show`-vs-`read` split already
   enforces it.
4. **Two storage verbs, one syntax.** `@path` dispatches by kind (small text
   included, everything else attached by reference) instead of "references
   anywhere, bytes everywhere." Large/arbitrary binaries are *never* inlined —
   that is the whole of the binary strategy.
5. **Ship text-manifest first (no Rust change), promote to wire later.**
   Avoids blocking the feature on a cross-repo migration while keeping the
   grammar forward-compatible.

## 6. Recommended solution (v1)

1. **Syntax:** `@path`, `@"path with spaces"`, token-start rule (§3.1);
   `@@` escapes only ambiguous positions; `--no-expand` fallback; whole-value
   behavior unchanged.
2. **Write path (Python handlers + `cli_file_values` successor):** scan all
   free-text note/description/reason fields; classify by kind (§3.2); small
   text spliced as fenced includes; everything else copied once into the
   content-addressed pool + artifact index, referenced by a stable manifest
   block using the future wire's field names. Missing/unreadable → error;
   oversize text → truncated-with-marker. Keep the fast-path guard (any `@`
   stays on the Python lane) until a Rust arm exists.
3. **`show` rendering:** `auto` default = inline text + cards;
   `--attach=inline` = thumbnails via `CellImageRenderable` (reuse caps,
   fallback card, capability sniff); piped = no graphics; `--open` /
   `--save-to` actions for binaries; JSON exposes `attachments[]`.
4. **Agents:** structured `attachments[]` in `read --format json`; no
   thumbnails; direct-path reads unchanged.
5. **Docs & polish:** one syntax diagram, three examples (log snippet, mockup
   PNG, 200 MB capture), cap table, escape rule in one sentence, and the
   "includes bake bytes permanently; attaches link" warning. Beauty = aligned
   cards, dim metadata lines, aspect-correct thumbnails, and graceful cards
   where pixels can't go.

## 7. Open questions for the lead

- Text-include cap value (64 KiB default proposed) and max include count per
  note.
- Manifest visibility: hidden HTML-comment block vs. visible `Attachments:`
  section (I lean visible-one-line + hidden-JSON).
- Whether `--open` should shell out to `sase artifact open` directly or print
  the command (I lean print-first for auditability, open on explicit flag).
- Wire promotion (Option B) timing relative to v1.

## 8. Sources checked (independent)

`src/sase/cli_file_values.py`, `tests/test_cli_file_values.py`,
`src/sase/bead/cli_crud_evidence.py`, `src/sase/main/bead_fast_path.py`,
`src/sase/bead/model.py`, `src/sase/bead/note_codec.py`,
`src/sase/bead/cli_detail_sections.py`, `src/sase/bead/cli_detail_render.py`,
`src/sase/bead/cli_query.py` (`show`/`read` split), `src/sase/artifact_cli/read.py`
(binary card), `src/sase/ace/tui/graphics/{cell,capability,renderable,images}.py`,
`docs/agent_images.md`, `docs/mobile_gateway.md` (20 MiB cap),
`src/sase/axe/image_attachments.py` (10-attachment cap). No peer swarm report
was located, opened, or read; no chat transcript or summary of a peer was
consulted.
