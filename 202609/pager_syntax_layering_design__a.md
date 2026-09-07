# Pager syntax highlighting without sacrificing existing styles

## Executive decision

SASE should keep the pager's current Rich `Text` model and add syntax highlighting as
one more **offset-preserving style layer**. It should not replace the body widget with a
`TextArea`, render Markdown structurally, or shell out to `bat`/`pygmentize`.

The design hinge is simple:

1. The section's original plain text remains the sole coordinate space for link spans,
   attached targets, search, trails, and copy/edit actions.
2. Pygments/Rich supplies token styles over that exact text.
3. Existing caller-authored/ANSI styles are applied over syntax styles, so they remain
   authoritative.
4. Pager link capsules and target accents are applied last, as they are today.

That ordering makes the feature additive. Raw `.py`, `.rs`, `.yaml`, `.md`, `.diff`,
and other recognized files gain highlighting. Existing rich bead output and any other
pre-styled sections keep their present appearance. A lexer failure, an ambiguous type,
a large file, or a text-normalization mismatch degrades to today's rendering rather
than changing content or failing the pager.

## What exists today

The pager already has unusually good foundations for this feature:

- `src/sase/pager/document.py` converts string bodies with `Text.from_ansi()`. Thus ANSI
  output becomes plain text plus Rich style spans, and `plain_text` is the stable source
  scanned for links.
- `src/sase/pager/_labels.py` inserts capsules by slicing and appending the section's
  `Text`. Rich slices retain spans, so existing ANSI styles survive normal link-label
  composition. The target accent is intentionally applied afterward.
- `src/sase/pager/_layout.py` renders all sections in one `Static`, preserving the
  pager's continuous-document navigation and cheap scrolling.
- File-backed routes converge on `path_section()` in `src/sase/pager/adapters.py`, while
  artifact reads, bead reads, stdin, generated cards, and ACE file viewing construct
  `PagerSection`s at explicit seams. Those seams retain enough provenance to decide
  whether a body is raw source or already-presented output.
- `src/sase/ace/tui/util/lazy_syntax.py` already establishes syntax budgets of 64 KB /
  1,500 lines, with stricter Markdown budgets of 24 KB / 600 lines, and caches syntax
  work by content digest.
- `src/sase/ace/tui/util/frontmatter_syntax.py` already has the desirable Markdown
  behavior: YAML frontmatter is lexed as YAML and the remaining source as Markdown.

There are also two traps in the current representation:

1. `PagerSection.body` permits any Rich renderable. Once labels are present, an opaque
   renderable is flattened through `_render_plain()`, which cannot retain arbitrary
   styles. The syntax feature should not widen that existing limitation: automatic
   syntax should be requested only for raw-text sections.
2. A `Syntax` renderable cannot simply be placed in `body`. The label path needs a
   character-addressable `Text`; it would flatten `Syntax` and discard its styles.
   `Syntax.highlight()` (or an equivalent token-to-`Text` helper) is the correct seam.

The original pager design also explicitly requires that first paint not wait for syntax
highlighting. The implementation should honor that by treating syntax as a lazy visual
layer, not work performed by `PagerSection.__post_init__` on the UI path.

## Non-negotiable invariants

The design should encode these as tests, not conventions:

- `styled_text.plain == section.plain_text` exactly.
- Syntax never inserts line numbers, padding, notices, or a trailing newline into the
  section body.
- Default/automatic syntax does not run on a section merely because `kind == "file"`.
  Generated file cards and existing styled output also use that kind.
- Existing styles win on every overlapping Rich style attribute.
- Link scanning and attached-target validation always use the original plain text.
- Link capsules and destination accents remain the top visual layer.
- Plain/redirected output remains byte-stable and contains no newly generated ANSI.
- Highlighting never performs disk I/O or expensive lexing on Textual's event loop or
  serial message pump.
- Any auto-detection, lexer, cache, or worker error returns today's body unchanged.

