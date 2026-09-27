# SASE Goals: intuitive, reliable, beautiful outcome tracking

Researcher: mus (independent swarm report)
Date: 2026-09-27
Prior synthesis reviewed: `202609/goal_outcomes_and_verification/goal_outcomes_and_verification.md`

## Summary

Build Goals, but not as described. The core idea — one durable outcome per
agent run, claimed complete with evidence, verified by a human — is worth
building. It fixes a real attention bug: today every agent completion pings
the user (`JumpToAgent`, tag `done`), so "needs my eyes" is buried in "a
process stopped."

The proposed enforcement mechanism is the weakest part. Do not gate on
`SASE_PLAN` inside the conversation, and do not make a `/sase_new_goal`
xprompt skill the invariant. Skills are skippable, four parallel agents can
race to create four copies of one goal, and the launcher already strips
`SASE_PLAN` on spawn (`src/sase/agent/launch_spawn.py::_remove_inherited_sase_plan_env`).
The launcher knows the prompt, plan, bead, lineage, and eventual agent ID
before the model ever runs. Bind the goal there, in host code, with the
model only refining or linking — never establishing the invariant.

My recommended solution: **host-bound goals at launch + required
`builtin@goal` finalizer with typed evidence + Artifacts-pane Goals inbox
with `JumpToGoal` attention + hot unsettled-goal projection for O(n)
reads.** Details below. Adjustments to the original requirements are
marked **[ADJUSTMENT]**.

## Is this a good idea?

Yes, with scope discipline.

What is good:

- Outcome vs. process is the right cut. One epic spans planner + phases +
  retries + lander; one research question spans a 5-agent swarm plus a lead
  synthesis. Tying "done" to the agent run forces the user to reassemble
  the outcome from N completion pings. Tying it to a goal lets N runs
  converge on one verifiable claim.
- Plan `goal` strings already exist (tale/epic frontmatter, Rust-validated
  via `src/sase/sdd/plan_validate.py`). Goals give that string a lifecycle,
  an owner, evidence, and a settle decision instead of leaving it as dead
  frontmatter.
- Verification-gated attention is strictly better than completion-gated
  attention for this user's stated pain. Keep errors, questions, gates, and
  plan approvals on their own routes; move only "outcome ready to check"
  onto the goal route.

What is risky or wrong in the request as written:

1. **"Every agent checks `SASE_PLAN` and maybe calls a skill" puts a
   system invariant in the least reliable layer.** The model can forget,
   the skill can be skipped, and parallel agents can duplicate. This has
   been tried in spirit with commit declarations: the reason
   `builtin@commit` works is that the host issues the obligation,
   binds the digest/nonce, and adjudicates. Goals need the same treatment.
2. **"All agents MUST have a goal" needs a precise subject.**
   Literally every shell (monitor delivery, gate follow-up, `%proc`,
   hidden helpers) filing independent goals would spam the inbox and make
   "active goals" meaningless. The invariant should be: every **LLM work
   agent** starts with exactly one primary goal; mechanical/hidden shells
   inherit context and cannot close user goals without delegation.
3. **A blanket evidence rule ("always attach a test run") breaks
   legitimate goals.** Answering a question, writing a doc, delivering a
   plan, or triaging options cannot produce a test receipt. Evidence must
   be typed by outcome, with "resolvable ref + human check" as the floor
   and receipts added only when the goal's policy demands them.
4. **A fourth top-level tab is the most expensive UX answer, not the
   most beautiful one.** The TUI chrome is exactly
   `Agents | Artifacts | Services` (`src/sase/ace/tui/tab_order.py`), and
   the Artifacts pane already owns list/detail/relation-rail/jump
   contracts. A Goals inventory fits there with far less navigation,
   persistence, and grouping cost than a new tab.
5. **Cross-machine "lightning fast" needs a freshness contract, not just
   a data structure.** Any Git-backed share has clone/pull lag. The O(n)
   promise should cover the warm local read, with an explicit sync
   watermark and pending-publication state, not a claim of global
   instant visibility.

## Goal model (recommended)

A goal is a durable **outcome record**, not a bead, plan, notification, or
agent alias:

- `id`: opaque stable `goal:<...>`; title may change, ID never does.
- `title` + `outcome` (one sentence each): what "done" means in user terms.
- `acceptance`: 0–N checkable criteria; empty is allowed for open-ended
  answers but then the verify hint must say "read the answer."
