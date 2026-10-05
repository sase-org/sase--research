# Macro Invocations, "Smack", and Prompt Terminology: Analysis and Recommendations

**Date:** 2026-10-05 · **Author:** Researcher `gem` (5-Researcher Swarm) · **Status:** Complete  
**Topic:** Formalizing SASE Macro Invocation Naming (`#foo`), Critiquing the "Smack" / "Smack Prompt" Proposal, and Defining the Canonical Glossary Strand

---

## Executive Summary

> **Verdict: Proceed with formalizing the concept, but reject "smack" and "smack prompt".**
>
> 1. **The core goal is sound:** Giving the call-site syntax (`#foo`, `#!foo`, `#foo(args)`) a distinct, standardized name solves a real ambiguity. Today, "macro" refers simultaneously to the definition file (`.md` or `.yml`), the subsystem, and the inline token. A dedicated term clarifies communication, parser mechanics, and agent instructions.
> 2. **"Smack" is fundamentally flawed:** While phonetically punchy, "smack" suffers from:
>    - **Severe negative external connotations:** Worldwide street slang for heroin, physical violence ("give someone a smack"), and hostility ("talking smack"). SASE's terminology is built on craft, woodworking, structural mechanics, and community (`stitch`, `bead`, `axe`, `chop`, `deck`, `card`, `tribe`, `hood`), not illicit substances or physical assault.
>    - **Forced orthography:** S-M-A-C-K relies on an orthographic excuse ("invocation has the sound 'kay' in it") that requires explanation every time it is introduced.
>    - **Agent / LLM cognitive degradation:** Modern frontier LLMs understand standard computer science terminology natively. Invented slang degrades agent instruction fidelity, increases token overhead in system memory, and raises hallucination risk.
> 3. **"Smack prompt" is a serious architectural category error:**
>    - A prompt is an outer container; a macro invocation is an optional inner expression.
>    - Many prompts contain zero macros (e.g., `+sase %m:sonnet review the diff`). Labeling prompts "smack prompts" is a false synecdoche.
>    - SASE recently completed a major migration from `xprompt` to `macro`, specifically eliminating `raw_xprompt.md` in favor of `raw_prompt.md`. Re-branding raw prompts to "smack prompts" recreates the exact semantic defect that was just painstakingly removed.
> 4. **Recommended Solution:**
>    - Adopt **`Macro Reference`** (abbreviated in common speech as **`macro ref`**) as the canonical primary term.
>    - Accept **`Macro Invocation`** and **`Macro Call`** as official, formal synonyms.
>    - Add the glossary memory web strand `sase/memory/glossary/macro-reference.md` (`keyword: Macro Reference`, `aliases: [macro ref, macro invocation, macro call]`).
>    - Preserve `raw_prompt` and `submitted_prompt` without modification.

---

## 1. The Problem: What Needs Naming?

In SASE's prompt architecture, several related but distinct concepts currently compete for the word "macro":

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          PROMPT TAXONOMY                               │
├────────────────────────────────┬───────────────────────────────────────┤
│ Concept                        │ Current Concrete Representation       │
├────────────────────────────────┼───────────────────────────────────────┤
│ 1. Macro Definition (Template) │ sase/macros/foo.md (Macro Part)       │
│                                │ sase/macros/bar.yml (Macro Workflow)  │
├────────────────────────────────┼───────────────────────────────────────┤
│ 2. Call-Site Token / Syntax    │ #foo, #foo(args), #foo: text, #!foo   │
│    (The subject of this study) │ Currently: "macro", "macro reference" │
├────────────────────────────────┼───────────────────────────────────────┤
│ 3. Preprocessing Mechanism     │ macro expansion (lookup -> substitute)│
├────────────────────────────────┼───────────────────────────────────────┤
│ 4. Prompt Container            │ raw prompt -> submitted prompt        │
└────────────────────────────────┴───────────────────────────────────────┘
```

When users or agent prompts say:
- *"Add a macro to the prompt"* -> Do they mean authoring a new `.md` file, or inserting the `#foo` token into the input string?
- *"The macro failed"* -> Did the Jinja template fail to compile, did the parser fail to match `#name`, or did the expanded agent task fail?

