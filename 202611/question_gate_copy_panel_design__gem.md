# Question Gate Copy Panel & Agent-Specified Copiable Items

**Date:** 2026-11-26  
**Author:** Researcher `gem`  
**Status:** Design research & recommendation  
**Governing Decisions:** `decisions:rust-core-required`, `decisions:handoffs-end-through-host-completion`

---

## 1. Executive Summary

Making specific pieces of an agent's question effortless to copy is a **strongly justified, high-leverage UX improvement**. The reference screenshot (`~/tmp/screenshots/20261126_092327.png`) illustrates the failure mode vividly: an agent asks the user to paste **seven macOS folder paths** (one containing an embedded space, `/Users/bbugyi/Library/Application Support/sase`, wrapped across terminal lines) and a **Chrome internal URL** (`chrome://settings/performance`) into System Settings and Chrome, while `UserQuestionModal`'s sole copy action (`y`) dumps the entire formatted Q&A Markdown ballot onto the clipboard. Terminal mouse selection breaks across wrapped lines and TUI borders, and the remote SSH/tmux setup (`sase tui` running on `athena`, displayed on macOS) amplifies every extra step.

The core idea — **pressing `y` inside the Questions modal opens a single-keypress copy popup featuring agent-specified copiable items plus curated question-level copy targets** — is the right direction. However, a close audit of the codebase across `sase`, `sase-core`, and `sase-telegram` justifies **four deliberate adjustments** to the initial sketch:

| # | Original Sketch | Recommended Adjustment | Why |
|---|---|---|---|
| **1** | Inline syntax inside question prose (`copy[<label>]: <text>`) | **Structured optional `"copy"` array on each question JSON object** (accepting bare strings or `{"label"?, "text"}` objects) | Inline syntax breaks on embedded spaces, commas, URLs, and multi-line commands (including the exact screenshot example); leaks raw DSL into Telegram, Mobile, `qa_markdown.py`, and follow-up prompts; and collides with SASE's exact-`question`-string matching contract (`user_question_actions.py:412`, `question_round/project.rs:413`). |
| **2** | Only agent-specified items + built-ins | **Add a conservative, high-precision auto-detection fallback** (fenced code blocks, non-trivial backtick spans, scheme URLs, SASE refs — deduplicated against agent items) | LLMs occasionally forget optional fields, and older/unprompted questions still contain URLs or commands. Restricting auto-detection to unambiguously delimited tokens preserves 100% reliability (no broken space-truncated paths). |
| **3** | Dismiss-on-copy single-pick popup only | **Default dismiss-on-copy PLUS multi-copy batch ergonomics**: session-persistent `✓` copied tracking, smart next-uncopied cursor highlight, `Space` to copy-and-stay-open, and `Tab` to pin the popup open | The screenshot requires copying **8 items sequentially** across app switches. Tracking what was already copied (`✓`) and letting the user copy without repeatedly reopening eliminates losing one's place while keeping 1-item copies fast (`y1`, `yy`). |
| **4** | Popup-only discoverability | **Subtle visual cues in `UserQuestionModal` itself**: `border_subtitle` counter (`📋 8 copiable items · y to copy`), dynamic `y=Copy (8)` footer hint, and character-preserving Rich highlight on matching spans in `#user-question-text` | Users immediately see that copiable items exist (and how many they have already copied) without cluttering the modal or breaking native mouse selection. |

**Recommended Solution in Brief:**
1. Extend the `sase questions` JSON schema with an optional `"copy"` array per question (shorthand strings or `{"label"?, "text"}` objects), normalized through one shared validator and projected into `sase-core`'s `QuestionEntryWire` (per `decisions:rust-core-required`).
2. Add a dedicated **`QuestionCopyModal`** opened by `y` from `UserQuestionModal`, styled to harmonize with `CopyAsModal` and `AgentActionChooserModal`, featuring:
   - **`FROM AGENT`** (`1`–`9`, `0`, overflow letters, plus `a` for "All N items" when ≥2),
   - **`DETECTED IN QUESTION`** (only when unambiguous non-duplicate tokens exist),
   - **`QUESTION`** (`y` for legacy All Q&A Markdown so **`yy`** preserves muscle memory, conditional `c` for Current Q&A Markdown on multi-question ballots, `t` for plain question text, `o` for highlighted option, `J` for question JSON),
   - **Path-aware middle truncation** in list rows, a **live verbatim Preview pane** at the bottom, **`✓` copied badges**, and **`Space` / `Tab` stay-open batch support**.
3. Follow up cleanly across `sase-telegram` (native `CopyTextButton` rows) and read-only notification/Agents-tab views using the same structured schema.

---

## 2. Current State Analysis

### 2.1 How Questions Flow Across the SASE Stack Today

An agent question touches six layers across three repositories:

1. **Agent Skill & CLI (`sase`)**:
   - `src/sase/macros/skills/sase_questions.md` teaches agents to run `sase questions '<json>'` with a JSON array of objects containing `question` (required string), `header` (optional string), `options` (optional list of `{label, description?}`), and `multiSelect` (optional bool).
   - `src/sase/main/questions_command_handler.py` parses JSON, runs `_validate_questions()`, and stages the handoff via `build_questions_staged_record(questions=questions)` (`src/sase/agent/_staged_handoff_records.py:70`). Per `decisions:handoffs-end-through-host-completion`, the host adopts the staged handoff after `/sase_final` settles.
