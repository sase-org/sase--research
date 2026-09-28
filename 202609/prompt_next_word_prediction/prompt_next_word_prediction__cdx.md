---
title: Fast personalized next-word prediction for the SASE prompt widget
date: 2026-09-28
researcher: cdx
status: complete
---

# Fast personalized next-word prediction for the SASE prompt widget

## Executive conclusion

This is a good feature idea if it is treated as **explicit, personalized, high-precision
continuation**, not as always-on generative autocomplete. Prompt language is unusually
repetitive and project-specific, the user explicitly asks for a prediction with
`Ctrl+T`, and an incorrect guess is easy to ignore. Those properties make a small local
statistical model much more attractive here than they would be for general prose.

My recommended first implementation is an in-memory, sequence-aware word n-gram model
(up to five preceding lexical tokens) trained locally from:

1. the active project's canonical prompt archive and project-attributed local history;
2. the user's machine-wide prompt history as a lower-priority backoff model; and
3. the current draft as a very small, highest-recency cache.

It should return up to three candidates but show nothing unless the top candidate clears
a calibrated confidence threshold. Querying must be a pure in-memory operation. Index
construction, source reads, tokenization, and persistence must happen off the TUI event
loop. The shared tokenizer, model, scoring, and query contract belong in `sase_core`,
with the Python TUI acting as a thin adapter.

I would **not** put a remote LLM or a newly loaded local transformer on the keystroke
path. A neural/general-language model can be evaluated later as an optional prior or
reranker, at equal suggestion coverage, if the history model demonstrably leaves useful
accuracy on the table. For the first version, abstaining is better than filling gaps
with generic “common sense.”

## Requirements I would adjust

These are deliberate changes or clarifications to the request:

| Requested direction | Recommended adjustment | Why |
| --- | --- | --- |
| Keep pressing `Ctrl+T` | Repeated `Ctrl+T` accepts-and-chains only for plain word and next-word completion kinds. Preserve current behavior for paths, directives, references, snippets, and other structured menus. | A repeated key must not accidentally accept a path or launch-control token. |
| Predict after completing a word | Arm a transient chain only after an explicit word completion acceptance, anchored to the exact text revision and cursor offset. Any edit, cursor movement, pane switch, or `Esc` cancels it. | Ordinary `Ctrl+T` in whitespace currently means recent-file/artifact history; next-word prediction must not steal that behavior globally. |
| Guess the next word | Suggest only at a clean lexical boundary with no preserved right-hand suffix. Insert exactly the necessary separator plus one word. Do not generate punctuation or multiword phrases in version 1. | This keeps edits reversible and avoids damaging Markdown, paths, directives, or existing suffix text. |
| Use user/project history | Add durable project identity to new local prompt-history records; use the canonical per-project prompt archive for historical project data. Treat legacy unattributed local rows as user-global only. | `PromptEntry` currently has no project field. Inferring the project from prompt text is incomplete because prompts for the current project need not contain a project tag. |
| “Maybe common sense” | Use machine-wide user history as the initial broad prior and abstain when evidence is weak. Evaluate a bundled general model only in a later, measured experiment. | Generic completions can be fluent but unhelpful, increase privacy/licensing/dependency surface, and make instant cross-platform behavior harder. |
| “Excellent” prediction | Optimize precision at a chosen coverage and characters saved, not perplexity or the number of suggestions emitted. | A quiet model is better than a confidently annoying one in an explicit completion workflow. |

## Is the interaction a good idea?

### Why it fits this product

- Agent prompts contain recurring instruction templates, repository terminology,
  filenames, test vocabulary, and habitual connective phrases. A personal/project model
  can exploit those repetitions directly.
- The feature is explicitly invoked. It does not continuously distract the user or
  replace text while they type.
- One accepted word becomes the exact context for the next lookup, so a cheap model can
  support a satisfying one-chord-per-word rhythm.
