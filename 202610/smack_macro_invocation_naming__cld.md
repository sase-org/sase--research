# Naming `#foo`: "Smack", "Macro Invocation", and the "Smack Prompt"

**Date:** 2026-10-05 · **Researcher:** cld · **sase:** `master` @ `6fde796604`

**Question.** Should SASE give the `#foo` construct its own name? The proposal is
**smack**, short for "**s**ase **mac**ro invo**c**ation". The "k" comes from the "kay"
sound in "invocation". The proposal also has two follow-ons: add a glossary strand, and
start calling the raw prompt the "smack prompt". Is this a good idea? What is the best
way to do it?

---

## Bottom Line

1. **Naming the construct: yes, do it.** Today the use site of a macro has no stable
   name. Docs and code use five competing phrases. The most common one, "macro
   reference", reuses SASE's most overloaded word. A glossary strand fixes this for the
   cost of one small memory commit.
2. **"Smack" as the canonical term: no. Keep it as an alias instead.** Make the strand's
   keyword **Macro Invocation** and list `smack` as an alias. "Macro invocation" is the
   industry-standard name for exactly this thing, and SASE's own highlighter already
   uses it. The glossary roster, TUI, and LSP will still recognize and link "smack"
   wherever you use it. If smack proves itself in daily use, promoting it to the
   keyword later is a one-line frontmatter change.
3. **"Smack prompt" for the raw prompt: no.** In a sample of 690 recent raw prompts,
   `%` directives were just as common as `#` invocations. The sample also showed that
   `+project` tags are rewritten into `#gh:` invocations before `raw_prompt.md` is
   written. Naming the whole authored prompt after one of its sigils repeats the
   mistake that `raw_xprompt.md` made, which the xprompt→macro rename fixed
   **three days ago**. Add a **Raw Prompt** glossary strand that defines the three
   prompt stages instead.

The rest of this report gives the evidence, the full critique, the requirement changes
I made (each marked **ADJUSTMENT**), and an implementation recipe. The final section is
the recommended solution.

---

## 1. What Exactly Needs a Name

The concept is the **use site** of a macro in prompt text, as opposed to the macro
**definition** (the `Macro` strand). Concretely, it is one `#`-sigil construct that SASE
resolves through the macro registry before the agent sees the prompt:

| Form                                        | Example                       | A use site? |
| ------------------------------------------- | ----------------------------- | ----------- |
| bare, parenthesized, colon, plus            | `#plan`, `#greet(Alice)`, `#review:x`, `#flag+` | yes |
| line shorthands (the payload is part of it) | `#review: text`, `#review:: text`   | yes |
| namespaced, including memory macros         | `#ns/name`, `#memory/foo`     | yes         |
| VCS workspace refs (these are macros too)   | `#gh:sase`, `#git:home`       | yes         |
| standalone workflow launch                  | `#!sync`                      | yes         |
| `#`-shaped token matching no macro          | `#typo`                       | an *unresolved* one; passes through as literal text |
| inside inline code, fences, disabled region | `` `#plan` ``                 | **no**      |
| `+project` tag                              | `+sase`                       | **no**; it *expands into* a `#gh:` use site |
| Jinja macro call inside a macro body        | `{{ m() }}`                   | **no**      |

Any name you pick must cover all the "yes" rows. "Smack" and "macro invocation" both
can. The table belongs in the strand's definition so the boundary cases get settled
once.

## 2. Evidence: The Gap Is Real

### 2.1 Five names for one thing

| Phrase in this repo                   | Where it lives                                                                       | Count            |
| ------------------------------------- | ------------------------------------------------------------------------------------ | ---------------- |
| "macro reference(s)"                  | docs prose (~35 lines; 15 in `docs/macros.md`), docstrings, the TUI toast `Unknown macro reference(s): #foo …` (`src/sase/macro/unresolved.py:108`) | 109 prose hits |
| `macro_reference` identifiers         | `process_macro_references`, `iter_macro_references`, `scan_macro_references`, …      | 379              |
| "macro invocation" / `macro.invocation` | the highlight role at `src/sase/macro/highlight.py:24`; docstrings in `workflows/crs.py`, `workflows/mentor.py` | 15 |
| "macro call" / `_MacroCall`           | two private `_MacroCall` classes, `extract_macro_calls`, `build_macro_call`, and the LSP docs' "A call that is still being typed" | 58 |
| "macro usage" / "used macros"         | `used_macros.py`, `macros.json` capture                                              | 7+               |

