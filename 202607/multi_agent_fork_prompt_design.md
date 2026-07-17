---
create_time: 2026-07-17
updated_time: 2026-07-17
status: research
---

# Multi-Agent `#fork`: The Ideal Pre-Constructed Prompt for Forking Off 2+ Agents

## The Question

The `#fork` xprompt workflow resumes the context of **one** prior SASE agent conversation into the next agent's
prompt. We want to extend it to accept **two or more** agent names as arguments (e.g. `#fork:auth-refactor,db-migration`)
so the next agent forks off of several prior chats at once. The central question: **what should the pre-constructed
prompt injected into the forking agent look like** so that the agent clearly understands it is inheriting context from
multiple, independent parent conversations — and, secondarily, what implementation changes make that prompt possible?

## Headline

**Extend `#fork` (do not add a separate `#merge`), keep the single-agent output byte-identical, and for N≥2 emit one
labeled multi-transcript block:** a short preamble that names the situation ("you are forking from N prior
conversations"), then one `## Conversation K of N — agent \`name\`` section per parent, each holding that parent's
existing flat `**User:**`/`**Assistant:**` turns, all inside the existing `%xprompts_enabled:false … :true` envelope,
terminated by the existing `# New Query` lead-in. The load-bearing change relative to today is **per-source
attribution** — today's `load_chat_for_resume` output carries no agent identity at all, so a naive concatenation of two
transcripts would read as one indistinguishable blur.

The grammar and value-validation already accept the multi-agent invocation (`#fork:a,b` delivers `"a,b"` to a single
`type: agent` input untouched, because agent-typed values reject only whitespace, not commas). The real work is four
small, well-scoped edits: the resolver script, the `load_history` step, and two single-argument regexes that must
become comma-aware so re-forking a merged agent still re-expands *all* of its parents. **No new xprompt input type and
no fixed arity limit are required.**

---

## 1. How the single-agent fork works today

### 1.1 The workflow (`src/sase/xprompts/fork.yml`)

```yaml
input:
  name:
    type: agent
    default: null
steps:
  - name: resolve      # hidden
    python: |
      from sase.scripts.agent_chat_from_name import main
      name = {{ name | tojson }}
      main([name] if name else [])
    output: { path: text }
  - name: load_history # hidden
    python: |
      from sase.history.chat import load_chat_for_resume
      history = load_chat_for_resume({{ resolve.path | tojson }})
      injected_history = (
          "%xprompts_enabled:false\n"
          "# Previous Conversation\n\n"
          f"{history}\n\n"
          "---\n\n"
          "%xprompts_enabled:true\n"
          "# New Query"
      )
      print(json.dumps({"injected_history": injected_history}))
    output: { injected_history: text }
  - name: inject
    prompt_part: |
      {{ load_history.injected_history }}
```

Three hidden steps: **resolve** a name → a chat path (`src/sase/scripts/agent_chat_from_name.py`), **load** that chat
into flat turns (`load_chat_for_resume`), **inject** the wrapped block via `prompt_part`. When the user writes
`#fork:builder\nKeep going`, the reference is expanded inline and the surrounding user text is preserved after
`# New Query` (verified by `tests/test_fork_workflow.py`: the expanded prompt contains the chat text, `# Previous
Conversation`, and the surrounding `Review`/`Continue` text).

### 1.2 The exact injected block

```
%xprompts_enabled:false
# Previous Conversation

**User:**

<sanitized prompt>

**Assistant:**

<response>

---

**User:**

<sanitized prompt>

**Assistant:**

<response>

---

%xprompts_enabled:true
# New Query
<the user's remaining prompt text appears here>
```

Key facts about the pieces (`src/sase/history/chat.py`):

- **`load_chat_for_resume(path)`** parses a transcript into chronological `(prompt, response)` turns and emits them as
  flat blocks joined by `\n\n---\n\n`, each block literally
  `**User:**\n\n{clean_prompt}\n\n**Assistant:**\n\n{response}`. It deliberately uses **bold markers, not headings**, so
  repeated resumes don't inflate heading levels.
- **No attribution.** The returned text has no header, no agent name, no timestamp, no model. Agent identity exists only
  in the source `.md` file (filename, the `# Chat History - <workflow> (<agent>)` banner, and the `**AGENT:**` metadata
  row) and in `ChatTranscriptInfo.agent` from `chat_catalog.py` — all of which `load_chat_for_resume` discards.
- **`%xprompts_enabled:false … :true`** marks a *disabled region* (`src/sase/xprompt/_disabled_regions.py`): everything
  between the markers is shielded from xprompt/directive re-interpretation, so literal `#foo`/`%bar`/`{{ }}` in the
  historical transcript is treated as inert content. `# New Query` sits after `:true` and is processed normally.
- **`_sanitize_resume_prompt`** strips SASE control syntax (`%name` directives, `#`/`#!` refs, unrendered Jinja) from
  each historical *user* prompt so the transcript reads as clean natural language; assistant responses are left
  untouched.

### 1.3 Re-fork recursion (why this matters for the design)

The saved transcript's `## Prompt` section retains the raw `#fork:` reference; `load_chat_for_resume` **re-expands
those references at read time** (`_find_resume_refs` → `_resolve_resume_to_chat_path` → recursive `load_chat_for_resume`
with a `_visited` cycle-guard). This is the *only* place today where multiple histories concatenate — but strictly
transitively (a parent's own single parent), never a top-level *set* of co-equal parents. Any multi-parent design must
keep this recursion working, or re-forking a merged agent will silently drop parents (see §4.3).

---

## 2. What changes with two or more parents

Concatenating two `load_chat_for_resume` outputs under one `# Previous Conversation` heading would produce a single
undifferentiated stream of `**User:**`/`**Assistant:**` turns from two different agents about two different tasks. The
forking agent could not tell where one conversation ends and the next begins, which turns belong together, or that the
two threads are *parallel* rather than *sequential*. Three properties must be added:

1. **Provenance** — each conversation must be labeled with its source agent's name.
2. **Boundaries** — each conversation must be a visually distinct, self-contained section.
3. **Framing** — a preamble must tell the agent it is *merging* N independent threads and how to treat conflicts,
   because "fork off two agents" is a genuinely new mental model (nothing in the codebase does it today — §4.1).

Everything else (the disabled-region envelope, the flat-turn format inside each conversation, the `# New Query`
lead-in) should be **reused unchanged** so the N=1 case stays byte-identical and existing tests/behavior don't churn.

---

## 3. The ideal pre-constructed prompt

### 3.1 Worked example (N = 2)

```
%xprompts_enabled:false
# Previous Conversations

You are forking from 2 prior agent conversations. Each `## Conversation` section
below is a complete, independent transcript produced by a different agent working
separately. Treat them as parallel context you are merging: draw on all of them to
answer the new query, and when they disagree, reconcile the difference explicitly
rather than silently picking one.

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

### 3.2 Element-by-element rationale

| Element | Choice | Why |
| --- | --- | --- |
| Top heading | `# Previous Conversations` (plural) | Signals multiplicity immediately; degrades to the existing singular `# Previous Conversation` when N=1. |
| Preamble | One short paragraph, inside the disabled region | Names the situation ("forking from N conversations"), asserts the threads are **independent/parallel**, and gives a conflict-resolution instruction. This is the piece that makes a *merge* legible rather than a blur. It contains no `#`/`%` directives, so living inside `:false` is safe. |
| Per-conversation header | `## Conversation K of N — agent \`name\`` | `K of N` tells the agent the total up front and its position; the backticked agent name supplies provenance. `##` is one level below the `#` top heading and never collides with the `Prompt`/`Response` heading pattern the re-fork parser looks for (§4.3). |
| Ordering | User-specified order (left→right = 1..N) | Order is intentional (the user chose to list `auth-refactor` before `db-migration`); do **not** silently reorder by recency. If a "primary" parent matters, it is the first one listed. |
| Intra-conversation turns | Unchanged `**User:**`/`**Assistant:**` flat turns, `---`-separated | Reuses `load_chat_for_resume` verbatim per source; preserves the anti-heading-inflation property. |
| Inter-conversation separator | The next `## Conversation` header (no extra `---` between sections) | The header is already a strong boundary; reserving `---` for intra-conversation turn separation keeps the re-fork flat-turn parser unambiguous. |
| Envelope | One `%xprompts_enabled:false … :true` region around the whole block | Matches today's design; one region is simpler than one-per-source and equally correct. |
| Closing | `---` then `%xprompts_enabled:true` then `# New Query` | Identical to today, so the handoff to the user's new instructions is unchanged. |

### 3.3 Optional enrichment (recommend deferring)

A compact metadata line under each header — e.g. `_(run · 2026-07-15 14:02)_` from the transcript banner — would help
the "prefer the most recent" reconciliation instruction. It is available (`ChatTranscriptInfo` / the `**TIMESTAMP:**`
row) but requires reading each source's banner separately. Recommend shipping without it first and adding it only if
conflict-resolution quality proves to need it.

### 3.4 Backward compatibility (N = 1)

For a single agent, emit the **exact current block** (`# Previous Conversation`, no preamble, no `## Conversation`
header). The multi-conversation format is a strict superset activated only at N≥2. This keeps `test_fork_workflow.py`
and all existing resume behavior unchanged and makes the feature purely additive.

---

## 4. Constraints imposed by the current implementation

### 4.1 No multi-parent concept exists anywhere

`fork.yml`/`fork_by_chat.yml` each take one input; `names/_resume.py` `first_resume_agent_name` /`first_fork_agent_name`
return after the **first** match; `resume_agent_name_template(base) = f"{base}.f@"` derives a child name from exactly one
base; `multi_prompt_reference_*` "multi" refers to launching several agents *sequentially from one command*, not one
agent with several parents. A multi-parent fork is new ground — there is no prior pattern to conform to, which is why
the explicit framing preamble (§3.2) matters.

### 4.2 No variadic xprompt input — but the grammar already carries the list

`InputType` has no list member and `InputArg.validate_and_convert` is strictly `str → scalar`; positional binding is
one-value-per-input and extra positionals are dropped (`workflow_runner.py`). **However**, the invocation grammar
already supports the multi form, and one detail makes a schema change unnecessary:

- **Colon-comma** `#fork:a,b`: the reference lexer's colon-argument fragment (`_parsing_references.py`) *includes* `,`
  in its character class, so `a,b` arrives as a **single** value `"a,b"`. Agent-typed validation rejects only
  whitespace, so `"a,b"` passes through untouched to the `resolve` step, which can `split(",")`. **This is the canonical
  multi form** and it aligns with the documented `#name:a,b` shorthand.
- **Paren** `#fork(a, b)`: `parse_args` tokenizes on commas into positionals `["a","b"]`; with a single input only `a`
  binds and `b` is dropped. Supporting paren-multi therefore needs either a second declared input or a runner tweak to
  fold leftover positionals into the first input — recommend documenting colon as the multi form for v1 and treating
  paren-multi as a follow-up.

### 4.3 The re-fork regexes are single-argument (correctness-critical)

`_RESUME_REF_RE` in `chat.py` captures the colon argument as `[^\s,)]+` — it **stops at the first comma**. So a saved
`#fork:auth-refactor,db-migration`, when a *third* agent later forks off the merged agent, would re-expand only
`auth-refactor` and silently lose `db-migration` (and leave a dangling `,db-migration` in the text). The sibling
`_RESUME_REF_RE` in `names/_resume.py` (used for name allocation and implicit waits) has the same limitation. Both must
become comma-aware, and `_resolve_resume_to_chat_path` must return a *list* of paths so the recursion inlines every
parent. This is the least obvious but most important code change — without it, multi-fork works on first launch but
quietly degrades on re-fork.

### 4.4 TUI completion nuance

`_xprompt_arg_assist_detection.py` only auto-offers agent-name completion for **single-input** xprompts in paren
syntax; with the colon-comma form, each comma-separated position completes against the input's type, so
`#fork:auth-,db-…` still gets agent completion. This is another reason to keep a single `type: agent` input and prefer
the colon form rather than declaring `name`, `name2`, … (which would break the single-input completion special case).

### 4.5 Naming and waits for multiple parents (secondary)

If forking off *live* (not yet completed) agents, the new agent should arguably `%wait` on all of them; `#fork`
primarily targets completed agents (it resolves `done.json`'s `response_path` first), so this is a lower priority. For
auto-naming, derive the forked child's name from the **first** listed parent (the primary), keeping
`resume_agent_name_template` deterministic. Both are follow-ups, not blockers for the prompt design.

---

## 5. Recommended solution

**Extend `#fork` in place**, keep a single `type: agent` input, make `#fork:a,b` the canonical multi form, and localize
the change to four spots. Alternatives (a separate `#merge` xprompt; a new variadic input type) were considered and
rejected: `#merge` duplicates resolve/load/inject and splits discoverability, while a variadic input type is a
framework-wide change far larger than this feature warrants when the grammar already carries the comma-list.

### 5.1 Concrete changes

1. **`src/sase/scripts/agent_chat_from_name.py`** — accept a comma-separated `name`, resolve **each** token (reusing the
   existing per-name resolution, including bare-`#fork` "most recent" fallback for the empty case), and print an ordered
   list of `{name, path}` sources instead of a single `{path}`. Preserve current single-name output shape or bump both
   the script and `fork.yml` together.

2. **`src/sase/xprompts/fork.yml`** — keep `input: name {type: agent, default: null}` (no schema change). Update
   `resolve` to emit the sources list, and rewrite `load_history` to:
   - loop the sources, calling `load_chat_for_resume` once per source;
   - for **N=1**, emit the current block verbatim (backward compat);
   - for **N≥2**, emit `# Previous Conversations` + the preamble + one `## Conversation K of N — agent \`name\`` section
     per source, all inside the existing envelope, terminated by the current `--- / :true / # New Query` tail.

   Sketch of the N≥2 body:
   ```python
   header = "%xprompts_enabled:false\n# Previous Conversations\n\n" + PREAMBLE.format(n=len(sources))
   sections = []
   for i, src in enumerate(sources, start=1):
       history = load_chat_for_resume(src["path"])
       sections.append(f"## Conversation {i} of {len(sources)} — agent `{src['name']}`\n\n{history}")
   body = "\n\n".join(sections)
   injected = header + "\n\n" + body + "\n\n---\n\n%xprompts_enabled:true\n# New Query"
   ```

3. **`src/sase/history/chat.py`** — widen `_RESUME_REF_RE`'s colon capture to allow commas, split the argument on
   commas in `_find_resume_refs`/`_resolve_resume_to_chat_path`, and make resolution return a **list** of paths so the
   `load_chat_for_resume` recursion inlines every parent (fixes §4.3). Preserve `_visited` cycle-guarding across all
   resolved paths.

4. **`src/sase/agent/names/_resume.py`** — mirror the comma-aware regex so name allocation / implicit waits see all
   parents; derive the forked child's auto-name from the first listed parent.

### 5.2 Tests to add

- `tests/test_agent_chat_from_name.py`: multi-name resolution → ordered `{name, path}` list; whitespace/empty handling.
- `tests/test_fork_workflow.py`: N≥2 produces `# Previous Conversations`, the preamble, and one
  `## Conversation K of N — agent \`name\`` per source in order; N=1 stays byte-identical.
- `tests/history/test_chat_resume_refs.py`: `#fork:a,b` re-expands **both** parents (guards §4.3 regression);
  cycle-guard holds with multiple paths.

### 5.3 Risk assessment

Low. The prompt-shape change is additive and gated on N≥2; the only sharp edge is the re-fork regex (§4.3), which the
dedicated resume-refs test above pins. No new input type, no arity cap, no change to the disabled-region or flat-turn
machinery.

---

## 6. Open questions

- **Paren-multi** `#fork(a, b)`: ship colon-only for v1, or also fold leftover positionals into the first input so both
  syntaxes work? (Recommend: colon-only first, document it.)
- **Live-parent waits**: should multi-fork off running agents auto-`%wait` on all parents, or stay
  completed-agent-only? (Recommend: completed-only first.)
- **De-duplication**: if two listed parents share a common ancestor (via §1.3 recursion), the shared turns can appear
  twice. Acceptable for v1? The `_visited` guard prevents infinite loops but not cross-parent duplication.
- **Metadata line** (§3.3): include per-conversation timestamp/model now, or defer?

---

## Appendix — file reference map

- `src/sase/xprompts/fork.yml`, `src/sase/xprompts/fork_by_chat.yml` — the fork workflows.
- `src/sase/scripts/agent_chat_from_name.py` — name → chat-path resolver (resolve step).
- `src/sase/history/chat.py` — `load_chat_for_resume`, `_RESUME_REF_RE`, `_find_resume_refs`,
  `_resolve_resume_to_chat_path`, `_sanitize_resume_prompt`, transcript save/format.
- `src/sase/history/chat_catalog.py` — `ChatTranscriptInfo` (per-transcript agent/workflow/timestamp).
- `src/sase/xprompt/_disabled_regions.py` — `%xprompts_enabled:false/true` region handling.
- `src/sase/xprompt/_parsing_references.py`, `src/sase/xprompt/_parsing_args.py` — invocation grammar (colon includes
  `,`; paren tokenizes on `,`).
- `src/sase/xprompt/models.py`, `loader_parsing.py`, `workflow_runner.py` — input types, validation, positional binding.
- `src/sase/agent/names/_resume.py` — resume/fork name allocation, `resume_agent_name_template`.
- `src/sase/ace/tui/widgets/_xprompt_arg_assist_detection.py`, `directive_completion.py` — TUI agent-name completion.
- Tests: `tests/test_fork_workflow.py`, `tests/test_agent_chat_from_name.py`, `tests/history/test_chat_resume_refs.py`,
  `tests/history/test_chat_resume_sanitize.py`.
</content>
</invoke>