2. **Gate Creation & Validation (`sase`)**:
   - `src/sase/user_question_actions.py` validates questions in `validate_user_questions()` (preserving extra keys via `dict(raw_question)` at line 342) and wraps them in a v3 gate bundle (`request.json -> payload.questions`).
   - **Critical invariant**: `question_response_schema()` (`src/sase/user_question_actions.py:412`) pins `"question": {"const": question["question"]}` in the Draft 2020-12 JSON Schema, and answer alignment in `qa_prompt.py:24`, `question_summary.py:255`, and Rust `question_round/project.rs:413` matches answers against the **exact `question` string**.
3. **Rust Core Projection (`sase-core`)**:
   - `crates/sase_core/src/question_round/wire.rs` and `project.rs` project `request.json`/`response.json`/`cancellation.json` into `QuestionRoundWire` / `QuestionEntryWire` (consumed via `src/sase/core/question_round_facade.py` and `src/sase/question_gate_turn/projection.py`).
   - `crates/sase_core/src/fleet_attention.rs` and `notifications/mobile.rs` project question notifications for mobile/gateway clients.
4. **TUI Answering Modal (`sase`)**:
   - `src/sase/ace/tui/modals/user_question_modal.py` (`UserQuestionModal`) displays a two-pane modal: left `OptionList` (`#user-question-list`), right question header, scrollable `Static(..., markup=False)` (`#user-question-text`), `_WrappingSelectionList` (`#user-question-options`), hidden `SingleLineVimTextArea` inputs (`#user-question-other-input`, `#user-question-global-input`), and footer hints.
   - Pressing `y` runs `action_copy_questions()` (lines 504–515): saves the current answer, builds full Markdown via `sase.main.qa_markdown.build_qa_markdown()`, and delivers it through `schedule_copy_delivery()` (`src/sase/ace/tui/actions/clipboard/_delivery.py`), which runs `copy_to_system_clipboard()` (`tmux load-buffer -w -` / `pbcopy` / `wl-copy` / `xclip`) off the event loop, emits Textual OSC 52 (up to 64 KiB base64), shows a top-right toast (`Copied questions & answers`), and falls back to `CopyFallbackModal` if no transport succeeds.
   - `UserQuestionModal` also inherits `CopyModeForwardingMixin` (`src/sase/ace/tui/modals/base.py:7`), forwarding `%` to ACE's global `CopyAsModal` for the underlying tab (e.g., `%s` tmux pane snapshot).
5. **Follow-Up Prompts & Read-Only Views (`sase`)**:
   - `src/sase/main/qa_markdown.py` renders `### Questions and Answers` for both `UserQuestionModal`'s `y` copy and follow-up agent prompts (`question_gate_turn/followup.py`) + SDD prompt snapshots.
   - `src/sase/ace/tui/widgets/prompt_panel/_agent_questions_render.py` renders rounds in the Agents tab `QUESTIONS` section.
   - `src/sase/ace/tui/modals/notification_modal_question.py` + `src/sase/notifications/question_summary.py` render read-only question previews in the Notification modal.
6. **Telegram (`sase-telegram`)**:
   - `src/sase_telegram/formatting.py` (`render_question_message()`, lines 1760–1810) escapes `question["question"]` verbatim for MarkdownV2 and renders inline option buttons. Notably, `sase-telegram` **already imports and uses Telegram's native `CopyTextButton`** (256-char limit) across 5 handlers (`formatting.py`, `agent_launch.py`, `agent_actions.py`, `agent_show.py`, `macro_commands.py`).

### 2.2 Existing Copy Palette & Picker Precedents in SASE

SASE already has two strong TUI modal idioms worth studying before designing this feature:

- **`CopyAsModal`** (`src/sase/ace/tui/modals/copy_as_modal.py`, `copy_as_types.py`, `styles.tcss:10977-11037`): Centered `double $primary` modal (`width: 72`, responsive `-narrow` at `<= 90` cols or `<= 32` rows), grouped `OptionList` with dim uppercase category headers (`IDENTITY`, `LOCATION`, `CONTENT`, `DATA`, `ACTIONS`), `#00D7AF` teal key column, bold label, dim single-line preview, always dismisses on selection, configured keys take precedence over `j`/`k`/`q`.
- **Modern single-keypress choosers (`AgentActionChooserModal`, `DeckPickerModal`)**: Centered modals using crisp keycap styling (`bold black on <accent>` when focused), `› ` focus pointers, section headings with optional subtitles, mouse click support, and adaptive legend truncation on narrow widths.

### 2.3 Why the Current UX Fails on the Screenshot Case

Inspecting `~/tmp/screenshots/20261126_092327.png` reveals four compounding friction points:

1. **All-or-nothing copy granularity:** `y` copies the entire Markdown ballot (`### Questions and Answers`, `> ` blockquotes, and all 4 options). Extracting a single path requires pasting into a scratchpad and slicing it manually.
2. **Broken terminal selection:** `/Users/bbugyi/Library/Application Support/sase` wraps across lines 4–5 of `#user-question-text-scroll`. Drag-selecting in tmux/Textual captures box-drawing borders, leading padding, and hard newlines.
3. **Unlabeled identical prefixes:** Paths 5–7 share `/Users/bbugyi/projects/github/...` (~35 chars of shared prefix). Even if listed naively with right-ellipsis truncation, they become visually indistinguishable.
4. **Sequential multi-copy loop across apps:** The user must copy **8 distinct strings** one by one, `Cmd+Tab`ing between the remote `athena` tmux session and macOS System Settings / Chrome, with zero visual record of which items have already been copied.

---

## 3. Critique of the Plan & Justified Requirement Adjustments

### 3.1 Is This Feature Worth Building?