In programming language theory, separating the **definition** from the **call-site reference / invocation** is standard:
- Function declaration vs. Function call / invocation.
- Macro definition (`#define FOO` / `macro_rules! foo`) vs. Macro invocation / call (`FOO()` / `foo!()`).

Furthermore, in SASE's prompt language, other tokens already possess clear, symmetric two-word names:
- `@ref` / `@file:...` → **Artifact Reference** (`ref`)
- `#git:...` / `#gh:...` → **Workspace Reference** (`workspace ref`)
- `%auto` / `%wait` → **Directive**
- `+sase` → **Project Tag**
- `#name` / `#!name` → **Currently unanchored in the glossary!**

While `Artifact Reference` and `Project Tag` have dedicated strands in `sase/memory/glossary/`, the `#name` call-site syntax currently has no strand of its own. Adding one is an undeniable improvement to SASE's knowledge base.

---

## 2. In-Depth Critique of the "Smack" Proposal

The user proposal suggests naming the macro invocation "sase macro invocation", abbreviated as **"smack"** (noting that "invocation" has the sound "kay" in it), and extending this to refer to the "raw prompt" as the "smack prompt".

Below is an objective evaluation of this proposal across linguistic, social, architectural, and agentic dimensions.

### 2.1 Forced Phonetics and Orthographic Friction
The justification provided is:
> *"sase macro invocation" (aka "smack"--note that "invocation" has the sound "kay" in it)*

- An acronym or abbreviation works best when it is either a direct initialism (e.g., `SMI` for SASE Macro Invocation) or a natural syllabic portmanteau.
- Deriving `S-M-A-C-K` requires:
  - `S` = SASE
  - `M` = Macro
  - `A` = ? (Unaccounted for; perhaps "Action" or "Application"?)
  - `C` / `K` = "invoCation" (taking a middle hard 'c' sound and spelling it as 'k')
- If a technical term requires an explicit explanatory parenthetical every time someone learns it (*"note that invocation has the sound 'kay' in it"*), it reveals that the abbreviation is artificially forced rather than natural.

### 2.2 Harmful Connotations and Professionalism
SASE already possesses a rich, distinctive, and slightly whimsical terminology. However, examining SASE's existing vocabulary reveals a very clear thematic pattern:
- **Craft, Textiles, & Tailoring:** `stitch`, `Patch`
- **Measurement & Counters:** `bead`
- **Forestry, Woodcraft, & Carpentry:** `lumberjack`, `axe`, `chop`
- **User Interface & Structure:** `deck`, `card`, `node`, `panel`
- **Community & Coordination:** `hood`, `clan`, `tribe`

Every single established metaphor in SASE is grounded in **constructive work, physical craftsmanship, or social organization**.

In stark contrast, **"smack"** introduces immediate, severe negative connotations:
1. **Illicit Narcotics:** In the English-speaking world, "smack" is one of the most widely recognized street slang terms for **heroin**. Introducing "smack" into a software engineering platform creates bizarre, jarring phrases:
   - *"Inject the smack into your prompt."*
   - *"Agent failed due to a bad smack."*
   - *"Did you inspect the smacks?"*
2. **Violence / Physical Blow:** "Smack" means a sharp physical slap or strike (*"smack someone across the face"*).
3. **Hostility / Trash Talk:** "Talking smack".

In enterprise environments, customer demos, academic papers, open-source repositories, and developer documentation, using "smack" damages credibility and causes unnecessary discomfort or humor at the expense of clarity.

### 2.3 The "Smack Prompt" Category Error
The proposal suggests:
> *"we could start referring to the 'raw prompt' as the 'smack prompt'."*

This is the most technically problematic aspect of the idea. It commits a classic **part-for-whole fallacy (faulty synecdoche)**:

1. **Prompts without macros are common:**
   Users regularly write prompts like:
   ```text
   +sase %m:sonnet Fix the regression in test_queue.py
   ```
   or:
   ```text
   Review this commit diff and check for edge cases
   ```
   This prompt contains a project tag (`+sase`), a directive (`%m:sonnet`), and natural language. It contains **zero** macros. Calling this a "smack prompt" is completely nonsensical.