- `origin`: immutable content-addressed snapshot of the creator's
  **submitted unit prompt** (pre-xprompt-expansion, cf.
  `submitted_xprompt.md` vs alias-resolved `raw_xprompt.md`), plus
  upstream/root prompt or group digest for fan-outs, plus each
  contributor's submitted prompt and global agent identity.
- `links`: plan ref, bead refs (linked, not embedded), evidence refs from
  the accepted claim.
- `visibility`: `user` (default inbox) vs `internal` (hidden helpers,
  coordination scaffolding).
- `status`: `active` → `needs_review` (claim filed) → `verified` /
  `waived`, plus `canceled` / `superseded`. Rejection returns to `active`
  with feedback. Only `active` + `needs_review` are hot.
- `revision`: monotonically increasing; every attach/claim/settle names
  its basis revision so races fail closed instead of last-writer-wins.

**[ADJUSTMENT] Goals are not beads.** Beads carry scheduling, size, phase
ancestry, and close semantics; forcing every answered question through
them inflates the tracker and drags closed-record history into the hot
path. Link goals↔beads; do not subtype one as the other. The shared
model, transitions, and evidence rules belong in `sase-core` (Rust
boundary per project rules); Python owns launch orchestration and TUI.

## Binding: how every agent gets a goal without burdening the user

This directly answers the user's worry that agents can't set their own
goals and users would have to do it in every prompt. They should not.
The host sets the binding; the agent only confirms, narrows, or asks to
split.

Launch-time resolution order (host-owned, deterministic, no fuzzy
auto-merge):

1. Associated plan's persisted `goal_id` (backfill legacy plans once by
   deriving an ID from plan ref + required `goal` text). Plan goal text
   becomes the outcome statement.
2. Explicit operator selection (`--goal`, TUI picker, or API field) when
   the launcher was told which goal this run serves.
3. Parent/session/pipe/recovery inheritance (`sase pipe`, questions,
   gates, plan approval, retries, monitors carry the binding in the
   host handoff transaction).
4. Exact structured identity (bead/epic ID) when it uniquely names one
   unsettled goal — exact match only.
5. Otherwise create an ad-hoc goal from the submitted prompt (title +
   outcome drafted by host heuristics, agent free to tighten in its
   first turn).

The launcher persists the binding with agent metadata and injects the
goal statement into agent instructions. Expose `SASE_GOAL_ID` as a
convenience for tools; it is **not** the source of truth, exactly as
`SASE_PLAN` is not today.

**[ADJUSTMENT] No planner exemption.** A planner has a purpose: give it
the incoming outcome goal at launch. `sase plan propose` attaches the
resulting plan artifact to that same goal. If the user asked only for a
plan, plan delivery satisfies a plan-delivery goal through the existing
PlanApproval attention — no duplicate goal alert.

**[ADJUSTMENT] No `SASE_PLAN`-check skill as enforcement.** Keep an
optional goal-inspection skill (show active goals, propose split/link)
because it is handy mid-run, but the invariant lives in
`launch_spawn`/attach/approval paths, which already own env hygiene.
Concretely: the current scrub of `SASE_PLAN` proves env vars are the
wrong trust anchor — the child must receive an explicit, host-recorded
goal binding, not detect one ambiently.

Concurrency rules:

- Never silently join two goals on text similarity. Show semantic
  matches as suggestions; joining requires an explicit agent or human
  action naming both IDs.
- Reject binding to a settled goal unless it is reopened or a linked
  follow-up is created.
- A sibling/phase may not close a goal while required contributors are
  live; the designated coordinator/lander files the outcome-level claim.
- Prepared monitor completion (`sase final prepare`) carries a
  predeclared choice: green may file the claim, red keeps open and
  launches recovery. Crashes/kills cannot choose; the host records
  failed work and keeps the goal `active`.

Example default goal the user asked for: "answer the user's question"
is fine as an auto-created ad-hoc goal, with outcome = "user has a
correct, sufficient answer to <prompt digest>" and evidence = the
response/transcript artifact.

## Finalizer and evidence: what "close" requires

Add non-removable `builtin@goal`, ordered **after** `builtin@commit`,
triggered even on clean trees (today `defaults: [commit]`,
`required: []` in `src/sase/default_config.yml`). Every normal provider
return chooses:

- `keep_open { reason, next_step }` — no notification.
- `close { claim, criterion_map, verify_hint, limitations, evidence_refs }`
  — files `needs_review`, emits one attention item after durable
  publication.

