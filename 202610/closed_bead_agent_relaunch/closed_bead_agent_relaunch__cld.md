# Launching `%id(bead=…)` Agents On Closed Beads: Reopen-On-Launch With An Audit Trail

**Researcher:** cld · **Date:** 2026-10-16 · **Repos read:** `sase` (HEAD `e297cefb8e`), `sase-core`
(linked checkout) · **Evidence:** 11 real failure reports from `~/.sase/projects/*/artifacts`, plus
`sase bead history` replays of every affected bead.

**The request:** let an agent launch with `%id(..., bead=<bead>)` even when `<bead>` is already closed.
The usual case is a `,x` relaunch on the Agents tab after the agent or its finalizer closed the bead and
then the run failed. Leave a recognizable, timestamped audit trail on the bead. Critique the plan,
adjust the requirements where that is justified, and recommend an implementation.

---

## TL;DR

- **One hard guard in sase-core causes the failure.** `run_claim_launch` returns `kind: "closed"`
  (sase-core `crates/sase_core/src/bead/mutation/claims.rs:108-114`). The runner reaches it through its
  just-in-time claim, which runs *after* the workspace has been prepared
  (`src/sase/axe/run_agent_runner_launch.py:289` prepares, then `:319` promotes the claim). So the
  agent uses up a workspace, then dies with an error report.
- **I found 11 real occurrences between 2026-07-26 and 2026-10-03.**
  - **8 match your scenario.** The bead was closed *before* the relaunch was submitted. The closer was
    the agent itself or its epic's land agent, 7 minutes to 10 hours earlier.
  - **3 are the opposite.** The bead was closed *while the agent sat queued*:
    - you superseded it ("I forgot that I already had the sase-12y epic bead for this…");
    - a *different* agent finished the work 17 h later;
    - it was closed 52 min after a land agent had wait-claimed it.

  In all 3, refusing to launch was the right outcome.
- **The plan is good, but "always fine" would have been wrong in 3 of 11 cases (27%).** It would have
  resurrected a superseded phase, and with normal ancestor semantics its superseded epic too. It would
  also have redone work another agent had already finished.
  **Adjusted rule:** a launch may reopen a closed bead only if the close happened **at or before the
  moment the launch was submitted**. I call this the *visible-close rule*. If a bead closes while a
  launch is queued, the launch still respects that close.
- **"Fine" should mean reopen and claim (`closed → in_progress`), atomically.** It should not mean
  "run the agent while the bead stays closed". The phase prompt tells the agent its bead is already
  `in_progress`. sase already has close-history machinery: archived close records, a ↺ badge, and a
  "Previously Closed" section. That machinery covers most of the audit trail you asked for.
- **Write a two-layer audit trail in the same mutation and SDD commit.**
  - A structured close-history record with a new reopen cause (`agent_launch`, `reopened_by=<agent>`).
  - A greppable note with a fixed prefix (`LAUNCH REOPEN: …`).
- **Put the behavior in sase-core**, per the Rust-core boundary rule. Carry the cause as an **additive
  optional field on the existing `issue_updated` event**, not as a new event kind. An unknown event
  operation hard-fails older cores (`crates/sase_core/src/bead/jsonl.rs:925`), and the beads sidecar
  is shared across athena, apollo and the mac.
- **Refuse when reopening would also need a closed ancestor reopened** (in practice, a landed epic).
  This never happened in the 8 legitimate cases. Auto-reopening a landed epic leaves no land agent to
  close it again.
