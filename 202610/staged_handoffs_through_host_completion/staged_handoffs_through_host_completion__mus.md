# Gates and Monitors Should Finalize Instead of Kill: Research and Recommendation

`research:202610/gate_monitor_finalizer_unification__mus.md`

## Summary

Directionally yes: the current "handoffs kill the agent and skip finalizers" design
loses work, and the motivating cases are real. But the proposal as stated —
"just use the existing commit finalizer, require every turn to declare, teach commit
that empty is okay" — is underspecified in the one place that matters: **ordering and
enforcement**.

The commit finalizer already knows empty-is-okay. The hard part is making
`commit-then-handoff` atomic enough that the handoff cannot strand the commit and the
commit cannot strand the handoff. The recommended solution is a small, explicit
protocol change, not a new finalizer type:

1. Agents submit their final declaration **before** invoking any turn-ending handoff
   (`sase plan propose`, `sase monitor start`, `sase gate create`, plus `questions` /
   `pipe` for consistency).
2. Each handoff command validates `final_submission_is_current()` (or
   `submission_required is false`) and refuses to hand off when the declaration is
   missing or stale — the agent is still alive at that point, so it can repair.
3. The host stops skipping finalizers when a pending-handoff marker exists and
   instead runs them **before** adopting the handoff successor.

This preserves the existing `builtin@commit` semantics, reuses the already-built
prepared-completion machinery for monitors, and fixes the demonstrated data-loss bug.
Do not ship a version that only removes the exemption without the handoff-side
refusal: that recreates the same lost-edit window with a new name.

## What the Current System Does

### Five kill-paths, one skip

Pending-handoff markers in `src/sase/agent/pending_handoff.py`:

- `PLAN_PENDING_MARKER` (`.sase_plan_pending`)
- `QUESTIONS_PENDING_MARKER`
- `MONITOR_PENDING_MARKER`
- `GATE_PENDING_MARKER`
- `PIPE_PENDING_MARKER`

Each path follows the same shape:

- Monitor: `src/sase/monitor/handoff.py:maybe_handoff_monitor_from_agent()` →
  `src/sase/turns/handoff.py:maybe_handoff_turn_from_agent()` →
  `src/sase/main/utils.py:kill_agent_runner_group()` (`SIGTERM` to the runner
  process group). The docstring is explicit: the helper "kills this runner" and is
  `NoReturn` when `SASE_AGENT` is set.
- Gate: `src/sase/gate_turn/agent_handoff.py:maybe_handoff_gate_from_agent()` uses
  the same `maybe_handoff_turn_from_agent()` + kill path, with compensation
  (`_compensate_failed_handoff`) that cancels the gate and restores the claim when
  the marker write fails.
- Plan: `src/sase/main/plan_propose_handler.py:458-479` writes
  `PLAN_PENDING_MARKER`, pulses the TUI refresh, then `kill_agent_runner_group()`.
  The comment at line 482-490 states the consequence directly: "Proposing a plan
  terminates the runner mechanically, so this is the only place a handoff can be
  caught at all — a finalizer or a later commit-triggered hook never runs for this
  turn."

Finalizer execution then explicitly yields. `src/sase/finalizers/controller_context.py:41-47`
(`should_skip_finalizers`) returns `True` when `has_pending_handoff()` is set, and
`src/sase/finalizers/controller_run.py:217` returns the provider result unchanged in
that case (`_journal_handoff_skip`). The mechanical exemptions (`/sase_plan`,
`/sase_monitor`, `/sase_handoff`, `/sase_questions`) are not violations of
`decisions:host-owned-completion` — they are its documented carve-out — but they are
exactly the window where dirty work is stranded.

Instruction accounting agrees: `src/sase/finalizers/_prepare_completion.py` says
prepare "does not submit a declaration, commit, or end the turn," and the skill
`src/sase/macros/skills/sase_final.md` lists "successfully executed handoffs through
plan, monitor, pipe, or questions" as the only exemption. `src/sase/instructions/readout.py`
classifies `plan_handoff` / `monitor_prepared` / `monitor_plain` / `other_handoff`
as non-miss outcomes without any declaration.

### The commit finalizer already handles "nothing to commit"

`src/sase/finalizers/declaration_store.py:build_context_requirements()` sets the
`builtin@commit` requirement to:

- `trigger = "dirty_repository"` and `submission_required = bool(repository_obligations)`
  when dirty repos exist;
- `trigger = "not_triggered"`, `submission_required = False` when the tree is clean.