**Yes.** Agent questions frequently act as human-in-the-loop checkpoints for manual GUI steps (System Settings, browser URLs, OAuth pages), local shell commands, file paths, PR/issue links, or exact identifiers. Right now, `UserQuestionModal` treats questions purely as read-and-click forms, forcing awkward workarounds whenever a question asks the user to *act* on a concrete string before answering.

### 3.2 Adjustment 1: Replace Inline `copy[label]: text` Syntax with a Structured `"copy"` JSON Field

**Critique of inline `copy[<optional_label>]: <some_text_to_be_copied>`:**

Although inline syntax looks lightweight on paper, it breaks down severely in SASE's actual architecture and on the user's own screenshot example:

1. **Delimiter ambiguity on real payloads.** Look at the screenshot text:
   > `repeat for each folder: /Users/bbugyi/.sase, /Users/bbugyi/Library/Application Support/sase, ..., /Users/bbugyi/projects/github/bobs-org/bob-mac-capture/.build. Chrome: open chrome://settings/performance, turn on Memory Saver...`
   - Where does `<some_text_to_be_copied>` terminate?
     - **Whitespace** breaks paths with spaces (`Application Support`) and shell commands (`brew install --cask ...`).
     - **Comma or period** breaks URLs, filenames (`.sase`, `.build`), commands with flags (`-o a,b`), and JSON.
     - **End-of-line** forbids inline prose mentions *and* prevents multi-line shell scripts or config blocks.
   - Adding closing delimiters (e.g., `copy[label]{text}` or ``copy[label]: `text` ``) introduces escaping rules inside JSON strings that agents are *already* single-quoting on the bash command line (`sase questions '[{"question": "..."}]'`). LLMs regularly drop or mis-escape nested DSLs.
2. **Cross-surface pollution & exact-string contract breakage.**
   - `question["question"]` is consumed verbatim by at least **six surfaces**: `UserQuestionModal`, `qa_markdown.py` (follow-up prompts & SDD archive), `notification_modal_question.py`, `_agent_questions_render.py` (Agents tab), `sase-telegram`, and `sase_gateway`.
   - Worse, `user_question_actions.py:412` enforces `"question": {"const": question["question"]}` in JSON Schema and `question_round/project.rs:413` aligns answers by exact `question` string. Stripping inline syntax on ingest mutates the agent's text; leaving it in storage forces *every* consumer (and follow-up LLM prompts!) to parse and strip a custom micro-syntax or display ugly `copy[...]:` noise.
3. **Agents already author structured JSON for `sase questions`.** Unlike freeform chat markdown, agents are *already* constructing a JSON array (`question`, `header`, `options`, `multiSelect`). Adding an optional `"copy"` field to each question object requires zero new escaping rules and validates cleanly before handoff staging.

**Recommended JSON Schema Extension:**

```json
[
  {
    "question": "Mac busy-process fixes are measured and recorded in mac/busy-processes-2026-11-26.md ... repeat for each folder: /Users/bbugyi/.sase, /Users/bbugyi/Library/Application Support/sase, ... Chrome: open chrome://settings/performance ...",
    "header": "Mac GUI",
    "copy": [
      { "label": "Spotlight: .sase", "text": "/Users/bbugyi/.sase" },
      { "label": "Spotlight: App Support", "text": "/Users/bbugyi/Library/Application Support/sase" },
      { "label": "Spotlight: .cargo", "text": "/Users/bbugyi/.cargo" },
      { "label": "Spotlight: .rustup", "text": "/Users/bbugyi/.rustup" },
      { "label": "Spotlight: bob-cli/target", "text": "/Users/bbugyi/projects/github/bobs-org/bob-cli/target" },
      { "label": "Spotlight: sase-core/target", "text": "/Users/bbugyi/projects/github/sase-org/sase-core/target" },
      { "label": "Spotlight: bob-mac-capture/.build", "text": "/Users/bbugyi/projects/github/bobs-org/bob-mac-capture/.build" },
      { "label": "Chrome Memory Saver", "text": "chrome://settings/performance" }
    ],
    "options": [
      { "label": "Done, both", "description": "Added all 7 Spotlight folders and turned on Chrome Memory Saver" }
    ]
  }
]
```

**Shorthand ergonomics (preserving `<optional_label>`):**
Each element of `"copy"` accepts **either**:
- A bare non-empty string: `"/Users/bbugyi/.sase"` → normalized to `{"text": "/Users/bbugyi/.sase"}` (no label required when the string is self-explanatory), **or**
- An object: `{"text": "...", "label": "..."}` (`text` required non-empty string; `label` optional string).

| Criterion | Inline `copy[label]: text` | Structured `"copy"` JSON Field |
|---|---|---|
| Spaces, commas, quotes, multi-line scripts | Fragile / ambiguous delimiters | **Lossless & unambiguous** (standard JSON) |
| LLM authoring reliability | Error-prone (nested DSL inside JSON inside shell quotes) | **High** (same JSON object as `options`) |
| Exact `question["question"]` invariant | Violated or requires stripping everywhere | **Preserved verbatim** |
| Telegram / Mobile / Agents tab compatibility | Leaks raw DSL unless every frontend parses it | **Clean prose everywhere + structured Copy buttons** |
| Validation at `sase questions` CLI | Hard to diagnose malformed inline spans | **Strict fail-fast schema errors before staging** |
| Token cost when string also appears in prose | Slightly shorter (~60–80 fewer tokens) | Negligible (~80 tokens); multi-line snippets need not even be repeated in prose |

> **Why not support *both* inline syntax and JSON?** Supporting two ways to declare copiable items splits skill instructions, doubles parser maintenance, and encourages agents to emit inline DSL that breaks non-TUI surfaces. Choose one clean contract: **structured `"copy"` in JSON**.

