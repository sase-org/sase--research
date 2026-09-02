# Cross-Machine Agent Sync and Revival Architecture

Research date: 2026-09-02

## Executive summary

The malformed `athena.7n--code` rows in the supplied screenshot are not a
cosmetic TUI defect. They are the visible result of an older v1 import path
that imported one run at a time, immediately marked each imported run as
visible, did not reconstruct family containers, and persisted a
machine-qualified display name without consistently localizing the nested
`agent_family` field.

The newer v2 protocol is much closer to the required design. It publishes an
owner-qualified identity, an explicit hood snapshot, family membership, run
payloads, a saved family group, and a dismissed bundle. Its transactional
import deliberately keeps imported terminal runs out of the Agents tab. The
current machine has not upgraded to those v2 records, however: all 338
foreign imports found locally are v1 imports, while the agents sidecar has an
exact v2 successor for every one of them. A real v2 preflight currently fails
because the name registry treats the existing v1 `athena` namespace as an
unrelated owner rather than as evidence that can be promoted.

There is also an independent revival-fidelity bug. The asynchronous cleanup
path serializes only a narrow projection of an `Agent`, reconstructs a partial
object in a subprocess, and then writes the dismissed bundle from that partial
object. In the sampled `athena.7n--code` bundle, `agent_family`,
`artifacts_dir`, `response_path`, `model`, `provider`, and reasoning effort are
all missing. The system can often restore a visible row from such a bundle,
but it cannot honestly promise a faithful, fully restartable revival.

The right fix is therefore not to special-case the TUI label. SASE should:

1. make an immutable, owner-qualified run archive the source of truth;
2. model visibility/dismissal as a machine-local projection over that archive;
3. add an atomic, evidence-backed v1-to-v2 promotion transaction;
4. make a revival capsule complete and validate its capabilities; and
5. keep identity localization in the Rust core, deriving display names at the
   boundary rather than persisting them as canonical identity.

## Requirements and invariants

The user-visible requirements imply the following architectural invariants.

### Imported terminal runs are hidden by default

A completed run imported from another machine should be durable and
discoverable through revival/history, but it should not acquire a live
Agents-tab marker merely because it arrived. "Imported" is a provenance fact;
"visible" is a local UI choice. They must not be represented by the same bit.

### Revival is a lossless durable-state operation

For a terminal agent, full revival should restore at least:

- the stable run identity and source owner;
- the localized display name;
- project, workflow, status, timestamps, model, provider, and reasoning effort;
- raw prompt/restart input and prompt-step metadata;
- chat, response, commits/diff, output variables, and declared artifacts;
- parent, child, family, role, retry, and neighborhood relationships; and
- enough artifact metadata to reconstruct loader markers and run restart
  planning.

This does not mean resuming the same OS process. It means losslessly restoring
the durable agent record and, where the original run was restartable, retaining
the inputs needed to launch a successor.

### Identity is global; names are projections

The canonical identity must include the source owner and a stable source run
identifier. A display name is computed for the configured destination owner:

| Source relative to destination | Display form for local name `7n--code` |
| --- | --- |
| Same username and same machine | `7n--code` |
| Same username, machine `athena` | `athena.7n--code` |
| User `bbugyi200` differs | `bbugyi200.athena.7n--code` |

The same rule must apply to the run name, family name, parent/child references,
saved groups, and every registry key exposed to the local UI.

### Import is atomic at hood scope

A family must never become visible or revivable as a bag of unrelated children.
The source hood snapshot, all run capsules, relationship graph, registry claims,
archive rows, and initial visibility state should commit together or not at all.

## Investigation method and evidence

The investigation compared four layers:

1. the screenshot and current local SASE state;
2. the agents sidecar's v1 and v2 payloads;
3. the import, registry, dismissal, and revival implementations; and
4. the Rust owner-aware identity localizer.

The current SASE checkout was at `8b0c65476`; the screenshot identifies
`v0.17.1+30.gae7ca2226`. The agents sidecar inspected for the source data was at
`693917592d` on `origin/main`.

### Screenshot symptoms

The screenshot shows many terminal rows such as `athena.7n--code` in the normal
Agents tab. The selected child is rendered as a root, even though its `--code`
role and family metadata establish that it belongs to an agent family. Its
detail pane also says `No prompt file found`.