2. **Re-introducing the exact defect fixed in the `xprompt -> macro` migration:**
   Just days ago, in epic `sase-1eq`, SASE completed a major codebase-wide rename from `xprompt` to `macro` (documented in `xprompt_to_macro_naming_verdict.md`).
   A central achievement of that migration was fixing the misleading legacy terminology where the entire prompt was conflated with xprompts:
   - `raw_xprompt.md` was renamed to `raw_prompt.md`.
   - `submitted_xprompt.md` was renamed to `submitted_prompt.md`.
   This was done because developers and agents were confused into believing that every prompt was an "xprompt", or that prompts could only run xprompts.
   Renaming `raw_prompt` to `smack prompt` would immediately undo that progress, re-introducing the exact same conceptual entanglement under a new, less professional name.
3. **Pipeline Incoherence:**
   The SASE prompt processing pipeline is:
   $$\text{Raw Prompt} \xrightarrow{\text{expansion \& directive extraction}} \text{Submitted Prompt}$$
   If the input is a "smack prompt", what is the output? An "un-smacked prompt"? An "expanded smack"? The terminology breaks down instantly.

### 2.4 Agent Comprehension and Token Budget
SASE is fundamentally an agent-orchestrated system. Prompts are ingested, manipulated, and authored by autonomous LLM agents (Claude, Gemini, GPT).
- LLMs are pre-trained on billions of tokens of computer science literature, code repositories, and documentation. They have deeply ingrained semantic priors for terms like **`macro reference`**, **`macro call`**, and **`macro expansion`**.
- An LLM encountering "macro reference `#plan`" immediately understands its semantics, syntax, and purpose with zero prompting overhead.
- In contrast, "smack" is an out-of-distribution neologism for this concept. Using "smack" in agent instruction files (`AGENTS.md`), memory strands, or tool definitions:
  - Consumes token budget in core memory to define and explain the slang.
  - Increases the risk of agent confusion, tool hallucination, or inappropriate slang generation in agent responses.
  - Creates friction during prompt debugging and multi-agent transcript inspection.

---

## 3. Scorecard: Evaluating Naming Candidates

To evaluate the options rigorously, we test five candidate terms against the core functional and communicative requirements:

1. **Self-Describing:** Can a newcomer or an LLM understand what it means without consulting a dictionary?
2. **Taxonomic Symmetry:** Does it align with sibling concepts (`Artifact Reference`, `Workspace Reference`, `Directive`)?
3. **Codebase Harmony:** Does it match existing AST / parser symbols in `src/sase/macro/`?
4. **Professionalism & Tone:** Is it free from drug, violent, or colloquial baggage?
5. **Prompt Independence:** Does it keep the prompt container distinct from the syntax token?
6. **Brevity & Colloquial Ease:** Can developers say and type it quickly in conversation?

| Evaluation Criterion | `Macro Reference` (`macro ref`) | `Macro Invocation` (`macro call`) | `Smack` (`sase macro invocation`) | `Mref` / `Minv` | `Loop` / `Notch` (Craft metaphor) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Self-Describing** | **High (5/5)**<br>Clear CS standard | **High (5/5)**<br>Clear CS standard | **Very Low (1/5)**<br>Opaque slang | **Moderate (3/5)**<br>Unix abbreviation | **Low (2/5)**<br>Metaphoric leap |
| **Taxonomic Symmetry** | **High (5/5)**<br>Pairs with `Artifact Ref` & `Workspace Ref` | **Moderate (3/5)**<br>"Ref" family is broken | **Very Low (1/5)**<br>Isolated one-off | **Moderate (3/5)**<br>Abbreviated only | **Low (2/5)**<br>Novel theme |
| **Codebase Harmony** | **High (5/5)**<br>Matches `MacroReference` class | **Moderate (3/5)**<br>Matches style key `"invocation"` | **None (0/5)**<br>Absent in code | **Low (2/5)**<br>Absent in code | **None (0/5)**<br>Absent in code |
| **Professionalism & Tone** | **High (5/5)**<br>Clean, technical | **High (5/5)**<br>Clean, technical | **Negative (0/5)**<br>Heroin / violence slang | **High (5/5)**<br>Technical jargon | **High (5/5)**<br>Whimsical craft |
| **Prompt Independence** | **High (5/5)**<br>Prompt is prompt; ref is ref | **High (5/5)**<br>Prompt is prompt; call is call | **Very Low (1/5)**<br>Encourages "smack prompt" | **High (5/5)**<br>Clean distinction | **High (5/5)**<br>Clean distinction |
| **Colloquial Ease** | **High (4/5)**<br>"macro ref" is 3 syllables | **Moderate (3/5)**<br>"macro call" is 3 syllables | **High (5/5)**<br>1 syllable punch | **High (4/5)**<br>Short spoken form | **High (4/5)**<br>1 syllable punch |

