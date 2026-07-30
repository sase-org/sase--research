---
create_time: 2026-07-30
updated_time: 2026-07-30
status: research
---

# SASE Artifacts: The Best Next Investments

## Executive decision

SASE should evolve artifacts from **durable files that can be referenced** into **managed outputs that can be retained,
traced, composed, and handed off**.

The reference and inspection layer is no longer the main gap. On 2026-07-29 and 2026-07-30, SASE landed the core of the
previous artifact research: kind-tagged references, prompt expansion, `@` completion, artifact read commands, enriched
file records, a Files pane, marks, previews, and cross-project browsing. Repeating that work or building another
all-purpose artifact registry would solve yesterday's problem.

The best path is now:

1. control storage growth with explicit lifecycle policy and safe garbage collection;
2. record what each run consumed and produced in a small run manifest;
3. use the SHA-256 values SASE already stores to deduplicate physical blobs without changing logical artifact refs;
4. build bundles, contracts, search, aliases, and interoperability on those primitives.

This direction preserves the current `file:` references and JSONL index, fits the Rust-core backend boundary, and avoids
recreating the large generic artifact graph that the project already built and removed in May.

## Scope and method

This report combines:

- inspection of the current SASE implementation, tests, docs, and artifact CLI;
- a live inventory and integrity check of the artifact-file corpus on 2026-07-30;
- comparison with official specifications and documentation for Git, W&B Artifacts, GitHub Actions, GitLab CI, OCI,
  A2A, and MCP;
- the 2026-07-29 report `artifact_refs_and_inspector.md`, treated as a baseline rather than a backlog.

The word *artifact* is overloaded in SASE. This report focuses on persistent artifact files and their use in agent
handoffs, while designing the metadata so the same concepts can connect document, commit, chat, bug, bead, and agent
references.

## What SASE has already solved

The current implementation is substantially ahead of the state described at the start of the prior report:

- `sase artifact create|doctor|list|open|path|show` exists, and the read commands accept every artifact-reference kind.
- File records carry `sha256`, `size_bytes`, and `mime_type`; `doctor -v` verifies stored content.
- `file:`, `chat:`, `commit:`, `bug:`, document-role, `bead:`, and `agent:` references share a Rust-owned grammar and
  resolver.
- Prompt launch expands `@` references, and ACE offers a cached, unified completion menu.
- The Artifacts tab has a Files pane with filters, detail, preview, open, copy, marks, and agent navigation.
- Documents from the sidecar roles are browsable, and plan previews render as Markdown.

The live file model in `src/sase/core/artifact_file_types.py` now contains a stable logical id, display label, coarse
kind, stored and source paths, producer association, creation time, explicit/default origin, digest, size, and MIME
type. The Rust-backed query facade supports kind, project, agent, date, explicit-only, substring, and limit filters.

That is a good technical inventory. It is not yet a managed artifact system:

- There is no retention class, expiration, pin, promotion, trash, or garbage collector.
- There is no description, semantic role, tag, version family, alias, or acceptance state.
- The index does not record input/output relationships between a run and artifact refs.
- `sase artifact create` accepts one file and **moves** it, unlinking the source; the safer copy behavior is reserved for
  automatically discovered default artifacts.
- Exact duplicate bytes are stored more than once even though every row already has a SHA-256 digest.
- `-q` searches labels and paths, not descriptions or text content.
- There is no declared output contract that can tell a workflow whether the expected deliverables were produced.

## Live corpus: the pressure is lifecycle, not lookup

The following measurements came from `sase artifact list -l 0 -j`, filesystem checks of the recorded source paths, and
`sase artifact doctor -v` on 2026-07-30.

| Measure | Current value | Implication |
| :--- | ---: | :--- |
| Indexed files | 4,287 | Large enough to require policy; still small enough for simple indexes |
| Stored bytes | 662,014,824 bytes (631.3 MiB) | Material local storage for one user |
| Images | 4,051 (94.5%) | Auto-generated media, especially snapshots, dominates |
| Markdown | 211 | The main content-search opportunity |
| Generic files | 25 | The current kind taxonomy is coarse |
| Explicit artifacts | 216 (5.0%) | Most retention decisions are currently implicit |
| Distinct producing agents | 587 | Producer lookup alone is not a useful organizing model |
| Missing stored files | 0 | The managed store is reliable |
| Missing/mismatched digests | 0 | Integrity metadata is complete and trustworthy |
| Missing source paths | 1,225 (28.6%) | The stored object, not the workspace source, is the durable identity |
| Duplicate digest groups | 94 | Exact duplication is observable now |
| Redundant logical rows | 107 | Provenance records should remain distinct even if blobs deduplicate |
| Reclaimable exact-duplicate bytes | 35,824,488 bytes (34.2 MiB) | A content-addressed blob layer would save about 5.4% immediately |