Those three symptoms correspond directly to the v1 importer:

- it writes a `done.json`, so the terminal import is immediately visible;
- it imports each run independently, so no family container is reconstructed;
- it only has `meta.json`, `commits.json`, and `chat.md`, so it cannot restore a
  missing prompt or a complete relationship snapshot.

### Current local population

The source sidecar contains two generations of Athena data:

- a legacy v1 manifest with 338 entries, all from machine `athena`; and
- a strict v2 owner manifest at
  `users/bbugyi200/machines/athena/manifest.json` containing 1,963 hoods,
  9,632 runs, and 1,590 families.

The current machine has exactly 338 imported v1 artifacts and no imported v2
artifacts. At inspection time none of those 338 artifacts retained `done.json`,
which is consistent with the rows having been manually dismissed after the
screenshot. Manual dismissal changed local visibility; it did not upgrade the
underlying records.

Every one of the 338 v1 entries has one unique deterministic v2 successor. The
mapping was checked by recomputing the source run id:

```text
run- + first_32_hex(
  sha256(project_key + "\0ace-run\0" + artifact_timestamp)
)
```

The resulting v2 global name is `bbugyi200.` plus the v1 machine-qualified
name. There were 338 exact matches and zero unmatched v1 entries. This makes
the current dataset suitable for deterministic migration without guessing.

### The `7n` case

The v1 source stores only:

```text
agents/athena.7n--code/meta.json
agents/athena.7n--code/commits.json
agents/athena.7n--code/chat.md
```

Its local imported metadata contains:

```json
{
  "name": "athena.7n--code",
  "agent_family": "7n",
  "agent_family_role": "code",
  "imported_from_machine": "athena",
  "imported_owner_kind": "username_unknown_v1"
}
```

The name parser therefore sees the localized family `athena.7n`, while the
stored relationship says the family is `7n`. The TUI cannot attach the child to
the expected local family and displays it as a root.

The corresponding v2 hood fixes the source representation. Its container is an
explicit family with global name `bbugyi200.athena.7n`, and its members are the
root run and the code run. On a destination configured as
`bbugyi200.kellys_mbp`, these should localize to `athena.7n` and
`athena.7n--code`. On a destination owned by a different username, the
`bbugyi200.` component must remain.

## How the current architecture behaves

```text
Athena artifacts
    |
    | publish v1: independent run bundles
    | publish v2: owner manifest + hood snapshot + run capsules
    v
agents sidecar Git repository
    |
    | fetch, validate, cache
    v
destination import transaction
    |-- artifact directory and loader markers
    |-- name registry claim
    |-- dismissed bundle/archive data
    |-- dismissed identity set
    `-- saved family group
            |
            v
       Agents-tab projection / revival UI
