# Copying exact text from SASE questions

Independent research and design recommendation · researcher **cdx** · 2026-11-26

## Decision in brief

Build this feature. The screenshot demonstrates a concrete, repeated task: transferring individual paths and a URL into other applications while a question stays open. A small copy palette fits SASE's keyboard-oriented interface, and SASE already has most of the required UI and clipboard machinery.

My recommendation is **optional structured `copy_items` on each question, rendered visibly with the question, and a question-scoped “Copy…” palette on `y`**. Give authored snippets stable single-key shortcuts, preserve the old full Q&A export as `y` inside the palette (`yy` overall), and add only three other copy representations: the current question, the highlighted answer option, and the current draft answer. Include a way to view/select the exact payload when automatic clipboard delivery fails or is uncertain.

Do not introduce a prose parser, automatic path harvesting, clipboard history, command execution, or a collection of output formats in the first release. The hard part is preserving intent and exact text through all question surfaces, not drawing another modal.

This report is independent. I inspected the supplied screenshot, the current SASE and sase-core checkouts, relevant project decisions, and public primary documentation. I did not consult the other swarm reports or their findings. This is source-based design research, not an implemented prototype or a completed usability study.

## What the example actually needs

The supplied screenshot, `~/tmp/screenshots/20261126_092327.png`, contains seven Spotlight exclusion folders, including `/Users/bbugyi/Library/Application Support/sase`, followed by `chrome://settings/performance`. The toast says “Copied questions & answers.” The user must extract a short exact value from a long, visually wrapped paragraph before pasting it elsewhere.

The useful unit is **one intended paste**, not one displayed line, one recognized filesystem token, or the entire question. The folder containing a space is an especially good counterexample to token-based extraction. The Chrome URL also shows why a generic “copy all paths” command would not solve the whole task.

The copy panel should preserve the surrounding work: which question is active, which option is highlighted, which options have actually been selected, and any answer or global-note draft. Copying must never answer the question. A highlight is not a selection; the screenshot alone does not establish which answers have been chosen.

The screenshot also exposes a writing problem. The question mixes progress reporting, a record reference, two sets of instructions, eight paste targets, and the actual question. Copy support helps, but authoring guidance should also encourage short instructions, named snippets, and a clear final decision. It should not encourage agents to ask more questions or split one coherent decision into many gates merely to create copy targets.

## Current implementation and reusable pieces

Inspected SASE revision: `5db9dbf33b5c824174942a445fa8fda8a2e3897e`.
Inspected sase-core revision: `fdc57d0cf1aede8926b5f42833aa4f9f0722838b`.

| Finding | Evidence and consequence |
| --- | --- |
| `UserQuestionModal` binds `y` directly to `action_copy_questions`. It saves current selections, builds Markdown for every question in the current modal, and schedules clipboard delivery. | [S1]. Change this entry point to open the palette. Preserve the aggregate representation for sharing context. |
| Question text is a `Static(..., markup=False)`; answer labels use literal `Content` values. | [S1]. Raw agent strings are deliberately not Rich markup. Keep this property for snippet labels, previews, and full text. |
| `CopyAsModal` already supports accelerator keys, a highlighted row, arrows or `j/k`, Enter, mouse activation, disabled rows, and Escape. Its context is captured before opening. | [S2]. Reuse this interaction and visual vocabulary. Its fixed categories and one-line ellipsized rows need a modest extension for snippets and a full preview. |
| Existing copy accelerators take precedence over navigation, including `j`, `k`, and `q` when configured. | [S2], [S7]. Do not allocate these keys to generated snippet shortcuts; do not change precedence globally as part of this feature. |
| Shared clipboard delivery runs outside the UI message pump, attempts system transport plus OSC 52, and opens a selectable fallback when neither is available. | [S3]. Route new actions through this seam rather than creating another clipboard implementation. |
| CLI and gate validation currently live in Python. They validate existing fields but retain unknown question keys. | [S4]. An extra field passing today is not a supported schema: validate `copy_items` explicitly before staging. |
| Rust's question projection currently includes prompt, options, recommendation and answer data, but no copy items. Notification summaries also reconstruct a narrower model. | [S5], [S6]. A TUI-only implementation could silently lose snippets in history and other views. |
| The questions skill teaches a JSON array with `question`, `header`, `options`, and `multiSelect`; the CLI accepts a JSON positional argument. | [S4], [S8]. Structured metadata fits the existing authoring model without a new CLI subcommand. |

