# After Goals: a durable memory end state, not a design archive

_Independent research · cdx · 2026-09-27 · project: sase_

## Question and conclusion

What SASE memory should change after the Goals program in
`sase_goals_epic_roadmap.md` has landed?

My answer is: **make a small, layered update, but do not preserve the roadmap or the
whole Goals design as memory.** The finished feature will be too cross-cutting to leave
entirely implicit, yet most of its details belong in code, tests, CLI help, ordinary
docs, the injected goal block, and generated skills. Durable memory should retain only
facts that a future agent is likely to violate while changing a different seam.

The target end state I recommend is:

- three decision strands recording the authority, storage, and attention boundaries;
- three glossary strands for the new nouns agents will encounter everywhere;
- one concise `sase_goals.md` reference note for maintainers;
- narrow updates to the existing xprompt, artifact, bead, and glossary notes;
- no new core note, Goals memory web, task type, or permanent feature-flag guidance.

The first authority decision should ideally be accepted before G1 is planned, as the
roadmap recommends. The storage decision should land with G1, and the attention
decision should wait for G6's measured cutover. The final post-program task should be
an audit and consolidation, not the first time any of this is written down.

## Sources and method

I independently consulted:

1. `research:202609/sase_goals_epic_roadmap/sase_goals_epic_roadmap.md`, through an
   audited `sase artifact read`.
2. `research:202609/sase_goals_design/sase_goals_design.md`, also through an audited
   artifact read.
3. Current reference memory through audited `sase memory read`: `sase_artifacts.md`,
   `sase_beads.md`, `sase_flags.md`, `tui.md`, `tui_perf.md`, `xprompts.md`, and
   `generated_skills.md`.
4. The accepted memory-architecture decisions `corpus-before-mechanism`,
   `memory-webs`, `webs-render-in-their-own-section`, and
   `memory-links-are-authored`, plus representative glossary strands.
5. Git history for `sase/memory/` in this checkout. Since 2026-09-01 it added 13
   decision strands, 28 glossary strands, and only 3 flat notes. Recent programs such
   as tool receipts, triage, holds, dispatch, turns, and the TUI consistently put
   rationale in decisions, vocabulary in the glossary, and create a flat reference
   note only when there is a real operational workflow to protect.

I did not inspect any other report from this research swarm.

## What memory is for here

The design and roadmap contain at least four different kinds of information, and only
two belong in memory:

| Information | Durable home after landing |
| --- | --- |
| Why SASE assigns authority the way it does | Decision strand |
| Stable words used across code, prompts, UI, and docs | Glossary strands |
| Rules a maintainer must obey across several modules | Reference note |
| Commands, flags, config keys, keymaps, wire fields, event lists, file paths, rollout phases, and benchmark values | CLI help, schemas, code, tests, and ordinary docs |

This distinction matters because the roadmap is intentionally provisional. It names
open choices, predecessor epics, temporary flags, phase counts, candidate thresholds,
and current source locations. Those are useful planning evidence and poor memory. A
future agent should not pay for or obey a frozen copy after the implementation has
moved.

The runtime contract is also not primarily a memory problem. Once G4 lands, every LLM
turn receives a bound-goal or draft-goal instruction. Once G3 lands, the required
`builtin@goal` finalizer and the generated `sase_final` / `sase_goal` skills teach the
agent what it must do. Repeating that procedure in always-loaded core memory would add
token cost and create two authorities that can drift.

Memory should instead answer the maintainer's questions: Why may an agent claim but not
verify? Why is `%goal` different from `@goal`? Why can't the TUI reduce ledger state on
the event loop? Why does a successful agent no longer notify? Why isn't a Goal a bead?

## The three decisions worth preserving

### 1. The host binds, agents claim, users settle

Recommended strand: `sase/memory/decisions/goals-bind-claim-settle.md`.

The claim should be narrow and durable:

> Every LLM turn is bound by the host to exactly one primary SASE Goal before provider
> execution. An agent may name a draft and claim that an outcome is ready, but only the
> user may verify, acknowledge, reject, drop, merge, or reopen it. Goal-system failures
> fail open for the agent turn and remain visible to audit.

This is the program's central authority boundary. It explains several otherwise
arbitrary-looking mechanisms: host-side resolution, draft name/adopt rather than
agent-created goals, host-derived claim eligibility, provenance checking, human-only
status verbs, and fail-open finalization. Its rejected alternatives are credible and
already documented by the design: checking `SASE_PLAN`, asking every model to create a
goal, allowing an agent to close its own outcome, or attaching only a per-agent
"attention needed" bit.

This decision should link to `single-turn-agents`, `host-owned-completion`,
`gates-never-block`, and `rust-core-required`. It is the one Goals memory item worth
accepting before planning, because all six epics otherwise have to rediscover it.

### 2. Goals use immutable events and a hot unsettled index

Recommended strand:
`sase/memory/decisions/goals-use-immutable-events.md`.

