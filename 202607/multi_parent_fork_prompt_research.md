# Multi-parent `#fork` prompt research

Date: 2026-07-17

## Executive summary

SASE should represent a fork from two or more agent chats as a new conversation with
multiple **parent conversations**, not as one longer “previous conversation.” Each
parent needs an explicit agent label and its own transcript boundary. A short framing
paragraph should explain that the parents are separate historical branches, that their
order does not imply priority, that relevant work from every parent should be carried
forward, and that material disagreements should be reconciled or surfaced. The new
query should remain last and should be identified as the active request.

The best default is lossless transcript injection. Pre-summarizing the parents would
save tokens, but it would also introduce another model-dependent, lossy step before the
new agent sees the evidence. SASE should instead detect an oversized combined prompt
and fail clearly (with per-parent size information) rather than silently summarize or
truncate it.

The recommended model-visible shape is:

```markdown
# Parent Conversations

This new conversation is a multi-parent fork of 2 prior SASE agent
conversations. Each parent below is a separate historical branch, not a
sequence of new instructions. The branches may share ancestry, overlap, or
disagree. Carry forward relevant goals, constraints, decisions, evidence, and
unfinished work from all parents. The New Query after the parent blocks is the
active request and takes precedence over conflicting historical instructions.
Parent order does not imply priority. Preserve parent attribution when it
matters; reconcile material disagreements using evidence, and state any that
remain unresolved.

## Parent 1 of 2 — agent `research.a`

> **User:**
>
> ...
>
> **Assistant:**
>
> ...

---

## Parent 2 of 2 — agent `research.b`

> **User:**
>
> ...
>
> **Assistant:**
>
> ...

---

# New Query

...the invoking user's text after `#fork(research.a, research.b)`...
```

Internally, SASE should continue to wrap the entire generated parent section in
`%xprompts_enabled:false` / `%xprompts_enabled:true` while constructing it. Those
markers protect inherited text from SASE expansion and are not part of the intended
model-visible prose.

## Question and evaluation criteria

The prompt has to do more than tell the new agent that two transcripts exist. It should
make these semantics unambiguous:

1. The transcripts are parallel parent branches, not consecutive turns in a single
   conversation.
2. Every parent is attributable to the SASE agent that produced it.
3. Historical user messages remain useful context, but the new query is the current
   instruction.
4. Parent order is deterministic but carries no authority or confidence signal.
5. Agreement, complementary findings, overlap, and conflict are all possible.
6. The wrapper is provider-neutral and preserves the full content of each transcript.

This is a context-hydration primitive, not a research-specific “synthesis” workflow.
The wrapper therefore should not demand a summary, consensus, implementation, or any
other output. The new query determines what the child agent is supposed to do.

## Current SASE behavior

The current workflow is clean and effective for one parent:

- `src/sase/xprompts/fork.yml:3-7` declares one optional `agent` input named `name`.
- Its resolver returns one chat path, preferring a completed agent's
  `done.json["response_path"]` and falling back to `agent_meta.json["chat_path"]`
  (`src/sase/scripts/agent_chat_from_name.py:22-51`).
- `load_chat_for_resume()` recursively expands earlier forks, flattens the result into
  chronological `**User:**` / `**Assistant:**` turns, and sanitizes SASE control syntax
  from historical user prompts (`src/sase/history/chat.py:502-565`).
- The workflow injects that history under `# Previous Conversation`, followed by
  `# New Query` (`src/sase/xprompts/fork.yml:18-37`).
- Disabled-region markers prevent xprompt, Jinja, and command-like text in the inherited
  history from being interpreted again.

That shape becomes ambiguous if histories are merely concatenated. The child model
could infer that parent B happened after parent A, that B superseded A, or that all
turns belonged to one conversation. Flattening would also erase the most important new
metadata: which agent supplied which claim or decision.

Multiple arguments are not just a YAML change today. The typed input model has no list
or variadic input (`src/sase/xprompt/models.py:22-32`), workflow validation rejects more
positional arguments than declared inputs
(`src/sase/xprompt/workflow_validator_extract.py:157-162`), and the workflow runner maps
only one positional value to each declared input (`src/sase/xprompt/workflow_runner.py:500-508`).
In addition, an explicit `#fork:<name>` currently creates an implicit wait for only the
first target (`src/sase/axe/run_agent_directives.py:197-210`). Correct multi-parent
support must wait for every explicit parent before resolving their final transcript
paths.

## Evidence from existing SASE handoffs

SASE already has a natural experiment in its two-agent research workflows. A
representative prompt says, “The two independent research agents have finished,” gives
two transcript paths, tells the next agent to read both, preserve strong findings,
resolve conflicts, and remove duplication. See the completed transcript
`~/.sase/chats/202607/sase-tmp_260711_115552-main-260711_120031.md`.