The host issues the obligation (ID, revision, criteria, eligibility,
candidate evidence) and rechecks revision + eligibility at execution;
stale declarations (commit or monitor changed the world underneath) are
rejected and recovered. The agent's `close` is a **claim**, not a
settlement. Only explicit human **Verify / Waive / Reject-and-reopen**
settles it. Reading or dismissing a notice is not verification.

Evidence floor (host-validated, not model-asserted):

| Outcome | Minimum durable evidence | Host checks |
|---|---|---|
| Answer / review | Captured response or transcript artifact | Digest + association to closing run; "read the answer" is a valid verify hint |
| Research / doc | Registered report/file ref | Ref resolves to the produced version; claim cites section or finding |
| Plan delivery | Validated archived `plan:` ref | Proposal/approval handoff state; suppress duplicate PlanApproval alert |
| Code / ops change | Host-finalized stitch/Patch or immutable output ref, **plus** any check/monitor receipts the acceptance criteria require | Commit finalizer succeeded; refs + receipts exist; criteria met or human-waived |

Policy-sensitive points:

- Plain assertion text ("tests pass") is never sufficient alone. The
  agent may explain *why* evidence supports the claim but cannot mint a
  receipt, ref, or policy waiver.
- A reply-only run may need the host to publish its response snapshot
  before an `agent:` page exists remotely; a close-before-commit run
  needs the "current commit result" token the goal finalizer resolves
  to the real stitch after `builtin@commit`. This closes the timing gap
  where the evidence does not exist at submit time.
- For code work missing a required receipt: keep open or disclose the
  limitation for explicit human waiver. The agent never waives its own
  criterion on the closing turn.
- The `completion_claimed` event carries accepted refs + digests; the
  artifact-link projection is derived from that event so a claim is
  never visible without its evidence links. Notification emission
  follows durable publication and is idempotent on claim ID.

## Storage and the O(n) read path

The request demands any human/agent on any machine can read active goals
fast, with done goals costing nothing. Directory layout alone does not
achieve this; publication atomicity and projection design do.

Recommended:

- Canonical store: append-only, schema-versioned per-goal events
  (`created`, `agent_attached`, `plan_attached`, `completion_claimed`,
  `verification_accepted`, `reopened`, ...) with actor, basis revision,
  idempotency key. Prefer extending the existing private **agents
  sidecar** (already holds agent identities + prompt objects, hidden
  machine-owned clone, publication/retry machinery) over minting a new
  sidecar repo with its own clone/sync/repair/consent surface. Do not
  put the canonical goal in workspace-local `agent_meta.json`, the
  notification inbox, or the bead event log.
- Publication: prompt objects + new events + **per-goal hot snapshots**
  land in one Git transaction. Keep unsettled snapshots in
  `goals/live/<id>.json`; settlement removes the hot file, leaving
  archived history. Publisher locks locally, validates `basis_revision`,
  pull/recomputes on non-fast-forward, pushes with bounded retry. On
  conflicting concurrent claims, retain/reopen `active` with a conflict
  diagnostic rather than timestamp-picking a winner.
- Read path: foreground `sase goal list` reads only a compact local
  projection (one bounded record per unsettled goal, no history scan, no
  synchronous pull). The TUI paints the cached view and refreshes off
  the event loop. Hot list is therefore `O(n_unsettled)` — active plus
  awaiting-review — and settled history has no foreground cost. Measure
  p95 hot-list latency and TUI frame budget per supported machine;
  do not assert "sub-millisecond" without measurement.
- Freshness honesty: show last-sync watermark + pending-publication
  state. Strict shared launch/close requires successful publication;
  projects without an initialized/consented shared sidecar run explicit
  local-only mode or refuse the shared guarantee. First clone still
  transfers history; the O(n) promise covers warm active queries, not
  bootstrap or repair (rebuild from full history stays off the
  foreground path).

A local SQLite read model with a partial index over unsettled rows is a
reasonable later optimization if the file projection outgrows its
update/query pattern; it is not needed for v1.

## TUI and navigation: answering "which goals are active, and how do I jump?"

The user's two UX questions should drive the design: (1) for this
project, what is active? (2) from a goal, how do I reach every linked
artifact and running agent?

Recommended (beautiful = restrained, not a new tab):

- **Goals pane inside Artifacts** as the project-wide inventory, plus a
  compact goal chip/header + `by goal` grouping on the Agents tab. This
  reuses the existing three-tab chrome and the artifact relation rail
  instead of paying for a fourth tab's navigation/persistence/grouping.
