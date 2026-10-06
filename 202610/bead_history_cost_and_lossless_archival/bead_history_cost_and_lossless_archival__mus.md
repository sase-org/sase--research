# Bead-count vs. read/write performance, and lossless archival options

Researcher: mus (`__mus`). Independent report for the 5-researcher swarm.
Date: 2026-10-06. Project measured: `sase` (7034 beads).

## Question asked

1. Does the number of beads in a sase project matter for bead read/write
   performance? If so, by how much?
2. What are ways to compress and/or archive old beads to improve performance
   without losing any information permanently?
3. Critique of the plan itself, adjustments, and a recommended solution.

## TL;DR (top finding)

Yes, bead count matters, and it matters **linearly on every single
operation** — but not for the reason most people assume. The dominant cost is
not disk size (the whole store is only ~195 MB) but the fact that **every
read and every mutation loads and reduces the entire store**: all 2,108
event-stream files plus a 20.7 MB `issues.jsonl` projection. At today's 7,034
beads that is ~1–2 s per CLI invocation (~0.5 s of which is interpreter
startup); ~92% of those beads are closed, so ~92% of that per-op tax buys
nothing on the hot path. Archiving old beads is worth doing, but as specified
("move old beads somewhere to go faster") it treats a symptom: without fixing
the full-scan-per-op read path, any query that touches history still pays the
full cold-load price, and the recommended design should be **hot/cold
partitioning with tombstone pointers plus indexed single-bead reads**, not
deletion or opaque compression.

## 1. How the store actually works (evidence)

All paths below were inspected in-tree (`src/sase/bead/`) and in the linked
Rust core (which owns storage; Python only calls facades).

### 1.1 Layout of the live store

Measured at `sase/repos/beads` (workspace 17 checkout, `SASE_SDD_BEADS_DIR`):

| Component | Size / count | Role |
|---|---|---|
| `events/streams/` | 38 MB, 2,108 files | Canonical store. One JSONL event stream per top-level bead family |
| `issues.jsonl` | 20.7 MB, 7,034 lines | Derived projection, regenerated from the event store (`events/manifest.json`: `"generated_from": "issues.jsonl"`, `"migration_tool": "sase-core bead events"`) |
| `events/manifest.json` | tiny | `stream_count` (2,108); reads fail closed on count mismatch |
| `pages/` | 33 MB, 816 entries | Generated per-bead pages |
| `assets/` | 1.2 MB | Snapshots (e.g. directory map PNG) |
| `.git` (pack) | ~104 MB, 143,015 objects in 1 pack | Every mutation commits `issues.jsonl` + touched streams |
| Working tree total | ~195 MB | What every fresh workspace clones |

Row-size distribution of `issues.jsonl` (parsed locally): mean 2,950 B,
median 2,011 B, p90 5,485 B, max 117 KB.

Status mix from `sase bead stats`: total 7,034; **closed 6,444 (91.6%)**,
open 27, in-progress 169, ready 393, snoozed 1; by type: plans 949, phases
4,976 (!), tasks 1,109, flags 66. Two facts matter for everything below:
(1) closed beads dominate ~12:1, and (2) **phases are ~70% of all beads** —
any archival story is mostly a closed-phase story.

### 1.2 Read path: full-store load per operation

`BeadProjectQueryMixin` (`src/sase/bead/_project_queries.py`) routes
`show`, `show_issue_detail`, `resolve_id`, `history`, `lost_notes`,
`list_issues`, `search`, `ready`, `blocked`, `stats`, `get_epic_children`
through the Rust read facade, whose entry point is `read_store_issues`
(`crates/sase_core/src/bead/read.rs`): if an event store is present, it calls
`read_event_store`, which **reads every stream file** (`read_event_streams
_without_manifest`: open + parse + validate all 2,108 files, duplicate-ID
check, manifest count check) and then `reduce_event_streams` folds all events
into issues. There is no index, no lazy stream selection, no "read one bead"
fast path — `show ONE` costs the same full load as `list ALL`.

### 1.3 Write path: full load + full projection rewrite + git commit