The lasting claim should be about source-of-truth shape, not today's directory names:

> Goal state is reduced from immutable, uniquely named events. A small live marker
> index bounds ordinary reads to unsettled goals, and machine-local projections are
> disposable caches. Machine writes use the host-owned clone rather than a project's
> primary checkout.

The reason is cross-machine conflict avoidance and read complexity. The rejected
alternatives are mutable per-goal snapshots, moving records between active/settled
directories, or storing shared mutable state in the agents sidecar. The record should
link to `machine-link-writes-off-primary`, `rust-core-required`, and
`corpus-before-mechanism`.

Do **not** make "co-hosted in the beads repository" an eternal part of the claim. It is
a current deployment choice with an explicit reopen condition: measured contention may
move the `goals` role to another repository without changing the domain model.

### 3. Goal claims, not successful turns, own success attention

Recommended strand:
`sase/memory/decisions/goal-claims-own-success-attention.md`.

This decision should be written only after the G4/G6 soak, using the actual measured
coverage, precision, merge rate, and notification-volume change in its Why section:

> Successful agent turns are history, not user attention. A durable Goal claim opens
> one idempotent GoalVerify gate; reading or dismissing its notification never settles
> the claim. Errors and unrelated decisions retain their existing routes.

This preserves the product reason for G6 and prevents a future notification cleanup
from casually restoring per-turn success pings. It also captures that the ledger is
canonical and the gate is decision transport, not another goal store. Answer-only
acknowledgement is a policy detail for the reference note, not part of the decision's
core claim.

Its reopen condition should be empirical: sustained failure of claim coverage or
precision, or evidence that outcome-level review creates more attention cost than it
removes. That is stronger than copying the roadmap's proposed thresholds into memory.

## Vocabulary: add three terms, not a Goals web

Goals will be referenced by launch code, finalizers, gates, artifacts, plans, agents,
the TUI, and user docs. That is a demonstrated vocabulary corpus, so glossary strands
are appropriate:

1. **SASE Goal** (`glossary/sase-goal.md`, alias `goal`): a durable user outcome behind
   one or more agent turns, distinct from an agent's execution status and a bead's work
   status. Its short definition can name the lifecycle and the fact that the user
   settles it.
2. **Goal Binding** (`glossary/goal-binding.md`): the host-resolved association between
   a launch/turn and exactly one primary Goal. It should distinguish `%goal:<id>`
   (binding) from `@goal:<id>` (citation) and name `goal_id`, not the environment
   variable, as truth.
3. **Goal Claim** (`glossary/goal-claim.md`): an agent's evidence-backed assertion that
   a Goal is ready for user review. A claim moves a Goal to Review and is not a
   settlement.

I would fold draft, standing goal, acknowledgement, and GoalVerify into these bodies
and the reference note at first. Add separate glossary strands only if those terms
become independently ambiguous across the landed corpus. Likewise, do not create a
`goals` memory web. The accepted `corpus-before-mechanism` decision argues against a
keyed retrieval structure before many independently readable goal-policy records
exist, and every web descriptor is always injected into every agent instruction.

## One maintainer reference note

Add `sase/memory/sase_goals.md` as a `type: reference` note with a description like:

> Read before changing Goal storage or lifecycle, launch binding and inheritance,
> claim/finalizer policy, GoalVerify gates, Goals attention, or the Goals TUI.

It should be a rulebook, not a second design document. A useful compact structure is:

- **Model and authority:** host binds; agent names/claims; user settles; a goal status
  is not an agent or bead status.
- **Binding:** resolution is host-owned and deterministic; settled goals do not bind;
  `%goal` binds while `@goal` cites; all launch/successor paths must remain in the
  frozen matrix.
- **Lifecycle:** only the landed statuses and flavors, with the concurrency rules that
  code alone makes easy to violate.
- **Storage and sync:** events are truth, markers/projections are derived, shared writes
  go through the hidden clone, freshness is explicit, and settled history must not
  enter hot reads.
- **Claims:** eligibility is host-derived; evidence must resolve and prove provenance;
  `@commit`/`@reply` are symbolic until host resolution; receipts crossing machines
  require snapshots; goal errors keep the turn open rather than failing it.
- **Attention:** one claim yields one gate; dismiss is not a verdict; answer
  acknowledgement and follow-up/retraction rules.
- **Performance and tests:** name the required acceptance matrices and invariants, but
  link ordinary runbooks for exact commands and benchmark values.

The note should author links to the three new decisions, the three glossary terms,
`sase_artifacts.md`, `sase_beads.md`, `xprompts.md`, and `tui.md`. It should not contain
the six-epic sequence, old feature flags, current source line numbers, the exhaustive
CLI, keymaps, full event vocabulary, or proposed soak thresholds.

## Surgical updates to existing memory

The new note does not remove the need to update current integration points whose text
would otherwise become false:

