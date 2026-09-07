# File-Type Syntax Highlighting In The SASE Pager — Consolidated Design

Lead consolidation of two independent reports (`__a`, `__b` in this directory) plus the
lead's own verification pass over `src/sase/pager/`, `src/sase/xprompt/highlight*.py`,
the original pager design doc, and live Pygments/Rich probes. Every load-bearing claim
below was re-verified in this workspace; the few places the researchers disagreed are
resolved explicitly in §9.

---

## 1. The real problem

The request is "highlight by file type **and keep the current highlighting intact**" —
and the second half is structural, not visual. The pager's current styling is
position-addressed: link spans, jump-hint capsules, dangling marks, the search corpus,
`:line` navigation, the trail's scroll restore, and `--plain` output are all keyed off
character offsets into `PagerSection.plain_text`. So the design question is:

> How do we add a second styling producer such that **no producer can ever change a
> single character of the document**?

The pager already fights for this invariant today — `document.py:185`
(`_restore_trailing_newlines`) exists solely because `Text.from_ansi` may drop a
trailing newline. The syntax layer must be held to the same standard, structurally.

## 2. What exists today (verified)

The pager styles text through five layers, all offset-respecting:

| # | Layer | Where |
|---|-------|-------|
| L1 | Producer ANSI | `document._body_to_text` → `Text.from_ansi` (bead detail, `git show`, colorized stdin). `cli_detail.py:47` states the additive-ANSI invariant in writing. |
| L2 | Link target accents | `_labels.render_section_with_labels` — slices `body_text` (Rich slices retain spans) and accents only the target |
| L3 | Key capsules | `_labels._label_prefix` — the **only** thing that inserts characters, and only into a throwaway render `Text`, after all offset consumers ran |
| L4 | Search matches | `vim_search_controller._render_overlay` |
| L5 | Chrome | `_chrome.py` — separate widgets, no body-offset interaction |

Other foundations that make this feature additive rather than invasive:

- `_ensure_body` (`_screen_body.py:98`) composes the body **synchronously**, cached by
  width per `tui_perf` rule 8; `compose_body` already does a full `render_lines` of the
  document at every width change. Highlighting is a proportionate cost, not a new class
  of cost.
- SASE has already solved span-based semantic highlighting once, frontend-agnostically:
  `src/sase/xprompt/highlight.py` (`HighlightSpan(start, end, role)`, explicit
  `_ROLE_PRECEDENCE`, sweep-line flattening, fail-open `try/except → ()`, caps
  `MAX_HIGHLIGHT_BYTES = 80_000` / `MAX_HIGHLIGHT_LINES = 1_200`) and
  `src/sase/xprompt/highlight_theme.py` (`HighlightStyle` with `.rich_style` **and**
  `.ansi_sgr` projections, colors derived from the pinned flexoki theme, `neutral_code`
  deliberately recessed). The pager should be the second consumer of this pattern, not
  the inventor of a rival one.
- `frontmatter_syntax.py` already has the right Markdown behavior: an offset-preserving
  composite lexer (YAML frontmatter + Markdown body) whose `get_tokens_unprocessed`
  yields corrected original-text offsets.
- The original pager design doc (`research:202608/link_traversing_pager`, §7) sets the
  budget: *"First chrome paint never waits on file content, syntax highlighting, or
  graph enrichment. Scrolling and label handling do no I/O."*

## 3. The measurement that eliminates most options

Verified on this host (Rich 14.3.3, Pygments 2.19.2):

**`rich.syntax.Syntax.highlight()` silently rewrites the document.** No trailing
newline → one appended; CRLF → normalized to LF; empty string → `"\n"`; tabs → expanded
to spaces. Every one of these desyncs offsets: capsules paint at wrong characters,
`y<label>` copies the wrong ref, `E<label>` opens the wrong line, search scrolls to the
wrong row. `rich.markdown.Markdown` reflows entirely. Both are disqualified as-is.

