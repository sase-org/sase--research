---
create_time: 2026-10-16
updated_time: 2026-10-16
status: draft
tags:
  [
    research_swarm,
    id-directive,
    beads,
    agent-launch,
    relaunch,
    tui,
    sase-core,
  ]
---

# Allow `%id(..., bead=<closed>)` launches, with an audit trail

**Question.** Should SASE let an agent launch with `%id`'s `bead=<bead>` even when
that bead is already `closed`, so `,x` / `sase agent restart` can recover a failed
run whose agent or finalizer already closed the bead? Add a recognizable,
timestamped note or annotation when that happens. Critique the plan. Adjust
requirements that would make the feature surprising or unsafe. Recommend a
design.

**Researcher.** grk (`research.4n.grk`). Independent report. I did not locate,
open, read, or otherwise consult peer reports from this swarm.

## Bottom line

**Yes, stop failing the launch.** The motivating workflow is real: `,x` on the
Agents tab rewrites the stored prompt, keeps `bead=`, and then the runner's
just-in-time launch claim dies with `closed: cannot claim closed bead`. That
guard is deliberate (there is an integration test named for it), and it is
the wrong guard for a human relaunch of the same implementer.

**Do not reopen the bead.** That is the load-bearing requirement change.
Reopening on launch would archive close history, reopen closed ancestors,
flip lists and `↺N` badges, and collide with task `+1` / `TaskTriage`
reopen rules. The user asked to make the launch *fine* and to leave an audit
trail. Keeping `closed` and appending a structured note does both.

Recommended contract:

1. `%id(..., bead=<id>)` still binds `SASE_BEAD_ID` and `agent_meta["bead_id"]`.
2. When the bead is `closed` at promotion, skip the open→`in_progress` claim.
3. Append one attributed note with a stable prefix (`CLOSED-BEAD LAUNCH:`).
4. Tell the new agent the bead is already closed, so it does leftover work
   and treats `bead_action: close` as idempotent.
5. Keep every other closed-bead refusal: missing IDs, `in_progress` owned by
   someone else, epic preclaim of closed phases, `sase bead work` skipping
   closed phases.

The change belongs in the **launch-claim primitive** (sase-core, consumed by
the Python runner helper), because `,x`, `sase agent restart`, retry
handoffs, and auto-restart all reuse `bead=` and all die at the same call.

## Verdict on the idea

This is a good idea. I would ship it, with the keep-closed adjustment, rather
than a TUI-only special case, a new directive keyword, or an automatic
`sase bead open`.

### Why the request is justified

The failure is late and expensive. Directive parse accepts any
whitespace-free ID (`resolve_launch_bead_id` in
`src/sase/macro/_directive_values.py`). `SASE_BEAD_ID` is bound during
bootstrap (`src/sase/axe/run_agent_directives_prompt.py`). Wait-claim for a
closed own-bead already *declines* and continues (`claim_bead_for_waiting_agent`
prints `Bead … claim declined: status=closed` and returns false). The hard
error is `_promote_bead_claim` → `claim_bead_for_agent_launch` → Rust
`claim_for_agent_launch`, immediately before the model runs. A relaunch that
also has `%wait` can sit parked until every dependency clears, then die.

`,x` is designed to carry `bead=` across. From
`docs/reference/tui/agents-tab-modes.md`:

> An existing `bead=` value is carried across

The CLI twin is `sase agent restart NAME`. Force-reuse (`%id(!name, bead=…)`)
already has a closed-bead-shaped hole: it retains the association only when
the bead is still `in_progress` for the prior owner
(`issue_retains_force_reuse_owner` in `src/sase/bead/force_reuse.py`). A
closed bead fails that predicate, falls through to `claim_for_agent_launch`,
and raises.

