# `%auto` UX: Autonomy You Can See, Steer, and Account For

_Consolidated research, 2026-10-08. This report merges five independent UX reports
(`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`) with my own verification against sase
`7d50dc29c1` and sase-telegram `70701a0`, fresh gate-bundle and prompt-history counts,
and a re-check of the prior art. It accepts every recommendation of
[`auto_directive_autonomy_policy.md`](../auto_directive_autonomy_policy/auto_directive_autonomy_policy.md)
(autonomy profiles that `%auto` selects, Rust-owned policy, fail-closed parsing, one
live record, role defaults, agent awareness, audit) and uses its terms: `standard`,
`attended`, `overnight`, `epic_worker`, `on_ask`, and defects D1–D8. Everything marked
**proposed** is a design, not existing behavior._

---

## Bottom line

- **There is real UX work, and almost none of it is syntax.** Users already treat `%auto`
  as a habit: 100% of September and October uses are the bare spelling, in 75% and 73% of
  prompts. The problem is what happens around the token:
  - **You cannot see what autopilot did.** In the last 30 days the host auto-resolved
    **224 gates** (145 tale plans, 78 epic plans, 1 question). Humans answered 64. From
    October 1 to 8 the ratio is **106 to 1**. Auto gates publish no notification. The
    only trace is a quiet receipt, and only for plans that carry Plan Decisions. Every
    TUI view hides that receipt. Telegram renders it as a bare `🔔 *plan-decisions*`
    message with no buttons.
  - **The only live control lies.** `A` turns a bare-`%auto` agent "off" and clears its
    `⚡`, but the runner's `SASE_AGENT_AUTO_APPROVE=1` still auto-resolves the next gate
    (D5).
  - **The glanceable UI names the wrong thing.** `⚡`/`⚡T`/`⚡E` and `⚡ PLAN/TALE/EPIC`
    encode a plan-tier argument. They cannot name `overnight` and say nothing about
    questions or what happens when nobody is listening.
  - **Profiles that live only in docs will not be used.** Nobody typed a parenthesized
    `%auto` in three months. New power has to appear where the habit already happens:
    the `%` completion menu, the agent row, the `A` key, and the phone.
- **Recommendation: one autonomy record, shown everywhere in the same words, changeable
  from wherever you are, and accountable afterwards.** Concretely:
  1. A **named chip** (`⚡ standard`) and a **color class** (autopilot, attended,
     unattended) on every surface. Both come from one Rust summary.
  2. **Profile-aware completion, hover, and diagnostics** inside the `%auto` token you
     already type, plus a live chip in the prompt bar.
  3. **A truthful `A`** (Manual ↔ last profile) and a **`,a` picker** for choosing among
     profiles.
  4. **An Autonomy section in the Context card**: effective rules, where they came from,
     what the agent was told, and every decision made this session.
  5. **Announcements only for fan-out and refusals.** Epic auto-launches ring, with
     Pause and Manual buttons on the TUI and Telegram. Routine approvals stay quiet but
     findable, and the agent's existing completion message gains one autonomy line.
  6. **`sase autonomy` CLI** (`explain`, `list`, `log`, `pause`, `resume`, `set`,
     `show`) and a small **Telegram `/auto`** control, both writing the same record as
     the TUI.
- **One new capability ships: Pause autonomy.** It is a host-wide brake that makes every
  gate wait for you without stopping any work. It is the only control that also stops
  agents that do not exist yet, such as the workers of an epic already fanning out.
- **One capability is designed but deferred: grace windows** (`epic: approve after 30m`).
  The idea is sound and SASE already has gate deadlines. Demand is unproven, though, and
  it costs more than it looks (§5.7).
- **What not to build:** a `--auto` launch flag, numeric levels or sliders, per-profile
  rainbow colors, a toast for every decision, an autonomy deck, a policy editor in the
  TUI, a pending-gate sweep, and any "restricted" badge while provider shells run with
  bypass flags.

---

## 1. Is there actually much to do?

I started from the skeptical position: `%auto` is typed three times out of four and seems
to "just work", so the policy's P0 fixes plus a chip might be enough. The evidence says
otherwise. It also says the work is bounded.

| # | Evidence (verified this session unless noted) | Why it is a UX problem |
| --- | --- | --- |
| 1 | 30-day gate bundles: 224 auto-resolved vs 64 human. October 1–8: 106 auto vs 1 human. Auto-resolutions per active day: median 11, max 29 | The user's dominant mode is "autopilot, look later". The weakest part of today's UX is exactly **later**: auto gates create no notification (`notification_gates/service.py`, `notification_id = None if spec.auto.enabled`) |
| 2 | Receipts are posted only when a plan has decision rows (`sdd/plan_decision_handoff.py:post_auto_approval_receipt` returns early otherwise). They are `silent=True`, and the inbox dataset is "unread, non-silent" (`docs/notifications.md`) | Most automatic decisions leave no trace a user would ever see. Auto-answered questions leave none at all (U6 in `__cld`) |
| 3 | `docs/notifications.md` says auto receipts get no Telegram delivery. The plugin forwards them (`sase_telegram/outbound.py:_is_quiet_decision_receipt`) and renders them with `_format_generic` as `🔔 *plan-decisions*` | The one receipt that reaches the phone is unlabeled and has no agent link or action |
| 4 | `A` writes meta and rewrites the stored prompt (`_approve.py`, payload `set_auto_mode`). `is_auto_approve_active()` ORs the env var the runner exported at launch | The only live control can claim "off" while the next gate auto-resolves |
| 5 | Prompt history: September 581 of 771 non-cancelled prompts use `%auto`, October 86 of 118. **All bare** | Discovery must happen inside the existing habit |
| 6 | Since September, **zero** gates were answered from Telegram (all human answers came from the TUI, `sase plan approve`, or the sudo CLI). The Telegram outbound routine is running | Telegram matters for *knowing* and for *stopping*. The evidence does not support building a full remote policy editor there. Keep the phone surface small |

The verdict: roughly four pieces of work carry most of the value (§12). Everything else
in this report refines those pieces or deliberately sequences them later.

---

## 2. Where the reports disagreed, and how I resolved it

