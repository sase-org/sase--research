# Naming `#foo`: Macro Invocation, Smack, and the Raw Prompt

**Date:** 2026-10-05 · **Researcher:** grk (independent swarm member) · **Status:** recommendation

> **Verdict: name the use site; do not rename the prompt.** Add a glossary strand whose
> canonical keyword is **Macro Invocation**, with **smack** as the spoken nickname and
> **macro reference** as a compatibility alias. Do not call the authored prompt a
> "smack prompt". Do not put "Sase" in the keyword. Do not rename `raw_prompt.md`,
> the TUI **RAW PROMPT** tab, or the `MacroReference` parser type in this change.

---

## The Question, Stated Precisely

SASE already has a name for the *definition*: a **macro** (formerly xprompt), stored as
`.md` / `.yml` / config and expanded before the agent sees the prompt.

It does not have a first-class name for the *use site*: the `#foo`, `#foo(args)`,
`#foo: text`, `#foo:: text`, `#foo+`, and `#!foo` tokens in prompt text. Docs and code
mostly say "macro reference". The glossary `Macro` strand only says "Triggered with
`#foo`".

The proposal is:

1. Call that use site a **sase macro invocation**, nickname **smack** (from the "kay"
   in *invocation*).
2. Add a glossary memory-web strand for the term.
3. Start calling the "raw prompt" the "smack prompt".

The name has to work in five slots:

- count noun: *a smack*, *three smacks* / *a macro invocation*
- talk-about-syntax: *smack syntax*, *smack args*, *unresolved smack*
- glossary keyword + aliases (LSP highlight, `sase memory read glossary:…`)
- contrast with siblings: `%` directive, `@` artifact ref, `+` project tag
- contrast with the definition: *the `#plan` smack* vs *the `plan` macro*

It does **not** have to become a CLI group, a config key, a directory, or an on-disk
artifact filename. Those slots already belong to `macro`.

---

## Recommendation (short)

**Do it, narrowed.**

The definition/use-site split is real, currently unnamed in the glossary, and already
solved for `@` as **Artifact Reference** (alias **ref**). `#` deserves the same split.
A glossary strand is the right first vehicle: cheap, on-demand, highlighted in the TUI
and LSP, fetched with `sase memory read glossary:smack`.

**Smack is a good nickname and a bad official name.** Keep it as an alias, the way
`ref` sits under Artifact Reference and `Chop` sits under Job.

**"Smack prompt" is a bad idea.** It repeats the exact confusion the xprompt→macro
rename just spent an epic undoing. Keep "raw prompt" (or, if you later rename it,
"authored prompt").

---

## 1. What the system already calls this

### 1.1 The use site is already a type: `MacroReference`

`src/sase/macro/_parsing_references.py` is the lexical source of truth:

- `MacroReference` — "A parsed macro/workflow reference in prompt text."
- `MacroReferenceMarker` — `INLINE = "#"`, `STANDALONE = "#!"`
- `MacroReferenceArgKind` — `none`, `paren`, `colon`, `colon_shorthand`,
  `double_colon_shorthand`, `plus`
- Shared regex: leading context `^` / whitespace / `([{"'`, then `#!` or `#`, then a
  name, optional `!!`/`??`, then args

Docs, CLI help, and user-facing errors agree with that type name:

- `docs/macros.md` section **Reference Syntax**
- Error: `Unknown macro reference(s): #foo - passed through as literal text`
- `sase macro expand`: "Expands macro references in prompt text"
- LSP: "macro reference names" vs "directive names"

"Invocation" appears only in a handful of comments (`_macro_swarm_rendering.py`,
`workflows/crs.py`, `workflows/mentor.py`) and in tests that talk about "macro
invocations" in the English sense. It is not a public term.

### 1.2 The definition already has a glossary family

| Strand            | What it names                                      |
| ----------------- | -------------------------------------------------- |
| Macro (xprompt)   | The definition. "Triggered with `#foo`."           |
| Macro Part        | `.md` → one `prompt_part`                          |
| Macro Workflow    | `.yml` → steps                                     |
| Macro Swarm       | `---` fan-out inside a macro body                  |
| Macro Memory      | `#memory/<stem>`                                   |
| Project Tag       | `+<project>`, which *expands to* a VCS `#gh:`/`#git:` ref |

