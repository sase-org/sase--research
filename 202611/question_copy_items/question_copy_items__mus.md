# Copying from SASE Questions Gates: Research Report (`__mus`)

- Date: 2026-11-26
- Request: make it much easier to copy specific parts of questions asked by sase
  agents. Proposal under review: (1) a `copy[<label>]: <text>` inline syntax so
  agents can mark independently-copiable pieces; (2) `y` from the questions gate
  opens a pop-up panel with single-keypress choices among several copy options;
  (3) a well-designed set of panel options; (4) lead the design — intuitive,
  reliable, beautiful.
- Screenshot: `~/tmp/screenshots/20261126_092327.png` — the `User Questions`
  modal (question `Q1 Mac GUI`, five answer options, footer
  `Space=Toggle j/k=Up/Down Enter/S=Submit all g=Global note y=Copy d=Debug
  q=Cancel Ctrl+D/U=Scroll`), with a `Copied questions & answers` toast
  top-right.
- Verdict up front: the feature is worth building, but not as specified. Keep
  the goal, change two requirements: **reject the inline `copy[…]:` syntax in
  favor of a structured `copyables` field**, and **do not silently repurpose
  `y`** — make `y` open the panel *with the current behavior preserved as the
  default/Enter row*, and record the keymap change in `default_config.yml`.
  Reuse the existing `CopyAsModal` (`Copy as…`) palette instead of inventing a
  new popup. Details and options catalog below.

## 1. What exists today (evidence)

All paths below were read in the session workspace checkout (sase repo); no
peer swarm report was consulted.

- Modal: [user_question_modal.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/ace/tui/modals/user_question_modal.py)
  (`UserQuestionModal`, `CopyModeForwardingMixin`). Bindings include
  `y → action_copy_questions`, `g → global note`, `d → debug view`,
  `Enter/S → submit all`, `j/k/Ctrl+D/U → navigate/scroll`.
- Current `y` behavior
  ([action_copy_questions](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/ace/tui/modals/user_question_modal.py:504)):
  saves the current answer, builds one markdown string via
  `_build_qa_markdown` → [qa_markdown.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/main/qa_markdown.py)
  (`build_qa_markdown` → `build_merged_qa_markdown`), then
  `schedule_copy_delivery(self, content, copied_label="questions & answers",
  task_name="sase-copy-user-questions")`. That toast in the screenshot is this
  notify path succeeding. There is exactly one copy target and no selection.
- Delivery seam:
  [clipboard/_delivery.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/ace/tui/actions/clipboard/_delivery.py)
  (`deliver_copy` / `schedule_copy_delivery`): tries system clipboard on a
  pump-free task, emits OSC 52, falls back to
  [copy_fallback_modal.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/ace/tui/modals/copy_fallback_modal.py)
  (selectable `TextArea`) when no transport exists, and notifies
  `Copied <label>` / `Copied <label> (OSC 52)` / errors. OSC 52 payloads are
  capped at 64 KiB base64 (`OSC52_MAX_BASE64_BYTES`). Any new panel must go
  through this seam — do not call `copy_to_clipboard` directly.
- Existing beautiful precedent — the `Copy as…` palette:
  [copy_as_modal.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/ace/tui/modals/copy_as_modal.py),
  [copy_as_types.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/ace/tui/modals/copy_as_types.py)
  (`CopyAsRow`/`CopyAsContext`), context builders in
  [clipboard/_palette.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/ace/tui/actions/clipboard/_palette.py)
  plus `build_copy_as_context` dispatch in
  [clipboard/_core.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/ace/tui/actions/clipboard/_core.py).
  Properties worth copying: warm-only context capture (no filesystem/subprocess
  work before the modal opens), grouped rows with `Category` headers
  (`Identity/Location/Content/Data/Actions`), per-row `key`, `key_display`,
  `label`, `preview` (truncated via `shorten()`), `disabled_reason`, single-key
  accelerators with configured-key precedence, `j/k/enter/q/esc` navigation,
  unknown-key warning, `-narrow` responsive class, and snapshot deferral via
  `captures_snapshot`. This is the interaction the request is really asking
  for; building a second one-off popup would fork the UX and the key-handling
  logic for no benefit.
- Question data model and validation:
  [user_question_actions.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/user_question_actions.py)
  (`validate_user_questions`, `user_question_gate_spec`,
  `question_response_schema`). `validate_user_questions` preserves unknown
  question keys (`question = dict(raw_question)`), so a new structured field
  passes through without breaking the gate hash or the response schema (which
  constrains *answers*, `additionalProperties: False`, not questions). The
  follow-up prompt renderer
  ([qa_prompt.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/main/qa_prompt.py))
  and the merged markdown renderer intentionally flatten rounds and must be
  taught to *ignore* (not render) the new field, or agent copy metadata leaks
  into the successor prompt.
