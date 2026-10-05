# Naming `#foo`: Macro Invocation, "Smack", and the Smack Prompt

> **Research query:** Should SASE macro invocations such as `#foo` get a distinct name,
> "sase macro invocation" or "smack" for short, backed by a new glossary memory web
> strand, and should the raw prompt then be called the "smack prompt"? Critique the
> plan, call out any justified adjustments to the requirements, and recommend the best
> way to implement it.

![Infographic: the four prompt sigils with # as Macro Invocation, the terminology decision matrix (keyword Macro Invocation, alias smack, compatibility aliases macro reference and macro ref), the submitted to raw to expanded prompt pipeline with "smack prompt" rejected, and the glossary-only scope guardrails](macro_invocation_glossary_term_smack_infographic.png)

## Bottom line

1. **Name the use site: yes.** All five researchers agree the gap is real. "Macro" names
   the definition, and the `#foo` token in a prompt has no glossary entry. Code and docs
   call it four different things.
2. **Canonical keyword: `Macro Invocation`, with `smack` as an alias.** Three reports
   (cdx, cld, grk) favor this, with cdx preferring the longer keyword "Sase Macro
   Invocation". Two (mus, gem) prefer "Macro Reference". I pick **Macro Invocation**
   (see [how the disagreements were resolved](#disagreements-and-how-i-resolved-them)).
   It is your own word, the standard term (Rust, GNU CPP), and the name the highlighter
   already uses (`macro.invocation`). It also avoids SASE's most overloaded word, "ref".
   Add `macro reference` and `macro ref` as aliases so existing prose links to the new
   strand.
3. **Smack is a good nickname but not yet the keyword.** As an alias it gets everything
   you want: `sase memory read glossary:smack` works, the TUI and LSP underline it,
   and the always-loaded roster shows it. The keyword is the spelling agents copy into
   docs, so it should be the self-describing one for now. Promoting smack later is a
   one-line swap, and [the promotion test](#when-to-promote-smack-to-the-keyword) gives
   a concrete test for when to do it.
4. **"Smack prompt": no.** All five researchers reject it. A prompt is a container and
   a smack is one expression inside it. The name also repeats the `raw_xprompt.md`
   mistake that the xprompt→macro rename just fixed. Fix the real confusion instead:
   add a [**Raw Prompt** strand](#raw-prompt-strand-file) that defines the submitted →
   raw → expanded stages. **This is an
   [adjustment to your requirements](#adjustments-to-your-requirements).** One of the
   five researchers got those stages backwards, which shows the confusion is real.
5. **Keep the change glossary-only.** Add two strand files, append one sentence to the
   Macro strand, add one docs paragraph, and run `sase memory init`. Do not rename
   code identifiers, CLI commands, artifact filenames, or TUI labels. One test
   allowlist line must change (see
   [the terminology guard](#the-terminology-guard-will-trip-and-the-rename-epic-is-still-open)).
   The full plan is in the [recommended solution](#recommended-solution).

## Critique of the plan

### What the plan gets right

- **The gap is real.** "Add a macro to the prompt" can mean writing a `.md` file or
  typing `#foo`. "The macro's args" can mean declared inputs or supplied values. LSP
  diagnostics, docs, and agent conversations need that distinction.
- **The glossary is the right vehicle.** A strand gets on-demand definitions, TUI and
  LSP underline, hover, jump-to-definition, and a roster entry for about 10–15
  always-loaded tokens. Strand bodies never inline.
- **A short spoken form has real value.** "Macro invocation" is seven syllables.
  SASE's working vocabulary is full of one-syllable count nouns (stitch, bead, patch,
  ref, hood, deck), and the long form will get clipped in practice anyway.
- **The name opens up useful phrases** ([see the vocabulary](#vocabulary-this-opens-up)):
  two smacks in this prompt, smack args, an unresolved smack, a standalone smack.

### What I would change

1. **The keyword should translate; the nickname can be fun.** SASE's whimsical
   canonical names (Stitch, Patch, hood, deck) all name **SASE-original concepts with
   no standard name**. "Macro invocation" already has a textbook name. When a glossary
   definition has to say "a smack is a macro invocation", the second phrase is the
   name (the test from the September terminology study). Precedent agrees: Chop,
   Lumberjack, and AXE now survive as aliases of Job, Routine, and Sase Scheduler.
   Starting smack as an alias avoids a later demotion.
2. **"Smack prompt" names the wrong layer.** It names a container after one optional
   kind of expression inside it. It cannot tell the submitted prompt from the raw
   prompt, because both contain smacks. It also spends the compound on its least useful
   meaning. And it repeats the conflation that made `raw_xprompt.md` a target of the
   macro rename. Your underlying wish seems to be a crisp way to talk about the
   pre-expansion prompt. A [Raw Prompt strand](#raw-prompt-strand-file) gives you that,
   and **source prompt** → **expanded prompt** is the better metaphor if you ever want a
   new stage name.
3. **External collisions matter only on public surfaces.** gem overweights the slang
   ("heroin", "violence"). It is real, but irrelevant to an internal alias that sits in
   the same glossary as "chop" and "AXE". The collisions do argue for keeping "smack"
   out of public docs (sase.sh), CLI help, and config keys until it earns promotion.
4. **Scope the term to an intended call, not every `#` token.** A Markdown `# Heading`,
   a `#D7D7FF` color, or a `#foo` inside a code span or disabled region is not a smack.
   An intended call to an unknown name is an *unresolved* smack; SASE passes it through
   as literal text and raises the `Unknown macro reference(s)` warning.

### Name comparison

| Test | `smack` | `Macro Invocation` | `Macro Reference` |
| --- | :---: | :---: | :---: |
| A newcomer or LLM can guess the meaning | ✗ | ✓ | ✓ |
| Matches standard CS usage (Rust, GNU CPP) | ✗ | ✓ | ~ |
| Avoids "ref"/"reference" overload (Artifact Reference, Reference Memory, workspace refs) | ✓ | ✓ | ✗ |
| Already in the product | ✗ | ~ (`macro.invocation` highlight role) | ✓ (`MacroReference`, error toast) |
| Fits `#!sync` / `#git:home`, which run workflows | ~ | ✓ | ~ |
| Brief in speech | ✓✓ | ✗ | ~ (`macro ref`) |
| Survives a product rename | ~ | ✓ | ✓ |
| Free of external collisions and slang | ✗ | ✓ | ✓ |

## Adjustments to your requirements

These adjustments are called out explicitly.

| # | You asked for | Adjusted to | Why |
| --- | --- | --- | --- |
| A1 | "smack" as the name | Keyword **Macro Invocation**; `smack` is an alias | Self-describing keyword; smack keeps full lookup, highlight, and roster presence; promote later per [the promotion test](#when-to-promote-smack-to-the-keyword) |
| A2 | "sase macro invocation" | Drop "Sase" from the keyword; give the etymology in the body | Matches the Macro family's naming; robust to the pending product rename; the matcher already covers the long phrase |
| A3 | (unstated) what counts | Include `#!name`, namespaced, shorthand, and **workspace** (`#gh:`/`#git:`) forms; exclude literal-zone text, headings, and non-macro `#` tokens | Verified that workspace refs invoke workflow macros |
| A4 | "smack prompt" for the raw prompt | **Reject.** Add a `Raw Prompt` strand defining submitted → raw → expanded | Fixes the confusion that has actually been demonstrated; no artifact rename |
| A5 | (implied) broader rollout | Glossary plus one docs paragraph only; no identifier, CLI, filename, TUI-label, or toast changes, and no prose sweep | Every past rename that crossed this line became a multi-repo epic |
| A6 | (new) | Add aliases `macro reference` and `macro ref` | Existing prose and the Project Tag strand link correctly; fixes the "ref" → Artifact Reference mislink |
| A7 | (new) | Sequence after `sase-1eq.11` and update the guard allowlist line | See [the terminology guard](#the-terminology-guard-will-trip-and-the-rename-epic-is-still-open) |

## Vocabulary this opens up

| Use | Means |
| --- | --- |
| a smack / smacks | one or more macro invocations in prompt text |
| smack syntax | the `#`/`#!` grammar: parens, colon, `:`/`::` shorthand, `+`, `[[ ]]`, `!!`/`??` |
| smack args | the actual arguments supplied at the use site, as opposed to the macro's declared inputs |
| inline vs standalone smack | `#name` vs `#!name` |
| workspace smack | `#gh:…` / `#git:…`, which a `+project` tag expands into |
| unresolved smack | an intended call that names no macro and passes through as literal text |
| nested smack | an invocation introduced by expanding another macro's body |

**Do not coin:**

- **smack prompt.** It names the wrong layer.
- **smack language.** The prompt language is `#` + `%` + `@` + `+` + prose.
- **smack catalog.** The catalog lists macros, not invocations.
- **Nicknames for the other sigils** ("dack", and the like). A cascade of nicknames would
  cost more than this one is worth.

## What the panel agreed on

| Finding | Agreement |
| --- | --- |
| The definition/use-site split is real and has no glossary entry | 5/5 |
| A glossary strand is the right vehicle; no runtime or wire change is needed | 5/5 |
| Reject "smack prompt" as a name for the raw prompt | 5/5 |
| Do not rename `MacroReference`, `raw_prompt.md`, the RAW PROMPT tab, or the CLI | 5/5 |
| "Smack" should not be the canonical keyword | 5/5 (mus and gem would also drop it entirely or nearly so) |
| External collisions exist: the Linux Smack LSM, the SMACK verifier, the Smack XMPP library, English slang | 5/5 note them; they disagree on how much they matter |

The `#` sigil is the one prompt sigil whose instance has no name. `@` has **Artifact
Reference** (alias `ref`). `+` has **Project Tag**. `%` has "directive" in prose, but no
strand yet. The `Artifact` → `Artifact Reference` pair is exactly the pattern `Macro` →
`Macro Invocation` would complete.

## Disagreements and how I resolved them

| Question | Positions | Resolution (with evidence) |
| --- | --- | --- |
| **Keyword: Invocation or Reference?** | cld, grk: Macro Invocation. cdx: Sase Macro Invocation. mus, gem: Macro Reference. | **Macro Invocation.** "Reference" leads in prose (109 hits against 3 for "macro invocation") and in identifiers (`MacroReference`). But "ref" already belongs to Artifact Reference, and the [matcher simulation](#glossary-matcher-simulation) shows the collision causing a mislink in today's glossary. mus argues that `#foo` is expanded, not invoked. That argument fails: GNU CPP and the Rust Reference both call preprocessor-time expansion an *invocation*, and `#!sync` and `#git:home` literally run workflows. Keep "macro reference" as an alias, so nothing written today stops linking. |
| **"Sase" in the keyword?** | cdx yes; cld, grk no | **No.** The `Sase ` prefix appears only where the bare word is generic: Sase Agent, Sase Turn, Sase Project. The macro family is Macro, Macro Part, Macro Swarm, Macro Workflow, and Macro Memory. Explain the etymology in the strand body instead. The matcher already highlights "sase macro invocation" through its "macro invocation" span (verified). The sase product rename is also still undecided (the 2026-10-04 shortlist puts the decision "on a clock"), so tying the keyword to "sase" is fragile. |
| **Drop smack entirely?** | mus: yes, no alias. gem: tertiary alias at most. Others: alias. | **Keep it as an alias.** You asked for the word, and an alias costs about 2 roster tokens. The highlighting test in the [matcher simulation](#glossary-matcher-simulation) found no false positives on "smacking", "smacked", or "smackdown". mus's corpus-before-mechanism objection does not apply: a glossary strand is content, not retrieval machinery. |
| **Are `#gh:` / `#git:` workspace refs smacks?** | cld: yes. cdx: depends on dispatch. grk: no ("they do not name a macro"). gem: separate "workspace reference". | **Yes; grk is factually wrong.** `#git:<ref>` invokes the workflow macro `src/sase/macros/git.yml`, and its `git_ref` input carries the ref. The history code classifies a `MacroReference` as "actually a VCS workflow ref" (`prompt_metadata.py:_is_vcs_reference`). The docs say workspace workflows "use the same `#name:ref` reference syntax as macros". So a workspace reference is a specialized smack, and a project tag expands *into* one. That makes the definition simpler, not harder. |
| **Prompt stage order** | cdx, cld: submitted → raw → expanded. gem: raw → expansion → submitted ("sent to the LLM"). | **cdx and cld are right; gem inverted it.** `write_submitted_prompt_artifact` persists "the launch-boundary prompt without alias or macro expansion". `preprocess_prompt_macros` then canonicalizes project tags and aliases, writes `raw_prompt.md`, and only then expands macro references (`run_agent_runner_setup_prompt.py`). |
| **Do derived plurals need explicit aliases?** | cld: add them if needed. grk: not needed. | **Not needed.** The matcher derives plurals of terms and aliases (`docs/macros.md`, Editor LSP section). The probe matched "smacks" and "macro invocations" with no plural alias configured. |
| **Add a Raw Prompt strand?** | cld: yes. cdx, grk: defer. mus, gem: no. | **Yes, in the same small change.** The confusion is demonstrated: gem's stage order is wrong, and mus calls the stage both "raw" and "raw submitted". "Raw" also carries three other meanings: the `raw_prompt.md` artifact, `sase prompt show -f raw`, and raw `<label>` placeholders. |
| **Sweep docs from "macro reference" to "macro invocation"?** | cld: about 35 lines, after `sase-1eq`. gem: align the docs. grk, cdx: no sweep. | **No sweep.** The alias makes existing prose link to the new strand. Add one paragraph; retitle "Reference Syntax" only if the term sticks. |
| **Add a `Directive` strand?** | cld: optional, same change. grk: follow-up. | **Follow-up.** It is worthwhile, but it is a separate term. |
| **Is the S-MAC-K derivation legitimate?** | gem: "A = ? unaccounted". mus: "folk etymology". | **It is fine as a blend:** **S**ase + **MAC**ro + invo**C**ation, with the "kay" sound spelled *k*. gem misread it. It is still not *recoverable* from the word (cld's point), which matters for the keyword but not for an alias. |

## New evidence from lead verification

### Glossary matcher simulation

I compiled today's glossary catalog with the same Rust-backed matcher that drives TUI
highlighting, LSP semantic tokens, and `sase memory read` implicit closure. Then I
compiled it again with the proposed strand added. Keyword: `Macro Invocation`. Aliases:
`smack`, `macro reference`, `macro ref`.

| Text | Today | With the new strand |
| --- | --- | --- |
| "expands to the project's VCS macro ref" (the Project Tag strand body) | `macro` → Macro, **`ref` → Artifact Reference (mislink)** | `macro ref` → Macro Invocation |
| "two smacks and an unresolved smack" | no match | `smacks`, `smack` → Macro Invocation |
| "Unknown macro reference(s) … macro invocations" | `macro` → Macro twice | `macro reference`, `macro invocations` → Macro Invocation |
| "lip-smacking smacked smackdown" | no match | no match |
| "a sase macro invocation" | `macro` → Macro | `macro invocation` → Macro Invocation |

Three findings follow:

- **The new strand fixes an existing mislink.** Today the Project Tag strand implicitly
  links to Artifact Reference through the bare word "ref". The `macro ref` alias wins
  by longest match.
- **Smack produces no false positives on inflected English.** It matches only "smack"
  and the derived plural "smacks".
- **No plural aliases and no "sase macro invocation" alias are needed.**

I also ran both draft bodies from the [recommended solution](#recommended-solution)
through the matcher. The [Macro Invocation draft](#macro-invocation-strand-file) links
Macro, Sase Agent, Sase Workspace, and Project Tag. The
[Raw Prompt draft](#raw-prompt-strand-file) links Project Tag, Macro, and Macro
Invocation. Both draft bodies avoid the bare word "ref" on purpose.

### What raw prompts actually contain

Replicating cld, I scanned the 710 `raw_prompt.md` files under `~/.sase` modified in the
last 30 days, with code spans stripped:

| Measure | Share |
| --- | ---: |
| Contains a `%` directive | 100% |
| Contains any `#` token | 99.7% |
| Contains a `#` token other than `#gh`/`#git` | 83.5% |
| Contains only workspace refs (`#gh:` / `#git:`) | 16.2% |
| Most common non-workspace names | `#fork` 266, `#bd/work_phase_bead` 142, `#plan` 91, `#research` 70 |

This supports cld's conclusion, with two refinements:

- **Nearly every raw prompt contains a smack, because launch setup puts one there.**
  `+project` becomes `#gh:…`, and a bare prompt gets `#git:home`. Nearly every prompt is
  therefore technically a "smack prompt", so the label tells you nothing. Many of these
  prompts are also machine-written, by epic phase workers and research swarms.
- **Not every `#` token is a smack.** Hex colors such as `#D7D7FF` and `#A8A8A8` turned
  up in at least a dozen prompts and pass the lexical shape. The strand should define a smack as
  an intended macro call, and treat a bare lexer match as only a candidate.

### The terminology guard will trip and the rename epic is still open

`tests/_macro_terminology_docs.py` allowlists exact lines that may still say "xprompt".
Two of those lines are affected:

- **The `sase/memory/glossary.md` roster line**
  `"Calls; Machine Tab; Macro (xprompt); Macro Memory (memory file, sase memory); Macro"`.
  Inserting `Macro Invocation (smack, macro reference, macro ref);` after
  `Macro (xprompt);` is guaranteed to rewrap that line. The implementer must update the
  allowlist entry to the regenerated line. They must not weaken the guard.
- **The first body line of `glossary/macro.md`**
  (`Formerly called an xprompt. Triggered with ...`). gem and grk propose rewriting this
  sentence, which would break the allowlist. **Append** the cross-reference sentence at
  the end of the body instead, so the allowlisted line stays byte-identical.

The epic `sase-1eq` (xprompts → macros) is still IN_PROGRESS. Phase `.11` ("Cross-repo
audit, guardrail, …") may itself edit this guard. Land this change after `.11` closes,
or rebase onto it and recheck the allowlist.

## Recommended solution

**Add a `Macro Invocation` glossary strand with aliases `smack`, `macro reference`, and
`macro ref`. Add a `Raw Prompt` strand. Point the Macro strand at the new term. Add one
docs paragraph. Change nothing else.**

### Authorization

This research turn does not authorize memory edits, so none were made. To implement,
ask an agent directly ("add the Macro Invocation and Raw Prompt glossary strands per
`research:202610/macro_invocation_glossary_term_smack/macro_invocation_glossary_term_smack__final.md`")
or file a `memory` task bead. The implementing agent must route the edit through
`/sase_memory_write`. This is an XS–S change.

### Macro Invocation strand file

File: `sase/memory/glossary/macro-invocation.md`

```markdown
---
keyword: Macro Invocation
aliases:
  - smack
  - macro reference
  - macro ref
---

A macro invocation (smack) is one `#name` or `#!name` use of a macro in prompt text,
with its arguments and modifiers: `#review(path=a)`, `#review:x`, `#review: text`,
`#flag+`, `#ns/name`, or a standalone `#!sync`. SASE expands or runs it before the agent
sees the prompt. The macro is the definition and the invocation is one use of it; a
prompt can hold zero or many. VCS workspace references such as `#gh:sase` and
`#git:home` are invocations of workspace workflows, and a project tag expands into one.
A `#` token that names no macro passes through as literal text, and one inside a literal
zone is not an invocation. Smack is short for sase macro invocation.
```

Notes:

- The slug `macro-invocation` matches `artifact-reference` and `project-tag`.
- Do not add `type:`, plural aliases, `macro call` (it would mislink "Jinja macro
  call"), or `sase macro invocation`.
- The body must not contain "xprompt" (the terminology guard) or the bare word "ref"
  (it would mislink to Artifact Reference).
- Uniqueness validation is fail-closed: slug, keyword, and aliases must not resolve to
  another strand. None of the proposed names collide today.

### Raw Prompt strand file

File: `sase/memory/glossary/raw-prompt.md`

```markdown
---
keyword: Raw Prompt
---

The raw prompt is an agent's launch prompt after project tags and macro aliases are
canonicalized (`+sase` becomes a `#gh:` workspace reference and `#c` becomes `#commit`)
and before any macro invocation expands. It is saved as `raw_prompt.md`, shown on the
RAW PROMPT tab, and reused by restarts. It follows the submitted prompt
(`submitted_prompt.md`, the launch-boundary text before canonicalization) and precedes
the expanded prompt the model receives, from which directives are stripped. It is
unrelated to `sase prompt show -f raw` and to raw `<label>` placeholders.
```

Every factual claim here was verified: `run_agent_runner_setup_prompt.py`,
`project_aliases.canonicalize_project_aliases_in_prompt` (which expands tags first),
`artifact_files.get_restartable_prompt_content` ("`raw_prompt.md` is authoritative"),
and `PREVIEW_TAB_LABEL = "RAW PROMPT"`.

### Other edits

1. **`glossary/macro.md`:** append one sentence at the end of the body, such as "Each
   use of a macro in a prompt is a macro invocation (smack)." Leave the allowlisted
   first line untouched. The phrase alone creates the implicit link (verified).
2. **`docs/macros.md` → Reference Syntax:** after the opening paragraph, add one
   sentence: "Each `#name` or `#!name` use is a *macro invocation*; the file or config
   entry it names is the macro." Keep the section title and the `#reference-syntax`
   anchor. Leave "smack" out of public docs until it is promoted.
3. **Run `sase memory init`** to regenerate the roster, `AGENTS.md`, and the provider
   shims. Do not hand-edit generated files.
4. **Update the allowlist:** in `tests/_macro_terminology_docs.py`, replace the
   `sase/memory/glossary.md` roster entry with the regenerated line that still contains
   `Macro (xprompt)` (see
   [the terminology guard](#the-terminology-guard-will-trip-and-the-rename-epic-is-still-open)).
5. **Verify:**
   - `sase memory read glossary:smack glossary:raw-prompt -r "<why>"` resolves.
   - The closure includes Macro, Project Tag, and Sase Workspace.
   - A TUI prompt containing "two smacks" underlines the term.
   - Then follow `lint_and_test.md` (guarded `just check`).

### Explicitly out of scope

- Renaming `MacroReference`, `MACRO_REFERENCE_PATTERN`, `raw_prompt.md`,
  `submitted_prompt.md`, the RAW PROMPT tab, the LSP legend, or the
  `Unknown macro reference(s)` toast.
- A `sase smack` command, or any config key or JSON field containing "smack".
- A docs-wide prose sweep.
- **Follow-up, not this change:** a `Directive` strand, so that all four prompt sigils
  have entries.

### When to promote smack to the keyword

Swap `keyword:` and the `smack` alias, regenerate the roster, and update the allowlist
line if **both** of these hold about a month after landing:

1. A grep of new plans, research, and commit messages shows "smack" outnumbering
   "macro invocation" in the text you and your agents actually write.
2. The sase product-rename decision has closed, either with no rename or with a name
   whose derivation you still like.

If either test fails, leave smack as an alias. Lookups and highlighting already work in
both directions.

## Report scope and inputs

**Date:** 2026-10-05 · **Type:** lead consolidation of five independent reports
([cdx](macro_invocation_glossary_term_smack__cdx.md),
[cld](macro_invocation_glossary_term_smack__cld.md),
[grk](macro_invocation_glossary_term_smack__grk.md),
[mus](macro_invocation_glossary_term_smack__mus.md),
[gem](macro_invocation_glossary_term_smack__gem.md)), plus lead verification against
sase `master` @ `8c8c47f720`.

**Question.** Should a SASE macro use site such as `#foo` get its own name, "sase macro
invocation" or **smack** for short? Should that name get a glossary strand? Should the
raw prompt become the "smack prompt"?

## Sources

**Lead verification (this report):**

- A glossary matcher probe using `sase.core.glossary_facade` (`compile_glossary_catalog`,
  `scan_glossary_spans`) over the live `sase/memory/glossary` strands, with and without
  the proposed entries.
- A scan of 710 `raw_prompt.md` files under `~/.sase`, modified in the last 30 days,
  with code spans stripped.
- Files and docs: `src/sase/macros/git.yml`; `src/sase/history/prompt_metadata.py`;
  `src/sase/axe/run_agent_runner_setup_prompt.py`; `src/sase/project_aliases.py`;
  `src/sase/ace/tui/models/artifact_files.py`; `src/sase/macro/highlight.py`;
  `src/sase/memory/web/closure.py`; `tests/_macro_terminology_docs.py`; `docs/macros.md`
  (overview pipeline, Reference Syntax, VCS Workspace References, Editor LSP);
  `docs/memory.md` (Memory Links).
- Audited reads:
  - glossary strands: `macro`, `artifact-reference`, `project-tag`, `strand-keyword`,
    `memory-web`, `core-memory`, `macro-swarm`, `macro-workflow`
  - bead `sase-1eq`
  - `research:202610/sase_rename_new_name_shortlist/sase_rename_new_name_shortlist__final.md`

**Panel reports:** see the links in [report scope and inputs](#report-scope-and-inputs).
External sources cited by the panel include
the [Rust Reference, Macro invocation](https://doc.rust-lang.org/reference/macros.html),
[GNU CPP, Macro Arguments](https://gcc.gnu.org/onlinedocs/cpp/Macro-Arguments.html),
[Linux kernel Smack LSM](https://www.kernel.org/doc/html/latest/admin-guide/LSM/Smack.html),
[SMACK verifier](https://github.com/smackers/smack),
[Wikipedia: Smack (software)](https://en.wikipedia.org/wiki/Smack_(software)), and the
[Google developer style guide on abbreviations](https://developers.google.com/style/abbreviations).
