# Xprompt → Macro: Is "Macro" Really the Better Name?

**Date:** 2026-10-02 · **Epic:** `sase-1eq` · **Plan:** `plan:202610/xprompts_to_macros.md`
· **Status:** in flight (`core-expand` landed in sase-core as `015ce7f`)

> **Verdict: proceed.** "Macro" is the better name, by a clear margin. It says what the
> thing _is_ and _when it happens_. It also removes a mix-up with "prompt" that is
> already measurable in the codebase. Its costs are real but small, and the plan already
> handles them. Four naming refinements (end of report) would make the rename better.
> None of them is a reason to stop.

---

## The Question, Stated Precisely

The name has to label one concept: **a named, parameterized definition that SASE
resolves before an agent sees the prompt.** It is invoked as `#name`, `#name(args)`, or
`#name: text`. It expands recursively into prompt text, swarm segments, or a workflow.

The same word also has to work in five grammatical slots:

- a count noun (`a ___`, `three ___s`)
- a CLI namespace (`sase ___`)
- a config key (`___s:`)
- a directory (`sase/___s/`)
- a modifier (`___ catalog`)

As requested, cost and churn are out of scope. Only the quality of the name is judged.

## Scorecard

| Test                                                   |          `xprompt`           |            `macro`            |
| ------------------------------------------------------ | :--------------------------: | :---------------------------: |
| Self-describing: a newcomer can guess what it is       |  ✗ the `x` is undocumented   |               ✓               |
| Says _who_ resolves it and _when_                      |              ✗               |     ✓ SASE, before launch     |
| Clearly distinct from SASE's _prompt_                  |      ✗ one letter apart      |               ✓               |
| Works as count noun, plural, article, casing           |  ~ "an xprompt", 4 casings   |               ✓               |
| Fits sibling syntax (`%directive`, `@ref`, `+project`) |              ~               |  ✓ same preprocessor family   |
| Stretches to workflows, swarms, skills, memory         | ✗ "a prompt with no prompt"  |  ~ via the automation sense   |
| Free of in-repo collisions                             |              ✓               | ✗ Jinja, query bar, LSP, Rust |
| Unique when grepping                                   |              ✓               |            ✗ noisy            |
| Distinctive outside SASE                               | ~ a 2022 prompt-tuning paper |        ✗ a common word        |

`macro` wins the tests about how people and agents **understand** the concept.
`xprompt` wins only the tests about how **tools find** the word. Understanding matters
more, so `macro` comes out ahead.

---

## Why `macro` Is Better

### 1. It is the textbook name for what SASE does

In computing, a macro is _"a rule or pattern that specifies how a certain input should
be mapped to a replacement output."_ SASE's documented expansion loop is a macro
expander, step for step:

```text
alias substitution
  → fenced-block and disabled-region protection
  → parse → lookup → args → render → substitute   (repeat until no refs remain, ≤100 rounds)
```

It has function-like parameters (`#greet(Alice)`), recursive expansion, and protected
regions. That is the C preprocessor's feature set, plus typed inputs. Some built-ins are
literally macros for other syntax: `#t:5m` expands to `%wait(time=5m)`, and
`#tribe:review` expands to `%id(tribe=review)`. Even the sigil fits, because `#` means
"preprocessor" in C. LLM tooling uses the word the same way: SillyTavern calls its
`{{user}}`/`{{char}}` prompt placeholders _macros_.

### 2. It names the distinction that now matters most: who resolves it, and when

By 2026 the agent ecosystem has settled on **skills** for reusable instructions that the
_agent_ loads at runtime. Claude Code folded custom slash commands into skills. Codex
deprecated custom prompts in favor of skills. SASE has both kinds of reuse, plus
directives:

|                       | Resolved by     | When                             | What the model sees     |
| --------------------- | --------------- | -------------------------------- | ----------------------- |
| **Macro** `#name`     | SASE (the host) | before launch, deterministically | only the expansion      |
| **Directive** `%name` | SASE (the host) | at launch or a step boundary     | nothing (it is control) |
| **Skill** `/name`     | the agent       | at runtime, on demand            | the skill body          |

The word "macro" puts the concept on the right side of that line immediately. "Xprompt"
says nothing about it. A user, or an LLM reading generated instructions, could
reasonably guess that an "xprompt" is something sent _to_ a model.

### 3. "Xprompt" is already confused with "prompt", inside SASE itself

