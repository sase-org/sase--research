# Why SASE Agent Commit Stages Take So Long

**Question:** Commit stages feel very slow — why, and what should change?

**Short answer:** There is no single slow step. The commit path is a long
*sequential* pipeline in which every repository is stitched one at a time,
and almost every step inside it can legitimately wait on the network, on a
lock, or on another model turn. The dominant costs are (1) per-repo
`git fetch` / `rebase` / `push`-with-retry inside every stitch, each with
multi-minute timeouts; (2) a 30-minute per-stitch subprocess allowance that
lets one stuck repo look like a hung agent; (3) four to five full dirty-state
rescans of every repo per commit; and (4) an LLM conflict-repair turn plus a
resume stitch on any rebase conflict. Fix the network-retry budget and the
sequential fan-out first; everything else is second-order.

## What "the commit stage" actually runs

The agent-visible "commit" is `builtin@commit`, orchestrated by
`execute_commit_finalizer` (`src/sase/finalizers/commit_execution.py`), which
fans out per repository through `dispatch_commit_decisions`
(`src/sase/finalizers/commit_dispatch.py`). Each repository runs
`sase stitch create` as a child `python -m sase` subprocess
(`src/sase/finalizers/commit_repair_stitch.py::_run_stitch_argv`), whose body
is `CommitWorkflow.run` (`src/sase/workflows/commit/workflow.py`). Around
that core there are reconciliation scans before dispatch, residual-dirt
checks after dispatch, discarded-work guards, an unpushed-commit resume
path, a conflict-repair LLM turn, per-commit file hooks, and agent
publication (bead pages, prompt archive, agent hood).

Rough order for one commit finalizer invocation:

1. `prepare_commit_dirty_state` → 2× `collect_dirty_state` + SDD/bead
   auto-commits (`src/sase/finalizers/reconciliation_state.py`).
2. Load/validate the accepted declaration; checkpoint recovery
   (`resume_owned_pending_checkpoint`); already-clean resume
   (`resume_unpushed_already_clean_repos`).
3. `dispatch_commit_decisions`: loop over repos **sequentially**
   (`while index < len(pending)`), one `run_stitch_create` per repo, with
   inline conflict repair (`resolve_commit_conflict`) on `EXIT_CODE_CONFLICT`.
4. `reject_discarded_dirty_work`, `ensure_no_residual_dirt`
   (re-scans state again), unpushed-local-commit checks, memory guard.
5. Inside each stitch (`CommitWorkflow.run`): bead handling → before-hook →
   VCS dispatch (`create_commit`) → file hooks → after-hook → tracking →
   agent publication.

Any of steps 1–5 can add minutes, and they add *serially*.

## Where the time goes (ranked)

### 1. Every stitch does fetch + rebase + push-with-retry (the biggest cost)

`GitCommitDispatchMixin.vcs_create_commit`
(`src/sase/vcs_provider/plugins/_git_commit_dispatch.py`) does, in order:

- `_sync_with_origin_after_commit`: `git fetch origin <default> --quiet`
  with `timeout=600`, then `git rebase --autostash origin/<default>` with
  `timeout=600` (`_rebase_onto_origin_default`).
- `_push_current_branch_with_rebase_retry`: up to
  `_PUSH_REBASE_RETRY_LIMIT + 1` = **4 push attempts**, and between attempts
  another `fetch` (600 s) plus another rebase (600 s).

So one repository commit can issue on the order of 2 fetches, 2 rebases,
and up to 4 pushes before it fails. Each git op in the generic
`CommandRunner._run` (`src/sase/vcs_provider/_command_runner.py`) defaults
to `timeout=300`, with the fetch/rebase paths explicitly raised to 600.
A slow or contended remote, a large fetch, or a lock-wait therefore
contributes *minutes per repo*, and multi-repo commits multiply it because
dispatch is sequential (see §2).

