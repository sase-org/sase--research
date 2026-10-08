# Making `%auto` Configurable: How to Split the Work into Verifiable Epics

> **Research query:** `%auto` should become much more configurable, intuitive, and
> powerful. Accepting all recommendations in
> `auto_directive_autonomy_policy.md` (policy) and `auto_autonomy_profiles_ux.md`
> (UX), what is the best way to split the work into multiple epics such that each
> epic has distinct, verifiable results — and is such a split possible without too
> many hoops?
>
> **Researcher:** mus (independent swarm report, 2026-10-08).
> **Method:** read both accepted baselines via audited artifact reads; verified the
> current `%auto` seams in this checkout (`src/sase/macro`,
> `src/sase/main/plan_approve_handler.py`, `src/sase/notification_gates/service.py`,
> `src/sase/bead/work_prompt.py`, `sase-core`); checked SASE bead/flag/CLI/memory
> rules. Did not consult any peer report from this swarm.

## Bottom line

- **Yes, split — into three shippable epics plus one explicitly deferred epic.**
  The work separates cleanly along seams that already exist in the codebase, and
  each piece lands a user-visible, independently testable behavior change:
  1. **Epic A — Truth and safety (stop the silent automation).** Fail-closed
     parsing, live-read policy record, uniform inheritance, nested-epic stopgap,
     truthful `A` toggle, docs/memory truth. Verifiable the day it lands: no
     prompt spelling silently grants more than it says, and epic workers stop
     minting nested-epic auto-approvals.
  2. **Epic B — Policy foundation (Rust-owned policy + CLI truth).** One
     `EffectiveAutonomyPolicy` in `sase-core`, frozen at launch, read live at
     every gate, explicit option-ID selection, audit fields, `sase autonomy
     explain/list/show/log`, agent awareness block. Verifiable without any TUI:
     one evaluator, one CLI proof command, identical words everywhere.
  3. **Epic C — Profiles and steering (config + every-surface control).**
     `autonomy:` config with layering and tighten-only project rule, role
     defaults, `%auto:<profile>` / `%auto(...)` selector grammar, prompt
     completion + chip, `,a` picker, undoable `A`, Context Autonomy section,
     epic/decline announcements, `sase autonomy set`, Telegram `/auto` +
     chooser, host-wide **Pause autonomy**. Verifiable by a profile × gate-kind
     outcome matrix plus TUI screenshots and phone cards.
  4. **Epic D (deferred, do not staff yet) — Bounded delegation.** Config-only
     `launch: allow(...)` with cumulative budget, atomic reservation, retry
     identity/refund, attenuation, and launch-preview UX. Staff it only after
     B + C are in users' hands; demand today is 49 launch gates in three months.
