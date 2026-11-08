# Athena SASE error digests: missing sidecars, repeated retries, and historical failures

Independent investigation by researcher **cdx**, 2026-11-08. No other report, transcript, or findings from this research swarm were consulted. This is a diagnosis and recommendation; no production configuration, repository provisioning, cleanup, or recovery changes were applied.

**The example digest has one immediate cause repeated 100 times:** the publisher cannot clone `git@github.com:sase-org/sase-spotify--agents.git`. The broader recent notifications have several causes. The current dominant problem is incomplete sidecar initialization combined with a legacy-store compatibility gap and a repository-failure retry loop. Earlier incidents include scanner-protected publication, missing publication evidence, inefficient maintenance scans, authentication failures, lock contention, and two repository-integration verification failures.

**Recommended direction:** finish and verify `sase-spotify`'s sidecar setup while preserving its existing combined SDD data; add repository-level publication backoff and capability-aware sidecar readiness; retain the already-landed maintenance fixes and recover historical publication obligations separately. Restarting SASE or suppressing notifications alone will not repair the current failures.

## Scope and evidence quality

I read the supplied Athena digest and programmatically classified all **109 November digest files available through `digest_20261108_064118.txt`**, containing **5,848 recorded error entries**. Their event timestamps range from November 1 at 12:42:24 to November 8 at 06:40:59, both with `-05:00` offsets. I also examined selected job logs, publication outbox/heartbeat/protection metadata, current project and repository inventory, repository metadata on GitHub, and the relevant source code and commit history.

Athena's timestamps in this report are EST (`UTC−05:00`) unless explicitly marked UTC. The supplied digest was created at 11:41:18 UTC, not 06:41 UTC. Live observations were collected approximately 06:46–06:54 EST. I did not extend this investigation to the entire July–October archive. The counts describe retained digest entries, not unique incidents or a complete execution census: the error store keeps only 100 rows and can lose coverage during a storm.

The notification corresponding to the user's example is:

- ID: `8043d5a9-360e-4b64-9d09-e94b5c9f1bee`.
- Sender: `axe`; timestamp: `2026-11-08T06:41:18.541872-05:00`.
- At inspection: unread, priority, not dismissed, muted, or silent.
- Attachment: `athena:~/.sase/axe/error_digests/digest_20261108_064118.txt`.
- Attachment SHA-256: `a03aeac90f180a8f00a698aad8fbda6f975774b381ed2f15f42524acde935f6b`.

Athena reported Python SASE version `0.18.1+444.g35e4d88ef`, matching the investigated checkout `35e4d88efc5a294a9038d04f7f892058391c68c8`; `sase-core-rs` reported `0.44.0`. The linked Rust source examined was `317ea6a1252710e1d6c44d7289eb856f994950e0`; the package version alone does not prove that exact compiled Rust revision. The service had restarted at **06:41:15 EST**, and the same clone failures continued afterward.

## Inventory of the errors

The following classification accounts for every entry in the November corpus. Publication rows containing several symptoms are classified by their dominant diagnostic, giving SSH authentication precedence over protection messages.