| Question | Positions | Resolution |
| --- | --- | --- |
| **User-facing noun** | grk, gem, mus say "posture". cdx and the base policy say "autonomy" plus "profile" | **"Autonomy" for the control, "profile" for named sets, "Manual" for none.** Config is `autonomy:` and the CLI is `sase autonomy`. A second noun in the UI would be a second thing to learn. "Posture" may appear in prose, never in chrome |
| **Agent-row badge** | cld: letter suffixes (`⚡A`, `⚡O`). gem: emoji and 3-letter pills (`⚡🌙`, `⚡ngt`). grk, mus: a single bolt with color. cdx: words (`auto:attended`) when space allows | **Single `⚡`, colored by a computed class** (§4.3). Letters turn into a cryptic enum once a user adds a fourth profile. Emoji widths break alignment. The name lives one glance away in the header chip, and the class is spelled in words wherever color is the only signal |
| **Color scheme** | gem, mus: one hue per profile. grk: cyan/amber from `on_ask`. cld: three classes computed from the policy | **Three computed classes plus "paused".** Custom profiles get a correct color with no configuration, and each class has a one-sentence rule a user can learn |
| **Picker key** | cld, grk, cdx: `,a`. mus: `P`. gem: `Shift+A` | **`,a`.** I checked `default_config.yml`: `P` is the Agents `cycle_deck_view`, and `Shift+A` *is* `A` (`accept_proposal`). Leader `a` is free (`,A` is the agent run log) |
| **Picker shape** | cld: a matrix of profiles × gate kinds. grk: a plain list with descriptions ("not a matrix"). cdx, gem: a list plus an effects pane | **Matrix rows plus a description footer.** Choosing a profile means comparing columns. The footer carries the sentence, the scope, and the coverage line. Manual comes first, as in grk |
| **`A` re-enable target** | cld, grk, gem: restore the last profile. cdx, mus: the configured default | **Restore the last profile this session, else the default.** The footer names the exact target (`A auto:overnight`), which answers cdx's predictability concern. 702 `:tale` users would otherwise be silently widened to `standard` |
| **Enabling `A` while a gate already waits** | cld: resolve it immediately ("already appears to happen"). cdx: never sweep a pending gate | **Never sweep.** I verified that auto-resolution only runs at gate creation (`service.py:_resolve_auto_gate`, "creation-time auto-resolution always runs inline"). Nothing re-evaluates a pending gate, so cld's observation does not hold. A keystroke meant for *future* gates must not approve a plan you have not read. The toast says the waiting gate still needs you, and Enter reviews it |
| **Per-decision loudness** | gem: a toast for every auto-resolution. cld: quiet, except that epic launches ring. grk: silent in the TUI, forwarded to Telegram. cdx: a completion digest | **Announce only fan-out and refusals; everything else is quiet and findable** (§5.5). At a median of 11 decisions a day, a toast each would train you to ignore toasts |
| **Where "what happened" lives in the TUI** | cld: a `⚡ Auto` inbox tab of every receipt. gem: an `⚡ AUTONOMY` deck plus inbox receipts. grk: silent. cdx: no permanent panel | **Per agent: an Autonomy section in the Context card. Across agents: a `⚡ Auto` inbox tab holding announcements only, plus `sase autonomy log` and the Admin Center pane.** The inbox is the *unread* dataset, so putting 11 routine rows a day there creates chores. A new deck would add a fifth deck for one section of content |
| **Telegram control** | cld: a `✋ Manual` button and `/auto` with pause. grk: a `⚡ overnight ▾` chooser and `/auto`. gem: a Pause button on every receipt. cdx: an Autonomy card | **One `⚡ <profile> ▾` button on agent cards, `/auto`, and Pause/Manual on epic alerts.** Small, because Telegram is used for knowing and stopping (§1 row 6) |
| **CLI mutation home** | grk: `sase agent auto set/clear`. cdx: `sase agent autonomy NAME -p/-m`. cld, gem: `sase autonomy set` | **`sase autonomy set`.** One noun holds profiles, live sessions, the brake, and the log. `sase agent show` and `sase agent list` still *display* autonomy where agent-centric users look. (`sase agent tribe set` is a fair counter-precedent; I chose a single home for discoverability) |
| **`--auto` launch flag** | gem: yes. cld, grk: no | **No.** The prompt token is the launch truth and survives retry, fork, and history. `sase autonomy explain -p` is the dry run |
| **`%auto:off`** | Base policy D2: fail closed. cdx: an error with Manual guidance. cld: a reserved `manual` profile with alias `off` | **Reserve `manual` (alias `off`).** Inside a session, absence of `%auto` means *inherit*, so narrowing to Manual needs an explicit token. Live toggles, launch review ("launch as manual"), and agent-authored follow-ups all need it, and `off` then means what people expect |
| **Global brake** | cld only | **Adopt** (§5.6), with one correction: the brake must force `on_ask: park`. Otherwise pausing an `overnight` agent would *decline* its plans instead of holding them |
| **Grace windows** | cld: yes (`after 20m`, a `glance` profile). cdx: "countdown/undo… not default" | **Design now, ship later, opt-in only** (§5.7) |
| **Overnight digest** | grk: a settle digest for `on_ask: deny` sessions. cdx: a completion digest for all | **No new message. Add one autonomy line to the agent's existing completion notification**, for every profile |
| **Profile semantics** | gem's table sets `attended` epics to `ask` and describes `standard` as "stop at major epics" | **Use the accepted definitions.** `attended` differs from `standard` only on questions. gem's variant contradicts the baseline |

Smaller corrections from my verification:
- `auto_badge` is not dead (cld). sase-telegram's `/list` and `/show` consume it. The CLI
  pretty table is what ignores it.
- Jules auto-approves an *unanswered plan after a timeout* (about a minute in one
  hands-on review). It is not triggered by navigating away, as cld said.
- Warp's newer "Ask questions" setting (*Never ask / Ask unless auto-approve / Always
  ask*) maps almost one-to-one onto `question: decide / recommended / ask`. That is useful
  external support for the policy's question vocabulary.

---

## 3. Design principles

1. **One record, many views.** The prompt token decides at launch. After launch, the
   session's `agent_meta.autonomy` record is the only truth. Every surface reads that
   record through one Rust summary and writes it through one mutation path. A live
   change also rewrites the stored prompt's `%auto` token, which the existing
   `set_auto_mode` mutator already does, so Retry and fork replay what you see.
2. **Show consequences, not mechanisms.** Say "Epics launch automatically", not
   `epic_plan: approval`. Cells show the *effective* outcome: `ask` under
   `on_ask: deny` renders as "declined — nobody is waiting", never as "asks you".
3. **Calm by default, loud on fan-out.** Routine decisions are quiet and findable.
   Decisions that multiply work, or that leave work undone, are announced.
4. **Tightening is free; widening is deliberate and human.** Manual, deny, and pause
   never ask for confirmation. Any widening from inside an agent run is refused: a
   `%auto` in a follow-up, `sase autonomy set`, or `resume`. Escalations granted only
   by config (P3 launch delegation) need an explicit confirmation.
5. **Honest coverage.** Every inspect view ends with the line "Covers host checkpoints
   only · the agent's shell is not restricted". Never show a padlock, a shield, or a
   "restricted" badge.
6. **Progressive disclosure.** The row bolt answers "will it act without me?" The chip
   answers "under which profile?" The picker and Context section answer "what exactly,
   and why?" `explain` answers "prove it."
7. **Restraint is the aesthetic.** No new theme, deck, or permanent panel. Each surface
   gains at most one new interactive element. Reuse existing borders, the `●` changed
   mark, the `★` recommended mark, and existing toast and notification machinery.

---

## 4. Vocabulary and visual system

