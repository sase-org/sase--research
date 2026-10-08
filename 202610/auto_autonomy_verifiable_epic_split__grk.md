# Split `%auto` At The Soak Boundaries

> **Research query:** Given that the recommendations in
> `auto_directive_autonomy_policy.md` and `auto_autonomy_profiles_ux.md` are accepted,
> what is the best way to split making `%auto` more configurable, intuitive, and
> powerful into multiple epics, if each epic can have distinct, verifiable results
> without too many hoops? If a split is unnecessary, say so.

![Infographic: split %auto at the soak boundaries. P0 safety tales ship this week, then Epic A (visible autonomy: see, explain, stop), a 2–4 week log soak, Epic B (configurable autonomy: choose a policy), and a data-gated Epic C for bounded launch delegation. Yardstick commands are extract_prompt_directives, sase autonomy explain, and sase autonomy explain -p '%auto:overnight'. Policy and UX stay in the same epic.](auto_autonomy_verifiable_epic_split_infographic__grk.jpg)

## Bottom line

**Split this work. Two committed epics, a handful of safety tales that ship first, and
one optional later epic.** Draw the cuts where you need to watch real runs before the
next behavior change. Do not wrap the whole redesign in one epic, and do not invent a
legend that pre-commits the deferred layers.

| # | Slice | Form | Distinct result you can check | You can stop here because |
| ---: | --- | --- | --- | --- |
| **P0** | [Safety and truth](#p0-safety-tales-not-an-epic) | 4 tales (2 already filed) | Fail-closed parse; docs match observed gates; epic workers park nested epics; `/sase_questions` names the recommended option | Nested-epic fan-out is stopped and `%auto(epic=ask)` no longer grants full automation |
| **A** | [Visible autonomy](#epic-a-visible-autonomy) | Epic, 4 phases | `sase autonomy explain` matches live gate `evaluate()`; every auto outcome is in `autonomy log`; `A` and Pause change the next gate; epic launches announce | Bare `%auto` is honest, inspectable, and stoppable. 100% of current usage is this spelling |
| **B** | [Configurable autonomy](#epic-b-configurable-autonomy) | Epic, 4 phases, after an A soak | `%auto:overnight` and `%auto(q=ask)` parse; the picker and `%` completion list real profiles; epic workers read `autonomy.roles` | Users can choose a policy. If logs show only `standard` plus one other profile, collapse the catalog and keep A |
| **C** | [Delegated autonomy](#epic-c-delegated-autonomy-optional) | Epic, later, only if A+B logs demand it | Config-only `launch: allow(...)` with a reserved budget; launch preview shows the child policy | Optional. Skip it until someone actually needs auto-approved launches |

The accepted policy paper already named P0–P5. The accepted UX paper already mapped
UX-0–UX-4 onto those phases and said to ship UX with its policy phase. This report
keeps that pairing and **moves the cuts** so that each landed slice is a product a
human can use, a land agent can verify with a short command list, and a later epic can
refuse to start until logs justify it.

## Scope and method

Independent research, 2026-10-08, researcher `grk`. I treated both accepted papers as
binding on *what* to build, and asked a different question: *how to cut the work so
each cut is verifiable without a compatibility maze.*

I read, via `sase artifact read`:

- `research:202610/auto_directive_autonomy_policy/auto_directive_autonomy_policy.md`
- `research:202610/auto_autonomy_profiles_ux/auto_autonomy_profiles_ux.md`

I used `research:202610/memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md`
only as a *methodology analog* (how this repo has split a multi-epic program). I did
not use any peer report from this swarm.

I re-checked the live tree at sase `7e75bbcd8d` and sase-core `cd73d968`:

- Parser probe: `%auto(plan=ask, questions=ask)`, `%a(epic=ask)`, and
  `%auto(sudo=approve)` still extract as `auto_enabled=True, mode='plan', argument=None`
  (D1). `%auto:off` still enables auto with argument `off` (D2).
- `src/sase/bead/work_prompt.py:187,226` still appends a literal `%auto` to every epic
  phase and land worker. `tests/test_bead/test_work_epic_plan.py` still asserts
  `%auto:tale` is absent (D7).
- `is_auto_approve_active()` still ORs `SASE_AGENT_AUTO_APPROVE`
  (`src/sase/main/plan_approve_handler.py:633-645`). The runner still exports that env
  var at launch (`src/sase/axe/run_agent_runner_launch.py:308-309`) (D5).
- In-process follow-ups copy `approve` and skip `auto_approve_plan_action`
  (`src/sase/axe/run_agent_helpers_artifacts.py:161-186`) (D6).
- Epic-plan auto still accepts only `{None, "", "epic", "epic_plan"}` and raises
  `invalid_auto_argument` on `%auto:tale` (`src/sase/notification_gates/adapter.py:70-80`).
  A D7 stopgap that emits `%auto:tale` without a mismatch→`ask` change would *error*
  nested epic gates rather than park them.
- Beads `sase-1hg` (D1/D2, medium bug, READY) and `sase-1hh` (D3/D4 memory+docs, small,
  READY) already exist, related to each other.
- Nested epic `sase-19i.7.3.3.3.3.3` is in progress, seven epic levels deep, created
  2026-09-27. D7 is not historical.
- Plan Decisions (`sase-1hi`) just ran as a 9-phase core+CLI+TUI+Telegram epic and
  immediately grew a landing-repair child (`sase-1hi.10`). `bead.big_epic_phase_threshold`
  is 5 (`src/sase/default_config.yml`).
- Feature-flag rule: a `beta` flag is epic scaffolding and must be removed before that
  epic lands (`sase/memory/sase_flags.md`). An epic launch assigns every phase and the
  land agent at once, so an epic cannot sit in production for a month to watch logs.

## Why a split is the right shape

The accepted papers already say P0 is independent tales and P1/P2/P3 are epics. The
reason to keep that shape, and to refuse both "one mega-epic" and "an epic per
surface", is mechanical to this repo:

1. **Soak points are epic boundaries.** The UX paper's own revisit rule is "if a month
   of UX-1 logs shows only `standard` plus one other profile, collapse the picker."
   Watching production from inside one epic is impossible: every phase is assigned at
   launch, and a `beta` flag cannot outlive its epic. The month of logs has to happen
   *between* epics.
2. **Each slice has to remain a complete product if the next slice never ships.** Bare
   `%auto` is 100% of September and October uses (UX paper). Epic A upgrades that
   habit. Epic B adds the spellings nobody has typed yet. Epic C is a new capability
   with a different risk class (auto-approving launches).
3. **Policy and UX for the same slice stay together.** The UX paper's "one renderer"
   test (chip, strip, picker, Telegram, and `explain` print identical words from one
   Rust summary) fails if you land a policy epic and a trailing UX epic. Plan Decisions
   already proved the paired shape: core grammar in phase 1, CLI/TUI/Telegram in later
   phases of the *same* epic, pin ratchet in the core phase.
4. **Size is a hint, soak is the cut.** The instruction-migration analog measured
   median time-to-close at 3.3 h for 1–4 phase epics and 19 h for 9+. Plan Decisions
   was 9 phases and needed a repair child. Aim each autonomy epic at 4 phases, under
   the big-epic lander threshold of 5.

A single epic covering P0+P1+P2+UX-0+UX-1+UX-2 would be Plan-Decisions-sized or
larger, would hide the soak, and would force either an illegal lingering `beta` flag or
shipping profiles before anyone has seen the named chip. That is the hoop the user
asked to avoid.

## Mapping the accepted papers onto the cuts

| Paper phase | Lands in | Why this cut |
| --- | --- | --- |
| P0 D1/D2 fail-closed parse | P0 tale (`sase-1hg`) | Safety bug, already filed, blocks nothing in A except that A inherits a parser that rejects parens |
| P0 D3/D4 docs + `macros.md` row | P0 tale (`sase-1hh`) | Memory/docs; every agent loads the stale row today |
| P0 D7 nested-epic stopgap + tier mismatch → `ask` | P0 tale (new, medium, urgent) | Live seven-deep nest; must include the mismatch change or `%auto:tale` errors on epic gates |
| P0 D8 `/sase_questions` guidance | P0 tale (small) | Instruction-only; cheap |
| P0 D5 live-read, D6 inheritance | **Epic A runtime** | Doing these as P0 tales *and* again as `agent_meta.autonomy` is the hoop to skip |
| UX-0 truthful `A`, fail-closed prompt-bar errors, glyph cleanup | Epic A inspect / P0 where it is docs-only | `A` becomes truthful only once the live record exists |
| UX-0 Telegram receipt formatter | P0 small tale in `sase-telegram`, or A's surfaces phase | Independent of the policy object |
| P1 policy object, explicit option IDs, awareness, audit | Epic A | The engine. Zero intended behavior change besides P0 |
| UX-1 chip, Context section, `explain`/`log`, decision records, "why it asked", completion line | Epic A | Visibility for the engine. This is how A is verified |
| Pause autonomy + epic/decline announcements + Telegram Manual/Pause buttons | Epic A | The UX paper's third of "four things". Announcements without a brake are a dead control. Pause does not depend on named profiles |
| P2 profiles, overrides, roles, `deny` / `on_ask: deny`, `question: recommended` | Epic B | New user-facing grammar. Needs A's `evaluate()` and record |
| UX-2 completion, `,a` picker, `sase autonomy set`, Telegram `/auto` and chooser | Epic B | Discovery for profiles. The 100%-bare ratio will not move without this |
| P3 / UX-3 bounded launch delegation | Epic C, data-gated | Different risk class; config-only `launch: allow` |
| P4 standing approvals, `review(@model)` | Task beads after B, if logs show friction | Medium; not an epic until the need is measured |
| P5 hard sandbox/tools | Separate decision, as the policy paper said | Coverage line stays honest until then |
| UX-4 grace windows, override editor, save-as-profile | After a month of B, if epic-alert buttons are used | The UX paper already deferred these |

## P0 — Safety tales (not an epic)

Do not wrap these in an epic. An epic plan would delay D7 while
`sase-19i.7.3.3.3.3.3` and its siblings keep nesting. Each tale is independently
shippable and independently testable. Two of them are already READY.

### Tales

| Tale | Existing bead | Verify |
| --- | --- | --- |
| Fail-closed `%auto(...)` and `%auto:off` at launch, in Python, the Rust typed extractor, editor metadata, and the macro LSP | `sase-1hg` (medium bug) | `extract_prompt_directives('%auto(plan=ask, questions=ask)\nx')` raises `DirectiveError`. Same for `%a(epic=ask)` and `%auto:off`. Prompt-bar shows the error |
| Rewrite the core `macros.md` `%auto` row and `docs/macros.md` Auto Directive to describe observed behavior: bare archives tales, launches epics, answers questions; `:tale`/`:epic` still answer questions | `sase-1hh` (small memory) | `sase memory show macros.md` no longer says auto-approve is plan-only and non-committing |
| Epic phase and land workers emit `%auto:tale`; plan and epic adapters treat a tier mismatch as `ask` rather than `invalid_auto_argument` | **New medium tale.** The mismatch change is required; without it D7 turns nested epics into mid-run errors | `sase bead work <epic> --dry-run` shows `%auto:tale` on every phase and land segment. A fixture epic-plan gate with argument `tale` parks. `tests/test_bead/test_work_epic_plan.py` flips its assertion. Changelog names the nested-epic behavior change |
| `/sase_questions` tells authors to mark the recommended option first (and, once A lands, to set `recommended: true`) | New small tale, or a phase of A if you want it next to the awareness block | Skill text + a unit test on the bundled skill source |

Optional fifth tale: sase-telegram quiet-receipt formatter (UX paper U4/U5). It does
not need the policy object.

### What P0 deliberately leaves to Epic A

D5 (stop trusting the env snapshot) and D6 (one inheritance path) look like small
fixes. They are also the first two mutations of the source of truth that Epic A
replaces with `agent_meta.autonomy`. Doing them now as triad-copying patches, then
rewriting them in A, is the hoop this split is designed to skip. Ship D7 this week;
let A own the record.

### Two-step grammar, accepted

P0's D1 rejects parenthesized forms. Epic B later accepts `%auto(overnight, q=ask)`
with real semantics. That is a documented fail-closed interval, not a compatibility
layer. The D1 error should say the parenthesized form is unsupported (and, once B is
planned, that profile overrides land there). Users who type `%auto(epic=ask)` between
P0 and B get a launch error instead of silent full automation. That is already a
product improvement.

D7's `%auto:tale` is the *destination semantic* of the `epic_worker` role
(`epic: ask`, tales still auto). Epic B only moves the source of that mapping from a
literal in `work_prompt.py` to `autonomy.roles`. Behavior stays. The stopgap is not
throwaway.

## Epic A — Visible autonomy

**Goal.** Make today's `%auto` a named, inspectable, stoppable session property,
without adding profile syntax.

**Accepted content.** Policy P1 + UX-1 + Pause autonomy + epic/decline announcements.
Compatibility translation of existing spellings (`%auto` / `%a` / `%auto+` /
`%auto:plan` → `standard`; `:tale` / `:epic` → reserved profiles). Awareness block.
`question: recommended` flag on the schema, with `first` still the compatibility
fallback until B's `/sase_questions` guidance has been live. One `sunset` flag for
`SASE_AGENT_AUTO_*` env readers and the meta triad, tested in both states, removed
later by FlagTriage after old runners drain.

**Why this is a complete product.** After A, a human can answer "what will this agent
do without me, what did it already do, and how do I stop the next gate?" for every
session that uses the spelling they already type. The UX paper's first three of four
things live here. The fourth (profile-aware completion and the picker) is B, because
it is how *new* profiles get discovered.

**Why Pause belongs in A, even though the UX paper listed it under UX-2.** Pause does
not depend on named profiles. It depends on `evaluate()` honoring a host-wide brake
and on `mutate_autonomy`. Epic-launch announcements without Manual/Pause buttons are
a control that cannot act. Pause is also the only control that covers agents that do
not exist yet (an epic already fanning out). That value is available the moment the
record exists.

### Recommended phases

DAG: `core` → `runtime` → (`inspect` ∥ `brake`). Four phases, three waves, under the
big-epic threshold.

| id | Title | depends_on | size | Owns |
| --- | --- | --- | --- | --- |
| `core` | sase-core autonomy schema, `evaluate()`, summary/decision/why wires, revisioned `mutate_autonomy`, fail-closed parse of *today's* spellings | [] | large | Linked `sase-core`. Pin moves in this phase. Golden tests: same record → identical summary words |
| `runtime` | Persist `agent_meta.autonomy`; gates call `evaluate()` with explicit option IDs; one inheritance path; awareness block; env/triad behind the sunset flag | [core] | large | Python glue, gate adapters, follow-ups, runner. D5 and D6 die here |
| `inspect` | `sase autonomy explain\|list\|log\|show`; `agent list`/`show` and `gate show` lines; named chip; Context Autonomy section; coverage line | [runtime] | medium | CLI per `cli_rules.md` (bare group → `list`, alpha subcommands, short aliases). TUI snapshots for the chip and the Context section |
| `brake` | Pause autonomy (host-wide, optional TTL, fail-closed store); epic and decline announcements on TUI + Telegram with Manual/Pause; completion-line; decision records for every automatic outcome including questions | [runtime] | large | TUI, Telegram, notification tabs. `sase autonomy pause`/`resume` join the CLI group here |

`inspect` and `brake` can run in parallel after `runtime`. Telegram work is a phase of
this epic, the way Plan Decisions phase 7 was, not its own epic.

### Land-agent yardstick

A land agent confirms A with these, plus `just check` in sase and sase-core:

```text
sase autonomy explain <auto-agent>          # matches the fixture gate's recorded digest
sase autonomy log --since 1h                # one row per auto tale, epic, and question
sase autonomy pause -t 5m && …              # next plan gate parks; resume does not auto-resolve it
sase agent list                             # AUTO column from the core badge, not ⚡T/⚡E
```

TUI: snapshot of an `%auto` row showing `⚡ standard`, the Context Autonomy section
with the coverage line, and a paused row with the dim class. `A` off then
`sase autonomy explain` reads Manual. A follow-up coder in the same session keeps the
record (D6). Coverage line present on picker-less inspect views; shipping a chip
without it is a bug.

Zero intended behavior change for bare `%auto` besides P0. Changelog names the sunset
flag and Pause as the new capability.

### Repos

- `sase-core` (phase `core`, pin ratchet)
- `sase` (runtime, inspect, brake)
- `sase-telegram` (announcement buttons, receipt formatter if it did not ship in P0)

## Epic B — Configurable autonomy

**Goal.** Let a human choose a policy, from the prompt, the TUI, the CLI, and
Telegram, using the record Epic A already shows.

**Accepted content.** Policy P2 + UX-2, minus Pause (already in A). Named `autonomy:`
profiles with builtin < user < project layering and project tighten-only; `%auto:<profile>`
and `%auto(<profile>, plan\|epic\|q=…)`; role defaults replacing the D7 literal;
`deny` and `on_ask: deny`; `question: decide` / `recommended`; `,a` picker; profile-aware
completion, hover, diagnostics; prompt-bar chip; `sase autonomy set` (tighten-only from
inside an agent); Telegram `▾` chooser and `/auto`; Admin Center pane; one-time notice.
`epic: approve(max_depth=N)` can land here or wait for C; I would wait unless A logs
show depth-budget demand, because D7 already parked nested epics.

**Why this waits for an A soak.** B is the first slice that changes what a *human*
can type. A's `autonomy log` is the yardstick that tells you whether anyone needs
`overnight`, `attended`, or a custom profile. If two to four weeks of A show only
`standard` plus the `epic_worker` role, B still ships — roles, fail-closed overrides,
and completion are how the catalog stays small on purpose — but the plan should allow
collapsing to Manual / `standard` / `epic_worker` / one attended-or-away profile.

**Why B is still a complete product if C never happens.** Users can select `overnight`
before walking away, `attended` when they want questions, and a project can tighten
`standard`. Launch, sudo, and custom stay `ask`. That is the v1 the policy paper
recommended.

### Recommended phases

DAG: `profiles` → (`steer` ∥ `telegram` ∥ `roles`).

| id | Title | depends_on | size | Owns |
| --- | --- | --- | --- | --- |
| `profiles` | `autonomy:` config, layering, ceilings, new grammar, reserved `plan`/`tale`/`epic` names, `evaluate()` against overrides | [] | large | sase-core + Python config load. Pin moves again. Launch errors for unknown profile/key/value, extra positionals, mixed `%auto:x(...)`, and privileged `allow` |
| `steer` | `%` completion and hover; `,a` matrix picker; undoable truthful `A`; prompt chip / `alt+a`; `sase autonomy set`; Admin Center pane | [profiles] | large | TUI snapshots, LSP/editor metadata in core (nvim consumes it) |
| `telegram` | `/auto`, card chooser, revision-bound callbacks | [profiles] | medium | sase-telegram. Epic-alert buttons already exist from A; this phase adds profile choice |
| `roles` | `bead/work_prompt.py` emits the configured role profile; docs; one-time notice; `question: recommended` translation once awareness+skill guidance are live | [profiles] | medium | Replaces the D7 `%auto:tale` literal. Tests that used to pin `%auto:tale` now pin the role's canonical directive |

### Land-agent yardstick

```text
sase autonomy explain -p '%auto:overnight'
sase autonomy explain -p '%auto(attended, epic=deny)'
sase autonomy show overnight
sase autonomy set 'overnight' <agent> --dry-run
```

Expect: overnight epics wait, questions decide, `on_ask: deny`; the attended+deny
override is visible as an override chip; a project config that widens a user profile
is rejected; `sase bead work <epic> --dry-run` no longer contains a hardcoded
`%auto` / `%auto:tale` — it contains the role profile. Completion on `%auto:` lists
configured profile names first. Picker snapshot shows Manual, `standard`, `attended`,
`overnight`, with the coverage line. An agent-authored follow-up `%auto:overnight`
when the parent is `standard` is refused (widen from inside an agent).

### Soak after B, before C

The UX paper's collapse rule and grace-window demand signal both live here. Watch:

- profile mix in `sase autonomy log` (is anyone using more than `standard` + one other?)
- whether Telegram `/auto` and alert buttons are used
- whether epic-alert buttons are tapped within minutes (grace-window demand)

Those measurements are *not* Epic B's exit criteria. B lands when the yardstick
above is green. The measurements decide whether to file C, UX-4, or a catalog-collapse
tale.

## Epic C — Delegated autonomy (optional)

**Do not plan this until A and B have logs.** Bounded `launch: allow(...)` with a
cumulative, atomically reserved budget, retry identity, refund on failed dispatch,
attenuation (`min(requested, requester)` plus `child_profile` ceiling), and the
"Arm this autonomy?" confirmation plus remaining-budget display. This is P3 + UX-3.

It is a real epic when it happens: new risk class, new confirmation, new accounting.
It is a bad legend child, because a legend would launch its planner now.

P4 (standing approvals, `review(@model)`) and P5 (hard permissions) stay off this
program. P5 is a separate decision on the same profile object; the coverage line
gains an `enforced: shell` clause in that change and never earlier.

## What not to split, and what not to combine

| Cut | Verdict |
| --- | --- |
| One epic for everything the papers recommend | Too big, no soak, illegal lingering beta, Plan-Decisions-plus |
| Policy epic, then a UX epic | Breaks the one-renderer contract; A would land an engine nobody can see |
| One epic per surface (TUI / CLI / Telegram / nvim) | Same words would drift; Plan Decisions already showed the paired-surface phase pattern |
| P0 as an epic | Delays D7; the tales do not share a land-agent story |
| D5/D6 as P0 tales *and* Epic A | Two source-of-truth migrations |
| Pause as its own epic between A and B | Extra hoop; Pause is how A's announcements act |
| A legend of A+B+C | Commits to C before the data exists |
| P5 in this program | Different decision; bypass flags still lie if you badge "restricted" |
| `sase-1i1` (memory consent under `%auto`) | Adjacent Plan Decisions fallout. Leave it as its own feature bead |
| Grace windows, override editor, save-as-profile | UX-4, data-gated after B |
| `--auto` launch flag, numeric levels, per-decision toasts, autonomy deck | Accepted "what not to build" |

## Flags, core pin, and hoops that stay small

- **One `sunset` flag** in Epic A for env-var and triad readers. Default on. Both-states
  tests. Removal is FlagTriage after old runners drain, not an epic.
- **No `beta` flag for profiles.** New syntax is opt-in by typing it. Absence of `%auto`
  stays Manual, which generated launches rely on.
- **Two pin ratchets**, one per committed epic, each in that epic's first core-touching
  phase. Host-owned dual-repo commit already writes `sase-core-revision.txt` when both
  repos are in the declaration (`docs/rust_backend.md`). That is the same hoop Plan
  Decisions paid, once per epic, which is acceptable.
- **Telegram and nvim stay phases**, opened with `sase repo open`, not sibling epics.
- **Memory edits** (`macros.md`, `/sase_questions`, `cli_rules` consumers) are named in
  the approved plan and go through `/sase_memory_write`. P0's `sase-1hh` is the first.

The remaining two-step (D1 rejects parens → B accepts them; D7 emits `%auto:tale` → B
reads `autonomy.roles`) is the cost of shipping safety before syntax. It does not
require a flag matrix.

## Sequence

```text
now     sase-1hg, sase-1hh, D7+mismatch tale, D8 tale
        (D7 is the urgent one; nested epic sase-19i.7.3.3.3.3.3 is live)

then    plan + approve Epic A
        land A, soak 2–4 weeks of `sase autonomy log`
        (nested-epic rate, announcement noise, pause usage, explain usage)

then    plan Epic B against that log
        land B, soak for profile mix and Telegram /auto

maybe   Epic C if launch-approval demand is real
        UX-4 tales if epic-alert buttons are used
        catalog-collapse tale if only one extra profile is in use
```

P0 tales can overlap Epic A *planning*. They should land before A's `runtime` phase
so A does not have to carry D1/D7 as well.

## Open decisions

I recommend the first option in each row.

1. **Pause in Epic A, or wait for B?** A. Announcements need a brake; Pause does not
   need profiles.
2. **D7 tale includes mismatch→`ask`, or wait for A's `evaluate()`?** Include it. A
   `%auto:tale` epic gate today is `invalid_auto_argument`, which is worse than parking.
3. **How long is the A soak?** Two to four weeks, or 200 auto-resolutions, whichever
   comes first. The UX paper's "a month" is the upper bound, not a gate you invent
   inside A.
4. **Legend?** No. File A, then B as a dependent epic, then C only if logs say so.
5. **`approve(max_depth=N)` in B, or C?** C, unless A's log shows repeated parked
   nested epics that you then want to allow one level of.

## What would change this recommendation

- **If D7 cannot ship as a tale this week** (for example if mismatch→`ask` turns out
  to touch the whole auto-selection path), fold D7 into Epic A's `runtime` phase and
  still keep A and B apart. Do not delay fail-closed parse (`sase-1hg`) for that.
- **If you will not look at logs between A and B**, the soak argument weakens and a
  single 8-phase epic (A+B, still no P3) becomes viable. I would still split: Plan
  Decisions at 9 phases grew a repair child, and B's grammar is the risky half.
- **If Pause feels too large for A's fourth phase**, split `brake` into a 3-phase
  mini-epic that depends on A and still precedes B. That is the only extra epic I
  would consider, and only if A's plan review says `brake` will blow the threshold.

## Sources

**Accepted baselines (artifact reads):**

- `research:202610/auto_directive_autonomy_policy/auto_directive_autonomy_policy.md`
- `research:202610/auto_autonomy_profiles_ux/auto_autonomy_profiles_ux.md`

**Methodology analog (unrelated prior research):**

- `research:202610/memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md`
  (soak = epic boundary; beta flags die with their epic; yardstick commands; fold
  existing beads into the first slice)

**Beads:** `sase-1hg`, `sase-1hh`, `sase-1hi` + `sase-1hi.10` (size analog),
`sase-19i.7.3.3.3.3.3` (live nested-epic evidence), `sase-1i1` (out of scope).

**Live tree, 2026-10-08:** sase `7e75bbcd8d`, sase-core `cd73d968`. Parser probe
against workspace `src` via `.venv`. Files cited above plus
`sase/memory/sase_flags.md`, `sase/memory/cli_rules.md`, `sase/memory/macros.md`,
`docs/rust_backend.md` (CI source revision pin), `docs/sdd.md` (epic phases),
`src/sase/default_config.yml` (`big_epic_phase_threshold: 5`, `accept_proposal: A`).

**Memory:** `macros.md`, `sase_flags.md`, `cli_rules.md`, `tui.md` /
`tui_screenshot.md`, `sase_beads.md`, `glossary` terms for macro, gate, feature flag,
receipt, artifact; `decisions:gates-never-block`, `decisions:rust-core-required`.
