# Ending handoff turns through host completion instead of killing the agent

_Researcher: cld · 2026-10-28 · sase master `a2fbbc3b9d`_

## TL;DR

- **Yes, killing the agent on a handoff was a mistake, and it is now costing real work.**
  A handoff kills the runner from inside a tool call, and the finalizer controller then
  skips itself when it sees the pending marker. So any edit the agent made before the
  handoff is either inherited by a same-workspace successor or silently discarded when
  the workspace is reused. I confirmed three cases from the last day alone, including a
  bead (`sase-1p6`) that was closed as fixed even though its fix never reached any
  commit (§2.1).
- **Handoffs are now the common way a turn ends, not the edge case.** Over the last two
  weeks about half of all recorded runs ended in one: 310 monitor, 207 plan, 19
  auto-approved epic, and 19 other gate handoffs, against 546 normal completions (§2.3).
- **Keep the direction, but change three parts of the proposal.**
  1. Use the existing declaration protocol and `builtin@commit` for the repository
     decisions. But run the handoff itself as a host continuation step _after_ the
     finalizers settle, not inside the commit finalizer. It must not be something
     `%final:none` or a trusted config can remove.
  2. **Reverse the relaxation for plans.** A turn that proposes a plan must commit (or
     formally defer) its dirty repositories, because no successor reliably inherits the
     tree. Leaving work uncommitted ("carry") is only safe for handoffs that resume in
     the same workspace (monitor, questions, pipe, and most gates). Even then, the carry
     should be a recorded disposition, not a silent omission.
  3. Cover all eight in-agent handoff entry points, not just plans and monitors.
     Otherwise SASE keeps two end-of-turn protocols indefinitely.
- **Recommended solution:** a turn _stages_ its handoff, ends normally through
  `/sase_final`, and the host then commits, adopts the staged handoff, and starts the
  successor. Roll this out behind one epic-scaffolding flag, plans first. Details are in
  §8.

---

## 1. How it works today

### 1.1 The kill path

Every in-agent handoff ends the same way:

1. The handoff command writes a pending marker into `$SASE_ARTIFACTS_DIR`. There are
   five: `.sase_plan_pending`, `.sase_questions_pending`, `.sase_monitor_pending`,
   `.sase_gate_pending` and `.sase_pipe_pending`.
2. The command then calls `kill_agent_runner_group()` (`src/sase/main/utils.py:60`),
   which sends SIGTERM to the runner's whole process group. The provider dies in the
   middle of the tool call.
3. Back in the runner, `_invoke.py` still calls `run_finalizers()`. But
   `should_skip_finalizers()` (`src/sase/finalizers/controller_context.py:41`) returns
   true whenever a pending marker exists, so **the commit finalizer never runs** and
   only a "handoff skip" entry is journaled.
4. `_handle_killed_iteration()` (`src/sase/axe/run_agent_exec.py:154`) reads the marker
   and dispatches to `handle_plan_marker`, `handle_questions_marker`,
   `handle_monitor_marker`, `handle_gate_marker` or `handle_pipe_marker`. These handlers
   create the plan gate turn, adopt the monitor member, and so on. Because the model's
   final reply never arrived, they write a **synthetic response** to the chat
   transcript. The code says so: "the LLM response was lost to SIGTERM, so we use a
   plan-file preview as the synthetic response" (`src/sase/axe/run_agent_exec_plan.py:191`).

The `/sase_final` skill makes the matching exemption explicit: "Only a successfully
executed plan, monitor, pipe, or questions handoff is exempt". So does decision record
`host-owned-completion`.

### 1.2 Which commands hand off

The Codex adapter lists eight in-agent handoff entry points
(`src/sase/llm_provider/_subprocess_codex.py:259`): `monitor start`, `plan propose`,
`pipe`, `questions`, `gate create`, `sudo request`, `launch request`, and `run`. They
fall into two groups, and the difference matters for implementation:

| Group                                    | Commands                                                                                  | Where the side effect happens                                                                                    |
| ---------------------------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **A – marker only**                      | `plan propose`, `questions`, `pipe`                                                       | The CLI validates and writes the marker. The runner does the real work (gate creation, successor) after the kill |
| **B – side effect first, then the kill** | `gate create`, `sudo request`, `launch request` / `run`, workflow HITL, `monitor start` | The CLI creates the gate or spawns the monitor supervisor, moves the workspace claim, _then_ kills               |

