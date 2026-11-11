# Seven next task beads for SASE: verified reliability priorities

Independent research by **cdx**, 2026-11-11.

**Recommendation:** work the existing tasks `sase-1db`, `sase-1s2`, `sase-1re`, `sase-1qr`, `sase-1kp`, `sase-1cg`, and `sase-1mb`, in that order. They address a privacy boundary, process shutdown, stalled work ownership, capacity accounting, storage locking, prompt preservation, and bounded Git I/O. The detailed ranked list ends this report.

This is a research recommendation, not a launch request. I did not create, claim, close, or edit beads, alter production services, or inspect another member of this research swarm's report, transcript, or findings.

**Scope and selection method**

I enumerated the current task backlog through `sase bead list --type task --format json`, inspected active epic records, audited shortlisted beads through `sase bead read --no-links`, and checked the relevant implementations and recent commits. I opened the research repository and linked sase-core repository through `sase repo open`. No prior research reports were needed.

The captured backlog had **423 nonclosed tasks: 410 ready, nine open, three snoozed, and one in progress**. It included 153 bugs, 110 features, 104 flakes, 30 memory tasks, 15 CI tasks, six flags, and five legacy untyped tasks. There were 127 in-progress plan records; that is a tracker count, not 127 live agents. The initial all-bead statistics were 8,466 total, 238 in progress, and 7,803 closed. These are a dated snapshot of a changing store.

I used four judgments, rather than treating report counts as votes:

- **Consequence:** prevent private disclosure, lost work, indefinite stalls, and incorrect lifecycle decisions before adding convenience.
- **Reach:** favor defects in shared execution and storage paths over one test or one view.
- **Evidence today:** distinguish current source and bounded reproductions from historical observations or predictions.
- **Marginal value now:** discount work already implemented or assigned to an active repair epic, and account for the task's recorded size.

The final seven all remained `ready`, had empty assignees, and appeared in **`sase bead ready`** on the final check. Six have no recorded dependencies. `sase-1db` depends on `sase-1d5`, which is closed and already supplied the visibility probe. The generic JSON `is_ready_to_work` field was false on all seven; eligibility here is based on the explicit task status, dependencies, and dedicated ready-command result, not an assumption about that field.

**Source baseline and limits**

