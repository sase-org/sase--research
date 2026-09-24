# Faster Beads: Daemon Service Proc vs. Fixing the Direct Path — Consolidated Evaluation and Recommendation

Date: 2026-09-24. This is the lead researcher's consolidation of three independent reports. I also re-checked the
claims they disagreed on against sase `075225d53`, sase-core `eef7ca4`, the live `sase` bead store, and athena's sync
and git-op telemetry.

| Dependency | Preserved report | Immutable snapshot | Main contribution |
| --- | --- | --- | --- |
| `research.2e.cld` | [cld](bead_speedup_daemon_vs_direct_path__cld.md) | `file:explicit:9ad92478bbed29fae8a2e1ea` | End-to-end profiles of reads *and* writes. Found the ~20 s integrity-guard walk (filed as `sase-17q`). Fingerprinted snapshot-cache design. Prior art: `sase-3e` and upstream Beads daemons, both removed |
| `research.2e.mus` | [mus](bead_speedup_daemon_vs_direct_path__mus.md) | `file:explicit:6f28f8eda99b38c56c9f4ba2` | Import-tax analysis. Fast-path exclusion list. Lists what a daemon plan omits (versioning, freshness contract, test and sandbox behavior). Staged "read cache first, writes later" plan |
| `research.2e.gem` | [gem](bead_speedup_daemon_vs_direct_path__gem.md) | `file:explicit:8f456bfed07a2c8e77e92aec` | In-process SQLite read model. Why write-behind conflicts with single-turn agents. First to flag slow first-use sidecar clones in fresh workspaces |

No predecessor chat transcripts were read.

## Bottom line

**The pain is real, but a daemon is the wrong tool for most of it.** Bead commands are slow:

- A read takes **0.8–3.8 s**.
- A mutation takes **22–31 s**.
- The **first bead command in a fresh workspace takes 22–50 s**.

Almost none of that time is the kind a long-lived process removes. Here is where it goes:

1. **Mutations: ~20 s is one pathological loop.** The publication integrity guard runs one `git show` subprocess per
   event stream, per revision, twice per publish. That is ~6,850 subprocesses per mutation. A daemon would still have
   to run the guard. The fix is ~2 subprocesses instead of 6,850. It is already filed as `sase-17q`.
2. **First use in a workspace: 22 s p50 is a git housekeeping bug (new finding).** The beads sidecar clone uses
   `--reference-if-able … --dissociate`. That repacks ~1.2 GiB of loose objects, which are old copies of
   `issues.jsonl` that git's auto-gc never collects.
   - The same clone from a packed reference takes **2 s**.
   - A daemon cannot help here. A scheduler job and one git flag can. Filed as `sase-17r`.
3. **Reads: 1.3–2 s is Python importing the pager, Textual and ACE widgets.** This cost is in module imports; the
   store is not involved. A daemon only helps if the CLI becomes a thin client, and building that client is the same
   work as fixing the imports.
4. **The only cost a daemon uniquely targets: 0.4–0.55 s to replay the full 28 MB event history per read, 1–3 times
   per command.** An in-process, fingerprint-validated disk cache inside `sase_core` removes it too. It does so for
   every consumer (CLI, TUI, scheduler jobs, gateway, editor) with no socket, no invalidation protocol and no fallback
   path.

After those fixes, a read daemon would save **~10–30 ms per read** and **~0 ms per write**. The price is a second
code path. SASE's own `sase-3e` daemon (reverted 2026-05-14, −40k lines) and upstream Beads' daemon (deleted in
v0.50.0, ~19.7k lines) both paid that price and then removed it.

**Recommendation (details in §6):**

1. Fix the direct path: the guard, lazy imports, redundant reads, the double publish, and sidecar repacking.
2. Add a **disposable, fingerprint-validated read-model cache in `sase_core`**.
3. Stop regenerating the 16.7 MB `issues.jsonl` on every mutation.
4. Treat any daemon as a **later, optional, non-serving accelerator**, built only if measurements after steps 1–3 still
   call for one.
5. Handle "faster writes through a daemon" as an explicit **durability-contract decision** (a machine-local
   publication outbox), not as a performance feature.

Expected results:

| Operation | Today (verified) | After Phase 0 (fixes) | After Phase 1 (cache) |
| --- | --- | --- | --- |
| `sase bead ready` / `stats` | 0.81–1.3 s | ~0.6–0.7 s | **~0.1 s** |
| `sase bead list` | 2.7–2.9 s | ~0.8–0.9 s | **~0.15–0.25 s** |
| `sase bead read <id>` (agent path) | 2.5–3.8 s | ~0.9–1 s | **~0.15–0.25 s** |
| Mutation (`note`, `update`, `close`) | 22–31 s; sync-run p90 23.8 s | ~3–4 s | **~1.5–2 s**, bounded by the network push |
| First bead command in a new workspace | clone p50 22 s, max 47 s | **~2–3 s** | same |
| TUI Beads sub-tab | 3 full replays per project per auto-refresh tick | only when the store changes | tens of ms when it changes |

The "after" columns are estimates, derived in §1 and §6.

---

## 1. Where the time goes (merged and re-verified)

### 1.1 Store shape

| Metric | Value (2026-09-24) |
| --- | --- |
| Issues | 5,979 (416 non-closed ≈ 7%) |
| Event streams (one per root bead) | 1,715 |
| Event history | 28 MB, 83% of it in streams of closed beads (cld) |
| `issues.jsonl` (generated projection, tracked in git) | 16.7 MB; the non-closed subset is only 2.0 MB |
| Growth, last month | +61% bytes, +59% streams (cld) |

Every uncached cost below grows with **history** or **stream count**, not with active beads, so each one gets worse
every month.

### 1.2 Reads

| Command | Wall time | Path | Where the time goes |
| --- | --- | --- | --- |
| `list`, `show`, `read` | 2.5–3.8 s (`read` of 3 beads: 8.1 s) | Python slow path | Imports **1.3–2.0 s**: `sase.pager`, Textual, `ace.tui.widgets.prompt_panel`, 2,911 modules. Rust `bead_list` 0.53 s. argparse 0.17 s |
| `ready`, `stats`, `search`, `blocked` | 0.81–0.93 s | Rust fast path | Rust replay **0.4–0.48 s**. Imports 0.29 s, because the `sase.bead` package `__init__` is heavy |

Notes:

- The fast path deliberately excludes `list`, `read`, `show` and full-format `search`
  (`src/sase/main/bead_fast_path.py:28`). Those are exactly the verbs that feel slow.
- **Why the Rust replay is slower than it should be** (cld, confirmed in `sase-core`):
  - `read_event_store` first runs `prune_removed_flag_event_streams`, which parses every stream untyped
    (`jsonl.rs:395`), and then parses everything again typed.
  - The reducer deep-copies every stream.
  - Events are validated three times.
  - There is no memoization anywhere.
  - CPython `json.loads` of the same 28 MB takes 240 ms, which beats the 400–550 ms Rust replay.
- **Cache hot-path costs, measured today on the real store:**
  - `scandir` + `stat` of all 1,715 streams (a store fingerprint): **6.5 ms**.
  - Parsing just the 416 active issues: **9 ms**, even in CPython.
  - Parsing all 5,979 issues: 105 ms in CPython.
  - So a warm, fingerprint-checked in-process read costs tens of milliseconds. There is no headroom left for a daemon to
    win.

### 1.3 Writes

cld's sandbox run used a byte copy of the real store with a local bare remote, so it includes everything except the
network:

- `note` took 24.0–24.2 s and `update --status` took 22.3–22.4 s.
- Live mutations against GitHub took 28.3 s and 31.4 s.

cProfile breakdown of one `note`:

| Step | Time |
| --- | --- |
| `refuse_unpublished_event_stream_shrink`: 2 calls → 4 × `streams_at_rev` → **6,854 `git show` subprocesses** | **~20 s** |
| Imports (pager, Textual, ACE) | 2.2 s |
| Write lock, including a 43-git-call health preflight | 1.2 s |
| Target routing runs a **full `list_issues`** only to validate one ID (`operation_context.py:280`) | 0.86 s |
| Rust mutation: full replay, append, then rewrite and fsync of the whole 16.7 MB `issues.jsonl` | 0.6–0.73 s |
| `git add`, which re-hashes `issues.jsonl` | 0.24–0.42 s |
| Network, from `tui_git_ops.jsonl` | fetch p50 0.48 s; push p50 0.57 s, p90 3.2 s |