- **Do not make P0 a six-epic swarm, and do not make the whole thing one epic.**
  P0 items are tales-sized individually but share one verdict ("nothing is silent
  anymore"); shipping them as scattered tales loses the single verification pass
  that proves the bleeding stopped. One giant epic fuses the two-repo Rust landing
  with TUI/Telegram polish and cannot demonstrate anything until everything works.
- **The split needs no exotic machinery.** Three guardrails carry the whole plan:
  a versioned `agent_meta.autonomy` record frozen at launch (later epics only add
  keys), a compatibility translation for every legacy spelling, and a `sunset`
  flag for legacy meta/env readers while old runners drain. Each epic moves the
  `sase-core-revision.txt` pin at most once, and only Epic B introduces new wire.
- **Deliberately deferred:** grace windows / `glance`, standing approvals,
  `review(@model)` (all data-gated on Epic C logs), and hard tool/sandbox
  permissions (a separate decision on the same profile object, only after
  per-provider deny-honoring is verified under the bypass flags SASE passes).

## What the two baselines jointly require

Both reports agree on the architecture; the UX report explicitly accepts every
policy recommendation. The combined requirement stack is:

- **Policy object, not a bigger directive.** Named profiles defined in config
  (`autonomy:` with `version`, `default`, `roles`, `profiles`), following the
  `%final` / `finalizers:` precedent. `%auto` selects (`%auto`,
  `%auto:<profile>`, `%auto(<profile>, k=v)`); narrow inline overrides adjust.
  Bare `%auto` selects `standard` (today's *observed* behavior, documented).
- **Per-gate-kind decisions mapping to explicit option IDs**, never UI defaults
  (`primary_branch`, `default_selected`, option order). This is the D3 root-cause
  fix: a keymap change once silently changed what `%auto` publishes.
- **Fail-closed launch validation.** Unknown profiles/keys/values, extra
  positionals, mixed forms, and any prompt-typed `launch=allow` / `sudo` /
  `custom` allow are launch errors (fixes D1/D2 fail-open).
- **Resolve once, read live, inherit by one rule.** Frozen `agent_meta.autonomy`
  (`policy`, `profile`, `overrides`, `source`, schema version, config digest);
  gates read it live (fixes D5 env-snapshot staleness); every successor
  (in-process, monitor, gate, handoff) inherits structurally without re-emitting
  `%auto` strings (fixes D6); `%dispatch` ships the resolved record.
- **Role defaults for generated launches.** `bead/work_prompt.py` emits the
  configured role's profile instead of a literal `%auto`, ending the 170
  nested-epic auto-approvals (D7). Epic `max_depth` budget arrives with profiles.
- **Agent awareness + audit + visibility.** ~5-line awareness block rendered into
  context (fixes D8 blind questions); every auto outcome records
  `{profile, rule, decision, option_ids, source, revision, digest}`; TUI chip
  names the profile; `sase autonomy` CLI (`explain`, `list`, `log`, `pause`,
  `resume`, `set`, `show`); Telegram `/auto` + chooser + epic alerts; Pause
  autonomy brake (host-wide, TTL-optional, fail-closed, never auto-resolves on
  resume).
- **Rust owns the shared semantics.** Schema, parse, merge/clamp, `evaluate()`,
  summary/decision wires, mutation with revision checks, prompt-token
  editor metadata — consumed by TUI, CLI, Telegram, mobile, LSP. Python keeps
  adapter I/O, bundles, executor, glue. Each Rust landing moves the
  `sase-core-revision.txt` pin (see `docs/rust_backend.md`).
- **Honest coverage.** Every inspect view states "host checkpoints only · the
  agent's shell is not restricted" while provider bypass flags are on. No
  padlocks, shields, or "restricted" badges.

## Why this split is possible without too many hoops

I checked each proposed seam against the current code. All four hold.

### 1. Gate resolution is already creation-time and adapter-shaped

`notification_gates/service.py` resolves auto gates inline at creation
(`_resolve_auto_gate`, `source="auto_resolution"`) and records
`auto_resolution={enabled, argument, state}` on the bundle. Each `GateAdapter`
already carries an `auto_policy` and a `resolve_auto_selection` hook. That means:

- Epic A can change *what counts as auto* (fail-closed parse, live-read record)
  without changing *how gates execute*.
- Epic B can swap the *decision function* (explicit option IDs from a frozen
  record) behind the same `_resolve_auto_gate` call site. Adapters keep only
  selection semantics; validation moves central — exactly the policy report's
  cut.
- Epic C can add *new decision inputs* (profile layers, roles, brake) without
  touching the execution path again.

Verification seam: gate bundles under `~/.sase/interaction_requests/` plus
`~/.sase/prompt_history/` already gave both baselines their counts (7,993/11,501
prompts; 234 auto epics; 557/557 tale approve+archive). Every epic below
reuses the same bundle assertions as its acceptance test — no new harness.

### 2. The launch record is the single migration joint

Today launch writes up to three `agent_meta.json` keys (`approve`,
`auto_approve_plan_action`, `auto_approve_argument`) plus a
`SASE_AGENT_AUTO_APPROVE=1` env export, read back by layering in
`main/plan_approve_handler.py` (`is_auto_approve_active()` true if *any*
argument present). In-process successors copy only `approve`; monitor
follow-ups re-emit a `%auto` prefix; gate follow-ups drop `%auto`. This is
D5/D6 — and it is also the epic joint:

- Epic A stops trusting the env snapshot (read meta live) and carries session
  auto state structurally into follow-ups. No schema change.
- Epic B introduces the one new thing: `agent_meta.autonomy` (resolved policy +
  `profile`, `overrides`, `source`, version, digest). Legacy triad + env readers
  stay as *derived* compatibility behind a `sunset` flag (mandatory per
  `sase_flags.md` for backward-compatible branches) until old runners drain.
- Epics C/D never change the record shape incompatibly — they add profile keys
  and values the Epic B evaluator already knows how to ignore-or-ask (`unknown
  kind → ask`).

No epic needs a flag-day migration. Old runners, `%dispatch` remotes with drift,
and stored-prompt replays each have a defined answer (derived readers / shipped
resolved record / token rewrite via the same mutator).

### 3. Generated prompts are one substitution point

`bead/work_prompt.py:187,224` appends a literal `%auto` to every phase and land
worker — the source of 170 nested-epic auto-approvals. Both baselines agree the
fix is a config `roles:` substitution at that one site. Epic A can ship the
interim stopgap (emit `%auto:tale` so epic plans become `ask` once the tier
mismatch lands) in a single small change; Epic C replaces the literal with the
role lookup. One file, one test (render + assert token), no fan-out.

### 4. The Rust boundary concentrates in one epic

Today `sase-core` knows only legacy approve flags (`agent_scan` wire
`auto_approve_plan_action`, `fleet_owner_facts` auto-approved bit, directive
metadata for colon/bare/plus forms). There is no autonomy evaluator in core, so
Epic B is greenfield wire + `evaluate()` + summary/decision renderers — the one
place that pays the two-repo pin-move cost. Epics A, C (Python/TUI/Telegram),
and D (budget arithmetic reusing the Epic B decision type) need at most
additive core keys. I deliberately put prompt-completion metadata, the
`AutonomySummaryWire`, `autonomy_why()`, and `mutate_autonomy()` all in Epic B
so Epic C's many surfaces share one renderer (the UX report's "one renderer"
test: chips, strips, picker, Telegram, and explain print identical words for
the same record).

### Hoops I am explicitly avoiding

- **No per-epic core schema redesign.** If Epic C invents a second evaluator or
  a parallel Python policy, the "one record, one evaluator, one renderer"
  guarantee collapses and every surface needs re-verification. The plan forbids
  it: additive keys only after Epic B.
- **No UX-trailing epic.** The UX report warns that P2 without profile-aware
  completion keeps the 100%-bare ratio frozen. Each epic below ships its own
  surfaces (Epic B: CLI + awareness + chip rename; Epic C: picker, completion,
  announcements, Telegram). There is no "backend now, UI later" gap.
- **No cross-epic flag entanglement.** One `sunset` flag (legacy readers),
  created with `sase flag new` and tested in both states, owned by Epic B.
  Epic C's Pause brake is config/state, not a flag. Epic D needs no flag
  (config-only `allow(...)` absent by default). Grace windows get no flag until
  they are staffed.
- **No waiting-gate sweeps or undo promises.** All epics keep the verified
  creation-time-only semantics: live edits apply from the next gate; waiting
  gates stay waiting; declines never open modals. This is load-bearing for
  verifiability — otherwise every epic's acceptance test would need
  time-travel assertions.

## Recommended epics

Each epic below names its **result** (the sentence the land agent must be able
to demonstrate), its **scope**, its **acceptance checks** (the distinct,
verifiable results the prompt demands), a possible **phase shape**, and its
**size and dependencies**. Phases are advisory — the epic planner owns them —
but they show the work fits SASE phase sizing (small/medium tales plus a verify
phase, never a phase that re-verifies another epic).

### Epic A — Truth and safety: nothing is silent anymore

**Result:** every `%auto` spelling either does what it says or fails at launch;
epic workers no longer mint nested-epic auto-approvals; the `A` toggle tells
the truth.

**Scope (policy P0 + UX-0, Python-only, no core wire change):**

- Fail-closed `%auto` parsing at launch: parenthesized/named args without a
  policy object, `%auto:off`, unknown colon values, duplicates, and mixed
  `%auto:x(...)` are launch errors with did-you-mean guidance (D1/D2). Prompt
  bar shows the same error before submit (fail forward to typing time).
- Tier-mismatch rule: `:tale` on an epic plan (and `:epic` on a tale) becomes
  `ask`, not a mid-run `invalid_auto_argument` crash (D3/D4 companion).
- Live-read session auto state: gates read `agent_meta`, never the runner's
  exported env snapshot; `A` writes the same record it reads, with read-back
  confirmation (D5). Row chip renders any `%auto` argument (no more bare-only
  `⚡`).
- Structural inheritance for in-process successors, monitor follow-ups, and
  gate-turn follow-ups; coder keeps the session's auto state (D6). No
  `%auto`-string re-emission.
- Nested-epic stopgap: epic phase/land roles emit `%auto:tale` (one-site change
  in `bead/work_prompt.py`), so nested epic plans park for a human. Plus
  `/sase_questions` "mark the recommended option first" guidance (D8).
- Truth pass: `docs/macros.md` Auto-Directive + `%auto:epic` paragraphs, core
  `macros.md` directive row (via `/sase_memory_write`), help/toast copy, TUI
  glyph cleanup (`⚡` reserved for autonomy; run-log `▶`, Update-panel `↯`),
  Telegram receipt formatter + header fixes (U4/U5/U7).

**Out:** no profiles, no config surface, no `evaluate()` swap, no picker, no
brake, no delegation. Anything shaped like `autonomy:` config belongs in
Epic C.

**Acceptance (each directly runnable):**

1. Parser probe matrix: `%auto(plan=ask)`, `%a(epic=ask)`, `%auto:off`,
   `%auto:foo`, duplicate `%auto`, mixed `%auto:x(...)` all fail at launch
   with a named error; bare/`+`/`true`/`:tale`/`:epic` still launch.
2. Bundle replay: a `:tale` run auto-answers questions (documented kept
   behavior) but parks an epic plan as `ask`; a bare run still
   approves+archives tales (observed behavior, now documented).
3. Toggle test: launch bare-`%auto`, press `A`, assert the next plan/question
   gate parks; press `A` again, assert the named restore target resumes.
4. Inheritance test: planner → coder, monitor follow-up, and gate follow-up
   each preserve (or narrow) auto state without prompt-string surgery.
5. Epic-worker render test: phase/land prompt contains `%auto:tale`, and an
   actually-launched nested epic plan parks with "asked by policy" wording.
6. `just check` green; docs/memory diff reviewed (memory edit audited).

**Possible phases (4–5, all small + verify):** (1) fail-closed parse + prompt
diagnostics; (2) live-read record + inheritance; (3) worker stopgap +
question guidance; (4) docs/memory/help/glyph/Telegram-receipt truth pass;
(5) verify: bundle + toggle + inheritance matrix on a live host.

**Size/dependency:** one small epic (roughly 5–6 tales). No predecessor. Lands
first and unblocks everything by removing the silent-escalation hazard that
would otherwise poison Epic B/C testing.

### Epic B — Policy foundation: one Rust-owned policy + CLI truth

**Result:** autonomy is a frozen, inspectable, auditable session property with
one evaluator and one proof command — before any new profile power exists.

**Scope (policy P1 + UX-1 backend/CLI half, the single two-repo epic):**

- `sase-core`: `EffectiveAutonomyPolicy` + `AutonomyRequest`/`AutonomyDecision`
  wire, `%auto` argument parse + directive metadata, layering/ceiling/clamp,
  `evaluate()` mapping to **explicit option IDs** (combined selections:
  partial grant never executes), `AutonomySummaryWire` /
  `AutonomyDecisionWire` + `decision_sentence()`, `autonomy_why()`,
  `mutate_autonomy()` with expected-revision checks + tighten-only agent
  actors, `edit_prompt_autonomy()`, completion/hover/diagnostic metadata.
  Move `sase-core-revision.txt` pin with the binding.
- Python: `agent_meta.autonomy` frozen record (policy + profile + overrides +
  source + version + digest); compatibility translation (`%auto`/`%a`/`+`/
  `:plan` → `standard`; `:tale`/`:epic` → reserved profiles; `first` stays
  `first` until Epic C ships awareness); adapter cutover to central
  `evaluate()`; `sunset` flag for legacy triad/env readers +
  `auto_launch_prefix` (both-states tests, via `sase flag new`).
- Surfaces in this epic (no picker, no completion UI yet): header chip renamed
  to profile (`⚡ standard`), Context Autonomy section (effective rules +
  provenance + verbatim awareness block + session decisions), "why it asked"
  lines, decision records for *every* automatic outcome incl. questions,
  inbox `⚡ Auto` tab (announcements only: `epic` + `decline` defaults via
  existing delivery rules), completion-line autonomy sentence, Launch-Review
  child-autonomy row + Plan-Review coder-autonomy row, `sase autonomy
  explain/list/log/show` (+ `agent list`/`show`/`gate show` lines), Admin
  Center read-mostly pane (matrix + provenance + recent log), one-time
  profiles-shipped notice. Visual snapshots for each new surface per `tui.md`.
- Awareness block (5 lines) + `preauthorized` list semantics (instruction-layer,
  labeled soft); `question: recommended` flag schema (at most one
  `recommended: true` per question; fallback first; free-text/malformed stays
  manual; answers never mint launch/sudo/publish authority).

**Out:** no user-defined profiles, no `roles:` substitution (beyond the Epic A
stopgap), no `%auto:<profile>` custom names, no `deny`/`on_ask: deny`/`decide`
user surface, no `set`/`pause`, no Telegram chooser, no grace windows, no
launch delegation, no sandbox. Epic B's `standard` equals today's observed
bare behavior plus the three called-out Epic A exceptions.

**Acceptance:**

1. Core unit suite: layering, ceilings, clamping, unknown-kind→`ask`,
   combined-selection atomicity, revision-conflict refusal, tighten-only
   agent-actor refusal, dry-run `explain -p` never executing macro
   substitutions — all in `sase-core`, mirrored through the binding.
2. One-renderer test: chip, strip, Context section, `explain`, and Telegram
   formatter print identical words for the same record.
3. `sase autonomy explain <agent|prompt>` agrees with a live gate: run an
   agent, compare the explain output to the bundle's recorded
   `{profile, rule, decision, option_ids, source, revision, digest}`.
4. `sase autonomy log --since 1d` shows every auto question/decline (the
   class of outcome invisible today); inbox holds only epic/decline
   announcements (no 11-rows-a-day chore).
5. Both-states flag test: `sunset` on/off preserves behavior for old runners
   (legacy triad read) and new sessions (frozen record); stored-prompt
   retry/fork replays the visible policy.
6. `just check` green in `sase` **and** `sase-core` (wrapped `sase tool run
   check` in each); pin move reviewed; `tui.md` snapshots added/updated.

**Possible phases (4–5):** (1) core schema + parse + evaluate + wires;
(2) Python record + adapter cutover + sunset compatibility; (3) CLI
(`explain/list/log/show`) + audit/decision plumbing; (4) TUI Context section +
chips + announcements + Admin pane + snapshots; (5) verify: cross-surface
agreement + bundle-audit matrix + flag both-states.

**Size/dependency:** one full epic. Depends on Epic A (fail-closed + live-read
semantics must already hold, or Epic B's evaluator inherits silent inputs).
Pays the two-repo cost once; later epics must not reopen the wire.

### Epic C — Profiles and steering: config power on every surface

**Result:** users can name, discover, steer, and brake autonomy from wherever
they are — prompt, row, picker, CLI, or phone — and every change says what it
will do before it does it.

**Scope (policy P2 + UX-2, additive on Epic B wire):**

- `autonomy:` config: `version`, `default`, `roles:` (epic_phase/epic_land →
  `epic_worker`), `profiles:` with single-level `extends`, builtin < user <
  project layering with **project tighten-only** (mirroring Claude Code's
  ignore-project-`auto` rule), reserved `plan`/`tale`/`epic` compatibility
  names, `manual` (alias `off`), `attended`, `overnight`, `epic_worker`
  built-ins, 72-char `description:` shown *alongside* generated one-liners,
  `^[a-z][a-z0-9_]{0,15}$` id grammar; `deny`, `on_ask: deny`, `question:
  decide/recommended`, epic `max_depth`.
- Selector grammar: `%auto`, `%a:profile`, `%auto(q=ask)`,
  `%auto(overnight, epic=deny)` with canonicalized aliases (`q`→`question`,
  `e`→`epic`), one `%auto` per launch unit, launch-time ceiling checks
  (role/parent ceiling always wins; prompt may set plan/epic/question freely
  but only tighten escalation kinds; `launch=allow` from prompt refused with
  "must come from a config profile").
- Steering surfaces: profile-aware `%auto` completion/hover/diagnostics (core
  metadata → TUI + LSP + nvim; bare `%auto` menu lists profiles with
  consequence one-liners), live prompt-bar chip (`⚡ standard` / `manual` /
  red fail-closed error; `mixed (2)` for `%{a|b}` branches; `from #macro`
  provenance), `alt+a` draft picker, `,a` matrix picker (Manual first, digits
  apply, `e` explain, `p` pause, coverage line, role/compat rows only when
  current), undoable `A` (profile ↔ Manual whole-session, marks-aware,
  no-sweep toast), `sase autonomy set` (takes `%auto` grammar; agent-actor
  widening refused; dry-run flag), command-palette entries, colored `⚡` by
  computed class (autopilot cyan / attended green / unattended amber / paused
  dim; Manual no bolt) with words-not-color redundancy.
- **Pause autonomy** on all surfaces (TUI chip `⏸`, `sase autonomy
  pause/resume` with `-t/--ttl` + `-r/--reason`, Telegram `/auto pause [1h]`,
  picker `p`): every allow → `ask`, `on_ask` forced to `park`, explicit `deny`
  stays denial, no auto-resolve on resume, host-wide, fail-closed brake store
  (unreadable = paused + warning — the deliberate inversion of `%hold`
  fail-open).
- Telegram: agent-card autonomy line + `⚡ <profile> ▾` in-place chooser,
  epic alert (`Plan` / `Manual` / `Pause all`, rings), `/auto` (list / card /
  set / pause / resume), question auto-answer quiet card with fork-correct,
  revision-bound `pending_actions` callbacks (64-byte `callback_data`
  discipline, stale-revision refresh, idempotent taps, no sticky chat mode).
- Mobile gateway projections (`autonomy {profile, class, badge}`),
  announcements as ordinary notifications; `default_config.yml` keymap updates
  for `,a`/`alt+a` (leader `a` verified free; `P` and `Shift+A` rejected —
  already bound).

**Out:** no launch delegation values (Epic D), no grace windows/`glance`, no
in-picker override editor / save-as-profile, no per-decision Telegram receipts
by default, no sandbox/tools section beyond a reserved empty key.

**Acceptance:**

1. Profile × gate matrix test: for `standard`/`attended`/`overnight`/
   `epic_worker`/custom × plan/epic/question/launch/sudo/custom, assert the
   effective consequence sentence (e.g. "Epics: declined — split into tales")
   and the live behavior on a scratch host.
2. Discovery test: bare `%auto` completion lists profiles with generated
   one-liners; hover shows matrix + source layer + coverage line; invalid
   token blocks submit with the launch error sentence.
3. Steering test: `,a` pick, `A` toggle, `sase autonomy set`, and Telegram
   chooser all converge on the same record (read-back revision check); stale
   revision refused without lost update; batch `A` on marked agents reports
   per-target results.
4. Brake test: pause → every gate parks (incl. `overnight` sessions that would
   otherwise decline); resume → parked gates stay parked; unreadable brake
   store parks with warning.
5. Role test: phase/land workers inherit `epic_worker` (`epic: ask`) by
   default; project layer can only tighten (attempted widening ignored with
   visible `●` provenance); `%dispatch` remote keeps the shipped resolved
   record despite config drift.
6. Snapshots + `just check` green; Telegram callback round-trip on a real bot
   host (tap → applied → card re-render; duplicate tap idempotent).

**Possible phases (4 + verify):** (1) config + layering + roles + grammar;
(2) completion/chip/picker/`A`/`set`; (3) Pause brake + announcements +
Admin-pane brake status + palette; (4) Telegram chooser + `/auto` + epic
alerts + mobile projections; (5) verify: matrix + steering-convergence +
brake + screenshots on a live host.

**Size/dependency:** one full epic, the largest user-visible one. Depends on
Epic B (wire, evaluator, revision discipline, one renderer). Additive core
keys only; if a phase needs new wire, that is scope creep — cut the phase,
not the boundary.

### Epic D (deferred) — Bounded delegation: launch authority with a budget

**Result (when staffed):** allowlisted agents may auto-approve launches inside
an explicit, visible, exhaustible budget — and prove they stayed inside it.

**Scope (policy P3 + UX-3, config-only, never prompt-typed):**
`launch: allow(max_children, max_depth, max_model, scope, child_profile)` with
cumulative atomically-reserved budget, retry identity + refund on failed
dispatch, fan-out accounting, `min(requested, requester)` attenuation +
`child_profile` ceiling, **Arm this autonomy?** confirmation for
config-granted delegation, child-policy line in every launch preview
(TUI + Telegram `Approve · manual`), remaining-budget display.

**Acceptance (deferred with the epic):** budget-exhaustion test (N+1th launch
parks), failed-dispatch refund test, depth-attenuation test (grandchild
clamped), human-approved-launch-keeps-policy test with preview screenshot,
`launch_request_planning.py:37` hard-coded `approval: "required"` now
`"policy"`-aware without regressing the 49-launch baseline.

**Staffing rule:** do not plan or staff until Epics A–C have been used for at
least one release cycle. Rationale: lowest demand in the data, highest safety
cost, and every line of its design (budgets, attenuation, preview) composes
with — rather than reworks — the Epic B decision type.

## Explicitly not epics (tales or deferred decisions)

- **Grace windows (`approve after 30m`, `glance` profile).** Designed in both
  baselines, deferred for cause: unproven demand (106 auto : 1 human in early
  October reads as "don't want to review" at least as much as "would review
  with more time"), plus a real turn-model cost (windowed gates end the
  creator's turn and lose in-process question context). Data-gate: staff only
  if Epic C logs show epic-alert taps within minutes or users ask for plans
  they now auto-approve. Small-to-medium tale(s) inside a later epic, not a
  standalone epic.
- **Standing approvals / `review(@model)`.** A medium friction-reducer epic at
  most, placed *after* deterministic rules (Codex/Claude-auto precedent), reusing
  `%hold` TTL/cap vocabulary. Not part of the configurable-`%auto` ask.
- **Hard tool/sandbox permissions (policy P5).** A separate project on the same
  profile object (`sandbox:`/`tools:` section compiled to Claude/Codex/OpenCode
  natives or a broker layer), only after per-provider verification that deny
  rules are honored *under the bypass flags SASE passes*. Shipping a `%caps`
  dial with no enforcement is the theater both baselines reject. Never an
  `%auto` epic's tail phase.
- **`--auto` launch flag, numeric levels/sliders, per-profile hues, toast per
  decision, autonomy deck, in-TUI policy editor, waiting-gate sweep, approval
  undo, Telegram wizard, `sudo`/`custom` auto-allow, padlock badges.** Each is
  rejected in the baselines with a named reason; listing them here so no epic
  planner re-adds them as "small extras."

## Landing order, flags, and the no-hoop contract

1. **A → B → C, strictly.** A removes silent inputs B would otherwise enshrine;
   B installs the evaluator C's surfaces share. C without B rebuilds the bug
   (a second evaluator). D waits a release.
2. **One flag total:** Epic B's `sunset` for legacy readers (via
   `sase flag new`, both-states tests, removal by deleting the Off branch and
   closing the bead). No beta flag for profiles — profiles are config fields
   users choose forever, not temporary routes (per `sase_flags.md` kinds).
3. **Zero-behavior-change discipline:** Epic A changelog calls out exactly three
   intended changes (fail-closed malformed forms; tier-mismatch → `ask`;
   worker stopgap). Epic B changelog calls out `first`→`recommended` only after
   awareness + `/sase_questions` guidance ship. Everything else reproduces
   observed behavior under new names.
4. **Each epic moves `sase-core-revision.txt` at most once** (Epic B: the move;
   Epic C: only if additive keys need it; Epic A: never). Each epic runs its
   own wrapped verification (`sase tool run check` in touched repos; never raw
   `just check-full` unless CI names it, per `lint_and_test.md`).
5. **Epic planners copy (do not re-derive) the acceptance lists above** into
   phase beads, and the land agent demonstrates each numbered item live. A
   checklist that re-runs another epic's matrix is a smell: the earlier epic
   regressed or the seam leaked.

## Alternatives considered and rejected

| Alternative | Why rejected |
|---|---|
| One epic for everything | No verifiable midpoint; fuses the two-repo Rust landing with TUI/Telegram polish; failure anywhere blocks the safety fixes users need first. |
| Six micro-epics (one per P-phase / UX-phase) | Multiplies pin moves, flag states, and cross-epic contract negotiation beyond the value of smaller demos; P0 tales are individually shippable but share one verdict. |
| Backend epics first, one UX epic last | Repeats the known failure the UX baseline documents: profiles without completion/picker/announcements keep the 100%-bare ratio and leave automation invisible until the end. |
| Profiles-in-prompt DSL epic (no config) | Rejected on trust grounds both baselines share: 73% of auto epics came from generated prompts, so prompt-typed grants let agents mint authority the user never gave. |
| Delegation or sandbox first | Lowest demand (launch) or no enforcement (sandbox under bypass flags); either would gate the highest-value visibility work behind the hardest safety work. |

## Open decisions carried forward (no new position)

The baselines leave these to you; the split is neutral on each, but each needs
an answer before its epic plans:

- Nested-epic default: `epic: ask` vs `approve(max_depth=1)` (policy open
  decision 1; I use `ask` in Epic A and the budget in Epic C, matching the
  policy recommendation).
- Bare `%auto` on top-level epics and tale auto-archive: keep observed behavior
  in `standard` (policy decisions 2–3); revisit from Epic B audit data.
- Absence of `%auto` stays Manual (policy decision 4) — load-bearing for
  generated launches; use `#auto` macro or prompt defaults, never implicit
  config.
- Announcement default `[epic, decline]` vs `[epic]`; brake scope host-wide;
  `A` restores last profile; keep the name `overnight` (UX open decisions 1–4).

## What would change this recommendation

- If tool-level (shell/network/write) risk dominates gate-level friction in
  real incidents, pull the sandbox project forward — but keep it a separate
  project on the same profile object, never Epic C scope creep.
- If after one release only `standard` + one profile see use, collapse Epic C's
  picker to Manual + those two (both baselines agree) while keeping records,
  announcements, explain, and the brake.
- If Telegram `/auto` goes unused, keep the epic alert + completion line and
  drop the chooser. If epic-alert buttons are tapped within minutes, that is
  the demand signal for grace windows.
- If Epic B's wire review shows the evaluator cannot stay additive for Epic C
  keys, split Epic B instead of letting Epic C fork a second evaluator — the
  one-evaluator rule outranks the three-epic count.

## Sources

- **Accepted inputs (read via audited `sase artifact read`):**
  `research:202610/auto_directive_autonomy_policy/auto_directive_autonomy_policy.md`
  (2026-10-07 consolidated, sase `142636c528`) and
  `research:202610/auto_autonomy_profiles_ux/auto_autonomy_profiles_ux.md`
  (2026-10-08 consolidated, sase `7d50dc29c1`, sase-telegram `70701a0`).
- **Lead verification this session:** `src/sase/macro/_directive_values.py`
  (`%auto` opaque arg); `src/sase/main/plan_approve_handler.py`
  (`is_auto_approve_active`, layered env+meta reads);
  `src/sase/notification_gates/service.py` (creation-time `_resolve_auto_gate`,
  `source="auto_resolution"`, bundle `auto_resolution` record);
  `src/sase/bead/work_prompt.py:187,224` (literal `%auto` for phase/land
  workers); `src/sase/llm_provider/*.py` (bypass flags) via the policy
  report's layer table; `sase-core` (`agent_scan` wire, `fleet_owner_facts`
  auto-approved bit, directive metadata — no autonomy evaluator yet, confirming
  Epic B is greenfield); `docs/rust_backend.md` (pin-move procedure).
- **Memory (via `sase memory read`):** `lint_and_test.md` (verify via
  `sase tool run check`, `check-full` explicit-only, known-long commands),
  `cli_rules.md` (`sase autonomy` alphabetical subcommands, short aliases,
  bare-delegates-to-`list`), `sase_beads.md` (phase description prefixes,
  non-cascading close, land-agent ownership, `PROPOSED FOLLOW-UP` discipline),
  `sase_flags.md` (`sunset` for legacy readers via `sase flag new`,
  both-states tests, Off-branch deletion on removal).
- **Prior research reused:** `research:202609/sase_11e_nested_landing_loop.md`
  (nesting-loop evidence behind the Epic A stopgap and Epic C roles).
- **Not consulted:** any peer report from this swarm (`__cdx`, `__cld`,
  `__grk`, `__gem` for the epic-split question), per the swarm protocol.
