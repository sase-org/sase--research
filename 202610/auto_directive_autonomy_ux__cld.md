# `%auto` UX: Autonomy You Can See, Steer, and Trust

> **Research query:** Make the `%auto` directive much more configurable, intuitive, and
> powerful. Accept every recommendation in `auto_directive_autonomy_policy.md` (autonomy
> profiles that `%auto` selects, Rust-owned policy, fail-closed parsing, role defaults,
> agent awareness, audit). That research did not focus on UX. Lead the design for the
> TUI, CLI, and Telegram so the feature is intuitive, reliable, and beautiful. Decide
> honestly whether there is much UX work to do, and end with a recommended UX design.

## Bottom line

- **There is real UX work, and most of it is not about configuring `%auto`. It is about
  seeing it.** Today `%auto` mostly means *invisible*.
  - In the last 30 days, **224 gates were auto-resolved**: 145 tale plans, 78 epic
    plans, and 1 question. Only 64 gates were answered by a human.
  - **86% of epic plans (78 of 91) launched a clan with no human checkpoint.** None of
    those launches produced an inbox row, a toast, or a Telegram message.
  - The only trace is a quiet receipt, and only for plans that carry Plan Decisions.
    Every TUI view filters it out. Telegram renders it as a generic `🔔 *plan-decisions*`
    message with no agent link and no buttons.
- **The one live control is not reliable.** `A` toggles a bare-`%auto` agent "off" and
  clears the `⚡`. The runner, however, still has `SASE_AGENT_AUTO_APPROVE=1` in its
  environment, so the next gate is still auto-resolved (D5). A control that lies is
  worse than no control.
- **Profiles are worthless without surfaces.** Users type `%auto` out of habit:
  - 72–75% of prompts in September and October contain it.
  - **100% of those uses are the bare spelling**.
  - In October the typed prompts end with a habitual signature line: 41 of 85 auto
    lines are exactly `#plan %m:<model> %auto`.

  Nobody will discover `%auto:overnight` by reading docs. They will discover it:
  - in the completion menu as they type the token they already type;
  - in a picker the moment they want to change a running agent;
  - from a button on their phone.
- **Recommendation: "visible autonomy" across four moments.**
  - **Compose:** an autonomy chip in the prompt bar, profile-aware completion, hover,
    and diagnostics.
  - **Run:** a truthful `A` toggle, a matrix picker on `,a`, profile chips on rows,
    and an Autonomy block in the Context card.
  - **Gate time:** a receipt for every automatic decision.
    - Receipts are quiet by default.
    - Receipts are **loud when autonomy fans out into an epic**.
    - Gates that do reach you carry a one-line *why it asked you*.
  - **After:** a `⚡ Auto` inbox tab, `sase autonomy log`, and `sase autonomy explain`.
- **Telegram becomes a remote control, not just a mirror.** Add a `✋ Manual` button on
  launch messages and receipts, a `/auto` command, and dedicated receipt cards. Your
  phone is where you are when your autonomy posture changes: leaving your desk, or
  coming back.
- **Two genuinely new capabilities earn their place.** I add both to the policy
  research.
  1. **A global autonomy brake.** `⏸ Pause autonomy` makes every gate ask you, without
     killing any work. It is the calm answer to a runaway epic fan-out.
  2. **Grace windows.** `epic: approve after 20m` publishes the gate with a countdown
     and auto-approves only if nobody steps in. This removes the binary choice between
     "I must approve" and "I will never see it", which is the actual dilemma behind
     `#plan %auto`.
- **Rendering stays in Rust.** Every sentence, badge, and matrix shown to the user comes
  from one Rust-core summary wire, the same way `plan_decision_summary` already serves
  the TUI, Telegram, mobile, and CLI. Surfaces cannot disagree about what a profile
  means.

## Scope and method

_Research, 2026-10-08, sase `bb8673ea7c`. I accept the policy research as settled and
did not re-litigate it. Its terms are used as defined there: profiles, `standard`,
`epic_worker`, `on_ask`, the decision vocabulary, and defects D1–D8. All UI below marked
**proposed** is a design, not existing behavior._

- **Code read:**
  - sase TUI (`src/sase/ace/tui`), CLI parsers, gate adapters and receipts;
  - the `sase-telegram` plugin;
  - `sase-core` directive metadata, the LSP, the launch planner, and Plan Decisions;
  - the mobile gateway projections.
- **Data:**
  - `~/.sase/prompt_history/2609.json` and `2610.json` (the July and August files the
    policy research used are no longer on disk);
  - gate bundles under `~/.sase/interaction_requests/` responded to within the last 30
    days.