`MutableStore::load` (`bead/mutation/store.rs`) performs the same full read;
a mutation appends tail events to (usually) one stream via
`write_event_store_changed` (append-preserving, so the stream write itself is
small and history-immutable by construction), then `save_issues` rewrites the
**entire 20.7 MB `issues.jsonl`**, and `sync`/`git_sync` commits. Recent
history confirms the shape: each bead commit touches `issues.jsonl` + one
`events/streams/<id>.jsonl` (+ `config.json`/`manifest.json` on create).
So every mutation pays O(store) read + O(N) projection rewrite + one new
~20 MB git blob (delta-compressed in the pack, but the pack still grows —
101 MB today and monotonically increasing).

### 1.4 What this implies for scaling

- Reads scale with **stream-file count (opens/stats/validates) + total event
  bytes (parse + reduce)**. Both grow ~linearly with bead count.
- Writes add a **full-projection rewrite** linear in N on top.
- Git porcelain is currently fine (`git status` 29 ms, `git diff --quiet`
  6 ms, single-pack repo) — the git tax today is clone/fetch size, not
  per-command latency.
- The `beads.db` SQLite mirror exists in code as a compat layer (a
  `WARNING: beads.db missing` doctor line confirms it is not currently
  maintained in this store), i.e. an indexed-read substrate already exists
  conceptually but is not the serving path.

## 2. Measured numbers (N = 7,034)

Method: wall-clock `sase bead …` timings in this workspace, `TIMEFORMAT=%R`;
Python-JSON full parse of `issues.jsonl` copies as a parse-cost proxy.
`show` is agent-gated (agents must use audited `sase bead read`), so single
reads were timed via `read`.

| Operation | Time | Notes |
|---|---|---|
| `sase --help` (startup baseline) | ~0.50 s | interpreter + import floor every command pays |
| `bead stats` ×5 | 1.08–1.70 s | store load ≈ 0.6–1.2 s net of startup |
| `bead ready` | ~1.08 s | same full load |
| `bead search "auth" --limit 20` | ~1.15 s | limit does not avoid the load |
| `bead list --status open` ×3 | 1.88–2.03 s | filter does not avoid the load; rendering adds ~0.8 s |
| `bead list --status closed --limit 5` | ~2.26 s | ditto — LIMIT is applied after the full load |
| `bead read sase-10 -r …` | 3.5–5.6 s | single-bead read incl. audit write; slowest op observed |
| Python-JSON parse of `issues.jsonl` | 161 ms @7,034; 52 ms @2,000; 14 ms @500 | perfectly linear, ~25 µs/bead — parse is NOT the bottleneck; the 2,108 file opens + reduce + startup are |

By how much does count matter, then?

- **Today (7k beads): ~1–2 s per bead CLI call, of which ~0.6–1.5 s is
  store-load attributable to N.** Annoying, paid on every agent bead touch.
- **Projection to 70k beads (linear extrapolation): ~6–15 s per op** plus
  ~200 MB `issues.jsonl` rewrites per mutation and multi-hundred-MB clones.
  The failure mode is latency-per-action, not disk exhaustion.
- **Closed-bead share of the tax: ~92%.** A hot store of only open beads
  (~590 rows, ≈1.7 MB) would cut projection parse ~12× and stream opens
  roughly proportionally (closed top-level families drop out).

Caveat: these are single-machine, warm-cache, one-workspace numbers, not a
controlled benchmark (no cold-cache, no contended-lock, no 70k-bead store
existed to test against). The complexity claims (full scan per op) are
structural from the code, so the direction is certain; the exact slope is
approximate.

## 3. Lossless compression / archival options

Constraint honored throughout: **no information permanently lost** — every
option below preserves full event history and can restore a bead bit-for-bit.
Hard deletion (`sase bead rm`) is therefore excluded as an archive mechanism.

### Option A — Hot/cold projection split (cheapest, no format change)

