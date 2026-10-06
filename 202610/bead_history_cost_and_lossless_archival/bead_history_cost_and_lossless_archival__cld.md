# Does Bead Count Matter? Bead-Store Scaling, and Archiving Old Beads Without Losing Them

Date: 2026-10-06 · Researcher: `research.3u.cld` · Host: athena (64 cores, load average 11–18 during runs)

Code measured: sase `22ea0cf4db`, sase-core `fa390362` (`sase_core_rs` 0.37.0, optimized build), and the live `sase`
beads sidecar at `2b55fc23b`. All benchmarks ran either read-only against the live store or against copies in `/tmp`.
No live bead was mutated.

---

## Bottom line

**Yes, the number of beads matters, and the cost is linear in total history.** Bead count is a rough proxy. The real
driver is the number of events and bytes in the store. Most of them belong to closed beads.

- **Every bead read and every write replays the entire event store.** There is no index or cache, and nothing persists
  between calls. One replay costs about **83 µs per bead (≈12 µs per event)**: **0.58 s** at today's 7,034 beads,
  1.28 s at 14k, 2.7 s at 28k and 5.7 s at 56k (measured on scaled copies, §2.2).
- **Commands multiply that cost.** A read does 1–2 replays. A write does 3–5, then rewrites and commits the whole
  20.8 MB `issues.jsonl` projection. The count-dependent part of one write is about **3–4.5 s at today's size and
  ~16–21 s at 4×** (§2.5).
- **The TUI Beads pane is quadratic, not linear.** One refresh takes 2.8 s today, 8.2 s at 2× and **48 s at 4×**. It
  re-runs every 10 s while the pane is visible (§2.7).
- **The store is growing fast:** +88 beads/day (5,979 on 09-24 → 7,034 today), so it is on track for 2× around
  January 2027 and 4× around mid-2027.

**On the plan itself:** the goal is right, but archiving first is the wrong order. Reads and writes should pay only
for active work. But physically archiving closed beads buys only **1.6–2.8×** on today's store (measured, §2.10). It
also adds the most correctness risk of any option. Several cheaper fixes each deliver as much or more, and none of
them moves any data:

- **Remove waste in the replay itself.** 25% of every replay re-runs a finished migration, and CPython parses the same
  JSON 2.5× faster than the Rust reducer does.
- **Stop re-replaying within one command.**
- **Fix the quadratic TUI loop.**
- **Add a fingerprint-validated read cache.** This is a "logical archive": closed streams are never re-parsed unless
  they change. Warm reads drop to ~20–50 ms at any history size.
- **Take the derived `issues.jsonl` off the commit path.** It is 74% of the beads repo's git history.

"Compress" helps disk and clone size, not speed: replay is CPU-bound, and I/O is 4% of it.

**My recommendation, in order:**

1. Cheap fixes.
2. A disposable read cache in `sase_core`, which delivers the hot/cold split logically.
3. Stop committing `issues.jsonl` on every mutation.
4. Only then, and only when a measured trigger fires, a **byte-preserving "sealed segment" archive** for cold lineages.
   It never edits or deletes an event, and it thaws by overlay rather than by moving files back.

The repo already has a working precedent for this shape: the goal ledger's O(unsettled) hot read.

---

## 1. How the store works today (the parts that matter for scaling)

- **Layout.** The beads sidecar holds:
  - `events/streams/<stream>.jsonl`: canonical append-only events, one stream per root lineage (plus a few
    child-specific streams), 2,108 files;
  - `events/manifest.json`: only a `stream_count`;
  - `issues.jsonl`: a generated projection, tracked in git;
  - `pages/`: generated Markdown, also tracked;
  - `config.json`;
  - `beads.db`: gitignored, now only the mutation flock target (`crates/sase_core/src/bead/mutation/store.rs:45-49`).
- **Read.** `read_event_store` (`crates/sase_core/src/bead/jsonl.rs:392`) does the following on every call:
  1. Runs `prune_removed_flag_event_streams` (`jsonl.rs:395`). It parses **every line of every stream** into an untyped
     `serde_json::Value`, a leftover from the flag-type removal migration.
  2. Parses everything again, typed.
  3. Deep-copies all streams in `validated_event_streams` (`events/reduction.rs:262-266`).
  4. Validates events three times, merges, reduces and sorts.

  No mtime, hash or HEAD check exists anywhere. Every binding call starts from scratch.
- **Write.** `MutableStore::load` (`mutation/store.rs:273-308`) does a full replay. Then `save` (`store.rs:310-333`)
  does three things:
  1. validates every issue;
  2. sorts and validates all streams and rewrites each changed stream file whole;
  3. calls `write_issues_jsonl`, which **serializes, fsyncs and atomically renames the entire 20.8 MB projection**.

  The Python lane then does extra replays: routing builds an ID set with `list_issues`, plus `resolve_id` and `show`
  calls. It finishes with `git add`, commit, push and "verify published".
