# Research Report: SASE Bead Acceleration Architecture

**Author**: Researcher `gem` (Independent Swarm Evaluation)  
**Date**: September 2026  
**Target Repository**: `sase` / `sase-core`  
**Classification**: Systems Architecture & Storage Engine Evaluation  

---

## Executive Summary

This research investigates the proposal to introduce an **optional service proc (daemon)** to dramatically accelerate reading and, ideally, writing SASE beads.

### Key Conclusions

1. **The Problem is Severe and Measurable**:
   In the active project store (comprising 5,968 beads and 1,712 individual event stream files), `sase bead list` takes **~2.7 seconds**, `sase bead show` takes **~2.7 seconds**, and even Rust core fast-pathed queries take **~0.8–0.9 seconds**. Writes take **1.5 to 5+ seconds** due to full 16MB projection generation, local Git commits, and synchronous network `git push` round-trips to GitHub under exclusive lock contention. The TUI repeatedly re-scans all 1,712 files sequentially and executes ~1,700 `stat` calls every polling cycle.
2. **Critique of the Proposal**:
   - **For Reads**: A daemon *can* accelerate reads by caching reduced state in RAM, but it is an **over-engineered and brittle solution**. SASE already embeds Rust via `sase_core_rs`. An in-process SQLite database (`beads.db`) in WAL mode delivers **1–3ms read queries** directly within the CLI process—with zero daemon management, zero IPC serialization, zero port/socket contention, and zero fallback discrepancies.
   - **For Writes**: Implementing asynchronous write-behind buffering in a daemon is **fundamentally hazardous** within SASE. It violates the core architectural invariant that *agents are single-turn* and *completion is host-owned*. If an agent records a task or closes a bead and immediately declares completion, a subsequent background Git push failure (network drop, rebase conflict, GitHub rate limit) creates an unrecoverable split-brain condition. Furthermore, SASE runs parallel agents in ephemeral workspace clones (`sase_<N>`), each with its own nested beads sidecar checkout; a daemon cannot safely arbitrate Git commits across isolated, ephemeral working trees without risking silent workspace eviction losses.
3. **Recommended Solution (The Hybrid "Fast-Local, Safe-Remote" Model)**:
   - **Core Engine (In-Process)**: Activate the existing, currently dormant `beads.db` in `sase_core` as an incremental SQLite projection in WAL mode. Migrate `list`, `read`, and `show` to the Rust CLI fast-path. This reduces read latency from **2,700ms to <15ms** unconditionally, without needing any daemon running.
   - **Service Proc Role (Proactive Supervisor, not Write-Behind Buffer)**: If an optional service proc (`bead-syncd`) is implemented, its purpose must NOT be to buffer uncommitted writes. Instead, it should act as a **Proactive Sync and Maintenance Supervisor**:
     1. Continuously pre-fetching and rebasing the remote Git sidecar in the background so local writes can fast-forward push in <300ms without rebase contention.
     2. Monitoring event streams via OS filesystem notifications (`notify`) to keep `beads.db` warm.
     3. Serving live change events directly to the SASE TUI via SSE/IPC, entirely eliminating the 1,700-stat polling loop.

---

## 1. Deep-Dive: Current Architecture & Empirical Profiling

### 1.1 Store Anatomy & Topology

A SASE bead store operates on an event-sourced architecture under `sdd/beads/` or `sase/repos/beads/`:
- **Canonical Event Store (`events/`)**:
  - `manifest.json`: Stores store-level metadata (e.g., `stream_count`).
  - `streams/<bead-id>.jsonl`: Append-only event stream for each root bead and its hierarchy. In the tested workspace, there are **1,712 stream JSONL files**.
- **Projections**:
  - `issues.jsonl`: A monolithic, generated flat projection of all reduced beads. In the current repository, this file is **16 MB** containing **5,968 issues** (819 plans, 4,305 phases, 844 tasks, 45 flags).
  - `beads.db`: A **0-byte empty file** created at initialization. Although `BEAD_SQLITE_SCHEMA` exists in `sase_core::bead::schema`, SQLite is currently not used for queries.
  - `bead_touch_index`: An actor-keyed secondary index file reduced from event streams.