**I independently re-verified the guard:**

- `streams_at_rev` (`src/sase/bead/_stream_integrity_git.py:114`) runs `ls-tree` and then one `show_text` per stream.
  `refuse_unpublished_event_stream_shrink` calls it for HEAD and for the ancestor (`_stream_integrity.py:182-183`).
- The sync logs agree. Across 2,368 beads-sidecar sync-worker runs (Sep 22 14:38 → Sep 24 09:01):
  - duration p50 **2.1 s**, p90 **23.8 s**, p99 36.4 s, max 55.3 s;
  - **22%** of runs exceeded 10 s;
  - the pre-integration guard gap alone was p50 1.4 s and p90 10.6 s.

Another write cost is double publication (cld). The default `push_after_commit: async` spawns a detached sync worker.
Then `ensure_bead_mutation_published` forces a synchronous publish that waits up to 30 s
(`MUTATION_PUBLICATION_WORKER_LOCK_WAIT_SECONDS`) for the worker it just spawned.

### 1.4 First use in a fresh workspace (new finding, extends gem)

My first `sase bead ready` in this workspace took **50.1 s**, and 47.3 s of that was `sdd.clone.remote` of the beads
sidecar. Across the last 13 h of `tui_git_ops.jsonl` there were **41** such clones:

- p50 **22.2 s**, p90 28.4 s, max 47.3 s;
- roughly 3 per hour, each blocking an agent's first bead command.

The cause is not the network:

- `_remote_clone_args` (`src/sase/sdd/_store_clone_remote.py:229`) clones with
  `--reference-if-able <primary beads clone> --dissociate`. Dissociating repacks everything borrowed from the
  reference.
- The reference is fresh, but it holds **1,891 loose objects totaling 1.15 GiB**. The primary project store holds
  2,334, totaling 1.52 GiB.
- ~230 of those loose objects are over 200 KB. Each is a **~5.4 MB compressed copy of `issues.jsonl`**, one per bead
  commit since the last repack. Together they account for essentially all 1.15 GiB.
- Git's `gc.auto` threshold is 6,700 loose objects, so auto-gc never fires, even though the loose objects are huge.

Local experiment, no network:

| Clone style | Time |
| --- | --- |
| `--dissociate` from the loose-heavy reference | **24.1 s** |
| `--dissociate` from a fully packed copy of it | **2.0 s** |
| `--shared` (alternates) | 7 ms, plus 0.38 s checkout |

So a periodic repack of the reference removes ~90% of this cost. Taking `issues.jsonl` off the per-commit path removes
the cause.

### 1.5 Consumers other than the CLI

The CLI is not the only thing paying replay costs:

- **TUI.** `load_project_beads` (`beads_data_sources.py:30-32`) calls `list_issues`, `ready` and `blocked`, which is
  three full replays.
  - `BeadsPane.on_refresh` passes `force=True` (`beads_pane.py:150`), and `force` skips the unchanged-store check in
    `load_beads_snapshot` (`beads_data.py:89`).
  - The auto-refresh loop calls `on_refresh` on every tick while the Beads artifacts sub-tab is visible
    (`_auto_refresh_surfaces.py:464`), so the TUI re-replays the store every tick. The Plans pane has the same pattern
    (`plans_pane.py:192`).
  - Verified in code; not timed.
- **Gateway.** The Rust gateway serves `/api/v1/beads[/:id]` by spawning `sase mobile helper-bridge beads-list|show`
  per request (`host_bridge.rs:415,422`). The one long-lived process SASE already has does no bead caching.
- **Scheduler jobs and `bead_statuses_for_project`.** They hydrate the whole store to answer a few IDs. `sase-x3`
  (open) proposes a multi-get for this.

This matters for the design: **a CLI-facing daemon would not fix the TUI, the gateway or the scheduler unless each of
them also became a client.** An in-process cache in `sase_core` fixes all of them automatically.

---

## 2. Where the reports disagreed, and how I resolved it

