# File-Type Syntax Highlighting In The SASE Pager

**Researcher B** · 2026-09-07 · workspace-local investigation of `src/sase/pager/`,
`src/sase/xprompt/highlight*.py`, and the Rich/Pygments/Textual rendering stack.

---

## 1. The question, restated precisely

> "Add appropriate syntax highlighting depending on the file type, **and keep the current
> syntax highlighting intact.**"

The second half is the whole problem, and it is not primarily a visual problem. The
pager's "current highlighting" is not decoration layered on inert text — it is
**position-addressed styling computed from character offsets into
`PagerSection.plain_text`**. Link labels, jump-hint allocation, dangling marks, the
search corpus, the wrapped-row estimator, the trail's scroll restore, and the `--plain`
fallback are all keyed off those offsets.

So the design question is not "which highlighter looks best." It is:

> **How do we add a second styling producer without any producer ever being allowed to
> change a single character of the document?**

Everything below follows from answering that first, and answering it structurally rather
than by convention.

---

## 2. Inventory: what the pager highlights today

I walked every producer of styled output in the pager. There are five, and all of them
already obey the offset invariant — one of them explicitly and in writing.

| # | Layer | Where | How it styles |
|---|-------|-------|----------------|
| L1 | **Producer ANSI** | `document._body_to_text` → `Text.from_ansi(body)` | Bead detail, `git show`, any colorized CLI output piped in. `cli_detail.py:47` documents the invariant verbatim: *"Styling is purely additive ANSI: for any detail, style, and wrap, stripping SGR escapes from the output reproduces the matching `DetailStyle.PLAIN` bytes exactly."* |
| L2 | **Link targets** | `_labels.render_section_with_labels` | `bold <kind accent>` over the target span; `dim` + ` (missing)` when dangling. |
| L3 | **Key capsules** | `_labels._label_prefix` | `[<hint>]` on `#FFD75F`, then a kind glyph + NBSP in the kind accent. Inserted into a *derived* render `Text`, never into `plain_text`. |
| L4 | **Search matches** | `vim_search_controller._render_overlay` | `MATCH_STYLE` / `CURRENT_MATCH_STYLE` over corpus offsets. |
| L5 | **Chrome** | `_chrome.py` | Subject line, section rules, footer legend. Separate widgets; no interaction with body offsets. |

Two facts about this inventory matter for the design:

1. **L3 is the only thing in the pager that inserts characters**, and it gets away with
   it because insertion happens *after* all offset consumers have run, into a throwaway
   render `Text`. That is the existing precedent for "how do you add glyphs safely" and
   it is worth preserving as the *only* exception.