### 4.1 Words

| Term | Meaning shown to users |
| --- | --- |
| **Autonomy** | How SASE handles host checkpoints (plans, epics, questions, requests) for this agent session |
| **Profile** | A named, config-defined set of rules: `standard`, `attended`, `overnight`, or your own |
| **Manual** | No profile. Every checkpoint waits for you. This is what a prompt without `%auto` means |
| **Paused** | The host-wide brake is on. Every checkpoint waits for you, whatever the profile says |
| **Coverage** | "Host checkpoints only · the agent's shell is not restricted" |

Effect wording (adapted from cdx). The UI never prints a bare `approve`, because the
compound effect matters:

| Policy value | Wording |
| --- | --- |
| `plan: approve_archive` | Tales: approve + archive, then implement |
| `plan: approve` | Tales: approve, then implement (not archived) |
| `epic: approve` | Epics: archive + launch workers |
| `question: recommended` | Questions: take the ★ recommended answer (else the first) |
| `question: decide` | Questions: the agent decides and lists its assumptions |
| `ask` (with `on_ask: park`) | Waits for you |
| `ask` (with `on_ask: deny`) or `deny` | Declined — the agent is told to skip or split |

### 4.2 Profiles a user meets

| Profile | Class | Generated one-liner | Where it appears |
| --- | --- | --- | --- |
| `manual` (reserved; alias `off`) | — | Every checkpoint waits for you | Picker (first row), completion, Telegram chooser |
| `standard` ★ default | autopilot | Tales approve + archive · epics launch · questions take ★ | Everywhere; bare `%auto` |
| `attended` | attended | Plans and epics automatic · questions come to you | Everywhere |
| `overnight` | unattended | Tales automatic · epics declined · questions decided · nothing waits | Everywhere |
| `epic_worker` (role) | attended | Like standard, but nested epics wait for you | Only where applied: chips, explain, Admin Center. Hidden from the picker unless current |
| `tale`, `epic` (compatibility) | attended | Tale-only / epic-only automation | Completion, under "compatibility". Picker only when current |

- One-liners are **generated** from effective values, never hand-written.
- A custom profile's `description:` (one sentence, at most 72 characters; adopted from
  grk) is shown *alongside* the generated line, never instead of it.
- Profile ids match `^[a-z][a-z0-9_]{0,15}$` (grk). That keeps the chip and Telegram
  callbacks short.

### 4.3 Glyphs and color classes

| Glyph | One meaning, on every surface |
| --- | --- |
| `⚡` | An autonomy profile is active (color = class) |
| `✓` | Resolved automatically |
| `✋` | Waits for you |
| `✗` | Declined by policy |
| `★` | Recommended / default (the existing Plan Decisions meaning) |
| `●` | Changed from the profile: an inline or live override (the existing gold changed mark) |
| `⏸` | Autonomy paused |
| `⏳` | Grace window counting down (only if §5.7 ships) |

The core computes the class from the effective policy, so the user never configures it:

| Class | Rule (one sentence each) | Color |
| --- | --- | --- |
| **autopilot** | Plans, epics, and questions all resolve without you | Today's auto cyan (`#5FD7FF` in the header) |
| **attended** | At least one of plans, epics, or questions waits for you | Green (`#87D787` proposed) |
| **unattended** | Nothing waits for you (`on_ask: deny`) | Amber (`#FFD75F` proposed) |
| **paused** | The brake is on | Dim grey, with `⏸` |

- **Manual shows no bolt.** An empty row prefix is the signal, as it is today (grk).
- **Glyph cleanup (U7, verified).** `⚡` currently also appears in
  `agent_run_log_modal.py` and `update_panel.py`. Reserve it for autonomy. The run log's
  RUNNING glyph becomes `▶`, matching Telegram's status tokens, and the Update panel's
  "apply now" glyph becomes `↯`.
- **Never color alone.** The class is spelled out in words in the header tooltip, the
  picker, explain, and Telegram, so monochrome terminals and color-blind users lose
  nothing (cdx).

---

## 5. The design, moment by moment

### 5.1 Compose: the prompt bar

**Live chip (proposed).** The chip sits at the right of the prompt border title, after
the existing TODO and Jinja chips (`widgets/_prompt_input_bar_title.py`). It is parsed
with the same core launch extractor, so it cannot disagree with the launch.

```text
╭─ Prompt · +sase ─────────────────────────────────────────── ⚡ standard ─╮
│ Fix the tab-strip flicker. #plan %m:opus %auto                          │
╰─────────────────────────────────────────────────────────────────────────╯
╭─ Prompt · +sase ──────────────────────────────────────────────── manual ─╮
│ Fix the tab-strip flicker. #plan %m:opus                                │
╰─────────────────────────────────────────────────────────────────────────╯
╭─ Prompt · +sase ────────────────────────── ✗ unknown profile 'ovrnight' ─╮
│ … %auto:ovrnight            did you mean overnight?   (red underline)   │
╰─────────────────────────────────────────────────────────────────────────╯
```

- **Manual is shown, dimly.** With habitual use at 73%, a *forgotten* `%auto` is the
  notable case.
- **Fan-out and macros.** `%{a | b}` branches with different policies show
  `⚡ mixed (2)`, and the tooltip lists each branch. A `%auto` that comes from a macro
  shows `from #worker` (cdx).
- **Fail closed at the keyboard.** An invalid token turns the chip red, gets an
  underline diagnostic, and blocks submit with the same sentence the launch would print.
  This brings the D1/D2 fixes forward to typing time.
- **`alt+a` (proposed; check it against the prompt editor keymap and add it to
  `default_config.yml`)** opens the same picker as `,a` in *draft* mode. Enter inserts
  or replaces the token in the visible text. There is no hidden flag and nothing sticky
  across launches (grk).

**Completion, hover, diagnostics** live in `sase-core` editor metadata, so the TUI, the
macro LSP, and nvim get them together. Follow the `%final` precedent of
config-driven completion rows. The **bare `%auto` menu lists profiles**, which grk calls
the single highest-leverage change:

```text
%auto█
  %auto              ⚡ standard   tales ✓  epics ✓  questions ★      default
  %auto:attended     ⚡ attended   tales ✓  epics ✓  questions ✋
  %auto:overnight    ⚡ overnight  tales ✓  epics ✗  questions decide · nothing waits
  %auto:manual          manual     every checkpoint waits for you
  %auto(…)           profile + overrides (plan= epic= q=)
  ── compatibility ─ %auto:tale · %auto:epic
```

- **Hover** shows the matrix, the source layer, and the coverage line.
- **Values only config may grant** (`launch=allow`, any value for `sudo` or `custom`) are
  absent from completion. If typed, they get a diagnostic: "launch=allow must come from
  a config profile".

**First launch under a profile** gets one toast, a single line priced like Claude Code's
first-use notice (grk):
`⚡ standard — tales approve + archive · epics launch · questions take ★`.

### 5.2 Review moments

