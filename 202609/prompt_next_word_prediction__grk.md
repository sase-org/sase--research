# Next-word prediction in the prompt input: research and recommended design

**Researcher:** `research.l.grk` (Grok)  
**Date:** 2026-09-28  
**Question:** How should sase's TUI prompt bar predict the *very next word*, driven by the user's / project's prompt history, and how should `<ctrl+t>` chain those guesses after completing a word?

This report is independent. It does not consult peer swarm reports.

---

## Recommendation

Build it. Chained next-word after prose completion is a good idea, and the current prompt bar is one binding change plus one new index away from it.

Do **not** treat this as a new completion kind that invents English. Treat it as **partial accept of a history continuation**, the same interaction fish, zsh-autosuggestions, and VS Code inline suggestions already teach:

1. Find a high-confidence continuation of the text already in the bar.
2. Show it as muted ghost text on the current line.
3. Each `<ctrl+t>` at a complete-word boundary inserts **one word** of that continuation, then refreshes the ghost.

The corpus is the machine-local prompt-history shards (already warmed for history-word completion), with a same-project boost from the existing Ctrl+K project-identity matcher. The "common sense" layer is the project's own reusable phrasing — xprompt bodies, `ace.snippets`, and canonical archived prompts — ranked *below* personal history. A general English language model, KenLM, or an LLM call on the keystroke path is the wrong tool.

Keep today's unique-match and shared-prefix behavior for the *current* token. Use the currently near-noop **second** `<ctrl+t>` on an open *word* menu to accept the highlighted row, then enter the chain.

---

## 1. Is the original plan a good idea?

Yes, with a tighter model of what "excellent" means here.

The operator already reuses phrasing across launches. Prompt history is sharded JSON under `~/.sase/prompt_history/`, indexed off-thread, and already consulted for **prefix completion of the current word**. The missing piece is sequential: after `authentication` is committed, the next press should be able to insert `middleware` because that pair actually occurred in a recent prompt.

That interaction is high-leverage **when precision is high**. A wrong next word that the user keeps accepting by rhythm is worse than silence. Fish-style history continuation is high precision because it replays text the user already wrote. Statistical bigrams of `"the"` are low precision. The design should optimize for the first and refuse to guess in the second.

The original sketch (`<ctrl+t><ctrl+t>` completes the selected word, further `<ctrl+t>` walks next words) matches a hole in the current keymap: on an open prompt-local / history-word menu with no remaining shared prefix, a second `<ctrl+t>` re-dispatches and rebuilds the same menu. That press is available. Unique matches already commit on the first press, so the chain starts on the second.

---

## 2. Justified adjustments to the requirements

These change the original request. Each is a requirement for the implementation, not an optional extra.

