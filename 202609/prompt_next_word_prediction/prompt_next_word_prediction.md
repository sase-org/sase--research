# Next-word prediction in the prompt input (`<ctrl+t>` chaining): consolidated report

**Lead researcher** · 2026-09-28 · Merges five independent reports
(`prompt_next_word_prediction__{cdx,cld,grk,mus,gem}.md`, in this directory), with new
code verification and a new replay experiment on the cross-machine prompt archive.

---

## 1. Bottom line

**Build it, with changes.** Your prompts are highly formulaic, so a small, local,
sequence-aware (n-gram) model trained on your own prompts predicts the next word well
enough for a "keep tapping `<ctrl+t>`" rhythm. That holds only if you **see the guess
before you commit it** and the model **stays silent when unsure**. Four changes to the
plan as written:

1. **The premise is false today.** A second `<ctrl+t>` on an open word menu does *not*
   accept the highlighted word. It re-dispatches completion, rebuilds the same menu, and
   resets the highlight to row 1. The chain needs a defined start: `<ctrl+t>` on an open
   prompt-word or history-word menu should accept the highlighted row.
2. **Blind insertion loses keystrokes on new text.** Show the prediction as inline ghost
   text (Textual's built-in `TextArea.suggestion`, which sase's Command Line already
   uses). Each `<ctrl+t>` takes one ghost word and re-predicts. `ctrl+f`/`→` take the
   whole ghost.
3. **Leave "common sense" out of v1.** Three independent measurements agree that more or
   broader text adds only a point or two of accuracy. That includes a 50× larger corpus,
   measured here for the first time. An LLM cannot meet the keystroke latency budget, and
   neither can a local transformer.
4. **The engine belongs in `sase-core` (Rust).** This follows the project boundary rule.
   There is also a concrete memory reason: a CPython dict model over the full prompt
   archive cost **+182 MB RSS** in this research.

Expected value, stated plainly: suggestions shown under a sensible confidence gate are
right **~70–80%** of the time. On *novel* prose they save only **~4–9%** of keystrokes.
On formulaic or re-typed prompts they save **20–70%**. That skew is the feature's real
value, and part of it overlaps with tools you already have (Ctrl+K recall, xprompts,
snippets). See §4.

---

## 2. What the code does today (verified at `f379c64179`/`d1063d161c`)