### Key Findings from the Scorecard:
- **`Macro Reference` is the dominant winner.** It achieves the highest score across every single metric except raw single-syllable brevity, where its standard short form **`macro ref`** is equally punchy and already natural to developers.
- **`Macro Invocation` is a strong formal partner.** It precisely describes the dynamic evaluation phase (argument passing, template execution), though SASE docs already use "invocation" for LLM API calls (`provider invocation`, `LLMInvocationError`).
- **`Smack` fails almost every technical and communicative criterion.** Its sole virtue is monosyllabic punchiness, which is heavily outweighed by severe social and architectural liabilities.

---

## 4. Requirements Adjustments

Based on the research findings, the following adjustments to the user's initial proposal are strongly justified:

### Adjustment 1: Establish `Macro Reference` as the Canonical Term
- Instead of establishing "sase macro invocation" or "smack" as the primary concept, establish **`Macro Reference`** (slug: `macro-reference`, keyword: `Macro Reference`).
- Define its standard colloquial abbreviation as **`macro ref`**.
- Accept **`Macro Invocation`** and **`Macro Call`** as official synonyms in frontmatter aliases and documentation.
- If the user/team strongly desires to retain "smack" as an affectionate, informal internal nickname, list `smack` strictly as a tertiary entry in `aliases:` on the glossary strand, but do **not** use it in formal documentation, CLI commands, or agent instructions.

### Adjustment 2: Reject "Smack Prompt" Completely
- The raw input prompt MUST remain **`raw prompt`** (in documentation, UI labels, and artifact files such as `raw_prompt.md`).
- The processed prompt sent to the LLM MUST remain **`submitted prompt`** (and `submitted_prompt.md`).
- A prompt that contains macro references is simply *"a prompt containing macro references"* (or *"a prompt with macro refs"*), maintaining the clean boundary between container and contents.

### Adjustment 3: Complete SASE's Reference Syntax Taxonomy
- Formally document the triad of prompt references:
  1. **Workspace Reference:** `#git:...`, `#gh:...`
  2. **Artifact Reference:** `@<kind>:<target>`
  3. **Macro Reference:** `#<name>`, `#!<name>`, `#<name>(args)`
This brings complete symmetry to SASE's prompt language specification.

---

## 5. Implementation Blueprint

Implementing this recommendation requires no disruptive code rewrites because the codebase already uses `MacroReference` internally. The implementation focuses on knowledge architecture, documentation, and glossary strands.

### 5.1 New Memory Web Strand: `macro-reference.md`

Create the new file `sase/memory/glossary/macro-reference.md`:

```markdown
---
keyword: Macro Reference
aliases:
  - macro ref
  - macro invocation
  - macro call
---

A macro reference (macro ref, or macro invocation) is an inline `#<name>` or
standalone `#!<name>` token in an agent prompt that SASE expands before the agent runs.
It can supply arguments using paren syntax (`#name(arg1, key=val)`), colon shorthand
(`#name: arg`), double-colon shorthand (`#name:: text`), or plus syntax (`#name+`), and
can carry HITL suffix overrides (`!!` or `??`).