### 3.3 Adjustment 2: Layer Conservative Auto-Detection Beneath Agent Items

Even with a clean JSON field in `/sase_questions`, agents will occasionally mention a URL, SASE artifact reference, or backticked command in `question` prose without adding `"copy"`.

- **Why pure heuristics alone fail:** As `Application Support` proves, regexes cannot safely extract unquoted filesystem paths with spaces, cannot identify multi-word commands in plain prose, and cannot invent meaningful labels. Copying a silently truncated path (`/Users/bbugyi/Library/Application`) is worse than offering nothing.
- **Why a strictly high-precision secondary layer wins:** Populate an optional **`DETECTED IN QUESTION`** section *below* explicit agent items, deduplicated by exact `text` against `FROM AGENT`, extracting **only unambiguously delimited tokens**:
  1. **Fenced code blocks** (```` ```...``` ```` — inner body, stripped of opening/closing fence lines),
  2. **Non-trivial inline backtick spans** (`` `...` `` with length ≥ 4, or containing `/`, `:`, `-`, `_`, or whitespace — filtering out noise like `` `y` `` or `` `A` ``),
  3. **Explicit-scheme URLs** (`https://...`, `http://...`, `chrome://...`, `file://...` — stripping trailing sentence punctuation like `.`, `,`, `)` cleanly),
  4. **SASE artifact/prompt references** (`plan:YYYYMM/...`, `research:YYYYMM/...`, `@patch:...`, `@bead:...`, etc.).
- **Explicitly excluded from auto-detection:** Bare prose filesystem paths (too prone to silent space-truncation or false positives on slash-separated words like `Enter/S`). Agents should declare paths via `"copy"` (or wrap them in backticks).

### 3.4 Adjustment 3: First-Class Multi-Copy Batch Ergonomics

The screenshot's 8-path workflow exposes a subtle trap in single-pick popups: if `y` + `1` closes the modal every time and forgets what was copied, the user must press `y` eight times and mentally track whether they are on path #4 or #5 after each macOS `Cmd+Tab`.

**Recommended hybrid interaction model (zero cost for 1-copy, huge win for N-copy):**
- **Default behavior stays single-keypress & dismiss-on-copy** (`y` then `1`, `y` then `y`, `Enter`, or click copies and immediately returns to `UserQuestionModal`), matching `CopyAsModal` muscle memory.
- **Session-persistent `✓` tracking:** `UserQuestionModal` keeps `_copied_texts: dict[int, set[str]]` per question for the lifetime of the open modal. Reopening `y` shows a green `✓` beside every already-copied item and automatically highlights the **first uncopied `FROM AGENT` item**.
- **`Space` = Copy & stay open:** Copies the highlighted item, marks it `✓`, updates an inline confirmation flash inside the popup, and advances the cursor to the next uncopied item — without dismissing!
- **`Tab` = Pin / Stay-open toggle:** Displays a clear `📌 STAY OPEN` badge in the modal header; while pinned, *all* hotkeys (`1`–`9`), `Enter`, and mouse clicks copy, mark `✓`, advance, and keep the popup open until `Esc` or `q`.

A user facing the 8-item screenshot can now either:
- Press `y`, `Tab`, then `1` → `Cmd+Tab` → paste → `Cmd+Tab` → `2` → … → `8` → `Esc`, **or**
- Press `y`, then tap `Space` after each `Cmd+Tab` (it auto-advances 1 → 2 → … → 8 with `✓` progress!).

### 3.5 Adjustment 4: Reject Inline Numbered Copy Chips in `UserQuestionModal` (Keep the `y` Popup)

One plausible alternative is binding `1`–`9` *directly* inside `UserQuestionModal` to copy items without a popup (1 keypress instead of 2). That approach should be **rejected** for three reasons:
1. **Keymap conflict:** Other SASE gate modals (`PlanApprovalModal`, `CustomGateModal`) bind `1`–`9` to numbered decision branches (`build_gate_numbered_branch_bindings()`). Binding `1`–`9` to *copying* in `UserQuestionModal` contradicts SASE's gate keymap direction.
2. **Layout crowding:** Rendering 8 copy chips inline steals vertical space from `#user-question-text-scroll` and `#user-question-options`.
3. **Incomplete coverage:** You still need a menu for non-snippet targets (Q&A Markdown, plain question text, highlighted option, JSON, copy-all).

Two rapid keypresses (`y1`, `y2`, `yy`) keep `UserQuestionModal` clean and scale gracefully from 0 to 20+ items.

### 3.6 Dedicated `QuestionCopyModal` vs. Extending `CopyAsModal` (and `y` vs. `%`)

**Do not contort `CopyAsModal` (`src/sase/ace/tui/modals/copy_as_modal.py`).** `CopyAsModal` is tightly coupled to ACE's tab copy-mode registry (`CopyTargetCategory = Literal["Identity", "Location", "Content", "Data", "Actions"]`, single-line `OptionList`, `width: 72`, always-dismiss, `captures_snapshot` semantics). Building a dedicated **`QuestionCopyModal`** lets us cleanly support dynamic sections, path-aware middle truncation, a live multi-line Preview pane, `✓` tracking, and `Space`/`Tab` stay-open mode while reusing `schedule_copy_delivery()` and matching `CopyAsModal`'s visual language (`double $primary` border, `#00D7AF` teal keys, `-narrow` breakpoint).