- **Consumers beyond the CLI.**
  - The TUI Beads pane runs list, ready and blocked (three replays) on every 10 s auto-refresh while visible. Its
    `on_refresh` passes `force=True`, which skips the existing mtime key (`beads_pane.py:149-150`).
  - The Plans pane, scheduler jobs (`bead_task_triage`, `bead_stale_cleanup`, `bead_claim_checks`), the touch index
    and page publication all replay too.

---

## 2. Measurements

### 2.1 Store shape and growth

| Metric | 2026-09-24 (prior research) | 2026-10-06 (now) |
| --- | --- | --- |
| Beads | 5,979 | **7,034** (closed 6,445 = 91.6%; ready 393, in_progress 168, open 27, snoozed 1) |
| Types | — | phase 4,976 · task 1,109 · plan 949 |
| Event streams / events | 1,715 / — | **2,108 / 48,357**, 35.1 MB (median stream 9 KB, max 165 KB) |
| `issues.jsonl` | 16.7 MB | **20.8 MB**. Closed rows are 18.3 MB of it (88%); active rows only 2.4 MB (588 rows) |
| Largest projection field | — | `notes` 11.0 MB (53%), `description` 2.6 MB |
| Beads created per month | — | May 754 · Jun 251 · Jul 1,181 · Aug 1,987 · Sep 2,228 |
| Beads repo | — | 20,443 commits since 2026-07-28 (~290/day, peak ~690/day). Pack 101.6 MB |

The comment in `src/sase/sdd/_store_maintenance.py:14` still describes "a ~5 MB copy of the `issues.jsonl`
projection". The file is now 4× that.

### 2.2 Core replay and write cost vs. store size (Rust bindings, median of 5)

Method: subsets are random root streams closed under dependency, parent and child references. Multiples combine the
real store with 1, 3 or 7 copies whose bead IDs get a different 4-letter prefix of the same length, so validation
limits and field sizes are unchanged. Details are in Appendix A.

| Corpus | Beads | Streams | Events | Event MB | `bead_read_store` (incl. Python conversion) | `bead_show` | `bead_ready` | `bead_append_note` | `bead_update` | `issues.jsonl` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ⅛× | 1,023 | 263 | 7,311 | 5.1 | 0.098 s | 0.080 s | 0.083 s | 0.098 s | 0.096 s | 3.0 MB |
| ¼× | 1,848 | 527 | 13,051 | 9.3 | 0.195 | 0.150 | 0.154 | 0.181 | 0.177 | 5.4 |
| ½× | 3,611 | 1,054 | 25,370 | 18.3 | 0.375 | 0.292 | 0.288 | 0.360 | 0.396 | 10.8 |
| **1× (today)** | **7,034** | **2,108** | **48,361** | **35.1** | **0.805** | **0.577** | **0.585** | **0.700** | **0.732** | **20.8** |
| 2× | 14,066 | 4,216 | 96,722 | 70.1 | 1.752 | 1.280 | 1.277 | 1.499 | 1.769 | 41.5 |
| 4× | 28,130 | 8,432 | 193,444 | 140.2 | 3.472 | 2.702 | 2.898 | 3.396 | 3.411 | 83.0 |
| 8× | 56,258 | 16,864 | 386,888 | 280.4 | 7.483 | 5.727 | 6.641 | 7.567 | 7.381 | 166.0 |

- **Scaling is linear, slightly worse than linear at the top.** `show`, a single-bead lookup, costs 82 µs per bead at
  1× and 102 µs at 8×. Single-bead reads pay the full-store price.
- **A mutation costs about one replay plus 15–25%** for the stream rewrite and the projection rewrite.

### 2.3 Where a replay's time goes (1×)

| Component | Time |
| --- | --- |
| Full replay with a tiny result (`bead_stats`) | 0.63 s |
| … of which `prune_removed_flag_event_streams` (untyped re-parse of every line, every read) | **0.157 s (25%)** |
| Raw read of all 35 MB of stream bytes | **0.025 s (4%)** |
| CPython `json.loads` of every event (comparison) | 0.25 s |
| CPython `json.loads` of the whole projection / of active rows only | 0.11 s / **0.012 s** |
| `scandir` + `stat` of every stream (a cache fingerprint): 1× / 4× / 8× | **5.9 / 23 / 48 ms** |

Replay is CPU-bound, and the Rust reducer runs 2.5× slower than CPython's JSON parser on the same bytes. That leaves
a lot to gain from engineering alone, before any change to data layout.

### 2.4 CLI commands on the live store

`hyperfine`, 5 runs each:

| Command | Wall time | Count-dependent share |
| --- | --- | --- |
| `sase bead -h` (baseline) | 0.38 s | — |
| `ready` / `stats` / `search` (Rust fast path) | 1.08 / 1.10 / 1.15 s | ~0.6 s (one replay) |
| `list` | 1.92 s | ~0.8 s (replay plus Python conversion) |
| `read <id> -r …` (the audited agent read) | **5.69 s** | ~0.75 s |