- **Launch Review modal** (`modals/launch_approval_modal.py`) gains a **Child autonomy**
  row above the prompt preview. A human-approved launch keeps the child's requested
  policy, so this row must be impossible to miss. Pressing `m` launches the child as
  `%auto:manual`. Telegram's launch-approval card gets the same line and an
  `✅ Approve · manual` button. Core `render_launch_approval_preview` adds the profile to
  each unit line (cld).
- **Plan Review → Coder options** gains one row, `u autonomy ⚡ standard (inherited)`,
  so whoever approves a plan can hand the coder a different profile in the same step
  (cld).

### 5.3 Run: seeing and steering a live agent

**Rows** keep today's two-cell prefix (`_agent_list_render_agent_prefix.py`). Only the
color changes.

```text
  ⚡ sase.fix-tabs        RUNNING    opus@high   3m     ← cyan  (standard: autopilot)
  ⚡ sase.tab-docs        QUESTION   sonnet      1m     ← green (attended)
  ⚡ sase-1hx.2           RUNNING    opus       12m     ← green (epic_worker)
  ⚡ sase.nightly         RUNNING    opus       40m     ← amber (overnight: unattended)
     sase.manual-one      PLAN       opus        —      ← Manual: no bolt
```

**Header chip** (`_identity_header_compact.py`): `⚡ standard` replaces `⚡ PLAN`.
- Overrides add `●`: `⚡ standard ●`.
- While the brake is on, the chip reads `⏸ standard`, dimmed.
- While a write is in flight, it reads `⚡ standard → manual…`. It flips only after the
  record is read back (cld, cdx).
- The `Auto:` field in the agent header becomes the one-line strip:
  `Auto: ⚡ overnight · tales ✓ · epics ✗ · questions decide · nothing waits`.

**Context card → Autonomy section (proposed).** This is the one place that answers
*what will happen, why, and what has happened*. It appears whenever the session has a
profile or a decision record.

```text
── Autonomy ─────────────────────────────────────────────────────────────────
⚡ standard ● · attended · from prompt %auto(epic=ask) · session sase.fix-tabs · rev 3
  tales      ✓ approve + archive, then implement        gates.plan (standard)
  epics      ✋ wait for you                             override epic=ask ●
  questions  ★ recommended answer (else first)           gates.question (standard)
  other      ✋ launch · sudo · custom wait for you
  Covers host checkpoints only · the agent's shell is not restricted
  Inherited by: planner → coder → verify
▸ What the agent was told  (turn 2; updates at its next turn)
Decisions this session
  14:02  ✓ tale approved + archived      tab_flicker.md          standard · gates.plan
  14:09  ★ question answered             "Keep the CSS var?" → yes
  14:31  ✋ epic plan waiting for you     big_refactor.md         override epic=ask
```

- The awareness block is shown **verbatim**, folded by default (cld, grk). You can check
  exactly what the agent believed about who was listening.
- After a live edit, the fold reads "told: standard (turn 2) · your change applies to
  gates now; the agent learns it at its next turn". The UI never claims the model knows
  something that was not delivered to it (cdx).

**`A`: truthful and undoable.**

| From | `A` does | Footer label |
| --- | --- | --- |
| Any profile | Sets `manual` for the **whole session**, effective at the next gate | `A manual` |
| Manual | Restores this session's last profile, else `autonomy.default` | `A auto:overnight` (names the target) |

- **Read-back.** The chip and toast render from a read-back of the record after the
  write. This depends on the D5 fix: gates read the record live, never the env snapshot.
- **No sweep.** A gate that is already waiting stays waiting. The toast says so:
  `⚡ standard on · sase.fix-tabs — the plan already waiting still needs you (Enter)`.
- **Marks.** With marked agents, `A` applies to every one of them, like `S` for bulk
  status, and the toast reports per-target results (`⚡ 3 agents → manual`; on partial
  failure: `2 → manual · 1 failed (sase.x: stale)`).
- **Unchanged.** On `WAITING INPUT` and remote-attention rows, `A` keeps its answering
  meaning.
- **Consequence sentences, no "unapprove".**
  `✋ sase.fix-tabs is now manual — its next plan, epic, or question will wait for you`.

**`,a`: the autonomy picker (proposed; leader `a` is free).**

```text
╭─────────────────────────── Autonomy · sase.fix-tabs ───────────────────────────╮
│                    tales        epics        questions    other   nobody there │
│  0    manual       ✋            ✋            ✋            ✋       waits        │
│▸ 1 ⚡ standard     ✓ +archive   ✓ launch     ★            ✋       waits    now │
│  2 ⚡ attended     ✓ +archive   ✓ launch     ✋            ✋       waits        │
│  3 ⚡ overnight    ✓ +archive   ✗ declined   decides      ✗       declines     │
│                                                                                │
│ standard (default) — Approve and archive tales, launch epics, take the         │
│ recommended answer. Launch, sudo, and custom requests wait for you.            │
│ Applies to: whole session, from its next gate · 1 plan already waiting stays   │
│ Covers host checkpoints only · the agent's shell is not restricted             │
╰─ 0-9 apply · j/k move · enter apply · e explain · p pause all · esc ───────────╯
```

- The styling matches the deck picker: round primary border, centered bold title, and a
  legend subtitle that shortens to fit.
- **Digits apply immediately.** Letters would collide as soon as custom profiles exist.
- Role and compatibility profiles appear only when one is current.
- Opened from the prompt bar (`alt+a`), the same picker edits the draft token, and its
  footer reads "Applies to: this prompt".
- The command palette gains **Set autonomy…** and **Pause / resume autonomy**.
- **Deferred:** an in-picker override editor and "save as profile". Zero parenthesized
  uses suggest overrides are rare, and `sase autonomy set` accepts the override grammar
  for power users.

### 5.4 Gate time: "why it asked you"

When a profile parks a gate, the Plan Review subtitle, the question modal, and the
Telegram card each gain one dim line. It turns today's most confusing moment, an agent
under `%auto` that stopped anyway, into a sentence:

```text
✋ asked by policy · epic_worker: epic = ask (nested epics need you)
✋ asked by policy · %auto:tale on an epic plan
⏸ asked because autonomy is paused (you, 14:02 · 41m left)
```

A policy decline never opens a modal. It produces a decision record, an announcement
(§5.5), and the awareness block has already told the agent to split or skip.

### 5.5 After: receipts, announcements, and the completion line

Three layers, each with one job:

| Layer | Contents | Where | Loudness |
| --- | --- | --- | --- |
| **Decision record** | Every automatic outcome, including auto-answered questions (today: none) and declines: `{profile, rule, decision, option_ids, source, revision, digest}` | Context section, `sase autonomy log`, `sase gate show`, the Admin Center pane, `sase notify list` | Silent. Audit, not attention |
| **Announcement** | Events that multiply or block work. Default `autonomy.announce: [epic, decline]` | Inbox `⚡ Auto` tab (tag `autonomy`), Telegram, mobile | Epic launches ring. Declines arrive quietly, with no toast or bell, but are counted |
| **Completion line** | One summary line on the agent's existing completion notification | TUI toast/inbox, Telegram | Inherits the completion message's loudness. No new message |