Keep serving `issues.jsonl` hot-only (non-closed, ≈590 rows / ≈1.7 MB) and
move closed rows to `issues.closed.jsonl`. All list/search/ready/blocked
defaults read hot; add `--include-closed` / `--closed-only` that also loads
cold. Zero format change, fully reversible by concatenation, ~12× smaller
default parse. **Limitation:** the event-store path (2,108 stream files)
still dominates load — this alone only fixes the legacy/compat path, so it
must be paired with stream partitioning (Option B) to matter.

### Option B — Partitioned event streams + cold archive sidecar (recommended core)

Move streams of eligible closed top-level families out of
`events/streams/` into a versioned archive (same stream format, so no codec
change): either `events/archive/<yyyymm>/` in-tree or, better, the existing
`beads-archive` sidecar pattern the repo already uses for plans/research.
Leave a **tombstone pointer** in the hot store (`archived_to`, stream ID,
content hash, event count) so that:

- `resolve_id` / `show` / `history` on an archived ID lazily materialize
  from the archive (or print the archive ref) instead of failing;
- `doctor` can still verify hash-chained integrity across the boundary;
- `reopen` transparently repatriates the stream.

Eligibility gate (all must hold): status closed; no open descendants; no
active blockers/dependents (`blocked`/`ready` must be provably unaffected —
closed beads only ever satisfy dependencies, but the gate should assert it);
no unresolved bead-owned artifact links; archive age > threshold (e.g.
closed > 90 days; never archive the current release's beads). Phases
(70% of rows) archive as part of their epic's subtree, never solo, so the
epic→phase→task hierarchy stays jointly restorable.

### Option C — Compaction without moving anything

- Prune **redundant close events** (doctor already reports them: 457 across
  319 beads today) with a history-preserving compaction (mark superseded,
  don't rewrite published bytes — the append-preserving writer already
  enforces prefix immutability, so compaction must be a new-event
  "supersedes" marker or an offline migration, never a silent rewrite).
- Garbage-collect `pages/` for long-closed beads (33 MB, 816 entries) with
  regeneration on demand; pages are derived artifacts, losslessly rebuildable.
- Enforce the existing small-line discipline (notes/edits append events;
  attachments stay in `assets/` by reference, not inline).

### Option D — Indexed reads (the structural fix; archive complements it)

Serve `show`/`history`/`resolve_id` from an index instead of a full reduce:
the `beads.db` SQLite compat mirror already has schema/codec/migration
machinery (`src/sase/bead/db.py`, `_db_*`) — promote it (or a lighter
manifest→stream-offset index) to the serving path for point reads, with the
event store remaining canonical and doctor asserting projection equivalence.
This turns the most common agent op from O(N) into O(1) and is the only option
that helps reads *without* moving any bead. Estimated effect at 7k: point
reads drop from ~1–4 s toward startup floor (~0.5 s).

### Option E — Git/clone-level relief (helps distribution, not latency)

Shallow or partial clone of the beads sidecar for ephemeral workspaces;
`pages/` and `assets/` on a separate ref/branch so `--depth 1` checkouts skip
33 MB of derived pages; `git gc` cadence on the sidecar. Note: this reduces
network + disk, not per-op CPU — do it for workspace-spinup time, not bead
latency, and never as a substitute for B/D.

### What NOT to do

- **Do not `rm` old beads to "go faster."** Lossy, breaks links/history, and
  the speedup is identical to archival without the safety.
- **Do not gzip `issues.jsonl`/streams in place.** Kills `git diff`
  readability (a relied-upon property: commits are reviewed as diffs), saves
  little (git pack already compresses; working-tree bytes are the load cost,
  and compressed bytes must still be decompressed per op).
- **Do not split by creating a second live store.** Two writable bead stores
  for one project forks identity/counter allocation (`next_counter`, prefix
  policy) — the archive must be read-mostly with exactly one writer path
  (the archival migration itself).

## 4. Critique of the plan

**Is "compress/archive old beads for performance" a good idea? Partially —
the diagnosis is right, the prescription is incomplete.**

Fair points in its favor: the 92%-closed measurement vindicates the instinct
(nearly all per-op work serves dead beads); the event format is already
append-only and content-addressable-friendly, so moving streams is safe; and
clone weight (195 MB, 101 MB pack, +1 × ~20 MB blob per mutation) genuinely
grows without bound.

But four objections, in decreasing order of importance:

1. **It optimizes the wrong layer first.** Per-op latency comes from
   full-scan reads, not from bytes at rest. Archiving 6,444 closed beads
   without indexed reads converts "every op loads 7k beads" into "every op
   loads 590 beads + every history query loads the archive" — good for the
   common case, but the tail (search-all, doctor, reopen, audit) still scans
   everything, just across two stores. The durable fix is D (index), with
   archival as the capacity companion, not the other way round.
2. **Closed beads are load-bearing.** `ready`/`blocked` derivation, epic
   subtree expansion, artifact-link provenance, close-history/`lost_notes`
   audits, and `reopen` all traverse closed records. Any design that makes
   closed beads second-class must prove each consumer still resolves —
   hence the tombstone + lazily-materializing requirement in §3B, which the
   naive "move old files away" plan lacks.
3. **195 MB is not a storage emergency.** Framing this as compression risks
   over-engineering (custom codecs, migration risk) for a problem whose user-
   visible symptom is seconds-per-command. Partitioning + pages GC + index
   gets ~90% of the benefit with boring, reversible mechanics.
4. **Unstated requirements need stating:** archival eligibility rules,
   reopen semantics, doctor coverage across the boundary, and a rollback
   (repatriation) procedure. "Without losing information" must mean
   bit-restorable + link-resolvable + doctor-verifiable, and acceptance
   should assert all three, not just row counts.

## 5. Requirement adjustments (explicit)

1. **Restate the goal as latency-per-operation**, with acceptance thresholds
   (e.g. p50 `stats`/`ready` < 1 s, point `read` < 1 s at 2× current N),
   not "smaller store".
2. **Archive means move + tombstone + lazy fetch**, never delete; `rm`
   stays out of scope.
3. **Closed-epic-subtree granularity** (epic + its phases/tasks together),
   not per-bead cherry-picking — phases are 70% of volume and meaningless
   outside their epic.
4. **Add the index deliverable** (point reads O(1)) alongside archival;
   archival alone does not fix tail queries.
5. **Doctor-gated**: archive migration must keep `sase bead doctor` green
   including cross-boundary integrity, and add an `--include-archived` audit
   mode.

## 6. Recommended solution

**Phase 1 (no format change, immediate relief):** hot/cold projection split
(open-only `issues.jsonl` + `issues.closed.jsonl` with opt-in flags) and
`pages/` GC for long-closed beads with on-demand regeneration. Expected:
default-parse −90%, clone −~30 MB, fully reversible.

**Phase 2 (the actual archive):** age- and eligibility-gated migration of
closed epic subtrees to the archive sidecar in native stream format, with
hash-bearing tombstones in the hot store and lazy `show`/`history`/`reopen`
across the boundary. Expected: stream-file opens cut ~proportionally to
archived families; working-tree and pack growth flatten.

**Phase 3 (structural):** promote indexed point reads (SQLite mirror or
stream-offset index; event store stays canonical) so single-bead ops stop
paying O(N) at any N. Re-measure §2's table at each phase; stop when the
acceptance thresholds in §5 hold at 2× N.

First step if this is accepted: a bead (naturally) specifying the
eligibility gate, tombstone schema, doctor rules, and the latency acceptance
table — implementation after that is three small migrations, none of them a
rewrite.

## Appendix — Method and provenance

- Store census: `du`, `wc`, `git count-objects -vH`, `git log --stat`,
  `sase bead stats` / `sase bead doctor` in workspace 17 on 2026-10-06.
- Code paths: `src/sase/bead/_project_queries.py`,
  `src/sase/bead/_project_store.py`, `src/sase/bead/db.py`,
  `src/sase/bead/project.py`, and the Rust core
  `bead/read.rs`, `bead/jsonl.rs`, `bead/mutation/store.rs` (read via the
  workspace's linked `sase-core` checkout).
- Deliberately not consulted: sibling swarm reports (`__cdx`/`__cld`/`__grk`/
  `__gem`) and their transcripts — conclusions above are my own.
