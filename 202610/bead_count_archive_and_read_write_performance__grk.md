---
create_time: 2026-10-06
updated_time: 2026-10-06
status: draft
tags:
  [
    research_swarm,
    beads,
    performance,
    storage,
    archive,
    sase-core,
    event-sourcing,
  ]
---

# Does bead count matter for read/write performance, and should we archive old beads?

**Question.** Does the number of beads that exist for a SASE project matter for
bead read/write performance? If so, by how much? What are some ways we can
compress and/or archive old beads to improve performance without losing any
information permanently? Critique the plan. Recommend a solution.

**Researcher.** grk (`research.3u.grk`). Independent report. I did not locate,
open, read, or otherwise consult peer reports from this swarm
(`research.3u.cdx`, `research.3u.cld`, `research.3u.mus`, `research.3u.gem`).

**Method.** Code and docs in sase and sase-core; the live sase project beads
sidecar (HEAD `2b55fc23b`, 2026-10-06); Rust-binding and CLI timings; a
same-filesystem subset/snapshot bench that never mutated the live store;
publication sync logs under `~/.sase/bead_push_logs`; prior research
`research:202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md`
and `research:202605/greenfield_bead_storage_architecture.md`; decision
`decisions:goal-ledger`.

## Bottom line

**Yes, bead count matters, but it is the wrong first knob.** Every
`sase bead` store operation in sase-core still **opens and reduces every event
stream in the project**, including closed beads, tombstoned streams, and the
closed children of live epics. On today's sase store that is **7,034 beads,
2,108 streams, 48,357 events, 35 MB of streams, 21 MB `issues.jsonl`**. The
Rust load is **~600 ms** whether the caller asked for one bead or all of them.

That 600 ms is real, and it is growing. Twelve days ago the same store had
5,979 beads and a ~400–550 ms replay. It will keep growing because **91.6% of
beads are closed** and they still sit on the hot path.

Archiving or gzipping old bead *bodies* is a weak first move:

1. Agent-facing `sase bead read` is **5.1–7.6 s**. The store is ~12% of that.
   The rest is Python (inventory, name registry, attachment fetch, artifact-link
   neighborhood, audited-read recording, pager). Shrinking the store will not
   make `read` feel fast.
2. Streams are **one file per root bead**, not per bead. 481 closed phases live
   inside live epic streams. You cannot archive "closed beads" at file
   granularity without splitting streams or leaving those 481 in the hot set.