Two governing decisions matter. `decisions:rust-core-required` places shared deterministic behavior in Rust, with thin Python adapters. `decisions:handoffs-end-through-host-completion` requires questions to validate and stage before the creator finishes; copy metadata must not change continuation or gate settlement. Existing Python validation is a seam to improve, not permission to duplicate the new contract across frontends.

## Assessing the authoring approaches

| Approach | Strength | Cost or failure mode | Judgment |
| --- | --- | --- | --- |
| `copy[Label]: value` in prose | Short, readable, close to the proposed syntax | Ambiguous end of value, multiline handling, literal occurrences, brackets, Markdown nesting, and escaping; may appear raw elsewhere | Attractive shorthand later; avoid as the canonical v1 contract |
| Structured items on the question | Explicit boundaries, natural JSON escaping, optional labels, exact multiline text, portable across frontends | Requires schema, projection, rendering, and skill changes | **Best initial implementation** |
| Automatically extract paths, URLs, inline code, and fences | Helps some old questions without author changes | False positives, missing schemes, punctuation mistakes, ambiguous whitespace, many low-value rows | Defer; cannot provide the exactness guarantee |
| Mouse selection only | Arbitrary text without author cooperation | Difficult for wrapped text and repeated transfers; terminal/widget dependence | Keep as a complementary fallback |
| Rich-document AST or span offsets into the question | Avoids duplication; supports many interactive annotations | New document language or fragile indexing for a small feature | Too much infrastructure for this need |