`context_requires_submission()` (`src/sase/finalizers/declaration_manifest_io.py:219`)
is `any(requirement.submission_required ...)`. So a plan/monitor turn on a clean
tree already yields `submission_required: false`, and the skill already says "if
context says no payloads are required, stop here and return."

Dirty discovery (`src/sase/llm_provider/commit_finalizer_state/__init__.py:collect_dirty_state`)
covers main, configured sibling/linked repos, opened externals, and SDD stores —
i.e. the plans-sidecar and test-fix edits in the motivating case are already
obligation-eligible. Nothing about the commit finalizer needs to "learn" the empty
case; the proposal's second bullet is already implemented. What is missing is (a) the
requirement to consult it at all on handoff turns and (b) host execution when a
handoff marker is present.

### Prepared completion already marries commit + monitor for one profile

`sase final prepare` seals a conditional-completion intent
(`src/sase/finalizers/_prepare_completion.py:prepare_conditional_completion`), and
`sase monitor start -f <ref>` binds it (`src/sase/monitor/start_flow.py:_prepared_completion_accept`).
On green the host commits (and closes the bead when `bead_action: close`) and runs
no successor; on red it invalidates the intent and launches recovery. The skill text
in `sase_final.md` ("Prepared Monitor Completion") and `sase_monitor.md` documents
this, including the `accept: no-new` receipt-gated variant.

That is the existence proof for the requested feature — but only for `verify`
monitors with a stage-reporting check. General monitors, gates, plans, questions,
and pipes have no equivalent binding today.

## Motivating Evidence

### `bob-cli-dw.land`: concrete data loss

`bob-cli-dw` note #3 (2026-10-28, `sase bead read bob-cli-dw`) is the smoking gun:

> The B6 plan asks the lander to /sase_plan-propose the next backlog epic as its
> final action. The lander found that every earlier chained lander's plan
> `status: done` edit was lost (backlog_batch_a1, b2–b5 all `status: wip` despite
> closed epics), consistent with a plan-propose handoff never committing the
> proposer's dirty edits. This turn holds a sase test fix (dv coverage regression)
> and nine plans-sidecar edits, so it ends with a final declaration to commit them,
> and the B7 successor proposal is deferred.

The lander chose correctly under today's rules (commit won, chain stalled) and
filed the bug (`bob-cli-e0`). The desired behavior — commit the test fix plus the
nine sidecar edits **and** propose B7 in the same turn — is impossible without this
change.

### `sase-1ou.land`: consistent pattern, weaker direct evidence

`sase-1ou` note #2 is a long landing triage (closed `sase-12f`, `sase-18t`, filed
`sase-1pd`/`sase-1pc`/`sase-1pe`/`sase-1pf`/`sase-1pg`, fixed a `sase-core`
contention regression, reopened phase `sase-1ou.4` as child epic `sase-1ou.6`).
It does not explicitly say "I needed to commit and propose in one turn." Its value
is as a second witness to the lander shape that keeps hitting the bug: a land turn
that simultaneously (a) holds committable verification/fix work and (b) needs to
propose follow-up plan structure. The B6 note is the proof; the 1ou note is the
generality argument. Do not cite 1ou as an independent reproduction.

## Critique of the Proposal

**What is right:**

- Using the existing commit finalizer instead of inventing a handoff finalizer is
  correct. A new finalizer type would duplicate obligation discovery, deferral
  adjudication (`declaration_deferrals.py`), baseline handling, and the
  `stitch create` execution path for no benefit.
