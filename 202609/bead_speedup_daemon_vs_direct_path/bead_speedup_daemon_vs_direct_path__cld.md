# Should Bead Reads/Writes Get An Optional Daemon Service Proc? — Evaluation And Recommendation (cld)

Date: 2026-09-24 · Researcher: `cld` (one of three independent swarm reports)

## Question

Would a new optional **service proc** — a daemon under the per-machine `sase service` host — make reading and
(ideally) writing sase beads much faster when it is running? How should it be built? Is it a good idea at all, and
would a different approach be better?

## Short Answer

**The instinct is right; the diagnosis is mostly wrong.** Bead commands really are slow. A read takes 0.85–3.4 s and
a mutation takes **22–31 s**. But I measured where that time goes, and very little of it is the kind of cost a
long-lived process removes:

| Where the time goes (measured) | Share | Would a read/write RPC daemon remove it? |
|---|---|---|
| **Writes:** the publication stream-integrity guard runs ~6,850 `git show` subprocesses per mutation | ~20 s of ~24 s | **No.** The fix is ~2 subprocesses instead of ~6,850. Filed as `sase-17q`. |
| **Reads (list/show/read) and slow-path writes:** Python imports the pager, Textual and ACE widgets (2,911 modules) | 1.3–2.0 s | Only if the CLI becomes a thin client, and making it thin is the same work as fixing the imports |
| Every call replays the full 28 MB event history in Rust (no cache; the store is parsed twice) | 0.4–0.55 s per read, repeated 1–3× per command | **Yes.** An on-disk fingerprinted snapshot cache also removes it, and needs no process |
| Each mutation rewrites the 16.7 MB `issues.jsonl` projection, and git then re-hashes it | ~0.9 s | No |
| Publication bookkeeping: an async worker is spawned, then a forced sync push waits on its lock; a 43-git-call health preflight | ~1–2 s | No |
| Network fetch plus push | ~1.1 s p50 | Only by weakening the "published before success" contract. The direct path could do the same |

After fixing the direct path (Phase 0–1 below), a read daemon would save roughly **10–40 ms** more per read and
**≈0 ms** per write. That buys a second code path, a socket protocol, per-workspace-clone invalidation and a fallback
matrix. Two teams have already paid that price and backed out:

- **SASE itself.** The `sase-3e` "Rust Daemon and Indexed Projections" legend (11 epics, including daemon-backed bead
  reads) was reverted on 2026-05-14 (`5a65fa4fc`).
- **Upstream Beads.** It deleted its daemon/RPC layer (~19,663 lines) in v0.50.0 (2026-02-14) after a long tail of
  "works differently in daemon mode" bugs. All commands now go straight to the embedded database.

**Recommendation:**

1. **Make the direct path fast** with cheap, targeted fixes: the integrity guard, lazy imports, redundant reads, and
   the double publish.
2. **Add a fingerprinted on-disk snapshot cache inside `sase_core`.** Readers check it against a ~5 ms `stat` of the
   store, so it is correct for every process: CLI, TUI, scheduler jobs, gateway and editor. No IPC and no invalidation
   protocol are needed.
3. **Keep a daemon only as an optional cache-warmer service proc**, and build it only if measurements after step 2
   still justify it. It writes cache files that clients validate. Clients never talk to it, so "optional" is literally
   true.
4. **Treat "writes through a daemon" as a separate decision** about SASE's durability contract (a machine-level
   publication outbox), not as a performance feature.

Expected results (estimates, derivations in §7):

| Operation | Today | Expected |
|---|---|---|
| `sase bead ready` | 0.85 s | ~0.1 s |
| `sase bead list` | 2.9 s | ~0.1–0.15 s |
| Mutation, median | ~24–31 s | ~1.5–2 s, dominated by the network push |

---

## 1. What I Measured

All measurements were taken on athena on 2026-09-24:

- installed `sase` (editable checkout at master) with the `sase_core_rs` wheel;
- warm page cache;
- the real `sase` project bead sidecar (`sase repo path beads`).

Methodology and commands are in the Appendix.

### 1.1 Store shape and growth