There is **no** strand for the `#` token, and **no** strand for `%` directives. `@` has
Artifact Reference. `+` has Project Tag. The prompt-sigil family is uneven, and `#` is
the hole that actually hurts, because "macro" names the file, not the token.

### 1.3 "Raw prompt" already means three different things

| Surface | Meaning today |
| ------- | ------------- |
| `raw_prompt.md` (was `raw_xprompt.md`) | Authored launch text, macros and directives still present |
| TUI preview tab `RAW PROMPT` | That same authored text, highlighted |
| `sase prompt show -f raw` | Exact bytes, no added newline (a *format*, not a kind of prompt) |
| Raw Prompt Placeholders (`<label>`) | Fill-in tags collected at TUI submit |

`submitted_prompt.md` is the companion artifact: the prompt as submitted on the launch
path. Directives are stripped from what the model sees; "the raw prompt keeps them"
(`docs/macros.md`, `%tab`).

The xprompt→macro naming verdict (`research:202610/xprompt_to_macro_naming_verdict.md`)
called out `raw_xprompt.md` as evidence that "xprompt" had drifted to mean *the whole
authored prompt*. Rule 2 of that rename existed to untangle definition from prompt.
`raw_prompt.md` is the fix that just landed.

### 1.4 Sibling syntax already has short names

| Sigil | Official term | Short name | Glossary strand |
| ----- | ------------- | ---------- | --------------- |
| `#` / `#!` | macro reference (de facto) | *(none)* | no |
| `%` | directive | — | no |
| `@` | Artifact Reference | ref | yes |
| `+` | Project Tag | tag | yes |

The missing short name is specifically for `#`, and the missing official name is
specifically for the use site.

---

## 2. Critique of the plan

### 2.1 What is right

**The use site needs a name.** People and agents currently say "the `#foo`", "the macro
reference", or "the macro" for both the file and the token. That collision is smaller
than the old xprompt/prompt collision, but it is the same shape: one word covering two
layers. Artifact references already split *Artifact* from *Artifact Reference*. Macros
should split *Macro* from *Macro Invocation*.

**A glossary strand is the correct first implementation.** Glossary phrases are
highlighted in the TUI prompt and in the LSP (`type` tokens, `SaseGlossaryTerm` in
nvim). Hover and `K` preview teach the term where it is used. Strand bodies stay
on-demand, so this does not inflate always-loaded instructions. The glossary web
already inlines a roster of keywords and aliases into agent instructions, so
`glossary:smack` becomes discoverable the next `sase memory init`.

**A punchy nickname helps.** SASE's spoken vocabulary is already full of short
count-nouns (stitch, bead, patch, ref, hood). "Macro invocation" is correct and long.
A one-syllable nickname is how that term will actually get used.

**The backronym is honest about being a mnemonic.** "Invocation" does contain the
/keɪ/ of *smack*. That is a joke-expansion, not a product acronym. Treated as a
mnemonic for a nickname, it is fine. Treated as the official expansion that must appear
in the keyword ("Sase Macro Invocation"), it warps the glossary.

### 2.2 What is wrong, or too big

**"Smack prompt" reopens the xprompt wound.** A raw prompt is source text. It may
contain zero smacks (plain prose), and it always may contain `%` directives, `+`
project tags, `@` refs, `<label>` placeholders, and frontmatter. Calling the whole
thing a smack prompt is like calling a C file a "macro file" because it might contain
`#include`. That is the same category error as `raw_xprompt.md`. The rename epic
just moved that file to `raw_prompt.md` and relabeled the preview tab **RAW PROMPT**.
Renaming again, weeks later, to a word that names a *subset* of the tokens inside the
file, would be a regression.

**"Sase macro invocation" is a redundant official name.** Glossary keywords already
live inside SASE. We say Artifact Reference, not Sase Artifact Reference; Macro, not
Sase Macro. "Sase" is prefixed only when the bare word is hopelessly generic (Sase
Agent, Sase Turn, Sase Project). "Macro Invocation" is specific enough. The `S` in
SMACK does not need to appear in the keyword.

**Three public names is one too many.** The plan as stated would put *sase macro
invocation*, *smack*, and the existing *macro reference* in circulation at once, on
top of *macro*. Pick an official phrase and a nickname. Keep "macro reference" as a
compatibility alias because the parser, docs, and errors already say it. Do not make
the backronym the keyword.