- **Prior art:** current docs for Claude Code, Codex CLI, Gemini CLI, Warp, Zed,
  Factory Droid, Kiro, and Jules (see [Sources](#sources)).
- **Memory consulted:** `macros.md`, `tui.md`, `cli_rules.md`,
  `decisions:gates-never-block`, and the glossary (gate, gate turn, deck, card, block).

## 1. Is there actually much to do?

I started from the skeptical position: `%auto` is typed 75% of the time and appears to
"just work", so perhaps the P0 fixes plus profiles are enough. The evidence says no, for
five reasons.

| # | Evidence | Why it is a UX problem, not a policy problem |
| --- | --- | --- |
| 1 | 78 auto-launched epics in 30 days. Auto gates publish no notification (`notification_gates/service.py:97`). The only receipt is `silent=True` (`sdd/plan_decision_handoff.py:538-578`), and the TUI inbox drops silent rows (`actions/agents/_notification_provider_direct.py:96`) | A user cannot calibrate trust in something they cannot see. Profiles will automate *more* kinds of decisions, so the cost of invisibility grows with the feature |
| 2 | `A` "off" does not stick for bare `%auto` (D5): `axe/run_agent_runner_launch.py:309` exports the env var and both readers OR it with meta | The only live control silently lies. Every new surface built on it would inherit the lie |
| 3 | Telegram and mobile cannot change autonomy at all. Telegram `/list` shows a read-only `⚡` badge (`sase_telegram/agent_format.py:191-199`); mobile projections have no autonomy field | The moment you want to change posture (leaving the desk, coming back) is the moment you are on your phone |
| 4 | 100% bare spelling, and October's signature line `#plan %m:<M> %auto` | Users do not reach for arguments they cannot see. Profiles need discovery *inside the habit*: completion, chip, picker |
| 5 | `A` on a `⚡T` agent turns it off; it never switches tier. The old picker was deleted (`651a32ee00`). `%auto:<other>` shows no chip at all | Today's on/off control cannot express what the policy research adds |

What I would **not** do is equally important. The recommended design is mostly small,
visible, and honest affordances, not a control panel. Rejected ideas are listed in
[§8](#8-what-not-to-build).

## 2. Today's UX, moment by moment

### 2.1 Surface audit

| Moment | TUI | CLI | Telegram | Mobile / editor |
| --- | --- | --- | --- | --- |
| **Compose** | Generic directive highlight (`widgets/_macro_syntax_highlight.py`). `%auto:` completion lists `plan`/`tale`/`epic`, each described as a "…compatibility alias…" (`macro/_directive_types.py:67-71`). No chip; the launch context bar shows only model and project (`widgets/launch_context_bar.py`) | Prompt text only; no flag | Typed into the message; the launch confirmation never mentions autonomy (`inbound_handlers/agent_launch.py:436`) | LSP hover is the generic description only (`sase_core/src/editor/hover.rs:74-104`); no diagnostics for `%auto` args |
| **Launch review** (agent-requested) | Raw prompt text; `%auto` is just highlighted text (`modals/launch_approval_modal.py`) | `render_launch_approval_preview` omits auto (`sase_core/src/agent_launch/plan_resolution.rs:624`) | `🚀 *Launch Approval*` card with no autonomy line | — |
| **Run** | Row `⚡`/`⚡T`/`⚡E` in bold `#00FFFF`; header `⚡ PLAN`/`TALE`/`EPIC`; binary `A` toggle; toast `Auto-approve enabled (%auto)` (`actions/agents/_approve.py:84,90`) | `sase agent list` has no column. `--json` `approve` is false for tale/epic agents. `auto_badge` (`integrations/_agent_list_entry_models.py:184`) is never called. `sase agent show` says nothing | `/list` badge; `/show` row `Auto ⚡T tale`; no way to change it | Nothing |
| **Gate time** | Nothing. Auto gates create no notification | `sase gate show` appends `· source auto_resolution` | Decision-plan receipts arrive as generic `🔔 *plan-decisions*` (`formatting.py:2030-2036`) | Silent rows are excluded unless `include_silent=true`; notifications have no `tags` |
| **After** | Decision sheet shows `decided by auto` inside the agent's Plan section only | `sase notify list` shows the silent receipt | — | — |

### 2.2 UX-layer defects found (in addition to D1–D8)

| # | Defect | Evidence |
| --- | --- | --- |
| U1 | The `A` toggle lies for bare `%auto` (this is D5 seen from the UI) | `_approve.py:116-131` clears meta; `run_agent_runner_launch.py:309` env var survives |
| U2 | `%auto:<anything-else>` agents show no chip, and `A` treats them as off | `axe/run_agent_directive_metadata.py:292-299` stores only `auto_approve_argument`; the chip reads `approve`/`auto_approve_plan_action` |
| U3 | Auto receipts are invisible in every TUI view | `docs/notifications.md:962-986` (silent rules) and `_notification_provider_direct.py:96` |
| U4 | `docs/notifications.md` says auto receipts get "no Telegram delivery"; the plugin delivers them | `sase-telegram` `outbound.py:61,72-85` |
| U5 | Telegram receipts have the wrong header. Edited cards default to `✅ Tale approved · you via Telegram` even for auto, ACE, CLI, and epics, and a reject renders `✅ Rejected approved` | `decision_receipt.py:100-108` defaults; `gate_completions.py:279-285`. The wip repair plan `telegram_decisions_repairs` (sase-1hi.10.6) covers part of this |
| U6 | Auto-answered questions leave no trace on any surface | `axe/run_agent_exec_questions.py:191` |
| U7 | The `⚡` glyph is overloaded. It means "auto" on rows, RUNNING (gold) in the run log, and "apply now" in the Update panel | `agent_run_log_modal.py:167`; `update_panel.py:31` |
| U8 | Launch review never flags the child's autonomy, though a human-approved launch keeps the child's `%auto` | `agent/launch_preview.py:112-212`; `launch_request_gate.py:254` |

## 3. Prior art and what it teaches

| Tool | Autonomy UX | Lesson for SASE |
| --- | --- | --- |
| **Claude Code** | Mode shown in the status bar. `Shift+Tab` cycles default → acceptEdits → plan; `auto` stays out of the cycle. `defaultMode: "auto"` is ignored in project settings | The current posture is **always visible where you type**. A one-key cycle covers the common modes. Escalation never comes from shared or project text |
| **Codex CLI** | `/permissions` picker of presets (Read Only / Auto / Full Access, with a caution note on Full Access); `/status` shows the active policy | A **small picker of named presets** beats a pile of flags. Explain lives one keystroke away |
| **Gemini CLI** | `Ctrl+Y` toggles YOLO with a footer indicator; `--approval-mode default\|auto_edit\|yolo`; YOLO only from the command line | **Toggle plus indicator** is the baseline. The most permissive mode is not a settings-file default |
| **Warp** | Named **agent profiles**, each with per-action autonomy: *Agent decides / Always ask / Always allow / Never*. Switch profiles from an icon in the input area. Examples include a "YOLO" profile and a "Prod" profile | Closest to the policy research. **Per-kind ask/allow/never inside named profiles**, switched **from the input area** |
| **Zed** | Built-in profiles (Write / Ask / Minimal) with a profile selector in the agent panel; tool permissions are separate | Profiles are a picker-first concept. Keep "what the agent may do" separate from "who approves" |
| **Factory Droid** | `--auto low\|medium\|high` (default read-only); interactive Off/Low/Medium/High | An ordered ladder works for **risk of one action**. SASE's kinds are not ordered (`overnight` is tighter on epics and looser on questions), so **avoid a slider** |
| **Kiro** | *Autopilot* vs *Supervised* switch in the chat; revert after each turn | Name postures by **human presence**, not mechanism |
| **Jules** | If you navigate away, the plan **auto-approves on a timer** | A **grace window** resolves the "may or may not be around" case. SASE gates are already non-blocking, so a timer costs only latency |

**Synthesis.** The tools converge on four things:
1. a visible posture indicator at the input;
2. a one-key toggle plus a richer picker of named profiles;
3. per-kind ask/allow/never inside each profile;
4. guarded escalation.

None of the tools I surveyed puts much weight on **what happened while I wasn't
looking**. SASE's unattended, multi-agent shape makes that the most important gap, so
receipts are where this design invests most.

## 4. Design principles

1. **The prompt and the session record are the only truth.** Every surface either edits
   the `%auto` token in prompt text (compose time) or edits the session's persisted
   autonomy record (run time). No hidden "sticky" state exists. Retry, history, and
   Telegram all replay faithfully because the token is in the text.
2. **Show consequences, not mechanisms.**
   - Say "the next plan will wait for you", not "approve=false".
   - Say "epics launch automatically", not "epic_plan: approval".
3. **Calm by default, loud on fan-out.**
   - Routine automatic decisions are quiet and findable.
   - Decisions that multiply work (an epic launching a clan) or that a human should
     know about (a denial that changed the plan) get a normal notification.
4. **Honest coverage everywhere.** Each explain surface ends with
   `gates only · shell is not restricted` until hard permissions exist. Never show a
   reassuring "restricted" badge.
5. **One vocabulary, rendered once.** Glyphs, profile names, and sentences come from one
   Rust summary wire. `★` keeps meaning "the default the policy would pick" and `●`
   keeps meaning "changed", exactly as in Plan Decisions.
6. **Steer from wherever you are.** The TUI for the desk, Telegram for away, the CLI for
   scripts. Every live change works on all three.
7. **Tightening is free; loosening is deliberate.**
   - Manual, deny, and pause never ask for confirmation.
   - Anything above the configured default (P3 launch delegation) requires a
     confirmation, like the broad-`%hold` **Arm this hold?** dialog.

## 5. Recommended UX design

### 5.1 Vocabulary and visual system

**Profiles a user sees (proposed).** These are the built-ins from the policy research,
plus two additions marked ★.

| Profile | Badge | Posture class | One-line meaning (generated) |
| --- | --- | --- | --- |
| `standard` (default) | `⚡` | autopilot | Plans approve + archive · epics launch · questions take ★ |
| `attended` | `⚡A` | attended | Plans and epics are automatic · questions ask you |
| `overnight` | `⚡O` | unattended | Plans automatic · epics denied · questions decided · nothing waits for you |
| `glance` ★ | `⚡G` | attended | Everything asks you **with a countdown**, then proceeds |
| `epic_worker` (role) | `⚡W` | attended | Like standard, but nested epics ask you |
| `tale` / `epic` (compat) | `⚡T` / `⚡E` | attended | Today's tier-specific spellings, kept working |
| `manual` ★ (reserved, alias `off`) | `✋` | manual | Every gate waits for you; identical to having no `%auto` |

- `manual` exists so that live edits, agent-authored follow-ups, and Telegram buttons
  have an explicit *narrow* token. It also gives `%auto:off` (D2) a correct meaning
  instead of an accidental one.
- The badge is a config field `badge:`. It defaults to the profile's first letter,
  uppercased. The default profile renders as a bare `⚡`, so the 72% case looks exactly
  like today. The compat badges keep `⚡T`/`⚡E`, so muscle memory and existing
  snapshots survive.

**Glyphs.** One meaning each, shared by all surfaces.

| Glyph | Meaning | Where |
| --- | --- | --- |
| `⚡` | Autonomy profile active (color = posture class) | Rows, header, chips, receipts |
| `✋` | Asks you (manual, or a kind set to `ask`) | Matrix cells, picker, toasts, "why" lines |
| `✓` | Resolved automatically | Matrix cells |
| `✗` | Denied by policy (the agent is told to skip) | Matrix cells, receipts |
| `★` | Recommended / default option (existing Plan Decisions meaning) | Questions, receipts |
| `⏳` | Grace window counting down | Gate cards, rows (overlay), matrix cells |
| `⏸` | Autonomy paused (global brake) | Launch context bar, dimmed row chips |

**Posture colors.** These are computed in core from the effective policy, never chosen
per surface.

| Class | Color | Rule |
| --- | --- | --- |
| autopilot | `#5FD7FF` (today's `⚡ PLAN` cyan) | Plan, epic, and question all auto-resolve |
| attended | `#87D787` | At least one of plan/epic/question asks you |
| unattended | `#FFD75F` | `on_ask: deny` or `question: decide`; nobody is expected |
| paused / manual | dim `#8A8A8A` | Brake engaged, or no profile |

**U7 cleanup.** Reserve `⚡` for autonomy. The run log's RUNNING glyph becomes `▶`,
matching Telegram's `/list` status tokens. The Update panel's "apply now" glyph becomes
`↯`.

### 5.2 Compose: the prompt bar

**Autonomy chip (proposed).** The chip sits at the right end of the prompt border title,
after the existing TODO and Jinja capsules (`widgets/_prompt_input_bar_title.py:91-118`).
It is parsed live from the prompt with the same core extractor the launch uses
(`plan_typed_launch_units`, whose `AgentUnitWire` already carries
`auto_enabled`/`auto_mode`).

```text
╭─ Prompt · +sase ──────────────────────────────────────────── ⚡ standard ─╮
│ Can you help me fix the tab-strip flicker? #plan %m:opus %auto            │
╰────────────────────────────────────────────────────────────────────────────╯

╭─ Prompt · +sase ──────────────────────────────────────────────── ✋ manual ─╮
│ Can you help me fix the tab-strip flicker? #plan %m:opus                    │
╰──────────────────────────────────────────────────────────────────────────────╯

╭─ Prompt · +sase ─────────────────────────────── ⚡ ✗ unknown profile 'ovrnight' ─╮
│ … #plan %auto:ovrnight                                    ~~~~~~~~ (red curl)    │
╰───────────────────────────────────────────────────────────────────────────────────╯
```

- **Manual shows, dimly.** With 72% habitual use, *forgetting* `%auto` is the notable
  case, so the absence is shown, quietly.
- **Mixed fan-out.** `%{… | …}` alternatives with different autonomy show `⚡ mixed`.
  The tooltip lists each branch.
- **Invalid fails closed, early.** The chip turns red, the token gets a diagnostic
  underline, and submit is refused with the same message the launch would produce. This
  surfaces D1/D2 fail-closed parsing *before* launch instead of in an error toast after.
- **Cycle key (proposed `alt+a`; check it against the prompt editor keymap and add it
  to `default_config.yml`).** Cycles `manual → default → configured profiles → manual`
  by rewriting the token in place, using the existing `set_prompt_auto_mode` logic
  moved into core. The text stays the truth.

**Completion and hover (proposed; `sase-core` editor metadata, so nvim gets it free via
the macro LSP).** Completion follows the `%model` dynamic-role precedent: a new
`AutonomyProfile` role lists configured profiles with their generated summary instead
of "compatibility alias" jargon.

```text
%auto:█
 ┌────────────────────────────────────────────────────────────────┐
 │ ⚡  standard    plan ✓   epic ✓   question ★     default        │
 │ ⚡A attended    plan ✓   epic ✓   question ✋                    │
 │ ⚡G glance      plan ⏳10m epic ⏳30m question ⏳10m              │
 │ ⚡O overnight   plan ✓   epic ✗   question decide · no asks     │
 │ ✋  manual      every gate waits for you                         │
 └────────────────────────────────────────────────────────────────┘
```

Hover replaces today's one-line description (`hover.rs:74-104`) with the matrix, the
source layer, and the coverage line:

```text
%auto:overnight — unattended                     (user config · extends standard)
  plan       ✓ approve + archive
  epic       ✗ deny — the agent is told to split into tales
  question   decide — the agent records its assumptions
  launch · sudo · custom   ✋ ask (no human expected → denied)
  gates only · shell is not restricted
```

`%auto(` lists keys (`plan=`, `epic=`, `question=`/`q=`) with their legal values,
following the `QUEUE_KEYWORDS` alias precedent (`p` → `priority`). Values that only
config may grant (for example `launch=allow`) are absent from completion. If typed, they
get a diagnostic: *"launch=allow must come from a config profile"*.

### 5.3 Review moments: launch approval and coder options

- **Launch Review modal** (agent-requested launches, `modals/launch_approval_modal.py`).
  Add a **Child autonomy** row above the prompt preview. A human-approved launch keeps
  the child's requested policy, so it must be impossible to miss.

  ```text
  Child autonomy   ⚡ standard — plans approve + archive · epics launch · questions ★
                   requested by @sase.planner in its prompt          [m] launch as manual
  ```

  `m` rewrites the child's `%auto` to `%auto:manual` before approval. Telegram's
  `🚀 *Launch Approval*` card gets the same line and a third button,
  `✅ Approve · manual`. The core `render_launch_approval_preview` adds `auto=<profile>`
  to each unit line.
- **Plan Review → Coder options** (`c`). Add one row,
  `u autonomy   ⚡ standard (inherited)`, so a human approving a plan can hand the coder
  a different posture without a separate step.

### 5.4 Run: seeing and steering a live agent

**Rows** keep today's placement (`widgets/_agent_list_render_agent_prefix.py:145-171`):

```text
  ⚡  sase.fix-tabs         RUNNING    opus@high   3m
  ⚡A sase.tab-docs         QUESTION   sonnet      1m
  ⚡W sase-1hx.2            RUNNING    opus       12m
  ⚡⏳ sase.big-refactor     EPIC PLAN  opus       auto-approves in 18m
      sase.manual-one       PLAN       opus        —
```

While the brake is engaged, every `⚡` renders dim. U2 is fixed by construction: the
chip renders from the resolved session record, not from three legacy meta keys.

**Header chip** (`prompt_panel/_identity_header_compact.py:92-108`): `⚡ standard`
replaces `⚡ PLAN`, colored by posture class. Its tooltip is the generated one-line
meaning.

**Context card → Autonomy block (proposed).** This is a titled card block in the Main
deck's Context card, present whenever the session has a profile. It answers three
questions in one place: what will happen, why, and what has happened.

```text
── Autonomy ─────────────────────────────────────────────────────────────
⚡ standard · from prompt · session sase.fix-tabs (3 turns)
  plan       ✓ approve + archive
  epic       ✓ approve + launch clan
  question   ★ recommended option (else first)
  launch · sudo · custom   ✋ ask you
  gates only · shell is not restricted
What the agent was told   (▸ expand: the 5-line awareness block, verbatim)
Decisions this session
  14:02  ✓ tale approved + archived       tab_flicker.md        standard · plan
  14:09  ★ question answered              "Keep the CSS var?" → yes
  14:31  ✋ sudo asked you                  not auto-allowable
```

Showing the awareness block verbatim matters for trust. You see exactly what the agent
believed about who was listening.

**`A`: a truthful, undoable toggle (proposed semantics).**

- **Enabling `A`** on a manual agent restores the profile it last had, or
  `autonomy.default` if it never had one. Pressing `A` twice is an undo, not a reset.
- **Disabling `A`** on an auto agent sets `manual` for the **whole session**, effective
  at the next gate.
  - This depends on D5: gates read the persisted record live, never the env snapshot.
  - The chip and toast are rendered from a **read-back** of the record after the write.
    The UI cannot claim a state the gate will not see.
- **Pending gates.** If the agent is parked at a gate the new profile would
  auto-resolve, enabling `A` resolves it immediately. This already appears to happen
  (Telegram cards get settled "by a later auto toggle"), but it should be explicit and
  stated in the toast. Disabling `A` never un-resolves anything.
- **Marks.** `A` on marked agents applies to every marked agent, like `S` bulk status.
- **Toasts are consequence sentences:**

  ```text
  ✋ sase.fix-tabs is now manual — the next plan, epic, or question will wait for you
  ⚡ standard on · sase.fix-tabs — approved the pending plan; epics launch; questions ★
  ⚡ 3 agents → manual
  ```

**`,a`: the autonomy picker (proposed; `a` is free in leader mode).** It is a matrix,
because the choice between profiles is a choice between columns.

```text
╭───────────────────────── Autonomy · sase.fix-tabs ─────────────────────────╮
│                      plan     epic     question   launch                   │
│ ▸ s  ⚡  standard     ✓        ✓        ★          ✋      ← current         │
│   a  ⚡A attended     ✓        ✓        ✋          ✋                        │
│   g  ⚡G glance       ⏳10m    ⏳30m    ⏳10m       ✋                        │
│   o  ⚡O overnight    ✓        ✗        decide     ✗                        │
│   m  ✋  manual       ✋        ✋        ✋          ✋                        │
│                                                                            │
│ standard — Approve and archive tales, launch epics, answer questions with  │
│ the recommended option.        applies to: whole session · from next gate  │
│ gates only · shell is not restricted                                       │
╰─ letters pick · j/k move · enter apply · e explain · P pause all · esc ────╯
```

- Styling matches the deck picker: `round $primary` border, a bold centered title, and
  a legend subtitle that shortens to fit.
- Letters apply immediately, as in the deleted Auto-Approve picker.
- `P` engages the global brake from here ([§5.8](#58-the-global-brake)). That gives the
  brake a home without spending another global key.
- The command palette gains **Set autonomy profile…** and **Pause / resume autonomy**.

### 5.5 Gate time: receipts, loudness, and "why it asked"

**Every automatic outcome gets a receipt (proposed).** Today only decision plans get
one. The receipt is a core `AutonomyReceiptWire`:
`{event, kind, decision, option_ids, profile, rule, sentence, agent, plan_ref?, question?, answer?}`.
Each surface renders that wire; none of them composes its own text.

**Loudness is fixed by the event, not the surface.**

| Event | Loudness | Why |
| --- | --- | --- |
| Tale auto-approved | **Quiet** | Routine, ~5.6/day. Reviewable after the fact in the plans sidecar |
| Question auto-answered | **Quiet** | Rare (1 in 30 days), but must be findable: it changed the agent's direction |
| Gate denied by policy | **Quiet** | The agent is told to skip; the receipt says so |
| **Epic auto-launched** | **Normal** (bell, toast, Telegram with sound) | ~3/day. It multiplies work and runner load; it is where the nested-epic loops came from. You want a chance to brake |
| Grace window started | **Normal** (it is a real gate) | You are being offered the decision |
| Gate parked for you under a profile | **Normal** (it is a real gate), plus a *why* line | — |

- **Configuration.** One knob, `autonomy.announce: [epic]` (default), lets a user make
  more kinds loud. Per-profile loudness is not worth the complexity.
- **TUI inbox: a `⚡ Auto` tab (proposed).**
  - Receipts are tagged `autonomy`.
  - They are born quiet: no bell, no toast, and no top-bar count.
  - The Rust tab precedence places them in an `⚡ Auto` tab with a low default priority
    (5): below custom tags, above Snoozed. The panel, top bar, and mobile snapshot keep
    agreeing because the core already owns tab assignment (`docs/notifications.md`,
    "Tabs and Ordering").
  - This replaces `silent=True`, which today means "audit-only, invisible".
  - The `⚡ Auto` tab is the "what did autopilot do while I was away" feed. `d` on the
    tab dismisses all of it.

  ```text
   ⚑ Gates 2   ✉ General 1   ⚡ Auto 9
   ────────────────────────────────────────────────────────────────────────
   ⚡ 14:02  sase.fix-tabs        ✓ Tale approved + archived · tab_flicker.md
   ⚡ 14:09  sase.fix-tabs        ★ Answered "Keep the CSS var?" → yes
   ⚡ 14:20  sase.big-refactor    🚀 Epic launched · 5 phases          (rang)
   ⚡ 14:31  sase-1hx.2           ✗ Nested epic denied · split into tales
  ```

- **"Why it asked you" on every gate a profile parks (proposed).** This is one dim line
  in the Plan Review subtitle, the question modal, and the Telegram card:

  ```text
  ✋ asked by policy · epic_worker: epic = ask (nested epics need you)
  ✋ asked by policy · %auto:tale on an epic plan → ask
  ⏸ asked because autonomy is paused (you, 14:02, 41m left)
  ```

  This turns today's most confusing moment into a sentence. Today that moment is a
  `%auto` agent that stopped anyway, or a mid-run `invalid_auto_argument` error.

### 5.6 Telegram: from mirror to remote control

Telegram is where autonomy changes happen in real life, so it gets steering, not just
receipts.

**Launch confirmation** (`inbound_handlers/agent_launch.py:436`, `:358-381`) gains an
autonomy line and one toggle button. Its callback data follows the existing
`kill:<name>:go` shape.

```text
🚀 opus Launched  @sase.fix-tabs
workspace #19 · ⚡ standard
Can you help me fix the tab-strip flicker? …
[🍴 Fork] [⏳ Wait]
[🗡️ Kill] [🔄 Retry] [✋ Manual]
```

After a tap, the message is edited in place to `· ✋ manual` and the button becomes
`⚡ Auto`. The edit happens only after the record write is read back.

**Receipts get a dedicated formatter** instead of `_format_generic`. Quiet receipts are
sent with `disable_notification`; epic launches ring.

```text
⚡ Tale approved · @sase.fix-tabs
tab_flicker.md · coder launched · archived
standard · plan ✓
[📄 Plan] [✋ Manual]
```

```text
⚡🚀 Epic launched automatically · @sase.big-refactor
big_refactor.md · 5 phases (2 small · 3 medium)
standard · epic ✓
[📄 Plan] [⏸ Pause autonomy] [✋ Manual]
```

```text
⚡ Answered for you · @sase.fix-tabs
❓ Keep the CSS variable?
→ yes ★ recommended
[🍴 Correct]
```

`🍴 Correct` is a copy-text button. Its text is
`#fork:sase.fix-tabs Re "Keep the CSS variable?": `. An automatic answer cannot be
undone (the agent has moved on), so the honest affordance is a correction fork, built
on the existing `🍴 Fork` pattern.

**`/auto` command (proposed).**

```text
/auto                      → list running agents with their autonomy
/auto <agent> <profile>    → set a session's profile (manual|off to stop)
/auto pause [1h]           → engage the global brake (optional TTL)
/auto resume               → release it
```

```text
⚡ Autonomy · 6 running
⚡  sase.fix-tabs        standard
⚡A sase.tab-docs        attended
⚡W sase-1hx.2           epic_worker
✋  sase.manual-one      manual
[⏸ Pause all · 1h] [⏸ Pause all]
```

**Grace-window plan card.** This is the existing plan review card plus a header line and
one button. The countdown text refreshes on a coarse schedule (every 5 minutes, then
every minute in the last 5) so it stays within Telegram edit limits.

```text
📋 opus Epic Review  @sase.big-refactor · 5 phases
⏳ auto-approves in 18m · glance
…
[✅ Epic] [❌ Reject] [💬 Send Feedback]
[✋ Hold for me]
```

**Fix first:** U4 and U5 (wrong receipt headers, contradictory docs). The repair plan
for sase-1hi.10.6 already intends to map `auto_resolution` to "auto"; extend it so the
receipt formatter reads the core receipt wire.

### 5.7 CLI

A `sase autonomy` group (proposed) follows `cli_rules.md`:
- subcommands sorted alphabetically;
- bare invocation delegates to `list`;
- every long option gets a short alias;
- colored output.

```text
sase autonomy explain [AGENT] [-p/--prompt TEXT] [-j/--json]
sase autonomy list    [-j/--json]
sase autonomy log     [AGENT] [-s/--since 1d] [-k/--kind plan|epic|question] [-j/--json]
sase autonomy pause   [-S/--scope project|host] [-t/--ttl 1h]
sase autonomy resume  [-S/--scope project|host]
sase autonomy set     AGENT... PROFILE          # manual|off stops autonomy
sase autonomy show    PROFILE [-j/--json]       # layer provenance
```

`explain` is the canonical answer to "what will happen?". It calls the same core
`evaluate()` the gates call, so it cannot disagree with them.

```text
$ sase autonomy explain sase-1hx.2
⚡W epic_worker   role default for epic phase workers · extends standard
   source: role (bead/work_prompt) · config ~/.config/sase/sase.yml:212 · digest 3f9c…

   plan       ✓  approve + archive          gates.plan           (standard)
   epic       ✋  ask you                    gates.epic           (epic_worker)
   question   ★  recommended, else first    gates.question       (standard)
   launch     ✋  ask you                    default
   sudo · custom · hitl   ✋  ask you        not auto-allowable

   decisions so far: 1 ✓ plan · 0 ✗ · 1 ✋ pending (epic plan, 6m)
   gates only · shell is not restricted
```

```text
$ sase autonomy log --since 1d
14:02  sase.fix-tabs       ✓ plan      tale approved + archived       standard · gates.plan
14:09  sase.fix-tabs       ★ question  "Keep the CSS var?" → yes      standard · gates.question
14:20  sase.big-refactor   ✓ epic      5 phases launched              standard · gates.epic   🔔
14:31  sase-1hx.2          ✗ epic      nested epic denied             epic_worker · gates.epic
```

Existing commands:
- **`sase agent list`** gains an `AUTO` column built from the core summary badge. This
  revives the dead `auto_badge`.
- **`--json`** gains `autonomy: {profile, badge, posture, source}`. The legacy `approve`
  key is kept while the `sunset` flag lives.
- **`sase agent show`** gains the same Autonomy block as the TUI.

### 5.8 The global brake

**Semantics (proposed):**
- While paused, every auto-resolving decision evaluates to `ask`. `deny` stays `deny`.
  Running work is never stopped.
- Gates that arrive during a pause are ordinary human gates. They carry the `⏸` *why*
  line and **do not auto-resolve later when you resume**: there are no surprise
  approvals.
- Pending grace windows convert to plain asks.
- Scope is `project` by default and `host` optionally. The TTL is optional.
- **Store failures fail closed** (treated as paused) and show `⚠ autonomy brake
  unreadable`. This is the opposite of `%hold`, and it is correct here: a failed brake
  should publish gates to a human, which is today's default, not silently resume
  automation.

**Surfaces:**
- The TUI launch context bar shows `⏸ autonomy paused · 41m`, styled like the
  `override opus@high 2h` chip already shown there.
- In the TUI, `P` in the picker or the palette engages the brake, and every row `⚡`
  dims.
- CLI: `sase autonomy pause|resume`.
- Telegram: `/auto pause`, plus the `⏸ Pause autonomy` button on epic receipts.

**Why it earns its place.** The 234 auto-approved epics and the `sase-11e`/`sase-xe`
nesting loops (see the policy research) show that the realistic failure is *fan-out you
notice late*. Today the only remedy is killing agents. The brake is a tighten-only
ceiling over the live-read record, so it introduces no escalation path.

### 5.9 Grace windows: "auto, unless I look"

**Policy addition (proposed).** Any allow-value for `plan`, `epic`, or `question` may
carry `after <duration>`:

```yaml
gates:
  plan: approve_archive after 10m
  epic: approve after 30m
  question: recommended after 10m
```

**Semantics:**
- The gate is published as a normal gate turn carrying a deadline. The creator's turn
  already ended at gate creation (`gates-never-block`), so the window costs only
  latency, not a runner slot.
- At the deadline, a scheduler routine resolves the gate through the same executor with
  `source="auto_resolution"` and `rule="gates.epic after 30m"`.
  - A human answer before the deadline wins through the existing response lock.
  - `✋ Hold` (TUI `h`, Telegram button) cancels the timer and makes the gate an
    ordinary ask.
  - Merely viewing a gate never stops the clock. That keeps the behavior predictable.
- Deadlines live in the bundle, so restarts and dispatch are safe.
- **Built-in `glance` profile:** `plan after 10m`, `epic after 30m`,
  `question after 10m`, `launch: ask`.
- **TUI.**
  - The modal subtitle reads `⏳ auto-approves in 8:41 · glance   [h] hold for me`.
  - The row overlay `⚡⏳` shows the countdown in the status column.

**Why it is worth it.** The dominant typed pattern, `#plan … %auto`, asks for a plan
(an artifact you *could* read) and then guarantees you never get the chance. `glance`
fits the real posture of someone who is often, but not reliably, around. It is also the
gentlest fix for epic fan-out: epics still launch, but only after a window in which a
glance at your phone can stop them. Jules ships the same idea for plan approval.

### 5.10 Configuration and the Admin Center

The config shape follows the policy research. The UX adds three fields: `badge`,
`description` (required for custom profiles, like custom model aliases), and the
`after` modifier.

```yaml
autonomy:
  version: 1
  default: standard
  announce: [epic]                 # loud receipts; everything else is quiet
  roles: { epic_phase: epic_worker, epic_land: epic_worker }
  profiles:
    overnight:
      description: I'm away — never wait for me; no nested fan-out.
      badge: O
      extends: standard
      gates: { epic: deny, question: decide }
      on_ask: deny
```

- **Admin Center → Config → Autonomy pane** (read-only in v1). It sits next to Holds
  and Flags and shows the picker matrix for every profile, with layer provenance.
  - `e` opens the config file at the profile's line.
  - `x` shows the explain output.
  - No in-TUI editing in v1. YAML stays the single writer, and `sase config layers`
    already explains layering.
- **One-time notice.** When profiles first ship, show a dismissible tip, following the
  existing `*_notice_shown` pattern: *"`%auto` now selects a profile. Press `,a` on any
  agent to see what it does."*

### 5.11 Mobile and editor parity

- **Mobile gateway.**
  - Add `autonomy {profile, badge, posture}` to agent projections and `tags` to
    notification rows.
  - Treat `autonomy`-tagged rows as visible quiet rows rather than excluding them with
    `silent`.
  - Steering actions can reuse the Telegram action set later.
- **nvim and other editors.** The completion, hover, and diagnostics above live in
  `sase-core` editor metadata and the macro LSP. Any LSP client inherits them with no
  plugin work.

## 6. Rust core boundary for the UX

Under `rust_core_backend_boundary`, any text or decision that more than one frontend
shows belongs in `sase-core`. The precedent is the Plan Decisions summary sentence that
the TUI, Telegram, mobile, and CLI already share.

| Core addition (proposed) | Consumers |
| --- | --- |
| `AutonomySummaryWire {profile, badge, posture, sentence, short, cells[{kind, glyph, label, rule, source_layer}], coverage, source}` | Chips, picker, Context block, `/auto`, `sase agent list`/`show`, mobile |
| `AutonomyReceiptWire` (see [§5.5](#55-gate-time-receipts-loudness-and-why-it-asked)) plus a `receipt_sentence()` renderer | Inbox `⚡ Auto` tab, Telegram formatter, `sase autonomy log` |
| `autonomy_why(gate, policy, brake) -> Option<String>` | The *why* line on TUI, Telegram, and mobile gate cards |
| `edit_prompt_autonomy(prompt, profile \| manual)` (move `set_prompt_auto_mode` from Python) | TUI cycle key, `A` persistence, Telegram toggle, retry |
| `AutonomyProfile` dynamic directive role, keyword specs, and hover/diagnostic providers | Completion, hover, and LSP diagnostics in the TUI and editors |
| Notification tab precedence for `autonomy`-tagged quiet rows | TUI inbox, top bar, mobile snapshot |

Python keeps widgets, modals, Telegram transport, and glue. Move the
`sase-core-revision.txt` pin with each binding.

## 7. Rollout, mapped to the policy phases

| UX phase | Ships with | Content | Size |
| --- | --- | --- | --- |
| **UX-0: stop lying, start showing** | Policy P0 | <ul><li>D5 read-back toggle (U1)</li><li>row chip for any `%auto` arg (U2)</li><li>`sase agent list` `AUTO` column and `show` line</li><li>Telegram receipt formatter and header fixes (U4/U5)</li><li>receipts for auto-answered questions (U6)</li><li>`autonomy`-tagged quiet receipts in an `⚡ Auto` inbox tab (U3)</li><li>launch-review child-autonomy line (U8)</li><li>loud epic-launch receipt</li></ul> | Small ×6–8 tales |
| **UX-1: one vocabulary** | Policy P1 | <ul><li>Core summary, receipt, and why wires</li><li>header chip and Context Autonomy block (with the awareness text)</li><li>"why it asked" lines</li><li>`sase autonomy explain/list/log/show`</li><li>glyph cleanup (U7)</li><li>visual snapshots for each new surface (see `tui.md`)</li></ul> | Epic, 3–4 phases |
| **UX-2: steer anywhere** | Policy P2 | <ul><li>Prompt chip, completion, hover, diagnostics, and cycle key</li><li>`,a` matrix picker</li><li>undoable `A` and marks</li><li>`sase autonomy set`</li><li>Telegram `/auto` and launch toggle button</li><li>global brake (all surfaces)</li><li>Admin Center Autonomy pane</li><li>one-time notice</li></ul> | Epic, 4 phases |
| **UX-3: grace windows** | Policy P2/P4 | <ul><li>`after <duration>` decision modifier</li><li>deadline routine</li><li>countdown in TUI and Telegram</li><li>`✋ Hold`</li><li>`glance` built-in</li></ul> | Epic, 2–3 phases |
| UX-4 | Policy P3 | <ul><li>Escalation confirmation (an **Arm this autonomy?** dialog) for config-granted launch delegation</li><li>child-policy line in every launch preview</li></ul> | Medium |

**If you only build four things,** build UX-0, the `,a` picker, the Context Autonomy
block, and the Telegram `✋ Manual` button. Together they turn `%auto` from an invisible
habit into something you can see and steer. Everything else is polish on that base.

## 8. What not to build

| Idea | Why not |
| --- | --- |
| A `--auto` flag on `sase run`/launch commands | It creates a second spelling of the same decision. The prompt token already works on every surface and survives retry |
| A config-level "implicit autonomy for prompts without `%auto`" | Machine-generated launches rely on absence meaning manual (policy research, open decision 4). Hidden defaults break replay |
| A numbered autonomy level or slider (Factory-style low/med/high) | Gate kinds are not ordered. `overnight` is tighter on epics and looser on questions, so a slider misrepresents it |
| The full matrix on every agent row | It is noise. Rows carry a badge; the matrix lives one keystroke away (`,a`, Context block) |
| A toast for every automatic decision | ~8/day median and 29/day peak would train you to ignore toasts. Only epic launches ring |
| "Undo" for automatic approvals | The coder or clan is already running, and undo would promise something the host cannot deliver. Offer **Correct** (a fork) and **Manual** (stop further automation) instead |
| An in-TUI profile editor (v1) | YAML is the single writer and layering is already explained by `sase config layers`. Revisit only if profile counts grow |
| Auto-allow for `sudo`/`custom` from any surface | These gates exist to reach a human. Pre-authorization goes through the profile's awareness block (policy research) |

## 9. Open questions for you

1. **Loud epics.** Should an auto-launched epic ring by default (`announce: [epic]`)?
   I recommend yes. It is about 3 a day, and it is the fan-out you most want a chance
   to brake.
2. **Grace windows.** Do you want `glance` and `after`? If so, are 10 minutes for plans
   and 30 minutes for epics the right defaults? Would you ever make `glance` your
   `autonomy.default`?
3. **Profile names.** `standard` or `default`? `manual` or `off`, with the other as an
   alias? `overnight` or `away`?
4. **Brake scope.** Should the default be `project` (like `%hold`) or `host`? I lean
   `host`, because "stop" should mean stop.
5. **`A` re-enable.** Should it restore the last profile (my recommendation, which makes
   it an undo) or always the default?

## Sources

**Code (sase `bb8673ea7c`):**
- **TUI:**
  - `src/sase/ace/tui/actions/agents/_approve.py`
  - `.../actions/proposal_rebase.py:338-361`
  - `.../widgets/_agent_list_render_agent_prefix.py`
  - `.../prompt_panel/_identity_header_compact.py`
  - `.../widgets/launch_context_bar.py`
  - `.../widgets/_prompt_input_bar_title.py`
  - `.../modals/launch_approval_modal.py`
  - `.../modals/approve_options_modal.py`
  - `.../actions/agents/_notification_provider_direct.py:96`
  - the deleted `auto_approve_modal.py` (`651a32ee00^`)
  - `.../modals/wait_modal.py` (the Follow-epics toggle precedent)
- **Runtime:**
  - `src/sase/axe/run_agent_runner_launch.py:308-309`
  - `src/sase/axe/run_agent_directive_metadata.py:292-304`
  - `src/sase/main/plan_approve_handler.py`
  - `src/sase/notification_gates/{adapters,service}.py`
  - `src/sase/gate_turn/transaction.py:226`
  - `src/sase/sdd/plan_decision_handoff.py:489-578`
  - `src/sase/agent/launch_request_gate.py:254`
  - `src/sase/agent/launch_preview.py`
  - `src/sase/integrations/_agent_list_entry_models.py:184`
  - `src/sase/bead/work_prompt.py:187,226`
- **Config and docs:**
  - `src/sase/default_config.yml` (keymaps; `leader_mode`; `finalizers:`; `model_aliases:`)
  - `docs/notifications.md` (Silent Notifications; Tabs and Ordering)
  - `docs/ace.md` (Admin Center; Agent Holds)
  - `docs/macros.md` (Auto Directive)
- **sase-telegram:**
  - `src/sase_telegram/{formatting,agent_format,decision_receipt,decision_keyboard,outbound,callback_data}.py`
  - `inbound_handlers/{agent_launch,gate_completions,keyboard_cleanup}.py`
- **sase-core:**
  - `crates/sase_core/src/editor/directive/metadata.rs:770-783`
  - `editor/hover.rs:74-104`
  - `editor/diagnostics.rs`
  - `agent_launch/{typed_units,plan_resolution,wires}.rs`
  - `plan/decisions/{resolver,sheet}.rs`

**Data (computed for this report):**
- `~/.sase/prompt_history/2609.json`: 581 of 771 non-cancelled prompts (75.4%) use
  `%auto`, all bare.
- `~/.sase/prompt_history/2610.json`: 85 of 118 (72.0%), all bare. 41 auto lines are
  exactly `#plan %m:<model> %auto`.
- Gate bundles responded to within 30 days:
  - auto-resolved: `plan` 145, `epic_plan` 78, `question` 1;
  - human or other: `plan` 46, `epic_plan` 13, `sudo` 4, `custom` 1;
  - auto-resolutions per active day: median 8, max 29.

**Prior research:**
- `research:202610/auto_directive_autonomy_policy/auto_directive_autonomy_policy.md`
  (accepted as the policy baseline)
- `research:202609/sase_11e_nested_landing_loop.md` (cited through it)

**External (fetched 2026-10-08):**
- [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes)
- [Codex CLI slash commands](https://developers.openai.com/codex/cli/slash-commands) and
  [Codex approval modes (third-party overview)](https://codex.danielvaughan.com/2026/03/26/codex-cli-approval-modes-sandbox-security)
- [Gemini CLI configuration](https://geminicli.com/docs/reference/configuration.md) and
  [keyboard shortcuts](https://www.mintlify.com/google-gemini/gemini-cli/reference/keyboard-shortcuts)
- [Warp agent profiles and permissions](https://docs.warp.dev/agents/using-agents/agent-permissions)
- [Zed agent profiles](https://zed.dev/docs/ai/agent-profiles)
- [Factory Droid exec / auto-run](https://docs.factory.ai/cli/user-guides/auto-run)
- [Kiro autopilot](https://kiro.dev/docs/ide/chat/autopilot/)
- [Jules: reviewing plans](https://jules.google/docs/review-plan/)