| ID | Adjustment | Why |
| --- | --- | --- |
| A1 | Unique current-token matches keep completing on the **first** `<ctrl+t>`. The next press starts next-word. | Today's contract in `_try_prompt_word_completion_tab` / `_try_history_word_completion_tab`: a single candidate calls `_commit_word_completion` immediately. Requiring two presses to commit `GitHub` from `Gith` is a regression. |
| A2 | Shared-prefix extension on the **first** `<ctrl+t>` stays. The "accept selected" meaning of a **second** `<ctrl+t>` applies only when a word menu is already open and no longer shared prefix remains. | First press already extends `te` → `test` while leaving `test` / `tests` / `testing` on screen. That is the bash/zsh "complete as far as possible" step. The second press is the one that is free. |
| A3 | Scope the new accept-and-chain behavior to `prompt_word` and `history_word` only. Structured kinds (`#`, `%`, `=`, `@`, paths, Jinja, placeholders, VCS refs) keep today's `<ctrl+t>` dispatcher. | Bare-`@` already uses "first `<ctrl+t>` reveals files, later press completes" (`_try_artifact_ref_completion_tab`). Path completion uses `<ctrl+t>` for shared prefix and directory drill-down. Command Line uses `<ctrl+t>` to toggle full height. Colliding with those would make the feature feel broken in the places the bar is already excellent. |
| A4 | Trigger next-word when the cursor is at a **complete-word boundary** (end of an identifier-like word, or the space immediately after one), including after Ctrl+F / Ctrl+L acceptance. | `_commit_word_completion` leaves the cursor on the last character of the committed word, so a follow-up `<ctrl+t>` currently sees a prefix that is an exact match and is suppressed as a no-op. That is the natural chain slot. Ctrl+F must enter the same chain, or two accept chords would disagree. |
| A5 | On whitespace after a complete word, try next-word **before** file-history. Empty prompt and leading whitespace keep file-history. | `extract_token_around_cursor` returns `None` on whitespace, and `_try_file_completion_tab` then opens recently referenced files. If the chain ever leaves a trailing space, or the user spaces then taps `<ctrl+t>`, file-history would steal the press. |
| A6 | Predict from **contiguous history phrases** and **whole-prompt prefix matches**. Do not query the existing bag-of-words `PromptWordIndex` for "the next word." | The current index unique-ifies words per prompt, drops tokens shorter than `ace.prompt_completion.word_min_length` (default 5), and ranks by *same-prompt co-occurrence*, not order. `"review"` and `"middleware"` sharing a prompt does not mean `"middleware"` follows `"review"`. Glue words (`the`, `for`, `with`) are exactly the tokens a chain needs, and they are currently ineligible. |
| A7 | "Common sense" = lower-priority **project phrasing** (xprompt bodies, snippets, canonical archived prompts). No general English LM, no KenLM, no LLM on the keystroke path. | Generic next-word models on English news/web data predict function words. Operator prompts are a tiny, repetitive domain. The project's own templates already encode the useful prior. A neural guess is slower, less private, and worse on this corpus. |
| A8 | Show the continuation as **Textual `TextArea.suggestion` ghost text** (next 1–3 words). `<ctrl+t>` accepts one word. **Do not** let right-arrow accept the ghost in the prompt bar. | Textual 8.x renders `suggestion` at the cursor and `action_cursor_right` inserts the *entire* suggestion. Command Line already uses this for fish-style remainder, and overrides right-arrow so it only accepts at end of line. In the vim prompt, right-arrow is cursor motion. Auto-inserting a remainder mid-edit would fight INSERT-mode editing. Cap the visible ghost; the chain can still walk a longer remainder. |
| A9 | If several next words are plausible, open a small next-word menu. Insert immediately only when the continuation is unique or dominant. Silence beats a wrong insert. | Chained `<ctrl+t>` is a rhythm. A 40% guess that the user has to undo on every other press trains them to stop using it. |
| A10 | TUI-first. sase-nvim / LSP get a helper-bridge later, not in v1. | The TUI already owns the warmed history-word cache and the `<ctrl+t>` dispatcher. The nvim plugin mirrors structured completion through `sase lsp`; next-word is a local-history client feature. |

---

## 3. What the prompt bar already does

### 3.1 Completion dispatcher

`PromptTextArea` is a multiline Textual `TextArea` (`src/sase/ace/tui/widgets/prompt_text_area.py`). INSERT-mode `<ctrl+t>` always calls `_try_file_completion_tab` (`_prompt_text_area_key_handling.py`). That dispatcher is exhaustive and kind-specific (`docs/ace.md` Completion):

- `#` / `#!` / `/skill` → xprompts
- `+query` → projects / Patches
- `#gh:` / `#git:` → VCS refs and repos
- `%` and `=` / `==` → directives and model shortcuts
- `@` → artifact kinds / payloads (first `<ctrl+t>` on a gated kind menu *reveals files*)
- `<placeholder>` → current-prompt then saved tags
- path-like tokens → filesystem
- whitespace / empty prefix → file-reference history
- remaining prose → **prompt-local words**, then **history words**

Active-menu keys today (`_prompt_text_area_key_handling.py`):