**A cute name as the canonical keyword has a local precedent for getting demoted.**
Chop and Lumberjack started as the names of scheduler concepts and are now aliases of
**Job** and **Routine**. AXE is an alias of **Sase Scheduler**. Stitch, Patch, and Bead
stayed canonical because they *are* the concept, not a joke about it. Smack is closer
to Chop than to Stitch: it was chosen because it sounds good, then reverse-fitted to
"invocation". Start it as an alias. If six months of speech promote it, flip the
keyword later. That flip is a one-line frontmatter change. The reverse (demoting a
canonical Smack after it has been highlighted in every prompt) is louder.

**External collisions are real and small.**

- Linux **Smack** (Simplified Mandatory Access Control Kernel), in-tree LSM since
  2.6.25, still documented at kernel.org.
- **SMACK** the LLVM→Boogie software verifier (Utah / `smackers/smack`).
- English: slap, kiss, heroin (UK).

None of these will steal `sase memory read glossary:smack` inside this project. They
do argue against putting SMACK on a public marketing surface or a CLI group. A
glossary alias used in conversation is the right altitude.

**Glossary highlighting is a side effect, not a free lunch.** Once `smack` is an
alias, the prompt highlighter and LSP will mark the English word *smack* (and the
derived plural *smacks*) wherever it appears outside literal zones. That is the
desired behavior when you mean the term, and a false positive when you do not. The
glossary already accepts this for *patch*, *goal*, *turn*, *job*, *card*, *deck*,
*node*, *gate*, *ref*. `smack` is no worse than those. It is a reason to keep the
canonical keyword as the two-word phrase, so the *primary* highlight in docs is
"macro invocation".

**Do not cascade nicknames.** `%` already has "directive". Do not invent *dack*.
Do not rename the prompt language. The value of this change is one new count-noun
for `#` tokens.

### 2.3 Is this a good idea?

Yes, as a **vocabulary split plus a nickname**, implemented as a glossary strand and
a small docs touch.

No, as a **rename of "raw prompt"**, a new official acronym, or a parser/TUI/artifact
filename churn.

The idea pays for itself if, after the strand exists, a human can say "put a `#plan`
smack at the top" and an agent can `sase memory read glossary:smack` and know that
means the `#` token, not the `.md` file, not the whole prompt.

---

## 3. Justified adjustments (called out)

These change the stated requirements. Each is intentional.

| # | Stated requirement | Adjustment | Why |
| - | ------------------ | ---------- | --- |
| A | Official name is "sase macro invocation" | Official keyword is **Macro Invocation**. Optional alias: `sase macro invocation` only if you want the backronym to be a lookup key. | Matches Artifact Reference / Macro Part / Macro Swarm. "Sase" is redundant in this web. |
| B | Nickname "smack" is *the* name | **smack** is an alias, not the keyword. | Same pattern as `ref`, `Chop`, `AXE`. Easy to promote later; hard to demote. |
| C | Also refer to the raw prompt as the "smack prompt" | **Reject.** Keep raw / authored prompt. | Category error; undoes the xprompt rename's Rule 2. |
| D | (implied) Maybe rename files, TUI tab, parser type | **Out of scope.** `raw_prompt.md`, `RAW PROMPT`, `MacroReference`, and the "Unknown macro reference(s)" error stay. | Glossary-first. Code already has a coherent type name. A class rename is a noisy diff with no user benefit. |
| E | (unstated denotation) `#foo` | Define the denotation tightly, below. `#gh:`/`#git:` workspace refs are **not** smacks. `%` / `@` / `+` are **not** smacks. `#!name` **is** a smack (standalone). | Unique syntax is the `#`/`#!` macro language, not every hash token. |
| F | New glossary strand only | Also edit the existing **Macro** strand so it names the use site and implicit-links the new term. One-paragraph note under `docs/macros.md` **Reference Syntax**. | A strand that nothing mentions will not be discovered by implicit glossary closure. |
| G | (unstated) wholesale replace "macro reference" in docs | **Do not.** Add the new term; leave existing "macro reference" prose. The alias makes both highlight. | Avoids a docs-and-error churn for a synonym. |

---

## 4. Name scorecard

