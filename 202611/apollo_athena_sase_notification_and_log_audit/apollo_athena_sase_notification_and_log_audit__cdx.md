# SASE notification and error-log audit: Apollo and Athena

Independent report by **cdx**, 2026-11-19. Evidence collection began around 09:59 UTC and the main inventory snapshot began at 10:03 UTC. Later checks verified current code and runtime behavior. No other researcher's report, findings, or chat was consulted.

## Findings that matter

There are worthwhile fixes here, but the largest historical error count is misleading: **1,893 Apollo digest entries came from one unmanaged-project publication problem that already has a deployed fix.** It should not become another implementation task.

The strongest remaining opportunities are preventing another Apollo disk-exhaustion incident; repairing a reproducible Python/Rust artifact-link contract mismatch; making deferred publication finish reliably without losing prompt evidence; protecting running work from updates; preserving diagnostic counts during error storms; and reducing measured TUI stalls. These recommendations address observed failures, data preservation, or measured responsiveness. They do not depend on a preference for a new architecture or a different interface.

This was an audit, not a repair run. I did not dismiss notifications, restart services, change configuration, delete files, replay publication queues, or alter product code. The only durable deliverable is this report and its registered snapshot.

## Scope, method, and limits

I used `sase notify list -j -a -l 100000` on both machines, then read the live and archived notification JSONL stores because the ordinary inbox is not the whole historical record. Rows were deduplicated by notification ID, with the live row taking precedence. I inventoried retained scheduler digests and operational logs, scanned scheduler warning/error patterns, inspected relevant attached digests, and examined selected structured telemetry and current source. Athena was accessed read-only through its configured SSH alias.

The detailed incident window is **November 12–19**, with November-wide notification counts and all-retained-history inventory for context. Notification/digest date filtering uses the recorded local calendar date; current examples have `-05:00` offsets. TUI telemetry uses epoch timestamps with a November 12 00:00 UTC cutoff. These are not precisely identical seven-day windows. Collection was live, not a transactional snapshot; files rotated and acquired new rows during collection. Counts below are observations, not lifetime totals or failure rates.

To preserve swarm independence, the main aggregate scan conservatively excluded rows mentioning the four peer identities or their report filename suffixes. That also excludes some unrelated older research-notification rows. Aggregate notification counts are consequently **lower bounds on eligible retained history**, not the exact size of each entire inbox. No report content was opened. Focused operational follow-up queries excluded this swarm's identity and did not consult reports or transcripts.

| Retained evidence reviewed | Apollo | Athena |
|---|---:|---:|
| Eligible unique notifications, live + archive | 6,518 | 25,089 |
| Earliest retained notification in that set | Aug 31 | Jul 6 |
| Eligible November notifications | 1,967 | 3,606 |
| Eligible Nov 12–19 notifications | 853 | 1,480 |
| Retained scheduler digest files inventoried | 436 | 726 |
| Error records parsed from those digest files, all dates | 18,818 | 12,139 |
| Nov 12–19 digest error records | 2,050 | 95 |
| Publication errors among those recent digest records | 1,917 | 45 |

The focused digest pass deduplicated recent records by timestamp, job, and error text and returned the same recent totals: 2,050 and 95. Those records are attempts/errors, not distinct root causes.

Operational sources included `~/.sase/axe/logs/`, `~/.sase/axe/error_digests/`, `~/.sase/logs/` including rotations, selected `~/.sase/service/procs/*/output.log`, and user-journal warnings mentioning SASE. I inventoried scheduler per-run storage but did not read every per-agent output or transcript. I did not inspect system crontabs, every system journal, every project-specific log, or old research documents. Successful commands and normal safety refusals were not counted as bugs merely because their text included “failed”, “error”, or “protected”. In particular, counters such as `failed=0` are not failures.

Both machines reported host version `0.19.0+196.g065eda332` and Rust core `0.44.2+43.g6f8f016e8`. Apollo runs Python 3.12.3; Athena runs Python 3.14.7. Both user `sase.service` units were active with `NRestarts=0` in the current activation. That does not erase historical service-child failures.