```text
 ⚑ Gates 1   ✉ General 2   ⚡ Auto 2
 ───────────────────────────────────────────────────────────────────────
 ⚡ 14:20  sase.big-refactor   🚀 Epic launched automatically · 5 phases   standard
 ⚡ 14:31  sase-1hx.2          ✗ Nested epic declined · split into tales   epic_worker
```

```text
✅ sase.fix-tabs done · 12m
⚡ standard: 1 tale approved + archived · 1 question answered (★) · 0 declined
```

- **Loudness reuses existing machinery.** Announcement rows carry tags `autonomy` plus
  `autonomy-epic` or `autonomy-decline`. Users retune them with the existing
  `ace.notification_rules` (`match: {tags: autonomy-decline}`), not with a new
  per-profile knob. `autonomy.announce` decides only *whether a row exists*; delivery
  rules decide toast and sound.
- **Plan-decision receipts** keep their current quiet Telegram forwarding (a recent,
  deliberate choice) but get a real formatter (§6). Fix the contradictory
  `docs/notifications.md` paragraph (U4) in the same change.
- **Why not every receipt in the inbox?** The inbox is the *unread* dataset. At 11 a
  day, routine approvals would add a standing count and a dismissal chore. Per-agent
  history (the Context section) and the cross-agent log (`sase autonomy log`, the Admin
  Center pane) answer "what did autopilot do" without that cost. Adding `plan` or
  `question` to `autonomy.announce` opts a user into more.

### 5.6 Pause autonomy: the host-wide brake

**Semantics (proposed):**
- While paused, every gate **waits for a human**: every allow value becomes `ask`, and
  `on_ask` is forced to `park`. Without the second rule, pausing an `overnight` session
  would decline its plans instead of holding them. Explicit `deny` rules stay denials.
  Running work is never stopped.
- Gates that park during a pause **do not auto-resolve on resume.** There are no
  surprise approvals.
- Scope is **host-wide**: "stop" should mean stop. A TTL is optional (`-t 1h`). With no
  TTL, the brake holds until a human resumes it.
- **Fail closed.** An unreadable brake store counts as paused and shows
  `⚠ autonomy brake unreadable · sase autonomy resume rewrites it`. This deliberately
  inverts `%hold`'s fail-open rule (`decisions:hold-pull-fail-open`). A failed hold
  could freeze the host. A failed brake only routes gates to a human, which is what a
  prompt without `%auto` does anyway.
- Agents may **pause** (tightening) but may not **resume** (widening).

**Surfaces:**
- **TUI:** `⏸ autonomy paused · 41m` in the launch context bar, next to the existing
  `override opus@high 2h` chip. Every row bolt dims. `p` in the `,a` picker and the
  palette entry toggle it.
- **CLI:** `sase autonomy pause|resume`.
- **Telegram:** `/auto pause [1h]`, `/auto resume`, and `⏸ Pause all` on epic alerts.

**Why it earns its place.** The realistic failure is fan-out you notice late: 234 epics
auto-approved since July, 170 of them by epic workers, plus the `sase-11e`/`sase-xe`
nesting loops. Today the only remedy is killing agents. Bulk `A` cannot help, because the
workers that matter have not launched yet. The brake can only tighten, so it opens no
escalation path.

### 5.7 Grace windows: designed, deferred, opt-in

**Proposal (from cld, adjusted).** Any allow value for `plan`, `epic`, or `question` may
carry `after <duration>`, for example `epic: approve after 30m`. The gate publishes
normally with a deadline. At the deadline the host answers with the profile's option IDs
(`source: auto_resolution`, `rule: gates.epic after 30m`). A human answer before then
wins through the existing response lock. `h` / `✋ Hold for me` cancels the timer.
Viewing a gate never stops the clock. Under the brake, the window becomes a plain ask.

**Why it is feasible:** gate turns already carry `gate_timeout_seconds`, and the TUI
already renders deadlines (`_agent_gate_section.py:_deadline_text`). The new parts are
"resolve to an option at the deadline" and a scheduler routine.

**Why it is deferred:**
1. **Demand is ambiguous.** October shows 106 automatic decisions to 1 human answer.
   That is consistent with "I don't want to review" at least as much as with "I'd review
   if I could".
2. **It costs more than latency.** Today an auto gate resolves *inline in the creator's
   own turn*, and questions continue in-process (`_continue_after_auto_answered_question`).
   A windowed gate ends the creator's turn, so the work continues in a follow-up turn,
   exactly as if a human had answered. That adds one turn and loses in-process context
   for questions.
3. **cdx's objection stands for defaults.** A countdown must never be the default
   posture, and it must never be presented as undo.

**Ship it only** if users report wanting to see plans they now auto-approve, or if the
P1 decision log shows epic-launch announcements being acted on within minutes. When it
ships, add a built-in `glance` profile (plans after 10m, epics after 30m, questions after
10m) and the `⏳` overlay.

---

## 6. Telegram: small, honest, and useful away from the desk

Telegram is the surface for **knowing** and **stopping**. It is not a policy editor.

**Agent cards.** The launch acknowledgment and `/show` gain an autonomy line and one
button. Tapping the button edits the keyboard in place into a chooser. One more tap
applies.

```text
🚀 opus Launched  @sase.fix-tabs
workspace #19 · ⚡ standard (autopilot)
Fix the tab-strip flicker …
[🍴 Fork] [⏳ Wait]
[🗡️ Kill] [🔄 Retry]
[⚡ standard ▾]
      ↓ tap
[✋ Manual]   [⚡ standard ●]
[⚡ attended] [⚡ overnight]
[« Back]
```

**Epic alert** (an announcement; it rings):

```text
⚡🚀 Epic launched automatically · @sase.big-refactor
big_refactor.md · 5 phases (2 small · 3 medium)
standard · epics launch automatically
[📄 Plan] [✋ Manual] [⏸ Pause all]
```

**`/auto`** (proposed; add `auto` to `RESERVED_COMMAND_NAMES`):

```text
/auto                     → running agents with their profile, plus pause buttons
/auto <agent>             → that agent's autonomy card
/auto <agent> <profile>   → set it (manual or off stops automation)
/auto pause [1h] · /auto resume
```

```text
⚡ Autonomy · 4 running
⚡ sase.fix-tabs     standard
⚡ sase.tab-docs     attended
⚡ sase-1hx.2        epic_worker (role)
   sase.manual-one   manual
[⏸ Pause all] [⏸ Pause 1h]
```

**Receipts and fixes:**
- Replace `_format_generic` for receipts with a dedicated formatter that renders the core
  receipt wire, for example `⚡ Tale approved · @sase.fix-tabs` plus decision lines and
  `[📄 Plan]`.
