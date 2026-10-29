# Root Cause Analysis: SASE Agent Commit Stage Latency and Publication Drain Bottlenecks

**Author:** researcher gem (`research.5h.gem`)  
**Date:** 2026-10-29  
**Target Architecture:** SASE Agent Finalizer & Commit Framework (`sase stitch create`, `agents_sync`, `sdd`)  
**Environment:** Athena (`gh_sase-org__sase`, `sase-core`)

---

## 1. Executive Summary & Core Diagnosis

A widespread observation in SASE agent workflows is that agents spend an unexpectedly large amount of time completing their "commit stages" — frequently stalling for 3.5 to 7.5 minutes (210s to 450s+) after problem-solving and code edits have already finished.

Through code inspection across `src/sase/workflows/commit/`, `src/sase/finalizers/`, and `src/sase/agents_sync/`, combined with production telemetry extracted from `finalizers/commit/attempt-*.main.steps.jsonl`, `~/.sase/logs/agent_publication_drains.jsonl`, and `sase doctor -C state.agent_publication_outbox -j`, this investigation has identified the precise root causes:

1. **The actual Git commit and push is NOT the bottleneck**: Creating the Git commit, syncing with upstream origin, rebasing, and pushing to GitHub consistently executes in **2.0 to 3.5 seconds** (<1% of commit stage elapsed time).
2. **Pre-commit formatting overhead is notable but secondary**: The configured pre-commit hook (`commit_hooks.before` running `just fix`) formats and checks the entire repository (12,800+ files, Ruff, Prettier, Keep-Sorted, doc renderers), consuming **20 to 40 seconds**.
3. **The primary bottleneck is post-commit synchronous publication and outbox draining (85% to 95% of elapsed time)**:
   - When an agent commits via `sase stitch create`, the workflow executes `run_agent_publication_step()`, which attempts synchronous execution of three heavy operations: `publish_bead_pages`, `publish_prompt_archive`, and `publish_committed_agent_hood` (which triggers `drain_agent_publications`).
   - A full publication drain builds a project-wide inventory across all runs and hoods (scanning 1,190+ runs and ~10,000 Git calls, taking 30–40s) and generates Markdown/chat pages across hoods (taking 75–145s).
   - Drains consistently exceed the 120.0s `SIGALRM` timeout bound (`DEFAULT_PUBLICATION_DRAIN_TIMEOUT_SECONDS`), logging `alarm_fired: true` and `error_class: timeout`.
4. **Lock serialization and concurrency stampede**:
   - Both `publish_prompt_archive` and `drain_agent_publications` serialize on a single repository flock: `sase-agents-sync.lock`.
   - When parallel agents (e.g., swarms of 5 researchers or concurrent phase workers) commit around the same time, the first agent acquires the lock and holds it for 120s to 220s during its heavy drain.
   - Subsequent agents block on the lock until their timeout expires, or queue up in a serialized cascade.
5. **Backlog feedback loop**:
   - Athena currently holds **3,501 quarantined publication requests** and **10,393 artifact link outbox entries**. The sheer volume of outbox files causes even "skipped" or unselected agent drains to spend 10 to 125 seconds simply reading and partitioning JSON entries.

---

## 2. Architectural Anatomy of the SASE Agent Commit Stage

To understand where time is spent, we must trace how an agent transitions from completing its turn to final settlement:

```
[Agent Turn Finishes]
        │
        ▼
[Host Controller: run_finalizers()]  (src/sase/finalizers/controller_run.py)
        │
        ▼
[builtin@commit: commit_execution.py]
        │
        ▼
[Subprocess: sase stitch create]  (src/sase/workflows/commit/workflow.py)
        │
        ├── Phase 1: Pre-commit Validation & Bead/Plan Hooks
        │     - validate_bead_action_before_commit()
        │     - handle_beads(), handle_sase_plan()
        │
        ├── Phase 2: Before-Commit Hook (commit_hooks.before)
        │     - Runs `just fix` (Ruff, Prettier, Keep-Sorted, Docs Renderers)
        │     - Duration: ~20s – 40s
        │
        ├── Phase 3: VCS Commit & Remote Sync (_git_commit_dispatch.py)
        │     - git add, git commit
        │     - git fetch origin master, git rebase origin/master
        │     - git push origin <branch>
        │     - Duration: ~2s – 3.5s  [FAST]
        │
        └── Phase 4: Post-Commit Publication Pipeline (workflow_publication.py)
              │
              ├── 4.1 publish_bead_pages()
              │     - Renders bead lineage & updates beads sidecar
              │
              ├── 4.2 publish_prompt_archive()
              │     - Enqueues to agents-publication-outbox.json
              │     - Acquires `sase-agents-sync.lock`
              │     - Pushes prompt archive, runs _drain_referenced_by
              │     - Duration: ~30s – 80s (or lock wait)
              │
              ├── 4.3 publish_committed_agent_hood() -> drain_agent_publications()
              │     - Acquires `sase-agents-sync.lock`
              │     - Inventory build (scans all project runs): ~35s
              │     - Hood publish & Markdown rendering: ~75s – 145s
              │     - SIGALRM bound: 120s
              │     - Duration: ~10s (if lock busy) to ~170s – 225s
              │
              └── 4.4 _drain_artifact_link_outbox_for_agent()
                    - Scans 10,390+ queued link records
                    - Partitions & publishes link events to machine store
                    - Duration: ~10s – 125s
```

### 2.1 The Two Execution Tiers

The commit stage is split across two tiers:
1. **The Host Finalizer Harness** (`src/sase/finalizers/controller_run.py`):
   Runs in the host orchestrator process. It authenticates the finalizer plan (`finalizer_plan.json`), observes dirty repositories, issues `final_context.json`, and spawns `sase stitch create` as a bounded subprocess tracked via `attempt-<N>.main.steps.jsonl`.
2. **The Commit Workflow Engine** (`src/sase/workflows/commit/`):
   Runs inside the workspace as `sase stitch create`. It executes the four phases depicted above.

---

## 3. Empirical Evidence & Telemetry Profiling

### 3.1 Step Timing Across Recent Production Agent Runs

An inspection of `attempt-1.main.steps.jsonl` across real production agent runs on Athena (project `gh_sase-org__sase`) provides unambiguous timing breakdowns:

| Run ID | Before Hook (`just fix`) | Git Commit & Push | Post-Commit Publication Pipeline | Total Commit Stage Duration | % Time in Publication |
|:---|:---:|:---:|:---:|:---:|:---:|
| **20261028170604** | 21.3s | 2.5s | **414.4s** | **438.3s** (7.3 min) | **94.5%** |
| **20261028181409** | 32.0s | 2.8s | **288.4s** | **323.4s** (5.4 min) | **89.2%** |
| **20261028200510** | 24.4s | 2.4s | **318.1s** | **345.0s** (5.8 min) | **92.2%** |
| **20261028200511** | 20.0s | 2.1s | **224.8s** | **247.0s** (4.1 min) | **91.0%** |
| **20261028200849** | 28.0s | 2.6s | **184.2s** | **214.9s** (3.6 min) | **85.7%** |
| **20261028204919** | 23.5s | 2.6s | **198.9s** | **225.0s** (3.8 min) | **88.4%** |
| **20261028221057** | 22.1s | 2.5s | **196.9s** | **221.6s** (3.7 min) | **88.9%** |

### 3.2 Granular Step Breakdown Within the Publication Pipeline

Examining the timestamped log events inside `attempt-1.main.steps.jsonl` reveals how the publication phase unfolds:

```json
{"v": 1, "t": 1793237428.71, "step": "before hook: just fix", "state": "start"}
{"v": 1, "t": 1793237456.68, "step": "before hook: just fix", "state": "ok"}          (+28.0s)
{"v": 1, "t": 1793237457.00, "step": "create_commit", "state": "start"}
{"v": 1, "t": 1793237459.27, "step": "create_commit", "state": "ok"}                  (+2.3s)
{"v": 1, "t": 1793237459.28, "step": "push", "state": "ok"}                           (+0.0s)
{"v": 1, "t": 1793237459.43, "step": "publication", "state": "start"}
{"v": 1, "t": 1793237508.43, "step": "The primary commit succeeded, but prompt archive publication was deferred: agents sync lock is busy", "state": "warn"} (+49.0s)
{"v": 1, "t": 1793237519.48, "step": "Primary commit succeeded, but this project already has 3499 quarantined requests... Last error: agents sync lock is busy (holder: pid 2543851, age 23s)", "state": "warn"} (+11.0s)
{"v": 1, "t": 1793237643.61, "step": "publication", "state": "ok"}                   (+124.1s)
```

Notice:
1. `publish_prompt_archive` consumed **49.0s** before deferring due to lock contention.
2. `publish_committed_agent_hood` consumed **11.0s** (waiting for `bounded_agents_lock` timeout of 10s) before deferring due to lock contention.
3. `_drain_artifact_link_outbox_for_agent` consumed **124.1s** scanning outboxes and publishing links.

### 3.3 Publication Drain Log Data (`agent_publication_drains.jsonl`)

When `drain_agent_publications` *does* acquire the lock, the detailed timing data recorded in `~/.sase/logs/agent_publication_drains.jsonl` illustrates where time is spent during a publication drain:

```json
{
  "timestamp": 1793249679.71,
  "pid": 2420235,
  "project_key": "gh_sase-org__sase",
  "active_requests": 5,
  "distinct_hoods": 2,
  "runs_scanned": 1192,
  "alarm_fired": true,
  "alarm_stage": "hood_publish:research",
  "outcome": "published",
  "stage_durations": {
    "payload_clean": 1.91,
    "pull_rebase": 0.64,
    "inventory_build": 37.91,
    "prepare": 147.11,
    "hood_publish:research": 142.12,
    "hood_publish:sase-1pj": 3.81,
    "commit": 26.64,
    "push": 3.29,
    "cleanup": 1.65,
    "manifest_verify": 0.05,
    "verify": 0.10
  }
}
```

Key takeaways from the drain telemetry:
- **`inventory_build` takes ~35s – 40s**: It scans 1,192 runs across hoods and invokes dozens of Git subprocesses.
- **`hood_publish` takes ~120s – 145s**: Preparing the Markdown files, prompt archives, and chat session histories for large hoods (like `research`) dominates execution time.
- **`alarm_fired: true`**: Because total duration exceeds 120s, the SIGALRM alarm fires on almost every active drain. When the alarm fires, the drain raises `PublicationDrainTimedOut` and fails the active request.

### 3.4 Outbox Health (`sase doctor -C state.agent_publication_outbox -j`)

A live inspection of the agent publication outbox via `sase doctor` reports:
- **Total quarantined requests**: **3,767** (3,501 in `sase`, 266 in `bob-cli`).
- **Error classification histogram**:
  * `timeout`: **2,910**
  * `lock_busy`: **439**
  * `other`: **396**
  * `index_lock`: **19**
  * `unstaged_changes`: **6**
  * `manifest_mismatch`: **3**
- **Artifact Link Outbox**: **10,393** queued records in `gh_sase-org__sase`.

The outbox is trapped in a vicious cycle: because drains take >120s, they time out; because they time out, requests are quarantined; because thousands of requests are quarantined, future inventory scans and outbox parsers do more work, driving up latency even further.

---

## 4. Root Cause Breakdown

### Root Cause 1: Synchronous Execution of Heavy Publication Work During Agent Turn Finalization

