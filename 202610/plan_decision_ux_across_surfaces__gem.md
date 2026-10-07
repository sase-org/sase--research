# Plan Decisions: Unified UX Design Across TUI, Telegram, and CLI

> **Author:** researcher `gem`  
> **Topic:** User experience (UX) and interface design for embedded plan decisions across ACE (TUI), Telegram, and the CLI  
> **Date:** 2026-10-07  
> **Status:** Proposal / Design Specification  
> **Target Path:** `sase/repos/research/202610/plan_decision_ux_across_surfaces__gem.md`

---

## 1. Executive Summary & UX Thesis

### 1.1 The UX Thesis
When an agent writes a plan (tale or epic), it often faces secondary implementation forks: architectural trade-offs, configuration details, or policy-sensitive operations like modifying long-term memory. Today, the agent faces a false dichotomy: **interrupt early** via `/sase_questions` (forcing the user to answer without the context of a completed plan) or **guess** (burying optional paths in plan prose with no mechanical enforcement).

The architectural foundation established in prior research (`plan_frontmatter_decisions.md`) solves this mechanically by introducing **Plan Decisions**: typed, defaulted choices declared in frontmatter under `decisions:`, compiled into typed inputs on the gate's `approve` option, and stamped permanently into the archived plan upon approval.

However, the mechanical foundation is only as good as the **human experience** that wraps it. If configuring a decision is slow, confusing, or hidden behind obscure sub-modals, developers will ignore it or default-approve blindly.

The UX design for Plan Decisions is founded on three golden tenets:

1. **The Single-Key Default Path ("Enter to Approve"):**
   Plan decisions must **never** degrade the default review velocity. If the planner did its job and proposed sensible defaults, approving a plan must remain exactly **one keystroke (`Enter`)** in the TUI, **one tap** in Telegram, and **zero extra flags** in the CLI. Defaults carry the system.
2. **Zero Hidden State (Primary Surface Integration):**
   Crucial reviewer choices must never be relegated to secondary dialogs (like the `c` custom options modal, which telemetry reveals is opened in 0 out of 54 human reviews). Decisions must live directly on the primary review viewport across all surfaces.
3. **Live Outcome Projection (The "Contract" Line):**
   A user toggling an option should never wonder what side effects will follow. As decisions are toggled or cycled, a live, human-readable **Outcome Projection Line** dynamically summarizes the resulting agent prompt and authorization envelope before submission.

---

## 2. Core Interaction Model & Visual Language

### 2.1 The Two Decision Primitives
Plan decisions are deliberately constrained to two lightweight primitives:

| Primitive | YAML Syntax | Visual Glyph | Interaction (TUI) | Interaction (Telegram) | Interaction (CLI) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Toggle** | Boolean (`default: true/false`) | `☑️` / `⬜` | `Space` / Click | In-place switch button | `-D id=yes/no` |
| **Choice** | Enum map (`choices: {...}`) | `‹ slug ›` | `Space` (cycle forward)<br>`Shift+Space` (cycle back) | Inline keyboard menu | `-D id=slug` |

### 2.2 Visual Anatomy of a Decision
Each decision row conveys five pieces of information with maximum scannability:

```text
 [Glyph]  [Icon]  [Label / Ask]               [Current Value]    [Status / Provenance]
   ☑️       🧠     Record keymap conventions    yes                 ✓ requested
```

1. **State Glyph:** `☑️` (on/true), `⬜` (off/false), or `‹ slug ›` (active enum choice).
2. **Domain Icon:** Normal decisions carry a subtle bullet `◆` or category icon; **Memory Decisions** carry the brain icon `🧠` to signify durable knowledge modification.
3. **Ask / Label:** Concise, human-oriented question ending in `?`.
4. **Current Value:** The active setting. If altered from the planner's recommended default, it is badged with an accent bullet `•` and highlighted color.
5. **Provenance Chip:** For memory decisions, displays verification status:
   - `✓ requested`: Matched word-for-word against text authored by a human in the prompt history. Defaulted to `true`.
   - `not requested`: No explicit human request found. Defaulted to `false`.
   - `⚠ unverified`: Planner attempted to default to `true` without a matching quote. Forced to `false` by `sase-core`.

---

## 3. Surface 1: ACE Terminal User Interface (TUI)