**Clarifying `y` vs. `%` inside `UserQuestionModal`:**
- `UserQuestionModal` inherits `CopyModeForwardingMixin`, so `%` opens ACE's global **`Copy as…`** palette (underlying agent name, chat path, `%s` tmux snapshot).
- `y` opens **`Copy from Question`** (question-scoped items & representations).
- `QuestionCopyModal` intentionally does *not* forward `%` (swallowing unbound keys cleanly, just like `CopyAsModal` and `DeckPickerModal`), preventing awkward triple-stacked modals.

---

## 4. Questions Copy Panel Options: Usefulness Audit

Every option in `QuestionCopyModal` must earn its screen space and keycap. Below is the complete audit of candidate options:

### 4.1 Included Options

| Section | Key | Option | Payload Copied | Condition | Why It Earns Its Spot |
|---|---|---|---|---|---|
| **FROM AGENT** | `1`–`9`, `0`, then free letters | Each agent-declared `"copy"` item | Exact verbatim `item.text` | Shown when `len(copy_items) > 0` | Core use case: paths, URLs, commands, IDs, multi-line snippets. |
| **FROM AGENT** | `a` | **All N items (one per line)** | `"\n".join(item.text for item in copy_items)` | Shown only when `len(copy_items) >= 2` | Pasting a full batch of paths/IDs into a shell loop, note, or tool in one shot. |
| **DETECTED IN QUESTION** | Next free dynamic keys | Unambiguous tokens (fenced code, backticks, URLs, SASE refs) not already in `FROM AGENT` | Exact extracted token | Shown only when ≥1 non-duplicate token detected | Zero-effort fallback when agents omit `"copy"`; tagged with dim `url` / `code` / `ref` badge. |
| **QUESTION** | **`y`** | **Questions & answers (Markdown)** *(or **All questions & answers** when >1 Q)* | `build_qa_markdown(...)` (all Qs + current selections + global note) | Always shown | **Preserves existing `y` behavior via Vim-native `yy` double-tap!** Zero muscle-memory regression. |
| **QUESTION** | **`c`** | **Current question & answer (Markdown)** | `build_qa_markdown([current_q], [current_a], None)` | Shown only when `len(questions) > 1` | On a 4-question ballot, lets you share/quote just Q2 without dumping Q1, Q3, Q4. Omitted on 1-question ballots to avoid duplicating `y`. |
| **QUESTION** | **`t`** | **Question text (plain)** | Raw `current_q["question"]` | Always shown | Clean prose without `###`, `> ` blockquote prefixes, or `- [ ]` option clutter — ideal for searching, quoting, or asking another agent. |
| **QUESTION** | **`o`** | **Highlighted option** | `label` (or `label — description` if description exists); if `"Other..."` is highlighted, copies current custom "Other" draft (disabled if empty) | Always shown (disabled with reason if empty `"Other..."`) | High-value real workflow: copy a proposed option's wording/command to paste into `"Other..."` and tweak it, or look up a term mentioned in an option. |
| **QUESTION** | **`J`** | **Question JSON** | Pretty-printed JSON of `questions` (or current question? Recommend full `questions` array matching `sase questions` input) | Always shown | Debugging/reproducing question payloads without opening `d` → `]` → `y`; matches `J` across every ACE `CopyAsModal`. |

### 4.2 Explicitly Cut Options (Not Worth the Clutter)

| Candidate | Why Cut |
|---|---|
| **Question header only** | 2–3 words (e.g., `Mac GUI`); almost never worth a dedicated clipboard target. |
| **Global note only** | User just typed it themselves and can press `g` to view/edit it. |
| **All options without question** | Rarely useful detached from question context (`y` or `c` covers this better). |
| **Gate bundle path** | Diagnostic-only; `d` → `Y` in `GateDebugModal` already handles this cleanly. |
| **Tmux snapshot (`s`)** | Already accessible anywhere inside `UserQuestionModal` via `%s` (`CopyModeForwardingMixin`), which waits for modal unmount properly. Keeping `QuestionCopyModal` focused on *question content* avoids duplicating `%`. |
| **Answers-only summary** | Before submission the user is still filling out the ballot; `y` already includes checked selections. |

### 4.3 Deterministic, Collision-Free Key Allocation

A common failure mode in dynamic single-keypress menus is dynamic items colliding with navigation (`j`/`k`), exit (`q`/`Esc`), or fixed actions. We eliminate collisions permanently by partitioning the keyspace:

- **Control keys (NEVER assigned to items):** `j`, `k`, `down`, `up`, `ctrl+n`, `ctrl+p`, `q`, `escape`, `enter`, `space`, `tab`.
- **Fixed action keys (NEVER stolen by dynamic items):** `y`, `c`, `t`, `o`, `a`, `J`.
- **Dynamic item key pool (assigned in order across `FROM AGENT`, then `DETECTED IN QUESTION`):**
  1. Digits: `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `0` (first 10 items — covers >98% of questions with zero mental mapping).
  2. Overflow safe lowercase letters: `b`, `d`, `e`, `f`, `g`, `h`, `i`, `l`, `m`, `n`, `p`, `r`, `s`, `u`, `v`, `w`, `x`, `z` (up to **28** single-keypress items total).
  3. Beyond 28 items: no keycap shown; still fully accessible via `j`/`k` + `Enter`/`Space` or mouse click.

**Scope rule for multi-question ballots:** `FROM AGENT` and `DETECTED IN QUESTION` always show items for the **currently active question** (`self._current_idx`), so `1` is always the first item of the question you are reading. If other questions in the ballot also declare copiable items, the subtitle appends a subtle cue (e.g., `Q1/3 · Mac GUI · +2 items on other Qs`).

---

## 5. Visual & Interaction Design

### 5.1 Subtle, High-Craft Enhancements to `UserQuestionModal`

Before the user even presses `y`, `UserQuestionModal` should communicate copiable items gracefully without adding visual noise:

1. **In-text span styling (character-preserving, markup-safe):**
   - Replace `#user-question-text`'s plain `str` with a Rich `Text` builder that appends raw segments via `text.append(...)` (preserving the markup-safety invariant from `tests/ace/tui/test_user_question_modal_markup.py` — bracket tokens like `[/]` and `[bold]` never trigger markup parsing!).
   - When an agent-declared `item.text` occurs verbatim inside `question`, style those exact character spans in soft teal (`#5FD7AF underline`), shifting to soft green (`#5FFF87`) once copied in this session. **No characters are injected** into the prose, so native mouse selection stays clean.