The user's picture of "the agent or the finalizer has already closed the
bead" matches host completion: `bead_action: close` after a successful
commit is a real close, and a later stitch timeout, verification failure, or
runner crash still leaves a failed agent row whose prompt still has `bead=`.
Re-closing is already a verified no-op (`docs/beads.md`: "Closing a bead that
is already closed exits successfully"). The launch path is the one surface
that still treats "already closed" as fatal.

### Why the request as written is too broad

"Make it fine for an agent to be launched using `bead=<bead>` even when
`<bead>` is already closed" can be read as "treat a closed bead like an open
one and claim it." That reading is a bad idea.

`closed` is a product invariant, not a lock-file leftover:

- `sase bead work` retries skip closed phases and, when every phase is
  closed, launch only the land agent (`docs/beads.md`).
- Epic preclaim rejects closed targets (`preclaim target is closed` in
  `sase-core` `crates/sase_core/src/bead/mutation/claims.rs`).
- `%wait(bead=…)` means "until this bead is closed." Reopening a phase under
  a still-running land wait is mostly harmless because "once a wait
  releases, reopening does not re-park," but *new* waiters and unlaunched
  land segments would block again.
- `sase bead open` reopens the bead **and every closed ancestor**. A phase
  relaunch that reopened only the phase would leave an open child under a
  closed epic, which the close-never-cascades rule forbids in the other
  direction.
- Closed tasks reopen through `+1` with an observation window and
  `--verified-after-close`. Automatic reopen on launch would bypass
  `TaskTriage`.
- Close history (`plus_one` / `open` / `update` / `epic_preclaim`) would
  grow a `↺N` badge for operational retries of work that really did finish.

The audit note the user asked for is the right artifact for "we launched
anyway." Reopening is a different product decision, and it already has a
front door: `sase bead open`.

## Current behavior (evidence)

### Where `bead=` is accepted

| Layer | Closed beads |
| --- | --- |
| `%id(..., bead=id)` parse | Accepted. Only non-empty, whitespace-free. |
| TUI / LSP completion | Offers **open** bead IDs (`docs/macros.md` completion matrix). Typed closed IDs still parse. |
| `,x` / force-reuse rewrite | Copies `bead=` onto `%id(!suffix, …)`. |
| Retry prompt rewrite | Explicitly keeps `bead=` (`src/sase/agent/retry_prompt.py`). |
| Bootstrap env / meta | Sets `SASE_BEAD_ID` and `agent_meta["bead_id"]`. |
| Wait-claim (`claimed`) | Advisory. Closed → decline, continue. |
| Launch-claim (`in_progress`) | **Fatal.** Rust `kind: "closed"`. |
| Host finalizer close | Idempotent (`close_idempotent`). |

Rust source of the failure, `run_claim_launch` in
`sase-core/crates/sase_core/src/bead/mutation/claims.rs`:

```rust
if current.status == StatusWire::Closed {
    return Err(BeadError {
        kind: "closed".to_string(),
        message: format!(
            "cannot claim closed bead for agent launch: {issue_id}"
        ),
    });
}
```

Same-agent `in_progress` is already a no-op success. Closed is the only
status that errors. `ready`, `snoozed`, `claimed`, and `open` all promote to
`in_progress` and take the assignee. Python then wraps the error:

```text
Failed to claim bead '{bead_id}' for agent '{agent_name}': …
```

The contract is tested as intentional:

- `claim_for_agent_launch_rejects_missing_closed_and_blank_requests` in
  sase-core.
- `test_claim_for_agent_launch_maps_missing_and_preserves_specific_failures`
  (`ValueError`, `closed: cannot claim closed bead`).
- `test_closed_rendered_bead_fails_before_model_callback` in
  `tests/test_bead/test_epic_jit_claim_integration.py` — the model callback
  list stays empty.

### Claim lifecycle this would sit next to

From `docs/beads.md` (Bead Claim Lifecycle):

```
open ──claim──▶ claimed ──promote──▶ in_progress ──close──▶ closed
```

Promotion is what makes the claim permanent. Claims are compare-and-swap
from `open`; promotion currently refuses `closed` so a finished bead cannot
be silently owned by a new process. The user's `,x` case is the inverse: the
*same* implementer is coming back after the close already happened.

Force-reuse of a still-`in_progress` bead already skips mutation
(`issue_retains_force_reuse_owner`). Closed is the missing sibling of that
path.

### Notes already do what the audit trail needs

Bead notes are timestamped, attributed, append-only
(`BeadNoteWire`: `id`, `timestamp`, `author`, `text`). `append_issue_note`
works on closed beads (sase-core mutation-proof tests include a
"closed-bead note path"). Repeat `sase bead close --note` on an
already-closed bead is a note-only commit. There is a convention for
machine-recognizable prefixes (`PROPOSED FOLLOW-UP:`, `DISCOVERED ISSUE:`).
A new prefix fits that pattern. A new `BeadEventOperation` / `BeadReopenCause`
does not, unless we reopen.

## Requirement adjustments (called out)

These change the request. They are the difference between a recovery hatch
and a status-model leak.

1. **Keep the bead `closed`.** Launch succeeds; status, resolution,
   `closed_at`, and assignee stay as they were. The agent may call
   `sase bead open` later if the close was premature. Automatic reopen is
   out of scope for this change.
2. **Do not add a new `BeadReopenCause`.** Adding `agent_launch` (or similar)
   is the reopen design. Ship it only if product later chooses reopen.
3. **Fix the runner claim, for every launch that carries `bead=`, not only
   `,x`.** `sase agent restart`, retry, and auto-restart reuse the same
   prompt field and the same `claim_bead_for_agent_launch` call. A TUI-only
   branch would leave those paths red.
4. **Tell the agent.** Bind `agent_meta["bead_closed_at_launch"]=true` (plus
   resolution / `closed_at` if cheap to copy) and inject a short preface:
   the assigned bead is already closed; prefer leftover commit/finalizer
   work; `bead_action: close` is idempotent; `sase bead open` is the way to
   resume implementation. Today's generated skills assume an assigned bead
   the agent was launched to finish (`/sase_final`, `/sase_git_commit`).
5. **Leave epic scheduling and preclaim unchanged.** Closed phases stay
   unscheduled on `sase bead work` retry. Preclaim still rejects closed
   targets. Human `,x` of one finished worker is a different intent from
   "resume the epic."
6. **Leave occupancy checks unchanged.** `in_progress` assigned to another
   live owner still fails. Missing IDs still fail. Blank agent names still
   fail.
7. **No extra gate and no feature flag.** The current failure is a footgun
   nobody is relying on as a safety interlock (the safety interlocks are
   occupancy and missing-ID). A `FlagTriage` beta would add a second way
   for `,x` to surprise. A confirmation gate would recreate the
   interruption the user is trying to delete. If a later epic wants a
   chooser ("attach closed" vs "reopen"), that can be a TUI option on top
   of this primitive.
8. **Optional TUI copy, not a blocker.** `,x` confirmation can mention
   "bead `<id>` is closed; relaunch will attach and note, without
   reopening." Nice; the runner must be correct even when the prompt is
   submitted from CLI.

## Alternatives considered

### A. Reopen, then claim (`in_progress`)

Call `open_issue` (which already walks closed ancestors) or a new
`BeadReopenCause::AgentLaunch`, then the existing claim.

This matches "I am sending an implementer, so the work is open again." It
protects the new run under non-closed-bead artifact retention. It makes
`bead_action: close` meaningful again.

Cost: close-history noise, ancestor cascade, `TaskTriage` bypass, land-agent
waits, `↺N` badges on operational retries. Wrong for the common case where
the work *did* finish and the user is retrying a failed finalizer or a
cosmetic runner error.

Reject as the default. Keep `sase bead open` for this intent.

### B. Drop `bead=` on `,x` when the bead is closed

The relaunch would succeed as an unbound agent.

Cost: the host loses `assigned_bead`, `SASE_BEAD_ID`, `implements bead:<id>`
links, and the agent's ability to `sase bead note` / close idempotently in
context. The user would have to paste the ID back. Worse than today for
recovery.

Reject.

### C. TUI-only special case in the `,x` rewriter

Detect closed, rewrite the prompt, maybe pop a note from ACE before spawn.

Cost: `sase agent restart` and auto-restart still fail. Notes issued outside
the runner miss the store lock / managed-sidecar commit path the claim
helper already owns.

Reject as the sole fix. TUI copy can sit on top of C's runner change.

### D. Fail earlier (bootstrap) with a better message

If we kept the refusal, moving it to bootstrap would at least avoid
wait-then-die. It would not fix `,x`.

Reject as the product answer. Worth remembering if the keep-closed change
is deferred: fail before `%wait`, name `sase bead open` and "strip `bead=`".

### E. New keyword (`reopen=true`, `bead=!id`)

Explicit reopen stays available as a later additive. v1 does not need it.
The user wants the default relaunch to succeed.

### F. Python-only short-circuit in `claim_bead_for_agent_launch`

`project.show` already runs before the Rust claim. Branch on `Status.CLOSED`,
`append_issue_note`, return the issue.

This would unblock the runner with a smaller sase-core diff. The Rust
primitive would still error for every other caller, including tests that
mirror the runner. Shared backend behavior belongs in `sase_core`
(`rust_core_backend_boundary`). Prefer changing `run_claim_launch` and
letting the existing Python helper commit `changed=true` note mutations.

## Recommended solution

### Semantics

For `claim_for_agent_launch(bead, agent)` when the bead exists:

| Current status | Result |
| --- | --- |
| `in_progress` + same owner | No-op success (today). |
| `in_progress` + other owner | Python occupancy error (today). |
| `open` / `claimed` / `ready` / `snoozed` | Promote to `in_progress`, assign (today). |
| `closed` | **New:** success, status unchanged, append `CLOSED-BEAD LAUNCH:` note, `changed=true`. |
| missing | `not_found` (today). |

Wait-claim stays advisory and status-strict (`open` only). Closed own-beads
during `%wait` already decline; promotion then records the note. No second
wait-claim note.

Idempotency: every closed-bead launch appends a new note. Five `,x` presses
are five audit lines. That is the trail. Do not collapse them.

### Note text

Stable, greppable prefix, same family as `PROPOSED FOLLOW-UP:`.

```text
CLOSED-BEAD LAUNCH: agent {agent_name} launched with %id(..., bead={bead_id})
while status=closed (resolution={resolution}, closed_at={closed_at}).
Claim skipped; association retained.
```

- **timestamp** comes from the note record (`BeadNoteWire.timestamp`), not
  from stuffing a clock into prose twice.
- **author** is the launching agent name, passed through
  `append_issue_note`'s `author` argument (do not rely on the known defect
  that some mutations attribute events to the bead creator).
