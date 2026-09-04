---
create_time: 2026-09-04
updated_time: 2026-09-04
status: research
---

# Making `sase stitch create` Reliable Under Contention And On Small Machines

## Research question

Why have recent SASE agents on Apollo failed with
`LLMInvocationError: Error: sase stitch create stitch_timeout`, and what change will
prevent this from recurring across fast and resource-constrained machines?

## Executive summary

The error is not an LLM outage. The model turn finished, submitted a valid final
declaration, and then the host-owned commit finalizer failed while waiting for its
`sase stitch create` subprocess. `LLMInvocationError` is only the wrapper used to carry
that finalizer failure through the provider invocation boundary.

Apollo recorded **nine** `stitch_timeout` finalizer results on September 3–4. Every
bounded stitch ran for exactly the old **600-second** limit:

- **Seven were false failures.** The primary commit existed, a matching
  `commit_results.json` marker named its SHA, and the checkpoint had completed through
  `publish_prompt_archive`. The subprocess was killed later, during auxiliary
  post-commit work, and the old finalizer classified the entire agent as failed before
  consulting the marker.
- **Two were real pre-commit timeouts.** Their only stdout was
  `Running before commit hook: just fix`; no commit marker existed. In the SASE repo,
  `just fix` depends on `_setup`, which can rebuild the Rust extension in release mode.
  That is environment preparation and native compilation inside the commit-critical
  path.

The incidents coincided with Apollo's ordinary 4-shared-vCPU/8-GB shape and
`max_running_agents: 10`. A temporary resize now reports 16 vCPU/31 GiB, so today's
capacity is not representative of the failures. On the larger shape, a live
`maturin`/Cargo release build still occupied a full CPU while multiple long-lived agent
runners were active.

Commit `ad1da7fc2` (2026-09-03,
`fix(finalizers): rescue stitch timeouts after the commit already landed`) is a good
emergency fix: it raises the outer cap to 30 minutes, uses SIGTERM before SIGKILL, and
turns a timeout into a warning when a new repo-matching commit marker exists and normal
dirty-tree reconciliation passes. Apollo's currently installed `b8f62f182` contains it.
The failed tracebacks point to the old unconditional raise at `commit_dispatch.py:310`,
proving those processes had imported pre-fix code; updating files on disk does not
update an already-running Python agent.

That patch should be deployed and all pre-update SASE/ACE agent processes allowed to
finish or restarted. It prevents the seven false failures. It is not the complete
low-resource solution: a fixed 30-minute envelope still combines formatting, cold
environment setup, commit/push, sidecar writes, and publication into one opaque timer.

The durable solution is to make the **primary commit plus its verified marker** the
success boundary, enqueue every auxiliary publication for idempotent background
delivery, and serialize commit finalizers in a host-wide one-at-a-time lane. Move
bootstrap/native builds out of `commit_hooks.before`, provide a cached
revision/ABI/platform-keyed `sase-core-rs` wheel (or shared compiler cache), and add
per-stage timing/checkpoints. This makes the critical section small and predictable,
eliminates shared-sidecar contention, and trades excess CPU for queueing rather than
false failure.

## 1. Apollo incident evidence

The evidence below came from read-only SSH inspection of Apollo on 2026-09-04:

- `sase agent list -a -j` identified recent visible failures.
- A recursive search of
  `~/.sase/projects/*/artifacts/ace-run/202609/**/finalizer_result.json` found failures
  no longer present in the conservative agent-list view.
- For each run, `finalizer_result.json`, the bounded-subprocess inputs/stdout,
  `commit_state.json`, `commit_results.json`, `done.json`, and `error_report.md` were
  correlated.
- The stitch start is the commit-message file mtime; the end is the finalizer's inputs
  artifact mtime, written immediately after the child returns. Eight preserved both
  timestamps and measured exactly 600 or 601 seconds; the ninth had lost its message
  file but ended with the same timeout diagnostic and state shape.