The agent-facing memory note `macros.md` titles its syntax section **"Invoke"**. The docs
title the same material **"Reference Syntax"**. The LSP legend calls it "Macro reference
name", and the highlighter calls it `macro.invocation`. Nobody has picked a term, so each
author has used a different one.

### 2.2 "Reference" is SASE's most overloaded word

A "macro reference" competes with all of these:

- **Artifact Reference**, whose glossary alias is literally **`ref`** (`@kind:arg`)
- **Reference Memory** (`type: reference`)
- **VCS Workspace References** (`#gh:<ref>`, where `<ref>` is a branch or Patch)
- `@name` **agent references** inside `#gh:@planner`
- memory **`[[...]]` references** and the "Linked References" section

So "macro ref" and "artifact ref" are one word apart and mean different sigils. That is
a concrete reason to stop saying "macro reference". It supports the motivation behind
your proposal.

### 2.3 The sibling sigils already have instance names

| Sigil | Instance noun                         | Glossary strand?                |
| ----- | ------------------------------------- | ------------------------------- |
| `@`   | artifact reference (ref)              | yes                             |
| `+`   | project tag                           | yes                             |
| `%`   | directive                             | **no** (only in `macros.md`)    |
| `#`   | ??? (the definition is "Macro")       | **no**                          |

`Artifact` → `Artifact Reference` is the exact pattern the `#` sigil is missing:
`Macro` → **`Macro Invocation`**.

## 3. Critique of "Smack" as the Canonical Term

### 3.1 What smack gets right

- **It is short.** One syllable, compared with seven for "macro invocation". That
  matters in speech, in chat with agents, and in commit subjects.
- **It is unique.** It has zero hits in the repo, so grep, the glossary phrase matcher,
  and a reader's eye all find it immediately.
- **It works in every grammatical slot**: "a smack", "three smacks", "smack args",
  "an unresolved smack". It even works as a verb: "smack `#plan` into the prompt".
- **It is memorable**, and the glossary UX makes coined words cheaper than they used
  to be. A strand alias is underlined in the TUI prompt pane and in editors through the
  LSP (`SaseGlossaryTerm`), `Ctrl+]` / `gG` jump to its definition, and the
  always-loaded roster shows it next to its keyword.

### 3.2 Why it should not be the keyword

1. **It fails the "definition stops translating" test.** SASE's own September naming
   criteria (`research:202609/sase_terminology_renames/sase_terminology_renames.md`)
   say: *if the glossary has to say "an X is basically a Y", then Y is probably the
   name.* The smack strand would have to open with "A smack is a sase macro
   invocation." By that test, the name is "macro invocation".

