# Next-word prediction for the prompt input widget — research (`mus`)

## TL;DR

Next-word prediction off prompt history is feasible and fits the existing
completion architecture well, but the plan as stated — chained `<ctrl+t>`
presses that alternate between "complete current word" and "guess next word" —
has a real mode-confusion problem and should be adjusted. Recommend: keep
`<ctrl+t>` purely for current-word completion (as today), and put next-word
prediction on a **separate affordance** (ghost-text suggestion accepted with
`<ctrl+l>`/`<ctrl+f>`, or a dedicated `<ctrl+g>w`-style binding), backed by a
**follow-word (bigram) index** built from the same prompt-history shards that
already feed history-word completion. Skip "common sense" (LLM) prediction for
v1: it breaks the latency budget and the offline guarantee, and history alone
covers the highest-value cases (repeated workflows, names, paths, flags).

## 1. What exists today (verified in-tree)

### 1.1 `<ctrl+t>` dispatch (`_prompt_text_area_key_handling.py:390`, `_file_completion_tab.py`)

- `<ctrl+t>` in INSERT mode calls `_try_file_completion_tab()`, an
  exhaustive, priority-ordered dispatch: placeholder → VCS project/repo/ref →
  jinja → directive clause → xprompt args → artifact refs → model shortcuts →
  directive/xprompt/file tokens → **prompt-local word completion** →
  **history-word completion** (the final fallback).
- Single-word completion semantics are already "press repeatedly": a lone
  match inserts directly; a shared prefix (`shared_extension`) is inserted and
  the menu re-narrows; otherwise a menu opens with the first row selected and
  `<ctrl+f>`/`<ctrl+l>` accepts it.
- There is **no second-press-means-something-else state machine** anywhere in
  this path. Every `<ctrl+t>` re-dispatches from the cursor context.

### 1.2 History-word completion (the closest existing feature)

- `src/sase/history/prompt_word_index.py`: immutable word corpus over the
  newest 24 shards / 20k prompts, with prefix lookup via sorted casefold keys,
  document frequency, and last-used epochs. Shard-tokenized results are cached
  (LRU-32).
- `src/sase/history/prompt_word_ranking.py`: relation (co-occurrence lift,
  weight 0.50) + recency (0.30) + frequency (0.20) composite scoring, with a
  memoized per-context ranking context. Tuned for **prefix completion of the
  current word**, not for predicting the following word.
- `src/sase/ace/tui/widgets/history_word_completion.py`: menu-row building
  with word-range-at-cursor replacement semantics (only the typed prefix is
  replaced; right-hand suffix preserved).
- Config (`src/sase/default_config.yml:514`): `history_word_count: 10000`,
  `word_min_length: 5`, `word_ranking: smart`. Loaded async — there is a
  "loading…" placeholder path and a cold-cache path, i.e. the codebase already
  accepts that history-backed completion is not instant at startup.
- Soft (ghost) completion exists separately (`_prompt_soft_completion.py`),
  accepted with `<ctrl+l>`.

### 1.3 No next-word / bigram infrastructure

A search for bigram/n-gram/Markov/next-word concepts in `src/sase/` finds only
unrelated vim-motion matches. Follow-word statistics would be greenfield, but
they can reuse the shard iteration, tokenization regex (`_PROMPT_WORD_RE`),
timestamp parsing, and caching patterns from `prompt_word_index.py` almost
directly. Note the `word_min_length: 5` filter: a next-word model must index
**short words too** (`to`, `the`, `a` are exactly what next-word prediction is
for), so it needs its own token stream, not the filtered word list.

### 1.4 Boundary constraints

- Per `docs/rust_backend.md` / AGENTS.md §1.3: shared backend behavior belongs
  in `sase_core` (linked `sase-core` repo) with no Python fallback. A
  follow-word index over prompt history is arguably backend/domain logic (any
  frontend would want the same predictions), so the index-building half likely
  belongs in Rust with a thin Python adapter, while key handling, ghost
  rendering, and menu rows stay in this repo. Budget for the cross-repo step
  (wire/API + `sase-core-revision.txt` pin move).
- Prompt history lives in sharded JSON on disk with a lock file; any new index
  must respect the same locking and the existing shard-limit conventions.

## 2. Critique of the plan as stated

