# Naming SASE macro invocations: “smack” and the boundary of a prompt

Researcher: cdx  
Date: 2026-10-05  
Scope: independent research and an implementation recommendation; no product or canonical memory changes.

**Recommendation:** add **Sase Macro Invocation**, with **smack** as a glossary alias, for one authored macro call. Retain “macro” for the reusable definition. Use “SASE prompt source” for the complete authored input, and preserve the existing distinction between submitted and raw prompts. Do not rename all raw prompts to “smack prompts” as part of this change.

## What the proposal gets right

Naming the invocation solves a real conceptual problem. “Macro” currently refers to a reusable definition, while people also use it loosely for its appearance in a prompt. A definition can be used several times, with different arguments; a particular use can be unresolved, malformed, protected as literal text, or expanded away. A term for that use makes discussion more precise:

- “This macro defines a review template.”
- “This prompt contains two smacks.”
- “The second smack passes the wrong argument.”
- “The macro expands into a directive.”
- “Copy the invocation, including its arguments.”

The new concept is useful even if the nickname never becomes universal. “Macro invocation” already has an established technical meaning: Rust explicitly defines a macro-invocation syntax and distinguishes the invocation from its expansion; GNU CPP similarly describes a macro name plus actual arguments as an invocation. That is good precedent for the proposed long form, rather than a reason to invent a different technical category. [Rust Reference](https://doc.rust-lang.org/reference/macros.html#macro-invocation), [GNU CPP: Macro Arguments](https://gcc.gnu.org/onlinedocs/cpp/Macro-Arguments.html).

“Smack” is short, pronounceable, and memorable. Its phonetic derivation can work as a personal mnemonic; it does not need to be justified as a literal initialism. I would spell the nickname **smack**, plural **smacks**, and introduce it as “SASE macro invocation (smack).” Keep “invoke,” “expand,” and “launch” as the verbs.

Its main cost is vocabulary acquisition. A new reader understands “macro invocation” immediately but must learn “smack.” Google’s documentation guidance cautions that unfamiliar abbreviations can slow comprehension and recommends introducing the full term first. My inference is that the descriptive name should remain canonical, with the nickname available in conversation and explanatory prose. [Google developer style guide: Abbreviations](https://developers.google.com/style/abbreviations#when-to-use-abbreviations).

There is also an existing technical name collision: Linux **Smack** is a mandatory-access-control implementation. That makes unqualified searches for “smack” less distinctive. This is a discoverability concern, not a reason to prohibit a local nickname or a claim about trademark clearance. Use “SASE smack” in titles where external discovery matters. [Linux kernel documentation: Smack](https://www.kernel.org/doc/html/latest/admin-guide/LSM/Smack.html).

## What the current implementation actually models

I inspected the primary SASE checkout at the full revision recorded in the evidence section and the linked sase-core checkout at its pinned revision. The important facts are:

| Concept | Current evidence | Naming implication |
| --- | --- | --- |
| Reusable definition | The Macro glossary strand and `docs/macros.md` describe definitions in Markdown, YAML, or configuration. | Keep **macro**. |
| One use in source | Python already has `MacroReference`, with marker, normalized name, start/end offsets, raw source, argument syntax, argument source, and HITL override. | The proposed concept largely already exists; a new public word does not require a new runtime type. |
| Inline and standalone forms | `#name` is inline-capable; `#!name` is the standalone-workflow form. | Define the term’s scope explicitly instead of treating every call as inline expansion. |
| Lexical candidate versus active use | The lexical iterator deliberately does not filter fences. Literal-zone filtering and catalog resolution are separate operations. | A regex match is not proof that an invocation executes. |
| Complete prompt | Launch setup includes project tags, workspace references, swarm fan-out, aliases, macro expansion, and directive extraction. | A whole prompt is a larger object than an invocation. |
| Existing glossary integration | Editor glossary catalogs load strands and aliases; TUI highlighting uses the shared Rust-backed catalog. | A strand can participate in existing lookup and presentation without a new “smack” subsystem. |

See [the existing reference representation](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/src/sase/macro/_parsing_references.py), [literal-zone composition](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/src/sase/macro/_literal_zones.py), [usage scanning](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/src/sase/macro/used_macros.py), and [macro documentation](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/docs/macros.md).

The invocation includes its arguments and modifiers, not just `#` plus the name. For example, `#review(path=src/app.py)` is one invocation. A line-style text argument can make the invocation span multiple lines; “token” is therefore an imprecise general synonym.

The code also exposes the distinction across frontends. Rust editor parsing uses `ParsedMacroCall` and `ParsedMacroReference`; the Python runtime exposes `MacroReference`. These are compatible conceptual names, even though their implementations are not a single shared class. Do not rename either merely to mirror the nickname. If a later project introduces shared invocation classification or a public wire type, that behavior belongs in sase-core and its bindings, under the project’s Rust boundary. [Rust editor macro parsing](https://github.com/sase-org/sase-core/blob/ecd2e074b4489c0c326e2137075dfd29be2bc384/crates/sase_core/src/editor/macro_args.rs), [SASE Rust backend guide](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/docs/rust_backend.md).

### Recommended scope and boundary cases

Use **smack** for an invocation expression, with a narrower qualifier where needed:

| Example or context | Recommended description |
| --- | --- |
| `#foo`, `#foo(a, k=v)`, `#foo:arg`, `#foo+` | Inline smack, assuming it is used as a macro call. |
| `#foo: free text`, `#foo:: free text` | A smack with a text argument; the argument belongs to the invocation. |
| `#ns/foo` and supported alias spellings | Namespaced or aliased smack; spelling and resolved name are distinct. |
| `#!build(target=staging)` | Standalone workflow smack. It launches the appropriate workflow rather than promising inline text replacement. |
| An intended call to an unknown name | Unresolved invocation / unresolved smack; do not imply resolution succeeded. |
| `# Heading` | Markdown heading. |
| A `#foo` example inside a protected literal zone | Literal invocation syntax; it is not an active invocation at that location. |
| `%model:opus` | Prompt directive. |
| `@research:202610/example.md` | Artifact reference. |
| `+sase` | Project tag. |
| `#git:home` or `#gh:...` at a launch boundary | Workspace reference is the useful, specific name. Where the resolver dispatches a macro/workflow, it can also be described as an invocation; the shared `#` marker alone is insufficient to classify it. |

Do not create a rule that all hash-prefixed text is a smack. The current launch parser treats some workspace references specially, and unknown references can pass through as prose hashtags. An “unresolved smack” describes an intended call; a lexical candidate need not be one. This terminology should explain the existing distinction, not change unknown-reference handling.

A macro body can introduce further invocations through recursive expansion. It is useful to distinguish **authored invocation** from **an invocation introduced by expansion** when debugging, but there is no need to create separate glossary strands for every variation now.

## Why I would not rename “raw prompt” to “smack prompt”

A prompt is a container; a smack is one expression inside it. Consider:

```text
+sase %model:opus Review error handling. #review(path=src/app.py) #style
```

This contains prose, a project tag, a directive, and two invocations. A plain “Review error handling” input can contain zero authored invocations, although launch normalization may later add a workspace reference. Calling all such input a “smack prompt” can suggest that only macro syntax matters, or that the prompt contains one invocation, or that macros are required.

There is a more significant implementation finding: **the current raw prompt is not necessarily the exact submitted text.**

The runner’s `write_submitted_prompt_artifact()` preserves the launch-boundary input without alias or macro expansion. Its `preprocess_prompt_macros()` then canonicalizes project aliases and resolves macro aliases, writes `raw_prompt.md`, and only afterward processes macro references. For example, a configured `#c` alias can already be `#commit` in the raw artifact. The submitted artifact is itself the runner’s launch-boundary input; upstream input collection or launch planning may already have transformed the original editor buffer. [Prompt preprocessing and artifact writers](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/src/sase/axe/run_agent_runner_setup_prompt.py), [runner launch-input capture](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/src/sase/axe/run_agent_runner_bootstrap.py).

A useful vocabulary is therefore:

| Stage or object | Preferred term | Existing representation / caveat |
| --- | --- | --- |
| Text as authored in an editor | **Authored prompt** or **SASE prompt source** | Can include prose, frontmatter, invocations, directives, references, and separators. |
| Input received by the runner | **Submitted prompt** | `submitted_prompt.md`; not a promise of byte identity with the original editor buffer. |
| Alias-resolved, pre-expansion launch input | **Raw prompt**, with “normalized source prompt” as an explanatory phrase | `raw_prompt.md`; exact boundary is defined by its writer. |
| Text produced by macro expansion | **Expanded prompt** | May still undergo other processing; not automatically the full provider request. |
| Prompt text actually passed onward to the model | **Model prompt** | Provider instructions and other context can be additional inputs. |

This is a vocabulary map, not a claim that every launch path materializes all five artifacts in that exact order.

Existing consumers make the raw-stage boundary operationally important. Restarting uses raw prompt content; archive publication reads it; compatibility readers prefer `raw_prompt.md` while still accepting `raw_xprompt.md`. A wholesale rename would affect data readers and migration logic, not just wording. [Restartable prompt selection](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/src/sase/ace/tui/models/artifact_files.py), [archive preparation](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/src/sase/agents_sync/prompt_archive/preparation.py), [durable compatibility names](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/src/sase/legacy_xprompt_names.py).

If “smack prompt” becomes a natural conversational phrase, I would allow it informally for **a prompt containing smacks**, and clarify its meaning on first use. I would not establish it as another canonical stage name or glossary strand now.

There is one other use of “raw” to avoid conflating: `sase prompt show -f raw` means unadorned output bytes of the stored prompt, rather than the metadata-bearing output formats. It does not identify an agent artifact’s preprocessing stage. Renaming that format because of “smack” would change the wrong concept. [Prompt history documentation](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/docs/prompt.md).

## Options and tradeoffs

These ratings are judgment calls informed by the implementation, not measured user-study results.

| Approach | Benefit | Cost | Assessment |
| --- | --- | --- | --- |
| Add “macro invocation” only | Immediately intelligible; standard technical wording. | Less distinctive in conversation. | Good baseline. |
| Add “Sase Macro Invocation,” alias “smack” | Precise definition plus a memorable local nickname. | One extra term to learn. | **Best fit for the request.** |
| Make “Smack” canonical everywhere | Strong local identity and short labels. | Search collision; less transparent docs and APIs. | More cost than the initial benefit justifies. |
| Rename the whole prompt to “smack prompt” | Distinctive phrase for authored input. | Blurs expression, container, and processing stage; invites migration scope. | Defer. |
| Name the entire source language “Smack” | Could unify a future language reference. | Expands the proposal to directives, references, frontmatter, and execution semantics. | Separate design decision if there is demonstrated need. |

A new term earns its place when it enables clear statements that were previously awkward. “Two smacks in this prompt” passes that test. “The raw prompt is now the smack prompt” does not add comparable precision.

## Explicit adjustments to the requirements

1. **Preserve the descriptive canonical name.** Add the requested glossary concept as **Sase Macro Invocation**, with **smack** as an alias. Do not replace “macro” or rebrand the macro subsystem.
2. **Scope it to one invocation expression.** Include arguments and supported modifiers; distinguish definition, call, and expansion result.
3. **Cover both `#` and `#!` forms.** The implementation already groups macro/workflow references, so “inline smack” and “standalone workflow smack” are useful qualifiers.
4. **Separate the whole-prompt naming decision.** Prefer “SASE prompt source”; retain submitted/raw/expanded distinctions. Defer canonical “smack prompt.”
5. **Make the first implementation a terminology and memory change.** No grammar, command, configuration, stored filename, wire schema, or public type migration is required.
6. **Keep the glossary concise.** Add one strand and a small cross-reference in the existing Macro definition. Do not add a new core-memory essay or a taxonomy of “smack” subterms.

These adjustments narrow the implementation while retaining the user’s main idea.

## Concrete implementation recommendation

The following is proposed implementation, not work performed by this research turn.

### 1. Add one canonical strand

Create `sase/memory/glossary/sase-macro-invocation.md` with the existing strand frontmatter format:

```markdown
---
keyword: Sase Macro Invocation
aliases:
  - smack
  - macro invocation
summary: One use of a macro, including its marker and arguments.
---

A sase macro invocation (smack) is one call to a
[[glossary:macro]] in SASE prompt source, including its marker, name,
and any arguments or modifiers. For example,
`#review(path=src/app.py)` is one smack.

The inline-capable form is `#name`; the standalone
[[glossary:macro-workflow]] form is `#!name`.
Protected literal text can show this syntax without invoking it.

A macro is the reusable definition; a smack is a use of it.
A whole prompt can contain zero, one, or many smacks together with
other text and syntax.
```

The stable filename is descriptive rather than nickname-dependent. The frontmatter provides both direct `glossary:smack` lookup and the discoverable technical phrase. Do not add `type: core` or `type: reference` to a strand.

The glossary index currently has no “smack” entry. Its keyword and alias roster is generated; the body remains on-demand. Existing editor/TUI glossary catalogs consume these strand entries and aliases. A new bespoke matcher, menu, icon, parser, or shortcut is unnecessary for this scope. [Memory web documentation](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/docs/memory.md), [strand-format tests](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/tests/test_memory_web_mutation.py), [editor glossary catalog](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/src/sase/macro/glossary_catalog.py).

### 2. Clarify the existing Macro strand

Keep its historical-name statement and its definition location information. Append a short distinction, for example:

> A use of a macro in prompt source is a [[glossary:sase-macro-invocation]] (smack).

This is an authored cross-reference to the new concept. The two strands may refer to each other; verify the actual read closure rather than duplicating the definition in both.

The existing terminology test has narrowly allowlisted historical “xprompt” lines. Preserving the current historical line avoids unnecessary changes; if regenerated roster wrapping changes its allowlisted line, update that specific retained-history entry instead of weakening the guard. [Existing terminology documentation guard](https://github.com/sase-org/sase/blob/6fde79660418540d98dd81fbcdd317f50c062cf8/tests/_macro_terminology_docs.py).

### 3. Introduce the word where it helps comprehension

Add a brief paragraph near the beginning of `docs/macros.md` and its reference-syntax section: a macro is the definition; an invocation, or smack, is a use such as `#review(path=a)`. Keep the established page, anchors, CLI names, and APIs.

Add a small prompt-stage clarification to the relevant prompt documentation if it is in the approved implementation scope. Explain submitted versus alias-resolved raw source using the actual writer boundary. Do not perform a repository-wide replacement of “raw prompt” or “macro reference.”

Retain `MacroReference`, `sase macro`, `macro_aliases`, `macros.json`, `raw_prompt.md`, and `submitted_prompt.md`. This does not deprecate existing behavior and has no need for a feature flag. If a later proposal does deprecate syntax or change a serialized contract, use the project’s separate CLI, feature-flag, and Rust-boundary procedures then.

### 4. Republish and verify

For the implementation turn:

- Use `/sase_memory_write`, review the affected terms through audited `sase memory read`, and edit canonical memory only.
- Run `sase memory init` to regenerate the glossary roster and instruction shims. Inspect the generated diff; do not hand-edit the roster, `AGENTS.md`, or provider shims.
- Confirm `sase memory read glossary:smack glossary:macro -r "Verify invocation terminology and cross-links"` resolves to the intended entries and a sensible closure. Confirm the full canonical keyword also resolves.
- Inspect the glossary index for the new keyword and aliases. Where existing glossary integration is exercised, confirm that prose mentions lead to this definition after catalog refresh, without assuming the strand changes syntax highlighting of `#foo`.
- Read `lint_and_test.md` before finishing a turn that changes tracked primary-repository files; use the prescribed fix and guarded `just check` workflow. `check-full` remains explicit-only.

A new parser test suite would add little value to a glossary-only change. Reuse the existing memory-web and terminology verification. Only add focused behavior tests if implementation actually changes behavior.

Acceptance is concrete: there is one authoritative definition; alias and canonical-name lookup work; the Macro definition points to it; docs distinguish definition, invocation, and complete prompt; generated instructions contain the new term roster; existing command, grammar, artifact, and replay contracts still work.

### 5. Evaluate adoption before expanding scope

Try the wording in actual design discussions and a few documentation examples. Ask whether readers can distinguish a definition, an invocation, and a whole prompt without looking up the nickname repeatedly. Compare “macro invocation” and “smack” in the same sentence.

If the nickname saves time for regular users, it can become common shorthand. If it does not, retaining it as an alias is inexpensive. This is a practical adoption check, not a proposed experiment with an invented success metric. A whole-language or artifact rename needs its own demonstrated communication problem.

## Evidence, method, and limits

This report was researched independently. No peer reports, transcripts, summaries, or findings were consulted.

Repository evidence:

- Primary SASE revision: `6fde79660418540d98dd81fbcdd317f50c062cf8`.
- Opened sase-core revision and primary CI pin: `ecd2e074b4489c0c326e2137075dfd29be2bc384`.
- Audited memory reads: `macros.md`, `sase_artifacts.md`, `tui.md`, and glossary strands `macro`, `macro-part`, `macro-workflow`, `memory-strand`, and `memory-web`.
- Metadata-only glossary index queries showed existing Macro-family terms and no “smack” match.
- Source inspection covered prompt artifact writers/readers, macro reference parsing and usage scanning, memory-web formatting, glossary integration, and existing rename guards.

I ran a small read-only lexical probe using the workspace Python environment. It confirmed full-call spans for bare, parenthesized, colon, text-shorthand, and standalone-HITL forms; headings and a hash attached to a preceding word did not match. The probe also confirmed that the lexical iterator alone finds candidates inside fenced and disabled examples. That is consistent with its explicit caller-filtering contract.

A separate attempted end-to-end literal-zone probe could not execute because the editable `sase_core_rs` extension was unavailable in that workspace environment. Protected-zone conclusions here come from source and documentation, not a claimed successful integration test. No macro bodies or workflows were executed, and no build was needed for this research deliverable.

External sources are primary documentation, linked at the supported claims. They support established terminology, abbreviation guidance, and the existing Smack name collision; the recommended naming policy and adoption approach are my conclusions. No user study, performance benefit, name exclusivity, or legal clearance is claimed.

Only the research report is being produced and registered in this turn. The glossary draft and implementation sequence are recommendations for a later implementation turn.

## Recommended solution

**Adopt “Sase Macro Invocation” as the canonical glossary term and “smack” as its conversational alias. Define it as one macro/workflow call expression, including its marker, name, arguments, and modifiers. Add one strand, a cross-reference from Macro, and a short documentation explanation; regenerate and verify the existing glossary machinery.**

**Keep the complete input named “SASE prompt source,” and preserve “submitted prompt,” “raw prompt,” and “expanded prompt” for their actual boundaries. Defer a canonical “smack prompt” name and any runtime or artifact rename.** This gives the proposal its strongest benefit—clear language for a specific use of a macro—with a small, reviewable implementation.
