---
create_time: 2026-10-06
updated_time: 2026-10-06
status: draft
tags:
  [
    research_swarm,
    wait-directive,
    epics,
    beads,
    artifact-links,
    tui,
    macros,
  ]
---

# `%wait(..., for_epic=)`: launch before the epic ID exists

**Question.** Should SASE add a `for_epic=<true|false>` keyword to `%wait`, so a
launch can wait for a named agent and then for any epic that agent creates,
without the user first copying the epic bead ID into `bead=`? Critique the
request. Adjust requirements that would make the feature unreliable or
surprising. Recommend a design that is intuitive, reliable, and beautiful.

**Researcher.** grk (`research.3v.grk`). Independent report. I did not locate,
open, read, or otherwise consult peer reports from this swarm.

## Bottom line

**Yes, build this.** It fills a gap the product already documents. A wait on an
epic-approved planner waits for that planner, not for the host-owned epic it
launched; today the escape hatch is "copy the new epic ID into
`%wait(bead=…)` once it exists." That is exactly the kind of human glue SASE
orchestration should absorb.

**Do not ship the request as written.** Three changes are load-bearing:

1. **Opt-in, never default-on.** `%wait:builder` must keep today's meaning.
   `for_epic` defaults to true only as the *value of the keyword when the
   keyword is present*, and only next to an agent name.
2. **Bind created epics, not worked-on epics.** `epic_bead_id` is overloaded:
   planners get it after back-fill, and phase/land agents get it because they
   *work* the parent epic. Naive use of that field waits for the wrong bead.
3. **Creation-settled, then bead-close.** Agent-done is not enough. Plan
   submission, `epic_approved`, and `EPIC APPROVED` all happen *before* the
   epic ID exists. The waiter must stay parked until creation has either
   produced an ID or settled as "no epic," then wait for that epic bead to
   close.

Recommended spelling stays close to the request:

```text
%wait(builder, for_epic=true)
%w(builder, for_epic=true, time=5m)
```

The runtime is a two-phase rebind of an existing parked runner: agent wait
with a stricter success rule, then the ordinary `wait_for_beads` close gate,
with a gold `★` handoff in the TUI so the row obviously changes meaning.

## Verdict on the idea

This is a good idea. I would build it, with the adjustments below, rather than
a new directive, a synthetic session member, or a "wait for the epic clan"
hack.

### Why it is worth doing

The user workflow is real and currently two-step:

1. Launch agent A, which will propose and (after approval) create an epic.
2. Watch until the epic bead exists, copy `sase-…`, launch B with
   `%wait(bead=sase-…)`.

B cannot be typed at step 1 because `bead=` needs a concrete ID, and named
agent waits do not cover the host-owned epic launch. `docs/axe.md` says this
out loud: a wait on an epic-approved planner waits for that planner, not for
the epic it launched; use a bead wait or a wait on the launched epic clan.

Bead waits already mean "park until this bead is **closed**." That is the
semantic the user already uses once they have the ID. The new keyword is not
a new kind of done-ness. It is a **late-bound bead wait** whose ID is
discovered from the waited-on agent.

The TUI already knows how to show mixed agent + bead waits (`WAITING ▶1 ◐2`,
singleton `WAITING ◐ sase-64`, detail lanes `[agents]` / `[beads]`). The
missing piece is a **handoff** that is impossible to miss, plus a resolver
that will not release on plan-submitted or epic-approved.

### Why the naive reading of the request would hurt

| Request as written | What goes wrong |
| --- | --- |
| "Default to true when an agent name is provided alongside it" if that means every `%wait:foo` | Breaks swarms, `%repeat` chains, `.w@` derived names, research macros, every existing wait-for-agent prompt. An agent that happens to file an epic would trap its waiter for the whole epic. |
| Wait for "any epic this agent may or may not create" without a settled-creation rule | Race: planner writes `epic_approved` and unblocks named waits *before* `sase bead work` back-fills `epic_bead_id`. The waiter starts, or concludes "no epic," and the epic appears a few seconds later. |
| Use existing `epic_bead_id` / `implements` as the created-epic link | Phase and land agents also carry `epic_bead_id` for the parent they were launched to close. `%wait(sase-64.1, for_epic=true)` would wait for the rest of the parent epic, not for a child the phase proposed. |
| AND all conditions from t=0 with an unknown bead | There is no bead ID yet. This cannot be a static `%wait(builder, bead=???)`. It has to rebind `waiting.json` after creation settles. |
| Treat `--plan` submitted-plan as success | `%wait:foo--plan` already unblocks while the plan is still in review. With `for_epic`, that is the opposite of the goal. |

