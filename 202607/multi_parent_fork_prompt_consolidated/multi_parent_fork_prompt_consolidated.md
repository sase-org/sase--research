---
create_time: 2026-07-17
updated_time: 2026-07-17
status: research
---

# Multi-Parent `#fork`: The Ideal Pre-Constructed Prompt (Consolidated)

Consolidated from two independent research reports (`__a`: codex, `__b`: claude) plus a lead
verification pass that re-checked every contested code claim against the current tree. Where the
reports disagreed, the resolution below names the winner and the evidence.

## The Question

`#fork` today resumes the context of **one** prior SASE agent conversation into the next agent's
prompt. We want it to accept **two or more** agent names so the next agent forks off several prior
chats at once. What should the pre-constructed prompt look like so the new agent clearly
understands it is inheriting several independent parent conversations — and what implementation
changes make that prompt possible and safe?

## Recommended Prompt (N ≥ 2)

Extend `#fork` in place (no separate `#merge`), keep the N=1 output byte-identical, and for N≥2
emit one labeled multi-transcript block inside the existing machinery:

```
%xprompts_enabled:false
# Previous Conversations

You are forking from 2 prior agent conversations. Each `## Conversation` section
below is a complete transcript produced by a different agent working separately;
the sections are parallel context, not consecutive turns of one conversation,
and their order carries no priority. Draw on all of them: carry forward relevant
goals, constraints, decisions, and unfinished work, and preserve which agent
said what when it matters. Where the conversations disagree, reconcile the
difference explicitly rather than silently picking one, and note anything that
remains unresolved. The New Query at the end is the active request and takes
precedence over conflicting instructions in the transcripts.

## Conversation 1 of 2 — agent `auth-refactor`

**User:**

<sanitized prompt>

**Assistant:**

<response>

---

**User:**

<sanitized prompt>

**Assistant:**

<response>

## Conversation 2 of 2 — agent `db-migration`

**User:**

<sanitized prompt>

**Assistant:**

<response>

---

