# The next 7 task beads to work, ranked by impact (2026-11-11)

Researcher: mus (independent swarm report; snapshot 2026-11-11 ~21:45 UTC).
Code state: sase master `671ff5bde0` (release 0.19.0, PR #322, merged same day).
Bead corpus at snapshot: **9 open / 410 ready / 3 snoozed / 1 in-progress task beads**
(`sase bead list --type task --status ...`).

## Bottom line

| # | Bead | Type · size | Why it matters in one line |
|---|------|-------------|----------------------------|
| 1 | **sase-1re** | bug · medium | Done monitors with stale `followup_pending` own their bead forever; beads never strand, waiters park forever |
| 2 | **sase-1qm** | bug · large | Host completion discards a passing `just check` on a phantom fingerprint mismatch; every epic landing path pays |
| 3 | **sase-1rb** | bug · medium | 53 stale publication-protection blocks can never be revisited, so `sase doctor` WARNs forever |
| 4 | **sase-1kp** | bug · large | `beads.db` doubles as Rust's mutation lock and Python's WAL mirror, so a Rust lock close drops Python's POSIX locks |
| 5 | **sase-1qi** | bug · medium | `sase agent restart` cannot find crash-killed agents; the Nov-01 restart needed manual bead work for 27 waiters |
| 6 | **sase-1qx** | bug · large | Commit-stage finalizer median 101 s vs 60 s targets; every agent turn pays the tax |
| 7 | **sase-1rt** | bug · medium | `preview_aggregate` builds the artifact-link event snapshot twice; 59 s reconciles get deferred, `doctor --fix` drags |

All seven are READY, unowned by any live epic, and independently verifiable.
What was deliberately left out, and why, is in [Excluded](#excluded-not-ranked).

## Conflict screen (what is running now)

- **sase-1s7.7.3** (OPEN, was closed/canceled, reopened today): PR #322 is merged at
  `671ff5b`, but the release train has not started. A fresh note (minutes before this
  snapshot) records a new defect: the peeled tag and merge SHA `671ff5b...` differ from
  the PR source head `c366d45...` that the release-watch facts reader uses as
  `merged_head_sha`, so `release_watch --once` exits `watcher_broken`; PyPI returns 404
  for sase 0.19.0 and the draft release has no assets. This is the repo's most urgent
  problem, but it is **owned by epic sase-1s7.7** and is a phase, not a task bead, so it
  is not ranked below. Recommendation: the sase-1s7.7 lander should file it as a task
  bead (facts-reader SHA identity vs squash-merge/train SHAs) if it is not fixed inline.
- **sase-1r2.6** (in progress): one green Full CI run on master in every job.
  Do not rank flakes it took over; do not move the core pin underneath it.
- **sase-1rq.2.1.4.1.5.3.1.3** (in progress): hosted contention-test confirmation on
  landed master. Contention-lane flakes stay out of this list.
- **sase-1ra.8 / .9 / .10 / .11 (+ child epic .11.1) / .12** (in progress): staged-zombie
  settle, skew-core classifier, import ratchet, boot reconciler, zombie-epic invariant.
  Picks below were screened for file overlap; adjacencies are noted per pick.
- **sase-1s5.3** (OPEN, previously closed then reopened 2026-11-09): exact-run dismissal
  lookup. Reopened state means it needs owner triage before any adjacent dismissal work.
- **sase-1qh.7** (in progress): clearing already-stuck planner/research rows.
  Publication-row picks below are the unowned residuals around it, not its scope.
- **sase-1rs.11** (in progress): Spotify install + acceptance on athena. Untouched.

## The ranked list

### 1 · sase-1re: done monitor with stale `followup_pending` owns its bead forever

- **Location:** `crates/sase_core/src/stranded_work/classify.rs`, `owner_kind()`
  monitor/gate branch (linked `sase-core` repo).
- **Evidence.** A monitor member that is `done` but still reports `followup_pending=true`
  (stale `next_action`, no `followup_outcome`) reduces to `owned/monitor` instead of
  `stranded`. Live examples: `sase-1ih.2`, `sase-kp` (`sase-kp.land--mon`),
  `sase-ru.6`, `sase-s5`. Corroborated (+1). Repro is a unit-level wire reduction, so
  the fix is testable without live hosts.
- **Impact.** Finished monitor turns hold their beads open indefinitely: ACE never shows
  STRANDED, waiters on those beads stay parked, and the stale `next_action` is never
  investigated. This is a liveness defect in the exact machinery the in-flight
  sase-1ra.11 boot-recovery and sase-1ra.12 zombie-epic work builds on: every
  reboot-stranded or zombie epic behind a done-but-pending monitor stays invisible
  until this ownership rule is fixed.
- **Why now.** It multiplies the value of the two in-flight recovery epics, and the fix
  needs a root-cause check of why the follow-up never launched first — that finding
  will itself route follow-up work.
- **Adjacency.** Distinct from sase-1ra.8 (orphaned *staged* monitors); note the shared
  stranded-work classifier surface and keep the two in contact.

### 2 · sase-1qm: host completion refuses a green prepared completion

- **Location:** sase-core `crates/sase_core/src/continuation/completion_eval.rs`
  (`stale_worktree_fingerprint`); sase `src/sase/monitor/followup_prompt.py`.
- **Evidence.** Observed 2026-11-01 on athena: ToolRun `adb74711...` (`just check`)
  succeeded (exit 0, evidence complete, `mutated_input=false`, dirty 19 -> 19), yet
  host completion refused intent `file:explicit:37585a8f...` with
  `stale_worktree_fingerprint`. A recovery agent compared every dirty-file hash, dirty
  path set, and HEAD in both repos against the sealed fingerprints — all matched — and
  the phase completed only through a fresh final declaration. Each refusal wastes a
  ~30-minute check plus another turn.
- **Impact.** This taxes the landing path of *every* epic that uses prepared
  completion: green verification is thrown away on a phantom mismatch and agents redo
  declarations by hand. With the release train, Full CI confirmation, and four
  sase-1ra phases all converging on host completion this week, the expected cost is
  several wasted check cycles.
- **Why now.** Frequency is the argument: it is a throughput tax on all the
  highest-priority in-flight work, and the suspect area is narrow (fingerprint scope
  across the main + sase-core repo set, or seal-vs-evaluate time-of-check).

### 3 · sase-1rb: 53 stale publication-protection blocks never revisited

- **Evidence.** Epic sase-1r8 (now CLOSED) made scanner-hit blocks rules-versioned with
  `revalidation = automatic`: a block under older rules stops enforcing, and the next
  publish attempt for the same (repository, path, sha256) rescans it. After the
  reinstall (rules v2), 15 blocks were superseded — but 53 remain stale forever: 43
  `openai-key` (bob-cli), 4 `openai-key` + 4 `high-entropy-assignment` + 1 `stripe-key`
  (sase), 1 `openai-key` (tailnet). Every record sits on an older hood's
  `agents/<agent>/chat.md` whose request was acknowledged long ago with content
  withheld, so no drain, retry, or `--retry-quarantined` path ever reaches them.
- **Impact.** `sase doctor -C state.agent_publication_protection` stays WARN
  permanently ("0 enforced blocked, 53 stale awaiting revalidation") with a next step
  that cannot run — a broken window on the single command users trust for publication
  health — and the withheld bytes stay unpublished.
- **Why now.** The introducing epic just closed, the rule version and schema are
  settled, and the remedy is bounded (a repair pass over stale blocks, consistent with
  the `revalidation = automatic` decision). It also clears the WARN noise that would
  otherwise mask regressions from the fresh release.

### 4 · sase-1kp: `beads.db` is both the Rust mutation lock and Python's WAL mirror

- **Location:** sase-core `crates/sase_core/src/bead/mutation/store.rs`
  (`BEAD_MUTATION_LOCK_FILENAME = "beads.db"`, `with_bead_mutation_lock`); sase
  `src/sase/bead/_project_store.py` (`BeadProjectStoreMixin._conn`).
- **Evidence.** Proposed by guard phase sase-1kk.6: epic sase-1kk established a
  one-SQLite-library-per-file rule, but `beads.db` is still shared — Rust uses it as
  its mutation lock file while Python holds it as a WAL SQLite mirror, so a Rust lock
  close drops Python's POSIX locks.
- **Impact.** This is the only pick in the data-integrity class: silently dropped POSIX
  locks on the bead store mean concurrent Rust/Python writers can interleave bead
  mutations. Severity outranks frequency — a corruption-shaped defect in the store
  behind all 410 ready beads and every epic above.
- **Why now.** It has sat unowned for 28 days with no active epic covering it, the
  owning epic's rule names the fix direction, and every week of additional
  Rust-boundary migration (sase-1qq, sase-1qv's affected area) built on top of a
  shared-lock store raises the blast radius.

### 5 · sase-1qi: restart cannot find crash-killed agents

- **Location:** `find_named_agent` (skips non-done records whose PID is dead).
- **Evidence.** Kill a waiter without `done.json`: the TUI lists it FAILED ("Runner
  exited without recording an error") but `sase agent restart <name>` reports
  not-found. On 2026-11-01 this forced manual `sase bead` work per epic for 27 waiters
  (16 land + 11 phase waiters).
- **Impact.** The restart primitive is the recovery path: without it, every host
  restart or crash-kill degrades to per-epic hand repair. The in-flight sase-1ra.11
  boot reconciler will relaunch reboot-stranded epics once per boot — it needs a
  working restart-by-name for dead members, or the reconciler inherits this gap on day
  one.
- **Why now.** Pair with (but do not merge into) the boot-recovery stack: fix the
  lookup first, so sase-1ra.11.1's recovery execution lands on a primitive that works.
  Medium size, crisp repro, directly relieves the next athena reboot.

### 6 · sase-1qx: commit-stage finalizer latency above 60 s targets

- **Location:** commit-stage finalizer — `publication: bead_pages` substep (~38 s
  median) and the `just fix` before-commit hook (~21 s median).
- **Evidence.** Installed re-prove on athena (73 runs, host commit `207ded297a`
  containing publisher-repair `6d615680b8`, ancestry 73/73, exclusions accounted):
  ~3.4x improvement over baseline, but median 101 s and finalizer p95 ~178–201 s still
  miss the 60 s targets. Per-substep timings come from
  `finalizers/commit/*.steps.jsonl`, so the two named substeps are the measured
  bottleneck, not a guess.
- **Impact.** A continuous per-turn tax on every agent on the installed publisher —
  the most frequently paid cost in this list. Sibling bead sase-1qy (77 quarantined
  Referenced By rows, one 2-day-pending cites event) is the same re-prove's other
  residual and a natural follow-up, not a substitute.
- **Why now.** The publisher repair just shipped inside the 0.19.0 line, so this is
  the measured remainder *after* the fix — exactly the right moment to take the next
  step while the measurement harness (`/tmp/measure_reprove.py` method, artifact
  paths on the bead) is fresh.

### 7 · sase-1rt: `preview_aggregate` builds the event snapshot twice

- **Location:** `src/sase/sdd/_artifact_link_store_aggregate.py:69`
  (`preview_aggregate`) + `src/sase/sdd/_artifact_link_store_rows.py:247`
  (`_load_store_truth_rows`).
- **Evidence.** Every reconcile preview scans every durable link-event root twice and
  parses the whole pending outbox twice. Measured on athena during the
  `artifact_link_backfill_timeouts` plan (sase, ~12.9k queued outbox rows):
  `store.preview_aggregate()` took 59 s and read the outbox 4 times; the plan's
  single-read pending snapshot halves it to 2, but the duplicated build remains
  (one full outbox parse costs ~3.7–4.7 s).
- **Impact.** The hourly `artifact_link_backfill` reconcile/repair (37–59 s) is the
  chop's longest uninterruptible step; since the chop refuses to start reconcile
  without headroom, a slow preview means sase's own reconcile gets deferred more
  often. Interactive `sase artifact doctor --fix` pays the duplicate cost too.
- **Why now.** Bounded, mechanical fix (pass the prebuilt `event_snapshot` into
  `_load_store_truth_rows`), with a counting test and a re-time on the real store as
  the acceptance bar — a high ratio of certain relief to effort, and it compounds the
  backfill-timeout plan that just landed.

## Excluded (not ranked)

- **Release-train `merged_head_sha` defect** (on sase-1s7.7.3, noted today): the single
  most urgent item in the repo, but it is owned live-work on an in-progress phase, not
  a rankable task bead. If it is not fixed inline, file it as a task bead.
- **sase-1qj** (reboot recovery, +1): covered by the in-progress sase-1ra.11 phase stack
  and child epic sase-1ra.11.1. Rank sase-1qi (#5) first so the reconciler inherits a
  working restart.
- **sase-1jf** (resume-in-place after update skew, +1): adjacent to Agent Hijack
  restart/crash-repair surfaces; sequence it after the hijack phases and sase-1ra.9.
- **sase-1s5.3** (dismissal lookup, reopened): needs owner triage of the reopen before
  adjacent dismissal/evidence work starts.
- **Flag retirements** (sase-1kb/1ks/1kt/1ku/1kv due v0.19.0, sase-1nu due v0.20.0):
  routine post-release retirements now that #322 merged; schedule normally, not as
  impact picks.
- **sase-j0 / sase-x4** (check-full red): `check-full` is explicit-only per the
  `check-full-is-explicit` decision; sase-j0 is already in progress. Not agent
  launch-now work.
- **Runner-ups, all READY:** sase-1he (finalizer 500 misclassified as Claude error,
  full agent re-run — rare but catastrophic; #8); sase-1qr (PID-reuse guard degraded
  to PID-only for scanned records — latent safety issue; #9); sase-1rc (worker row
  retired after 2 attempts, commit possibly missing from its published page —
  single-incident publication correctness; #10); sase-1ri (creator-as-actor on
  update/claim/remove/ready-mark, with the sase-1rg.10 template to copy; #11);
  sase-1qy (77 quarantined Referenced By rows + 1 pending cites event — follow #6);
  sase-1qp (queued monitor follow-ups hidden from `agent list` — operator visibility);
  sase-1qv (+1, slot-refusal policy still Python despite closeout claim — boundary
  hygiene, lower user pain); sase-1s2 (SIGTERM handler overwrite on runner import —
  small, safety-adjacent).

## Method

Read-only. Listed the full task corpus (open/ready/snoozed/in-progress), re-read the
2026-11-04 ten-bead final to avoid re-ranking landed work (its phases sase-1ra.1–.7
are CLOSED), screened all picks against live epics (sase-1s7.7, sase-1r2.6,
sase-1rq.2.1.4.1.5.3.1.3, sase-1ra.8–.12, sase-1s5.3, sase-1qh.7, sase-1rs.11), and read
the full bead record of every ranked pick plus the excluded near-misses. Ranked by
expected user-visible relief per unit effort right now, with data-integrity severity
(sase-1kp) promoted over frequency. Peer swarm reports were not consulted.