The ACE Plan Review Modal is the primary workspace for interactive plan evaluation. Today, the left column features a generic "Decision" header containing branch buttons (`1 ✅ Tale`, `2 ❌ Reject`, `3 💬 Feedback`) and an obscure `c` key for host-collected properties.

### 3.1 Redesigned Modal Layout
The redesigned modal introduces a dedicated **Decisions** section positioned above the branch controls (which are renamed to **Verdict** to prevent nomenclature collisions).

```text
┌ Plan Review · claude/opus ──────────────────────────────────────────────────────────────┐
│ ✏️  Edit plan                         e │ sase_plan_keymap_help_overlay.md              │
│                                       │ ---                                           │
│ Decisions                     2 · 🧠  │ tier: tale                                    │
│                                       │ title: Keymap help overlay                    │
│ ◆  Grouping             ‹ mode ›  •   │ goal: Pressing ? in ACE shows active bindings.│
│      By leader mode; denser           │ size: small                                   │
│                                       │ decisions:                                    │
│ ☑️ 🧠 Record keymap conventions        │   grouping:                                   │
│      tui.md · reference · ✓ requested │     ask: How should the overlay group?        │
│                                       │     choices: ...                              │
│                                       │                                               │
│ ───────────────────────────────────── │ ## Grouping Trade-offs                        │
│ Outcome Projection                    │ If grouped by pane, bindings match footer...  │
│ → Tale coder · grouping=mode          │ If grouped by mode, bindings are denser...    │
│   Authorized: edit tui.md             │                                               │
│                                       │ ## Implementation Steps                       │
│ Verdict                               │ 1. Create overlay widget                      │
│ ☑️ 🚀 Launch coder agent               │ 2. Wire ? binding                             │
│ ☑️ 💾 Commit plan file                 │ 3. If tui_note: update sase/memory/tui.md     │
│ 1 ✅ Tale   2 ❌ Reject   3 💬 Feedback │                                               │
│ c Custom coder options                │                                               │
└───────────────────────────────────────┴───────────────────────────────────────────────┘
  Enter Tale · Space cycle/toggle · r reset · j/k navigate · e edit · 1–3 verdict
```

### 3.2 Component Breakdown

#### A. Decisions Section Header
- **Label:** `Decisions`
- **Metadata Counters:** Displays total decisions count and badges (e.g., `2 · 🧠` indicating 2 decisions including at least one memory modification).
- If a plan contains no decisions, the section is completely omitted, preserving the clean legacy layout.

#### B. Choice (Enum) Widget (`PlanDecisionChoice`)
- Displays the decision `ask` on line 1, followed by a compact horizontal stepper `‹ choice_key ›`.
- Line 2 displays the consequence description in dimmed italics (`By leader mode; denser`).
- **Interaction:**
  - Pressing `Space` cycles to the next choice.
  - Pressing `Shift+Space` (or Left Arrow) cycles to the previous choice.
  - For choices with >3 options, pressing `Enter` or clicking opens a lightweight popup dropdown.
  - An accent dot `•` in theme highlight color appears whenever the value differs from `default`.

#### C. Toggle Widget (`PlanDecisionToggle`)
- Displays `☑️` or `⬜` followed by the prompt text.
- For memory decisions, line 2 shows:
  `[selector] · [note_type] · [provenance_chip]`
  e.g.: `tui.md · reference · ✓ requested`
- **Interaction:**
  - Pressing `Space` or clicking flips the toggle.

#### D. The Outcome Projection Line
- Situated directly above the Verdict section.
- Framed with subtle horizontal borders.
- Re-renders instantly on any keystroke or toggle.
- Synthesizes the downstream contract into plain language:
  `→ Tale coder · grouping=mode · Authorized: edit tui.md`
- If an unrequested memory change is toggled on:
  `→ Tale coder · grouping=pane · Authorized: edit tui.md (MANUAL OVERRIDE)`
- This prevents "accidental approval" of sensitive actions.

#### E. Verdict Section
- Renamed from `Decision` to `Verdict`.
- Contains the existing branch execution options:
  - `1 ✅ Tale` (or `Approve` for non-tale plans)
  - `2 ❌ Reject`
  - `3 💬 Feedback`
- Retains `c` Custom options for underlying execution overrides (`coder_model`, `wait_spec`, `coder_prompt`).

### 3.3 Keyboard Ergonomics & Focus Flow
The modal adheres strictly to vim-friendly and standard accessibility navigation:

| Key | Context | Action |
| :--- | :--- | :--- |
| `j` / `k` or `Down` / `Up` | Left Column | Move focus between Decisions and Verdict items |
| `Space` | Focused Decision | Toggle boolean or cycle enum forward |
| `Shift+Space` | Focused Choice | Cycle enum backward |
| `r` | Focused Decision | Reset current decision to planner `default` |
| `R` | Anywhere in modal | Reset **all** decisions to planner defaults |
| `Enter` | Anywhere in modal | Submit active verdict (default: `Tale`/`Approve`) with current decisions |
| `1` | Anywhere in modal | Instant submit: Tale/Approve with current decisions |
| `2` | Anywhere in modal | Instant submit: Reject |
| `3` | Anywhere in modal | Instant submit: Feedback |
| `e` | Anywhere in modal | Open plan in `$EDITOR` (in-gate edit) |
| `c` | Anywhere in modal | Open custom coder properties modal |
| `Esc` | Anywhere in modal | Dismiss modal without action |

### 3.4 In-Gate Plan Editing (`e`) & Decision Freezing
When a user presses `e` to edit the plan in their external editor:
1. **Schema Freezing:** The decision *definitions* (`id`, `choices`, `memory` targets, `requested` quotes) are **frozen** for the review session.
2. If the user edits markdown prose or changes the wording of `ask:`, the modal reloads and updates smoothly.
3. If the user attempts to add, delete, or rename decision keys in the frontmatter, `validate_edited_resource` halts and displays a clear modal warning:
   > *"Decision keys are locked during review. To change decision values, use the TUI controls. To change the decision structure, submit Feedback (`3`) to request a replan."*

---

## 4. Surface 2: Telegram Bot Experience

The Telegram surface is used for mobile triage, notifications on the move, and remote plan approval. Telegram imposes hard constraints:
- **4,096 character** limit per message.
- **64-byte** callback data limit per inline button.
- Latency and UI jitter if multi-message wizards are introduced.

### 4.1 The Two-Tier Strategy: High-Density Card & Interactive Switchboard
Rather than forcing mobile users through a tedious multi-step wizard, Telegram employs a two-tier interaction model:
1. **Tier 1 (The Review Card):** Displays the full plan summary, all decisions, pre-selected defaults, and a single **"✅ Approve as shown"** button.
2. **Tier 2 (The Interactive Switchboard):** If the user wants to adjust decisions, tapping **"🎛 Change Decisions"** transforms the inline keyboard in-place into an interactive switchboard.

### 4.2 Tier 1: The Initial Review Notification Card

```telegram
📋 *CLAUDE(opus) Tale Review*  _@keymap_help_overlay_

*Goal:* Pressing ? in ACE shows every active binding.
*Tier:* tale  •  *Size:* small

🎛 *Decisions (preselected defaults):*
1. *Grouping:* `pane` (matching footer hints)
   _Options: pane | mode_
2. 🧠 *Record keymap conventions:* `yes` (✓ requested)
   _Target: tui.md (reference)_

*Outcome:* → Tale coder with `grouping=pane`, authorized for `tui.md`.

📖 *Plan Summary:*
Adding keyboard shortcut helper overlay in ACE TUI...
```

#### Inline Keyboard (Tier 1):
```text
┌─────────────────────────────────────────┐
│          ✅ Approve as shown            │
├────────────────────┬────────────────────┤
│ 🎛 Change Decisions│     ❌ Reject       │
├────────────────────┴────────────────────┤
│               💬 Feedback               │
└─────────────────────────────────────────┘
```

- **One-Tap Execution:** Tapping `[✅ Approve as shown]` immediately submits the gate with all defaults accepted. Zero friction.

### 4.3 Tier 2: The Interactive Switchboard Keyboard
When the user taps `[🎛 Change Decisions]`, the Telegram bot **does not** post a new message. Instead, it edits the message inline via `editMessageReplyMarkup`, replacing the keyboard with the **Decision Switchboard**:

```text
┌─────────────────────────────────────────┐
│ Grouping: ‹ pane ›                      │
├─────────────────────────────────────────┤
│ 🧠 tui.md: ☑️ YES (requested)           │
├─────────────────────────────────────────┤
│        ✅ Submit with choices           │
├────────────────────┬────────────────────┤
│ ↩️ Reset Defaults  │      ⬅️ Back        │
└────────────────────┴────────────────────┘
```

