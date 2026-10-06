# SASE bead performance and lossless archival: measure replay before archiving

Independent research by **cdx**, 2026-10-06. Other swarm reports and findings were not consulted. This is a research recommendation; no production bead was modified, removed, compressed, or archived.

## Answer and conclusion

**Yes. The number of beads affects present-day SASE bead read and write performance substantially.** The underlying cause is that ordinary Rust queries replay the complete canonical event store, and mutations also regenerate the complete current-state JSONL projection. Closed beads still contribute to that work. The important variables are **current bead count, total historical event count, event bytes, separate stream count, current-state bytes, and contention**, rather than bead count alone.

Measured on an isolated copy of the current SASE project: **7,034 beads, 48,357 events, 2,108 streams, 35.05 MB of event data**. A Rust single-bead lookup took **526 ms**, an active-only list **565 ms**, and a note append **755 ms**. These are warm medians, excluding CLI startup, Git commit/push, attachment handling, and host publication. An actual read-only `sase bead stats` invocation took **1.04 s** median including CLI overhead.

**Recommendation: retain the event history and build a trustworthy, Rust-owned persistent read projection first.** Eliminate repeated migration scans and redundant replay; then make writes update the projection incrementally instead of regenerating all rows. Introduce compressed cold archives only if storage, synchronization, or measured cold-rebuild costs still justify them. Lossless compression is useful, but deleting old beads or merely gzipping their files is not a sound performance fix.

## Evidence and scope

The primary source review used SASE at `22ea0cf4db9b383bb2d907f31f0884cc0de3a6e9` and the linked `sase-core` checkout at `fa390362a556fe156701ee6bdf505411d4f0f7c5`, which also matches SASE's CI revision pin. The runtime measured was `sase-core-rs 0.37.0`, matching the checked-out crate's version. I did not establish the installed wheel's exact build SHA; source findings and runtime observations are therefore reported separately rather than claiming a verified binary-to-commit identity.

The copied beads sidecar was at `2b55fc23becfb28aa58cb0ed81965b05fe906b51`. Its HEAD and file signatures were unchanged during the main copy. Measurements ran on Linux/ext4 on an AMD Ryzen Threadripper 3970X, with 64 logical CPUs. The host was busy, with roughly 25–31 one-minute load during the investigation. Every operation had one warm-up and seven sequential measured repetitions, except the end-to-end CLI sample, which had five. Tables give medians and relevant observed ranges; seven samples are insufficient to claim reliable production p95/p99 latency.

Synthetic stores and real-store mutation tests ran inside disposable local directories. There were no remote pushes or production mutations. The data and scripts are included beside this report in [bead_count_scaling_lossless_archival__cdx_data](bead_count_scaling_lossless_archival__cdx_data/): `bench.py`, `live_bench.py`, `archive_model.py`, and their three JSON results files. The results preserve every measured sample, sizes, versions, and compression checks. They contain aggregate measurements rather than bead descriptions or note bodies.

## What the current implementation actually does

### Reads replay everything

