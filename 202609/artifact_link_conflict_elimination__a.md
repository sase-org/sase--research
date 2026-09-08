# Making Artifact-Link Conflicts Practically Impossible

**Researcher:** A (`research.1o.cdx`)  
**Date:** 2026-09-08  
**Scope:** SASE artifact-link durability and publication; independent of researcher B

## Executive conclusion

The conflict is caused by the unit of storage, not by weak retry logic. SASE stores the
complete neighborhood of an artifact in one tracked `links/<artifact>.json` snapshot.
Every agent that reads the same popular report rewrites that same file in its own clone.
Local `flock` locking cannot coordinate clones or machines, so concurrent, correct
writes necessarily become Git add/add or content conflicts.

The best durable design is a **set of immutable, content-addressed link events**, with
one newly created file per logical mutation and no ordinary updates or deletions.
Because different mutations have different paths and an exact retry has the same path
and bytes, Git has nothing to conflict over. The existing machine-local aggregate and
Markdown tables should remain derived projections. SASE should also immediately stop
writing automatic read links into agent-owned sidecar clones and add a schema-v2
semantic resolver as a migration safety net.

This is stronger than merely copying the bead resolver. Beads still append to a shared
per-bead stream and therefore need semantic conflict repair. Artifact-link mutations are
small and independent enough to be sharded one step further, so ordinary link
publication can avoid a shared writable path altogether.

## Method and evidence

I inspected:

- the completed transcript for `research.1n.cdx`,
  `~/.sase/chats/202609/gh_sase_org__sase-ace_run-research_1n_cdx-260908_090340.md`;
- the resulting research-sidecar history and link-index diffs;
- the artifact-link CLI, store, outbox, commit, and SDD integration code in `sase` at
  `a0ac015e0bda1d0cc1e1eeb859e92e2f0314cdfe`;
- the artifact-link row and bead-event merge semantics in `sase-core` at
  `630323fcefea5ef266ce4653e4a0c0a39fa75f16`; and
- the prior consolidated artifact-link design report through an audited
  `sase artifact read`.

I did not inspect the other report from the current swarm.

## What happened in the example

The earlier agent's transcript records two conflict rounds in the same index:

1. Two researchers independently read
   `research:202609/remote_machine_management_enablement.md`. Each branch added the
   previously absent `links/202609/remote_machine_management_enablement.md.json`,
   producing an add/add conflict.
2. The agent semantically preserved both records and resumed.
3. The resume fetched another valid read from agent `088`, causing a second conflict in
   the same file.
4. The final resolution retained three distinct rows in chronological order.

The rebased sidecar history preserves the result:

- `f9c7d86` introduced the index with the `research.1n.cld` read;
- `3c5b047` added the `088` read; and
- `3427d6a` added the `research.1n.cdx` read to the already integrated two-row file.

No writer was wrong. The merge conflict was the storage format correctly exposing that
multiple branches had rewritten the same aggregate document.

## The conflict is structural

The current write path has five relevant properties.

1. `src/sase/artifact_cli/read.py::_record_read_link` calls `store.upsert_row(row)`
   immediately and only then appends the replayable outbox entry. The outbox therefore
   does not isolate an agent checkout from canonical link file changes.
2. `src/sase/sdd/_artifact_link_store_rows.py::upsert_row` writes the row to every
   document endpoint that has a sidecar owner.
3. `src/sase/sdd/_artifact_link_store_sidecar.py::_upsert_sidecar` reads the complete
   per-artifact JSON object, updates its `rows` array, and atomically replaces the
   complete file. Its sibling lock protects processes sharing one filesystem clone, not
   another workspace or machine.
4. `src/sase/sdd/_artifact_link_commit.py` commits those index paths and verifies
   publication. When the remote advanced independently, the publication path must
   integrate histories.
5. `src/sase/sdd/_repository_integration.py` invokes only the bead conflict resolver.
   Artifact-link indexes are unsupported conflicts, and managed Git commands explicitly
   disable ambient `rerere` in `src/sase/sdd/_git.py`.

The row itself is also mutable. In
`sase-core/crates/sase_core/src/artifact_link/wire.rs`, an upsert rewrites the
description and increments `uses` for `read` and `prompt_ref`. Link removal rewrites the
array again. A plain line union is therefore not a complete semantic merge: two branches
may change the same counter, change a description, or remove versus update the same
edge.

### Measured pressure in the research sidecar

At sidecar revision `90a7f5a04704f6a54a8aef5fb91962a4a7400df4`, before this
investigation's own audited prior-report read, the repository contained:

- 264 tracked link-index files;
- 539 physical row copies;
- 107 indexes with more than one row;
- a hottest index with 17 rows; and
- 126 `chore(artifact-links): persist link indexes` commits out of 451 total commits.