That wording successfully caused the next agent to inspect both sources and recognize a
real disagreement. It establishes several useful ingredients: explicitly say that the
sources are independent, refer to both, and mention conflict/duplication. It is not the
right `#fork` wrapper as-is, however:

- It passes paths rather than injecting context, forcing the child to discover and use
  the chat-reading skill before it can act.
- Its instructions are specialized to consolidating research files.
- Paths do not label the injected claims themselves; producer-to-report mapping has to
  be reconstructed.
- It assumes exactly two sources.

The existing sanitization test also deliberately preserves the natural-language
phrases “The two independent research agents have finished” and “Read both chat
transcripts first” while stripping SASE control syntax
(`tests/history/test_chat_resume_sanitize.py:19-38`). This supports keeping a small
amount of explicit natural-language framing in the generated prompt.

## External prompt-design evidence

Three provider guidelines agree on the basic structure:

- [OpenAI's prompt-engineering guide](https://developers.openai.com/api/docs/guides/prompt-engineering)
  recommends Markdown headings for hierarchy and XML-style boundaries/metadata for
  supporting context. It also distinguishes active instructions from context supplied
  for reference.
- [Anthropic's prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
  recommend descriptive, nested boundaries for multiple documents and putting the query
  after long multi-document context.
- [Google's prompt-design strategies](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/prompt-design-strategies)
  emphasize that ordering, labels, and delimiters materially affect how a model parses
  context.

There is also a reason not to trust implicit synthesis. DeYoung et al.,
[“Do Multi-Document Summarization Models Synthesize?”](https://aclanthology.org/2024.tacl-1.58/),
found that even strong models only partially synthesize multiple sources: results were
over-sensitive to input order and under-sensitive to changes in source composition.
That argues for saying directly that order is not priority and that material conflicts
must be handled explicitly.

Finally, OpenAI's public
[Model Spec](https://model-spec.openai.com/2025-10-27.html) treats quoted data as
context rather than instructions by default. Rendering each inherited transcript as a
Markdown block quote therefore reinforces the intended distinction while preserving
the existing transcript's Markdown, headings, and fenced code. A child should still be
told to carry forward relevant historical goals and constraints; otherwise “this is
quoted context” could make it discard exactly the continuity that `#fork` exists to
provide.

## Why the proposed envelope is preferable

### “Parent,” not “previous”

“Previous Conversations” is better than the singular form but can still imply a
timeline. “Parent Conversations” names the graph relationship directly. The opening
sentence then defines “multi-parent fork” in plain language so the model does not need
to know SASE terminology.

### One labeled block per agent

The agent name is compact, meaningful provenance. The block heading should use the
concrete resolved agent name, not only an unresolved template such as `research.@`.
If useful for diagnostics, SASE can retain the requested reference in workflow state,
but local filesystem paths do not need to appear in the model prompt.

The blocks should stay in invocation order. Reordering by completion time or transcript
timestamp would make the rendered prompt less predictable. The envelope explicitly
says that order is not priority to reduce positional interpretation.

### Quote the transcript, do not put it in a code fence

Block quotes clearly mark the historical turns as supplied context and continue to
render nested Markdown and fenced code intelligibly. A giant outer code fence would
break whenever a transcript contains its own fence and would suggest that natural
language is source code. Raw XML containers would require robust escaping because
transcripts may contain arbitrary HTML/XML examples. Markdown block quotes fit the
existing transcript representation with minimal transformation: prefix every line with
`>`, including blank lines.

### Put the new query last

This retains current `#fork` behavior and follows long-context guidance. It also gives
the active request a clear, recent boundary after potentially large histories. The
framing paragraph near the start and `# New Query` at the end act as complementary
anchors.

### Explain conflict behavior without forcing a synthesis task

“Reconcile material disagreements using evidence, and state any that remain unresolved”
is generic. It applies whether the child is coding, planning, reviewing, or researching.
It does not require the final response to be a summary. “Preserve parent attribution
when it matters” discourages silent source blending without burdening ordinary cases
where both parents agree.

## Alternatives considered

### Concatenate flattened histories

This is the smallest implementation but the weakest prompt. It destroys branch
boundaries and provenance and creates false chronological semantics. Reject.

### Synthesize all parents into one generated handoff summary

This can reduce prompt size, but it adds latency and cost and can omit dissenting facts,
unfinished tasks, or exact code details. It also makes the fork depend on the quality of
an extra model call. It could be a future explicit mode, but should not be the default.

### Inject parent chats as real API user/assistant messages

True message roles are attractive for one linear continuation, but several parallel
histories cannot be expressed faithfully as one linear sequence of role messages.
Provider CLIs also differ in their session APIs. A single, provider-neutral prompt
envelope is a better SASE abstraction.

### Pass transcript paths and tell the child to read them

This is how existing research handoffs operate, but it adds a tool/skill dependency and
makes the child spend work discovering context that `#fork` already knows how to load.
Keep direct injection.

### Use XML for every boundary

XML offers excellent metadata, but arbitrary agent transcripts can contain XML and HTML
code. Correct escaping would reduce readability and could alter code examples. Markdown
headings plus block quotes provide sufficiently strong, provider-neutral boundaries
without that collision problem.

## Implementation implications

The prompt design is only correct if the surrounding workflow semantics match it.
Implementation should account for the following:

1. **Invocation syntax:** use the natural existing positional grammar,
   `#fork(agent_a, agent_b, agent_c)`. Do not overload colon shorthand with a
   comma-separated mini-language.
2. **Variadic typing:** add a variadic `agent` input capability, or a narrowly scoped
   equivalent for this workflow, so each positional value is validated and agent-name
   completion can repeat for later positions. A generic variadic input is cleaner than
   teaching the parser a `fork`-only comma string, but it is a larger framework change.
3. **Backward compatibility:** bare `#fork` and one-name `#fork:name` /
   `#fork(name)` should retain their current resolution and singular prompt shape. Use
   the plural envelope only for two or more resolved parents.
4. **Wait-all behavior:** extract every explicit fork target and add every target to the
   launch dependency set. The current “first fork name” helper is insufficient.
5. **Resolution result:** resolve all inputs to records containing at least
   `requested_name`, `resolved_name`, and `chat_path`. Render the concrete name. Preserve
   invocation order.
6. **Failure semantics:** resolve atomically and report all missing/unreadable parents in
   one error where practical. Do not launch with silently missing branches.
7. **Duplicate inputs:** reject duplicate resolved chat paths with a clear message. A
   duplicate parent has no useful semantics and would overweight that transcript.
8. **Nested forks:** call the existing recursive loader independently for each parent so
   each branch remains self-contained. This can duplicate shared ancestry, but sharing
   one `_visited` set across roots would make whichever parent appears first own the
   ancestry and create a subtler order dependency.
9. **Context limits:** estimate the completed prompt before launch. If it is too large,
   fail with total and per-parent sizes and suggest selecting fewer parents. Do not
   silently truncate or summarize a lossless fork.
10. **Sanitization:** retain the current historical-user sanitization and disabled-region
    protection. Quote only after `load_chat_for_resume()` returns the sanitized flat
    transcript.
11. **Lineage naming:** if implicit child naming still derives from a fork target, retain
    the first parent as the compatibility anchor or require an explicit `%name`; do not
    pretend the existing single-parent name encodes the whole multi-parent graph.

Exact common-ancestry factoring is a possible later optimization. A generalized solution
would need to represent a conversation DAG or build a trie of identical turn prefixes;
naively removing duplicate turns can erase meaningful provenance. Full, independently
expanded parent blocks are the safer first version.

## Suggested evaluations

Prompt changes should be evaluated across every supported agent runtime with the same
wrapper. At minimum, fixtures should cover:

- two complementary parents where the answer requires one fact from each;
- two parents with a material disagreement, verifying that the child does not silently
  choose one;
- swapped parent order, checking that the substantive result remains stable;
- parents with shared ancestry, verifying that the child understands them as branches;
- a historical prompt whose old instruction conflicts with the new query;
- three or more parents;
- headings, fenced code, xprompt-looking text, and XML/HTML inside transcripts;
- duplicate names or paths, a missing parent, and one still-running parent;
- a combined history near and beyond the target model's context budget;
- legacy singular and bare forms, which should render exactly as before.

Useful metrics are parent coverage, provenance accuracy, conflict detection, adherence
to the new query, order sensitivity, and prompt token count. Snapshot tests should pin
the exact rendered envelope, while behavioral evaluations should use tasks with known
facts and intentional contradictions rather than judging prose style.

## Recommended solution

Implement `#fork(agent_a, agent_b, ...)` as a lossless, wait-all **multi-parent fork**.
For two or more unique resolved agents, inject the exact `# Parent Conversations`
envelope shown in the executive summary: a concise semantics paragraph, one
invocation-ordered and concretely named Markdown block-quoted transcript per parent,
then `# New Query` last. Preserve the existing singular output for zero or one explicit
name, keep recursive loading and sanitization per parent, reject missing/duplicate
parents, and fail transparently on context overflow. This is the smallest prompt that
correctly preserves branch structure, provenance, active-instruction priority, and
conflict awareness without imposing a task-specific synthesis step.
