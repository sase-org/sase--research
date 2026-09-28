# Research Report: Next-Word Prompt Prediction in SASE TUI

**Author:** researcher gem (`__gem`)  
**Date:** September 2026  
**Target Repository:** [`sase`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21) / [`sase-core`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21/sase/repos/linked/sase-core)  
**Topic:** Fast "next-word" prediction in the prompt input widget triggered via `<ctrl+t>` chaining from prompt history and domain priors.

---

## 1. Executive Summary

The user proposes introducing a high-speed "next-word" prediction capability in the SASE TUI prompt input widget ([`PromptTextArea`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21/src/sase/ace/tui/widgets/prompt_text_area.py#L50)), utilizing user and project prompt history alongside general "common sense." The proposed interaction flow triggers on `<ctrl+t>`:
1. User types a prefix and presses `<ctrl+t>` to open the completion menu.
2. User presses `<ctrl+t>` again (`<ctrl+t><ctrl+t>`) to complete the selected word.
3. User continues pressing `<ctrl+t>` to consecutively predict and accept the next word, enabling rapid single-key prompt composition.

### Core Verdict
- **Is it a good idea?** Yes, but with **crucial architectural and UX adjustments**. In repetitive agentic workflows (e.g. testing, routine bug triage, running recipes, dispatching beads), prompt structures are highly repetitive. A fluent prediction engine can eliminate significant typing friction.
- **The Pitfalls**:
  1. *Blind buffer insertion*: Inserting unverified predictions directly into the text buffer destroys typing flow when predictions miss, forcing jarring backspaces.
  2. *Single-word cognitive bottleneck*: Reading and evaluating a predicted word takes ~250–350 ms. For single generic words ("the", "in", "to"), typing is often faster than reading and tapping `<ctrl+t>`. Value is unlocked when predicting **phrases, command sequences, and domain arguments**.
  3. *Keybinding collision*: Currently in SASE, `<ctrl+t>` at whitespace invokes recent file history ([`_try_file_history_completion`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21/src/sase/ace/tui/widgets/_file_completion_open.py#L521)), while inside an open menu `<ctrl+f>`/`<ctrl+l>` accepts candidates. Making `<ctrl+t>` both open, accept, and chain-predict requires a formal, unambiguous modal state machine.
  4. *Corpus Sparsity*: User prompt histories are sparse (hundreds to low thousands of entries). A raw n-gram model over history alone suffers severe cold-start failure on new projects or novel tasks.
- **The Recommended Solution**:
  1. **UX**: Use **Ghost Text (Soft Completion)** preview rather than blind text insertion. Show the predicted word in dim ghost text ahead of the cursor. Pressing `<ctrl+t>` confirms and advances the chain. In addition, allow `<ctrl+l>`/`<ctrl+f>` to accept the entire predicted *phrase*.
  2. **Model**: Implement a **Tiered Interpolated N-Gram Language Model** (Modified Kneser-Ney / Jelinek-Mercer smoothing) combining:
     - *Tier 1 (Project History)*: N-grams extracted from project-specific prompts (highest weight).
     - *Tier 2 (Global User History)*: N-grams across all user prompts.
     - *Tier 3 (Domain Common Sense Prior)*: A static, embedded corpus of ~5,000 developer, CLI, and agent prompt idioms (git verbs, testing workflows, markdown directives).
  3. **Backend Location**: In accordance with SASE Rule 1.3 (*Rust Core Backend Boundary*), implement the n-gram index, tokenization, and scoring engine in Rust within the `sase_core` crate, exposing it via `sase_core_rs` PyO3 bindings for sub-millisecond evaluation (<1 ms).

---

## 2. Analysis of Existing SASE Completion Architecture

To understand how next-word prediction fits into the system, we must examine the existing completion stack in `src/sase/ace/tui/widgets/` and `src/sase/history/`.

### 2.1 Current Completion Flow & Keybindings

In [`PromptTextAreaKeyHandlingMixin`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21/src/sase/ace/tui/widgets/_prompt_text_area_key_handling.py#L56), key dispatch operates as follows:
- **`ctrl+t` (Line 390)**:
  ```python
  if event.key == "ctrl+t":
      event.stop()
      event.prevent_default()
      self._clear_soft_completion(cancel_timer=True)
      self._try_file_completion_tab()
      return
  ```
- **Menu Active Handling (Lines 338–363)**:
  - `ctrl+n` / `down`: moves candidate selection down.
  - `ctrl+p` / `up`: moves candidate selection up.
  - `ctrl+f` / `ctrl+l`: accepts the highlighted completion candidate via `_accept_file_completion()`.
  - Notice that if `ctrl+t` is pressed while `_file_completion_active` is `True`, it is **not** handled by the active menu branch; it falls through to line 390 and re-executes `_try_file_completion_tab()`.
- **Empty Prefix Fallback**:
  - In [`_file_completion_tab.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21/src/sase/ace/tui/widgets/_file_completion_tab.py#L141):
    ```python
    token_info = self._extract_token_around_cursor()
    if token_info is None:
        return self._try_file_history_completion()
    ```
  - When the cursor is at a space (empty token prefix), `<ctrl+t>` currently pops open the `file_history` menu showing recent file references!
- **Existing Soft Completion (Ghost Text)**:
  - SASE already has a soft completion engine in [`PromptSoftCompletionMixin`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21/src/sase/ace/tui/widgets/_prompt_soft_completion.py#L58) and [`build_prompt_soft_completion()`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21/src/sase/ace/tui/widgets/prompt_completion.py#L203).
  - Soft completions display inline ghost text, accepted with `ctrl+l` (`_accept_or_build_soft_completion()`).

### 2.2 History Word Indexing (`PromptWordIndex`)

The current history word system lives in [`PromptWordIndex`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21/src/sase/history/prompt_word_index.py#L56) and [`prompt_word_ranking.py`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21/src/sase/history/prompt_word_ranking.py#L1):
- **Bag-of-Words Model**: It indexes unique words per prompt and stores document frequency and postings. It ranks candidate words matching a typed prefix by a composite score:
  $$\text{Score} = 0.50 \cdot \text{Relation} + 0.30 \cdot \text{Recency} + 0.20 \cdot \text{Frequency}$$
- **Lack of Sequential Context**: The current index computes *co-occurrence* (words that frequently appear together in the same prompt), but **discards word order**. It cannot determine whether word $B$ immediately follows word $A$.
- **Short Word Exclusion**: `PromptWordIndex` uses a default `word_min_length: int = 5` and filters out stopwords (`CONTEXT_STOPWORD_RATIO = 0.20`).
  - *Critical Insight*: While skipping short words and stopwords is appropriate for prefix completion of long identifiers, it is **fatal for next-word prediction**. In natural language and CLI syntax, words like `to`, `in`, `for`, `git`, `pr`, `run`, `add`, `fix` are the syntactic backbone of prompts.

---

## 3. Comprehensive Critique of the Proposed Plan

### 3.1 The Value Proposition: Where Next-Word Prediction Succeeds

| Use Case | Example Prompt | Prediction Utility |
| :--- | :--- | :--- |
| **Command & Tool Invocations** | `just check...` $\rightarrow$ `just check-full` | High (deterministic command syntax) |
| **Common Agent Directives** | `Please verify that...` $\rightarrow$ `all unit tests pass` | High (frequently repeated idioms) |
| **File and Path Contexts** | `in file src/sase/...` | High (tight local collocations) |
| **Repetitive Workflows** | `sase artifact create -p ... -l ...` | High (parameter sequence flags) |

Developers frequently type identical phrasing when directing coding agents. Accelerating these transitions with low cognitive effort is genuinely valuable.

### 3.2 The Friction Points & Risks

#### 1. Single-Word vs. Phrase Granularity (The Cognitive Bottleneck)
In HCI cognitive research (e.g., Card, Moran, & Newell's GOMS model), the human cycle for perceptual verification (reading text on screen and verifying correctness) takes roughly 200–350 ms. Fast typists produce 60–100 words per minute, or 100–160 ms per keystroke.
- If a user has to press `<ctrl+t>` 6 times to write *"fix the bug in the test"*:
  - User reads "fix" $\rightarrow$ presses `<ctrl+t>` (300 ms).
  - User reads "the" $\rightarrow$ presses `<ctrl+t>` (250 ms).
  - User reads "bug" $\rightarrow$ presses `<ctrl+t>` (300 ms).
  - Total elapsed time: ~1.8 seconds.
  - A fast typist can type those 24 characters in ~1.5 seconds without breaking flow.
- **Adjustment**: Next-word prediction must not be restricted to single isolated words. When the model has high conditional probability ($P(w_i | w_{<i}) > \tau$), it should support **multi-token / phrase completion** or allow chaining to complete the entire phrase via `<ctrl+l>` / `<ctrl+f>`.

#### 2. Blind Buffer Insertion vs. Ghost Text
The user proposal states: *"triggered using `<ctrl+t>` after using `<ctrl+t><ctrl+t>` to complete the first / selected word in the completion menu. This way they can just keep hitting `<ctrl+t>` if the next-words that we guess are correct."*
- If pressing `<ctrl+t>` immediately inserts text into the document buffer without the user seeing it beforehand:
  - If the prediction is **wrong**, the user has unwanted characters in their buffer. They must stop, press Backspace (or `Esc u i` in Vim mode), and resume typing.
  - Even a 20% error rate makes blind insertion intolerable.
- **Adjustment**: The next word must be previewed as **Ghost Text (Soft Completion)** before insertion! Pressing `<ctrl+t>` commits the ghost text and projects the subsequent ghost word.

#### 3. State Machine & Collision with Empty-Prefix `<ctrl+t>`
In the current implementation:
1. Typing `re` + `<ctrl+t>`: opens completion menu.
2. If user presses `<ctrl+t>` again: currently re-runs `_try_file_completion_tab()`, which does not accept!
3. If cursor is at a space (e.g. `reproduce `), pressing `<ctrl+t>` invokes `_try_file_history_completion()`.
- If `<ctrl+t>` at a space triggers next-word prediction instead, how does a user ever trigger file history?
- **Adjustment**: Create a transient **`ChainedPredictionState`**.
  - If `<ctrl+t>` was just used to complete a word, enter `ChainedPredictionState`.
  - In `ChainedPredictionState`, the next `<ctrl+t>` advances the prediction chain.
  - If the user moves the cursor, types regular text, or presses Escape, the chained state drops.
  - Stand-alone `<ctrl+t>` at a space can either show next-word ghost text or fall back to file history if no prior word exists on the line.

---

## 4. Deconstructing "Common Sense": What Models Can Work Fast?

The prompt asks: *"using the user' / project's prompt history (and maybe just common sense?--think hard about how to make this work). This would need to be fast..."*

What does "common sense" actually mean in a fast, keystroke-level TUI assistant?

### 4.1 Evaluation of Technical Approaches

```
+-------------------------------------------------------------------------------------+
| Approach                  | Latency  | Memory   | Offline? | Quality / Common Sense |
+-------------------------------------------------------------------------------------+
| 1. Local SLM (ONNX/GGUF)  | 30-100ms | 300-800MB| Yes      | High semantic fluency  |
| 2. Cloud LLM Streaming    | 300-1500ms| Negligible| No     | Superior, but too slow |
| 3. Unigram Bag-of-Words   | < 0.5ms  | < 5MB    | Yes      | Zero sequential sense  |
| 4. Tiered N-Gram with     | < 1.0ms  | 10-20MB  | Yes      | Excellent for idioms,  |
|    Kneser-Ney Smoothing   |          |          |          | commands, syntax       |
+-------------------------------------------------------------------------------------+
```

#### Approach 1: Tiny Local Neural Model (SLM via ONNX Runtime / `llama.cpp`)
- *Concept*: Run a quantized ~100M–500M parameter model (e.g. `SmolLM-135M-Instruct` or `Qwen2.5-0.5B` quantized to INT4) embedded in the process.
- *Why it fails the requirement*:
  - **Latency**: Even on modern hardware, running inference for 1 token through ONNX or `llama.cpp` on CPU takes 25–60 ms. In a Textual TUI running at 60 FPS (16.6 ms frame budget), this introduces perceptible stutter on keystrokes.
  - **Memory & Packaging**: Bundling a 150–400 MB model file in SASE distributions bloats installation, slows CI, and consumes significant memory across multiple workspace instances.
  - **Drift**: Without fine-tuning, SLMs tend to hallucinate conversational prose rather than terse CLI/prompt directives.

#### Approach 2: Cloud / Background LLM
- *Why it fails*: Network roundtrip alone is 100–300 ms, plus inference time (300–800 ms). It cannot serve a synchronous `<ctrl+t>` keystroke chain.

#### Approach 3: Pure Unigram Co-occurrence (Current `PromptWordIndex`)
- *Why it fails*: As established, bag-of-words co-occurrence cannot predict word order. It knows "test" and "flake" co-occur, but not whether "flake" follows "investigate" or "reproduce".

#### Approach 4: Tiered Statistical N-Gram Model with Smoothing (The Recommended Winner)
- *Concept*: A multi-tier N-gram language model (Trigrams + Bigrams + Unigrams) with **Modified Kneser-Ney Smoothing** or **Jelinek-Mercer Interpolation**.
- *Why it succeeds*:
  - **Sub-millisecond Latency**: Querying a trie or hash map of n-grams takes < 0.5 ms in Python, and < 0.05 ms in Rust.
  - **Zero Dependency / Low Footprint**: In-memory data structures require ~10–20 MB for 100,000 n-grams.
  - **Project & Recency Adaptation**: Dynamic weighting gives immediate priority to commands used in the active project within the last hour or day.

### 4.2 How to Operationalize "Common Sense" Without a Neural Net

"Common sense" in software engineering prompts is not philosophical reasoning; it is **collocational frequency, grammatical coherence, and domain grammar**:

1. **Tier 1: Project-Specific History (Weight: 0.50)**
   - Extracted from prompts associated with the current project (via [`PromptHistoryProjectCatalog`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21/src/sase/history/prompt_history_project_filter.py#L81) and VCS tags).
   - Captures local symbols, branch names, file paths, and project-specific tasks (`just check-full`, `sase repo open sase-core`).

2. **Tier 2: User-Global Prompt History (Weight: 0.30)**
   - Extracted from all historical shards in `~/.local/state/sase/prompt_history/`.
   - Captures personal phrasing, preferred instructions ("Please ensure", "Do not modify", "Run tests synchronously").

3. **Tier 3: Domain Prior / "Developer Common Sense" Table (Weight: 0.20)**
   - A static, compact compiled table (~5,000 entries) embedded directly in the binary/package.
   - Contains universal software development collocations:
     - *Git/CLI commands*: `git commit -m`, `git status --short`, `cargo test --`, `pytest -v`, `npm run build`.
     - *Directive phrasing*: `fix the issue where`, `reproduce the error in`, `add unit test for`, `refactor the implementation of`, `ensure backward compatibility with`.
     - *Prepositional / functional bridges*: `according to`, `in order to`, `under the directory`, `as well as`.
   - **Why this is critical**: This solves the **cold-start problem**. On day 1 of a new project, the engine already feels remarkably smart because it anticipates standard developer sentence structures.

---

## 5. Recommended Adjustments to the Requirements

Before writing code or finalizing specifications, the following adjustments to the user's initial proposal are strongly advised:

### Adjustment 1: Ghost Text (Soft Completion) Preview over Blind Mutation
- **User Proposal**: Pressing `<ctrl+t>` blindly writes the predicted word into the buffer.
- **Adjustment**: When a prediction is available, render it as **dim ghost text** after the cursor.
  - Pressing `<ctrl+t>` accepts the ghost word, appends a space, and displays the next ghost word.
  - Pressing any normal typing key ignores the ghost text and types normally.
  - Pressing `Escape` dismisses the ghost text.

### Adjustment 2: Word-Level AND Phrase-Level Acceptance
- **User Proposal**: Only single next-word advancement via `<ctrl+t>`.
- **Adjustment**: While `<ctrl+t>` advances one word at a time, provide an accelerator (e.g. `<ctrl+l>`, `<ctrl+f>`, or `End`) that accepts the **entire multi-word prediction sequence** (up to 3–5 words).
  - Example: Cursor after `reproduce `. Ghost text shows `the flaky test in CI`.
  - Tapping `<ctrl+t>` accepts `the ` (ghost text moves to `flaky test in CI`).
  - Pressing `<ctrl+l>` accepts the entire phrase `the flaky test in CI`.

### Adjustment 3: Inclusion of Short Words in N-Gram Corpus
- **User Proposal**: Use existing prompt history.
- **Adjustment**: Unlike `PromptWordIndex` (which enforces `min_length >= 5`), the next-word n-gram tokenizer must index words down to length 1 (including `a`, `to`, `in`, `on`, `rm`, `ci`, `pr`, `git`).

### Adjustment 4: Explicit State Machine for `<ctrl+t>`
- **User Proposal**: `<ctrl+t>` opens menu, `<ctrl+t><ctrl+t>` accepts, then subsequent `<ctrl+t>` chains.
- **Adjustment**: Formalize four states in [`PromptTextAreaKeyHandlingMixin`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_21/src/sase/ace/tui/widgets/_prompt_text_area_key_handling.py):
  1. `IDLE` (cursor inside word): `<ctrl+t>` opens manual completion menu (unchanged).
  2. `MENU_OPEN`: `<ctrl+t>` accepts the highlighted candidate (closing the menu and inserting word + space), and immediately transitions to `CHAINED_PREDICTION`.
  3. `CHAINED_PREDICTION`: Ghost text preview of next word is active. `<ctrl+t>` commits previewed word, advances cursor, and projects next word.
  4. `WHITESPACE_STANDALONE`: Cursor at whitespace without prior chain:
     - If preceded by non-space text on the same line: show next-word ghost text.
     - If line is blank: trigger `_try_file_history_completion()` (file reference history).

---

## 6. Recommended Architecture & Implementation Plan

### 6.1 Architectural Boundary (Rule 1.3 Compliance)

In accordance with SASE Rule 1.3:
> *"Shared backend and domain behavior belongs in the `sase_core` crate of the linked `sase-core` repo... Use this litmus test: if a web app, CLI, editor integration, or another frontend would need the behavior to match the TUI, treat it as core backend logic."*

Next-word prompt prediction is valuable not just in the Textual TUI, but also in `sase-nvim` (the Neovim plugin via LSP) and potential CLI interactive modes. Therefore:
- **Rust Core (`sase-core` / `sase_core`)**:
  - Module: `sase_core::prompt_prediction`.
  - Implements: N-gram tokenization, inverted n-gram trie, Kneser-Ney scoring, and fast serialization.
  - Exposed via `sase_core_rs` PyO3 bindings.
- **Python TUI Adapter (`sase`)**:
  - Module: `sase.history.prompt_predictor`.
  - Wraps the Rust engine and handles cache warming during TUI startup.
  - Interacts with `PromptTextArea` and `PromptSoftCompletionMixin` to render ghost text and manage keypress events.

```
+-----------------------------------------------------------------------------------+
| Textual TUI (Python)                                                              |
|   PromptTextAreaKeyHandlingMixin                                                  |
|     |_ on_key('ctrl+t') -> handles State Machine (MENU_OPEN, CHAINED_PREDICTION)  |
|   PromptSoftCompletionMixin                                                       |
|     |_ renders ghost text at cursor                                               |
+------------------------------------------+----------------------------------------+
                                           | calls via PyO3
+------------------------------------------v----------------------------------------+
| Rust Core Backend (sase-core / sase_core::prompt_prediction)                       |
|   +-----------------------+  +-----------------------+  +-----------------------+ |
|   | Project N-Grams (T1)  |  | User History (T2)     |  | Static Priors (T3)    | |
|   +-----------------------+  +-----------------------+  +-----------------------+ |
|                             \             |             /                         |
|                              Interpolation & Smoothing                            |
|                                           |                                       |
|                               Next-Word Scored Candidates                         |
+-----------------------------------------------------------------------------------+
```

### 6.2 Data Structures & Scoring Algorithm

#### Tokenizer
Tokens are extracted using an identifier/word regex supporting CLI flags and hyphenated terms:
```regex
r"[\w\-]+|#[\w\-]+|@[\w\-:]+"
```
Leading/trailing punctuation is stripped, but hyphenated flags (`--short`, `-p`) and xprompt tags (`#audit`) remain distinct tokens.

#### Scoring Formula (Interpolated Kneser-Ney with Domain Fallback)
For context words $(w_{t-2}, w_{t-1})$:
$$P(w_t | w_{t-2}, w_{t-1}) = \alpha \cdot P_{trigram}(w_t | w_{t-2}, w_{t-1}) + \beta \cdot P_{bigram}(w_t | w_{t-1}) + \gamma \cdot P_{unigram}(w_t)$$
Where the counts $C(w)$ are weighted by project recency:
$$C_{eff}(n\text{-gram}) = C_{proj}(n\text{-gram}) \cdot \omega_{proj} + C_{user}(n\text{-gram}) \cdot \omega_{user} + C_{prior}(n\text{-gram}) \cdot \omega_{prior}$$
- $\omega_{proj} = 3.0 \cdot e^{-\Delta t / 7\text{ days}}$
- $\omega_{user} = 1.0 \cdot e^{-\Delta t / 30\text{ days}}$
- $\omega_{prior} = 0.5$ (constant base prior)

#### Multi-Word Phrase Expansion
If the top candidate $w_t$ has high confidence ($P(w_t | \dots) \ge 0.65$), the engine greedily looks ahead:
$$(w_{t-1}, w_t) \rightarrow w_{t+1}$$
If $P(w_{t+1} | w_t) \ge 0.60$, the engine builds a phrase candidate:
$$\text{display\_phrase} = w_t + " " + w_{t+1}$$
The user can tap `<ctrl+t>` to take $w_t$, or `<ctrl+l>` to take the full phrase.

### 6.3 State Machine Implementation Details

In `_prompt_text_area_key_handling.py`:
```python
# Pseudo-logic for the new key handling state machine
if event.key == "ctrl+t":
    event.stop()
    event.prevent_default()
    
    # Case 1: Completion Menu is Open
    if self._file_completion_active:
        # Accept the highlighted candidate
        self._accept_file_completion()
        # Immediately transition to chained prediction
        self._enter_chained_prediction_state()
        return

    # Case 2: In Chained Prediction State (Ghost text visible)
    if self._chained_prediction_active and self._has_active_ghost_word():
        self._commit_ghost_word()
        self._advance_chained_prediction()
        return

    # Case 3: Standard Insertion Mode
    if self._has_word_under_cursor():
        # Regular prefix completion
        self._clear_soft_completion(cancel_timer=True)
        self._try_file_completion_tab()
    else:
        # At whitespace: trigger next-word prediction if preceding context exists
        if self._can_predict_next_word_at_cursor():
            self._trigger_next_word_soft_prediction()
        else:
            self._try_file_history_completion()
    return
```

---

## 7. Comparison Matrix: Proposed vs. Recommended Approach

| Dimension | User Proposal | Recommended Solution | Rationale |
| :--- | :--- | :--- | :--- |
| **Output Presentation** | Direct text insertion into buffer | Inline Ghost Text (Soft Completion) | Prevents buffer corruption on incorrect guesses. Non-disruptive. |
| **Acceptance Granularity** | Single word only | Word (`<ctrl+t>`) + Phrase (`<ctrl+l>`) | Overcomes the ~300ms perceptual bottleneck for multi-word idioms. |
| **Model Architecture** | History only + "common sense" | 3-Tier Interpolated N-Gram (Project + User + Domain Prior) | Guarantees <1ms latency, solves cold start, deterministic. |
| **Keybinding Flow** | Overloaded `<ctrl+t>` sequence | Formal 4-state prediction machine | Resolves collisions with file history and menu navigation. |
| **Vocabulary Bounds** | Undefined (inherits `word_min_length: 5`) | Custom tokenizer including 1–4 char tokens | Essential for natural language syntax (`to`, `in`, `fix`, `git`). |
| **Backend Boundary** | Unspecified | Rust in `sase-core`, Python TUI bindings | Rule 1.3 compliance; reusable in Neovim plugin and CLI. |

---

## 8. Actionable Implementation Roadmap

1. **Phase 1: Rust Core N-Gram Engine (`sase-core`)**
   - Create `sase_core::prompt_prediction` with trie-based n-gram index and Kneser-Ney smoothing.
   - Embed static domain prior table (`src/resources/developer_priors.json`).
   - Expose `PromptPredictor` through PyO3 bindings in `sase_core_rs`.
2. **Phase 2: History Ingestion & Caching (`sase.history`)**
   - Hook into prompt store loading during TUI startup (`_startup_history_words.py`).
   - Extract sequential tokens from loaded prompt shards, tagged by project ref.
3. **Phase 3: TUI Interaction & Ghost Text UI (`sase.ace.tui`)**
   - Update `PromptSoftCompletionMixin` to render next-word ghost text at word boundaries.
   - Implement the `ChainedPredictionState` in `PromptTextAreaKeyHandlingMixin`.
   - Wire `<ctrl+t>` to commit word and advance; wire `<ctrl+l>` / `<ctrl+f>` to accept full phrase.
4. **Phase 4: Telemetry & Benchmark Verification**
   - Measure prediction query latency (target: $\le 1.5$ ms).
   - Add unit tests verifying state transitions, backoff handling, and key disambiguation.

---

## 9. Conclusion

The user's vision of tapping `<ctrl+t>` to fluidly draft prompts is highly achievable and addresses real repetitive typing friction in agentic engineering. However, implementing it as direct, blind single-word insertion over raw prompt history would lead to frequent errors, slow cognitive verification, and keybinding conflicts. 

By refining the requirements to use **inline ghost text preview**, **dual word/phrase acceptance**, and a **three-tier interpolated statistical model implemented in the Rust backend (`sase-core`)**, SASE can achieve lightning-fast (<1 ms), highly intelligent prompt completions that feel like genuine "common sense" without the bloat, cost, or latency of neural language models.