| Error family | Recorded entries | Assessment |
| --- | ---: | --- |
| `agent_publication`: missing Spotify agents repository | 736 | Confirmed, still recurring during investigation; all 100 entries in the supplied digest |
| `agent_publication`: run/prompt withheld by publication protection, sometimes also unresolved prompt evidence | 5,005 | Historical retry storm; underlying protection and recovery obligations remain |
| `agent_publication`: SSH authentication denied | 62 | Confirmed historical transport failures; five rows also mention protection |
| `agent_publication`: requested revision absent from published page, without protection diagnostic | 2 | Confirmed failed acknowledgment; two additional mixed rows are counted in protection above |
| `agent_publication`: missing Python import | 1 | Confirmed historical module inconsistency; exact deployment cause unproven |
| `agent_publication`: whole job exceeded 300 seconds | 2 | Confirmed timeout; the retained digest output does not identify the stalled operation |
| `agent_publication`: hood drain exceeded 120 seconds | 1 | Confirmed; retained timing metadata shows expensive inventory/render work |
| `artifact_link_backfill`: 300-second timeout | 14 | All end at the SASE project's outbox drain; scaling fix is present and recent runs succeed |
| `artifact_run_prune`: `protection_unavailable` | 11 | Missing Spotify beads/plans protection sources; newer live logs show it still occurs |
| `artifact_run_prune`: 300-second timeout | 1 | Confirmed; insufficient retained stage detail for a precise sub-operation diagnosis |
| `workspace_sdd_clone_recovery`: upstream ancestry verification failed | 2 | Confirmed integration invariant failure; moving-upstream race is a plausible mechanism |
| `external_issue_mirror`: `auth_error` | 6 | Three tailnet, two actstat, one bob-cli; workspace Git authentication failed |
| `toobig_split[sase]`: operational lease preparation authentication failure | 1 | Same SSH failure family |
| `gate_turn_reclaim`: `reclaim_errors` | 2 | Five-second per-gate follow-up lock contention |
| `sidecar_auto_sync`: 120-second timeout | 1 | Confirmed; output absent |
| `stale_running_cleanup`: 90-second timeout | 1 | DNS failure appears in its output; slow/failing workspace preparation contributed |
| **Total** | **5,848** | **5,809 publication entries and 39 other entries** |

## 1. Current publication storm: missing repository plus unbounded repeated admission

The supplied digest spans **06:08:52.621123–06:40:59.146754 EST**, only **32 minutes 6.526 seconds**. Every entry contains the same project and clone failure:

```text
[agent_publication] gh_sase-org__sase-spotify:
  could not clone configured agents sidecar
ERROR: Repository not found.
fatal: Could not read from remote repository.
```

The median interval between recorded failures is **16.958 seconds**. The varying temporary checkout name is incidental; these are repeated attempts against the same configured remote.

Read-only live checks corroborate the failure:

| Inventory item | Athena state | Remote metadata check |
| --- | --- | --- |
| Primary `sase-spotify` | Enabled, launchable, no active claims at inspection | Exists; private; connected GitHub account has admin access |
| `agents` | Hidden clone absent; inferred remote `sase-org/sase-spotify--agents` | GitHub connector returns 404; Athena's `gh repo view` cannot resolve it |
| `beads` | Expected `sase-spotify--beads` clones absent | GitHub connector returns 404 |
| `plans` | Expected `sase-spotify--plans` clones absent | GitHub connector returns 404 |
| Combined SDD store | Existing `.sase/sdd` clone; storage `separate_repo`; remote `sase-org/sase-spotify--sdd` | Exists |

A read-only SSH authentication check **from Athena** successfully authenticated to GitHub as `bbugyi200`. This distinguishes the current missing-repository failure from November 4's `Permission denied (publickey)` incidents. A GitHub 404 cannot universally distinguish absence from inaccessible private content, but the inferred default names, working primary access, repeated authenticated clone failures, and independent metadata checks strongly support **unprovisioned or incorrectly routed sidecars**, rather than a general SSH outage. The available evidence does not establish who created the legacy store or whether a missing repository was ever deleted.

The publication state explains why it keeps trying:

1. Athena's Spotify outbox has **two pending revision-scoped requests**, both from `chop.refresh_docs.sase-spotify.2_471527` session members. They still have `attempts=0`, `last_error=null`, no parked reason, and are neither quarantined nor terminal.
2. Target selection accepts an agents inventory row with an inferred remote URL; it does not require a successfully provisioned remote.
3. `drain_agent_publications()` calls `ensure_agents_clone()` and classifies clone failure as a **repository-scoped** failure.
4. The Rust failure-accounting policy deliberately does not charge repository failures against individual publication requests. Thus the row-level retry/quarantine threshold cannot stop this incident. That policy protects valid requests from being discarded because infrastructure is broken.
5. The job retains active work and rings the publication doorbell again. The routine checks every 15 seconds; the next pass repeats the clone. There is no comparable repository-unavailability cooldown on this path.
6. Each failed pass sets structured result status `check_error`, so the scheduler records another error even though the script process exits zero.