| Question | cld | mus | gem | Resolution |
| --- | --- | --- | --- | --- |
| Mutation latency | 22–31 s, ~20 s of it the guard | Not measured; "dominated by git and network" | 1.8–4.5 s, dominated by the `issues.jsonl` rewrite and push | **cld is right.** Code and 2,368 production sync runs confirm it (§1.3). gem's figure probably came from a store where the guard returned early: it returns immediately when there is no upstream or no changed stream |
| Is there IPC precedent? | Yes: federation worker | "No existing IPC story" | — | **cld is right.** `src/sase/dispatch/federation/_ipc.py` implements length-prefixed JSON over `AF_UNIX`. Irrelevant anyway if no socket is built |
| What should hold the warm read model? | On-disk fingerprinted snapshot in `sase_core` | Daemon RAM, after an import diet | In-process SQLite `beads.db` in WAL mode | **In-process, disposable cache in `sase_core`.** SQLite is a fine substrate, with direct precedent (below), but **not in `beads.db`**: that file is the Rust mutation lock (`BEAD_MUTATION_LOCK_FILENAME`, `mutation/store.rs:49`) |
| Is an import diet enough? | Necessary, not sufficient | "~70% of read latency; gets reads to ~1 s" | Move reads to the Rust fast path | Imports are the biggest *read* item, but ~1 s is not "much faster". The remaining 0.4–0.55 s replay, times 1–3 per command, needs the cache |
| What would a service proc do? | Cache warmer at most; later an outbox publisher | Read-cache UDS server; later a write queue | `bead-syncd`: background fetch, SQLite warm-up, TUI change events | See §4. The only job that genuinely needs a daemon is an **outbox publisher**, and that changes the contract. The rest are cheaper as scheduler jobs or in-process code |
| Human-facing fast writes | Outbox, as a product decision | Not in v1 | `--async` / `--no-push` for humans | Both relax "published before success". Neither belongs in v1 (RA2) |

**Why SQLite is acceptable here, despite cld's warning.** cld points out that the legacy `beads.db` mirror accumulated
nine migration helpers before it was abandoned. That mirror was treated as data to preserve. A cache that is
**never authoritative and is dropped and rebuilt on any schema-version mismatch** never migrates: a version bump costs
one ~0.5 s replay.

sase-core already runs exactly this pattern in production. The agent-artifact index
(`agent_scan/index/storage.rs`) is WAL SQLite with per-file signature columns, a `record_json` payload, and a
`schema_version` meta row (now v31). Reusing that pattern gives three things for free:

- point lookups for `show` and `read`;
- the `sase-x3` multi-get;
- indexed `status` filters for `ready` and `blocked`.

cld's flat binary snapshot is an equally valid substrate. The format matters far less than the invariants in §6
Phase 1.

---

## 3. Critique of the plan as stated

### What is right about it

- **The pain is large, widespread and growing.**
  - Every agent blocks ~25 s per bead mutation.
  - An 8-phase epic spends minutes of wall time on bead bookkeeping.
  - The TUI and scheduler replay 28 MB repeatedly.
  - Costs grow ~60% per month with the store.
- **"Keep a warm projection instead of rebuilding it" is the correct core idea.** It just does not need a process.
- **The service host fixes one of `sase-3e`'s failure modes.** `sase-3e`'s daemon sat dormant because nobody ran
  `sase daemon`. The 2026-05-14 review found it `stale` with a dead PID, and clients paid a 1 s socket-probe timeout
  per command. A service proc really would be kept running. That does not fix the other failure modes.

### Why I would not build a read/write RPC daemon

1. **Most of the measured cost is out of its reach.** It does not touch the ~20 s guard, the 22 s clone, the ~2 s of
   imports or the ~1 s network push. Of the list in §1, it removes only the replay, and the in-process cache removes
   that as well.
2. **It creates two code paths for every verb.** *The Rust Core Is Required* rejects dispatchers, dual-run and
   backends that can quietly diverge.
   - A daemon with direct fallback is exactly that shape.
   - `sase-3e` grew per-surface switches, milestone kill switches and `force_direct` before it was reverted.
   - Upstream Beads' changelog lists what follows: flags that did not work in daemon mode, `created_by` lost over RPC,
     custom types hidden while the daemon ran, double JSON encoding, stale daemons after binary upgrades, and zombie
     state after the database was replaced. Upstream deleted the whole layer in v0.50.0 (2026-02-14) and finished the
     removal in v0.59/v0.60.
   - What upstream runs now is a general-purpose shared Dolt SQL server, not a per-verb RPC mirror.
