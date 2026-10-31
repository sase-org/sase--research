# Agent publication failures: planner prompts incorrectly require commit ownership

Researcher: `cdx` · Investigation date: 2026-10-31 (America/New_York)

## Finding

**The recent “published agent page … did not materialize during commit drain” notifications are caused by a mismatch between planner prompt publication and commit publication.** Accepted-plan processing archives the planner's prompt using the workspace's existing HEAD, then creates a revision-scoped publication request. Completion requires that SHA to be associated with the planner or its session. The SHA can belong to an entirely different agent, so the request cannot satisfy that requirement even after its page and prompt have been published.

This is strongly supported for the supplied `sase-1pj.6` incident and four other recent requests. Their required pages exist. A read-only evaluation of the production Rust completion policy against their published snapshot metadata returns **“required page exists without the requested primary revision”** for all five. Python reduces that result to a boolean and reports the misleading missing-page message.

The best fix is to give planner prompt requests an explicit, durable publication intent that requires the appropriate page and prompt archive, but does not require ownership of the planner's input HEAD. Preserve strict revision association for actual primary commits. Repair existing requests only when accepted-plan evidence proves their origin.

## Evidence and scope

I independently examined the specified digest, other October 31 digests, the local outbox, affected agents' runtime metadata and commit markers, publication-sidecar metadata, an audited published-agent page, and the Python and Rust implementations. I did not consult the other researchers' reports, chats, summaries, or findings. No retry, repair, queue deletion, source-code fix, notification dismissal, or full publication was performed.

Source baselines:

- SASE checkout: `eef22a012481fa8cadd0b9ac315c106eacb66fb0`.
- Opened `sase-core` checkout: `f9878e769a2c53f835b898ebfc21344d4e5f2afd`.
- SASE's checked-in core CI pin: `32c66ddf2b8b0cc1456cdea79a36dcd8202cd24d`.
- The reproduction used this workspace's Python source with the installed SASE interpreter and native binding. I did not rebuild the Rust checkout or establish that its HEAD is the installed wheel's exact source revision. The installed policy's observed result agrees with the inspected implementation.

### The supplied notification

Notification `ede90333-6310-4cbe-90d3-da56df5700a2`, sender `axe`, timestamp `2026-10-31T10:04:32.323287-04:00`, was an unread priority notification. Its attachment is:

`~/.sase/axe/error_digests/digest_20261031_100432.txt`

The attachment reports one failure at `2026-10-31T09:10:38.612893-04:00`, routine `publication`, job `agent_publication`:

```text
published agent page for 'bbugyi200.athena.sase-1pj.6'
did not materialize during commit drain
```