- SASE already has a completion panel, selection navigation, word casing logic, prompt
  history, deletion controls, and an off-thread history-word warmup path. This is an
  extension of an established interaction rather than a new UI system.

### The main problems

1. **The proposed key sequence changes existing semantics.** Today `Ctrl+T` starts or
   narrows completion; `Ctrl+F`/`Ctrl+L` accepts. Pressing `Ctrl+T` while a menu is open
   currently dispatches completion again rather than accepting the selected row. The
   desired `Ctrl+T Ctrl+T Ctrl+T ...` flow therefore needs an explicit state-machine
   change and documentation.
2. **Whitespace already has a provider.** At whitespace or an empty prefix, `Ctrl+T`
   opens recent files and artifact references. A global “word boundary means next word”
   rule would regress a useful feature. The chain must be transient and anchored to a
   prior word acceptance.
3. **A bad suggestion has an attention cost even when insertion is manual.** Showing a
   plausible but wrong word repeatedly can be slower than typing. Confidence-based
   abstention is a product requirement, not a later optimization.
4. **Short words offer little net savings.** Accepting a three-letter word with a
   two-key chord is only worthwhile when confidence is high or it unlocks a longer
   continuation. Ranking and evaluation should include gross characters saved, not only
   exact-match accuracy.
5. **History can resurface sensitive text.** The existing history-word provider already
   has this general risk; next-word prediction makes contextual resurfacing easier. The
   model should remain local, inherit deletion/pruning invalidation, filter secret-like
   and identifier-like candidates, and expose a single disable/reset control.

On balance, the benefits outweigh the risks because invocation is manual and the local
history is strongly repetitive. I would ship it experimentally with conservative
thresholds, then tune against acceptance and rejection data stored without prompt text.

## What the current implementation provides—and what it cannot provide

Relevant code and documentation inspected at SASE revision
`f379c6417954120ee24f1b21160894c9d6d91835`:

- `src/sase/ace/tui/widgets/_prompt_text_area_key_handling.py` routes insert-mode
  `Ctrl+T` to `_try_file_completion_tab()`.
- `src/sase/ace/tui/widgets/_file_completion_tab.py` prioritizes structured providers,
  paths, prompt-local word completion, then history-word completion. It inserts a lone
  match or a shared prefix and otherwise opens a menu.
- `src/sase/ace/tui/widgets/_file_completion_accept.py` accepts the highlighted menu row
  on `Ctrl+F`/`Ctrl+L`, then clears the menu.
- `src/sase/ace/tui/widgets/prompt_word_completion.py` already defines useful Unicode
  word boundaries, case preservation, safe partial-word replacement, and current-draft
  candidates.
- `src/sase/history/prompt_word_index.py` builds an immutable index from at most 24
  history shards and 20,000 prompts. It is mtime-keyed and warmed off-thread.
- `src/sase/history/prompt_word_ranking.py` ranks history words by prompt-level
  co-occurrence, recency, and frequency. It is useful candidate-prior machinery, but it
  is not a language model.
- `src/sase/history/prompt_store.py` stores exact prompt text and timestamps in monthly
  shards. Records are deduplicated by exact text across reads, and `PromptEntry` has no
  durable project identity.
- The canonical agents-sidecar prompt archive is project-specific and curated, while
  local history is machine-wide across repositories (`docs/prompt.md`).

The crucial limitation is that `PromptWordIndex` intentionally stores each distinct word
at most once per prompt. It retains “these words occurred together,” but discards token
order, adjacency, repeated occurrences, punctuation, and sentence boundaries. It cannot
answer “what followed these preceding words?” A new sequence-aware index is required;
trying to stretch the existing co-occurrence score into next-word prediction would give
the wrong abstraction.

The current TUI performance rules also prohibit synchronous disk I/O, JSON parsing,
subprocesses, unbounded locks, or side-effectful resolution on a keystroke path. That
strongly favors a prebuilt immutable model with an atomic pointer swap after background
rebuild.

## Evidence from prior work