cProfile of `sase bead read sase-1a0`:

| Step | Time |
| --- | --- |
| `append_artifact_link_outbox_entry` → `_reject_outbox_operation_collision` (`src/sase/sdd/_artifact_link_outbox_io.py:477`). It re-reads and re-canonicalizes all **11,436** outbox entries (three Rust calls each) to check one UUID for collision | **2.93 s** |
| Imports | ~1.2 s |
| `resolve_bead_creator_url` → `hosted_links.agent_url` | 0.94 s |
| `bead_show_issue_detail`: the full replay | 0.73 s |

**The single biggest cost on the agent read path is not bead count.** It is another append-only log that grows without
bound: the artifact-link outbox, 7.8 MB, with its oldest entry 27 days old. That cost appeared after the 09-24
research. The collision check landed 09-10 and audited bead reads landed 09-21. It is why real `read` latency rose
from 2.5–3.8 s to ~8 s.

Rust CLI handler (`bead_cli_execute`) on a 1× copy: show, list and ready 0.60 s; stats 0.56 s; **update 1.22 s and
close 1.16 s** (two replays plus a write; Python routing adds more on top).

### 2.5 Write path: Rust mutation plus git

Throwaway clone with a local bare remote; median of 6 runs at 1× and 4 at 4×. The 4× repo has no history, so its delta
base is the previous commit.

| Step | 1× (20.8 MB projection) | 4× (80 MB projection) |
| --- | --- | --- |
| Rust `append_note` (replay, append, full projection rewrite) | 0.69 s | 3.31 s |
| `git ls-files -m -o -d` | 0.03 | 0.02 |
| `git add` (re-hashes and zlibs the whole projection) | 0.30 | 1.18 |
| `git commit` | 0.14 | 0.26 |
| `git push` to a local bare repo (pack and delta of the new blob) | 0.70 | 3.05 |
| **Total, before Python overhead, extra replays and network** | **1.86 s** | **7.81 s** |

On top of this, the CLI adds 2–4 extra replays: 1.2–2.4 s today, 5.4–10.8 s at 4×.

### 2.6 Real-world latencies

**Agent tool calls.** Bash `sase bead <verb>` calls from Claude sessions in sase workspaces, 2026-09-01 → 10-05. Only
timing metadata was extracted. The harness baseline is about 2.3 s: `sase bead task-type` has p50 2.3 s.

| Verb | n | p50 | p90 |
| --- | --- | --- | --- |
| `show` | 190 | 5.5 s | 10.6 s |
| `read` | 141 | 7.0 s | 10.1 s |
| `read` (after 09-25) | 57 | **8.4 s** | 12.3 s |
| `note` / `update` / `create` / `close` (before 09-25) | 35 / 13 / 6 / 5 | **23–25 s** | 25–30 s |
| `note` (after the `sase-17q` guard fix) | 5 | ~11 s | 20 s |

**Background sync logs**, 09-29 → 10-06, n = 7,040:

- p50 2.4 s, p90 5.3 s, p99 11.4 s. Before the `sase-17q` fix, p90 was 23.8 s.
- 2% of syncs needed semantic conflict resolution, and 85 of those 152 involved `issues.jsonl`. It is the main
  conflict hotspot because every mutation rewrites it.

### 2.7 TUI Beads pane: superlinear

`load_project_beads` runs list, ready and blocked, which is three replays. `load_beads_snapshot` then groups phases
under epics with a nested scan, `for epic in epics: sorted(i for i in issues if PHASE and parent_id == epic.id)`
(`src/sase/ace/tui/widgets/artifacts/beads_data.py:141-154`). That is O(epics × issues).

| | 1× | 2× | 4× |
| --- | --- | --- | --- |
| `load_project_beads` (three replays plus `Issue` hydration) | 2.24 s | 4.83 s | 10.28 s |
| Phase grouping loop (a faithful replica of `beads_data.py:141-154`) | 0.56 s | 3.41 s | **37.9 s** |
| Epics × issues | 949 × 7,034 | 1,898 × 14,066 | 3,796 × 28,130 |
| Existing `store_mtime_key` (unused under `force=True`) | 0.031 s | 0.057 s | 0.114 s |

At 4×, one refresh (about 48 s) takes longer than the 10 s refresh interval. Result conversion holds the GIL, so the
UI would stall. This is an algorithmic bug, and a dict group-by fixes it in O(n).

### 2.8 What the beads repo's git history is made of

| Path | Objects | On disk | Share | Raw (uncompressed) |
| --- | --- | --- | --- | --- |
| `issues.jsonl` | 16,771 versions | **95.9 MB** | **74.4%** | **192.7 GB** |
| `events/` (the canonical data) | 23,870 | 12.5 MB | 9.7% | 0.48 GB |
| `pages/` | 18,695 | 8.7 MB | 6.8% | 0.07 GB |
| trees / commits | 61,774 / 20,449 | 7.5 / 3.0 MB | 8.2% | — |