- Include resolution and `closed_at` so `sase bead show` / generated pages
  answer "which close did this relaunch sit on?" without opening history.

One mutation: stage the note in the same `run_claim_launch` commit as the
(non)status change, so managed sidecar stores get one
`chore(beads): note closed-bead launch of {id} for {agent}` rather than a
misleading `chore(beads): claim {id} for {agent}` with no status change.
Python `claim_bead_for_agent_launch` already commits when
`project.mutation_changed` and the store is managed; teach it the distinct
message when status stayed `closed`.

### Agent-visible signal

After a successful closed attach:

- `agent_meta["bead_id"]` remains.
- `agent_meta["bead_closed_at_launch"] = true`.
- `agent_meta["bead_claim_promoted"]` stays false or becomes a richer
  `"retained_closed"` — do not claim a promotion that did not happen.
  Today's `_promote_bead_claim` sets `bead_claim_promoted = True`
  unconditionally after the helper returns; that would lie.
- Inject a short stripped-from-raw, visible-to-model preface (or a
  generated-instruction clause keyed off the meta flag) so `/sase_final`
  chooses `bead_action: keep` unless the agent reopened.

Host close of an already-closed assigned bead is already
`close_idempotent`. No finalizer change required beyond the agent choosing
`keep` when it did no new bead work.