- Default lanes: **Needs review** first, then **In progress**. Row:
  status, title, project, last activity, contributor count. No prompt
  bodies in rows (privacy + density); origin prompt is a preview with
  an explicit open action.
- Detail: outcome, acceptance checklist, "How to verify" hint from the
  claim, plan/bead refs, contributing agents, evidence refs with digests,
  limitations. Actions: Verify / Waive / Reject-and-reopen / Reopen,
  each mirrored in CLI (`sase goal list/show/verify/reopen`) so the TUI
  is never the only control path.
- Links: add `goal` as a first-class artifact kind and one projected
  `agent pursues goal` relation (artifact-link registry is closed, so
  this is a deliberate schema extension). Derive plan/evidence links
  from binding/claim records rather than hand-editable pages. Jump from
  a goal to its plan/report/stitch, or select a specific contributor on
  the Agents tab even when grouped/collapsed. Empty state: "new work
  receives a goal at launch."
- Visual discipline: one restrained accent, readable status text (never
  color alone), stable row order so the inbox does not jump under the
  reader.

## Notifications: from "an agent stopped" to "an outcome is ready"

- One `needs_review` transition → one `JumpToGoal` attention item with
  claim + verify hint, deduplicated by goal/claim identity across
  machines and retries.
- `keep_open` and ordinary success completion no longer create default
  user-completion unread dots/chimes; they remain visible as execution
  history. This is the cutover the user actually wants: retire the old
  `JumpToAgent(done)` noise on the success path (`src/sase/axe/run_agent_runner_finalize.py`),
  keep failures/questions/approvals on their own routes, and suppress
  the duplicate plan-only goal alert when PlanApproval already covers it.

## Critique of alternatives considered

- **Bead-backed goals:** reuses lifecycle/sync but overloads scheduling
  semantics and drags closed-record history into reads. Link, don't merge.
- **Separate goals sidecar:** cleaner boundary, but a whole new repo to
  configure/clone/sync/repair/authorize. Revisit only if the agents
  sidecar's access policy or publication load proves incompatible.
- **Env-var + skill enforcement (`SASE_PLAN` check):** cheapest to
  prototype, wrong to ship. Fails the reliability bar (skippable,
  racy, ambient) and the beauty bar (every agent doing intake paperwork).
- **Mandatory uniform evidence triad (e.g. command witness + artifact +
  rationale for everything):** fits code changes, excludes answers and
  plans. Typed evidence with a resolvable-ref floor is strictly more
  expressive.
- **Goals deck confined to the Agents tab:** keeps jumps local but makes
  the verification inbox depend on agent selection and risks
  overwhelming the tab the user already uses for process. Project-wide
  inbox belongs in Artifacts; Agents gets a context chip.

## Risks and open questions

- Backfill: existing active plans get deterministic `goal_id`s; history
  (completed agents) stays legacy/unbound — do not invent goals for the
  past.
- Privacy: publishing creator prompts to the sidecar is a publication
  decision. Respect `disabled`/private settings; document what a goal
  publish discloses.
- Multi-machine races on the same goal need real tests (two-machine
  same-goal claim race, interrupted publication, cold bootstrap, stale
  projection).
- Close-before-commit and failed-monitor paths need explicit finalizer
  tests (duplicate submit, deferred commit, concurrent close/reopen).

## Recommended build order

1. `sase-core`: goal wire model, transitions, provenance, evidence
   validation, publication protocol; Python binding + revision ratchet.
   Publisher + hot projection first, with race/interrupt/bootstrap tests.
2. Launch binding across direct runs, approvals, bead work, swarms,
   child launches, retries, pipes, monitors, gates, hidden helpers.
   Assert every *new* LLM agent starts with exactly one primary goal.
3. Required `builtin@goal` + handoff/prepared-monitor handling with
   typed evidence checks.
4. `JumpToGoal` attention + Verify/Waive/Reject; then retire ordinary
   success-completion noise.
5. Artifacts Goals pane + Agents context + relation jumps; benchmark
   hot-list latency vs. growing settled history.

## Bottom line

Ship host-owned goals, not skill-gated goals. The user never writes a
goal by hand unless they want to; agents never "remember" to create one;
the launcher guarantees it, the finalizer forces the keep/close choice
with real evidence, and the Artifacts pane turns "done" into a calm,
jumpable verification inbox. That is intuitive (no new user burden),
reliable (host adjudication + idempotent publication), and beautiful
(one accent, two lanes, every jump one keypress away).