#### Callback Handling & Micro-Interactions:
1. **Tapping `[Grouping: ‹ pane ›]`:**
   - Callback data: `gate:<pfx>:c:grouping:mode`
   - Telegram bot instantly flips the button label to `Grouping: ‹ mode › •` and updates the Outcome line in the message body.
2. **Tapping `[🧠 tui.md: ☑️ YES]`:**
   - Callback data: `gate:<pfx>:t:tui_note:0`
   - Button instantly flips to `[🧠 tui.md: ⬜ NO •]`.
3. **Tapping `[✅ Submit with choices]`:**
   - Submits the gate with the overridden values.
4. **Callback Data Budget Optimization:**
   Telegram's 64-byte limit is respected using compact encoding:
   `gt:<pfx_6>:<action_1>:<dec_id_12>:<val_8>` (max ~32 bytes).

### 4.4 Tier 3: Settlement & Post-Approval Receipt
Once approved (whether via one-tap or switchboard), the Telegram message updates to a permanent receipt:

```telegram
✅ *Tale Approved*  _@keymap_help_overlay_
*Approved by:* Bryan (Telegram) • *Runtime:* 12s

*Decisions Applied:*
• *grouping:* `mode` (overrode default `pane`)
• 🧠 *tui_note:* `yes` (authorized: `tui.md`)

🚀 Coder agent launched (`claude/opus`).
```

---

## 5. Surface 3: Command Line Interface (CLI)

The CLI serves power users, scripts, CI checks, and headless terminal environments. It must adhere strictly to `cli_rules.md` (sorted options, short aliases, colored Rich output, comprehensive `--help`).

### 5.1 Inspecting Plans: `sase plan show`
`sase plan show` gains a prominent, colorized **DECISIONS** table placed immediately between PROPERTIES and BODY:

```bash
$ sase plan show keymap_help_overlay
```

```text
Keymap help overlay                                                            tale
Pressing ? in ACE shows every active binding, grouped for scanning.
───────────────────────────────────────────────────────────────────────────────────
PROPERTIES
    reference     plan:202610/keymap_help_overlay.md
    title         Keymap help overlay
    tier          tale
    size          small
    validation    ok
───────────────────────────────────────────────────────────────────────────────────
DECISIONS (2)
  ID         KIND    DEFAULT  CURRENT  PROVENANCE    ASK / CONSEQUENCES
  grouping   choice  pane     pane     -             How should overlay group bindings?
                                                     • pane: By pane, matching footer [default]
                                                     • mode: By leader mode; denser
  tui_note   toggle  true     true     ✓ requested   Record keymap in tui memory note?
             [🧠]                                    • Memory scope: tui.md (reference)
                                                     • Quote: "and note the convention..."
───────────────────────────────────────────────────────────────────────────────────
OUTCOME PREVIEW
  → Tale coder agent with grouping=pane
  → Authorized memory modifications: tui.md
───────────────────────────────────────────────────────────────────────────────────
BODY
# Keymap help overlay
...
```

For JSON consumers (`sase plan show --format json`), the decisions map is emitted with full structural typing and resolution metadata.

### 5.2 Approving with Decisions: `sase plan approve`

#### A. Flag Grammar
The `sase plan approve` command is extended with repeatable decision overrides:

- `-D, --decide KEY=VALUE`: Override a specific decision. Can be specified multiple times.
- `-r, --reset-decisions`: Force all decisions to their authored defaults (useful in automated scripts).

#### B. CLI Examples & Workflow

```bash
# 1. Approve taking all authored defaults (exact match for legacy behavior)
$ sase plan approve keymap_help_overlay

# 2. Approve overriding a choice and a toggle
$ sase plan approve keymap_help_overlay -D grouping=mode -D tui_note=no

# 3. Dry-run preview of decision overrides
$ sase plan approve keymap_help_overlay -D grouping=mode --dry-run
```

#### C. Dry-Run Output (`--dry-run` / `-n`)
```text
[DRY RUN] Plan Approval Simulation: keymap_help_overlay (tale)

Decisions Applied:
  • grouping: mode (default: pane) [OVERRIDDEN]
  • tui_note: false (default: true) [OVERRIDDEN]

Authorized Memory Scope:
  • NONE (tui_note declined)

Follow-up Action:
  • Launch tale coder agent (claude/opus)
  • Commit approved plan to sdd/plans/202610/keymap_help_overlay.md
```