### 2.1 The `<ctrl+t><ctrl+t>` → "complete word" then `<ctrl+t>` → "next word" chaining is the weakest part

1. **It collides with existing repeat-press semantics.** Today, pressing
   `<ctrl+t>` twice with an open menu / shared prefix means "narrow further /
   move through candidates". Reassigning the second or third press to "insert
   space + guessed next word" makes one key do two unrelated jobs depending on
   invisible state (was the previous completion "finished"?). Users will
   trigger next-word insertion accidentally when they merely wanted to cycle
   candidates, and vice versa.
2. **Accept-then-predict conflates two decisions.** Accepting candidate #1 and
   accepting a guessed next word are different bets with different accuracies.
   Bundling them into one keypress removes the user's chance to reject the
   first word before seeing the second. A wrong first-word guess followed by a
   space + wrong second word costs more keystrips to undo than it saves.
3. **Discoverability is nil.** Nothing on screen tells the user that "one more
   `<ctrl+t>` will now guess the next word". Ghost text (fish-style) solves
   this for free: the prediction is visible before you accept it.
4. **`<ctrl+t>` is also `toggle_full_height`** in some pane context
   (`default_config.yml:537`) — verify no binding conflict for the chosen mode
   before adding press-count state.

### 2.2 Is next-word prediction a good idea at all? Yes, with scoped expectations

- **Where it wins:** operators repeat themselves constantly (`sase bead …`,
  `sase memory read …`, project names, agent names, flag sequences). A
  follow-word model trained on personal + project history will nail these, and
  repeated-`<key>` acceptance is genuinely faster than retyping or menu
  navigation for multi-word tails.
- **Where it loses:** novel prompts (the interesting ones) get no help; the
  first few weeks of history (cold start) give thin statistics; short
  function-word transitions (`of the`, `to be`) are high-frequency but
  low-value and can feel like clutter if shown aggressively.
- **The "common sense" half of the request should be cut from v1.**
  General-knowledge next-word guessing means either (a) shipping a static
  English bigram table (megabytes for mediocre benefit, and it will fight the
  history model for the top slot), or (b) calling an LLM per keystroke
  (latency, cost, offline breakage — this is a TUI that works over SSH on
  remote machines). History statistics plus the existing prefix completion
  already cover the valuable cases. Revisit only with measured acceptance-rate
  data showing a gap that history can't fill.

### 2.3 Latency reality check

"Fast" here means **<10 ms synchronous lookup** on the keypress path, with
index build/rebuild off the UI thread (worker + stale-while-revalidate, same
as the existing cold-cache placeholder pattern). A bigram map
`word → top-k followers with counts` over ≤20k prompts is tens of thousands of
entries — trivially small enough to hold in memory and query synchronously.
The expensive part is the initial shard scan, which the existing index code
already pays; a follow-word pass can piggyback on the same tokenized-shard
cache. Do NOT do disk I/O or shard parsing inside the `<ctrl+t>` handler.

## 3. Options considered

| # | Approach | Pros | Cons |
|---|----------|------|------|
| A | **Follow-word (bigram) index over prompt history**, surfaced as ghost text + accept key | Fast; offline; personal; reuses shard/tokenize/cache patterns; visible-before-accept | Cold start; no help for novel text |
| B | Same model, but chained onto `<ctrl+t>` repeat presses (the literal proposal) | No new binding to learn | Mode confusion (§2.1); invisible predictions; conflicts with menu-narrowing |
| C | Full-phrase history recall (like shell `Ctrl+R` / existing `ctrl+k` history browser, but inline) | Great for exact repeats | All-or-nothing; doesn't compose novel + familiar halves |
| D | Static English bigram table ("common sense") | Helps cold start slightly | Size; mediocrity; ranking fights with history; maintenance burden |
| E | LLM per-keystroke suggestion | Best novel-text guesses | Latency/cost/offline/privacy; wildly disproportionate for v1 |

A + C complement each other (C already ~exists via `ctrl+k`); D and E are
correctly deferred.

## 4. Requirement adjustments (proposed)