| Key | Action |
| --- | --- |
| `<ctrl+n>` / Down | next row |
| `<ctrl+p>` / Up | previous row |
| `<ctrl+f>` / `<ctrl+l>` | accept highlighted |
| Enter | submit the prompt as typed; never accept |
| `<ctrl+d>` | delete a recent file, saved placeholder, or history word |
| Escape | cancel |
| `<ctrl+t>` | **not** handled in the active-menu branch; falls through to re-dispatch |

Soft live suggestions (`ace.prompt_completion.auto: soft`) appear in the prompt-bar subtitle and accept with `<ctrl+l>`. `build_prompt_soft_completion` covers Jinja, xprompt args, directives, xprompts, and optional file paths. It does **not** suggest history words or next words.

### 3.2 How `<ctrl+t>` treats the current word

For prompt-local and history words (`_file_completion_tab.py`):

1. One eligible candidate → `_commit_word_completion` and close the menu.
2. Several candidates sharing a longer prefix → insert that prefix, keep the menu.
3. Several candidates with no extra shared prefix → open / refresh the menu.

`_commit_word_completion` (`_file_completion_base.py`) replaces only the typed prefix. A right-hand suffix gets a separating space and the cursor stays immediately after the committed word. At a plain boundary with no suffix, an exact-prefix candidate is suppressed as a no-op.

So after committing `authentication`, the next `<ctrl+t>` currently does nothing useful. That is the chain hook.

### 3.3 History-word infrastructure (reuse this, extend it)

| Piece | Role |
| --- | --- |
| `~/.sase/prompt_history/YYMM.json` | Monthly shards; `PromptEntry` is `{text, timestamp, last_used, cancelled}`. No project field. Project identity is parsed from the prompt text (`+tag`, `#gh:…`) by `prompt_history_project_filter.py`. |
| `build_prompt_word_index` | Off-thread, mtime-tokenized, 24 newest shards / 20 000 prompts. Tokenizer is identifier-like (`[\w\-]+`), `min_length` default 5, digits-only dropped. **Order is discarded**: each prompt becomes a set of word ids. |
| `_cached_tokenized_shard` | Already keeps ordered word tuples per prompt before the index unique-ifies them. Sequential data is one step away. |
| `prompt_word_ranking.py` | Smart rank = 0.50 relation + 0.30 recency + 0.20 frequency. Relation is *same-prompt lift* (TF-IDF-ish), not next-word. |
| `StartupHistoryWordsMixin` | App-global warm cache; `Ctrl+D` deletions live in `prompt_word_deletions.json` and apply at query time without a rebuild. |
| File-history on whitespace | Separate store (`file_reference_history.json`). |

Cancelled drafts are included in shard loads. That is desirable for next-word: abandoned phrasing is how the operator actually types.

### 3.4 A sibling that already solved "history continuation"

The `:` Command Line (`src/sase/history/command_line.py`, `command_line/history.py`) stores up to 1 000 lines and implements `ghost_for_prefix`: the remainder of the best prefix match, same-cwd first. The input widget sets `TextArea.suggestion` when the cursor is at end of line; `→` accepts the remainder. That is fish autosuggestions on a single line.

The prompt bar should copy the *data model* (prefix match against stored text) and the *paint path* (`suggestion`), and keep `<ctrl+t>` as the word-at-a-time accept chord. Right-arrow stays motion.

---

## 4. Binding analysis: why `<ctrl+t>` for the chain is right

Industry next-word / partial-accept chords:

| Surface | Show guess | Accept all | Accept one word |
| --- | --- | --- | --- |
| fish | ghost as you type | `→` / `Ctrl+F` / End at EOL | `Alt+F` / `Alt+→` / `Ctrl+→` (token) |
| zsh-autosuggestions | ghost as you type | `forward-char` / `end-of-line` | `forward-word` family (`ZSH_AUTOSUGGEST_PARTIAL_ACCEPT_WIDGETS`) |
| VS Code / Copilot | inline ghost | Tab | `Ctrl/Cmd+→` (`editor.action.inlineSuggest.acceptNextWord`) |
| SASE Command Line | `TextArea.suggestion` | `→` at EOL | none yet |
| SASE prompt bar | subtitle soft-complete for *structured* tokens; menu for words | Ctrl+F / Ctrl+L | **this feature** |

