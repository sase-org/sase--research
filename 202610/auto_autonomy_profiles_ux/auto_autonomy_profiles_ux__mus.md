# `%auto` User Experience: Making Autonomy Configurable, Intuitive, and Beautiful

> **Researcher:** mus · **Swarm role:** UX lead for the `%auto` redesign ·
> **Date:** 2026-10-08 · **Workspace source tree:** sase (this checkout)
> **Stance on the base policy:** I agree with all recommendations in
> `research:202610/auto_directive_autonomy_policy/auto_directive_autonomy_policy.md`
> (hereafter **"the base policy"**). I reviewed it in full before doing my own
> research. This report does not relitigate its backend decisions (config profiles
> selected by `%auto`, narrow overrides, fail-closed parsing, one persisted record,
> agent awareness, Rust-owned evaluation). It answers the question the base policy
> left open: **what should all of that feel like to use?**

## Bottom line

- **There is genuinely a lot to do here — but almost none of it is syntax.**
  Today's `%auto` syntax (bare, `:tale`, `:epic`, `+`) is already terse and
  muscle-memoried (69.5% of prompts). The UX problem is everything around it:
  auto-resolutions happen **silently**, the TUI shows a cryptic `⚡` glyph that
  cannot distinguish postures, there is **no way to preview** what a profile will
  do, Telegram shows no auto receipt, the `A` toggle does not reliably stick, and
  error messages arrive mid-run instead of at launch. Users cannot see, predict,
  or trust what `%auto` will do — so they either over-trust it (bare `%auto`
  everywhere, including the 170 nested-epic auto-approvals) or avoid it.
- **The recommended UX keeps daily typing as short as today and moves all power
  into visible, named, previewable postures.** One directive, three built-in
  profiles with plain-language meanings, a picker instead of memorized keywords,
  a profile chip everywhere the agent already appears, a quiet receipt for every
  auto decision, and one `explain` command that is the source of truth on every
  surface (TUI, CLI, Telegram, mobile).
- **Beauty is calm, not chrome.** The design below deliberately adds only one new
  interactive element per surface (a picker in the TUI, three read-only commands
  in the CLI, a footer line plus one command in Telegram). Everything else is
  restating existing information in plain words where the user already looks.

## Method and sources

I verified the current UX against this checkout's source (not docs alone):

- Directive surface: `src/sase/macro/_directive_types.py` (compat suggestions,
  aliases), `docs/macros.md` Auto Directive section (~lines 3025–3063) and the
  completion table (~lines 2042–2072).
- Gate semantics: `src/sase/notification_gates/adapters.py`
  (`resolve_auto_selection`, `_default_branch_selection`, per-kind
  `auto_policy`), `src/sase/main/plan_approve_handler.py`
  (`is_auto_approve_active`, env/meta layering).
- TUI: `src/sase/ace/tui/actions/agents/_approve.py` (`A` toggle),
  `src/sase/ace/tui/widgets/prompt_panel/_identity_header_compact.py`
  (`⚡ PLAN/TALE/EPIC` chip), `src/sase/ace/tui/widgets/_agent_list_render_agent_prefix.py`
  (`⚡`/`⚡E`/`⚡T` prefix), `Auto:` header field in
  `_agent_display_header_metadata_identity.py`.
- Telegram: `sase-telegram` sidecar (opened via `sase repo open sase-telegram`) —
  `formatting.py` (gate icons, message budget), `agent_format.py` (Auto badge
  row), `inbound_handlers/macro_commands.py`, `decision_keyboard.py`.
- CLI inventory: `sase --help` / `sase gate --help` / `sase run --help`
  (no `autonomy` commands exist yet — confirming the base policy's CLI sketch is
  greenfield).
- Precedents I lean on: `%final` + `finalizers:` (config instances selected by a
  short directive, with **config-driven completion rows** in docs/macros.md:2052),
  `%hold`/`%queue` keyword grammar, `%dispatch` machine-alias completion.

I did not consult any peer report from this swarm.

## The current UX, surface by surface

### Prompt typing (all surfaces)