3. **Invalidation is harder in SASE than upstream, because there are many stores.**
   - Every numbered workspace has its own beads clone, at its own commit.
   - Sync workers pull underneath all of them.
   - A daemon would therefore need a fingerprint per clone anyway. Once the fingerprint exists, the daemon's RAM copy
     is only a slightly faster version of the disk cache.
   - Watching with inotify is worse than fingerprinting on every read. It misses cross-clone and git-integration
     updates (mus).
4. **Writes carry client context the daemon would have to re-host.** The daemon would need:
   - the acting agent's identity (`SASE_AGENT_NAME` → `created_by`);
   - cwd-relative and cross-project routing;
   - `@path` values resolved from the client's cwd;
   - the pytest sandbox guard;
   - read-only-store refusal;
   - the mutation lock;
   - **publication verification against the client's own clone**.

   Each is a new place for the daemon and direct modes to disagree.
5. **Write-behind breaks single-turn completion (gem).** An agent that closes a bead and then declares done relies on
   the mutation having been published. If a daemon acknowledges in 5 ms and fails to push 10 s later, the agent has
   already exited, and its workspace may be evicted along with the unpushed commit. This is why `docs/beads.md`
   requires "published before success".
6. **The service host restarts often** (updates, flag flips, config saves). The fallback path will be exercised
   constantly, so it has to stay first-class forever. That means the direct path must be fast anyway (gem's "optional
   dilemma").

### What the plan leaves unspecified (mus)

- a transport and auth model;
- protocol versioning across mixed CLI versions (uv tool, repo `.venv`, release);
- a freshness contract: what "stale" means, and who can see it;
- coexistence with direct writers and machine sidecar writers;
- behavior in tests and sandboxes, where the service lifecycle exits 125 under pytest;
- observability;
- which side of the Rust boundary the store logic lives on.

The recommended design below makes all of these questions disappear rather than answering them.

---

## 4. What a bead service proc *would* be good for

Sorted from most to least justified.

| Candidate job | Verdict |
| --- | --- |
| **Machine-local publication outbox and publisher.** The CLI commits, then pushes to a never-evicted machine mirror (~50 ms, e.g. `~/.sase/projects/<key>/repos/beads.git`) and returns. A daemon pushes to GitHub, coalescing all workspace clones on the machine (cld) | **The only genuinely daemon-shaped job.** It removes the ~1 s push from every mutation and reduces push races. But it relaxes "published before success" to "durable outside the workspace", and other machines see writes later. **Your product decision; not v1** |
| **Sidecar repacking and maintenance** (new) | Periodic and short-lived, so it is a **scheduler job**, not a daemon. It removes ~20 s from every fresh-workspace clone |
| **Cache warmer.** Watch stores and refresh cache entries after pulls (cld, gem) | Optional, later, **only if** cold first reads after a sync measurably hurt. No socket, and readers still validate by fingerprint. The worst case without it is one ~0.1–0.5 s cold read |
| **Background `git fetch` so pushes fast-forward** (gem) | Weak. It saves at most the ~0.5 s fetch. Fetching or rebasing inside a workspace clone underneath a running agent adds lock contention. It only helps for real if clones use a machine mirror as their remote, which is the outbox option again |
| **TUI change events instead of polling** (gem) | Unnecessary. The stat poll costs ~6.5 ms. The real TUI cost is the `force=True` reload, which is a one-line fix |
| **Read RPC server** (mus Phase 1; the original proposal) | Not recommended. It saves ~10–30 ms per read after the cache, at the cost of §3 |
| **Write queue / single writer** (mus Phase 2) | Not recommended unless lock-timeout telemetry shows contention itself, rather than the guard holding the lock for 10–25 s, is the bottleneck. After `sase-17q`, the lock-hold time falls by ~100× |

---

## 5. Requirement adjustments (called out explicitly)

- **RA1 — Reframe the goal.** Replace "an optional daemon that makes beads much faster when running" with **"bead
  operations are fast for every consumer, with or without the service host. Any daemon is a pure accelerator that no
  client depends on."**
  - Success criteria:
    - `ready`/`list`/`read` p50 ≤ 150–250 ms;
    - mutation p50 ≤ 2 s and p90 ≤ 5 s, including the network;
    - first bead command in a new workspace ≤ 5 s.
- **RA2 — Keep "published before success" in v1.** Fast writes come from removing the guard walk, the double publish,
  the per-mutation `issues.jsonl` rewrite and the redundant reads. They do not come from skipping the push.
  - Relaxing the contract (outbox, or gem's `--async` for humans) is a separate, explicit decision.
- **RA3 — Widen the scope from "the CLI" to every reader:** the TUI Beads and Plans panes, scheduler jobs, the gateway,
  editor completion and bead pages. They all pay the replay today.
- **RA4 — Take `issues.jsonl` off the mutation hot path.** Today every mutation costs:
  - a 16.7 MB fsynced rewrite;
  - a git re-hash;
  - a new ~5.4 MB loose object, which causes §1.4.

  Regenerate it lazily (at sync, in `doctor`, or on demand) and consider untracking it.
  - About 25 Python modules reference it: the conflict resolver, `finalizers/reconciliation.py`, TUI surface tokens,
    the wait-bead catalog and others.
  - Consumers keyed on its mtime must move to the store fingerprint.
  - This needs a consumer audit first, so it is the riskiest item in the plan.
- **RA5 — No new rollout-knob surface.** The cache must return exactly what a full replay returns. It needs a parity
  test and a `doctor` check, not per-surface switches. At most one temporary `beta` flag as epic scaffolding, per the
  flag policy.
- **RA6 — Performance budgets on a realistic corpus.**
  - `just bead-perf-smoke` benchmarks 50 issues, and its mutation scenario has no remote, so the guard never runs.
    That is how a 20 s regression went unnoticed.
  - Add a copied or synthetic ~6k-issue / ~1.7k-stream corpus, a remote-backed mutation case, and an import-budget
    test for `sase bead list` (like the TUI's `test_app_import_budget`).
- **RA7 (new) — Fresh-workspace bead latency is in scope.** Nobody feels a read daemon's 30 ms, but every new agent
  feels the 22 s sidecar clone.

---

## 6. Recommended solution

### Phase 0 — Remove the pathological costs (small, independent, no new architecture)

1. **Integrity guard (`sase-17q`, filed).**
   - Take new-stream names from the `ls-tree` output already fetched.
   - Read only the changed streams, plus new streams lazily when events are missing.
   - Batch blob reads through one `git cat-file --batch`.
   - Apply the same fix to `diagnose_event_stream_history`.
   - Expected: ~20 s → <0.3 s per publish. It also stops holding the sync-worker lock for 10–25 s.
   - Keep the `sase-li` protection it exists for.
2. **Sidecar repacking (new).** Add a scheduler job that runs `git repack -d` (or `git gc`) on the primary and
   reference beads clones whenever their loose-object bytes exceed a threshold. The threshold must be on bytes, not
   object count.
   - Optionally switch fresh-workspace clones to `--shared` against a never-pruned machine mirror; only the repack is
     required.
   - Expected: clone p50 22 s → ~2–3 s.
3. **Lazy imports.** `sase.bead.cli*` must not import `sase.pager`, Textual or ACE at module level. Import the pager
   only when paging to a TTY. Slim the `sase.bead` package `__init__`. Guard the result with an import-budget test.
   Expected: −1.3 to −2.0 s on slow-path verbs, −0.1 s on fast-path verbs.
4. **Single publish.** When `ensure_bead_mutation_published` will run anyway, push synchronously once. Do not spawn a
   detached worker and then wait up to 30 s for it. Also cache the health-preflight verdict, which is 43 git calls.
5. **Routing without a full read.** Validate target IDs by stream path (a root ID maps to
   `events/streams/<root>.jsonl`, and a child's root is its prefix) instead of calling `list_issues`. Expected: −0.4 to
   −0.9 s per targeted command.
6. **TUI.** Drop `force=True` from the Beads and Plans panes' `on_refresh`. The existing store mtime key already
   decides whether a reload is needed.
7. **Gateway.** Serve `/api/v1/beads` through in-process `sase_core` reads instead of spawning Python per request.

### Phase 1 — A disposable read-model cache in `sase_core`

This is the heart of the solution. Per the Rust-core boundary, the logic lives in `sase-core`, and Python only calls
the binding (with `sase-core-revision.txt` moved past the change).

1. **Parse once.**
   - Move `prune_removed_flag_event_streams` out of the read path, into mutation, `doctor` or a migration. Today it can
     delete files and rewrite the manifest *during a lockless read*.
   - Drop the deep copy and the triple validation.
   - Expected uncached replay: ~450 ms → ~100–150 ms.
2. **Cache: substrate.** A gitignored cache file next to the store, e.g. `beads.cache.sqlite`. **Never `beads.db`**,
   which is the mutation lock. Model it on the agent-artifact index:
   - WAL mode;
   - a `meta.schema_version` row carrying the reducer and schema version;
   - one row per root stream, keyed by the stream's `(relpath, size, mtime_ns, inode)` signature (the scheme
     `touch_index.rs` already uses);
   - one row per issue, with `record_json` plus indexed `id`, `status`, `parent`, `stream` columns.

   A flat binary snapshot is an acceptable alternative.
3. **Cache: read algorithm.**
   1. `stat` all streams (~6.5 ms today).
   2. Re-reduce only streams that are new or whose signature changed.
   3. Run the cheap global post-pass: removal cascades, dependency-target validation, external-ref collapse.
   4. Commit the changes.

   Readers take no bead lock. SQLite's own locking serializes the cache writers.
4. **Cache: correctness.**
   - A version mismatch or corruption means drop and rebuild. The cache is never authoritative.
   - Every read revalidates against the filesystem. That covers pulls by any sync worker, writes by any process, and
     manual edits, with no watcher and no IPC.
   - Ship with a parity test (cached vs. full replay over a large corpus with randomized mutation sequences) and
     `sase bead doctor --verify-cache`.
5. **Cache: tiering.** `ready`, `blocked` and default `list` touch only the ~416 active rows plus a closed-ID status
   index. Point reads (`show`, `read`, `sase-x3` multi-get) are single indexed lookups.
6. **Mutations through the cache.**
   - Load state from the cache instead of replaying.
   - Keep the byte-preserving stream append.
   - Update touched rows write-through, under the existing `beads.db` flock.
   - Stop the per-mutation `issues.jsonl` rewrite (RA4).
   - Expected Rust mutation: ~650 ms → ~20–50 ms. `git add` drops to single-file cost. End to end: ~0.3 s local plus
     ~1.1 s network ≈ **1.5–2 s p50**.
7. **Close two lockless-read races.** These come from cld's code reading; neither was reproduced.
   - New stream files are written before the manifest, so a concurrent reader can fail the `stream_count` check.
   - The prune step mutates the store during a read.

   The fingerprint scan should trust the directory listing and repair the manifest under the lock.
8. **Optional after Phase 1:** extend the Rust CLI fast path to `list`, `show` and `read` (mus, gem) if the p50 budget
   is still missed. After lazy imports and the cache, this is polish, not the fix. It is also real work: pager
   rendering and audited-read recording would move into Rust.

### Phase 2 — Optional cache-warmer service proc (only if Phase 1 telemetry justifies it)

- **Trigger:** cold first reads after syncs measurably exceed budget.
- **Shape:** a `command` service proc, e.g. `sase bead cache warm --watch`. It watches the primary store and the stores
  of workspaces with live agents, and calls the same `sase_core` refresh function that readers call.
- **Guardrails:**
  - no socket;
  - no request handling;
  - no client code path that depends on it;
  - no configuration beyond `enabled`.

  Readers validate everything it writes, so a buggy warmer cannot serve stale data.

### Phase 3 — Only with an explicit contract decision: publication outbox and publisher service proc

Revisit this if, after Phases 0–1, the ~1 s network push is still the complaint, or if sync logs show push races
between workspace clones. This is where a daemon earns its keep. Its failures need loud notification, and the
rescue-store semantics must extend to the outbox.

### If you still want a read daemon anyway

- It must execute the **same `sase_core` functions against the same cache**, never reimplementing verbs.
- Use the federation-worker transport: length-prefixed JSON; a 0600 socket under `~/.sase/run/<host>/`; a same-user
  peer check; version negotiation.
- Serve read verbs only.
- Clients try the socket once with a ~20 ms budget, fall back silently, and have no knobs.
- Point the gateway at it first.

---

## 7. What would change this recommendation

- **After Phase 1, reads are still >250 ms p50 and the time is in store loading, not process start.** I consider this
  unlikely: the fingerprint plus active-tier load is ~20–40 ms. If it happens, a read daemon becomes reasonable.
- **You accept "durable outside the workspace" as the completion bar for bead writes.** Then build Phase 3 (the outbox
  publisher) early. It is the one place a daemon removes a cost the direct path cannot.
- **A web or remote frontend needs live bead subscriptions** (not polling). Then the gateway, already a long-lived Rust
  process, should grow a change feed backed by the same cache. That is still not a new bead daemon.

## 8. Follow-ups

- **Filed:** `sase-17q` — the integrity-guard walk (~20 s per mutation).
- **Filed this turn:** `sase-17r` — the fresh-workspace beads sidecar clone (p50 22 s, caused by `--dissociate` repacking
  ~1.2 GiB of loose `issues.jsonl` objects). See §1.4.
- **Related, open:** `sase-x3` (multi-get). Phase 1 point lookups subsume it, so coordinate rather than build twice.
- **Not yet filed; each needs a duplicate check first:**
  - TUI Beads/Plans `force=True` reload on every tick. Check against the in-flight `sase-zn` TUI-lag epic.
  - An import budget for bead verbs.
  - A realistic-corpus `bead-perf-smoke` with a remote.
  - Gateway per-request Python spawn for beads.
  - The lockless-read races.

## 9. Open questions for you

1. Is relaxing "published before success" to "durable outside the workspace" acceptable in principle? This is the
   only thing that makes a write daemon worth discussing (Phase 3).
2. Can `issues.jsonl` leave the per-mutation path, and can it leave git tracking entirely? Which external consumers
   still need it?
3. Should agent-facing bead verbs get CI-enforced budgets on the realistic corpus (e.g. `read` p50 ≤ 250 ms, `close`
   p50 ≤ 2 s)?

---

## Appendix — The lead researcher's own verification

All run on athena on 2026-09-24, between ~08:55 and 09:10 EDT.

- **Guard code path:** read `_stream_integrity_git.py:114-142` and `_stream_integrity.py:160-200`. Confirmed one
  `show_text` subprocess per stream for HEAD and ancestor, in each of the two calls per publish.
- **Sync telemetry:** the last 3,000 `~/.sase/bead_push_logs/sync-2609*.log` files, filtered to `beads_dir` ending
  in `/repos/beads` (n = 2,368). Durations run from first to last event; the guard gap is `started` → `manifest_repair`.
- **CLI timings:** `date +%s%N` around `sase bead ready|list|stats|read`, two runs each, output discarded.
- **Fresh-workspace clone:**
  - `sdd.clone.remote` rows in `~/.sase/logs/tui_git_ops.jsonl` and `.1`, covering 2026-09-23 19:58 → 09-24 09:04,
    beads staging paths only (n = 41).
  - `git count-objects -vH` and loose-object size census on the reference and primary beads clones.
  - A local-only `git clone --no-checkout` experiment in `/tmp`: `--reference-if-able … --dissociate` from the real
    reference; the same from a freshly packed copy; `--shared`. Cleaned up afterwards.
- **Cache hot-path costs:** `os.scandir` + `stat` of `events/streams` (best of 5), and CPython `json.loads` of the
  active and full `issues.jsonl` rows.
- **Cross-checks:**
  - TUI `force=True` call chain: `beads_pane.py:150` → `lifecycle.py:45` → `view.py:353` →
    `_auto_refresh_surfaces.py:464`, and the `force` bypass at `beads_data.py:89`.
  - `beads.db` as the mutation lock: `sase-core` `mutation/store.rs:49`.
  - Agent-artifact SQLite index precedent: `agent_scan/index/storage.rs`.
  - Federation UDS IPC: `src/sase/dispatch/federation/_ipc.py`.
  - Gateway bridge spawns: `host_bridge.rs:415,422`.
  - `sase-3e` revert: `5a65fa4fc`, 346 files, −40,172 lines; the historical review is at `020a01ee3`.
  - Upstream Beads `CHANGELOG.md`: v0.50.0 (2026-02-14) "Removed daemon/RPC subsystem … ~19,663 lines"; v0.59.0 and
    v0.60.0 finished the removal. Read from an external checkout opened through `sase repo open`.
