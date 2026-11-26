# Copying specific parts of agent questions: consolidated design

**Date:** 2026-11-26 · **Lead researcher consolidation** of five independent reports
(`__cdx`, `__cld`, `__grk`, `__mus`, `__gem` in this directory) plus the lead's own
code and corpus verification.

**Request:** make it much easier to copy specific parts of questions asked by sase
agents — agent-declared copiable snippets (sketched as `copy[<label>]: <text>`), a `y`
pop-up in the questions gate with single-keypress copy choices, plus whatever other
options genuinely earn their place. Critique the plan; adjust requirements where
justified; end with a recommended solution.

---

## 1. Verdict

**Build it — all five researchers and the lead agree.** The pain is frequent, not a
one-off: cld's corpus analysis of every retained question bundle found **35% of 185
athena questions contain at least one obvious copy candidate** (backtick command,
path, or URL) and 22% contain two or more; the lead independently reproduced the same
rate on apollo (13/41 questions, 32%). Today the only escapes are `y` (the whole Q&A
Markdown blob — the screenshot's "Copied questions & answers" toast) or mouse-selecting
word-wrapped `Static` text through tmux/SSH, which breaks on exactly the hard cases
(the motivating question's `/Users/bbugyi/Library/Application Support/sase` wraps
across two rendered lines).

**But not as literally specified.** All five reports independently rejected the inline
`copy[<label>]: <text>` syntax and converged on a structured JSON field, and all five
converged on `y` opening a palette with `yy` preserving today's copy-all. The rest of
this report resolves the places they disagreed, backed by the lead's own verification
of the disputed code claims.

---

## 2. Unanimous findings (treat as settled)

1. **The feature is worth building** (§1).
2. **Reject inline `copy[label]: text`; adopt a structured optional `copy` array on
   each question object.** Reasons, each verified against the code:
   - *Delimiter ambiguity:* whitespace, comma, and period terminators each break real
     payloads in the motivating screenshot (space-containing path, `.build.` before a
     sentence period, `chrome://` URL). Multi-line commands are impossible.
   - *Cross-surface leakage:* `question["question"]` is consumed verbatim by at least
     six renderers (TUI modal, `qa_markdown.py` successor prompts, notification
     previews, Agents-tab QUESTIONS deck, sase-telegram, gateway/mobile). An inline
     DSL either shows raw markup on every surface that doesn't parse it, or requires
     a stripper everywhere.
   - *Exact-string invariant:* `question_response_schema()` pins
     `"question": {"const": …}` and the Rust projection aligns answers by exact
     question string (`question_round/project.rs`). Stripping markup on ingest would
     mutate the contracted string.
   - *Authoring reliability:* agents already emit structured JSON to
     `sase questions '<json>'`; one more field needs no new escaping rules, and the
     TUI renders question text with `markup=False` (verified at
     `user_question_modal.py:199`), so raw bracket syntax would be displayed, not
     hidden.
3. **`y` opens the copy panel; `yy` reproduces today's exact copy-all.** Every copy
   stays ≤2 keypresses; muscle memory survives. The input-mode guard stays: `y` while
   typing an "Other" answer or global note remains ordinary typing (verified guard at
   `user_question_modal.py:506`).
4. **All clipboard writes go through the existing delivery seam**
   (`schedule_copy_delivery` → system clipboard via `tmux load-buffer -w` /
   `pbcopy` / `wl-copy` / `xclip`, then OSC 52 capped at 64 KiB base64, then the
   selectable-text fallback modal). No new clipboard implementation, no direct
   `copy_to_clipboard` calls. Over the user's SSH+tmux setup the clipboard is the one
   channel that reliably reaches the Mac — which is also why the panel stays
   copy-centric: "open URL/file" actions would act on the wrong machine.
5. **Agent-authored text is data, never Rich markup** — labels, previews, and payloads
   render via `Text`/`Content` (the `[/]`-in-option-label lesson already encoded in
   `test_user_question_modal_markup.py`).
6. **Copying never answers.** No row submits, selects an option, or writes a response
   file; Esc closes only the palette; Enter inside the palette must not bubble into
   form submission.

---

## 3. Disagreements, resolved

### 3.1 Generalize `CopyAsModal` vs. build a dedicated modal

cdx, cld, grk, and mus say reuse/generalize the existing "Copy as…" palette; gem says
it is "tightly coupled" and wants a new `QuestionCopyModal`. **Lead verification:**
`copy_as_modal.py` is 177 lines and entirely context-driven off two frozen dataclasses
(`CopyAsRow`, `CopyAsContext`); the only hard-coded pieces are the module-level
`_CATEGORY_ORDER` tuple, the "Copy as…" title string, and the `CopyTargetCategory`
Literal. gem's coupling claim is overstated.

**Resolution: generalize `CopyAsModal`** with cld's concrete, minimal list — per-context
section order and title, an optional `marker` on rows (for ✓), and an initial-highlight
target — then add a thin question-scoped subclass carrying the question-specific CSS
and gem's two genuinely valuable visual upgrades (a verbatim preview pane for the
highlighted row; path-aware middle truncation). One palette look across the TUI,
existing accelerator-precedence and unknown-key behavior for free, and the visual
goldens for palette-over-modal stacking already exist as precedent.