- Gate debug modal precedent for a modal-local copy key:
  [gate_debug_modal.py](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/src/sase/ace/tui/modals/gate_debug_modal.py)
  (`y → copy tab`, `Y → copy bundle path`). Lowercase/uppercase pairing is the
  established convention for "quick copy vs. second copy target" inside a
  modal. The questions modal currently uses only lowercase `y`.
- Keymap source of truth: `src/sase/default_config.yml` (`copy_mode` section,
  modal bindings). Per project gotchas memory, any keymap/leader change must
  update that file. A change to what `y` does in the questions modal is such a
  change.
- Vocabulary: gates are durable command-backed decisions; a question gate turn
  (`turn_kind: "gate"`) outlives its agent and settles once (see `sase memory
  read glossary:gate`). Copying never answers a gate — the panel must be
  answer-safe (no `dismiss(result)`, no command execution, Escape restores
  focus to the options list, current selections preserved).

## 2. Critique of the plan as stated

### 2a. Is this a good idea? Yes — the pain is real

The screenshot makes the case: the question body contains at least seven
Spotlight paths plus a Chrome settings path, all embedded in prose. Today the
only way to get any of them onto the clipboard is `y` (the whole Q&A blob)
followed by manual trimming in an editor, or mouse-selecting wrapped
`Static` text. That is slow and error-prone, especially for paths, commands,
and URLs the agent *knows* are the actionable payload. A one-keypress copy
panel is the right fix, and it generalizes beyond this one question (any
question with a command to run, a file to open, or a choice to relay).

### 2b. The `copy[<label>]: <text>` inline syntax — recommend against

It looks lightweight but fails on intuitiveness, reliability, and beauty:

1. **Collides with real text.** `copy:` and bracket prefixes appear naturally
   in questions (e.g. `Copy: <path>`, `copy[all]: ...`, option text containing
   `[/]` — the codebase already had to wrap option labels in `Content()` to
   stop markup parsing; see `_build_selections`). Any inline sigil needs an
   escape rule, and escape rules are exactly what users and agents get wrong.
2. **Pollutes the rendered question.** Unless the renderer strips it, the
   syntax itself is shown to the answering user; if the renderer strips it,
   what the user reads differs from what the agent wrote, which complicates
   quoting, screenshots, and the `question_response_schema` `const` match on
   question text. A structured field has neither problem.
3. **No place for the key.** Single-keypress choice needs one unique key per
   row. Agent-authored labels do not supply keys; the TUI must assign them
   (`1–9`, `a–z`) anyway. Inline labels duplicate that job badly
   (`copy[1]:` vs auto-keys, collisions across questions).
4. **Validation and cross-surface cost.** Every surface that renders questions
   (TUI modal, Telegram, mobile, `sase gate show`, notification summaries,
   `question_request.json` viewers) would need the same parser, or some
   surfaces leak raw `copy[…]:` text. A structured field degrades gracefully:
   surfaces that do not understand it ignore it; the TUI panel is the only
   renderer.
5. **Prompt-injection and trust surface.** Inline directives inside
   agent-authored prose train users to treat prose as actionable; a visually
   separated `copyables` list (distinct styling, "FROM THE AGENT" grouping)
   keeps "text to read" and "text to copy" distinct.

**Adjustment (justified): replace the syntax with a structured field.**
Suggested shape (naming to be finalized at plan time; keep it parallel with
existing `options: [{label, description}]`):

```json
{
  "question": "...",
  "header": "...",
  "options": [{"label": "...", "description": "..."}],
  "copyables": [
    {"label": "Spotlight folders (7)", "text": "/Users/…/sase\n/Users/…"},
    {"label": "Chrome setting", "text": "chrome://settings/performance"}
  ]
}
```

Rules: `copyables` is optional, max N items (suggest 8/question, enforced in
`validate_user_questions`), each `label` short (suggest ≤ 48 chars, shown in
the panel), each `text` non-empty (suggest ≤ 4 KiB, capped by existing
`cap_copy_content` at copy time anyway). Unknown-field-tolerant readers ignore
it; `build_qa_markdown` / `merge_qa_for_prompt` must explicitly skip it so it
never enters the follow-up agent prompt as phantom question text. Agent label
text is data: render via `Content()` (as options already are), never markup.

A pragmatic middle path if agents struggle to emit JSON: also auto-derive
panel rows from the question (see §4, "Derived" group) so agents get value
with zero new syntax, and treat explicit `copyables` as the override for
cases auto-derivation misses (multi-path lists, exact commands).

### 2c. "`y` opens the popup" — adjust, don't just implement