| Test | `macro reference` (status quo) | `macro invocation` | `smack` as official | `sase macro invocation` |
| ---- | :----------------------------: | :----------------: | :-----------------: | :---------------------: |
| Distinguishes use site from definition | ~ | ✓ | ✓ | ✓ |
| Matches C/Rust terminology | ~ ("reference" is citation-ish) | ✓ Rust Reference has a "Macro invocation" production; GNU cpp talks about invoking macros | ✗ | ~ |
| Matches SASE parser (`MacroReference`) | ✓ | ~ | ✗ | ✗ |
| Parallel with Artifact Reference | ✓ | ✓ (better verb: cite vs invoke) | ✗ | ~ |
| Count noun, plural, article | ✓ | ✓ | ✓ *a smack*, *smacks* | ~ long |
| Spoken in a prompt-bar conversation | ~ | ~ | ✓ | ✗ |
| Unique in this repo today | ✓ | ✓ | ✓ (zero hits) | ✓ |
| Ownable outside SASE | ✓ | ✗ common CS | ✗ LSM + verifier + slang | ✗ |
| Fits glossary keyword style | ~ not a strand yet | ✓ Title Case two-word | ~ one cute word | ✗ extra "Sase" |
| Survives the Chop/Lumberjack test | ✓ boring | ✓ boring in a good way | ✗ likely to be demoted | ~ |

**Winner as keyword:** Macro Invocation.
**Winner as nickname:** smack.
**Keep as alias:** macro reference (already in the product).

"Reference" is slightly the wrong verb. An `@bead:` *cites*. A `#plan` *invokes* and
*expands*. That is why the new official phrase should be invocation, even while the
parser type stays `MacroReference`.

---

## 5. Precise denotation

A **macro invocation** (smack) is one lexer-recognized `#` / `#!` use of a *catalog
name* in prompt text.

In:

- `#name`
- `#name(args)` / `#name(k=v)` / `#name([[ ... ]])`
- `#name:arg` / `` #name:`arg with spaces` `` / `#name:a,b`
- `#name: text` (line shorthand) / `#name:: text` (to next line-boundary smack or directive)
- `#name+`  (boolean true)
- `#ns/name` / `#memory/<stem>` / `#skill/<name>`
- `#!name` and the same argument forms (standalone workflow)
- shorthands that expand to directives (`#t:5m` → `%wait(time=5m)`, `#tribe:review`)

Out:

- `%name` directives (control plane; stripped before the model)
- `@kind:arg` artifact references (citations)
- `+project` project tags (selectors; they *expand into* `#gh:`/`#git:` workspace refs)
- `#gh:` / `#git:` VCS workspace refs (workspace selectors that share the `#` lexer
  and the `MacroReference` type, but they do not name a macro)
- unknown `#word` tokens that pass through as literal text are *unresolved smacks*
  only when they matched the lexer; a Markdown heading `# Heading` is not a smack
  (leading-context rule already ignores it)
- the macro definition file / config entry (that is the Macro)
- the whole authored prompt (that is the raw prompt)

This denotation is the one that makes "smack syntax" useful: it is exactly the grammar
in `docs/macros.md` **Reference Syntax** plus **Shorthand Syntax**, minus workspace
refs.

If you instead define smack as "any `MacroReference` token", then `#gh:sase` is a
smack, and you have to explain why a project tag expands *into* a smack. That is
worse. The parser type is a superset of the glossary term. Living with that
superset is cheaper than renaming the parser in this change.

---

## 6. Related talk that *does* open up (and talk that should not)

Once the strand exists, these phrases are load-bearing and cheap:

| Phrase | Means |
| ------ | ----- |
| a smack / smacks | use sites |
| smack syntax | the `#`/`#!` grammar (parens, colon, `::`, `+`, `[[ ]]`) |
| smack args | the argument payload |
| inline smack vs standalone smack | `#` vs `#!` |
| unresolved smack | lexer hit, no catalog entry, passed through |
| nested / recursive smack | expansion that contains further `#` tokens |
| "smack `#plan` at the top" | verb: write an invocation |

These phrases should **not** be coined:

| Phrase | Why not |
| ------ | ------- |
| smack prompt | names the wrong layer; see §2.2 and adjustment C |
| smack language | the prompt language is `#` + `%` + `@` + `+` + prose |
| dack / dirack / "hash call" | nickname cascade |
| smack catalog | the catalog is of macros (definitions), not of invocations |

If "raw prompt" still bothers you as a name, the *next* research topic is a better
name for that layer. Candidates that preserve the contrast with submitted/expanded
text: **authored prompt**, **source prompt**, **launch prompt**. None of them should
be "smack prompt". I would not rename the filename or the TUI tab unless that
separate research lands; `raw_prompt.md` is a month old and already has a legacy
fallback.