The derived projection is three-quarters of the repo. The canonical events are a tenth. Every mutation also leaves a
~2–5 MB loose blob behind. That is the root cause of `sase-17r`, the ~22 s fresh-workspace clone, still `ready`.

Compression of all 35.1 MB of events:

| Method | Size | Ratio | Compress time |
| --- | --- | --- | --- |
| gzip-9 | 7.9 MB | 4.4× | — |
| zstd-3 | 7.4 MB | 4.8× | 0.12 s |
| zstd-19 | 5.7 MB | 6.1× | — |
| xz | 5.6 MB | 6.3× | — |

Git's zlib-plus-delta already captures most of that.

### 2.9 How much is archivable, and do cold beads stay cold?

A stream is "cold" when every live bead in it is closed and the newest `closed_at` is at least N days old:

| Closed ≥ | Streams | Beads (approx.) | Events | Bytes |
| --- | --- | --- | --- | --- |
| 0 d | 1,536 (73%) | 6,013 (85%) | 85% | 29.3 MB (83%) |
| 7 d | 1,477 | 5,718 (81%) | 78% | 27.2 MB (78%) |
| 14 d | 1,292 | 4,991 (71%) | 64% | 22.5 MB (64%) |
| 30 d | 1,042 | 4,318 (61%) | 55% | 19.0 MB (54%) |
| 60 d | 551 | 2,836 (40%) | 31% | 9.4 MB (27%) |
| 90 d | 197 | 1,369 (19%) | 12% | 3.3 MB (10%) |

- **Live dependencies rarely point into cold lineages.** One fully closed stream is referenced by a live bead's
  dependency at 0 d, and none at ≥ 7 d.
- **Cold beads still receive writes.** In the last 60 days, beads closed more than 60 days earlier received **970
  `link_added`, 385 `issue_updated` and 8 other events**: link backfills, reprojection repairs and reopen paths. **Any
  archive must stay writable.** A freeze-and-reject design would break existing machinery.

### 2.10 Simulated archive vs. simulated cache (1×, median of 5)

Hot sets keep every non-cold lineage plus its dependency closure, which slightly overstates them.

| Variant | Streams | `show` | `append_note` | Projection |
| --- | --- | --- | --- | --- |
| Today (everything hot) | 2,108 | 0.577 s | 0.700 s | 20.8 MB |
| Archive lineages closed ≥ 30 d | 1,221 | 0.359 s (1.6×) | 0.445 s | 11.0 MB |
| Archive lineages closed ≥ 7 d | 812 | 0.207 s (2.8×) | 0.262 s | 6.2 MB |
| Fingerprinted cache, warm, estimated: stat sweep + parse 588 active rows (§2.3) | 2,108 stat'd | **~0.02–0.05 s (12–30×)** | — | — |
| Cache **plus** sealed cold segments, estimated, 8× | ~800 stat'd | ~0.02–0.05 s, vs. 5.7 s today | — | — |

Archiving bounds the hot set at roughly the creation rate × the window, which is good. A cache makes the hot path
O(active + changed) and needs no data movement. Once a cache exists, physical archiving saves only the stat sweep on
reads: ~40 ms at 8×. Its remaining value is in git, the working tree and the projection.

---

## 3. Answer: does count matter, and by how much?

| Quantity | Today (7k) | 2× (14k, ~Jan 2027) | 4× (28k, ~mid-2027) | 8× (56k) |
| --- | --- | --- | --- | --- |
| One full replay (any read binding) | 0.58 s | 1.28 s | 2.70 s | 5.73 s |
| Count-dependent read cost per command (1–2 replays) | 0.6–1.2 s | 1.3–2.6 s | 2.7–5.4 s | 5.7–11.5 s |
| Count-dependent write cost per command: 3–5 replays incl. the locked load, projection rewrite, git add/commit/push packing (local) | ~3–4.5 s | ~6–9 s (est.) | **~16–21 s** | ~35–45 s (est.) |
| TUI Beads pane, per 10 s refresh while visible | 2.8 s | 8.2 s | **48 s** | not run (≫ 2 min, extrapolated) |
| Fingerprint stat sweep (what a cache would pay) | 6 ms | ~12 ms | 23 ms | 48 ms |

Other costs that grow with history, outside the bead store but on the bead path:

| Log | Size | Effect |
| --- | --- | --- |
| Artifact-link outbox | 11,437 entries | 2.9 s per audited read |
| `~/.sase/bead_push_logs/` | **125,957 files, 507 MB** | — |
| Touch index | 9.2 MB | Fully rewritten when anything changes |

**What does not matter much:** the number of *active* beads (588), raw I/O, the number of stream files (stat is cheap),
and network round-trips (fetch p50 0.49 s, push p50 0.57 s per `tui_git_ops.jsonl`).

---

## 4. Ways to compress or archive without permanent information loss