### sase-core shape

Extend `run_claim_launch` rather than adding a parallel entry point the
runner might forget to call. Closed becomes a third terminal branch next to
same-owner `in_progress` no-op and the promote path.

Do **not** call `archive_close_metadata`. Do **not** walk ancestors. Do
**not** add a `BeadReopenCause` variant.

If the note append needs the existing `append_issue_note` internals, share
the staging helper; keep one `commit`.

sase's `sase-core-revision.txt` CI pin moves past the core commit once the
binding is what sase calls (`docs/contribute/rust-backend.md`).

### Python / TUI / docs (thin)

- `src/sase/axe/run_agent_runner_bead.py`: distinct commit message; do not
  wrap closed-attach as `Failed to claim`.
- `src/sase/axe/run_agent_runner_launch.py`: set meta from the returned
  issue status.
- Optional ACE: `,x` confirmation / kill-and-edit banner names the closed
  bead.
- Optional completion: `%id` `bead=` rows may include recent closed IDs
  with a closed glyph. Low priority; `,x` already types them.
- Docs: claim lifecycle in `docs/beads.md`; `,x` paragraph in
  `docs/reference/tui/agents-tab-modes.md`; `%id` `bead=` in
  `docs/macros.md`; changelog.

### Tests to invert or add

- sase-core: split closed out of
  `claim_for_agent_launch_rejects_missing_closed_and_blank_requests`; add
  closed-attach note + unchanged status + second-launch second note.