Today `y` is a one-shot "copy everything." The request repurposes it to "open
chooser." That breaks muscle memory and removes the fastest path for the
common case (paste the whole Q&A into notes/chat). Two better options:

- **Recommended: `y` opens the panel, with the current behavior as the
  preselected default row.** First `Enter` (or `y` then `y`/the row's key)
  reproduces today's exact clipboard content. Zero capability loss, one extra
  keystroke only when the user wants something else. Document the change in
  `default_config.yml` and the footer (`y=Copy…` with ellipsis).
- **Alternative: keep `y` = copy all, add `Y` (or `c`) = copy panel.**
  Preserves muscle memory perfectly and matches the gate-debug `y`/`Y`
  convention. Costs a discoverability problem (users never find the panel).

Either is defensible; the first is better UX if the panel opens instantly and
`Enter` is wired to the default. Do not ship a version where today's blob is
unreachable or requires three keystrokes. Also reserve `q/esc` = cancel
without touching selections, and keep `d` (debug) and `g` (global note)
working from the panel's parent (panel dismissal returns focus to the
options list, input-mode guards unchanged).

### 2d. What the request under-specifies

- Multi-question ballots (which question's pieces? current vs all?).
- Multi-select and `Other...` interplay (copy labels vs copy current
  *selections*?).
- Empty states (no `copyables`, no selections, no global note) — rows must
  carry `disabled_reason`, not vanish silently.
- Size/terminal limits (OSC 52 64 KiB cap, `cap_copy_content` truncation —
  the label must say "truncated" honestly, as `_copy_snapshot` already does).
- Non-TUI surfaces (Telegram/mobile/`sase gate` CLI): the panel is TUI-only;
  those surfaces keep today's full-text copy. Say so explicitly.
- Rust-core boundary: per `rust_core_backend_boundary` memory, shared Q&A
  shaping belongs in `sase-core` if a web/CLI/editor frontend would need it.
  The panel UI stays in Python/Textual; the `copyables` validation + markdown
  exclusion likely crosses the boundary — check `sase-core-revision.txt` and
  `docs/rust_backend.md` at plan time.

## 3. What the panel should offer (only genuinely useful rows)

Design principle: every row answers "I want *that exact string* on my
clipboard with one keypress." Group like the `Copy as…` palette. Keys are
TUI-assigned (`1–9 a–z`), never agent-chosen; previews truncated with
`shorten()`.

**Group A — Agent-specified (only when `copyables` present).**
Per current question first, then other questions' items clearly prefixed
(`Q2: <label>`). This is the request's core ask, and the group header should
say so (e.g. `AGENT-SPECIFIED`). If the agent gave no `copyables`, this group
is absent — not an error.

**Group B — This question (always present).**
1. Current question text (the prose block). The single most-missed target
   today.
2. Highlighted option (label + description, exactly as displayed). Follows
   the selection cursor, so `j/k` then `y <key>` copies the option under the
   cursor without toggling it.
3. Current selections as checklist (`- [x] …`, reusing the qa_markdown line
   format) — for pasting "what I picked" into notes. Disabled with reason
   when nothing is selected yet.
4. `Other` / global-note draft text, when present (these live only in modal
   state until submit — copying them mid-flow is genuinely useful).

**Group C — Whole ballot (always present; preserves today's behavior).**
5. All questions & answers as markdown — today's `y` content, byte-identical,
   as the default/highlighted row so `y Enter` is a no-regression path.
6. Answers only (no question prose) — for "paste my decisions" flows.
7. Questions only (no answers) — for forwarding "what is being asked" without
   leaking half-made selections.
8. Compact JSON of the ballot (`question_request.json` slice for the current
   ballot) — for debugging, re-asking via CLI, filing with bug reports.

**Group D — Derived conveniences (auto-extracted, no agent work needed).**
Only rows with actual content appear; each shows a count preview:
9. All paths in scope (current question, then ballot-wide) — the screenshot's
   exact pain: seven Spotlight folders + Chrome path as one clipboard blob.
10. All commands / code spans.
11. All URLs (`https://`, `chrome://`, `file://`).
Show these collapsed per-question with a ballot-wide variant only when
> 1 question has hits; cap counts honestly (`12 paths — truncated`).

**Deliberately excluded:** copy-with-screenshot (`%s`-style snapshot makes no
sense inside a question modal — the modal *is* the foreground; the existing
`CopyModeForwardingMixin` `%` path already covers pane snapshots outside the
modal), per-character/word granularity (terminal selection already does
that), "copy and submit" combos (answering must stay a separate explicit
`Enter/S` act — never let a copy keystroke settle a gate).

## 4. Recommended solution

**Ship a `Copy as…`-style questions copy panel; feed it from a structured
`copyables` field plus auto-derivation; keep `y`'s current content one
keystroke away.**

1. **Schema (small, tested):** add optional `copyables: [{label, text}]` to
   the question shape in `validate_user_questions` (limits above), thread
   through `user_question_gate_spec`, ignore in `question_response_schema`,
   and explicitly exclude from `build_qa_markdown` / `merge_qa_for_prompt`
   (with a regression test proving agent copy metadata never reaches the
   follow-up prompt). Update `docs/` for the question-gate payload 
   ([docs_writing](/home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_15/sase/memory/docs_writing.md)
   memory applies).
2. **Panel (reuse, don't reinvent):** new `build_questions_copy_context`
   alongside `_palette.py` producing a `CopyAsContext` (subtitle:
   `Q{idx}/{total} · {header}`), opened by `y` via `push_screen(CopyAsModal,
   callback)`. Reuse `CopyAsRow` (`key/key_display/label/preview/
   disabled_reason`), warm-only capture (snapshot modal state — questions,
   current index, highlighted option, selections, other/global drafts —
   before pushing), and `schedule_copy_delivery` for every row with honest
   `copied_label`s (`question 2 text`, `option …`, `7 paths`, `questions &
   answers`, …). Dismissal returns focus to `#user-question-options`
   without altering `_answers` (copying must not mutate answer state beyond
   the existing `_save_current_answer` snapshot semantics — decide at plan
   time whether panel-open should snapshot at all; leaning no, except the
   default row which mirrors today's save-then-copy).
3. **Keys and footer:** `y` opens panel (default row highlighted, `Enter`
   copies it); rows get single-press keys; `q/esc` cancels; footer becomes
   `y=Copy…`. Record in `default_config.yml`; add the keymap test the repo's
   keymap tests require. Consider `Y` as a direct "copy all, no panel"
   escape hatch for muscle memory (mirrors gate-debug `y`/`Y`).
4. **Auto-derivation:** path/URL/code-span extractors over the current
   question (regexes the codebase already uses for artifact references —
   reuse, don't invent) power Group D; no agent cooperation needed on day
   one, which de-risks adoption of `copyables`.
5. **Beauty pass (explicit acceptance bar, not afterthought):** grouped
   category headers, one-line previews, current-question-first ordering,
   `Qn:` prefixes on cross-question rows, disabled rows with reasons
   (`No paths in this question`), `-narrow` behavior under 90×32, footer
   `enter select · j/k navigate · <key> copy directly · q/esc cancel`,
   and the existing `Copied <label>` toast preserved verbatim for the
   default row. Verify with the repo's live TUI screenshot tooling per the
   `tui`/`tui_screenshot` memories before landing.
6. **Surfaces and rollout:** TUI-only panel; Telegram/mobile/CLI unchanged
   (full-text copy). If `copyables` validation or markdown shaping is core
   backend per the Rust boundary, land the `sase-core` half first and pin
   `sase-core-revision.txt`.

**Why this wins over the literal request:** agents write JSON fields more
reliably than inline sigils; users get value on day one even when agents
write nothing new (Groups B–D); one palette component serves every future
copy need instead of a bespoke popup per modal; and today's fastest path
survives as `y Enter`.

## 5. Risks and open questions for the planner

- Key assignment collisions when `copyables` + derived rows exceed
  single-key space: cap total rows (suggest 12–16) with overflow via
  navigation+`Enter` rather than inventing two-key chords.
- Whether opening the panel should `_save_current_answer()` (today's copy
  does) — copying mid-deliberation arguably should not checkpoint
  selections; the default row is the only one that must match legacy bytes.
- Long-question performance: warm-only capture must pre-truncate previews;
  full bodies resolve inside the pump-free copy task (the `_delivery.py`
  callable-value pattern), never on the UI thread.
- Telegram/mobile parity expectations: decide explicitly that rich panel =
  TUI-only, and say it in help text, or mobile users will file "missing
  feature" beads.

---

*Evidence: `src/sase/ace/tui/modals/user_question_modal.py` (modal + `y`
handler), `src/sase/main/qa_markdown.py` + `src/sase/main/qa_prompt.py`
(renderers), `src/sase/user_question_actions.py` (validation/gate spec),
`src/sase/ace/tui/actions/clipboard/{_core,_delivery,_palette}.py` +
`src/sase/ace/tui/modals/{copy_as_modal,copy_as_types,copy_fallback_modal,
gate_debug_modal,base}.py` (palette + delivery precedents),
`src/sase/default_config.yml` (keymaps), screenshot
`~/tmp/screenshots/20261126_092327.png`. Memory: `decisions` roster read;
glossary `gate`/`stitch` read; `tui` entry + linked screenshot/perf notes
identified for the implementation phase.*