## Evidence and conclusions

### 1. Apollo actually exhausted disk space; automatic recovery did not restore headroom

Apollo emitted 18 disk-pressure notifications in the focused window. At **2026-11-16 20:38:14 -05:00**, notification `4f23a756-4a44-4b8e-aed1-3fff1df18f4e` from `disk_pressure` reported:

- 443.7 MiB free, approximately 0.2% of the managed-temp filesystem.
- 192.2 GiB categorized as “unattributed”.
- 9.7 KiB reclaimed, roughly 522 MiB remaining, against a 9.6 GiB recovery target.
- The managed-temp reaper was blocked/incomplete.

This was followed by actual `OSError: [Errno 28] No space left on device` traces in Apollo's agent-wait, Telegram, and wait scheduler logs around **20:40–21:06**. The detailed `disk_pressure` record in `~/.sase/axe/error_digests/digest_20261116_210556.txt` gives `reclaimed_bytes=9897`, `available_after_bytes=547528704`, and `reason=recovery_blocked`. The associated `axe` notification is `2e93bbe3-c65c-463b-b5e8-9264c3dc60f4`, timestamp **21:05:56 -05:00**, read and not dismissed at capture.

At the audit's filesystem check Apollo had **26 GiB free of 193 GiB**, 87% used; Athena had **285 GiB free of 875 GiB**, 68% used. There is no basis to call either machine currently out of space. There is strong evidence that Apollo's previous recovery was ineffective when it mattered.

“Unattributed” is a residual for the whole filesystem. It does **not** prove SASE owns all 192.2 GiB, or identify a directory safe to remove. Better ownership accounting and a clear escalation when automatic recovery cannot reach its target are justified. Blind deletion, a larger blanket cleanup scope, or treating protected artifacts as disposable are not.

There is also a continuing cleanup impediment on Athena: the housekeeping log repeatedly says it cannot fully inspect `~/.cache/sase/tmp/agent-tmp/gh_bobs-org__bob-cli-ws0-261007_081241`, preserving it because its newest write time is unobservable. The scan found **195 matching “could not fully inspect” warning lines** over the recent window, including **Nov 19 04:45:32 -05:00**. Other current skips name unreadable process `environ`/`cwd`, or a live process holding a candidate. The correct preservation behavior is already present. The useful improvement is to explain and repair the particular unreadable ownership/liveness evidence, while retaining those protections. The amount of reclaimable space behind these skips was not established.

**Confidence:** high that disk exhaustion caused operational failures; medium on the best capacity/cleanup remedy until the unattributed usage is explained.

### 2. `prompt_prose` links fail the current Rust schema: confirmed, reproducible defect

Athena's **2026-11-18 15:56:18 -05:00** `axe` notification `a96dc060-7471-4f30-9567-032ed0e887c7` points to `~/.sase/axe/error_digests/digest_20261118_155618.txt`. It was unread and not dismissed at capture. The attached file contains three publication failures at **15:50:43, 15:51:33, and 15:52:24**, including:

> unknown variant `prompt_prose`, expected one of `manual`, `migrated`, `prompt_ref`, `read`, `derived`, `projected`

The failing events attempted to write citations to `plan:202611/research_commit_gap.md`. I did not read that document; the reference appears in the error message.

Current source confirms a producer/consumer disagreement:

- Host `src/sase/agents_sync/referenced_by_planning.py` defines `PROMPT_PROSE_ORIGIN = "prompt_prose"` and uses it for prose-derived citations. Several SDD adapters also explicitly recognize it.
- Core `crates/sase_core/src/artifact_link/wire.rs:66` defines `ArtifactLinkOriginWire` without that variant.
- A **read-only call to the installed** `sase_core_rs.artifact_link_validate_row` rejected a synthetic row with `origin="prompt_prose"` with exactly the production error. The same row with `origin="prompt_ref"` was accepted. The probe did not write a link or artifact.

