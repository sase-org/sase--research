# Does Bead Count Matter? Bead-Store Scaling, Lossless Archival, and What to Build Instead

> **Research query:** Does the number of beads that exist for a sase project matter for bead read/write
> performance, and if so, by how much? What are some ways to compress and/or archive old beads to improve
> performance without losing any information permanently? Critique that plan (is it a good idea, and would a
> different approach be better?), clearly calling out any justified requirement adjustments, and end with a
> recommended solution.

![Infographic summarizing bead performance: 7,034 beads, ~48,400 events and 91.6% closed; every read and write replays the entire event store, so a single-bead lookup grows from 0.58 s at 1× history to 5.73 s at 8×; ~40% of replay work is removable redundancy and raw file I/O is only 3%; physical archiving gains only 1.6–6.8× and closed beads still receive writes; the recommended path is remove waste, cache current state in a Rust-owned read model, stop rewriting the issues.jsonl projection, and archive only if needed](bead_history_cost_and_lossless_archival_infographic.png)

## Bottom line

**1. Yes, it matters, and the cost is linear in total history.** Every bead read and every bead write replays the
whole event store from scratch: all 2,108 stream files and ~48,400 events. A one-bead `show` costs the same as
`stats` over everything. Nothing persists between calls.

- One replay costs **~0.48–0.52 s** in pure Rust at today's 7,034 beads. Through the Python binding it costs
  **0.55–0.61 s**.