Push races between concurrent agents make this worse by design: on a
collision the code pulls/rebases and retries, and the PR path
(`vcs_create_pull_request`) adds `ls-remote --heads` (60 s), a
`pull --no-edit`, and a up-to-10-iteration `_resuffix_and_push` loop. This
is correct behavior under contention, but it is slow behavior.

### 2. One repo at a time, each allowed 30 minutes

`dispatch_commit_decisions` processes `pending` with a plain index loop —
no parallelism across repositories. `_run_stitch_argv` gives **each**
stitch `timeout=HARD_MAX_SUBPROCESS_TIMEOUT_SECONDS` = **1800 s**
(`src/sase/finalizers/bounded_subprocess.py:21`,
`src/sase/finalizers/commit_repair_stitch.py:509`). A single stuck
`fetch`/`push`/hook therefore lets one repo consume up to 30 minutes while
the agent shows nothing but "commit in progress". With N dirty repos
(main + siblings + externals + SDD sidecars), worst-case wall time scales
as N × 30 min. Even the happy path pays N × (Python interpreter startup +
`python -m sase` import + per-repo git work) serially.

### 3. The same dirty state is scanned four to five times per commit

`execute_commit_finalizer` calls `prepare_commit_dirty_state` at entry,
again after checkpoint recovery, again after the already-clean branch
(twice in that branch), and `ensure_no_residual_dirt` / `collect_dirty_state`
re-scan after dispatch. Each `prepare_commit_dirty_state` runs
`collect_dirty_state` **twice** (before and after SDD auto-commits), and
each `collect_dirty_state`
(`src/sase/llm_provider/commit_finalizer_state/__init__.py`) scans the
main repo plus every configured sibling, every opened external, and every
SDD/bead sidecar via `git_changed_files` (`status --porcelain=v1
--untracked-files=all`, `timeout=20`) and `git_status_records`
(`timeout=5`). Fingerprinting (`dirty_path_fingerprints`) runs
`git hash-object` per dirty path (`timeout=5` each), and
`stitch_attempt_input_fields` plus `progress_fingerprint` re-run
`dirty_path_fingerprints` and `git_head_commit_id` per repo per attempt.
On a big worktree (or a machine-wide shared sidecar such as the agents
prompt archive, scanned concurrently by many agents) this is dozens to
hundreds of git subprocesses per commit, serialized, before any commit
happens. The status layer already notes why: without
`--no-optional-locks`, status takes git's optional index lock and contends
with writers on shared checkouts
(`src/sase/llm_provider/commit_finalizer_git_status.py:1-12`).

### 4. Any conflict buys a full extra model turn plus a resume stitch

On `EXIT_CODE_CONFLICT`, dispatch calls `resolve_commit_conflict`
(`src/sase/finalizers/commit_repair_conflict.py`), which runs
`run_conflict_repair_turn` — a real LLM invocation via
`invoke_with_instructions`/`finalizer_owned_turn` — and then a
`stitch create --resume` subprocess for the same repo. So a conflicted repo
costs: failed stitch + model repair turn + resume stitch + the rebase
semantic-conflict loop (`_continue_rebase_resolving_semantic_conflicts`,
up to 20 iterations) that preceded it. One conflict can easily exceed the
cost of all happy-path stitches combined, and the agent surface shows
little of it (only step-channel `emit_step` events).

### 5. The post-dispatch tail is slow, serial, and nearly invisible

After VCS dispatch succeeds, `CommitWorkflow.run` still must do, per repo,
in order: `_run_file_hooks` (`produce_commit_file_hooks`, which resolves
providers, classifies repos, and derives/dispatches file events),
`run_after_commit_hook` (arbitrary user shell command, waited on with no
timeout of its own — `_run_hook_command` blocks in `process.wait()`),
`create_patch` / `write_result_marker` / `append_commits_entry`,
`refresh_deltas_after_commits_change`, `close_assigned_bead_after_commit`,
and `run_agent_publication_step` (bead-page publication, prompt-archive
publication, agent-hood publication, artifact-link outbox drain, each with
its own git I/O and checkpoint writes). None of these is individually
huge, but they run inside the stitch subprocess after the push, so the
push looks done while the agent still waits.