Those 126 commits touched 445 JSON paths and no Markdown paths. The link tree occupied
about 1.4 MiB in the working tree. This is a small amount of data but a large amount of
coordination. Popular research inputs are exactly the artifacts most likely to be read
by a parallel swarm, so contention grows with the usefulness of the artifact.

After my audited read, the physical row count became 540 and the corresponding existing
index became dirty in this checkout. That side effect reproduces the same architectural
coupling while merely doing research about it.

## What to take from the bead work

The bead implementation contains several proven ideas worth reusing:

- **Append-only truth.** `events/streams/*.jsonl` is canonical and `issues.jsonl` is a
  projection.
- **Stable event identity.** `sase-core` includes a SHA-256 digest of canonical event
  content in bead event IDs.
- **Deterministic convergence.** Concurrent append sets are unioned and ordered
  deterministically. The core tests explicitly exercise branch swapping, associativity,
  idempotence, and sequential rebase replay.
- **Integrity guards.** Published events may not be deleted or rewritten.
- **Semantic repair.** `src/sase/bead/conflict_resolver.py` reconstructs streams from
  Git stages, invokes the Rust merge, rebuilds projections, and stages only the needed
  result.
- **Local ownership reduction.** Recent artifact-link work routes background mutations
  to hidden host-owned sidecar clones, following the bead publication model.

These measures make bead conflicts uncommon and recoverable, but they do not prevent Git
from first observing a conflict because two writers can append to the same stream path.
Artifact links do not require that degree of co-location. Each mutation can be its own
immutable object.

## Options considered

| Option                                          | What it fixes                                             | What remains                                                                                                                              | Assessment                                   |
| ----------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| Retry push/rebase with jitter                   | Simultaneous non-fast-forward pushes                      | Same-path conflicts are deterministic, not transient                                                                                      | Insufficient                                 |
| Route automatic writes through one hidden clone | Same-machine agent/workspace contention                   | Cross-machine writers and foreground link commands still race                                                                             | Valuable immediate mitigation                |
| Add a semantic merge for current JSON snapshots | Common distinct-row add/add and append conflicts          | Same-key counter, description, and remove/update concurrency need policy; Git still enters conflict state                                 | Necessary migration guard, not the end state |
| Store one mutable file per edge identity        | Different readers no longer share one target file         | Repeated reads of one edge and remove/update still conflict                                                                               | Large improvement, incomplete                |
| Append-only JSONL plus Git's `union` driver     | Common concurrent appends can merge without stopping      | Correctness depends on attributes and a textual driver; malformed/rewrite cases can be silently combined; every hot log is still one path | Good runner-up                               |
| Central database/service                        | Can serialize all writes                                  | Sacrifices offline Git-backed truth, adds availability and backup concerns, and duplicates the existing sidecar model                     | Wrong architectural direction                |
| Immutable content-addressed event files         | Removes shared writable paths; retries converge naturally | More small files and a reducer/migration are required                                                                                     | Best fit                                     |

## Proposed durable format

### 1. One immutable file per mutation

Use a new tracked namespace that cannot be mistaken for schema-v2 indexes, for example:

```text
link-events/v1/ab/abcdef...json
```

The filename is the SHA-256 digest of a canonical event payload. The two-character
directory is only a filesystem fan-out. A minimal wire shape is:

```json
{
  "schema_version": 1,
  "operation_id": "stable invocation identity",
  "operation": "put | observe | remove",
  "link_key": {
    "kind": "directed",
    "source_ref": "agent:research.1o.cdx",
    "relation": "read",
    "target_ref": "research:202609/example.md"
  },
  "payload": {},
  "actor": "research.1o.cdx",
  "created_at": "2026-09-08T00:00:00Z"
}
```

`event_id` may be returned in APIs, but it should be derived from the canonical bytes
rather than trusted as independent data. Validation must reject a file whose path hash
does not match its bytes.

`operation_id` is essential. Two genuinely separate, identical reads must produce two
events, while a retry of one read must reproduce the same event. The current outbox
already mints an entry ID; preserve that identity through retries instead of generating
a fresh timestamp or UUID during drain.

Ordinary commands only create files. They never rewrite or delete a published event. An
exact retry adds the same path with the same bytes, which Git merges trivially. Two
different mutations add different paths, which Git also merges trivially. A same-path,
different-bytes case means a SHA-256 collision or corruption and should fail loudly.

### 2. Define event-set semantics in `sase-core`

The fold must be a function of the event set, never filesystem enumeration or Git commit
order. This belongs in the Rust core because every frontend must agree.

- `observe` represents one audited `read` or prompt citation. `uses` is the count of
  distinct active observation IDs, not an incremented field that writers overwrite.
- `put` creates or updates deliberate/manual and derived edge state. An update names the
  active versions it observed and supersedes them.
- `remove` tombstones the active event/version IDs the caller observed. A genuinely
  concurrent unobserved add survives: add-wins observed-remove semantics avoid silently
  deleting work the remover never saw.