- Measured on [scaled copies of the real store](#replay-cost-versus-store-size), one `show` takes **0.58 s at 1×,
  1.28 s at 2×, 2.70 s at 4× and 5.73 s at 8×**.
- The variable that matters is **events and bytes, not bead count as such**. At fixed bead count, 25× more history
  made lookups 4.4× slower (cdx). The number of *active* beads (590) barely matters.
- 91.6% of beads are closed. Closed lineages hold ~85% of the events and 83–89% of the bytes, so most of every
  replay serves closed history.

**2. Commands multiply that cost, and some paths are worse than linear.**

- A read does 1–2 replays.
- A write does 3–5 replays. It then rewrites the 20.8 MB `issues.jsonl` projection, which is also `git add`ed,
  committed and pushed.
- The TUI Beads pane does three replays plus an O(epics × issues) grouping loop every 10 s while it is visible: 2.8 s
  today and ~48 s at 4×.
- [The store grows by ~88 beads/day](#projected-cost-as-the-store-grows), and that rate is rising. It reaches 2×
  around January 2027 and 4× around mid-2027.

**3. Much of what feels slow is not bead count at all.**

- [An agent's audited `sase bead read` takes 5–8 s](#cost-per-command-and-end-to-end), but the bead store is only
  ~0.6 s of that.
- The largest single cost is **2.9 s spent re-reading and re-canonicalizing all 11,419 artifact-link outbox
  entries** to check one UUID for a collision. Two independent profiles found this.
- Git cost comes from the derived projection, not from old beads. `issues.jsonl` is 74% of the beads repo's packed
  history.
- The host-owned hidden clone holds **1.84 GiB of loose objects plus 37 packs**. That is above every gc threshold,
  but it never gets packed.

**4. Archiving and compression are the wrong first lever.**

- [Physically archiving closed lineages](#how-much-would-archiving-actually-buy) speeds the core replay by **1.6× to
  6.8×**, depending on how aggressive the archive window is. The gain also erodes as the hot set regrows.
- It adds the largest correctness surface of any option:
  - live beads depend on closed beads;
  - 481 closed phases sit inside live epic streams;
  - **closed beads keep receiving writes** (verified: 2,899 events on 968 beads landed ≥ 7 days after those beads
    closed; see [why physical archiving is riskier than it looks](#why-physical-archiving-is-riskier-than-it-looks)).
- Compression cannot speed anything up. [Raw I/O is 3% of a replay](#where-replay-time-goes), and git already
  compresses history.

**5. Recommendation: make history irrelevant to the hot path instead of moving it.**

1. [Remove measured waste](#phase-0---stop-paying-for-waste). About 40% of every replay, plus several non-store
   costs, can go with no format change.
2. Add a [**Rust-owned, disposable, fingerprint-validated read model**](#phase-1---the-logical-archive) in
   `sase_core`. This is a "logical archive": closed history is never re-parsed unless it changes. Warm reads drop to
   tens of milliseconds at any history size.
3. [Take `issues.jsonl` off the per-mutation commit path](#phase-2---projection-off-the-per-mutation-path).
4. Only when a stated trigger fires, add a
   [**byte-preserving, writable "sealed segment" archive**](#phase-3---sealed-cold-segments-only-when-a-trigger-fires).

No event is ever edited, compressed in place or deleted.

The September research
(`research:202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md`) recommended the same
Phase 0 and Phase 1. Of those, only the integrity-guard fix (`sase-17q`) has landed. The next useful step is an epic,
not another round of research.

## Scope and measurement conditions

Consolidated report, 2026-10-06. It merges five independent reports
([cdx](bead_history_cost_and_lossless_archival__cdx.md), [cld](bead_history_cost_and_lossless_archival__cld.md),
[grk](bead_history_cost_and_lossless_archival__grk.md), [mus](bead_history_cost_and_lossless_archival__mus.md),
[gem](bead_history_cost_and_lossless_archival__gem.md)) with the lead's own verification. That verification
includes a [stage-by-stage Rust benchmark of the read path](#where-replay-time-goes), which settles the main
disagreement between the reports.

Code measured: sase `22ea0cf4db`, sase-core `fa390362` (`sase_core_rs` 0.37.0, matching the CI pin), and the live
`sase` beads sidecar (`2b55fc23b`–`a58a7de1`). All benchmarks ran read-only against the live store or against
copies under `/tmp`. No bead was mutated. Host: athena, 64 cores, load average 9–31 during the runs. Treat absolute
times as ±10–15%; the ratios are stable across all five researchers.

## Does count matter, and by how much?

### How the store works

Only the parts that matter for scaling:

- **Canonical data.** `events/streams/<root>.jsonl` holds append-only events, one stream per root lineage. An epic's
  phases share the epic's stream. There are a few child-specific streams and 257 relocated or tombstoned stems.
- **Derived data:**
  - `issues.jsonl` (20.8 MB, tracked in git);
  - `pages/` (5,892 generated Markdown files, 18.7 MB, tracked);
  - the touch index.
- **`beads.db` is not a cache.** It is the Rust mutation flock (`mutation/store.rs:45-49`). Any new cache needs a
  different filename. The docs and mus's report still describe it as a SQLite mirror.
- **Read.** `read_store_issues` (`read.rs:66`) calls `read_event_store` (`jsonl.rs:392`), which does the following:
  1. runs `prune_removed_flag_event_streams`, an untyped parse of every line that is left over from a finished
     migration and can delete files during a lockless read;
  2. parses everything again, typed;
  3. validates each stream;
  4. hands off to `reduce_event_streams`, which deep-copies all streams, validates them again, merges them, applies
     every event (validating each), sorts, validates every issue and checks external-ref uniqueness.

  `issues.jsonl` is ignored whenever `events/` exists. Filters and `--limit` are applied after the full replay.
- **Detail reads are global by nature.** `show_issue_detail` (`read.rs:112`, `:712`) returns:
  - **children** (a scan of all issues);
  - **`blocks`**, the reverse dependencies (a scan of all issues);
  - ancestors;
  - the inbound **artifact-link neighborhood**, built from link provenance across all streams;
  - shorthand ID resolution (a suffix scan over all IDs).

  It also clones and sorts every issue. **Reading only one stream file therefore cannot answer `sase bead read`.**
  Point reads need an index.
- **Write.** `MutableStore::load` runs a full replay. `save` rewrites the changed stream (append-preserving, with a
  prefix check) and then serializes, fsyncs and renames the whole `issues.jsonl`. The Python lane adds routing,
  resolve and show replays, then `git add`, commit, push and "verify published".

### Store shape and growth

As of 2026-10-06:

| Metric | Value |
| --- | --- |
| Beads | **7,034**: closed 6,444 (91.6%), ready 393, in_progress 169, open 27, snoozed 1 |
| Types | phase 4,976 · task 1,109 · plan 949 (66 tasks are flags) |
| Streams / events / bytes | **2,108 / ~48,400 / 35.1 MB** (median stream 9 KB, max 165 KB) |
| `issues.jsonl` | **20.8 MB**. Closed rows are 18.3 MB (88%); the 590 active rows are 2.4 MB |
| Fully closed root lineages | 1,364–1,540 streams (definitions vary slightly), holding ~85% of events and 83–89% of bytes |
| Mixed lineages | 61 live roots carrying **481 closed beads** inside live streams |
| Growth | +88 beads/day (5,979 on 09-24 → 7,034). Creations per month: Jul 1,181 · Aug 1,987 · Sep 2,228 |
| Beads repo | ~20,450 commits, ~290–330/day. Workspace pack 108 MiB. **Hidden clone: 1.84 GiB loose (2,293 objects) + 37 packs (1.34 GiB)** |

### Replay cost versus store size

cld built scaled corpora: random dependency-closed subsets for the fractions below 1×, and length-preserving
prefix-renamed copies of the real store for the multiples above 1×. Times are Rust bindings, median of 5.

| Corpus | Beads | Events | `bead_show` | `bead_ready` | `bead_append_note` | `issues.jsonl` |
| --- | --- | --- | --- | --- | --- | --- |
| ⅛× | 1,023 | 7.3k | 0.080 s | 0.083 s | 0.098 s | 3.0 MB |
| ½× | 3,611 | 25.4k | 0.292 | 0.288 | 0.360 | 10.8 |
| **1× (today)** | **7,034** | **48.4k** | **0.577** | **0.585** | **0.700** | **20.8** |
| 2× | 14,066 | 96.7k | 1.280 | 1.277 | 1.499 | 41.5 |
| 4× | 28,130 | 193k | 2.702 | 2.898 | 3.396 | 83.0 |
| 8× | 56,258 | 387k | 5.727 | 6.641 | 7.567 | 166.0 |

That works out to roughly **80–100 µs per bead, or ~12 µs per event**, slightly worse than linear at the top end.
Synthetic stores from cdx and gem agree:

- cdx: lookup 29.5 ms at 1k beads and 359 ms at 10k (12.2×); a note append 4.6× slower;
- gem: ~45 µs per one-event stream, linear from 100 to 15k.

### Where replay time goes

Where a replay's ~480 ms goes (lead's measurement, new).

[The reports disagreed here](#where-the-reports-disagreed-and-how-it-was-resolved). gem attributed 380 ms (>50%) to
opening 2,108 files; cld attributed 4% to I/O and 25% to the migration rescan. To settle it, I compiled a
stage-timing harness against `sase_core` at the pinned revision (release profile, thin LTO). It ran on a copy of the
live store, median of 7, in two separate runs. Script and output are in
[`bead_history_cost_and_lossless_archival__final_data/`](bead_history_cost_and_lossless_archival__final_data/).

| Stage (1×: 2,108 streams, 48,393 events) | Time | Share | Removable without a cache? |
| --- | --- | --- | --- |
| `readdir` + `stat` every stream (what a fingerprint check costs) | **4 ms** | 1% | — |
| Open and read all 35 MB of stream bytes | **15 ms** | 3% | — |
| `prune_removed_flag_event_streams` (untyped re-parse; a no-op today) | **128–132 ms** | 26% | **Yes**: move to a migration or `doctor` |
| Typed `BeadEventRecordWire` parse | 87–89 ms | 18% | Only with a cache |
| Per-stream validation (runs twice, plus per-event validation in `apply_event`) | ~28 ms per pass | ~6–12% | **Yes**, one pass |
| Deep clone of every parsed stream (`validated_event_streams`) | **32 ms** | 6% | **Yes** |
| Merge, apply, sort, issue validation, external refs | ~130 ms | 26% | Only with a cache |
| **`read_store_issues` (the production read)** | **481–516 ms** | 100% | ~190 ms (~40%) removable |
| `show_issue_detail` (core of `sase bead read`) | 581–587 ms | — | +~100 ms for link provenance and a full clone and sort |
| Python binding: `bead_stats` / `bead_show_issue_detail` / `bead_read_store` | 558 / 615–633 / 749–769 ms | — | Conversion adds 50–270 ms |
| For comparison: serialize the projection (`export_issues_to_jsonl`) | 43–46 ms | — | Plus a 20.8 MB fsync and rename per write |
| For comparison: parse all of `issues.jsonl` | 95–102 ms | — | Still O(N): not an index |

What this shows:

- **File opens do not dominate.** Opening and reading every stream costs 15 ms.
- **JSON parsing in Rust is not slow.** The typed parse takes 87 ms, which is faster than CPython's 0.25 s for the
  same bytes. cld's "Rust is 2.5× slower than CPython" compared a parse against a whole replay.
- **The cost is redundant work plus irreducible replay.** Removing the migration rescan, the deep clone and the
  duplicate validation takes the replay to about **~290 ms**. The remainder is still linear in history, so
  engineering alone buys ~1.7×. A cache is needed to make the cost independent of history.

### Cost per command and end to end

| Path | Today (1×) | Notes |
| --- | --- | --- |
| `sase bead -h` (floor) | 0.38–0.50 s | imports |
| `stats` / `ready` / `search` (Rust fast path) | 1.06–1.15 s | one replay |
| `list` (Python slow path) | 1.84–2.03 s | replay plus conversion and rendering |
| Audited `sase bead read <id>` | **5.1–8.8 s** (transcript p50 8.4 s since 09-25) | **Outbox collision scan 2.9 s**, imports ~1 s, creator-URL lookup ~0.9 s, replay ~0.75 s |
| Rust `bead_cli_execute` update / close | 1.16–1.22 s | two replays plus a write |
| Local write tail at 1× / 4× | 1.86 s / 7.81 s | Rust append 0.69 / 3.31, `git add` 0.30 / 1.18, commit 0.14 / 0.26, local push 0.70 / 3.05 |
| CLI write, count-dependent part | **~3–4.5 s** at 1×, **~16–21 s** at 4× | 3–5 replays, projection rewrite, git |
| Background sync (n = 7,040) | p50 2.4 s · p90 5.3 s · p99 11.4 s | after `sase-17q`. 85 of 152 semantic conflicts involved `issues.jsonl` |
| TUI Beads pane refresh | **2.8 s** (8.2 s at 2×, 48 s at 4×) | three replays plus O(epics × issues) grouping (`beads_data.py:141-154`), forced every 10 s (`beads_pane.py:149-150`) |

### Projected cost as the store grows

| Quantity | Today (7k) | 2× (~Jan 2027) | 4× (~mid-2027) | 8× |
| --- | --- | --- | --- | --- |
| One replay (any read binding) | 0.58 s | 1.28 s | 2.70 s | 5.73 s |
| Count-dependent cost per read command | 0.6–1.2 s | 1.3–2.6 s | 2.7–5.4 s | 5.7–11.5 s |
| Count-dependent cost per write command | ~3–4.5 s | ~6–9 s | ~16–21 s | ~35–45 s |
| TUI Beads pane per refresh | 2.8 s | 8.2 s | **48 s** (longer than the refresh interval) | ≫ 2 min |
| Stat sweep (what a cache pays) | 4–6 ms | ~12 ms | ~23 ms | ~48 ms |

## How much would archiving actually buy?

The reports quoted gains from 1.6× to 3,600×. They were measuring different things:

| What is removed from the hot path | Hot read (1×) | Gain | Source | What it actually is |
| --- | --- | --- | --- | --- |
| Nothing (today) | 0.58–0.60 s | 1× | all | |
| Lineages closed ≥ 30 d (keep the rest plus dependency closure) | 0.359 s | **1.6×** | cld | physical archive, conservative window |
| Lineages closed ≥ 7 d | 0.207 s | **2.8×** | cld | physical archive, aggressive window |
| **Every** fully closed root (0-day window) plus dependency closure | 0.088 s | **6.8×** | grk | upper bound for a physical archive. 338 closed beads stay in mixed epics |
| All history dropped, current state of active beads only | 0.025–0.028 s | 21–29× | grk, gem | **a cache**, not an archive |
| Indexed point lookup over all 7,034 current rows (SQLite) | 0.15 ms | ~3,000× | cdx | **a cache**. It excludes validation, so it is not a production promise |

**The large numbers come from serving current state instead of replaying history. That needs no archive.** The
physical-archive numbers also decay: the hot set regrows at creation rate × window. With a cache in place, physical
archiving would mainly save the stat sweep, ~40 ms at 8×.

### Why physical archiving is riskier than it looks

Three facts make physical archiving riskier than it looks:

1. **Dependencies cross the boundary.** A live-only reduce failed with `dependency_added target does not exist`. grk
   and gem both hit this independently. The archive unit must be a whole root lineage plus its dependency closure.
2. **Mixed epics.** 481 closed phases live inside 61 live epic streams. Archiving at bead granularity would mean
   splitting streams, which is a format change.
3. **Closed beads keep getting written to (verified by the lead).** Counting events applied to beads that are still
   closed:

   | Arrived at least … after close | Events | Beads | Main operations |
   | --- | --- | --- | --- |
   | 7 days | **2,899** | 968 | `link_added` 1,702, `issue_updated` 975, `note_appended` 207 |
   | 30 days | 1,493 | 535 | `link_added` 828, `issue_updated` 663 |
   | 60 days | 927 | 284 | `link_added` 510, `issue_updated` 415 |

   These come from link backfills, reprojection repairs and migrations. There were also 41 explicit reopens and 1,241
   `+1` events, which can reopen closed tasks. **A frozen, read-only archive would break existing machinery.** Any
   archive must accept writes.

## Ways to compress or archive without permanent loss

"Lossless" here means three things:

- **no event is ever edited or deleted;**
- derived files (projection, pages, caches) may be dropped and regenerated;
- git history is never rewritten, and every old ID keeps resolving.

| # | Option | Speed effect | Loss and correctness risk | Verdict |
| --- | --- | --- | --- | --- |
| 1 | **Fingerprint-validated read model ("logical archive")**: a gitignored cache that never re-parses unchanged streams | Warm reads 12–30× or more; flat with history | None. Derived; drop and rebuild | **Do. This is the core of the solution** |
| 2 | **Live/hot index inside #1**: ready, blocked and default list touch active rows only. Same shape as the goal ledger | Hot queries O(active) | None | **Do, as part of #1** |
| 3 | **Take `issues.jsonl` off the per-mutation commit path** (generate on demand, or shard into active plus monthly closed files) | −0.3 s `git add`, −most push packing, −0.05 s serialization plus fsync | None, because it is a projection. **Requires migrating the mtime-keyed consumers first** ([see the hazard](#a-hazard-none-of-the-plans-fully-covered)) | **Do, after the consumer migration** |
| 4 | **Repack the hidden clone (`sase-17r`)** and add retention for `~/.sase/bead_push_logs` (126k files, 507 MB) | Clone and first-use time | None | **Do now** |
| 5 | **Sealed cold segments** (physical archive): fully closed, quiet lineages moved verbatim to `events/sealed/<YYYY-MM>/`, with a checksummed index; new events go to an overlay stream | 1.6–6.8× without a cache; bounds the working tree | Low if byte-preserving, writable and parity-proven; medium implementation risk | **Later, [behind a trigger](#phase-3---sealed-cold-segments-only-when-a-trigger-fires)** |
| 6 | Derived snapshots or checkpoints | Small on top of #1 | None if derived. **Lossy if they replace events** | Derived only |
| 7 | zstd/gzip of event files | **None or negative**: replay is CPU-bound and I/O is 3% | None, but it defeats git delta, grep and diffs | **Not in the working tree.** Off-repo backup bundles only (zstd-3: 35 MB → 7.4 MB; full canonical-state tar round-trips exact bytes) |
| 8 | Drop closed pages from HEAD (5,752 of 5,892 pages are closed) | Checkout size only | None if `pages refresh` regenerates them | Optional |
| 9 | Fold the 257 non-root stream stems | Small (~16% of stream bytes) | **Loses history if done by deletion**. Relocation only | Only as a lossless relocation |
| 10 | Compact closed streams to one snapshot event in HEAD, keeping the old bytes only in git | ~2.5× | Changes history UX. History lives only in git. Collides with ongoing writes | **No** |
| 11 | Separate archive repo or service | Smaller clones | Cross-repo consistency, offline reads | Only if clone size becomes the complaint |
| 12 | `sase bead rm`, history rewrite, LLM summaries replacing events | `rm` does **not** speed replay (tombstoned streams remain) | Lossy | **No** |
| 13 | A bead daemon | ~10–30 ms per read after a cache | Second code path (`sase-3e` and upstream Beads both deleted theirs) | **No** |

## Critique of the plan

### What is right

- The premise is real and getting worse. Closed history dominates every operation, and nothing in today's design
  gets cheaper with time.
- The "without losing information" constraint is correct. It rules out pruning, squashing and rewriting.
- A hot/cold split is the right **end state**. SASE already chose it for goals (`decisions:goal-ledger`: hot reads
  are O(unsettled), settled files are never opened, and hot-list p95 moved −6% from 25k to 100k settled goals).

### What is wrong or too narrow

1. **Archive-first optimizes the smaller, eroding term.** A physical archive buys 1.6–6.8× once. Each of the
   following is as large or larger, and none moves any data:
   - removing the migration rescan, the deep clone and the duplicate validation (~1.7×);
   - one replay per command (2–5× on writes);
   - fixing the TUI loop (10–70× on that path);
   - fixing the outbox scan (−2.9 s per audited read);
   - a cache (12–30× or more, and flat with history).
2. **Compression is a category error for speed.** Reading all 35 MB takes 15 ms. The cost is CPU replay, and
   compression only adds decode work.
3. **The plan targets canonical data, but the write and git cost is in derived data.** `issues.jsonl` is 74% of git
   history, the largest per-mutation write and the top conflict file. Dropping it from the commit path is lossless by
   definition.
4. **Physical moves create a large new correctness surface:**
   - writes to cold beads ([see above](#why-physical-archiving-is-riskier-than-it-looks));
   - cross-boundary dependencies;
   - mixed epics;
   - the publication integrity guard, which would see a move as event deletion;
   - modify/delete rebase conflicts with concurrent appends in other workspaces;
   - every read family needing a cold path: show, history, search, `list --status closed`, `doctor`, pages, the
     touch index, the conflict resolver, and **`/sase_new_task` duplicate detection, which must keep seeing closed
     beads**.
5. **It frames the problem as bead count.** The variable that matters is replays per command × history size. On the
   agent read path, the biggest cost is not the bead store at all.

### Would I take a different approach?

Yes. Make history irrelevant on the hot path (a cache), stop committing a generated 21 MB file, and fix the adjacent
unbounded logs. Physical archiving then becomes an optional storage measure with explicit triggers, not a
performance project.

### A hazard none of the plans fully covered

Taking `issues.jsonl` off the write path silently breaks change detection. At least five Python consumers use its
`(mtime_ns, size)` as a cheap store fingerprint:

- `_artifact_ref_entity_catalogs._read_cached_bead_store`;
- `wait_bead_catalog`;
- the Beads and Plans data sources' mtime keys;
- `_surface_tokens`.

If the file stops changing on every mutation, those TUI views and caches go stale. A store-fingerprint binding has to
land first, and those consumers have to move to it. No linked plugin (sase-github, sase-telegram, sase-nvim) reads
`issues.jsonl`, so the consumer audit is limited to sase (27 files mention it) and sase-core.

## Requirement adjustments

These adjustments are explicit:

- **A1. Re-target the metric.** Replace "reduce the number of beads" with **"hot-path bead latency is independent of
  closed history."** Acceptance, modeled on the goal ledger's G1 criterion:
  - on 1× → 8× scaled corpora, `ready`, `list`, `read` and mutation p95 move by less than 10%;
  - warm core point read ≤ 20 ms;
  - active list ≤ 50 ms;
  - TUI no-change refresh < 100 ms.
- **A2. Drop compression as a performance lever.** Keep it only for off-repo backups and storage.
- **A3. Define lossless precisely.** Events are byte-immutable and never deleted. Derived files may be regenerated.
  Git history is not rewritten. Old IDs, shorthand, history, search, duplicate checks and dependency resolution keep
  working. Edited and retracted note revisions, `+1` evidence and close history stay recoverable.
- **A4. "Archived" means logical first.** It is a property computed by the read model (closed and quiet). A physical
  seal is optional, comes later and needs a trigger. When it happens it must be:
  - byte-preserving and checksummed;
  - **writable**, by thawing through an overlay stream;
  - at root-lineage granularity, with dependency closure;
  - parity-proven (replay of hot + sealed must equal the replay before sealing);
  - run by one host-owned writer under the store lock.
- **A5. Widen the scope to derived artifacts and adjacent unbounded logs on the bead path:**
  - `issues.jsonl` and pages;
  - the outbox collision scan;
  - hidden-clone gc;
  - `bead_push_logs` retention;
  - the TUI loop.
- **A6. Keep `beads.db` as the lock file.** The cache gets a new name. Do not add a serving daemon.
- **A7. Benchmark in CI on a scaled corpus (≥ 4×).** Use cld's length-preserving prefix copy, so that toy stores do
  not hide regressions.

## Recommended solution

### Phase 0 - stop paying for waste

Small, independent changes; no format change.

1. **Outbox collision check in O(1)** (`src/sase/sdd/_artifact_link_outbox_io.py:477`). Pre-check the UUID as a
   substring before parsing, or keep an ID index. Also drain or compact the outbox. This takes **~2.9 s off every
   audited read** of beads, artifacts and memory.
2. **TUI Beads pane:**
   - group phases with a single dict pass;
   - drop `force=True` from `on_refresh`;
   - compute list, ready and blocked from one replay.
3. **sase-core, one parse per replay:**
   - move `prune_removed_flag_event_streams` out of `read_event_store`, into a migration or `doctor`, or run it only
     on new or changed streams once the cache exists. This also ends file deletion during lockless reads.
   - drop the deep clone of every stream;
   - validate once.

   Measured target: **~480 ms → ~290 ms**.
4. **One replay per CLI command.** Route by stream path or ID catalog instead of `list_issues`, and pass the resolved
   snapshot into the mutation. Writes go from 3–5 replays to 1.
5. **Make `sase-17r` actually reach the hidden clone.** Its 37 packs, 2,293 loose objects and 1.84 GiB of loose
   bytes exceed all three thresholds in `_store_maintenance.py`, yet it stays unpacked. Also update that file's stale
   "~5 MB" comment (the projection is now 20.8 MB), and add retention for `bead_push_logs`.

### Phase 1 - the logical archive

A Rust-owned persistent read model in `sase_core`.

This follows the Rust-core boundary rule: the logic lives in `sase-core`, the binding is thin, and the
`sase-core-revision.txt` pin moves with it.

- **Substrate.** A gitignored `beads.cache.sqlite`, schema- and reducer-versioned, dropped and rebuilt on mismatch.
  It is never authoritative. The precedents are `touch_index.rs`, the agent-artifact SQLite index and the goal
  ledger's `goals-hot.json`.
- **Contents:**
  - per-stream signature: path, size, `mtime_ns`, inode;
  - the merge frontier: the largest `(timestamp, op priority, event_id)` applied so far;
  - the **pre-post-pass** reducer state: issue rows with indexed id, status, type, parent, stream and `created_at`;
  - edge tables for dependencies (both directions) and children;
  - link provenance keyed by target;
  - an ID-suffix catalog for shorthand resolution.
- **Correctness argument.** This resolves cdx's caution against cld's incremental proposal.
  `merge_stream_events` (`events/merge.rs:786`) is a k-way merge on `(timestamp, op priority, event_id)` that
  preserves order within each stream. Snapshot + tail therefore **equals a full replay exactly** when four conditions
  hold:
  1. every changed stream is a pure append (the old bytes are a prefix, which the append-preserving writer already
     guarantees locally);
  2. no stream disappeared or was renamed;
  3. every new event's merge key sorts after the frontier;
  4. the global post-pass (sort, issue validation, external-ref collapse and validation) re-runs over the result.

  Anything else falls back to a full rebuild, ~0.3 s after Phase 0. Examples are clock-skewed events from another
  machine, relocations, conflict resolutions and backdated appends. The design is always correct; it is just slower
  in rare cases.
- **Reads.** A stat sweep (4 ms today, 48 ms at 8×) is followed by one of three things: serve directly, apply the
  tail, or rebuild.
  - `ready`, `blocked` and default `list` touch only active rows.
  - `show` and `read` are indexed lookups plus edge and provenance tables.
  - Search and closed listings read cached rows and keep today's substring and regex semantics.
- **Writes.** Under the existing flock, a write loads only the affected rows, appends event bytes exactly as today,
  and writes rows and frontier through in the same critical section.
- **Proof obligations:**
  - a parity test (cache vs. full replay) over randomized mutation sequences, incoming merges, clock-skewed events
    and relocations on a scaled corpus;
  - `sase bead doctor --verify-cache`;
  - the [A1](#requirement-adjustments) perf gate in CI.

### Phase 2 - projection off the per-mutation path

1. Add a `bead_store_fingerprint` binding and migrate the five mtime-keyed consumers to it
   ([see the hazard](#a-hazard-none-of-the-plans-fully-covered)). Audit the remaining content readers.
2. Stop rewriting and committing `issues.jsonl` on every mutation. Generate it on demand (`bead export` or
   `doctor --fix-projection`). If an audited consumer truly needs a tracked file, shard it into `issues/active.jsonl`
   plus `issues/closed-<YYYY-MM>.jsonl`.
3. Effect:
   - removes the largest O(N) write;
   - ends ~74% of future git growth;
   - removes the top conflict file;
   - removes the loose-blob bloat behind `sase-17r`.

### Phase 3 - sealed cold segments only when a trigger fires

**Triggers:** any of

- more than 10k hot stream files;
- a stat sweep above 50 ms;
- a working tree above ~250 MB;
- clone or first-use complaints that partial clones cannot fix;
- Phase 1 parity proving infeasible. In that case sealing becomes the primary lever, worth 1.6–6.8×.

**Design.** The full design is in cld §7 Phase 3 and cdx's "third" section. In outline:

- Seal fully closed root lineages that have been quiet for ≥ 30 days and have no live dependents, claims or pending
  outbox entries.
- Move them verbatim with `git mv` into `events/sealed/<YYYY-MM>/`, one file per stream, which keeps git delta and
  grep working.
- Record a SHA-256 manifest and a sealed index (id → segment, status, title, parent, `closed_at`). ID allocation and
  high-water marks stay reserved.
- **Thaw by overlay:** a new event creates a fresh hot stream, and the reducer de-duplicates by `event_id`.
- The integrity guard and the conflict resolver compare event sets across hot + sealed.
- Every seal commit carries a parity proof.
- zstd bundles may be shipped off-repo for backup only.

### Expected results

All columns after "Today" are estimates derived from the measurements above, not a prototype.

| Operation | Today (1×) | After Phase 0 | After Phase 1 | After Phases 1–2, at 8× history |
| --- | --- | --- | --- | --- |
| Core read (`show` / `ready` binding) | 0.55–0.60 s | ~0.3 s | **≤ 20–50 ms** | ~50–100 ms (stat sweep; Phase 3 trims it) |
| Audited `sase bead read` | 5–8 s | ~2–3 s | ~1.5–2.5 s, bounded by imports and creator-URL lookup (not count) | same |
| Mutation, local and count-dependent | ~3–4.5 s | ~1–1.5 s | ~0.6–1 s | **~0.2–0.4 s + network**, independent of history |
| TUI Beads pane | 2.8 s every 10 s | ~0.6 s, only on change | tens of ms | tens of ms |
| Git growth per mutation | one 20.8 MB projection blob | same | same | **one stream's delta** |

**What would change this recommendation:**

- **Phase 1 parity proves infeasible.** Promote [Phase 3](#phase-3---sealed-cold-segments-only-when-a-trigger-fires).
- **An external consumer needs a single tracked `issues.jsonl`.** Shard it rather than keep the full rewrite.
- **Clone size, not latency, is the complaint.** Do Phase 2 and the repack first, then choose between partial clones
  and an off-repo archive.

## Follow-ups

These were found during this research and are independent of whether the plan above is accepted:

- **Outbox collision scan on every audited read** (2.9 s).
- **TUI Beads pane:** quadratic grouping plus forced refresh.
- **`sase-17r` not reaching the hidden clone.** The bead is still `ready`. Add the new evidence to it (37 packs,
  1.84 GiB loose, every threshold exceeded) rather than filing a duplicate.

The plan itself ([Phases 0–3](#recommended-solution)) should become one epic through `/sase_plan` if accepted. The
September research already specified Phases 0–1 in detail.

## Where the reports disagreed and how it was resolved

| Topic | Disagreement | Resolution |
| --- | --- | --- |
| Where replay time goes | gem: file opens ~380 ms (>50%). cld: I/O 4%, rescan 25% | **[Lead's stage bench](#where-replay-time-goes):** opens and reads take 15 ms (3%); the rescan is 26%; redundant clone and validation ~12%; parse 18%; reduce ~26%. gem's breakdown is refuted |
| Rust vs. CPython parsing | cld: the reducer is "2.5× slower than CPython parsing" | Apples to oranges. The Rust typed parse (87 ms) is ~3× *faster* than CPython; the replay is slow because of extra work |
| Single-stream point reads | gem: `show`/`read` can load one stream in < 5 ms with no storage change | **Not possible as stated.** The detail view needs children, reverse dependencies, inbound link provenance, ancestors and shorthand resolution, all global. It needs an index ([Phase 1](#phase-1---the-logical-archive)) |
| Write gain from dropping `issues.jsonl` | gem: 1,400 ms → ~60–75 ms in Phase 1 | Overstated. `MutableStore::load` still replays (~0.5 s) until a cache exists. Dropping the projection saves ~0.05 s serialization, the fsync, and ~0.3 s+ of git |
| Archive speedup | 1.6–2.8× (cld) vs. 6.8× (grk) vs. 29× (gem) | All correct for different windows. Physical archive: 1.6–6.8×. 21–29× is a current-state cache, not an archive ([see above](#how-much-would-archiving-actually-buy)) |
| Using `beads.db` as the index | mus: promote the SQLite mirror | `beads.db` is now the mutation flock. Use a new cache file |
| Hot/cold `issues.jsonl` split first | mus Phase 1 | Does not touch the production read path, which ignores `issues.jsonl` when `events/` exists. Useful only as Phase 2 sharding |
| Order: index vs. archive | mus: archive, then index. The others: index or cache first | Cache first. It is larger, flat with history, and needs no data movement |
| Incremental cache safety | cdx: per-stream incremental is unsafe. cld: re-reduce changed streams plus a post-pass | Snapshot + tail with a merge-frontier precondition and full-rebuild fallback is exact ([Phase 1](#phase-1---the-logical-archive)) |
| Agent `read` breakdown | grk: ~5 s spread across Python sessions (no profile) | Two cProfiles (cld, gem): the outbox scan is 2.9 s, the largest single item. Verified: 11,419 entries, 7.8 MB, a full re-read on every append |
| Hidden-clone bloat | grk only | Verified and still growing: 1.75 → 1.84 GiB loose within the day; 37 packs |
| Event count | gem: "~15,000+" | 48,393 (counted) |

## Confidence and gaps

| Claim | Confidence |
| --- | --- |
| Every store verb replays everything; cost is linear in history | **High** (source plus five independent measurements) |
| Stage breakdown and ~40% removable waste | **High** (compiled harness, two runs, matching cld's independent numbers) |
| Physical archive gain 1.6–6.8× | **High** for today's corpus. It decays with time |
| Closed beads keep receiving writes | **High** (direct count over all events) |
| Snapshot + tail equivalence | **High** from the merge code. **Not prototyped**; Phase 1's parity test must confirm it |
| 2× / 4× dates | Medium (creation rate is rising and could change) |
| Phase 1 latency targets | Medium (derived from component costs, not a prototype) |
| TUI at 4× | Medium (a faithful replica of the loop, not a full pane load) |

**Not done:**

- a cache prototype;
- an end-to-end mutation with a remote at 8×;
- an audit of how often the merge-frontier precondition fails in practice (clock skew across athena, apollo and
  mac).

## Method and sources

- **Lead's measurements.** Scripts and raw output are in
  [`bead_history_cost_and_lossless_archival__final_data/`](bead_history_cost_and_lossless_archival__final_data/):
  - `stagebench.rs`: a `sase_core` example built at `fa390362` in a scratch export, never in the linked checkout;
  - `binding_bench.py`: `sase_core_rs` binding timings;
  - `cold_writes.py`: post-close write census.

  All three ran on a `/tmp` copy of the live store. Also used: `git count-objects` on the workspace and hidden beads
  clones, and code reading of `read.rs`, `jsonl.rs`, `events/{reduction,merge}.rs`, `_artifact_link_outbox_io.py`,
  `beads_data.py`, `beads_pane.py`, `_store_maintenance.py` and the issues.jsonl consumers (sase plus three plugin
  repos).
- **Researchers' methods** (see each report):
  - cdx: controlled synthetic scaling, real-store live bench, compression round trips (data in
    `bead_count_scaling_lossless_archival__cdx_data/`);
  - cld: scaled real-store corpora, git write-path timings, transcript and sync-log latencies, archivability windows,
    TUI loop replica;
  - grk: real-store subset reduces and the hidden-clone census;
  - mus: CLI timings and store census;
  - gem: synthetic scaling and a `sase bead read` cProfile.
- **Prior work:**
  - `research:202609/bead_speedup_daemon_vs_direct_path/bead_speedup_daemon_vs_direct_path.md`;
  - `research:202605/greenfield_bead_storage_architecture.md` (cited by grk);
  - `decisions:goal-ledger`;
  - beads `sase-17q` (closed) and `sase-17r` (ready).