The summary reports `errors=1`, `lock_busy=0`, `deferred_projects=0`, and `active_remaining=2`. Exit code 0 does not contradict the error: the job explicitly sets its structured result to `check_error` when its error counter is nonzero. See [the job adapter](https://github.com/sase-org/sase/blob/eef22a012481fa8cadd0b9ac315c106eacb66fb0/src/sase/scripts/sase_chop_agent_publication.py).

The digest's referenced run log no longer existed when examined. The retained digest, durable queue row, and agent metadata supply the incident evidence; I cannot reconstruct every step of that original process from its missing log.

The separate warning about dropping `bead:[sase-1g4.2.1.5]` is not the failure under investigation. It names a malformed projected reference; it does not explain the reproducible commit-association failure. Fixing that warning alone would not make these requests fulfill.

### Five requests show the same mismatch

All global agent names below begin with `bbugyi200.athena.`. All five rows had `scope=revision`, three attempts, and quarantine enabled at inspection. Their metadata identifies an approved planner turn; each row's requested SHA equals its planner's recorded `workspace_head`.

| Queued agent/session | Requested SHA | Agent named by that commit's `SASE_AGENT` footer | Published completion decision |
|---|---|---|---|
| `sase-1pj.6` | `2763a6bc58cd` | `sase-1pj.5.1.land` | Page exists; requested revision unassociated |
| `sase-1pj.7` | `2763a6bc58cd` | `sase-1pj.5.1.land` | Page exists; requested revision unassociated |
| `sase-1q2.land` | `eec20f6ad54e` | `sase-1q2.6` | Page exists; requested revision unassociated |
| `sase-1q4.land` | `4a4b6fede82a` | `sase-1q4.8` | Page exists; requested revision unassociated |
| `sase-1q5.land` | `cb230adb5e50` | `sase-1q4.3` | Page exists; requested revision unassociated |

Evidence locations:

- Queue: `~/.sase/projects/gh_sase-org__sase/agents-publication-outbox.json`.
- Affected planner metadata: `artifacts/ace-run/202610/28/20261028203149/agent_meta.json` and `20261028203150/agent_meta.json`, and `artifacts/ace-run/202610/30/20261030123856/agent_meta.json`, `20261030174519/agent_meta.json`, and `20261030184159/agent_meta.json`, relative to that project state directory.
- Publication metadata: `users/bbugyi200/machines/athena/hoods/<hood>/snapshot.json`, relative to the agents sidecar opened through `sase repo open agents`.
- Commit attribution: local `git show --no-patch` of the four SHAs above.

For `sase-1pj.6`, the row requests the full SHA `2763a6bc58cd74d4882ab97bace343de0c73fa97`. Its local planner metadata records `plan_approved=true`, `plan_action=epic`, and the archived prompt path `prompts/202610/staged_handoff_recovery.md`. That prompt file exists. No primary commit markers were present in this planner artifact directory. Its published session and member records have no commits.

The audited read `sase artifact read agent:bbugyi200.athena.sase-1pj.6 ...` also found an existing older solo-agent page showing zero commits. Both solo and session pages exist; importantly, the completion policy classifies the current snapshot as a **session** and checks `sessions/bbugyi200.athena.sase-1pj.6.md`. The diagnosis therefore does not depend on accidentally inspecting an obsolete solo page.

Two other sessions later acquired commits: `sase-1q5.land--1` carries `e32449dad97d…`, and `sase-1q4.land--code` carries `9b880fbfdfc3…`. Neither is the original requested SHA. A later successful coding turn does not, by itself, satisfy an incorrectly revision-bound planner request.

October 31 digest records show three attempts for each of `sase-1q5.land`, `sase-1q2.land`, `sase-1q4.land`, and `sase-1pj.7`. This is repeated failure across newly generated requests, with bounded retries per request—not evidence that one active row retries forever.

## Causal chain

1. **Accepted-plan processing gets the current checkout HEAD.** `publish_planner_prompt_archive()` runs `git rev-parse HEAD` and passes it as `primary_revision`, with `commit_cwd=ctx.workspace_dir`. It does not establish that the planner created that commit. See [planner archive producer, lines 20–60](https://github.com/sase-org/sase/blob/eef22a012481fa8cadd0b9ac315c106eacb66fb0/src/sase/axe/run_agent_exec_plan_accept_sdd.py#L20). Git's revision resolution identifies a commit; it is not evidence of SASE agent ownership. See [Git's official revision documentation](https://git-scm.com/docs/git-rev-parse).
2. **Prompt archiving also enqueues an agent-publication obligation.** `publish_prompt_archive()` creates an `AgentPublicationOutboxItem` before its publication transaction, projecting a planner turn to its session identity. Its scope is inferred from the checkout location. See [archive enqueue, lines 143–163](https://github.com/sase-org/sase/blob/eef22a012481fa8cadd0b9ac315c106eacb66fb0/src/sase/agents_sync/prompt_archive/publish.py#L143).
3. **A primary workspace means revision scope.** `fulfillment_scope_for_commit_cwd()` chooses `revision` for primary roots and `linked` for non-primary roots. The actual intent—archive an approved planner prompt—is not represented. See [scope inference, lines 211–219](https://github.com/sase-org/sase/blob/eef22a012481fa8cadd0b9ac315c106eacb66fb0/src/sase/agents_sync/_commit_publication_queue.py#L211).
4. **The drain successfully prepares a hood but cannot acknowledge the request.** Rust requires the canonical page and, for revision scope, the requested SHA in the correct run/session's commit associations. A sibling's SHA does not count merely because it appears elsewhere in the same hood. See [Rust completion policy](https://github.com/sase-org/sase-core/blob/f9878e769a2c53f835b898ebfc21344d4e5f2afd/crates/sase_core/src/agent_publication_recovery/complete.rs).
5. **The explanatory result is discarded.** `publication_request_fulfilled()` returns only `.fulfilled`. The caller emits the same missing-page message for any false result, charges the attempt, and retains the request. See [boolean adapter](https://github.com/sase-org/sase/blob/eef22a012481fa8cadd0b9ac315c106eacb66fb0/src/sase/agents_sync/publication_completion.py#L24) and [acknowledgment gate](https://github.com/sase-org/sase/blob/eef22a012481fa8cadd0b9ac315c106eacb66fb0/src/sase/agents_sync/_commit_publication_transaction_steps.py#L296).

The production policy was evaluated without queue mutation against all five snapshots. Each failed with the precise revision-association reason. Changing only the input scope to the existing revision-independent `linked` semantics made each page-completion check pass. This does **not** prove a full drain will succeed: prompt restoration, protection, git publication, and link side effects have their own gates.

A separate four-case assertion probe confirmed that an existing page plus a foreign SHA fails revision scope, the same page passes revision-independent scope, a missing page remains blocked, and a correctly associated commit passes revision scope. This isolates the contract error while demonstrating that commit verification remains useful.

## The older backlog is a separate recovery problem

At inspection, the SASE project outbox held **3,544 rows: 3,542 quarantined and two retired; none active**. A simple classification of stored `last_error` text gave:

| Stored error category | Rows |
|---|---:|
| Publication did not complete within its time budget | 2,912 |
| Agents-sync lock busy | 439 |
| Prompt archive unresolved | 124 |
| Page did not materialize | 36 |
| Manifest file-set mismatch | 2 |
| Snapshot digest mismatch | 2 |
| Other | 29 |

These are historical recorded errors, not diagnoses of each row's present condition. In particular, this report does not attribute all 3,544 rows—or even all 36 materialization failures—to planner scope. No other project's full backlog was audited.

`--check --json --project sase` exited successfully but reported cached git diagnostics unavailable and 3,544 quarantine diagnostics. “Ready” and zero active requests do not mean all publication obligations succeeded. The different `active_remaining=2` in the earlier digest is consistent with requests later reaching quarantine.

A blanket `--retry-quarantined` would revive thousands of historical failures without repairing their causes. It would also obscure whether the targeted fix works. Process the planner cases separately, then investigate the older timeout, contention, missing-source, and integrity cohorts in bounded batches.

## Fix choices

| Approach | Assessment |
|---|---|
| Increase timeouts, retry everything, or mute the digest | Does not change the impossible revision association. |
| Acknowledge every request when a page exists | Incorrectly weakens genuine commit-publication guarantees. |
| Remove the planner's queue entry immediately after prompt publication | Loses durable recovery/verification for page and deferred archive work. |
| Explicitly give planner requests existing `linked` semantics | Small, viable containment patch, but overloads a repository-origin name and needs careful request merging and repair. |
| Add explicit planner-prompt scope/intent using the current outbox | Recommended durable design: expresses the real obligation while retaining revision checks for actual commits. |

No new worker, transport, or queue service is needed. The issue is the contract carried by the existing durable request.

### Proposed implementation

- Add an explicit planner-prompt intent to the archive API and persist it in the outbox (for example, a `prompt` scope). The accepted-plan producer selects it explicitly. Commit callers continue to create `revision` requests; linked-repository callers retain their existing behavior. Keep the planner's observed HEAD as provenance, not as an attribution requirement.
- Define the new completion semantics in `sase_core`: canonical agent/session page present, with the existing prompt archive/protection checks still required by the transaction. Use Python for gathering filesystem observations and invoking policy. Update the wire/binding contract, serialization compatibility, and SASE core pin as needed.
- Preserve durable source identity and enough archive context to reconstruct the same approved prompt after lock contention, process interruption, or planner-to-session renaming. Existing rows already carry `artifacts_dir`, `commit_cwd`, and optional `run_id`; do not weaken missing-source handling to make recovery look successful.
- Preserve obligations when requests collide. The existing key is `(global_agent, primary_revision)` and enqueue replaces fields from the incoming item. An archive-only enqueue must not downgrade an existing real-commit obligation. Define and test strict-obligation merging, or distinguish intents in identity if that is necessary for correct acknowledgment.
- Return and report the structured completion decision: required page, request scope, requested SHA, and reason. Distinguish missing page, unreadable snapshot, and absent revision association. A diagnostic improvement should not convert a failed obligation into success.

Existing approval tests mock the planner archive function and verify it was called; that does not cover its interaction with the real queue and completion policy. See [approval archive tests](https://github.com/sase-org/sase/blob/eef22a012481fa8cadd0b9ac315c106eacb66fb0/tests/test_axe_run_agent_exec_plan_followup_approval_archives.py#L28).

### Recover existing rows after fixing production

Implement a report-first, audited repair through the outbox mutation API. Select exact requests whose retained metadata proves approved-plan prompt publication: matching planner artifact/session identity, approved-plan metadata and archive reference, and requested SHA matching the observed planning HEAD. Cross-check commit records so the repair does not discard a genuine commit obligation sharing the same key. Missing or contradictory evidence remains unresolved.

Preserve the original SHA and repair provenance. Re-scope proven planner rows, then explicitly revive a small selected batch. Start with the supplied request. After the repair, the existing bounded retry interface can target it:

```sh
sase agent sync --project sase --retry-quarantined --retry-limit 1 \
  --retry-key 'bbugyi200.athena.sase-1pj.6@2763a6bc58cd74d4882ab97bace343de0c73fa97'
```

This command was **not run** during research, and running it before repairing the obligation is expected to reproduce the error. A new repair command/option described above is a proposal, not an existing CLI capability.

The existing `sase agent sync --project sase --repair-revisions` is a report-only tool without `--apply`, but it solves a narrower problem: it can map an old pre-commit SHA to an evidenced descendant commit, or identify a linked-repository revision. For the supplied request, the Rust classifier returned `unresolved: no recorded run commits for this agent`. It cannot establish planner intent from the absence of commits. Even successful revision repair preserves quarantine state, so repair and retry remain separate steps. See [repair classifier](https://github.com/sase-org/sase-core/blob/f9878e769a2c53f835b898ebfc21344d4e5f2afd/crates/sase_core/src/agent_publication_recovery/stale.rs) and [repair application](https://github.com/sase-org/sase/blob/eef22a012481fa8cadd0b9ac315c106eacb66fb0/src/sase/agents_sync/_publication_revision_repair_apply.py#L74).

### Acceptance criteria

1. Approve a plan in a primary workspace whose HEAD belongs to another agent; with no planner commit, its prompt/page publication drains and acknowledges successfully.
2. Repeat with a solo planner promoted into a session and with a fresh hood containing no committed run.
3. Force initial lock contention or interruption; the durable retry retains planner intent and archives the correct prompt after restart.
4. A real commit request with the wrong SHA remains unfulfilled; missing pages, missing required prompt bytes, and protection failures remain blocked.
5. Mixed planner/commit enqueues cannot downgrade a stricter request; duplicate repair/retry is idempotent.
6. A legacy proven planner row is repairable with an audit record; ambiguous, missing-evidence, or actual commit rows are not broadly re-scoped.
7. The targeted row disappears by verified acknowledgment, the archived prompt and canonical session page remain available, and new accepted plans stop producing this error. Check quarantine counts as well as active counts.

## Recommended solution

**Fix the producer-to-completion contract: add explicit planner-prompt publication intent to the existing outbox, implement its revision-independent completion policy in Rust, and retain strict revision association for actual commits. Then repair and retry only evidence-proven planner rows, beginning with `sase-1pj.6`, and expose the existing structured failure reason in notifications.** An explicit planner override using today's `linked` semantics is a reasonable short-term patch if a smaller release is necessary, but broad retries, timeout increases, queue deletion, and globally relaxed acknowledgment are not fixes for this incident. Treat the thousands of older stopped requests as a separate, measured recovery effort.