Textual documents mouse selection and Ctrl+C for most widgets, with terminal-specific modifier selection as a fallback. That is a reason to retain selection, not a reason to force eight precise selections in this example. [Textual FAQ](https://textual.textualize.io/FAQ/#how-can-i-select-and-copy-text-in-a-textual-app)

If shorthand is later justified by actual authoring friction, compile it into the same core representation before persistence. Specify line/block boundaries and literal escaping then. Do not independently reinterpret stored prose whenever a frontend displays it. For now, literal `copy[foo]: bar` remains ordinary text.

## Proposed contract

Add optional `copy_items` to each question. Each item has required `text` and optional `label`. Do not require agent-chosen hotkeys, generated IDs, a type taxonomy, or a redundant `copyable` flag.

```json
[
  {
    "header": "Mac GUI",
    "question": "Add the listed folders to Spotlight Search Privacy, then open Chrome performance settings and enable Memory Saver. Which steps did you complete?",
    "copy_items": [
      {"label": "SASE state", "text": "/Users/bbugyi/.sase"},
      {"label": "SASE app support", "text": "/Users/bbugyi/Library/Application Support/sase"},
      {"label": "Cargo cache", "text": "/Users/bbugyi/.cargo"},
      {"label": "Rust toolchains", "text": "/Users/bbugyi/.rustup"},
      {"label": "Bob CLI build", "text": "/Users/bbugyi/projects/github/bobs-org/bob-cli/target"},
      {"label": "SASE core build", "text": "/Users/bbugyi/projects/github/sase-org/sase-core/target"},
      {"label": "Mac capture build", "text": "/Users/bbugyi/projects/github/bobs-org/bob-mac-capture/.build"},
      {"label": "Chrome performance", "text": "chrome://settings/performance"}
    ],
    "options": [
      {"label": "Done, both"},
      {"label": "Done, Spotlight only"},
      {"label": "Done, Chrome only"},
      {"label": "Skip for now"}
    ],
    "multiSelect": false
  }
]
```

This illustrates the copy contract; a real question should retain any needed instruction detail, such as the Spotlight “Go to Folder” sequence. The paths come from the screenshot, not from inspecting or validating the Mac filesystem.

The contract should be deliberately boring:

- Omission or `[]` means no authored snippets. `null`, non-array values, non-object items, missing/non-string text, and empty or whitespace-only text fail new-request validation with an indexed field path.
- Missing labels display as `Snippet 1`, `Snippet 2`, etc. Provided labels are short, nonempty, single-line display text. Duplicate labels can be disambiguated visually by ordinal; they do not determine identity.
- Array order is authoritative. Identify a row by gate/question/item position, not its label or truncated preview. Do not deduplicate or reorder authored items automatically.
- Copy the decoded string exactly: no trimming, Unicode normalization, shell quoting, tilde expansion, path resolution, Markdown wrappers, or added newline. Preserve tabs, leading spaces, embedded newlines, and an explicitly authored trailing newline. A folder containing spaces stays one unquoted path.
- Preview rendering may escape controls and show whitespace indicators, but must not replace the stored payload. For new items, reject NUL and terminal control characters other than tab and ordinary line endings using a shared validation policy.
- Apply documented aggregate size/count limits before staging. Do not confuse application limits with a terminal's OSC 52 capacity. Choose limits after reviewing existing gate payload limits; the evidence here does not justify a new magic number.
- For malformed historical metadata, keep the question usable, report unavailable items, and never copy a guessed or partially reconstructed value. New submissions receive a clear error instead of this tolerant historical path.

Render items visibly beneath the question in a compact “Copyable text” area, with labels, values, and a `y` hint/count. This avoids requiring prose and metadata to duplicate every path. The palette and visible list use the same values.

Visibility also applies to text exports and successor prompts. Otherwise “the listed folders” becomes incomplete when copied, viewed in history, or answered elsewhere. Labels belong in contextual representations, but not in an individual snippet's clipboard payload.

## Interaction design

Pressing `y` in question navigation mode always opens “Copy…”, including for questions without authored items. It must not commandeer `y` while the user types an Other answer/global note or while the embedded Vim editor owns that key.

The popup names its scope: `Question 1 of 3 · Mac GUI`. Authored snippets come first, followed by a short, stable group of contextual representations.

| Key inside palette | Action | Scope and reason |
| --- | --- | --- |
| `1`–`9`, then `0` | Copy authored snippet | One exact value, in declared order. Solves the primary task. |
| `t` | Copy question text | Current prompt plus labeled copyable items, without offered answers. Useful for asking someone else or sharing context. |
| `o` | Copy highlighted option | Label and description of the option highlighted before opening. Does not select it. Useful for discussing an alternative. |
| `a` | Copy draft answer | Current question's actually selected labels and custom feedback, in stable option order. No unselected options. Clearly labeled “draft.” |
| `y` | Copy all questions & answers | Existing Markdown export for this modal's batch, including choices, draft selections, copy items, and global note. Keeps fast `yy`. |
| `v` | View/select highlighted text | Full read-only payload for inspection or manual selection; a utility action, not another output format. |

Keep `o` and `a` at stable keys but disabled with a short reason when inapplicable. For synthetic “Other…”, enable `o` only when actual custom text exists and label it explicitly; do not copy a placeholder. A global note belongs in full Q&A; a separate note row needs demonstrated demand.

Define `o` as `label`, or `label — description` when a description exists. Define `a` as selected labels one per line, followed by a separated custom-feedback block when present. These contextual exports are not executable text. An intended command should be an authored snippet. Only an individual snippet promises an unchanged source string.

The aggregate row means **this batch**, not all questions ever asked in the agent session, matching the current modal behavior. Avoid silently widening it to merged historical rounds.

### Keys, focus, and state

- Assign digits first. Beyond ten snippets, allocate from a fixed safe letter pool after reserving built-in action/navigation keys. With the proposed keys, `bcdefghilmnprsuwxz` provides eighteen further accelerators. Scrolling and resizing never reassign them.
- Beyond that finite pool, every item remains reachable with arrows/`j/k` and Enter. Do not hide items or recycle keys per page. This qualifies “single keypress”: direct keys for normal lists, navigable overflow for pathological lists. All eight screenshot targets are direct.
- `Esc` and `q` dismiss only the copy palette. Enter copies the highlighted row. Do not allocate `q`, `j`, or `k` as snippet keys.
- Opening/cancelling preserves question index, scroll, option highlight, selections, and drafts. Capture a read-only snapshot; do not submit or persist a response.
- After copy, return to the same question. A small toast names the item without repeating a long or sensitive value. Stable keys make repeated `y1`, `y2`, etc. efficient without a persistent palette mode.
- Consume selection events before dismissal. Enter must not bubble into form submission; Escape must not cancel the whole gate. Test both.
- Keep application-wide `%` copy mode distinct. The local palette must not accidentally activate or leave behind the global copy-mode flag.

A modal should take focus, contain interaction, close with Escape, and restore focus to its invoker. W3C's modal pattern supplies this behavioral precedent; it does not establish web-ARIA compliance for a terminal UI. [W3C dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)

Textual searches bindings from the focused widget upward and treats priority bindings specially. Explicit event ownership is more reliable here than a global priority `y` binding. [Textual input guide](https://textual.textualize.io/guide/input/#bindings)

## Visual design

Make the palette a compact, calm layer over the question. Retain SASE's surface, accent, border, and muted-text tokens. Avoid a new icon-heavy visual language. The existing 72-column copy modal is a useful baseline; long path previews justify more width when available.

Illustrative layout, with an abbreviated list preview and the actual selected value below:

```text
╭─ Copy… ────────────────────────────────────────────────────────╮
│ Question 1 of 1 · Mac GUI                                     │
│                                                              │
│ COPYABLE TEXT                                                │
│  1  SASE state          /Users/bbugyi/.sase                    │
│ ▸2  SASE app support    …/Library/Application Support/sase      │
│  3  Cargo cache         /Users/bbugyi/.cargo                   │
│  4  Rust toolchains     /Users/bbugyi/.rustup                  │
│  5  Bob CLI build       …/bob-cli/target                      │
│  6  SASE core build     …/sase-core/target                    │
│  7  Mac capture build   …/bob-mac-capture/.build              │
│  8  Chrome performance  chrome://settings/performance         │
│                                                              │
│ QUESTION & ANSWER                                            │
│  t  Question text                                            │
│  o  Highlighted option    Done, both                          │
│  a  Draft answer          No answer selected                  │
│  y  All questions & answers · Markdown                       │
│                                                              │
│ /Users/bbugyi/Library/Application Support/sase                 │
│ 1 line · no trailing newline                                 │
│                                                              │
│ key / enter copy · ↑↓ navigate · v view text · esc back        │
╰──────────────────────────────────────────────────────────────╯
```

The disabled draft row is an illustrative state, not an inference about the screenshot. This is a layout sketch, not a captured implementation.

Aim for roughly 76–92 columns when available, capped by the viewport. At 80×24, reduce padding and preview height and scroll the list; preserve title and essential footer. At very small sizes retain key, label, and navigation first. Never shrink text or require horizontal scrolling just to discover an action.

Align shortcut, label, and muted preview columns. Use a cursor marker plus a contrasting row background so selection is not conveyed by hue alone. Keep group labels subdued. A selected-item preview is necessary for paths differing only at the end; generic middle ellipsis preserves context without a path classifier. Multiline items show a few lines and a line count; `v` opens the whole value. Whitespace indicators remain separate from the copy payload.

Initially highlight the first enabled snippet, or the aggregate row if no snippets exist. Do not remember a surprising last-used action across unrelated questions. Stable `yy` serves users who prefer the old export.

Microsoft's Quick Pick guidance supports brief labels/details, a title when no input field supplies context, and restrained multi-step interactions. This is precedent for a compact picker, not a reason to add search or a wizard. [VS Code Quick Picks](https://code.visualstudio.com/api/ux-guidelines/quick-picks)

## What to leave out

| Candidate | Decision |
| --- | --- |
| Automatic URL/path/code-span extraction | Defer. Boundaries are uncertain and the author knows the intended paste targets. |
| “Copy all snippets” | Omit initially. Seven paths and a Chrome URL are not a useful single paste. Authors can provide an explicit multiline bundle for a destination that accepts one. |
| JSON, shell-escaped, Markdown, plain, quoted variants for every row | Omit. They multiply choices and invite wrong representations. Snippets have one exact payload. |
| Run command / open URL / open path | Omit from a copy panel. Effects and trust requirements differ. |
| Clipboard history, append mode, multiple clipboards | Omit. This is not a clipboard-manager project. |
| Persistent palette, automatic next item, copy-and-submit | Defer or reject. Added state can obscure whether a question was answered. Reopening with stable keys is sufficient. |
| Search by typing | Defer until real lists justify it. Typing conflicts with immediate shortcuts; a later explicit `/` search mode could resolve that. |
| Agent identity, gate ID, debug JSON, screenshots | Omit. Existing global copy/debug tools cover these. |

## Reliability is part of the design

Reuse `schedule_copy_delivery` and the current fallback [S3]. Preserve its distinction between successful transport and an OSC-52-only attempt. Its `VERIFIED` enum currently reflects command success, not proof that the final workstation clipboard contains the intended bytes.

This matters for the screenshot's apparent remote/tmux workflow. OSC 52 can be disabled by the terminal; tmux also allows or blocks clipboard operations. The protocol carries base64 selection data, so rendered previews and source-size guesses are inappropriate transport inputs. [xterm control sequences](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html), [tmux manual](https://man.openbsd.org/tmux#set-clipboard)

The delivery seam guards OSC 52 at 64 KiB of encoded payload. Reuse that implementation limit without claiming it is universal. A large item can still use system transport; failure must offer complete selectable text, never truncation. Textual documents terminal compatibility limits for its clipboard API. [Textual App clipboard API](https://textual.textualize.io/api/app/#textual.app.App.copy_to_clipboard)

Keep transport details out of the normal menu. On known failure show the existing manual-selection fallback. When only OSC 52 was attempted, retain honest status and keep `v` available for silent rejection. Do not probe by reading the user's clipboard or automatically reconfigure tmux.

Snapshot payloads before asynchronous work. Rapid copies must not race so an earlier slow operation overwrites a later choice. Verify the delivery behavior with two deliberately delayed operations; if ordering is not guaranteed, serialize this palette's delivery requests in activation order. A sequence token alone cannot undo an external clipboard write that completes late.

Never interpret a copied path as a path on the SASE host. The Mac paths may not exist remotely; no existence check is needed. Clipboard actions must not execute or interpolate values into shell syntax. Preserve the existing subprocess-stdin delivery pattern.

## Implementation boundaries and rollout

This is a coordinated contract and presentation change with a modest UI layer, not a broad rewrite of question answering.

| Area | Responsibility |
| --- | --- |
| `sase_core` question domain | Validate/normalize metadata, preserve it in projections, define shared semantic copy content. Any future shorthand parser belongs here too. |
| PyO3 and Python facade | Expose core behavior; keep CLI and gate adapters thin. Validate metadata before a successful staged handoff. |
| `UserQuestionModal` | Capture draft/highlight state, render visible snippets, build local context, open palette, dispatch selected payload. |
| Existing copy modal/types/styles | Add a question context or focused reusable extension for custom groups and preview. Preserve unrelated behavior; do not force snippets into the current Identity/Location taxonomy. |
| Q&A rendering and projections | Include snippets in question/aggregate exports, history, and successor context. Preserve draft versus submitted distinctions. |
| Authoring guidance | Update `src/sase/macros/skills/sase_questions.md` with path/URL and multiline examples. Generate installed skills only through the established post-landing process. |
| Help/configuration | Change footer to `y Copy…` and update help. If fixed bindings become configurable, use the keymap/default-config machinery. Dynamic snippet allocation stays internal. |

The base shape should be additive: old requests without the field behave normally. Do not rewrite or rehash old immutable gate bundles to insert guessed targets.

“Additive JSON” does not prove compatibility everywhere. Rust wire types use strict deserialization, and older projected readers may drop or reject new fields. Audit both directions, including binding fixtures and version policy, then coordinate the core change and SASE's `sase-core-revision.txt` pin. Do not blindly bump the entire gate envelope version for a nested optional field.

Enable authoring only after supported question surfaces render the content. A frontend without copy actions must at least show a readable label/value list. A compatibility formatter can provide that without changing canonical question text. Older deployed clients ignoring the field require a rollout decision: update them or temporarily retain essential values in prose. This report did not inspect the Telegram plugin or perform a full mobile consumer audit; that remains an implementation check, not an established result.

A useful delivery order is shared contract/readable projections, then question palette/delivery tests, then agent guidance. Keep ordinary questions usable at each stage. Do not teach new metadata before the deployed host supports it.

## Verification and a small usability check

Judge observable behavior, not only snapshots.

| Area | Acceptance checks |
| --- | --- |
| Exactness | Space-containing paths, `chrome://`, brackets/Rich tokens, quotes, backslashes, Unicode, multiline indentation, leading/trailing spaces, and explicit final newline arrive unchanged. |
| Validation | CLI staging and direct gate creation reject malformed metadata with indexed errors. Old requests remain valid; damaged historical metadata does not make questions unreadable. |
| Single-key behavior | `y2` copies snippet two; `yy` exports Q&A; keyboard and mouse agree; overflow never reuses a key. |
| Form preservation | Copy/cancel returns to the same question, highlight, selections, scroll, and drafts. Copying an option does not select it. No response file is written. |
| Event isolation | Enter cannot submit the underlying form, Escape cannot close two layers, typing `y` remains typing, and global `%` mode does not leak. |
| Scope | `t` includes snippets but no choices; `o` reflects pre-popup highlight; `a` excludes unselected choices; full Q&A includes global note and current-batch snippets. |
| Transport | System transport, OSC-only, failure, over-limit payloads, Unicode encoded size, and delayed rapid copies preserve content and truthful feedback. |
| Continuity | Request → gate → live modal → history/notification → aggregate export → successor retains values. Test relevant old/new reader directions. |
| Layout | Dark/light, 80×24 and 120×40, long labels, similar path suffixes, missing labels, zero/many items, and multiline preview remain legible. |

Build on existing clipboard, palette, markup, and Vim-input tests [S7]. Snapshot the actual Textual widget rather than treating the sketch as a pixel specification. No application code was changed or application tests run for this report.

Before expanding scope, try three tasks: copy the seven screenshot paths in order to a plain-text scratch destination; inspect/copy a multiline command without an added newline; and copy Q&A from a legacy question without snippets. Wrong pasted values and accidental form changes are failures. The expected interaction is `y` plus one key per normal snippet, without trimming. These are proposed checks, not measured usability results.

## Explicit changes to the requested requirements

1. **Replace tentative inline syntax with structured `copy_items` for v1.** JSON gives reliable boundaries through the existing authoring channel.
2. **Make snippets visible question content, not hidden menu metadata.** This avoids duplication and keeps views/exports complete.
3. **Qualify single-key selection for finite keyboard capacity.** Normal lists have unique shortcuts; unusually large lists remain navigable.
4. **Preserve full Q&A through `yy`.** Opening a panel adds a keystroke, so provide a stable fast path.
5. **Keep the panel focused on copying.** No execution/open actions, speculative extraction, or universal bundle copy initially.
6. **Require transport fallback, exact payloads, and form-state preservation.** These are core to reliability, not optional polish.

## Evidence index

Code links identify the inspected revisions. Files were inspected locally, not web-fetched.

- **[S1] Question form:** [user_question_modal.py](https://github.com/sase-org/sase/blob/5db9dbf33b5c824174942a445fa8fda8a2e3897e/src/sase/ace/tui/modals/user_question_modal.py), especially bindings, `_build_qa_markdown`, `action_copy_questions`, and event handling.
- **[S2] Palette:** [copy_as_modal.py](https://github.com/sase-org/sase/blob/5db9dbf33b5c824174942a445fa8fda8a2e3897e/src/sase/ace/tui/modals/copy_as_modal.py), [copy_as_types.py](https://github.com/sase-org/sase/blob/5db9dbf33b5c824174942a445fa8fda8a2e3897e/src/sase/ace/tui/modals/copy_as_types.py), and `src/sase/ace/tui/styles.tcss` around `CopyAsModal`.
- **[S3] Delivery:** [clipboard/_delivery.py](https://github.com/sase-org/sase/blob/5db9dbf33b5c824174942a445fa8fda8a2e3897e/src/sase/ace/tui/actions/clipboard/_delivery.py), [core/clipboard.py](https://github.com/sase-org/sase/blob/5db9dbf33b5c824174942a445fa8fda8a2e3897e/src/sase/core/clipboard.py), and `src/sase/ace/tui/modals/copy_fallback_modal.py`.
- **[S4] Requests:** [user_question_actions.py](https://github.com/sase-org/sase/blob/5db9dbf33b5c824174942a445fa8fda8a2e3897e/src/sase/user_question_actions.py), [questions_command_handler.py](https://github.com/sase-org/sase/blob/5db9dbf33b5c824174942a445fa8fda8a2e3897e/src/sase/main/questions_command_handler.py), and `src/sase/notification_gates/kind_validation/question.py`.
- **[S5] Rust projection:** sase-core `crates/sase_core/src/question_round/{wire.rs,project.rs}` at `fdc57d0cf1aede8926b5f42833aa4f9f0722838b`; Python facade `src/sase/core/question_round_facade.py`.
- **[S6] Summary/export:** [question_summary.py](https://github.com/sase-org/sase/blob/5db9dbf33b5c824174942a445fa8fda8a2e3897e/src/sase/notifications/question_summary.py), [qa_markdown.py](https://github.com/sase-org/sase/blob/5db9dbf33b5c824174942a445fa8fda8a2e3897e/src/sase/main/qa_markdown.py), and `src/sase/ace/tui/modals/notification_modal_question.py`.
- **[S7] Tests:** `tests/ace/tui/test_copy_as_palette_modal.py`, `tests/ace/tui/actions/test_clipboard_delivery.py`, `tests/ace/tui/test_user_question_modal_markup.py`, and `tests/ace/tui/test_user_question_modal_vim.py` at the SASE revision above.
- **[S8] Authoring:** [questions skill source](https://github.com/sase-org/sase/blob/5db9dbf33b5c824174942a445fa8fda8a2e3897e/src/sase/macros/skills/sase_questions.md); CLI reference `docs/reference/cli/questions.md`.
- **Project guidance:** audited reads of `roster:decisions`, `decisions:rust-core-required`, `decisions:handoffs-end-through-host-completion`, `ace.md`, `tui.md`, `tui_perf.md`, `generated_skills.md`, and `glossary:Sase Gate`.
- **External primary sources:** Textual FAQ/input/App documentation, Microsoft Quick Pick guidance, W3C modal guidance, xterm control sequences, and the OpenBSD tmux manual, linked beside supported claims and accessed 2026-11-26. Current docs may differ from SASE's pinned Textual 8.0.1; verify APIs against that dependency during implementation.

## Recommended solution

Implement **question-local `copy_items` and a compact `y` palette built on SASE's existing copy UI and delivery seam**. Put exact snippets first, provide stable `y1`–`y0` transfers, retain `yy` for the complete current Q&A batch, and offer question text, highlighted option, and draft answer as the only additional copy representations. Show the selected payload clearly, preserve the form completely, and carry snippets through supported question views and exports using a Rust-owned shared contract. Defer inline syntax and automatic extraction until real use demonstrates that their complexity earns its place.