The prompt bar already stole INSERT `<ctrl+t>` from vim's indent mapping and made it the completion dispatcher. Operators who complete words with `<ctrl+t>` will keep tapping it. Teaching a second chord (`Ctrl+Right`, `Alt+F`) for the chain would split the muscle memory the request is trying to build.

What `<ctrl+t>` must **not** become:

- A replacement for Ctrl+F on xprompt / path / `@` menus.
- An auto-accept of the first row the moment a word menu opens. The first press still opens (and maybe extends a shared prefix). The highlighted row is accepted on the *next* press, matching the request's `<ctrl+t><ctrl+t>`.
- Right-arrow. Textual's default `action_cursor_right` inserts the full `suggestion`. `PromptTextArea` must override that to `move_cursor` whenever a next-word ghost is showing, or vim INSERT motion regresses.

Recommended INSERT contract after this change:

```
<ctrl+t> on a structured token     → existing dispatcher
<ctrl+t> on a partial prose word   → existing word menu / unique commit / shared prefix
<ctrl+t> on an open word menu      → accept highlighted (when no shared prefix left), then arm chain
<ctrl+t> at a complete-word edge   → insert one predicted next word if confident;
                                      else open a  next-word menu if several;
                                      else file-history if on whitespace;
                                      else no-op
Ctrl+F / Ctrl+L                    → accept highlighted, then arm the same chain for word kinds
```

NORMAL mode is unchanged. Tab remains snippets.

---

## 5. How to predict the next word

Three layers, in this order. Query is a pure in-memory function on the warm cache. Disk I/O stays on the existing history-word worker.

### Layer 1 — Whole-prompt prefix (fish)

Keep the newest N prompt texts (recommend 2 000, same 20 000-prompt build cap as the word index). Normalize only for matching: collapse ASCII whitespace, casefold. Rank hits:

1. Current buffer is a prefix of a stored prompt (strongest).
2. Last k tokens of the buffer (k from 4 down to 2) appear as a contiguous sequence in a stored prompt; take the token after that span.
3. Prefer same-project (see §5.3), then recency, then frequency of that continuation.

The continuation is the remainder of **one** chosen source prompt (or the shared remainder if several sources agree on the next word). `<ctrl+t>` inserts the next identifier-like token plus the original separator (usually one space). If sources disagree on the next word, fall through to the menu in layer 2.

This layer is why retyping `Review the authentication` feels magic: it is the same prompt, one word at a time.

### Layer 2 — Bounded n-grams with conservative backoff

Build, at index time, contiguous n-grams of order 4, 3, and 2 over a **sequence tokenizer**:

- Same identifier-like definition as `prompt_word_completion.is_word_character` (`alnum`, `_`, ASCII `-`).
- **`min_length = 1`**. Keep `the`, `for`, `to`.
- Still drop digits-only and hyphen-only tokens (`_has_useful_history_content`) so SHAs and `--` flags do not pollute.
- Preserve order and repeats inside a prompt.
- Record `(count, last_used_epoch, project_key)` per `(context → next_word)`.

Query uses **stupid backoff** (Brants et al. 2007): if the 4-gram context was observed, use it; else 3; else 2. **Do not backoff to unigrams** for insertion. Unigram next-word is "insert a frequent word," which is how generic English models embarrass themselves.

Insert immediately when:

- the chosen order is ≥ 3 and there is a unique next word, or
- the chosen order is 2, the next word has ≥ 3 observations, and it accounts for ≥ ~70% of that context's mass.

Otherwise show a short ranked menu (cap ~8 rows) using the same relation/recency/frequency chips the history-word menu already taught, with the dominant reason being the matched phrase (`⇄ authentication middleware`).

Memory sketch, worst case of the current index bounds (20 000 prompts × ~40 tokens): a few megabytes of sequences plus a hash map of contexts. Trivial next to the TUI. Query is a handful of dict lookups — well under the 16 ms keystroke budget in `tui_perf.md`.