1. **Separate affordance, not `<ctrl+t>` chaining.** Next-word guesses appear
   as ghost text after the cursor (fish-style) and are accepted with the
   existing soft-completion accept key (`<ctrl+l>`, with `<ctrl+f>` as alias —
   both already mean "accept" in this widget), word-by-word. `<ctrl+t>` keeps
   its current meaning untouched. Rationale: visible predictions, zero new
   state machine, consistent with the widget's existing accept vocabulary.
2. **Scope v1 to history only; drop "common sense".** Ship the follow-word
   index; log acceptance rates; let data justify any D/E follow-up.
3. **Predict one word per accept press, not whole tails.** Repeated presses
   still give the "keep hitting the key" flow the request wants, but each step
   is visible and individually rejectable. (Optionally show 2–3 words of ghost
   context while committing only the first — nice compromise.)
4. **Rank with a small extension of the existing signals**, not a new
   philosophy: `P(next | prev)` with add-k smoothing, backoff to unigram
   recency/frequency when the bigram is unseen, and a project-scope boost
   (the codebase already has per-project history filtering —
   `prompt_history_project_filter.py`). Reuse `RELATION_*`/`RECENCY_*`
   vocabulary where possible so the two models stay mutually intelligible.
5. **Trigger automatically, not only on a key chord.** Once the model exists,
   ghost text can render opportunistically after each keystroke (debounced,
   like soft completion), with the accept key as the only "trigger". This
   removes the need for users to remember to ask for predictions and makes a
   dedicated trigger binding unnecessary. Keep a config kill-switch
   (`next_word: off`) for the distraction-averse.
6. **Privacy/scope default:** personal history + current-project history only;
   never cross-project leakage by default (mirrors the existing project
   filter). Short-word indexing is required (§1.3), but exclude pure-digit
   tokens.

## 5. Recommended solution (v1)

1. **New `FollowWordIndex`** (naming: `src/sase/history/prompt_follow_word_index.py`,
   or in `sase_core` in Rust per §1.4 with Python bindings — decide at
   implementation time, defaulting to Rust if the index-scan cost matters):
   `dict[prev_word_folded, list[(next_word, count, last_used)]]`, top-k (e.g.
   8) followers per predecessor, built from the same newest-24-shards/20k-prompt
   window and the same `_cached_tokenized_shard` cache, but with its own
   tokenizer pass that keeps short words. Additive smoothing + unigram
   backoff at query time. Synchronous `<10 ms` in-memory query; async
   build with stale-while-revalidate and the existing cold-placeholder UX.
2. **Surface as ghost text** in `PromptTextArea` reusing the soft-completion
   rendering/accept path (`<ctrl+l>`/`<ctrl+f>` accept one word; `Esc`/typing
   dismisses). No changes to `_try_file_completion_tab` or `<ctrl+t>`
   semantics. Auto-trigger debounced post-keystroke; config-gated.
3. **Instrumentation first-class:** log suggestion-shown/accepted/dismissed
   counts (existing prompt-stats area) so the D/E decision and ranking tuning
   are data-driven.
4. **Tests:** index unit tests (bigram counts, smoothing/backoff, short-word
   handling, project scoping), widget tests (ghost render/accept/dismiss,
   no-interference with `<ctrl+t>` menu flow), perf assertion (query p99
   budget). Follow `sase/memory/lint_and_test.md` gates before landing.
5. **Explicitly out of v1:** `<ctrl+t>` chaining, static English tables, LLM
   suggestions, multi-word auto-commit, cross-project pooling.

## 6. Risks / open questions for the implementer

- Rust-vs-Python placement (§1.4) needs a decision with the `sase-core`
  owners; starting in Python behind a thin adapter interface keeps the option
  open.
- Ghost-text rendering inside a Textual `TextArea` with vim modes, snippets,
  tabstops, and the frontmatter bar needs care — the soft-completion mixin is
  the integration point to study, including what happens mid-snippet-session.
- `<ctrl+t>` vs `toggle_full_height` (`default_config.yml:537`) and terminal
  interception of `ctrl+t` (some terminals/muxes swallow it) deserve a check;
   if `<ctrl+t>` is unreliable in some environments, the auto-ghost design
   (§4.5) conveniently reduces dependence on any trigger chord at all.
- Cold-start UX: with <8 prompts of history (cf. `RELATION_MIN_PROMPTS`),
   suppress ghosts rather than showing unigram noise.