### 3.2 Auto-detected "found in text" fallback

cdx defers all detection; grk wants aggressive extraction including bare prose paths
(via `pager.path_hints`); cld and gem want conservative detection. **Resolution: ship
conservative detection, as its own phase after the declared-snippet palette lands.**

- The case *for*: cld measured it — about 23% of historical questions would gain at
  least one detected row at ~80% precision, with zero agent effort, and it covers old
  rounds and forgetful agents.
- The case *against aggressive*: bare-path regexes get **two of the seven motivating
  paths wrong** (space truncation; trailing sentence period), which is worse than
  offering nothing. grk's bare-path extraction is rejected on this evidence.
- Scope: inline backtick spans passing a noise filter, fenced code blocks, explicit
  scheme URLs (`https://`, `chrome://`, `file://`… — note today's URL pattern is
  `https?://` only), and SASE artifact refs. Deduplicate against declared items, cap
  (~5 rows), render in a visually separate dim section. Display-only: never part of
  the CLI contract. If it proves noisy in practice, remove it rather than add a knob.

### 3.3 Where the contract lives: sase-core vs. Python-only

cdx, cld, and gem put normalization/projection in `sase_core`; grk argues Python-only
for v1; mus says "check at plan time." **Resolution: the contract is core-owned.** The
`rust_core_backend_boundary` litmus ("would another frontend need the behavior to
match?") answers yes: Telegram already renders questions (and already uses
`CopyTextButton` elsewhere, 256-char cap), the Agents-tab QUESTIONS deck is projected
from Rust, and mobile notification projections exist. grk's position contradicts
`decisions:rust-core-required` for data that crosses surfaces.

**Lead verification that settles the mechanics** (both cdx's warning and cld's claim
were half-right):

- `question_round/project.rs:parse_questions()` reads the raw `request.json`
  **tolerantly** (unknown fields like `copy` are ignored today), so old cores never
  choke on new bundles.
- The projected wire structs (`QuestionEntryWire` and siblings in
  `question_round/wire.rs`) are **`#[serde(deny_unknown_fields)]`** — strict. An
  additive `copy_items: Vec<QuestionCopyItemWire>` with `#[serde(default)]` is
  accepted by new readers of old payloads, but old readers reject payloads carrying
  it, and sase-core's own conventions flag "any wire change that old readers reject"
  as breaking within the released minor window.

So the sequencing is mandatory, not optional: land the sase-core change first (wire
type, tolerant `copy` parsing in `project.rs`, strict normalizer + binding), then
ratchet sase's `sase-core-revision.txt`, then wire the Python validators and TUI (per
`docs/rust_backend.md`). Python's two duplicated validators
(`questions_command_handler._validate_questions`, `validate_user_questions` — both
currently pass unknown keys through, verified) should both call the shared normalizer,
closing the existing drift seam.

