# Next-Word Prediction for the Prompt Input (`<ctrl+t>` chaining)

Researcher: `cld` · Date: 2026-09-28 · Scope: SASE TUI prompt input (`PromptTextArea`)

## TL;DR

- **The idea is good, but only with some changes.** This user's prompt prose is very
  formulaic: 72 of 219 hand-typed prompts start with "Can you help me". A small
  context-aware n-gram model trained on the user's own typed prompts gets **22–23%
  top-1** next-word accuracy on genuinely new prompts, and **88%** on prompts that
  re-type an earlier one. The context-free ranking used today gets about 7%.
- **Blind `<ctrl+t>` insertion (the plan as written) costs keystrokes on new text.** In
  a replay of real history it gave −7.5% keystroke savings, because wrong guesses cost
  an undo. Showing the guess *before* accepting it (inline ghost text, like fish or
  Copilot's "accept next word") turns this into about +15% theoretical savings. With
  confidence gating, shown suggestions are right 55–64% of the time.
- **The premise needs a fix.** In the current code, `<ctrl+t><ctrl+t>` does **not**
  accept the first or selected word. A second `<ctrl+t>` on an open word menu just
  re-renders it and resets the highlight to row 1. The chain needs a defined start.
- **The biggest measured win is one the plan didn't ask for.** Feeding the same n-gram
  context into today's `<ctrl+t>` *current-word* completion **doubles top-1 accuracy
  at a 1-letter prefix (18% → 38%)** and lifts 2-letter prefixes from 39% to 51%.
- **"Common sense" is not worth it in v1.** A background model trained on the project's
  docs added only +0.7 points of top-1. A general-English model mostly predicts short
  function words. There is no local LLM runtime in the environment, and the latency
  and footprint of one don't fit a per-keystroke TUI path. I'd defer it to an explicit,
  separately evaluated "suggest phrase" action.
- **Recommendation:** build a sequence (n-gram) model of *human-typed* prompt prose,
  owned by `sase-core` (Rust) with a thin Python adapter. Ship in this order:
  1. `<ctrl+t>` on an open word menu accepts the highlighted row.
  2. Context-aware ranking for current-word completion.
  3. Ghost-text next-word chaining, where `<ctrl+t>` takes one ghost word and
     `ctrl+f`/`→` take all of it.
  4. Opt-in automatic ghost text at word boundaries, including multi-word phrases.

  Full details are in §7.

---

## 1. What exists today (verified in code)

### 1.1 `<ctrl+t>` dispatch

`_prompt_text_area_key_handling.py` sends INSERT-mode `ctrl+t` to
`FileCompletionTabMixin._try_file_completion_tab()` in `_file_completion_tab.py`.
Structured contexts are tried in order: placeholders, `+project`, VCS repo/ref, Jinja,
directive args, xprompt args, `@` refs, `=model` shortcuts, `%directive`, `#xprompt`.
For a plain prose token:

1. **No token under the cursor** (whitespace or empty prefix) opens
   `_try_file_history_completion()`, the recent-files/artifacts panel.
2. **Path-like token** runs filesystem completion.
3. **Otherwise** runs `_try_prompt_word_completion_tab()`. This tries prompt-local
   words first (nearest-first), then falls back to history words
   (`_try_history_word_completion_tab`, backed by the app-global `PromptWordIndex`).

A lone candidate is committed directly. A shared prefix is inserted and the menu stays
open. Acceptance keys are `ctrl+f` / `ctrl+l`. `Enter` never accepts.

### 1.2 Behavior probes

I drove the real `PromptTextArea` with the test harness
(`tests/ace/tui/widgets/_history_word_completion_helpers.HistoryCompletionTestApp`):

| Keys                                    | Result                                                                                 |
| --------------------------------------- | -------------------------------------------------------------------------------------- |
| `please rev` + `ctrl+t`                 | Menu opens: `review / revise / revert`                                                 |
| …then `ctrl+t` again (×2)               | **Text unchanged, menu still open** — the second `<ctrl+t>` does not accept             |
| `ctrl+t`, `ctrl+n`, `ctrl+t`            | Highlight goes 0 → 1 → **back to 0** (re-dispatch resets `_file_completion_index`)     |
| `please review` + `ctrl+t` (full word)  | No-op (no longer candidates; kind `file`, inactive)                                    |
| `please review ` + `ctrl+t` (after space) | Opens the **file-history** panel                                                     |

So "use `<ctrl+t><ctrl+t>` to complete the first word" is not current behavior. The two
positions where a next-word `<ctrl+t>` would fire (right after a word, or after
word+space) are respectively a no-op and the file-history panel. Both need an explicit
rule (§6.3).

### 1.3 History-word model

`src/sase/history/prompt_word_index.py` and `prompt_word_ranking.py`:

- `PromptWordIndex` is a **bag of words per prompt**. `_build_prompt_word_index_from_paths`
  dedups each prompt's words (`seen_in_prompt`) and keeps no positions. Words shorter
  than `word_min_length` (default 5) are never indexed. **Word order is discarded, so
  this index cannot answer "what comes after X Y".** A next-word feature needs a new
  sequential structure. It can share the same warm-cache lifecycle.
- Ranking is `0.50·relation + 0.30·recency + 0.20·frequency`. "Relation" is
  document-level co-occurrence lift against the rarest words in the current prompt. It
  is topical and has no notion of the preceding word.
- The index is built off-thread by `ace/tui/actions/_startup_history_words.py`. It is
  keyed by a shard `(path, mtime, size)` source token, capped at 24 shards / 20k
  prompts, and published to widgets through
  `app.history_prompt_word_index()`. A next-word model should reuse this lifecycle.

### 1.4 Existing ghost-text precedent

- **Textual 8.0.1's `TextArea` has built-in ghost text.** It has a `suggestion` reactive,
  rendered dim at the cursor in `_render_line`. `edit()` consumes it as you type
  through matching characters, and `action_cursor_right` inserts the whole suggestion.
  `PromptTextArea`'s render overrides (`_line_rendering.py`) call
  `super()._render_line`, so this works without new rendering code.
- **SASE already uses it.** `command_line/screen_navigation.py::_update_ghost` sets
  `CommandLineInput.suggestion` from `CommandLineHistory.ghost()`. That is fish-style
  history autosuggestion, shown only when the cursor is at end of line.
- INSERT-mode `ctrl+f` is bound to `cursor_right` (`vim_text_area.py:58`). With a
  `suggestion` set, **`ctrl+f`/`→` accept the whole ghost with no new code.** That is
  exactly fish's split: `ctrl+f`/`→` take the whole suggestion and `alt+f` takes one
  word. `<ctrl+t>` can play fish's `alt+f` role.
- The existing "soft completion" (`_prompt_soft_completion.py`) is different. It shows
  a hint in the **border subtitle** (`[^L] accept …`) and covers only structured tokens
  (xprompts, directives, paths), not prose.

### 1.5 Prompt-history store facts

- `PromptEntry` has `text`, `timestamp`, `last_used`, `cancelled` and nothing else.
  **There is no project field and no origin field.**
- Exact duplicates are merged (`last_used` bumped). Near-duplicates are stored
  separately.
- **Machine-generated prompts are recorded alongside typed ones.** For example,
  `agent/launch_cwd_bead_work.py:162` calls `add_or_update_prompt(..., allow_short=True)`
  for epic phase launches.
- History is **per machine** (`~/.sase/prompt_history/YYMM.json`).

---

## 2. What's actually in the history (apollo, Sept 2026)

I measured this on the local store: one shard, `2609.json`, 670 entries from 09-01 to
09-28. Only aggregates are reported here, no prompt contents.

| Measure                                                                                                                             | Value                                                                        |
| ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Entries                                                                                                                             | 670                                                                          |
| **Machine-generated** (epic phase launches `%id(...) %model:@… #bd/work_phase_bead:…`, swarm/lead prompts, `%wait(...)` blocks)     | **449 (67%)**                                                                |
| Human-typed                                                                                                                         | 221 (≈ 8/day)                                                                |
| Human prose tokens, after stripping leading `#gh:` / `%directive` / `+project` tokens                                                | 19.4k (median 53 per prompt)                                                 |
| Most common opener                                                                                                                  | "Can you help me …" = **72 / 219**; "Can you now help …" = 11                |
| Near-duplicate human prompts (≥ 60% 5-gram overlap with an earlier prompt)                                                          | 36 (16%); 21 are ≥ 90%                                                       |
| Prompts carrying a VCS project tag (`#gh:…`)                                                                                        | ~100%, so **project can be derived from text**                               |

Implications:

1. The corpus must be restricted to **human-typed prose**. Otherwise two-thirds of it
   is directive boilerplate. It also slightly pollutes today's history-word menu.
2. "Project history" isn't stored, but it can be derived from the leading VCS tag. The
   Ctrl+K filter already extracts these facts via `prompt_history_project_filter`.
3. Corpora are small: about 20k tokens per month per machine. That means low-order
   n-grams with backoff, not anything trained.

---

## 3. Offline evaluation (replayed on real history)

### 3.1 Method

- **Prequential replay.** Prompts are sorted by timestamp. The model is warmed on the
  first 40% of human prompts. Then each later prompt is scored word by word using only
  earlier prompts plus its own already-typed prefix, and is added to the model
  afterwards. This mirrors real use.
- **Unit.** A whitespace token (the surface form, including punctuation), because that
  is what `<ctrl+t>` would insert. Context keys are normalized (casefold, strip
  surrounding punctuation). A prediction counts as correct only on an exact surface
  match. "Loose" matching adds only about 1 point, so surface tokens are fine.
- **Keystroke savings rate (KSR).** Typing a word costs `len+1` keys; accepting costs 1.
  - *Ghost mode:* you see the guess first and ignore it when wrong.
  - *Blind mode:* the plan as written. You press `<ctrl+t>` whenever a prediction
    exists, and a wrong guess costs about 2 keys (the press plus an undo).
  - KSR is an **upper bound on benefit.** It ignores the attention cost of reading
    suggestions (§4, Quinn & Zhai).
- **Subsets.**
  - *All* human prompts.
  - *Novel* prompts: < 30% 5-gram overlap with any earlier prompt, and ≤ 400 tokens
    (drops pastes). This is the honest "am I writing something new" case.
  - *Near-dup* prompts: ≥ 60% overlap.
- **Models.**
  - Context-free unigram (frequency+recency, like today's ranking without relation).
  - Bigram through 5-gram with stupid backoff (α = 0.4, Brants et al. 2007).
  - 4-gram plus recency decay (14-day half-life).
  - 4-gram plus an in-prompt cache.
  - Fish-style longest-match: longest matching context of up to 8 words, most recent
    continuation wins.
  - 4-gram also trained on machine prompts.
  - 4-gram plus a background model built from the repo's `docs/**/*.md` and
    `sase/memory` (408k tokens).
  - Docs-only.

The scripts were throwaway (`/tmp/cld_nwp/*.py`, pure Python). §8 has enough detail to
rebuild them.

### 3.2 Results: next word (no prefix typed)

**All human prompts** (n = 9,627 predicted positions):

| Model                               | top-1     | top-3 | coverage | mean correct run | KSR ghost | KSR blind  |
| ----------------------------------- | --------- | ----- | -------- | ---------------- | --------- | ---------- |
| Unigram, context-free               | 6.7%      | 11.1% | 100%     | 1.00             | 3.4%      | −28.2%     |
| Bigram                              | 24.7%     | 36.2% | 91.1%    | 1.52             | 15.3%     | −7.1%      |
| Trigram                             | 37.2%     | 47.1% | 91.1%    | 2.80             | 27.2%     | +9.0%      |
| 4-gram                              | 41.9%     | 49.4% | 91.1%    | 4.00             | 31.6%     | +14.9%     |
| 5-gram                              | 42.8%     | 49.6% | 91.1%    | 4.33             | 32.4%     | +16.1%     |
| **4-gram + recency**                | **43.1%** | 49.8% | 91.1%    | 4.25             | 32.7%     | +16.4%     |
| 4-gram + in-prompt cache            | 42.8%     | 50.5% | 92.6%    | 4.00             | 32.1%     | +15.3%     |
| Longest-match (fish-style)          | 41.9%     | 48.6% | 91.1%    | **5.47**         | 32.9%     | +16.2%     |
| 4-gram + machine prompts in training | 41.9%    | 49.2% | 91.3%    | 3.93             | 31.5%     | +14.8%     |
| 4-gram + docs background            | 42.4%     | 50.2% | 97.1%    | 3.89             | 31.8%     | +13.3%     |
| Docs-only (no prompt history)       | 8.4%      | 14.6% | 94.2%    | 1.07             | 4.0%      | −25.0%     |

**Novel prompts only** (n = 6,171). This is the number to plan around:

| Model                     | top-1     | top-3 | coverage | mean run | KSR ghost | KSR blind |
| ------------------------- | --------- | ----- | -------- | -------- | --------- | --------- |
| Unigram, context-free     | 6.9%      | 10.9% | 100%     | 1.00     | 3.5%      | −28.0%    |
| Bigram                    | 18.9%     | 27.4% | 87.5%    | 1.47     | 10.7%     | −12.5%    |
| Trigram                   | 21.4%     | 30.4% | 87.5%    | 1.85     | 14.0%     | −8.4%     |
| 4-gram                    | 22.3%     | 30.6% | 87.5%    | 1.91     | 14.6%     | −7.5%     |
| **4-gram + recency**      | **23.0%** | 30.9% | 87.5%    | 1.92     | **15.1%** | −6.7%     |
| Longest-match             | 20.0%     | 28.9% | 87.5%    | 2.08     | 14.4%     | −8.4%     |
| 4-gram + docs background  | 23.0%     | 31.9% | 96.1%    | 1.87     | 14.9%     | −9.8%     |

**Near-duplicate prompts only** (n = 2,454), 4-gram: **87.8% top-1**, a mean correct run
of **10.9 words**, and 85% of words inside runs of 3 or more. KSR is 71% (ghost) and 67%
(blind). This is where "just keep hitting `<ctrl+t>`" really shines.

**Confidence gating** (4-gram, *novel* prompts). The gate shows a suggestion only when
the model is confident. `p` is the backoff score of the top candidate; `order` is the
matched context length.

| Gate                        | shown | precision | KSR blind (gated) |
| --------------------------- | ----- | --------- | ----------------- |
| Always                      | 87.5% | 25.5%     | −7.5%             |
| order ≥ 2                   | 46.7% | 34.5%     | +0.9%             |
| order ≥ 3                   | 22.7% | 51.0%     | +4.4%             |
| p ≥ 0.5                     | 19.7% | 57.6%     | +5.1%             |
| order ≥ 2 & p ≥ 0.7         | 15.6% | **63.5%** | +5.2%             |

On *all* prompts the same gates give 77–88% precision at 36–44% coverage.

**Where the value comes from.** On novel prompts, 57% of correct predictions are words
of 3 characters or fewer ("to", "the", "a"). Those give only 36% of the characters
saved. Most of the payoff comes from phrases ("Can you help me add a new …") and from
re-typed prompts.

**Learning curve** (novel prompts, fixed test set). With 1.2k training tokens, top-1 is
20.7%. With 13.5k tokens it is 23.9%. More history (multiple machines, several months)
buys a few points, not a step change.

### 3.3 Results: context-aware *current-word* completion (prefix typed)

The target is every word of ≥ 5 characters in novel prompts (the words today's
`<ctrl+t>` word menus serve), n = 2,053. The baseline is **the repo's real code path**.
It tries `build_prompt_word_completion_result` (prompt-local) first, then
`build_indexed_history_word_completion_result(smart=True)` over a `PromptWordIndex`
rebuilt from all earlier history entries. The "+ context" variant puts n-gram
candidates that match the typed prefix first, then the baseline order.

| Typed prefix | Today: top-1 | Today: top-3 | + n-gram context: top-1 | + context: top-3 |
| ------------ | ------------ | ------------ | ----------------------- | ---------------- |
| 1 char       | 18.2%        | 31.8%        | **37.7%**               | **49.1%**        |
| 2 chars      | 39.2%        | 54.0%        | **51.1%**               | **62.6%**        |
| 3 chars      | 55.0%        | 70.9%        | **62.3%**               | **74.4%**        |

This is the highest-return change in the whole space. It makes "the first word" you
complete with `<ctrl+t>` right far more often, with **no new UX**. The chain also
starts from a correct word.

### 3.4 Performance

- **Query:** 6–8 µs in a lean interned-id Python table; 36–66 µs p50 in the research
  code. Rust would be well under 1 µs. There is no need for debounce or a worker on
  the query path.
- **Build (CPython dicts):**
  - One month of human prose (19.4k tokens): **7.7 MB**, well under 0.5 s.
  - 408k tokens (the docs corpus): **2.6 s and 189 MB.**
  - Today's index caps at 24 shards. For this user that could mean about 470k
    human-prose tokens, or roughly **200 MB in CPython**. That is too much for the TUI
    process.
  - A compact Rust table (about 16 B per n-gram entry) or a suffix array (8 B per
    token) is 10–25× smaller and about 50× faster to build.

---

## 4. Critique of the plan

### What's right

- **The signal is real and strong for this user.** Going from context-free ranking to a
  4-gram raises top-1 from 7% to 22–43%, depending on how novel the prompt is. Prompts
  to agents reuse a lot of stock phrasing ("Can you help me", "I want to", "Is this a
  good idea?", "Make any adjustments to the requirements…").
- **"Keep hitting one key" is a proven interaction.** fish accepts one autosuggestion
  word with `alt+→`/`alt+f`. VS Code/Copilot has
  `editor.action.inlineSuggest.acceptNextWord` on `ctrl+→`. Your `<ctrl+t>` chain is
  the same idea.
- **It can be fast, private and local.** No network or model download is needed.

### What's wrong or missing

1. **Blind insertion is the core flaw.** If `<ctrl+t>` inserts a word you haven't seen,
   every miss costs an undo. On novel text it's a net loss (−7.5% KSR; −28% for a naive
   context-free guesser). Precision on novel text is about 25% ungated, so you would be
   undoing three times out of four. **You must see the prediction before you commit
   it.** Inline ghost text does this for free (Textual `suggestion`).
2. **The trigger is broken today** (§1.2). `<ctrl+t><ctrl+t>` doesn't accept; the
   second press resets the highlight. The chain has no well-defined start until
   `<ctrl+t>` on an open word menu *accepts* the highlighted row.
3. **Chaining only after a completion is too narrow.** Most words are typed, not
   completed, so the chain would rarely start. The best opportunities are prompt
   openers and stock phrases, which usually begin right after a space you typed. A
   confident ghost at word boundaries, offered as a mode, covers them.
4. **Pressing `<ctrl+t>` at the natural spots already does something.** Right after a
   word it is a no-op or a "longer word" menu. After a space it opens the file-history
   panel. The rule has to be simple and visible: **if ghost text is showing,
   `<ctrl+t>` takes its next word; otherwise `<ctrl+t>` behaves as today.**
5. **"Project's prompt history" doesn't exist as data.** Entries have no project field,
   and history is per machine. With about 20k tokens per month, a hard per-project
   filter would starve the model. Use project as a **boost** (weight up prompts with the
   same VCS tag), not a filter.
6. **67% of history is machine-generated.** Those prompts must be excluded from the
   sequence model. My prose extraction stripped most directive tokens, so they didn't
   hurt accuracy here, but a naive tokenizer would learn `%model:@medium` chains.
   Record an origin at write time instead of guessing.
7. **"Common sense" doesn't earn its cost here.**
   - Project docs as a backoff: +0.7 top-1 on novel text, but higher coverage *lowers*
     precision (KSR blind −9.8% vs −7.5%). Docs prose ("The panel shows …") is a
     different register from prompts ("Can you help me …").
   - General English n-grams mostly add function words, which are worth little.
   - Gboard's production neural LM reached **16.4% top-1 on general chat** (up from
     13.0% for an n-gram; Hard et al. 2018). The personal 4-gram already beats that
     here because the corpus is so formulaic.
   - A local LLM needs a runtime (none installed: no torch, onnxruntime, llama.cpp or
     ollama), 100 MB–1 GB of RAM, and 10–100 ms per token on CPU. Gmail Smart Compose
     had to fall back to an RNN to hit a 60 ms p90 latency.
   - Where an LLM *would* help is multi-word phrase suggestion on novel text. Treat that
     as a separate, explicit feature and gate it on the same replay harness.
8. **The attention cost is real.** Quinn & Zhai (CHI '16) found that more assertive
   suggestions cut keystrokes and were preferred, but *slowed* average entry time.
   Gating to high confidence (≥ 55–65% precision) is how Smart Compose and Gboard
   manage this. Also, Arnold et al. (IUI '20) found predictive text makes writing
   shorter and more predictable. For agent prompts that is mostly harmless, but it's a
   reason not to make suggestions pushy.
9. **Near-duplicate re-typing should be handled as phrase recall, not word-by-word.**
   At 88% top-1 with 11-word runs, showing the *whole* likely continuation (fish-style)
   and letting `ctrl+f` take it all beats eleven `<ctrl+t>` presses. Ctrl+K history
   recall also exists for whole-prompt reuse.

### Would I take a different approach?

I'd keep the n-gram core and the `<ctrl+t>` key, and change the order and the surface:

- First, fix `<ctrl+t>`-accepts-highlighted.
- Next, add context-aware ranking. This is the biggest measured win, needs no new UX,
  and is low risk.
- Then add ghost-text chaining.
- Then add opt-in automatic ghost text at word boundaries.
- Skip the LLM.

---

## 5. Adjusted requirements (changes from the original ask, called out)

| #   | Original                                             | **Adjusted**                                                                                                                                                                                                                                                                             | Why                                                                                                                                             |
| --- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | `<ctrl+t>` inserts the guessed next word             | **Show the guess as inline ghost text first.** `<ctrl+t>` accepts *one* ghost word; `ctrl+f` / `→` accept the whole ghost (Textual default, fish parity).                                                                                                                                  | Blind insertion loses keystrokes on novel text (§3.2).                                                                                          |
| R2  | "`<ctrl+t><ctrl+t>` completes the first/selected word" | **New behavior:** `<ctrl+t>` on an open prompt-word or history-word menu *accepts the highlighted row*. This also fixes the reset-to-row-1 quirk.                                                                                                                                         | Today the second press doesn't accept (§1.2).                                                                                                   |
| R3  | Chain only after a completion                        | The chain starts after **any** word-completion accept (lone `<ctrl+t>`, `ctrl+f`/`ctrl+l`, R2). **Optional mode:** a confident ghost also appears at word boundaries (after typing a space).                                                                                              | Most words are typed; openers and stock phrases start after a space.                                                                            |
| R4  | Always guess                                         | **Confidence-gated.** Show only if the top candidate clears a threshold (start at `order ≥ 2 & p ≥ 0.6`, target ≥ 60% precision). Extend a multi-word ghost only while each step stays ≥ threshold, up to 5 words.                                                                        | Quinn & Zhai attention cost; §3.2 gating curve.                                                                                                 |
| R5  | "User/project prompt history"                        | Train on **human-typed prompts only**, using a new `origin` field (`typed` / `generated`) on `PromptEntry` set at write sites. Cancelled prompts count as typed. Project is a **boost** from the leading VCS tag, not a filter.                                                            | 67% of entries are generated; the per-project corpus is too small to filter.                                                                   |
| R6  | —                                                    | **New scope:** feed n-gram context into current-word `<ctrl+t>` ranking (prompt-local and history words) as a "sequence" signal.                                                                                                                                                        | 18% → 38% top-1 at a 1-char prefix (§3.3).                                                                                                      |
| R7  | "Maybe common sense"                                 | **Out of v1.** Revisit an LLM only as an explicit "suggest phrase" action, after it beats the n-gram on the replay harness.                                                                                                                                                               | +0.7 points from docs; no runtime; latency.                                                                                                     |
| R8  | "Fast"                                               | **Budget:** < 1 ms per query on the UI thread; build off-thread; **incremental update on submit** (no full rebuild).                                                                                                                                                                     | Measured µs queries; builds of hundreds of ms or more.                                                                                          |
| R9  | —                                                    | Only show ghost text in INSERT mode, with no menu open, no snippet session, not in feedback mode, and not inside fenced/inline code, frontmatter, directive or xprompt-arg contexts. The cursor must be at end of line or before whitespace. Same blocking rules as `_soft_completion_blocked`. | Avoid fighting structured completion; Textual ghost text doesn't wrap.                                                                          |

---

## 6. Design details

### 6.1 Model

- **Corpus.** Human-typed prompt prose. Strip leading structural tokens (`#gh:…`,
  `%…`, `+project`, `#xprompt`), and skip fenced code and pasted blocks (for example,
  lines over 400 tokens or stack-trace-looking lines). Treat each logical paragraph
  line as a sequence with a `<s>` start marker so openers are learned.
- **Tokens.** Whitespace tokens with their surface form (punctuation and backticks
  kept). Context keys are normalized (casefold, strip surrounding punctuation), so
  "help me," and "help me" share context but insertion keeps the typed form.
- **Scoring.**
  - Orders 1–4 (5 adds only +0.9 points), stupid backoff α = 0.4.
  - Recency: `count × (0.5 + 0.5·2^(−age/14d))` (+0.7 points).
  - Project boost: ×(1+β) for prompts with the same VCS tag. Tune β with the harness.
  - Small in-prompt cache (+0.5 points top-3).
- **Phrase ghost.** Extend greedily while each step clears the gate. When the matched
  context is ≥ 4 tokens (the near-dup case), use the longest-match continuation from
  the most recent matching prompt.
- **Suppression.** `Esc` dismisses the ghost for that position. Optionally, a
  deletions store like `prompt_word_deletions.json` could hold "never suggest X after
  Y" pairs; I'd defer that.
- **Casing and spacing.**
  - Accepting right after a word inserts `" word"`; after a space it inserts `"word"`.
  - A sentence start (after `.`/`?`/`!` or at line start) prefers capitalized surface
    forms.

### 6.2 Where the code lives

- **Model build and query: `sase-core` (Rust) behind `sase_core_rs`.** Two reasons:
  - The project's boundary rule: an editor/LSP or web frontend offering the same
    prompt completion should match the TUI.
  - The memory and build-time numbers in §3.4.

  Suggested API:
  - `build_prompt_sequence_model(entries) -> handle`
  - `model.add(entry)`
  - `model.predict(context_tokens, prefix, project, k) -> [(surface, score, order)]`
  - `model.continuation(context_tokens, max_words, threshold)`

  Note: today's history-word index is pure Python, which is a precedent for a Python
  v1. If you prototype in Python, cap the corpus (for example, the latest 150k tokens)
  and keep the API shape identical so the port is mechanical. Remember the
  `sase-core-revision.txt` CI pin.
- **Warm cache.** Extend `_startup_history_words.py` to build the sequence model
  alongside `PromptWordIndex`, under the same shard source token. Add an `add()` call
  on prompt submit so the chain learns within the session.
- **Origin tagging.** Add `origin` in `prompt_store.py` (`_prompt_to_json` /
  `prompt_entry_from_json`, defaulting to `typed`). Pass `origin="generated"` from
  `agent/launch_cwd_bead_work.py` and any other programmatic launcher. For existing
  entries, backfill with the heuristic used here (`#bd/work_phase_bead`, `%id(` blocks,
  swarm/lead templates).
- **TUI.** A new `_prompt_next_word.py` mixin on `PromptTextArea`:
  - `_refresh_next_word_ghost()` is called after completion accepts, after a
    ghost-word accept, and (in `auto` mode) after a space typed after a word. It sets
    `self.suggestion`.
  - A `ctrl+t` pre-branch in `_prompt_text_area_key_handling.py` checks, in order:
    - a visible ghost → accept its first word and refresh;
    - an open prompt-word or history-word menu → accept the highlighted row (R2), then
      refresh the ghost;
    - otherwise → the existing dispatch.
  - Any non-type-through edit or cursor move clears the ghost. Textual already clears
    it on non-matching edits; mirror `CommandLineInput._refresh_ghost_for_cursor_move`.
- **Ranking (R6).** Add a fourth "sequence" signal to `rank_history_words` and to the
  prompt-local ordering: n-gram probability given the preceding words, filtered by the
  typed prefix. When `order ≥ 2`, let it dominate. The row chip could read
  `→ after "help me"`.

### 6.3 Keys and config

- `<ctrl+t>`: when ghost text is visible, take one ghost word. On an open word menu,
  accept the highlighted row. Otherwise, today's behavior. The file-history panel
  stays reachable whenever no ghost is visible (for example, `Esc`-dismiss, then
  `<ctrl+t>`).
- `ctrl+f` / `→`: accept the whole ghost (built in).
- New settings under `ace.prompt_completion`:
  - `next_word: off | chain | auto` (default `chain`; `auto` adds word-boundary ghosts)
  - `next_word_min_confidence: 0.6`
  - `next_word_max_words: 5`
  - `next_word_project_boost: 1.0`
- Update `src/sase/default_config.yml` (per the gotchas memory), the Completion section
  of `docs/ace.md`, and `docs/configuration.md`. Consider a feature flag for the `auto`
  mode, per the project's flag conventions.

### 6.4 Measurement

- Turn the replay harness into a dev tool (`sase prompt-history eval-next-word` or a
  `tools/` script). Use it to tune α, the recency half-life, the project boost and the
  gate on each user's real history.
- Keep local-only counters (ghost shown, accepted words, chain length, dismissals) so
  thresholds can be tuned from real usage. Target ≥ 50% accept rate for shown ghosts.
- Tests: pilot tests modeled on `tests/ace/tui/widgets/test_history_word_completion_*.py`
  covering:
  - ghost shown and hidden under each blocking condition;
  - `<ctrl+t>` word-by-word acceptance and spacing;
  - `ctrl+f` whole-ghost accept;
  - R2 accept-highlighted;
  - no regression of file-history at an empty prefix without a ghost.

### 6.5 Risks

- Textual draws `suggestion` inline without re-wrapping. A long ghost near the right
  edge of a soft-wrapped line gets clipped. Keep ghosts short and only at end of line
  or before whitespace.
- Interaction with the xprompt arg hints and the soft-completion subtitle: ghost text
  must yield to both.
- The history is per machine. A user who types mostly on athena or the Mac gets a
  model trained on that machine's history.

---

## 7. Recommended solution

1. **P0 (tiny, independent):** `<ctrl+t>` on an open prompt-word or history-word menu
   accepts the highlighted row. This fixes the premise and the reset-to-top quirk.
2. **P1 (biggest measured win):** a *prompt sequence model* in `sase-core`:
   - human-typed prose only (new `origin` field);
   - 4-gram, stupid backoff, recency decay, project-tag boost;
   - built off-thread in the existing history warm cache, with incremental add on
     submit.

   Use it right away to **rank current-word `<ctrl+t>` completions by preceding
   context**: 18% → 38% top-1 at 1 char, 39% → 51% at 2 chars.
3. **P2 (your feature, corrected):** after any word-completion accept, show a
   **confidence-gated ghost** of the next word, or of the next few words while
   confidence holds. `<ctrl+t>` accepts one word and re-predicts; `ctrl+f`/`→` accept
   the whole ghost. It's fish's `alt+f` / `ctrl+f` split, built on Textual's
   `TextArea.suggestion` the way the Command Line panel already uses it.
4. **P3 (opt-in):** `next_word: auto` shows the ghost at word boundaries when
   confidence is high. This is where openers and re-typed prompts pay off (88% top-1,
   11-word runs on near-duplicates).
5. **Not now:** docs, general-English, or LLM "common sense." Reconsider an LLM only as
   an explicit phrase-suggestion action, and only once it beats the n-gram on the
   replay harness.

Expected benefit on novel prose is honest but modest: about 15% theoretical keystroke
savings, with gated suggestions right about 60% of the time. On formulaic and re-typed
prompts, which are a large share of this user's writing, it is large: 30–70%. The
context-aware ranking in P1 improves every `<ctrl+t>` word completion whether or not
you ever chain.

---

## 8. Appendix: reproducing the evaluation

- **Corpus loader.** Read `~/.sase/prompt_history/*.json`, sort by `timestamp`.
  - Mark as generated any prompt containing `#bd/work_phase_bead`, `#bd/…` together
    with `%id(`, starting with `%wait(`, or matching the swarm/lead templates.
  - Prose tokens are each line's whitespace tokens after popping leading tokens that
    match `^(%[\w-]+[:(]?.*|#(gh|git|bd|!)?[\w/-]*[:(].*|#[\w/-]+|\+[\w-]+)$`.
  - Keep prompts with ≥ 3 tokens.
- **Normalization.** `tok.casefold().strip("\"'`()[]{}<>.,;:!?*")`.
- **n-gram.** For each position `i` and each order `k` in `0..3`, count
  `ctx = norm(seq[i-k:i]) → surface seq[i]`, with `<s>` prepended. Predict with
  stupid backoff: at each order from high to low, score `α^(max−k) · c(ctx,w)/c(ctx)`
  and keep each word's maximum.
- **Novelty.** 5-gram overlap between a prompt's normalized 5-grams and the union of
  all earlier prompts' 5-grams.
- **Prefix experiment.** Uses the repo's own
  `build_prompt_word_completion_result` / `build_indexed_history_word_completion_result`
  with a `PromptWordIndex` built via
  `build_prompt_word_index(shard_paths=[…], load_shard_func=…)` over all earlier
  entries.

## Sources

- Hard et al., *Federated Learning for Mobile Keyboard Prediction* (2018): Gboard
  top-1 recall 13.0% (n-gram) → 16.4% (CIFG). <https://arxiv.org/pdf/1811.03604>
- Quinn & Zhai, *A Cost-Benefit Study of Text Entry Suggestion Interaction* (CHI '16).
  <https://dl.acm.org/doi/10.1145/2858036.2858305> ·
  <https://research.google/pubs/a-costbenefit-study-of-text-entry-suggestion-interaction/>
- Chen et al., *Gmail Smart Compose: Real-Time Assisted Writing* (KDD '19): 60 ms p90
  latency, confidence-thresholded triggering. <https://ar5iv.labs.arxiv.org/html/1906.00080>
- Arnold, Gajos & Kalai, *On Suggesting Phrases vs. Predicting Words for Mobile Text
  Composition* (UIST '16). <https://dl.acm.org/doi/10.1145/2984511.2984584>
- Arnold, Chauncey & Gajos, *Predictive Text Encourages Predictable Writing* (IUI '20).
  <https://www.eecs.harvard.edu/~kgajos/papers/2020/arnold20predictive.pdf>
- Brants et al., *Large Language Models in Machine Translation* (EMNLP-CoNLL 2007),
  stupid backoff. <https://aclanthology.org/D07-1090.pdf>
- fish shell autosuggestions (`alt+→`/`alt+f` accept one word; `→`/`ctrl+f` accept
  all). <https://fishshell.com/docs/current/interactive.html>
- VS Code inline suggestions, `editor.action.inlineSuggest.acceptNextWord`
  (`ctrl+→`). <https://code.visualstudio.com/docs/editing/ai-powered-suggestions>
- Textual 8.0.1 `TextArea.suggestion` (verified in the installed source,
  `textual/widgets/_text_area.py`).
