# Agent publication notifications: pages exist, ack demands a foreign SHA

**Researcher:** grk  
**Date:** 2026-10-31  
**Primary evidence:** `~/.sase/axe/error_digests/digest_20261031_100432.txt`  
**Scope:** live `agent_publication` axe errors on athena, the sase project outbox, the agents sidecar, and the ack-gate code in sase plus sase-core.

## Verdict

The notifications are real, repeating, and easy to misread. The publisher **does** write the agent, session, and family pages. The commit-drain ack gate then refuses the outbox row because it demands that the requested primary revision appear on **this** agent's snapshot run. For the rows in today's digest, that SHA is a **different agent's stitch**. Three 15-second job ticks later the row is quarantined, and the next lander or late-finishing hood-mate repeats the cycle.

Existing repair (`sase agent sync --repair-revisions --apply`) will **not** clear these rows. It classifies them as unresolved: the named agent has no commits, or none that descend from the requested SHA.

The durable fix is to treat a published page whose requested SHA belongs to someone else (or to no one) as **linked-scope fulfillment**, and to enqueue linked-scope in that case. Keep revision-scope only when this agent actually produced the named commit. Pair that with an honest error string and stop promoting this class to axe `check_error`.

---

## What the user is seeing

Digest `digest_20261031_100432.txt` is one sample of a day-long pattern:

```
Routine:    publication
Job:        agent_publication
Error:      agent_publication: projects=4 hood_drained=0 link_drained=2
            referenced_by_drained=0 active_remaining=2 lock_busy=0
            deferred_projects=0 errors=1
Exit Code:  0
  dropping projected edge with invalid ref: rule=stitch-bead
    ref='bead:[sase-1g4.2.1.5]'
  [agent_publication] gh_sase-org__sase: published agent page for
    'bbugyi200.athena.sase-1pj.6' did not materialize during commit drain
  Structured job result: check_error · … errors=1
```

Process shape, observed across 2026-10-31 digests:

| Time (EDT) | Agent row | `active_remaining` across the burst |
|---|---|---|
| 00:53–00:55 | `sase-1q5.land` | 1 → 1 → 0 |
| 05:24–05:26 | `sase-1q2.land` | 1 → 1 → 0 |
| 07:51–07:54 | `sase-1q4.land` | 1 → 1 → 0 |
| 08:53–08:56 | `sase-1pj.7` | 1 → 1 → 0 |
| 09:01 then 09:10 | `sase-1pj.6` | 2 → 1 |

The publication lumberjack runs every 15 seconds (doorbell plus `max_quiet: 5m`; `src/sase/default_config.yml` `publication` routine). Default max attempts is 3 (`DEFAULT_PUBLICATION_MAX_ATTEMPTS`). Each doomed drain writes `check_error` even though the process exit code is 0, and axe's lumberjack treats `check_error` as a failed chop, which is what fills `error_digests/`.

On 2026-10-30 the same job also notified for `agent-hood publication did not complete within 120s`. Those rows are already quarantined. Today's live bursts are the materialize class.

---

## Live state (athena, 2026-10-31 ~10:00 EDT)

sase project outbox `~/.sase/projects/gh_sase-org__sase/agents-publication-outbox.json`:

- Schema 7, **3544** rows: **3542 quarantined**, 2 terminal, **0 active**.
- Dominant historical error: `agent-hood publication did not complete within 120s` (2849).
- Second: `agents sync lock is busy` (436).
- **36** rows with `did not materialize` (35 at attempts=3, all quarantined). 31 are `scope=revision`, 5 `scope=linked`.

bob-cli has the same materialize class on landers (`bob-cli-an.land`, `bob-cli-at.land`, `bob-cli-an.6.land`). tailnet's outbox is empty. actstat's two terminal rows are a different error (`hood has no publishable runs`).

The five digest agents are all quarantined with attempts=3, `scope=revision`, `requested_revision=null`, `run_id=null`, and this last_error:

> published agent page for '…' did not materialize during commit drain

---

## The pages are there

Every named agent has all three browsing pages in `~/.sase/projects/gh_sase-org__sase/repos/agents`:

| Agent | `agents/…/README.md` | `sessions/….md` | `families/….md` | Page "Commits" |
|---|---|---|---|---|
| `sase-1q5.land` | yes | yes | yes | 0 |
| `sase-1q2.land` | yes | yes | yes | 0 |
| `sase-1q4.land` | yes | yes | yes | 0 |
| `sase-1pj.6` | yes | yes | yes | 0 |
| `sase-1pj.7` | yes | yes | yes | 0 |

So "did not materialize" is **not** "the sidecar write failed."

---

## Ack gate: what "materialize" actually checks

Drain path:

1. `sase_job_agent_publication` → `run_publication_job` → `drain_selected_agent_publications`.
2. `prepare_publications` calls `publish_hood` for the request's hood, then verifies the owner manifest.
3. After the sidecar commit, `acknowledge_completed` (`src/sase/agents_sync/_commit_publication_transaction_steps.py`) calls `publication_request_fulfilled`.
4. That function returns only a boolean. On false it records the generic string above, increments attempts, and (in current tree) passes `terminal_reason=error`. Live rows still reached attempts=3 and quarantined rather than retiring on the second identical error, which matches the three-strike job bursts.

`publication_request_fulfilled` (`src/sase/agents_sync/publication_completion.py`) is a thin wrapper around sase-core `decide_publication_request_completion` (`crates/sase_core/src/agent_publication_recovery/complete.rs`):

1. Classify the request as session vs run. A name without `--` that has a session/family container is a **session**. All five digest agents are sessions (`sase-1pj.6` has `--gate/--plan/--mon` members; landers the same).
2. Required page: `sessions/<global>.md` for sessions, else `agents/<global>/README.md`. Both exist here.
3. Linked-scope: page existence is enough.
4. Revision-scope: `revision_associated` must find the requested SHA on the matching session container **or** on a member run.

If the snapshot cannot be read, runs and containers are empty. The page still counts as present, so the decision is `required page exists without the requested primary revision`. The Python ack path **drops that reason**.

---

## The SHA on each doomed row belongs to someone else

| Outbox identity | Requested SHA | Git author of that SHA | Snapshot attribution |
|---|---|---|---|
| `sase-1pj.6` and `sase-1pj.7` | `2763a6bc58` | stitch `docs(monitor): …` for **sase-1pj.5.1.land** (`SASE_BEAD=[sase-1pj.5.1]`) | run + session container `sase-1pj.5.1.land` |
| `sase-1q5.land` | `cb230adb5e` | stitch by **sase-1q4.3** (different hood) | **absent** from the sase-1q5 snapshot |
| `sase-1q2.land` | `eec20f6ad5` | stitch by **sase-1q2.6** | run `sase-1q2.6--1` and session `sase-1q2.6` |
| `sase-1q4.land` | `4a4b6fede8` | stitch by **sase-1q4.8** | run `sase-1q4.8--3` and session `sase-1q4.8` |

Each agent's own snapshot runs have **zero commits** carrying that SHA. Some land members do have a commit, but a **different** one (`sase-1q4.land--code` carries `9b880fbf…`; `sase-1q5.land--1` carries `e32449da…`).

Outbox provenance shows these rows were enqueued **as those agents**, from their own ACE artifact dirs, using a workspace HEAD that another agent had already committed:

| Agent | `commit_cwd` | `artifacts_dir` (ACE run) | Enqueued (EDT) | SHA commit time |
|---|---|---|---|---|
| `sase-1q5.land` | `…/sase_14` | `20261030184159` | 00:45 | 00:15 (`sase-1q4.3`) |
| `sase-1q2.land` | `…/sase_13` | `20261030123856` | 05:23 | 04:37 (`sase-1q2.6`) |
| `sase-1q4.land` | `…/sase_14` | `20261030174519` | 07:39 | 07:11 (`sase-1q4.8`) |
| `sase-1pj.7` | `…/sase_16` | `20261028203150` (Oct 28 run) | 08:52 | 08:36 (`sase-1pj.5.1.land`) |
| `sase-1pj.6` | `…/sase_21` | `20261028203149` (Oct 28 run) | 08:56 | 08:36 (same SHA) |

`sase-1pj.6` and `sase-1pj.7` sharing one SHA from a third hood-mate, minutes after that lander committed, is the same shape as the landers: a later `sase stitch create` in a workspace whose HEAD is someone else's stitch, with `publication_agent` still equal to the finishing agent.