**Pygments `get_tokens_unprocessed()` is offset-exact.** It yields
`(char_offset, token, value)` triples where `code[i:i+len(v)] == v` for every token —
verified across no-trailing-newline, CRLF, empty, tabs, malformed syntax, and
astral-plane Unicode. One precision the lead adds to researcher B's account: the
mutations live in `Lexer.get_tokens()`'s preprocessing step, which
`get_tokens_unprocessed()` bypasses — offsets are exact even with default lexer kwargs.
Still construct lexers with

```python
get_lexer_by_name(name, stripnl=False, ensurenl=False, stripall=False, tabsize=0)
```

as defense-in-depth (a future refactor to `get_tokens()` or Rich `Syntax` would
otherwise reintroduce every mutation with no test failure below), and keep the R1
property test (§6) as the actual guarantee.

**The invariant is sufficient.** Researcher B wired a throwaway prototype
(`PagerSection.syntax` field, spans under the existing layers) and ran the pager's full
suite plus CLI and ACE callers: 140 passed, zero test changes. If plain text is
invariant, nothing in the pager notices a new styling layer.

**Engine comparison** (all four alternatives rejected):

| Engine | Fatal flaw |
|--------|-----------|
| Rich `Syntax` renderable in `body` | Mutates text; label composition also flattens opaque renderables and discards their styles |
| Rich `Markdown` | Reflows; destroys offsets and the editor-like source contract |
| Read-only Textual `TextArea` | Owns cursor/scroll/keys; small fixed language set; can't host the multi-section Rich body plus inserted capsules — a style feature becomes a pager rewrite |
| Shell out to `bat`/`pygmentize` | Subprocess on the render path (`tui_perf` rule 1); no offset contract; restores exactly the dependency `docs/pager.md` advertises removing |
| Textual tree-sitter (already in repo for prompt fences) | Only 15 grammars — **no `diff`**, which the pager explicitly supports; its Markdown grammar is block-only (no inline emphasis/code/links) and Markdown is SASE's dominant content type. A tree-sitter/Pygments hybrid doubles the token vocabulary and theme and makes two files in one document look like different products |