| Metric | Value |
|---|---|
| Beads | 5,968 (408 non-closed = 6.8%; 5,560 closed) |
| Event streams (one per root bead; children write into the parent's stream) | 1,712 |
| Events | 38,161 (28.0 MB) |
| Event bytes in streams whose root bead is **closed** | 23.3 MB of 28.0 MB (**83%**) |
| Event mix by bytes | `note_appended` 32%, `issue_created` 26%, `issue_updated` 12%, rest ≤6% each |
| `issues.jsonl` (generated projection, tracked in git) | 16.7 MB; the non-closed subset is only 2.0 MB |
| Beads sidecar `.git` | 213 MB; 15,352 commits since the sidecar split on 2026-07-28 |
| Growth, last month | 17.4 MB / 1,078 streams (2026-08-24) → 28.0 MB / 1,712 streams (2026-09-24): **+61% bytes, +59% streams** |
| Bead commits per day, last 9 days | 57–505 |
| Sync-worker runs per day, all SDD sidecars | ~1,700–1,900 (`~/.sase/bead_push_logs`) |

Every uncached cost below is O(history) or O(stream count). None of them is O(active beads). So they grow as fast as
the store does.

### 1.2 Read latency (real CLI, three runs each)

| Command | Wall time | Path |
|---|---|---|
| `sase bead list` | 2.84–3.06 s | Python slow path |
| `sase bead show <id>` | 2.5–2.7 s (3.4 s in the sandbox) | Python slow path |
| `sase bead ready`, `search`, `stats`, `blocked` | 0.84–0.87 s | Rust fast path |

`sase bead read` (the audited agent command) is on the same slow path as `show`.

**Profile of `sase bead list` (3.0 s):**
- Importing `sase.bead.cli` takes **2.03 s**:
  - `cli_query` → `cli_show_batch` → `sase.pager` accounts for 1.41 s;
  - `sase.pager` imports Textual and `sase.ace.tui.widgets.prompt_panel`;
  - `cli_admin` → `bead_pages` → `agents_sync` accounts for another 0.53 s.
- The command imports 2,911 modules, versus 516 for `ready`.
- Rust `bead_list` takes **0.525 s**.
- Building the argparse parser takes 0.17 s.

**Profile of `sase bead ready` (0.83 s):**
- Rust `bead_cli_execute` takes **0.48 s**.
- Imports take 0.29 s. The `sase.bead` package `__init__` pulls in `project`, `config` and `ace.patch`.
- Context resolution takes 0.11 s.
- `schedule_bead_refresh` takes 0.085 s, all of it config loading.

### 1.3 The Rust read path in isolation (Python bindings, 5 runs, minimum and median)

| Operation | Time |
|---|---|
| Interpreter start / `import sase_core_rs` | 17 ms / +3 ms |
| Raw read of all 1,712 stream files (28 MB), no parsing | 16 ms |
| `scandir` + `stat` of all streams (a store fingerprint) | **4.6 ms** |
| CPython `json.loads` of every event | 240 ms |
| Rust `bead_ready` | 391 / 407 ms |
| Rust `bead_list` (all 5,968 issues converted to Python objects) | 529 / 547 ms |
| Rust `bead_read_event_store` | 541 / 564 ms |

The Rust replay is slower than CPython simply parsing the same JSON. The code explains why:

- `read_event_store` first runs `prune_removed_flag_event_streams`. That step reads and parses every stream into
  untyped `serde_json::Value` (`sase-core/crates/sase_core/src/bead/jsonl.rs:395`, `:152-254`).
- It then reads and parses everything again with typed parsing (`jsonl.rs:418-437`, `575-650`).
- The reducer deep-copies every stream (`events/reduction.rs:262-278`).
- Events are validated three times.
- Reads run on one thread.
- There is no memoization of any kind anywhere in `bead/` or the bindings.

### 1.4 Write latency

**Sandbox setup.** A temp split-layout project containing a byte copy of the real store, a **local** bare `origin`,
and an upstream-tracking branch. This includes every step except real network latency.

| Command (sandbox) | Wall time |
|---|---|
| `sase bead note <id> "…"` | 24.2 s, 24.0 s |
| `sase bead update <id> --status …` (Rust fast path) | 22.3 s, 22.4 s |
| `sase bead dep list <id>` (read) | 4.2 s |

**Live production corroboration.** Filing the bug below took 28.3 s for `sase bead create` and 31.4 s for
`sase bead update --status ready`, against the real GitHub remote.

**cProfile of `note` (26.4 s under the profiler):**

| Step | Time |
|---|---|
| `ensure_bead_mutation_published` → `push_bead_work_launch` → `_run_locked_sync` | **21.1 s** |
|  ↳ `refuse_unpublished_event_stream_shrink`: 2 calls → 4 `streams_at_rev` → **6,854 `git show` subprocesses** | **19.95 s** |
| Imports (`sase.bead.cli` → pager / Textual / ACE) | 2.2 s |
| `bead_store_write_lock`, including a repository-health preflight of 43 git calls (0.73 s) | 1.19 s |
| Routing: `_descriptor_for_location` runs a **full `list_issues`** just to validate the target ID (`src/sase/bead/operation_context.py:280`) | 0.86 s |
| `append_note` (of which the Rust mutation is 0.60 s) | 1.02 s |

**Local write floor** (Rust binding plus git, measured separately in a clone):

| Step | Time |
|---|---|
| Rust `bead_append_note` (full replay, stream write, then a rewrite and fsync of the whole 16.7 MB `issues.jsonl`) | 604–734 ms |
| `git add` (re-hashing `issues.jsonl`) | 240–418 ms |
| `git commit` | 58–60 ms |

**Production sync logs.** 1,984 beads-sidecar sync-worker runs in September 2026, from `~/.sase/bead_push_logs`:

- p50 **2.1 s**. These are runs with nothing to publish, which leave the guard early.
- p90 **23.8 s**, p99 36.7 s, max 55.3 s.
- 425 runs (**21%**) took more than 10 s.
- The slow runs show ~10.4–10.9 s before `manifest_repair`, which is the pre-integration guard. They show another
  ~13–14 s between `integration` and `completed`, which is the post-integration guard plus the push.

Network, from `~/.sase/logs/tui_git_ops.jsonl`:

| Operation | p50 | p90 | max | n |
|---|---|---|---|---|
| `bead.sync.fetch` | 481 ms | 568 ms | — | ~575 |
| `bead.sync.push` | 565 ms | 3,245 ms | 5.7 s | ~575 |

---

## 2. Root Causes

- **R1 — Integrity guard walks every stream through per-file `git show` (writes, ~20 s).**
  - Every publication calls `refuse_unpublished_event_stream_shrink`:
    - the forced synchronous push that follows every CLI mutation;
    - any sync worker that has local stream changes.
  - It is called twice, pre- and post-integration (`src/sase/bead/sync_worker.py:134`, `:205`). Each call builds full
    stream maps for HEAD and for the ancestor (`src/sase/bead/_stream_integrity.py:182-183`). It does this with one
    subprocess per stream file (`src/sase/bead/_stream_integrity_git.py:114-142`).
  - Only two things are actually needed:
    - the set of new stream **names**, which the `ls-tree` it already runs provides;
    - the contents of *new* streams, and only in the rare case where a changed stream is missing ancestor events
      (`_stream_integrity_analysis.py:201-212`).
  - The cost grows with stream count. Filed as **`sase-17q`** (bug, medium).
- **R2 — Import bloat on the Python slow path (1.3–2.0 s).**
  - `list`, `read`, `show`, `close`, `create`, `note`, `update` with notes, `+1` and `snooze` all import the full
    pager/TUI stack at module import time.
  - The fast-path `bead_fast_path` import alone costs ~0.15 s, because of what the `sase.bead` package `__init__`
    pulls in.
- **R3 — Full-history replay on every call, with no cache (0.4–0.55 s, linear in history).**
  - 83% of the bytes replayed belong to closed beads that almost never change.
- **R4 — Redundant full reads within one command.**
  - Routing reads the full store to validate IDs (0.86 s).
  - CLI mutations resolve IDs and old status with 1–2 extra full reads before taking the lock (`cli/mutate_commands.rs`,
    `create_command.rs`).
  - `search --format full` does N+1 full reductions.
  - The TUI's Beads and Plans panes force a reload on every 10 s tick, making three full reads per project. See
    `beads_pane.py:150`, `_request_load(force=True)`, which bypasses the mtime key. This comes from reading the code; I
    did not measure it.
- **R5 — The compatibility projection is regenerated on every mutation.**
  - `MutableStore::save` always rewrites and fsyncs the whole `issues.jsonl` (`mutation/store.rs:310-333`).
  - Git must then re-hash it, and the sidecar's history grows with it.
- **R6 — Publication bookkeeping.**
  - The default `sdd.push_after_commit: async` spawns a detached sync worker. Right after that,
    `ensure_bead_mutation_published` sees "unpublished" (the tracking ref has not moved yet). It then runs the same sync
    in-process, waiting up to 30 s (`MUTATION_PUBLICATION_WORKER_LOCK_WAIT_SECONDS`, `src/sase/bead/sync.py:55`) for the
    worker it just spawned.
  - So the CLI waits for the push anyway, and pays for an extra Python process.
  - Separately, the health preflight runs ~43 git calls per mutation.
- **R7 — Network fetch plus push (~1.1 s p50, p90 >3 s).**
  - This is irreducible under the documented invariant that a bead mutation must be *published* before the command
    reports success. The invariant exists because numbered workspace clones are evicted and destroy unpushed commits
    (`docs/beads.md`, "Publication Verification").
- **R8 — The mobile gateway spawns Python for every bead request.**
  - `GET /api/v1/beads[/:id]` in the Rust gateway spawns `sase mobile helper-bridge beads-list|beads-show`
    (`sase-core/crates/sase_core/src/host_bridge.rs:282`, `:415`). The long-lived process that already exists does no
    caching at all.

## 3. Would A Daemon Fix These?

| Root cause | Cost today | RPC read/write daemon | Direct-path fix |
|---|---|---|---|
| R1 integrity guard | ~20 s per mutation, growing | No. The daemon would still have to run the guard, unless it reimplements it, which *is* the direct fix | Read changed streams only; one `git cat-file --batch`. Expect <0.3 s |
| R2 import bloat | 1.3–2.0 s | Only with a new thin client. That is the same work as the direct fix | Lazy-import the pager only when paging to a TTY; slim `sase.bead.__init__` |
| R3 replay | 0.4–0.55 s per read | Yes (warm RAM) | Fingerprinted snapshot cache. Expect ~10–30 ms |
| R4 redundant reads | 0.4–1.3 s | Mostly | One load per command, plus the cache |
| R5 projection rewrite | ~0.9 s per write | No, unless the projection is dropped, which the direct path can also do | Take `issues.jsonl` off the hot path |
| R6 publish bookkeeping | 0.7 s plus lock waits | No | Push synchronously once when verification will run; cache the health verdict |
| R7 network | ~1.1 s | Only by relaxing the contract, and the direct path can relax it the same way | Optional machine-level outbox (§6 F) |
| R8 gateway | ~1–3 s per request | The gateway already *is* a daemon | Call `sase_core` bead reads in-process from the gateway |

The daemon uniquely wins only on R3. The cache wins R3 as well, and it does so for every process, without a protocol.

---

## 4. Critique Of The Daemon Plan

### What is right about it

- The pain is real and growing:
  - agents block ~25 s on every bead mutation;
  - an 8-phase epic pays minutes of wall time on bead bookkeeping alone;
  - the TUI and background jobs re-replay the full history constantly.
- "Keep the projection warm instead of rebuilding it" is exactly the correct idea. It just does not need a process.
- The *service host* changes one thing from the `sase-3e` era. The earlier daemon was dormant because nobody ran
  `sase daemon`; a service proc would actually be kept running. So the "never running" failure mode is solved. The
  other failure modes are not.

### Why I would not build a read/write RPC daemon

1. **Most measured cost is outside its reach** (§3). The two biggest items are the ~20 s guard and ~2 s of imports.
   Neither goes away because a process stays alive.
2. **It creates a second code path.** SASE's own accepted decision, *The Rust Core Is Required*, forbids "a
   dispatcher", "dual-run" and backends that can quietly diverge. A daemon with direct fallback is exactly that shape:
   every verb works in two modes.
   - Upstream Beads' changelog is a catalogue of what follows:
     - flags that did not work in daemon mode;
     - `created_by` not propagated through RPC;
     - custom types hidden while the daemon ran;
     - double JSON encoding in RPC responses;
     - socket paths too long;
     - stale daemons after binary replacement;
     - zombie state after database file replacement.
   - Upstream then deleted the whole layer (v0.50.0). What it later added back was a general-purpose *database* server
     (shared Dolt server mode, v0.60.0), not a bespoke per-verb RPC mirror.
3. **Staleness is harder here than in upstream Beads, because SASE has many stores per project.**
   - Every numbered workspace has its own `sase/repos/beads` clone, often at a different commit. Agents write into
     their own clone.
   - Detached sync workers pull underneath all of them.
   - A daemon would need a watcher and invalidation logic per clone. That means it needs the store fingerprint anyway.
     Once the fingerprint exists, the daemon's RAM copy is only a slightly faster cache.
4. **Writes carry context the daemon would have to marshal:**
   - the acting agent identity (`SASE_AGENT_NAME` → `created_by` and note authors);
   - cwd-relative routing and cross-project full-ID routing;
   - `@path` file values resolved from the client's cwd;
   - the pytest sandbox guard;
   - the mutation lock;
   - above all, publication verification against the *client's* clone.
   Each item is a new place for the daemon and direct modes to disagree.
5. **The service host restarts often** (updates, flag flips, config saves). Clients must handle a missing or starting
   daemon, which guarantees the fallback path is exercised and has to be maintained.
6. **Rollout-knob gravity.** `sase-3e` ended up with per-surface env switches, milestone kill switches and
   `force_direct`. The research at the time concluded the rollout controls had become a product of their own. A new
   daemon starts down the same road the moment it needs "use daemon for X but not Y".
7. **Its marginal value after the direct fixes is small:** ~10–40 ms per read. That is below what a human notices,
   and far below agent turn latencies.

### When a daemon *would* be the right call

- **After Phase 0–1, reads are still >150 ms p50 and the remaining cost is store loading, not process start.** I
  consider this unlikely: the fingerprint plus active-snapshot load is ~10–30 ms.
- **You explicitly relax the publication contract** and want a *publisher* that batches pushes for all workspace clones
  on a machine (§6 F). That is a legitimate daemon job, but it is about durability semantics, not read speed.

---

## 5. Requirement Adjustments (Called Out Explicitly)

- **RA1 — Reframe the goal.** Change "an optional daemon that makes beads faster when running" to "bead operations are
  fast for every consumer; any daemon is a pure accelerator".
  - Success criteria, **with or without the service host**:
    - p50 `ready`/`list`/`read` ≤ 150 ms;
    - mutation p50 ≤ 2 s including network, p90 ≤ 5 s.
- **RA2 — Keep synchronous publication in v1.** "Fast writes" should come from removing R1, R5 and R6, not from
  skipping the push. Relaxing "published before success" to "durably journaled outside the ephemeral workspace" is a
  separate, explicit decision (§6 F).
- **RA3 — Widen the scope beyond the CLI.** Include the TUI panes, scheduler jobs (`bead_claim_checks` and
  `wait_checks` run on 10 s routines), the mobile gateway, editor/LSP completion and bead pages. They all pay R3 today.
- **RA4 — Take `issues.jsonl` off the mutation hot path.** Regenerate it lazily, for example at `sase bead sync`, in
  `doctor`, or when a consumer asks. Consider untracking it.
  - It is a compatibility projection. Today it costs a 16.7 MB fsynced write plus a git re-hash on every mutation, and
    it inflates sidecar history.
  - Consumers keyed on its mtime would switch to the store fingerprint: the TUI `_BEAD_CACHE` and the wait-bead
    catalog.
- **RA5 — No new rollout-knob surface.** The cache always returns what a full replay would, so it needs a parity test
  and a doctor check, not a flag. If a flag is wanted, use at most one temporary `beta` flag as epic scaffolding, per
  the flag policy. No per-surface environment switches.
- **RA6 — Performance budgets on a realistic corpus.**
  - `just bead-perf-smoke` runs `tests/perf/bench_bead.py --issues 50 --dependencies 25`. The real store has 5,968
    beads and 1,712 streams.
  - The sidecar mutation benchmark has no upstream, so publication and R1 never run.
  - That is how a 20 s regression went unnoticed. Add a large synthetic or copied corpus, plus a remote-backed
    mutation scenario, with budgets.

---

## 6. Options Considered

**A. Read/write RPC daemon** — the proposal as stated.
- A Unix socket on the federation-worker framing, which is the existing precedent in
  `sase_gateway::federation_worker` and `src/sase/dispatch/federation/_ipc.py`.
- The daemon keeps each store's projection hot. Clients probe it and fall back to direct access.
- *Pros:* warm reads (~1 ms of server time); a natural home for push batching later.
- *Cons:* everything in §4. It fixes only R3 (and R8, if the gateway also became the bead server).
- **Not recommended.**

**B. Fix the direct path and add a fingerprinted on-disk snapshot cache in `sase_core`.** Fixes R1–R6 and R8.
Details in §7. **Recommended.**

**C. B plus a cache-warmer service proc.**
- The daemon inotify-watches known bead stores and rebuilds cache entries after pulls and mutations, so even the first
  read after a sync is warm.
- It serves no requests. If it is down, behavior is identical, just occasionally ~100 ms colder.
- **Recommended only if post-B telemetry shows cold misses matter.**

**D. SQLite projection instead of a binary snapshot.**
- This is what `research:202605/greenfield_bead_storage_architecture.md` proposed.
- *Pros:* SQL filters, and FTS for `search`.
- *Cons:* schema migrations. The legacy `beads.db` mirror accumulated nine migration helpers before being abandoned,
  and today it survives only as the Rust mutation lock file.
- Filtering 6k issues in memory takes microseconds, so SQL buys little now.
- **Defer.** Revisit if search needs FTS.

**E. Storage compaction or archival of closed streams** (checkpoint snapshots, archived shards).
- Attacks O(history) at the source. It would also shrink file counts, which feed R1's old shape, `git add` and
  `ls-tree`.
- But it is a canonical-format change with merge and resolver implications.
- **Defer.** The cache makes it unnecessary for speed. Revisit for repository size.

**F. Machine-level publication outbox plus a publisher service proc.**
- The CLI commits locally, then pushes to a never-evicted machine-local mirror or outbox, for example
  `~/.sase/projects/<key>/repos/beads.git`. That is ~50 ms, versus ~1.1 s or more to GitHub. The command returns
  there.
- A publisher daemon pushes to GitHub asynchronously, coalescing pushes from all of the machine's workspace clones and
  reducing non-fast-forward races.
- *Pros:* removes R7 from the CLI; fewer pushes. The durable rescue store already embodies "durable outside the
  workspace".
- *Cons:* changes an explicit invariant; other machines see writes later; publisher failures need loud notification.
- **A product decision for you, not a performance fix. Not in v1.**

---

## 7. Recommended Solution

### Phase 0 — Remove the pathological costs (small, independent changes; no new architecture)

1. **Integrity guard (`sase-17q`).**
   - Derive new-stream names from `ls-tree`.
   - Read only the changed streams, plus new streams lazily in the missing-events case.
   - Batch blob reads through a single `git cat-file --batch`.
   - Apply the same fix to `diagnose_event_stream_history`.
   - *Expected:* ~20 s → <0.3 s per publishing sync. It also stops holding the sync-worker lock for 10–25 s.
2. **Single publish.** When `ensure_bead_mutation_published` will run anyway, push synchronously once. Do not spawn a
   detached worker first. *Saves* a Python process and the lock wait.
3. **Lazy imports.**
   - `sase.bead.cli*` must not import `sase.pager`, Textual or ACE widgets at module level. Import the pager only when
     stdout is a TTY and paging is requested.
   - Trim the `sase.bead` package `__init__`.
   - *Expected:* −1.3 to −2.0 s on every slow-path verb; −0.1 s on fast-path verbs.
   - Guard it with an import-budget test for `sase bead list`, like the existing TUI `test_app_import_budget`.
4. **Routing without a full read.** Validate targets with the stream index or `bead_resolve_id`:
   - a root ID maps to `events/streams/<root>.jsonl`;
   - a child's root is its prefix before the first `.`.
   - *Saves* ~0.4–0.9 s per targeted command.
5. **TUI.** Stop passing `force=True` to the Beads and Plans pane loads on every tick, and let the existing mtime
   snapshot key decide. The key is already stored per file under `events/`.
6. **Gateway.** Serve `/api/v1/beads` by calling `sase_core` bead reads in-process from Rust instead of spawning
   Python per request.

### Phase 1 — Make `sase_core` reads O(changed) and writes O(1) (the core of the solution)

Belongs in `sase-core`, per the Rust-core boundary. Python only calls through.

1. **Parse once.**
   - Move `prune_removed_flag_event_streams` out of the read path and into the mutation path, `doctor` or a migration.
     Today it can delete files and rewrite the manifest *during a lockless read*.
   - Remove the deep copy and the triple validation.
   - Optionally parse streams on a small thread pool.
   - *Expected uncached replay:* ~400 ms → ~80–150 ms (estimate, based on CPython's 240 ms for the same JSON).
2. **Fingerprinted snapshot cache.**
   - **Location:** gitignored `beads.cache/`, next to `beads.db`, or `~/.sase/cache/beads/<store-key>/`.
   - **Keys:** each root stream keyed by `(relpath, size, mtime_ns, inode)`. Writes use temp-file-plus-rename, so a
     rewrite changes the inode. This is the same signature scheme `bead/touch_index.rs` already uses.
   - **Value per stream:** that stream's reduced issues, plus the few cross-stream facts: removals with their cascade
     IDs, dependency targets, and external refs.
   - **On read:**
     1. `stat` all streams (~3–5 ms).
     2. Reuse cached per-stream reductions for unchanged streams.
     3. Re-reduce only changed or new streams.
     4. Run the cheap global post-pass: `issue_removed` dependency pruning, dependency-target validation,
        external-ref collapse, and canonical sort.
     5. Write the updated entries atomically.
   - **Simpler fallback for v1:** one whole-store snapshot keyed by the full fingerprint. Any change triggers a full
     (Phase 1.1-fast) replay.
   - **Tiering:** keep a separate *active* segment for the ~408 non-closed issues (~2 MB), plus a compact status index
     of closed IDs for dependency blocking. `ready`, `blocked` and default `list` load only that segment; `--status
     closed`, `search` and `history` load everything.
   - **Format:** versioned `postcard`/`bincode`, or `rkyv` for mmap. The header carries the reducer and schema version.
     Any mismatch or corruption triggers a rebuild; the cache is never authoritative.
   - **Concurrency:** readers never lock. Mutations update the entries for the streams they touched write-through,
     under the existing `beads.db` flock.
   - **Correctness:**
     - Every read revalidates against the filesystem, so a pull by any sync worker, a write by any process, or a manual
       edit is picked up with no watcher or IPC.
     - Add a parity test (cached vs. full replay over a large corpus and randomized mutation sequences) and
       `sase bead doctor --verify-cache`.
   - *Expected warm read:* ~10–30 ms of Rust. End to end, `sase bead ready` ≈ 17 ms interpreter + ~40 ms of lean
     imports + ~20 ms ≈ **~80–120 ms**.
3. **Mutations through the cache.**
   - Load from the cache instead of replaying.
   - Keep the byte-preserving stream append that already exists.
   - Stop the per-mutation `issues.jsonl` regeneration (RA4).
   - *Expected Rust mutation:* ~650 ms → ~20–50 ms. `git add` drops to single-file cost.
   - *Expected end to end:* ~0.2–0.4 s local plus ~1.1 s network ≈ **1.5–2 s p50**, bounded by the network push under
     RA2.
4. **Close the lockless-read races found while reading the code.** I did not reproduce either:
   - New stream files are written before the manifest (`jsonl.rs:471-488`), so a concurrent lockless reader can fail
     the `stream_count` check (`jsonl.rs:408-414`).
   - The prune step in the read path mutates the store.
   The cache's fingerprint scan should tolerate a stream count that is one ahead: trust the directory, and repair the
   manifest under the lock.

### Phase 2 — Optional cache-warmer service proc (only if Phase-1 telemetry justifies it)

- **Trigger:** measured cold-cache reads (the first read after a sync) exceed a small budget, or you want TUI/agent
  reads to be warm immediately after pulls.
- **Shape:** a `command:` service proc (no new builtin is needed in `sase_core::service`), for example
  `sase bead cache warm --watch`.
  - It inotify-watches the primary store and the stores of workspaces with live agents.
  - After changes it calls the same `sase_core` cache-refresh function readers use.
  - It publishes a `status.json` summary for the Services tab.
- **Guardrails:**
  - no socket;
  - no request handling;
  - no client code path that depends on it;
  - no configuration beyond `enabled`.
  - If it writes a cache entry, readers still validate it by fingerprint, so a buggy warmer cannot serve stale data.

### Phase 3 — Only with an explicit contract decision: publication outbox and publisher daemon (§6 F)

Revisit if, after Phase 0–1, the ~1.1 s network push is still the complaint, or push races between workspace clones
show up in the sync logs.

### If you still want a read daemon, build it like this

- **Execute the same `sase_core` functions the direct path executes**, against the same snapshot cache. The daemon
  must never reimplement verbs. Its only difference is that the cache lives in RAM.
- Use the federation-worker transport:
  - 4-byte length-prefixed JSON;
  - 0600 socket under `~/.sase/run/<host>/`;
  - a same-user peer check;
  - stale-socket recovery;
  - version negotiation.
- Serve read verbs only.
- Clients:
  - try the socket once with a ~20 ms connect budget;
  - otherwise fall back to direct access, silently;
  - have no user-visible knobs.
- Start by pointing the gateway's bead routes at it (R8). The gateway is already long-lived.

---

## 8. Other Findings Worth Tracking

- **`sase-17q` (filed).** The integrity-guard walk (R1): ~20 s per mutation; p90 23.8 s in production.
- **Import budget for bead verbs (R2).** No test guards it today.
- **TUI forced reloads (R4).** `beads_pane.py:150` and the Plans pane bypass their own mtime snapshot key every tick.
  Worth checking against the in-progress `sase-zn` epic (TUI lag, O(corpus) refresh work) before filing.
- **`bead-perf-smoke` corpus is 50 issues, and its mutation scenario has no remote (RA6).**
- **Lockless-read races** in `read_event_store`: the prune mutation, and the manifest being written after new streams
  (Phase 1.4). Found by reading the code, not reproduced.
- **Gateway per-request Python subprocess for beads (R8).**

## 9. Open Questions For You

1. Is relaxing "published before success" to "durable outside the workspace" (§6 F) acceptable in principle? It
   decides whether any write daemon is worth discussing.
2. Can `issues.jsonl` leave the per-mutation path (RA4)? Can it leave git tracking entirely? Which external consumers
   still read it?
3. Should agents' `sase bead read`/`close` get a dedicated budget, for example p50 ≤ 150 ms and ≤ 2 s respectively,
   enforced in CI with the realistic corpus?

---

## Appendix — How The Numbers Were Produced

- **CLI wall times:** a bash loop timing `sase bead <verb>` three times each with `date +%s%N`, output discarded.
- **Profiles:** `cProfile` around `sase.main.entry.main()` with argv `bead list`, `bead ready` and `bead note …`.
- **Import graphs:** `python -X importtime` with the same argv.
- **Rust isolation:** a Python harness calling the `sase_core_rs` functions `bead_ready`, `bead_list` and
  `bead_read_event_store` directly, 5 runs, against `sase repo path beads`. Raw I/O, CPython `json.loads` and
  `scandir`/`stat` were timed on the same tree.
- **Local write floor:** `git clone --local` of the beads sidecar into the agent tmp dir, with origin removed. Then
  `sase_core_rs.bead_append_note(…)` plus `git add` and `git commit`, 5 iterations.
- **End-to-end sandbox:** a temp project (`.sase/checkout.json` plus a schema-2 `sidecar_repos` store record) whose
  `sase/repos/plans/beads` is a byte copy of the real store. It has a local bare `origin` with upstream tracking, the
  same shape as `_bench_sidecar_mutation_shell` in `tests/perf/bench_bead.py` plus a remote. Agent environment
  variables were unset.
- **Production:** the latest 2,500 `~/.sase/bead_push_logs/sync-2609*.log` files, filtered to `beads_dir` ending in
  `/repos/beads`, with durations computed from first to last event timestamp. Network durations come from
  `~/.sase/logs/tui_git_ops.jsonl` and `.1`.
- **Store stats:** `issues.jsonl` statuses, per-stream sizes, per-`operation` byte totals, and `git ls-tree -l` at
  historical revisions.
- **Prior art:**
  - SASE: `research:202605/rust_snapshot_migration_landing_research.md`,
    `plan:202605/revert_sase_3e_legend.md`, commits `5a65fa4fc` and `020a01ee3` (the historical
    `sase_3e_no_daemon_value_review.md`), and `research:202605/greenfield_bead_storage_architecture.md`.
  - Upstream: the Beads `CHANGELOG.md` (v0.50.0 and v0.59/0.60 daemon removal entries), read from an external
    checkout opened through `sase repo open`.