---

## 7. How to implement (recommended sequence)

This is a **memory + docs** change. It is authorized later by an approved plan or a
direct "add this glossary strand" ask; this research does not itself edit memory.

### Step 1 — Glossary strand (the actual deliverable)

Create `sase/memory/glossary/macro-invocation.md`:

```markdown
---
keyword: Macro Invocation
aliases:
  - smack
  - macro reference
---

A macro invocation (smack) is one use of SASE's `#` / `#!` syntax that names a
[[glossary:macro]] at a use site: `#name`, `#name(args)`, `#name:arg`,
`#name: text`, `#name:: text`, `#name+`, namespaced forms such as `#memory/foo`,
and standalone `#!name`. SASE expands it before the agent sees the prompt.

It is not the macro definition, not a [[glossary:project-tag]] (`+<project>`),
not an [[glossary:artifact-reference]] (`@kind:arg`), and not a `%` directive.
`#gh:` / `#git:` workspace refs share the `#` lexer but are workspace selectors,
not smacks. Unresolved smacks that match the lexer and miss the catalog pass
through as literal text.
```

Notes on this shape:

- **Slug** `macro-invocation` matches `artifact-reference`, `macro-swarm`,
  `project-tag`. Identity is the filename; lookup is the keyword plus aliases.
- **Do not** add `smacks` as an explicit alias. Derived plurals of terms *and*
  aliases already match (`docs/macros.md` LSP glossary section).
- **Do not** make `smack` the keyword on the first pass.
- Optional third alias `sase macro invocation` only if you want
  `glossary:sase macro invocation` to resolve. I would skip it; prefix lookup
  on `Macro Invocation` plus the `smack` alias is enough, and the roster line
  is already long.
- Mention Macro, Project Tag, and Artifact Reference by phrase so the glossary
  web's `link_reference: implicit` closure actually connects the family.
- Keep the body short. Existing macro strands are 1–4 sentences. A glossary
  strand is a term, not a tutorial; `docs/macros.md` stays the syntax reference.

Keyword uniqueness is fail-closed (`src/sase/memory/web/mutation_validate.py`):
slug, keyword, and each alias must not resolve to another strand in the same
web. `smack` currently matches nothing. `macro reference` does not collide with
`Artifact Reference` or its alias `ref`.

### Step 2 — Point the Macro strand at the new term

Today `glossary/macro.md` is:

> Formerly called an xprompt. Triggered with `#foo` in agent prompts. …

Change the second sentence so it *names* the trigger, e.g. "Invoked with a
[[glossary:macro-invocation]] (`#foo`) in agent prompts." That is the implicit
link that makes `sase memory read glossary:macro` also teach smack.

### Step 3 — One paragraph in `docs/macros.md` Reference Syntax

After the existing "Reference inline-capable macros… `#` prefix" paragraph, add
one sentence: a `#name` / `#!name` token is a **macro invocation** (smack); the
definition it names is the macro. Do not retitle the section in this change
(keep **Reference Syntax** so URLs and the TOC stay stable). A later docs pass
can retitle it **Invocation Syntax** if the new term sticks.

### Step 4 — Republish

`sase memory init` regenerates the `**GLOSSARY TERMS:**` roster. The new line
will look like:

`…; Macro Invocation (smack, macro reference); …`

That roster is always-loaded. It is the entire always-loaded cost of this
change: a few words. Strand bodies stay on demand.

Route the edit through `/sase_memory_write` (user asked for the strand in the
original idea; an approved plan that names the files is also enough). Do not
hand-edit `AGENTS.md`.

### Step 5 — Explicitly do not do

- Do not rename `raw_prompt.md` / `submitted_prompt.md` / the `RAW PROMPT` tab.
- Do not rename `class MacroReference` or `MACRO_REFERENCE_PATTERN`.
- Do not change the unknown-reference error string in this pass.
- Do not add a `sase smack` CLI.
- Do not add a Directive glossary strand in the same change (worth a follow-up;
  not required to make smack work).
- Do not file this as a mechanical replace of "macro reference" across `docs/`
  and `src/`.

### Size

This is an **XS/S memory** change: two strand files, one docs paragraph, memory
init. No tests beyond whatever `sase memory init` / glossary catalog tests
already assert about unique keywords. If you want a test, add a catalog fixture
that `glossary:smack` and `glossary:macro invocation` resolve to the same slug.