2. **Non-inline declared items:**
   - If an agent declares a `"copy"` item whose `text` does **not** appear verbatim in `question` (e.g., a 4-line shell command omitted from prose to avoid repetition), render a clean muted section at the bottom of `#user-question-text-scroll` below a thin divider so the user can always inspect it before copying or answering.
3. **Border subtitle on `#user-question-text-scroll`:**
   - Zero declared items: no border subtitle (identical to today).
   - Declared items present: `📋 8 copiable · y to copy` → updates live to `📋 3/8 copied · y to copy` → `✓ 8/8 copied · y to copy`.
4. **Dynamic footer hint:**
   - Zero declared items: `[cyan]y[/cyan]=Copy`
   - Declared items present: `[cyan]y[/cyan]=Copy [dim](8)[/dim]` (or `[cyan]y[/cyan]=Copy [green](3/8 ✓)[/green]` once copying starts).

```
╭─ Question 1/1 (Mac GUI) ───────────────────────────────────────────────────────────────────╮
│  Mac busy-process fixes are measured and recorded in mac/busy-processes-2026-11-26.md      │
│  (turn 1 of plan:202611/mac_busy_process_fixes.md, projects_scope=targets). Two steps      │
│  need you in System Settings and Chrome... repeat for each folder: /Users/bbugyi/.sase,    │
│  /Users/bbugyi/Library/Application Support/sase, /Users/bbugyi/.cargo, ...                 │
│  Chrome: open chrome://settings/performance, turn on Memory Saver... What did you do?      │
╰──────────────────────────────────────────────────────────── 📋 3/8 copied · y to copy ─────╯
  (matched spans subtly tinted: copied items in #5FFF87 green, remaining in #5FD7AF teal)

Footer: Space=Toggle  j/k=Up/Down  Enter/S=Submit all  g=Global note  y=Copy (3/8 ✓)  d=Debug  q=Cancel
```

### 5.2 `QuestionCopyModal` Layout Mockup

Modeled directly on SASE's `CopyAsModal` (`double $primary` border, `$surface` background, `#00D7AF` teal keys) and `AgentActionChooserModal` (`› ` pointer, inverted keycap badge on focus, crisp section dividers), upgraded with a **live verbatim Preview pane** and **path-aware middle truncation**:

```
╔════════════════════════════════════════════════════════════════════════════════╗
║                    Copy from Question              3/8 copied                  ║
║                         Q1/1 · Mac GUI                                         ║
║                                                                                ║
║ ┌────────────────────────────────────────────────────────────────────────────┐ ║
║ │ FROM AGENT                                                       3/8 ✓     │ ║
║ │    1  ✓ Spotlight: .sase              /Users/bbugyi/.sase                  │ ║
║ │    2  ✓ Spotlight: App Support        /Users/…/Application Support/sase    │ ║
║ │    3  ✓ Spotlight: .cargo             /Users/bbugyi/.cargo                 │ ║
║ │ › [4]   Spotlight: .rustup            /Users/bbugyi/.rustup                │ ║
║ │    5    Spotlight: bob-cli/target     /Users/…/bobs-org/bob-cli/target     │ ║
║ │    6    Spotlight: sase-core/target   /Users/…/sase-org/sase-core/target   │ ║
║ │    7    Spotlight: bob-mac-capture    /Users/…/bob-mac-capture/.build      │ ║
║ │    8    Chrome Memory Saver           chrome://settings/performance        │ ║
║ │    a    All 8 items                   newline-separated · 8 lines          │ ║
║ │                                                                            │ ║
║ │ DETECTED IN QUESTION                                                       │ ║
║ │    9    plan:202611/mac_busy_process_fixes.md                         ref  │ ║
║ │                                                                            │ ║
║ │ QUESTION                                                                   │ ║
║ │    y    Questions & answers           Markdown · Q1 Mac GUI                │ ║
║ │    t    Question text                 Mac busy-process fixes are measured… │ ║
║ │    o    Highlighted option            Done, both — Added all 7 Spotlight…  │ ║
║ │    J    Question JSON                 1 question · 8 items                 │ ║
║ └────────────────────────────────────────────────────────────────────────────┘ ║
║ ┌─ Preview · 21 chars · 1 line ──────────────────────────────────────────────┐ ║
║ │ /Users/bbugyi/.rustup                                                      │ ║
║ └────────────────────────────────────────────────────────────────────────────┘ ║
║                                                                                ║
║  key copy · Space copy & stay · Tab pin · j/k move · Enter copy · q/Esc close  ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

**When pinned (`Tab` pressed — batch copy mode):**
- Header right-aligned badge switches to **`📌 STAY OPEN  3/8 ✓`** (`bold black on #FFAF00`).
- After pressing `4` (or `Space`), row `4` turns green `✓`, highlight advances to `5`, the Preview pane updates to `/Users/bbugyi/projects/github/bobs-org/bob-cli/target` (untruncated!), and the Preview border subtitle flashes **`✓ Copied: Spotlight: .rustup`** in `bold #5FFF87`.