| Existing memory | Required final-state delta |
| --- | --- |
| `xprompts.md` | Add `%goal:<id>` / `%goal:new` to the directive table. State that `%goal` binds while `@goal` only cites, that settled goals are refused, and point detailed inheritance rules to `sase_goals.md`. |
| `sase_artifacts.md` | Add `goal:` to the artifact model/read examples and add the landed `pursues`, `evidences`, `defines`, and `follows` relations plus inverses to the closed registry. Do not duplicate the Goal card schema. |
| `sase_beads.md` | Add one short Goal-vs-bead boundary: a Goal is the outcome, beads are scheduled implementation work; bead dependency/status operations remain independent, and agents must not settle a Goal by closing a bead. Link to `sase_goals.md`. |
| `glossary/artifact.md` | Include a SASE Goal among durable artifact examples. |
| `glossary/artifact-reference.md` | Add `@goal` to built-in kinds and preserve the cite-versus-bind distinction. |
| `glossary/sase-gate.md` | Add GoalVerify to the typed gate kinds and state that its notification is transport, not settlement by dismissal. |

These are edits, not replacements. Existing notes already establish the generic rules
for artifacts, beads, gates, and xprompts; Goals only adds one integration contract to
each.

## What I would deliberately leave unchanged

- **Core memory (`sase.md` / `gotchas.md`).** The live goal block and required
  finalizer already reach every relevant turn. Making the full Goal contract core would
  duplicate them and charge every agent forever. Promote one concise rule only if
  post-launch evidence shows agents repeatedly violate it despite injected guidance.
- **`sase_flags.md`.** If each epic removes its beta scaffolding as planned, no
  Goal-specific flag survives. A permanent user choice is config, not a flag. A
  lingering umbrella flag means the rollout is not actually complete.
- **`tui.md` / `tui_perf.md`.** Their existing rules already require cached snapshots,
  off-thread refresh, read-only render paths, bounded startup, change tokens, and the
  16 ms navigation budget. Add Goal-specific text only if implementation reveals a new
  non-obvious trap that those rules and tests do not cover.
- **`generated_skills.md`.** G3/G4 must update the source templates for `sase_final`
  and `sase_goal`, but the existing memory already says generated skills come from
  `src/sase/xprompts/skills/` and are deployed only from landed code. Goal procedure
  belongs in those skill sources, not this note.
- **Task types and feature-flag glossary.** Goals do not create a new class of task.
- **The design and roadmap.** Keep them as research artifacts and link them from the
  new decisions if useful; do not paste their content into memory.

## Timing and final audit

Although the question is framed around the end of all six epics, deferring every memory
change until then creates an avoidable period where landed behavior and agent guidance
disagree. I would stage the work this way:

| Point | Memory action |
| --- | --- |
| Before G1 planning | Accept `goals-bind-claim-settle` if its authority boundary is settled. |
| G1 | Add the storage decision and the first `sase_goals.md` sections; update artifact memory only for behavior that actually landed. |
| G2–G4 | Add binding/claim glossary strands and increment the reference/xprompt/bead notes with shipped contracts. |
| G5 | Usually no memory change beyond links; record a TUI gotcha only if one is genuinely novel. |
| G6 after soak | Add the measured attention decision; remove any stale flag-era text. |
| Program close | Compare every memory statement against landed code and tests, run memory generation/validation, and trim rollout history or duplicated procedure. |

Each mutation should go through `/sase_memory_write`. The final audit should use the
landed implementation as its authority, not assume that roadmap names, statuses,
relations, thresholds, or storage placement survived unchanged.

## Recommended set of memory updates and additions

1. **Add three decision strands:**
   `decisions/goals-bind-claim-settle.md`,
   `decisions/goals-use-immutable-events.md`, and—only after measured G6
   cutover—`decisions/goal-claims-own-success-attention.md`.
2. **Add three glossary strands:** `glossary/sase-goal.md`,
   `glossary/goal-binding.md`, and `glossary/goal-claim.md`; keep draft and GoalVerify
   inside those definitions until the landed corpus proves they need separate terms.
3. **Add one reference note:** `sase_goals.md`, scoped to stable maintainer rules for
   authority, lifecycle, binding, storage/sync, claims, attention, and invariant tests.
4. **Update six existing integration notes:** `xprompts.md`, `sase_artifacts.md`,
   `sase_beads.md`, `glossary/artifact.md`, `glossary/artifact-reference.md`, and
   `glossary/sase-gate.md` with only the small Goal-specific deltas listed above.
5. **Do not add** a Goals core note, Goals memory web, task type, permanent flag note,
   duplicated CLI/keymap/event catalog, or copy of the roadmap/design. Leave
   `sase_flags.md`, `tui.md`, `tui_perf.md`, and `generated_skills.md` unchanged unless
   the actual implementation creates a new durable rule those notes do not already
   cover.
6. **Stage the memory with the owning epics and finish with one post-G6 audit**, using
   `/sase_memory_write`, landed code/tests, and measured cutover results as the source
   of truth.