At `2026-11-08T11:48:38.606188+00:00`, the publisher heartbeat showed Spotify `active_count=2`, `last_outcome="repository_error"`; the other seven projects were idle with zero active requests. Post-restart logs `20261108T064803_083708`, `064820_025494`, and `064836_881337` still report the same clone failure. This is persistent configuration/readiness failure, not a crash cured by restarting the host.

Source: [publication job](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/agents_sync/publication_job.py#L96), [clone/drain classification](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/agents_sync/_commit_publication_drain.py#L112), [Rust failure accounting](https://github.com/sase-org/sase-core/blob/317ea6a1252710e1d6c44d7289eb856f994950e0/crates/sase_core/src/agent_publication_recovery/accounting.rs#L14).

## 2. The same incomplete setup blocks retention; legacy connectivity hides the missing capabilities

`artifact_run_prune` needs authoritative beads and plans references before deleting old run artifacts. Its protection collector requires both roles for each inventoried project. The November 8 log `20261108T064117_560573.log` reports:

```text
protection source unavailable: sase-spotify:beads
protection source unavailable: sase-spotify:plans
candidates=24307 selected=2634 bytes=1258243043
protected=21673 unavailable=2 reason=protection_unavailable
```

The purge performed no deletion. The roughly 1.26 GB is the preview's candidate volume, not proof that it is safe to reclaim while those sources are unavailable. This is a justified refusal caused by missing protection coverage.

There is a specific compatibility gap beyond “the project has never been launched”:

- The inventory recognizes the existing combined `sase-spotify--sdd` store, while also injecting missing split plans/beads rows.
- Retention's `_record_has_role()` matches a role name or a `--beads` / `--plans` suffix. A combined `--sdd` row does not satisfy either role.
- `sdd_store_connected()` considers a positive materialized legacy `separate_repo` record connected.
- `_unconnected_candidates()` selects only projects for which that predicate is false. `auto_connect_sdd_store()` likewise returns immediately for an already-materialized record.

Consequently **“connected” and “has every required sidecar capability” are different states**. The automatic connector skips this project, and retention cannot find its required roles. Recent sidecar-sync logs report `missing=2` on a due pass, `connected=0`, `connect_failed=0`, and overall status `ok`; its schedule contains Spotify `:beads` and `:plans` entries, but no pending `:__connect__` entry. A green sidecar-sync job therefore does not establish complete protection coverage.

Commit [`5922991bcf`](https://github.com/sase-org/sase/commit/5922991bcfee7ab2d9afc615811da430ffd95a20), November 7, added first-use automatic connection and clearer missing-source labels. It is present in the inspected build. It only connects existing remotes for unconnected projects; it neither provisions absent remotes nor repairs this already-connected legacy layout. The change from “sidecars not connected on this machine” in November 7 digests to bare role labels on November 8 is consistent with this distinction, rather than evidence that all roles became healthy.

Source: [inventory handling of combined and split stores](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/repo_inventory.py#L296), [required protection roles](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/core/agent_artifact_run_protection.py#L126), [role matching](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/core/agent_artifact_run_protection.py#L453), [auto-connect eligibility](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/_sidecar_auto_connect.py#L82), [materialized-record short circuit](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/sdd/_auto_init.py#L20).

## 3. Historical publication protection, missing evidence, and quiet unfinished work

Most November 1–4 publication errors concern bob-cli and say “run withheld by publication protection” or “prompt archive withheld by publication protection.” Some also report that a deferred prompt cannot be restored: a missing local source is not proof that no prompt obligation existed. These are real publication refusals, not Python exceptions.

The current bob-cli protection ledger corroborates scanner involvement without needing to expose candidate bytes:

- 46 blocked content records remain: 43 `openai-key` evidence entries, two `env-dump-window`, one `structured-env-dump`.
- 15 older records are superseded with `reason="rescanned_clean"`; the inspected supersession example moved to scanner rules version 2.
- These metadata establish scanner hits and subsequent clean rescans. They do **not** prove that every blocked candidate was a real credential, nor that every remaining hit is a false positive.

Commit [`1b62dfb9bd`](https://github.com/sase-org/sase/commit/1b62dfb9bdb52b9a81a7755f8f6184c5d1cc2ec2), November 4, added parking for protection-withheld requests. The old storm ends around that rollout in the retained digests. However, current bob-cli outbox metadata contains **297 quarantined requests and five terminal requests**, with none active at the heartbeat observation. Across those 302 historical rows, stored reason families are 234 unresolved prompts, 63 missing pages, two snapshot-digest mismatches, two missing requested revisions, and one other failure. These counts include older work; they are not additional November incident counts.

**No current retry does not mean successful publication.** Repair must classify and recover the evidence for selected rows; indiscriminate retrying, acknowledging them manually, or disabling scanners would hide the original contract failure. The existing report-first revision repair is useful for stale revision requests, but cannot conjure missing prompt bytes.

Two standalone digest rows for `bob-cli-f5.land` specifically require revision `f1ead7bf6499`, absent from the published session page. Two mixed protection rows later concern `bob-cli-h4.2` and revision `029b426601d6`. The repository contains an explicit stale-revision repair path for requests enqueued before a post-commit revision fix. That establishes a known mechanism and repair route; the digest alone does not prove that every affected row was created by that historical bug.

Source: [withheld-request semantics](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/agents_sync/_publication_snapshot_hood.py#L59), [report-first revision repair](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/agents_sync/publication_revision_repair.py#L34). Runtime evidence: `athena:~/.sase/projects/gh_bobs-org__bob-cli/agents-publication-protection.json` and `agents-publication-outbox.json`, inspected as metadata only.

## 4. Maintenance and publication timeouts have measurable scaling costs

All **14** retained `artifact_link_backfill` timeouts end with the last progress line `gh_sase-org__sase: drain`. The November 6 07:49 run spent **190.23 seconds on bob-cli** before reaching SASE, including 65.66 seconds sweeping and 98.14 seconds draining. The November 7 11:40 run spent 98.89 seconds on bob-cli, including 61.02 seconds reconciling, before timing out in the SASE drain.

The implementation had expensive repeated work within that drain: rereading release-evidence JSONL per queued row, insufficient deadline checks within eligibility processing, repeated catalog construction, and full queue rewrites even without progress. This is a scaling and deadline-enforcement problem, not a reason to merely raise the 300-second kill threshold.

Commit [`5692321a2e`](https://github.com/sase-org/sase/commit/5692321a2e827eefd440f3ebb35f8f645d8c6397), November 7, addresses those exact paths: one validated evidence index per pass, one queue read, inner-loop deadline checks, less rewriting, lazy shared catalogs, persisted stale-check cadence, and fairer deferral. The historical 11:45 timeout does not by itself disprove the fix: a commit timestamp does not prove when a running job loaded the changed code. More decisively, **three inspected November 8 runs** (`054923_368518`, `055916_457615`, `064117_564222`) finish `ok`, with eight reconciled projects, zero failed/deferred projects, and the new phase timing fields. The improvement is deployed and observed; it should be retained and monitored.

The separate 120-second bob-cli publication failure has useful timing evidence. A drain recorded at **2026-11-07 16:01:43 UTC** reports the 120-second alarm, 61.19 seconds in `inventory_build`, 32.15 seconds in `hood_publish:research` (nested inside 34.47 seconds of `prepare`), and 12.10 seconds in commit. Its alarm stage is `cleanup`. Those durations should not all be added together because some stages nest, but they demonstrate that catalog/render work consumes most of the budget. This supports incremental or exact-request discovery and propagation of the remaining global budget into nested work.

The two 300-second publication-job timeouts have absent subprocess output. The 300-second prune timeout on November 6 only shows that trash purge had finished before the subsequent work stalled. The 120-second sidecar-sync timeout also has absent output. Their exact blocking operation cannot be reconstructed from those digests; attributing all three to one particular lock or network call would overstate the evidence. Preserve per-stage timing and stack/proc diagnostics before killing such jobs, and verify all network, lock, catalog, and reconcile operations respect a common remaining deadline.

Runtime timing source: `athena:~/.sase/logs/agent_publication_drains.jsonl.1`. Backfill progress sources are the logs named inside `digest_20261106_084909.txt` and `digest_20261107_120333.txt`.

## 5. Authentication and DNS incidents are distinct from missing sidecars

November 4 publication, external issue mirror, and `toobig_split` errors contain:

```text
git@ssh.github.com: Permission denied (publickey).
```

For the six external-mirror entries, the failure is in **operational workspace preparation**, before the issue-mirroring work can proceed; it is not evidence of an expired issue API token. `toobig_split` fails at the same preparation boundary. Service processes lacking a usable unattended SSH identity, often because they inherited a dead or empty SSH-agent socket, are a plausible common explanation. The retained messages even identify that possibility. The old process environment/key state was not preserved here, so the particular credential-lifetime failure remains an inference.

The November 6 `stale_running_cleanup` timeout instead includes:

```text
ssh: Could not resolve hostname ssh.github.com:
Temporary failure in name resolution
```

Its output says a leaked monitor claim for workspace 14 was retained with other dirt. This is evidence of DNS-dependent preparation failing and conservative claim retention, not evidence that deleting the workspace would fix the underlying problem. Sidecar-sync timed out around the same time, but its empty output is insufficient to assign it the same cause conclusively.

The current Athena SSH check succeeds and publisher work on other projects succeeds. That establishes current availability, not reliable credentials or DNS across future restarts. Validate credentials in the service's effective environment and use an unattended identity whose lifetime is independent of a login shell; retain bounded retry for transient DNS/network failures.

## 6. Lock contention, integration races, and one module import inconsistency

**Gate reclaim:** on November 5, gate `18i--gate` could not acquire `.gate_followup.lock` within five seconds; the diagnostic names holder PID `2627768`. On November 7, `sase-1rs.11--gate` hit the same timeout with holder PID `2356907`. Both paths use the same per-gate follow-up lock as settlement. The reconciler wraps the lock timeout as a `GateError`, increments its errors, and publishes `reclaim_errors`. A valid concurrent holder can therefore become an error notification. The old PIDs alone do not prove deadlock or stale ownership. Routine contention should be a bounded deferred result with eventual progress tracking; prolonged no-progress contention should remain actionable. Do not delete a lock based only on its filename.

Source: [five-second follow-up lock](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/gate_turn/handoff.py#L50), [reconciliation lock acquisition](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/gate_turn/_handoff_reconcile.py#L219).

**SDD recovery:** two digests, November 2 and 4, report bob-cli's machine beads clone holding unpublished commits, followed by `completed SDD integration does not contain upstream with exit code 1`. This exact message is emitted when the post-integration `git merge-base --is-ancestor <upstream> HEAD` check fails. The source fetches before acquiring its cooperative store write lock, then uses the symbolic upstream ref throughout rebase and final verification, despite resolving it earlier. A concurrent fetch can move that reference after the rebase target was chosen. That is a concrete plausible race: the final check asks about a newer upstream than the one integrated. Logs supplied here do not prove that race occurred rather than another repository mutation. A robust fix pins the intended upstream OID inside the transaction, verifies against that OID, and treats later upstream movement as new integration work while preserving unpublished commits.

Source: [transaction/fetch ordering and symbolic upstream](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/sdd/_repository_integration.py#L46), [failed ancestry invariant](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/sdd/_repository_integration.py#L328).

**Import inconsistency:** one November 1 publication entry cannot import `AgentRunStateDiscoveryWindowRequestWire` from `sase.core.agent_run_state_wire`. Commit `a0b00da79b` introduced the bounded-discovery work that day; the current module exports the symbol. An editable checkout changed beneath an already-running interpreter is a plausible explanation for callers and imported modules observing different revisions, but a complete historical process/module snapshot was not available. Treat this as a historical deployment/module-consistency failure, not as the cause of the current repository-not-found storm. Prefer coherent service rollouts and restart processes after interface changes.

## 7. The notification pipeline amplifies repetition and undercounts errors

The latest notification says “100 error(s) in the last hour,” but the attached 100 rows span only 32 minutes. The code explains why:

1. `append_error()` truncates `recent_errors.json` to its last 100 rows.
2. The hourly digest reads those retained rows, filters by a one-hour cutoff and its last-notified timestamp, and advances its checkpoint after notifying.
3. Repeated clone failures are distinct timestamped rows. They are not grouped by a stable project/error signature.

At roughly one error per 17 seconds, 100 retained rows cannot represent a full hour. The storm can evict less frequent errors before the next digest, so **the notification count is not a complete hourly total** and “only publication failures in this digest” does not mean the other jobs were healthy. Live prune logs demonstrate that other failures continue.

The zero process exit code in clone/prune entries is not evidence of successful work: `check_error` is part of the job-result protocol and intentionally causes scheduler error recording. This report's distinction is between process completion and job outcome, not a recommendation to change every such exit code.

Source: [100-row retention](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/axe/_state_scheduler.py#L175), [digest window/checkpoint](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/scripts/sase_chop_error_digest.py#L18), [structured publication error status](https://github.com/sase-org/sase/blob/35e4d88efc5a294a9038d04f7f892058391c68c8/src/sase/scripts/sase_chop_agent_publication.py#L12).

## Recommended solution

1. **Repair Spotify's sidecar readiness first.** Use the repository workflow to inspect `sase repo init --check`, then perform a reviewed initialization/migration that provides the required plans and beads stores and the agents repository used by the two pending publication requests. Preserve and reconcile any durable content in the existing `sase-spotify--sdd` store before changing authoritative routing; creating empty split repositories alone is not evidence that legacy data was migrated. Review actual remote names and visibility in the initialization proposal. The supported initializer asks before creating missing remotes. This research does not authorize or perform that creation. Verify afterward that inventory resolves real readable plans/beads sources and a usable agents clone, then allow the two pending requests to publish and verify their acknowledgments. Do not clear their outbox to silence the errors.

2. **Make readiness describe the required roles, and add a repository cooldown.** Replace the single materialized-store predicate used for readiness decisions with a role/capability result distinguishing unconfigured, intentionally disabled, missing remote, disconnected clone, legacy-compatible store, and ready. Either map supported combined-store content to authoritative roles or require an explicit migration; do not claim readiness solely because a combined record exists. Publication must keep repository failures separate from request attempt counts, but persist `next_retry_at`, reason, first/last occurrence, and a capped exponential backoff keyed by project/remote. Reset eligibility when configuration or remote readiness changes. This prevents a valid uncharged request from causing a fresh clone every 15 seconds.

3. **Finish historical recovery with evidence.** Keep scanner protection and retention refusal intact. Review bob-cli's quarantined/terminal rows separately from active publication; use report-first revision repair for stale revisions, recover prompts/pages only from verified sources, and rescan exact bytes using current rules before publication. An idle heartbeat must not be the sole completion criterion. Preserve the backfill indexing/deadline fixes already deployed, and confirm recurring maintenance remains within budget. For the unresolved empty-output timeouts, collect stage/proc evidence on the next recurrence instead of claiming an unproven cause or simply increasing timeouts.

4. **Harden the smaller independent failure paths.** Validate unattended Git credentials in the service environment and bounded DNS/network retries. Represent ordinary gate-lock contention as deferred work with a retry and a no-progress escalation threshold. Pin the fetched upstream commit for SDD integration and record both intended/current upstream OIDs on verification failures. Roll out Python/core interface changes coherently so long-lived processes cannot mix module generations.

5. **Make digests count incidents without losing events.** Retain durable error events for the whole reporting window, group notifications by stable project/job/error-class/remote signature, and show first/last occurrence, repetition count, representative diagnostics, and recovery status. Exclude temporary clone directory names from the fingerprint. Emit a clear coverage/truncation indicator when full counts cannot be established. This complements fixing the underlying failures; it does not substitute for repair.

Implement shared readiness, retry classification, and recovery policy in `sase_core` with bindings and thin Python orchestration, following the repository's backend boundary. Regression coverage should include an enabled project with only a legacy `--sdd` store, an absent agents remote with pending requests, healthy projects alongside one failing project, recovery after provisioning, protected bytes remaining unpublished, deadline exhaustion inside a large queue, live gate-lock contention, and an upstream ref moving during integration. Acceptance evidence is **successful required publication plus complete protection coverage and bounded background execution**, not just a quieter inbox.