Lossless here means: **no event is ever edited or deleted**. Derived files (`issues.jsonl`, pages, caches) may be
dropped and regenerated, and git history is not rewritten.

| # | Option | What it does | Perf gain | Loss risk | Verdict |
| --- | --- | --- | --- | --- | --- |
| 1 | **Fingerprinted read cache (logical archive)** | Gitignored per-store cache, e.g. `beads.cache.sqlite` or a binary snapshot. One row per stream keyed by `(relpath, size, mtime_ns, inode)`; reduced issue rows with indexed `id`, `status`, `parent`. Re-reduce only changed streams. Same pattern as `touch_index.rs` and the goal ledger's `goals-hot.json` | 12–30× on reads; mutations load from cache | None. Derived, drop-and-rebuild on schema mismatch | **Do (core of the solution)** |
| 2 | **Live markers / hot index** | A tiny committed or derived set of non-closed lineages. Closed streams are never opened on hot reads. The goal ledger already does this: "settled goals' directories are never opened; the I/O probe proves it" | Hot reads O(active) | None | **Do, inside #1** |
| 3 | **Take `issues.jsonl` off the commit path** | Stop rewriting and committing it per mutation. Generate it on demand (`doctor --fix-projection` / export) or at sync. Or shard it into `active.jsonl` plus monthly closed shards, so a mutation rewrites ~2.4 MB | −0.7 s write, −0.3 s add, −most of push packing; ends the main conflict hotspot and 74% of git growth | None. It is a projection of events (the sidecar started with the event store already canonical) | **Do, after a consumer audit** (~25 Python modules reference it) |
| 4 | **Sealed cold segments (physical archive)** | Move fully closed, quiet lineages verbatim into `events/sealed/<YYYY-MM>/…`, with a sealed index and manifest checksums. New events for a sealed bead go into a fresh hot overlay stream, and the reducer merges by event order | 1.6–2.8× without a cache; bounds stat count, working tree and projection shards | Low *if* byte-preserving and parity-proven; medium implementation risk | **Later, behind a trigger** (§7 Phase 3) |
| 5 | **Snapshot/checkpoint compaction** | Store reduced state for sealed segments so cold reads skip replay | Small on top of #1 | None if derived; risk if it *replaces* events | Only as a derived artifact. Never replace events |
| 6 | **Compress cold data (zstd)** | 4.8× at zstd-3, 6.1× at zstd-19 | **None or negative for reads** (decompress plus parse). Git already zlibs about 4.4×. Compressed blobs defeat git delta and grep | None | **Don't, in-repo.** Fine for off-repo archive bundles |
| 7 | **Slim the event wire** | `event_id` is 13% of event bytes and redundant with other fields. `issue_updated` carries about 2.5% null padding | ~15% fewer bytes | Format migration | Not worth it alone |
| 8 | **Git hygiene without rewrites** | Byte-threshold repack (`sase-17r`); `--filter=blob:none` partial clones for workspace sidecars | Clone and first-use latency | None | Do repack now; evaluate partial clone |
| 9 | **History rewrite** (drop the old `issues.jsonl` versions) | Shrinks the pack by ~96 MB once | One-time clone gain | Breaks 47 clones and `refs/sase/recovery/` | **Don't.** Stop the growth (#3) instead. If ever needed, bundle the old history to an archive repo first |
| 10 | **Off-repo cold archive** (second sidecar or bundle) | Move sealed segments to a `beads-archive` repo or bundle | Smaller workspace clones | Cross-repo consistency, offline reads | Only if clone size becomes the complaint |

---

## 5. Critique of the plan

### What is right

- **The premise is real and growing.** Cost tracks history. 85% of events belong to fully closed lineages, and creation
  roughly doubled from July to September. Nothing in today's design gets cheaper over time.
- **A hot/cold split is the right end state.** SASE already chose it once, for the goal ledger (`decisions:goal-ledger`):
  O(unsettled) hot reads, immutable events, live markers. Its G1 benchmark showed hot-list p95 moving −6% from 25k to
  100k settled goals. Beads should reach the same property.
- **"Without losing information" is the correct constraint.** It rules out pruning or squashing events.

### Where I disagree

1. **Archive-first optimizes the smaller term.** At today's size, physical archiving gives 1.6–2.8× on the core
   replay. Each of the following delivers comparable or larger wins with no data movement:
   - removing prune-on-read: −25% of every replay;
   - deduplicating replays within a command: 2–5× per write;
   - fixing the TUI grouping: 10–70× on that path;
   - fixing the outbox check: −2.9 s per audited read;
   - a cache: 12–30×.
2. **"Compress" is a category error for speed.** Replay is CPU-bound, and reading all 35 MB takes 25 ms. Compression
   only adds decode work on the hot path, and git already compresses.