2. **There is a live plan that already fixed a bleed between two of these layers** —
   `plan:202608/pager_hint_highlight_boundary.md` ("Limit pager hint highlighting to the
   bracketed key"). Its root cause was Rich merging an appended span with a base style,
   so the capsule background leaked onto the kind icon. That is precisely the class of
   bug a third styling layer will reintroduce if layer precedence stays implicit.

**Conclusion for the design:** "keep the current highlighting intact" should be made a
*declared, tested precedence table*, not an emergent property of the order in which spans
happen to be appended.

---

## 3. The constraint that eliminates most of the option space

I measured what the obvious implementations do to the text. This is the single most
important result in this report.

### 3.1 `rich.syntax.Syntax` silently rewrites the document

`Syntax.highlight(code)` returns a `Text`, which looks perfect for our purposes. It is
not. Pygments' `Lexer._preprocess_lexer_input` mutates the input before tokenizing, and
Rich passes that mutation through:

| Input | `Syntax.highlight()` output | Damage |
|-------|------------------------------|--------|
| `"x = 1\ny = 2"` (no trailing NL) | `"x = 1\ny = 2\n"` | +1 char — every later offset shifts |
| `"x = 1\r\ny = 2\r\n"` (CRLF) | `"x = 1\ny = 2\n"` | −2 chars |
| `""` (empty file) | `"\n"` | +1 char |
| `"def f():\n\tif 1:\n\t\treturn 2\n"` | tabs expanded to 4 spaces | +9 chars |
| `"a=1\n\n\n\n"` | unchanged | ✓ |

Three of five realistic cases desync. A desync here is not cosmetic: `_labels` would
paint capsules at the wrong characters, `y<label>` would copy the wrong ref, `E<label>`
would open the editor at the wrong line, and `search_corpus` would scroll to the wrong
row. **`rich.syntax.Syntax` is disqualified as-is.**

`rich.markdown.Markdown` is worse — it reflows and re-emits, so offsets are destroyed
entirely. Also disqualified.

### 3.2 Direct Pygments *is* offset-exact, with three lexer options

Constructing the lexer with `stripnl=False, ensurenl=False, stripall=False, tabsize=0`
disables every preprocessing step, and `get_tokens_unprocessed()` then yields
`(char_offset, token, value)` triples that index the original string exactly. Verified
across the same case matrix plus astral-plane Unicode:

```
'no trailing nl'   rebuilt_eq=True offsets_ok=True
'crlf'             rebuilt_eq=True offsets_ok=True
'empty'            rebuilt_eq=True offsets_ok=True
'tabs'             rebuilt_eq=True offsets_ok=True
'bad syntax'       rebuilt_eq=True offsets_ok=True
'unicode'          rebuilt_eq=True offsets_ok=True     # "s = '你好 😀'"
```

`offsets_ok` asserts `code[i:i+len(v)] == v` for every emitted token — i.e. the offsets
are not merely *consistent*, they are *correct against the original text*.

### 3.3 End-to-end proof that the invariant is sufficient

I wired a throwaway prototype into `PagerSection` (`syntax: str | None` field, spans
applied under the existing ANSI/label layers) and ran the pager's full suite plus its
CLI and ACE callers:

```
tests/pager tests/test_cli_pager.py tests/main/test_pager_command.py
tests/ace/tui/actions/test_view_files_pager.py
→ 140 passed, 6 deselected
```

Zero test changes. **If plain text is invariant, nothing in the pager notices a new
styling layer.** The prototype was removed and the tree restored to clean before writing
this report (`tests/pager` re-verified: 102 passed).

---

## 4. Engine evaluation

| Engine | Offsets | Languages | Markdown quality | Verdict |
|--------|---------|-----------|------------------|---------|
| `rich.syntax.Syntax` renderable | **mutates text** | 500+ | n/a | ✗ disqualified (§3.1) |
| `rich.markdown.Markdown` | reflows | n/a | good | ✗ disqualified |
| Shell out to `bat` | no contract | 200+ | good | ✗ subprocess on the render path violates `tui_perf` rule 1; no offset contract; also abandons the in-process design `docs/pager.md` advertises ("SASE no longer shells out to `$PAGER` or `less`") |
| **Textual tree-sitter** (`sase/ace/tui/util/code_injection.py`) | UTF-8 bytes → needs conversion | **15** | **block-only** | ✗ as primary (see below) |
| **Pygments, unprocessed** | **exact chars** | 500+ | adequate + nests fences | ✓ **recommended** |

### 4.1 Why not tree-sitter, despite it already being in the repo

This was the closest call, and the repo does already have the machinery: `code_injection.py`
uses `textual._tree_sitter.get_language` + `TextArea._get_builtin_highlight_query` to
highlight fenced code inside prompt Markdown. Reusing it would give editor-consistent
colors for free.

I measured its coverage. Two findings kill it as the *primary* engine:

**(a) Only 15 languages**, all installed:
`bash css go html java javascript json markdown python regex rust sql toml xml yaml`.
Notably absent: **`diff`** — which the pager explicitly supports (`PagerOrigin.DIFF`
exists; `docs/pager.md` documents `git show --stat | sase pager -t "git show"`).

**(b) Textual's markdown grammar is block-only.** Capture counts on a real SASE plan
file:

```
tree-sitter markdown: heading, heading.marker, list.marker, punctuation.special   (4 roles)
pygments  markdown:   Generic.Heading, Generic.Subheading, Generic.Strong,
                      String.Backtick, Name.Attribute, Name.Tag, Keyword        (7 roles)
```

No inline emphasis, no code spans, no links. **Markdown is SASE's dominant content type**
— beads, plans, research, memory notes, agent pages, `sase artifact read` output. Losing
bold/italic/inline-code on markdown to gain richer Python highlighting is the wrong
trade for a *reader*.

Pygments' markdown lexer also **nests fenced code through the inner lexer**, verified:

```
34 Token.Literal.String.Backtick  '\n```'
38 Token.Literal.String.Backtick  'python'
45 Token.Keyword                  'def'
49 Token.Name.Function            'f'
70 Token.Literal.Number.Integer   '1'
```

That is the single highest-value markdown behavior for SASE documents, and it comes free.

**Recommendation:** one engine, Pygments. A hybrid (tree-sitter for 15, Pygments for the
rest) doubles the token vocabulary, doubles the theme, and guarantees that two files in
the same document look like they came from different products. That is a beauty
regression disguised as a capability win.

---

## 5. The house pattern already exists — use it

The strongest finding in this research is that **SASE has already solved this exact
problem once**, in a frontend-agnostic way, and the pager should not invent a second
approach.

### 5.1 `src/sase/xprompt/highlight.py`

> *"Frontend-agnostic xprompt syntax highlight spans."*

- `HighlightSpan(start, end, role)` — half-open **character** ranges carrying a
  **semantic role name**, never a style.
- `_ROLE_PRECEDENCE: dict[Role, int]` — *"Lower numbers win. Keeping every role explicit
  makes precedence additions deliberate and gives same-family overlaps a deterministic
  result."*
- `_flatten_spans()` — sweep-line flattening to a **non-overlapping partition**, so
  "which layer won here" is a decidable question rather than a Rich style-merge accident.
- Every producer wrapped in `try/except → empty` (**fail open**).
- Caps checked before any work: `MAX_HIGHLIGHT_BYTES = 80_000`, `MAX_HIGHLIGHT_LINES = 1_200`.
- `_byte_to_character_offsets()` for producers that speak bytes.

### 5.2 `src/sase/xprompt/highlight_theme.py`

- `HighlightStyle` — *"A frontend-neutral foreground style with Rich and ANSI
  projections"* (`.rich_style`, `.ansi_sgr`). One role table drives both the TUI and
  plain CLI output.
- Colors derived from the **pinned** `flexoki` theme (`ACE_THEME_NAME`), never hardcoded,
  with `derive_argument_color()` blending toward foreground/background.
- `neutral_code = foreground.blend(background, 0.35)` — an explicitly *recessed* tone for
  code.
- `@functools.cache`d.

### 5.3 `plan:202608/agent_metadata_semantic_highlighting.md`

A `wip` plan whose goal line is almost verbatim this request — *"reliable, beautiful,
project-aware semantic highlighting"* — and which already wrote down the precedence
discipline:

> 1. Markdown supplies the base presentation.
> 2. Glossary and repo roles annotate natural-language text.
> 3. Xprompt/directive/skill syntax wins inside structural xprompt tokens.
> 4. Inline and fenced code retain code styling without semantic underlines.
> 5. **Numbered file hints are restored last and remain the strongest local affordance.**
>
> *"The overlay must be bounded by the existing prompt/Markdown byte and line caps and
> must fail open."*

Line 5 is the pager's answer to "keep the current highlighting intact," stated in
SASE's own words: **the link layer is the strongest local affordance and is applied
last.** Adopt that sentence as the pager's contract.

---

## 6. Recommended design

### 6.1 The pager layer stack (the core of the proposal)

Make the layer order explicit, ordered, and tested:

```
L0  characters          the document.  NO layer may insert, delete, reorder,
                        or normalize a character of L0.
L1  producer ANSI       Text.from_ansi spans (bead show, git, colorized CLI)
L2  syntax              NEW.  Pygments roles.  Applied only when L1 is empty.
L3  semantic            RESERVED.  glossary / repo / artifact-ref overlays
                        (the metadata plan's layer, if it ever reaches the pager)
L4  link                target accent, dangling dim, key capsule       ← strongest
L5  search              match / current-match, painted on the overlay
```

Three rules, each a test:

- **R1 — Text invariance.** For every language and every section,
  `section.plain_text == <raw body>`, byte for byte. Property test over a corpus
  including CRLF, tabs, no-trailing-newline, empty, lone-newline, and astral-plane
  Unicode. This is the rule that makes everything else safe.
- **R2 — L2 yields to L1.** If the body contains `\x1b`, the syntax layer emits nothing.
  We never fight a producer that already chose its colors. (This also means bead
  documents are untouched by construction — their bodies are always ANSI.)
- **R3 — L4 wins.** A character inside a link target renders with the link style
  regardless of its syntax role. Assert this at style-resolution level, in the style of
  the boundary assertions `plan:202608/pager_hint_highlight_boundary.md` already
  mandated ("resolve the effective Rich style at representative offsets").

One deliberate nuance on R3: `_LABEL_DANGLING_STYLE` is `"dim"` — *attribute only, no
color*. Rich layering means a dangling link over highlighted code shows the syntax color,
dimmed. That is the correct and prettier behavior; keep it, and pin it with a test so a
later refactor to a flat partition does not silently lose it.

### 6.2 Modules

```
src/sase/pager/language.py      resolve_language(...) -> str | None      (pure)
src/sase/pager/syntax.py        syntax_spans(text, language) -> tuple[HighlightSpan, ...]
src/sase/pager/syntax_theme.py  role -> HighlightStyle, flexoki-derived, cached
```

`syntax.py` mirrors `xprompt/highlight.py` exactly: closed role vocabulary, caps first,
`try/except → ()`, char offsets, `_flatten_spans` for determinism. The lexer is
constructed **once per language and cached**, with the offset-fidelity options:

```python
get_lexer_by_name(name, stripnl=False, ensurenl=False, stripall=False, tabsize=0)
```

Those four keyword arguments are the entire correctness argument of §3.2. They deserve a
comment saying so, because a future contributor "simplifying" them to
`get_lexer_by_name(name)` reintroduces every failure in the §3.1 table with no test
failure in `tests/pager` unless R1 exists.

**Role vocabulary** (fold ~40 Pygments token types into ~14 roles; fewer roles is the
beauty decision, see §6.4):

```
code.keyword  code.type     code.function  code.constant  code.number
code.string   code.comment  code.decorator code.error
md.heading    md.emphasis   md.code
diff.inserted diff.deleted
```

Everything else — `Name`, `Operator`, `Punctuation`, `Text` — emits **no role** and
renders as plain foreground.

### 6.3 Language resolution

`PagerSection` gains `language: str | None`, **declared by the adapter, never sniffed at
paint time.** Resolution order:

1. Explicit `PagerSection.language` (caller/adapter wins).
2. `sase pager --syntax <name|none>` CLI override.
3. **SASE override table**, then `pygments.lexers.get_lexer_for_filename`.
4. Shebang sniff for extensionless files (`#!/usr/bin/env python`).
5. Content sniff, *diff only*: `diff --git` / `^--- a/` / `^@@ ` → `diff`. This is what
   makes `git show | sase pager` beautiful, and it is the one stdin case worth sniffing.
6. `PagerOrigin.DIFF` → `diff`; markdown-bodied artifact kinds (`plan:`, `research:`) → `markdown`.
7. Otherwise `None` → today's behavior exactly.

**Never call `pygments.lexers.guess_lexer()`** on content. It is slow and unreliable, and
a wrong guess makes a document *worse* than no highlighting.

The override table is not optional — I measured `get_lexer_for_filename` against SASE's
actual file inventory and it misses or mis-maps eight types that exist in this repo:

| Filename | Pygments default | Should be |
|----------|------------------|-----------|
| `*.tcss` (e.g. `src/sase/ace/tui/styles.tcss`) | *(none)* | `css` |
| `Justfile` / `justfile` | *(none)* | `make` |
| `uv.lock`, `*.lock` | *(none)* | `toml` |
| `*.j2`, `*.jinja` | *(none)* | `jinja` |
| `*.xprompt` | *(none)* | `markdown` |
| `*.sql` | `tsql` | `sql` |
| `.gitignore`, `.env` | *(none)* | `text` / `bash` |
| `*.log` | *(none)* | *(leave none — deliberate)* |

Correct out of the box: `.py .md .rs .toml .yml .yaml .json .sh .html .css .xml .svg
.ini .cfg .rst .diff .patch .ts .tsx .js .go .c .cpp .java .rb .lua .vim Dockerfile
Makefile .bashrc`.

**Rust-core boundary note.** Per `rust_core_backend_boundary`, "would another frontend
need this to match?" — a web viewer or editor integration *would* need the same answer to
"what language is this artifact?" The *renderer* (Pygments, Rich styles) is presentation
and stays in Python. The *language identity* is arguably domain. I recommend keeping it
in Python now but isolating it in one pure function with no I/O, so promoting
`resolve_language` into `sase-core` later is a mechanical move rather than an
archaeology project. Flagging this explicitly rather than deciding it unilaterally.

### 6.4 The beauty argument, with numbers

This is the part I would defend hardest, because it is where a naive implementation goes
wrong and still passes every test.

**The pager is a reader with a job.** Its primary affordance is *finding and pressing
links*. Syntax color is a structural hint, not a call to action. If the syntax layer is
as loud as the link layer, the feature makes the pager objectively worse at its job while
looking "more colorful."

I rendered this A/B. With Rich's `ansi_dark` palette, `String → yellow` and
`Number → bright_blue` — and the file accent `#FFAF5F` and the `#FFD75F` capsule stopped
reading as *the* thing on the line. With a restrained palette (strings green, comments
dim-italic, keywords cyan, `Name` unstyled) the link layer popped straight back out.

Quantitatively, WCAG relative contrast against flexoki's `#100F0F` background:

```
LINK ACCENTS (figure)                 FLEXOKI ROLES (ground)
  capsule bg  #FFD75F   13.80          neutral_code #ABA9A1   8.13
  stitches    #FFD700   13.65          warning      #AD8301   5.49
  files       #FFAF5F   10.53          accent       #9B76C8   5.30
  patches     #00D7AF   10.33          success      #66800B   4.24
  beads       #D787FF    8.02          secondary    #24837B   4.20
  external    #FF5F5F    6.43          error        #AF3029   2.99
  agents      #0062FF    3.82          primary      #205EA6   2.93
                                     body foreground #FFFCF0  18.62
```

Flexoki's raw role colors land at **2.9–5.5**; the link accents at **6.4–13.8**; plain
body text at **18.6**. That is already the right three-tier hierarchy — *content
brightest, affordances next, structure quietest* — but two flexoki roles (`primary`,
`error`) fall below the 4.5:1 body-text floor and are genuinely hard to read.

So the theme derivation should **lift each chromatic role toward the foreground until it
enters a contrast band**, exactly the way `derive_argument_color()` already blends. I
computed a candidate palette with floor 4.5 and ceiling 6.4 (the minimum link-accent
contrast):

```
code.keyword   #205EA6 → #4E7FB5   4.58
code.function  #205EA6 → #4E7FB5   4.58
code.string    #66800B → #6C8414   4.51
code.type      #24837B → #2E8980   4.56
code.number    #9B76C8 → #9B76C8   5.30   (already in band)
code.constant  #AD8301 → #AD8301   5.49   (already in band)
code.error     #AF3029 → #C15E56   4.56
diff.inserted  #66800B → #6C8414   4.51
diff.deleted   #AF3029 → #C15E56   4.56
code.comment   dim + italic (no color)    4.40 — deliberately recessed
md.heading     bold (no color)            inherits 18.62
md.emphasis    bold / italic (no color)
md.code        #ABA9A1 (neutral_code)     8.13 — achromatic, does not compete for hue
```

**Make that band an automated test**, not a style guide sentence:

> Every *chromatic* syntax role satisfies `4.5 ≤ contrast(role, background) ≤ min(link accent contrast)`.

That single assertion is what keeps this feature beautiful after ten people have touched
it. It is the kind of rule that survives contributors; "use restrained colors" is not.

Four supporting rules:

- **Fewer roles, not more.** Leave `Name`, `Operator`, and `Punctuation` unstyled. The
  visual difference between "keywords, strings, comments, and types are marked" and
  "every token is marked" is the difference between a calm document and a ransom note.
  This also happens to be why `ansi_dark` reads well despite being tiny.
- **Reserve the SASE accent hues.** Orange, gold, violet, agent-blue, teal, and
  external-red belong to the link layer. The syntax palette must not borrow them —
  flexoki's hues are naturally distinct, which is a second reason to derive from it.
- **Absence costs nothing** (`_chrome.py`'s own stated rule). No language → no color, no
  badge, no notice. Never render a "plain text" chip.
- **But make the guess visible.** The subject line already carries `⌘ 1.2Kc`. Add one
  more dim chip: `· py`, `· md`, `· diff`. It costs three cells, makes the feature
  discoverable, and turns "why isn't my file highlighted?" from a bug report into a
  glance. It is also the honest thing to do: the pager is guessing, and it should say so.

### 6.5 Where the layer is applied (and why not in `__post_init__`)

Tempting: highlight inside `_body_to_text`, as my prototype did. It works and it is ~10
lines. I recommend against it for three reasons:

1. **`--plain` would pay for it.** `handle_pager_command` builds the full document and
   *then* decides to dump plain text (redirected stdout, `--plain`, no `/dev/tty`).
   Eager highlighting lexes a 9 000-line file to throw the styles away.
2. **The theme is not known yet.** `PagerSection` is constructed outside the app.
   Flexoki-derived styles need `app.current_theme` (or the pinned `BUILTIN_THEMES["flexoki"]`),
   and a theme change should be able to repaint.
3. **`PagerSection` is a document model, not a view.** Baking presentation into a frozen
   dataclass that `--plain`, the search corpus, and the link scanner all read from is the
   kind of coupling that makes the next feature hard.

Apply it in `_layout._section_renderable` / `_labels.render_section_with_labels` instead,
against a **cached styled base text keyed by `(section identity, theme signature)`**.
Width changes must *not* invalidate it: spans are character offsets, wrapping happens
downstream, so the cache survives every resize. The metadata-highlighting plan already
calls for "a compact style signature for rendered cache keys so switching between dark and
light themes cannot reuse stale colors" — same mechanism, same reason.

### 6.6 Performance and bounds

Measured on `src/sase/ace/tui/styles.tcss` — 174 KB, 9 258 lines, the largest text file
in the repo:

```
pygments lex (unprocessed)   0.125 s   45 013 tokens
build spans + stylize        0.034 s   29 511 spans
render_lines (with spans)    0.372 s
render_lines (plain)         0.208 s   → +0.164 s attributable to styling
```

For context, the pager is *already* O(document) and synchronous: `compose_body` calls
`_measure_section_heights`, which does a full `render_lines` at every width change. So
this is a proportionate cost, not a new class of cost — but `tui_perf` rules 1 and 2 mean
it must be bounded.

- **Adopt the house caps**: `MAX_HIGHLIGHT_BYTES = 80_000`, `MAX_HIGHLIGHT_LINES = 1_200`
  (`sase/xprompt/highlight.py`). At 80 KB the lex+span cost is roughly 70 ms — under the
  work the pager already does to lay the same document out.
- **Add a max-line-length guard.** A 5 MB single-line minified JSON blob passes a
  line-count cap and destroys a lexer. Neither existing cap catches it.
- **Cache the lexer per language** (`@lru_cache`) — `get_lexer_by_name` is not free.
- **Do not lex on a pump callback.** Highlight during body composition (already
  synchronous and already O(document)), never in a keypress or timer callback.
- *(Deferred)* Progressive highlighting for documents over the cap — paint plain
  immediately, lex in a `spawn_pump_free_task`, repaint. Beautiful, and correctly a
  second phase.

### 6.7 Surfaces — including two flags that currently do nothing

`sase pager` parses `-c/--color` and `-w/--wrap`, and **neither is referenced anywhere in
`src/sase/main/pager_handler.py` or `src/sase/pager/`.** They are documented in
`docs/pager.md` and dead in the code. This feature is the natural occasion to give
`--color` a real job:

| Surface | Behavior |
|---------|----------|
| `--color never` | No syntax layer. (Ideally no accent layer either — that is what the flag claims to mean.) |
| `--color auto` / `always` | Syntax layer on when a language resolves. |
| `--syntax <name\|none>` *(new)* | Force or suppress the language for every section. |
| `--plain` / non-TTY | Unaffected — plain output has no styles by construction. |
| `pager.syntax: auto\|never` *(new config)* | Per the `sase_flags` rule: **this is a config field, not a feature flag.** "Do not flag anything users are meant to choose forever." A `beta` flag is only warranted if this lands as a multi-phase epic where an intermediate phase would expose unfinished behavior. |

`--wrap` being dead is out of scope but worth a task bead; it is adjacent enough that
someone will trip over it while implementing this.

---

## 7. Reliability: failure modes and how each is closed

| Failure | Closure |
|---------|---------|
| Lexer mutates text → labels/search/editor jumps land wrong | R1 property test; the four lexer options; commented as load-bearing |
| Lexer raises on malformed input | `try/except → ()` (house pattern). A pager must never fail to display a file it can display today |
| Unknown extension | Return `None`; render exactly as today |
| Producer ANSI + syntax fight | R2: syntax suppressed when `\x1b` present |
| Syntax color swallows a link | R3 style-boundary assertions at resolved offsets, per the `pager_hint_highlight_boundary` precedent |
| Huge file freezes the TUI | Byte + line + max-line-length caps before any lexing |
| Light terminal / theme switch | Theme-derived colors + style signature in the cache key |
| Contrast drift over time | The §6.4 contrast-band test |

**One testing trap worth calling out.** I verified that markdown headings and `**strong**`
receive `bold` spans — and then found that **Textual's SVG export emits no `font-weight`
at all** (`grep -o 'font-weight="[^"]*"'` on an exported pager screenshot: zero matches).
So bold-only and italic-only styling is *invisible in the PNG goldens*. Any test that
relies on `tests/pager/visual/` to prove `md.heading`, `md.emphasis`, or `code.comment`
will pass whether or not the feature works. Those roles must be asserted **semantically**,
by resolving the effective Rich style at a character offset. PNG goldens remain the right
tool for color and layout.

---

## 8. Known seams (name them; don't silently accept them)

1. **Search flattens the document.** `VimSearchController._render_overlay` builds
   `Text(self.corpus, no_wrap=True)` from a plain `str` — all body styling is dropped
   while search is active. Today that is invisible because the body is nearly monochrome;
   with syntax highlighting, pressing `/` will visibly drain the color out of the page.
   The fix is an optional host hook returning a styled corpus, but the controller is
   shared with ACE's zoom panel, so the blast radius argues for a follow-up bead rather
   than folding it into this change. **Decide it deliberately; do not discover it in a
   screenshot.**
2. **No line numbers.** `Syntax` normally supplies a gutter; a gutter inserts characters
   and is therefore forbidden by L0. Real, and correctly deferred — it needs a separate
   render structure, not a wider syntax feature.
3. **No horizontal scroll.** `PagerBodyScroll` is a `VerticalScroll` (`overflow-x: hidden`),
   so long code lines wrap. Highlighting makes wrapped code *more* legible, not less, but
   it will make the wrapping more noticeable.
4. **Standalone `SasePager` does not pin flexoki.** ACE sets `self.theme = ACE_THEME_NAME`
   in `_state_init_runtime.py:71`; `SasePager` does not, so `sase pager` from the CLI runs
   on `textual-dark`. Highlighting derived from flexoki would then be theme-mismatched in
   exactly the entry point most people use. **Pin flexoki on `SasePager` as part of this
   change** — it is a one-line fix and without it the feature looks wrong half the time.
5. **`--wrap` is dead** (§6.7). Separate bead.

---

## 9. Recommended solution

**Add a fourth layer to the pager's render stack — a Pygments-backed, role-emitting,
offset-preserving syntax layer built in the exact shape of `sase/xprompt/highlight.py`,
themed from flexoki inside a measured contrast band, and placed *below* the link layer in
an explicit precedence table.**

Phased:

**Phase 1 — the invariant and the plumbing.**
`syntax_spans()` over Pygments with `stripnl=False, ensurenl=False, stripall=False,
tabsize=0`; the closed role vocabulary; house caps plus a max-line guard; fail-open.
`resolve_language()` with the SASE override table. `PagerSection.language`. Composition
in the render path with a `(section, theme signature)` cache. The R1/R2/R3 tests. Pin
flexoki on `SasePager`. **At the end of Phase 1 the pager looks identical when no
language resolves, and every existing test passes unchanged — which I have already
demonstrated empirically (§3.3).**

**Phase 2 — the beauty.**
Flexoki-derived `syntax_theme.py` using `HighlightStyle` from
`sase.xprompt.highlight_theme` (so the roles get a free `.ansi_sgr` projection for
non-TUI output); the contrast-band test; the subject-line language chip; PNG goldens for
`python`, `markdown`, and `diff` at the pager suite's two sizes; semantic style
assertions for the bold/italic roles the SVG exporter cannot see.

**Phase 3 — the surfaces.**
`--syntax`, `--color never` wired to actually suppress color, `pager.syntax` config field
in `default_config.yml`, `docs/pager.md` updated.

**Deferred to beads, not to this change:** styled search corpus; progressive highlighting
above the cap; line-number gutter; the dead `--wrap` flag; promoting `resolve_language`
into `sase-core` if a second frontend appears.

**Why this is the right answer in one sentence:** it makes "keep the current highlighting
intact" a *structural guarantee* — a text-invariance property test plus a declared
precedence table — rather than a hope, and it does so by reusing the span/role/precedence/
fail-open pattern SASE already wrote, tested, and shipped for xprompts.

---

## Appendix A — Reproduction

```bash
# §3.1 Syntax.highlight mutation matrix
.venv/bin/python -c "
from rich.syntax import Syntax
for c in ['x = 1\ny = 2', 'x = 1\r\ny = 2\r\n', '', 'def f():\n\tif 1:\n\t\treturn 2\n']:
    print(repr(c), '->', repr(Syntax(c,'python',theme='ansi_dark').highlight(c).plain))"

# §3.2 offset fidelity
.venv/bin/python -c "
from pygments.lexers import get_lexer_by_name
lx = get_lexer_by_name('python', stripnl=False, ensurenl=False, stripall=False, tabsize=0)
c = 'def f():\n\tif 1:\n\t\treturn 2'
t = list(lx.get_tokens_unprocessed(c))
print(''.join(v for _,_,v in t) == c, all(c[i:i+len(v)]==v for i,_,v in t))"

# §4.1 tree-sitter coverage
.venv/bin/python -c "
from textual.widgets._text_area import BUILTIN_LANGUAGES; print(sorted(BUILTIN_LANGUAGES))
from sase.ace.tui.util.code_injection import injected_highlights
from collections import Counter
md = open('sase/repos/plans/202608/pager_hint_highlight_boundary.md').read()[:1600]
print(Counter(h.name for h in injected_highlights('markdown', md)))"

# §6.4 contrast band
.venv/bin/python -c "
from textual.color import Color
from textual.theme import BUILTIN_THEMES
def lum(c):
    f=lambda v:(v/255)/12.92 if v/255<=0.03928 else (((v/255)+0.055)/1.055)**2.4
    return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b)
def k(a,b):
    la,lb=lum(Color.parse(a)),lum(Color.parse(b)); return (max(la,lb)+.05)/(min(la,lb)+.05)
t=BUILTIN_THEMES['flexoki']
for n,c in [('files','#FFAF5F'),('beads','#D787FF'),('external','#FF5F5F')]: print(n,c,round(k(c,t.background),2))
for n in ('primary','secondary','accent','warning','success','error'): print(n,getattr(t,n),round(k(getattr(t,n),t.background),2))"
```

## Appendix B — Key source references

| Concern | Location |
|---------|----------|
| Body → `Text`, the single insertion point for L2 | `src/sase/pager/document.py:175` (`_body_to_text`) |
| Link layer painting, capsule construction | `src/sase/pager/_labels.py:197` (`render_section_with_labels`), `:249` (`_label_prefix`) |
| Where composition should apply L2 | `src/sase/pager/_layout.py:152` (`_section_renderable`) |
| Width-cached rebuild + perf budget | `src/sase/pager/_screen_body.py:98` (`_ensure_body`) |
| Search corpus (styles dropped) | `src/sase/pager/_layout.py:131` (`search_corpus`), `src/sase/ace/tui/widgets/vim_search_controller.py:379` |
| File adapter — where `language` is declared | `src/sase/pager/adapters.py:35` (`path_section`) |
| Dead `--color` / `--wrap` | `src/sase/main/parser_pager.py:36,61` |
| House span/role/precedence pattern | `src/sase/xprompt/highlight.py` |
| House theme derivation + ANSI projection | `src/sase/xprompt/highlight_theme.py` |
| Tree-sitter alternative | `src/sase/ace/tui/util/code_injection.py` |
| Additive-ANSI invariant, stated | `src/sase/bead/cli_detail.py:47` |
| Prior layer-bleed fix + test discipline | `sase/repos/plans/202608/pager_hint_highlight_boundary.md` |
| Precedence-contract precedent | `sase/repos/plans/202608/agent_metadata_semantic_highlighting.md` |
| ACE theme pin (missing on `SasePager`) | `src/sase/ace/tui/actions/_state_init_runtime.py:71` |