### 1.2 Ephemeral Workspaces & Multi-Repo Sidecar Structure

SASE executes agents in numbered ephemeral workspaces (`sase_<N>`). Bead storage for projects configured with sidecar repositories (`sase-org/sase--beads.git`) is cloned into `<workspace>/sase/repos/beads`.
- Each workspace maintains its **own Git clone** of the beads sidecar, cloned via `--reference-if-able` from the primary workspace.
- Multi-agent concurrency is isolated at the filesystem level, but all checkouts converge onto the single canonical GitHub remote.
- The AXE scheduler actively guards against workspace reset/eviction via `runner_workspace_beads.py` because any unpushed commits inside an ephemeral workspace checkout are permanently destroyed when the workspace is recycled.

### 1.3 Empirical Latency Breakdown

Profiling conducted on the production repository checkout (`sase_36`, local SSD, Linux):

```
┌──────────────────────────────────────┬───────────┬────────────────────────────────────────────┐
│ Operation                            │ Latency   │ Dominant Bottleneck                        │
├──────────────────────────────────────┼───────────┼────────────────────────────────────────────┤
│ sase bead stats (Rust fast-path)     │ 0.83 s    │ 1,712 JSONL stream reads & full reduction  │
│ sase bead search (Rust fast-path)    │ 0.93 s    │ 1,712 file opens, JSON parse, text scan    │
│ sase bead list (Python slow-path)    │ 2.69 s    │ Python startup, slow path, object hydration│
│ sase bead show (Python slow-path)    │ 2.67 s    │ Python CLI dispatch, full store reduction  │
│ TUI load_project_beads (per cycle)   │ ~2.5 s    │ Sequential list + ready + blocked scans    │
│ TUI store_mtime_key (polling check)  │ ~25 ms    │ 1,712 stat syscalls via rglob("*")         │
│ sase bead update/note (write path)   │ 1.8–4.5 s │ 16MB jsonl rewrite + git commit + git push │
│ First sase bead in fresh workspace   │ 10–30+ s  │ git pack-objects clone of sidecar repo     │
└──────────────────────────────────────┴───────────┴────────────────────────────────────────────┘
```

#### Why Reads Are Slow:
1. **Full Reductive Scan on Every Invocation**:
   In `crates/sase_core/src/bead/read.rs`, `read_store_issues()` calls `read_event_store()`, which executes `read_event_streams_without_manifest()`. This iterates through all 1,712 stream files in `events/streams/*.jsonl`, parses each line with `serde_json`, and re-reduces the entire issue tree into memory. Even in optimized Rust, traversing 1,712 inodes and deserializing tens of thousands of JSON lines takes ~800ms.
2. **Sequential Redundant Reads**:
   In the TUI (`src/sase/ace/tui/widgets/artifacts/beads_data_sources.py`):
   ```python
   def load_project_beads(beads_dir: Path):
       issues = bead_read_facade.list_issues(beads_dir)
       ready_ids = frozenset(issue.id for issue in bead_read_facade.ready(beads_dir))
       blocked_ids = frozenset(issue.id for issue in bead_read_facade.blocked(beads_dir))
   ```
   Because `list_issues`, `ready`, and `blocked` each call `read_store_issues()`, the TUI parses all 1,712 files **three times consecutively** on a single load.
3. **Python Exclusion from Fast-Path**:
   In `src/sase/main/bead_fast_path.py`:
   ```python
   if argv[0] in {"list", "read", "show"} or _search_uses_full_format(argv):
       return None
   ```
   The most common interactive commands (`list`, `read`, `show`) bypass the Rust CLI fast-path entirely, incurring Python interpreter startup, `argparse` construction, cross-boundary FFI dictionary conversions, and Python string formatting, pushing latency to nearly 3 seconds.

#### Why Writes Are Slow:
1. **Monolithic Projection Generation**:
   Every mutating verb (`update`, `note`, `close`, `create`, `+1`) triggers `write_issues_jsonl()`, which serializes and writes the entire **16 MB** `issues.jsonl` file to disk atomically.
