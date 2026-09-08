# Eliminating Artifact-Link Merge Conflicts

Date: 2026-09-08

**Decision:** adopt immutable, content-addressed link events, with a serialized host-owned publisher for automatic mutations. Use a conservative resolver for existing JSON indexes during rollout. This combines A's stronger storage guarantee with B's useful publisher design, while correcting assumptions about replay and migration.

This is a research recommendation, not an implemented change. It targets ordinary artifact-link metadata conflicts; concurrent edits to report prose remain normal document conflicts.

## Evidence and scope

The independent inputs are [report A](artifact_link_event_store__a.md), registered for `research.1o.cdx`, and [report B](artifact_link_event_store__b.md), registered for `research.1o.cld`. Both were read through their canonical `research:` references. B's registered snapshot, `file:explicit:e94c860aa400ceb91ce6f134`, was also read to recover its complete output. The files retain their original A/B assignments and are preserved byte-for-byte here. A's registered snapshot is `file:explicit:1284eebfc6f4e184f8b62d10`.

I independently inspected SASE at `77b7e5ea05da528cc2b680e14630f4ca11812117`, sase-core at `a98156150e5f76fb58a982da4650170177cc9d39`, and research-sidecar history at `c9584db6814f2423e9a4e6c1ecf42e91d3f7e4c0`. I ran small merge and reducer probes, and read the opening architecture discussion of `research:202605/greenfield_bead_storage_architecture.md` through `sase artifact read`. **No predecessor chat transcripts were opened for this consolidation.** Details of the example agent's two pauses come from A/B; its resulting link history was independently checked.

## What causes the conflict

Each document has one tracked `links/<document-relative-path>.json` containing its entire link neighborhood. Reading a popular report changes that same file in every agent's independent clone:

1. `artifact_cli/read.py::_record_read_link` immediately calls `store.upsert_row`, then queues the resulting row in the local outbox.
2. `_artifact_link_store_rows.py::upsert_row` writes each document endpoint's index.
3. `_artifact_link_store_sidecar.py::_upsert_sidecar` reads the array, changes it, and replaces the whole file under a local lock.
4. Finalization or link publication commits those paths. Concurrent branches must then integrate their different versions of the same file.

The lock protects processes using one checkout. Different clones have different lock files, so it cannot prevent this conflict. Deterministic row sorting would improve diffs but would not remove overlapping edits or add/add conflicts.

In the `research.1n.cdx` example, multiple readers created or updated `links/202609/remote_machine_management_enablement.md.json`. A/B report an initial add/add conflict and another conflict after resuming. Sidecar commits `f9c7d86`, `3c5b047`, and `3427d6a` corroborate the accumulation of reads from `research.1n.cld`, `088`, and `research.1n.cdx` respectively.

This is meaningful operational traffic: A/B counted about 126–127 link-only commits among 451 research commits, roughly 28%. Their snapshots differ, so these are approximate historical measurements, not a measured conflict rate. My own audited reads also created untracked link indexes in this checkout.

Both SASE integration paths currently repair bead conflicts only: `_repository_integration.py::_repair_or_abort_rebase` and `_git_commit_dispatch.py::_continue_rebase_resolving_beads`. The latter explicitly requires every unmerged path to start with `beads/`. There is no equivalent recovery for document link indexes.

## What the bead work establishes

Beads provide the right pattern: canonical append-only events, generated projections, deterministic semantic reconciliation, and serialized local publication. In the inspected implementation:

- `events/streams/<bead-id>.jsonl` contains events; `issues.jsonl` and pages are projections.
- Rust's `merge_bead_event_streams_with_relocation` validates append-only branches and combines event additions deterministically.
- The Python conflict resolver integrates that result and rebuilds generated state.
- `run_managed_sync_worker` takes publisher/store locks and retries publication with re-integration.
- Bead endpoints of artifact links already use `LinkAdded` and `LinkRemoved` events.