In `src/sase/workflows/commit/workflow.py` (lines 604–606):
```python
publication_result = self._run_agent_publication_step(cp)
```
The design intent of the SASE single-turn model is that commits should be host-owned, fast, and deterministic. However, `sase stitch create` delegates directly to `publish_committed_agent_hood` in `src/sase/agents_sync/_commit_publication_queue.py`:

```python
def publish_committed_agent_hood(...):
    # Enqueues the request into the durable outbox...
    outcome, target, item = _enqueue_committed_agent_publication(...)
    ...
    # BUT THEN IMMEDIATELY ATTEMPTS A SYNCHRONOUS DRAIN:
    return drain_agent_publications(
        target.project_key,
        git_runner=git_runner,
        preferred_key=item.logical_key if item is not None else None,
    )
```
Because `drain_agent_publications` is invoked inline during the commit command:
- Every agent run that commits must wait for a full inventory build and hood planning cycle.
- What should be an instantaneous metadata append (writing one JSON line to `agents-publication-outbox.json`) becomes a 2-to-4 minute batch processing job.

### Root Cause 2: Coarse-Grained Synchronization via `sase-agents-sync.lock`

Both `publish_prompt_archive()` and `drain_agent_publications()` acquire `sase-agents-sync.lock` using `fcntl.flock`:
- The lock covers the entire project sidecar clone (`~/.sase/projects/<project>/repos/agents`).
- Drains hold this lock across the entire duration of `inventory_build`, `plan_hoods`, `commit`, and `push` (often 120s to 220s).
- Any other agent attempting to commit during this window blocks on the lock.
- If multiple agents from a swarm (or concurrent phase workers) finish concurrently, they enter a lock stampede. When their `lock_timeout_seconds` (10s) expires, they fail with `agents sync lock is busy` and must defer.

### Root Cause 3: Massive Outbox Accumulation in the Artifact Link Subsystem

In `workflow_publication.py` (lines 235–238):
```python
_drain_artifact_link_outbox_for_agent(cp, checkpoint_save=checkpoint_save)
```
This invokes `drain_artifact_link_outbox()` in `src/sase/sdd/_artifact_link_outbox_drain.py`.
- The outbox has ballooned to **10,393 records**.
- Every single agent commit reads, parses, and filters this entire 10,000+ item JSON payload, even if the committing agent has zero relevant link updates.
- Parsing and partitioning this file alone takes **10.8 seconds** of pure CPU time. When operations are actually drainable or contend for `ARTIFACT_LINK_EVENT_LOCK`, this step takes **115s to 130s**.

### Root Cause 4: Global Pre-Commit Hook Scope (`just fix`)

In `default_config.yml`:
```yaml
commit_hooks:
  before: "just fix"
```
In the SASE repository, `just fix` is not scoped to the staged files. It runs:
- `ruff format src/ tests/` (12,800+ files)
- `ruff check --fix src/ tests/`
- `render_docs --format-only` and `render_docs --sase-only`
- `prettier --write "**/*.md"`
- `keep-sorted` across all YAML files
- `sync_footprint_catalog --write`

This comprehensive suite ensures impeccable repository cleanliness, but running it unconditionally on every single agent turn adds **20 to 40 seconds** of fixed overhead to every commit.

---

## 5. Recommended Solutions & Architectural Roadmap

To reduce the commit stage duration from **~300 seconds down to <10 seconds**, the following phased interventions are recommended:

### Phase 1: Decouple Publication Draining from the Synchronous Commit Path (Immediate Win)

**The Principle:** *Commits must enqueue; background workers must drain.*

In `src/sase/agents_sync/_commit_publication_queue.py`:
Currently, `publish_committed_agent_hood` enqueues the item and immediately calls `drain_agent_publications()`.
Similarly, `_drain_artifact_link_outbox_for_agent` in `workflow_publication.py` runs a full outbox drain synchronously.