This is not merely stale log evidence or a missing install: the installed current binding still rejects the host's value. The repair should define the intended provenance in the Rust wire contract and update binding tests and the host core revision pin together. Alternatively, retiring the origin requires an explicit compatible migration; silently relabeling it as `prompt_ref` would erase the distinction the producer deliberately records. Add a contract test that sends every host-produced origin through the real binding, then verify pending events replay once after the fix.

**Confidence:** very high. This is the clearest small, actionable code defect in the audit.

### 3. Publication retains obligations safely, but some obligations cannot finish

Two distinct failure modes remain after removing the historical unmanaged-project storm.

**Missing deferred prompt sources on Athena.** There are **32 recent digest records** containing “a missing local source does not prove there was no prompt obligation”, from Nov 15 through Nov 18. The latest digest, `~/.sase/axe/error_digests/digest_20261118_211912.txt`, records three attempts at **20:55:36, 20:56:20, and 20:57:05 -05:00** for `bbugyi200.athena.1e6@50c90e3f2f54`. Its `axe` notification is `a43f4008-eb4e-4f27-86d0-a4fb7d38a8b5`, **21:19:12 -05:00**, unread and not dismissed.

I also found **25 recent notifications** whose affected-repository note specifically names `sdd:agents prompt archive`. For example, `021631b8-8486-48a8-a950-34ffacf9572d`, sender `user-agent`, **Nov 18 20:06:59 -05:00**, reports “Workspace held: stranded work” with “Cause: completed”. These 25 notices are not proven to represent 25 independent lost archives or 25 independent workspaces; they show recurring retention/recovery work being surfaced to the user.

The current implementation in `src/sase/agents_sync/prompt_archive/deferred.py` intentionally refuses to infer that no archive was required merely because the local source is absent. That is correct. The unresolved issue is whether the durable publication obligation has enough protected source material to be fulfilled after completion, cleanup, and workspace reuse. Audit the source lifecycle, restore from verified retained material where available, and provide one explicit terminal recovery state when the obligation cannot be reconstructed. Do not mark it successful just to clear a queue.

**Bounded publication attempts still exceed their budget on Apollo.** Notification `19d447eb-d6ac-4fc6-acbe-3877111537b9`, sender `axe`, **Nov 19 01:39:03 -05:00**, links `~/.sase/axe/error_digests/digest_20261119_013903.txt`. It was unread but dismissed at capture, illustrating why an unread-only audit would be insufficient. At **01:24:08**, publication had exceeded 120 seconds, and cleanup also exceeded one second.

Structured evidence in `~/.sase/logs/agent_publication_drains.jsonl` makes this more specific:

| Apollo failure | Timed stage | Relevant recorded work |
|---|---|---|
| Nov 18 around 11:35 local | `inventory_build` | 114.68 s in inventory; cleanup 15.26 s, exhausted budget |
| Nov 18 around 18:41 local | `hood_publish:bob-cli-eb` | 29 runs, 3,859,751 chat bytes, 73,169 prompt bytes; about 100.97 s publishing/preparing |
| Nov 19 around 01:24 local | `inventory_build` | 96.09 s inventory, 15.64 s payload cleanup, 8.00 s pull/rebase; cleanup failed at about 1 s |

Recorded lock waits for these examples were below 3 ms. A lock-contention fix alone would not explain these particular timeouts. The core problem is bounded work/progress and reliable cleanup, not simply choosing a larger global timeout. Some later scheduler passes succeed, so these are not evidence that all publication is permanently broken.

**Confidence:** high on recurrence and affected stages; medium on the precise source-loss and workload causes. No unpublished prompt was read or protection bypassed.

### 4. Running jobs and finalization are exposed to runtime updates

The focused notification scan found 19 Athena rows mentioning import failures or explicit “during a sase update” recovery messages. This is a mixed group of initial errors and follow-up notices, not 19 unique incidents. Examples include missing `is_valid_git_revision_name` imports and instructions to inspect held work after a model turn died during an update.

Independent operational evidence is stronger than the notification wording alone:

- Apollo `~/.sase/logs/launch_failures.jsonl`, error ID **`err_261118_072052_6ce1b8`**, **Nov 18 07:20:52 -05:00**: a launch failed importing `BeforeSpawnCallback` from managed SASE code. That symbol exists in the current source. The update ledger records an update at **07:20:16**, lasting **9.506 s**, with binding checks passing.
- Athena `~/.sase/axe/error_digests/digest_20261116_105314.txt`: `wait_checks` failed at **10:52:47 -05:00** because `sase_core_rs` could not be imported.
- Athena recorded missing `sase_job_tg_outbound` executables on Nov 16 and missing `sase_job_agent_auto_restart` at **Nov 17 07:15:51**. The update ledger has a successful update at **07:15:57**, duration **9.08 s**.
- Athena's Nov 18 **12:36:20** `agent_auto_restart` and `sidecar_auto_sync` subprocesses exited **-7**, near an update recorded at **12:36:26**, duration **16.071 s**. On Linux -7 denotes SIGBUS. These logs do not establish whether a replaced mapped file, another native defect, or some other cause produced that signal.

These observations support protecting execution across updates. They do not prove a single underlying mechanism for every crash. A successful post-update binding check cannot prove a process already running through an in-place update saw a coherent old or new runtime.

There are already partial fixes: commit `ea7916d7a7` (Nov 17) classifies scripts that vanish during a code swap as skipped/retryable; `1ccd5c0579` (Nov 18) queues dev updates behind an in-flight epic launch. Any follow-up should test the remaining exposure—running jobs, late imports, and finalizers—rather than reimplement these guards.

**Confidence:** high that update-adjacent breakage occurred; medium that generation-isolated runtime use is the appropriate complete remedy. A narrow reproducer should choose the implementation.

### 5. Hourly digests cannot account for all errors during storms or long delays

Apollo's retained publication log contains **3,005** recent “Error in agent_publication” lines for the structured publication-summary family, whereas the digest files contain **1,900** records of that family. The separate generic timeout family is not included in either side of this comparison. These are observations from differently retained/live sinks, not a global exact missing-event total, but they are consistent with a concrete limitation in current code:

- `src/sase/axe/_state_scheduler.py:177` appends errors to `recent_errors.json`, then keeps **only the last 100**. It also silently returns on an `OSError` while recording.
- `src/sase/scripts/sase_chop_error_digest.py:21` uses the later of the last digest timestamp and **now minus one hour** as its cutoff.
- Several storm digests end at exactly 100 records. The Nov 17 07:36 digest is one example.

At more than 100 errors between digest runs, older events can disappear from the digest input. If the digest job is delayed more than an hour, older undelivered events can also be skipped. The timestamp checkpoint does not compensate for either case. This particularly matters when a noisy subsystem competes with a distinct disk or publication-integrity failure for those 100 slots.

The desirable outcome is **bounded detailed storage with accurate counts and explicit coverage**, not infinite log retention or an alert for every repeated attempt. Persist per-signature first/last/count and an acknowledgement cursor, preserve representative diagnostics, and expose dropped/overflowed records if full accounting is impossible. A digest could state “publication target unavailable ×N; disk recovery blocked ×M” and report its covered interval. Tests should include >100 errors between drains, a delayed digest, repeated timestamps, and a write failure.

**Confidence:** high on the implementation limitation; medium on attributing the whole observed cross-sink difference to that limitation.

### 6. Both TUIs have measured stalls; Athena's worst examples overlap GC

The retained `~/.sase/logs/tui_stalls.jsonl*` records, filtered by epoch timestamp, include:

| Recorded recovered event-loop stalls | Apollo | Athena |
|---|---:|---:|
| Events since Nov 12 UTC | 14 | 70 |
| Median duration | 8.355 s | 12.592 s |
| Maximum duration | 115.796 s | 331.173 s |

These are watchdog events, not a measurement of all user-visible latency. Rotated coverage differs by machine, and the counters do not normalize for active UI sessions. I used recovery events once rather than adding detected and recovered events together.

Athena provides unusually useful attribution:

- **Nov 16 11:33:26 UTC:** 331.173 s recovered stall, **324.238 s GC overlap**.
- **Nov 17 18:40:04 UTC:** 74.118 s recovered stall, **73.073 s GC overlap**.
- **Nov 17 21:30:58 UTC:** 62.493 s recovered stall, **61.368 s GC overlap**.