The July 2026 _plang_ study kept `xprompt` partly because the `x` "does useful work": it
marks the concept as distinct from a raw prompt. The codebase shows the opposite:

- `raw_xprompt.md`, `submitted_xprompt`, `get_raw_xprompt_content`, and `xprompt-proc`
  use "xprompt" to mean _the whole authored prompt_, not a definition. That accounts for
  about 180 lines in `src/` alone.
- The agent preview has a tab labeled **`XPROMPT`** next to one labeled **`PROMPT`**.
  There, "xprompt" means _the prompt before expansion_, which is a third meaning.
- `sase prompt` (prompt history) and `sase xprompt` (definitions) are sibling command
  groups whose names differ by one keystroke.

The plan needs a dedicated rule (Rule 2) just to untangle this. The name invited the
drift, and both maintainers and agents followed it. Nobody will mistake a macro for the
prompt itself. Even `sase prompt save` reads better as _save this prompt as a macro_,
like an editor's "record macro".

### 4. It completes a coherent vocabulary

With `macro`, SASE's prompt syntax reads as one metaphor: **a prompt is source code that
a preprocessor handles before launch.**

| Sigil | Term         | Role     |
| ----- | ------------ | -------- |
| `#`   | macro        | expands  |
| `%`   | directive    | controls |
| `@`   | artifact ref | cites    |
| `+`   | project tag  | selects  |

"Macro" and "directive" are the two core words of the C preprocessor, so SASE's existing
term "directive" now has its natural partner. This also makes the best idea in the plang
study work. Its proposed umbrella, _SASE Prompt Language_, now has cleanly named parts.

### 5. It is easier to write, say, and pluralize

`macro` has one casing and takes the article _a_. `macros:`, `sase macro list`, and
`sase/macros/` all read naturally. Today the tree mixes `XPrompt`, `Xprompt`, `xprompt`,
and `XPROMPT`, and contains 139 occurrences of "an xprompt". `xprompt` also isn't unique
in its own field: _XPrompt_ is already an EMNLP 2022 prompt-tuning method.

---

## What `macro` Costs

| Cost                                                                                                                             |    Severity    | Why it is manageable                                                                                                                                                   |
| -------------------------------------------------------------------------------------------------------------------------------- | :------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Jinja collision.** Macro bodies are Jinja, and Jinja has `{% macro %}`.                                                        |      Low       | No definition in sase or chezmoi uses `{% macro %}` (checked). The plan's "Jinja macro" qualifier covers the edge case in the docs.                                    |
| **Grep noise.** `macro` also matches Jinja, `macro_rules!`, tokio `macros`, and LSP token types. "xprompt" had no other meaning. |     Medium     | The terminology guard test and its allowlists replace "grep comes back clean" as the audit tool. Searches for `sase.macro` and `macros:` stay exact.                   |
| **Generic word.** "macro" can't be owned in web search.                                                                          |      Low       | SASE isn't discovered through brand search, and searching "xprompt" mostly finds the 2022 paper.                                                                       |
| **Workflows stretch the word.** A bash-only `#!name` workflow is not a text expansion.                                           |      Low       | It stretches `xprompt` further: a "prompt" with no prompt. In the everyday sense of macro (Excel, Keyboard Maestro, Vim), a macro _is_ an automated sequence of steps. |
| **Connotations.** Office's "macros have been disabled" warning; Vim's recorded macros.                                           |      Low       | If anything these are accurate, since workflows _do_ run code. Neovim commands are prefixed `:Sase…`.                                                                  |
| **Rust keyword.** `macro` is reserved in Rust.                                                                                   | None for users | The plan's `macro_def` and `serde(rename)` rules already handle it.                                                                                                    |

None of these costs makes the name _less accurate_. They are all about tooling and
context, and the plan already addresses each one.

## Why Not Another Word?

SASE's vocabulary is crowded. Every common alternative is already taken or names the
wrong level:

| Candidate                        | Problem                                                                                                         |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| _prompt_                         | Taken: prompt history, `sase prompt`, submitted prompt text.                                                    |
| _template_                       | Taken: Jinja templating, keyed template clans, snippet templates. It also says nothing about inline invocation. |
| _snippet_                        | Taken: TUI snippets. Definitions already have a `snippet:` field, so a snippet is derived _from_ this concept.  |
| _skill_                          | Taken: skills are _generated from_ these definitions.                                                           |
| _command_                        | Overloaded (CLI commands, `$(…)` substitution, gate commands), and it suggests the agent invokes it at runtime. |
| _recipe_ / _routine_             | Taken: `just` recipes, guarded recipes, Lumberjack routines.                                                    |
| _workflow_ / _part_ / _fragment_ | These name subtypes, not the umbrella.                                                                          |