2. **The derivation is not recoverable.** The initialism is SMI. Getting from there to
   "smack" means borrowing a phoneme from the middle of "invocation", which your own
   proposal had to explain. Nobody, human or LLM, will reconstruct the meaning from
   the word. That is the same problem the prior verdict raised against xprompt (*"the
   `x` is undocumented"*), and it was one reason for that rename
   (`research:202610/xprompt_to_macro_naming_verdict.md`).

3. **It runs against eight months of SASE naming history.** Here is what was retired
   and what survived:

   | Retired (opaque or mismatched)                    | Replaced by                        |
   | ------------------------------------------------- | ---------------------------------- |
   | ACE, AXE (acronyms)                               | TUI, scheduler                     |
   | xprompt (opaque coinage)                          | macro (landed 2026-10-03)          |
   | chop, lumberjack (metaphor didn't match)          | job, routine                       |
   | agent family, sase shell (metaphor didn't match)  | agent session, sase turn           |

   The whimsical terms that survived (stitch/Patch, hood/clan/tribe, deck/card) all
   belong to coherent metaphor families. A stitch is part of a patch, and a hood sits
   inside a clan. "Smack" is a backronym with no metaphor family, which is the same
   category as ACE and AXE. Past behavior predicts it would be renamed later.

4. **The "s" depends on a name that may change.** The 2026-10-04 consolidated report
   `research:202610/sase_rename_new_name_shortlist/sase_rename_new_name_shortlist__final.md`
   recommends **renaming sase itself** within a two-week decision window (top pick:
   `handful`). If that happens, "smack" loses its first letter's meaning. At the very
   least, do not tie a new coinage to the word "sase" before that decision lands.

5. **It collides outside the repo and carries slang.** **SMACK** is a mainline Linux
   security module (Simplified Mandatory Access Control Kernel, used in Tizen and
   Automotive Grade Linux). **Smack** is also a long-lived Java XMPP client library, and
   "SMACK stack" was a big-data buzzword. In everyday English it means a slap, it is
   slang for heroin, and it appears in "smack talk". None of these matter inside the
   TUI. They do matter on the public sase.sh docs and blog, which agents edit and which
   would carry the keyword spelling.

6. **The keyword is the default spelling everywhere.** Agents writing docs, commit
   messages, and plans copy the keyword. An alias is something they *recognize*. A
   keyword is something they *produce*. Putting "smack" in the keyword slot turns your
   shorthand into public vocabulary.

### 3.3 Scorecard

| Test                                                  | `smack`                                | `macro invocation`                          |
| ----------------------------------------------------- | :------------------------------------: | :-----------------------------------------: |
| A newcomer or LLM can guess what it is                | ✗                                      | ✓ (Rust Reference, GCC cpp manual)          |
| Distinct from definition ("macro")                    | ✓                                      | ✓                                           |
| Distinct from `@` artifact "ref"                      | ✓                                      | ✓                                           |
| Already used in the codebase with this meaning        | ✗ (0 hits)                             | ✓ (`macro.invocation` role, `## Invoke`)    |
| Brevity in speech and chat                            | ✓✓                                     | ✗                                           |
| Fits the trend of retiring opaque coinages            | ✗                                      | ✓                                           |
| Survives a SASE product rename                        | ✗                                      | ✓                                           |
| Free of external collisions and slang                 | ✗                                      | ✓                                           |
| Grep-unique                                           | ✓                                      | ~ (5 prose hits today, all the same meaning) |

Smack wins on brevity and uniqueness. Macro invocation wins on understanding. Prior
SASE naming verdicts have consistently ranked understanding higher. The alias approach
in §6 keeps smack's brevity for you without paying its understanding cost in the docs.

## 4. Critique of "Smack Prompt" for the Raw Prompt

### 4.1 The raw prompt is one of three stages, and smacks are not what defines it

From the code (`src/sase/axe/run_agent_runner_bootstrap.py`,
`src/sase/axe/run_agent_runner_setup_prompt.py`):

| Stage                     | Artifact               | Contents                                                                                     |
| ------------------------- | ---------------------- | -------------------------------------------------------------------------------------------- |
| **Submitted prompt**      | `submitted_prompt.md`  | exact launch-boundary text, with no alias or macro processing                                |
| **Raw prompt**            | `raw_prompt.md`, shown as `AGENT RAW PROMPT` | after project-alias canonicalization and macro-alias resolution (`#c` → `#commit`), **before** macro expansion |
| **Agent prompt**          | `AGENT PROMPT` section | the expanded text the model receives, with directives stripped                               |

Two of the three stages are unexpanded, so both contain smacks. "Smack prompt" cannot
tell submitted and raw apart, and that distinction is the one people actually get wrong.

### 4.2 Data: what raw prompts actually contain

I scanned the 690 `raw_prompt.md` files under `~/.sase` modified in the last 30 days.
Fenced and inline code were stripped before scanning.

| Construct                               | Share of raw prompts |
| --------------------------------------- | -------------------: |
| any `%` directive                       | **100%** (`%auto` 79%, `%model` 70%, `%id` 54%, `%queue` 47%) |
| any `#` invocation                      | 99.7%                |
| of which `#gh:`/`#git:` workspace refs  | 66.7% (many come from `+project` canonicalization or launch setup, not hand-typed) |
| `@kind:` artifact reference             | 0.3%                 |
| `+project` tag                          | **0%**, because tags are canonicalized to `#gh:` before `raw_prompt.md` is written |

Raw prompts are as much "directive prompts" as "smack prompts". Many are also
machine-written (epic phase workers, research swarms). Naming the stage after one sigil
picks an arbitrary feature, not a defining one. A hand-written prompt like
`sase run "fix the flaky test"` contains no user-written smack at all, yet it still
has a raw prompt.

### 4.3 This is the xprompt mistake repeating

The prior verdict found that `raw_xprompt.md`, `submitted_xprompt`, and an `XPROMPT`
preview tab had borrowed the *definition* word to mean *the whole authored prompt*. It
called this "a third meaning" that "the name invited". The rename fixed it to
`raw_prompt.md` / `RAW PROMPT`, landed on 2026-10-03, and still has phases in flight
(`sase-1eq.10`, `sase-1eq.11`). "Smack prompt" would bring the same conflation back one
level down, with the invocation word standing in for the prompt.

### 4.4 It is also expensive where "smack" is cheap

`raw_prompt.md` is a durable artifact filename with legacy readers
(`legacy_xprompt_names.py`). `AGENT RAW PROMPT` is a TUI section heading, a pager key,
a goldens subject, and a config-schema description. Renaming it would need another
expand/contract cycle, the kind of epic described in `plan:202610/xprompts_to_macros.md`.
A glossary-only "smack" costs nothing to back out. A "smack prompt" UI rename does.

### 4.5 A better framing if you want new vocabulary here

If the goal is to talk about the *language* the raw prompt is written in, that is the
umbrella the July plang study proposed: **SASE prompt syntax**, with `#` invocations,
`%` directives, `@` refs, `+` tags, `<label>` placeholders, and `---` segments. If you
ever want a stage name that fits the macro/preprocessor metaphor, **source prompt** →
**expanded prompt** fits better than "smack prompt". I do **not** recommend renaming
now. A Raw Prompt strand fixes the actual confusion for free.

## 5. Alternatives Considered

| Candidate             | Verdict | Why |
| --------------------- | ------- | --- |
| **Macro Invocation**  | **Pick** | The standard term (Rust Reference's "Macro invocation" grammar; the GCC cpp manual's "invoke a macro that takes arguments"). It is already the highlighter role and the memory note's "Invoke" heading, and it pairs with `Macro` the way `Artifact Reference` pairs with `Artifact`. |
| smack                 | Alias   | See §3. Great for speech, wrong as the published default. |
| macro reference / macro ref | Alias only | This is the incumbent prose term, but "reference"/"ref" collides with Artifact Reference (alias `ref`), Reference Memory, workspace refs, and memory links. |
| macro call            | Alias only | Standard (GCC), and matches `_MacroCall`, but "call" collides with "LLM Calls" and tool calls, and the prior research recommends renaming LLM Calls to "Tool Calls". |
| invocation (bare)     | Reject  | 994 repo hits: CLI invocation, provider `_invoke`, tool invocation. |
| hash / hashtag / tag  | Reject  | "Tag" is already used by project tags, macro `tags:`, and VCS tags; "hash" means commit SHAs. |
| just say "macro"      | Viable fallback | This is how C programmers talk, by metonymy. It works casually but cannot resolve "the macro's args" (definition inputs) vs "the invocation's args" (actual values), which is exactly where LSP diagnostics and docs need precision. |

## 6. Requirement Adjustments (Called Out)

- **ADJUSTMENT 1: keyword `Macro Invocation`, with `smack` as an alias.** You asked
  for "smack" as *the* name. I am moving it to an alias. You keep the word: the roster
  renders `Macro Invocation (smack, …)`, `sase memory read glossary:smack` resolves,
  and the TUI and LSP underline it and jump to its definition. Docs and agents keep
  writing the self-describing form. If you later want to promote it, swap `keyword:`
  and `aliases:`. Lookups by either spelling keep working.
- **ADJUSTMENT 2: drop "smack prompt", and add a `Raw Prompt` strand instead.** The
  strand defines submitted → raw → agent prompt. That fixes the actual stage confusion
  without renaming a durable artifact.
- **ADJUSTMENT 3: hard scope boundary.** The new word stays in the glossary and prose
  docs only. There are no code-identifier renames (`macro_reference` stays: 379
  occurrences, not worth an epic), no CLI, config, filename, or JSON changes, and no
  TUI label changes in this step. Prior renames show that crossing this line turns a
  vocabulary decision into a multi-repo epic.
- **ADJUSTMENT 4: do not tie a coinage to "sase" yet.** Leave `sase macro invocation`
  out of the alias list, since `macro invocation` already matches that phrase. Revisit
  any smack promotion only after the SASE product-rename decision window closes
  (about 2026-10-18).
- **ADJUSTMENT 5 (optional, same commit or next): add a `Directive` strand.** `%` is
  the only prompt sigil without a glossary entry. Filling it gives all four sigils
  (`#`, `%`, `@`, `+`) a strand, so the glossary can describe SASE prompt syntax as a
  whole. That supports "new ways of talking about this topic" better than one coinage
  would.
- **ADJUSTMENT 6: sequence the docs prose sweep after `sase-1eq` lands.** Phases
  `sase-1eq.10` and `sase-1eq.11` (core flip, terminology guard) are still in progress
  and edit the same docs. Change "macro reference" → "macro invocation" in about 35
  docs lines afterward, keeping the `#reference-syntax` anchor. The toast string
  `Unknown macro reference(s)` is optional and needs a test or golden check.

## 7. How to Implement

### 7.1 Authorization path

Memory changes need explicit authorization: your prompt for that turn, an approved
plan, or a bead. This research turn is not authorization, so **no memory was
changed**. When you decide, either ask an agent directly ("add the Macro Invocation
glossary strand per research:…__cld.md") or file a `memory` task bead.

### 7.2 Mechanics (glossary web)

1. Create `sase/memory/glossary/macro-invocation.md`. The slug is its identity. The
   keyword and aliases go in frontmatter, and other strands use the same pattern.
2. Run `sase memory init`. This regenerates `AGENTS.md`, the provider shims, and the
   roster line. It adds roughly 10–15 tokens to every agent's always-loaded context,
   and nothing else, because strand bodies are read on demand.
3. Because `glossary` uses `link_reference: implicit`, the alias `macro ref`
   automatically links the **Project Tag** strand ("expands to the project's VCS
   macro ref") to the new strand. That is correct: a project tag expands *into* a
   macro invocation. Also author explicit `[[glossary:macro]]`,
   `[[glossary:artifact-reference]]`, and `[[glossary:project-tag]]` links in the
   body.
4. The LSP and TUI glossary catalogs pick up the new phrase on their next refresh.
   "smack", "macro invocation", and "macro reference" in prompt text then get the
   glossary token, `SaseGlossaryTerm` underline, and `Ctrl+]` jump. Verify it in a
   prompt pane.
5. If the phrase matcher doesn't stem, add plural aliases. There is precedent:
   `chops`, `agent tabs`, `project tags`.

### 7.3 Draft strand: `glossary/macro-invocation.md`

```markdown
---
keyword: Macro Invocation
aliases:
  - smack
  - smacks
  - macro invocations
  - macro reference
  - macro references
  - macro ref
  - macro call
---

A macro invocation (smack) is one `#` use site in prompt text that names a
[[glossary:macro]] for SASE to expand before the agent sees the prompt: `#name`,
`#name(args)`, `#name:arg`, `#name+`, the line shorthands `#name: text` and
`#name:: text` (whose payload belongs to the invocation), namespaced `#ns/name` and
`#memory/<stem>`, VCS workspace refs such as `#gh:sase`, and standalone `#!name`
workflow launches. The macro is the definition; the invocation supplies its actual
arguments. A `#` token matching no macro is an unresolved invocation and passes
through as literal text; one inside a literal zone is not an invocation. Not a `%`
directive, an `@` [[glossary:artifact-reference]], a `+` [[glossary:project-tag]]
(which expands into a workspace invocation), or a Jinja macro call in a macro body.
Formerly called a macro reference.
```

### 7.4 Draft strand: `glossary/raw-prompt.md`

```markdown
---
keyword: Raw Prompt
aliases:
  - raw prompts
---

A raw prompt is an agent's authored prompt after project-alias canonicalization and
macro-alias resolution but before any [[glossary:macro-invocation]] expands. It is
stored as `raw_prompt.md` and shown as AGENT RAW PROMPT. It follows the submitted
prompt (`submitted_prompt.md`, the exact launch-boundary text) and precedes the agent
prompt (AGENT PROMPT: the expanded text the model receives, directives stripped).
`+project` tags are already rewritten to `#gh:`/`#git:` invocations here. Unrelated to
raw placeholders (`<label>` tags).
```

### 7.5 What not to do

- Do not rename `macro_reference` identifiers, `raw_prompt.md`, `AGENT RAW PROMPT`, the
  LSP legend's token types, or the docs anchor `#reference-syntax`.
- Do not use "smack" in CLI help, config keys, JSON fields, or public docs prose. Only
  the glossary strand mentions it.

## 8. Recommended Solution

**Adopt a canonical name for `#foo` use sites now, as a glossary strand only. The
keyword is `Macro Invocation` and `smack` is its alias. Reject "smack prompt" in favor
of a `Raw Prompt` strand.**

Concretely, in one small authorized memory change:

1. Add `glossary/macro-invocation.md` (draft in §7.3). Its aliases are `smack`,
   `macro reference(s)`, `macro ref`, and `macro call`, so every current spelling,
   including yours, resolves and links to it.
2. Add `glossary/raw-prompt.md` (draft in §7.4), defining submitted → raw → agent
   prompt.
3. Optionally add a `Directive` strand so all four prompt sigils have entries.
4. Run `sase memory init`.
5. After `sase-1eq` lands, sweep about 35 docs lines from "macro reference" to "macro
   invocation". Leave code identifiers, durable filenames, and TUI labels alone.

Say "smack" in conversation and prompts all you like. The glossary makes it a
first-class, linked synonym. **Reopen the keyword choice** if both of these hold after
the SASE product-rename decision closes: "smack" has become the spelling that you and
your agents actually use in plans and commit messages, and the new product name still
fits its derivation. Then swap `keyword:` and `aliases:`. That costs one line and loses
nothing.

---

## Sources

**Local (audited reads):** `sase memory read glossary:{macro, macro-part,
macro-swarm, macro-workflow, macro-memory, project-tag, artifact-reference,
memory-web, job, routine, agent-hood, …}`; `sase memory read macros.md`;
`sase artifact read research:202610/xprompt_to_macro_naming_verdict.md`,
`research:202607/xprompt_plang_rename_consolidated.md`,
`research:202609/sase_terminology_renames/sase_terminology_renames.md`,
`research:202610/sase_rename_new_name_shortlist/sase_rename_new_name_shortlist__final.md`,
`plan:202609/axe_routines_jobs.md`, `plan:202610/xprompts_to_macros.md`;
`sase bead read sase-11e`, `sase-1eq`.

**Code and docs:** `docs/macros.md` (Reference Syntax, Raw Prompt Placeholders,
Renamed from xprompts), `docs/editor.md` (semantic token legend), `docs/memory.md`
(Memory Webs), `src/sase/macro/highlight.py:24`, `src/sase/macro/unresolved.py:108`,
`src/sase/axe/run_agent_runner_setup_prompt.py`,
`src/sase/axe/run_agent_runner_bootstrap.py`, `src/sase/legacy_xprompt_names.py`.

**Data:** 690 `raw_prompt.md` files under `~/.sase` (mtime ≤ 30 days), sigil scan with
code zones stripped.

**External:**

- [The Rust Reference: Macros (macro invocation)](https://doc.rust-lang.org/reference/macros.html)
- [GCC, The C Preprocessor: Macro Arguments](https://gcc.gnu.org/onlinedocs/cpp/Macro-Arguments.html)
- [Linux kernel docs: Smack](https://www.kernel.org/doc/Documentation/security/Smack.txt)
- [Wikipedia: Smack (software)](https://en.wikipedia.org/wiki/Smack_(software))
- [LWN: Smack for simplified access control](https://lwn.net/Articles/244531/)
