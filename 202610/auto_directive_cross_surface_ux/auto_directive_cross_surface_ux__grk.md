# Run as posted: `%auto` as a named posture across ACE, Telegram, and the CLI

> **Research query:** Make `%auto` much more configurable, intuitive, and powerful.
> All recommendations in `auto_directive_autonomy_policy.md` are accepted. That work
> focused on policy. This report leads the UX: TUI, CLI, and Telegram. What is the
> best possible user experience? Additional integrations are in scope when they are
> genuinely helpful. End with a recommended UX design that is intuitive, reliable,
> and beautiful.

![Infographic titled "Run as posted." Three columns show the ACE/TUI agent list and posture picker, a Telegram agent card with an overnight digest, and `sase autonomy` / `sase autonomy explain`; a shared posture strip across the bottom reads "⚡ overnight · tales archive · epics ask · questions decide · on_ask deny" with a coverage line distinguishing host-enforced gates from the cooperative shell.](auto_directive_cross_surface_ux_infographic.jpg)

## Bottom line

The policy object is settled. I keep it. Named config profiles, a selector `%auto`,
narrow overrides, one live record, role defaults, fail-closed parsing, agent
awareness, and host-enforced option IDs are the right engine. This report designs
the experience around that engine. The whole design follows from one sentence:

> **Run as posted.**

Every surface shows the same named posture next to the agent, with the same words.
You can change the posture without launching anything. The primary action (`A` in
ACE, the lightning button on Telegram, a bare `%auto` in the prompt, `sase agent
auto set`) writes the same live record the gate evaluator reads. Absence of `%auto`
stays Manual. The chip, the prompt token, the Telegram card, and `sase autonomy
explain` cannot disagree.

There is real UX work here. The policy's chip, picker, and three read-only CLI
commands are the skeleton. They are not the experience. **The actual UX problem is
discoverability.** Since July, **12,142 of the recorded `%auto` spellings are
bare**, **702 are `:tale`, and zero are parenthesized**. People already treat
`%auto` as a binary flag they type by ritual. A more powerful policy that is only
reachable by typing `%auto:overnight` will be unused. The UX has to put named
postures in front of the user at the three moments they already have: composing a
prompt, glancing at a running agent, and walking away with a phone.

These are the twelve choices that make it work. The first seven are UX. The last
five are reliability.