**Beads still need a semantic resolver because concurrent writers can touch the same stream.** B overstates the precedent when it calls that storage conflict-safe without qualification. The reusable lesson is how to preserve and reconcile operations. Artifact links can go further by giving each operation its own immutable path.

## Resolving the disagreements

### Replay is not currently idempotent

B's fetch/reset/replay proposal depends on an incorrect premise: deduplicating an edge's identity does not make its mutation idempotent. Rust's `upsert_artifact_link_row` increments `uses` for an existing read and replaces its description.

Using the current Python adapter and installed `sase-core-rs` 0.32.43, I submitted the identical read row three times. There was one edge, but its `uses` values were **1, 2, 3**. The Python adapter specially converges prompt-reference counts; it does not apply that policy to reads.

The current outbox provides a different, limited protection: `_converged_rows` keeps the maximum cumulative count for each key. Three separately identified queued rows, each with `uses=1`, reduced to **one row with `uses=1`** in my probe. Consequently, simply removing the eager upsert and queuing today's initial row would lose repeated-read counts. Stable operation identity must reach the durable store; an outbox ID that is discarded during reduction is insufficient.

### Neither proposed legacy counter formula is universally correct

Suppose the base count is 1 and both branches contain 2:

| History behind those identical snapshots | Correct result |
| --- | ---: |
| Each branch recorded a different new read | 3 |
| Both branches replayed the same read | 2 |

B's `max(uses)` loses the first history. A's `ours + theirs - base` double-counts the second. The snapshots do not retain enough identity to distinguish them. Likewise, `created_at` stays fixed during description changes, so choosing the "later description" from that field is unsound.

A legacy resolver should confidently merge distinct-key additions and unambiguous three-way changes. It should preserve evidence and refuse ambiguous same-key counter, description, and remove/update combinations unless operation-level audit evidence resolves them. Do not advertise exact recovery from information the format never stored.

### A local publisher helps, but its guarantee has conditions

B correctly identifies the value of removing automatic link writes from agent checkouts. The hidden machine-owned document clone and outbox already exist. However, one publisher **per machine** is not one publisher globally; human commands, other hosts, backfill, and rename repair also matter.

A properly journaled fetch/reset/replay publisher could avoid merges in its exclusively owned clone. It would require stable operation IDs, durable acknowledgements, a complete replay journal, and proof that every unpublished change being discarded is reconstructible. That is substantially more work than replacing an upsert call. In particular, today's outbox can retire entries after a local commit with asynchronous publication; a future reset must not discard the only remaining copy of those operations.

Host batching is worthwhile for ownership and commit pressure. Immutable events make cross-host convergence independent of that serialization and avoid requiring destructive reset/replay for ordinary publication.

### JSONL plus union is viable, but not the strongest choice

B correctly notes that Git's `union` driver is built in and needs no per-clone driver installation. It combines lines rather than understanding their meaning, and Git explicitly leaves output order unspecified. A deterministic event-set reducer would still be required. [Git attributes documentation](https://git-scm.com/docs/gitattributes#_built_in_merge_drivers).

My Git 2.47.3 `merge-file` probes found:

| Input | Result |
| --- | --- |
| Two new pretty-printed v2 indexes for different readers | Ordinary merge reported conflicts |
| Same inputs with `--union` | Exit 0, but duplicate object keys; ordinary JSON decoding retained only one reader |
| JSONL versions changing the same edge's description | Union kept both competing lines; semantic selection remained necessary |
| Identical immutable event bytes added on both sides | Ordinary merge was clean |

These are file-level probes, not a many-clone publication benchmark. B separately reports successful JSONL add/add merge/rebase experiments and a delete/modify conflict. The local probes use Git's documented three-way file operation. [Git merge-file documentation](https://git-scm.com/docs/git-merge-file).

