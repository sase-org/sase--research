# Smack as a name for sase macro invocations (`#foo`): research and recommendation

**Researcher:** mus · **Date:** 2026-10-05 · **Suffix:** `__mus`
**Independence:** conducted independently. I did not locate, open, read, or
consult any peer report from this swarm (`__cdx` / `__cld` / `__grk` / `__gem`),
their transcripts, or summaries. Shared input material, external sources, and
unrelated prior research (notably the `xprompt → macro` verdict) were used
independently. I listed the output directory only to pick a non-colliding
filename and left all peer files alone.

## Verdict up front

Do not adopt "smack". Do not add a `smack` glossary strand. Do not rename the
"raw prompt" to "smack prompt".

The real gap is narrower than the proposal assumes: SASE already has a dominant,
precise term for a `#foo` use-site — **macro reference** — used consistently in
code (`src/sase/macro/processor.py`, `src/sase/history/prompt_metadata.py`,
`src/sase/content_layout.py`) but never defined in the glossary. Standardize on
that, add one strand named **Macro Reference** (not "smack") only if the lead
judges a strand warranted, tighten the existing **Macro** strand to point at it,
and document the prompt lifecycle (authored/unexpanded → expanded/launch)
instead of renaming "raw prompt".

## What was asked

1. Coin "sase macro invocation" aka **"smack"** (rationale offered: the "kay"
   sound inside "invocation") as the talk-about name for `#foo`-style macro
   invocations.
2. Add a new glossary memory-web strand for the term.
3. License new compounds such as **"smack prompt"** for the "raw prompt".

Requested output: research helping decide the best implementation, a general
critique, justified requirement adjustments, and a recommended solution.

## Method and sources

- `sase memory read macros.md` + `glossary:macro`, `glossary:macro-memory`,
  `glossary:stitch` — macro invocation grammar, memory-macro namespacing, and
  the Macro strand's current two-sentence shape ("Formerly called an xprompt.
  Triggered with `#foo` in agent prompts.").
- `sase memory read glossary:macro-workflow glossary:macro-part
  glossary:macro-swarm glossary:prompt-stash` and the full-glossary read —
  macro-family scope and strand style.
- `sase memory read glossary:strand-keyword glossary:artifact-reference` and
  `src/sase/memory/web/models.py` (`MemoryStrand`: `keyword`, `aliases`,
  `summary`, `body`) plus `sase memory web show glossary` — strand
  keyword/slug/alias conventions (e.g. keyword `Macro`, slug `macro`, aliases
  `xprompt`; keyword `Macro Memory`, aliases `memory file · sase memory`).
- `docs/macros.md` (notably Renamed-from-xprompts, Reference Syntax, Raw Prompt
  Placeholders) and prior verdict
  `sase/repos/research/202610/xprompt_to_macro_naming_verdict.md` (2026-10-02,
  epic `sase-1eq`).
- Code searches for `macro invocation|macro reference|macro call|macro
  expansion`, `raw prompt|raw submitted prompt|expanded prompt`, and `smack`
  across `src/sase`, `docs`, and `sase/memory`.
- `sase memory read lint_and_test.md` to scope verification (report lives under
  `sase/repos/research/`, excluded from the `just check` gate).

No peer-report content was consulted. All repository claims below were observed
directly in this session.

## Background: what the vocabulary actually says today

**A macro is the definition; `#foo` in a prompt is already named.** The Macro
strand defines the *definition* ("Defined in a `sase/macros/` directory …").
The *use-site* already has a settled name in code: **macro reference**.

- `src/sase/macro/processor.py`: "Macro reference processing for prompts";
  "Pattern to match macro references: `#name`, `#name(`, `#name:arg`, `#name+`";
  "Process macro references in the prompt"; "Find all macro references".
- `src/sase/macro/_parsing_shorthand.py`, `_trace.py`, `_directive_values.py`,
  `cli_show_resolve.py`, `macro_sources.py`: "macro references" throughout.
- `src/sase/history/prompt_metadata.py`: "Return deduplicated macro references
  with arguments preserved."
- `src/sase/content_layout.py`: "the canonical `skill/<name>` macro reference",
  "the canonical `memory/<stem>` macro reference".
- `src/sase/macro/naming.py`: "whether *name* matches the inline macro
  reference grammar".