- Auto-answered questions get a quiet card with a `🍴 Correct` copy-text fork, because an
  automatic answer cannot be undone (cld).
- Extend the `sase-1hi.10.6` repair work so `auto_resolution` never renders as "you via
  Telegram" (U5).

**Reliability:**
- Callbacks use `pending_actions` plus a short key holding `{agent, change, expected
  revision}` server-side. Agent and profile names would overflow the 64-byte
  `callback_data` limit.
- Acknowledge every tap promptly. "Submitted" and "applied" are distinct states: the card
  is edited only after read-back.
- A stale card (the record's revision moved) refuses with "Autonomy changed — refreshed",
  then re-renders the card. It never overwrites the newer state.
- Duplicate taps are idempotent.
- Controls retire when the session is terminal.
- There is no sticky chat mode: a typed prompt without `%auto` stays Manual.

---

## 7. CLI

`sase autonomy` follows `cli_rules.md`: subcommands sorted alphabetically, a short alias
for every long option, colored Rich output, and a bare invocation that delegates to
`list` with the standard notice.

```text
sase autonomy explain [AGENT] [-g/--gate ID] [-j/--json] [-p/--prompt TEXT]
sase autonomy list    [-j/--json]
sase autonomy log     [AGENT] [-j/--json] [-k/--kind KIND] [-s/--since 1d]
sase autonomy pause   [-r/--reason TEXT] [-t/--ttl DURATION]
sase autonomy resume
sase autonomy set     SELECTION AGENT... [-j/--json] [-n/--dry-run]
sase autonomy show    PROFILE [-j/--json]
```

- **`SELECTION` uses exactly the text that may follow `%auto`.** Examples: `manual`,
  `overnight`, `"overnight, epic=deny"`. There is one grammar to learn and one validator.
- **Inside an agent run**, `set` may only narrow and `resume` is refused. The error says
  which human surface can do it.
- **`explain` is the trust command.** It calls the same core `evaluate()` the gates use,
  so it cannot disagree with them.
  - With `-p`, it is a static dry run that never executes `$(...)` macro substitutions.
    Unresolved dynamic parts are labeled as such (cdx).
  - With `-g`, it shows the policy revision that decided a settled gate, not today's
    config.

```text
$ sase autonomy explain sase-1hx.2
⚡ epic_worker · attended    role default for epic workers · extends standard
   source: role (bead/work_prompt) · ~/.config/sase/sase.yml:212 · rev 1 · digest 3f9c…

   tales      ✓ approve + archive, then implement     gates.plan      (standard)
   epics      ✋ wait for you                          gates.epic      (epic_worker)
   questions  ★ recommended answer (else first)       gates.question  (standard)
   other      ✋ launch · sudo · custom wait for you    not auto-allowable

   decisions so far: 1 ✓ · 0 ✗ · 1 ✋ waiting (epic plan, 6m)
   Covers host checkpoints only · the agent's shell is not restricted
```

```text
$ sase autonomy log --since 1d
14:02  sase.fix-tabs       ✓ tale       approved + archived     standard · gates.plan
14:09  sase.fix-tabs       ★ question   "Keep the CSS var?" → yes
14:20  sase.big-refactor   🚀 epic       5 phases launched       standard · gates.epic  🔔
14:31  sase-1hx.2          ✗ epic       nested epic declined    epic_worker · gates.epic
```

**Existing commands:**
- `sase agent list` gains an `AUTO` column, rendered from the core badge and class.
- `--json` gains `autonomy: {profile, class, overrides, source, revision}`. The legacy
  `approve` key stays while the `sunset` flag lives.
- `sase agent show` prints the same Autonomy section as the TUI.
- `sase gate show` gains a policy line (`auto: standard · gates.plan → approve+commit`).

---

## 8. Editors, mobile, and the Admin Center

- **nvim and LSP clients** inherit completion, hover, and diagnostics from core metadata
  with no plugin work. Do not design nvim-specific chrome.
- **Mobile gateway:**
  - agent projections gain `autonomy {profile, class, badge}`;
  - announcements flow as ordinary notifications;
  - mutation reuses the Telegram action set later.
- **Admin Center → Config → Autonomy pane** sits beside Flags and Holds. It is
  read-mostly:
  - the profile matrix with layer provenance (builtin, user, project), with gold `●` on
    fields the project layer tightened, so the tighten-only rule never looks like a bug;
  - brake status, with pause and resume keys;
  - the recent decisions log.

  `e` opens the YAML at the profile and `x` shows explain. YAML stays the single writer;
  there is no form builder in v1.
- **One-time notice when profiles ship**, following the existing `*_notice_shown`
  pattern: "`%auto` now selects a profile. Press `,a` on any agent to see what it does."

---

## 9. Reliability contracts

The backend must make these true before any surface promises them.

| Situation | Required behavior |
| --- | --- |
| Live change (`A`, picker, `/auto`, `set`) | One core mutation with an expected revision. An atomic write bumps the revision, and the UI renders from read-back. States: confirmed → submitting → confirmed, or → failed with the previous state kept and a retry offered |
| Change races a gate being created | Auto-resolution reads the record once, at creation. Whichever revision it read is recorded on the decision. No cancellation is promised |
| Gate already waiting | No sweep into execution. The human answers normally |
| Two frontends edit | A stale revision is rejected and the client refreshes. No lost update |
| Config edited or deleted | The running session keeps its frozen snapshot. Explain shows "config has moved" and offers an explicit reapply, subject to ceilings |
| Successor turns (in-process, monitor, gate, handoff) | Inherit the record structurally. An old prompt or env var can never resurrect automation |
| Widening from inside an agent | Refused for `%auto` in follow-ups, `sase autonomy set`, and `resume` |
| Brake store unreadable | Treated as paused, with a visible warning |
| Unknown plugin gate kind | Evaluates to `ask`. The UI shows the consequence when nobody is there |
| Remote host unreachable (Telegram, mobile) | "Not applied". Show the last confirmed profile with its timestamp |
| Batch edit partly fails | Per-target results. Failed targets keep their old policy. No global success toast |
| Coverage line | Mandatory on the picker, explain, the Context section, `list`, and Telegram `/auto`. Shipping a chip without it is a bug (grk) |
| One renderer | Chip, strip, picker, Telegram, and explain all call one core summary. A test asserts they print identical words for the same record (grk) |

---

## 10. Rust core boundary

Under `rust_core_backend_boundary`, everything that more than one frontend displays or
decides belongs in `sase-core`. The precedent is the Plan Decisions summary that the TUI,
Telegram, mobile, and CLI already share.

| Core addition (proposed) | Consumers |
| --- | --- |
| `AutonomySummaryWire {profile, class, badge, overrides, sentence, short, cells[{kind, glyph, effect, rule, layer}], coverage, source, revision}` | Chips, rows, picker, Context section, `/auto`, `agent list`/`show`, mobile |
| `AutonomyDecisionWire` plus a `decision_sentence()` renderer | Context section, `autonomy log`, announcements, Telegram receipts |
| `autonomy_why(gate, policy, brake) -> Option<String>` | "Why it asked" lines on every surface |
| `mutate_autonomy(session, selection, expected_revision, actor)`, with the tighten-only rule for agent actors | `A`, picker, `/auto`, `set`, brake |
| `edit_prompt_autonomy(prompt, selection)` (move `set_prompt_auto_mode` out of Python) | Prompt chip, `alt+a`, stored-prompt rewrite, launch review `m` |
| Profile-aware directive role, keyword specs, hover, and diagnostics | TUI completion, LSP, nvim |

Python keeps widgets, modals, Telegram transport, and glue. Move the
`sase-core-revision.txt` pin with each binding.

---

## 11. Rollout, mapped to the policy phases

| UX phase | Ships with | Content | Size |
| --- | --- | --- | --- |
| **UX-0: stop lying** | Policy P0 | <ul><li>`A` reads and writes the live record (D5), with read-back toasts</li><li>A row chip for any `%auto` argument</li><li>Help, toasts, and docs describe observed behavior (bare `%auto` archives tales)</li><li>Telegram receipt formatter and header fixes (U4, U5)</li><li>Glyph cleanup (U7)</li><li>Fail-closed errors shown in the prompt bar</li></ul> | 5–6 small tales |
| **UX-1: one vocabulary, visible decisions** | Policy P1 | <ul><li>Core summary, decision, and why wires</li><li>Header chip and class colors</li><li>Context Autonomy section (with awareness text)</li><li>Decision records for every automatic outcome, including questions</li><li>Announcements (`epic`, `decline`) in the inbox and on Telegram</li><li>Completion line</li><li>"Why it asked" lines</li><li>Launch-review child autonomy</li><li>`sase autonomy explain/list/log/show`, plus `agent list`/`show`/`gate show` lines</li><li>Visual snapshots for each new surface (`tui.md`)</li></ul> | Epic, 3–4 phases |
| **UX-2: steer anywhere** | Policy P2 | <ul><li>Profile completion, hover, and diagnostics</li><li>Prompt chip and `alt+a`</li><li>`,a` picker</li><li>Undoable `A` with marks</li><li>`sase autonomy set`</li><li>**Pause autonomy** on all surfaces</li><li>Telegram `▾` chooser and `/auto`</li><li>Admin Center pane</li><li>One-time notice</li></ul> | Epic, 4 phases |
| **UX-3: delegation** | Policy P3 | <ul><li>An **Arm this autonomy?** confirmation for config-granted launch delegation</li><li>Child-policy line in every launch preview</li><li>Remaining budget display (children, depth)</li></ul> | Medium |
| **UX-4: data-gated extras** | After a month of UX-1 logs | <ul><li>Grace windows and `glance`</li><li>In-picker override editor</li><li>Save as profile</li><li>Per-decision Telegram receipts as a default</li></ul> | Each small to medium |

Ship UX with its policy phase, never as a trailing epic. If P2 ships without
profile-aware completion, the 100%-bare ratio will not move.

---

## 12. If you build only four things

1. **UX-0 plus the named chip.** The toggle stops lying and the agent shows its profile.
2. **The Context Autonomy section plus `sase autonomy explain`.** Every agent can answer
   "what will you do without me, and what did you do?"
3. **Epic-launch announcements with `✋ Manual` and `⏸ Pause all`** on the TUI and
   Telegram, backed by the brake.
4. **Profile-aware `%auto` completion plus the `,a` picker.** This is how profiles get
   discovered and used.

---

## 13. What not to build

| Idea | Why not |
| --- | --- |
| `--auto` flag on launch commands | A second source of truth next to the token. `explain -p` is the dry run |
| Implicit autonomy for prompts without `%auto` | `/sase_run` children and other generated launches rely on absence meaning Manual |
| Numeric levels, sliders, ladders | Profiles are not ordered: `overnight` is tighter on epics and looser on questions |
| Per-profile hues, emoji badges | They do not scale to custom profiles and break alignment. Computed classes do scale |
| A toast for every automatic decision | At 11 a day (29 at peak), toasts would stop meaning anything |
| An `⚡ AUTONOMY` deck | A fifth deck for one section of content. The Context card already exists |
| Sweeping waiting gates on enable | Approves something the user never saw, with a key meant for the future |
| "Undo" for automatic approvals | The coder or clan is already running. Offer Correct (a fork) and Manual instead |
| A Telegram profile wizard or rule editor | Profiles are config. The phone selects and stops |
| Auto-allow for `sudo`/`custom` from any surface | Those gates exist to reach a human. Pre-authorization goes through the awareness block |
| Padlock or "restricted" badges | Every provider runs with a bypass flag until P5 |

---

## 14. Open decisions for you

I recommend the first option in each row.

1. **Announcement default:** `[epic, decline]`, or `[epic]` only? Declines arrive quietly
   either way. I recommend including them, because a decline means work was left undone.
2. **Brake scope:** host-wide, or per project like `%hold`? Host-wide, because "stop"
   should mean stop.
3. **`A` re-enable target:** the last profile, or always the default? The last profile,
   with the target named in the footer.
4. **Name `overnight`, or `away`?** `away` is shorter and more accurate for a two-hour
   absence. The accepted baseline says `overnight`, and renaming is a config edit, so I
   keep `overnight` unless you prefer otherwise.
5. **Grace windows:** defer, or build in UX-2? Defer until UX-1 logs show demand.
6. **Prompt chip:** UX-2, or never? UX-2, token-writing only. Drop it if UX-2 runs long:
   completion does the discovery job.

## 15. What would change this recommendation

- **If a month of UX-2 shows only `standard` plus one other profile in use,** collapse
  the picker to Manual, `standard`, and that profile. Keep the records, announcements,
  explain, and the brake.
- **If Telegram `/auto` and the alert buttons go unused,** keep the epic alert and the
  completion line, and drop the chooser.
- **If epic-alert buttons are tapped within minutes,** that is the demand signal for
  grace windows.
- **If a hard sandbox lands (policy P5),** the coverage line gains an `enforced: shell`
  clause in the same change. Never earlier.

---

## Recommended UX design

**Make autonomy a visible, named, steerable property of every agent session, rendered
from one Rust summary and changed through one mutation path.**

- **Compose.** Keep `%auto` as typed today. The bare `%auto` completion menu lists
  profiles with generated one-liners, and hover and diagnostics share the same core
  metadata in the TUI and editors. A live prompt-bar chip shows the effective profile or
  a fail-closed error before submit. `alt+a` opens the picker to edit the token.
  `%auto:manual` (alias `off`) is the explicit narrow token.
- **Run.**
  - Rows keep a single `⚡`, colored by a computed class: autopilot cyan, attended
    green, unattended amber, paused dim, and no bolt for Manual.
  - The header chip names the profile (`⚡ standard ●`).
  - The Context card gains an Autonomy section: effective rules with provenance, the
    awareness text verbatim, and this session's decisions.
  - `A` truthfully toggles Manual ↔ the last profile, effective at the next gate. It
    never sweeps waiting gates and confirms by read-back.
  - `,a` opens a matrix picker, with Manual first, digits to apply, and a coverage line.
- **Gate time.** Every gate a profile parks says why. Declines never open modals.
- **After.**
  - Every automatic outcome gets a silent decision record, visible per agent, in
    `sase autonomy log`, and in the Admin Center.
  - Epic launches and declines are announced in the `⚡ Auto` inbox tab and on Telegram,
    tuned with the existing delivery rules.
  - Each agent's completion message gains one autonomy line.
- **Brake.** **Pause autonomy** is host-wide, optionally timed, and fails closed. It
  makes every gate wait for you without stopping work, and it never auto-resolves on
  resume.
- **Telegram.** An autonomy line and a `⚡ <profile> ▾` chooser on agent cards, an epic
  alert with Plan, Manual, and Pause buttons, `/auto`, a real receipt formatter, and
  revision-bound callbacks.
- **CLI.** `sase autonomy explain|list|log|pause|resume|set|show`. `set` takes the
  `%auto` grammar, and widening from inside an agent is refused. `agent list`, `agent
  show`, and `gate show` display the same summary.
- **Later and data-gated.** Grace windows (`after <duration>`, `glance`), an override
  editor, save as profile, and launch-delegation UX with P3.

It is **intuitive** because the new power appears where habits already are: the `%`
menu, the row bolt, the `A` key, and the phone alert. It is **reliable** because one
record, one evaluator, one renderer, read-back confirmation, revision checks, and
tighten-only agent actors sit under every surface. It is **beautiful** because it adds
almost nothing to the screen: one colored glyph, one named chip, one card section, one
picker, and quiet history until something actually multiplies or blocks work.

---

## Sources

**Researcher reports (this swarm, moved into this directory):**
- `__cdx`: session-scoped mental model, effect wording, reliability contracts, Telegram
  callback semantics, dry-run limit, no-sweep rule.
- `__cld`: usage data, surface audit and UX defects U1–U8, visual system, Context block,
  matrix picker, the brake, grace windows, receipt loudness, Rust wires.
- `__grk`: discoverability thesis, bare-`%auto` completion as top lever, binary row bolt,
  name grammar, `pending_actions` callbacks, "one renderer" test, what not to build.
- `__mus`: visibility-over-vocabulary framing, did-you-mean errors, honest coverage
  wording.
- `__gem`: posture mental model, race and generation framing, Telegram Pause button,
  CLI surface breadth. Its `--auto` flag, per-profile hues, per-decision toasts, and
  altered profile semantics were not adopted.

**Accepted baseline:**
`research:202610/auto_directive_autonomy_policy/auto_directive_autonomy_policy__final.md`
(read via `sase artifact read`).

**Lead verification:**
- **sase source** (`7d50dc29c1`):
  - `src/sase/default_config.yml`: leader-mode keys; `cycle_deck_view: "P"`;
    `accept_proposal: "A"`.
  - `src/sase/ace/tui/actions/agents/_approve.py`: payload with `set_auto_mode`.
  - `src/sase/ace/tui/actions/proposal_rebase.py:action_accept_proposal`.
  - `src/sase/agent/status_buckets.py:AUTO_APPROVE_ELIGIBLE_STATUSES`.
  - `src/sase/ops/commands/_agent_directive.py` (prompt mutators).
  - `src/sase/notification_gates/service.py` (`_start_gate_creation`,
    `_resolve_auto_gate`).
  - `src/sase/main/plan_approve_handler.py:is_auto_approve_active`.
  - `src/sase/sdd/plan_decision_handoff.py:post_auto_approval_receipt`.
  - `src/sase/axe/run_agent_exec_questions.py`.
  - `src/sase/ace/tui/widgets/prompt_panel/_agent_gate_section.py:_deadline_text`.
  - `src/sase/ace/tui/widgets/{launch_context_bar,_prompt_input_bar_title,_agent_list_render_agent_prefix}.py`
    and `prompt_panel/_identity_header_compact.py`.
  - `src/sase/integrations/_agent_list_entry_models.py`; `src/sase/agents/cli_list.py`.
  - `docs/notifications.md`: Viewing, Tabs and Ordering, Delivery Rules, Silent, Tags.
  - `docs/ace.md`: Admin Center.
  - `sase agent --help`, `sase agent tribe --help`, `sase agent hold --help`.
- **sase-telegram** (`70701a0`): `outbound.py` (`_is_quiet_decision_receipt`),
  `formatting.py` (`_format_generic`, `_format_gate`), `agent_format.py` (`auto_badge`
  consumers), `inbound_handlers/agent_launch.py` (`_build_agent_action_keyboard`),
  `custom_commands.py` (`RESERVED_COMMAND_NAMES`), and the bot runtime state under
  `~/.sase/telegram/`.
- **Data (computed 2026-10-08):**
  - **Gate bundles,** `~/.sase/interaction_requests/*/*/response.json`, last 30 days:
    - auto-resolved: `plan` 145, `epic_plan` 78, `question` 1;
    - human: `tui` 55, `plan_response` 5, `sudo_cli` 4;
    - auto per active day: median 11, max 29 (24 days);
    - by month: September 132 auto vs 77 other; October 1–8: 106 auto vs 1 TUI;
    - no `telegram` source since the bundles begin (September).
  - **Prompt history,** `~/.sase/prompt_history/2609.json` and `2610.json`: 581 of 771
    and 86 of 118 non-cancelled prompts use `%auto`, all bare.
- **Memory:** `tui.md`, `cli_rules.md`, `decisions:gates-never-block`,
  `decisions:hold-pull-fail-open`, `decisions:single-turn-agents`, and glossary entries
  for deck, card, deck panel, gate, and gate turn.

**External (checked 2026-10-08):**
- [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes): the
  status-bar mode indicator; Shift+Tab cycles default → acceptEdits → plan, with auto
  outside the loop.
- [Warp agent profiles & permissions](https://docs.warp.dev/agents/using-agents/agent-permissions):
  per-action *Agent decides / Always ask / Always allow / Never*; the "Ask questions"
  setting; profiles switched from the input area.
- [The New Stack: Jules vs Claude Code](https://thenewstack.io/agentic-coding-how-googles-jules-compares-to-claude-code/)
  and [InfoWorld: agentic coding with Jules](https://www.infoworld.com/article/4086269/agentic-coding-with-google-jules.html):
  unanswered plans auto-approve after a timeout.
- As cited by the researchers: Microsoft HAI guidelines, Google PAIR, VS Code agent
  approvals, the Telegram Bot API (64-byte `callback_data`), W3C use-of-color and
  status-message guidance, Codex CLI, Gemini CLI, Zed, Factory Droid, Kiro, NN/g "Power
  of Defaults", and the GOV.UK check-answers pattern.