#### D. Error Handling & Diagnostics
The CLI fails fast and provides actionable suggestions:

```bash
# Unknown decision key:
$ sase plan approve keymap -D layout=vertical
Error: Unknown decision 'layout' for plan 'keymap_help_overlay'.
Available decisions:
  • grouping (choices: pane, mode)
  • tui_note (boolean toggle)

# Invalid choice value:
$ sase plan approve keymap -D grouping=grid
Error: Invalid choice 'grid' for decision 'grouping'.
Allowed choices:
  • pane: By pane, matching the footer hints
  • mode: By leader mode; denser, but splits pane actions

# Invalid boolean toggle:
$ sase plan approve keymap -D tui_note=maybe
Error: Invalid boolean value 'maybe' for decision 'tui_note'.
Accepted values: true/false, yes/no, 1/0, on/off.
```

### 5.3 Interactive Terminal Fallback Mode
When `sase plan approve` is run in an interactive TTY without `-D` or `--yes`, and the plan contains decisions:
1. It prints the Decisions summary table.
2. It prompts:
   `Approve plan with defaults shown above? [Y/n/c(hange)]: `
3. If the user presses `c`, an interactive prompt steps through each decision with arrow keys/selections before proceeding to execution.

---

## 6. Planner Authoring & Cognitive Ergonomics

### 6.1 When to Embed a Decision vs. When to Ask Now
Planners must adhere to clear cognitive guidelines to prevent decision bloat:

```text
                     Decision Tree for Planner Agents
                     ────────────────────────────────
                       Does the ambiguity affect:
                       • The architecture?
                       • The plan tier (tale vs epic)?
                       • The phase graph structure?
                                  │
                 YES ─────────────┴───────────── NO
                  │                              │
         Use /sase_questions            Can you defend a sensible
           (Block & Ask)                    default yourself?
                                                 │
                                 YES ────────────┴──────────── NO
                                  │                            │
                          Embed Decision in          Use /sase_questions
                             Frontmatter                (Block & Ask)
```

- **Ask Now (`/sase_questions`):** If the answer dictates whether the work is a tale or an epic, changes the number of phases, or chooses between fundamentally incompatible libraries.
- **Embed Decision (`decisions:`):** If the planner can author a unified plan that encompasses both alternatives (e.g. "Step 3a if grouping=pane; Step 3b if grouping=mode"), and the planner has a recommended default.

### 6.2 Hard Guardrails & Limits
- **Maximum Count:** Exactly **5 decisions** per plan. Cognitive psychology confirms that reviewers rubber-stamp forms exceeding 5 controls.
- **Mandatory Default:** Every decision MUST declare a `default`. A decision with no default is rejected by `sase-core` validation.
- **Strict Key Naming:** Keys must be alphanumeric slugs (`^[a-z][a-z0-9_]*$`, max 32 chars). Reserved approval keywords (`approve`, `reject`, `feedback`, `commit`, `model`, `prompt`) are forbidden.

---

## 7. Downstream Lifecycle & Implementer Consumption

### 7.1 Recording the Answers in Frontmatter
Upon approval (via any surface), the `sase plan approve` engine stamps the resolved answers and audit provenance directly into the plan frontmatter before archiving:

```yaml
---
tier: tale
title: Keymap help overlay
decisions:
  grouping:
    ask: How should the overlay group bindings?
    choices:
      pane: By pane, matching the footer hints
      mode: By leader mode; denser, but splits pane actions
    default: pane
    answer: mode
  tui_note:
    ask: Record the overlay's keymap conventions in the tui memory note?
    memory: [tui.md]
    requested: "and note the convention in the tui memory"
    default: true
    answer: true
decided_by: reviewer     # reviewer | auto | cli
decided_at: 2026-10-07T20:45:00Z
decided_surface: tui     # tui | telegram | cli
---
```

### 7.2 The Tale Coder Turn Injection
When the host launches the follow-up tale coder agent, it automatically injects a sealed **Reviewer Decisions** block into the prompt:

```markdown
Reviewer decisions for this plan (binding and final):
- grouping — "How should the overlay group bindings?" → mode
  (Reviewer selected 'mode'; planner default was 'pane').
  Consequence: By leader mode; denser, but splits pane actions.
- tui_note — "Record the overlay's keymap conventions in the tui memory note?" → true
  Memory write authorization granted for: [tui.md].
  No other memory files may be edited.

Implement only the branches selected above. Do not implement unselected branches.
```