Never apply union to today's pretty JSON. If JSONL is chosen, use immutable operation lines and tombstones, and sort only the projection. B's proposed whole-log sorting/deduplication rewrites conflict with its append-only invariant. Its rejection of writer sharding because one writer cannot remove another's record also overlooks observed-remove tombstones: removal can reference a record without editing it.

## Design choices

| Choice | Benefit | Limitation | Decision |
| --- | --- | --- | --- |
| More retries, locks, or sorted JSON | Smaller race windows or clearer diffs | Shared mutable paths remain | Insufficient |
| Semantic v2 resolver | Automatically handles the dominant distinct-reader case | Limited to managed integration; legacy ambiguities remain | Rollout protection |
| Host publisher with current snapshots | Removes automatic dirt from agent clones | Complete replay protocol and all-writer coverage needed | Useful containment, incomplete alone |
| Immutable JSONL events plus union | Fewer files; common append conflicts combine | Depends on merge attributes and strict log discipline | Reasonable second choice |
| One mutable file per edge or writer | Separates most independent writes | Repeated writes to that shard can still collide | Weaker than per-operation files |
| One immutable file per operation | Independent changes have independent paths; retries have identical bytes | More files and an event reducer | Recommended durable format |
| Central authoritative database | Can serialize global mutations | Adds a service and changes offline/Git ownership | Unnecessary for this problem |

## Recommended architecture

### Immutable durable operations

Use an additive namespace independent of document paths, for example:

```text
link-events/v1/ab/<sha256-of-canonical-event>.json
```

Every event contains a schema version, project identity, stable operation ID, canonical relation-aware edge identity, operation type, provenance, and any observed predecessor IDs. Freeze its complete payload before enqueueing. Use a full-strength operation ID, such as a 128-bit random ID, rather than truncating the current outbox UUID to 12 hexadecimal characters.

Canonical serialization and byte normalization must be specified. Same path with different bytes is corruption or a digest collision: reject it. Ordinary commands create objects only; they never rewrite, rename, compact away, or delete published objects.

The guarantee follows directly: different operations add different paths; a retry adds the same path with identical bytes. Under those invariants, Git has no conflicting content to choose between. Push rejection can still happen, but integration combines additions without a link-file conflict. This guarantee does not cover old writers, event tampering, physical deletion, or unrelated document edits.

### Deterministic semantics in Rust

Implement event validation, canonicalization, and reduction in `sase-core`, expose them through the binding, and keep Python as the storage/publication adapter. Preserve the relation registry, directed/undirected identity rules, and existing CLI removal matching.

- **Observations:** one actual read has one operation ID; retry preserves it. Count distinct observations. Prompt occurrences need stable occurrence IDs or an explicitly identified batch with a fixed count. Repeated derivation/backfill of the same fact must reuse its identity rather than minting endless events.
- **Manual put/update:** record which previous versions it supersedes. A causally later update replaces those versions. For concurrent descriptions, use a documented stable tie-break and retain both versions for inspection. Event-ID ordering suffices as an arbitrary tie-break; adding hybrid logical clocks is not required merely to avoid conflicts.
- **Removal:** append a tombstone naming the versions/observations the remover actually saw. Retain tombstones even when their referenced events have not arrived yet. A concurrent unseen addition survives. This add-wins policy is a proposed product choice and must be documented; it prevents a delayed remover from silently erasing work it never observed.
- **Multiple owners:** store one object per owning sidecar, with identical IDs and bytes across copies. Deduplicate globally by event identity. Preserve bead-store ownership of bead endpoints and carry mutation identity through that adapter so repair does not create a second mutation. Cross-repository publication is eventually complete, not atomic.

The reducer must produce the same logical result from the same event set, regardless of filesystem order, arrival order, or duplicate delivery. Test those properties directly.

### Publication and projections

Automatic reads, citations, derivations, and maintenance should durably enqueue first and update a local pending view. One publisher per project/machine batches operations into the hidden host-owned clones. Hold the publication lock across repository integration and writes; keep queue-append locking short.