1. **One shared [Posture Strip](#the-posture-strip) built in sase-core.** Every
   surface renders the same record and the same words, for example
   `⚡ overnight · tales archive · epics ask · questions decide · on_ask deny`.
2. **[ACE list rows stay binary](#ace-tui).** A cyan `⚡` means "this agent will
   act without you on some gates"; an amber `⚡` means `on_ask: deny` (walking
   away). The profile *name* lives in the compact identity header, the detail
   `Auto:` field, the footer, and the picker. List columns are too tight for
   `overnight`.
3. **`A` stays a toggle. `,a` opens the picker.** `A` never cycles unbounded
   user-defined profiles. Off restores Manual. On restores this agent's last
   posture this session, defaulting to `autonomy.default`. The picker is how you
   choose among many.
4. **[Bare `%auto` completion lists profiles](#prompt-authoring).** This is the
   highest-leverage change. The menu that already opens on `%` tokens must offer
   `standard`, `attended`, `overnight`, role profiles, and compatibility
   spellings *before* the colon, each with its one-line description.
5. **[Telegram is the walking-away surface](#telegram).** `/show` grows a
   `⚡ overnight ▾` button that opens the same picker. `/auto` sets a live
   posture by name. Overnight sessions send a settle digest. Per-gate quiet
   receipts keep flowing as they do today.
6. **[CLI: inspect under `sase autonomy`, mutate under `sase agent auto`](#cli).**
   The three read-only commands from the policy stay. Live changes belong next
   to `sase agent hold` and `sase agent tab`, because they mutate an agent.
   There is no `--auto` launch flag; the prompt token remains the launch source
   of truth.
7. **[One visual language](#visual-language).** `⚡` stays the glyph. Cyan is
   attended-capable, amber is unattended, gold `●` marks a live override, `★`
   marks the profile default. Coverage is always a dim line:
   `host-enforced: gates · cooperative: shell, network`. There is never a
   padlock or a "restricted" badge while the provider still runs with a bypass
   flag.
8. **The prompt token is always visible.** A chrome control that inserts
   `%auto:overnight` is welcome. A hidden session flag that disagrees with the
   prompt is forbidden.
9. **Defaults resolve before the receipt identity is computed.** Toggling `A`,
   tapping Telegram, and `sase agent auto set` produce the same
   `agent_meta.autonomy` record the evaluator reads.
10. **Submissions bind to the live record.** A later config edit never widens a
    running agent. A stale Telegram picker is refused.
11. **Fail closed in the surface that authored the mistake.** Unknown profiles
    and illegal overrides are launch errors in the prompt bar, `/auto` callback
    toasts, and CLI stderr, with the same sentence and the configured names.
12. **Receipts name the posture.** Auto-approved plans, auto-answered questions,
    and policy denials all record `{profile, rule, decision, source, digest}`.
    Silent in the TUI inbox; forwarded on Telegram the way plan-decision
    receipts already are.

## Scope and method

I agree with every recommendation in
[`research:202610/auto_directive_autonomy_policy/auto_directive_autonomy_policy.md`](../auto_directive_autonomy_policy/auto_directive_autonomy_policy.md),
including the phased rollout, the role default that stops nested-epic
auto-approval, the tighten-only project layer, the awareness block, and the
decision that absence of `%auto` stays Manual. This report does not reopen those
questions.

It asks a different one: once that policy exists, what should a person *see and
touch*?

Verification for this report covered sase workspace `sase_21` (ACE identity
header, Agents-tab `A` toggle, keymap `accept_proposal: "A"`, directive
completion for `%auto`, quiet `%auto` receipts, Config hub catalog),
sase-telegram (`/list` / `/show` auto badges, agent action keyboard, quiet
decision-receipt forwarding, 64-byte callback encoding), `docs/macros.md` Auto
Directive and completion tables, `docs/ace.md` glyphs and the `A` contract,
`docs/cli.md` agent commands, `docs/notifications.md` silent receipts, and the
official Claude Code permission-mode docs plus Codex sandbox/approval docs as
prior art. Syntax and chrome below marked **proposed** describe a design, not
existing behavior.

## Is additional UX actually worth building?

Yes. Three facts make "just ship the policy and a chip" fail as an experience.

**People do not type arguments.** Bare `%auto` is the product. Colon values are
already a compatibility graveyard (`:epic` has zero uses). Parenthesized forms
have zero uses *and currently fail open*. A profile grammar that is only
documented will not be discovered.

**The glanceable UI is a three-value enum pretending to be a flag.** ACE list
rows show `⚡` / `⚡T` / `⚡E`. The compact header shows `⚡ PLAN` / `⚡ TALE` /
`⚡ EPIC`. Telegram `/list` repeats the same badge. Help text still says
"Auto-approve (plan)". None of that can name `overnight` or `epic_worker`. If
the chip keeps encoding tale-vs-epic, the new profiles are invisible at the
exact moment you scan a busy Agents tab.

**Walking away is a different surface from launching.** The policy's `overnight`
profile is a phone posture: you leave, and you want a way to put running work
into unattended mode and a way to see what it did. Telegram already lists
agents, kills them, and forwards quiet plan-decision receipts. It has no way to
set `%auto`. The TUI `A` key cannot help you from a train.

What is *not* worth building is equally important. A visual policy-matrix
editor, per-gate-kind toggles on every row, a Claude-style Shift+Tab cycle
through unbounded profiles, a second `%caps` chrome, interactive CLI prompts, a
hidden prompt-bar mode that disagrees with the token, and a padlock badge on an
unsandboxed shell are all extra surface area that would make the feature less
intuitive. Those sit in [What not to build](#what-not-to-build).

## What the surfaces do today

This section is verified against current code and docs.

### ACE / TUI

| Surface | Today |
| --- | --- |
| Agents list prefix | `⚡` when `approve` is set; `⚡T` / `⚡E` when `auto_approve_plan_action` is `tale` / `epic` (`_agent_list_entry_models.auto_badge`, `test_agent_list_status_indicators.py`) |
| Compact identity header | Chip `⚡ PLAN` cyan, `⚡ TALE` gold, `⚡ EPIC` violet (`_identity_header_compact._auto_approve_chip`) |
| Detail metadata | `Auto: ⚡ PLAN` (same three values) |
| `A` (`accept_proposal`) | Toggles *bare* `%auto`. On writes `approve: true` and clears tale/epic. Off removes `approve`, `auto_approve_plan_action`, and `auto_approve_argument`. Toast: `Auto-approve enabled (%auto)` / `Auto-approve disabled`. Footer: `auto-approve` / `unapprove` (`actions/agents/_approve.py`, `test_keybinding_footer_agent.py`) |
| Help | `A` is labeled "Toggle %auto / answer local or remote attention". Glyph legend still lists `⚡` / `⚡T` / `⚡E` |
| Prompt completion | `%auto` / `%a` complete bare, plus, and `%auto:...` with fixed values `plan`, `tale`, `epic`. No keywords. (`docs/macros.md` completion table) |
| Config hub | Sub-tabs are misc, flags, holds, launch, memory, snippets, macros. No autonomy page |
| Gate modal | Auto-resolved gates never appear. Manual plan review is the Decisions rail from the plan-decisions UX |
| Receipts | Quiet `plan_decisions_receipt` notifications, `silent=True`, no TUI unread bump, no toast. Telegram *does* forward them (`sase_telegram/outbound.py` `_is_quiet_decision_receipt`) |
| Persistence bug (policy D5) | `A` updates meta; the runner's `SASE_AGENT_AUTO_APPROVE=1` snapshot can keep auto on. The toggle looks like it worked |

`A` is already overloaded by context (WAITING INPUT uses it to answer). That
overload stays; the posture toggle remains Agents-tab, active-status only.

### Telegram

| Surface | Today |
| --- | --- |
| `/list` | Micro-badge `⚡` / `⚡T` / `⚡E` on the overview line (`agent_format.entry_micro_badges`) |
| `/show` | Detail grid row `Auto  ⚡` or `Auto  ⚡T tale` |
| Agent keyboard | Fork, Wait, Kill, Retry. No auto control (`_build_agent_action_keyboard`) |
| Slash commands | `/list`, `/show`, `/kill`, `/fork`, `/changes`, `/macros`, `/bead`, `/usage`, `/update`. No `/auto` |
| Launch | Plain text launches an agent; `%auto` in that text works as a prompt token |
| Callbacks | `action:id:choice`, hard 64-byte cap; overlong payloads already go through `pending_actions` + a short key |
| Quiet receipts | Plan-decision auto receipts are the one silent notification class Telegram forwards |

### CLI

| Surface | Today |
| --- | --- |
| Launch | `%auto` in the prompt string. No `--auto` flag, which is the right default |
| Live edit | `sase agent persist-directive` with a `set_auto_mode` payload; TUI `A` is a client of this. There is no human-facing `sase agent auto` |
| Inspect | `sase agent show` / `sase agent list -j` expose the meta triad, not a posture sentence |
| Plan review | `sase plan approve -D id=value` (plan-decisions UX). Independent of `%auto` |
| Proposed by policy | `sase autonomy list` / `show` / `explain` — do not exist yet |

### Prompt token

`docs/macros.md` and the core memory row still describe the June behavior
("bare does not commit"). Since July 18 the tale primary branch is approve +
archive, so bare `%auto` matches Enter. The policy's P0 already owns the doc
fix. UX should describe *observed* behavior in every chip and completion row
from day one, or the new chrome will teach the old lie.

## Prior art, translated

Claude Code, Codex, Cursor, Gemini CLI, and OpenCode all solved "how often does
this agent stop" as a **named mode next to the prompt**, with a short cycle or
a dropdown, and a status-bar sentence you can read without opening settings.

Claude Code is the closest analog, and the one to steal from carefully:

- **Named postures with jobs, not a permission DSL in the prompt.** Manual,
  Accept edits, Plan, Auto, Don't ask, Bypass. Each row in the docs is a "best
  for". SASE's `standard` / `attended` / `overnight` / `epic_worker` are the
  same idea at the *gate* layer.
- **A visible indicator that updates as you switch.** CLI status bar
  (`⏵⏵ auto mode on`), VS Code mode indicator on the prompt box, Desktop
  selector next to send, mobile `+` → Permission. SASE already has the
  lightning chip; it just names the wrong enum.
- **Project settings cannot turn on the dangerous modes.** Claude ignores
  `auto` and `bypassPermissions` in `.claude/settings.json`. That is the
  policy's project tighten-only rule, and the UX must say so in `sase autonomy
  show` as layer provenance.
- **The cycle is a *small, ordered* set.** Shift+Tab walks Manual → Accept
  edits → Plan, with Auto as a side door. SASE profiles are user-defined and
  unbounded. Cycling them with `A` would be a trap the first time someone adds
  a fourth profile. Toggle + picker is the SASE translation of Shift+Tab +
  dropdown.
- **First-use notice.** Claude tells you once when Auto becomes the default.
  SASE should toast the posture at launch (`⚡ standard — tales archive ·
  questions recommended`) for the same reason: 70% of prompts will keep using
  the default, and they deserve to know what it now *means*.

Codex splits sandbox (what can run) from approval_policy (when to ask) from
approvals_reviewer (who answers). SASE's coverage line is that split in one
sentence: host-enforced gates versus a cooperative shell. Codex profiles are
whole config files selected with `--profile`. SASE already has a better
selector (`%auto:<name>`) sitting in the prompt; it does not need a parallel
`--auto` flag that can disagree with the token.

The GOV.UK check-answers pattern and NN/g's "power of defaults" still apply,
the same way they did for plan decisions. People accept the default. The
default profile must match today's observed bare `%auto`. Alternatives must
appear at the moment of choice, which for SASE is the `%` completion menu and
the picker, not a wiki page.

## Design principles

1. **Posture, not a matrix.** Daily use is a named job ("I'm walking away"),
   matching the policy's `overnight` / `attended` / `epic_worker`. The matrix
   is what `explain` is for.
2. **Prompt-first.** SASE launches are prompt documents. Claude's hidden
   session mode is a REPL affordance. The token in the prompt is the launch
   source of truth; chrome writes the token, it does not shadow it.
3. **One record, many views.** Compact (list bolt), named (header chip),
   sentence (strip), table (`explain`). Same `EffectiveAutonomyPolicy`.
4. **Absence is Manual, and Manual is visible by being empty.** No ghost
   "manual" badge on every row. The empty column is the signal, the same way
   today's rows without `⚡` already work.
5. **Coverage is a caption, never a shield.** If the shell is unrestricted,
   the UI says so. Beauty here is honesty.
6. **Progressive disclosure.** List: will it wait. Header: which posture.
   Picker / explain: every gate kind and why.
7. **The phone is a first-class author of live policy.** Overnight is not a
   TUI-only idea.
8. **Errors name the configured world.** `unknown profile 'nighhtly'.
   configured: standard, attended, overnight, epic_worker`.

## The Posture Strip

sase-core owns one renderer. Python, Telegram, the CLI, and the mobile
gateway call it. Nothing else concatenates gate values into a sentence.

**Full strip (explain, picker footer, Telegram detail, agent show):**

```text
⚡ overnight · tales archive · epics ask · questions decide · on_ask deny
host-enforced: gates · cooperative: shell, network
```

**Named chip (compact header, Telegram button, CLI list mark):**

```text
⚡ overnight
```

**List bolt (Agents tab prefix, `/list` micro-badge):**

```text
⚡     # cyan  — some gates auto, on_ask is park
⚡     # amber — on_ask is deny (unattended)
      # empty — Manual
```

**Override mark.** A live inline override (`%auto(overnight, q=ask)` or a
picker change that diverges from the profile) adds the Config-pane gold `●`
after the name: `⚡ overnight ●`. The strip then includes the override:
`questions ask ●`.

**Source chip**, shown in explain and in the picker subtitle, using the
policy's `source` field: `prompt` · `tui` · `cli` · `telegram` · `inherited` ·
`role` · `launch_clamp`.

The profile's `description:` is the one-line job statement in menus. Builtin
profiles ship with sentences, not with gate lists:

| Profile | Description (proposed) |
| --- | --- |
| `standard` | Approve and archive tales, launch epics, answer questions. |
| `attended` | Same as standard; questions wait for you. |
| `overnight` | Walking away. Epics wait; questions are decided; no parked gates. |
| `epic_worker` | Nested epics wait for a human. |
| `tale` | Compatibility. Tales auto; epics wait. |
| `epic` | Compatibility. Epics auto; tales wait. |

**Name grammar, as a UX constraint on the schema.** Profile ids are
`^[a-z][a-z0-9_]{0,15}$`. Sixteen characters is the compact-header budget and
keeps Telegram callbacks short. Descriptions are one sentence, ≤ 72
characters. Both are validated at config load, the same way finalizer instance
ids are.

## ACE / TUI

### Agents list

Keep the lightning prefix. Replace `⚡T` / `⚡E` with a single `⚡` whose color
carries `on_ask`. Tale-versus-epic was a compatibility enum; it is no longer
the thing you need at scan time. The scan questions are "will this wait" and
"did I leave this unattended". Color answers the second without eating the
name column.

Workflow children keep the connector alignment they have today
(`└─ ⚡ `). Help's glyph table drops `⚡T` / `⚡E` once the sunset flag for the
legacy meta triad is gone; until then the legend lists them as compatibility
spellings.

### Compact identity header

Row 1 already has name, model, auto chip, machine. Replace `⚡ PLAN` with
`⚡ <profile>`. Truncate the name at 12 cells with a single `…`. Gold `●`
follows when overrides are present. The existing cyan/gold/violet tale-tier
colors retire for this chip; cyan/amber from `on_ask` take their place, so the
header and the list agree.

Row 2 (macros, queue, wait) is unchanged. The posture does not get a second
row; the strip belongs in the expanded detail, not in the compact pair.

### Expanded detail

Replace `Auto: ⚡ PLAN` with two lines:

```text
Auto: ⚡ overnight ●
      tales archive · epics ask · questions decide · on_ask deny
```

A third dim line is the coverage caption. `sase agent show` prints the same
block, so the TUI panel and the CLI cannot drift.

Show the awareness block the *agent* received in a folded `Awareness` section,
default-collapsed. Trust is "I can see what it was told."

### `A` and `,a`

| Key | Action |
| --- | --- |
| `A` | Toggle. Manual ↔ last posture this session (default `autonomy.default`). Eligible statuses only, same as today |
| `,a` | Open the Posture picker. Leader-mode, Agents tab. Bound in `ace.keymaps` as `pick_autonomy` (new), default `,a` |

`A` on a `%auto:tale` agent currently *collapses* it to bare `%auto`. After
this design, `A` off is Manual and `A` on restores `tale` (the last posture),
which is the intuitive inverse of unapprove. The persist payload writes the
same `agent_meta.autonomy` record the evaluator reads; it no longer depends on
`SASE_AGENT_AUTO_APPROVE` (policy D5).

Footer labels, state-aware:

| State | `A` label | `,a` label |
| --- | --- | --- |
| Manual | `auto` | `posture` |
| Any posture | `manual` | `posture` |

Toasts name the posture: `overnight enabled` / `manual — gates will wait`.
Persist failure still toasts as an error and rolls back the optimistic row,
same as today.

`A` on WAITING INPUT stays "answer". Do not steal it.

### The Posture picker

A small OptionList modal, in the family of the model picker and the save
location picker. Not a form. Not a matrix.

```text
┌─ Posture ──────────────────────────────────────────┐
│  Manual                                            │
│  You decide every gate.                            │
│                                                    │
│  ⚡ standard                                 ★ now │
│  Approve and archive tales, launch epics,          │
│  answer questions.                                 │
│                                                    │
│  ⚡ attended                                        │
│  Same as standard; questions wait for you.         │
│                                                    │
│  ⚡ overnight                                       │
│  Walking away. Epics wait; questions are decided.  │
│                                                    │
│  ⚡ epic_worker                          role       │
│  Nested epics wait for a human.                    │
│                                                    │
│ host-enforced: gates · cooperative: shell, network │
│ enter select · A toggle · q back                   │
└────────────────────────────────────────────────────┘
```

Rules:

- Manual is first.
- Configured profiles follow in config order, compatibility names last.
- `★` is `autonomy.default`. `now` is this agent's live posture.
- `role` marks a role-applied profile the user did not type.
- Enter writes the live record and, for a not-yet-launched prompt, inserts or
  replaces the `%auto` token in the prompt bar (see below).
- The dim coverage line is always present.
- `e` jumps to the Config Autonomy page for the highlighted profile. Editing
  happens in config, not in this modal.

### Gate modal

Auto-resolving gates still do not appear. That is the feature.

When a gate *does* appear because the posture said `ask`, the compact Verdict
gains one dim caption: `overnight · epic: ask`. You know this waited on
purpose. The Decisions rail from the plan-decisions UX is unchanged. Enter
still means Approve as shown.

A policy `deny` never opens a modal. It posts a quiet denial receipt and the
agent is told through the awareness block.

### Config hub

Add an `autonomy` catalog child next to `holds` and `launch`. It is a
**read-mostly table**, not a form builder.

Columns: name, description, layer (builtin / user / project), default mark,
role marks. Gold `●` on fields the project tightened. Enter opens the YAML
location in `$EDITOR`. `sase autonomy show` is the CLI twin.

This is genuinely helpful because layer provenance is otherwise invisible, and
the policy's tighten-only rule will otherwise look like a bug ("I set
overnight in the project and it didn't loosen questions"). It is not a policy
IDE.

### Prompt bar, while composing

See [Prompt authoring](#prompt-authoring). The Agents-tab chrome above is for
*live* agents. The prompt bar is for the next launch.

## Prompt authoring

This is the highest-leverage UX change in the whole design.

The directive completion menu already auto-opens on `%` tokens
(`ace.prompt_completion.auto_directive_menu`). Today, `%auto` inserts `%auto`
and `%auto:` offers `plan`, `tale`, `epic`. Tomorrow, **the menu for `%auto`
with or without a colon lists profiles**.

```text
%auto█
  %auto                 standard — approve and archive tales, launch epics, answer questions.
  %auto:attended        questions wait for you
  %auto:overnight       walking away
  %auto:epic_worker     nested epics wait
  %auto:tale            compatibility · epics wait
  %auto:epic            compatibility · tales wait
  %auto(...)            profile + overrides
```

`%auto(` then offers profile names first, then the allowed override keys
(`plan`, `epic`, `q`/`question`) with their legal values. Illegal keys
(`launch=allow`, `sudo=approve`) are omitted from completion *and* rejected at
launch with the same sentence.

The Rust directive contract already feeds ACE, the macro LSP, and nvim. Profile
rows belong in that contract. nvim gets them for free. Do not design a unique
nvim chrome.

A **prompt-bar ⚡ chip** that inserts or removes the token is a P2 convenience,
modeled on Claude Desktop's selector next to send. Constraints, if it ships:

- It writes `%auto` / `%auto:<profile>` into the visible prompt. It never
  stores a parallel flag.
- Empty prompt + chip on → inserts `%auto` (the default profile) at the top.
- Chip off → removes the `%auto` directive, leaves the rest of the prompt.
- Long-press / `,a` while the prompt is focused opens the same picker, whose
  Enter inserts the token.
- It is *not* sticky across launches. A remembered default that auto-inserts
  `%auto` would surprise the 30% of prompts that are Manual on purpose, and
  would leak into pasted machine-generated launches.

P1 is the completion menu. The chip is sugar.

After a successful TUI launch with a posture, one toast:

```text
⚡ standard — tales archive · questions recommended
```

One toast per launch is enough teaching. It is the Claude "auto is on" notice,
priced at a single line.

Fail-closed errors land in the prompt bar as an error toast *and* keep the
prompt unsent:

```text
unknown profile 'nighhtly'
configured: standard, attended, overnight, epic_worker, tale, epic
```

```text
sudo cannot be auto-allowed from a prompt; put it in a config profile
```

The CLI prints the identical sentences. Telegram `/auto` answers the callback
with the identical sentences (200-character `answerCallbackQuery` budget is
enough).

## Telegram

Telegram is where `overnight` becomes real. The TUI cannot help you from a
train.

### `/list` and `/show`

Keep the micro-badge. Recolor it cyan/amber from `on_ask`, matching ACE.
`/show`'s `Auto` row becomes the named chip plus the strip:

```text
🐙 builder — details
▶ 2m14s

Auto     ⚡ overnight
         tales archive · epics ask · questions decide · on_ask deny

Model    opus @ high
...
```

### The live control

Add one button to the existing Fork / Wait / Kill / Retry keyboard:

```text
[🍴 Fork]     [⏳ Wait]
[🗡️ Kill]     [🔄 Retry]
[⚡ overnight ▾]
```

Tap opens a radio keyboard of Manual + configured profiles, current marked
`●`, with a `✓ Set` primary. Edits happen in place, the same way plan
decisions already flip on the main keyboard. The message is edited once to
show the new chip.

Implementation: `pending_actions` + a short key, *not* `encode("auto",
agent_name, profile)`. Agent names already strain the 64-byte callback budget
on Kill. Profile names would push it over. The show/retry code already uses
this pattern.

`/auto` is the slash twin:

```text
/auto                  → picker for the last /show agent, or a chooser
/auto overnight        → set last agent
/auto overnight builder
/auto manual builder
```

Plain-text launches already honor `%auto` in the message. Do not add a second
launch wizard. Completions on the bot are not a thing; the `/auto` chooser
covers discovery on the phone.

### Receipts and the overnight digest

Keep forwarding quiet plan-decision receipts. Extend the same silent-but-
forwarded class to:

- auto-answered questions (today: 46 auto vs 20 human, and *no* receipt)
- policy denials (a nested epic `overnight` refused)

Each receipt's first line names the posture:

```text
🤖 Auto-approved tale foo · overnight
grouping = mode ★
```

For profiles with `on_ask: deny`, also post **one settle digest** when the
session becomes terminal, instead of relying on a hail of per-gate cards:

```text
🌙 builder settled · overnight
✓ 2 tales archived
✗ 1 epic denied — no human
• 3 questions decided by the agent
```

Standard/attended keep per-gate receipts and skip the digest. Those postures
assume you might still be watching.

Stale picker: if the live record's digest moved after the card was sent, `✓
Set` is refused with `posture changed — /show again`. Same reliability rule as
plan-decision revision binding.

## CLI

Follow `cli_rules.md`: excellent `-h`, alphabetized subcommands, short aliases
on public long options, colored output, bare group delegates to `list`.

### Inspect — `sase autonomy`

The policy's three commands, with the list default:

```text
sase autonomy                 # notice + list
sase autonomy list            # -j/--json
sase autonomy show <profile>  # -p is not needed; positional
sase autonomy explain [<agent>|<prompt>]
```

`list` prints the table in [The Posture Strip](#the-posture-strip), marks
`autonomy.default` with `★`, marks role-claimed profiles, and ends with the
coverage line.

`show` prints layer provenance (builtin < user < project), `extends`, every
gate value, and gold `●` on tightened fields. This is how the tighten-only
rule becomes visible.

`explain` is the trust command. It shares `evaluate()` with the runtime. Forms:

```text
sase autonomy explain builder
sase autonomy explain --prompt '%auto:overnight fix the flake'
sase autonomy explain --prompt '%auto(attended, epic=deny) +sase #pr:x'
```

Output is the strip, then a per-kind table of `{decision, option ids, source,
ceiling}`. A `--gate plan` filter is a later nicety; v1 prints every kind.

Short aliases: `-j/--json`, `-p/--prompt` on explain. Agent name is positional
to match `sase agent show`.

### Mutate — `sase agent auto`

Live changes are agent operations:

```text
sase agent auto               # notice + list live postures
sase agent auto list
sase agent auto show -n builder
sase agent auto set  -n builder -P overnight
sase agent auto clear -n builder
```

`-P/--profile` (capital P) avoids colliding with the many meanings of `-p` on
agent commands (`cli.md` already warns that `-n` and `-p` are not one flag
across the agent group). `-n/--name` matches `sase agent kill`.

`set` / `clear` write the same persist-directive path `A` uses, so a CLI
change is visible in ACE on the next refresh and vice versa.

There is no `sase launch --auto`. The prompt token is the launch source of
truth. `explain --prompt` is how you dry-run a token.

### `sase agent show` and `sase agent list`

The Auto block in `show` becomes the named chip plus the strip, identical to
the TUI expanded detail. JSON grows `autonomy` as the structured record; the
legacy triad stays until the sunset flag drops.

## nvim, LSP, mobile, Config YAML

- **nvim / macro LSP.** Same Rust completion rows as ACE. No extra chrome. A
  hover on `%auto:overnight` can show the strip; that is a P2 using the same
  renderer.
- **Android / mobile gateway.** The agent list already carries `auto_badge`.
  Swap it for the named chip + color. Mutations can wait: Telegram is the
  phone author in v1, and the gateway already executes generic gate actions.
  A native picker is a follow-up once the live record exists.
- **YAML.** People will edit profiles in config. The Config hub table and
  `sase autonomy show` are the UX; a form builder is not. Snippet examples in
  `docs/configuration.md` next to `finalizers:` are part of shipping P2.

## Receipts, awareness, and after-the-fact beauty

The quiet `%auto` receipt is already the most-seen surface of plan decisions
(about three plans in four). Once postures exist it is also the most-seen
surface of *this* feature. Treat it that way.

- First line: `🤖 Auto-approved <plan> · <profile>`.
- Decision lines unchanged from the plan-decisions receipt.
- New: a one-line strip under the title when the receipt is rendered in
  `sase notify list` and on Telegram.

Question auto-answers and policy denials join the same class, so overnight
does not go missing in the transcript.

The awareness block the policy proposed is instruction-layer, labeled as
cooperative. UX shows it to the *human* in agent detail, folded. If the agent
was told "no human will see gates", the owner can confirm that sentence is the
one they meant.

## What not to build

| Idea | Why it fails |
| --- | --- |
| Cycle all profiles with `A` / Shift+Tab | Profiles are unbounded; Claude's cycle works because it is three plus a side door |
| `--auto` launch flag | A second source of truth next to `%auto`; `explain --prompt` already dry-runs the token |
| Sticky prompt-bar default that auto-inserts `%auto` | Surprises Manual launches and pasted machine prompts |
| Per-kind toggles on the agent row | That is what profiles exist to collapse |
| Visual policy-matrix editor in Config | YAML plus `show` provenance; a form will lag the schema |
| Padlock / "restricted" badge | The shell is unrestricted until P5; a shield would be theater |
| Numeric autonomy levels 0–5 | False ordering; the policy already dropped this |
| A second `%caps` chrome | One posture object; hard permissions attach later |
| Interactive CLI `[Y/n]` | Agents and scripts drive this CLI |
| Flashing auto-resolved gates in ACE | Auto means the modal does not appear |
| Telegram step-wizard to *create* profiles | Profiles are config; the phone only *selects* |
| Rainbow per-profile colors | Cyan/amber from `on_ask` scales; five named hues do not |
| Making absence of `%auto` mean `standard` | Machine-generated launches (`/sase_run` children) rely on Manual |

## Phasing, aligned with the policy rollout

UX ships *with* the policy phases, not as a separate epic that trails them.

| Phase | UX that lands with it |
| --- | --- |
| **P0** truth and safety | Toasts and help text describe observed behavior (bare archives tales). `A` reads the live record (D5). Footer labels stay. Completions still offer `plan`/`tale`/`epic`, mapped to the reserved profiles once they exist |
| **P1** policy object, no new syntax | Named chip (`⚡ standard` / `⚡ tale` / `⚡ epic`) replaces `⚡ PLAN`. Posture strip in detail, `sase agent show`, receipts. `sase autonomy list/show/explain`. Launch toast. Coverage caption. Awareness folded into detail. Question and denial receipts |
| **P2** profiles and overrides | Bare `%auto` completion lists profiles. `,a` picker. Telegram `⚡ ▾` + `/auto`. Config hub Autonomy table. Cyan/amber list bolts. Gold `●` overrides. `sase agent auto set/clear`. Overnight settle digest |
| **P3** bounded launch delegation | Launch-preview strip on the child: `child will run as ⚡ epic_worker`. Telegram launch-approval cards show the child's strip before you tap Yes |
| **P4** standing approvals | Picker gains "keep for this session, N h" as a TTL row, reusing `%hold`'s model. Not a new glyph |
| **P5** hard permissions | Coverage line gains a third clause when a real sandbox exists. Only then may a surface say `enforced: shell` |

P1 is already a better product with no new prompt syntax: the chip stops
lying, explain exists, receipts name the posture. P2 is the one that makes
profiles *used*. If P2 ships without bare-`%auto` completion, the 12,142-to-0
ratio will not move.

## Reliability contract

1. **One renderer, one evaluator.** The strip, the chip, the Telegram button
   label, and `explain` all call sase-core. A test asserts they print the same
   words for the same record.
2. **One persist path.** `A`, `,a`, `/auto`, and `sase agent auto set` all
   write `agent_meta.autonomy` through persist-directive. Optimistic TUI
   updates roll back on failure, as they do today.
3. **Launch-frozen policy.** A config edit does not widen a running agent.
   `explain` on a live agent shows the frozen record plus a dim "config has
   moved" note if the digest differs, so you know a *next* launch would
   change.
4. **Stale Telegram cards refuse.** The pending_actions payload stores the
   digest; mismatch → callback toast, no write.
5. **Fail closed at the authoring surface.** Unknown profile, illegal
   override, mixed `%auto:x(...)`, extra positionals: the prompt is not sent,
   `/auto` does not write, the CLI exits 2. Same sentence everywhere.
6. **Coverage caption is mandatory** on picker, explain, detail, and
   `autonomy list`. Shipping a chip without it is a bug.
7. **Manual is the empty state.** Tests assert that a row without `%auto` has
   no bolt, no Auto field, and `explain` says every kind is `ask`.

## Recommended UX design

Ship **Run as posted.**

**Shared.** A sase-core Posture Strip and named chip, cyan/amber from `on_ask`,
gold `●` for overrides, a coverage caption on every inspect view, receipts
that name the profile.

**ACE.** Binary bolt on the list; named chip in the compact header; strip in
detail; `A` toggles last posture; `,a` opens a small picker with Manual first;
Config hub gains a read-mostly Autonomy table; gate modals that wait say why.

**Authoring.** Bare `%auto` completion lists profiles with one-line jobs. The
Rust contract feeds ACE, LSP, and nvim together. Launch toasts the strip once.
Errors keep the prompt unsent. A prompt-bar ⚡ chip that writes the token is
optional P2 sugar.

**Telegram.** `/show` shows the strip. A `⚡ <profile> ▾` button and `/auto`
write the live record through pending_actions. Quiet receipts keep flowing and
gain question + denial siblings. Overnight sessions add one settle digest.

**CLI.** `sase autonomy` for inspect (list default, show, explain).
`sase agent auto` for live set/clear/show. No `--auto` flag. `sase agent show`
prints the same Auto block as the TUI.

**Explicitly out of v1 chrome:** cycling, sticky hidden defaults, per-kind row
toggles, a policy IDE, a padlock, interactive CLI, auto-flashing gates.

This is intuitive because the default path is the path people already take
(type `%auto`, press `A`, glance for a bolt), and the new power appears in
those same three places. It is reliable because one record, one renderer, one
persist path, and fail-closed authoring sit under every surface. It is
beautiful because the list stays quiet, the name is a chip, the sentence is
one line, and the phone card becomes its own overnight receipt.

## Open UX decisions for the lead

These are presentation choices on top of accepted policy. I recommend the
left-hand option in each row.

1. **List bolt: color vs. short code.** Color (cyan/amber) vs. `⚡n` / `⚡a`.
   **Color.** Short codes become a new cryptic enum the moment a fourth
   profile appears.
2. **`A` restore last vs. always `standard`.** **Last posture this session.**
   Restoring `tale` after unapprove is the inverse people expect; always
   jumping to `standard` would surprise every `:tale` user (702 of them).
3. **Picker key `,a` vs. `Shift+A`.** **`,a`.** Shift+A is unreliable in
   terminals; leader-mode is the SASE pattern (`,x` restart, `,H` collapse).
4. **Overnight digest vs. only per-gate receipts.** **Digest on settle, plus
   per-gate.** Per-gate alone is noisy on a phone; digest alone hides the
   moment something is denied.
5. **Prompt-bar ⚡ chip in P2 vs. never.** **P2, token-writing, not sticky.**
   Completions do the discovery job; the chip is for the Claude-Desktop
   muscle memory of "selector next to send." Skip it if P2 is already large.

## What would change this recommendation

- If P2 ships and a month of completions data shows people still only pick
  `standard`, collapse the picker to Manual / standard / one other, and keep
  the strip, receipts, and Telegram control.
- If Telegram usage of `/show` is negligible next to ACE, still ship `/auto`
  (it is small) but drop the settle digest until overnight is observed on
  that surface.
- If a hard sandbox lands earlier than P5, promote the coverage line's
  `enforced: shell` clause with it; do not wait on chrome.

## Sources

**Accepted baseline** (read through `sase artifact read`):
[`auto_directive_autonomy_policy.md`](../auto_directive_autonomy_policy/auto_directive_autonomy_policy.md).
Related UX baseline:
[`plan_decisions_cross_surface_ux.md`](../plan_decisions_cross_surface_ux/plan_decisions_cross_surface_ux.md)
("Approve as shown," quiet `%auto` receipts, Telegram in-place keyboards,
Decision Sheet in sase-core).

**Internal, verified in this workspace:**

- ACE list bolt and header chips: `src/sase/integrations/_agent_list_entry_models.py`,
  `src/sase/ace/tui/widgets/prompt_panel/_identity_header_compact.py`,
  `src/sase/ace/tui/widgets/prompt_panel/_agent_display_header_metadata_identity.py`,
  `tests/ace/tui/widgets/test_agent_list_status_indicators.py`
- `A` toggle: `src/sase/ace/tui/actions/agents/_approve.py`,
  `src/sase/ace/tui/widgets/_keybinding_bindings_agents.py`,
  `tests/test_keybinding_footer_agent.py`,
  `src/sase/default_config.yml` (`accept_proposal: "A"`)
- Help glyphs: `src/sase/ace/tui/modals/help_modal/agents_reference_sections.py`,
  `docs/ace.md` Agent Row Glyphs and the `A` contract
- Completions: `docs/macros.md` directive completion table;
  `tests/ace/tui/widgets/test_directive_completion_candidates.py`
- Persist path: `src/sase/ops/commands/_agent_directive.py` (`set_auto_mode`)
- Receipts: `src/sase/sdd/plan_decision_handoff.py`,
  `docs/notifications.md` Plan decision `%auto` receipts
- Config hub children: `src/sase/ace/tui/modals/config_hub_session.py`
- CLI rules: `sase/memory/cli_rules.md`; agent commands in `docs/cli.md`
- Telegram: `sase-telegram` `agent_format.py`, `outbound.py`,
  `inbound_handlers/agent_show.py`, `inbound_handlers/agent_launch.py`
  (`_build_agent_action_keyboard`), `callback_data.py` (64-byte cap),
  `README.md` slash commands
- Policy defects D1–D8 and usage (12,142 bare / 702 `:tale` / 0 parenthesized;
  69.5% of prompts) as reported in the accepted baseline

**External:**

- [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes):
  Shift+Tab cycle, status-bar sentences (`⏵⏵ auto mode on`), VS Code indicator
  on the prompt box, Desktop selector next to send, mobile `+` → Permission,
  project settings ignoring `auto` / `bypassPermissions`, first-use Auto notice
- [Codex sandbox and approvals](https://developers.openai.com/codex/concepts/sandboxing):
  `sandbox_mode` × `approval_policy` × `approvals_reviewer`; profiles as
  selected config files; auto-review as a reviewer *behind* deterministic rules
- [Codex auto-review](https://developers.openai.com/codex/concepts/sandboxing/auto-review)
- NN/g, [The Power of Defaults](https://www.nngroup.com/articles/the-power-of-defaults/)
- GOV.UK, [Check answers](https://design-system.service.gov.uk/patterns/check-answers/)
- Telegram Bot API: `callback_data` 64-byte limit, `answerCallbackQuery` 200
  characters (already the sase-telegram constraint)

_Independent swarm report · researcher grk · 2026-10-08._