### 3.4 Direct digit chips on the question modal

grk proposes digits `1`–`9` copy immediately from the modal plus a chip strip; gem
explicitly rejects inline digit bindings. **Resolution: reject for v1 — gem's keymap
argument is verified.** `build_gate_numbered_branch_bindings()` already binds digits to
*decision branches* in `plan_approval_modal.py`, `custom_gate_modal.py`, and
`gate_branch_controls.py`. Making digits mean "copy" in one gate modal and "decide" in
the others breaks the gate keymap convention, and a chip strip steals vertical space.
`y`+digit is two fast keypresses. Discoverability comes from §4.4's cues instead.

### 3.5 Multi-copy ergonomics (the seven-paste loop)

cdx rejects added state ("stable keys suffice"); cld wants ✓ marks plus
cursor-on-next-uncopied; gem adds Space copy-and-stay and a Tab pin mode.
**Resolution: adopt cld's middle ground, defer gem's modes.** Session-only in-memory ✓
marks per question, and the palette reopens with the cursor on the first uncopied
declared snippet, so the motivating workflow becomes `y ⏎ · paste · y ⏎ · paste …`
with the panel always showing how far you've gotten. This adds no modal state machine
and cannot obscure whether a question was answered. Space/Tab stay-open modes are a
plausible follow-up if real use demands them; they conflict with `CopyAsModal`'s
dismiss-on-select contract and aren't needed to make the loop fast.

### 3.6 Which fixed rows earn a key

Union of proposals, with votes and the resolution:

| Row | Votes | Resolution |
| --- | --- | --- |
| `y` everything (today's Q&A Markdown, current batch) | 5/5 | **Keep** — the `yy` compatibility path, always present, highlighted when no snippets exist. |
| `t` current question text (plain prose, no options) | 4/5 | **Keep** — the most-missed target today; ideal for quoting or asking another agent. |
| `o` highlighted option (label — description) | 3/5 | **Keep, disabled with reason when inapplicable.** Concrete workflow: copy an option's command/wording to tweak into "Other…". Copying never selects. |
| `a` all declared snippets, one per line | 2/5 (cdx, grk reject) | **Keep, only when ≥2 snippets** — cheap, honest preview ("8 lines"), useful for shell loops and notes. |
| Question JSON (`J`) | 2/5 | **Cut** — `d` (gate debug) already offers copy there. |
| Snapshot (`s`) | 1/5 | **Cut** — `%` forwarding already reaches the app palette's snapshot. |
| Draft answer / selections / global note | 1/5 | **Cut** — the user just typed or picked them; `y` includes selections. |
| Current-question Q&A (`c`, multi-question ballots) | 1/5 | **Defer** — revisit if multi-question ballots prove common. |
| Open URL / run command / clipboard history / format variants (JSON, shell-quoted…) / copy-and-submit | 0 for v1 | **Cut** — wrong machine over SSH, effect-vs-copy trust boundary, clipboard-manager scope creep, representation explosion. |

Scope rule: snippet and detected rows always belong to the **currently active
question**; `y` (everything) covers the whole batch. Cross-question snippet mixing
breaks key stability (cld, gem agree).

### 3.7 Do copy items leak into exports and successor prompts?

cdx wants snippets visible in exports and successor context ("'the listed folders'
becomes incomplete otherwise"); mus and gem want `qa_markdown`/`qa_prompt` untouched so
copy metadata never echoes back to the asking agent. **Resolution: split by audience.**

- **Successor-agent prompts (`qa_prompt` / follow-up rendering): exclude.** The agent
  authored the values; echoing eight paths back costs tokens and risks drift
  (mus/gem majority), and a regression test should prove the exclusion.
- **Human-facing `yy` Markdown export: include** a compact labeled "Copyable items"
  section, so the user's archived copy of the ballot is complete (cdx's completeness
  concern, honored where it actually matters).
- **On-screen:** a declared item whose text does *not* appear verbatim in the prose
  renders in a muted block under the question text (gem's rule), so nothing copiable
  is ever invisible before copying.

### 3.8 Smaller conflicts

- **Trailing newlines:** strip at normalization (cld) rather than preserve authored
  trailing newlines (cdx) — a pasted one-line command must never auto-execute.
  Everything else copies byte-for-byte: no trimming, quoting, tilde expansion, or
  Unicode normalization; tabs and interior newlines survive.
- **Duplicates:** strict validation rejects duplicate `text` on new submissions (cld);
  display never dedupes or reorders stored items (cdx). Compatible; adopt both.
- **`%` forwarding:** leave unchanged in v1 (cld, gem) — it is the path to the app
  palette's snapshot from inside the modal. grk's observation that `%` targets the
  agent row underneath is a real footgun to watch, not a v1 change.
- **Caps:** validation cap of 20 items/question (cld; historical max observed is 11),
  digits `1`–`9`,`0` then the established safe-letter pool
  (`artifact_file_selector_keys` convention minus the palette's reserved keys
  `j k q y t o a enter esc`); beyond the key pool rows stay reachable via `j/k`+Enter.
  Keys are stable — never reassigned by scrolling or paging.
- **Field name:** `copy` (3/5), entries `string | {"text": …, "label"?: …}` — the bare
  string shorthand keeps agent friction minimal; unknown entry keys are errors so
  `value`/`name` typos fail loudly at `sase questions` time, before the handoff stages
  (`decisions:handoffs-end-through-host-completion`).

---

## 4. Recommended solution

### 4.1 Contract

Optional `copy` array per question in the `sase questions` JSON:

```json
{
  "header": "Mac GUI",
  "question": "…Spotlight: System Settings → Search Privacy → + → paste each folder…
               Chrome: open chrome://settings/performance, enable Memory Saver. What did you do?",
  "copy": [
    { "label": ".sase",            "text": "/Users/bbugyi/.sase" },
    { "label": "App Support/sase", "text": "/Users/bbugyi/Library/Application Support/sase" },
    "/Users/bbugyi/.cargo",
    "/Users/bbugyi/.rustup",
    { "label": "bob-cli/target",   "text": "/Users/bbugyi/projects/github/bobs-org/bob-cli/target" },
    { "label": "sase-core/target", "text": "/Users/bbugyi/projects/github/sase-org/sase-core/target" },
    { "label": "mac-capture/.build", "text": "/Users/bbugyi/projects/github/bobs-org/bob-mac-capture/.build" },
    { "label": "Chrome Memory Saver", "text": "chrome://settings/performance" }
  ],
  "options": [ { "label": "Done, both" }, { "label": "Skip for now" } ],
  "multiSelect": false
}
```

Validation (strict at `sase questions` and gate creation, via one core-owned
normalizer; tolerant at display so malformed historical metadata never breaks the
modal): optional array, 1–20 entries; entry is a non-empty string or
`{text (required, ≤4 KiB), label? (single line, ≤48 chars)}`; no control characters
except `\n`/`\t` (blocks ANSI/OSC escapes reaching terminal or clipboard); trailing
newlines stripped; duplicate text rejected; errors name the entry index. Array order
is authoritative — agents list items in the order the user will paste them.

### 4.2 Interaction

`y` (outside input mode) always opens the panel — even with no snippets, for
predictability. Inside:

| Key | Action |
| --- | --- |
| `1`–`9`, `0`, then safe letters | Copy that snippet (declared first, then detected), close, toast names the item |
| `t` | Current question text (plain) |
| `o` | Highlighted option (disabled with reason when empty) |
| `a` | All declared snippets, one per line (only when ≥2) |
| `y` | Everything — today's Q&A Markdown byte-compatible path (`yy`) |
| `j/k` `↑/↓` `ctrl+n/p`, `⏎`, click | Navigate / copy highlighted |
| `q` / `esc` | Close, nothing copied, form state untouched |
| other printable | "Unknown copy key (…)" toast, palette stays open |

Copied rows carry a session-only ✓; reopening highlights the first uncopied snippet
(or the `y` row when there are none). Opening, copying, and cancelling preserve
question index, option highlight, selections, drafts, and scroll. Rapid successive
copies are serialized in activation order so a slow earlier delivery can never
overwrite a later choice (cdx's race concern).

### 4.3 Layout

Generalized `CopyAsModal` visual language — double border, dim uppercase section
headers, teal `#00D7AF` key column, bold labels, dim previews — plus gem's preview
pane and path-aware middle truncation (tails are the distinctive part of paths):

```
╔═ Copy · Q1/1 · Mac GUI ═══════════════════════════════════════════╗
║ SNIPPETS                                                3/8 ✓     ║
║  1 ✓ .sase                /Users/bbugyi/.sase                     ║
║ ›2   App Support/sase     /Users/…/Application Support/sase       ║
║  3 ✓ /Users/bbugyi/.cargo                                         ║
║  …                                                                ║
║  8   Chrome Memory Saver  chrome://settings/performance           ║
║  a   All 8 snippets       one per line · 8 lines                  ║
║ FOUND IN TEXT                                                     ║
║  9   plan:202611/mac_busy_process_fixes.md                  ref   ║
║ QUESTION                                                          ║
║  t   Question text        Mac busy-process fixes are measured…    ║
║  o   Highlighted option   Done, both                              ║
║  y   Everything           all questions & answers · Markdown      ║
║ ┌─ 2 · App Support/sase · 1 line ───────────────────────────────┐ ║
║ │ /Users/bbugyi/Library/Application Support/sase                │ ║
║ └───────────────────────────────────────────────────────────────┘ ║
║  key copy · ⏎ highlighted · j/k move · esc close                  ║
╚═══════════════════════════════════════════════════════════════════╝
```

Multi-line snippets preview their first line plus a dim `+N lines` badge (an honest
warning before pasting into a shell). Reuse the existing `-narrow` responsive class;
at 80×24 shrink padding and preview, never hide the key/label columns.

### 4.4 Discoverability before the first `y`

- Footer changes to `y=Copy…` (the ellipsis is the standard "opens a chooser" cue).
- A dim right-aligned border badge on the question pane: `⧉ 8 copyable`, updating to
  `⧉ 3/8 copied` as the session progresses.
- *Spike, not commitment:* character-preserving underline of declared snippet
  occurrences in the prose (no glyphs inserted, so wrapping and mouse selection are
  unaffected; must respect the markup-safety invariant and confirm the under-modal
  screen repaints).

### 4.5 Reliability requirements (core to the design, not polish)

- One delivery seam; preserve its honest status distinction (system transport vs.
  OSC-52-only vs. failure → selectable fallback modal). Never probe the user's
  clipboard or reconfigure tmux.
- Exact bytes end-to-end: space-containing paths, `chrome://`, brackets/Rich tokens,
  quotes, Unicode, multi-line indentation all arrive unchanged (acceptance-tested).
- Event isolation: Enter in the palette cannot submit the form; Esc cannot close two
  layers; `y` while typing stays typing; the global `%` copy-mode flag never leaks.
- Tolerant display of damaged historical metadata: report unavailable items; never
  copy a guessed or truncated value.

### 4.6 Agent guidance (adoption lives or dies here)

Update the questions skill source (`src/sase/macros/skills/sase_questions.md`; deploy
through the generated-skills flow) with the worked Spotlight example plus rules:
declare `copy` for every path, URL, command, or ID the user must paste; order items in
paste order; label long or opaque values; **prefer one runnable command over N manual
GUI steps** — the best copy panel is the one a well-written question barely needs.
Guidance should not encourage splitting one decision into many gates to create copy
targets.

---

## 5. Explicitly called-out requirement adjustments

1. **Inline `copy[label]: text` → structured `copy` array** (unanimous; §2.2). The
   inline form may later become sugar *compiled* into the same array at parse time —
   never independently reinterpreted at render time.
2. **`y` becomes "open panel"; `yy` keeps today's exact behavior** (unanimous).
3. **"Single keypress" qualified by finite keys:** digits then letters cover ~28 rows;
   beyond that, rows stay navigable rather than hiding or recycling keys.
4. **Scope addition: conservative auto-detection fallback** (backticks, fenced code,
   scheme URLs, artifact refs — never bare prose paths), as a separable phase.
5. **Scope addition: ✓ copied-tracking + first-uncopied cursor** for the sequential
   paste loop; stay-open/pin modes deferred.
6. **Scope addition: the contract is core-owned** (`sase-core` wire + normalizer +
   detector) so Telegram, mobile, and the QUESTIONS deck inherit identical lists —
   mandated by `decisions:rust-core-required` and made concrete by the
   `deny_unknown_fields` finding (§3.3).
7. **Exactness bounded by safety:** byte-exact copies except stripped trailing
   newlines and rejected control characters.

---

## 6. Implementation phases

| Phase | Repo | Work |
| --- | --- | --- |
| 1 | `sase-core` | `QuestionCopyItemWire` + `copy_items` (`#[serde(default)]`) on `QuestionEntryWire`; tolerant `copy` parsing in `project.rs`; strict normalizer (string/object forms, caps, control-char and duplicate rejection, trailing-newline strip); `sase_core_rs` binding; unit tests incl. the 7-path fixture |
| 2 | `sase` | Ratchet `sase-core-revision.txt`; both Python validators call the normalizer; skill source + CLI docs (`docs/reference/cli/questions.md`) with worked example; round-trip test that `copy` survives staging and never reaches `qa_prompt` |
| 3 | `sase` | Generalize `CopyAsModal`/`CopyAsContext` (section order, title, marker, initial highlight) without changing existing palettes; question copy mixin/modal + CSS; rebind `y`; footer/badge; ✓ state; `yy` export's "Copyable items" section; tests (key map incl. reserved keys, `yy` byte-compat, input-mode guard, event isolation, form-state preservation, markup safety) + visual goldens wide and `-narrow`, dark and light |
| 4 | `sase-core`+`sase` | Conservative detector (core, pure, fixture-tested against the real corpus) + dim FOUND IN TEXT section |
| 5 (follow-ups) | `sase-telegram`, `sase-core`+`sase` | `CopyTextButton` rows for snippets ≤256 chars (plugin already uses the API); carry `copy_items` through the QUESTIONS-deck/history projection so answered rounds stay copyable |

Phases 1–3 are the shippable feature; 4 is cheap and separable; 5 is nearly free once
the data is structured. No feature flag: additive schema plus one rebound key with a
compatibility chord. Old bundles without the field behave exactly as today; immutable
historical bundles are never rewritten.

---

## 7. Where to look for more depth

- **`__cld`** — the corpus analysis (adoption evidence, detection precision), Telegram
  `CopyTextButton` specifics, detection filter rules.
- **`__cdx`** — exactness/validation edge cases, delivery-race analysis, acceptance
  checklist, external precedent (Textual, W3C dialog, VS Code quick picks, xterm/tmux
  OSC 52).
- **`__gem`** — visual polish detail (preview pane, truncation, in-text highlighting,
  batch modes), full cross-surface flow map, phased blueprint.
- **`__grk`** — Copy-as reuse mechanics, extractor sources, the `%`-forwarding footgun,
  diagrams of the key flow and row assembly.
- **`__mus`** — default-row alternative for `y`, empty-state/disabled-row treatment,
  open questions for the planner (answer-snapshot semantics, key-space overflow).

Key code anchors (sase @ `5db9dbf33b`): `src/sase/ace/tui/modals/user_question_modal.py`
(`y` → `action_copy_questions`, input-mode guard, `markup=False`),
`src/sase/ace/tui/modals/copy_as_modal.py` + `copy_as_types.py`,
`src/sase/ace/tui/actions/clipboard/_delivery.py`, `src/sase/user_question_actions.py`
+ `src/sase/main/questions_command_handler.py` (duplicated validators, unknown keys
pass through), `src/sase/main/qa_markdown.py`; sase-core @ `fdc57d0cf1`:
`crates/sase_core/src/question_round/{wire,project}.rs` (tolerant parse, strict
`deny_unknown_fields` wire).