Retain operation payloads until publication to every required owner is verified, or until custody passes to another durable recovery journal. Survive interruption after file creation, commit, push, and before acknowledgement. A rejected push should trigger bounded integration/retry; temporary failure leaves a retryable queue, not an agent merge task.

Human link commands should use the same operation API. They can request synchronous acknowledgement to preserve the current published-on-success behavior. If agent commands become enqueue-only, report that status accurately and ensure aggregate rebuilds overlay pending operations instead of dropping them as absent from durable sources.

Keep the current aggregate and Markdown interfaces as projections. Do not recreate the hotspot in a tracked event manifest or a globally rewritten index. Use incremental local indexing; benchmark cold rebuilds and large histories before choosing a new database or compaction mechanism.

Two existing paths require explicit treatment:

- **Renames:** `_artifact_link_renames.py` currently rewrites refs and unlinks old indexes. Event paths must remain unchanged. Record artifact identity/alias changes separately and apply them during reduction. Handle chained and conflicting aliases deterministically, and accept late events carrying an old ref. A reused filename must not accidentally inherit an unrelated artifact's identity.
- **Managed Markdown blocks:** `_artifact_link_refresh.py` can rewrite tables inside authored documents. Restrict generation to the host publication lane and regenerate managed-block-only conflicts from integrated truth, preserving the authored body. If the body itself conflicts, leave it as a document conflict. Otherwise event storage would only move the hotspot into Markdown.

## Rollout and acceptance

1. **Contain existing failures.** Add a strict v2 resolver to both managed integration paths. Handle validated distinct-key unions and unambiguous base-aware edits; fail closed on corruption and unresolved semantics. Measure unresolved link conflicts, publication retries, and outbox age. Do not broaden recovery to arbitrary JSON files.
2. **Build operation identity before changing enqueue behavior.** Introduce the Rust event contract/reducer and an operation-aware durable outbox. Then move automatic writers into the host-owned publication lane. Test counts, pending visibility, and crash recovery together.
3. **Coordinate the cutover.** Deploy capable readers and fence legacy writers before freezing canonical sidecar heads for import. Reads may continue to spool while publication is paused. A new version marker alone cannot stop an old binary that ignores it.
4. **Import once, deterministically.** Produce baseline events from the agreed authoritative legacy state. Deduplicate endpoint copies; preserve existing count/provenance without pretending to recover missing historical operation IDs. Record source heads and import identity. Once imported, baseline events replace those raw snapshots as reducer input. Indefinite raw-v2-plus-event union would resurrect removed links and double-count baselines. Resume event publication after validation; leave old indexes read-only until retirement is safe.

Avoid requiring a full JSONL migration followed by another event-file migration. Keep the legacy resolver while old histories still need integration.

The acceptance suite should use independent clones and two simulated machines, exercise add/add on a new report, many readers of a hot report, exact retry versus repeated read, concurrent descriptions, remove/add and remove/update, stale clones, duplicate endpoint delivery, bead/document links, and rename plus a late old-reference read. Include failures at every publication/acknowledgement boundary, mixed-version rejection, import replay, and managed Markdown regeneration.

Require zero user-visible link-metadata merge pauses, no lost or double-counted operations, verified hashes, and equal logical projections from equal event sets. Exclude machine-local generation counters from byte comparisons. Record p95 queue age, link-only commit volume, warm-read latency, and cold rebuild time. Neither report supplies a fleet benchmark or supports B's projected reduction from 127 commits to 20; batching savings must be measured.

## Recommended solution

**Implement immutable, content-addressed artifact-link events with deterministic Rust reduction, and publish automatic mutations through the existing hidden host-owned lane with durable operation IDs and batching.** Ship a conservative resolver for legacy JSON as rollout protection, and include rename identity and generated-block reconciliation in the design. This removes the shared-write cause across agents and machines while retaining Git-backed provenance. Choose JSONL plus union only if measured file-count costs justify accepting its additional merge and log-discipline requirements.