3. Live beads still depend on closed ones. A live-only reduce **fails** until
   the missing closed target is restored (`sase-1d5` was the one extra root
   today's live set needed).
4. The git disaster is not "too many old bead files." It is **rewriting and
   committing the 21 MB `issues.jsonl` projection on every mutation** (~330
   commits/day, 4,750 `issues.jsonl` touches in 14 days, 20,439 commits in the
   beads sidecar). The hidden host clone currently holds **1.75 GiB of loose
   objects** plus a **1.34 GiB pack**. The workspace clone of the same history
   packs to **102 MB**.
5. gzip of canonical JSONL would **slow** the hot parse. Git already compresses
   history. The working-tree files need to stay plain text.

**Do this instead:** treat closed beads like the goal ledger treats settled
goals — **hot path O(live) or O(changed), cold path complete** — and stop
putting the generated projection on the per-mutation git path. A disposable
fingerprint-validated read-model cache in `sase-core` is the first performance
fix. A closed-root cold tier is a later, optional working-tree shrink, not the
identity/archive story. Do not build a bead daemon; that recommendation from
2026-09-24 still holds, and both SASE (`sase-3e`) and upstream Beads already
paid for a daemon and deleted it.

## 1. What the store actually is

Canonical state is append-only event streams under `events/streams/<id>.jsonl`,
one stream per **root** bead (docs/beads.md, sase-core `bead/jsonl.rs`).
`issues.jsonl` is a generated compatibility projection. `beads.db` is **not** a
SQLite cache on the production path; it is the mutation flock
(`BEAD_MUTATION_LOCK_FILENAME` in `mutation/store.rs`). Docs still mention a
"SQLite compatibility cache"; that is stale. Python `sase.bead.db` remains for
legacy/test helpers.

Every read and every mutation goes through a full reduce:

```66:86:sase/repos/linked/sase-core/crates/sase_core/src/bead/read.rs
pub fn read_store_issues(
    beads_dir: &Path,
) -> Result<Vec<IssueWire>, BeadError> {
    // ...
    if event_store_present(beads_dir) {
        return read_event_store_issues(beads_dir);
    }
    read_legacy_jsonl_issues(beads_dir)
}

pub fn read_event_store_issues(
    beads_dir: &Path,
) -> Result<Vec<IssueWire>, BeadError> {
    let (_manifest, streams) = read_event_store(beads_dir)?;
    reduce_event_streams(&streams)
}
```

`show_issue`, `list_issues`, `stats`, `ready_issues`, `blocked_issues`,
`resolve_issue_id`, and `MutableStore::load` all call that. `read_event_store`
also runs `prune_removed_flag_event_streams` **on the read path**, which parses
every stream untyped (and can delete files) before the typed parse. Writes then
append one stream and **rewrite all of `issues.jsonl`**.

The TUI Artifacts → Beads pane makes it worse: `load_project_beads` calls
`list_issues`, then `ready`, then `blocked` — **three full reduces per
refresh** — and `on_refresh` still passes `force=True`.

## 2. Live corpus (sase project, 2026-10-06)

| Quantity | Value |
|---|---|
| Beads | 7,034 |
| Closed / live | 6,444 / 590 (91.6% closed) |
| Status mix | closed 6444, ready 393, in_progress 169, open 27, snoozed 1 |
| Types | phase 4976, task 1109, plan 949 (flags 66) |
| Event stream files | 2,108 |
| Issue roots (stream keys that still have a bead) | 1,851 |
| Extra streams (relocated/tombstoned stems, not an issue root) | 257 files, 5.6 MB |
| Events | 48,357 (median 12/stream, p99 ~122, max 239) |
| Stream bytes | 35.0 MB (gzip/tar 8.6 MB) |
| `issues.jsonl` | 20.8 MB, 7,034 lines (gzip -9: 5.6 MB) |
| Closed-row share of `issues.jsonl` | ~18.3 MB (88.3%) |
| Live-row share of `issues.jsonl` | ~2.4 MB (11.7%) |
| Notes text | ~11.0 MB, of which ~10.3 MB is on closed beads |
| Pages | 5,892 Markdown files, 18.7 MB (gzip/tar 4.4 MB); 5,752 closed / 139 live |
| Beads sidecar commits | 20,439 |
| Commits last 14 days | ~5,656 (~330/day) |
| `issues.jsonl` touches last 14 days | 4,750 |
| Workspace clone | 0 loose, pack **101.6 MiB** |
| Hidden host clone `~/.sase/projects/gh_sase-org__sase/repos/beads` | **2,180 loose / 1.75 GiB** + pack **1.34 GiB** |

Root-level closedness (the only granularity an archive can use without splitting
streams):

| Root class | Roots | Beads | Stream bytes | Events |
|---|---|---|---|---|
| Fully closed | 1,364 (73.7%) | 5,963 closed | 24.6 MB (83.6%) | 34,750 (85.4%) |
| Fully live | 426 | — | — | — |
| Mixed (live + closed descendants) | 61 | 481 closed still in live files | (in live-root bytes) | (in live-root events) |
| Live roots total | 487 | 590 live + 481 closed | 4.8 MB (16.4%) | 5,921 (14.6%) |

Growth since the 2026-09-24 speedup research: **+1,055 beads (+17.6%), +393
streams (+23%), +4.1 MB `issues.jsonl` (+24%)** in twelve days. Net ~88
beads/day. At that clip the store is 10k beads in about five weeks.

## 3. How much does count cost, measured

### 3.1 Rust store load (no CLI)

`bead_stats` / `bead_show` / `bead_ready` / `bead_history` against the live
store, via `sase_core_rs`:

| Call | min |
|---|---|
| `bead_stats` | **597 ms** |
| `bead_show sase-j0` (one in-progress bead) | **599 ms** |
| `bead_history sase-j0` | **591 ms** |
| `bead_ready` | **594 ms** |
| `bead_list in_progress` (169 rows) | **608 ms** |
| `bead_search "latency"` | **646 ms** |
| `bead_list` all 7,034 | **723 ms** |
| `bead_list closed` | **738 ms** |
| TUI `list + ready + blocked` | **1,959–1,983 ms** |

Show-one and stats-all are the same. That is the definition of "count matters":
the hot path is **O(all history)**, not O(the bead you named).

`scandir`+`stat` of 2,108 streams is **11 ms**. A fingerprint check is cheap.
The 600 ms is parse + validate + reduce.

### 3.2 CLI wall time

| Command | min |
|---|---|
| `sase bead stats` / `ready` / `search` (Rust fast path) | **1.06–1.14 s** |
| `sase bead list` / `list --status in_progress` (Python slow path) | **1.84–1.92 s** |
| `sase bead show` (refused for agents; still ~1.5 s to error) | 1.53 s |
| `sase bead read <id>` smallest bead (`sase-8n`, 449 B closed) | **5.13 s** |
| `sase bead read` largest bead (`sase-xs`, 117 KB closed) | **5.64 s** |
| `sase bead read sase-j0` | **7.57–8.82 s** |
| `sase bead history sase-j0` | **4.57 s** |
| `sase bead doctor` | **11.6 s** |

Fast-path CLI ≈ 0.45 s process/import + 0.60 s store. Slow-path list ≈ 1.3 s
Python + 0.60 s store (matches the September finding that `list`/`read`/`show`
are excluded from `bead_fast_path.py`). Audited `read` is a different animal:
payload size barely moves the needle (5.1 s vs 5.6 s from 449 B to 117 KB), so
**~5 s is fixed overhead outside the store** — `repo_inventory_session`,
`name_registry_load_session`, attachment fetch, artifact-link neighborhood,
`record_bead_reads`, pager. Archiving beads cannot fix that.

### 3.3 Writes and publication

`sase-17q` (closed 2026-09-24) removed the ~20 s integrity-guard walk (one `git
show` per stream × two revisions). The guard now `ls-tree`s names and
`cat-file --batch`es only changed streams. Publication of the sase beads
sidecar in the last ~3,000 sync logs:

| | duration |
|---|---|
| n | 1,965 completed runs |
| min / p50 / p90 / p99 / max | 1.19 s / **2.60 s** / **5.16 s** / 11.3 s / 109 s |
| latest 10 | 2.2–2.8 s |

A typical mutation commit is one appended event line plus a two-line
`issues.jsonl` diff **of a 20.8 MB blob**. `git add` still hashes the whole
file. That is why clone/gc, not the Rust reducer, dominates write pain after
17q.

`sase-17r` added byte-threshold `git gc` (256 MiB loose) on sidecar auto-sync.
It is **not winning** on the hidden clone: 1.75 GiB loose remains. GC is only
invoked from `sase_chop_sidecar_auto_sync`, not after each mutation, and the
hidden clone is the machine write lane (`decisions:machine-link-writes-off-primary`).

### 3.4 Scaling curve (synthetic, same reducer, live issues as snapshots)

Evenly slicing *real* streams fails: `dependency_added target does not exist`.
That is a finding, not a bench bug. Snapshot stores (one `issue_created` per
bead, deps stripped) and jsonl-only fallback:

| Store | streams / issues | min `bead_stats` |
|---|---|---|
| Snapshot 200 issues | 37 / 200 | 3.4 ms |
| Snapshot 500 | 75 / 500 | 8.7 ms |
| Snapshot 1,000 | 131 / 1,000 | 17.3 ms |
| Snapshot 2,000 | 302 / 2,000 | 40.0 ms |
| Snapshot 4,000 | 927 / 4,000 | 122 ms |
| Snapshot all 7,034 (history dropped, current rows kept) | 1,851 / 7,034 | **236 ms** |
| Live issues + ancestors, snapshot | 487 / 591 | **28 ms** |
| Live-root **full history** + 1 closed dep-target | 488 / 869 (338 closed remain) | **88 ms** |
| jsonl-only 500 | — / 500 | 4.0 ms |
| jsonl-only 2,000 | — / 2,000 | 19.6 ms |
| jsonl-only 7,034 (no event store) | — / 7,034 | **112 ms** |
| Live event store (today) | 2,108 / 7,034 | **597 ms** |

Observations:

- Full-history replay is **~linear in event bytes**, not in live beads.
  14.6% of events (live roots + one dep) → 88/597 = **14.7% of time** (6.8×).
- Compacting every stream to a current-state snapshot, still loading all
  7,034 beads, is **2.5×** (236 vs 597 ms). History is expensive; closed
  *count* is also expensive.
- Reading the generated `issues.jsonl` is **5.3× faster** than reducing
  events (112 vs 597 ms) and is already on disk. The production path ignores
  it whenever `events/` exists.
- A live-only snapshot is **21×** (28 vs 597 ms). That is the goal-ledger
  shape: settled history is never opened.

Rough extrapolation of **uncached full-history replay**, assuming today's
bytes-per-bead:

| Beads | Rust load | Fast-path CLI | TUI triple load |
|---|---|---|---|
| 7,034 (today) | 0.60 s | 1.07 s | 2.0 s |
| 10,000 (~5 weeks) | ~0.85 s | ~1.3 s | ~2.6 s |
| 15,000 | ~1.3 s | ~1.7 s | ~3.9 s |
| 30,000 | ~2.5 s | ~3.0 s | ~7.6 s |

These are the uncached numbers. They are the ones every command pays today.

## 4. Ways to compress or archive without losing information

"Without losing information permanently" is the right constraint. It rules out
deleting closed beads, rewriting history, or making `sase bead read sase-old`
fail. It does **not** require every byte to live in the hot working tree.

### 4.1 What must remain reachable

Closed beads are still used for:

- `sase bead read` / `history` / `open` (reopen)
- `search`, `doctor`, duplicate checks (`/sase_new_task`)
- dependency and parent graphs (live work cites closed work; measured)
- `+1` reopen windows, close-history, flag beads
- `@bead:` pages and artifact links
- TUI and mobile pickers that list or filter closed

A cold tier that drops identity, title, or dependency stubs will break those.
A cold tier that drops **event bodies** from the working tree is fine if git
still has them and a thaw path exists.

### 4.2 Options, ranked

**A. Fingerprint-validated read-model cache in `sase-core` (do this first).**
Gitignored `beads.cache.sqlite` (never `beads.db`, that is the lock). One row
per issue, keyed by per-stream `(path, size, mtime_ns, inode)` like
`touch_index.rs` already does. Readers `stat` (~11 ms), re-reduce only
changed streams, serve list/show/stats/search from the projection. Cache is
never authoritative; mismatch rebuilds. This is the 2026-09-24 speedup
research's Phase 1, and the 2026-05-13 greenfield architecture's "local query
store." It does not archive anything. It makes count cheap.

Expected: uncached replay stays for the first miss; warm reads tens of
milliseconds; mutations load from cache; `issues.jsonl` rewrite can leave the
per-mutation path.

**B. Stop committing `issues.jsonl` on every mutation (do this in the same
epic).** Events are the source of truth. The 21 MB projection is a view. Git
currently treats it as the collaboration surface: 4,750 rewrites in 14 days,
gigabytes of loose zlib copies of the same file. Generate it locally for
legacy consumers (`doctor --fix-projection`, export, tests). Commit it on a
cadence, or not at all. **This is the archive that actually shrinks git**,
and it loses no information — the events already have it. Fresh-clone
bootstrap already knows how to rebuild the projection.

**C. Point reads without a full reduce.** `show`/`read`/`history` of
`sase-ab.3` only needs `events/streams/sase-ab.jsonl` plus an ID→root index.
ID resolution today loads everyone so shorthand (`ab`, `ab.3`) can detect
ambiguity. Keep a small ID catalog (id, root, status, title) for that; do not
open 2,108 files.

**D. Closed-root cold tier (real archive, later).** Move fully-closed root
streams that are **not** dependency targets of live beads to
`events/cold/<id>.jsonl` or a companion git history (orphan branch, separate
pack, or `git archive` bundle in the same repo). Hot reduce skips `cold/`.
Thaw on `read`/`history`/`open`/`search --all`. Keep a catalog row so IDs
never 404. Today's live set needed **one** extra closed root (`sase-1d5`) to
satisfy deps; 1,364 fully-closed roots are candidates, minus a small dep
closure. Measured win of the hot set: **88 ms vs 597 ms** (and 338 closed
beads still remain inside mixed live epics).

Do **not** gzip those cold files if the thaw path is a hot read. Git pack is
the compressor. A `.jsonl.zst` cold tier is acceptable only behind an explicit
thaw that copies a plain stream back.

**E. Event compaction of closed roots.** Replace a 239-event closed stream
with one `issue_created` snapshot (current reduced state) in HEAD; leave the
old bytes in git so `bead history --from-git` can replay. Snapshot-all was
236 ms vs 597 ms. Compacting only closed roots would land between the 88 ms
live-history figure and 236 ms. History UX has to change: HEAD is a snapshot,
full log is `git log -p` / `bead history --full`. That is information
preserving if the recovery command is real and tested.

**F. Drop closed pages from HEAD.** 5,752 of 5,892 pages are closed (17.8 MB
of 18.7 MB). Pages are generated projections (`sase bead pages refresh`).
Omitting closed pages from the current tree is not data loss if they can be
rebuilt from events. This shrinks checkout inodes and clone time; it does not
speed `bead_stats`.

**G. Prune extra streams.** 257 stream files (5.6 MB) are not issue roots —
relocated dotted IDs and tombstones. They are still parsed on every read.
Doctor/repair should drop or fold them. Cheap, low-risk, small win (~16% of
stream bytes in the extra set; not all of the 600 ms, but real).

**H. gzip/zstd the working-tree JSONL.** Reject as a hot-path strategy.
gzip -9 of `issues.jsonl` is 5.6 MB vs 20.8 MB, but every command would
decompress 21 MB of JSON anyway, and git-portable review dies. Git pack
already stores history compressed; the workspace clone is 102 MB for 20k
commits of 21 MB files.

**I. A bead daemon / RPC.** Reject as the performance design. September
research: after a cache, a daemon saves ~10–30 ms per read and ~0 ms per
write. SASE deleted `sase-3e` (−40k lines, 2026-05-14). Upstream Beads
removed its daemon in v0.50.0 (~19.7k lines). A cache-warmer *service proc*
that only calls the same `sase_core` refresh is the most that is justified,
and only if cold-after-sync remains slow.

**J. Copy the goal-ledger pattern.** `decisions:goal-ledger`: immutable
events plus live markers; **hot reads O(unsettled); settled files are never
opened**. G1: hot-list p95 moved −6% from 25k to 100k settled goals. Beads
already have the event half. They are missing the marker/hot-set half. This
is the in-tree proof that "archive" can mean "do not open settled files,"
not "invent a new product."

## 5. Critique of the plan

The plan as asked: *count is probably the problem; compress and/or archive old
beads so reads and writes get faster without losing information.*

**What is right.** Count is on the hot path. Closed beads are 92% of the
corpus and 84% of event bytes. Something that keeps closed history out of
every `stats`/`list`/`show`/`save` will win, and the win is large (6–21× on
the reducer, measured). "No permanent loss" is the correct invariant.

**What is wrong, or too small.**

1. **The question frames archive/compression as the solution.** The bottleneck
   is *algorithmic* (full reduce, full projection rewrite), not *density*.
   gzip fights the git-portable design. Archive-without-an-index breaks deps
   and search. The greenfield note already said this in May: events + SQLite
   projection + generated JSONL. Five months later the reducer still walks
   everything and JSONL is still the file git hates.

2. **Agent `read` will not improve much.** 5–8 s, ~0.6 s of which is the
   store. Fixing bead count to save 0.5 s on an 8 s command is the wrong
   epic if the user-visible pain is `sase bead read`. That pain is Python
   sessions, artifact-link recording, and the slow path. Lazy imports and a
   Rust fast path for `read`/`show`/`list` are in the September Phase 0 list
   and still open (`bead_fast_path.py` still excludes those verbs).

3. **Archive-at-bead granularity is incompatible with stream-per-root.**
   Mixed epics trap 481 closed beads in live files. Any design that says
   "closed ⇒ cold" without a split or a stub will either strand those beads
   on the hot path (fine) or split streams (a storage-format change, not a
   GC job).

4. **Live→closed dependencies are not hypothetical.** Live-only reduce
   failed on `sase-1d5`. Closure added one stream and then succeeded. An
   archive job that does not compute dep closure will corrupt the hot store.

5. **Git bloat is the projection, not the old events.** Old streams are
   append-only and git-friendly. `issues.jsonl` is a 21 MB blob rewritten
   ~330 times/day. Compressing beads does not stop that. Stopping the
   rewrite does. The hidden clone's 1.75 GiB loose objects are that blob
   escaping `gc.auto`'s count threshold — the bug `sase-17r` described,
   still present.

6. **A second store (archive sidecar, compressed pack, daemon) is a new
   consistency protocol.** Beads already have events, projection, pages,
   sqlite lockfile, touch index, and a hidden clone. Adding an archive
   repo before the cache means doctor, merge, clone, and every ID lookup
   grow a new miss path. `decisions:corpus-before-mechanism` is satisfied
   — the corpus is huge — but the mechanism that corpus wants is a
   **projection cache**, which the greenfield design already named.

7. **TUI pays 2 s × every refresh** because it reduces three times and
   forces reload. Archive would make each reduce faster; one snapshot per
   tick would make two of them vanish. Do both, but the one-line TUI fix
   is cheaper.

**Would I take a different approach?** Yes. I would not start with
"archive old beads." I would start with "stop paying O(history) for
O(1) questions," the way goals already do, and "stop committing a
generated 21 MB file." Archive of closed-root streams is a working-tree
optimization after those two, with a catalog and a thaw. Compression of
canonical JSONL is not on the list.

## 6. Adjusted requirements

Call-outs. These replace or tighten the implied requirements.

1. **Do not require gzip/zstd of canonical event JSONL or `issues.jsonl`
   in the working tree.** Git pack compresses history. Hot files stay
   plain text.

2. **Do not require closed beads to leave the identity space.** `bead:sase-x`
   must keep resolving. Reopen, search, doctor, +1, and deps must work.
   "Archived" means "not opened on the hot path," not "gone."

3. **Require the hot path to be O(changed streams) or O(live beads),**
   with a complete cold path. This is the goal-ledger invariant applied
   to beads.

4. **Require `issues.jsonl` off the per-mutation git path.** Events
   remain canonical. Projection is generated locally and may be committed
   on a slow cadence or never. Name the remaining consumers (tests,
   doctor, any external Beads JSONL importers) and give them
   `bead export` / `doctor --fix-projection`.

5. **Require point reads.** `show`/`read`/`history` of one ID must not
   reduce 2,108 streams. Shorthand disambiguation uses an ID catalog.

6. **Require TUI to take one snapshot per store change.** Drop
   `force=True` on the Beads pane; derive ready/blocked from the same
   `list_issues` result.

7. **If a cold tier is built, it is closed-root granularity plus
   dependency closure**, with stub catalog rows, and it is **optional
   after** the cache. Mixed-root closed children stay hot until someone
   splits streams (out of scope unless a later epic wants it).

8. **Flag beads, in-window +1 evidence, and anything `doctor` needs to
   name stay indexed**, even if their event bodies are cold.

9. **Pages are generated.** Omitting closed pages from HEAD is allowed.
   Regenerating them must be a documented command, not folklore.

10. **Do not add a serving daemon** in this work. A cache-warmer service
    proc is allowed only if post-sync cold reads miss a stated budget.

11. **Make hidden-clone packing actually happen.** `sase-17r`'s 256 MiB
    threshold is not packing the host-owned beads clone. Mutation
    publication or the chop must gc that clone, or the clone cost
    returns the first time a workspace dissociates from it.

12. **Keep `beads.db` as the lock file.** A new cache uses a new name.
    Do not revive the sqlite-as-source-of-truth confusion.

13. **CI budget on the realistic corpus**, not a toy store. Suggested
    starting bars: Rust `bead_stats` p50 ≤ 50 ms warm / ≤ 150 ms cold;
    `sase bead ready` p50 ≤ 250 ms; `sase bead read` p50 ≤ 500 ms after
    the Python-side work; mutation local (no push) p50 ≤ 500 ms.

## 7. Recommended solution

Three phases. Only Phase 1 is required to answer the performance question.
Phase 2 is the honest "archive" if working-tree size still matters. Phase 0
is leftover from September and still unpaid.

### Phase 0 — direct path, still unpaid

- Rust fast path for `list` / `show` / `read` (today excluded).
- Lazy imports so the remaining Python path does not pull Textual/ACE/pager
  until a TTY pages.
- TUI: one reduce per refresh; `force=False`; ready/blocked from that
  snapshot.
- Point `maybe_gc_sidecar_clone` at the **hidden** beads clone on a
  schedule that actually fires, or gc after publication when loose bytes
  exceed 256 MiB. Re-verify `sase-17r` against
  `~/.sase/projects/gh_sase-org__sase/repos/beads` (currently 1.75 GiB
  loose).
- Move `prune_removed_flag_event_streams` off the lockless read path.
- Fold or drop the 257 extra streams.

Expected: list 1.9 s → ~0.8–1.0 s; TUI 2.0 s → ~0.6 s; clone from hidden
ref 20 s class → ~2 s when packed; `read` still seconds until Python/audit
work lands.

### Phase 1 — the actual fix (sase-core)

A disposable, fingerprint-validated read model, as specified in
`research:202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md`
§6 Phase 1, with one addition: **mutations must not rewrite `issues.jsonl`
every time.**

- Cache file gitignored, schema-versioned, WAL, drop-on-mismatch.
- Read: stat streams → re-reduce changed → serve.
- Write: lock, cache load, append-preserving stream write, write-through
  cache rows, skip JSONL (or write it async / on `bead sync --export`).
- Parity test: cached vs full reduce on the real sase corpus with random
  mutation sequences. `sase bead doctor --verify-cache`.
- ID catalog for shorthand and for "does this closed ID exist?" without
  thawing.

Expected on today's corpus: warm `stats`/`ready`/`show` tens of ms;
Rust mutation ~20–50 ms; `git add` one stream file; publication p50 stays
network-bound (~1–2 s) instead of blob-bound.

This is also the answer to "does count matter": **after Phase 1, live
count matters a little (index size), closed count matters for cache
rebuilds and doctor, and neither matters for the interactive path.**

### Phase 2 — closed-root cold tier (optional)

Only if working-tree size, fresh reduce, or clone inode count still miss
budget after Phase 1.

- Select roots that have been closed for a floor (e.g. 14 days), have no
  live descendants, and are not in the live dep-closure.
- Move their streams to `events/cold/` (same repo, same git history) and
  leave catalog rows.
- Hot reduce never opens `cold/`.
- `read`/`history`/`open`/`search` thaw one stream (copy back, or parse
  in place and keep cold).
- Pages for those roots can leave HEAD; `pages refresh --bead` rebuilds.
- Do not compact events in the same epic as the move. Compaction is a
  history-UX change and should be its own decision.

Expected: hot working tree ~5 MB streams + ~2.4 MB live projection
instead of 35 + 21 MB; cold reduce of the live set ~88 ms even with no
cache; git history unchanged.

### What I would not do

- gzip canonical JSONL
- a `--beads-archive` second repository as the first archive
- a read/write daemon
- deleting closed beads, even behind a flag
- splitting mixed epic streams just to archive 481 closed phases
- treating `issues.jsonl` as the thing to compress rather than the thing
  to stop committing

## 8. Confidence and gaps

| Claim | Confidence |
|---|---|
| Every store verb full-reduces today | High (source) |
| ~600 ms Rust / ~1.07 s fast CLI / ~1.9 s list on this corpus | High (repeated timings) |
| Linear-in-events, 6.8× if closed-root streams are skipped | High (488-stream subset on the real reducer) |
| Agent `read` is ~5 s of non-store work | High for the split; medium for the exact 5 s breakdown (no cProfile this turn) |
| Hidden clone still 1.75 GiB loose | High (`git count-objects`) |
| Cache-in-core is the right first fix | High (this corpus + May greenfield + September speedup + goal ledger) |
| Cold-tier dep-closure stays small | Medium (today: 1 extra root; not proven over time) |
| `read` Python/audit work is a separate epic | High that it is separate; I did not design that epic here |

Not done this turn: a mutation microbench on a copied store with a local
remote (did not want to risk the live sidecar); cProfile of `bead read`;
whether any external consumer still requires committed `issues.jsonl`
besides sase's own tests and doctor.

## Sources

- sase-core `crates/sase_core/src/bead/{read.rs,jsonl.rs,mutation/store.rs,touch_index.rs,events/reduction.rs}`
- sase `src/sase/main/bead_fast_path.py`, `src/sase/bead/cli_query.py`,
  `src/sase/ace/tui/widgets/artifacts/{beads_pane.py,beads_data_sources.py}`,
  `src/sase/sdd/_store_maintenance.py`, `src/sase/bead/_stream_integrity.py`
- `docs/beads.md` (storage, pages, event log)
- Live beads sidecar HEAD `2b55fc23b`, 7,034 issues, 2,108 streams
- `~/.sase/bead_push_logs` (1,965 sase-beads completed runs)
- Beads `sase-17q` (closed, integrity guard), `sase-17r` (ready, clone/gc)
- `research:202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md`
- `research:202605/greenfield_bead_storage_architecture.md`
- `decisions:goal-ledger`, `decisions:machine-link-writes-off-primary`,
  `decisions:corpus-before-mechanism`