On 2026-07-29 alone, 296 new files totaling 40,456,509 bytes were indexed. That single day added almost as many records
as some artifact systems see in a project lifetime. The previous report measured 3,985 rows; the current corpus is 302
rows larger roughly a day later.

This does **not** mean SASE needs a database or object-storage service. It means the system needs a lifecycle before
growth makes deletion frightening. The current healthy store is an excellent migration point: all objects exist, every
object has a digest, and exact duplicates can be identified deterministically.

## Lessons from adjacent systems

### 1. Separate immutable bytes from human organization

Git's core is a content-addressable object store: content produces a key, while trees and commits provide names and
relationships around the blobs. The important lesson for SASE is not to turn artifacts into Git; it is to keep physical
blob identity separate from logical provenance records. Two agents may produce byte-identical files and should retain
two logical records, while the store needs only one copy of the bytes. See the official
[Git objects documentation](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects).

OCI uses the same separation at a portable boundary: a descriptor carries media type, digest, and size; a manifest
organizes one or more blobs; and a `subject` plus the referrers API associates signatures, SBOMs, and other derived
objects without mutating the subject. The useful SASE pattern is a small typed edge or manifest, not an OCI registry.
See the [OCI artifact guidance](https://specs.opencontainers.org/image-spec/manifest/) and
[OCI Distribution referrers API](https://specs.opencontainers.org/distribution-spec/?v=v1.1.1).

### 2. Retention needs a protected escape hatch

GitHub Actions defaults workflow artifacts to a finite retention period, configurable within plan limits. GitLab adds
two useful refinements: an explicit **Keep** operation and automatic protection for artifacts from the latest successful
pipeline on a ref. W&B supports per-artifact and default TTLs, soft deletion, and prevents registered production
artifacts from accidentally expiring.

The shared design is better than either “keep forever” or “delete after N days”: default expiry plus a visible,
auditable promotion mechanism. See
[GitHub artifact retention](https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization),
[GitLab job artifacts](https://docs.gitlab.com/ci/jobs/job_artifacts/), and
[W&B artifact TTLs](https://docs.wandb.ai/models/artifacts/ttl).

### 3. Lineage comes from declaring run inputs and outputs

W&B does not infer its artifact DAG from similar filenames. A run explicitly consumes an artifact and logs another as
output. That makes producer and consumer traversal reliable and makes versions useful. SASE has an even better
capture point: it already resolves every `@artifact` reference before launch and already knows every persisted output
at finalization. Recording those two lists would produce useful lineage without a graph database or a new user ritual.
See [W&B artifact lineage](https://docs.wandb.ai/models/artifacts/explore-and-traverse-an-artifact-graph).

GitHub's artifact attestations reinforce the provenance value of the digest: an attestation binds a SHA-256 subject to
the workflow, repository, commit, and triggering context, and can be verified independently. SASE does not need to sign
every visual snapshot, but accepted or exported deliverables should eventually be able to carry a verifiable statement.
See [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/use-artifact-attestations).

### 4. Agent outputs are often multi-part

The A2A protocol defines an artifact as a task output with an id, optional name and description, metadata, and one or
more parts. A part can be text, raw bytes, a URL, or structured data, with filename and media type; streamed artifact
updates can append chunks and mark the final chunk. That is a much closer model for “research report + infographic +
source data” than a flat list of unrelated files.

SASE should not adopt A2A as its internal storage format, but its artifact bundle should map cleanly to this model.
See the [A2A Artifact object](https://a2a-protocol.org/v0.3.0/specification/#67-artifact-object) and current
[A2A part and artifact fields](https://a2a-protocol.org/dev/specification/#417-artifact).

### 5. Agent discovery needs descriptions and cost hints

MCP resource links distinguish a programmatic name from a human title and add URI, description, MIME type, annotations,
and raw byte size. Its specification explicitly notes that size lets a host estimate context-window use. SASE already
has ref, label, MIME, and size; adding description and a bounded read path would make artifact selection much better for
agents and would permit a straightforward MCP projection later. See the
[MCP resource-link schema](https://modelcontextprotocol.io/specification/2025-06-18/schema#resourcelink).

### 6. Versions and aliases solve different problems

W&B finalizes an artifact version, creates a new version only when checksummed content changes, and uses mutable aliases
such as `latest`, `best`, `staging`, or `production` to point at immutable versions. Protected aliases also prevent
accidental deletion. SASE should copy the separation, not the ML vocabulary: durable documents and prompts should store
an immutable `file:` ref, while interactive commands may resolve a friendly alias and record which immutable ref was
chosen. See [W&B artifact versions](https://docs.wandb.ai/models/artifacts/create-a-new-artifact-version) and
[artifact aliases](https://docs.wandb.ai/models/registry/aliases).

## The target model

SASE can get the useful behavior with five small concepts layered over the existing index:

| Layer | Identity | Mutable? | Purpose |
| :--- | :--- | :---: | :--- |
| **Blob** | SHA-256 | No | One physical copy of the bytes |
| **Artifact record** | Existing `file:<source>:<id>` ref | No | Label, producer, role, MIME, size, digest, description |
| **Run manifest** | Existing `agent:` ref / run directory | Append until finalization, then no | Inputs consumed, outputs produced, contracts, invocation fingerprint |
| **Bundle** | New immutable artifact ref | No | Ordered, role-labelled parts forming one deliverable |
| **Policy pointer** | Pin, alias, tag, retention rule | Yes and audited | Discovery, promotion, acceptance, and reachability for GC |

The critical boundary is between a blob and an artifact record. Deduplicating records by digest would be wrong: two
agents producing the same PNG are two provenance events. Deduplicating their stored bytes is safe.

Similarly, aliases must never replace immutable refs in durable documents. If `report:accepted` later moves to a new
version, a prior bead or research note must still resolve to the original file it reviewed.

### Minimal run-manifest shape

A run manifest can be deliberately boring:

```json
{
  "schema_version": 1,
  "run_ref": "agent:bbugyi200.athena.example",
  "inputs": [
    {"ref": "research:202607/prior_report.md", "role": "source"}
  ],
  "outputs": [
    {
      "ref": "file:explicit:0123456789abcdef01234567",
      "role": "report",
      "description": "Decision memo comparing artifact lifecycle designs"
    }
  ],
  "contracts": [
    {"role": "report", "required": true, "mime_type": "text/markdown"}
  ],
  "finalized": true
}
```

SASE can fill `inputs` automatically from the refs resolved at launch. It can fill `outputs` from the persistent index at
finalization. Users or workflows only need to provide roles, descriptions, and contracts when they care about them.
Lineage queries can scan these small manifests or maintain a derived cache; the manifests remain the source of truth.

## Candidate improvements and tradeoffs

### Lifecycle, promotion, and garbage collection

Add lifecycle metadata at ingestion:

- `retention_class`: `run`, `project`, or `pinned`;
- `expires_at`, nullable;
- `pinned_at` and a short reason/source;
- `deleted_at` for a recoverable trash stage.

Suggested defaults:

- automatically discovered media starts as `run`;
- `sase artifact create` starts as `project`;
- a ref stored in a bundle, accepted alias, SDD document header, bead, or ChangeSpec protects the target through
  reachability;
- pinning always wins over TTL.

Provide `sase artifact pin|unpin`, `promote`, `stats`, and `gc --dry-run`. A real collection should move candidates to a
trash directory first and purge only after a grace period. `doctor` should report references that would become dangling.
ACE should show retention/expiry and offer promotion from the Files pane.

At the same time, make explicit creation non-destructive by default: copy the source, add `--move` for the current
behavior, and print both source and stored paths. “Create an artifact” should not silently consume a workspace file.

The main risk is deleting useful artifacts. Reachability protection, dry-run output grouped by project/agent/kind, a
trash grace period, and explicit pinned defaults for hand-created artifacts make the first release conservative.

### Automatic run lineage

Write `artifact_manifest.json` beside the existing run metadata. Capture:

- canonical refs resolved from the prompt;
- output refs persisted during finalization;
- producer agent/run, project, workflow, provider/model, source commit, and prompt digest by reference to existing run
  metadata rather than duplicating everything;
- typed roles such as `source`, `report`, `image`, `test-result`, or user-defined strings.

Then add `sase artifact lineage <ref> [--upstream|--downstream] [-j]` and a compact “Inputs / Outputs / Derived from”
section in ACE.

This is intentionally not a general graph platform. The authoritative data is a set of per-run input/output manifests;
any reverse index is disposable. It delivers the highest-value part of lineage—“what produced this?” and “what used
this?”—while respecting the project's previous decision to remove the generic graph.

### Content-addressed physical storage

Store bytes under a digest-derived path such as `blobs/sha256/de/2e...`, and let artifact records point to the blob.
Keep existing artifact ids and refs unchanged. Multiple records with the same digest share one blob, but retain their
own labels, producers, creation times, and logical stored filenames for display.

A low-risk migration is:

1. teach the resolver to read both legacy paths and blob paths;
2. on new ingestion, write or reuse a blob, then write the logical record;
3. add `doctor --migrate-blobs --dry-run`;
4. only remove a legacy duplicate after its digest is verified and its logical record resolves through the blob.

The immediate saving is only 34.2 MiB, so this should follow lifecycle rather than precede it. Its larger value is that
retention becomes reference counting, integrity is inherent, sync/export becomes cheaper, and duplicate future
snapshots stop multiplying storage.

### Multi-part bundles

Add an immutable manifest whose parts are ordered artifact refs with a role, title, and optional description. A bundle
can contain local files, SDD documents, chats, commits, or external resource links without copying all of them.

Candidate UX:

```text
sase artifact bundle create \
  --label "Artifact strategy research" \
  --part report=research:202607/sase_artifacts_next_steps_20260730.md \
  --part evidence=file:explicit:0123456789abcdef01234567
```

ACE marks already provide the natural UI: mark entries, choose “Create bundle,” assign roles, then hand one bundle ref
to the next agent. Prompt expansion should expose a short manifest first and materialize parts on demand so a large
bundle does not flood context.

Bundles solve a real mismatch in the current model: the user's deliverable is often a report, its images, and supporting
data together, while `sase artifact create` can express only one path at a time.

### Declared output contracts

Allow xprompt workflows and agent launches to state expected outputs:

```yaml
outputs:
  - role: report
    required: true
    mime_type: text/markdown
  - role: diagram
    required: false
    mime_type: image/png
    max_bytes: 5000000
```

At finalization, SASE validates presence, MIME type, size, and optionally JSON Schema for structured artifacts. Missing
or invalid output should be a visible completion diagnostic with machine-readable status. Whether it fails the whole
run should be configurable; a coding task can succeed even if an optional illustration did not.

Contracts give workflows a reliable handoff boundary and make artifact generation testable. They should write into the
same run manifest, not create a second workflow-only artifact system.

### Agent-oriented discovery and bounded reads

Extend records with `description`, `role`, and `tags`. Search descriptions and text content for text-like MIME types,
while keeping technical path substring search as a fielded option. Add:

- `sase artifact search` with field filters and full-text search;
- `sase artifact read <ref> --max-bytes N`;
- line, page, and time fragment-aware reads;
- a JSON result that reports exact byte size and whether content was truncated;
- optional generated summaries as derived artifacts, never as replacements for source content.

Do not start with vector search. With only 211 Markdown files and a few thousand labels, SQLite FTS or a derived
full-text cache is cheaper, inspectable, and deterministic. Revisit embeddings only when users can name failed queries
that lexical search cannot answer.

This is also the right prerequisite for an MCP resource adapter: expose the existing logical ref as a resource URI at
the protocol boundary and return title, description, MIME, size, and bounded content. It does not require replacing the
internal colon reference grammar.

### Versioned collections and aliases

Introduce a logical collection name above immutable artifact versions. A collection might be
`sase/artifact-strategy-report`; its versions are concrete immutable refs. Mutable aliases such as `latest`,
`candidate`, or `accepted` point to one version, and protected aliases imply a pin.

Use aliases for interactive selection and automation, but resolve them to an immutable ref at launch and record that
resolution in the run manifest. Durable SDD documents should store the immutable ref.

This is valuable once repeated deliverables exist. It should not precede lifecycle or lineage because an alias without
safe retention and provenance is only a prettier dangling pointer.

### Selective attestations and external interchange

For artifacts promoted to `accepted`, `release`, or external publication, optionally emit a provenance statement keyed
by the subject digest. It can include producing run, project, commit, prompt digest, provider/model, timestamp, and
contract results. Start unsigned and local; add signing only when artifacts cross a trust boundary.

Model the statement as another artifact that *refers to* the subject, following the OCI/GitHub pattern. Do not add
attestation fields to every artifact row or sign thousands of transient PNG snapshots.

Once bundles and descriptions exist, add export adapters:

- MCP `ResourceLink` / `resources/read` for tool and editor consumers;
- A2A Artifact projection for agent-to-agent transport;
- a self-contained JSON manifest plus blobs for offline transfer.

Interchange should be an edge adapter, not a new canonical artifact model.

## Alternatives considered

### Keep polishing only the ACE Files pane

This would improve daily browsing but leave the system with unlimited growth, no safe deletion, and no traceable
handoffs. The pane is now good enough to expose the next problems; it should consume lifecycle and lineage features,
not be the center of the next design.

### Rebuild a unified artifact graph or central registry

Rejected. SASE recently removed a much larger graph/store implementation, the current JSONL corpus is small, and the
existing artifact record already contains most registry fields. Per-run manifests plus derived indexes deliver lineage
without a second source of truth.

### Make the SHA-256 digest the public artifact ref

Rejected. A digest identifies bytes, not a provenance event. Byte-identical outputs from two agents should share a blob
but remain separately attributable. Existing `file:` refs should stay stable.

### Adopt OCI, MCP, or A2A internally

Rejected. Each offers useful boundary patterns, but none models SASE's local project, run, sidecar, and agent semantics
better than SASE itself. Design for clean projection to those protocols later.

### Add semantic/vector search first

Rejected. Search quality is constrained first by missing descriptions, roles, and content indexing. Lexical full-text
search is sufficient at the present corpus size and is easier to debug.

## Delivery sequence

| Phase | Work | Exit condition |
| :--- | :--- | :--- |
| **A — Control** | Copy-by-default ingest, retention fields, pin/promote, stats, dry-run GC, trash grace period | Storage growth is visible and deletion is recoverable |
| **B — Connect** | Run input/output manifest, lineage query, content-addressed blobs | Every new artifact has reliable producer/consumer context and duplicate bytes are shared |
| **C — Compose** | Bundles, output contracts, descriptions, roles, full-text and bounded reads | Agents can declare, discover, validate, and hand off complete deliverables |
| **D — Curate** | Versions, aliases, accepted/release promotion, selective attestations and protocol adapters | Stable deliverables can be curated and exported without weakening immutable refs |

## Ranked recommended improvements

1. **Add lifecycle policy, pin/promote, safe garbage collection, and copy-by-default creation.** This directly addresses
   the observed 40.5 MB/day burst, makes deletion recoverable, and fixes the surprising destructive ingest behavior.
   Ship `stats` and `gc --dry-run` before any automatic deletion.
2. **Record automatic per-run input/output manifests and expose lineage queries.** SASE already knows refs at launch and
   outputs at finalization, so this produces trustworthy provenance with little user burden and without reviving a graph
   database.
3. **Move physical bytes to a SHA-256-addressed blob layer while preserving every existing logical artifact ref.** It
   recovers 34.2 MiB immediately, prevents future exact duplication, and makes retention, verification, and export
   simpler.
4. **Introduce immutable multi-part artifact bundles with role-labelled parts.** This gives reports, images, data, and
   evidence one handoff identity and maps cleanly to the artifact model emerging in agent protocols.
5. **Add declared output contracts for workflows and agent runs.** Required roles, MIME/size constraints, and optional
   schemas make deliverables testable and turn missing artifacts into clear completion diagnostics.
6. **Improve agent discovery with descriptions, roles, tags, full-text search, and bounded fragment-aware reads.** Use a
   derived lexical index first; expose size and truncation so agents can manage context deliberately.
7. **Add versioned logical collections and mutable, optionally protected aliases.** Resolve aliases to immutable refs at
   launch and record the resolution; let protected aliases imply retention.
8. **Add selective provenance attestations and MCP/A2A export adapters for promoted artifacts.** Apply these at trust and
   interoperability boundaries, not to every transient artifact.