| Start (local date/time) | Agent              | Repo            | Last durable state                         | Classification          |
| ----------------------- | ------------------ | --------------- | ------------------------------------------ | ----------------------- |
| Sep 3 09:22             | `sase-w0.1`        | main            | commit `f67169ea7`; publication checkpoint | false failure           |
| Sep 3 14:18             | `sase-w2.2`        | main            | commit `e09a5f9ab`; publication checkpoint | false failure           |
| Sep 3 14:26             | `sase-w3.2`        | main            | only `just fix`; no marker                 | real pre-commit timeout |
| Sep 3 14:52             | `c--code`          | main            | commit `d60eecd87`; publication checkpoint | false failure           |
| Sep 3 15:50             | `sase-w3.1--code`  | main            | commit `8c3e7b6bf`; publication checkpoint | false failure           |
| Sep 3 15:52             | `research.0.final` | research        | commit `a4333c690`; publication checkpoint | false failure           |
| Sep 3 16:19             | `d--code`          | main            | commit `92dfd5ebd`; publication checkpoint | false failure           |
| Sep 3 17:46             | `bob-cli-1w.1`     | external `sase` | commit `d5747a3d7`; publication checkpoint | false failure           |
| Sep 4 00:49             | `sase-w0.5--1`     | main            | only `just fix`; no marker                 | real pre-commit timeout |

The seven false failures had a particularly strong consistency signal:

1. stdout said `create_commit completed successfully`;
2. `commit_results.json` contained a newly created marker whose `cwd` matched the
   finalizer's target repo;
3. `commit_state.json` contained the same SHA and listed `dispatch`, `file_hooks`,
   `after_hook`, `write_result_marker`, `publish_bead_pages`, and
   `publish_prompt_archive` as completed;
4. `finalizer_result.json` nevertheless contained no evidence and reported
   `stitch_timeout`.

The old branch explains item 4. It tested `stitch.timed_out` and raised before loading
new commit markers. The current branch calls
`_rescue_landed_commit_after_bounds_failure` first, then continues through the same
marker, hook reconciliation, and unexpected-dirty-path checks used by a normal success.

### What hung after the commits?

The retained artifacts bracket but do not uniquely identify the post-commit call. The
checkpoint was saved after prompt-archive publication and before `publish_agent_hood`.
Between those points the workflow refreshes a committed plan header and calls
`publish_committed_agent_hood`; either can touch a sidecar and perform Git work. The
artifacts have no start/end marker per substage, so naming one as the sole cause would
overstate the evidence.

There is direct contention evidence. One timed-out stdout reports that prompt archive
publication was deferred because the shared agents checkout already had
`.git/index.lock`. Multiple `commit_results.json` files also show plans/beads sidecar
commits immediately before the long silent interval. The architecture makes this
plausible: each agent commits its own workspace, then several agents converge on shared
plans, beads, and agents checkouts.

SASE already applies useful local defenses:

- agents-sync uses a bounded `sase-agents-sync.lock`;
- Git network operations default to a 120-second timeout;
- agent-hood publication has a 120-second SIGALRM guard when it runs on a POSIX main
  thread;
- publication requests live in a durable outbox.

But auxiliary publication is still synchronously drained by the committing process. The
guard is conditional, several post-commit steps sit outside it, and the entire operation
is ultimately judged by one outer wall-clock deadline. The incident artifacts show that
this composition is not reliably bounded in practice.

## 2. Why `just fix` exhausted the budget

The two genuine cases never left the configured before-commit hook. In this project:

```text
commit_hooks.before = "just fix"
just fix -> fmt-py + fmt-docs + fmt-md + fix-keep-sorted
fmt-py/fmt-docs -> _setup
_setup -> validate environment -> possibly rust-install
rust-install -> maturin develop --release -> cargo rustc --profile release
```

This is appropriate for making a development checkout usable, but it is a poor match for
the last commit-critical section of an agent run:

- Every numbered workspace has its own Rust `target` tree, so the default local Cargo
  cache is not shared across agents.