### 5.3 Visual Details That Make It Feel Polished

1. **Path-aware middle truncation in list rows:**
   - For single-line values that look like paths (`/`-separated) and exceed the preview column width, preserve the root prefix + `…` + the last 2–3 path segments (`/Users/…/bobs-org/bob-cli/target` instead of `/Users/bbugyi/projects/github/bobs-…`).
   - For multi-line values (e.g., a 5-line shell script), show the first non-empty line collapsed + a dim badge like `· 5 lines`, while the bottom Preview pane shows up to 5 real lines (`+N more lines` if longer).
2. **Smart initial focus:**
   - If `FROM AGENT` has uncopied items, focus the **first uncopied `FROM AGENT` item** (so `y` + `Enter` or `y` + `Space` immediately copies the next item in sequence!).
   - If all `FROM AGENT` items are already copied (or none exist), focus the first `DETECTED` item if present, else `y` (`Questions & answers`).
3. **Rich toast messages:**
   - Replace generic `Copied item` with informative, bounded labels:
     - Labeled item: `Copied Spotlight: App Support (/Users/…/Application Support/sase)`
     - Unlabeled item: `Copied /Users/bbugyi/.sase`
     - Multi-line item: `Copied Migration script (5 lines)`
     - Legacy Q&A: `Copied questions & answers`
4. **Responsive `-narrow` layout (matching `CopyAsModal`):**
   - At `width <= 90 or height <= 32`, add `-narrow` class: expand container to `94%` width / `92%` max-height, shrink preview pane to 2–3 lines (or collapse preview at very short heights `height <= 22`), and use tiered footer legend trimming (`key copy · Space stay · Tab pin · Esc`).
5. **Clipboard delivery & remote SSH safety:**
   - Always route through `schedule_copy_delivery()` (`src/sase/ace/tui/actions/clipboard/_delivery.py`), anchored to the parent `UserQuestionModal` (when dismissing) or `self.app` (when pinned) so notifications and `CopyFallbackModal` never attach to a torn-down screen.
   - Respect `UserQuestionModal._input_mode`: when `"other"` or `"global"` `SingleLineVimTextArea` is active, `y` is never intercepted by the modal.

---

## 6. Recommended Architecture & Implementation Blueprint

### 6.1 Data Schema & Validation Contract

**Canonical JSON shape for each question object in `sase questions '<json>'`:**

```json
{
  "question": "Full question text (required)",
  "header": "Short sidebar label (optional)",
  "copy": [
    "bare string shorthand (optional label)",
    { "label": "Short human label (optional)", "text": "Exact verbatim text to copy (required)" }
  ],
  "options": [
    { "label": "Option label (required)", "description": "Details (optional)" }
  ],
  "multiSelect": false
}
```

**Validation & normalization rules (single source of truth):**
- Unify `src/sase/main/questions_command_handler.py:_validate_questions()` and `src/sase/user_question_actions.py:validate_user_questions()` so CLI staging and gate validation enforce the exact same rules (currently duplicated).
- `"copy"` is optional; when absent or empty, omit/treat as `[]`.
- When present, `"copy"` must be a JSON array (`list`).
- Each entry must be:
  - A string with `entry.strip() != ""` → normalized to `{"text": entry}` (preserving internal/meaningful whitespace verbatim), **or**
  - A mapping with required `"text"` (string, `text.strip() != ""`), optional `"label"` (string or `None`; stripped, omitted if blank), and no unexpected keys.
- **No change to `question_response_schema()` or `question_response.json`:** Answers remain 100% unchanged and backward-compatible.
- **No change to `qa_markdown.py`:** Follow-up prompts and SDD prompt snapshots do not echo `"copy"` metadata back to the asking agent.

### 6.2 Rust Core Boundary (`decisions:rust-core-required`)

Applying the `rust_core_backend_boundary` litmus test ("if a web app, CLI, editor integration, or another frontend would need the behavior to match the TUI, treat it as core backend logic"):

- **Belongs in `sase-core` (`crates/sase_core/src/question_round/`):**
  1. Add `QuestionCopyItemWire` (`label: Option<String>`, `text: String`) and `#[serde(default, skip_serializing_if = "Vec::is_empty")] pub copy_items: Vec<QuestionCopyItemWire>` to `QuestionEntryWire` in `wire.rs` (additive & backward-compatible on wire v1).
  2. Parse `"copy"` tolerantly (both bare string and `{label?, text}` object) in `project.rs:parse_questions()`.
  3. Implement one pure deterministic `extract_question_copy_candidates(question: &str, explicit: &[QuestionCopyItemWire])` function in `sase_core::question_round` (returning deduplicated explicit + high-precision detected items with kind tags `url` / `code` / `ref`) and expose it via `sase_core_py` (`sase_core_rs`), so TUI, Telegram, CLI, and future web/mobile frontends produce **identical** copiable item lists with zero drift.
  4. Coordinate in order per `decisions:rust-core-required`: land `sase-core` first, ratchet `sase-core-revision.txt` in `sase`, then wire Python adapters.
- **Stays in `sase` (presentation-only TUI/Python):**
  - `QuestionCopyModal` widget, CSS (`styles.tcss`), key allocation, path-aware middle truncation, Rich `Text` in-question highlighting, `✓` session state, `Space`/`Tab` stay-open UX, and `schedule_copy_delivery()` integration.

### 6.3 Cross-Surface Synergy (Immediate & Follow-Up Wins)