- "Macro calls" appears too (`workflow_validator.py`: "Validates macro calls
  (required args …)"), but "reference" dominates and covers both bare `#foo`
  and parameterized `#foo(args)` / `#foo: text` forms.

So the premise "macro invocations have no distinct name" is only half true:
they have *two or three* names (`reference` dominant, `call`/`expansion` minor)
and no glossary definition pinning the distinction. That is a
standardization problem, not a coinage problem.

**"Raw prompt" already means three different things**, and the proposal touches
all three without distinguishing them:

1. The whole pre-expansion authored text: `directives.py` ("`prompt`: The raw
   prompt text"), `prompt_inputs.py` ("The raw submitted prompt (frontmatter +
   body)"), `launch_hold_preview.py` ("a raw submitted prompt"), the
   `AGENT RAW PROMPT` artifact section and TUI preview `RAW PROMPT` tab.
2. The persisted agent-directory file: `legacy_xprompt_names.py`
   ("raw prompt, accepting the pre-rename name", "raw prompt path"),
   `_mobile_agent_state.py` ("Return the raw prompt path").
3. Live `<label>` tags inside a draft: `docs/macros.md` § Raw Prompt
   Placeholders ("sase's TUI recognizes valid single-line `<label>` tags as raw
   placeholders … submitting a prompt … opens Fill in this prompt … raw
   placeholders first and then any frontmatter-declared inputs").

There is also an established contrast pair in `src/sase/agent/`: *submitted*
prompt vs *already-expanded* prompt ("Each input must be one per-segment,
already-expanded prompt", "Build a serialized typed launch plan from an
already expanded prompt", "One expanded prompt segment"). Any rename must
preserve that lifecycle, not flatten it.

**"Smack" has zero existing footprint.** A tree-wide case-insensitive search
for `smack` returned only an unrelated `pycparser` comment (`smack: 3` in a
pragma-lexer example) inside `.venv`. No collision — but also no demand signal.

## Critique 1: "smack" is a bad coinage for this concept

Apply the same scorecard the `xprompt → macro` verdict used (understanding
over tooling, five grammatical slots, sibling-syntax fit, collisions):

1. **The acronym does not parse.** "Sase macro invocation" should abbreviate to
   SMI, not "smack". The offered derivation (S + mack, with "kay" from
   *invocation*) is folk etymology: *invocation* is spelled with a `c`
   (`/ˌɪnvəˈkeɪʃən/`), not `ck`, and contributes no `m` or `a`. Readers cannot
   reconstruct the expansion from the word, so the name is opaque on first
   sight — the exact failure mode that sank `xprompt` ("the `x` is
   undocumented").
2. **It says nothing about mechanism, owner, or timing.** `macro` won because
   it names the textbook expansion mechanism and the host-before-launch
   contract (macro: SASE resolves before launch; directive: SASE controls;
   skill: agent loads at runtime). "Smack" carries none of that. A newcomer
   guessing from "smack" gets no hint of `#`, expansion, or preprocessing.
3. **Connotations and collisions are worse than "macro", not better.** *Smack*
   is a common English word (a hit; lip-smacking; drug slang; "smack talk"),
   an XMPP client library (Smack), and a noisy everyday verb. The prior verdict
   already marked `macro` down for grep noise and unownable web search;
   "smack" repeats both defects while adding an aggressive/undignified tone
   ("smack the prompt", "smacks") that `macro` avoided. Spoken in a meeting or
   via TTS it invites snickering; written, it reads as a joke name in a
   subsystem that just paid a full epic (`sase-1eq`) to sound professional.
4. **It fails the grammatical-slots test the name must pass.** Count noun ("a
   smack"? "three smacks"?) already sounds like blows, not references. As a
   CLI namespace (`sase smack …`), config key, directory, or modifier ("smack
   catalog", "smack swarm"?) it has no natural reading — and SASE just retired
   a whole family of such mismatches. "Macro reference" passes every slot
   because it reuses the existing `sase macro …` namespace.
5. **"Invocation" is the wrong head noun.** In SASE, `#foo` does not *invoke*
   at runtime; it *refers* to a definition that the host *expands*
   deterministically before launch (alias → protect → parse → lookup → render
   → substitute, recursing). `processor.py`'s choice of "reference" is the
   accurate one and parallels the sibling `Artifact Reference` (`@kind:arg`)
   strand exactly: `#` macro references cite-and-expand; `@` artifact
   references cite-and-expand; `%` directives control. "Invocation" belongs to
   the workflow/agent-launch layer (`mentor.py` / `crs.py` "macro invocation"
   builders generate a top-level launch string), not to every inline `#foo`.
   Minting "invocation" as the generic word blurs the reference/expansion/
   launch distinction the codebase currently keeps (mostly) straight.
6. **Timing: it churns the vocabulary weeks after the macro rename landed.**
   The rename epic touched docs, memory, skills, CLI help, completion, and the
   LSP, with a `legacy_xprompt_syntax` sunset flag still in flight. Every new
   synonym multiplies that migration surface (docs, strands, error strings like
   "Unknown macro reference(s): `#foo`", TUI labels, skill text). A cute
   nickname is not worth a second churn wave.

None of this denies the underlying itch: saying "the `#foo` thing on line 3"
is awkward. But the fix is to promote the accurate term the code already uses,
not to mint an opaque one.

## Critique 2: a new strand is not yet justified — and "smack" is the wrong keyword regardless

A glossary strand is a maintenance commitment: keyword + slug + aliases +
summary + body, roster placement, implicit-link fan-out (glossary uses
`link_reference: implicit`, so every mention becomes a link), `sase memory
web show` index churn, `sase memory init` / `sase validate` / `just check`
fallout, and AGENTS.md-adjacent instruction weight. The bar from prior
practice is a *demonstrated confusion* the strand resolves.

The demonstrated confusion here is real but small: *reference* vs *call* vs
*expansion* vs *definition* drift across ~20 call sites, and the Macro
strand's single "Triggered with `#foo`" sentence doing triple duty for the
definition, the use-site, and the expansion. A strand can fix that — but only
if its keyword is the term the code uses. A `smack` strand would instead:

- enshrine a synonym nobody writes yet, guaranteeing every future doc edit a
  "smack vs macro reference?" style choice;
- double the implicit-link surface (`macro`, `smack`, `macro reference` all
  linking overlapping sentences);
- teach agents a word that appears nowhere in code, errors, CLI help, or docs,
  so model-generated instructions and model behavior diverge.

If a strand is added at all, it should be **Macro Reference** (slug
`macro-reference`, keyword `Macro Reference`), with `macro call`, `macro use`,
and — only as a migration pointer, then dropped — `macro invocation` as
aliases. Its one-sentence contract: *a `#name…` occurrence in authored prompt
text that SASE parses, looks up, renders, and substitutes before launch; the
definition is the macro, the occurrence is the reference, the output is the
expansion.* The existing Macro strand then shrinks to definitions and gains a
pointer sentence. That is a two-strand edit with zero new vocabulary.

My adjustment: **defer even that strand unless the lead sees agents actually
confusing reference/definition/expansion in the wild.** The cheaper fix —
one paragraph in `docs/macros.md` § Reference Syntax plus normalizing new code
and error strings to "macro reference" — may be sufficient, per the
corpus-before-mechanism principle. Do not pre-build vocabulary for a confusion
we have not measured.

## Critique 3: "smack prompt" for "raw prompt" — reject outright

This is the most damaging third of the proposal, for three independent
reasons:

1. **Part-for-whole category error.** A prompt contains zero or more macro
   references plus prose, refs, tags, and directives. Naming the whole
   container after one optional part ("smack prompt" = prompt containing
   smacks? prompt that *is* a smack? the expansion result?) guarantees
   ambiguity. The existing lifecycle terms — *submitted/authored/unexpanded*
   prompt (input) vs *expanded/launch* prompt (output) — name the whole at
   each stage. "Smack prompt" names neither stage and fits neither.
2. **It collides with all three established "raw" meanings at once.**
   `AGENT RAW PROMPT` section headers, `PREVIEW_TAB_LABEL = "RAW PROMPT"`,
   `get_raw_xprompt_content`, "raw submitted prompt" in launch-guard code, and
   § Raw Prompt Placeholders (`<label>` tags) would each need a judgment call,
   and a bulk rename would destroy the submitted-vs-expanded distinction that
   launch validation, prompt history, and the TUI preview depend on. The blast
   radius is dozens of identifiers, user-visible strings, and docs sections —
   far beyond one strand file.
3. **It forecloses the useful compound.** If "smack prompt" means "raw
   prompt", what do we call "a prompt containing macro references" or "the
   prompt after smack expansion"? The proposal spends the compound on the least
   useful meaning. Keep `raw / submitted / unexpanded` for the input,
   `expanded / launch` for the output, and if a compound is ever needed,
   `macro-containing prompt` or `unexpanded prompt` says exactly what it
   means.

## Alternatives considered

| Candidate for the `#foo` use-site | Fate |
| --- | --- |
| **macro reference** (code-dominant) | **Recommend.** Accurate (cite-and-expand), parallels `artifact reference`, zero new vocabulary, matches errors/CLI/docs. |
| macro call | Tolerable for parameterized `#foo(args)` but wrong for bare `#foo`; keep as alias only. |
| macro expansion / expanded text | Names the *output*, not the use-site. Keep for the output stage. |
| macro use / macro occurrence | Accurate but unattested in tree; "occurrence" is clunky in prose. Alias at most. |
| macro tag | Taken: `+project` project tags are the "tags"; `#` is not called a tag anywhere. Reject. |
| hash-ref / pound-ref / octothorpe invocation | Sigil-talk; inaccessible, locale-fragile (`#` = hash, pound, sharp, octothorpe), and "ref" collides with `@ref`. Reject. |
| smack / sase macro invocation | Opaque, connoted, ungrammatical in slots, churns post-rename tree. Reject. |
| smack prompt for raw prompt | Category error with large blast radius. Reject. |

On the prior verdict's "macro-last for kinds" refinement (prefer *swarm
macro* over *macro swarm*): the use-site term should stay **macro reference**
("reference" is the head noun, "macro" the modifier — the sanctioned
"of-macros" order, like *macro catalog*), not "reference macro".

## Recommended solution (adjusted requirements)

1. **Drop "smack" entirely.** No strand, no alias, no compounds. Record the
   rejection and its reasons in this report so the next coinage attempt starts
   from evidence, not taste.
2. **Standardize on "macro reference" for the `#foo` use-site** in all new
   writing (docs, strands, error strings, TUI labels, skill text). Leave
   existing code identifiers alone; normalize prose first.
3. **Defer the new strand; if added, name it Macro Reference**, not Smack:
   slug `macro-reference`, keyword `Macro Reference`, aliases `macro call ·
   macro use` (and `macro invocation` only transiently as a redirect-then-drop
   if the term has already spread by implementation time). One-sentence
   contract distinguishing definition (the macro) / reference (the `#…`
   occurrence) / expansion (the substituted output) / launch (directives +
   expanded segments → agents). Cross-link `glossary:macro`,
   `glossary:artifact-reference` (the `@` parallel), and `macros.md` §
   Reference Syntax. Validate with `sase memory web show glossary
   macro-reference -b`, `sase memory init`, `sase validate`, and the normal
   `just check` path — no code changes, since strands are data.
4. **Keep "raw / submitted / unexpanded prompt" and "expanded / launch
   prompt".** Add (or keep) one lifecycle paragraph in `docs/macros.md`
   near the top: *authored prompt (with macro references, directives, refs)
   → expansion → expanded prompt → launch.* Optionally note the three "raw"
   senses (§ placeholders vs artifact section vs file) where § Raw Prompt
   Placeholders already lives. No identifier or TUI-string renames.
5. **Measure before minting.** If reference/definition confusion persists after
   (2)–(4), file it as a task bead with quoted agent-confused evidence; *that*
   evidence — not this proposal — should trigger the Macro Reference strand.

## If the lead overrides and wants "smack" anyway (least-bad implementation)

- Keyword `Smack`, slug `smack`, alias `sase macro invocation` only; never
  alias the bare `macro reference` to it (that would hijack the established
  term). Body must state it is *slang for* a macro reference and defer all
  semantics to `glossary:macro-reference`, which must then exist first.
- Do not rename any "raw prompt" concept; at most document "smack prompt" as
  deprecated-on-arrival slang for "unexpanded prompt containing macro
  references", and do not touch identifiers or TUI strings.
- Expect and budget for: `sase memory init` regeneration, `sase doctor` /
  `sase validate` web-validation fallout, `just check` (lint + scoped tests),
  LSP/completion additions if `#`-site completion should display the word,
  and a docs-wide "smack (slang)" pass. This cost is precisely why the
  recommendation above avoids it.

## Sources (observed this session)

- `sase memory read` outputs for `macros.md`, `glossary:macro`,
  `glossary:macro-memory`, `glossary:stitch`, `glossary:macro-workflow`,
  `glossary:macro-part`, `glossary:macro-swarm`, `glossary:prompt-stash`,
  `glossary:strand-keyword`, `glossary:artifact-reference`, `lint_and_test.md`.
- `sase memory web show glossary` roster (66 strands; Macro aliases `xprompt`;
  Macro Memory aliases `memory file · sase memory`).
- `src/sase/memory/web/models.py` (`MemoryStrand.keyword/aliases/summary`,
  `MemoryWeb` roster fields).
- `src/sase/macro/processor.py`, `naming.py`, `loader.py`,
  `workflow_validator.py`, `cli_show_resolve.py`, `macro_sources.py`,
  `_parsing_shorthand.py`, `_trace.py`, `_directive_values.py`,
  `directives.py`, `write_targets.py`; `src/sase/history/prompt_metadata.py`;
  `src/sase/content_layout.py`; `src/sase/agent/*` (submitted vs expanded
  prompt); `src/sase/workflows/mentor.py`, `crs.py`.
- `docs/macros.md` (Renamed from xprompts, Reference Syntax, Raw Prompt
  Placeholders, macro-expansion order model).
- Tree-wide `smack` search (only `.venv` `pycparser` noise); `raw prompt`
  / `macro invocation|reference|call|expansion` searches quoted above.
- Prior research: `sase/repos/research/202610/xprompt_to_macro_naming_verdict.md`.