### Alternatives I considered and rejected

**`%wait(epic_of=builder)` as a new target kind.** More compositional, and
structurally impossible to omit the agent name. Slightly better grammar.
Worse for the common sentence the user already wrote ("wait for builder, and
also their epic"). Keep `for_epic=true` on the same directive that names the
agent; it desugars internally to an `epic_of` set.

**`%wait(bead=epic_of:builder)`.** Overloads `bead=`, which today is a
whitespace-free ID and explicitly does *not* resolve agent-name templates.
Do not grow a mini-language inside `bead=`.

**Synthetic session member `builder--epic` that stays open until the epic
closes.** Then `%wait:builder` (session container) would wait for it. That
changes every session wait on a planner, including people who only wanted the
plan. Wrong attachment point. The extra wait belongs on the *waiter*, as
opt-in.

**Hood wait on `<epic_id>` once known.** Hood waits snapshot members at
*waiter launch*. At that moment the epic workers do not exist, so the hood is
empty and resolves immediately. Bead-close is the primitive that is live.

**Two-agent chain** (B1 waits for A, B1's successor waits for the bead). The
user still needs the ID, or B1 becomes a tiny host-owned trampoline. The
parked runner can rebind; do not spend a model turn on it.

**Start the waiter when the epic is created, not when it closes.** Different
product. The current workaround is `%wait(bead=id)`, which waits for close.
Match that. If someone later wants "unblock at creation so I can cite the
ID," that is a separate `until=created` mode. Do not smuggle it in.

## Requirement adjustments

Call these out as deliberate deltas from the prompt.

### R1. Opt-in keyword, not default-on agent waits

**Adjustment.** `%wait:builder` and `%wait(builder)` stay "wait for builder."
`for_epic` is off unless authored.

The phrase "default to true when a sase agent name is provided alongside it"
is kept in this narrower sense:

- The keyword is **illegal** without at least one agent/session/clan target
  on the same directive occurrence (`agent=` or positional).
- When the keyword is present, its default *value* is `true`
  (`for_epic=true`; a reserved bare `for_epic` token may mean the same).
- `for_epic=false` exists for Wait-modal round-trip and for cancelling a
  earlier occurrence in the same prompt.

This is the only reading that does not break the wait corpus.

### R2. Per occurrence, not launch-wide

`%wait(a, for_epic=true) %wait(b)` waits for a (plus a's epic) and for b
(agent only). `%wait(a, b, for_epic=true)` applies the flag to **both** names
in that occurrence. Mixed intent uses two directives. Same union rules as
`bead=` / `hood=` / `time=` today.

### R3. "Wait for the epic" means bead **close**

Same contract as `%wait(bead=<id>)`: every named bead must be `closed`;
missing store or missing ID fails closed; once `ready.json` is written,
reopening the bead does not re-park. Time floor still starts after *all*
dependency phases, including the bound epic.

### R4. Creation-settled before "no epic"

"May or may not create" is not "look once when `done.json` appears."
Creation is settled only when one of these holds for the newest matching
run:

| Evidence | Meaning |
| --- | --- |
| `created_epic_bead_ids` non-empty, or planner `EPIC CREATED` with back-filled ID | Created. Bind and wait for close. |
| Terminal success with no plan handoff (`completed`, `noop`) | No epic. Release the for_epic clause. |
| Tale path (`plan_committed`, `TALE DONE`, `PLAN COMMITTED`) | No epic. |
| `PLAN REJECTED` / `plan_rejected` | No epic. Named `%wait` already does not treat reject as success; for_epic agrees that there is nothing to bind, but the *agent* wait still follows the existing reject rule (exact artifact vs named wait). |
| `EPIC FAILED`, failed/lost epic-launch monitor, launch without back-fill | **Tried and failed.** Fail closed: park with the existing "never self-resolve" `wait_checks` notification. Do not pretend no epic was intended. |
| `PLAN` (submitted, in review), `EPIC APPROVED`, live epic-launch monitor, live plan gate | **Not settled.** Keep waiting. |

Disable the submitted-plan shortcut for any target that carries `for_epic`.
`%wait:foo--plan` with `for_epic=true` stays parked through approval and
launch back-fill.

### R5. Created vs assigned: new metadata, not `epic_bead_id` alone

The user is right that link infrastructure exists, and wrong that it is
already the right predicate.

Today:

- `sase bead work` back-fills the planner's `agent_meta.json` with
  `epic_bead_id` after a successful host launch. The planner row then shows
  `EPIC CREATED`.
- That field, plus `bead_id` and `phase_bead_id`, projects
  `agent:<name> implements bead:<id>`.
- Phase and land agents also carry `epic_bead_id` for the parent they
  implement.
- Plans already stamp `proposed_by` at propose time.
- `wait_for_beads` already projects `agent:<waiter> awaits bead:<id>`.

**Add** `created_epic_bead_ids` (list) on the creating run, written in the
same back-fill that sets planner `epic_bead_id`, and also when an agent
directly creates a `plan`+`epic` bead. Project a new closed-registry
relation `created` / `created-by` (agent → bead) from that field. Keep
`implements` as "this agent works or created-as-worker this bead."

Discovery, in order, against the **newest matching run** of the waited name
(and its session members, so a wait on the session container still sees the
planner's back-fill):

1. `created_epic_bead_ids`
2. Planner-only: `EPIC CREATED` plus `epic_bead_id`, when the row is not a
   phase/land worker
3. Projected `created` edges
4. Last-resort: epic-tier plan beads whose `proposed_by` / `created_by` is
   this run, created at or after that run's start

Never bind a phase/land agent's *parent* `epic_bead_id`. A phase that
proposes a *child* epic is bound through (1) or (4), which is the feature
the user wants when a worker files a follow-up epic.

### R6. Illegal combinations fail at parse, not at runtime

Error (directive error, launch does not park):

- `for_epic` / `for_epic=true` with no agent/session/clan target
- `for_epic` on a bead-only, hood-only, proc-only, or unit-only wait
- `for_epic` on an `@tribe` target (`%wait:@review` is next-entity; the
  concrete agent does not exist yet)
- `for_epic=true` together with only `time=`

Warn (launch proceeds):

- `for_epic=false` with no agent name (no-op)
- `for_epic=true` on a `%proc` / monitor name that cannot create beads
  (treat as ordinary wait + diagnostic)
- More than one created epic bound from one agent (wait for **all**, show
  both IDs)

`@epic` remains the tribe selector. `for_epic` is a different word on
purpose. Completion and docs must sit them next to each other so nobody
types `%wait:@epic` when they meant this feature.

### R7. No beta flag if the epic lands whole

This is user-reaching, but it is a new keyword with a closed parser. A beta
flag is only justified if a phase ships the keyword before the binder is
safe. Prefer one epic that lands parser, binder, links, and TUI together,
then delete nothing. If a phase *must* land the keyword early, the Off
branch is a parse error ("not available yet"), never a silent ignore.

### R8. Failed creation does not skip

If the user asked for `for_epic=true`, a failed epic launch is a failed
dependency, matching "Wait dependency can never self-resolve." Escape hatches
already exist: Wait modal, `Ctrl+R` run-now, kill/relaunch. Silent skip would
start a follow-up that assumes the epic ran.

## Recommended solution

### Grammar

Parenthesized `%wait` / `%w` gains one keyword:

| Form | Meaning |
| --- | --- |
| `%wait(builder, for_epic=true)` | Wait for `builder`, then for epics that run created |
| `%wait(builder, for_epic)` | Same, if we reserve the bare token (recommended) |
| `%wait(agent=builder, for_epic=true)` | Same |
| `%wait(builder, for_epic=false)` | Today's `%wait(builder)` |
| `%wait(builder, bead=sase-1, for_epic=true)` | Explicit beads **and** late-bound created epics |
| `%wait(for_epic=true)` | **Error:** needs an agent name |
| `%wait(bead=sase-1, for_epic=true)` | **Error** |
| `%wait:builder` | Unchanged; colon form does **not** take `for_epic=` |

Colon form stays positional agent/session/clan/tribe only, matching today's
completion rule that structured wait keywords are parenthesized.

Boolean values are `true` / `false` only (same as `%if(should_run=…)`).
Unknown values are directive errors. Duplicate `for_epic=` in one occurrence
is a duplicate-keyword error, like `bead=`.

Bare `for_epic` as a reserved positional token is worth supporting because
`%hold(pending, future)` already uses reserved positionals, and
`%wait(builder, for_epic)` is the sentence people will type. An agent
literally named `for_epic` is addressed with `%wait:for_epic` or
`%wait(agent=for_epic)`.

Parser work is local: `supported_keys` in
`src/sase/macro/_directive_collect.py`, `PromptWaitDirective` in
`_directive_edit_wait.py`, completion tables in `docs/macros.md`, and the
sase-core macro LSP keyword list. Unknown-keyword copy today names
`unit=, agent=, proc=, bead=, hood=, or time=`; add `for_epic=`.

### Durable state

`waiting.json` and `agent_meta.json` gain:

```json
{
  "waiting_for": ["builder"],
  "wait_for_epic_of": ["builder"],
  "wait_for_beads": [],
  "wait_epic_bindings": {}
}
```

After creation settles with an ID:

```json
{
  "waiting_for": [],
  "wait_for_epic_of": ["builder"],
  "wait_for_beads": ["sase-64"],
  "wait_epic_bindings": { "sase-64": "builder" }
}
```

After creation settles with no epic, `wait_for_epic_of` is cleared (or
marked resolved) and the ordinary remaining waits decide `ready.json`.

Updating **both** files matters: the TUI already prefers `waiting.json` for
live `waiting_for_beads`, and `awaits` projections come from published
`wait_for_beads` in meta. Bind once, project `waiter awaits epic`.

The parked runner does not restart. It already polls `ready.json` and
re-reads wait state on the fallback path. `wait_checks` mutates the marker
atomically, then waits for a later tick to evaluate bead close. Do not write
`ready.json` on the same tick as the bind.

`wait_completed_at` stays the full-barrier stamp. Rebind must happen before
that stamp exists; a refreshed runner that already crossed the barrier must
not grow a new epic wait.

### Resolver

Put the state machine next to today's Python wait core
(`sase.core.wait_dependency_resolution` + `wait_checks` + runner fallback).
TUI, CLI, AXE, and Telegram all need the same answer. This is shared backend
behavior; a later Rust move can take it. Do not block the feature on a
sase-core port. Do update the macro LSP in sase-core for completion.

Algorithm for each name in `wait_for_epic_of`:

1. Resolve the newest matching run with the **extended** success rule (R4).
   The normal `WAIT_SUCCESS_OUTCOMES` set includes `epic_approved`; for_epic
   treats that outcome as *not* sufficient until back-fill or launch failure.
2. If not creation-settled, stay in phase 1 (`waiting_for` still contains the
   name). Compact row still shows an agent token.
3. If settled with IDs, append unique IDs to `wait_for_beads`, record
   `wait_epic_bindings`, remove the name from `waiting_for`. Phase 2 is the
   existing closed-bead check, including `sidecar_auto_sync` hints for live
   bead waiters.
4. If settled with no epic, remove the name from `waiting_for` and from
   `wait_for_epic_of`.
5. If settled as failed creation, leave the waiter parked and emit the
   terminal-blocker notification naming waiter, planner, and launch monitor.

All other wait dimensions (hood snapshot, time floor, `%queue`, `%hold`)
keep their current order: dependencies including bound beads, then time,
then capacity, then holds.

The wait-checks confirmation pass (session grew a monitor/gate between
resolve and confirm) stays. Binding during that window must defer.

### Creating-agent back-fill

Extend `_update_epic_launch_metadata` in `src/sase/bead/epic_launch.py` to
set `created_epic_bead_ids` alongside `epic_bead_id`. Write the same list on
the session root if it is a different artifact than the planner row, so
`%wait:session` and `%wait:session--plan` discover the same ID.

Direct `sase bead create --type plan(…) --tier epic` from an agent should
append that ID too. That is the rare non-SDD path; without it, "any epic
this agent creates" is a lie.

### Jinja / vars (small, high-leverage extra)

Launch-time templates already synthesize `{{ agents["p--plan"].plan_file }}`
from a planner wait. After a for_epic wait binds and the waiter *starts*,
expose:

- `{{ agents["builder"].created_epic }}` — first bound ID
- `{{ agents["builder"].created_epics }}` — the list

so the follow-up can cite `@bead:{{ agents["builder"].created_epic }}`
without another human copy. This is not required for waiting, and it is
only available at start-of-turn after the wait releases (same as
`wait.chats` / `sase var`). Worth doing in the same epic.

### Wait modal

Add one control under Agents, not a sixth primary field:

**Also wait for epics they create**

Visible when the Agents field is non-empty; disabled with a one-line reason
when it is empty. Prefills from `wait_for_epic_of`. Apply without agent
names and with the box checked is the same hard error as the parser.

Live preview on that row:

- phase 1: `builder → ★ epic pending`
- phase 2: `builder → ★ sase-64`
- no-epic settled: `builder → no epic`

`Ctrl+R` still clears every wait, including for_epic. Editing Beads by hand
in phase 2 is allowed; clearing the bound ID is an explicit "I no longer
want the epic wait."

### TUI: make the handoff obvious

Do not add a new status word (`WAITING EPIC`). Status vocabulary is already
crowded, and `WAITING` is correct: the row is still a self-progressing
dependency wait. Make the *tokens* and the *Wait:* lanes carry the story.
Reuse the gold star the Agents tab already uses for epic creation (`★E` on
the planner).

**Compact Agents-tab row**

| Phase | What the row shows | Why it is readable |
| --- | --- | --- |
| 1. Agent still in flight | `WAITING ▶1 ★` | Agent glyph plus a quiet star that this wait will continue into an epic |
| 1b. Agent done, epic not back-filled yet | `WAITING ✓1 ★…` | The dangerous gap. Ellipsis says "creation in flight." Never look like a stuck `✓1` with no bead. |
| 2. Epic bound, agent names dropped from live `waiting_for` | `WAITING ★ ◐ sase-64` | Singleton bead ID path already exists; the star marks *inherited* epic vs a hand-typed `bead=` |
| 2, several epics | `WAITING ★ ◐2` | Counts, not IDs, as today |
| Failed creation | `WAITING ★ !` plus the red unresolvable treatment | Same family as reserved tribe `!` |

Dropping the satisfied agent name from live `waiting_for` after bind is
load-bearing for beauty: today's singleton bead renderer only names the ID
when there is **no** agent/hood wait. If `builder` stays in `waiting_for`
after it is done, the row stays `WAITING ✓1 ◐1` and the user never sees
`sase-64`. Keep provenance in `wait_epic_bindings`, not in `waiting_for`.

**Detail header `Wait:` lanes** (`ResponsiveWaitSection`)

Today:

```text
Wait: [agents] builder ▶
      [beads]  sase-64 ◐
```

Phase 1 with for_epic:

```text
Wait: [agents] builder ▶  ★ epic pending
```

Phase 1b:

```text
Wait: [agents] builder ✓  ★ creating epic…
```

Phase 2:

```text
Wait: [beads]  ★ sase-64 ◐  via builder
```

The agents lane *goes away* in phase 2 (or collapses to a dim one-liner
`via builder` under beads). That vanishing lane is the handoff. Magenta
`#FF87D7` stays on the active target; the star uses the existing epic gold
`#FFD75F` / `★E` family so the Wait: block rhymes with the planner's
`EPIC CREATED` badge.

Do not reuse the trailing gold `◆` linked-bead badge. That already means
"launched by `sase bead work`." This waiter is not an epic worker.

**No toast.** A notification on every bind would spam a research swarm.
The row change is the notification.

**Telegram / `sase agent list -j`.** Export `wait_for_epic_of` and
`wait_epic_bindings` so mobile and CLI summaries can show the same star
and `via` clause. The compact token logic should live beside
`wait_status_presentation.py`, not only in the list renderer.

### Docs and completion

- `docs/macros.md` wait section: one paragraph after `bead=`, with the
  creation-settled table and the `@epic` tribe disambiguation.
- `docs/axe.md`: replace "use a bead wait or wait on the launched epic
  clan" with "or `%wait(planner, for_epic=true)`."
- `docs/ace.md` Wait Modal + compact WAITING tokens.
- Completion: parenthesized `%wait` offers `for_epic=` with `true` / `false`
  after an agent target is present; hide the keyword on colon form.

### Tests that would actually catch the bugs

Parser: keyword with/without agent; `true`/`false`/garbage; duplicate;
colon form rejection; `%wait(a, b, for_epic=true)` attaches to both;
interaction with `bead=`, `time=`, `%queue`.

Resolver: no epic (plain DONE); tale; reject; one epic back-fill; child
epic from a phase worker; parent `epic_bead_id` on a land agent **not**
bound; `--plan` submitted does not release; `epic_approved` without
back-fill does not release; `EPIC CREATED` does; failed monitor fail-closed;
two epics; bind does not write `ready.json` on the same tick; confirmation
pass still defers if a session grew a member.

TUI: compact `★…` in the gap; singleton `★ ◐ id` after bind; Wait: lane
handoff; modal checkbox disabled without agents; snapshot goldens for the
three phases.

Links: `created_epic_bead_ids` projection; waiter `awaits` after bind;
phase worker still `implements` parent without `created`.

Jinja: `created_epic` present only after start, not at parse of the parked
prompt.

## Implementation sketch (one epic, three phases)

1. **Contract.** Parser, `PromptWaitDirective`, waiting-marker schema,
   `created_epic_bead_ids` back-fill, `created`/`created-by` relation,
   docs/completion. Flag off the resolver: authored `for_epic=true` parks
   and never silently ignores.
2. **Binder.** wait_checks + runner fallback state machine, extended
   success rule, notifications, auto-sync hint once beads exist.
3. **Beauty.** Compact tokens, Wait: lanes, Wait modal, JSON/Telegram
   parity, Jinja extras, visual snapshots.

Phase 3 is not polish-on-the-side. Without the handoff, the feature is
correct and still feels like a stuck waiter.

## Risks

- **Gap 1b is the hard UI.** If back-fill is slow, `WAITING ✓1 ★…` must
  never look idle. If we skip the ellipsis, users will Ctrl+R.
- **Name reuse.** Newest-run matching already exists for `%wait`; use it.
  Historical epics from an older `builder` run must not bind.
- **Remote V1.** `%dispatch` still cannot combine with `%wait`. No change.
- **`%repeat`.** Each iteration is its own waiter. `for_epic` on the seed
  prompt applies to each slot's `%wait:<previous>` only if it remains in
  that prompt; do not magically attach for_epic to the injected chain wait.
- **Performance.** Discovery reads agent meta already in the wait index.
  Bead-store reads start only after bind, on the path that already exists
  for `wait_for_beads`.

## Confidence and gaps

**High** on: the product gap, opt-in default, bead-close semantics, the
need to disable submitted-plan and `epic_approved` shortcuts, TUI reuse of
singleton bead display plus `★`, waiting.json rebind vs new runner.

**Medium** on: adding `created`/`created-by` vs stashing creation only in
`created_epic_bead_ids` without a new relation. A new relation is the
beautiful version and matches how `awaits` already works. If the registry
change is expensive, the metadata list alone is enough for the binder.

**Not verified in this pass:** whether every epic-create path besides
`finish_epic_launch` / `_update_epic_launch_metadata` would need the same
stamp (legacy proc fallback, `sase bead work` resume, manual
`sase bead create`). The implementation epic should inventory those before
calling discovery complete.

## Recommended solution (short)

Ship **opt-in** `%wait(<agent>, for_epic=true)` as a two-phase wait: stay
parked until the newest matching run has **settled creation**, bind
`created_epic_bead_ids` (never a phase worker's parent `epic_bead_id`) into
ordinary `wait_for_beads`, then wait for those beads to **close**. Fail
closed on failed epic launch. Show the handoff as `WAITING ▶1 ★` →
`WAITING ✓1 ★…` → `WAITING ★ ◐ sase-64`, with the Wait: lanes dropping the
agent and naming the epic `via <agent>`. That is the feature the user asked
for, made reliable enough to type without watching the planner.