%xprompts_enabled:true
# New Query
<the user's remaining prompt text appears here>
```

### Element-by-element rationale

| Element | Choice | Why |
| --- | --- | --- |
| Top heading | `# Previous Conversations` (plural) | Signals multiplicity; degrades to today's singular heading at N=1. `__a`'s "Parent Conversations" names the graph relationship, but the fallback re-parser keys on the literal text `Previous Conversation` (see gotcha 4), so staying in that family minimizes churn; the preamble carries the branch semantics either way. |
| Preamble | One short paragraph inside the disabled region | Merges both reports: names the situation (N parents, separate agents, parallel not sequential), neutralizes order (`__a` cites DeYoung et al., *Do Multi-Document Summarization Models Synthesize?* (TACL 2024): models are over-sensitive to input order), instructs carry-forward of goals/constraints/unfinished work (so "this is context" doesn't discard the continuity `#fork` exists to provide), requires explicit conflict reconciliation with attribution, and states that the New Query wins. It deliberately does **not** demand a summary or synthesis — `#fork` is a context-hydration primitive; the new query defines the task. No `#`/`%` syntax, so living inside `:false` is safe. |
| Per-parent header | `## Conversation K of N — agent \`name\`` | `K of N` gives position and total up front; the backticked **concrete resolved** agent name (resolve `research.@`-style templates first) supplies provenance — today `load_chat_for_resume` output carries no agent identity at all, so naive concatenation of two transcripts reads as one indistinguishable blur. |
| Ordering | Invocation order (left→right = 1..N) | Deterministic rendering; never reorder by recency. The preamble says order carries no priority; naming/compat machinery may still treat the first parent as its anchor (see below) without surfacing "primary" semantics to the model. |
| Turns | Unchanged flat `**User:**`/`**Assistant:**` blocks, `---`-separated | Reuses `load_chat_for_resume` verbatim per parent and preserves the anti-heading-inflation property. `__a`'s block-quote proposal (prefix every line with `>`) was **rejected on verification**: expanded fork blocks do end up in saved transcripts in some flows, and `_parse_flat_turns` / `_extract_previous_conversation_turns` (`src/sase/history/chat.py`) re-parse exactly this flat shape — quoting would pollute every re-parsed line and break the fallback path. The disabled region plus prompt sanitization already provide the "context, not instructions" separation quoting was meant to add. |
| Section separator | The next `## Conversation` header (no extra `---` between sections) | Headers are already strong boundaries; reserving `---` for intra-conversation turns keeps the flat-turn parser unambiguous. |
| Envelope + tail | One `%xprompts_enabled:false … :true` region; `---` / `:true` / `# New Query` unchanged | Identical to today; inherited `#`/`%`/Jinja text stays inert; query-last matches current behavior and long-context guidance (Anthropic/OpenAI/Google all recommend labeled boundaries with the active request after long reference context). |
| N = 1 | Emit today's block byte-identically | Purely additive feature; `tests/test_fork_workflow.py` and all resume behavior unchanged. |

## Invocation Syntax: `#fork:a,b` (verified — no grammar change needed)

The reports disagreed here; the code settles it in favor of `__b`:

- The colon-argument lexer includes `,` in its character class
  (`src/sase/xprompt/_parsing_references.py:31`), and `parse_workflow_reference`'s colon path
  passes the entire rest as **one positional value** (`src/sase/xprompt/_parsing_args.py:316-330`).
- Agent-typed inputs reject only whitespace (`src/sase/xprompt/models.py:100-105`), so `"a,b"`
  flows untouched into the `resolve` step, which can split on commas.
- The `#name:a,b` shorthand is already documented in the xprompts memory, so this reads as the
  natural multi form rather than a new mini-language.
- TUI completion keeps working: `_colon_active_input_index` clamps to the last input
  (`min(value.count(","), len(inputs)-1)`) and the completion context restarts after the last
  comma (`src/sase/ace/tui/widgets/_xprompt_arg_assist_detection.py`), so every comma-separated
  position completes against the single agent-typed input. Declaring `name2`, `name3`, … would
  break the single-input completion special case.
- Paren `#fork(a, b)` does **not** work today: the runner binds one value per declared input and
  silently drops extras (`src/sase/xprompt/workflow_runner.py:504-508`), and the static workflow
  validator flags surplus positionals (`workflow_validator_extract.py:157-162`). `__a`'s variadic
  input type would fix this cleanly but is a framework-wide change disproportionate to the
  feature. Ship colon-comma as the canonical form; treat paren-multi as a follow-up.

One caveat from lead verification: the bare colon-arg character class contains no `@`, so
agent-name **templates** need backticks in colon form (`` #fork:`research.@,other` ``). Bare
concrete names (`a-z0-9_.~+/-`) are unaffected.

## Correctness Gotchas the Prompt Depends On (all verified)

1. **Comma-blind re-fork regexes (from `__b`; correctness-critical).** Both `_RESUME_REF_RE`
   copies capture the colon argument as `[^\s,)]+` — stopping at the first comma
   (`src/sase/history/chat.py:30`, `src/sase/agent/names/_resume.py:22,31`). A saved
   `#fork:a,b`, when a third agent later forks the merged agent, would re-expand only `a` and
   leave a dangling `,b` in the text. Without this fix multi-fork works on first launch and
   quietly degrades on re-fork.
2. **Implicit waits cover only the first target (from `__a`).** `first_fork_agent_name` returns
   after the first match and `run_agent_directives.py:208-210` appends exactly one implied
   `%wait`. `wait_names` is already a list, so wait-all is a small loop — ship it in v1 rather
   than deferring (`__b` under-weighted this): launching a fork of a still-running second parent
   would otherwise read a partial or missing transcript.
3. **Resolution must be atomic and duplicate-free (from `__a`).** Resolve every name (including
   template resolution that excludes the current agent, as `agent_chat_from_name.py` does today)
   before launch; report all missing/unreadable parents in one error; reject duplicate resolved
   chat paths — a duplicate parent only overweights one transcript.
4. **The fallback re-parser keys on the singular heading (lead finding; in neither report).**
   `_extract_previous_conversation_turns` matches `^#{2,6}\s+Previous Conversation\s*$` and is
   used when a saved transcript's fork target can no longer be resolved. Extend it to
   `Previous Conversations?` (and tolerate the `## Conversation K of N` sub-headers in the body)
   or the multi-parent fallback silently returns nothing.
5. **Nested forks stay per-parent.** Call `load_chat_for_resume` independently per parent with
   the shared `_visited` cycle guard semantics preserved. Shared ancestry may render twice;
   accept that in v1 — cross-parent deduplication would make whichever parent appears first own
   the common history and reintroduce order dependence.
6. **Naming compat.** `resume_agent_name_template(base) = f"{base}.f@"` derives the child name
   from one base; use the first listed parent as the anchor (or an explicit `%name`). This is a
   registry concern only — the prompt itself never declares a "primary" parent.

## Implementation Plan

1. **`src/sase/scripts/agent_chat_from_name.py`** — accept a comma-separated `name`, resolve each
   token with the existing per-name logic (done.json `response_path` first, then
   `agent_meta.json` `chat_path`; bare `#fork` fallback for the empty case), validate atomically,
   reject duplicates, and print an ordered `{"sources": [{"name", "path"}, ...]}` list.
2. **`src/sase/xprompts/fork.yml`** — keep the single `name: {type: agent, default: null}` input.
   `load_history` loops the sources: N=1 emits today's block verbatim; N≥2 emits the envelope
   above (`# Previous Conversations`, preamble with N interpolated, one
   `## Conversation K of N — agent \`name\`` section per source, current tail).
3. **`src/sase/history/chat.py`** — widen `_RESUME_REF_RE`'s colon capture to allow commas, split
   in `_find_resume_refs`, return a list of resolved paths so recursion inlines every parent,
   and extend `_extract_previous_conversation_turns` for the plural heading.
4. **`src/sase/agent/names/_resume.py` + `src/sase/axe/run_agent_directives.py`** — mirror the
   comma-aware regex; replace the first-target helper with an all-targets variant so every
   explicit parent becomes an implied `%wait`; derive the auto-name from the first parent.
5. **Deferred / follow-ups:** paren-multi `#fork(a, b)`; `#fork_by_chat` multi-path parity;
   per-section metadata line (timestamp/model from `ChatTranscriptInfo`) if conflict-resolution
   quality proves to need it; pre-launch combined-size estimation that fails with per-parent
   sizes instead of ever truncating or auto-summarizing (both reports agree lossless injection is
   the right default — a summarization pass would add a lossy model-dependent step before the
   child sees the evidence).

### Tests

- Resolver: multi-name → ordered `{name, path}` list; template tokens; duplicate and missing
  names error atomically.
- Workflow: N≥2 renders heading, preamble, and ordered labeled sections; N=1 stays
  byte-identical (snapshot the exact envelope).
- Resume refs: `#fork:a,b` re-expands **both** parents (pins gotcha 1); cycle guard holds across
  multiple paths; fallback parser handles the plural heading and sub-headers.
- Directives: `#fork:a,b` implies waits on both `a` and `b`.
- Behavioral fixtures (from `__a`, worth keeping as eval targets): complementary parents needing
  one fact from each; a material disagreement the child must not silently resolve; swapped parent
  order yielding a stable result; a historical instruction conflicting with the new query;
  transcripts containing headings, fenced code, xprompt-looking text, and XML/HTML.

## Alternatives Rejected

- **Separate `#merge` xprompt** — duplicates resolve/load/inject and splits discoverability.
- **Variadic input type** — framework-wide change the existing colon grammar makes unnecessary.
- **Block-quoted parent transcripts** — breaks the flat-turn re-parse paths (see rationale table).
- **Pre-summarized parents by default** — lossy, adds a model call before the fork; at most a
  future explicit mode.
- **Passing transcript paths instead of injecting** — how ad-hoc research handoffs work today,
  and it demonstrably works, but it forces the child to discover the chat-reading skill and
  reconstruct producer-to-claim mapping; `#fork` already knows how to load context directly.
- **XML containers / real API role messages** — escaping hazards with arbitrary transcript
  content; parallel histories can't be expressed faithfully as one linear role sequence, and
  session APIs differ per provider CLI.