- Python facade: invert
  `test_claim_for_agent_launch_maps_missing_and_preserves_specific_failures`
  for the closed case.
- Runner: invert `test_closed_rendered_bead_fails_before_model_callback` —
  the helper returns, model is allowed to run, note is present.
- Force-reuse: closed prior-owner relaunch attaches without occupancy error.
- Managed store: note commit + publish path, distinct commit subject.
- Meta: `bead_closed_at_launch` set; `bead_claim_promoted` not set.
- Golden / dual-mode replay if the closed branch writes events.

### Surfaces that stay red on purpose

- Epic preclaim of a closed phase or epic.
- `sase bead work` scheduling of closed phases.
- Occupancy: live `in_progress` held by another owner.
- `%wait(bead=X)` still means closed-enough-to-release; attaching an
  implementer to already-closed X does not re-park anyone.

## Risks and leftover work

**Two live agents on one closed bead.** Occupancy is enforced only for
`in_progress`. Two prompts that name the same closed `bead=` can both
launch. `,x` and `restart` kill the previous row first, so the motivating
path is safe. A copied prompt is the residual. Acceptable for v1; a later
check against live `agent_meta.bead_id` could refuse a second implementer.

**Artifact GC.** Retention protects runs tied to *non-closed* beads
(`src/sase/core/agent_artifact_run_protection.py`). A relaunch attached to a
closed bead does not get that protection. Live agent-name / in-progress-run
protections still apply while the replacement runs. Follow-up: treat
`agent_meta.bead_id` on a live run as a protector even when the bead is
closed.

**Doctor.** `sase doctor` warns about live pre-launch agents whose bead is
still `open`. A live agent whose bead is `closed` is a new shape. Add an
info-level line rather than a warning, so it does not look like a stuck
claim.

**Confused agent.** Without the preface in adjustment 4, the model will try
to "finish" a done bead. The preface is part of the minimum, not polish.

**Goals.** The host binds a goal independently of beads
(`decisions/goals-host-binds`). A closed bead plus a live goal is already
legal. This change does not bind or unbind goals.

## Implementation sketch (for the later plan)

1. **sase-core:** closed branch in `run_claim_launch`; tests; dual-mode
   replay.
2. **sase:** pin `sase-core-revision.txt`; runner helper commit message and
   meta; prompt preface; invert JIT/facade tests; force-reuse closed case.
3. **Docs / changelog** as above.
4. **Optional same-change:** `,x` confirmation copy; doctor info line.
5. **Follow-up (not v1):** TUI chooser to reopen; `reopen=true` keyword;
   retention exception; live-duplicate implementer check.

v1 is a small, bounded, two-repo change: one Rust branch, one Python commit
message / meta flag, a handful of inverted tests, and a note prefix.

## Recommended solution (one paragraph)

Allow `%id(..., bead=<id>)` launches against a closed bead by making
`claim_for_agent_launch` succeed without changing status: append a
`CLOSED-BEAD LAUNCH:` note authored as the launching agent, keep
`SASE_BEAD_ID` / `implements bead:<id>`, set `bead_closed_at_launch` on
agent meta, and tell the model the close already happened. Apply this in
the shared launch-claim primitive so `,x`, `sase agent restart`, retries,
and auto-restart all recover. Leave reopen, epic retry, preclaim, and
occupancy exactly as they are. That is the smallest change that matches
the user's recovery workflow and still respects `closed` as a real
terminal state.