2. **Synchronous Git Push Contract**:
   In `src/sase/bead/cli_common.py`, mutations invoke `auto_commit_bead_store()` followed by `_push_committed_bead_store()`. This invokes `git commit` and `run_managed_sync_worker()` (`git fetch`, `git rebase`, and `git push`). Communicating with GitHub over SSH/HTTPS takes 1 to 4 seconds of network I/O.
3. **Contention & Locking**:
   Mutations hold `sase-bead-sync.lock` and `store_git_write_lock`. Under multi-agent swarms (such as the 3-researcher swarm running here), concurrent writes serialize and queue for up to 30 seconds (`MUTATION_PUBLICATION_WORKER_LOCK_WAIT_SECONDS`).

---

## 2. Critique of the "Optional Service Proc Daemon"

The user's concept envisions an optional service proc daemon that accelerates reads and (ideally) writes when active, with transparent fallback when disabled.

### 2.1 Reading via Daemon: Viable, but an Architectural Mismatch

A daemon could maintain an in-memory cache of reduced beads and serve queries over a Unix Domain Socket (UDS) in <5ms. However:
- **Redundant IPC Overhead**: SASE already has a high-performance native core in Rust (`sase-core`). An embedded storage engine (SQLite with Write-Ahead Logging) runs in the same process address space and executes indexed lookups in **1–2ms**, completely eliminating IPC serialization, socket connection handshakes, and process context switches.
- **The "Optional" Dilemma**: If the daemon is optional, the direct (non-daemon) path must still exist. If the direct path remains slow (~2.7s), users without the daemon have an unacceptable experience. Conversely, if the direct path is fixed to be fast (~10ms via embedded SQLite), the daemon's read cache adds zero incremental value while adding process management overhead.
- **Cache Invalidation Skew**: When agents in ephemeral workspaces mutate beads directly on disk (or Git pulls update streams), a read daemon must either continuously poll disk or maintain complex inotify/kqueue watchers across multiple workspaces.

### 2.2 Writing via Daemon: Highly Hazardous

Attempting to accelerate writes by having a daemon act as an asynchronous write-behind buffer (buffering mutations in memory/disk and pushing to Git in the background) introduces severe risks:

#### 1. Invariant Breach: SASE Single-Turn Agent Completion Contract
SASE agents run a single provider turn and declare completion. Core memory dictates:
- *Decision 3: Agents Are Single-Turn*
- *Decision 7: Completion Is Host-Owned*
- *sase_beads.md: "A CLI bead mutation carries a completion contract..."*

If an agent updates a task, closes a phase bead, and declares its turn finished, it relies on that mutation being durably published to the canonical remote. If a daemon acknowledges the write in 5ms but fails to push 10 seconds later (e.g., due to an SSH authentication timeout, GitHub 503, or upstream rebase conflict), **the agent has already exited**. The host cannot ask the agent to recover, and sibling agents on other machines or workspaces will operate on stale state.

#### 2. Multi-Workspace Git Topology & Workspace Eviction
In SASE, each parallel agent runs in a numbered checkout (`sase_36`, `sase_41`). The beads sidecar is cloned into each workspace.
- If the daemon performs background commits, **which Git repository does it commit into?**
  - If it commits into the agent's private workspace clone (`sase_36/sase/repos/beads`), the daemon must touch workspace-internal files. When the agent finishes, the AXE scheduler may evict or clean up `sase_36`. If the daemon has queued unpushed commits in that directory, AXE's eviction safety checks (`runner_workspace_beads.py`) will either stall waiting for the push or quarantine the directory.
  - If the daemon commits into a central "daemon-owned" clone, the agent's local workspace view becomes desynchronized from its own edits until a Git pull is executed.
- If two agents in different workspaces mutate beads simultaneously, a central daemon buffering writes to a single Git branch will generate frequent internal rebase conflicts, requiring complex three-way merge resolution that should never belong in a background daemon.

#### 3. Dual-Stack Maintenance Cost
Every edge case in `sase bead` (e.g., descendant-close validation, +1 deduplication, conflict resolution markers, task type schemas) would need to be implemented across two distinct write lanes: the direct Git lane and the daemon queue lane.

---

## 3. Adjustments to Requirements