Enqueue (`src/sase/agents_sync/_commit_publication_queue.py`) projects the committing turn through `sase_agent_ref_for_turn` (session member → session) and stores `cp.commit_sha` / HEAD as `primary_revision`. Scope is `revision` for a primary checkout and `linked` only for linked/sidecar cwd. A lander or failed session that still runs the commit workflow against a primary tree therefore stores **whatever HEAD is**, then the ack gate asks the snapshot "did *you* make this commit?"

Whole-hood publish is why the pages exist anyway: `publish_hood` rewrites every run in the hood. The ack is per outbox row, not per hood.

---

## Why prior fixes do not cover this

**sase-1nj** (closed 2026-10-26) was the same *symptom* with a narrower cause: a worker row named the **pre-commit** workspace HEAD, and the published run carried the **post-commit** stitch. Offline `decide_publication_request_completion` returned `required page exists without the requested primary revision`. Fix: sase-1nv.3 names the post-commit SHA; sase-1nv.4 adds `--repair-revisions`.

That repair classifier (`complete.rs`'s sibling `stale.rs` / `classify_stale_publication_request`) can:

- leave the row unchanged (SHA already on this agent's runs, or already linked-scope),
- switch to linked-scope if the SHA is a **linked-repo** commit,
- rekey to the earliest run commit that **descends from** the requested SHA,
- otherwise **unresolved**.

For today's rows:

- this agent's `run_commit_shas` is empty → unresolved ("no recorded run commits"),
- or the SHA is on a **different** agent → unresolved ("no recorded run commit descends from the requested revision").

sase-1nv.5 (prove recovery on both hosts) is still in progress. It does not change this classification.

**sase-1oh.5.1** remaining work (B) is adjacent but distinct: a **withheld** (secret-scan) run beside clean siblings is still retired as generic "did not materialize". `acknowledge_completed` already parks withheld runs without that string; the leftover is a withheld *sibling* inside a published hood. Not what the digest rows are.

**sase-1pt** (commit stage ends at durable enqueue; nested epic sase-1pt.9 still in progress) is why these failures are axe notifications instead of a blocked stitch. The background job is doing its job. The ack policy is wrong for foreign SHAs.

**sase-fh** (closed) was "family-lane pages ignored by the full-sync check." Today's required page is the session page, and it exists.

---

## Secondary line in the same digest

`dropping projected edge with invalid ref: rule=stitch-bead ref='bead:[sase-1g4.2.1.5]'` is **not** the publication failure.

Stitch trailers still parse the historical `SASE_BEAD=[bead-id]` shape. `project_stitch_rules` emits `bead:[sase-…]`; `_edge_refs_valid` drops it and logs a warning (`src/sase/artifact_links/projection/_entry.py`). Tests in `tests/artifact_links/test_stitch_rules_projection.py` pin this. The 09:10 digest also had `link_drained=2`, so the job did useful link work in the same tick.

The 09:04 digest's other error, `artifact_link_backfill` killed after 300s on `gh_sase-org__sase` after re-reducing 2515 streams, is a separate housekeeping timeout.

---

## Options

### A. Ack-gate policy: foreign or empty commits + page exists → fulfill (recommended, with C)

Change `decide_publication_request_completion` (sase-core) so revision-scope is fulfilled when:

- the required page exists, and
- either the matching run/session has **no** commits, or the requested SHA is recorded on **another** run in the same snapshot (or is simply absent from this agent).

Record a distinct reason, e.g. `required page exists; requested revision is not this agent's commit`. Mirror that string in Python instead of "did not materialize".

**Cost:** a row can ack without proving this agent authored the SHA. That is the correct meaning for a hood republish of a 0-commit session. **Do not** skip the page-existence check.

### B. Enqueue linked-scope unless this agent owns the SHA

After `create_commit`, if the stitch SHA is missing from this agent's attributed commits (empty commit, reused HEAD, late stitch), enqueue `scope=linked`. Keep `revision` only when the SHA is on this agent's run.

**Cost:** needs a snapshot or stitch-attribution read at enqueue time, or a footer/SHA ownership check. Complements A: new rows never enter the doomed state.

### C. Repair classifier: `foreign` → linked

Extend `classify_stale_publication_request` with a `foreign` (or reuse `linked`) action when the SHA is in the primary repo and/or another snapshot run, the page exists, and this agent's runs do not carry it. Then `sase agent sync --repair-revisions -p gh_sase-org__sase --apply` (and bob-cli) clears the 36 materialize rows.

**Cost:** one-shot backlog only, unless A/B also land. Without A/B, the next lander re-creates the row.

### D. Notification-only: stop `check_error` for this string

`sase_chop_agent_publication.py` sets `check_error` whenever `tick.errors > 0`. Parked foreign-SHA rows could be diagnostics, not errors.

**Cost:** silence without fixing ack. Next drain still burns three attempts. Acceptable as a **temporary** companion to A/B, not as the fix.

### E. Drop or `--retry-quarantined` the 36 rows

Dropping is safe for browsing (pages exist) and loses the durable "this request was owed" record. Retrying without A/B **re-fires the notifications**.

### F. Only retry `--repair-revisions` as it exists today

Observed classifier outcome is unresolved. No outbox change, no ack, no relief.

---

## Recommended solution

Land **A + B + C** as one change set (sase-core policy first, then sase pin, then Python enqueue + repair + error text). Use **D** only if notifications must stop before the pin moves.

Concrete sequence:

1. **sase-core** (`complete.rs`): if the required page exists and `revision_associated` is false, fulfill when the matching session/run has empty `commit_shas`, or when the requested SHA appears on a *different* observed run. Keep failing when the page is absent. Add unit tests for: 0-commit session + foreign SHA + page present → fulfilled; page absent → still false; this agent's own SHA → still the current success path.
2. **sase-core** (`stale.rs`): new action mapping those rows to linked-scope (or the same fulfill-without-rekey path) so `--repair-revisions --apply` is the operator tool for the 36 existing rows plus bob-cli's landers.
3. **sase** (`acknowledge_completed`): persist `decision.reason`; do not collapse to "did not materialize". Do not charge `check_error` for the new foreign/empty-commit reason (job counter can still mention it in diagnostics).
4. **sase** (`_enqueue_committed_agent_publication`): if the named revision is not this agent's attributed stitch, enqueue `PUBLICATION_SCOPE_LINKED`. Primary-checkout revision-scope stays for real stitches.
5. **Pin** `sase-core-revision.txt` past the core commits before relying on the new binding.
6. **Operate:** `sase agent sync --repair-revisions -p gh_sase-org__sase --apply` and the same for `gh_bobs-org__bob-cli`. Do **not** `--retry-quarantined` the materialize rows until step 1 is installed. Leave the 2849 timeout rows for a separate drain-budget pass.

Do **not** wait on sase-1nv.5 or sase-1pt.9. Those epics own recovery proof and publisher re-prove. This is a new ack-identity bug: the row names the right agent and the wrong commit.

The stitch-bead `bead:[…]` warning can stay a follow-up: strip wiki-link brackets in the stitch parser so the projection rule never emits an invalid ref. It is not what is paging you.

---

## What not to do

- Do not treat missing pages as the diagnosis. They are present.
- Do not `sase agent sync --retry-quarantined` these rows on today's installed policy.
- Do not broaden `revision_associated` to "any SHA anywhere in the hood fulfills any row." That would ack a worker row against a neighbor's stitch even when this agent's page was not published. The fulfill extra is **page exists** plus **this agent did not make that commit**.
- Do not confuse this with the 120s hood timeout backlog. Same job, different failure class, already quarantined.

---

## Sources

- Digest: `~/.sase/axe/error_digests/digest_20261031_100432.txt` and the 2026-10-31 / 2026-10-30 `agent_publication` digests.
- Outbox: `~/.sase/projects/gh_sase-org__sase/agents-publication-outbox.json`.
- Sidecar snapshots: `…/repos/agents/users/bbugyi200/machines/athena/hoods/{sase-1pj,sase-1q2,sase-1q4,sase-1q5}/snapshot.json`.
- Code: `src/sase/agents_sync/_commit_publication_transaction_steps.py`, `publication_completion.py`, `publication_job.py`, `sase_chop_agent_publication.py`, `_commit_publication_queue.py`, `publication_outbox_operations.py`, sase-core `agent_publication_recovery/complete.rs` and `stale.rs`.
- Beads (audited read): `sase-1nj`, `sase-1nv` / `.3` / `.4` / `.5`, `sase-1pt`, `sase-1oh.5.1`, `sase-fh`.