```

The architecture already contains most of the v2 transaction on the lower
half of this diagram, but legacy imports and the ordinary cleanup path do not
obey the same data contract.

### Legacy v1 import creates the screenshot state

`src/sase/agents_sync/bundles.py` imports each legacy bundle as a standalone
terminal artifact. It writes live loader markers, does not initialize a
dismissed record, and cannot create a family container because v1 has no hood
snapshot. `_imported_markers` changes `name` to the v1 entry name but copies
relationship fields without applying the same name projection.

This is the direct cause of the visible, flattened `athena.*--code` roots.

### V2 has the intended visibility and grouping behavior

The v2 transaction implemented around
`src/sase/agents_sync/v2_import_transactions.py` stages artifacts, dismissed
bundles, saved groups, and registry claims before finalization. The rendered
payload in `src/sase/agents_sync/v2_import_rendering.py` includes localized
family metadata, source owner, snapshot/transaction identity, model/provider
information, commits, embedded workflows, prompt steps, and a dismissed
bundle. The transaction updates the dismissed set before the imported terminal
record can be projected into the Agents tab.

Existing integration coverage also asserts that staged artifacts remain
invisible before completion and that imported identities are dismissed after
finalization. In other words, replacing v2 wholesale would discard good work;
the missing piece is safe promotion into it.

### V1 state blocks its v2 replacement

The current registry entry for `athena.7n--code` has origin `import_v1`, no
source owner, and only a legacy source machine. The normal dismissal path has
also produced a local collision owner whose canonical-looking global name is
`bbugyi200.kellys_mbp.athena.7n--code`. That name incorrectly treats a
presentation-qualified foreign run as if it were created locally.

The v2 registry mutation code accepts exact v2 ownership claims and a limited
set of local cases, but it has no evidence-backed v1 promotion case. A real
preflight against the current data raises:

```text
ImportedNameCollisionError:
imported agent name 'athena.7n' collides:
owner namespace 'athena' is already occupied
```

Thus the protocol with the right behavior cannot repair the records created by
the older protocol.

### The core identity localizer is already correct

`sase-core/crates/sase_core/src/agent_identity/identity.rs` distinguishes:

- the exact current owner;
- the same username on another machine;
- another username; and
- a v1 source whose username is unknown.

Its tests cover the expected shortening rules. The `bbugyi200.` stripping
requirement should remain there as shared domain behavior. The defect is that
legacy presentation names and partial provenance are later treated as durable
canonical identity, and related names are not always localized together.

## Revival is not currently lossless

The sync defect exposed a broader archive problem that also affects local
agents.

### Async cleanup serializes a partial `Agent`

`src/sase/ace/tui/actions/cleanup_payload.py::serialize_agent` emits a narrow
subset of the in-memory object. The cleanup subprocess in
`src/sase/ops/commands/agent.py` rehydrates that subset and calls the normal
dismissed-bundle writer. Fields omitted before the process boundary are
therefore persisted as null or defaults.

The actual dismissed bundle for `athena.7n--code` demonstrates the loss:

| Field | Value after dismissal |
| --- | --- |
| `agent_name` | `athena.7n--code` |
| `agent_family` | `null` |
| `agent_family_role` | `code` |
| `artifacts_dir` | `null` |
| `response_path` | `null` |
| `model` / `provider` / reasoning | `null` |

The serializer also reads `agent.artifacts_dir` directly instead of the
effective artifact location available through `get_artifacts_dir()` or the
index record. This is especially damaging for projected/imported agents.

Dismissal intentionally deletes only loader markers and leaves rich artifact
files in place. That design is safe only when the bundle retains a valid
artifact location and a complete reconstruction record. The current process
boundary breaks that assumption.

### Prompt completeness is systematically weak

The v2 representation can carry `prompt.md`, embedded workflows, and prompt
steps, but it can only publish what the source inventory finds. Among the 338
v1 entries with exact v2 successors:

| V2 content | Runs containing it |
| --- | ---: |
| Chat | 338 |
| Commits | 338 |
| Embedded workflows | 338 |
| Prompt steps | 311 |
| Family membership | 303 |
| Raw prompt | 35 |
| Missing raw prompt | 303 |

The `7n--code` v2 run has chat, commits, embedded workflows, prompt steps, and
family membership, but no raw prompt. Restart planning requires a raw xprompt,
so these records are historically viewable but not fully restartable.

One contributing path is that normal dismissed publication consults inline
prompt fields in the bundle, while normal dismissal deliberately retains path
references instead of embedding prompt contents. It does not consistently
fall back to `bundle.artifacts_dir/raw_xprompt.md`. More fundamentally, the
launch path should durably capture each member's restart input before provider
execution rather than hoping a later inventory can reconstruct it.

### Visibility identity is too weak

`dismissed_agents.json` is keyed by `(AgentType, cl_name, raw_suffix)`. It does
not include source owner or source run id. That makes dismissal vulnerable to
name reuse, cross-owner collision, and re-localization. It also conflates an
archive object's identity with one UI projection of that object.

The long-term model should make dismissal an overlay keyed by immutable run
identity, not a property encoded indirectly by deleting marker files or by a
machine-relative suffix.

## Sync validation does not scale to the present corpus

`sase agent sync --check --json -p sase` reported 2,201 validated foreign
hoods and 1,948 pending imports. A refresh that revalidated the current
sidecar still had not completed after more than three minutes and was stopped.

`src/sase/agents_sync/incoming_detection.py` walks each payload file, while
`src/sase/agents_sync/git_objects.py::read_bytes` launches `git show` once per
path. At thousands of hoods and several files per run, a refresh can launch
tens of thousands of Git subprocesses. The legacy capture loop also lists
`chat.md` twice.

The correctness work should not depend on such an expensive full pass. A
single `git cat-file --batch` stream, or one tree/archive stream per fetched
commit, can validate blobs in-process. Manifest/snapshot digests should be used
as the incremental cache boundary, with progress and cancellation exposed to
the caller.

One stale cache snapshot reported 15 chat digest quarantines. A sampled file in
the latest sidecar matched its declared digest exactly, so this investigation
does not treat those cached diagnostics as evidence of current repository
corruption. The slow refresh prevented a fresh full-corpus conclusion.

## Proposed target model

### 1. Immutable portable run capsules

Define one versioned archive object per source run, owned by a stable key such
as:

```text
(source_username, source_machine, source_run_id)
```

The capsule should carry canonical source-local names and stable relationship
ids, never destination-localized canonical names. It should contain or
content-address all durable material required by the revival contract. A hood
snapshot references the capsules and describes the family/neighbor graph.

A capability block should be explicit, for example:

```json
{
  "historically_viewable": true,
  "durably_revivable": true,
  "restartable": true,
  "missing_requirements": []
}
```

Publication should reject an assertion of `restartable: true` when prompt,
model/provider parameters, or required workflow inputs are absent. The UI can
still expose an incomplete historical record, but it must not call that record
fully revivable.

### 2. Destination-local archive and visibility overlay

Import the immutable capsule into an archive keyed by source identity. Keep a
separate local projection table containing:

```text
source identity -> hidden | visible | pinned
```

Terminal foreign imports initialize to `hidden`. Revival changes only the
projection and recreates any compatibility loader markers. Dismissal returns
the projection to `hidden`; it does not rewrite canonical provenance or create
a new locally owned global name.

This model also prevents retained dismissed bundles from accidentally hiding a
later revived projection: archive retention and local visibility no longer
share a key or lifecycle.

### 3. One owner-aware projection function

Move the complete projection operation into `sase-core` and apply it to the
whole graph in one call. The input is canonical owner/run/relationship data
plus the configured destination owner; the output contains the run name,
family name, relationship names, and collision namespace. Python importers and
the TUI should consume the projection rather than rebuilding prefixes.

This follows the existing Rust core boundary: every frontend needs identical
identity and migration behavior.

### 4. Atomic archive/import journal

Extend the v2 import transaction so its commit unit includes:

- validated hood snapshot and run capsules;
- archive rows/content objects;
- owner-aware name claims;
- family/group reconstruction;
- hidden visibility projections;
- compatibility dismissed bundles/markers while those formats remain; and
- a source-revision receipt for idempotence.

Crash tests should stop the transaction after every staged operation and prove
that neither a partial family nor a visible terminal row leaks into the TUI.

## Evidence-backed v1-to-v2 promotion

Current users need a migration, not merely a corrected clean install.

During v2 preflight, classify an existing v1 row as promotable only when all of
the following evidence agrees:

1. its legacy source machine equals the v2 source machine;
2. its project/workflow/artifact timestamp deterministically reproduces the
   v2 source run id;
3. its v1 name equals the v2 global name with only the newly known username
   removed; and
4. any shared chat/commit digests agree.

When the match is unique, the transaction may upgrade the v1 namespace claim
to the exact v2 owner, replace or relink the old artifact/archive record,
rewrite relationship data from the hood snapshot, install the hidden
projection, and retire the v1 bundle/registry aliases atomically. An ambiguous
or inconsistent row must be quarantined for explicit repair, never guessed.

This migration can deterministically promote all 338 legacy imports currently
present on the destination machine. It should also recognize and remove the
incorrect local collision claims produced by dismissing those imports, but
only when their archived provenance and payload digest prove that they refer to
the same source run.

`sase agent retire-v1` is not sufficient for this job. It retires a source
machine's own published v1 payload after v2 coverage exists; it does not repair
already imported v1 state on another machine. Athena should eventually run
that command, but only after destination promotion is supported and verified.

## Implementation boundaries

Shared semantics belong in the Rust core:

- portable capsule/hood schemas and validation;
- canonical source identity and full-graph name projection;
- v1-to-v2 promotion classification;
- archive visibility state transitions; and
- completeness/revivability capability calculation.

Python remains appropriate for:

- reading/writing the Git sidecar transport;
- adapting current artifact and dismissed-bundle layouts;
- transaction orchestration until a core API absorbs it; and
- presentation-only TUI behavior.

The cleanup subprocess should stop reconstructing an `Agent` from an ad hoc
subset. It should receive a versioned core archive DTO or a source archive key,
then persist the exact validated capsule. If a temporary patch retains the
current payload, it must serialize every bundle field and resolve effective
artifact paths before crossing the process boundary, but that should be viewed
as a compatibility repair rather than the final architecture.

## Acceptance tests

The fix should not be considered complete without the following end-to-end
tests.

1. **Owner projection matrix:** exact owner, same username/different machine,
   different username, and v1 unknown username. Assert identical projection
   for run, family, parent/children, saved groups, and registry namespaces.
2. **Foreign terminal default:** import a completed family and prove no member
   appears in the default Agents tab while the archive/revival search finds the
   family.
3. **Family round trip:** create a family with root and role children, publish,
   import on another machine, revive as a family, and prove no child appears as
   an orphan root.
4. **Content round trip:** byte-compare prompt, chat, response, commits/diff,
   workflows, prompt steps, output variables, and declared artifacts after
   publish/import/dismiss/revive.
5. **Restart round trip:** restart planning succeeds for every capsule that
   claims `restartable`; incomplete capsules expose precise missing
   requirements.
6. **Legacy promotion:** promote representative v1 standalone, family child,
   manually dismissed, name-reused, and conflicting records. Unique matches
   succeed idempotently; ambiguous matches quarantine without mutation.
7. **Transaction failure matrix:** crash after every stage and prove no partial
   family, registry claim, or visibility marker escapes.
8. **Cleanup projection:** dismiss an index-projected/imported agent through the
   subprocess and assert full bundle/capsule equality.
9. **Scale:** validate a fixture comparable to 2,000 hoods/10,000 runs with a
   bounded number of Git processes and useful progress/cancellation.

## Operational recovery after the code lands

The current machine should not be forced through today's v2 importer because
the preflight collision is deterministic. After promotion support lands:

1. back up the local agent registry, dismissed archive, artifact index, and
   project artifacts;
2. run a dry-run migration that reports all v1-to-v2 mappings and any
   ambiguities;
3. promote the 338 exact matches transactionally;
4. verify all imported terminal rows are hidden, the `7n` family is grouped,
   and owner projection changes correctly under a different configured
   username fixture;
5. rebuild/verify compatibility indexes; and
6. on Athena, publish a complete v2 snapshot, then dry-run and apply
   `sase agent retire-v1 -p sase` once every required destination reports v2
   coverage.

The migration should preserve the manually chosen hidden state. It should not
temporarily revive every legacy row while rewriting it.

## Recommended solution

Keep the existing v2 hood transaction as the transport foundation, but evolve
its destination into a first-class immutable Agent Archive with a separate
machine-local visibility projection. Implement the archive schema, canonical
owner identity, whole-graph name projection, revivability validation, and v1
promotion classifier in `sase-core`; keep Python as the sidecar and TUI adapter.

Deliver it in three slices:

1. **Stop further loss and visibility leaks.** Fix cleanup serialization to
   preserve the effective artifact path and complete durable record; require
   foreign terminal v2 imports to initialize hidden; capture raw restart input
   for every newly launched family member; and batch Git blob reads so a fresh
   sync is practical.
2. **Add transactional v1-to-v2 promotion.** Use source-machine, deterministic
   source-run id, global-name, and digest evidence to upgrade registry claims,
   reconstruct families, replace malformed v1 records, and preserve hidden
   state. Quarantine any non-unique match. Run this against the current 338
   exact mappings before retiring Athena's v1 publication.
3. **Finish the archive boundary.** Replace suffix-keyed dismissal as the
   source of truth with visibility keyed by immutable source identity. Treat
   current dismissed bundles and loader markers as compatibility projections,
   add explicit `historically_viewable`/`durably_revivable`/`restartable`
   capabilities, and only describe an agent as fully revivable when the
   validated capsule contains every required asset.

This solution fixes the screenshot symptom, preserves the correct username and
machine scoping rules, provides a safe path for the data already imported, and
turns full revival from an incidental consequence of surviving files into an
explicitly validated architectural guarantee.