To achieve the speedup the user desires without destabilizing SASE's distributed state, the requirements should be adjusted as follows:

| Original Requirement | Adjusted Requirement | Rationale |
| :--- | :--- | :--- |
| **Daemon as Query Server** | **In-Process SQLite Read Model** | SQLite WAL in Rust core gives 1–3ms reads with zero IPC, zero socket lifecycle bugs, and works identically across all workspaces. |
| **Daemon Write-Behind Buffer** | **Local-Fast, Remote-Synchronous Write Pipeline** | Decouple local mutation speed from remote push without sacrificing the completion contract. |
| **Daemon Optional for Performance** | **Performance Invariant Regardless of Daemon** | Direct CLI reads and writes must be inherently fast; the daemon's absence must not degrade performance to multi-second delays. |
| **New Standalone Daemon** | **Service Proc as "Proactive Sync & Watcher" (`bead-syncd`)** | Repurpose the service proc to handle proactive background Git fetching, SQLite index warmup, and TUI event streaming. |

---

## 4. Alternative Architectural Approaches

### Approach 1: Standalone RPC/UDS Daemon (User's Proposal)
- **Concept**: A background service proc (`sase bead daemon`) listening on a Unix domain socket (`~/.sase/run/bead.sock`). Keeps all beads in RAM. CLI connects over socket; daemon handles all reads and writes.
- **Pros**: Sub-millisecond in-memory queries; centralized write serialization.
- **Cons**: Severe failure modes on daemon crash; split-brain risks on background push failure; complex workspace path routing; high implementation cost.

### Approach 2: Embedded SQLite WAL Projection (Zero-Daemon)
- **Concept**: Activate `beads.db` in `crates/sase_core/src/bead/`. When reading, query SQLite directly. When writing, append to the event stream and immediately update SQLite.
- **Pros**: 100x read speedup (2ms); unlimited concurrent readers under WAL mode; zero daemon management; 100% resilient.
- **Cons**: Does not reduce Git push network latency on writes; does not provide push events to the TUI.

### Approach 3: The Hybrid Architecture (Recommended)
- **Concept**:
  1. **In-Process Engine**: Rust core maintains an incremental SQLite read-model (`beads.db`) in WAL mode for all CLI queries.
  2. **Fast-Path Expansion**: Move `list`, `read`, and `show` to Rust `bead_cli_execute`.
  3. **Optimized Write Pipeline**: Append event + update SQLite (<3ms) + commit local Git (<15ms). Push remains synchronous for agent contracts, but `--async` is available for interactive commands.
  4. **Proactive Service Proc (`bead-syncd`)**: A background service proc under `sase service` that:
     - Continuously fetches and rebases remote Git changes in the background (proactive warming), eliminating network rebase delays when the CLI pushes.
     - Streams real-time change events to the SASE TUI, eliminating filesystem polling.

### Tradeoff Comparison Matrix

```
┌───────────────────────────────┬──────────────────┬──────────────────┬────────────────────────┐
│ Metric / Dimension            │ Approach 1       │ Approach 2       │ Approach 3 (Hybrid)    │
│                               │ (Daemon RPC)     │ (SQLite Only)    │ (SQLite + Sync Daemon) │
├───────────────────────────────┼──────────────────┼──────────────────┼────────────────────────┤
│ Read Latency (CLI)            │ ~1 ms (IPC)      │ ~2–5 ms (In-proc)│ ~2–5 ms (In-proc)      │
│ Write Latency (Local)         │ ~2 ms (Buffered) │ ~15 ms           │ ~15 ms                 │
│ Remote Push Safety            │ Poor (Unbounded) │ High (Sync)      │ High (Sync + Pre-warmed│
│ Daemon Crash Impact           │ Catastrophic     │ None (No daemon) │ Zero (Graceful degrade)│
│ Multi-Workspace Complexity    │ Extreme          │ Low              │ Low                    │
│ TUI Polling Elimination       │ Yes (via Push)   │ No (Still polls) │ Yes (via Push/SSE)     │
│ Implementation Effort         │ High (3–4 weeks) │ Medium (1 week)  │ Medium-High (2 weeks)  │
└───────────────────────────────┴──────────────────┴──────────────────┴────────────────────────┘
```