**Recommended Change:**
1. Make `publish_committed_agent_hood` **enqueue-only** during the agent commit path:
   ```python
   def publish_committed_agent_hood(...):
       outcome, target, item = _enqueue_committed_agent_publication(...)
       if outcome.error or outcome.skip_reason:
           return outcome
       # Return immediately with queued=True; DO NOT drain synchronously!
       return CommitPublicationOutcome(queued=True)
   ```
2. Make `_drain_artifact_link_outbox_for_agent` enqueue-only or defer full replay:
   - When an agent commits, only write its pending read-link events to disk.
   - Defer bulk outbox reconciliation to an asynchronous background worker.

**Impact:**
- Eliminates **180s – 350s** of synchronous publication and drain latency from the agent's turn.
- Eliminates `sase-agents-sync.lock` contention across concurrent agents.
- Agents return to the user or host immediately after Git push succeeds (~3s).

### Phase 2: Delegate Draining to Lumberjack / Daemon Routines

Since publication is decoupled from the commit hot path, background draining must be handled reliably off-path:
1. **Lumberjack Routine**:
   Configure a periodic AXE/Lumberjack routine (e.g., every 5–10 minutes) or trigger an asynchronous background worker (`oneshot`) that runs:
   ```bash
   sase agent sync --project <project>
   ```
2. **Batch Amortization**:
   Instead of 5 swarm agents each independently attempting full 220s drains and colliding on locks, a single background routine drains the batched outbox once for all 5 agents.

### Phase 3: Outbox Backlog Reclamation & Hygiene

Athena currently carries 3,767 quarantined requests and 10,393 artifact link records that slow down inspection tools:
1. Run `sase agent sync --drop-retired` to purge permanently unpublishable entries.
2. Execute a one-time bounded recovery for recoverable quarantined requests:
   ```bash
   sase agent sync --project sase --retry-quarantined --retry-limit 50 --retry-error-class timeout
   ```
3. Archive or prune settled records in `state.artifact_link_outbox`.

### Phase 4: Scope Pre-Commit Hooks to Staged Files

Modify the `commit_hooks.before` recipe or create a dedicated `just fix-staged` hook:
- Instead of running Prettier and Ruff across all 12,800+ files in the project, pass the staged file list (`git diff --cached --name-only`).
- Run full repository linters during CI or `just check`, while keeping commit hooks strictly scoped to touched files.
- **Impact:** Reduces pre-commit hook duration from **~28s down to <2s**.

---

## 6. Latency Comparison: Current vs. Proposed

| Stage | Current Implementation | Proposed Architecture (Decoupled) | Savings |
|:---|:---:|:---:|:---:|
| **Pre-commit Validation** | ~0.5s | ~0.5s | 0s |
| **Before Hook (`just fix`)** | ~28.0s | ~2.0s *(scoped to staged)* | ~26s |
| **VCS Commit & Push** | ~2.5s | ~2.5s | 0s |
| **Prompt Archive Publication** | ~45.0s *(lock contention)* | <0.1s *(enqueue only)* | ~45s |
| **Agent Hood Publication Drain** | ~130.0s *(inventory + render)* | <0.1s *(enqueue only)* | ~130s |
| **Artifact Link Outbox Drain** | ~40.0s *(10k entry parse)* | <0.2s *(append only)* | ~40s |
| **Total Commit Stage Elapsed** | **~246.0s (4.1 min)** | **~5.3s** | **~240s (98% reduction)** |

---

## 7. Conclusion

The user's suspicion that SASE agents take an excessively long time in their commit stages is entirely justified. The commit stage currently acts not merely as a Git version control checkpoint, but as a synchronous batch-processing engine for project-wide documentation publishing, full repository code formatting, and heavy sidecar synchronization under coarse-grained file locks.

By **decoupling publication and draining into asynchronous outbox workers** and **scoping pre-commit hooks to staged changes**, SASE agent commit stages can be transformed from a **4-to-7 minute bottleneck** into a **sub-10-second operation**, radically improving multi-agent swarm responsiveness and overall system throughput.