| Fact | Evidence | Consequence |
| --- | --- | --- |
| INSERT `ctrl+t` always calls `_try_file_completion_tab()`. The active-menu branch handles `ctrl+n/p`, `ctrl+f/l`, `ctrl+d` but **not** `ctrl+t`. | `_prompt_text_area_key_handling.py` (active-menu block, then the `ctrl+t` branch) | A second `ctrl+t` re-dispatches. `_try_prompt_word_completion_tab` sets `_file_completion_index = 0`, so the highlight resets (confirmed by cld's widget probes). |
| A lone candidate commits on the first press. A shared prefix is inserted and the menu stays open. | `_file_completion_tab.py:256-330` | Unique words must keep committing in one press (grk A1). |
| `_commit_word_completion` leaves the cursor right after the word, with **no trailing space**. | `_file_completion_base.py:208` | This is the natural chain slot. `ctrl+t` there is a no-op today unless longer words match. |
| Whitespace or an empty prefix opens **recent-file/artifact history**. | `_file_completion_tab.py` (`token_info is None`) | Next-word must not take over whitespace `ctrl+t` globally. |
| `PromptWordIndex` is a **bag of words per prompt**. Words are deduped per prompt, have no positions, and `word_min_length: 5`. | `history/prompt_word_index.py`, `default_config.yml:516` | It cannot answer "what follows X Y". A new sequential index is needed, and it must keep short words (`to`, `the`, `a`). |
| Soft completion renders in the prompt **border subtitle** (`[^L] accept …`), not inline. | `_prompt_input_bar_completion_panel.py:289` | Corrects gem, which describes it as inline ghost text. Next-word needs a new paint path. |
| Textual 8.0.1 `TextArea.suggestion` draws dim text at the cursor. Typing matching characters consumes it. `action_cursor_right` **inserts the whole suggestion** wherever the cursor is. | `.venv/.../textual/widgets/_text_area.py:411, 1397, 1548, 2113` | Ghost text is nearly free. INSERT `ctrl+f` maps to `cursor_right` (`vim_text_area.py:58`), so `ctrl+f`/`→` already accept the whole ghost. |
| sase's Command Line already does fish-style ghosts through `suggestion`. Its documented contract is "Right to accept ghost text". | `command_line/screen_navigation.py:615`, `default_config.yml:530-537` | There is an in-repo precedent for both the paint path and the accept-all key. |
| Command Line `toggle_full_height: ctrl+t` is scoped to the focused Command Line panel. | `default_config.yml:537` | mus's binding-conflict worry is moot for the prompt bar. |
| Undo: Textual checkpoints every edit longer than one character. | `textual/document/_history.py:88-118` | Each `" word"` accept is its own undo step. Accept-all is one step. |
| The Ctrl+K project filter already lives in `sase_core::prompt_history_filter`: "the host resolves … off the event loop; every operation here is pure and synchronous". | `sase-core/crates/sase_core/src/prompt_history_filter/mod.rs` | This is the architectural template for the new index. |

---

## 3. What the data says

### 3.1 Corpus facts (aggregate only; no prompt text reproduced)

- **Local history on apollo** has one shard (`2609.json`) holding 670 deduplicated prompts.
  **~70% are machine-generated** (epic-phase launches, `%id(` / `#bd/` blocks, swarm and
  lead templates). Only 197–221 are human-typed (the count depends on the heuristic),
  which is about 14k prose tokens. cld first flagged this; only cld and this report
  filtered for it.
- **The canonical prompt archive** (agents sidecar, `prompts/YYYYMM/`) holds **6,955
  prompts from 2026-03 to 2026-09**. It is cross-machine and dominated by **athena**
  (about 92% of agent references). None of the five reports measured it. It removes
  cld's "history is per machine" limitation. The catch: archived bodies are
  *post-xprompt-expansion* and duplicated across swarm members, so they need
  paragraph-level dedup and template stripping. After deduping Mar–Aug by paragraph, it
  contributes **702k tokens**, 50× the local human corpus.
- About 100% of local prompts start with a `#gh:`/`#git:` tag, so the project can be
  derived from text today. The archive is already per project.

### 3.2 Reconciling the accuracy numbers

cdx reports 34.6% top-1 and cld reports 22–43%. They differ because cdx trained and
tested on **all** 670 rows, including the machine-generated ones, with a coarser
tokenizer. cld and this report tested on **human-typed prompts only** and agree
closely:

| Next word, human prompts (4–5-gram, stupid backoff) | cld | Lead: local-only | Lead: archive + local | Lead: archive + local, local counts ×5 |
| --- | --- | --- | --- | --- |
| All prompts, top-1 / top-3 | 41.9 / 49.4% | 42.1 / 50.7% | 42.1 / 52.7% | **43.5 / 53.9%** |
| **Novel** prompts (<30% 5-gram overlap), top-1 / top-3 | 22.3 / 30.6% | 24.4 / 34.5% | 26.1 / 38.4% | **26.5 / 39.2%** |
| Near-duplicate prompts, top-1 | 87.8% | **85.6%** | 79.5% | 84.3% |
| Positions right after a ≥5-char word (where your chain starts), top-1 | — | 41.2% | 44.0% | 45.3% |
| Same, novel prompts only | — | 20.7% | 25.4% | 26.0% |

Lead method: prequential replay. The model is warmed on the oldest 40% of human
prompts, then each later prompt is scored word by word and added after scoring. That is
9,079 positions (5,334 novel). Archive months are Mar–Aug only, so there is no test
leakage. Matches are exact on normalized tokens.

Takeaways:

- **Context is everything.** A context-free ranking (what today's history-word logic
  amounts to) gets about 7% top-1 (cld). Bigrams alone get about 19–25%. Orders 3–4 are
  where the value appears, and order 5 adds under 1 point (cdx and cld agree).
- **More data buys little.** The 50× larger archive adds about 2 points top-1 and 4–5
  points top-3 on novel text. cld's learning curve shows the same thing, and so does its
  docs-corpus background model (+0.7). The archive's real value is **cold start on a
  machine**: apollo has only one month of local history.
- **Unweighted mixing dilutes personal recall.** Near-duplicate top-1 falls from 85.6%
  to 79.5% when older archive text is mixed in unweighted. Weighting local or recent
  counts above the archive recovers most of it (84.3%). Blend sources and decay by
  recency. Do not simply concatenate.
- **Confidence gates must count distinct observations, not weighted mass.** With local
  counts ×5, the `support ≥ 3` gate was satisfied by a single local sighting, which
  inflated coverage. Gated numbers for that column are not comparable.

### 3.3 Gating, keystroke savings, and the value of chaining

The keystroke-savings rate (KSR) is an **upper bound**. It assumes a correct ghost word
costs one press instead of `len+1` keystrokes, and a wrong ghost costs nothing because
it is ignored. It ignores attention cost.

| Local-only model | Shown | Precision when shown | Ghost KSR |
| --- | --- | --- | --- |
| Ungated ghost at every word, all prompts | 100% | 42% | 32.8% |
| Gate: order ≥2, p ≥0.6, margin ≥0.2, support ≥3, all prompts | 18.6% | **81.4%** | 11.8% |
| Same gate, novel prompts | 14.8% | **70.9%** | 7.9% |
| Same gate, only in chains started right after a ≥5-char word, all / novel | — | — | **7.5% / 4.1%** |
| cld: **blind** insertion (plan as written), novel, ungated | 87.5% | 25.5% | **−7.5%** |

- **Blind insertion is a net loss on new text.** cld measured −7.5% KSR because each
  miss costs a press plus an undo. Preview-then-accept turns that loss into a gain.
- **Gating makes it pleasant.** A precision of 70–80% at 15–25% coverage matches Gmail
  Smart Compose's practice: serve only above a confidence threshold and compare models at
  equal coverage.
- **Chain-only triggering reaches about 60% of the available gated value.** Most words
  are typed, not completed, and prompt openers and stock phrases begin after a typed
  space. Once a chain produces a correct word, the median run is **2 words on novel
  prompts, 3 overall, and 4–7 on formulaic or near-duplicate text**.
- **Most correct novel-text predictions are short function words** (cld: 57% are ≤3
  characters, but those carry only 36% of the characters saved). The payoff is in
  phrases and re-typed text.

### 3.4 Where cld's data points to a bigger win

cld fed the same n-gram context into today's **current-word** `<ctrl+t>` ranking, using
the repo's real completion code path as the baseline. Top-1 rose from **18% to 38% at a
1-character prefix** and from 39% to 51% at 2 characters. That makes the *first* word of
every chain right twice as often, with no new UX. This report did not re-measure it. It
is the single strongest evidence in the set, and it reuses the same index.

### 3.5 Performance

- **Query.** An interned-ID Python table answers in 6–8 µs (cld). A naive
  dict-of-Counter recomputing totals takes 0.1–3 ms (this report). Rust with
  precomputed top-k per context would be well under 10 µs. **No worker is needed on the
  query path**, but top-k per context must be precomputed at build time.
- **Memory.** A local-only model has about 32k n-gram entries, which is trivial. At
  archive scale (≈920k entries, 600k contexts) a CPython dict model costs **+182 MB**.
  cld measured 189 MB for a 408k-token docs corpus. Dropping contexts seen once (except
  orders 0–1) leaves 218k contexts. A compact Rust table with interned IDs and bounded
  successors is 10–25× smaller.

---

## 4. Critique: is this a good idea?

**Yes, as explicit, precision-first continuation of your own phrasing.** It is not an
always-on generative autocomplete.

What is right about the plan:

- The signal is real. Agent prompts reuse openers ("Can you help me…"), request
  templates, repository vocabulary and closing formulae.
- "Keep tapping one key to take the next word" is a proven interaction: fish's `alt+f`,
  zsh-autosuggestions partial accept, and VS Code's
  `editor.action.inlineSuggest.acceptNextWord`.
- It can be fully local, private and sub-millisecond.
- sase already has almost every piece: the completion dispatcher, a warmed history
  cache, word casing and boundary logic, and a ghost-text precedent.

What is wrong or missing:

1. **Broken trigger (§2).** This needs a small, explicit state-machine change.
2. **Blind insertion (§3.3).** You cannot "keep hitting `<ctrl+t>` if the guesses are
   correct" without first seeing the guess.
3. **Narrow reach.** Chain-only captures about 60% of the gated value. An *opt-in*
   automatic ghost at word boundaries captures the rest, including openers.
4. **Attention cost is real.** Quinn & Zhai (CHI '16) found that more assertive
   suggestions cut keystrokes but could slow entry. Arnold et al. (IUI '20) found that
   predictive text makes writing more predictable. Default to silence when unsure, and
   keep the ghost short.
5. **Dirty corpus.** About 70% of local history is machine-generated boilerplate, and
   the archive is template-expanded and swarm-duplicated. Without hygiene, the model
   learns `%model:@medium` chains and research-template prose.
6. **"Project history" does not exist as a field.** `PromptEntry` has only `text`,
   `timestamp`, `last_used` and `cancelled`. Use the project as a *boost*, not a filter:
   per-project corpora are too small to filter.
7. **Part of the value overlaps with better tools.** The biggest wins (88% top-1, 7–11
   word runs) come from re-typing near-identical prompts. Ctrl+K recall, saved xprompts
   (`sase prompt save`) and `ace.snippets` serve that case in one action. Next-word
   chaining earns its place on *variations* of familiar phrasing, and by making the
   first `<ctrl+t>` word right more often (§3.4).
8. **Privacy.** Prediction can resurface secrets from history. That is the same exposure
   as Ctrl+K and history-word completion. Filter URL-, hash- and secret-like tokens,
   honour deletions, and keep everything local.

**Would I take a different approach?** Same core (a local n-gram over your own prompts),
but framed as **fish-style history autosuggestion with word-at-a-time accept on
`<ctrl+t>`**, not as a new "guess a word" feature. I would also ship the context-aware
current-word ranking alongside it, because it is the cheapest, largest measured win.

---

## 5. Adjusted requirements (changes to your ask, called out)

| # | Your ask | **Adjusted requirement** | Why |
| --- | --- | --- | --- |
| R1 | `<ctrl+t>` inserts the guessed next word | **Preview first.** A confident guess appears as dim inline ghost text. `<ctrl+t>` accepts **one** ghost word and re-predicts. `ctrl+f`/`→` accept the whole ghost. | Blind insertion is −7.5% KSR on novel text. Ghost gives fish and Command Line parity for free. |
| R2 | "`<ctrl+t><ctrl+t>` completes the selected word" | **New behavior:** `<ctrl+t>` on an open `prompt_word`/`history_word` menu accepts the highlighted row (never the loading placeholder), then arms the chain. `ctrl+f`/`ctrl+l` arm the same chain. Unique matches still commit on the first press. | Today the second press resets the menu. Requiring two presses for a unique match would be a regression. |
| R3 | Predict only after completing a word | **Also** `<ctrl+t>` at the end of a typed complete word where today's dispatch is a no-op. Whitespace `<ctrl+t>` with no ghost **stays file history**. Automatic ghosts at word boundaries are a later **opt-in** mode. | Chain-only reaches about 60% of the value. File history is a live feature. |
| R4 | Always guess | **Confidence-gated; silence by default.** Seed gate: matched order ≥2, distinct support ≥3, p ≥0.6, margin ≥0.2. Never ghost from a unigram-only match. When confidence is lower on an *explicit* `<ctrl+t>`, show a small `next_word` menu of the top 3. | Gated precision is 70–80%. Top-3 on novel text is 35–39%, versus 25% for top-1. |
| R5 | "User/project prompt history" | Train on **human-typed prose only**. Add an `origin` field (`typed`/`generated`) set at write sites, with a heuristic backfill. Add the **cross-machine canonical archive** as a lower-weight source. Weight the project as a **boost**, not a filter. | 70% of local rows are generated. The archive fixes per-machine cold start (§3.2). |
| R6 | "Maybe common sense" | **Out of v1.** No LLM or neural model on the keystroke path, and no bundled general-English table. Revisit only as a separate, asynchronous, explicit "suggest phrase" action that beats the n-gram on the replay harness. | +0.7 to +2 points from broader text. No runtime is installed. Latency. |
| R7 | One word per press | Keep that, **plus** a multi-word ghost (extend while each step clears the gate, capped at about 5 words) with accept-all on `ctrl+f`/`→`. | Near-duplicate runs are 7–11 words. |
| R8 | — | **New scope:** feed n-gram context into current-word `<ctrl+t>` ranking. | 18% → 38% top-1 at a 1-character prefix (cld). |
| R9 | — | **Scope guard:** prose only. Structured kinds (`#`, `%`, `=`, `@`, `+`, paths, Jinja, placeholders, VCS) are unchanged. Ghost only in INSERT mode, with no menu or snippet session open, outside code fences and frontmatter, and only when the rest of the line is blank in v1. | Avoids fighting structured completion. Textual ghosts do not re-wrap. |
| R10 | "Fast" | Query under 1 ms on the UI thread with no I/O. Build off-thread, add incrementally on submit, and swap atomically. A cold index means no ghost, never a stall. | `tui_perf` rules; §3.5. |

---

## 6. Disagreements between reports, and how they are resolved

| Question | Positions | Resolution |
| --- | --- | --- |
| Preview surface | cdx: popup menu. cld, grk, gem: inline ghost. mus: ghost on a different key. | **Ghost for a confident top-1; small menu only on an explicit, lower-confidence `<ctrl+t>`.** A ghost costs no layout and supports multi-word previews. The menu covers alternatives when a guess is ambiguous. Never show both: `ctrl+f` means "accept menu row" while a menu is open. |
| Keep `<ctrl+t>` or move to another key | mus: leave `<ctrl+t>` alone and accept with `ctrl+l`/`ctrl+f`. Others: use `<ctrl+t>`. | **`<ctrl+t>`.** Your muscle memory is already there, and grk's chord survey shows word-at-a-time accept on the completion chord is standard. mus's mode-confusion concern is answered by *visible* state: `<ctrl+t>` takes the ghost if one is showing, otherwise it behaves as today. |
| Whitespace `<ctrl+t>` | gem, grk: next-word before file history. cdx, cld: file history unless a chain or ghost is live. | **File history stays.** Next-word takes over only when a ghost is visible, or at a complete-word end where today's dispatch is a no-op. |
| "Common sense" | gem: a static ~5k-idiom developer prior at weight 0.2. grk: project phrasing (xprompts, snippets). cdx, cld, mus: none. | **None in v1.** gem's prior is unmeasured. Every measurement of broader text shows +0.7 to +2 points while lowering gated precision. grk's xprompt/snippet layer is a cheap later experiment; gate it on the harness. |
| Smoothing | gem: Kneser-Ney/Jelinek-Mercer. cld, grk, mus: stupid backoff or add-k. cdx: benchmark all three. | **Start with stupid backoff plus recency and source weights.** Adopt KN only if it wins on exact match or characters saved *at equal coverage*. |
| Unigram fallback | mus: yes. grk: never insert from a unigram. | **No unigram ghosts.** Unigrams may rank a lower-confidence explicit menu. |
| Python or Rust | grk: Python v1. mus: undecided. cdx, cld, gem: `sase-core`. | **`sase-core`.** The boundary rule applies (sase-nvim's LSP and any web UI need identical behavior). The accepted decision record *rust-core-required* forbids a Python fallback. `prompt_history_filter` is the precedent. The CPython model costs 182 MB at archive scale. |
| Project scoping | cdx: new `project_key` field. cld: derive from the VCS tag. grk, gem: Ctrl+K catalog. mus: never pool across projects. | **Boost, not filter.** Derive the project from the VCS tag with the existing catalog now. Record `project_key` (with `origin`) on new writes for robustness. Pooling across projects stays on, down-weighted, because per-project corpora are small. mus's strict isolation would starve cold projects. |
| Right-arrow | grk: override so `→` never accepts. cld: keep Textual's accept-all. | **Keep accept-all.** Ghosts appear only at end of line (R9), where `→` would otherwise just wrap. This matches the Command Line contract. |

Factual corrections to individual reports: gem's soft completion is subtitle-based, not
inline (§2). mus says repeated `<ctrl+t>` cycles or narrows candidates; it
re-dispatches and resets the highlight. cdx's accuracy numbers include
machine-generated prompts (§3.2).

---

## 7. Recommended solution

### 7.1 Interaction contract (INSERT mode, prompt bar)

```text
ctrl+t  on a structured token            → unchanged dispatcher
ctrl+t  on a partial prose word          → unchanged: unique commit / shared prefix / menu
ctrl+t  on an open prompt_word/history_word menu
                                         → NEW: accept highlighted row, then arm chain
ctrl+t  while a next-word ghost is shown → NEW: insert separator + first ghost word
                                           (one undo step), re-predict, re-ghost
ctrl+t  at end of a complete word, no ghost, current-word dispatch would be a no-op
                                         → NEW: predict; ghost if gated, else a top-3
                                           next_word menu (ctrl+t accepts + continues);
                                           else no-op
ctrl+t  on whitespace, no ghost          → unchanged: recent file / artifact history
ctrl+f / →  with ghost shown             → accept whole ghost (Textual built-in)
ctrl+f / ctrl+l on open word menu        → accept (unchanged) + arm chain
typing                                   → type-through consumes matching ghost; else clears
cursor move, Esc/NORMAL, menu opens, pane switch → clear ghost, end chain
```

"Arm chain" means: after a word-completion commit, predict synchronously from the warm
index and set `suggestion` if the gate passes. It never opens a menu by itself.

### 7.2 Model (`sase_core::prompt_prediction`, new)

- **Sources:** (1) local prompt history, `origin=typed` only, cancelled drafts included;
  (2) the current project's canonical archive, deduplicated by paragraph with
  xprompt/template text stripped, at lower weight; (3) earlier text in the current draft
  as a small cache. Machine-generated rows are excluded.
- **Tokens:** whitespace tokens. The surface form is used for insertion (canonical
  casing chosen by recency). A normalized key (casefold, strip surrounding punctuation)
  is used for context. Minimum length is 1. Sequence boundaries fall at prompt start,
  paragraphs, list items, sentence ends, code fences and structural tokens (`%…`, `#…`,
  `+…`, `@…`, `{{…}}`). Digit-only, hash-like, URL and secret-like tokens are dropped.
- **Scoring:** successor counts for context lengths 0–4, with the top-k per context
  precomputed. Stupid backoff (α ≈ 0.4). Recency decay (cld: 14-day half-life, +0.7
  points). Weights by source (local over archive). Same-project boost.
- **Gate (seeds, to be tuned):** matched order ≥2, distinct support ≥3, p ≥0.6, margin
  ≥0.2. A multi-word ghost extends while each step passes, up to 5 words or the line
  width.
- **API sketch:**
  - `build_prompt_prediction_index(rows, config) -> handle`
  - `handle.add(row)`
  - `handle.predict(text_before_cursor, project_key, k) -> [{word, score, order, support, source_mix}]`
  - `handle.continuation(text_before_cursor, project_key, max_words) -> ghost`
  - `handle.rank_prefix(text_before_cursor, prefix, candidates) -> scores`, used for
    R8.
- **Boundary:** Python does shard and archive reads plus origin tagging off-thread, then
  hands rows to Rust (the `prompt_history_filter` pattern). Move the
  `sase-core-revision.txt` pin. `sase_xprompt_lsp` can later serve the same index to
  sase-nvim.

### 7.3 TUI integration (`sase` repo)

- Fold the build into the existing `_startup_history_words` warm job, using the same
  shard source token plus the archive revision. Swap atomically. Call `add()` on prompt
  submit. Deleting history invalidates the index.
- Add a new `_prompt_next_word.py` mixin: `_refresh_next_word_ghost()`, the `ctrl+t`
  pre-branch in `_prompt_text_area_key_handling.py`, ghost clearing mirrored from
  `CommandLineInput`, and a new `next_word` completion kind.
- Check visual interaction with the post-render mixins (`_line_rendering`,
  `_codeblock_syntax_highlight`, `_todo_highlight`) using PNG goldens.
- Config under `ace.prompt_completion`: `next_word: off | chain | auto` (default
  `chain`; put `auto` behind a feature flag), `next_word_min_confidence`,
  `next_word_max_words`, `next_word_sources`. Update `default_config.yml`, `docs/ace.md`
  (Completion section and INSERT keymap) and `docs/configuration.md`.

### 7.4 Measurement

- Turn the replay harness into a dev tool: prequential replay over human-typed prompts,
  split into novel / mid / near-duplicate cohorts. Report top-1/top-3, the
  precision-coverage curve, KSR, run lengths, and latency and memory. Tune the gate,
  α, recency and source weights on it, and compare variants at equal coverage.
- Keep local, text-free counters: ghosts shown, words accepted, accept-alls, dismissals,
  chain length, and why each chain ended. Target a ≥60% accept rate for shown ghosts.

### 7.5 Delivery order

| Phase | Scope | Why this order |
| --- | --- | --- |
| **P0** | `<ctrl+t>` on an open word menu accepts the highlighted row. Tests. | Tiny and independent. It fixes the premise and the reset-to-row-1 quirk. |
| **P1** | `origin` (and `project_key`) on `PromptEntry` with backfill. `sase-core` index, binding, warm cache and incremental add. Replay harness. | This is the foundation. The harness sets the gates before any UI ships. |
| **P2** | The requested feature: ghost chaining on `<ctrl+t>`, accept-all on `ctrl+f`/`→`, the explicit top-3 `next_word` menu, and the scope guards. | Your ask, corrected. |
| **P2′** | Context-aware current-word ranking (R8). | Largest measured win with no new UX. It can ship before P2. |
| **P3** | Opt-in `auto` ghost at word boundaries, behind a flag. | Recovers the roughly 40% of value that chain-only misses. |
| Later | xprompt/snippet phrasing as a low-weight source; an async explicit LLM "suggest phrase" action. | Only if the harness shows a gain at equal coverage. |

---

## 8. Risks and open questions

- **Terminal delivery of `ctrl+t`.** It is reliable in the current setup. The auto mode
  reduces dependence on it.
- **Ghost at soft-wrap edges.** Textual clips rather than re-wraps, so keep ghosts short
  and end-of-line only.
- **Stale archive.** The archive is post-expansion text, so template stripping needs a
  reliable rule. Prefer the typed text when the local copy exists, using a normalized
  hash dedup.
- **Gate drift as the corpus grows.** Raw-count gates loosen with more data. Re-tune from
  the harness periodically, and keep support as *distinct* observations.
- **Human-typed detection.** The heuristic misses edge cases (for example, prompts
  assembled by `%dispatch`). Recording `origin` at write time is the durable fix.

---

## 9. Recommended solution (summary)

Build a **local, confidence-gated, project-boosted 4–5-gram "prompt prediction" index in
`sase-core`**. Train it on your **human-typed** prompt history plus the
**cross-machine canonical prompt archive**, weighted toward recent local text, and warm
it off-thread in the existing history cache.

Surface it as **inline ghost text** (Textual `suggestion`). `<ctrl+t>` accepts one ghost
word and re-predicts. `ctrl+f`/`→` accept the whole ghost. `<ctrl+t>` on an open word
menu newly accepts the highlighted row and arms the chain.

Leave structured completion and whitespace file history untouched. Use the same index to
rank current-word `<ctrl+t>` completions by preceding context. Keep LLMs and generic
"common sense" out of v1, and let a replay harness plus local acceptance counters decide
any later additions.

---

## Sources

- Chen et al., *Gmail Smart Compose: Real-Time Assisted Writing* (KDD '19): p90 60 ms
  latency, confidence-thresholded triggering, a personal n-gram blended with a global
  model. <https://arxiv.org/abs/1906.00080>
- Hard et al., *Federated Learning for Mobile Keyboard Prediction* (2018): Gboard top-1
  recall of 13.0% for an n-gram and 16.4% for CIFG. <https://arxiv.org/abs/1811.03604>
- Brants et al., *Large Language Models in Machine Translation* (EMNLP-CoNLL 2007):
  stupid backoff. <https://aclanthology.org/D07-1090.pdf>
- Mani et al., *Real-Time Optimized N-gram for Mobile Devices* (2021).
  <https://arxiv.org/abs/2101.03967>
- Shareghi et al., *Show Some Love to Your n-grams* (NAACL 2019).
  <https://aclanthology.org/N19-1417/>
- Quinn & Zhai, *A Cost-Benefit Study of Text Entry Suggestion Interaction* (CHI '16).
  <https://dl.acm.org/doi/10.1145/2858036.2858305>
- Arnold, Chauncey & Gajos, *Predictive Text Encourages Predictable Writing* (IUI '20).
  <https://www.eecs.harvard.edu/~kgajos/papers/2020/arnold20predictive.pdf>
- fish shell autosuggestions (`alt+f` accepts one word; `→`/`ctrl+f` accept all).
  <https://fishshell.com/docs/current/interactive.html>
- VS Code `editor.action.inlineSuggest.acceptNextWord`.
  <https://code.visualstudio.com/docs/editing/ai-powered-suggestions>
- In-tree: Textual 8.0.1 `TextArea.suggestion` and `EditHistory`; the sase files cited
  in §2; `sase-core` `prompt_history_filter`.
- Lead experiment: a throwaway replay harness (pure Python) over
  `~/.sase/prompt_history/2609.json` and archive months 202603–202608. It printed
  aggregates only. The method is in §3.2.