The primary checkout was `671ff5bde0`, the commit titled “chore(master): release 0.19.0 (#322).” The opened core checkout was `1ba79d2ffef677defba4208aa641ecb50d2d161c`; the primary checkout's CI core pin was `5c0e49cf3dcc8ce13dd8fbcdba88b9f9b26c6cb3`. Those are different baselines and are identified separately below.

Fresh Rust binding probes used the installed **sase-core-rs 0.44.1**. The workspace virtualenv contained 0.42.1 and lacked `stranded_work_reduce`; that first attempt failed before exercising the reducer. I reran the synthetic probes with the installed binding, successfully. I did not rebuild or reinstall either environment. Python source probes used this checkout.

This investigation did not rerun Full CI, measure a new long-lived TUI soak, survey current credentials, or reproduce database corruption. Existing incident reports are identified as such. The narrow probes used synthetic inputs or disposable files; the Git pipe child was killed and reaped after measurement. No real private attachment was uploaded.

**What the fresh checks established**

| Candidate | Fresh observation | What it does not establish |
| --- | --- | --- |
| `sase-1db` | Existing-remote preflight still skips the visibility comparison; private-store discovery creates a store and labels it private without a visibility probe. | No claim that an actual private attachment has leaked. |
| `sase-1s2` | In separate fresh interpreters, importing either runner module changed SIGTERM from `SIG_DFL` to `install_sigterm_handler.<locals>._handler`. Both exited normally. | Not every observed CI timeout is caused by this defect. |
| `sase-1re` | With binding 0.44.1, a synthetic cold, done, stopped monitor with `followup_pending=true` reduced to `owned/monitor`. Changing only that flag to false produced `stranded/unclosed`. | I did not resurvey the four historical live examples during this turn. |
| `sase-1qr` | A temporary artifact containing `process_identity: "boot:99"` in both `agent_meta.json` and `running.json` was scanned through binding 0.44.1. Both returned wire objects omitted the identity. Current Rust source also has no generic `process_identity` field in the scan domain. | No current count of runner slots held by reused PIDs. |
| `sase-1kp` | Source still shares `beads.db` between the Rust mutation-lock path and Python SQLite mirror. A disposable POSIX-lock experiment showed a second process blocked before a separate descriptor closed, then able to acquire the lock afterward. | This proves the locking primitive, not an end-to-end SASE corruption or SIGBUS incident. |
| `sase-1cg` | A fake object calling the real restart method with a failing stash returned events `watchdog_stopped → stash_failed → exit_requested`; `_quit_draft_stash_attempted` became true. | No real TUI session or user's prompt was terminated. |
| `sase-1mb` | A read-only `git cat-file --batch` protocol probe using the checkout's README blob blocked the write-first thread after 1,683 IDs. At 0.5 seconds, writer and Git remained alive despite the writer checking a 0.1-second deadline before each write. Cleanup completed. | The current Rust functions were source-reviewed; this probe reproduced their I/O ordering, not a call through their Rust API. |

The lock result agrees with SQLite's own warning: closing a separate descriptor can cancel the process's POSIX locks on that same database file. SQLite documents additional defenses since 3.51.0, but explicitly says they are not a complete solution. This supports correcting the ownership boundary; it does not justify asserting that every affected database is corrupt. [SQLite: file-locking problems, §2.2](https://www.sqlite.org/howtocorrupt.html#posix_advisory_locks_canceled_by_a_separate_thread_doing_close_)

Likewise, subprocess documentation warns that manual pipe writes and reads can deadlock when the other pipe fills. The relevant remedy is concurrent, bounded I/O with child cleanup, rather than checking a clock only between blocking writes. [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html#subprocess.Popen.communicate)

**Why several initially compelling tasks did not make the seven**

The largest prioritization error here would be to reimplement fixes whose original task statuses have not caught up.

| Candidate or group | Reason to defer from this immediate seven |
| --- | --- |
| `sase-1pw`: test-worker starvation | FIFO tickets and bounded backfill are already in `tests/_suite_gate_lease.py`; commit `0c677302d9`, closed phase `sase-1ra.4`. Reconcile completion evidence, rather than launch a duplicate implementation. |
| `sase-1qe`: quadratic test-home allocation | Current fixture uses `tempfile.mkdtemp`; commit `394ff93ff5`, closed phase `sase-1ra.3`. The old two-hour incident is not evidence that this implementation is still missing. |
| `sase-1ce`: failed-editor draft deletion | Commit `522b07a009` and closed phase `sase-1ra.2` preserve failed drafts. This is separate from the still-present restart failure selected below. |
| `sase-1r4`, `sase-1qj`, `sase-12u`, `sase-1jd` | Active `sase-1ra` phases already own signature-skew handling, orphaned staged monitors, reboot recovery, zombie-parent recovery, and the import ratchet. Additional independent workers would overlap. |
| `sase-j0`, `sase-11b`, and individual CI/flake beads | Extensive recent CI/contention repairs and active release/CI epics make old failure counts poor evidence of an unowned present blocker. The selected signal-handler defect has a fresh reproduction and was explicitly filed as a separate follow-up by the contention epic. |
| `sase-1ot`: historical secret purge | Its October 28 evidence records an owner rejection and says renewed remediation requires an owner request. November 5 also requires a scanner-v2 audit because v1 had false positives. Do not equate “27 scanner hits” with “27 live credentials,” or reauthorize a history rewrite through prioritization. |
| `sase-1nc`: TUI GC pauses | Potentially severe, but its October 31 note requires a restarted-instance remeasurement after the index-lock fix; earlier measurements include superseded load and allocation problems. It also intersects active `sase-1nf`. A fresh census/soak could move it sharply upward. |
| `sase-1o1`: nested continuation ancestry | The source and 256 KiB cap make this credible, but the bead's measured sessions had not yet reached the cap. It is a strong reserve candidate after observed terminal-state defects; retain a long-session regression when addressing it. |
| `sase-1n9`: session-shared Cargo target | Historical evidence of 5–7-minute cold builds is attractive. Shared-target custody and reclamation require a larger design, and I did not measure present cold-build frequency. It is a strong subsequent throughput investment. |
| `sase-1je`: immutable per-process releases | This is an important structural direction, recorded as xlarge. The immediate skew-recovery epic is still active. Plan it deliberately after that boundary settles rather than mix it into seven bounded repairs. |
| `sase-1qm`: false stale fingerprint; `sase-1s4`: checkout lock leak | Both could be costly, but the recorded cause is unconfirmed. They rank below fresh, precise reproductions here. |

These exclusions do not assert that every associated bead is complete. They distinguish implementation, validation, and tracker cleanup. I made no lifecycle changes.

**Evidence locators**

The audited task refs are `bead:sase-1db`, `bead:sase-1s2`, `bead:sase-1re`, `bead:sase-1qr`, `bead:sase-1kp`, `bead:sase-1cg`, and `bead:sase-1mb`. The earlier tables also draw on audited reads of `bead:sase-1ra` and its direct children, `bead:sase-1ra.11.1`, `bead:sase-1d5`, and the named reserve/exclusion candidates. The detail is in their descriptions, typed task fields, notes, and +1 evidence, not title matching alone.

Stable code locators used for the conclusions:

- **Private-store boundary:** [preflight](https://github.com/sase-org/sase/blob/671ff5bde0/src/sase/sdd/_sidecar_init.py#L132), [labels and discovery](https://github.com/sase-org/sase/blob/671ff5bde0/src/sase/bead/attachments/upload/discovery.py#L154), and [GitAttachmentStore construction](https://github.com/sase-org/sase/blob/671ff5bde0/src/sase/bead/attachments/git_store/store.py#L28).
- **Signals:** [agent import](https://github.com/sase-org/sase/blob/671ff5bde0/src/sase/axe/run_agent_runner.py#L87), [mentor import](https://github.com/sase-org/sase/blob/671ff5bde0/src/sase/axe/mentor_runner.py#L30), and [handler semantics](https://github.com/sase-org/sase/blob/671ff5bde0/src/sase/axe/runner_signals.py#L27).
- **Stranded ownership:** [core owner_kind](https://github.com/sase-org/sase-core/blob/1ba79d2ffef677defba4208aa641ecb50d2d161c/crates/sase_core/src/stranded_work/classify.rs#L115).
- **Scan identity:** [core wire](https://github.com/sase-org/sase-core/blob/1ba79d2ffef677defba4208aa641ecb50d2d161c/crates/sase_core/src/agent_scan/wire.rs#L519) and [Python liveness consumer](https://github.com/sase-org/sase/blob/671ff5bde0/src/sase/core/runner_slots/_scan.py#L39).
- **Lock ownership:** [Rust filename](https://github.com/sase-org/sase-core/blob/1ba79d2ffef677defba4208aa641ecb50d2d161c/crates/sase_core/src/bead/mutation/store.rs#L46), [lock lifetime](https://github.com/sase-org/sase-core/blob/1ba79d2ffef677defba4208aa641ecb50d2d161c/crates/sase_core/src/bead/mutation/store.rs#L511), and [Python mirror connection](https://github.com/sase-org/sase/blob/671ff5bde0/src/sase/bead/_project_store.py#L32).
- **Restart preservation:** [restart ordering](https://github.com/sase-org/sase/blob/671ff5bde0/src/sase/ace/tui/actions/axe_quit.py#L211) and [loss of the failure sentinel](https://github.com/sase-org/sase/blob/671ff5bde0/src/sase/ace/tui/actions/agent_workflow/_prompt_bar_stash.py#L61).
- **Git batch I/O:** [blob reader](https://github.com/sase-org/sase-core/blob/1ba79d2ffef677defba4208aa641ecb50d2d161c/crates/sase_core/src/file_history/blobs.rs#L41), [diff-tree reader](https://github.com/sase-org/sase-core/blob/1ba79d2ffef677defba4208aa641ecb50d2d161c/crates/sase_core/src/memory_history/causes.rs#L141), and [existing concurrent runner](https://github.com/sase-org/sase-core/blob/1ba79d2ffef677defba4208aa641ecb50d2d161c/crates/sase_core/src/file_history/runner.rs#L109).

All repository files were read locally from the authorized checkouts; these links are portable citations, not web-fetched repository evidence.

**Execution considerations**

The ranking is a priority order, not seven dependencies. The small signal and restart repairs can proceed while the core storage repair is designed. Coordinate core edits and ship binding/pin updates together where required; otherwise a correct Rust fix can remain absent from SASE's deployed behavior.

Shared policy belongs in sase-core. The scan, stranded-work, database-lock, and Git-runner changes belong there, with Python adapters and integration coverage as needed. The restart fix is Textual presentation/lifecycle glue. Private-store visibility must be enforced at the shared write boundary as well as reflected in preflight and labels, so an alternate frontend or outbox retry cannot bypass it.

For implementation, each worker should reconfirm the named source and bead status, add the focused regression that fails on the old behavior, and run the repository's required `sase tool run check`. This research itself changed no product source and did not run the exhaustive suite.

**Final ranked list: the next seven existing task beads**

1. **`sase-1db` — Verify an existing private attachment remote before sending bytes.**  
   **Recorded size: medium. Confidence: high in the missing boundary; exposure frequency unknown.** This is first because a destination presented as private can actually be public, and disclosure cannot be repaired merely by retrying a failed job. The prerequisite probe and doctor check already exist, so the remaining repair has a favorable scope-to-consequence ratio. Current preflight still compares visibility only for a missing remote, and discovery still trusts the configured role. Enforce rejection of a known-public private destination before any upload, define honest handling of unknown visibility, and stop rendering a private claim based solely on the role. Completion should cover existing-public remotes, visibility changes, cached results, and queued/retried uploads without sending sensitive test data. This is prevention of future disclosure, separate from the owner-declined historical purge.

2. **`sase-1s2` — Stop runner imports from replacing the caller's SIGTERM handler.**  
   **Recorded size: small. Confidence: high, freshly reproduced.** A module import changes process-wide shutdown behavior, including in test workers and other importers. The agent variant installs a soft handler that records a kill without exiting, so unrelated callers can survive termination and consume time or capacity until a harder kill. This is more valuable than chasing individual timeout symptoms, and it is explicitly outside the contention epic's completed local repairs. Move installation into the runner-owned entry lifecycle while preserving early production shutdown handling. Completion requires fresh-interpreter tests showing imports preserve default and custom handlers, plus real-entry signal tests proving actual agents and mentors still settle correctly.

3. **`sase-1re` — Stop finished monitors with stale follow-up flags from owning beads forever.**  
   **Recorded size: medium. Confidence: high in the reducer defect, with historical live corroboration.** This directly prevents completed/dead work from looking actively owned. Its November 5 +1 independently named four affected beads; binding 0.44.1 still reproduces the decisive classification with a cold terminal monitor. Hidden stranded work wastes more than one agent's time: it stalls dependent work and removes the recovery cue from the supervisor. Investigate why the follow-up did not settle, then bound ownership using actual delivery/recovery facts rather than a stale boolean. Completion must distinguish a dead abandoned follow-up from a real queued successor, a live monitor, retained recovery custody, and legitimate settlement grace. It is distinct from the active staged-adopter crash repair.

4. **`sase-1qr` — Preserve process identity through Rust scans and indexed records.**  
   **Recorded size: medium. Confidence: high, freshly reproduced.** Python already has the PID-reuse guard and knows how to consume identity, but the Rust projection silently drops its input. Consequently, recycled PIDs can make dead agents appear live in admission and listing paths, creating phantom capacity pressure. This is a relatively narrow missing-wire-field repair with broad operational reach. Carry identity from both metadata and running markers, preserve it through scan/index serialization, and decide how old cached/indexed rows refresh. Completion should prove scan-to-liveness behavior for matching, mismatched, and absent identity, including cached admission reads; update the binding contract and SASE core pin. I did not measure current lost slots, so the ranking rests on reach and a proven broken guard rather than an invented utilization figure.

5. **`sase-1kp` — Separate Rust's bead mutation locking from the Python SQLite mirror.**  
   **Recorded size: large. Confidence: high in the shared-file hazard; production corruption not reproduced.** Bead state is central to orchestration, and the current code still opens the SQLite database itself as the separate Rust lock file. The fresh descriptor experiment and SQLite's documentation corroborate why closing that descriptor can invalidate SQLite's assumptions. This merits fixing before another incidental crash exposes it. Its position below the narrower execution repairs reflects the remaining design work and the fact that the bead identifies the compatibility mirror, not a demonstrated loss of canonical event history. Choose a single-owner mirror design or a dedicated lock protocol with a coordinated mixed-version migration. Completion needs concurrent-process coverage and compatibility tests; simply renaming the lock for new clients while old clients use the old name would create another serialization gap.

6. **`sase-1cg` — Cancel TUI restart when saving an open prompt fails.**  
   **Recorded size: small. Confidence: high, freshly reproduced through the real methods.** This is a precise user-work-loss path: the failure sentinel is converted to false, restart marks the quit stash attempt complete, and exit still proceeds. The current method also stops the watchdog before it knows whether preservation succeeded. A disk-full or permission/lock failure should leave the user's editor usable, not discard the draft. Preserve the three outcomes—saved, no draft, save failed—and cancel restart with a useful notification on failure before setting exit state or disabling services. Completion should cover restart with and without scheduler restart, successful/no-draft paths, and simulated write failure. Unlike the already-landed failed-external-editor repair, this bug remains in the current source.

7. **`sase-1mb` — Replace write-first Git batch readers with bounded concurrent I/O.**  
   **Recorded size: medium. Confidence: high in the I/O defect, with a fresh bounded protocol reproduction.** Both the blob reader and instruction-history diff-tree reader still write all requests before draining output. A blocking write prevents their between-write deadline check from running, so large history work can hang past its advertised budget. The existing shared concurrent Git runner gives this task a concrete implementation route without new architecture. Migrate both callers while preserving framing, missing/oversize-blob behavior, output limits, truncation diagnostics, and child cleanup. Completion should include input and output larger than pipe capacity, a deliberately stalled child, and confirmation that timeout leaves no child behind. It earns the seventh slot ahead of speculative performance additions because the failure mechanism is current, deterministic at the protocol level, and bounded in scope.