- **Check before spawning, not after workspace preparation.** Warn at submit time ("this launch will
  reopen sase-1ex.9, closed 1h46m ago by sase-1ex.9 · done"). Fail fast in the cases that will be
  refused.

---

## 1. How It Works Today

### 1.1 The claim path for a `%id(bead=…)` launch

| Stage | Code | What happens when the bead is closed |
| --- | --- | --- |
| Directive parse | `%id(name, bead=X)` → `AgentInfo.bead_id`, `SASE_BEAD_ID` | No status check anywhere before spawn |
| Wait-time claim (only for `%wait`, runner-slot or duration waits) | `_claim_bead_before_wait` (`src/sase/axe/run_agent_runner_bootstrap.py:281`) → `claim_bead_for_waiting_agent` (`src/sase/bead/claims.py:133`) → core `claim_for_agent_wait` | **Declines silently.** The wait claim is advisory and prints "claim declined" |
| Force-reuse retention (`,x`, `sase agent restart`, healer) | `issue_retains_force_reuse_owner` (`src/sase/bead/force_reuse.py:21`) | Matches only `in_progress`, so a closed bead falls through to the next row |
| Promotion, just before the model runs | `_promote_bead_claim` (`run_agent_runner_launch.py:209`) → `claim_bead_for_agent_launch` (`src/sase/axe/run_agent_runner_bead.py:43`) → core `claim_for_agent_launch` | **Hard error** `closed: cannot claim closed bead for agent launch: X` → `RuntimeError` → the run fails |

Facts that matter for the design:

- **How `,x` builds the relaunch.** `prepare_kill_and_edit_prompt` (`src/sase/agent/relaunch_prompt.py:101`)
  rewrites the stored prompt to `%id(!name, bead=X)`. The `!` (forced reuse) produces a one-shot
  `SASE_AGENT_FORCE_REUSE_BEAD` association (`src/sase/agent/force_reuse_bead.py`,
  `force_reuse_launch.py`). `sase agent restart` and the auto-restart healer produce the same
  association. The `!` is stripped before the runner starts, so it does not appear in the run's
  `raw_prompt.md`.
- **`sase bead work` never targets closed beads.** sase_beads memory: "reassigns every non-closed bead
  and never touches closed phases". Its phase and land segments do carry `%w(...)`
  (`src/sase/bead/work_prompt.py:210-248`), so they sit queued for minutes to hours before the
  promotion claim. That queue is where the visible-close rule matters.
- **Wait claims can be released, which rules out reopening at wait time.** On kill or death before
  promotion, `release_agent_claim` sets a bead back from `claimed` to `open` (docs/beads.md "Bead Claim
  Lifecycle"). If a closed bead were reopened at wait time, an aborted relaunch would leave it as an
  `open` draft, and the close would be lost. **A reopen must only happen at promotion.**

### 1.2 Reopen and audit machinery that already exists (reuse it)

- **Close history.** `close_history: Vec<BeadCloseRecordWire>` stores `closed_at`, `close_reason`,
  `resolution`, `reopened_at`, `reopened_via` and `reopened_by` (sase-core
  `crates/sase_core/src/bead/wire.rs:573-640`). It landed in sase-core #86, "archive close metadata
  instead of destroying it on reopen".
- **One chokepoint.** Every reopen path, in both the mutation code and the event reducer, goes through
  `archive_close_metadata` (`events/reduction.rs:700`). A parity test checks that the mutated bead and
  the bead rebuilt from events are byte-identical.
- **Existing causes.** `plus_one`, `open`, `update` and `epic_preclaim`.
  - Python mirrors them in `ReopenCause` (`src/sase/bead/model.py:36`) and labels them in
    `close_record_reopened_label` (`src/sase/bead/reopen_presentation.py:37`).
  - They are rendered in the TUI bead detail ("Previously Closed"), on bead pages, and in
    `sase bead read`/`show`, with a ↺N badge.
  - `close_history_codec.py:35` already **drops unknown causes** instead of raising, so an older sase
    stays tolerant of a new cause.
- **Notes.** Notes are a timestamped, attributed, append-only log (`NoteAppended` event, author = the
  event actor). `sase bead search` matches note text.
- **Ancestors reopen with their children.** `sase bead open` and `update --status <non-closed>` both
  reopen every closed ancestor (`reopen_closed_ancestors_via_view`). No closed ancestor sits above a
  non-closed descendant anywhere else in the store.
- **Precedent for reopening at launch.** `EpicWorkPreclaimed` (the `sase bead work` checkpoint) already
  means "claim for an agent, and reopen if closed", with cause `epic_preclaim`. A launch-time claim that
  reopens is not a new idea.
- **Closer identity.** `issue_closed` events record `closed_by`, the acting closer, which is the agent
  name when an agent closed the bead. It lives only on the event, not on the `IssueWire` projection.

---

## 2. Evidence: Every Real Failure On Record

**Method:**

1. `grep -rl "cannot claim closed bead for agent launch"` over `~/.sase/projects/{gh_sase-org__sase,sase-core}/artifacts`
   found 41 files. 11 are `error_report.md` files from failed runs. The rest are tool-call logs and diffs
   from agents that worked on this code.
2. For each failed run, `sase bead history <bead> -f json -n 0` gave the close times. I compared them
   with the run's launch timestamp. Artifact directory names use local EDT; the times below are UTC.

| Bead | Agent | Launch (UTC) | Current close (UTC) | Closed by | Resolution | Close vs launch |
| --- | --- | --- | --- | --- | --- | --- |
| sase-av | sase-av.land | 07-29 20:51:13 | 07-29 20:44:21 | owner email (before attribution existed) | done | before, 7 min |
| sase-ba | sase-ba.land | 07-30 21:42:13 | 07-30 20:40:07 | owner email | done | before, 62 min |
| sase-xe.6 | sase-xe.6 | 09-07 00:31:10 | 09-06 23:54:11 | bbugyi200.athena.0gq | done | before, 37 min |
| sase-zt.6.4 | sase-zt.6.4 | 09-13 18:11:25 | 09-13 16:37:07 | sase-zt.land (epic land agent) | done | before, 94 min |
| sase-17x.13.1 | sase-17x.13.1 | 09-25 10:55:14 | 09-25 00:57:35 | sase-17x.land (epic land agent) | done | before, 10 h |
| sase-1bc.5 | sase-1bc.5 | 09-27 18:35:56 | 09-27 18:17:16 | itself | done | before, 19 min |
| sase-1bc.6.1.1 | sase-1bc.6.1.1 | 09-27 18:37:48 | 09-27 18:04:32 | itself | done | before, 33 min |
| sase-1ex.9 | sase-1ex.9 | 10-03 12:41:55 | 10-03 10:55:26 | itself | done | before, 1 h 46 min |
| **sase-96.8** | sase-96.8.land | 07-26 10:05:37 | 07-26 10:57:36 | owner email | (none) | **after, 52 min**. The land agent had wait-claimed it at 10:06 |
| **sase-131.4** | sase-131.4 | 09-18 18:42:33 | 09-18 18:43:59 | force close of epic sase-131 | **superseded** | **after, 86 s**. Reason: "I forgot that I already had the sase-12y epic bead for this…" |
| **sase-1ae.5** | sase-1ae.5 | 09-26 11:01:54 | 09-27 04:45:05 | **sase-1aq.10.7.5.6**, a different agent | done | **after, 17 h 43 min** |

What this shows:

1. **8 of 11 are your scenario.** The bead was closed before the (re)launch was submitted. Every
   ancestor of every one of these beads was open or in progress at relaunch time, so an
   ancestor-refusal rule would have blocked none of them.
2. **3 of 11 were correct refusals.** The close happened *while the run was queued*. "Always reopen"
   would have gone wrong in each:
   - sase-131.4: it would have restarted work you had just declared superseded.
   - sase-1ae.5: it would have repeated a phase another agent had already completed.
   - sase-96.8: it would have reopened a sub-epic someone closed by hand while its land agent waited.
3. **Who closed the bead is not a usable filter.** In 2 of the 8 legitimate cases the closer was an epic
   land agent, not the relaunched agent. "Only reopen beads the agent closed itself" would leave a
   quarter of the real annoyances in place.
4. **The 8 relaunches look like TUI relaunches, not fresh `sase bead work` launches.**
   - Their `agent_meta.json` has `wait_for_beads` and lacks
     `epic_bead_id`/`phase_bead_id`/`clan_tribe`.
   - The queued sase-131.4 run has `clan_tribe: epic`, which marks it as a genuine bead-work launch.
5. **No bead shows a later `issue_opened` event after these failures.** You gave up rather than running
   `sase bead open` and relaunching. That matches "annoying".
6. **Spot check of what the original runs did.** I read the chat transcripts of two original runs
   (sase-1ex.9, sase-zt.6.4). Both had finished their work and recorded verification notes. The
   relaunch mostly re-verifies. That is a hint for a complementary fix (§3.3), not an argument against
   this one.

---

## 3. Critique

### 3.1 Is this a good idea?

Yes. A relaunch the user chose to run should not die on a status the user can see and has implicitly
overridden. Today's guard dates from a model where `closed` was terminal. sase-core #86 already moved
beads to "closes can be undone, and the archive keeps the story". `epic_preclaim` already reopens at
launch. The real missing piece is a rule for *when* a launch is entitled to undo a close.

Two parts of the original framing need changing:

- **"Fine for any `bead=` launch" is too broad.** Unattended or queued launches must keep respecting
  closes that happen while they wait. The evidence shows such closes are deliberate: a superseded
  epic, and work finished by someone else.
- **The audit trail should not be only a note.** A note is free text that agents also write. The
  structured close-history record keeps the overwritten close (`closed_at`, `close_reason`,
  `resolution`) and already renders everywhere. Use both.

### 3.2 Risks the plan does not mention

1. **Queued launches**, discussed above. This is the main reason for the visible-close rule.
2. **Ancestors and landed epics.** Any reopen that follows store semantics must also reopen closed
   ancestors. A phase relaunched after its epic landed would reopen the epic, and no land agent would
   close it again. That is rare (0 of 8 observed) and confusing when it happens, so refuse and point
   the user at `sase bead open <phase>`.
3. **The wait-time claim must not reopen** (§1.1). Otherwise a relaunch killed during its wait turns a
   closed bead into an `open` draft.
4. **Compatibility across machines.** A new event kind would make every un-updated machine's core fail
   to replay the shared beads stream ("unknown bead event operation … run `sase update`",
   `jsonl.rs:925`). An optional field on `issue_updated` is ignored by old readers, because these wire
   types do not use `deny_unknown_fields`. `issues.jsonl` is gitignored and stays local
   (`.gitignore:6` in the beads store), so a new `reopened_via` value never reaches another machine.
5. **Downstream `%w(bead=X)` waiters.** Agents already released by X's close keep running after X
   reopens, exactly as with `sase bead open` today. That is acceptable, but the note and the warning
   should make the reopen visible so you can judge.
6. **A relaunch that fails again leaves the bead `in_progress`, where before it stayed `closed`.** This
   is more honest: the outcome of the work really is unknown at that point. The next `,x` retains it
   through force-reuse. The note explains why it is open.
7. **Healer race.** An agent dies, you cancel its bead, then the auto-restart healer relaunches it. The
   cancel predates the healer's submission, so the visible-close rule would reopen it. The window is
   small and the healer is narrow. Optional hardening: the healer only authorizes reopening `done`
   closes. See §6.7.
8. **Failure arrives late.** Today the error appears after workspace preparation. A pre-spawn check
   turns refusals into instant feedback and turns reopens into a visible warning.

### 3.3 Would I take a different approach?

Same direction, plus two complementary ideas:

- **Fix part of the cause.** Several of these relaunches exist because the agent closed its bead
  mid-turn and a later step failed. The `bd/work_phase_bead` prompt says to run `sase bead close …`
  before the final declaration (`src/sase/default_config.yml:2279`).
  - Host-owned completion (decision `host-owned-completion`) already has a declaration
    `bead_action: close` path that closes *after* the commit lands (`close_assigned_bead_after_commit`,
    `src/sase/workflows/commit/bead_hooks.py:125`).
  - Closing phase and task beads after commit would make a post-close failure leave the bead
    `in_progress`, and `,x` already handles that.
  - This is a bigger and separate change. It does not replace this work: you also relaunch runs that
    succeeded, and land agents close epics.
- **Retry only the finalization when that is all that failed.** Both sampled originals had finished
  their work, so a finalizer-only retry would be cheaper than a full relaunch. Bead `sase-1jf`
  ("resume in place instead of notify-only") is the nearest existing thread. Out of scope here.

---

## 4. Options Considered

| Option | Fixes the 8 real annoyances | Respects the 3 queued closes | Audit quality | Cost and fit |
| --- | --- | --- | --- | --- |
| **A. Delete the guard** (always reopen) | 8/8 | **0/3** | Depends on what gets added | Trivial, but wrong 27% of the time on real data |
| **B. Skip the claim and run against the closed bead** | 8/8, but the agent runs while the bead says closed | 0/3 | Weak: no state change, so nothing to audit structurally | Breaks the prompt's "already in_progress" promise. `bead_action: keep` would leave unfinished work marked closed. A re-close with a different `--reason` or resolution is refused by `reject_conflicting_close` |
| **C. Reopen only for forced-reuse replacements** (`!`: `,x`, restart, healer) | Probably 8/8 (all look like TUI relaunches) | 3/3 here (they were `!`-less bead-work launches) | Good | Small, but tied to *how* the launch was built: a fresh typed `%id(x, bead=closed)` still fails (your literal ask), and a queued `!` relaunch would still reopen a close made during its wait |
| **D. Visible-close rule** (reopen iff `closed_at ≤ launch submitted_at`) | 8/8 | **3/3** | Good, with the two-layer trail | Small-to-medium. Works on every surface (TUI, CLI, mobile, prompt-history recall, healer) without trusting the prompt syntax |
| **E. Ask every time** (confirm modal) | 8/8 at one extra keypress | 3/3 for interactive launches; unattended launches cannot ask | Good | Friction on the exact flow (`,x`) you want to make smooth |
| **F. Python-only stopgap** (catch `closed` → `project.open()` + note + claim, under one lock) | 8/8 | 0/3 unless the rule is added in Python | The cause label would wrongly say "Reopened by `sase bead open`". It also reopens ancestors | Violates the Rust-core boundary. Three mutations instead of one atomic one |

**Recommendation: D**, with C's force-reuse signal used only to enrich the note ("relaunch of X via
kill-and-edit"), not as the gate.

An alternative way to implement D is "episode pinning": the submitting surface records the exact
`closed_at` it saw and the runner reopens only that close. It is immune to clock skew but needs a
status read on every launch surface. A time comparison is universal and good enough on an NTP tailnet,
so I would start with that.

---

## 5. Adjusted Requirements (called out explicitly)

| # | Your requirement | Adjustment | Why |
| --- | --- | --- | --- |
| R1 | Launching with a closed `bead=` should be "fine" | **Changed:** fine = an atomic **reopen and claim to `in_progress`**, never running against a closed bead | Keeps the phase prompt's promise, the doctor and claim checks, and what dashboards show. Gives the audit trail a state change to record |
| R2 | …for any such launch | **Narrowed:** only when the current close happened **at or before the launch's submission time**. A close that lands while the launch is queued still causes a refusal, with a better message (§6.2) | 3 of 11 real cases were deliberate closes made during the queue |
| R3 | (not stated) | **Added:** refuse when a **closed ancestor** would also need reopening. Point the user at `sase bead open <id>` | Avoids silently reopening landed epics that nothing will close again. Happened 0 of 8 times in legitimate cases |
| R4 | Recognizable, timestamped note or annotation | **Expanded:** a structured close-history record (new cause `agent_launch`, `reopened_by=<agent>`) **plus** a `LAUNCH REOPEN:` note, written in the same mutation and SDD commit | Structured data drives the badge, "Previously Closed" and search. The note gives the narrative and is greppable |
| R5 | (not stated) | **Added:** check before spawning. Warn on reopen, fail fast on refusal | Today the failure only appears after a workspace has been prepared |
| R6 | (not stated) | **Added:** the event wire must be readable by un-updated cores on other machines | The beads sidecar is shared across the tailnet |
| R7 | (not stated) | **Kept out:** no feature flag and no config knob in v1 | Per sase_flags memory this is neither a beta nor a deprecation. Add a config field only if you later want different policies |

---

## 6. Recommended Solution

### 6.1 sase-core: one atomic "claim, reopening if allowed" mutation

- **API.** Add an optional reopen authorization to the launch claim, either a new binding or a new
  optional kwarg detected by capability. The new binding is the safer choice inside the
  `sase-core-rs` minor window.

  ```rust
  pub struct BeadLaunchReopenWire {
      /// RFC-3339 instant the launch was submitted. Only a current close at or
      /// before this instant may be reopened (the visible-close rule).
      pub submitted_at: String,
      /// Optional host context appended to the audit note, e.g.
      /// "relaunch of sase-1ex.9 via kill-and-edit (prior run 20261003064121)".
      pub context: Option<String>,
  }
  ```

  `claim_for_agent_launch(beads_dir, id, agent, now, reopen: Option<BeadLaunchReopenWire>)`

- **Behavior of `run_claim_launch` on a closed bead.**

  | Condition | Result |
  | --- | --- |
  | `reopen` is `None` | Today's error, kind `closed` (unchanged for callers that do not opt in) |
  | `closed_at > submitted_at` | New error, kind `closed_after_submit`. The message names `closed_at`, the closer, the resolution, and the remedy ("relaunch to reopen it deliberately") |
  | Any ancestor is closed | New error, kind `closed_ancestor`. The message names the ancestor and the remedy (`sase bead open <id>`) |
  | Otherwise | Set `status = in_progress` and `assignee = agent`. Call `archive_close_metadata(cause = AgentLaunch, reopened_by = Some(agent))`, then `clear_snooze_record`. Stage the events below. Return `outcome.reopened = Some(<archived BeadCloseRecordWire>)` |

- **Event shape, chosen for compatibility.**
  - The state change is the existing `issue_updated` event with
    `fields: { status: in_progress, assignee: <agent>, reopen_cause: "agent_launch" }`.
    `reopen_cause` is a new `#[serde(default, skip_serializing_if = "Option::is_none")]` field on
    `BeadIssueUpdateEventFieldsWire`. In `apply_update_event_fields` (`reduction.rs:~680`), when it is
    present, archive with that cause and set `reopened_by = event.actor` instead of `Update`.
    - Old cores ignore the field and archive with cause `update`, which renders as "Reopened by a status
      update". The note still tells the full story.
    - Pass the agent explicitly as the event actor, so `reopened_by` is accurate. #86 limited
      `reopened_by` to `plus_one` because other paths used the bead creator as actor.
  - The audit trail is the existing `note_appended` event, with the same actor and timestamp.
  - Do **not** add a new event kind (`jsonl.rs:925` hard-fails unknown operations).
- **Note text, composed in core so every frontend writes the same thing.** The prefix is fixed and
  greppable. The timestamp is in the text as well as in the note metadata, so plain-text exports keep
  it:

  ```text
  LAUNCH REOPEN: 2026-10-03T12:42:20Z — agent sase-1ex.9 launched against this closed bead
  (launch submitted 2026-10-03T12:41:55Z), so it was reopened and claimed (in_progress).
  Prior close: 2026-10-03T10:55:26Z · done · by sase-1ex.9 · "<close_reason excerpt>".
  Relaunch of sase-1ex.9 via kill-and-edit (prior run 20261003064121).
  ```

  The closer comes from the bead's latest `issue_closed.closed_by`, if it is cheap to get from the
  issue's already-loaded stream. Otherwise leave it out.
- **Tests.**
  - Mutation-vs-reducer parity for the new cause, on both backings.
  - Each refusal kind.
  - A same-agent call on an already-`in_progress` bead stays a no-op.
  - A reopen when there is no `closed_at` (legacy data): treat it as visible.
  - An "old reader" test that deserializes an `issue_updated` event carrying an unknown field.
- `BeadReopenCauseWire::AgentLaunch` (`"agent_launch"`) appears only in the local projection.

### 6.2 sase runner (Python)

- **Pass the authorization.** `_promote_bead_claim` (`run_agent_runner_launch.py:209`) passes
  `submitted_at`, which is the run's launch timestamp `state.timestamp` converted to UTC. The timestamp
  is allocated when the launch is planned, before any `%wait`; `parse_started_at` already parses it. It
  also passes a context string built from the force-reuse association, when there is one.
  `claim_bead_for_agent_launch` (`run_agent_runner_bead.py:43`) forwards both and keeps its existing
  lock, commit and publish flow.
- **Name the commit.** Use `chore(beads): reopen and claim <bead> for <agent>` when a reopen happened.
- **Make the reopen visible.**
  - Print one line to the agent output ("Reopened closed bead X (closed … · done · by …) for this
    launch").
  - Record `bead_reopened_for_launch: {closed_at, resolution, reopened_at}` in `agent_meta.json` so the
    Agents tab can show ↺ on the row.
- **Leave the wait-time claim unchanged.** `_claim_bead_before_wait` keeps declining on closed beads;
  the reopen happens only at promotion (§1.1).
- **Improve the refusal messages.**
  - `closed_after_submit`: "sase-131.4 was closed 2026-09-18T18:43:59Z (superseded) after this launch
    was queued at 18:42:33Z; not reopening it. Relaunch (`,x`) to reopen it deliberately."
  - A deliberate re-submission is itself the confirmation: the close now predates the new submission.
  - Optional follow-up: give this case a distinct non-failure outcome ("stood down: bead closed while
    queued") instead of a red failed agent.

### 6.3 Pre-spawn check and UX

- **Where to check.** Launch submission from the TUI prompt bar, `sase run`, the mobile and Telegram
  launch paths, and marked-set `,x`.
- **How.** Read each `bead=` status with the cheap batched read `bead_statuses_for_project`.
  - **Closed, ancestors open:** show a non-blocking warning toast. "sase-1ex.9 is closed (done, 1h46m
    ago, by sase-1ex.9); this launch will reopen it." Then launch.
  - **Closed ancestor:** refuse before spawning, with the `sase bead open` remedy.
- **`sase agent restart` preview** (`src/sase/agent/_restart_preview.py`, which already shows `bead`):
  add a warning line.
- **Do not add a blocking confirm in v1**, even when someone else closed the bead (2 of 8 real cases).
  Add it later only if accidental reopenings actually happen.

### 6.4 Presentation

- **Python labels.** Add `ReopenCause.AGENT_LAUNCH = "agent_launch"` and a `close_record_reopened_label`
  branch: "Reopened <ts> by launching agent `<name>`". The TUI bead detail, bead pages and
  `sase bead read`/`show` then pick it up with no other changes.
- **Older sase builds** silently drop the unknown cause (`close_history_codec.py`), so they degrade
  gracefully.

### 6.5 Prompt and docs

- **Agent prompts.** Add one sentence to `bd/work_phase_bead` and `bd/work_task`
  (`src/sase/default_config.yml:2279`): "If `sase bead read` shows a `LAUNCH REOPEN:` note, an earlier
  run already closed this bead; check whether its work already landed before redoing it." The
  relaunched agent sees the archived close and the note anyway. This sentence turns that into
  behavior.
- **docs/beads.md "Bead Claim Lifecycle".** Add a `closed ──launch reopen──▶ in_progress` edge, the
  visible-close rule, and the ancestor refusal.
- **docs/reference/macros/directives.md.** Update the `%id` `bead` row.
- Read `docs_writing.md` memory before editing either doc.

### 6.6 Rollout

1. **sase-core PR** (`feat(bead): …`). It is non-breaking: an additive optional event field and a new
   binding or optional parameter. Include tests and the binding round-trip.
2. **Move `sase-core-revision.txt` past that commit**, then land the sase PR: runner wiring, pre-spawn
   check, label, prompt sentence, docs, and runner and check tests.
3. **Update athena, apollo and the mac.** The order is not critical, because older cores replay the new
   events fine. That is the point of using a field rather than a new event kind.

Size: one core mutation branch with a reducer tweak and a binding, plus runner wiring, one check and
one label. That is a small 2-phase epic: core first, then sase. Two medium tasks would also work.

### 6.7 Decisions left to you

1. **Ancestor policy.** I recommend refusing. The alternative is to reopen ancestors like
   `sase bead open` does, for consistency.
2. **Healer auto-restart.** I recommend applying the same rule, for simplicity. The alternative is to
   authorize only `done` closes, which closes the "you cancelled, then the healer relaunched" race.
3. **Someone else closed the bead.** I recommend warning only. The alternative is a confirm step.
4. **Close made while the launch was queued.** For v1 I recommend keeping it a failure with the clearer
   message. Making it a distinct non-failure outcome can come as a follow-up.
5. **Note prefix.** `LAUNCH REOPEN:` is short, uppercase, and matches existing prefixes such as
   `PROPOSED FOLLOW-UP:` and `DISCOVERED ISSUE:`. Change it if you want different wording.

---

## Appendix: Reproducing The Evidence

```bash
# 1. Failed runs that hit the guard (41 files match; 11 are error reports)
grep -rl "cannot claim closed bead for agent launch" \
  ~/.sase/projects/gh_sase-org__sase/artifacts ~/.sase/projects/sase-core/artifacts \
  | grep error_report.md

# 2. For each bead: close and claim history (compare with the run dir's EDT launch timestamp)
sase bead history <bead> -f json -n 0

# 3. Relaunch-vs-fresh-launch signal
python3 -c 'import json,sys; print(json.load(open(sys.argv[1])))' <run>/agent_meta.json
#   relaunches: wait_for_beads present, no epic_bead_id/phase_bead_id/clan_tribe
#   bead-work launch (sase-131.4): clan_tribe=epic, epic_bead_id, phase_bead_id
```

Key code references:

- **sase-core:**
  - `crates/sase_core/src/bead/mutation/claims.rs:101-160`: `run_claim_launch` and its `closed` guard at `:108`
  - `crates/sase_core/src/bead/events/reduction.rs:680-719`: `apply_update_event_fields` and `archive_close_metadata`
  - `crates/sase_core/src/bead/wire.rs:573-640`: `BeadReopenCauseWire`, `BeadCloseRecordWire`
  - `crates/sase_core/src/bead/jsonl.rs:911-925`: unknown event operation is a hard error
- **sase:**
  - `src/sase/axe/run_agent_runner_launch.py:209,289,319`
  - `src/sase/axe/run_agent_runner_bead.py:43`
  - `src/sase/axe/run_agent_runner_bootstrap.py:281`
  - `src/sase/bead/claims.py:133`
  - `src/sase/bead/force_reuse.py:21`
  - `src/sase/agent/relaunch_prompt.py:101`
  - `src/sase/agent/force_reuse_launch.py`
  - `src/sase/bead/close_history_codec.py:35`
  - `src/sase/bead/reopen_presentation.py:37`
  - `src/sase/workflows/commit/bead_hooks.py:125`
  - `src/sase/default_config.yml:2279`
  - `docs/beads.md` ("Bead Claim Lifecycle")