Because `"copy"` is structured in `request.json -> payload.questions`, other SASE surfaces benefit cleanly:

1. **Telegram (`sase-telegram`):** In `src/sase_telegram/formatting.py:render_question_message()`, for each `copy` item with `len(text) <= 256` (Telegram's `CopyTextButton` cap, already tracked as `_COPY_TEXT_MAX = 256` in `inbound_handlers/common.py:26`), render compact `📋 <label or shortened text>` `CopyTextButton` buttons (2 per row, capped to e.g. 6–8 buttons so inline keyboards stay tidy; items > 256 chars fall back to a fenced code block). Users answering from their phone get one-tap clipboard copy for free!
2. **Notification Preview (`notification_modal_question.py` + `question_summary.py`):** Parse `copy` items onto `QuestionEntry` and display a compact dim `📋 N copiable items` pill under the question preview (with optional follow-up to allow `y` from the notification preview too).
3. **Agents Tab `QUESTIONS` Section (`_agent_questions_render.py` + `projection.py`):** Mirror `copy_items` onto `QuestionEntryView`; in `FULLY_EXPANDED` fold level, optionally list non-inline copy items or a muted count indicator.

### 6.4 Phased Implementation Plan

**Phase 1 — Rust Core & Contract (`sase-core`, then `sase` pin bump):**
- `sase-core/crates/sase_core/src/question_round/wire.rs` & `project.rs`: add `QuestionCopyItemWire`, `copy_items` on `QuestionEntryWire`, tolerant `"copy"` parser, and pure high-precision auto-detector (`extract_question_copy_candidates`) with Rust unit tests covering spaces-in-paths, fenced code, backticks, `chrome://`/`https://` URLs, SASE refs, and dedup.
- `sase-core/crates/sase_core_py/`: expose binding; update `sase`'s `sase-core-revision.txt` and `src/sase/core/question_round_facade.py` + `src/sase/question_gate_turn/projection.py`.

**Phase 2 — Schema Validation & Skill Authoring (`sase`):**
- `src/sase/user_question_actions.py` & `src/sase/main/questions_command_handler.py`: unify question validation and add `"copy"` validation + normalization (bare strings and `{"label"?, "text"}` objects).
- `src/sase/macros/skills/sase_questions.md` & `docs/reference/cli/questions.md`: document `"copy"` concisely with clear guidance on when to use it (paths, URLs, commands, IDs, snippets — not ordinary prose) and an example. Deploy generated skills *after* landing via `sase skill init --force` + `chezmoi apply` (per `generated_skills.md`).

**Phase 3 — TUI `QuestionCopyModal` & `UserQuestionModal` Integration (`sase`):**
- New `src/sase/ace/tui/modals/question_copy_items.py`: pure presentation helpers (row model, collision-free key allocator, path-aware middle truncation, Rich `Text` span highlighter for `#user-question-text`, highlighted-option payload extraction).
- New `src/sase/ace/tui/modals/question_copy_modal.py`: `QuestionCopyModal` with grouped rows (`FROM AGENT`, `DETECTED IN QUESTION`, `QUESTION`), live verbatim Preview pane, `✓` copied badges, `Space` (copy & stay + advance), `Tab` (pin toggle), mouse click support, `-narrow` responsive layout, and `schedule_copy_delivery` integration.
- Update `src/sase/ace/tui/modals/user_question_modal.py`, `src/sase/ace/tui/modals/__init__.py{,i}`, `_export_table.py`, and `src/sase/ace/tui/styles.tcss`: wire `y` → `QuestionCopyModal`, persist per-question `_copied_texts`, add in-text span highlighting, non-inline item block, `#user-question-text-scroll` `border_subtitle`, and dynamic footer badge.
- Update `src/sase/ace/tui/modals/help_modal/` if question modal shortcuts are documented there.

**Phase 4 — Verification & Cross-Surface Polish:**
- Unit & Textual pilot tests:
  - Validation tests for bare strings, labeled objects, invalid/empty entries, and exact `question` string preservation.
  - `UserQuestionModal` tests: `yy` backward compatibility, `y` + `1`–`9`/`a`/`c`/`t`/`o`/`J`, `Space` copy-and-stay + cursor advance, `Tab` pin mode, `✓` persistence across reopen, `_input_mode` guard (`y` ignored while typing in `"Other"`/`"Global note"`), bracket-markup safety (`[/]`, `[bold]` in both `label` and `text`), and clipboard fallback modal.
  - Visual PNG snapshot tests under `tests/ace/tui/visual/` covering `UserQuestionModal` with highlighted spans + `QuestionCopyModal` (normal, mid-copy `3/8 ✓`, pinned, and `-narrow` 80×30).
- Optional follow-up PR in `sase-telegram` adding `CopyTextButton` rows to `render_question_message()`.

---

## 7. Summary of Recommended Solution

Build **structured agent-declared `"copy"` items** (not inline `copy[label]: text` prose syntax) backed by a **shared `sase-core` model + high-precision auto-detector**, surfaced through a dedicated, visually polished **`QuestionCopyModal`** on `y` with **`yy` backward-compatible full Q&A copy**, **`t` plain question text**, **`c` current Q&A (multi-question)**, **`o` highlighted option**, **`J` JSON**, **`a` copy all items**, a **live verbatim Preview pane**, **path-aware middle truncation**, and **`✓` / `Space` / `Tab` batch-copy ergonomics**. This directly solves both the 1-item quick-copy case and the 8-item multi-app checklist case in `20261126_092327.png` — reliably, intuitively, and cleanly across TUI, Telegram, and future SASE frontends.