The exact-text invariant matters more than it first appears. Rich constructs Pygments
lexers with defaults that can add a final newline, and a positive `tabsize` expands
tabs. Pygments documents both behaviors: `ensurenl` defaults to true and `tabsize > 0`
expands tabs ([Pygments lexer options](https://pygments.org/docs/lexers/)). In a local
probe, `Syntax("x=1", "python").highlight(...)` returned `"x=1\n"`, and a leading tab
became four spaces with `tab_size=4`. Either change invalidates pager spans.

The safe construction is a concrete lexer instance configured with:

```python
stripnl=False, ensurenl=False, tabsize=0
```

and a `Syntax`/theme configuration that also uses `tab_size=0`. The result must then be
checked for exact equality before its spans are accepted. Pygments' documented token API
provides original input offsets, so building a `Text` directly from those tokens is also
viable ([Pygments API](https://pygments.org/docs/api/)); using Rich keeps SASE's current
style machinery and is less code.

## Recommended model

### 1. Make syntax intent explicit in the document

Add a small immutable value, conceptually:

```python
@dataclass(frozen=True, slots=True)
class PagerSyntax:
    lexer: str
    source: Literal["explicit", "filename", "artifact", "shebang"]

@dataclass(frozen=True, slots=True)
class PagerSection:
    ...
    syntax: PagerSyntax | None = None
```

Store a resolved canonical lexer alias, not merely a filename to guess later. Detection
belongs at adapter boundaries, where source provenance still exists; rendering belongs
in the pager. Existing constructors default to `None`, so all existing styled sections
are unchanged unless a caller deliberately opts them in.

Do not infer syntax from `PagerSection.kind`. In particular, directory listings, media
cards, binary metadata cards, and some artifact summaries all use `kind="file"` but are
not files whose title should drive a lexer.

This is presentation metadata tied to Pygments and Rich, so it belongs in the Python
frontend rather than the Rust core. A future frontend-neutral file-type classifier may
belong in core, but a Pygments alias does not.

### 2. Centralize conservative file-type resolution

SASE currently has near-identical extension maps in the file panel, mentor review,
workflow HITL, and attachment preview code. The pager should not create a fifth. Extract
a shared resolver and migrate callers opportunistically.

Recommended precedence:

1. Explicit caller/CLI lexer override.
2. Semantic source hint, such as a known diff or a Markdown research/plan artifact.
3. Pygments filename-plus-content resolution with
   `get_lexer_for_filename(name, code=content, ...)`.
4. A small reviewed basename table for gaps that matter to SASE, such as `README*` as
   Markdown, `uv.lock` as TOML, and `.tcss` as CSS.
5. For extensionless input only, content guessing if and only if there is a recognized
   shebang.
6. Plain text.

Filename-aware resolution is both broad and safer than maintaining a hand list.
Pygments says that when several lexers match a filename it uses each lexer's
`analyse_text()` to choose among them, while `guess_lexer_for_filename()` limits the
candidate set to matching filename patterns ([Pygments API](https://pygments.org/docs/api/)).
That is the right bias for a pager: an unknown file remaining plain is preferable to
confidently wrong colors.

Unrestricted content-only guessing should not be used. A small local probe illustrates
why:

| Input | Filename-aware result | Content-only result |
| --- | --- | --- |
| `Makefile` | Make | T-SQL |
| `Dockerfile` | Docker | plain text |
| `app.tsx` | TSX | GDScript |
| `config.yml` | YAML | plain text |
| `view.html.j2` | HTML+Django/Jinja | XML+Django |

The resolver should special-case Markdown to reuse SASE's frontmatter-aware composite
lexer. This preserves literal Markdown source characters—which link/search offsets
require—while highlighting frontmatter correctly. A Rich `Markdown` renderable is not
appropriate because it structurally transforms and reflows the source.

SASE's `.sase` ProjectSpec format deserves a native semantic highlighter eventually.
The linked `sase-nvim` repo already has an extensive ProjectSpec syntax definition whose
roles and colors match ACE. Pretending `.sase` is YAML or INI would be misleading.
For this feature's first version, leave it plain unless a canonical Python/core token
projection is added; record native ProjectSpec highlighting as the next format-specific
addition rather than copying the editor grammar into a third implementation.

### 3. Compose styles in a declared order

For an eligible section, create syntax-highlighted `Text` from
`section.plain_text`. Then merge the section's original `body_text` base style and spans
over it, in original order. Rich's later spans override only the attributes they set, so
an existing red ANSI token stays red; an existing bold-only span can remain bold while
receiving a syntax foreground beneath it.

The complete visual stack should be:

```text
plain source text (the one coordinate space)
  └─ syntax token styles
      └─ existing caller/ANSI semantic styles
          └─ link target accents + jump capsules
              └─ search match background/current-match emphasis
```

The current link renderer already implements the fourth layer correctly: it slices the
styled source and then accents only the linked target. That means a path remains visually
a pager link even if it appears inside a Python string or Markdown paragraph.

Search currently creates a fresh unstyled, unwrapped `Text` while search mode is active,
so both existing styles and labels temporarily disappear. Syntax highlighting need not
block on fixing that pre-existing behavior, but the polished implementation should let
`VimSearchController` accept an optional styled base `Text`: search over `.plain`, copy
the base, and add only match backgrounds. The pager can build a label-free styled search
base with the same section-divider text as `search_corpus()`. This makes the final layer
ordering literal and avoids a monochrome flash when `/` is pressed.

### 4. Highlight lazily and cache independently of width

On mount, paint the original/current body immediately. Start one pump-free worker that
highlights eligible sections, current section first, and returns immutable `Text`
results. Apply results only if the document generation still matches. If search is
active, cache the result and reveal it after search exits rather than replacing the
search overlay.

Cache the syntax layer by:

```text
(content digest, lexer identity/options, dark-or-light syntax palette)
```

Do not include viewport width: lexical styles are width-independent. The existing body
layout cache remains responsible for width-dependent wrapping and section offsets.
Because accepted highlighted text is character-identical, swapping the style layer does
not change wrapping, scroll positions, target spans, or trail anchors.

Use the existing syntax-highlight caps as the starting policy. The pager-specific large
file fallback must retain the **entire original body** rather than calling
`lazy_renderable()` unchanged, because that helper's later plain-render cap deliberately
truncates content for panels. A pager must not silently remove searchable/copyable text.
At most, expose a quiet one-time footer status such as “large file: syntax skipped.”

An indicative microbenchmark used the versions pinned by this checkout (Rich 14.3.3,
Pygments 2.19.2), seven warm runs, median wall time on this host:

| Lexer/input | Size / lines | Median `Syntax.highlight()` |
| --- | ---: | ---: |
| Python source | 6.8 KB / 176 | 8.2 ms |
| Python source | 64 KB / 1,653 | 80.4 ms |
| Markdown | 5.0 KB / 78 | 8.6 ms |
| Markdown | 24 KB / 371 | 42.7 ms |
| CSS | 64 KB / 3,541 | 39.1 ms |
| CSS | 174 KB / 9,259 | 106.8 ms |
| TOML | 64 KB / 332 | 13.2 ms |
| TOML | 416 KB / 2,616 | 96.4 ms |

These are not cross-machine performance claims, but they validate the architecture:
small files are cheap, the existing caps are defensible, and even sub-100 ms work should
not sit on Textual's serial UI path.

### 5. Use a quiet, theme-aware visual treatment

Rich officially supports the special `ansi_dark` and `ansi_light` syntax themes, which
use the terminal's configured colors, and supports a default terminal background
([Rich syntax documentation](https://rich.readthedocs.io/en/stable/syntax.html)). Use
`ansi_dark` when `app.current_theme.dark` is true and `ansi_light` otherwise. The ANSI
themes have no opaque Pygments background, so a whole file reads as part of the pager
rather than a giant Monokai card.

Specific aesthetic decisions:

- No line-number gutter in v1. It consumes width, changes the visual coordinate space,
  and competes with link capsules. Existing `:line` navigation and `E` cover the main
  need.
- No per-file border or colored background. The sticky subject and section rules already
  provide structure.
- Syntax colors should remain lower-salience than SASE link accents and the gold jump
  capsules; applying pager targets last guarantees this.
- Unknown/plain sections receive no badge or empty ornament. Automatic fallback should
  preserve the pager's “absence costs nothing” visual rule.
- If a persistent language indicator is later wanted, add a short dim language label to
  the subject only after narrow-width truncation is designed; it is not needed to make
  highlighting understandable.

Textual's `TextArea` supports read-only mode, syntax themes, wrapping, and tree-sitter
highlighting ([Textual TextArea documentation](https://textual.textualize.io/widgets/text_area/)).
It is attractive in isolation but wrong for this surface: it owns cursor/editing key
behavior, has its own scroll/document model, supports a smaller fixed language set unless
grammars and queries are registered, and cannot naturally preserve the pager's
continuous multi-section Rich body plus inserted label capsules. It would turn a style
feature into a pager rewrite.

## User-facing behavior

Default behavior should be automatic and conservative:

- File paths and file-backed artifact documents are highlighted when confidently
  recognized.
- Styled bead/detail sections remain exactly as rendered today.
- Generated directory/media/binary cards remain plain.
- Unknown types remain plain.
- Large files remain complete and plain.
- Redirected output and `--plain` remain plain and byte-stable.

Add `-s/--syntax VALUE` to `sase pager`, following the project's requirement that public
long options have short aliases:

- `auto` (default): adapter/filename detection.
- `never`: today's rendering, useful for accessibility or troubleshooting.
- Any valid Pygments lexer alias, such as `python`, `diff`, or `markdown`: force that
  lexer for raw input sections, especially stdin.

An invalid explicit alias should be a clear CLI error before the app starts. An inferred
lexer failure should silently fall back to plain and be logged for diagnostics. For
stdin, use a filename-looking `--title` as a filename hint; otherwise only a clear
shebang or explicit `--syntax` should enable highlighting.

Entry-point wiring should be explicit:

| Entry point | Syntax decision |
| --- | --- |
| `sase pager path...` | Central filename/content resolver in `path_section()` |
| Pager-followed file/artifact | Same resolver after the concrete path is known |
| ACE `v` file list | Inherits `document_from_paths()` behavior |
| `sase artifact read` for plan/research/chat | Resolved path first; artifact-kind Markdown hint if no useful suffix |
| `sase bead show` | No inferred syntax; preserve authored ANSI/Rich styles |
| stdin | `--syntax`, filename-like `--title`, or strong shebang; otherwise plain |
| Directory/media/binary cards | Plain |
| Commit/diff sections | Explicit `diff` from the semantic source |

## Alternatives considered

| Approach | Assessment |
| --- | --- |
| Replace the body with read-only Textual `TextArea` | Reject: incompatible key/scroll ownership, language coverage, Rich style preservation, multi-section layout, and jump-label insertion. |
| Store a Rich `Syntax` renderable directly in `PagerSection.body` | Reject: label composition flattens arbitrary renderables and loses the syntax spans; line-number/padding modes also corrupt the pager coordinate model. |
| Shell out to `bat` or `pygmentize`, then parse ANSI | Reject: restores the subprocess and dependency split the SASE pager was created to remove, makes cancellation/cache behavior harder, and offers no advantage over in-process Rich/Pygments. |
| Render Markdown with Rich `Markdown` | Reject: beautiful document rendering, but it hides markup and changes wrapping/geometry, breaking exact source offsets and the editor-like pager contract. |
| Apply syntax over all `kind="file"` sections | Reject: generated cards and already-styled outputs would be recolored or misdetected. Provenance must opt raw text in. |
| Content-only lexer guessing | Reject: visually confident false positives are worse than plain text; local examples guessed Make as T-SQL and TSX as GDScript. |
| Pre-highlight every section synchronously | Reject: simple but violates the pager/TUI first-paint and pump rules and scales poorly for multi-file documents. |

## Implementation and verification outline

1. Add a pure pager syntax module containing `PagerSyntax`, the conservative resolver,
   exact-text highlighting, style-layer merge, and a bounded digest cache. Reuse/extract
   the existing cap constants and frontmatter Markdown lexer rather than duplicating
   them.
2. Add optional syntax metadata to `PagerSection`; leave all existing constructors
   behaviorally unchanged.
3. Wire raw-source adapters and the `-s/--syntax` option. Do not infer at screen level
   from `kind` or title alone.
4. Add a per-screen syntax-layer cache and a generation-checked pump-free worker.
   Recompose with the existing label layer after results arrive.
5. Preserve syntax in search by allowing a styled search base, either in the shared
   controller or through a pager host adapter.
6. Add documentation and visual snapshots before considering a native ProjectSpec
   lexer.

Minimum tests:

- Exact text for no-final-newline, tabs, Unicode/wide cells, CRLF-normalized input,
  empty text, and multiple trailing newlines.
- Every failure path—unknown alias, lexer exception, token text mismatch, oversized
  source—returns the original `body_text` and complete `plain_text`.
- An ANSI-colored range overlapping a Python token retains the ANSI foreground, while
  unstyled neighboring tokens receive syntax colors.
- Link spans, attached targets, label hints, and copied values are identical before and
  after highlighting.
- Path detection covers Python, Rust, YAML, JSON/JSONL, TOML, shell, CSS/TCSS, JS/TSX,
  HTML templates, Markdown with frontmatter, diffs/patches, Makefile, Dockerfile,
  `uv.lock`, unknown extensions, and shebang scripts.
- Large files remain fully searchable and are not truncated.
- A stale worker cannot recolor a newly followed document; resizing never re-lexes.
- Search match backgrounds layer over syntax without removing syntax foregrounds.
- CLI redirected/plain output is byte-identical to the pre-feature output.
- PNG snapshots at 120×40 and 60×30 for Python, Markdown/frontmatter, diff, ANSI-plus-
  syntax overlap, link-inside-string, unknown/plain, large-file fallback, and active
  search. Include a pixel-equality assertion showing that `syntax=None` is identical to
  today's zero-syntax rendering.
- Performance traces prove first paint and scroll/key paths do no lexing; the existing
  pager and TUI latency budgets remain intact.

## Recommended solution

Implement an adapter-declared, lazy `PagerSyntax` layer backed by in-process
Rich/Pygments. Resolve file types conservatively from explicit hints and filename plus
content; highlight with a no-normalization lexer; accept the result only when its plain
text exactly matches the pager source; layer current ANSI/Rich styles above syntax and
pager labels/search above both; cache by content/lexer/theme; and fall back to the full,
unchanged body on ambiguity, size, or error. Ship `auto` by default with
`-s/--syntax never|LEXER` as the escape hatch. This is the smallest design that is
intuitive for files, reliable for the pager's offset-driven interactions, and visually
consistent with SASE rather than a second embedded editor.