`macro` is the strongest available word. It is also the only candidate that describes
the mechanism.

---

## Refinements Worth Making During the Rename

1. **Put "macro" last when naming a _kind_ of macro.** The prefix _macro-_ also means
   "large-scale", so "Macro Swarm", "Macro Memory", "Macro focus", and especially
   **"mini-macro pane"** (an oxymoron) read badly. For glossary keywords, prefer
   **swarm macro, workflow macro, memory macro, Markdown macro**. In the TUI, prefer
   **macro mini-pane** and **Macro usage**. Keep "macro" first when it means "of macros":
   _macro catalog_, _macro LSP_, _macro skill_.
2. **Rethink "shorthand" for the query bar's `%w`/`%d` tokens.** Macros already use
   that word. The docs have a _Shorthand Syntax_ section for `#name: text` and
   `#name:: text`, and built-ins such as `#t:5m` are documented as "shorthand for
   `%wait`". _Status abbreviations_ collides with nothing.
3. **Open the docs with the contract.** On first mention, use one sentence: _"A macro is
   a named prompt definition that SASE expands before the agent sees the prompt."_
   Follow it with the macro / directive / skill table above. Say "prompt macro" once in
   the page title or opening line, so readers still connect macros to prompts.
4. **Consider aligning the LSP semantic tokens later (optional).** Today `%directive`
   names get the LSP `macro` token type, and `#macro` references get `function`. Keeping
   that for theme stability is defensible. Still, it is now the one place where the
   editor contradicts the docs. It belongs in a follow-up bead, not in this epic.

## Recommendation

**Proceed with the rename.** Compared with `xprompt`, `macro` is:

- more accurate about the mechanism
- easier for both people and agents to learn
- impossible to confuse with _prompt_
- a natural partner for `%directive` and the rest of SASE's prompt syntax

`xprompt` is better in only two narrow ways: it is unique when grepping, and it collides
with nothing. Those properties help tools, not understanding, and the plan's guard tests
make up for losing them.

**Reopen this decision if** standalone `#!` workflows that never expand become most of
the catalog, or SASE gains a second expansion mechanism with a stronger claim to the
word.

---

## Sources

**Local (this workspace):** `plan:202610/xprompts_to_macros.md` (Rule 2, vocabulary,
existing-macro meanings); `plan:202610/core_macro_expand.md`;
`research:202607/xprompt_plang_rename_consolidated.md`; `docs/xprompt.md` (expansion
model, Shorthand Syntax, Snippet/Skill/Memory fields, Relationship to Workflows);
`docs/editor.md` (semantic-token table); `src/sase/main/parser_prompt.py`
(`sase prompt save`); `src/sase/ace/tui/widgets/agent_header_preview.py`
(`PREVIEW_TAB_LABEL = "XPROMPT"`); glossary strands `xprompt`, `xprompt-part`,
`xprompt-swarm`, `xprompt-workflow`, `xprompt-memory`, `project-tag`; chezmoi
`home/sase/xprompts/` (Jinja `{% macro %}` audit).

**External:**

- Macro (computer science), definition — <https://en.wikipedia.org/wiki/Macro_(computer_science)>
- SillyTavern, _Macros_ — <https://docs.sillytavern.app/usage/core-concepts/macros/>
- OpenAI Codex, _Custom Prompts_ (deprecated in favor of skills) —
  <https://developers.openai.com/codex/custom-prompts>
- _Custom slash commands in Claude Code: how they work now that commands are skills_ —
  <https://dev.to/rulestack/custom-slash-commands-in-claude-code-how-they-work-now-that-commands-are-skills-425k>
- Google Cloud, _Gemini CLI custom slash commands_ —
  <https://cloud.google.com/blog/topics/developers-practitioners/gemini-cli-custom-slash-commands>
- GitHub Docs, _Your first prompt file_ —
  <https://docs.github.com/en/copilot/tutorials/customization-library/prompt-files/your-first-prompt-file>
- Ma et al., _XPrompt: Exploring the Extreme of Prompt Tuning_, EMNLP 2022 —
  <https://aclanthology.org/2022.emnlp-main.758/>