The closest production precedent strongly supports a hybrid of a broad model and a
lightweight personal n-gram:

- Google Smart Compose treated latency, personalization, privacy, and confidence-based
  triggering as first-class requirements. It served only the top suggestion when its
  confidence exceeded a threshold chosen for a target coverage, and evaluated exact
  match at comparable coverage rather than merely comparing perplexity. Its production
  target was p90 under 60 ms. See [Chen et al., “Gmail Smart Compose: Real-Time Assisted
  Writing”](https://arxiv.org/abs/1906.00080).
- For personalization, Smart Compose chose a small Katz-backoff n-gram trained on a
  user's recent sent mail and linearly interpolated it with the global neural model. The
  paper reports that the blend outperformed either extreme and improved production
  click-through and exact match. This is particularly relevant: a personal n-gram is
  not merely an obsolete baseline; it was selected because it is small, adaptive, easy
  to retrain, and data-efficient.
- Optimized n-gram work for mobile next-word prediction shows that Stupid Backoff,
  pruning, and compact lookup structures are well suited to top-k suggestions with
  strict memory and latency budgets. See [Mani et al., “Real-Time Optimized N-gram For
  Mobile Devices”](https://arxiv.org/abs/2101.03967).
- Strong n-gram baselines remain competitive in resource-lean settings and are queried
  with cheap lookups rather than matrix operations. See [Shareghi et al., “Show Some
  Love to Your n-grams”](https://aclanthology.org/N19-1417/).

These systems operate at much larger scale than SASE, so their exact models and latency
numbers do not transfer directly. The architectural lesson does: personalize with a
small local model, blend sources, trigger selectively, and measure at equal coverage.

## Local feasibility experiment

I ran a read-only aggregate experiment on the machine-local prompt history. No prompt
text or example phrase is reproduced in this report.

### Method

- 670 usable deduplicated prompts were ordered chronologically by `last_used`.
- The oldest 80% (536 prompts, 40,383 lexical tokens) formed training data; the newest
  20% (134 prompts, 8,656 within-prompt next-word targets) formed the test set.
- Tokens were lowercased Unicode word/identifier runs (`[\w-]+`). This intentionally
  simple tokenizer ignored punctuation and project identity.
- For each target, the model used the longest observed suffix of up to five preceding
  tokens, backing off to shorter contexts and finally a global unigram.
- This was teacher-forced chronological evaluation, not a replay of actual completion
  invocations. It therefore measures corpus predictability, not final UX acceptance.

### Results

| Maximum preceding-token context | Top-1 exact match | Top-3 exact match |
| ---: | ---: | ---: |
| 1 | 28.70% | 41.73% |
| 2 | 33.55% | 44.45% |
| 3 | 34.17% | 44.25% |
| 4 | 34.54% | 44.10% |
| 5 | 34.63% | 44.18% |

The marginal gain beyond three tokens is small, but contexts of four or five are cheap
to keep and capture repeated templates. More important is selective triggering:

| Example trigger policy | Test-position coverage | Top-1 precision when shown |
| --- | ---: | ---: |
| Support ≥ 2 and top empirical probability ≥ 0.50 | 38.56% | 66.15% |
| Support ≥ 3, top probability ≥ 0.60, and lead over runner-up ≥ 0.20 | 30.59% | 76.51% |
| Support ≥ 3, top probability ≥ 0.70, and lead over runner-up ≥ 0.30 | 26.79% | 81.29% |

At the middle policy, correct accepts averaged 6.11 inserted characters including the
separator. Among positions where the top prediction was both shown and correct, the
mean consecutive correct run was 4.0 words, the median was 1, 49.85% continued for at
least two words, and 33.17% continued for at least three. Long repeated templates create
a heavy tail, so the mean should not be mistaken for a typical run; the median is the
safer expectation.

These results are unusually promising for such a simple model. They also show why the
feature should abstain: unconditional top-1 accuracy is not high enough for a pleasant
experience. The proposed starting threshold of roughly 0.60 probability, 0.20 margin,
and three observations is only a benchmark seed. The production implementation should
calibrate it on the real tokenizer and tune for a precision/coverage target.

Limitations of this experiment:

- The local history contains submitted prompts, not the distribution of contexts where
  a user will press `Ctrl+T`; explicit invocation may be easier or harder.
- Exact prompt deduplication removes repeat counts for identical full prompts, while
  overlapping fragments still repeat.
- Project attribution was unavailable, so the expected gain from project scoping was
  not measured.
- The simple tokenizer omitted sentence/Markdown boundaries and did not filter secrets,
  hashes, paths, or control syntax.
- Confidence values are raw empirical ratios, not calibrated probabilities.

## Alternatives considered

| Approach | Quality on project phrasing | Hot-path latency | Footprint / portability | Privacy | Recommendation |
| --- | --- | --- | --- | --- | --- |
| Local project + user n-gram | High when phrases repeat; cleanly abstains | Hash/trie lookups; expected sub-millisecond | Small, no model runtime | Stays local | **Build first** |
| Existing bag-of-words history ranking | Topic-aware but cannot model adjacency | Fast | Already present | Stays local | Use only as a weak prior, not as the predictor |
| Bundled general n-gram | Better common-language fallback, weaker on SASE-specific phrasing | Very fast | Corpus/model licensing and package size | Local | Optional later prior if measured benefit justifies it |
| Small local neural LM (roughly 100M+ parameters) | Better semantic/general continuation, may miss personal jargon without adaptation | Hardware/runtime dependent; cold start and memory are material | Large cross-platform dependency | Local inference, but model can memorize training data | Shadow-test later, not MVP |
| Remote LLM/API | Strong semantic context | Network jitter is incompatible with instant completion | Operational cost and offline failure | Sends draft/history-derived context away | Reject for default path |
| Hybrid n-gram + neural reranking | Potentially best quality | More moving pieces; neural cost remains | Highest complexity | Depends on neural placement | Consider only after the n-gram baseline and telemetry exist |

A modern small neural model is technically possible. It is not the best first tradeoff
here: the feature asks for one word, has a small private adaptation corpus, must feel
instant on heterogeneous developer machines, and already shows strong predictable
repetition. The model-runtime dependency would be paying a large fixed cost to improve
the cases where a conservative system can simply remain silent.

## Recommended model design

### 1. Training sources and provenance

Build three logical models from deduplicated prompt records while retaining source
provenance:

- **draft cache:** sequences earlier in the current pane/stack, highest recency;
- **project model:** canonical archived prompts for the active project plus local rows
  carrying that project key;
- **user model:** machine-wide local prompt history, including legacy unattributed rows.

Do not silently treat every local row as belonging to the current project. Add an
optional `project_key` to new `PromptEntry` writes and preserve backward compatibility
for old JSON. At launch time SASE already knows the effective project; recording it is
more reliable than parsing a tag later. The canonical prompt archive supplies curated
historical project text. Dedupe the same authored prompt across archive and local
sources by normalized content hash so it does not receive accidental double weight.

Cancelled/failed prompts should initially be excluded or heavily downweighted: they can
contain malformed syntax and text the user chose not to submit. This should be validated
empirically rather than assumed forever.

### 2. Tokenization

Use one shared tokenizer for training and queries:

- Unicode word tokens, keeping internal ASCII hyphens and underscores so repository
  terms remain intact;
- explicit beginning-of-prompt, newline, sentence-boundary, list-item, and code-fence
  boundary tokens;
- casefolded lookup identity plus a canonical spelling selected by project-first,
  recency-weighted evidence;
- no prediction inside an unfinished structured token, file path, URL, code span,
  directive, xprompt/ref token, template placeholder, or number/hash-like token;
- filter e-mail addresses, URLs, high-entropy strings, long numeric identifiers, secrets
  matching existing detectors, and candidates the user deleted from history completion.

The model should predict a lexical word, not a subword. A subword model adds complexity
and can produce fragments that are awkward in this one-key/one-word contract.

### 3. Counts, backoff, and blending

Store successor counts for context lengths 0 through 5, with compact token IDs and
bounded top successors per context. Apply recency decay during background construction
rather than at every query. Prune very low-value old singletons, but retain rare project
terms when they occur in a repeated context.

For version 1, compare these on chronological holdout and select by precision/coverage:

1. longest-context empirical counts with Stupid Backoff;
2. interpolated absolute discounting; and
3. modified Kneser-Ney/Katz backoff.

The first is a credible starting point and produced the local results above. A more
complex smoother should land only if it improves exact match or characters saved at the
same coverage.

Blend source scores dynamically rather than using a fixed project weight:

```text
project_weight = effective_project_support / (effective_project_support + k)
P = draft_boost + project_weight * P_project + (1 - project_weight) * P_user
```

Here `k` is tuned on holdout data. This makes a mature project model dominate while a
cold project backs off gracefully. The current history-word relation/recency/frequency
score can contribute a small tie-breaking prior, but adjacency evidence must dominate.

### 4. Triggering

Return at most three candidates and show none unless all initial gates pass:

- clean chain state and lexical boundary;
- effective support of at least three;
- top conditional probability around 0.60 or higher;
- margin over the runner-up around 0.20 or higher;
- positive estimated typing utility after accounting for word length and error cost;
- candidate passes privacy/syntax filters.

Do not expose raw probability as a promise. The response should include enough evidence
for testing and diagnostics: selected context order, effective support, source blend,
score, and confidence bucket. The user-facing menu needs only the words and perhaps a
small `project`/`history` provenance badge.

## Recommended `Ctrl+T` state machine

| State | `Ctrl+T` behavior |
| --- | --- |
| No menu, cursor on a partial token | Existing structured/path/current-word/history-word dispatch, unchanged |
| Plain word-completion menu open | Accept highlighted word, clear that menu, and arm next-word chaining if the cursor is at a clean end boundary |
| Chain armed, no menu | Query the warm next-word index and open a `next_word` menu if confidence clears the gate; otherwise end the chain with no edit |
| `next_word` menu open | Accept highlighted word, insert separator + word, query again, and keep the next menu open if another candidate clears the gate |
| User moves selection in either word menu | `Ctrl+T` accepts that selected row and continues the same chain |
| Any ordinary typing, cursor movement, text revision from another source, pane switch, `Esc`, or menu-kind transition | Cancel the chain |
| Whitespace without an armed chain | Existing recent-file/artifact completion, unchanged |

This interpretation gives the requested rhythm:

```text
Ctrl+T  -> open/narrow the first word menu
Ctrl+T  -> accept selected word and arm/show the next-word prediction
Ctrl+T  -> accept predicted word and show the next prediction
Ctrl+T  -> continue while predictions remain useful
```

Restricting repeat-to-accept to the two word kinds is the safest compatibility boundary.
`Ctrl+F` and `Ctrl+L` should remain documented acceptance aliases. `Enter` must continue
to submit the prompt as typed and never accept a completion.

## Architecture and performance

Shared prediction behavior passes the project's Rust-backend litmus test: the TUI,
external editor/LSP, and future clients would all need the same tokenization, ranking,
and filtering. Implement it in a new `sase_core` domain with no Python fallback.

Suggested core surface:

```text
NextWordTrainingRowWire { text, project_key?, last_used, source, cancelled }
NextWordBuildConfigWire { max_order, limits, decay, pruning }
NextWordQueryWire { text_before_cursor, project_key?, limit }
NextWordCandidateWire { word, score, confidence_bucket, support, order, source_mix }
```

The core crate should own an immutable `NextWordIndex`; `sase_core_py` can wrap an
`Arc<NextWordIndex>` as a Python object. Python owns source discovery and schedules the
build in a real thread. When a rebuild finishes, the TUI atomically swaps the warm
snapshot after revalidating the source token and current settings.

Persist a versioned compiled cache keyed by the local shard mtimes/sizes, archive
revision/token, tokenizer version, model schema, and settings. A cold or stale cache
must degrade to “no next-word suggestion” while rebuilding—not parse history on the
keypress. Deletion/pruning and project-archive change tokens invalidate it. Bound any
shared-store lock and never resolve repositories, fetch, or prompt on the query path.

Targets:

- warmed query p95 below 2 ms and key-to-paint within the TUI's existing 16 ms target;
- no synchronous filesystem opens, JSON parsing, subprocesses, or locks on `Ctrl+T`;
- bounded memory measured on 20,000 prompts and pathological unique-token corpora;
- cold cache never delays a key event.

## Evaluation and rollout

### Offline

Create a reproducible chronological evaluator that reports, separately for global and
per-project cohorts:

- top-1 and top-3 exact match;
- precision versus coverage curve;
- gross and estimated net characters saved per shown suggestion;
- consecutive-correct run distribution;
- performance by context order, support, candidate length, language, and history size;
- model bytes, build time, cold-load time, and query p50/p95/p99.

Compare algorithms at equal coverage. Tune on one time window and report on a later
untouched window. Include prompts from projects with sparse history so the blend is not
optimized only for the largest project.

### Product metrics

Record local aggregate counters without text or candidate strings:

- `shown`, `accepted_top1`, `accepted_alternative`, `dismissed`, `typed_over`;
- accepted words and gross characters saved;
- chain lengths and chain termination reason;
- confidence bucket, model source mix, and context order;
- query/build latency and cold-cache misses.

The primary success metric should be accepted characters per invocation with a low
wrong/ignored suggestion rate. Raw suggestion count is not success.

### Tests

In addition to core scorer fixtures, add coverage for:

- punctuation, Markdown lists, code fences, Unicode, hyphenated identifiers, casing,
  and multiline prompt stacks;
- project/global blending, legacy unattributed rows, archive/local deduplication, and
  cancelled rows;
- secret/URL/e-mail/hash filtering and prompt-word deletions;
- exact `Ctrl+T Ctrl+T Ctrl+T` state transitions, selected alternatives, stale text
  revisions, cursor movement, right-hand suffixes, and preservation of whitespace file
  history;
- cold-cache and rebuild races with no event-loop I/O;
- config schema/default config/docs parity and visual completion-panel snapshots.

## Implementation sequence

1. Land the aggregate offline evaluator and project-attributed prompt-history field.
2. Implement the Rust sequence index/query API and binding; benchmark backoff variants
   on chronological data before choosing the scorer.
3. Add background build, persistent compiled cache, invalidation, and atomic warm-swap.
4. Add the `next_word` completion kind and the word-only repeated-`Ctrl+T` chain state.
5. Roll out with conservative thresholds and aggregate text-free metrics; tune for
   precision/coverage and characters saved.
6. Only then shadow-test a compact general n-gram or local neural reranker. Keep it only
   if it improves accepted characters at equal coverage and satisfies latency, memory,
   privacy, licensing, and offline requirements.

## Recommended solution

Build the feature. Use a **local, project-aware, confidence-gated 1–5-gram predictor in
`sase_core`**, blended with machine-wide user history and a current-draft cache. Reuse
the existing completion panel and off-thread history infrastructure, but introduce a
new order-preserving index. Change repeated `Ctrl+T` to accept-and-chain only for plain
word and `next_word` menus; keep structured completion and whitespace file history
unchanged. Start with support ≥ 3, top probability near 0.60, and a 0.20 lead as
calibration seeds, then tune on chronological holdout and real aggregate acceptance
metrics.

Do not make a general or remote LLM part of version 1. The local corpus already shows
enough predictable repetition to justify the feature, and selective silence is cheaper,
faster, safer, and probably more useful than generic guesses. Revisit a compact general
prior only after the personalized baseline is measured in production.