### 7.3 Epic Phase Distribution & Bead Work
For epics, the stamped answers are written to the archived plan referenced by the epic bead's `design` pointer.
- `sase bead read <bead>` renders a clean **DECISIONS** section.
- Phase workers and the epic land agent see the decisions automatically, ensuring consistent choices across all waves without re-asking the user.

---

## 8. Surface Comparison Matrix

| Feature / Dimension | ACE Terminal UI (TUI) | Telegram Bot | Command Line Interface (CLI) |
| :--- | :--- | :--- | :--- |
| **Primary Interaction** | Dedicated left-column section with live keyboard focus | In-message preview card + dynamic inline keyboards | Rich detail table + `-D` override flags |
| **Approval Friction** | Single keystroke (`Enter`) | Single tap (`[✅ Approve as shown]`) | Single command (`sase plan approve`) |
| **Override Mechanism** | `Space` to toggle/cycle in place | `[🎛 Change Decisions]` switchboard | `-D key=value` flags |
| **Memory Provenance** | 🧠 badge + `✓ requested` chip | 🧠 icon + `✓ requested` tag in card | Table column + colorized status badge |
| **Outcome Projection** | Live dynamically updating line above verdict | Live updated outcome sentence in message | `--dry-run` summary block |
| **Error Feedback** | Inline modal notifications | Telegram alert popups (`answerCallbackQuery`) | Standard stderr with diagnostic help |
| **Accessibility / Scripting** | Vim keys (`j`/`k`, `r`, `Space`) | Touch friendly, low bandwidth | Exit codes, stdout, `--format json` |

---

## 9. Implementation Roadmap & Milestones

The rollout of Plan Decisions should proceed across five coordinated milestones:

```text
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Milestone 1 │ ──> │  Milestone 2 │ ──> │  Milestone 3 │
│  sase-core   │     │  CLI & Engine│     │   ACE TUI    │
│  Validation  │     │  -D & Stamping│     │   Redesign   │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 v
                     ┌──────────────┐     ┌──────────────┐
                     │  Milestone 5 │ <── │  Milestone 4 │
                     │ Guard & Skills│     │   Telegram   │
                     │  Enforcement │     │ Switchboard  │
                     └──────────────┘     └──────────────┘
```

1. **Milestone 1: `sase-core` Schema & Validation Engine**
   - Implement `decisions` schema in Rust (`serde_yaml`).
   - Add authoring-mode validation (max 5, required defaults, forbidden `answer` in authoring mode).
   - Implement word-for-word quote verification against human prompt history.
2. **Milestone 2: Host Gate Wiring, Stamping, and CLI**
   - Compile frontmatter decisions into declared gate inputs on `approve` / `commit`.
   - Add `-D/--decide` and `-r/--reset-decisions` to `sase plan approve`.
   - Update `sase plan show` to display the colorized Decisions table.
   - Implement frontmatter stamping (`answer:`, `decided_by:`).
3. **Milestone 3: ACE TUI Plan Review Modal**
   - Refactor `PlanApprovalModal` left column: introduce `Decisions` container above `Verdict`.
   - Implement `PlanDecisionToggle`, `PlanDecisionChoice`, and `OutcomeProjectionLine`.
   - Wire keyboard shortcuts (`j`/`k`, `Space`, `Shift+Space`, `r`, `R`).
4. **Milestone 4: Telegram Notification & Interactive Switchboard**
   - Format decision summary and outcome lines into `_format_plan_properties_preview`.
   - Add `[✅ Approve as shown]` and `[🎛 Change Decisions]` inline buttons.
   - Implement interactive switchboard callback loop using `editMessageReplyMarkup`.
5. **Milestone 5: Policy, Skills, and Finalizer Enforcement**
   - Update `/sase_plan` and `/sase_memory_write` skills to guide agent authoring.
   - Introduce beta-flagged finalizer guard checking memory git diffs against approved memory decisions.

---

## 10. Conclusion

Plan Decisions eliminate the friction between agent initiative and human authority. By standardizing reviewer choices into typed, defaulted frontmatter structures and projecting them through beautiful, cohesive interfaces in ACE, Telegram, and the CLI, SASE achieves the ideal UX balance: **zero-overhead approvals when the planner is right, and instantaneous, intuitive control when the reviewer wants to steer.**