For group A, "stop killing" is close to a deletion: the runner already adopts the marker
after the point where finalizers would have run. Group B needs its creation step split
into a stage step and a publish step.

### 1.3 What happens to a dirty tree after a handoff

Continuations that stay in the same workspace inherit the predecessor's commit
responsibility through `inherit_commit_finalizer_responsibility()`
(`src/sase/llm_provider/commit_finalizer_inheritance.py:33`). Its docstring says the
parent's uncommitted work becomes the successor's own responsibility to commit. So
"carry the dirty tree forward" is already the de-facto model for monitors, questions,
pipes, and tale coders. The plan gate turn uses `"workspace": "inherit"`
(`src/sase/plan_gate_turn/create.py:41,61`).

But carrying only works when a successor actually exists on the branch that runs:

| Handoff                     | Branches with a same-workspace successor           | Branches where nothing inherits the tree                                                                         |
| --------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Tale plan                   | approve(+commit) → coder; feedback → replanner     | reject, timeout, cancel, commit-only ("PLAN COMMITTED")                                                          |
| **Epic plan**               | feedback → replanner                               | **approve**: phase agents launch in _other_ workspaces, and this workspace is released. Also reject and timeout |
| Monitor                     | completed / failed / timeout → follow-up           | stopped, lost; prepared completion invalidated with no recovery                                                  |
| Questions                   | answered → successor                               | cancel, timeout                                                                                                  |
| Custom / sudo / launch gate | depends on the gate's branch policy                | denied, terminal branches, timeout                                                                               |

When nothing inherits the tree, the claim is released and the next agent to claim that
workspace resets it. The epic-approve case is the worst, because it is the _successful_
path.

---

## 2. Evidence

### 2.1 Work lost in the last day

1. **`sase-1ou.land` (sase, 2026-10-28).** This lander fixed two sase-core problems
   (flaky contention tests in `contention.rs`, and a product regression in
   `connection.rs` where a slow quarantine returned "busy" with nothing holding the
   lock). It also edited the sase flake baseline, closed `sase-1p6` as done, and then
   proposed child epic `sase-1ou.6`.
   - Its `agent_meta.finalizer_status.phase` stayed `planned`, and `commit_results.json`
     lists only bead-store commits.
   - sase-core `origin/master` has nothing after `ed8328f9` (12:31 EDT), and this
     workspace (`sase_20`, the same one that lander used) has a clean sase-core
     checkout. **The fix is gone.**
   - The chat transcript's `## Response` section is empty, because the SIGTERM ate the
     reply. The real summary exists only in `live_reply.md`.
   - _Action taken:_ I +1'd `sase-1p6` with this evidence, and it reopened to READY. I
     also added a `DISCOVERED ISSUE:` note on epic `sase-1ou` so its eventual lander does
     not trust the landing triage's claim that it was fixed.
2. **`bob-cli-dp.land--code` (bob-cli, 2026-10-28).** This coder edited
   `src/sase/sdd/_link_files.py`, `src/sase/scripts/validate_committed_plans.py` and a
   new `tests/sdd_store/test_nested_repo_open_sdd_root.py` in an opened sase checkout
   at 14:36 EDT, plus a plans-sidecar status edit, then ended by proposing epic B6.
   - The finalizer never ran (`phase: planned`), and no sase commit touches those paths
     after 14:12 EDT.
   - _Likely lost._ Some of the edits may have been exploratory; I did not confirm their
     intent.
3. **`bob-cli-e0` (filed by `bob-cli-dw.land`).** Five consecutive backlog-chain
   landers (a1, b2–b5) each lost their plan `status: done` edit the same way.
   `bob-cli-dw.land` diagnosed it and deliberately _did not_ propose B7, so that its own
   test fix would get committed. That decision stalled the chain.

**Related symptom on the monitor side:** `sase-1o0` asks for a warning when a monitor
starts with a dirty workspace and a `--next` that waits on master. Such a follow-up
waits on a SHA that cannot exist until someone commits the work. Committing _before_
starting a wait monitor is exactly what the proposal enables.

### 2.2 What the kill path has cost in engineering