3. **Physical moves enlarge the correctness surface.**
   - Cold beads take about 23 events/day today.
   - The publication integrity guard ("do not drop or rewrite events already on the upstream") would see a move as a
     deletion.
   - A concurrent append in another workspace turns into a modify/delete rebase conflict.
   - Every read family (show, history, search, `list --status closed`, doctor, pages, touch index, conflict resolver,
     relocation) needs a cold path.

   Without a cache, each of those paths is new code that must stay correct forever.
4. **The plan targets canonical data, but most bytes and write cost are in derived data.** `issues.jsonl` is 74% of
   git history and the largest per-mutation write. It is also the top conflict file. Dropping it from the commit path
   is lossless by definition.
5. **It frames the problem as "number of beads".** The variable that matters is replays per command × history size.
   On the agent read path, the biggest growth term today is not the bead store at all.

### Prior work this plan should build on

`research:202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md` (2026-09-24) recommended
several of the same fixes. Their status now:

| Recommendation | Status |
| --- | --- |
| Fix the integrity guard (`sase-17q`) | Done; sync p90 23.8 → 5.3 s |
| Repack sidecar clones (`sase-17r`) | Still `ready` |
| Disposable fingerprinted read cache in `sase_core` | Not started. No cache code in `crates/sase_core/src/bead` |
| Drop the TUI `force=True` reload | Not done (`beads_pane.py:149-150` unchanged) |
| Move prune out of the read path | Not done (`jsonl.rs:395`) |
| Stop the per-mutation `issues.jsonl` rewrite | Not done |

The present plan risks building an archive on top of an un-indexed, re-replaying read path. That is the most
expensive way to get the smallest gain.

---

## 6. Requirement adjustments (explicit)

- **A1 — Re-target the metric.** Replace "reduce the number of beads" with: **hot-path bead latency must be independent
  of closed history.** Acceptance, modeled on the goal ledger's G1 criterion:
  - on synthetic 1× → 8× corpora, `ready`, `list`, `read` and mutation p95 move by less than 10%;
  - the TUI Beads pane refresh stays under 100 ms when nothing changed.
- **A2 — Drop compression as a performance lever.** Keep it only for storage or clone size, and only outside the git
  working tree.
- **A3 — Archive means logical first.** "Archived" is a property computed by the cache or hot index (closed and quiet).
  Physical sealing is optional, later and triggered. When it happens it must be:
  - byte-preserving (events relocated verbatim, checksummed);
  - write-tolerant (thaw by overlay stream; sealed files are never edited);
  - parity-proven (replay of hot + sealed == replay before sealing, checked before commit and by `doctor`);
  - performed by one host-owned writer under the store lock.
- **A4 — Widen scope to derived artifacts and adjacent unbounded logs on the bead path.** That means `issues.jsonl` and
  pages, the artifact-link outbox collision scan (2.9 s per audited read), the touch-index full rewrite, and
  `bead_push_logs` retention (126k files).
- **A5 — Lossless is defined precisely.** Events are never mutated or deleted. Derived files may be dropped or
  regenerated. Git history is never rewritten.
- **A6 — Archived beads remain addressable and writable.** Shorthand resolution, dependency checks, ID allocation, show
  and history must keep working on sealed beads without opening them, through the index, or by opening exactly one
  segment.
- **A7 — Benchmark on a scaled corpus in CI.** `bead-perf-smoke` must exercise a ≥ 4× synthetic store with a remote.
  The length-preserving prefix-copy method in Appendix A builds one in seconds.

---

## 7. Recommended solution

### Phase 0 — Stop paying for waste (small, independent changes; no format change)

1. **sase-core: one parse per replay.** Move `prune_removed_flag_event_streams` out of `read_event_store`, into a
   one-shot migration or `doctor` (−25%). It also mutates the store during a lockless read. Drop the
   `validated_event_streams` deep copy and validate once. Target: uncached replay 0.63 s → ≤ 0.25 s, which is CPython
   parity.
2. **One replay per command.**
   - Route targets by stream-path or ID existence instead of `list_issues` (`src/sase/bead/operation_context.py`).
   - Pass the resolved context into the mutation.
   - Memoize the loaded store per process, keyed by the stream fingerprint.

   Writes drop from 3–5 replays to 1.
3. **TUI Beads pane.**
   - Group phases by `parent_id` in one dict pass, not O(epics × issues).
   - Drop `force=True` from `on_refresh`, so the existing mtime key decides.
   - Add one binding that returns list, ready and blocked from a single replay.

   This is the fix that prevents a ~48 s refresh at 4×.
4. **Artifact-link outbox.** Make the collision check O(1) in outbox size: substring-precheck the UUID operation ID
   before parsing, or keep an ID index. Also drain or compact the queue. This removes ~2.9 s from every audited read
   (beads, artifacts, memory). It is outside the bead store but on its read path.
5. **Repack** (`sase-17r`), and add retention for `~/.sase/bead_push_logs/`.

### Phase 1 — The logical archive: a disposable, fingerprinted read model in `sase_core`

Per the Rust-core boundary, this lives in `sase-core` with a thin Python binding, and sase's `sase-core-revision.txt`
pin moves with it.