---

## 8. Alternative approaches I would not take

**Make Smack the keyword.** Attractive if you want another Stitch. Wrong for a
brand-new nickname of an existing, well-documented concept. Start as alias.

**Skip the glossary and just start saying "smack" in chat.** Then agents will
not have a lookup, the LSP will not highlight it, and the next researcher will
ask what a smack is. The strand is the whole point of "a distinct name".

**Rename the parser type to `MacroInvocation` now.** Correct in the abstract,
expensive in the concrete: `_parsing_references.py`, every import, every test,
the regex constant names, error strings. Do it only if a later terminology
guard makes "macro reference" vs "macro invocation" a real consistency problem.
Today it is not.

**Name the whole prompt language.** The xprompt verdict already proposed
"SASE Prompt Language" as an umbrella for `#` / `%` / `@` / `+`. That is a
different (larger) naming task. Smack should not wait on it, and should not
try to be it.

**Add smack as a core-memory sentence.** Core memory is always-loaded budget.
A glossary alias on the roster is enough. Anyone who needs the denotation
reads the strand.

---

## 9. Recommended solution

1. **Accept the goal:** give `#foo` a distinct spoken name so we can talk about
   the use site without saying "the macro" or "the `#` thing".
2. **Official term:** **Macro Invocation**.
3. **Nickname:** **smack** (alias). Treat SMACK as a mnemonic, not as a product
   acronym that forces "Sase" into the keyword.
4. **Compatibility alias:** **macro reference**.
5. **Implement** as `sase/memory/glossary/macro-invocation.md` plus a one-line
   update to `glossary/macro.md` plus one sentence in `docs/macros.md`
   Reference Syntax, then `sase memory init`.
6. **Reject** renaming the raw prompt to "smack prompt". If that layer needs a
   better name later, research "authored prompt" separately and leave
   `raw_prompt.md` stable until then.
7. **Denote** smack as a catalog `#`/`#!` use site, not as every hash token and
   not as the prompt that contains it.
8. **Do not** rename parser types, artifact filenames, TUI tabs, or error
   strings in this change.

That is the Artifact Reference playbook, applied to `#`. It is the smallest
change that makes "smack" a real word in SASE instead of a private joke, and
the largest change this idea currently deserves.

---

## Sources

**Local (this workspace):**

- `sase/memory/glossary/macro.md`, `macro-part.md`, `macro-workflow.md`,
  `macro-swarm.md`, `macro-memory.md`, `artifact-reference.md`, `project-tag.md`,
  `chop.md` (Job / Chop), `lumberjack.md` (Routine / Lumberjack),
  `sase-scheduler.md` (AXE alias)
- `sase/memory/macros.md` (Invoke / Directives)
- `sase/memory/glossary.md` (roster; no invocation term today)
- `src/sase/macro/_parsing_references.py` (`MacroReference` and friends)
- `src/sase/macro/unresolved.py` (unknown macro reference error)
- `src/sase/legacy_xprompt_names.py` (`raw_prompt.md`, `submitted_prompt.md`)
- `src/sase/ace/tui/widgets/agent_header_preview.py` (`PREVIEW_TAB_LABEL = "RAW PROMPT"`)
- `src/sase/memory/web/mutation_validate.py` (keyword/alias uniqueness)
- `docs/macros.md` (Reference Syntax, Shorthand Syntax, Raw Prompt Placeholders,
  glossary LSP)
- `docs/prompt.md` (`show -f raw`)
- `docs/memory.md` (memory webs, implicit links, derived lookup)
- `docs/editor.md` (semantic tokens)
- `research:202610/xprompt_to_macro_naming_verdict.md` (definition vs prompt;
  Rule 2; preprocessor family `#` / `%` / `@` / `+`)

**External:**

- Rust Reference, *Macro invocation* —
  <https://doc.rust-lang.org/reference/macros.html>
- GNU C preprocessor, *Macros* / invocation of function-like macros —
  <https://gcc.gnu.org/onlinedocs/cpp/Macros.html>
- Linux kernel, *Smack* LSM (Simplified Mandatory Access Control Kernel) —
  <https://kernel.org/doc/html/latest/admin-guide/LSM/Smack.html>
- SMACK software verifier (LLVM → Boogie) —
  <https://github.com/smackers/smack>
- Wikipedia, *Smack (software)* —
  <https://en.wikipedia.org/wiki/Smack_(software)>