A macro reference is distinct from a [[glossary:macro]] definition (the source `.md` or
`.yml` file) and from macro expansion (the resolution process). It is also distinct from
a [[glossary:project-tag]] (`+project`), a workspace reference (`#git:<ref>`,
`#gh:<ref>`), and an [[glossary:artifact-reference]] (`@kind:arg`).
```

### 5.2 Updates to Existing Memory Strands

#### 1. `sase/memory/glossary/macro.md`
Update the description to cross-link the new strand:
```markdown
---
keyword: Macro
aliases:
  - xprompt
---

Formerly called an xprompt. A reusable prompt definition in a `sase/macros/` directory
(.md or .yml file) or in `~/.config/sase/sase.yml` (`macros` field). Invoked in agent
prompts via a [[glossary:macro-reference]] (`#foo`).
```

#### 2. `sase/memory/macros.md` (Reference Memory)
Under the section *Define* and *Project-Task Launches*, update inline mentions of `#name` to link to `[[glossary:macro-reference]]`.

### 5.3 Documentation Alignment in `docs/macros.md`

In `docs/macros.md`, under the section **Reference Syntax**, formalize the terminology:
- Use **Macro Reference** when referring to the syntax token (`#foo`).
- Use **Macro Invocation** when discussing the dynamic evaluation of arguments and execution of workflow steps.
- Maintain **Raw Prompt** for the pre-expansion prompt text.

---

## 6. Recommended Solution & Action Plan

### Recommended Solution Summary
1. **Name:** **`Macro Reference`** (colloquial: **`macro ref`**; formal execution synonym: **`macro invocation`**).
2. **Glossary Strand:** Add `sase/memory/glossary/macro-reference.md` as specified in Section 5.1.
3. **Prompt Container:** Keep `raw prompt` (`raw_prompt.md`). Reject `smack prompt`.
4. **Informal Jargon Policy:** If the team enjoys saying "smack" socially in chat or standup as shorthand for `#foo`, treat it as benign team slang, but do not promote it to an official system noun or memory concept.

### Step-by-Step Rollout Checklist
- [x] **Phase 1: Research & Decision (This Report)**
  - Deliver independent research report analyzing naming options, phonetics, connotations, and prompt mechanics.
  - Register report in the research artifact repository.
- [ ] **Phase 2: Memory Web Strand Addition**
  - Use `/sase_memory_write` to create `sase/memory/glossary/macro-reference.md`.
  - Update `sase/memory/glossary/macro.md` with cross-links.
  - Run `sase memory init` to re-index and refresh instruction shims.
- [ ] **Phase 3: Documentation Alignment**
  - Update `docs/macros.md` (Reference Syntax section) to use "macro reference" consistently.
  - Verify that `docs/prompt.md` and related tutorials maintain the clean separation between raw prompts and macro references.
- [ ] **Phase 4: Verification**
  - Run `sase memory web show glossary` to confirm the new term appears cleanly among the 67 glossary terms.
  - Run `just check` to ensure no broken memory links or lint regressions.

---

## Sources & Precedents

### Internal Codebase & Memory
- `src/sase/macro/_parsing_references.py` (`MacroReference`, `MACRO_REFERENCE_PATTERN`, `MacroReferenceMarker`)
- `src/sase/macro/naming.py` (`is_inline_reference_name`)
- `src/sase/ace/tui/util/macro_syntax.py` (`MACRO_TOKEN_STYLES["invocation"]`)
- `sase/memory/glossary/artifact-reference.md` (structural blueprint for reference strands)
- `sase/memory/glossary/macro.md`, `macro-part.md`, `macro-workflow.md`
- `sase/memory/macros.md` (macro discovery, expansion, syntax rules)
- `docs/macros.md` (Reference Syntax, arguments, shorthands)
- `research:202610/xprompt_to_macro_naming_verdict.md` (recent migration analysis from xprompts to macros)

### External Precedents
- **Rust Language Reference:** Macro Definition (`macro_rules!`) vs. Macro Invocation (`println!()`).
- **C/C++ Standard (ISO/IEC 9899):** Macro Definition (`#define`) vs. Macro Invocation / Macro Replacement.
- **Common Lisp HyperSpec:** `defmacro` vs. Macro Form / Macro Call.
- **Bjarne Stroustrup, *The Design and Evolution of C++*:** On the importance of separating container syntax from replacement tokens.