- **Substrate.** Gitignored, never authoritative, dropped and rebuilt on any version mismatch. Never `beads.db`, which
  is the mutation lock. The agent-artifact SQLite index (`agent_scan/index/storage.rs`) and `touch_index.rs` are the
  in-repo precedents.
- **Read algorithm.**
  1. `scandir` + `stat` every stream: 6 ms today, 48 ms at 8×.
  2. Re-reduce only new or changed streams.
  3. Run the cheap global post-pass: removal cascades, dependency targets, external refs.
- **Tiering.**
  - `ready`, `blocked` and default `list` read only active rows (588 today) plus a closed-ID status index.
  - `show` and `read` are indexed point lookups.
  - Search and closed listings read cached rows and never re-parse.

  This *is* the hot/cold archive, delivered with zero data movement.
- **Mutations** load from the cache, append the event byte-for-byte as today, and update touched rows write-through
  under the existing flock.
- **Correctness.**
  - Parity test (cached == full replay) over randomized mutation sequences on the scaled corpus.
  - `sase bead doctor --verify-cache`.
  - Close the lockless-read races: trust the directory listing over `manifest.stream_count`, and repair the manifest
    under the lock.

### Phase 2 — Projection off the commit path

- Stop the per-mutation rewrite and commit of `issues.jsonl`. Regenerate it on demand or at sync. Or, if a consumer
  audit finds an external reader that must have it, shard it as `issues/active.jsonl` plus `issues/closed-<YYYY-MM>.jsonl`.
  Then a mutation rewrites only the shard it touches.
- Move every mtime-keyed consumer (TUI keys, reconciliation auto-commit, conflict resolver paths) to the store
  fingerprint.
- Effect: removes the largest O(N) write, ~74% of future git growth, the top rebase-conflict file and the loose-object
  bloat behind `sase-17r`.

### Phase 3 — Sealed cold segments (physical archive), only when a trigger fires

**Triggers:** any of

- more than 10k hot stream files;
- stat sweep above 50 ms;
- `pages/` plus `events/` working tree above ~250 MB;
- clone or first-use latency complaints that partial clones cannot fix.

**Design:**

- **Seal criterion.** A lineage qualifies when it is fully closed ≥ 30 days, has no non-closed dependents, no live
  claims and no pending outbox entries. At 30 days that is ~55% of today's events (§2.9).
- **Operation.** `sase bead archive seal --before <YYYY-MM>` runs as a host-owned scheduler job, single writer, under
  the store lock. It relocates stream files verbatim (`git mv`) to `events/sealed/<YYYY-MM>/<stream>.jsonl` and
  writes:
  - `events/sealed/index.jsonl`: id → segment, status, title, parent, `closed_at`, resolution. It serves resolution,
    dependencies and ID allocation.
  - Manifest entries with per-segment event counts and SHA-256.

  Keep one file per stream rather than concatenating. That preserves git delta, greppability and cheap single-bead
  opens.
- **Thaw by overlay.** A new event for a sealed bead creates `events/streams/<stream>.jsonl` holding only the new
  events. The reducer merges sealed and hot events, deduplicated by `event_id`, so a concurrent seal-vs-append
  modify/delete conflict resolves mechanically. Sealed files are never edited. `unseal` exists but is never required.
- **Guards.**
  - The integrity guard and conflict resolver treat sealed relocation as event-set-preserving (compare by `event_id`
    across hot + sealed).
  - Each seal commit carries a parity proof.
  - `doctor --verify-sealed`.
- **Pages** for sealed lineages may move to `pages/sealed/<YYYY-MM>/` in the same commit. Optional.
- **No in-repo compression.** If repo size ever matters, ship sealed months as zstd bundles to an off-repo archive.
  That is a storage decision, not a speed one.

### Expected results

All columns after "Today" are estimates derived from §2 measurements.

| Operation | Today, 1× | After Phase 0 | After Phase 1 | After Phases 1–2 at 8× |
| --- | --- | --- | --- | --- |
| Core read (`show` / `ready` binding) | 0.58 s | ~0.2–0.3 s | **~20–50 ms** | ~50–100 ms (Phase 3 brings it back to ~20–50 ms) |
| `sase bead read` (agent) | 5.7 s (~8 s real p50) | ~2.5–3 s | ~2–2.5 s, bounded by imports (~1 s) and creator-URL resolution (~0.8 s), neither count-related | ~2–2.5 s (lower only if imports and URL lookup are also fixed) |
| Mutation, local part | ~3–4.5 s count-dependent | ~1.2–1.8 s | ~0.6–1.0 s | **~0.2–0.4 s + network**, independent of history |
| TUI Beads pane | 2.8 s every 10 s | ~0.6 s, only on change | tens of ms, on change | tens of ms |
| Git growth per mutation | 2–5 MB loose blob | same | same | **one stream's delta** |

### What would change this recommendation