- Cargo defaults `build.jobs` to the logical CPU count. Several cold workspaces can each
  try to consume the host at once; Cargo exposes `CARGO_BUILD_JOBS` for limiting that
  concurrency.
  [Cargo configuration](https://doc.rust-lang.org/cargo/reference/config.html#buildjobs)
- Cargo documents both a configurable target directory and `sccache` for sharing build
  work across workspaces.
  [Cargo build cache](https://doc.rust-lang.org/stable/cargo/reference/build-cache.html)
- Apollo's merged default allowed ten occupied runner slots on a four-vCPU shared
  machine. The slot gate limits agent count, not CPU/RAM consumed by each agent's child
  processes, and a running agent retains its slot during finalization.

Increasing the stitch cap from 10 to 30 minutes provides needed headroom, but scales
poorly: the slowest machine, coldest cache, largest repository, and worst concurrent
load determine whether a valid run is called failed. It also makes a genuinely wedged
hook take three times longer to surface.

## 3. Timeout and process semantics

The current bounded runner is substantially safer than plain `subprocess.run`:

- it incrementally drains stdout/stderr into bounded buffers, preventing pipe-fill
  deadlocks and unbounded memory use;
- it starts a new POSIX session, allowing termination of the entire descendant process
  group rather than only the immediate `python -m sase` child;
- current code sends SIGTERM, gives the group five seconds to clean up, then sends
  SIGKILL and reaps the process.

These choices align with Python's documented primitives: a `run()` timeout kills and
waits for the direct child, while `start_new_session=True` creates a distinct POSIX
session suitable for group management.
[Python subprocess documentation](https://docs.python.org/3/library/subprocess.html#subprocess.run)

The remaining semantic issue is not process cleanup; it is using child-process exit as
the truth source after an irreversible commit. Once a commit marker and repository state
prove that the primary mutation landed, a late timeout says only that ancillary work did
not finish. Treating it as if the commit failed both lies to the user and makes
automatic retry dangerous because the primary action is not idempotent.

The current rescue correctly keeps `stitch_timeout` non-retryable and uses durable
evidence instead. That behavior should remain.

## 4. Evaluation of the fix already on `master`

Commit `ad1da7fc2` implements three changes:

1. **Evidence-based rescue.** A bounds failure is downgraded only if the current run
   added a marker for the same repository. The normal clean-tree/hook reconciliation
   still runs, so a marker alone cannot hide remaining attributable dirt.
2. **30-minute hard cap.** `HARD_MAX_SUBPROCESS_TIMEOUT_SECONDS` rose from 600 to 1800.
3. **Graceful escalation.** Timeout and output-cap paths now send SIGTERM before
   SIGKILL, reducing stale Git lock files and giving subprocesses a chance to flush
   state.

This is a sound compatibility patch and should not be reverted. It directly prevents the
observed false-negative classifier, is safe against duplicate retry, and retains a
finite kill bound.

It leaves four reliability gaps:

- A pre-commit hook can still spend the whole 30 minutes bootstrapping or compiling.
- The timeout artifact says only `stitch_timeout`; it does not record the active stitch
  phase, per-phase elapsed time, last progress, load, or child command.
- Auxiliary plans/beads/agent publication remains inside the synchronous stitch process
  even though SASE already has durable retry queues.
- A package update affects only newly started Python processes. Long-running ACE and
  agents keep the imported old classifier until restarted.

No post-update failure window is yet long enough to establish field reliability: Apollo
had `b8f62f182` installed for less than an hour when inspected. The absence of a new
error in that interval is reassuring but not validation.

## 5. Options considered

### A. Only increase the timeout

Keep 1800 seconds or make it machine-configurable.

This is useful as a safety net, not as the design. It lets legitimate slow work finish
but does not distinguish progress from deadlock, does not prevent contention, and delays
a real failure. Per-machine tuning also makes correctness depend on fleet configuration
drift.

### B. Remove the timeout

This avoids false timeout failures but lets a lost child, lock cycle, blocked credential
prompt, or tool bug hold an agent and workspace forever. It is unacceptable for an
automatic finalizer.

### C. Retry `sase stitch create`

This is unsafe after dispatch because the first attempt may have committed even when its
process never returned. SASE's decision to keep `stitch_timeout` out of retryable
diagnostics is correct. Resume is safe only from a validated checkpoint whose primary
dispatch state is known.

### D. Keep synchronous publication but add more nested timeouts

Stage-specific bounds improve diagnostics, but multiple locks, Git subprocesses, and
native calls still share the critical path. Timeout layering also creates ambiguous
partial completion unless every step is idempotent and checkpointed. Use this for the
required commit/hook phases, not optional publication.

### E. Durable asynchronous publication plus serialized finalization

Commit, save evidence, enqueue derived work, and return; one background worker drains
the queue. This is the transactional-outbox shape: durable state and a replayable work
record are saved first, and an independent worker performs delivery later. The pattern
exists specifically to avoid making a primary state change and a fallible publication
one synchronous dual-write.
[Microsoft's transactional outbox guidance](https://learn.microsoft.com/en-us/azure/architecture/databases/guide/transactional-out-box-cosmos)

SASE already has most of this mechanism. The missing step is to stop draining the
agent-publication outbox on the commit call stack and make any queue gap reconstructible
from the durable commit marker. A host-wide one-at-a-time finalizer lane additionally
turns a burst of agents into orderly queueing rather than concurrent formatters,
compilers, and shared-sidecar writers. This is the strongest option.

## 6. Reliability requirements for the implementation

The long-term fix should preserve these invariants:

1. **A commit is successful only with proof.** Require a new repo-matching marker,
   commit SHA/tree evidence, and no remaining attributable dirty paths. Timeout alone
   never overrides contradictory repository state.
2. **No blind retry after the mutation boundary.** Recovery loads a checkpoint and
   reconciles HEAD/marker state; it never starts a fresh commit because the parent
   process returned an ambiguous code.
3. **Publication is durable but not synchronous.** Enqueue prompt archive, agent hood,
   plan-header refresh, artifact-link updates, and other derived projections. If an
   enqueue write is interrupted, a reconciler deterministically derives missing work
   from the commit marker. Queue consumers must be idempotent and keyed by project,
   repository, commit SHA, and operation.
4. **One commit finalizer runs per host by default.** Acquire a crash-releasing OS lock
   or durable FIFO lease before the stitch clock begins. Waiting for the lane is visible
   as `queued_for_finalizer`, not `stitch_timeout`. Keep an override for measured
   high-capacity hosts, but the portable default is one.
5. **The before hook is prepared and offline.** It may format or validate, but it must
   not install dependencies, update linked checkouts, build a native release artifact,
   or require network access. If tools are missing/stale, fail immediately with an
   actionable `finalizer_environment_unprepared` diagnostic.
6. **Build once, reuse everywhere.** The workspace provisioner builds or downloads one
   `sase-core-rs` wheel keyed by source revision, Python ABI, OS, and architecture, then
   installs that wheel into numbered workspaces through the existing `SASE_CORE_WHEEL`
   seam. `sccache` is a fallback, not the correctness mechanism. Constrain remaining
   Cargo work with a host-derived `CARGO_BUILD_JOBS` value.
7. **Timeouts are stage-specific and observable.** Persist `stage_started`,
   `stage_completed`, duration, command, last output/progress time, and termination
   signal for before-hook, dispatch, after-hook, evidence reconciliation, and enqueue.
   Retain a generous overall 30-minute kill switch, but a timeout diagnostic names the
   exact phase.
8. **Background Git reads avoid needless locks.** Where safe for read-only status/log
   scans, set `GIT_OPTIONAL_LOCKS=0`; Git documents this specifically for background
   processes that should not refresh the index and contend with writers.
   [Git environment documentation](https://git-scm.com/docs/git#Documentation/git.txt-codeGITOPTIONALLOCKScode)
9. **Old runtimes are visible.** Record the SASE code revision in `agent_meta.json` and
   timeout artifacts. After an update, ACE should label still-running agents as using an
   older runtime so operators know that on-disk fixes do not apply to them.
10. **Stress tests model the failure, not only a mock return value.** Run concurrent
    finalizers against shared sidecars; inject a slow before hook, blocked publication,
    index-lock contention, child ignoring SIGTERM, crash after commit-before-enqueue,
    and a one-CPU/low-memory configuration. Assert no duplicate commits, no orphaned
    process groups, no false failed status after verified commit, and eventual outbox
    convergence.

## Recommended solution

Adopt the solution in two horizons.

**Immediately:** require `ad1da7fc2` or newer on every machine, then restart ACE and
retire/restart any pre-update agent processes before trusting the fix. Keep its
marker-based timeout rescue, 30-minute outer cap, and TERM-to-KILL escalation. On
currently small hosts, temporarily set `max_running_agents` to 1–2 and
`CARGO_BUILD_JOBS` to 1–2; these are containment measures, not the final architecture.

**Implement next:** make the primary commit marker plus clean-tree reconciliation the
end of the synchronous success path. Atomically/deterministically enqueue all derived
publication and let `sase agent sync` or a supervised worker drain it later. Put commit
finalizers through a host-wide FIFO lane with concurrency 1 by default, starting the
stitch execution deadline only after admission. Replace the SASE repo's `just fix`
commit hook with a prepared/offline formatting recipe, and have workspace provisioning
provide a cached `sase-core-rs` wheel so finalization never invokes Cargo. Add per-stage
checkpoint/timing artifacts and the contention/crash tests listed above.

**In short: deploy the existing evidence-based rescue now, then remove compilation and
publication from the commit-critical path and serialize the small remaining critical
section.** This is more reliable than tuning a larger timeout, remains bounded when a
tool truly hangs, and degrades gracefully on a one-core machine by queueing work instead
of failing completed agents.