### Layer 3 — Project phrasing ("common sense")

Only if layers 1–2 produce nothing:

1. Current prompt's own earlier sentences (prompt-local *sequences*, nearest-first). Repeating a bullet list should continue from the previous bullet's phrasing.
2. Tokenized `ace.snippets` templates and xprompt bodies from the already-warm assist catalog.
3. Canonical archived prompts (`sase/repos/agents/prompts/YYYYMM/`), bounded and off-thread, same as `sase prompt search` already reads.

These are SASE-shaped English. They fire on a cold personal history without predicting `"the"` after every verb.

**Out of scope for v1:** KenLM, neural LMs, cloud completion, spell-check suggestions as next words, completing inside fenced/inline code or disabled prompt regions (match the existing structured-completion exclusions).

### 5.3 Project vs user history

`PromptEntry` has no project column. Ctrl+K already derives project identity from the prompt text via `PromptHistoryProjectCatalog` (directory key, aliases, `owner/repo` spellings, Patch names). Reuse that snapshot at index time:

- Attach a `project_key` to each sequence / n-gram posting when the source prompt names a known project or Patch.
- At query time, read the live bar's workspace tag (same helper the file-completion root uses).
- **Boost** same-project postings; do not hard-filter. A new project still inherits the operator's global phrasing.

Machine-wide history remains the corpus. "Project's prompt history" is a ranking prior.

---

## 6. UX details that make it feel excellent

**Ghost.** Set `PromptTextArea.suggestion` to the next 1–3 words of the chosen continuation, with a leading space if the cursor sits on a word character. Style is Textual's `text-area--suggestion` (already used by Command Line). Clear it on any edit that is not itself a chain accept, on cursor moves off the boundary, and when structured completion owns the cursor.

**One-word accept.** Split the remainder on the same identifier-like tokenizer. Insert ` ` + word (or just the word if the cursor is already on whitespace). Leave the cursor on the last character of the inserted word so the next `<ctrl+t>` is still at a complete-word boundary. Do not insert a trailing space; that would hand the following press to file-history unless A5 is implemented.

**Menu of alternatives.** Kind `next_word`. Rows are whole words, no shared-prefix logic. `<ctrl+t>` / Ctrl+F accepts the highlighted row and refreshes the ghost. `<ctrl+n>` / `<ctrl+p>` pick. Escape dismisses the ghost and the menu. `<ctrl+d>` can suppress that continuation (store analogously to `prompt_word_deletions.json`, keyed by `(context, next_word)`).

**Arming the chain.** After a prompt-local or history-word commit (unique `<ctrl+t>` or Ctrl+F), compute the continuation once and set the ghost. Do **not** auto-open a menu. The operator sees the guess and either taps `<ctrl+t>` or types.

**Break the chain** on any inserted character, Backspace, cursor motion off the boundary, opening a structured menu, or a next-word miss. Re-arm only from a fresh complete-word boundary.

**Do not ghost across newlines** in the TextArea (suggestion is spliced into the current line). A newline in the source remainder becomes a space in v1, or a single `\n` insert if the cursor is already at end of line and the source prompt broke there. Keep v1 on spaces.

**Undo.** Each accepted next word is one TextArea edit so a single undo peels one word, matching Copilot/Cursor partial accept.

---

## 7. Implementation sketch

Stay in Python, on the history-word warm path. Rust is not required for v1; the corpus is bounded and the TUI already owns this cache. Revisit `sase-core` only if nvim/LSP need the same index through the helper bridge.

### 7.1 Index (`sase/history/`)

New module, e.g. `prompt_next_word_index.py`, built in the same `_load_history_prompt_words` thread:

```
PromptNextWordIndex
  sequences: tuple[tuple[int, ...], ...]   # word ids per prompt, newest first
  prompt_epoch: array
  prompt_project: tuple[str, ...]          # "" if unknown
  words / folded_*                         # may share spellings with PromptWordIndex
  ngrams: dict[tuple[int, ...], list[NextWordStat]]  # orders 2–4
  prefix_texts: tuple[str, ...]            # newest 2000 full texts for fish match
```