`read_store_issues()` chooses event replay whenever an event manifest or stream directory exists. `show_issue()`, ID resolution, list, ready, blocked, statistics, and search all use that path. Filtering happens after the store has been loaded and reduced. Reading just one known full ID does not bypass replay. `issues.jsonl` is an output projection, not the normal authoritative read source. See [Rust bead reads](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/read.rs#L66) and [search](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/search.rs#L42).

The event loader also runs a legacy flag migration detector on every load. That detector opens every stream and parses its lines as generic JSON, even when there are no retired flag-type records. The loader then opens the streams again for typed parsing. Reduction validates/clones streams, performs a heap merge preserving intra-stream causal order, applies all events into a map, sorts the resulting issues, and checks global external-reference uniqueness. See [JSONL loading and migration](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/jsonl.rs#L146), [reduction](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/events/reduction.rs#L69), and [causal merge](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/events/merge.rs#L786).

A rough cost model is:

```text
read = file enumeration/open costs + parsing all event bytes
     + merging E events across S streams + event reduction/validation
     + sorting/filtering current issues + serialization of requested results
```

The merge term is approximately `O(E log S)` and map operations add approximately `O(E log N)`, before payload-specific work. Parsing and file overhead are often more informative than these asymptotic terms. Validation of growing note/relationship collections can add further work. A simple claim of exactly `O(N)` would be incomplete.

History queries also load and replay global streams. Some Python wrappers, such as `BeadProject.show()` and `history()`, resolve an ID through one complete read and then call another operation that reads again. The newer detail API intentionally takes one snapshot. These are opportunities to avoid duplicate work without changing retention. See [Python query adapter](https://github.com/sase-org/sase/blob/22ea0cf4db9b383bb2d907f31f0884cc0de3a6e9/src/sase/bead/_project_queries.py#L15) and [Rust history](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/history.rs#L53).

### Writes retain store-wide work

`MutableStore::load()` reads/reduces every event stream. `save()` validates the current issue set and stream set, writes selected changed streams, saves configuration, and serializes/sorts/writes **all** current issues to `issues.jsonl`. It no longer writes every unchanged stream. However, its append-preserving stream writer rereads and verifies the existing stream prefix, then atomically rewrites that stream's old bytes plus new tail. A tiny update can therefore rewrite a large epic stream. Atomic file writes sync file and directory data. See [mutation store](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/mutation/store.rs#L295) and [append-preserving writer](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/jsonl.rs#L509).

There are additional Python costs: repository locking, auto-commit, synchronization/publication, possible attachment uploads, and touch-index refresh. Network delay or lock waiting can dominate observed CLI latency. Archiving will not fix a slow remote or an unrelated busy writer. See [CLI mutation lifecycle](https://github.com/sase-org/sase/blob/22ea0cf4db9b383bb2d907f31f0884cc0de3a6e9/src/sase/bead/cli_common.py#L267).

`beads.db` is not evidence that ordinary bead reads are indexed SQL queries: the public project API delegates to Rust and preserves SQLite as a compatibility mirror. Rust also uses that filename as its advisory mutation lock; replacing/deleting it while locked would split lock ownership. A new projection database should have a separate path. See [project adapter](https://github.com/sase-org/sase/blob/22ea0cf4db9b383bb2d907f31f0884cc0de3a6e9/src/sase/bead/project.py#L34) and the mutation-store lock comments.

## How much does bead count matter?

### Controlled count scaling

Synthetic tasks had a 256-byte description, one creation snapshot each, separate streams, and approximately 95% closed status. Closing was encoded in the creation snapshot to isolate bead count from extra close events; this is not a claim that actual beads have only one event. All stores passed the Rust stats/count check. Writes appended a small note to one active bead.

| Current beads / streams | Single lookup | Open-only list | Statistics | Append one note | Replay + rewrite projection |
|---:|---:|---:|---:|---:|---:|
| 100 | 2.6 ms | 2.6 ms | 2.6 ms | 53.2 ms | 25.6 ms |
| 1,000 | 29.5 ms | 31.2 ms | 31.1 ms | 106.8 ms | 54.4 ms |
| 5,000 | 176.3 ms | 178.2 ms | 173.6 ms | 234.8 ms | 240.7 ms |
| 10,000 | 358.7 ms | 349.5 ms | 344.4 ms | 494.9 ms | 446.8 ms |

A tenfold increase from 1,000 to 10,000 beads made lookup **12.2× slower** and note append **4.6× slower** in this experiment. Moving from 100 to 1,000 made lookup **11.2× slower**, while append slowed **2.0×**. Fixed sync costs and noisy storage latency make write speedup differ from read speedup. The 100-bead note measurements ranged from 46 to 126 ms; precision beyond these broad conclusions would be misleading.

The open-only list gained almost nothing over statistics or single lookup because closed histories were still replayed. A result limit similarly limits output, not the initial store replay.

### History, bytes, and layout matter independently

| Fixed at 1,000 beads | Events | Streams | Single lookup | Append note |
|---|---:|---:|---:|---:|
| Tasks, one event each | 1,000 | 1,000 | 29.5 ms | 106.8 ms |
| Tasks, five events each | 5,000 | 1,000 | 49.4 ms | 100.0 ms |
| Tasks, 25 events each | 25,000 | 1,000 | 129.9 ms | 172.0 ms |
| Tasks, one event, 8 KiB descriptions | 1,000 | 1,000 | 42.1 ms | 130.8 ms |
| One epic and 999 phases, one event each | 1,000 | 1 | 11.9 ms | 61.8 ms |
| One epic and 999 phases, 25 events each | 25,000 | 1 | 132.5 ms | 248.4 ms |

At constant count, 25× more events increased task lookup **4.4×**. Fewer streams helped the short-history case **2.5×**, but did not help the long-history case, where replay dominated; its writes were slower because a much larger shared stream was rewritten. The epic case changes issue types as well as layout, so it is indicative rather than a perfect isolated syscall experiment. The non-monotonic five-event write result illustrates write noise, not a benefit from adding history.

### Current-project measurements

The real store contained 6,444 closed beads and 590 active beads, including one snoozed task. Flags are typed task beads, not a fourth disjoint issue type. Do not add the flag statistic to task/plan/phase counts.

| Operation on isolated real-store copy | Median | Observed range |
|---|---:|---:|
| Rust single-bead lookup | 525.7 ms | 497.5–540.8 ms |
| Rust active-status list | 565.5 ms | 541.0–643.7 ms |
| Rust statistics | 530.2 ms | 523.9–555.5 ms |
| Rust append note | 755.1 ms | 725.5–799.8 ms |
| Rust replay + export projection | 673.2 ms | 649.1–793.6 ms |
| Legacy flag detector alone | 149.5 ms | 147.4–164.6 ms |
| Read complete existing JSONL projection directly | 238.5 ms | 234.9–240.9 ms |
| Warm existing touch-index refresh | 52.8 ms | 51.8–55.7 ms |
| Actual `sase bead stats` wall time | 1,040.6 ms | 1,002.2–1,473.2 ms |

The flag detector accounts for roughly **28% of single-lookup median time** as an independently measured component. Removing it from the steady-state path could save about 150 ms here, but that is an estimate, not a measured optimized build; remaining replay would still be substantial.

The touch index already demonstrates derived, incremental caching in SASE. Its warm refresh scans signatures and reuses cached rows; the initial build took 369 ms. It is an implementation pattern, not a complete bead read projection. Its mtime/size signatures and independent per-stream touch reduction are insufficient by themselves to prove a correctness-sensitive full-state cache valid. See [existing touch-index refresh](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/touch_index.rs#L806).

Two explicitly **counterfactual** experiments show the headroom:

- A projection containing just the 590 active current-state rows occupied 2.44 MB and gave a 9.3 ms lookup / 19.8 ms list through the legacy JSONL reader. This omits history and cold-reference resolution. It is not a usable archival implementation and must not replace the live store.
- A local SQLite table containing all 7,034 fully serialized current-state rows gave a **0.152 ms** point lookup including opening a connection and decoding the selected JSON. This omits cache validation, relationships, mutation protocol, and production bindings. The large ratio to replay shows architectural potential; it is not a promised 3,000× production speedup.

### Estimating archival benefit honestly

Currently closed beads account for **44,145 / 48,357 events (91.3%)** and **31.18 / 35.05 MB of event bytes (89.0%)**. That makes retaining them outside the replay path promising. However, 92% closed beads does not imply that 92% of the whole command can disappear.

Use `T_after ≈ T_fixed + (1 − f) × T_replay + T_index/restore`, where `f` is the excluded share of actual replay work. Removing 89% of replayed bytes might reduce that component roughly ninefold if parsing dominated. Git/network/sync costs, retained mixed epic streams, and cold relationship lookups remain. Neither this estimate nor the active-only experiment establishes an end-to-end archival speedup. A production prototype must measure that.

Of 2,108 physical streams, **1,540 have only closed currently existing rows**, 518 have active/mixed rows, and 50 have no current rows. These are rough candidate counts, not validated archival eligibility: age, dependencies, references, deleted history, pending work, and global reducer semantics were not evaluated.

## Compression and archival options

| Option | Expected effect | Information and implementation implications |
|---|---|---|
| Filter/limit displayed results | Less output/rendering | Already useful; does not avoid store replay. |
| Delete closed beads with `rm` | Smaller current projection | Adds tombstones but retains ordinary event streams; replay continues, dependencies are removed, ordinary ID lookup disappears. This is deletion behavior, not archival. |
| Git maintenance/packing | Smaller/faster Git object storage | Does not reduce worktree JSONL enumeration or event reduction; it addresses a different cost. |
| Compress every stream and still replay all of them | Fewer stored/transferred bytes | Adds decompression and format support; CPU replay remains. Small compressed files still incur many opens. |
| Cache current state; retain raw event files | Faster point/filtered reads | Best first step. A disposable projection can recover from canonical events; no archival semantic change is needed. |
| Snapshot + retained history segments | Faster cold state reconstruction | Must include a proven event frontier and all reducer state; history is retained rather than replaced. |
| Immutable compressed cold packs + hot index/state | Bounded hot working set and smaller worktree | Supports old IDs/history on demand; requires explicit catalog, restoration, references, sync, and migration semantics. |
| Separate archive repository/service | Small primary checkout/clone | Adds availability and dependency management. A missing archive cannot silently mean a missing bead. Probably unnecessary at today's size. |
| LLM summaries / overwrite old events with final state | Smaller semantic representation | Loses exact notes/revisions, provenance, and intermediate history unless originals are separately retained. Summaries may supplement an archive, never replace it. |

`rm` appends `IssueRemoved`, leaves its stream, and drops dependency edges from current issues. The reducer also removes those edges. See [removal behavior](https://github.com/sase-org/sase-core/blob/fa390362a556fe156701ee6bdf505411d4f0f7c5/crates/sase_core/src/bead/mutation/close_remove.rs#L517). A removed bead count can therefore fall while historical replay remains expensive.

Git's documentation describes packing revisions and housekeeping; that does not change the application loader's worktree reads. Keep explicit durable refs/backups for retained history instead of relying on unreachable objects or reflogs, which maintenance can expire. No Git history rewrite is proposed. [Git maintenance](https://git-scm.com/docs/git-gc), [Git packfiles](https://git-scm.com/book/en/v2/Git-Internals-Packfiles).

### Actual lossless compression measurements

All sizes here use decimal MB. Compression timings are single runs, not medians. Codec round trips were compared for exact byte equality.

| Real event payload | Raw bytes | Compressed bytes | Reduction | Encode / decode |
|---|---:|---:|---:|---:|
| Concatenated streams, gzip level 6 | 35.05 MB | 8.07 MB | 4.35× | 672 / 93 ms |
| Concatenated streams, Zstandard level 3 | 35.05 MB | 7.36 MB | 4.76× | 122 / 63 ms |
| Filename-preserving event tar, gzip level 6 | 36.67 MB | 8.17 MB | 4.49× | 667 / 88 ms |
| Filename-preserving event tar, Zstandard level 3 | 36.67 MB | 7.41 MB | 4.95× | 126 / 58 ms |

The event tar was built after the isolated note benchmark, so it includes eight extra test notes; the concatenation was captured before those notes. This difference is negligible for the size comparison but matters for precise reproducibility.

A second experiment packed original event files, manifest, configuration, and `issues.jsonl` together: **12.63 MB compressed**. Decompression recovered **2,111 files with identical names and exact bytes**. This demonstrates preservation of those canonical-state files. It does not cover attachments, referenced plans/research, Git commit history, filesystem metadata, remote replication, or a functioning archive reader.

Synthetic data compressed by dozens to hundreds of times because its descriptions and metadata were deliberately repetitive. Those ratios are **not representative**; the real-store 4–5× results are the useful planning baseline. Compression efficiency also depends on pack size. [Zstandard's upstream overview](https://facebook.github.io/zstd/) describes its configurable speed/ratio tradeoff; SASE-specific numbers above come from this investigation.

Prefer bounded immutable packs containing independent compressed frames or an indexed container when direct cold lookup matters. A giant `tar.zst` is simple for backup, but a tar member lookup normally requires decompressing preceding compressed data. Monthly or size-limited packs bound that penalty; a per-stream locator/index avoids scanning unrelated packs. Do not rewrite a growing compressed pack on every bead update. Old compressed packs can also reduce Git's ability to delta similar plaintext revisions, so compression inside Git is not automatically a repository-size win.

## Critique and justified requirement adjustments

The request identifies a real performance problem, but **archiving by bead age should not be the initial requirement**. Today's roughly 35 MB of canonical events is small for storage yet expensive to replay per action. Indexed lookup addresses the actual mechanism, protects all existing references, and also benefits active beads with long histories. Archiving alone postpones the same problem as new history accumulates and adds a substantial lifecycle subsystem.

I recommend these explicit adjustments:

1. **Replace “reduce bead count” with “reduce unrelated history on hot read/write paths.”** Track event bytes, event count, stream count, projection size, lock time, and publication time alongside N.
2. **Define losslessness as preserving exact canonical event bytes and recoverable complete history.** Preserve edited/retracted note contents, actor/timestamp/event IDs, reasons, close/reopen history, +1 evidence and observation windows, links/provenance/operation receipts, task fields, dependencies, ID/collision mappings, and retained attachment payloads. Current-state JSON alone is not full history.
3. **Require old IDs and artifact references to remain usable without manual repository archaeology.** Existing detail/history/search/closed-list semantics must remain accessible. An explicit archived indicator may be added; archive residency should not become a replacement workflow status. Default-list fallback to closed beads when none are active must still work.
4. **Treat archival eligibility as graph- and stream-aware, with a configurable idle period rather than a guessed universal age.** Whole settled epics/streams are preferable initially. Pin active/in-progress/claimed/ready/snoozed work, pending gates/launches, unresolved descendants, and operationally relevant references. A closed task may later reopen through valid new +1 evidence.
5. **Separate retaining current indexed state from retaining full history on disk.** Keep all bead current-state rows queryable in an indexed projection, while cold history can be compressed. Closed rows need not disappear from the index for hot queries to be fast.
6. **Make cold storage operationally durable:** verified manifests/checksums, schema/reader versions, replicated bytes or protected VCS locators, atomic catalog publication, idempotent restoration, explicit missing/corrupt-archive errors, and restore drills. A single compressed file or an unreferenced Git object is not a durable retention policy.
7. **Keep this as research until a measured prototype preserves existing semantics.** Do not perform production cleanup merely because closed-count metrics look high.

Suggested initial acceptance targets, to refine on a stable test host: warm point lookup below 20 ms, active-list backend below 100 ms at the current corpus, and approximately flat point-read cost as old history grows tenfold. These are engineering targets, not achieved production results. Record end-to-end CLI and publish latency separately; choose a write target only after splitting replay, serialization, sync, locking, and remote publication.

## A safer design and implementation sequence

### First: trustworthy current-state projection

Implement shared storage/projection behavior in `sase_core`, expose bindings, and update SASE's core revision pin with the Python adapters. Do not add a competing Python storage engine.

Use a separate local derived database, such as `bead_projection.sqlite`, whose data can always be rebuilt from canonical events. Index full IDs, parent IDs, status/type/tier/creation order, external references, dependency endpoints, and relevant link identities. Retain full current-state rows for closed as well as active beads; queries should load only requested rows. Indexed equality lookup has logarithmic rather than full-table-scan cost. [SQLite query planning](https://www.sqlite.org/queryplanner.html).

Bind each projection generation to a canonical store revision/dirty-state identity, schema/reducer version, and consumed stream frontiers. All supported writers and incoming sync/merge paths must invalidate or update that generation under the existing store transaction protocol. Unknown changes, corrupt caches, or unproven freshness should trigger validation/rebuild, not stale state. A warm CLI invocation needs to avoid both full JSON parsing and full hashing of every historical byte. Start with conservative metadata/change detection where necessary, measuring its `O(S)` cost, and strengthen identity at write/sync boundaries.

For a first safe version, reuse complete validated reductions for unchanged generations and rebuild globally on change. Then optimize mutation/sync updates. Avoid assuming every stream can be reduced independently: dependency-added events require targets to exist, removed beads alter other dependencies, duplicate external references are reconciled globally, and independent streams are interleaved by the causal merge. Backdated events, stream relocation, collisions, and divergent Git merges can invalidate incremental assumptions. Rebuild affected dependency components or the whole projection whenever equivalence cannot be proven.

Optimize the legacy flag migration path so validated modern unchanged streams are not generically reparsed on every query. Keep compatibility with legacy or newly merged streams; a single “migration complete” marker without incoming-content invalidation would be unsafe.

Use the existing persistent touch index as an architectural example, but not as authoritative state: it stores different, sometimes shortened information. If using SQLite WAL, keep the database machine-local, synchronize writers, and handle checkpoints. WAL permits concurrent readers with one writer and does not work across a network filesystem. [SQLite WAL](https://www.sqlite.org/wal.html).

Preserve case-insensitive substring and regex search behavior. Replacing it with default word-token FTS changes results. SQLite's trigram tokenizer supports substring indexing, but short queries and regex still need compatible fallback and Unicode checks. [SQLite FTS5 trigram documentation](https://www.sqlite.org/fts5.html#the_trigram_tokenizer).

### Second: remove write amplification without weakening durability

Measure the remaining write stages. Update changed projected rows transactionally and keep canonical events durable. Move full compatibility JSONL materialization to an explicit, verified export/checkpoint only after auditing every consumer that reads it. Alternatively, shard derived output if preserving a continuously portable projection is necessary. Simply deleting `issues.jsonl` would break compatibility/doctor/export expectations.

Improve the event-tail writer only with a crash/merge-safe publication protocol: current prefix verification and atomic replacement protect immutable history. Do not trade fsync/durability away for a favorable benchmark. Batch supported multi-bead changes under one transaction/replay rather than issuing many separate commands.

### Third: compressed cold history if measurements justify it

Begin with backup/checkpoint packs that leave the canonical raw files untouched. Advance to actual cold placement only once all readers understand both locations:

- Archive an entire settled stream/epic at a proven revision. Retain exact bytes in immutable checksum-addressed packs and publish a manifest mapping stream/bead IDs to locations, event frontiers, hashes, and schema version.
- Keep queryable current-state rows, dependency/link registries, global uniqueness and ID allocator high-water marks. Archived IDs and child ordinals remain reserved.
- Keep enough exact provenance to answer current link/detail queries; a shallow archived stub is insufficient if it changes displayed fields or relationship behavior.
- On history access, locate and verify the required pack. On reopen or any mutation of a cold bead, restore/hydrate its relevant component under the store lock before applying the new event. Preserve its original history and IDs rather than importing a replacement creation snapshot.
- Verify byte hashes, reconstructed logical state, references, and typed artifact resolution before retiring the raw copy. Preserve attachment bytes and referenced records through their own retention contracts. Gate publication on archive availability to another machine, not merely successful local compression.

Snapshots can shorten reconstruction, but they must include all relevant reducer/provenance state and a valid frontier. They supplement immutable event history; they do not replace it. [Microsoft's event-sourcing snapshot guidance](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing).

Required prototype checks include full replay versus cached state, edited/retracted notes, closed-task +1 reopen, ancestors/descendants, cross-stream dependencies and links, duplicate external references and collision relocation, backdated appends, incoming divergent histories, two writers, process crashes between persistence steps, failed archive publication, corrupted/missing packs, and offline restoration. Keep the original format readable during rollout and allow recovery from canonical bytes.

## Recommended solution

**Choose a Rust-owned persistent indexed projection backed by the existing immutable event store, then optimize writes; defer actual bead removal from the hot store.** The measured 526 ms lookup is mostly unrelated historical work, and a replay detector alone consumes 150 ms. Eliminating that recurring work has better performance potential and fewer reference/history hazards than inventing archival semantics first.

Retain every canonical event. Add verified Zstandard checkpoint backups if compact durable copies are immediately useful—the real corpus demonstrated approximately 4–5× event compression and exact restoration. If future measurements show storage or rebuild pressure, extend that mechanism into immutable bounded cold-history packs with indexed current state and transparent old-ID/history access. Success should mean **history growth no longer slows ordinary bead operations, while complete information remains verifiably retrievable**, not merely a smaller bead count.
