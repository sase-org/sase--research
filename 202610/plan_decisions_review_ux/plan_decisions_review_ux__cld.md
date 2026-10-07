# Plan Decisions, Reviewed: the UX in ACE, Telegram, and the CLI

> **Research query:** Plans (tales and epics) should be able to embed gate options in
> their frontmatter. Two uses drive this. First, memory changes must be planned behind
> explicit human gates that default to on only when the user asked for them. Second, a
> planner with a plan-shaping question should be able to write a good plan now and let
> the coder implement whatever the reviewer picks. Building on the accepted
> recommendations in `plan_frontmatter_decisions.md`, what is the best possible UX for
> this across the TUI, Telegram, and the CLI? It should be intuitive, reliable, and
> beautiful.

_Researcher `cld` · 2026-10-07 · sase `ca3a194423`, sase-telegram `d335fb8`, Textual
8.0.1. The mock images are rendered with ACE's own frontmatter highlighter and its
SVG→PNG renderer (`sase.ace.tui.visual_render`). They are mocks, not product
screenshots._

## Bottom line

The canonical report settled the model: **Plan Decisions**. A plan declares a few typed,
defaulted choices. The host compiles them into the plan-approval gate. The reviewer
answers them in the same review, and the answers are stamped into the archived plan. I
keep all of that. This report designs the experience around it.

Before the details, here is the review experience in one picture:

![Proposed ACE Plan Review with a Decisions section. The focused "grouping" choice is expanded, showing both options with consequences, the planner default marked with a star, and the changed value marked with a gold dot. In the document pane the chosen branch callout is highlighted and the unchosen one is dimmed.](plan_decisions_review_ux__cld_tui_choice.png)

The design rests on eight recommendations:

1. **One visual language on every surface.**
   - `★` marks the planner's default, and a gold `●` marks anything you changed.
   - `🧠` marks consent to edit memory.
   - Every decision has a single name, its **id**: `grouping`, `tui_note`. That name
     appears in the TUI, on Telegram buttons, in `-D grouping=mode`, in the coder's
     prompt, and in the archive.
2. **A single summary sentence**, produced by sase-core and used everywhere:
   `→ coder + commit · 1 change · 🧠 tui.md`. It appears in the TUI outcome line, on the
   Telegram primary button and completion reply, in the CLI result and dry run, and in
   notifications. Every surface describes the same review in the same words.
3. **ACE: an accordion Decisions section in the left rail, above a compact, docked
   Verdict.**
   - Unfocused decisions take two lines each. The focused one expands to show its full
     question, every choice with its consequence, and the planner's reason.
   - Space, `h`/`l`, or ←/→ change a value, and `r` resets it. **Enter still approves
     as shown.**
   - The document pane is linked to the rail. Focusing a decision scrolls to its branch
     in the plan. The branch you picked is highlighted, and the one you didn't pick is
     dimmed.
4. **Telegram: the review message itself is the form.**
   - The message text is a static question sheet. The keyboard holds the live answers.
   - A toggle flips in place. A choice swaps the keyboard for a radio sub-keyboard,
     also in place, and goes back on selection.
   - The primary button reads **✅ Tale · defaults** or **✅ Tale · 1 change**. No new
     messages and no step flow.
   - When the review settles, the message is edited once to show the answers.
   - A plan that `%auto` approves with decisions gets a silent receipt.
5. **CLI: `-D id=value` (`--decide`) on `sase plan approve`.**
   - Every approval prints a decision card.
   - `sase plan show` gains a DECISIONS section, and `sase plan validate` gains decision
     diagnostics with fixes.
   - No interactive prompts in v1.
6. **Two small authoring additions, because they make the review experience much
   better.**
   - An optional one-line `why:`: the planner's reason for its default.
   - **Branch callouts** in the body, `> [!decision] grouping = mode`. These tie each
     answer to the prose it selects, so every surface can show the road not taken.
7. **Memory decisions show their consent trail.**
   - `✓ you asked: "<quote>"`, `not asked`, or `⚠ quote not found · off`.
   - The note's type: a `core` note costs context on every turn.
   - The note's status: new or existing.
   - An unrequested memory edit can only be switched on by a human.
8. **A rollout decision the earlier report left open.**
   - Compile decisions into the plan options' **raw `input_schema`** plus
     `payload.decisions`, not into generic declared `inputs`.
   - Otherwise every generic surface would treat decisions as ordinary gate inputs. The
     Telegram step flow would prompt each one in its own message, the TUI would show an
     `✎ inputs` badge, and the inbox card would list them twice.

## Contents