Rebuild when the existing `PromptWordIndexToken` (shard mtimes + min_length) changes. Sequence tokenization uses `min_length=1` regardless of `word_min_length`; that setting continues to govern *current-word* completion only.

Expose `predict_next_words(text, cursor, project_key, deleted) -> NextWordPrediction` with:

- `next_words: list[RankedWord]`
- `remainder: str` (for ghost; may be longer than one word)
- `source: "prefix" | "ngram" | "prompt_local" | "template"`
- `confident: bool` (insert vs menu)

### 7.2 Widget (`sase/ace/tui/widgets/`)

- New kind `NEXT_WORD_COMPLETION_KIND = "next_word"`.
- In `_prompt_text_area_key_handling.py`, before re-dispatching `<ctrl+t>`: if a word menu is active and `shared_extension` is empty, accept then `_arm_next_word_chain()`.
- At the bottom of `_try_file_completion_tab`, when token extraction fails (whitespace) or the current word is a complete exact match: `_try_next_word_completion_tab()`.
- `_arm_next_word_chain()` sets `suggestion` from the warm index; never on the UI thread from disk.
- Override `action_cursor_right` on `PromptTextArea` so a non-empty `suggestion` does not insert. Optional later: Command Line-style accept-all at true end-of-buffer only, on an explicit chord (not v1).
- `update_suggestion` hook: recompute from the warm index on text/cursor change, debounced with the existing 90 ms soft-completion timer **or** synchronously from cache (the lookup is cheap enough to be synchronous if the cache is warm; if cold, show nothing).

Cold cache: same placeholder pattern as history words is unnecessary for next-word. If the index is not warm, skip. The first `<ctrl+t>` on a partial word already schedules the warm.

### 7.3 Config

Add under `ace.prompt_completion`:

```yaml
next_word: true                 # master switch
next_word_ghost: true           # TextArea.suggestion
next_word_templates: true       # layer 3
next_word_prefix_prompts: 2000  # fish corpus cap
```

`history_word_count: 0` continues to disable current-word history fallback. Next-word can stay on (it uses sequences, not the MRU word list). A user who wants neither sets `next_word: false` and `history_word_count: 0`.

### 7.4 Tests and docs

- Pure tests on `predict_next_words`: prefix match, n-gram backoff, no unigram insert, project boost, deletions, min_length independence, cancelled drafts included.
- Widget tests: unique word then `<ctrl+t>` inserts next; open word menu second `<ctrl+t>` accepts highlighted then chains; whitespace after a word prefers next-word over file-history when confident; empty prompt still file-history; `@` reveal unchanged; path shared prefix unchanged; right-arrow does not swallow the ghost; Ctrl+F arms the chain; undo peels one word; code fences do not chain.
- PNG goldens for: ghost after a committed history word; next-word menu with signal chips; no-ghost when silent.
- `docs/ace.md` Completion section and the INSERT keymap table; `docs/configuration.md` `ace.prompt_completion`.

---

## 8. Performance, privacy, failure modes

**Keystroke path.** `tui_perf.md` rule 11: completion is read-only, no subprocess, no unbounded locks. Next-word query must be a cache lookup. Rebuilds stay on the `prompt-history-words` worker with the same coalescing flags.

**Startup.** Do not add work before first paint. The history-word warm already runs after the prompt bar mounts (`_prompt_input_bar_lifecycle.py`). Fold the sequence index into that job.

**Wrong guesses.** Dominant failure is inserting a fluent but unintended word (`the` after `review` when the user wanted `review <path>`). Mitigations already in A7/A9: no unigram insert, confidence gate, one-word undo, `<ctrl+d>` suppress.

**Secrets.** Prompt history can contain tokens. Next-word can replay them. That is the same exposure as Ctrl+K replay and history-word completion. Do not add a new store. Deleting a prompt (`sase prompt delete`) rebuilds the index via the mtime token.