### 6. Observability gap makes normal latency look like a hang

Stitch progress is emitted on the finalizer step channel (`emit_step` /
`make_progress_tick`, `src/sase/finalizers/steps.py`), and hook evidence
lands in `commit_hooks/*.json` metadata with durations
(`src/sase/workflows/commit/command_hooks.py`). But the agent's headline
progress text does not advance per sub-step the way it does during
planning/launch, so a 5–15 minute commit (normal under the budgets above)
reads as "stuck". The prior `agent_8h` investigation (unrelated codebase
area) showed the same human-factors pattern: long silent commands plus a
frozen live view equals a stall report even when the process is alive.

## Recommended solution

**Cap the network-retry budget per repo and make the commit pipeline
deadline-visible; parallelize only after that.**

1. **Bound one repo's network work (biggest win).** Give the whole
   fetch→rebase→push sequence a single per-repo deadline (e.g. 3–5 min
   total) instead of independent 300/600 s timeouts per attempt, and cut
   `_PUSH_REBASE_RETRY_LIMIT` from 3 to 1 inside the finalizer path,
   deferring further retries to `stitch create --resume`. A repo that
   cannot land in a few minutes should fail fast with the evidence already
   collected (`stitch_bounds_failure_message` already renders elapsed time
   and hook tail — keep that) rather than burn 10+ minutes silently.
2. **Fail fast on rebase contention.** When
   `_sync_with_origin_after_commit` or the push-retry rebase hits a
   conflict, return the `CONFLICT` path immediately instead of running the
   20-iteration semantic-resolver loop inline; leave semantic resolution
   to the repair turn or the human resume. Inline resolution multiplies
   the most expensive path (conflict) by the most expensive operation
   (repeated rebase + model turn).
3. **Stop re-scanning the world.** Cache one `collect_dirty_state` per
   finalizer invocation and invalidate only on observed mutation (a stitch
   landed, a resume ran), instead of re-collecting after every branch.
   At minimum, hoist the pre/post-reconciliation scans so
   `prepare_commit_dirty_state` is called once, not four to five times.
4. **Surface per-stage deadlines in the agent view.** Promote the existing
   step-channel events (`fetch`, `rebase`, `push`, `hooks`, `publication`)
   with elapsed time into the agent's headline progress, and log a
   per-repo timing breakdown (scan / stitch / fetch / rebase / push /
   hooks / publication) into the attempt outcome JSON. Most "why is this
   slow" questions die once the agent can say "repo X, push attempt 2,
   90 s elapsed".
5. **Do not start with cross-repo parallelism.** Parallel stitches would
   speed the multi-repo case but would also multiply contention on shared
   sidecars and the agents-sync lock (the status module's lock comments
   warn exactly about this). Revisit only after the retry budget is
   bounded and scans are cached; then parallelize at most the read-only
   scans, keeping mutations serial per checkout.

## Caveats and verification

- This is a code-path analysis, not a timed reproduction: I traced
  `commit_execution.py` → `commit_dispatch.py` →
  `commit_repair_stitch.py` → `workflows/commit/workflow.py` →
  `_git_commit_dispatch.py`, plus the status/fingerprint, hook, file-hook,
  and publication helpers cited above. Timeout constants and retry limits
  are quoted from those files.
- I did not run a live multi-repo commit under instrumentation, so the
  ranking (network retries > rescans > repair turn > tail) is by budget
  analysis (timeout × attempts × serial fan-out), not measured wall time.
  The natural follow-up is to add the per-stage timing log from
  recommendation 4 and read one slow commit's attempt JSON — that single
  artifact would confirm or reorder these causes definitively.