- **If Phase 1 parity cannot be achieved** (for example, global reduction rules make per-stream caching unsound),
  sealed segments plus a hot-only replay (Phase 3) become the primary lever. That would deliver the measured 1.6–2.8×
  plus bounded growth.
- **If an external consumer truly requires a single tracked `issues.jsonl`**, shard it (Phase 2 alternative) rather
  than keep the full rewrite.
- **If you want physical archiving mainly for repo or clone size**, do Phase 2 first. It stops 74% of the growth. Then
  decide between partial clones and an off-repo archive.

---

## 8. Follow-ups

These are proposed for the lead's synthesis. Each needs a duplicate check (`/sase_new_task`) before filing.

- The O(outbox) collision scan on every audited read: `src/sase/sdd/_artifact_link_outbox_io.py:477`, 2.9 s at 11.4k
  entries.
- The TUI Beads pane O(epics × issues) phase grouping plus the forced refresh: `beads_data.py:141-154`,
  `beads_pane.py:149-150`.
- `prune_removed_flag_event_streams` on every read (`crates/sase_core/src/bead/jsonl.rs:395`).
- The read cache (Phase 1), projection off the commit path (Phase 2), and the scaled-corpus perf smoke test (A7).
- Retention for `~/.sase/bead_push_logs/` (126k files, 507 MB).

---

## Appendix A — Methodology and reproducibility

- **Scaled corpora.**
  - *Subsets:* a seeded shuffle of stream files. Each pick adds the transitive closure of streams referenced by
    `depends_on_id`, `parent_id` or `issue_id`, including child-specific streams such as `sase-xe.16.jsonl`, so the
    reducer's existence checks pass.
  - *Multiples:* the real store plus 1, 3 or 7 copies with `sase-` rewritten to `sasb-`, `sasc-`, …. Prefixes are
    length-preserving, so the 240-character link-description limit and every field size are unchanged. ID prefixes are
    not validated on load. Rewriting `sase-org` inside the two `external_ref` values kept them unique.
  - The manifest `stream_count` was regenerated for each corpus.
- **Core timings:** `sase_core_rs` bindings called in-process, `time.perf_counter`, median of 5 (3–4 for git runs).
  Mutations ran against `/tmp` copies only. `bead_cli_execute` was used for the Rust CLI handler path.
- **Git timings:** a `--no-local` clone of the beads repo plus a bare local remote. Each run: binding mutation, then
  `git ls-files`, `git add -- issues.jsonl <stream>`, `git commit`, `git push`. The 4× corpus was committed into a fresh
  repo first.
- **CLI timings:** `hyperfine -N --warmup 1 --runs 5` on the live store, read verbs only. `read` used a real audit
  reason. cProfile of `read` ran through a small `SystemExit`-catching wrapper.
- **Real-world latencies:**
  - Claude transcripts under `~/.claude/projects/*sase-org-sase-sase-*`. Only Bash `sase bead <verb>` tool-use and
    tool-result timestamps were read, for calls before 2026-10-06, so no current-swarm session was included.
  - `~/.sase/bead_push_logs/sync-*.log` since 09-29 (n = 7,040).
  - `~/.sase/logs/tui_git_ops.jsonl`.
- **Archivability:** computed from `issues.jsonl` status and `closed_at`, plus per-stream event timestamps.
- **Caveats:**
  - The host was loaded (load average 11–18 on 64 cores). Absolute numbers carry ±10–15% noise; ratios are stable.
  - Synthetic multiples copy today's per-bead event mix. A future mix with heavier notes or epics would scale worse.
  - The TUI loop figure is a faithful replica of the grouping code, not a full pane load.
  - Transcript durations include ~2 s of harness overhead.

## Appendix B — Code references

| Area | Location |
| --- | --- |
| Read path | `crates/sase_core/src/bead/jsonl.rs:392-437` (prune at `:395`); `events/reduction.rs:29, 262-266`; `read.rs:66-92`; `read.rs:933` (shorthand suffix scan over all issues) |
| Write path | `mutation/store.rs:273-333` (load, save, `write_issues_jsonl`); `jsonl.rs:103-125` (full projection export); `jsonl.rs:446` (`write_event_store_changed`) |
| Python lane | `src/sase/main/bead_fast_path.py:69-170, 514-588`; `src/sase/bead/cli_common.py:266-347`; `src/sase/bead/operation_context.py` |
| TUI | `src/sase/ace/tui/widgets/artifacts/beads_data_sources.py:24-33`; `beads_data.py:89, 141-154`; `beads_pane.py:149-150` |
| Outbox | `src/sase/sdd/_artifact_link_outbox_io.py:86-130, 422-490` |
| Goal-ledger precedent | `crates/sase_core/src/goal/ledger/{layout,read,projection}.rs` (live markers, O(unsettled) read, stat-signature `goals-hot.json`) |
| Existing incremental cache precedent | `crates/sase_core/src/bead/touch_index.rs` (per-stream mtime/size signatures) |