**Multiline / mid-prompt.** Ghost is current-line only. Mid-buffer complete-word boundaries *can* chain using n-grams of the left context; skip fish prefix match unless the left-of-cursor slice is a prefix of a stored prompt.

**Non-English / identifiers.** Tokenizer is Unicode alphanumeric. `GitHub` case policy from `apply_word_case` should apply to inserted next words when the user has started a prefix; for a full next-word insert with no prefix, use the canonical history spelling.

---

## 9. Alternatives considered

**Subtitle-only (extend soft completion).** Zero new paint path, but the subtitle is already the structured-token channel and sits away from the caret. Ghost at the cursor is how every successful next-word UI works.

**Always open a next-word menu after accept.** More discoverable, more noisy. Unique commits would flash a panel on every `Gith` → `GitHub`. Ghost is enough; the menu appears when the guess is ambiguous.

**Tab for next-word.** Tab is snippet tabstops and list-item indent. Do not steal it.

**Ctrl+Right / Alt+F.** Correct for fish/Copilot; wrong here because the operator is already on `<ctrl+t>`. Can be added later as aliases.

**LLM next-word.** Even a local small model is a new runtime, a privacy surface, and tens of milliseconds. History replay is both faster and more "this is how I write prompts."

**Reuse `PromptWordIndex` relation scores as next-word.** Relation answers "which vocabulary belongs in this prompt?" That is the current-word menu. Next-word needs order.

---

## 10. Suggested delivery

| Phase | Scope | Size |
| --- | --- | --- |
| P0 | Sequence index + fish prefix match + ghost + `<ctrl+t>` one-word accept at complete-word boundaries; second `<ctrl+t>` on an open word menu accepts the row; right-arrow override; A5 whitespace rule; tests | M |
| P1 | N-gram backoff (orders 4–2), confidence gate, next-word menu with ranking chips, `<ctrl+d>` suppress, project boost | M |
| P2 | Layer-3 templates (snippets / xprompts / archive), `next_word_*` config, PNG goldens, docs | S |
| Later | helper-bridge + sase-nvim; optional accept-all chord at end of buffer | S |

P0 alone is already useful: a heavy user retyping a prompt they launched last week will walk it word by word. P1 is what makes *variations* work (`Please look at the authentication …` still predicting `middleware`).

---

## 11. Recommended solution (normative)

Implement **history-continuation next-word** in the TUI prompt input as a chain on `<ctrl+t>`, TUI-only in v1.

1. **Corpus.** Ordered tokens from prompt-history shards (include cancelled), plus a 2 000-prompt fish prefix list, warmed on the existing history-word worker. Same-project boost via the Ctrl+K identity catalog. Optional later: snippet / xprompt / archive sequences.

2. **Predictor.** Fish prefix first; then contiguous 4/3/2-gram stupid backoff with **no unigram insertion**; then prompt-local sequences. Insert when unique/dominant; otherwise a small `next_word` menu; otherwise silence.

3. **Binding.**
   - First `<ctrl+t>` on a partial word: today's unique commit / shared prefix / menu.
   - Second `<ctrl+t>` on an open `prompt_word` / `history_word` menu with no remaining shared prefix: accept highlighted, arm chain.
   - Further `<ctrl+t>` at a complete-word boundary: accept one predicted word.
   - Ctrl+F / Ctrl+L on those kinds: accept and arm the same chain.
   - Structured kinds, `@` file reveal, path drill-down, Command Line full-height: unchanged.

4. **Affordance.** `TextArea.suggestion` ghost of the next 1–3 words. Override right-arrow so it moves the caret. Undo is one word.

5. **Non-goals.** General English LMs, LLM calls, stealing Tab or `→`, requiring two presses for a unique current-word match, using the bag-of-words `PromptWordIndex` as a next-word oracle.

This is the fish/Copilot partial-accept pattern, fitted onto the chord the prompt bar already uses for "give me the rest of this token," extended by one press into "give me the next token I usually write after this."