- [What I kept and what I changed](#what-i-kept-and-what-i-changed)
- [Design principles](#design-principles)
- [The shared design language](#the-shared-design-language)
- [Authoring additions that pay off at review time](#authoring-additions-that-pay-off-at-review-time)
- [ACE TUI](#ace-tui)
- [Telegram](#telegram)
- [CLI](#cli)
- [Auto approval, notifications, and the rest of the system](#auto-approval-notifications-and-the-rest-of-the-system)
- [Cross-surface state matrix](#cross-surface-state-matrix)
- [Alternatives I rejected](#alternatives-i-rejected)
- [Implementation notes](#implementation-notes)
- [Open questions for you](#open-questions-for-you)
- [Sources](#sources)

## What I kept and what I changed

**I kept these from the canonical report without change:**

- The `decisions:` map with `ask`, `choices`, `default`, `memory`, and `requested`.
- At most five decisions, and a required default on each.
- Word-for-word verification of the `requested:` quote against text a human wrote.
- A frozen decision set for each review.
- `answer:` and `decided_by:` stamped into the archive.
- The coder's "Reviewer decisions" block, and DECISIONS shown in `bead read`.
- `%auto` takes the defaults.
- A fixed epic graph, a beta flag, and a later memory guard.

**I changed or added these, with the reason for each:**

| Topic | Canonical report | This report | Why |
| --- | --- | --- | --- |
| ACE layout | Decisions above Verdict, with every row fully expanded | **Accordion**: only the focused row expands. Verdict becomes compact and is **docked** to the bottom of the rail. | The rail is 42 cells wide and roughly 27 of its ~30 rows are already in use at 120×40. Five expanded decisions do not fit, and scrolling Verdict out of view is worse. |
| Document pane | Unchanged | **Linked to the rail.** The focused decision scrolls to its branch, the chosen branch is highlighted, and the unchosen one is dimmed. The `decisions:` frontmatter folds to one line. | The reviewer judges a choice by reading what it selects. |
| Telegram | Approve as shown, plus a "🎛 Change decisions" button that opens the step flow (one new message per input) | **The keyboard is the form.** Toggles flip in place and choices drill down in place. The primary button carries the change count. | The step flow sends a new message for each input, shows no defaults, and has no Back. Skip deletes the key, and a `bool` needs a typed reply. |
| Change marker | `•` in the accent colour | Gold **`●`** | ACE's Config pane already marks a changed value with a gold `●` (`config_pane_rendering.py:246`). |
| Choice glyph | `◆` | **`⋔`** (fork) | `◆` already marks epic phases in `plan show` and the PLAN lane (`_plan_display_rendering.py:219,418`). |
| Decision label | Humanized id (`Grouping`) | **The id itself**, shown in monospace | One name per decision on every surface, and it is the name you type in `-D`. |
| Rationale | None | Optional **`why:`** | Spec Kit pairs each recommended option with its reasoning. NN/g found that users read defaults as endorsements, so the endorsement should be explained. |
| Branch prose | The body "mentions" the id | **`> [!decision] id = choice` callouts** | These make dimming, linking, validation, and a precise coder block possible. The syntax is native to Obsidian and degrades to a blockquote everywhere else. |
| Wire shape | Left open: declared `inputs` or raw `input_schema` | **Raw `input_schema` plus `payload.decisions`** | This keeps every generic input UI from prompting for decisions ([details](#rollout-gotcha-generic-input-surfaces)). |

## Design principles

1. **One review, one place.** Decisions sit inside the plan review on every surface,
   never behind a secondary screen. Hidden controls go unused: human reviewers set the
   `c` inputs in 0 of 54 tale reviews.
2. **Approving the defaults costs nothing.** About 73% of tale approvals and 82% of
   epic approvals are automatic, and human reviewers almost always take the default
   verdict. Enter, `✅`, and a bare `sase plan approve` must keep meaning "approve as
   shown".
3. **The default is shown and explained.** `★` sits on the planner's default
   everywhere, and an optional `why:` explains it. A reviewer should never have to guess
   what happens if they do nothing.
4. **Changes are obvious.** A gold `●` marks a changed value. The change count appears
   in the outcome sentence and on the primary button. Reviewers cannot miss what they
   altered.
5. **Memory is consent.** Every memory decision carries `🧠` and shows where its default
   came from. An unrequested memory edit is off and only a human can switch it on.
   Treat it like a GDPR opt-in, never a pre-ticked box.
6. **The plan shows its branches.** Every choice points at the prose it selects. The
   reviewer sees both the selected branch and the one left behind.
7. **One name, one sentence.** Ids are the handles on every surface. sase-core writes
   the summary sentence once, so the TUI, Telegram, and the CLI cannot drift apart. This
   follows the
   Rust core boundary rule of thumb from sase's instructions: if every frontend needs it
   identical, it is core.
8. **Fail safe and predictable.**
   - An omitted value means the default.
   - An unknown id or value is an error before anything happens.
   - The decision set is frozen for the review.
   - A surface that does not understand decisions still settles correctly.

## The shared design language

### Vocabulary

| Term | Meaning | Where |
| --- | --- | --- |
| **Decisions** | The plan's open choices. This is the new section title. | All surfaces |
| **Verdict** | The existing Tale/Epic, Reject, and Feedback branches. Renamed from ACE's "Decision" heading so the two words don't collide. | ACE |
| **default** (`★`) | The planner's recommended value: what Enter, `✅`, and `%auto` take. | All surfaces |
| **changed** (`●`) | The value differs from the default. | All surfaces |
| **on / off** | The display words for toggles. YAML stays `true`/`false`. The CLI accepts `on/off/yes/no/true/false/y/n/1/0`, the same parsing `sase gate answer` uses. | All surfaces |
| **you asked** / **not asked** | Provenance of a memory default. | All surfaces |
| **decided by** | `reviewer`, `auto`, or `cli`, plus the surface (`TUI`, `Telegram`, `CLI`). | Archive, `plan show`, receipts |

### Glyphs and colours

All colours below already exist in ACE's palettes.

| Glyph | Meaning | Colour |
| --- | --- | --- |
| `⋔` | A choice decision | `#AF87FF`, the PLAN subheader colour |
| `☑️` / `⬜` | A toggle that is on or off. These are the same glyphs as the existing AND toggles: anything that shows them flips with Space. | Default |
| `🧠` | A memory decision. The note chip uses `#87AFFF`, the path colour. | — |
| `★` | The planner default | `#AF87FF` |
| `●` | Changed from the default | `#FFD700`, gold, as in the Config pane |
| `◉` / `○` | Selected and unselected options inside an expanded choice | `#00D7AF` / dim |
| `✓ you asked` | A verified memory request | `#5FD787` |
| `⚠ quote not found` | The claimed request could not be verified, so the default was forced off | `#FFAF5F` |
| `core` chip | The note is inlined into every turn | `#FFAF5F` |
| `reference` chip | The note is read on demand | Dim |
| `new` chip | The note or strand does not exist yet | `#5FD787` |

No meaning is carried by colour alone. Every state also has a glyph or a word.

### The summary sentence

sase-core exposes one formatter, for example
`render_decision_summary(decisions, answers, form)`, with two forms.

- **Short:** `1 change · 🧠 tui.md`.
  - When nothing changed: `defaults · 🧠 tui.md`.
  - When every memory decision is off: `defaults · 🧠 no memory edits`.
  - When the plan has no memory decisions, the 🧠 clause is omitted.
- **Full:** `grouping=mode● · tui_note=on 🧠 · glossary_term=off`, in declaration
  order.

The TUI outcome line puts the verdict in front of it (`→ coder + commit · …`). Telegram
uses the short form on the primary button and the full form in the completion reply. The
CLI prints the full form in dry runs and approvals. Notifications and `%auto` receipts
use the full form.

### Copy rules for planners

These go into the `/sase_plan` skill.

- **`ask`** is one question that ends in `?`. A toggle is phrased so that **on means do
  the work** ("Record … in the tui memory note?").
- **A choice's consequence** is one line that says what changes, not why ("By leader
  mode; denser, but splits pane actions").
- **`why:`** is one line that says why the default is the default ("pane keeps the
  footer's order").
- **Ids** are short nouns (`grouping`, `tui_note`, `keep_shim`). Reviewers see them, so
  `opt1` and `q2` are not acceptable.

## Authoring additions that pay off at review time

```yaml
decisions:
  grouping:
    ask: How should the overlay group bindings?
    choices:
      pane: By pane, matching the footer hints
      mode: By leader mode; denser, but splits pane actions
    default: pane
    why: pane keeps the footer's order          # NEW, optional, ≤100 chars
  tui_note:
    ask: Record the overlay's keymap conventions in the tui memory note?
    memory: [tui.md]
    requested: "and note the convention in the tui memory"
    default: true
```

### `why:`, the planner's reason for its default

- **Where it appears:** in ACE it is the `★` line of the expanded row. In Telegram it
  is appended to the default's line in the question sheet. In the CLI it appears in
  `plan show`.
- **Constraints:** it is optional and at most 100 characters. It is rejected on memory
  decisions, because their default is set by policy, not by preference, and the
  provenance chip already explains it.

### Branch callouts: one decision, one visible branch

The body marks the prose that each answer selects:

```markdown
## Grouping

> [!decision] grouping = pane
> Order sections by pane (Agents, Artifacts, Services), reusing the footer hint order.

> [!decision] grouping = mode
> One section per leader mode; pane-local actions sit under the mode that owns them.

## Memory

> [!decision] tui_note
> Add a "Help overlay" bullet to `tui.md` stating the grouping rule.
```

**Grammar:**

- `> [!decision] <id> = <choice>` marks a branch of a choice.
- `> [!decision] <toggle_id>` marks content that applies when the toggle is on.
- `> [!decision] <toggle_id> = off` is the rare off-branch.
- A callout runs until the end of its blockquote.

**Why this syntax:**

- It is an Obsidian callout. You read plans in Obsidian, where it renders as a titled
  callout.
- GitHub and pandoc render it as an ordinary blockquote, so it never breaks a reader.
- The TUI already lexes the body with Pygments' Markdown lexer, and the result is a
  Rich `Syntax` whose `stylize_range` can dim or highlight line ranges. The mock images
  were made exactly that way.

**What it unlocks:**

| Surface | Effect |
| --- | --- |
| ACE | Live dimming of unselected branches. Focusing a decision scrolls to its branch. |
| `plan show` (after approval) | The selected callout is tagged `✓ selected` and the others are dimmed. |
| Telegram | The body preview and PDF show `⋔ grouping = mode` headings. |
| Coder block | Lists exactly which callouts to implement: "Implement `grouping = mode`; ignore `grouping = pane`". |
| `plan validate` | Checks every callout against the declared decision ids and choices. |

**Validation rules:**

- **Error:** a callout names an unknown id or choice. This catches typos.
- **Warning:** a choice has no callout and its id is not mentioned anywhere.
- **Not a requirement:** callouts are not mandatory in v1. Some decisions are a single
  parameter that one sentence covers.

### Ordering

Decisions render in YAML order, except that **memory decisions always render last** as
their own group. The planner keeps control of importance among plan choices, and consent
items still form one visual block that is easy to scan.

## ACE TUI

### What constrains the design today

- **The plan modal's left column is 42 cells wide**, about 37 of them usable
  (`styles.tcss:1766-1777`). At 120×40, the tale controls already use about 27 of the
  column's roughly 30 rows. Every verdict control is a 3-row Textual `Button`, and the
  commit toggle wraps ("…plans s / idecar"), as the sase snapshot
  `tests/ace/tui/visual/snapshots/png/plan_gate_tale_five_controls_120x40.png` shows.
- **Enter has `priority=True`** and always submits the primary branch, whatever has
  focus (`keymaps/bindings.py:134-146`). Digits 1–9 submit branch N.
- **`_EnumField` cycles in place on Enter** (`typed_input_form.py:142-183`). That
  meaning of Enter conflicts with the modal's. A `bool` has **no widget** and falls back
  to a text box (`:323`). Decisions therefore need their own compact controls, not
  `TypedInputForm`.
- **ACE uses no Textual `RadioSet`, `Switch`, or `Collapsible`.** Its own idioms are the
  `☑️`/`⬜` AND toggles, the `►/▼` optional-inputs toggle, and the Config pane's gold
  `●`.
- **Textual 8.0.1 `Button` supports `compact=True`** (verified), which makes 1-row
  buttons a native option.

### Layout

Two states are shown below: a focused choice decision (top of report) and a focused
memory decision with the document scrolled to its branch.

![Focused memory decision. The tui_note row is expanded, showing the full question, the note chip "tui.md · reference · edit", and the quoted request "✓ you asked: 'and note the convention in the tui memory'". The grouping row is collapsed to two lines and shows "mode ●". The document pane shows the tui_note callout highlighted and the glossary_term callout dimmed because it is off.](plan_decisions_review_ux__cld_tui_memory.png)

The left rail holds three stacked parts. Width goes from 42 to **50 cells** when a plan
has decisions. The document keeps about 64 columns at 120 wide, and the narrow
breakpoint is unchanged.

1. **Actions** (`e ✏️ Edit plan`) takes one line. The "Accepted only when
   `sase plan validate` passes" hint moves into the refusal banner, where it matters.
2. **Decisions** has the header `Decisions  3 · 🧠 2` and holds the accordion rows. It
   scrolls if necessary.
3. **Verdict** is docked to the bottom of the rail, so it is always visible.
   - Line 1: the AND toggles with short labels: `☑️ 🚀 Launch coder  ☑️ 💾 Commit plan`.
     The long "to the plans sidecar" text moves to a tooltip.
   - Line 2: compact buttons `1 ✅ Tale  2 ❌ Reject  3 💬 Feedback`. Tale keeps the
     success variant.
   - Line 3: the outcome line, `→ coder + commit · 1 change · 🧠 tui.md`.
   - The Cancel button is dropped: `q` and Esc already cancel, and the footer says so.

**Make the compact Verdict the standard plan-review look, decisions or not**, so the
layout does not jump between plans. Custom gates can adopt it later.

### Row anatomy

**Collapsed rows** take two lines:

```
⋔ grouping                        mode ●
    How should the overlay group bindi…
☑️ 🧠 tui_note                      on ★
    tui.md · reference · ✓ you asked
```

- Line 1 holds the kind glyph, the id, and the value on the right with `★` or `●`.
- Line 2 holds the `ask`, truncated with `…`. A memory row shows its scope chips there
  instead.

**A focused choice** has a cyan `▌` bar and a tinted background (`#1E2A36`):

```
▌⋔ grouping                     ‹ mode › ●
▌  How should the overlay group bindings?
▌   ○ pane   By pane, matching the footer   ★
▌            hints
▌   ◉ mode   By leader mode; denser, but
▌            splits pane actions
▌  ★ pane keeps the footer's order
```

**A focused memory toggle:**

```
▌☑️ 🧠 tui_note                       on ★
▌  Record the overlay's keymap conventions
▌  in the tui memory note?
▌  🧠 tui.md · reference · edit
▌  ✓ you asked: "and note the convention
▌    in the tui memory"
```

**The other memory provenance states:**

- Not requested: `⬜ 🧠 glossary_term  off ★`, with `glossary:help-overlay · new · not
  asked`.
- Quote failed verification:
  `⚠ "note it in tui memory" — not in your messages · off until you turn it on`, in
  the warn colour. The value starts off, matching the gate-build rule.
- A human switches on an unrequested memory decision: the row shows `on ●`, and the
  outcome line gains that note. No confirmation dialog is needed, because the reviewer
  is the human the policy is waiting for.

**When the focused row expands**, the modal opens with the **first decision focused**,
so its question is visible without any action. This is a small, unobtrusive nudge
against rubber-stamping. Enter still approves at once.

### The document pane

- **Fold the `decisions:` frontmatter** to a single dim line:
  `decisions: 3 · answered in the Decisions panel`. The panel shows every field the
  YAML contains, so nothing is lost. `Y` (copy all) and `e` (edit) still work on the
  raw file.
- **Callout styling** is recomputed on every value change, using
  `Syntax.stylize_range` on the cached token stream:
  - The selected branch gets a green tint and a bold header.
  - An unselected branch, or a toggle that is off, is dimmed and italic.
  - Callouts are never hidden. The reviewer should see what they are declining.
- **Focus follows.** Moving focus onto a decision scrolls the document to its first
  callout, or failing that its first mention, keeping the line about a third of the way
  down the pane. If there is neither, nothing scrolls, and `plan validate` already
  warned the planner.
- **Performance.** The work is tiny: re-styling at most a few dozen lines on a key
  press, with the token cache already keyed by content digest. It still deserves a pass
  against the `tui_perf` note during implementation.

### Keys

These are added to `ace.keymaps.gate` in `src/sase/default_config.yml`, as the gotchas
memory requires, and to the ACE help modal.

| Key | On a choice | On a toggle | Elsewhere |
| --- | --- | --- | --- |
| `j` / `k` | Move. The ring is Actions → Decisions → Verdict. | Move | Move |
| `space` | Next choice, wrapping around | Flip | Toggles an AND member, as today |
| `l` / `right` (`next_choice`) | Next choice | Turn on | — |
| `h` / `left` (`previous_choice`) | Previous choice | Turn off | — |
| `r` (`reset_decision`) | Reset to `★` | Reset to `★` | — |
| `enter` | **Approve as shown.** Never changes a value. | Same | Same |
| `1`–`9` | Submit branch N, as today | Same | Same |
| `ctrl+s` | Submit the focused branch. On a decision row, that means the primary. | Same | As today |

**Rejected:** digit hotkeys for choices, which collide with branch submit; and
first-letter hotkeys, which collide across choices and with the static keys.

**The footer's Enter badge becomes dynamic:** `Enter=Tale`, then
`Enter=Tale · 1 change` once something changes. It keeps today's style,
`bold #1a1a1a on #00D7AF`.

### States worth designing explicitly

- **Close and reopen.** Esc does not discard provisional values. They persist for each
  request id while ACE is running, extending the existing `PendingApproveState` used by
  the `c` → `p` round trip. Losing three careful choices because you closed the modal to
  look at an agent would feel broken.
- **In-review edit (`e`).**
  - Prose edits re-render the document and keep every value.
  - Edits that change the decision set reuse today's red "Draft not accepted" banner
    with the canonical wording: "Decisions are fixed for this review. Change them in
    the Decisions panel, or press 3 to send feedback that changes the set."
- **Feedback (`3`).** The note panel shows a read-only first line,
  `Carries: grouping → mode`, so the reviewer knows the replanner will receive those
  values as its new defaults.
- **`i` and `c` ignore decisions.** `i` (inputs) and `c` (Custom Approval) never show
  decisions, and the Tale button gets no `✎ n inputs` badge for them. Decisions exist
  only in the Decisions section.
- **Narrow layout** (below 100 columns, rail docked at the bottom at 48% height). The
  same accordion applies, with Verdict docked last. At 90×40 that leaves about 11 rows
  for decisions, which is enough for three collapsed rows plus one expanded.
- **Epic review.**
  - The Verdict is a single line: `1 ✅ Epic  2 ❌ Reject  3 💬 Feedback`.
  - The outcome line reads `→ epic launch · 1 change · 🧠 tui.md`.
  - Decisions apply to the whole epic, so the rail rows are identical.

### Around the modal

- **Toast.**
  - Tale: "**Tale** ready for @agent: **file.md**", with a second line
    `3 decisions · 🧠 2`.
  - Epic: the existing phases/waves line gains the same clause.
- **Inbox row.** Append `· ⋔3 🧠` after the file count, and leave everything else
  unchanged.
- **Inbox gate card** (`notification_modal_gate.py`). Add a **Decisions** block under
  the status line.
  - Pending: `⋔ grouping  pane ★`.
  - Answered: `grouping: **mode** ●`.
  - Without this block, the generic field list would show every decision twice, once
    each under `approve` and `commit`.
- **PLAN lane and agent prompt panel, after approval.** They render the same DECISIONS
  section as `sase plan show`, using the shared `_plan_display_rendering` builders. The
  TUI and the CLI then cannot diverge.

## Telegram

### What constrains the design today

- **Rendering.** Plan reviews are MarkdownV2 messages: a properties card, the body
  preview in an expandable blockquote, and a PDF sent afterwards. A `decisions:` block
  would render today as **raw YAML lines** in the properties card
  (`formatting.py:556-738`).
- **Toggle idiom.** AND-group toggles flip `☑️`/`⬜` by editing the keyboard in place
  (`gate_callbacks.py:193-209`). State lives in `<bundle>/telegram_gate_progress.json`.
- **Declared-input step flow.** Each input is a **new message** and the old keyboard
  stays live (`gate_response.py:162-186`).
  - Defaults are never shown.
  - **Skip deletes the key** (`gate_inputs.py:146-150`).
  - A `bool` has no buttons and needs a typed reply.
  - There is no Back button.
- **Settling.** The keyboard is stripped and a separate "✅ Gate plan/<id> answered with
  approve, commit" message is sent. **The review message's text is never updated**
  (`gate_completions.py:53-76`).
- **Auto-resolved gates send nothing**, because they create no notification
  (`notification_gates/service.py:97`, verified).
- **Bot API.**
  - `callback_data` is 1–64 bytes, and the `gate:<8>:` prefix leaves 50 bytes for the
    token.
  - Clients released after 9 February 2026 honour an inline button `style`:
    `success`, `danger`, or `primary`.
  - Telegram recommends editing keyboards in place for settings-style interactions.

### The design

![Telegram mock in four panels: the live review message with a Decisions question sheet and a keyboard of decision rows, AND toggles, a green "✅ Tale · 1 change" button, and Reject/Feedback; the in-place radio sub-keyboard for grouping, with "○ pane ★", "◉ mode ●", and "↩ Back"; the same message after settling, edited to show the answers; and a silent %auto receipt.](plan_decisions_review_ux__cld_telegram.png)

**1. The message text is a static question sheet.** It is placed **before** Properties,
because it is the only part of the message you act on.

```
📋 CLAUDE(opus) Plan Review  @5m--plan
Tale ready for review: keymap_help_overlay.md

🎛 Decisions · 3
1. grouping — How should the overlay group bindings?
   ★ pane · By pane, matching the footer hints — pane keeps the footer's order
     mode · By leader mode; denser, but splits pane actions
2. 🧠 tui_note — Record the overlay's keymap conventions in the tui memory note?
   ★ on · tui.md (reference) · ✓ you asked
3. 🧠 glossary_term — Add a help-overlay glossary strand?
   ★ off · glossary:help-overlay (new) · not asked
━━━━━━━━━━━━━━━━━━━━
🧾 Properties …         (decisions: is removed from this card)
▸ Implementation …      (expandable, as today)
```

**Why the text stays static.** The live values live in the keyboard. Each tap calls
`editMessageReplyMarkup` only. It never rewrites a long MarkdownV2 message, which
would risk entity errors and "message is not modified" failures, and would make the
text jump.

**The length budget, in priority order:**

1. Header.
2. The Decisions sheet, which is never cut in the middle of a decision.
3. Properties.
4. Body.

If the sheet alone exceeds about 1,800 characters, it degrades in this order:

1. Drop the consequences of non-default choices.
2. Drop the remaining consequences.
3. Wrap the choice lines in an expandable blockquote.

The `ask` and the `★` line always survive.

**2. The keyboard is the answer sheet.** It has one row per decision, placed above the
verdict rows:

```
[ ⋔ grouping: mode ● ▾ ]
[ ☑️ 🧠 tui_note ] [ ⬜ 🧠 glossary_term ]    ← toggles pair up when both labels fit
[ ☑️ 🚀 Launch coder ] [ ☑️ 💾 Commit plan ]
[ ✅ Tale · 1 change ]                          ← style: success
[ ❌ Reject ] [ 💬 Feedback ]
```

The interaction rules:

- **A toggle** flips in place. Its toast echoes the effect and reads like a receipt:
  "🧠 glossary_term on — authorizes editing glossary:help-overlay".
- **A choice (`▾`)** swaps the keyboard, still in place, for a radio sub-keyboard:
  `[○ pane ★] [◉ mode ●] [↩ Back]`.
  - The opening toast shows the `ask` (`answerCallbackQuery` text is limited to 200
    characters).
  - Picking a value returns to the main keyboard and toasts `grouping → pane`.
  - One rule covers every choice: "`☑️`/`⬜` rows flip; `▾` rows open."
  - Two-choice decisions also drill down, for consistency, and because the sheet
    explains both options anyway.
- **The primary label:**
  - `✅ Tale · defaults` while nothing has changed, `✅ Tale · 2 changes` afterwards.
  - Epic: `✅ Epic · …`.
  - It uses the short form of the summary sentence. Labels stay under about 30
    characters, the point where clients begin truncating.
- **Long labels.** A decision label longer than about 28 characters falls back to the
  id alone. The value is visible in the sheet anyway.
- **Callback tokens** are `d<i>` (flip or open), `d<i>c<k>` (choose), and `db` (back),
  all a few bytes long. Values are stored next to the AND-toggle state in
  `telegram_gate_progress.json`.
- **Stale taps** after the gate settles toast "Already decided — see the summary
  above".

**3. On settle, the review message is edited once.**

- The Decisions sheet is replaced by
  `✅ Tale approved · 👤 you via Telegram · 14:02` and the answers
  (`1. grouping → mode ● (★ pane)` …), and the keyboard is removed.
- The completion reply carries the full summary sentence:
  `✅ Tale approved · grouping=mode● · tui_note=on 🧠 · coder launched`.
- The same edit applies when the review is settled from **another surface** (TUI or
  CLI), so the phone never shows a stale question sheet. The existing post-poll cleanup
  path is where this hooks in.

**4. Feedback.** `💬 Feedback` carries the current keyboard values to the replanner as
provisional defaults, exactly as in the TUI. The prompt asking for the note should
**ask for a reply** to the review message. Today an unreplied text can fall through and
launch a new agent when several prompts are waiting (`text_messages.py:135-176`). That
hazard is worth fixing in the same pass.

**5. The PDF.** Prepend a rendered Decisions table to the pandoc input, and render
callouts as labelled blockquotes (`⋔ grouping = mode`). Pandoc otherwise drops unknown
frontmatter keys, so today the PDF would never mention the decisions.

### Why not the step flow, a Mini App, or rich messages

- **The step flow**, even reached through an opt-in "🎛 Change decisions" button, costs
  N new messages, hides defaults, and has no Back. Decisions are at most five small
  closed choices, which is exactly what an in-place keyboard handles well.
- **A Telegram Mini App** (`web_app` button) could host a beautiful form, but it is a
  web frontend to build, host, and authenticate. Revisit it only if decisions ever gain
  free text or more than five entries.
- **Bot API 10.1/10.2 rich messages** (`sendRichMessage`, with tables and `<details>`)
  could render the question sheet as a real table. They are worth trying once
  sase-telegram adopts them, but they are not needed for v1.

## CLI

![CLI mock with four parts: plan show with a DECISIONS section; plan approve -D grouping=mode --dry-run printing a decision card with value sources; a strict error for -D grouping=tree that lists the allowed choices; and plan validate diagnostics for an unverified requested quote and a missing branch callout.](plan_decisions_review_ux__cld_cli.png)

### `sase plan approve … -D/--decide ID=VALUE`

`-D` is free on `plan approve`. It also matches the most familiar "define a named value"
flag in tooling (`cc -DNAME=…`, `java -Dkey=value`). Read the `cli_rules` note before
landing it: options sorted alphabetically, a short alias for every option, and coloured
help.

- **The flag is repeatable.** Giving the same id twice is an error, not "last wins",
  because an approval should not be ambiguous.
- **Choices need the exact key**, matched case-insensitively. Prefix matching would make
  `-D grouping=m` silently change meaning if a `minimal` choice were ever added.
- **Toggles accept** `on/off/yes/no/true/false/y/n/1/0`.
- **Unknown ids or values fail before any side effect** and list what is allowed, with
  `★` on the default:

  ```
  error: -D grouping=tree: 'tree' is not a choice for grouping
    choices: pane ★  By pane, matching the footer hints
             mode    By leader mode; denser, but splits pane actions
    nothing was approved
  ```

- **Turning a memory decision on from an agent process fails** with a human-readable
  reason: "memory decisions can only be switched on by a human; this shell runs inside
  agent `5m--plan`". This is the CLI face of the rule "An agent process cannot submit
  `-D <memory>=yes`".
- **`-D` works on epics too**: `sase plan approve big_epic -k epic -D x=y`.

### The decision card

Every approval with decisions prints this card. With `-n/--dry-run` it prints the
card and stops.

```
◇ Dry run · tale · keymap_help_overlay
  grouping       mode ●   -D        was ★ pane
  tui_note       on   ★   default   🧠 tui.md · you asked
  glossary_term  off  ★   default   🧠 not asked
  → coder + commit · 1 change · 🧠 tui.md
```

The source column (`-D` or `default`) follows the advice in Copier and clig.dev: show
where each value came from. **A bare `sase plan approve` still approves at once.** The
card is the confirmation, not a prompt.

### `sase plan show`

Add a **DECISIONS** section, placed before PROPERTIES because it is the most decision-
relevant part. It uses the existing `_print_section` and `_detail_table` helpers and
the PLAN palette.

- **Pending:** the ask, the choices with consequences, `★` on the default, the `why`
  line, and memory chips.
- **Approved:** the header reads `decided by reviewer · TUI · <time>`. The answer is
  `◉` with `● changed` where it differs, and unselected choices are dimmed.
- **`-f compact`:** add `⋔3 🧠1` to the one-line view.
- **`-f json`:** add
  `plan.decisions[]{id, kind, ask, why, choices[{key,label}], default, memory[{selector,type,exists}], requested, requested_verified, answer, changed}`
  plus `decided_by` and `decided_via`.

### `sase plan list`, `validate`, `gate`, and `bead read`

- **`sase plan list`:** the Proposed table gains a narrow `⋔` column (`3 🧠2`).
- **`sase plan validate`:** new diagnostic codes use the existing
  `path:line: severity [code] message` format. Each message says how to fix the
  problem.

  | Code | Severity |
  | --- | --- |
  | `decision-limit` | error |
  | `decision-id-reserved` | error |
  | `decision-default-missing` | error |
  | `decision-default-invalid` | error |
  | `decision-answer-forbidden` | error |
  | `decision-requested-missing` | error |
  | `decision-requested-unverified` | error |
  | `decision-branch-unknown` | error |
  | `decision-why-on-memory` | error |
  | `decision-unreferenced` | warning |
  | `decision-memory-uncovered` | warning |
  | `decision-ask-not-question` | warning |

  - **Closest match.** `decision-requested-unverified` prints the **closest matching
    human sentence**, so the planner, while still alive, can fix the quote instead of
    guessing.
  - **Example.** `--explain` gains a decisions example.
  - **Echo.** `sase plan propose` echoes `3 decisions (🧠 2)`, so the planner sees what
    it shipped.
- **`sase gate show`:** a plan gate lists its decisions as a table instead of
  `raw schema: decision_grouping, …`. `sase gate answer -I JSON` remains the low-level
  path. `sase plan approve -D` is the human path.
- **`sase bead read`** (read by agents): a plain-text DECISIONS block, such as
  `grouping = mode  (planner default: pane) — How should the overlay group bindings?`,
  plus `Implement callout "grouping = mode"; ignore "grouping = pane".`

### Why no interactive prompts in v1

The sase CLI has no prompt library today; its only prompts are plain `[y/N]`
confirmations. clig.dev's rule is "never *require* a prompt", and the TUI is already the
interactive surface. A later `-i/--interactive` could walk the decisions with numbered
choices as an accessible fallback for the TUI. It should be added only if someone asks
for it.

## Auto approval, notifications, and the rest of the system

- **`%auto` receipts.** An auto-approved plan **with at least one decision** posts a
  **silent, informational** notification with
  `decided_by: auto` and the full summary sentence. It is an inbox row with no gate, and
  Telegram sends it with `disable_notification`.
  - Plans without decisions stay silent, as they are today.
  - This is the only way the user ever sees what `%auto` decided for memory, and it
    turns the default rate into a visible metric.
  - To reduce noise, you could limit receipts to plans whose decisions include memory
    ([open question 3](#open-questions-for-you)).
- **No undo after `%auto`.** Post-hoc overrides would mean relaunching or abandoning a
  coder that is already running. The receipt is for audit. If you disagree, send
  feedback on the result, as you would today.
- **Mobile gateway.** It renders from the notification snapshot. Until it learns
  `payload.decisions`, it settles with the defaults, which is safe. It should adopt the
  question-sheet and answer-sheet split later.
- **`/sase_questions` consistency follow-up.** The question modal and the Telegram
  question flow have no "recommended" marker today. The `★` language could reach them
  later, which would also fix the `%auto` "first option wins" oddity, if questions gain
  an explicit default.

## Cross-surface state matrix

| State | ACE rail | Telegram | CLI |
| --- | --- | --- | --- |
| Default, untouched | `mode ★` | Sheet `★ pane`; button `⋔ grouping: pane ▾`; primary `✅ Tale · defaults` | Card source `default` |
| Changed | `mode ●`, `Enter=Tale · 1 change` | Button `… mode ● ▾`, primary `· 1 change` | Source `-D`, `was ★ pane` |
| Memory, requested | `on ★ · ✓ you asked`; focus shows the quote | `★ on · ✓ you asked` | `🧠 tui.md · you asked` |
| Memory, not requested | `off ★ · not asked` | `★ off · not asked` | `🧠 not asked` |
| Memory, quote unverified | `⚠ … not in your messages · off` | `⚠ quote not found · off` | Approve card `⚠`; validate error |
| Human turns memory on | `on ●`; outcome lists the note | Toast "authorizes editing …" | Allowed from a human shell only |
| Settled here | Modal closes; the PLAN lane shows answers | Message edited to the answers; completion reply | Card printed |
| Settled elsewhere | Inbox card shows answers | Message edited to the answers; keyboard removed | `plan show` shows `decided by` |
| `%auto` | — | Silent receipt | `plan show` shows `decided by auto` |
| Surface without decision support | Defaults apply on submit | Defaults apply (raw `input_schema` is invisible to the generic flows) | — |

## Alternatives I rejected

| Alternative | Why not |
| --- | --- |
| Every decision row fully expanded in the 42-cell rail (canonical mock) | It overflows at 120×40 with three or more decisions and pushes Verdict out of view. The accordion shows the same information in less space. |
| A full-width decision strip under both panes | It is wide enough to show every option inline, but it costs the document 8–10 rows and splits the controls into two places with no j/k ring connecting them. |
| A Decisions tab, or decisions behind `c` | Hidden controls go unused: 0 of 54 human reviews set the `c` inputs. |
| Reusing `TypedInputForm` and `_EnumField` | Enter cycles values there, which conflicts with Enter-approves. A `bool` falls back to a text box. Each field is 3 rows or more. |
| Textual `RadioSet` and `Switch` | They are visually foreign to ACE, which uses none of them. `☑️`/`⬜` plus `◉`/`○` is the house idiom. |
| A humanized `label:` field | It gives every decision two names. The id is the name you type in `-D`. |
| Telegram step flow (canonical) | N new messages, no defaults shown, no Back, Skip deletes the key, and a `bool` needs a typed reply. |
| Telegram choices that cycle on each tap | It is fine for two options and clumsy for 3–5. One rule ("▾ opens") is easier to learn than two. |
| Rewriting the message text on every Telegram tap | It is fragile with long MarkdownV2 messages and visually jumpy. The static sheet plus a live keyboard avoids it. |
| A confirmation when a human switches on an unrequested memory edit | The reviewer is the consent the policy is waiting for. A dialog would only train people to click through. |
| Requiring the reviewer to visit every decision | It adds friction to the roughly 25% of reviews done by humans and does nothing for the 75% done by `%auto`. Focusing the first decision is the gentle version. |
| Stripping unselected branches from the archive | It destroys the audit trail. The coder block names the selected callouts instead. |
| Compiling decisions into declared `inputs` | Every generic input surface would start prompting for them ([details](#rollout-gotcha-generic-input-surfaces)). |

## Implementation notes

### Rollout gotcha: generic input surfaces

If decisions become declared `inputs` on the `approve` and `commit` options, three things
happen with no other change:

- **Telegram** routes ✅ Tale into the step flow, sending one new message per decision
  with Skip buttons (`gate_callbacks.py:68-129`).
- **ACE** shows `✎ 3 inputs` on the Tale button, `i` opens a `TypedInputForm`, and the
  inbox card lists every field once per option.
- **`sase gate show`** lists them as generic fields.

**Recommendation.** Put decisions in the options' **raw `input_schema`**, which is
host-collected and invisible to the generic flows, as `coder_model` and `wait` are today.
Drive every dedicated UI from `payload.decisions`.

**Consequences:**

- Kind validation checks that the `input_schema` properties derived from
  `payload.decisions` match exactly. This is the equality check from the canonical
  report, moved to a different place.
- The canonical report's "an older surface still settles correctly" property becomes
  literally true: an old surface never sees the decisions, submits nothing, and the
  approve command fills in the defaults.

### What belongs where

- **sase-core.** It already owns schema validation, resolution, and quote verification.
  Add:
  - Parsing branch callouts and their validation diagnostics.
  - The summary-sentence formatter (both forms).
  - The closest-sentence suggestion for `decision-requested-unverified`.

  Every frontend needs these to match, so they are core by the boundary litmus test.
- **sase (Python).**
  - The compact Verdict and a docked rail. These are plan-modal CSS and
    `GateBranchControls` stacked-mode changes.
  - A `DecisionsSection` widget built from the rows above.
  - Callout styling in the document pane.
  - Gate keymap additions, mirrored in `default_config.yml` and the help modal.
  - Toast, inbox row, and inbox card blocks.
  - The PLAN lane and `plan show` sections, plus the CLI `-D` flag, card, and
    diagnostics rendering.
  - The `%auto` receipt.
- **sase-telegram.** This is a separate repo and its own follow-up bead.
  - The question sheet, the decision keyboard, the drill-down tokens, the primary label,
    the settle edit, the PDF table, and the reply-to fix for feedback.

### Visual coverage to add

Add these through `just fix-tui-screenshots`:

- `plan_gate_tale_decisions_120x40`, focused on a choice.
- `plan_gate_tale_decisions_memory_120x40`, focused on a memory decision with the
  document scrolled.
- `plan_gate_tale_decisions_unverified_120x40`.
- `plan_gate_tale_decisions_stacked_90x40`.
- `plan_gate_epic_decisions_120x40`.
- `notification_gate_decisions_pending_120x40` and
  `notification_gate_decisions_answered_120x40`.
- `plan_toast_tale_decisions_120x40`.

The existing `plan_gate_*` goldens change because of the compact Verdict. That is
intended, and should be reviewed as one group.

### Phasing

This slots into the canonical epic.

- Split the canonical `surfaces` phase into **`tui`** and **`telegram`**.
- Add callout parsing and the summary sentence to **`core`**.
- Land `policy` (the skill rules that make planners write decisions) last, as the
  canonical report planned. Agents should start emitting decisions only once ACE and
  Telegram both show them properly.

## Open questions for you

1. **Glyph.** Use `⋔` (fork) for choice decisions, or keep `◆` and move epic phases to a
   different glyph? I recommend `⋔`: phases are an older, wider convention.
2. **Branch callouts.** Recommended but optional (my recommendation), or required for
   every choice in v1? Required callouts make dimming and the coder block exact, but
   they burden one-parameter decisions.
3. **`%auto` receipts.** Send one for every auto-approved plan with decisions (my
   recommendation), or only when a memory decision is present?
4. **Compact Verdict everywhere.** Apply it to every plan review (my recommendation,
   because the layout stays stable), or only to plans with decisions?
5. **`why:`.** Add it now (my recommendation), or wait to see whether planners' choice
   consequences already carry enough of the reasoning?

## Sources

**Prior research (the user's accepted baseline):**

- `research:202610/plan_frontmatter_decisions/plan_frontmatter_decisions.md`, read
  through `sase artifact read`.

**Internal code** (sase `ca3a194423`; I read the code, and subagents read it under my
direction, all read-only):

- **Plan modal:**
  - `src/sase/ace/tui/modals/plan_approval_modal.py:151-235`, `plan_approval_gate_data.py:25-51`,
    `plan_approval_decisions.py:150-219`.
  - Rail CSS: `styles.tcss:1730-1830`.
  - Gate branch layout: `gate_branch_layout.py:51-92`.
- **Inputs:** `src/sase/ace/tui/widgets/typed_input_form.py:142-183,323` (enum cycling,
  the missing bool widget).
- **Keys:**
  - `src/sase/ace/tui/keymaps/bindings.py:134-146` (Enter priority).
  - `src/sase/default_config.yml` (`ace.keymaps.gate`).
- **Palettes:**
  - `src/sase/ace/tui/modals/config_pane_rendering.py:246` (gold `●`).
  - `src/sase/sdd/_plan_display_rendering.py:34-45,219,418` (PLAN palette, `◆`
    phases).
  - `src/sase/ace/tui/modals/notification_modal_palette.py`.
- **Document highlighting:** `src/sase/ace/tui/util/frontmatter_syntax.py`, which
  produces a Pygments YAML+Markdown token stream wrapped in a Rich `Syntax`.
- **Toasts and inbox:** `src/sase/ace/tui/actions/agents/_toasts.py:173-206`,
  `notification_modal_options.py:67-157`, `notification_modal_gate.py:158-366`.
- **Gates:**
  - `src/sase/notification_gates/service.py:97` (auto gates create no notification).
  - `adapters.py:46-74,334-362`.
  - `src/sase/plan_gate.py:225-272`.
- **CLI:** `src/sase/main/parser_plan.py:48-126`, `plan_approve_handler.py`,
  `plan_show_render.py:150-368`, `plan_validate_render.py:140-152`,
  `notification_gates/cli_answer.py:54-55,598-624`.
- **Visual snapshots:** `tests/ace/tui/visual/snapshots/png/plan_gate_tale_five_controls_120x40.png`,
  `plan_gate_frontmatter_120x40.png`, `gate_input_panel_group_120x45.png`.
- **Textual 8.0.1:** `Button(compact=True, flat=True)` signature, verified in the
  workspace venv.

**sase-telegram** (`d335fb8`, opened with `sase repo open`):

- Rendering and keyboard: `src/sase_telegram/formatting.py:98-104,556-738,1028-1223,1466-1617`.
- Callbacks and inputs: `callback_data.py:1-41`, `inbound_handlers/gate_callbacks.py:68-269`,
  `gate_inputs.py:146-150` (Skip deletes the key; verified).
- Responses: `gate_response.py:43-186`, `gate_completions.py:53-76`.
- `inbound_handlers/text_messages.py:106-176`: an unreplied text can launch an agent.

**External:**

- Telegram:
  - [Bot API](https://core.telegram.org/bots/api): `callback_data` 1–64 bytes,
    `answerCallbackQuery` text 0–200 characters, `editMessageReplyMarkup`.
  - [Bot features](https://core.telegram.org/bots/features): edit keyboards in place.
  - [`InlineKeyboardButton.style`](https://docs.python-telegram-bot.org/en/stable/telegram.inlinekeyboardbutton.html):
    `danger`, `success`, or `primary`, on clients after 9 February 2026.
  - [Bot API 10.2 rich messages](https://dev.to/unifyport/telegram-bot-api-102-migration-guide-rich-messages-ephemeral-edits-and-communities-gfe).
  - [Mini Apps](https://core.telegram.org/bots/webapps).
- AI planning tools:
  - [Claude Code user input / AskUserQuestion](https://code.claude.com/docs/en/agent-sdk/user-input)
    and the [tools reference](https://code.claude.com/docs/en/tools-reference).
  - [Spec Kit `/speckit.clarify`](https://github.com/github/spec-kit/blob/main/templates/commands/clarify.md):
    at most 5 questions, "Recommended: Option X – reasoning", answers written back into
    the spec.
- Terminal UI:
  - [charmbracelet/huh](https://github.com/charmbracelet/huh): inline selects and
    Confirm.
  - Textual [RadioSet](https://textual.textualize.io/widgets/radioset/) and the
    [widget gallery](https://textual.textualize.io/widget_gallery/).
  - [lazygit menu items](https://github.com/jesseduffield/lazygit/blob/master/pkg/gui/types/common.go).
  - [k9s delete dialog](https://github.com/derailed/k9s/blob/master/internal/ui/dialog/delete.go).
- Callouts:
  - [Obsidian callouts](https://help.obsidian.md/callouts): `> [!type] Title`, custom
    types allowed.
- CLI:
  - [clig.dev](https://clig.dev/).
  - [Copier configuring](https://copier.readthedocs.io/en/stable/configuring/).
  - [Terraform variables](https://developer.hashicorp.com/terraform/language/values/variables).
  - [gh workflow run](https://cli.github.com/manual/gh_workflow_run).
- Defaults and consent:
  - [NN/g: the power of defaults](https://www.nngroup.com/articles/the-power-of-defaults/).
  - [GOV.UK check answers](https://design-system.service.gov.uk/patterns/check-answers/)
    and [radios](https://design-system.service.gov.uk/components/radios/).
  - [Planet49 (pre-ticked consent is invalid)](https://en.wikipedia.org/wiki/German_Federation_of_Consumer_Organisations_v_Planet49_GmbH).
  - [Johnson & Goldstein 2003](https://www.science.org/doi/10.1126/science.1091721).
  - [Anthropic on approval fatigue (93% of prompts approved)](https://www.anthropic.com/engineering/claude-code-auto-mode).
- Approvals with parameters:
  - [Argo intermediate inputs](https://argo-workflows.readthedocs.io/en/latest/intermediate-inputs/).
  - [Slack radio buttons](https://docs.slack.dev/reference/block-kit/block-elements/radio-button-group-element).