All three have `pause_depth=0`. These establish a strong reason to examine allocation/retained-heap growth and collection cost. They do not establish which subsystem retained those objects.

Apollo's **Nov 18 21:12:36 UTC** 115.796 s event instead reports only **0.389 s** GC overlap. Its associated sampled stack is in `_launchable_mru_tick` → `peek_current_project_change_token` → `Path.stat`. A single stack sample does not prove that one stat call consumed the entire interval. It does justify checking synchronous I/O and CPU scheduling alongside the GC investigation; a GC-only fix should not be assumed to solve both machines.

The source already contains GC attribution and census telemetry. Use that evidence to target retention/allocation or blocking work, and evaluate under a reproducible loaded session. Silencing the watchdog or globally disabling GC would not establish improvement.

**Confidence:** high on recorded responsiveness problems and Athena's overlap; medium on individual root causes.

## Findings that should not become duplicate or speculative fixes

**The dominant unmanaged-project publication storm is already addressed.** Apollo had **1,893 digest records** naming `gh_bbugyi200__nut: no usable agents publication target` between **Nov 16 14:22:21 and Nov 17 07:35:41 -05:00**. These constitute approximately 92% of its recent digest errors. The same unmanaged project's missing sidecars also blocked artifact retention in six digest records. Commit **`b0de76422d`**, **Nov 17 07:35:03 -05:00**, explicitly silences unmanaged-project noise in retention/publication. Current `publication_job.py` distinguishes a skipped target with no active work from an unavailable target with queued obligations. The captured storm ends around deployment of that change. Verify it stays quiet; do not file another blanket suppression change.

**Timeouts misreported as repository damage already have a targeted fix.** The recent digests include Apollo and Athena messages claiming an invalid/detached Git worktree when the probe's actual output was “deadline expired before git operation”. Commit **`637a70a0f1`**, **Nov 18 09:44:03 -05:00**, introduces timeout-as-unknown-state handling, and `tests/sdd_store/test_repository_timeouts.py` explicitly covers avoiding unsafe classification and recovery on timeout. Both hosts now report code containing that commit. The latest captured examples predate it. Regression verification is appropriate; another implementation proposal is not yet justified.

**Athena also had a genuinely different Git-corruption signal.** There are **23** digest records on Nov 14–15 reporting an **empty Git object** in the bob-cli plans sidecar; the latest sampled attachment is `~/.sase/axe/error_digests/digest_20261115_121107.txt`. This must not be dismissed as the timeout-classification bug. I did not open or repair that repository, and there is no later recurrence in the inspected digest window. Verify existing recovery evidence before deciding whether any further repair is needed. Nothing here establishes ongoing corruption or hardware failure.

**The documentation-refresh argument failure is already fixed in the installed plugin.** Athena had 11 Nov 13–14 notifications rejecting `owner/repo` values because `#gh` required a `word`. The installed `sase-github` revision **`5f85ceb`** changes `gh_ref` to `type: line`; its commit is explicitly “bind owner/repo #gh refs as line inputs”. Current source supports the intended values. Verify a normal scheduled run, rather than changing unrelated scheduler behavior.

**Telegram transport warnings do not prove lost notifications.** Athena's retained Telegram scheduler log contains hundreds of timeout stack traces and three recent service crash-loop notifications. One representative notification, `ca1e9990-29fb-486a-8f81-dfcd1c3a5d40`, **Nov 15 10:16:54 -05:00**, reports receiver exit **75** and restart backoff. In current code, 75 is the credential-unavailable retry path; it should not automatically be blamed on polling timeout. The client already retries transient network failures and the receiver catches polling errors and continues. Later logs show the receiver starting/registering commands. More readable, rate-limited transport diagnostics may help, but this audit did not establish delivery loss or justify a retry redesign.