Bare `%auto` / `%a`, plus-form, and `:plan` / `:tale` / `:epic`. Completion
suggests the three compat values. Strengths: short, memorable, one dial.
Weaknesses (all confirmed in the base policy's defect table): parenthesized
forms fail open to full automation (D1), `%auto:off` enables auto (D2), and the
colon value conflates "which plan tier" with "whether a human is needed" so
`:epic` silently auto-answers questions (D4). **Typing is the one place users
already feel competent — the redesign must not make them feel otherwise.**

### TUI

- `A` toggles bare `%auto` for the selected agent (`_approve.py`); no panel, one
  toast. Fast and loved, but it can only express on/off and can disagree with the
  runner's env snapshot (D5).
- The agent list prefixes `⚡` (bare), `⚡T`, `⚡E`; the detail header shows
  `⚡ PLAN/TALE/EPIC` plus an `Auto:` field. Compact, but the glyphs encode the
  *tier-conflict* vocabulary rather than anything the user chose, and they say
  nothing about questions, launch, or what happens when no human is listening.
- Completion rows for `%auto` are static (`plan`, `tale`, `epic`) — unlike
  `%final`, which completes **configured instance names**. Profiles will be
  invisible at typing time unless completion becomes config-driven too.

### CLI

There is no autonomy surface at all: no list/show/explain, and `sase gate show`
does not mention policy. The CLI user debugs `%auto` surprises by reading
`agent_meta.json` and env vars — the exact layering the base policy removes.
The base policy's `sase autonomy list/show/explain` sketch is the right shape;
my contribution below is what each command must display to be trustworthy.

### Telegram (and mobile/inbox by extension)

Gate cards carry per-kind icons (`📋` plan/epic, `❓` question, `🚀` launch) and
decision keyboards; the agent list shows an `Auto` badge row. What is missing is
the **after** half: auto-resolved gates publish no notification (by design — the
creator keeps running), so from Telegram an `%auto` agent simply goes quiet and
work appears later. There is no "auto-approved by X" receipt, no statement of
what the profile will auto-resolve while you are away, and no way to change
posture except by typing a new prompt. For the user walking away from their
phone — the canonical `%auto` user — this is the whole ballgame.

### Docs and help

`docs/macros.md` describes the opaque-argument model accurately but teaches the
tier vocabulary (`:tale` vs `:epic`) without ever stating the two facts users
most need: (1) bare `%auto` archives tale plans (approves **and** commits), and
(2) any `%auto` spelling auto-answers questions. Both are D3/D4 fallout.

## Is there much to do? Yes — visibility, not vocabulary

I went in expecting to design a kinder keyword language. The evidence says that
is the wrong prize: only 702 `:tale` uses and zero parenthesized uses in three
months means users vote for the shortest spelling and never look back. The
genuine UX gaps, ranked by user harm:

1. **Silence.** Auto decisions leave no trace where users look (inbox,
   Telegram). Silent authority is the top complaint class in the base policy and
   the top trust risk.
2. **Unpredictability.** No preview, no per-kind statement, stale docs. Users
   cannot answer "what will `%auto` do to my epic plan at 2am?"
3. **Coarse control.** On/off toggle only; no attended/unattended distinction at
   the surface, though that is exactly how users think ("I'm here" vs "I'm
   walking away").
4. **Late errors.** Malformed `%auto` fails mid-run at the gate, far from the
   typing moment. Fail-at-launch with a fix suggestion is a UX feature.
5. **Cryptic display.** `⚡E` vs `⚡T` teaches internals; profile names teach
   intent.

## Design principles (UXrestatement of the base policy)

1. **One dial stays one dial.** `%auto` remains the only autonomy directive. No
   `%caps`, `%perm`, or numbered levels.
2. **Type postures, not mechanisms.** Profiles are named for human situations
   (`attended`, `standard`, `overnight`), each with a one-sentence promise.
   Gate-kind keywords exist but are the exception, not the daily path.
3. **Never type what config should remember.** The picker and completion offer
   configured profiles first (the `%final` precedent); hand-typed overrides are
   narrow and always previewable.
4. **Every auto decision is visible where the user already looks.** Chip,
   inbox, Telegram, receipt — same words everywhere.
5. **Honest coverage.** Every surface states "host gates only — shell commands
   are not restricted" until hard permissions ship. No reassuring badges.
6. **Errors arrive at typing time and name the fix** ("did you mean
   `%auto(overnight, epic=deny)`?"), never as a mid-run gate failure.
7. **Calm beauty.** One new control per surface, consistent tokens and colors,
   plain sentences over tables wherever possible.

## Recommended UX design

### 1. The typing language (shared across TUI, CLI, Telegram, LSP)

Keep every spelling that works today, and add exactly the base-policy grammar —
presented here as users meet it, shortest first:

```text
%auto                    # default posture (today's behavior, now named "standard")
%a:attended              # named posture
%auto(q=ask)             # default posture + one override
%auto(overnight, epic=deny)
```

Aliases: `q` → `question`, `e` → `epic` (canonicalized, shown canonically in
previews). Rules users can hold in their heads: **one `%auto` per launch; first
word (if bare) names a posture; the rest are `kind=value` adjustments; anything
else is a launch error that suggests the fix.** Privileged kinds (`launch`,
`sudo`, `custom`, …) accept only `ask`/`deny` from prompts — prompts can never
widen them, so there is nothing to memorize there.

Completion (TUI prompt box, LSP, Telegram command input) follows the `%final`
precedent exactly: **configured profile names first with one-line descriptions,
then kind keywords; profile rows preview their per-kind behavior inline.**

```text
%auto(|)                     →  standard    Approve tales+epics, answer questions
                               attended    Ask me questions; auto-approve plans
                               overnight   Decide questions yourself; deny epics…
                               ─────────────────────────────
                               q= / plan= / epic= / launch= …
```

### 2. Built-in postures (the only three most users ever meet)

| Posture | Promise (shown verbatim in picker, chip tooltip, explain) |
|---|---|
| `standard` | Approve tale and epic plans, answer questions with your recommended option. Ask me for launches and everything else. |
| `attended` | Everything `standard` does, except questions always come to me. Use when you are watching. |
| `overnight` | No human is listening. Approve tale plans, decide questions yourself and list your assumptions, deny epics and launches, park anything else. |

`epic_worker` exists as a role default (nested epics ask) but is hidden from the
picker — machinery, not a user choice. Projects may add postures or tighten
built-ins; they can never widen them (same trust rule as Claude Code ignoring
project-level `auto`).

### 3. TUI

- **Chip names the posture.** Replace `⚡ PLAN/TALE/EPIC` with `⚡ standard`,
  `⚡ attended`, `⚡ overnight` (custom profiles: `⚡ <name>`). Color by posture
  family, not tier: `attended` blue, `standard` cyan, `overnight` amber —
  glanceable from across the room. The agent-list prefix keeps the bare `⚡`
  (space is tight) but gains the posture color; the `E`/`T` suffixes retire with
  the tier vocabulary. The `Auto:` header field becomes
  `Auto: overnight (q=decide, epic=deny · sase config)` — posture, effective
  deviations, source.
- **`A` keeps toggling the default posture** (muscle memory preserved).
  **`P` opens the posture picker**: profile names, one-sentence promises,
  and the effective per-kind outcome for *this* agent (post-ceiling, so role and
  parent clamps are already applied — what you see is what the agent gets).
  Live agents can switch posture; the change writes the same single policy
  record the base policy defines (fixing D5's env-snapshot staleness), toasts
  `"Overnight on — questions will be decided, epics denied"`, and is audit-logged.
- **Gate rows that auto-resolve stay visible as quiet receipts**, styled dimmer
  than pending gates: `"✓ auto-approved by overnight (plan=approve_archive)"`.
  Nothing silently vanishes; nothing shouts.
- **Agent detail gains one Effective Autonomy section**: per-kind outcome +
  which layer set it (prompt / picker / role / parent ceiling / config digest).
  This is the `explain` output rendered in place — one implementation, two
  skins.

### 4. CLI

Three read-only commands exactly as the base policy sketches (names/placement
per `cli_rules.md`, read before implementing), with display contracts:

- `sase autonomy list` — posture names, promises, and provenance
  (`builtin · user · project (tightened)`).
- `sase autonomy show <profile>` — per-kind outcomes plus the coverage line:
  `"Enforced at host gates. Shell, network, and writes outside the workspace
  are not restricted by this profile."`
- `sase autonomy explain <agent|prompt>` — per kind: **what will happen, why
  (rule + source), and what the agent was told** (awareness-block digest). This
  command shares its evaluator with the runtime (base policy R10), so its
  answer can never disagree with real behavior — that guarantee is the feature,
  and it is what makes `explain` the debugger for every other surface.
- `sase gate show` gains one policy line per gate
  (`"auto: overnight → decide (recommended option)"` or `"auto: ask (you)"`).

### 5. Telegram (and inbox/mobile, same words)

- **Auto receipts.** Every auto-resolved or denied gate posts one quiet message:
  `"✓ Auto-approved tale plan by *overnight* (plan=approve\\_archive)."` /
  `"⛔ Denied epic launch by *overnight* (launch=deny) — split into tales."`
  Same `{profile, rule, decision}` triple as the TUI receipt and the audit
  record — the user learns one sentence shape and recognizes it everywhere.
- **Pending gates state the future.** While a gate waits: `"⏳ … (will
  auto-approve as *standard* · plan=approve)"`. No more wondering whether to
  keep watching.
- **Posture control from chat.** `/auto` with no args prints the current
  posture and promise; `/auto overnight` / `/auto attended` relaunches or
  retargets the agent's policy record (same write path as the TUI picker);
  launch prompts accept the same `%auto(...)` spellings with the same
  completion rows. Decision keyboards are unchanged — auto never mints
  authority through button order.
- **Agent cards** keep the `Auto` row but print the posture and promise
  (`Auto: overnight — no human will see gates during this run`) instead of the
  badge glyph. Message-budget discipline from `formatting.py` applies: receipts
  are one line, promises truncate with the existing markers.

### 6. The agent as a user (awareness block)

The five-line context block from the base policy ships verbatim in UX terms —
it is the cheapest item here and fixes blind question-answering (D8). Its UX
requirements: it names the posture, states per-kind behavior in verbs, lists
pre-authorized actions explicitly, and is labeled instruction-layer (soft).
`/sase_questions` gains one line: *"mark your recommended option first — in
unattended postures it is chosen automatically."*

### 7. Errors and edges (where reliability becomes UX)

- Unknown profile/key/value, extra positionals, mixed `:profile(...)` forms:
  **launch error naming the fix**, with did-you-mean over profile names
  (`%auto(overnite)` → `"unknown profile 'overnite'. Did you mean 'overnight'?"`).
- Tier mismatch (`:tale` on an epic) becomes `ask`, not an error and not silent
  automation — the receipt says why.
- Absence of `%auto` stays fully manual, stated in the picker empty-state and
  in docs, because machine-generated launches depend on it.
- Toggle-off applies to the live policy record immediately (D5 fix) and the
  toast names the consequence (`"Auto-approve off — next plan will wait for you"`).
- Question schema: at most one `recommended` option per question; free-text-only
  or malformed questions stay manual rather than guessing.

### 8. What deliberately does not ship (to keep it beautiful)

No second directive, no numeric levels, no `launch=allow` from prompts, no
`sudo`/`custom` auto-allow, no per-tool permissions UI until the P5 enforcement
layer exists (showing toggles the host cannot enforce would be decoration, and
decoration here is dishonest). Standing approvals and model-review (`P4`) reuse
the `%hold` TTL idiom when they come — one temporal vocabulary, not two.

## Rollout from the user's point of view

- **P0 (no new syntax):** receipts appear, docs state the two D3/D4 facts, `A`
  sticks, epic workers stop auto-approving nested epics, errors move to launch.
  Users feel safer with nothing new to learn.
- **P1 (policy object):** chips name postures, `explain`/`list`/`show` land,
  awareness block appears. Users can see and predict.
- **P2 (profiles + picker):** `/auto`, `P` picker, Telegram posture control.
  Users can steer.
- **P3+:** bounded delegation and friction reducers arrive as new posture
  options and receipt lines — no new interaction patterns to learn.

## Open questions for the lead (unchanged from the base policy, UX lens)

1. Nested-epic default (`ask` vs `max_depth=1`): UX-identical except the receipt
   line; I favor `ask` first.
2. Whether bare `%auto` keeps launching top-level epics: keep, but the receipt
   must say so loudly enough that the 64 affected users notice once.
3. Auto-archive default: keep `approve_archive` in `standard`, documented in the
   promise sentence — the picker makes the alternative one keypress away.
4. Absence stays manual: yes, with a `#auto`-style macro or prompt default for
   convenience rather than implicit config.

## What would change this recommendation

If P1 audit data shows users living in exactly two postures, collapse the
built-ins and keep receipts, roles, awareness, and `explain` — they carry the
value. If the felt friction turns out to be tool-level (shell/network) rather
than gate-level, the same posture picker fronts the P5 section; no UX rework,
only new rows.

## Sources (directly inspected)

Base policy `auto_directive_autonomy_policy.md` (full); `src/sase/macro/
_directive_types.py`; `src/sase/notification_gates/adapters.py`;
`src/sase/main/plan_approve_handler.py`;
`src/sase/ace/tui/actions/agents/_approve.py`;
`.../widgets/prompt_panel/_identity_header_compact.py`;
`.../widgets/_agent_list_render_agent_prefix.py`;
`.../widgets/prompt_panel/_agent_display_header_metadata_identity.py`;
`docs/macros.md` (Auto Directive, completion table); `sase --help`,
`sase gate --help`, `sase run --help`; `sase-telegram`
`formatting.py`, `agent_format.py`, `macro_commands.py`,
`decision_keyboard.py`.