---

## 5. The Recommended Solution: Hybrid "Fast-Local, Safe-Remote"

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             SASE CLI / TUI / AGENTS                         │
│  (sase bead list | read | show | update | close in workspace sase_<N>)     │
└───────────────┬─────────────────────────────────────────────┬───────────────┘
                │ Direct In-Process FFI (sase_core_rs)        │
                ▼                                             ▼
┌───────────────────────────────────────────┐   ┌─────────────────────────────┐
│       Rust Core Read Engine               │   │   Rust Core Write Engine    │
│  - Check manifest watermark (~0.2ms)      │   │  1. Append stream JSONL     │
│  - Query SQLite beads.db (WAL) (~2ms)     │   │  2. Upsert SQLite beads.db  │
│  - Fallback to stream replay if stale     │   │  3. Git commit (<15ms)      │
└─────────────────────▲─────────────────────┘   └─────────────┬───────────────┘
                      │                                       │
                      │ Incremental Sync                      │ Fast-forward push
                      │                                       ▼
┌─────────────────────┴───────────────────────────────────────────────────────┐
│                           LOCAL STORAGE LAYER                               │
│   events/streams/*.jsonl  │  beads.db (WAL)  │  issues.jsonl (deferred)     │
└─────────────────────▲───────────────────────────────────────▲───────────────┘
                      │ Watch & Pre-fetch                     │
                      │                                       │
┌─────────────────────┴───────────────────────────────────────┴───────────────┐
│               OPTIONAL SERVICE PROC: sase-bead-syncd                        │
│  - Supervised by `sase service run`                                         │
│  - Proactive Remote Fetch: `git fetch origin` every 30s                     │
│  - Watcher: inotify/FSEvents on `events/streams/` -> warmup `beads.db`      │
│  - Event Streamer: Emits SSE/socket events to TUI (no more rglob polling)   │
└─────────────────────────────────────▲───────────────────────────────────────┘
                                      │ Background Sync
                                      ▼
                        CANONICAL REMOTE (GitHub Git)
```

### Component Details

#### 1. In-Process SQLite WAL Read Projection (`beads.db`)
- **Location**: Resides alongside `events/` in `<beads_dir>/beads.db`.
- **Watermarking**: The database maintains a single-row metadata table:
  ```sql
  CREATE TABLE IF NOT EXISTS _projection_meta (
      stream_id TEXT PRIMARY KEY,
      last_mtime_ns INTEGER,
      last_size INTEGER
  );
  ```
- **Execution Flow on Read**:
  1. On invocation, `sase_core` reads `events/manifest.json` (1 stat, ~0.1ms).
  2. If the manifest mtime matches the SQLite watermark, execute the query directly against `beads.db`.
  3. Lookups by ID (`show`, `read`) execute in **<1ms** via `PRIMARY KEY (id)`.
  4. Filtered listings (`list --status ready`, `blocked`) execute in **2–4ms** via composite indexes on `status` and `parent_id`.
  5. If the manifest shows new or modified streams, perform an **incremental catch-up**: read *only* the modified `.jsonl` files (identified by mtime/size, matching the pattern in `bead_touch_index.rs`), reduce them, upsert into SQLite, and commit the transaction.

#### 2. Native Rust CLI Fast-Path for All Read Queries
- Edit `src/sase/main/bead_fast_path.py`:
  - Remove `list`, `read`, and `show` from the bypass check.
  - Route them directly to `execute_bead_cli(argv)`.
- In `crates/sase_core/src/bead/cli/`:
  - Implement native terminal rendering for `list` (compact, json, full) and `show`/`read`.
  - Audited reads (`sase bead read <id> -r "<why>"`) record the read event in `artifact_reads.jsonl` via Rust or a thin host hook, preserving audit guarantees while running in **<20ms**.

#### 3. Write-Path Streamlining
- **Decouple `issues.jsonl` Generation**:
  Stop regenerating the 16MB `issues.jsonl` file on every single mutation. Instead:
  - Generate `issues.jsonl` only during pre-push, explicit export, or background maintenance.
  - Or, convert `issues.jsonl` to an append-only delta stream that is compacted periodically.
- **Preserve the Synchronous Publication Contract**:
  - Keep `ensure_bead_mutation_published()` synchronous for agent-driven workflows and finalizers.
  - For human interactive commands, provide a `--no-push` or `--async` option where immediate UI return is preferred.

#### 4. The Role of the Service Proc: `bead-syncd`
The service proc is managed under `sase service` (`sase service proc add bead-syncd`):
- **Background Remote Fetch**: Runs `git fetch origin` every 30–60 seconds. When an agent runs `sase bead update`, the local Git branch is already up-to-date with remote HEAD; the subsequent push is a clean fast-forward push that completes in ~300ms without rebase retries.
- **Filesystem Watcher**: Uses Rust's `notify` crate to detect stream modifications and immediately updates `beads.db`, ensuring queries always hit a warm cache.
- **TUI Real-Time Push**: Provides an IPC socket or SSE endpoint that emits `beads_changed` events. The TUI subscribes to this stream and replaces its 1,700-file `rglob("*")` polling loop entirely.
- **Zero-Dependency Fallback**: If `bead-syncd` is stopped or disabled, the CLI continues to work at full speed using the in-process SQLite engine.

---

## 6. Migration & Implementation Roadmap

### Phase 1: In-Process Read Engine (Immediate 100x Speedup)
- **Target**: `crates/sase_core/src/bead/`
- **Work**:
  1. Leverage `BEAD_SQLITE_SCHEMA` in `crates/sase_core/src/bead/schema.rs` to initialize and open `beads.db` with `PRAGMA journal_mode = WAL`.
  2. Implement `sync_projection_from_events(&Connection, &Path)` using incremental stream file signatures (identical to `refresh_bead_touch_index`).
  3. Redirect `read_store_issues()`, `show_issue()`, `ready_issues()`, and `list_issues()` to query SQLite.
  4. Enable `list`, `read`, and `show` in `src/sase/main/bead_fast_path.py`.
- **Expected Result**: CLI reads drop from **2,700ms to <15ms**. TUI load drops from **2,500ms to <20ms**.

### Phase 2: Mutation Pipeline Streamlining
- **Target**: `crates/sase_core/src/bead/mutation/` and `src/sase/bead/cli_common.py`
- **Work**:
  1. Invert `issues.jsonl` generation: update `beads.db` synchronously during mutation; defer 16MB `issues.jsonl` export to Git commit hooks or background sync.
  2. Streamline `_refresh_touch_index_after_mutation` so it updates incrementally without directory scanning.
- **Expected Result**: Local mutation latency drops from **~1,200ms to <25ms** (excluding network push).

### Phase 3: The Optional `bead-syncd` Service Proc
- **Target**: `src/sase/service/` and a new crate/module `crates/sase_core/src/bead_syncd/`
- **Work**:
  1. Implement `bead-syncd` as a standard SASE service proc registered in `src/sase/default_config.yml`.
  2. Implement background Git fetch loop with exponential backoff and network detection.
  3. Implement filesystem watcher using `notify` on `events/streams/` to maintain the SQLite projection.
  4. Connect the TUI's Artifacts Beads panel to the service proc's notification socket, removing `store_mtime_key` disk polling.
- **Expected Result**: Network push latency drops to ~300ms (clean fast-forward). Zero TUI disk polling I/O.

---

## 7. Final Assessment & Recommendation

| Question | Assessment |
| :--- | :--- |
| **Is implementing a daemon a good idea?** | **Partially.** A daemon for *reading* is unnecessary (embedded SQLite is faster and simpler). A daemon for *write-behind buffering* is dangerous (breaks SASE completion contracts and workspace isolation). A daemon for *proactive background sync and cache warming* is an excellent idea. |
| **Would you take a different approach?** | **Yes.** Take the **Hybrid Approach**: prioritize activating the in-process SQLite read-model (`beads.db`) in Rust core first. This immediately solves 90% of the user's performance pain with zero operational overhead. |
| **How should requirements be adjusted?** | Keep writes strictly durable and synchronized; do not buffer unpushed Git writes in memory. Repurpose the daemon as an auxiliary sync and event broadcaster rather than a primary query router. |