**Preservation and admission refusals are often working correctly.** Waiters blocked on failed/killed dependencies, held workspaces, protection-withheld prompts, name-reuse cleanup refusals, and incomplete liveness inspections require individual recovery evidence. Their presence alone does not justify force-releasing reservations, declaring dependent work complete, deleting archives, or relaxing protection rules. Athena has several recent name-reuse refusals in `launch_failures.jsonl`; I did not establish whether the remaining owners were live, so I do not classify them as an ownership bug.

**Service shutdown warnings merit a focused follow-up only if impact recurs.** Apollo's user journal contains eight recent `sase.service` “Failed to kill control group … Invalid argument” warnings, sometimes followed by left-over subprocess warnings. The current unit is active and uses `KillMode=mixed`. This is evidence of imperfect shutdown, but not enough to justify changing kill policy: agent scopes intentionally survive some host lifecycle operations. First prove an owned scheduler child survived incorrectly and affected operation.

**This audit itself observed a sidecar-mismatch warning.** The requested `sase repo open research` printed a refusal to replace a mismatched nested plans clone, then successfully returned the isolated research checkout. I recorded the warning but did not inspect or alter the mismatched primary-sidecar path. Successful completion and a protective refusal do not establish a new repository-corruption defect.

## Ranked fixes and improvements to consider

The ranking balances observed impact, recurrence, and confidence that a change is beneficial. It is not a suggestion to implement every item at once. Shared backend/domain changes belong in `sase_core` with binding coverage and the host's revision pin updated; presentation-specific TUI work belongs in the host.

1. **Prevent another Apollo ENOSPC incident by fixing attribution and ineffective recovery.** Reconcile the large unattributed filesystem residual, make blocked cleanup identify the exact missing evidence and responsible owner, and provide an actionable escalation when the existing recovery target remains unmet. Repair demonstrably stale managed state only after proving it is safe. Acceptance: a controlled low-space scenario restores the configured headroom or clearly reports why it cannot, preserves live/protected work, and does not strand notification/scheduler state writes. **High impact; cause of exhaustion confirmed, exact owner still to determine.**

2. **Repair the `prompt_prose` Python/Rust contract and replay affected citation events.** Define compatible provenance semantics in Rust and exercise every host-produced origin through the actual binding. Preserve event identity and citation meaning during recovery. Acceptance: the audit's synthetic row validates; the recorded event family drains idempotently; existing origins still round-trip. **Very high confidence; best small code fix to start immediately.**

3. **Make deferred prompt publication recoverable and bounded by useful work.** Protect the source bytes needed by a durable obligation through completion and workspace cleanup; make missing-source recovery explicit; reduce repeated inventory/render work identified by the timing ledger and guarantee verifiable cleanup after interruption. Acceptance: large recorded publication workloads complete incrementally or remain clearly recoverable, and completion/restart/reuse cannot leave an unexplained missing archive. **High impact and recurrence; diagnose source lifecycle before choosing the implementation.**

4. **Close the remaining runtime-update races for jobs and finalizers.** Extend the existing launch/code-swap protections to preserve a coherent runtime for running work; use a targeted update-overlap reproducer to decide between narrower guards and versioned runtime instances. Acceptance: an update concurrent with late imports, a scheduler job, and finalization produces no missing binding/executable/import errors and no lost completion. Investigate SIGBUS separately if it reproduces. **High potential impact; update association is strong, exact mechanism partly unproven.**

5. **Make digest coverage explicit and preserve counts across storms and delays.** Replace silent last-100/last-hour loss with bounded representative details plus durable counts/cursors or an explicit overflow record. Group recurring failures by cause while keeping distinct failures visible. Acceptance: >100 events and a >1-hour delayed digest yield accurate counts and a truthful coverage interval, with bounded storage. **High confidence; improves detection without increasing alert volume.**

6. **Reduce the measured TUI stalls, starting with Athena's GC-heavy cases.** Use the existing heap/census evidence to remove avoidable retention/allocation and move proven blocking work off the UI path; separately investigate Apollo's low-GC stalls. Acceptance: replay the affected workload with materially lower stall duration and unchanged behavior, while retaining diagnostics. **User-visible impact confirmed; profile-guided work is justified, an unmeasured rewrite is not.**