- Concurrent manual descriptions use a documented deterministic winner, preferably a
  hybrid-logical-clock plus event-ID tie-break, while `sase artifact doctor` reports the
  concurrent versions. The projection can preserve the original creator/time and show
  the winning current description.
- Exact duplicate events deduplicate by digest. Cross-sidecar copies of the same event
  also deduplicate by digest in the project aggregate.

This makes the reducer associative, commutative, and idempotent. Property tests should
assert those laws directly.

### 3. Keep the three existing layers, but make their ownership honest

- **Durable truth:** immutable event objects in each owning document sidecar; bead link
  events remain in the bead event store.
- **Read model:** the existing untracked `~/.sase/projects/<key>/artifact-links.json`,
  rebuilt from event truth plus bead and projected relationships.
- **Presentation:** managed Markdown tables and ACE views rebuilt from the read model.
  Presentation must never be parsed back as truth.

When both document endpoints are in one sidecar, store one event object there. When the
endpoints belong to different sidecars, publish the same event object to both. Existing
reconciliation can repair a missing copy by digest without inventing a new mutation.

### 4. Funnel automatic writers through the host-owned lane

Even after event sharding, automatic writes should not dirty an agent's document
checkout.

`sase artifact read` should atomically append its durable local outbox event and update
the local aggregate optimistically, but should not call the sidecar `upsert` first.
After agent publication, the drain should resolve the machine artifact-link store and
write through the hidden host-owned clone. Prompt citations, derivation, and
housekeeping should use the same lane. Batch all ready events for one repository into
one commit and one publication attempt.

This does not provide global locking, nor does it need to. It reduces commit and fetch
pressure on one machine; immutable event paths provide cross-machine convergence.

## Safe rollout

1. **Immediate containment.** Stop direct automatic sidecar writes from
   `_record_read_link`; drain through the hidden machine clone. Add metrics for link
   publication rebases, auto-resolved conflicts, unresolved conflicts, retries, and
   outbox age.
2. **Schema-v2 safety net.** Implement a strict three-way resolver for current
   `links/**/*.json`: union distinct identities, merge observation `uses` as
   `ours + theirs - base`, preserve true deletions, and refuse ambiguous same-key edits.
   Invoke it from every SASE-managed sidecar integration and from the generic
   stitch/finalizer conflict path. This prevents the common incident during rollout.
3. **Core event model.** Add event validation, identity, observed-remove reduction, and
   event-set property tests in `sase-core`; expose the binding to Python.
4. **Dual-read migration.** Read schema-v2 snapshots and v1 events together. Emit one
   deterministic import event per unique legacy row, preserving the legacy `uses` count
   as a base observation count.
5. **Cut over writers.** New binaries write only immutable events. Leave legacy JSON
   indexes present and read-only while older fleet members may still exist. Deleting
   them during mixed-version operation would recreate delete/modify conflicts.
6. **Retire legacy input only after a fleet version floor.** Removal is optional and
   should be a coordinated migration, not normal link maintenance.

The existing aggregate schema and most CLI/UI consumers can remain stable during this
transition. The largest changes are confined to durable write/read adapters and the Rust
reducer.

## Verification and acceptance criteria

The landing gate should create many independent clones from one base and concurrently
exercise:

- different agents reading the same previously unlinked artifact;
- the same agent retrying one outbox operation;
- repeated genuine reads by one agent;
- manual add/update/remove races;
- a remove concurrent with a new observation;
- a relationship whose endpoints live in different sidecars;
- arbitrary push/rebase orders from at least two simulated machines; and
- process death after event write, local commit, and remote push.

After all retry loops settle, every clone should be clean, all remotes should contain
the same event set, every event hash should verify, aggregates should be byte-identical,
and no finalizer should pause for an artifact-link conflict. Event-set property tests
must prove branch-order independence, associativity, commutativity, and idempotence.

The operational success metric is **zero user-visible merge conflicts whose only
unmerged paths are artifact-link storage**. Secondary metrics are no lost link events,
bounded outbox age, and fewer link-only commits through batching.

## Recommended solution

Implement a **schema-v3 immutable, content-addressed artifact-link event store**, with
one new file per logical mutation, a deterministic observed-remove reducer in
`sase-core`, and the current aggregate/Markdown surfaces retained as projections. Route
all automatic read, prompt, derivation, and housekeeping events through the hidden
host-owned sidecar clone and batch their publication. As an immediate and migration-era
guard, add a strict semantic resolver for existing schema-v2 JSON indexes and wire it
into every SASE-managed rebase path.

This combination addresses both timescales: central host-owned draining and the v2
resolver make today's conflicts rare and automatically recoverable; immutable event
paths remove the shared-write cause, making ordinary artifact-link merge conflicts
practically impossible without relying on a custom Git merge driver or a globally
available lock service.
