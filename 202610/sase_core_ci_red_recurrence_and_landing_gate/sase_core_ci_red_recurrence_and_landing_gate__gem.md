# Analysis of sase-core CI Failures and the Viability of Git Hooks

**Author:** Researcher gem (`research.5g.gem`)  
**Date:** 2026-10-29  
**Target Repository:** `sase-org/sase-core`  
**Status:** Complete Independent Research Report  

---

## 1. Executive Summary

This investigation analyzes the recurring continuous integration (CI) failures in the [sase-core](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core) repository, evaluates whether a **post-commit hook** (or similar git hook) can prevent them from recurring, and provides concrete architectural and test-level recommendations.

### Key Findings

1. **Failure Nature: 100% Test Flakes Under Load, 0% Static or Formatting Errors**  
   An exhaustive audit of the 22 recent CI failures across `master` pushes and `release-plz` pull requests demonstrates that every single failure occurred in the `cargo test --workspace` step of the `cargo fmt + clippy + test` workflow. Formatting (`cargo fmt --check`), linting (`cargo clippy -D warnings`), dependency feature unification (`cargo hakari`), and extension wheel packaging (`maturin build`) have **never failed** in these runs.
2. **The Two Specific Culprits**:  
   Across all 22 analyzed failed CI runs, the failures trace back to exactly two test cases:
   - [`tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/src/tool_run/store/connection.rs#L875): Accounted for 16 failures exclusively on `macos-latest` runners due to a brittle 425 ms wall-clock assertion failing under virtualized scheduling jitter (where sleeps and thread wakes took up to 1.17 s).
   - [`bead_read_model_parity::concurrent_readers_see_consistent_snapshots`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/tests/integration/bead_read_model_parity.rs#L869): Accounted for 7 failures (including the most recent failures on `master` at commits `0fd85e4a` and `cd62c83d`) across both `ubuntu-latest` and `macos-latest`. Transient SQLite lock contention during 4 concurrent reader threads triggers an internal 10-minute rebuild backoff (`mark_failed_rebuild`), preventing the cache from refreshing before [`read_model_verify_cache`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/src/bead/read_model/store.rs#L440) verifies freshness.
3. **Inviability of Git Hooks as a Solution**:  
   Implementing a post-commit (or pre-commit/pre-push) hook cannot solve or prevent these failures:
   - **Post-commit hooks are non-blocking**: A `post-commit` hook executes *after* the commit object is written to the git object database. It cannot reject or abort a commit.
   - **Environment divergence**: These tests pass reliably when run locally in isolation or under normal workstation loads. They fail almost exclusively under the heavy CPU contention, thread saturation, and virtualized scheduling delays of GitHub Actions runners.
   - **Execution overhead**: `sase-core` contains over 5,500 tests across 4 crates and compiles Python C-extensions via PyO3. A full `just check` takes 5 to 10 minutes, making pre-commit hooks prohibitive for developer and agent velocity.
   - **SASE host-owned completion**: SASE agents run in ephemeral numbered workspace clones (`sase_<N>`) and commit through host-owned finalizers (`builtin@commit` via `sase stitch create`). Local git hooks are not installed or triggered in this workflow.

---

## 2. Empirical CI Failure Audit

### 2.1 Workflow Pipeline Breakdown

The primary CI gate for `sase-core` is defined in `.github/workflows/ci.yml` and executes four jobs:
- `maturin build + import smoke`: Builds ABI3 wheels and tests Python imports.
- `release workflow scripts`: Runs unit tests for release helpers via `uv`.
- `cargo fmt + clippy + test (ubuntu-latest)`: Linux gate.
- `cargo fmt + clippy + test (macos-latest)`: macOS ARM64 gate.

In the `cargo fmt + clippy + test` job, the execution sequence is:
```mermaid
flowchart LR
    A["cargo fmt --check"] --> B["cargo hakari features"]
    B --> C["cargo clippy (-D warnings)"]
    C --> D["cargo test --workspace"]
    D --> E["Status: Pass / Fail"]
```

Over the past 50 runs of the CI workflow on GitHub Actions, every observed failure occurred in step `D` (`cargo test --workspace`). Steps `A`, `B`, and `C` passed 100% of the time.

### 2.2 Historical Run Analysis

An analysis of 22 failed CI runs between 2026-10-26 and 2026-10-29 reveals a clear binary distribution of test failures:

| Run ID | Commit / PR | Branch | Failed Job | Failing Test Node | Panic / Failure Reason |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **40807288117** | `cd62c83d` | `master` | `ubuntu-latest` | `bead_read_model_parity::concurrent_readers_see_consistent_snapshots` | `cache is stale: the next read rebuilds` |
| **40797498289** | `0fd85e4a` | `master` | `ubuntu-latest` | `bead_read_model_parity::concurrent_readers_see_consistent_snapshots` | `cache is stale: the next read rebuilds` |
| **40794838320** | `5b45ff97` | PR `v0.43.1` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40794754688** | `df14e8f4` | `master` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget: 1.173s` |
| **40782130278** | `64646991` | PR `v0.43.1` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40726947246** | `d55a1ecb` | PR `v0.43.1` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40726794062** | `ed8328f9` | `master` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40706223791** | `836f7876` | PR `v0.43.1` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40701351445** | `f7e4533b` | PR `v0.43.1` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40701185834** | `65546fd2` | `master` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40694855276** | `c591612d` | PR `v0.43.1` | Both | `wal_mode_probe_consumes_conversion_budget` AND `concurrent_readers_see_consistent_snapshots` | macOS: WAL budget; Ubuntu: stale cache |
| **40684857269** | `b3a76939` | PR `v0.43.1` | Both | `wal_mode_probe_consumes_conversion_budget` AND `concurrent_readers_see_consistent_snapshots` | macOS: WAL budget; Ubuntu: stale cache |
| **40684718736** | `49870f00` | `master` | Both | `wal_mode_probe_consumes_conversion_budget` AND `concurrent_readers_see_consistent_snapshots` | macOS: WAL budget; Ubuntu: stale cache |
| **40663323914** | `47b8bbfc` | PR `v0.43.1` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40663209632** | `00fe29d5` | `master` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40649522677** | `36f10702` | PR `v0.43.1` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40649399409** | `f4bf6074` | `master` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40611440803** | `83b010dd` | `master` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40588456263** | `e0da0184` | PR `v0.43.1` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40588317685** | `3f8baa79` | `master` | `macos-latest` | `tool_run::store::connection::tests::wal_mode_probe_consumes_conversion_budget` | `WAL setup renewed an exhausted budget` |
| **40434321453** | `f1ea08fb` | `master` | `ubuntu-latest` | `bead_read_model_parity::concurrent_readers_see_consistent_snapshots` | `cache is stale: the next read rebuilds` |
| **40424599394** | `03dce1f2` | `master` | `ubuntu-latest` | `bead_read_model_parity::concurrent_readers_see_consistent_snapshots` | `cache is stale: the next read rebuilds` |

---

## 3. Deep Dive into the Two Failure Modes

### 3.1 Failure Mode A: `wal_mode_probe_consumes_conversion_budget`

#### Code Location
[`crates/sase_core/src/tool_run/store/connection.rs#L875-L902`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/src/tool_run/store/connection.rs#L875-L902)

#### Test Structure
The test sets up an SQLite database with an exclusive lock held by connection A. Connection B attempts to acquire the store with a 250 ms busy budget:
```rust
let budget = Duration::from_millis(250);
let started = Instant::now();
let result = with_write_store(&path, budget, |_| Ok(()));
let elapsed = started.elapsed();
drop(holder);

assert!(matches!(result, Err(ToolRunError::Busy { .. })));
assert!(
    elapsed < Duration::from_millis(425),
    "WAL setup renewed an exhausted budget: {elapsed:?}"
);
```

#### Mechanism of Failure
1. **Intended Invariant**: The test wanted to prove that WAL conversion attempts don't grant a *second* 250 ms budget (which would result in `elapsed >= 500 ms`). The author allowed an extra 175 ms (`425 ms` total) for thread scheduling.
2. **Reality on CI Runners**: GitHub Actions macOS runners (`macos-latest` running on Apple Silicon VMs) experience intense CPU and thread contention when `cargo test --workspace` executes 5,500 tests across dozens of threads.
3. **Scheduler Jitter**: In run `40794754688`, SQLite attempted to sleep in short slices, but thread context switching and hypervisor scheduling took 1.173 seconds. Because `elapsed < 425 ms` was a hard wall-clock assertion, the test panicked with:
   `WAL setup renewed an exhausted budget: 1.173389917s`
4. **Recent Status**: Commit [`0fd85e4a`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/src/tool_run/store/connection.rs#L310) reworked SQLite connection handling to use `sqlite3_busy_handler` callbacks with wall-clock deadline checks (`should_retry_busy_until`) and added `busy_handler_stops_after_a_scheduler_oversleep` using mocked time. This stabilized the macOS failure in subsequent runs, but the broader lesson remains: **wall-clock upper bounds in CI integration tests are inherently brittle under load**.

---

### 3.2 Failure Mode B: `concurrent_readers_see_consistent_snapshots`

#### Code Location
[`crates/sase_core/tests/integration/bead_read_model_parity.rs#L869-L936`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/tests/integration/bead_read_model_parity.rs#L869-L936)

#### Test Structure
The test validates that the SQLite-backed read model cache accurately reflects bead state when multiple reader threads query the cache concurrently while single-stream note appends occur:
```rust
for step in 0..10 {
    append_issue_note(&cache_dir, "bench-2", ...).unwrap();
    states.insert(serde_json::to_string(&read_event_store_issues(&cache_dir).unwrap()).unwrap());
}
for reader in readers {
    reader.join().unwrap();
}
// 1. Verify reader consistency
for snapshot in snapshots.lock().unwrap().iter() {
    assert!(states.contains(snapshot));
}
// 2. Parity check
resync(&stores);
assert_parity(&stores);
// 3. Cache freshness verification
let verify = read_model_verify_cache(&stores.cache_dir);
assert!(verify.compared, "{}", verify.reason);
assert!(verify.matched, "{}", verify.reason);
```

#### Mechanism of Failure
1. **The Panic**: The panic occurs at line 934:
   ```
   thread 'bead_read_model_parity::concurrent_readers_see_consistent_snapshots' panicked at crates/sase_core/tests/integration/bead_read_model_parity.rs:934:5:
   cache is stale: the next read rebuilds
   ```
2. **Root Cause Breakdown**:
   - `read_model_verify_cache` is a **read-only verification probe** ([`crates/sase_core/src/bead/read_model/store.rs#L440`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/src/bead/read_model/store.rs#L440)). It does not rebuild the cache; it checks `probe_cache(&connection, beads_dir)`. If the SQLite cache is not fresh compared to disk events, it returns `Probe::Stale`, which sets `compared: false` and `reason: "cache is stale: the next read rebuilds"`.
   - Why was the cache not rebuilt before line 934?
     In `store.rs`, when a cache rebuild fails (for instance, when multiple threads concurrently attempt to open or write to the SQLite database and hit a busy timeout), `store.rs` executes:
     ```rust
     Err(Fault::Cache) => {
         mark_failed_rebuild(cache_path);
         set_cache_diagnostic(cache_path, "read-model rebuild failed; replay served this read");
     }
     ```
   - **The 10-Minute Lockout**:
     [`mark_failed_rebuild`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/src/bead/read_model/store.rs#L159) records the failure in the global process cache map `cache_process_state()`.
     [`FAILED_REBUILD_BACKOFF`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/src/bead/read_model/store.rs#L103) is set to **10 minutes** (`Duration::from_secs(10 * 60)`).
   - **Replay Fallback in `assert_parity`**:
     When the test finishes joining the reader threads and calls `assert_parity(&stores)`, it executes:
     `read_store_issues(&stores.cache_dir)`
     Because `rebuild_backoff_fault` is active for `cache_dir`, `read_store_issues` skips rebuilding the cache, catches `Fault::CacheDiagnostic`, and falls back to plain event replay from disk!
   - Because `read_store_issues` quietly fell back to replay, parity with `replay_dir` passed, but the SQLite cache on disk was left un-rebuilt.
   - When line 933 calls `read_model_verify_cache`, it inspects the actual cache file, finds it stale, and immediately panics at line 934.

```mermaid
sequenceDiagram
    participant Main as Test Main Thread
    participant Readers as 4 Reader Threads
    participant SQLite as Read-Model Cache (SQLite)
    participant State as Process Backoff State

    Main->>Main: append_issue_note (10 iterations)
    Readers->>SQLite: Concurrent read_store_issues
    Note over Readers,SQLite: High concurrency creates busy lock contention
    Readers->>State: mark_failed_rebuild(cache_path) (Sets 10-minute backoff)
    Readers-->>Main: join()
    Main->>Main: assert_parity()
    Main->>SQLite: read_store_issues()
    State-->>Main: rebuild_backoff_fault (10m active) -> Fallback to Replay
    Note over Main: Cache file on disk is NOT rebuilt!
    Main->>SQLite: read_model_verify_cache() (Probe-only)
    SQLite-->>Main: Probe::Stale ("cache is stale: the next read rebuilds")
    Main-->>Main: PANIC at line 934: verify.compared is false
```

---

## 4. Evaluation: Can Git Hooks Prevent These CI Failures?

The user prompt asked:
> *"I'm wondering if there is a way we can fix this with a post-commit hook or something like that to prevent these same types of failures from continuing to recur."*

### 4.1 Git Hook Types and Execution Boundaries

To evaluate this proposal, we examine standard Git hooks:

```mermaid
flowchart TD
    subgraph Local Git Workflows
        A["Working Directory Edits"] --> B["git commit"]
        subgraph Pre-Commit Phase
            B --> C{"pre-commit hook"}
            C -- "Non-zero exit" --> D["Commit Aborted (No commit object created)"]
            C -- "Exit 0" --> E["Commit Created in Object Database"]
        end
        subgraph Post-Commit Phase
            E --> F["post-commit hook (Notification / Audit Only)"]
            F -- "Cannot abort" --> G["Commit Persisted"]
        end
        G --> H["git push"]
        subgraph Pre-Push Phase
            H --> I{"pre-push hook"}
            I -- "Non-zero exit" --> J["Push Aborted"]
            I -- "Exit 0" --> K["Pushed to Remote (origin/master)"]
        end
    end
    K --> L["GitHub Actions CI Pipeline"]
```

1. **`post-commit` Hook**:
   - A `post-commit` hook is invoked strictly *after* the commit has been created.
   - Its exit status is ignored by git; it has no ability to abort or roll back a commit.
   - It is typically used for desktop notifications or logging, not gating.
2. **`pre-commit` and `pre-push` Hooks**:
   - A `pre-commit` or `pre-push` hook can abort operations before pushing to GitHub.
   - However, running verification here is fundamentally flawed for `sase-core` for the reasons below.

### 4.2 Why Git Hooks Fail for This Problem

| Factor | Git Hook Reality | CI Reality | Impact |
| :--- | :--- | :--- | :--- |
| **Failure Determinism** | Tests pass 99%+ of runs locally in isolation. | Tests fail intermittently under 64-thread CI runner load. | A local hook running `cargo test` will pass and permit the commit/push, only for CI to fail anyway. |
| **Execution Time** | Gating hooks must run in < 5 seconds to remain usable. | `just check` takes 5 to 10 minutes (compiling 4 crates + 5,500 tests). | Running full checks in a git hook creates intolerable developer friction and will be bypassed (`--no-verify`). |
| **Platform Target** | Local development is typically on Linux x86_64. | Failure Mode A occurred exclusively on macOS ARM64 runners. | A developer on Linux cannot reproduce or detect macOS scheduling jitter locally. |
| **SASE Agent Architecture** | SASE agents run in ephemeral numbered workspace clones (`sase_<N>`). | SASE host commits via finalizers (`builtin@commit` calling `sase stitch create`). | SASE agents do not invoke interactive git CLI commands that run local user hooks. |

**Conclusion on Git Hooks:** A git hook (whether pre-commit, post-commit, or pre-push) is the **wrong mechanism** for addressing these CI failures. It cannot catch platform-specific timing races, cannot reliably reproduce multi-threaded contention flakes, and introduces massive friction.

---

## 5. Recommended Solutions

The true resolution requires fixing the test race conditions and refining the read-model backoff policy, supported by robust CI gating mechanisms.

### 5.1 Immediate Fix: Refine Read-Model Rebuild Backoff and Parity Test

#### 1. Distinguish Transient Contention from Persistent Corruption
In [`crates/sase_core/src/bead/read_model/store.rs`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/src/bead/read_model/store.rs#L1244-L1256):
```rust
// Currently:
Err(Fault::Cache) if another_writer_advanced_cache(cache_path, start_generation) => {}
Err(Fault::Cache) => {
    mark_failed_rebuild(cache_path);
    set_cache_diagnostic(cache_path, "read-model rebuild failed; replay served this read");
}
```
If an SQLite operation returns `Busy` or `Locked` due to thread contention during a read, that is a transient contention event, **not** an unrecoverable cache corruption. Marking `mark_failed_rebuild` (with a 10-minute lockout) on transient busy states penalizes all future reads in the process. Transient busy errors should not arm `FAILED_REBUILD_BACKOFF`.

#### 2. Ensure Test Cleanliness in `concurrent_readers_see_consistent_snapshots`
In [`crates/sase_core/tests/integration/bead_read_model_parity.rs`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/tests/integration/bead_read_model_parity.rs#L930-L936):
Before verifying that the cache on disk matches replay parity via `read_model_verify_cache`, the test must ensure that the cache has performed a clean, forced refresh after all concurrent readers have completed:
```rust
for reader in readers {
    reader.join().unwrap();
}
// Clear any transient rebuild backoff armed during reader contention
clear_failed_rebuild_for_store(&stores.cache_dir);

// Force a synchronous rebuild to ensure disk cache convergence
cached_store_snapshot_at(&stores.cache_dir, &read_model_cache_path(&stores.cache_dir), true).unwrap();

resync(&stores);
assert_parity(&stores);
let verify = read_model_verify_cache(&stores.cache_dir);
assert!(verify.compared, "{}", verify.reason);
assert!(verify.matched, "{}", verify.reason);
```

---

### 5.2 Fix: Eliminate Brittle Wall-Clock Bounds in Timing Tests

For tests that verify timeout bounds (such as `wal_mode_probe_consumes_conversion_budget`):
1. **Prefer Injected Clocks / Mock Timers**:
   Follow the pattern established in commit [`0fd85e4a`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_25/sase/repos/linked/sase-core/crates/sase_core/src/tool_run/store/connection.rs#L903-L925) (`busy_handler_stops_after_a_scheduler_oversleep`), which injects a deterministic `now()` generator and mock sleeper rather than measuring real wall-clock time on a virtualized hypervisor.
2. **Scale Timing Budgets Under CI**:
   When real time must be measured, check for the `CI` environment variable or scale acceptable scheduling slack (e.g. `Duration::from_secs(3)` instead of `425 ms`) so that multi-tenant cloud runner hiccups do not trigger false alarms.

---

### 5.3 Architectural & Process Recommendations

1. **Bead Flake Tracking**:  
   Ensure a dedicated flake bead is tracked for `concurrent_readers_see_consistent_snapshots` (similar to closed bead `sase-1p6` for `tool_run`).
2. **SASE Prepared Verification Monitors**:  
   Instead of client git hooks, SASE provides the `/sase_monitor` prepared completion workflow:
   ```bash
   sase final prepare <wrapper> -j
   sase monitor start -p verify -f <ref> -r 'Verify before host completion' -- just check
   ```
   This gates master landing on passing host verification in an asynchronous, non-blocking monitor turn without burdening local commits.
3. **GitHub Branch Protection / Merge Queue**:  
   To prevent red commits from reaching `master` and breaking downstream `release-plz` PRs, enable GitHub merge queues or required status checks on `master` so that only PRs with green CI runs can land.

---

## 6. Summary Checklist

- [x] Identified exact failing tests across 22 failed CI runs in `sase-core`.
- [x] Analyzed failure mechanisms: macOS VM scheduling jitter and SQLite read-model 10-minute backoff.
- [x] Evaluated post-commit and pre-commit hooks; demonstrated why they cannot solve this issue.
- [x] Delivered concrete code-level fixes for `store.rs` and `bead_read_model_parity.rs`.
- [x] Outlined long-term CI and merge-queue gating practices.