Pygments' Markdown lexer, by contrast, **nests fenced code blocks through the inner
lexer** (verified: `def`/function-name/number tokens inside a ` ```python ` fence) —
the single highest-value Markdown behavior for SASE plans, research, and memory notes,
for free. One engine, Pygments.

## 4. Recommended design

### 4.1 Declared layer stack, three tested rules

```text
L0  characters       the document. NO layer may insert, delete, reorder, or
                     normalize a character. (Capsule insertion into the derived
                     render Text stays the single, existing exception.)
L1  producer ANSI    Text.from_ansi spans (bead show, git, colorized stdin)
L2  syntax           NEW — Pygments role spans, only when L1 is empty
L3  semantic         RESERVED for the agent-metadata semantic overlay plan
L4  link             target accent, dangling dim, key capsules   ← strongest
L5  search           match / current-match overlays
```

- **R1 — Text invariance.** `styled.plain == section.plain_text` byte-for-byte, and
  every token satisfies `code[i:i+len(v)] == v`. Property-tested over CRLF, tabs,
  no-trailing-newline, empty, multiple trailing newlines, wide/astral Unicode.
- **R2 — L2 yields to L1.** If the body contains `\x1b`, the syntax layer emits
  nothing. We never fight a producer that already chose its colors; bead documents are
  untouched by construction. (Belt-and-suspenders — adapters only declare a language on
  raw-source sections anyway.)
- **R3 — L4 wins.** A character inside a link target renders with the link style
  regardless of syntax role, asserted by resolving effective Rich styles at
  representative offsets (the discipline `plan:202608/pager_hint_highlight_boundary.md`
  already established after the capsule-bleed bug). One deliberate nuance: dangling
  links are `dim` (attribute-only), so dangling-over-code shows the syntax color,
  dimmed — correct and prettier; pin it with a test.

This adopts the precedence sentence the agent-metadata highlighting plan already wrote:
*the link layer is the strongest local affordance and is applied last.*

### 4.2 Modules — mirror the house pattern

```text
src/sase/pager/language.py      resolve_language(...) -> str | None   (pure, no I/O)
src/sase/pager/syntax.py        syntax_spans(text, language) -> tuple[HighlightSpan, ...]
src/sase/pager/syntax_theme.py  role -> HighlightStyle (flexoki-derived, cached)
```

`syntax.py` mirrors `xprompt/highlight.py` exactly: closed role vocabulary, caps
checked before any work, fail-open, char offsets, deterministic flattening. Lexers are
cached per language (`@lru_cache`) and constructed with the four safety kwargs, with a
comment saying they are load-bearing. Fold Pygments' ~40 token types into a small
closed set (~14 roles):

```text
code.keyword  code.type     code.function  code.constant  code.number
code.string   code.comment  code.decorator code.error
md.heading    md.emphasis   md.code
diff.inserted diff.deleted
```

Everything else — `Name`, `Operator`, `Punctuation`, plain `Text` — emits **no role**
and renders as body foreground. Fewer roles is the core beauty decision (§4.4).

Markdown routes through a pager-owned instance of `FrontmatterMarkdownLexer` (reuse the
class from `frontmatter_syntax.py`; do **not** reuse the module singleton, which is
configured `ensurenl=True, tabsize=4` for its Rich-Syntax consumers). This gives YAML
frontmatter + Markdown body + nested fences, all offset-preserving.

### 4.3 Language resolution — adapter-declared, conservative

`PagerSection` gains an optional field (language identity plus its source), declared by
the adapter at construction time — never sniffed at paint time, and never inferred from
`kind` or title alone. This is presentation metadata; existing constructors default to
`None`, so every current caller is behaviorally unchanged. Precedence:

1. `sase pager -s/--syntax <alias|none>` CLI override (invalid alias → clear CLI error
   before the app starts).
2. Explicit adapter declaration from semantic provenance: `PagerOrigin.DIFF` → `diff`;
   Markdown-bodied artifact kinds (`plan:`, `research:`, memory notes) → `markdown`.
3. SASE override table, then `pygments.lexers.get_lexer_for_filename(name)`.
4. Shebang sniff for extensionless files only.
5. Stdin: content sniff for **diff only** (`diff --git` / `^--- a/` / `^@@`) — the one
   stdin case worth sniffing, and what makes `git show | sase pager` beautiful. A
   filename-looking `--title` may serve as a filename hint.
6. Otherwise `None` → today's rendering exactly.

**Never call `pygments.lexers.guess_lexer()` on content.** Verified failure modes:
content-only guessing maps `Makefile` → T-SQL and `app.tsx` → GDScript. A confidently
wrong lexer is worse than plain text.

The override table is required, not optional — verified against this repo's inventory,
`get_lexer_for_filename` misses or mis-maps: `*.tcss` → css, `Justfile` → make,
`uv.lock` → toml, `*.j2`/`*.jinja` → jinja, `*.xprompt` → markdown, `README*` →
markdown, `*.sql` → sql (Pygments defaults to Transact-SQL), `.gitignore`/`.env` →
text/bash. Leave `*.log` and `*.sase` deliberately unmapped — ProjectSpec deserves a
native semantic highlighter later (the `sase-nvim` grammar is prior art), not a
misleading YAML/INI costume. SASE already has near-identical extension maps in several
panels; `resolve_language` should become the shared resolver, with callers migrated
opportunistically.

**Rust-core note:** the renderer (Pygments, Rich styles) is presentation and stays in
Python. Language *identity* is arguably domain — keep `resolve_language` one pure
I/O-free function so promoting it into `sase-core` is mechanical if a second frontend
appears.

### 4.4 Theme: flexoki-derived, inside a measured contrast band

Derive the role palette from the pinned flexoki theme via
`highlight_theme.HighlightStyle` — not Rich's `ansi_dark` (see §9, disagreement 2).
The pager's primary affordance is finding and pressing links; syntax is structure, not
a call to action. Measured WCAG contrast against flexoki's background already shows the
right three-tier hierarchy — body text 18.6, link accents 6.4–13.8, flexoki role hues
2.9–5.5 — except two raw roles (`primary` 2.93, `error` 2.99) fall below legibility. So
blend each chromatic role toward the foreground (exactly `derive_argument_color()`'s
mechanism) until it lands in a band, and **make the band an automated test**:

> Every chromatic syntax role satisfies
> `4.5 ≤ contrast(role, background) ≤ min(link-accent contrast)` (≈ 6.4).

That one assertion keeps the feature beautiful after ten contributors; "use restrained
colors" does not. Supporting rules:

- Comments: `dim italic`, no color. Headings/emphasis: `bold`/`italic`, no color.
  Inline/fenced code base: `neutral_code` (achromatic — no hue competition).
- **Reserve the SASE accent hues** (gold capsule, file-orange, bead-violet,
  patch-teal, agent-blue, external-red) for the link layer exclusively.
- No line-number gutter, no per-file border, no opaque background, no "plain text"
  badge — *absence costs nothing* (`_chrome.py`'s stated rule).
- One discoverability affordance: a dim language chip in the subject line (`· py`,
  `· md`, `· diff`), three cells, dropped first under narrow-width truncation. It makes
  the guess visible and honest.
- **Pin flexoki on `SasePager`** (one line). Verified gap: ACE pins
  `ACE_THEME_NAME` but the standalone app runs on `textual-dark`, so a flexoki-derived
  palette would be theme-mismatched in exactly the entry point most people use.

### 4.5 Where and when the layer applies

Not in `PagerSection.__post_init__`: `--plain`/redirected output builds the document
and then dumps `plain_text` (eager lexing would be pure waste), the theme isn't known
at construction, and the frozen section is a document model, not a view.

Apply it during body composition (`_layout._section_renderable` /
`render_section_with_labels`), against a styled base `Text` cached by
**(content digest, lexer identity, theme signature)** — deliberately width-independent,
so resizes and scrolls never re-lex and swapping the style layer never changes
wrapping, offsets, or trail anchors.

**Synchronous under the caps, by choice** (see §9, disagreement 3): adopt the house
caps (80 KB / 1,200 lines) plus a max-line-length guard (an 80 KB single-line minified
blob passes both caps and can pathologically stress a regex lexer). Measured worst case
at the cap is ~70 ms of lex+span work, under the full-document `render_lines` the pager
already performs synchronously in the same call; typical files are single-digit
milliseconds. The design doc's budget is honored where it binds: chrome paints first,
and scroll/label/keypress paths do no lexing (the cache guarantees it). If tracing ever
shows the sync path breaching pager latency budgets, the escape hatch is the
already-established progressive pattern — paint plain, lex in `spawn_pump_free_task`,
repaint — deferred as a follow-up, not built speculatively.

**Above the caps: skip syntax, keep every character.** The pager must never truncate
searchable/copyable text the way panel-oriented `lazy_renderable()` deliberately does.
At most a quiet one-time footer note ("large file: syntax skipped").

### 4.6 CLI and config surfaces

| Surface | Behavior |
|---------|----------|
| `-s/--syntax <alias\|none>` *(new)* | Force or suppress the language for raw sections; short alias per `cli_rules` |
| `--color never` | Verified currently parsed-and-dead in `parser_pager.py:37` — wire it to suppress the syntax (and ideally accent) layers; this feature is its natural job |
| `--plain` / non-TTY | Unaffected — byte-identical to today by construction |
| `pager.syntax: auto\|never` *(new config)* | A `default_config.yml` config field, **not a feature flag** (a permanent user choice, per the `sase_flags` rule); a `beta` flag only if this lands as a multi-phase epic with an exposed intermediate |
| `sase bead show` | No language ever declared; authored ANSI preserved (R2 twice over) |
| Directory/media/binary cards, unknown types | Plain, no ornament |

`--wrap` is also parsed-and-dead — adjacent but out of scope; file a task bead.

## 5. Failure modes, each closed

| Failure | Closure |
|---------|---------|
| Lexer mutates text → labels/copy/editor/search desync | R1 property test + `get_tokens_unprocessed` + safety kwargs, commented load-bearing |
| Lexer raises on malformed input | Fail-open `try/except → ()`; the pager must never fail to display a file it displays today |
| Unknown extension / ambiguous type | `None` → exactly today's rendering |
| Producer ANSI vs syntax fight | R2 suppression |
| Syntax swallows a link or capsule | R3 resolved-style assertions at offsets |
| Huge file freezes the TUI | Byte + line + max-line-length caps before any lexing; full text always retained |
| Theme switch / light terminal | Theme signature in the cache key; flexoki pinned on `SasePager` |
| Contrast drift over time | The §4.4 contrast-band test |
| Stale/wrong recolor after follow | Cache keyed by content digest; document identity checked on apply |

## 6. Verification plan

- R1/R2/R3 as automated tests (property test corpus per §4.1).
- Contrast-band assertion over every chromatic role.
- ANSI-overlap test: an ANSI-colored range keeps its color; unstyled neighbors get
  syntax colors (relevant if R2 is ever relaxed).
- Link spans, labels, copied values, `E` jump lines identical before/after.
- Resolver table test: the §4.3 override rows plus the standard extensions, shebangs,
  and the diff sniff; content-only guessing asserted absent.
- Large files fully searchable, untruncated; resize never re-lexes (lexer call-count
  assertion).
- `--plain`/redirected output byte-identical to pre-feature output.
- PNG goldens (python, markdown+frontmatter, diff, link-inside-string, plain-unknown,
  active search) at the pager suite's two sizes, **plus a pixel-equality assertion that
  a no-language document renders identically to today**.
- **Testing trap (verified):** Textual's SVG export emits no `font-weight`, so
  bold/italic-only roles (`md.heading`, `md.emphasis`, `code.comment`) are invisible in
  PNG goldens — assert those semantically by resolving effective Rich styles at
  offsets. PNGs remain right for color and layout.
- Perf: existing pager latency budgets hold; scroll/keypress paths show zero lexing.

## 7. Phasing

1. **Invariant + plumbing.** `syntax.py`, `language.py` + override table, optional
   section language field, composition-path application with the
   content/lexer/theme cache, caps + guards, R1/R2/R3, flexoki pin on `SasePager`.
   End state: zero visual change when no language resolves; every existing test passes
   unchanged (already demonstrated empirically by B's prototype).
2. **Beauty.** Flexoki-derived `syntax_theme.py` on `HighlightStyle` (free `.ansi_sgr`
   projection for any future non-TUI use), contrast-band test, language chip, PNG
   goldens + semantic style assertions.
3. **Surfaces.** `-s/--syntax`, wire `--color never`, `pager.syntax` in
   `default_config.yml`, `docs/pager.md` update.

**Deferred as task beads, deliberately:** styled search corpus (pressing `/` today
flattens the body to an unstyled corpus — with syntax on, search will visibly drain
color; the controller is shared with ACE's zoom panel, so fix it as a follow-up with an
optional styled-base hook, decided now rather than discovered in a screenshot);
progressive highlighting above the caps; line-number gutter (inserts characters —
needs a separate render structure); dead `--wrap`; native `.sase` ProjectSpec lexer;
promoting `resolve_language` into `sase-core` if a second frontend appears.

## 8. Recommended solution

**Add a syntax layer to the pager's render stack: adapter-declared language identity on
`PagerSection`, Pygments `get_tokens_unprocessed` folded into a closed ~14-role
vocabulary in the exact shape of `sase/xprompt/highlight.py`, themed from flexoki
inside a measured contrast band, applied synchronously under the house caps in the body
composition path with a width-independent content/lexer/theme cache, placed below the
link layer in a declared precedence table, and failing open to today's rendering on any
ambiguity, size, or error.** Ship `auto` by default with `-s/--syntax` and
`pager.syntax` as escape hatches.

It is **intuitive** because files just gain color, everything already styled stays
exactly as it is, and the subject-line chip says what the pager decided. It is
**reliable** because "keep the current highlighting intact" becomes a structural
guarantee — a text-invariance property test plus a tested layer-precedence table —
rather than a hope, using a pattern SASE has already shipped once. It is **beautiful**
because the palette is derived from the house theme inside an enforced contrast band
that keeps content brightest, link affordances next, and structure quietest — and the
band is a test, so it stays beautiful.

## 9. Where the reports disagreed, and the ruling

| # | Question | A said | B said | Ruling |
|---|----------|--------|--------|--------|
| 1 | Highlight mechanism | `Syntax.highlight()` with a configured lexer + exact-equality check, discard on mismatch | Raw `get_tokens_unprocessed` → role spans, house pattern | **B**, with A's exact-text check retained as the R1 test. B's offsets are correct by construction (lead-verified even with default kwargs); A's check is a runtime guard that silently loses highlighting on mismatch, and Rich's theme bypasses the closed role vocabulary that the beauty rules need. A's frontmatter-composite-lexer reuse is adopted into B's mechanism. |
| 2 | Theme | Rich `ansi_dark`/`ansi_light` (terminal palette, no opaque background) | Flexoki-derived roles + contrast-band test | **B**. Once flexoki is pinned on `SasePager` (a gap B found and the lead verified), deriving from the house theme is strictly more consistent with ACE and the xprompt highlighter, and the contrast band gives A's "quiet, lower-salience than links" goal an enforceable form. |
| 3 | Sync vs lazy | Lazy pump-free worker, plain first paint, generation checks | Synchronous under caps in composition | **B for v1**, lead-verified: the design doc's budget line governs *chrome* paint and scroll paths, both preserved; composition is already synchronous and strictly heavier than capped lexing; the cache makes it once-per-content. A's worker (with its search-overlay and generation interplay) is the deferred escape hatch if measurement ever demands it. |
| 4 | ANSI + syntax coexistence | Layer existing styles over syntax; ANSI wins per attribute | Suppress syntax entirely when `\x1b` present | **B** (R2) for v1 — simpler, no real v1 case needs mixing since adapters only declare languages on raw sections. A's layering is the documented relaxation path. |
| 5 | Language chip | Defer (truncation risk) | Dim `· py` chip in the subject | **B**, in the beauty phase, with A's concern honored: the chip drops first under narrow-width truncation. |
| 6 | Caps source | `lazy_syntax.py` (64 KB/1,500; md 24 KB/600) | `xprompt/highlight.py` (80 KB/1,200) | **B's**, since the module mirrors that file's shape — plus B's max-line guard, plus A's rule that over-cap files keep their full text. |

## 10. Key references

| Concern | Location |
|---------|----------|
| Body → `Text`, trailing-newline restore | `src/sase/pager/document.py:175,185` |
| Label layer, capsule insertion | `src/sase/pager/_labels.py:197,249` |
| Composition seam for L2 | `src/sase/pager/_layout.py:152` |
| Width-cached rebuild | `src/sase/pager/_screen_body.py:98` |
| Search corpus flattening | `src/sase/pager/_layout.py:131`, `src/sase/ace/tui/widgets/vim_search_controller.py:379` |
| Adapter seam | `src/sase/pager/adapters.py:35` |
| Dead `--color`/`--wrap` | `src/sase/main/parser_pager.py:37,62` |
| House span/role/precedence pattern | `src/sase/xprompt/highlight.py` |
| House theme derivation + ANSI projection | `src/sase/xprompt/highlight_theme.py` |
| Frontmatter composite lexer | `src/sase/ace/tui/util/frontmatter_syntax.py` |
| Missing theme pin | `src/sase/pager/app.py` (vs `src/sase/ace/tui/actions/_state_init_runtime.py:71`) |
| Pager design budgets | `research:202608/link_traversing_pager/link_traversing_pager.md` §7 |
| Layer-bleed precedent + test discipline | `plan:202608/pager_hint_highlight_boundary.md` |
| Precedence-contract precedent | `plan:202608/agent_metadata_semantic_highlighting.md` |
