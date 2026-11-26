# Questions Gate Copy Panel — Design Research (cld)

_Researcher: cld · 2026-11-26 · Scope: the `y` copy experience inside the TUI's User
Questions modal, how agents mark text as copyable, and what else the new copy panel
should offer._

---

## TL;DR

- **Good idea. Build it.** The motivating screenshot isn't a one-off. In 185 real
  questions on athena (2026-07-18 → 2026-11-26), **35% contain at least one obvious
  copy candidate** (a command in backticks, a filesystem path, or a URL). **22% contain
  two or more.** Today the only way to get one of them out is mouse selection inside a
  bordered, word-wrapped Textual modal running over SSH and tmux.
- **Change the agent-side syntax.** Don't use an inline `copy[<label>]: <text>` marker.
  Add a **structured, optional `copy` array to each question's JSON**. Each entry is
  either a bare string or `{ "label", "text" }`. Questions are already structured JSON.
  An inline marker would leak into every other renderer (Telegram, mobile, the
  successor agent's Q&A prompt, the Agents-tab QUESTIONS deck). A structured field
  degrades gracefully and gives Telegram native copy buttons almost for free.
- **`y` opens a "Copy" panel**, built by generalizing the existing `CopyAsModal`
  ("Copy as…") palette so it keeps the TUI's established look. The panel has three
  sections:
  1. **Snippets** — agent-declared text, keys `1`–`9`, `0`, then letters.
  2. **Found in text** — a conservative auto-detected fallback: backtick spans and
     URLs only, never bare paths.
  3. **Question** — fixed rows: `t` this question (Markdown), `a` all snippets (one
     per line), and `y` everything (today's Q&A Markdown). So **`yy` keeps the current
     behavior**.
- **Built for the "paste seven paths" workflow.** Copied rows get a ✓. The cursor
  reopens on the next row not yet copied, so `y ⏎ … y ⏎` walks the checklist in order.
  The toast names exactly what was copied.
- **Put normalization in `sase-core`, not the TUI.** This covers string/object forms,
  default labels, trailing-newline trimming, control-character rejection, dedupe, and
  detection. The CLI validator, TUI, Telegram, and mobile must all agree on the list
  (`decisions:rust-core-required`, Rust core boundary rule).

---

## 1. What exists today (ground truth)

| Piece | Where | Notes |
| --- | --- | --- |
| Question modal | `src/sase/ace/tui/modals/user_question_modal.py` | Two panes. `y` → `action_copy_questions` (line 504) copies **all questions + current answers as Markdown** with the toast "Copied questions & answers". The question text renders as a plain `Static(markup=False)`. |
| Q&A Markdown | `src/sase/main/qa_markdown.py` | `build_qa_markdown` / `build_merged_qa_markdown` are shared with the successor-agent prompt, so they can't drift. |
| Clipboard delivery | `src/sase/ace/tui/actions/clipboard/_delivery.py` | `schedule_copy_delivery` runs off the event loop. It tries the system clipboard (`tmux load-buffer -w -` first, then `pbcopy` / `wl-copy` / `xclip`), then OSC 52 (64 KiB base64 cap), then a selectable-text fallback modal. It already toasts "Copied {label}" or "(OSC 52)". |
| "Copy as…" palette | `src/sase/ace/tui/modals/copy_as_modal.py`, `copy_as_types.py`, CSS at `styles.tcss:10981` | Grouped rows (`Identity/Location/Content/Data/Actions`), a one-key accelerator per row, a dim preview, disabled rows with reasons, a `-narrow` responsive class, and an "Unknown copy key (…)" toast. **This is the visual language the new panel should reuse.** |
| Modal-local palette precedent | `artifact_files_modal_copying.py:action_open_copy_as` | The artifact-files modal already opens `CopyAsModal` from inside another modal (on the `%` copy prefix). So stacking a palette over a modal is a proven path. |
| One-key selectors | `artifact_files_modal_rendering.py:28` `artifact_file_selector_keys` | `1234567890` then letters, skipping reserved keys. The docs describe this as "`1`-`0`, then letters". Snippet keys should follow the same scheme. |
| Question schema | `src/sase/main/questions_command_handler.py:_validate_questions`, `src/sase/user_question_actions.py:validate_user_questions` | Both are Python. Both **pass unknown keys through untouched**, so a new `copy` field already survives the round trip to `request.json` → `payload.questions[i]`. |
| Core projection | `sase-core/crates/sase_core/src/question_round/{wire,project}.rs` | Tolerantly parses `header/question/options/multiSelect` for the Agents-tab QUESTIONS deck. It has no notion of copy items yet. |
| Telegram | `sase-telegram/.../formatting.py:render_question_message` | Renders the question text escaped in MarkdownV2. The plugin **already uses `CopyTextButton`** elsewhere (`formatting.py:2101`, `agent_launch.py:344`), with `_COPY_TEXT_MAX = 256` (`inbound_handlers/common.py:26`). |
| `%` in the question modal | `CopyModeForwardingMixin` (`modals/base.py:7`) | Forwards `%` to the *app's* copy mode, which targets whichever agent row is selected underneath, not the question. |
| `y` / `Y` convention | ~20 modals | `y` = the modal's primary copy, `Y` = copy path. A `y` that opens a chooser is new, but it fits: the chooser's own `y` row keeps "primary copy" one keypress away (`yy`). |

**Transport implication:** in the screenshot, the TUI runs on athena inside tmux inside
a Mac terminal ("bas athena"). Anything that *opens* a URL or file would open it on
athena, the wrong machine. The clipboard (tmux `-w` / OSC 52) is the one channel that
reliably reaches the Mac where the user acts. That is a strong reason this feature
should be **copy-centric** and not "open"-centric.

---

## 2. Evidence: how often do questions contain copyable text?

I pulled every retained question bundle (`~/.sase/interaction_requests/question/*/request.json`):
**athena: 124 bundles / 185 questions** (2026-07-18 → 2026-11-26) and **apollo: 36
bundles / 41 questions**. I ran simple regexes over `payload.questions[*].question` and
the option text. All reads were local or read-only over Tailscale SSH, and all analysis
scripts lived outside the repos.

| Signal (athena, n = 185 questions) | Questions | Items |
| --- | ---: | ---: |
| Any candidate (backtick span ≥4 chars with alnum, multi-segment path, or URL) | **64 (35%)** | — |
| ≥2 candidates in one question | **41 (22%)** | — |
| Backtick spans (≥4 chars, alnum) | 51 (28%) | 147 raw |
| Multi-segment `/…/…` or `~/…` paths outside backticks | 14 (8%) | — |
| URLs (`https://…`, `chrome://…`) | 7 (4%) | 8 |
| Backtick spans in **option** text | 23 (12%) | 78 |
| Max candidates in one question / p90 | 11 / 3 | only 1 question > 9 |

Apollo gives the same picture at smaller scale: 14 of 41 questions (34%) contain
backtick spans.

**What the candidates are.** Mostly runnable commands (`caffeinate -dims`,
`tailscale ping -c 5 athena`, `gh api repos/…/SASE_RELEASE_TOKEN`,
`ob sync-status --path /home/bryan/bob`, `just install-all`), file paths, error strings
worth searching (`release-please failed: Bad credentials`), and URLs (PyPI publishing
settings, GitHub secrets pages, PRs, a Tailscale login link, `chrome://settings/performance`).

**Precision of naive auto-detection is poor; the motivating example proves it.** The
question in the screenshot lists seven paths in prose. A path regex gets **two of the
seven wrong**:

- `/Users/bbugyi/Library/Application Support/sase` stops at the space and becomes
  `/Users/bbugyi/Library/Application`.
- `/Users/bbugyi/projects/github/bobs-org/bob-mac-capture/.build.` picks up the
  sentence-ending period.

In the rendered modal, that first path is also **word-wrapped across two lines**
("…/Library/Application" | "Support/sase"). So mouse selection and terminal hint tools
(kitty hints, tmux-thumbs) fail at exactly the same spot.

A filtered backtick detector does better. I kept spans that contain whitespace, `/`,
`://`, or a file extension, and dropped Markdown-ish markers (`#task`, `[ ]`, `**…**`).
That keeps 81 spans and drops 66. Eyeballed, about **80% of kept spans are genuinely
copy-worthy**. The remaining ~20% are schema fragments (`pages/`, `events/`) and UI
strings. Most of what's dropped is right to drop, but a few useful IDs fall out (a
32-hex hash, `sase-ae.6`).

**Conclusions from the data**

1. The need is broad (about 1 in 3 questions), not a Mac-GUI corner case.
2. Agent-declared snippets are necessary for reliability. Heuristics break on real
   paths.
3. A *conservative* detector still pays for itself as a fallback when the agent forgot
   to declare snippets (and for old rounds). It must stay restricted to unambiguously
   delimited spans (backticks, URLs) and visually separated from curated rows.

---

## 3. Critique of the plan

### 3.1 Is this a good idea?

**Yes.** It removes a real, frequent, high-friction step, and it sits on top of
infrastructure that already exists: `CopyAsModal`, selector keys, and robust clipboard
delivery. The main risks are manageable:

| Risk | Mitigation |
| --- | --- |
| Agents forget to declare copyables | Skill guidance with a worked example, a CLI that validates the field, and the "Found in text" fallback |
| `y` stops being a one-key copy | `yy` = the old behavior; every copy is still exactly 2 keys |
| Schema drift across TUI / Telegram / mobile | One normalizer in `sase-core` that every surface calls |
| Clutter makes the panel ugly | Strict detection filter, cap of 5 detected rows, built-ins limited to 3 |
| Pasting a command auto-executes or carries escape codes | Trim trailing newlines; reject control characters at validation |

### 3.2 What I'd do differently from the proposal

1. **Structured field, not inline markup** (§4.1). This is the biggest change.
2. **Design for every surface, not just the TUI.** The same declared snippets should
   become Telegram `CopyTextButton`s and Agents-tab deck copy targets later. That's
   only cheap if the data is structured and core-normalized.
3. **Optimize for sequences, not single copies.** The motivating workflow is "paste
   path → Return → repeat ×7". ✓ marks plus cursor-on-next-uncopied make that a
   no-thinking loop.
4. **Teach agents to need less copying.** Skill guidance should say: when a manual step
   can be one shell command, offer that one command as a snippet instead of N GUI
   pastes. The panel makes good questions better. It shouldn't encourage long manual
   checklists.

### 3.3 Prior art considered

- **Terminal hint tools** (kitty `hints` kitten, tmux-thumbs / tmux-fingers, Vimium-style
  labels). They overlay key labels on regex matches in visible text and copy the pick.
  The user could get part of this today with no sase changes. They fail here because
  they see the *rendered, wrapped* modal, so "Application Support/sase" is split across
  lines. They also can't know labels or text that isn't on screen, and they can't
  offer "this question as Markdown". The panel should borrow their
  one-keypress-per-target ergonomics.
- **SASE's own hint mode** (file hints in the Agents tab, `[N]` markers): the same
  idea. Its numbering convention (`1`–`0`, then letters) is reused below.
- **Telegram `CopyTextButton`** (Bot API `InlineKeyboardButton.copy_text`, 1–256
  characters per library docs, already used by sase-telegram): the natural mobile
  rendering of declared snippets.

---

## 4. Design decisions

### 4.1 How agents declare copyable text

| Option | Verdict | Why |
| --- | --- | --- |
| **A. Inline `copy[label]: text` in the question string** (proposed) | ✗ Reject | (1) Unclear boundaries: where does `text` end? Line-based markers can't sit mid-sentence and can't hold multi-line text. (2) It leaks into every renderer that doesn't parse it: Telegram, mobile, successor-agent Q&A prompt, QUESTIONS deck, inbox previews. Each would need a stripper, i.e. core work anyway, and any missed surface shows raw markup. (3) It needs escaping rules for `]` and a literal `copy[`. (4) It mixes presentation into content the successor agent reads back. |
| **A′. Inline span markup like `{{copy:…}}`** | ✗ Reject | Fixes the boundaries, keeps every other problem in A. |
| **B. Backticks are the contract** ("wrap anything copyable in backticks") | ◐ Fallback only | Markdown-native and already used in 28% of questions. But backticks also mean "identifier/emphasis" (`#task`, `parent`, `[ ]`). My filter discards 66 of 147 spans (45%) as markers or identifiers, and about 20% of the spans it keeps are still noise. There are no labels, and paths with spaces are awkward. Good as *detection*, not as the contract. |
| **C. Auto-detect paths/URLs/commands** | ◐ Fallback only | Zero agent effort, but it broke on 2 of 7 paths in the motivating example. URLs and backtick spans are fine; bare paths are not. |
| **D. Structured `copy` field on each question** | ✓ **Adopt** | Exact bytes and labels, multi-line OK, validated at `sase questions` time with precise errors, ignored safely by any renderer that doesn't know it, maps directly to Telegram copy buttons. The one cost is duplication: the value appears in prose and in `copy`. That's trivial in tokens, and in-text highlighting (§4.6) recovers the "it's right there in context" benefit of inline markup. |

**Contract (agent-facing):**

```json
{
  "header": "Mac GUI",
  "question": "… Spotlight: System Settings → Spotlight → Search Privacy… → + → Cmd+Shift+G → paste a path → Return → Choose; repeat for each folder (press y in the TUI to copy each one). Chrome: open chrome://settings/performance …",
  "copy": [
    { "label": ".sase", "text": "/Users/bbugyi/.sase" },
    { "label": "Application Support/sase", "text": "/Users/bbugyi/Library/Application Support/sase" },
    "/Users/bbugyi/.cargo",
    "/Users/bbugyi/.rustup",
    { "label": "bob-cli/target", "text": "/Users/bbugyi/projects/github/bobs-org/bob-cli/target" },
    { "label": "sase-core/target", "text": "/Users/bbugyi/projects/github/sase-org/sase-core/target" },
    { "label": "bob-mac-capture/.build", "text": "/Users/bbugyi/projects/github/bobs-org/bob-mac-capture/.build" },
    { "label": "Chrome performance settings", "text": "chrome://settings/performance" }
  ],
  "options": [ … ]
}
```

**Validation (strict, in `sase questions`; the error names the index):**

- `copy` is optional. When present it is an array of **1–20** entries; 20 keeps the
  panel on one screen.
- An entry is a non-empty **string** or an **object** with required `text` (string)
  and optional `label` (single-line string, ≤ 48 chars). Unknown object keys are
  errors, so typos like `value` / `name` fail loudly.
- `text` is ≤ 4,096 chars after normalization. It must contain **no control
  characters** other than `\n` and `\t`. That blocks ANSI or OSC escapes, which would
  otherwise reach both the terminal and the clipboard.
- **Trailing newlines are stripped** so a pasted one-line command never auto-executes.
  Everything else copies byte-for-byte.
- A duplicate `text` is an error, so the agent learns to dedupe.
- The display path is **tolerant**: legacy or malformed bundles drop bad entries and
  never break the modal.

### 4.2 Trigger and keys

- **`y`** (outside "Other"/global-note input mode) **always opens the panel**, even with
  no snippets. The panel still offers `t` / `y`, and predictability beats cleverness.
- Inside the panel:

| Keys | Action |
| --- | --- |
| `1`–`9`, `0`, then `b c d e f g h i l m n o p r s u v w x z` | Copy that snippet row (declared first, then detected). The letter pool is `artifact_file_selector_keys` minus the panel's reserved keys. |
| `t` | This question as Markdown (header, text, options, no answer marks) |
| `a` | All snippets, one per line (shown only when there are ≥2 snippets) |
| `y` | Everything: all questions + current answers as Markdown (**today's `y`**, so `yy` is muscle-memory compatible) |
| `j`/`k`, `↓`/`↑`, `ctrl+n`/`ctrl+p` | Move the cursor |
| `⏎` / mouse click | Copy the highlighted row |
| `esc` / `q` | Close without copying |
| any other printable key | Toast "Unknown copy key (question: 1–8, t, a, y)", reusing `CopyAsContext.unknown_key_message` |

- **Leave `%` alone** (keep forwarding to app copy mode). Aliasing `%` to this panel
  would match the artifact-files precedent, but it would silently remove the existing
  "copy the selected agent's ref/name while a modal is open" path. It isn't worth the
  regression risk in v1; revisit if users reach for `%` here.

### 4.3 Layout and look

Generalize `CopyAsModal` instead of writing a new widget. Concretely:

- Let `CopyAsContext` carry its own section order and title instead of the hard-coded
  `_CATEGORY_ORDER`.
- Give `CopyAsRow` an optional `marker` (✓).
- Accept an initial cursor key.

The palette then stays one consistent object across the TUI. A `QuestionCopyModal`
subclass only adds CSS that **anchors the sheet over the options pane**
(`align: center bottom`), so the question text stays visible above it.

```
 Question 1/1  (Mac GUI)                                        ⧉ 8 copyable
┌───────────────────────────────────────────────────────────────────────────┐
│ … repeat for each folder: /Users/bbugyi/.sase, /Users/bbugyi/Library/     │  ← declared snippet
│ Application Support/sase, /Users/bbugyi/.cargo, …  Chrome: open           │    occurrences get a
│ chrome://settings/performance, turn on Memory Saver …                     │    subtle accent underline
└───────────────────────────────────────────────────────────────────────────┘
╔═ Copy · Q1 Mac GUI ═══════════════════════════════════════════════════════╗
║ SNIPPETS                                                                  ║
║  1  ✓  .sase                        /Users/bbugyi/.sase                   ║
║  2     Application Support/sase     /Users/bbugyi/Library/Appli…/sase     ║ ← cursor (reverse)
║  3     /Users/bbugyi/.cargo                                               ║
║  4     /Users/bbugyi/.rustup                                              ║
║  5     bob-cli/target               /Users/bbugyi/projects/…/target       ║
║  6     sase-core/target             /Users/bbugyi/projects/…/target       ║
║  7     bob-mac-capture/.build       /Users/bbugyi/projects/…/.build       ║
║  8     Chrome performance settings  chrome://settings/performance         ║
║ QUESTION                                                                  ║
║  t     This question                Markdown · text + 4 options           ║
║  a     All 8 snippets               one per line                          ║
║  y     Everything                   all questions & answers · Markdown    ║
║                                                                           ║
║        1–8 copy · ⏎ highlighted · j/k move · esc close                    ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

If the agent had declared only the seven paths, the URL would still appear under a dim
**FOUND IN TEXT** header as row `8`, showing the raw text with no label.

Visual rules (beauty is in the details):

- **Key column** uses the palette's existing accent (`bold #00D7AF`). **Labels** are
  bold. **Previews** are dim. **✓** is green. Disabled rows stay dim with a yellow
  reason, as in `CopyAsModal`.
- **Middle-ellipsis for paths and URLs** (`/Users/bbugyi/projects/…/target`), because
  the tail is the distinctive part. End-ellipsis for prose.
- **Multi-line snippets** preview their first line plus a dim `⏎ +4 lines`. That's
  also an honest warning that pasting into a shell runs several lines.
- A row with **no label** shows the text itself in the label column and no preview.
- All agent text is rendered as `Text`/`Content`, never markup. That's the same
  bracket-safety lesson as `_build_selections`.
- **The header badge `⧉ 8 copyable`** (dim, right-aligned) and the **footer `y=Copy…`**
  (the ellipsis is the standard UI cue for "opens a chooser") make the feature
  discoverable before the user needs it.
- **In-text highlighting.** Exact occurrences of declared snippet text in the question
  get a subtle accent underline. No glyphs are inserted, so wrapping never changes.
  While the panel is open, the occurrence of the *highlighted row* is emphasized
  (reverse), so moving the cursor visibly "points at" the text it will copy. *Spike
  item:* confirm the screen under the ModalScreen repaints while the panel is on top.
  If it doesn't, ship the static underline only.
- The narrow-terminal `-narrow` class carries over from `CopyAsModal`.

### 4.4 Behavior after a copy

- The panel **closes immediately**: one keypress, done. The toast names the item:
  "Copied 2 · Application Support/sase", or "… (OSC 52)" when only OSC 52 succeeded.
  This uses `schedule_copy_delivery` unchanged, including the >64 KiB fallback modal.
- The row gets a **✓** for the rest of the session. State is kept in memory on the app,
  keyed by the gate's response dir, so closing and reopening the question (or
  switching Q1↔Q2) doesn't lose the checklist. It isn't persisted to disk.
- **The cursor reopens on the first un-copied snippet row**, so `y ⏎` steps through
  snippets in order. That's ideal for "paste → Return → repeat".

### 4.5 The "Found in text" detector (fallback)

This is display-only and never part of the CLI contract.

- **Sources:** the question text, then option labels and descriptions (12% of
  questions have backtick spans in their options, often commands such as
  `bob plugins sync -F`).
- **What it detects:** only spans with unambiguous delimiters:
  - inline backtick spans, kept only if ≥4 chars, contain an alnum, don't start with a
    Markdown marker (`#`, `*`, `-`, `[`, `<`), *and* contain whitespace, `/`, `://`,
    `=`, or a file extension;
  - fenced code blocks, always kept, as one multi-line item;
  - URLs (`scheme://…`), with trailing `.,;:)]'"` trimmed.
- **Never bare paths.** The motivating example shows why.
- **Dedupe:** drop a detected item if it equals, or is a substring of, a declared
  snippet.
- **Cap:** 5 detected rows, in order of first appearance.
- **Expected impact:** about 23% of historical questions (43/185) would show at least
  one detected row, at roughly 80% eyeballed precision. Ship it on by default. If it
  proves noisy, remove it rather than adding a config knob.

### 4.6 Options considered for the panel and rejected

| Candidate row | Verdict | Reason |
| --- | --- | --- |
| Copy highlighted option label/description | ✗ | Options are chosen, not pasted. Commands inside options are already covered by detection. |
| Copy my draft "Other" / global note | ✗ | The user typed it. Pasting into the "Other" input already works through the terminal. |
| Copy gate id / bundle path / response command | ✗ | Debug-only. `d` (gate debug modal) already offers `y`/`Y` copy there. |
| "Open URL / open file" actions | ✗ | Over SSH and tmux they open on the wrong machine (athena, not the Mac). The clipboard is the reliable channel. |
| Asking agent's `@agent:` ref / "ask a helper agent about this" | ◐ Defer | Plausible, but the Agents tab `%` palette already has `@ref`/handoff, and `t` covers "paste this question into another chat". Revisit if requested. |
| Snippets from *all* questions in a multi-question form | ✗ | Breaks key stability between questions. Per-question scope is easier to learn. `a` covers bulk for the current question. |
| Stay-open multi-copy mode | ✗ | The user leaves the terminal to paste anyway. ✓ plus cursor-on-next already gives a 2-key loop. |
| Per-snippet "secret" flag / masking | ✗ | Agents shouldn't put secrets in questions. Not worth the schema surface. |

### 4.7 Where the logic lives

Everything a non-TUI surface must match lives in **`sase-core`**, in a small
`question_round`-adjacent module (for example `question_copy`):

- `normalize_question_copy(question) -> Result<Vec<QuestionCopyItemWire>, Error>` —
  strict; used by `sase questions` validation.
- `project_question_copy_items(question) -> Vec<QuestionCopyItemWire>` — tolerant;
  declared items plus detected items, each carrying `source: "agent" | "detected"`,
  `label?`, and `text`. Used by the TUI, Telegram, mobile, and (later) the QUESTIONS
  deck projection.
- Both are exposed through `sase_core_rs` with thin Python adapters. sase's
  `sase-core-revision.txt` CI pin must move past the sase-core commit (per
  `docs/rust_backend.md`).

**TUI-only (Python):** key assignment, section layout, ✓ state, in-text highlighting,
and toasts.

Both existing Python validators keep their current checks and call the core normalizer
for `copy`, so the CLI and the gate adapter agree.

---

## 5. Requirement adjustments (called out)

| # | Your requirement | My adjustment | Why |
| --- | --- | --- | --- |
| 1 | `copy[<label>]: <text>` inline syntax | **Structured `copy` field** (string or `{label,text}`) per question | Clear boundaries, multi-line, validation, no leakage into Telegram, mobile, successor prompts, or the deck. |
| 2 | Copiable text comes from the agent | **Agent-declared plus a conservative "Found in text" fallback** (backticks, URLs; never bare paths) | About 23% of past questions benefit with zero agent effort; covers forgetful agents and old rounds. |
| 3 | `y` opens a popup | Same, **plus `yy` = today's copy-all** and **✓ / cursor-on-next** for sequences | Keeps muscle memory; makes the motivating 7-path loop fast. |
| 4 | Popup is a new UI | **Generalize the existing `CopyAsModal`**, anchored over the options pane | One copy-palette look across the TUI. The question text stays visible so in-text highlights can point at the source. |
| 5 | TUI feature | **Core-normalized data designed for Telegram `CopyTextButton`s and the QUESTIONS deck** (follow-ups) | Same snippets everywhere. Telegram support is nearly free once the data is structured. |
| 6 | (implicit) | **Skill guidance to prefer one copyable command over many manual GUI steps** | The best copy is the one the user doesn't have to repeat. |

---

## 6. Recommended solution

### 6.1 Spec summary

1. **Schema.** Optional per-question `copy: [string | {text, label?}]`, with 1–20
   entries, text ≤ 4,096 chars, no control characters except `\n`/`\t`, trailing
   newlines trimmed, no duplicates, strict object keys. Normalized in `sase-core`.
   Strict at `sase questions`, tolerant at display.
2. **Panel.** `y` in the question modal opens **Copy · Q<n> <header>**, a generalized
   `CopyAsModal` anchored over the options pane, with sections **SNIPPETS**
   (declared), **FOUND IN TEXT** (≤5 detected), and **QUESTION** (`t` this question
   Markdown, `a` all snippets when ≥2, `y` everything). Snippet keys are `1`–`9`, `0`,
   then letters. `⏎`, click, and `j/k` work; `esc`/`q` close.
3. **Feedback.** The panel closes on copy. The toast names the item. ✓ marks persist
   for the session, keyed by gate. The cursor reopens on the next un-copied snippet.
4. **Discoverability and beauty.** A `⧉ N copyable` header badge, footer `y=Copy…`,
   accent-underlined snippet occurrences in the question text, live emphasis of the
   highlighted row's occurrence (if the spike confirms it repaints), middle-ellipsis
   previews, and a `⏎ +N lines` hint for multi-line snippets.
5. **Agent guidance** (`src/sase/macros/skills/sase_questions.md`, then deploy via the
   generated-skills flow):
   - Declare `copy` for every path, URL, command, ID, or value the user must paste
     somewhere.
   - Label entries when the text is long or opaque, and keep labels short.
   - Put them in the order the user will use them.
   - Prefer a single runnable command over many manual steps.
   - Mention "press y to copy" in prose only when helpful.

### 6.2 Implementation phases

| Phase | Repo | Work | Tests |
| --- | --- | --- | --- |
| 1 | `sase-core` | `question_copy` module: wire type, strict normalizer, tolerant projector with detection; `sase_core_rs` binding | Unit tests: both entry forms, every validation error, trailing-newline trim, control-char rejection, detection filter against fixtures drawn from the real corpus (the 7-path question, backtick noise like `#task`/`[ ]`, URL trailing punctuation) |
| 2 | `sase` | Bump `sase-core-revision.txt`. `_validate_questions` and `validate_user_questions` call the core normalizer. Update the skill source and docs (TUI reference page for the question modal) | CLI tests for error messages; gate adapter round-trip keeps `copy` |
| 3 | `sase` | Generalize `CopyAsModal`/`CopyAsContext` (section order, title, row marker, initial key) without changing existing palettes. Add `QuestionCopyModal` and its CSS. Rebind `y`. Add header badge, footer, in-text highlighting, ✓ state | Modal unit tests (key map, reserved keys, `yy`, ✓/cursor-next, unknown-key toast, input-mode guard); a visual snapshot of the panel, wide and `-narrow`; regression test that the existing Copy-as palettes render identically |
| 4 (follow-up) | `sase-telegram` | Under each live question, one row of `CopyTextButton`s per snippet ≤256 chars, labeled `📋 <label>`. Longer snippets render as MarkdownV2 code blocks (tap-to-copy on mobile) | Formatter tests for the button and code-block paths |
| 5 (follow-up) | `sase-core` + `sase` | Carry copy items in the question-round projection so the Agents-tab QUESTIONS deck can copy snippets from answered rounds (e.g., the user picked "Skip for now" and does it later) | Projection and deck tests |

Phases 1–3 are the shippable feature. Phases 4–5 are cheap because the data is
structured.

### 6.3 Open questions for you

1. **Detection on by default?** I recommend yes, given about 80% precision on the
   historical corpus. Say so if you'd rather start strictly agent-declared and add
   detection only after watching agent adoption.
2. **Cap of 20 snippets** feels right for one screen. The largest historical question
   had 11 candidates.
3. **`a` (all snippets) separator.** One per line is the obvious default. A
   shell-quoted, space-joined variant would help commands like
   `mdutil -i off <paths…>` but adds a row. I left it out.

---

## Sources

- SASE code (paths in §1):
  - `user_question_modal.py`
  - `copy_as_modal.py`, `copy_as_types.py`
  - `clipboard/_delivery.py`, `core/clipboard.py`
  - `artifact_files_modal_copying.py`, `artifact_files_modal_rendering.py`
  - `questions_command_handler.py`, `user_question_actions.py`, `qa_markdown.py`
  - `sase-core` `question_round/{wire,project}.rs`
  - `sase-telegram` `formatting.py`, `inbound_handlers/common.py`
- Corpus: `~/.sase/interaction_requests/question/*/request.json` on athena (124
  bundles, 185 questions) and apollo (36 bundles, 41 questions), analyzed read-only on
  2026-11-26.
- Screenshot: `~/tmp/screenshots/20261126_092327.png`.
- Telegram `CopyTextButton` (1–256 chars):
  [aiogram docs](https://docs.aiogram.dev/en/latest/api/types/copy_text_button.html),
  [python-telegram-bot CopyTextButton](https://docs.python-telegram-bot.org/en/v21.7/telegram.copytextbutton.html),
  [Bot API InlineKeyboardButton](https://core.telegram.org/bots/api/types/inlinekeyboardbutton.md),
  [MTProto keyboardButtonCopy](https://core.telegram.org/constructor/keyboardButtonCopy).
- Terminal hint-mode prior art:
  [kitty hints kitten](https://sw.kovidgoyal.net/kitty/kittens/hints/),
  [tmux-thumbs](https://github.com/fcsonline/tmux-thumbs),
  [tmux-copyrat](https://docs.rs/crate/copyrat/0.8.3/source/README.md).