Most of these exist only because the turn is ended by a signal from inside a tool call:

- `handoff_inflight.py`: in-flight markers, plus a bounded wait to adopt a late handoff
  or record an aborted one (`sase-18e.3`, `db337969b9`).
- Codex stranded-handoff recovery: `_is_sase_handoff_command`,
  `stranded_handoff_continuation_nudge` (`6a9bac885f`). Codex's yielding
  `exec_command` returns control after about 30 s while the command keeps running.
- Lost-gate-intent adjudication and the 60 s creator wait (`491daa988a`).
- `sase monitor start` latency work. It must finish inside the harness tool budget,
  print to stderr before slow work, and use a double-fork so the supervisor survives the
  kill. That took the start from 20–40 s down to under 1 s ("A start is fast, and never
  silent" in `docs/reference/automation/monitors.md`).
- Workspace-release special cases. The SIGTERM claim release skips pending markers
  (`run_agent_runner_signals.py`), and `release_vcs_workspace` refuses on a pending
  handoff (`vcs_release.py:72`).
- `kill_agent_runner_group()` exists because Claude Code puts Bash in an isolated
  process group (`fc8235db0e`), so killing our own group never reached `claude`.
- Synthetic chat responses for plans, monitors and gates.

### 2.3 How often turns end in a handoff

I scanned `done.json` for `ace-run` artifacts in 2026-10 modified since 2026-10-14,
across all projects (1,103 runs; approximate, and only this workflow layout):

| Outcome              | Runs | Notes                                             |
| -------------------- | ---: | ------------------------------------------------- |
| completed            |  546 | normal `/sase_final` path                         |
| monitored            |  310 | monitor handoff                                   |
| gated                |  226 | tale plan 129, epic plan 78, custom 9, question 6, sudo 4 |
| epic_approved        |   19 | plan auto-approved inline                         |
| failed               |    2 |                                                   |

About 50% of turns end in a handoff. Monitors are the largest group, so any per-turn
friction added to monitor turns needs to be close to zero (§5, adjustment 3).

---

## 3. Is this a good idea?

**Yes.** The kill was a reasonable shortcut when handoffs were rare and planners did not
edit code. Today three things have changed:

- landers and coders routinely make real edits before proposing a successor plan;
- monitors are the most common way a turn ends;
- the kill path has grown a family of race and recovery patches.

Moving the end of turn into host completion fixes the data-loss class at its root. It
gives every turn a real final response, and it lets the provider exit normally on every
harness instead of being shot mid-tool-call.

What the kill does buy, and what you give up:

1. **A hard mechanical stop.** Today nothing the agent does can happen after the
   handoff. With staging, the agent could keep working. That is mostly harmless: a
   staged monitor would just verify the _final_ tree, which is better. It does need two
   guardrails: refuse a wait on your own staged handoff, and refuse a second staged
   handoff.
2. **Immediate release of the runner slot.** With staging, the slot is held through
   finalization (commit, `before` hook, push) like any other turn. A plan gate may
   appear a minute later than today. That is acceptable for human-scale decisions.
3. **Independence from model compliance.** With staging, the handoff only takes effect
   if the turn ends. But SASE already depends on the model ending its turn through
   `/sase_final`, and it already has a bounded declaration-recovery turn for when it
   does not. A staged handoff simply waits for that recovery.

None of these outweighs the lost work. The decision records the kill came from
(`gates-never-block`, `single-turn-agents`) are about _not waiting_. They stay true
under staging: the agent still never blocks, and continuation is still mechanical. Only
the clause about how the turn ends changes.

### Would I take a different approach?

Not a different direction, but a different placement for the handoff. I considered four
designs:

| Option                                                        | What it is                                                                                                                                                                                                 | Verdict                                                                                                                                                                                                                                                                                                                         |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **0. Guardrail only**                                         | `plan propose` warns or refuses while owned repos are dirty (`bob-cli-e0`'s "expected" alternative)                                                                                                       | Stops silent loss, but makes commit-and-plan _impossible_, because agents may not commit directly. It pushes landers into `bob-cli-dw.land`'s choice: drop the plan or drop the commit.                                                                                                                                         |
| **M. Declare, then kill**                                     | The agent runs `/sase_final` submit, _then_ the handoff command. `should_skip_finalizers` stops skipping when a current submission exists, so finalizers run before marker adoption (that order already holds in `_invoke.py`) | Small for group A, and a credible stopgap for plans. Wrong for group B: a monitor or gate created before the kill would run concurrently with the commit finalizer (`just check` racing `before: just fix` and the push). Also keeps every cost in §2.2, including the lost final response. |
| **F. Handoff as a finalizer** (`builtin@handoff`, `required`) | The commit finalizer, or a sibling instance, performs the handoff                                                                                                                                         | Finalizers are a trusted, configurable, retryable selection: `%final:none`, `required`, `after`, `max_attempts`, plugin providers. A handoff is not optional and not retryable in that sense. A `%final:none` turn that proposes a plan must still propose it. It also blurs `builtin@commit`'s single job.                  |
| **S. Stage, declare, then the host adopts** (recommended)     | Handoff commands _stage_. The turn ends normally via `/sase_final`. The host runs finalizers to their fixed point, then adopts the staged handoff with the existing `handle_*_marker` code             | Fixes the loss class, gives a real final response, and retires the kill machinery. Larger, but group A is cheap and is delivered first.                                                                                                                                                                                        |

---

## 4. The proposal, point by point

| Your point                                                                    | Assessment                                                                                                                                                                                                                                                       |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Require a finalizer for gates and monitors instead of killing                 | **Agree**, phrased as: the turn ends through _host completion_ (declaration plus finalizers); the handoff is adopted after it.                                                                                                                                   |
| Use the existing commit finalizer                                             | **Agree for repository decisions.** Use the same declaration, context digest and `builtin@commit`. **Disagree for handoff execution**; see option F above.                                                                                                       |
| All turns must submit a final declaration                                     | **Adjust:** every root turn _runs_ `/sase_final`; a manifest is required only when the context has decision-requiring obligations (unchanged rule).                                                                                                             |
| The commit finalizer accepts that plan and monitor turns may not commit       | **Split it.** Plans: _require_ commit, the opposite of the proposal, because that is the bug. Monitors and same-workspace handoffs: allow a recorded **carry** disposition.                                                                                       |
| Benefit: intuitive                                                            | Agree. One end-of-turn protocol instead of "declare, unless you ran one of five commands".                                                                                                                                                                       |
| Benefit: commit and propose in one turn                                       | Agree, and the evidence is stronger than the two agents cited (§2.1). It also gives commit-then-wait monitors (`sase-1o0`).                                                                                                                                      |

---

## 5. Changes to the requirements

Each of these departs from, or adds to, what you asked for:

1. **"Every turn submits a declaration" becomes "every root turn runs `/sase_final`".**
   A clean-tree monitor turn should not have to author a manifest. The context reports
   `submission_required: false` and the skill returns, as it does today.
2. **Plans must commit; they may not carry.** For `plan propose` (tale and epic), every
   dirty repository obligation needs a `commit` decision or an adjudicated `defer`.
   Epic approval moves to other workspaces, and reject, timeout and commit-only release
   the claim, so carried work would be lost on the very paths that matter. Committing
   first also gives epic phase agents the lander's fixes on master. Open question for
   PR-mode projects in §9.
3. **"May skip the commit" becomes an explicit `carry` disposition, defaulted by the
   host.**
   - Carry is legal only when the staged handoff resumes in this workspace: monitor,
     questions, pipe, and gates whose turn block inherits the workspace.
   - The final context marks those obligations `carry_allowed` and pre-fills the
     template with `carry`. When _every_ obligation is carry-allowed,
     `submission_required` is false, so 310 monitor turns per two weeks pay one
     `sase final context` call and nothing more.
   - The agent can still mix decisions per repository, for example commit a sidecar and
     carry the primary repo.
   - The run view records `carried → <successor>`, so it is auditable.
   - An explicit disposition keeps sase-core's "exactly one decision per obligation"
     invariant, and makes "forgot to commit" distinguishable from "chose to carry".
4. **The handoff runs after the finalizer fixed point, as a host step.** It is not a
   finalizer instance and cannot be configured away. Ordering: finalizers settle →
   adopt the handoff → successor.
5. **If finalization fails, the handoff fails closed.** A failed commit (after
   conflict repair) means the staged handoff is _not_ adopted: no plan gate, no
   monitor. The run fails with `handoff_not_adopted`, keeps the staged record, and the
   notification names a re-adopt command. An upheld deferral (`refusal: defer`) is an
   accepted completion, so the handoff proceeds.
6. **Scope covers all eight entry points.** Ship them in phases (§8), but plan for all
   of them, or two protocols survive.
7. **Validate at stage time.** Everything that can be checked while the agent can still
   fix it must fail at stage time: plan validation (already done), monitor argv,
   profile and intent binding, the lane lock, gate spec validation. Adoption-time
   failures go to a recovery turn.
8. **Terminal branches never silently drop carried work.** When a carried tree reaches
   a branch with no successor (stopped or lost monitor, cancelled question, terminal
   gate branch), the host holds the workspace instead of releasing it, and raises the
   existing stranded-work flag. This also closes a loss path that exists today.

---

## 6. Detailed design (option S)

### 6.1 The turn-end protocol

```
agent work ─► stage handoff ─► /sase_final ─► final reply ─► provider exits normally
                (validate, write            (context shows the handoff;
                 staged marker; no kill)     commit / carry / defer per repo)
host:  run_finalizers to fixed point ─► adopt staged handoff ─► successor / gate / monitor
                │ failure
                └─► run fails "handoff_not_adopted"; staged record kept; notify
```

Rules for the agent:

- At most one staged handoff per turn (the existing `handoff_guard` refusal stays).
- Staging after a successful submit is refused: _stage first, then declare_. This
  avoids a stale-submission dance. The context digest covers the staged handoff in any
  case.
- `sase monitor wait`, `sase gate wait` and similar calls on your own staged handoff
  are refused with "it starts after your turn ends; finish with `/sase_final`".
- Turn-ending handoffs stay refused in finalizer-owned recovery and repair turns
  (`_refuse_finalizer_owned_handoff`). A recovery turn only completes the declaration;
  the already-staged handoff is adopted after it.

### 6.2 Wire changes (sase-core, required by `rust_core_backend_boundary`)

- `FinalizerContextWire` gains `handoff: {kind, staged_ref, successor_workspace:
  inherit|none, carry_allowed}`. It is included in `context_digest`, so staging always
  invalidates an older submission.
- The repository decision vocabulary gains `carry`, legal only when
  `handoff.carry_allowed`. The host synthesizes `carry` decisions when the agent
  submits nothing and every obligation is carry-allowed.
- A prepared completion bound to the staged monitor (`sase final prepare` plus
  `monitor start -f`) satisfies the declaration. The context reports
  `submission_required: false, disposition: prepared`, and the commit still happens
  after the monitor passes, unchanged.
- Bump `sase-core-revision.txt` past the sase-core commit (see `docs/rust_backend.md`).

### 6.3 Runner changes (Python)

- `should_skip_finalizers()` no longer skips for a _staged_ marker. Killed-mode markers
  keep the old behaviour while the flag is off.
- After `run_finalizers()` returns on a normal (not killed) iteration, the execution
  loop checks `pending_handoff_kind()` and calls the existing `handle_*_marker`. The
  handler receives the **model's real final response** instead of the synthetic one;
  keep the plan preview as an extra section.
- Keep `done.json` outcomes (`gated`, `monitored`, …) so analytics and status buckets do
  not move. Keep the `postprocessing.py:124` notification suppression so the turn does
  not send both an "agent done" and a "plan ready" notification.
- Claim movement (`gate_handoff_claim_moved`, `monitor_handoff_claim_transferred`) now
  happens while the runner is alive and on its normal shutdown path. That is simpler
  than the SIGTERM handler's marker exceptions.

### 6.4 Per entry point

| Entry point                                           | Stage step (CLI, agent alive)                                                                                                       | Adopt step (runner, after finalizers)                                    | Repository policy                                            |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------ |
| `plan propose`                                        | Unchanged validate, format and archive; write marker; **no kill**                                                                  | `handle_plan_marker` → plan gate turn (already the case)                 | commit / defer only                                          |
| `questions`                                           | Unchanged; no kill                                                                                                                  | `handle_questions_marker`                                                | commit or carry                                              |
| `pipe` / `/sase_handoff`                              | Unchanged; no kill                                                                                                                  | `handle_pipe_marker`                                                     | commit or carry                                              |
| `gate create`, `sudo request`, `launch request`/`run`, workflow HITL | Validate the spec and evaluate `%auto`. **If it auto-resolves, keep today's inline result (no handoff)**; otherwise write a staged spec | Create, publish and move the claim, then `handle_gate_marker`            | commit or carry, when the gate inherits the workspace         |
| `monitor start`                                       | Preflight: argv, profile, ToolRun reservation policy, completion-intent binding (reserve, not consume), lane lock, `--mon` suffix   | `start_monitor` spawn and ack, then `handle_monitor_marker`              | commit, carry, or prepared                                   |

Moving the monitor spawn out of the harness tool call into the runner removes the
"finish inside Codex's ~30 s yield" constraint. The supervisor still has to detach,
because the runner exits, but there is no longer a race against a SIGTERM aimed at the
caller.

### 6.5 Failure semantics

| Situation                                                     | Behaviour                                                                                                              |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Handoff staged, declaration missing, all carry-allowed        | Host synthesizes carry and adopts                                                                                      |
| Handoff staged, declaration missing, commit required (plan)   | Existing one-shot declaration recovery turn, then adopt                                                                |
| Finalizers fail                                               | Do not adopt; run fails `handoff_not_adopted`; staged record kept; notification gives the re-adopt command             |
| Upheld deferral (`refusal: defer`)                            | Adopt; run status `deferred`                                                                                           |
| Provider crashes or times out after staging                   | Same as a missing declaration: recovery turn, then adopt. A **user kill** discards the staged handoff (as today)       |
| Adoption itself fails (monitor spawn, gate publish)           | Run fails with the adoption error. Carried work stays in a _held_ workspace with a stranded flag; never released silently |

---

## 7. Instructions, skills, memory and decisions to update

- `/sase_final`: drop the exemption text in the description and in the "Successfully
  executed handoffs…" bullet. Add a short section: "If you staged a handoff, the
  context shows it; plans need commit decisions; same-workspace handoffs may carry."
- `/sase_plan`, `/sase_monitor`, `/sase_questions`, `/sase_handoff`, `/sase_gate`,
  `/sase_sudo`, `/sase_run`: change "this ends your turn" to "this stages the handoff;
  then run `/sase_final` and end your turn. Nothing starts until you do." These are
  generated skills; follow `generated_skills.md`.
- AGENTS.md "SASE Final Declaration" and the Claude single-turn text: remove "Only a
  successfully executed plan, monitor, pipe, or questions handoff is exempt."
- Land prompts: delete the workaround text ("The tale's coder commits only after its
  turn ends, so the closeout must never wait for…") once commit-before-plan is real.
- Decision records (through `/sase_memory_write`): a new record, roughly "Handoffs End
  Through Host Completion", that **partly supersedes**:
  - `gates-never-block` (the "kills the creating agent's turn immediately" clause);
  - `single-turn-agents` ("terminates the runner");
  - `host-owned-completion` (the mechanical-exemption sentence);
  - `helpers-return-roots-declare` (the turn-ending CLI list stays, but staging
    commands are added as root-only).

  Glossary strands `gate_turn` and `sase_monitor` say "hands off and kills that agent's
  turn" and need the same update.
- Root-only guard: the staging commands remain turn-ending operations for the PreToolUse
  helper guard.

---

## 8. Recommended solution

Adopt **option S, staged handoffs ended through host completion**, with the
adjustments in §5. Deliver it as one epic behind a `beta` epic-scaffolding flag (for
example `staged_handoffs`), created with `sase flag new` and removed at land, in this
order:

1. **Core wire.** Add the `handoff` context descriptor, the `carry` disposition, the
   prepared-disposition rule, the digest coverage, and the validation tests; bump the
   pin.
2. **Runner adoption path.** Make `should_skip_finalizers` stage-aware; adopt after the
   finalizer fixed point with the real final response; implement the failure semantics
   of §6.5; test both flag states.
3. **Plans.** `plan propose` stages; commit is required; update the `/sase_final` and
   `/sase_plan` skills. _This alone fixes `bob-cli-e0`, the `sase-1ou` loss, and the
   backlog-chain stall, and it is the cheapest slice, because the runner already adopts
   plan markers after the point where finalizers run._
4. **Questions and pipe.** Stage them; carry by default.
5. **Gates** (`gate create`, `sudo`, `launch request`/`run`, workflow HITL). Split
   creation into stage and publish; keep the `%auto` inline path.
6. **Monitors.** Split `start_monitor` into preflight and spawn; integrate prepared
   completion; make "commit, then wait on CI" a documented pattern (this resolves
   `sase-1o0`'s motivating case).
7. **Terminal-branch hardening.** Hold the workspace and raise the stranded flag when
   carried work has no successor.
8. **Land.** Remove the flag; delete the kill path and the coping code from §2.2 that
   no longer has a caller (in-flight markers, Codex stranded-handoff nudge, synthetic
   responses, SIGTERM marker exceptions); update the docs, the glossary and the
   decision records.

**Checkpoint after step 3:** if monitor turns turn out to need much heavier
preflight/spawn surgery than expected, it is defensible to ship steps 1–5 and leave
monitors on the kill path for a while. Monitors already carry dirty trees safely on
their non-stopped branches. But keep the flag open until monitors move, so the exemption
text does not become permanent.

**If step 3 cannot start soon,** option M for plans only is a small stopgap: allow
`/sase_final` submit before `sase plan propose`, and let finalizers run when a current
submission exists. Only do this if the epic is weeks away, because it teaches agents a
transitional protocol they will have to unlearn.

---

## 9. Open questions and risks

- **PR-mode projects.** When `builtin@commit` creates a PR instead of pushing to master,
  epic phase agents will not see a lander's pre-plan commit. Should epic approval wait
  for the PR to merge, or should phase agents branch from the PR branch?
- **Plan feedback rounds.** The replanner inherits the workspace and its committed base.
  Is "plans must commit" too strict for a planner that deliberately keeps a half-done
  spike in the tree? I recommend no carry for plans, with `defer` as the escape hatch,
  but you may prefer `carry` for tale plans whose approve and feedback branches both
  inherit, with terminal-branch holding (§5, item 8) as the safety net.
- **Gate latency.** Human gates will publish after the commit finalizer, which with
  hooks and a push can take a minute or more. Publishing early but holding the
  follow-up is possible, but it reintroduces concurrency with the commit; I would not
  do it initially.
- **Model habits.** Agents trained on "the handoff ends your turn" may keep going, or
  try to wait. The wait-refusal guard and clear CLI output ("staged; nothing starts
  until you end your turn") cover most of this; declaration recovery covers the rest.
- **Measurement gap.** My handoff counts cover the `ace-run` layout only, and I could
  not reliably measure how many handoff turns were dirty at handoff time, because
  provider tool logs differ (Bash `sed -i`, Codex `apply_patch`). A one-line host log
  of "dirty obligations at handoff" during the flag period would answer it.

## Appendix: key source references

- Kill: `src/sase/main/utils.py:60` (`kill_agent_runner_group`),
  `src/sase/turns/handoff.py` (`maybe_handoff_turn_from_agent`).
- Finalizer skip: `src/sase/finalizers/controller_context.py:41`; finalizer invocation
  at `src/sase/llm_provider/_invoke.py:~455`.
- Marker adoption: `src/sase/axe/run_agent_exec.py:154`, `run_agent_exec_plan.py`,
  `run_agent_exec_monitor.py`, `run_agent_exec_gate.py`.
- Dirty-tree inheritance:
  `src/sase/llm_provider/commit_finalizer_inheritance.py:33`; plan gate
  `"workspace": "inherit"` at `src/sase/plan_gate_turn/create.py:41,61`.
- Group-B creators: `src/sase/main/gate_handler.py:95`, `src/sase/sudo/cli.py:190`,
  `src/sase/agent/launch_request.py:200`, `src/sase/macro/workflow_hitl_gate.py:102`,
  `src/sase/monitor/handoff.py`.
- Prepared completion: `docs/reference/automation/monitors.md` ("Prepared host
  completion"), `src/sase/monitor/host_completion_execute.py`.
- Evidence beads: `bob-cli-e0`, `bob-cli-dn`, `sase-1o0`, `sase-1p6` (reopened by this
  research), `sase-1ou` (DISCOVERED ISSUE note added).