- Requiring a declaration on every turn removes a real footgun and simplifies the
  mental model ("every turn declares; handoffs are not a way to dodge the commit
  question"). The intuition benefit claimed in the prompt is genuine.
- The practical benefit (commit + propose in one turn) is confirmed by B6.

**What is missing or risky:**

1. **Order is everything, and the proposal does not specify it.** Declare-then-handoff
   is the only viable order: handoff kills the runner, so handoff-then-declare is
   impossible, and declare-after-kill cannot run. The design must say this normatively
   and enforce it in the handoff commands (refuse stale/missing declarations while
   the agent is still alive), not merely document it.
2. **Removing the skip without adding the refusal reopens the same bug.**
   If `should_skip_finalizers` stops skipping but handoff commands do not validate,
   an agent that forgets to declare still hands off and the host must guess whether
   to commit (it cannot — there is no accepted payload). Fail closed at the handoff
   boundary, mirroring `refuse_finalizer_owned_monitor_start()`
   (`src/sase/monitor/start_flow.py:72-80`) and `finalizer_owned_turn_refusal()`
   (`src/sase/finalizers/owned_turn.py`).
3. **Host execution order must be commit-before-successor.** Today the host treats a
   pending marker as "skip finalizers." The new host must treat
   "accepted submission + pending marker" as "run finalizers to fixed point, then
   adopt the handoff." Commit failure must block or explicitly defer the successor
   launch; launching a plan-approval gate or monitor `--next` agent on top of an
   uncommitted tree repeats the B6 loss.
4. **Scope should cover all five handoffs, not just gates/plans/monitors.**
   Questions and pipes kill the same way (`questions_command_handler.py:86`,
   `pipe_handler.py:287`). Leaving them exempt preserves the bug for two more paths
   and forces agents to remember which kills require declarations. Uniformity is
   cheaper to teach.
5. **Auto and terminal paths need explicit handling.** `%auto`-resolved gates still
   create the gate shell but skip the kill when already terminal
   (`gate_turn/agent_handoff.py:40-42` returns `False` when `record.is_terminal`
   after clearing intent). Under the new rule those turns still declare (usually a
   clean-tree no-op). Terminal-gate and replayed-monitor (`existing monitor`
   returns) paths must not double-require or double-commit.
6. **Cost is real but acceptable.** Every handoff turn gains a `sase final context`
   read and usually a `submit` roundtrip plus host commit execution. That is the
   price of not losing edits; it is small relative to a lost land turn. The readout
   classifier (`instructions/readout.py`), the `sase_final` / `sase_monitor` /
   `sase_plan` / `sase_gate` skills, and the decision notes
   (`host-owned-completion`, `gates-never-block`, `single-turn-agents`) all need
   updating so the new required-declaration turns are not scored as misses.
7. **Do not conflate this with prepared verification.** The `verify -f` path adds
   intent-sealing, accept-policy (`pass` vs `no-new`), receipt rechecks, and
   recovery-agent semantics. General commit+propose and commit+gate do not need
   verification gating — they need plain unconditional commit-then-handoff. Reuse
   the binding pattern, not the verification policy.

## Adjustments to the Requirements

1. State the order: declaration first, handoff second, host runs commit before
   successor. Make this a MUST, not a recommendation.
2. Extend the scope to questions and pipes (all `pending_handoff.py` markers), with
   the same declare-then-handoff rule.
3. Add fail-closed handoff validation: each turn-ending command refuses (nonzero
   exit, no marker, no kill) when `sase final context` shows `submission_required`
   but `final_submission_is_current()` is false. Emit the exact repair command.
4. Keep `builtin@commit` unchanged; no new finalizer type, no new provider ref.
   The "teach commit that empty is okay" bullet should be struck — it already holds.
5. Define the dirty-tree commit-failure policy: failed commit blocks the handoff
   (agent repairs and retries the handoff command); it never silently proceeds.
6. Define `bead_action` semantics for handoff turns: handoff turns are intermediate
   by definition — default `keep` unless the turn genuinely completes the assigned
   bead, and document that `close` on a plan-proposal turn is almost always wrong.
7. Update the three decision records (`host-owned-completion` exemptions paragraph,
   `gates-never-block` cost paragraph, `single-turn-agents` mechanism list) and the
   four skills rather than landing code with stale docs.

## Recommended Solution

### Phase 0 — Docs-only contract (lands the mental model)

- Amend `sase_final.md`: delete the "successfully executed handoffs … are exempt"
  line; replace with "handoffs never exempt a declaration — declare first, then
  hand off."
- Amend `sase_plan.md` step 6, `sase_monitor.md` hazards, `sase_gate.md` with the
  same two-line ordering rule and the refusal behavior.
- Amend `memory/decisions/*` (via `/sase_memory_write`): the exemptions exist
  because the runner dies, not because the work needs no commit.

### Phase 1 — Handoff-side refusal (fail closed while agent is alive)

Add a shared guard, e.g. `require_current_final_declaration(command)` in
`src/sase/finalizers/declaration.py` alongside `final_submission_is_current()`:

- If no `SASE_AGENT` / no `SASE_ARTIFACTS_DIR`, return (host-owned and non-agent
  callers unaffected).
- Publish-or-read context; if `submission_required is false`, allow.
- Else require `final_submission_is_current()`; on false, exit nonzero with:
  `run 'sase final context', submit the manifest, then retry <command>`.

Call it at the top of `plan_propose_handler`, `monitor/start_flow.py:start_monitor`
(next to `refuse_finalizer_owned_monitor_start`), `gate_turn` creation, and the
questions/pipe handlers — before any marker write, claim move, or proc submit, so a
refusal leaves no partial state (the same atomicity `start_flow.py:72-80`
already guarantees for finalizer-owned turns).

### Phase 2 — Host runs finalizers despite pending handoff

- Change `should_skip_finalizers()` / `controller_run.py` to skip only when there
  is a pending handoff **and** no accepted-current submission covering a
  submission-required context. When both exist, run the normal controller to fixed
  point first, then let the runner adopt the pending marker.
- Settlement order: commit execution → handoff adoption → successor launch. On
  commit failure, mark the handoff `stopped`/`failed` with reason
  `finalizer_commit_failed` and launch recovery rather than the recorded `--next` /
  gate-branch successor (reuse `failed_close_recovery` coordination in
  `controller_run.py:run_finalizers`).
- Keep the `finalizer-owned turn` refusal (`owned_turn.py`) intact: finalizer
  executors themselves still cannot hand off; only the agent turn declares then
  hands off.

### Phase 3 — Readout and metrics

- Update `src/sase/instructions/readout.py` classes: a handoff with a
  current accepted submission (or a not-required context) stays in its handoff
  class; a handoff with no declaration becomes a miss. Otherwise the new required
  behavior is unscored.
- Add a counter for handoff refusals (`handoff_declaration_refused`) so prompt
  compliance is observable.

### What deliberately does not change

- No new finalizer type or provider ref. No change to
  `build_context_requirements()` dirty-vs-clean logic.
- No change to `kill_agent_runner_group()` mechanics — the kill still happens, only
  later (after declaration) and with a validated commit behind it.
- Prepared `verify -f` monitors keep their verification-gated semantics; plain
  commit-then-handoff does not gain an accept policy or receipt requirement.

### Rollout risk and mitigation

- Risk: agents trained on the old exemption will hand off without declaring and
  hit the new refusal. Mitigation: the refusal message must contain the verbatim
  fix (`sase final context -f json` → submit → retry), and skills must show the
  order. Consider a one-release warn-then-refuse (log `handoff_without_declaration`
  but proceed) only if refusal rates spike; default to refuse because warn-mode
  reintroduces B6 data loss.
- Risk: double-commit on replayed monitor starts or terminal gates. Mitigation:
  the idempotency is already in `final_submission_is_current()` (digest + host
  records + deferral adjudication); handoff replay paths must recheck rather than
  resubmit.
- Risk: claim/ownership race between commit executor and monitor/gate member
  creation. Mitigation: commit runs before claim transfer (Phase 2 order); the
  existing `start_claim.py` / `gate_turn/start_claim.py` moves happen after the
  controller settles.

## Open Questions for the Lead

1. Should `sase final prepare -f` binding be extended beyond `verify` monitors to
   plan proposals and gates (a sealed "commit unconditionally, then hand off"
   intent), or is the two-command declare-then-handoff sequence sufficient? I
   recommend the latter first; sealing adds little when no verification gates the
   handoff.
2. Should questions/pipes be in scope for v1, or gates+plans+monitors only? I
   recommend all five for uniformity, but if scope must be cut, cut pipes last —
   pipes carry the same file-edit payload risk.
3. What is the intended `bead_action` on a turn that both lands work and proposes
   the successor epic? I recommend `keep` (the successor owns closure), documented
   explicitly, to avoid premature bead close.

## Sources Consulted

- `src/sase/agent/pending_handoff.py`, `src/sase/turns/handoff.py`,
  `src/sase/monitor/handoff.py`, `src/sase/gate_turn/agent_handoff.py`,
  `src/sase/main/plan_propose_handler.py:454-490`, `src/sase/main/utils.py:60-...`
- `src/sase/finalizers/controller_context.py`, `controller_run.py`,
  `declaration.py`, `declaration_store.py`, `declaration_manifest_io.py`,
  `owned_turn.py`, `_prepare_completion.py`
- `src/sase/llm_provider/commit_finalizer_state/__init__.py:collect_dirty_state`
- Skills `sase_final.md`, `sase_monitor.md`, `sase_plan.md`, `sase_gate.md`
- `sase memory read glossary:gate/monitor/receipt/stitch`,
  `glossary:macro/sase-turn/sase-agent`, `decisions:host-owned-completion`,
  `decisions:gates-never-block`, `decisions:single-turn-agents`
- Beads `bob-cli-dw` (notes #1–#3) and `sase-1ou` (notes #1–#2) via
  `sase bead read`
