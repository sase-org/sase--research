---
create_time: 2026-08-28
updated_time: 2026-08-28
status: research
tags:
  - memory
  - artifacts
  - ace
  - architecture
---

# Should SASE Memory Become an Artifact?

**Research question.** SASE currently treats memory as configuration-like,
Git-backed agent context and exposes it in ACE's Admin Center Config hub. Would it be
better to migrate memory into SASE's artifact model, including a new **Memory** subtab
under **Artifacts**? If so, what should actually move?

**Baseline and method.** This report was prepared on 2026-08-28 against `sase` at
`bcd6813d2`. It combines direct source and history inspection, audited reads of the
`memory-webs` and `corpus-before-mechanism` decisions and the artifact/TUI reference
memory, live CLI inspection, and comparison with three external models: Backstage's
source-backed catalog, SLSA's source-artifact taxonomy, and GitHub Actions' narrower
run-output artifacts.

## Bottom line

The idea contains two different proposals, and they deserve opposite answers:

1. **Make memory a first-class artifact identity and put its primary browse surface in
   Artifacts:** probably worthwhile. This would give memory stable references, a place
   in the common catalog, and an eventual path to typed relationships and unified
   provenance.
2. **Move canonical memory bytes into an artifact sidecar, snapshot store, or artifact
   database:** not worthwhile with the current evidence. It would separate policy from
   the code and generated instruction files it governs, break the current one-repo
   publish transaction, complicate Home memory, and collide with artifact snapshot and
   retention semantics.

The useful principle is **promote, do not relocate**: treat a memory note as a
Git-backed *source artifact*, keep `sase/memory/` and `~/sase/memory/` authoritative,
and adapt the existing `MemoryPane` into a built-in Artifacts pane. “Artifact” should
be an identity, catalog, and relationship boundary here—not a storage mandate.

## 1. “Move memory into artifacts” has five independent meanings

The proposal is easy to over-scope because “artifact” currently bundles several
concerns. These should be decided separately.

| Axis | Possible change | Does it require relocating files? |
| --- | --- | --- |
| Taxonomy | Say that memory notes and strands are artifacts | No |
| Identity | Add canonical `memory:` references and resolution | No |
| Presentation | Put Memory under ACE's Artifacts tab | No |
| Relationships | Let memory participate in artifact links and read/citation provenance | No, but durable link storage needs design work |
| Storage/lifecycle | Put memory in a sidecar, CAS, indexed-file store, or artifact retention system | Yes |

Only the last row is a physical migration. The first four can deliver almost all of
the proposed user value without it.

This distinction is not just wordplay. SLSA 1.2 defines an artifact broadly as an
immutable blob and explicitly defines **source** as an artifact directly authored or
reviewed by people. Backstage similarly ingests version-controlled YAML from an
authoritative source into a catalog without making the catalog database the source of
truth. By contrast, GitHub Actions uses “artifact” narrowly for files produced by a
workflow run and retained after the job. The external precedent therefore supports a
“source artifact” subtype, but not the inference that catalog membership determines
storage.

## 2. Current SASE ground truth

### 2.1 Memory is policy-bearing source, not inert configuration

Memory files do more than configure a process:

- Core notes are compiled into `AGENTS.md` and provider instruction shims.
- Reference notes are addressed by `sase memory read` with attributable audit events.
- Every flat note is also a `#memory/<stem>` launch-time composition source.
- Memory webs add independently addressable strands, scope merging, validation, and
  optional mention closure.
- Agent writes go through proposals and human review; canonical writes are deliberately
  protected.
- `sase memory init` validates the corpus, regenerates instruction files and indexes,
  and can fold source and generated changes into one Git commit and push.

Calling this “configuration” undersells it. Memory is closer to **reviewed,
executable documentation**: source text that compiles into agent behavior.

At this baseline the project memory tree contains 70 Markdown files: 17 top-level
files and 53 strands across three webs (`decisions`: 7, `glossary`: 41,
`task_types`: 5). This is a real corpus, not a speculative category.

### 2.2 Memory already has a specialized and recently unified UI

ACE already mounts `MemoryPane` as the **Memory** subtab of the Admin Center Config
hub. Prompt gestures such as `gm` route directly to that subtab with the selected note
as a seed. The pane already owns:

- project and Home scope selection;
- note hierarchy plus expandable web/strand rows;
- parent/child and mention-closure travel;
- audited strand reads;
- mtime-keyed snapshots and off-thread loading;
- guarded add, edit, delete, external-editor, and conflict handling;
- generated-note read-only rules;
- unpublished state and `sase memory init` publishing.

This is about 6,000 lines across the memory domain and ACE memory catalog/pane code,
before counting the large test surface. The Memory pane was introduced on 2026-08-19,
embedded into the Config hub on 2026-08-20, and unified with glossary/web browsing on
2026-08-24–25. Adding a second implementation under Artifacts would duplicate a
freshly consolidated subsystem.

The extraction was fortunately designed for reuse: `MemoryPane` is already a child
widget behind a small host protocol, while the standalone modal and Config hub are
adapters. Rehosting is feasible; reimplementation is unnecessary.

### 2.3 The artifact system has three related but distinct layers

SASE's current artifact model is broader than its file index:

- An **artifact** is any durable record with a canonical `<kind>:<argument>` identity.
- A document provider supplies path inventory, typed properties, prompt-reference
  resolution, and an Artifacts pane.
- `sase artifact list` inventories only indexed files. Explicit files are immutable
  snapshots; automatic captures are subject to reclaim and retention.
- Artifact links are durable typed graph edges. For Markdown documents, managed link
  tables normally project into the Markdown file itself.

The configured Artifacts panes are currently Agent, Stitch, Patch, Bead, Plan,
Research, and File. `memory` is neither a compiled artifact-reference kind nor a pane.
The document-provider path is also sidecar-oriented: provider discovery finds a
sidecar ref policy, document inventories load from sidecar roots, and durable
per-document link indexes are written under those roots.

That last fact is important. Registering a `memory:` spelling is not sufficient to make
memory a normal document provider. Project memory lives in the primary repository;
Home memory may live in `~/sase/memory/` or a chezmoi source tree. The artifact link
store currently assumes that a document-shaped kind owns a sidecar root.

### 2.4 An accepted decision already rejected the literal storage idea

The accepted **Memory Webs** decision explicitly rejected “a generic artifact
database” as over-general for a small keyed set of short records. It chose a flat
descriptor plus sibling strand files because that preserves Git-native diffs,
per-strand identity, and tier-specific rendering.

That does not prohibit calling memory a source artifact or showing it in Artifacts.
It does mean a database/sidecar migration reverses an accepted choice and would require
a new superseding decision with new evidence. The existing record should not be edited
in place.

## 3. What the idea gets right

### 3.1 “Config” is an incomplete mental model

Flags and model defaults are configuration. A decision record, glossary entry, or
reviewed operational rule is durable project knowledge. Grouping all of them under
Config makes memory look like a knob rather than a corpus.

Artifacts is a better browse location if SASE wants users to think in terms of durable
entities—plans, agents, beads, research, and the knowledge those entities cite.

### 3.2 Memory wants stable identity

Today memory has three address shapes with different semantics:

- a source path such as `sase/memory/cli_rules.md`;
- an xprompt trigger such as `#memory/cli_rules`;
- a read selector such as `cli_rules.md` or `glossary:stitch`.

None is a canonical artifact-link endpoint. A `memory:` identity would enable copying
a durable reference, opening the correct scope, linking a plan or research report to
the policy that informed it, and reporting which agents consumed a note.

### 3.3 The catalog can be unified without changing authority

Backstage is the useful analogue: authoritative files stay in version control near the
source they describe, while an indexed representation makes them searchable and
navigable. SASE already follows this pattern for several panes. The catalog is a read
model over authority, not a replacement for authority.

### 3.4 A built-in pane can preserve memory's special rules

Artifacts already permits specialized built-in adapters for entities whose behavior
cannot be expressed as a generic document-provider declaration. Patch is the explicit
precedent: it consumes the common contract and shell while retaining its specialized
query, detail, and mutation implementation.

Memory fits that model better than it fits a generic document provider. It needs Home
scope, tier semantics, webs, audited reads, approval boundaries, generated-note rules,
and a publish action. A built-in adapter can expose common navigation, identity, copy,
refresh, and relation capabilities without flattening those domain rules.

## 4. Critique: where a literal migration goes wrong

### 4.1 It breaks revision locality

Project memory and the instruction files generated from it currently share one Git
revision with the code they govern. Moving memory to a sidecar creates two revisions:
the memory commit and the primary-repo commit containing `AGENTS.md` and provider shims.

SASE would then need to answer questions it currently avoids:

- Which memory-sidecar revision belongs to a branch or historical code commit?
- What happens when the sidecar updates but `AGENTS.md` has not been regenerated?
- Can publishing atomically commit and push two repositories?
- Can an ephemeral workspace start if the sidecar is absent, stale, or offline?
- Which repository owns a rollback?

Plans and research tolerate looser coupling because they describe work. Memory changes
the instructions under which work executes. Temporal skew is therefore more dangerous.

### 4.2 Home memory does not fit a project sidecar

Memory has project-first/Home-second resolution and explicit shadowing behavior. Home
memory may be ordinary local content or chezmoi-managed source shared by many projects.
A project artifact sidecar cannot represent that without either duplicating Home notes,
inventing a global artifact repository, or changing scope precedence.

Any migration design that handles project memory but says “Home later” is not a safe
migration; it creates two memory systems with different identity and publishing rules.

### 4.3 Snapshot/retention semantics are wrong for live policy

Explicit artifact files are immutable and permanent. Automatic captures may be
reclaimed or pruned. Memory notes are mutable authoritative source with guarded edits,
generated derivatives, and a current effective version.

Putting canonical notes into the indexed-file store would force one of two bad models:

- every edit creates a new immutable file identity, so the “current memory note” is a
  moving alias over snapshots; or
- memory bypasses immutability and retention, becoming a special case that only looks
  like an indexed artifact.

Git already supplies version history and content identity. Duplicating that history in
the artifact file store adds synchronization work without a demonstrated retrieval
need.

### 4.4 Normal Markdown link projection can contaminate instructions

For a normal Markdown artifact, SASE projects managed **Links** and **Referenced By**
tables into the Markdown document itself; `sase artifact read` strips those tables
before presenting the body.

Memory has more consumers: core rendering into `AGENTS.md`, `#memory` expansion,
`sase memory read/show`, README generation, web roster generation, and ACE preview.
If a memory note became a normal linked Markdown artifact, every one of those consumers
would need to strip managed link blocks consistently or link metadata would become
agent instructions. It would also make a link-graph update modify a policy-bearing
source file and mark the memory scope unpublished.

That is solvable, but it is not a free consequence of registration. A separate metadata
projection or a generalized non-invasive link store is safer than decorating canonical
memory Markdown.

### 4.5 A generic document pane would lose domain guarantees

The schema-v1 provider pane supports frontmatter properties, filtering, grouping,
static relations, detail, and read-only document inventory. It does not implement:

- project/Home first-wins resolution;
- descriptor-plus-strand webs;
- mention-closure auditing;
- core/reference loading behavior;
- proposal review and human-only promotion;
- generated-note protection;
- publish/regenerate semantics.

Flattening memory into document rows would either remove these behaviors or re-create
them beside the existing Memory subsystem. Both outcomes are worse than a built-in
adapter around the existing pane and catalog.

### 4.6 A second Memory surface would create UX and state divergence

Keeping Memory under Config while adding another fully interactive Memory subtab under
Artifacts raises immediate questions: which one owns bookmarks, unpublished state,
filters, mutation, and direct-entry routing? If one is read-only, users must learn why
the same corpus behaves differently in two places. If both write, concurrent state and
refresh bugs become likely.

The pane should move or be rehosted, not be cloned. A temporary forwarding entry is a
reasonable compatibility device; two permanent primary surfaces are not.

### 4.7 Hidden mounting can regress ACE startup

The current `MemoryPane` starts its initial load on mount. Artifacts mounts every pane
inside a `ContentSwitcher`, then activates panes lazily. Dropping `MemoryPane` into that
tree unchanged would scan scopes and memory files during startup even when the pane is
hidden, violating the established rule that first paint must not wait on data-scaled
work.

An Artifacts adapter must defer initial loading until first activation, keep disk work
off the event loop, preserve the mtime cache, and verify the existing p95 `<16 ms`
navigation target.

## 5. Options

| Option | Benefits | Costs and failure modes | Judgment |
| --- | --- | --- | --- |
| Keep the current Config Memory surface only | No work; all current guarantees remain | Memory stays outside the durable-entity catalog; no canonical artifact identity | Good if the motivation is only naming or tab preference |
| Add a second, read-only generic Memory document pane | Quick visual discoverability | Duplicate surface; loses Home/web semantics; not a real artifact identity; users cannot tell which surface is authoritative | Avoid |
| Move all memory into a dedicated artifact sidecar/store | Strong categorical uniformity; sidecar document provider mostly fits existing artifact plumbing | Cross-repo skew, Home mismatch, non-atomic publish, offline/bootstrap dependency, snapshot/retention mismatch, migration and compatibility burden | Reject without materially new requirements |
| Keep storage but move the existing specialized pane to Artifacts | Better information architecture; low data risk; reuses the real domain model | Needs lifecycle/contract integration and compatibility routing; identity/link benefits remain incomplete | Worth doing if UI placement is the main pain |
| Keep storage, add source-artifact identity, and rehost the specialized pane | Unified catalog and references while preserving authority, audit, publishing, and Git history | Requires a built-in resolver/adapter and careful scope identity; durable link projection should be staged | Best fit |

The fourth option is a coherent small slice. The fifth is the coherent destination.

## 6. Proposed architecture

### 6.1 Define memory as a source artifact

A memory artifact is a mutable logical entity whose authoritative versions are Git
objects. It is **not** an artifact-file row and never participates in artifact-file
prune, reclaim, generation retention, or `sase artifact create`.

The logical identity remains stable across content edits; Git supplies version identity
when an immutable historical version is needed. Generated memory notes are source
artifacts with `generated` provenance and remain read-only in the UI.

### 6.2 Add a scope-explicit canonical identity

The canonical stored identity must distinguish project and Home without relying on the
current directory's first-wins lookup. It should be path-based, not keyword- or
alias-based, so a strand keyword change does not silently change graph identity.

One workable shape is:

```text
memory:<scope>@<memory-relative-path>
memory:gh_sase-org__sase@cli_rules.md
memory:gh_sase-org__sase@glossary/stitch.md
memory:home@obsidian.md
```

The exact delimiter should be settled with the Rust grammar, but the invariants are
more important than the spelling:

- persisted references always contain an unambiguous scope;
- project identity uses a stable project key, not a display label;
- a strand's canonical identity uses its source path;
- `glossary:stitch` remains a friendly `sase memory read` selector, not the persisted
  artifact identity;
- optional shorthand may use project-first/Home-second resolution interactively, but
  is canonicalized before storage.

`#memory/<stem>` should remain the explicit content-injection syntax. `@memory:...`
should behave like other artifact citations and expand to portable semantic prose, not
silently inline instruction text. This preserves the distinction between launch-time
composition, artifact citation, and an audited runtime read.

### 6.3 Delegate artifact operations to the memory domain

The artifact facade should route rather than duplicate behavior:

- `sase artifact show/path/open memory:...` resolves through memory scope/path logic.
- `sase artifact read memory:...` delegates to the same selector/render/audit path as
  `sase memory read`, then emits at most one artifact consumption/read projection.
- Core notes preserve the existing “already loaded” rule rather than becoming an ad
  hoc second read path.
- Canonical writes remain `sase memory write` proposals or the human Memory pane.
- `sase artifact create` never creates or promotes memory.

The memory read ledger should remain authoritative. If unified agent-to-memory `read`
edges are useful, derive or transactionally project them from successful memory reads;
do not create two independent audit events that can disagree.

### 6.4 Add Memory as a built-in Artifacts adapter

Use the Patch precedent: contract-in, specialized implementation out.

The adapter should:

- register one fixed `memory` pane descriptor and stable icon/accent;
- wrap the existing `MemoryPane` and `memory_panel_catalog`, not the generic document
  adapter;
- bridge memory row identities to `ArtifactEntryTarget` and `memory:` refs;
- preserve the scope ring, tree, web expansion, auditing, mutations, and publish flow;
- expose only capabilities it truly supports;
- defer its first load until the pane's first activation;
- refresh through the existing cached/off-thread path;
- remain exempt from the shared artifact-file retention and version actions.

The current seven panes would become eight, so the existing digit scheme still fits;
Files can remain the highest assigned digit.

### 6.5 Move the surface; do not duplicate it

Route `gm`, glossary direct entry, command-palette actions, and copied `memory:` refs to
Artifacts → Memory. Preserve the current Config → Memory entry as a forwarding tile or
route for one compatibility window, sharing the same session bookmark, then remove it.

If editing memory inside Artifacts feels categorically wrong, that is evidence that the
desired change is only a read-only catalog lens—not evidence for a second full pane.
In that case keep the current Config pane and do not add an Artifacts subtab until there
is a concrete relationship/discovery use case.

### 6.6 Defer manual artifact-link projection in the first slice

Stable identity and a common pane do not require immediately projecting managed link
tables into memory Markdown. The accepted `corpus-before-mechanism` decision is directly
applicable: add durable memory relations only after real links demonstrate the need.

When that need arrives, generalize the artifact link store to support an authoritative
document root in the primary repo and Home—not only sidecars—and choose a non-invasive
metadata location. Do not special-case memory by sprinkling link-block stripping across
every prompt-rendering path unless that tradeoff is explicitly accepted.

## 7. Suggested rollout and acceptance criteria

### Phase 0 — record the boundary

Add a decision stating that memory notes are Git-backed source artifacts and that
artifact identity does not imply artifact-file storage. This complements the existing
Memory Webs decision. A full sidecar/database move, by contrast, would require a new
decision that explicitly supersedes its rejected-alternative conclusion.

### Phase 1 — identity and read-only facade

- Add `memory` to the Rust-owned artifact kind catalog and canonical grammar.
- Add project/Home/path resolution without changing existing memory selectors.
- Implement `artifact show/path/open/read` delegation.
- Add completion and portable prompt-citation rendering.
- Explicitly exclude memory from artifact-file inventory and lifecycle commands.

### Phase 2 — built-in ACE adapter

- Add the fixed Memory descriptor and contract.
- Add a thin lifecycle/entry-navigation wrapper around `MemoryPane`.
- Make first activation lazy and preserve current caches and workers.
- Route direct-entry actions to Artifacts → Memory.
- Keep a temporary Config forwarding entry instead of a second mounted pane.

### Phase 3 — remove the compatibility route

After one release and documentation update, remove Memory as a Config subtab if the
Artifacts location has proven clearer. Keep the standalone adapter only if another
caller still needs it.

### Phase 4 — relationships only on evidence

If plans, research reports, beads, or agents begin needing durable links to memory,
design primary/Home document-root storage and project memory read events into the graph.
Do not block the identity/UI work on speculative graph machinery.

Acceptance tests should prove:

- existing `sase memory read/show`, `#memory`, proposal, review, and init behavior is
  byte-for-byte or semantically unchanged;
- project and Home notes with the same path canonicalize to different identities;
- a renamed keyword alias does not change a strand's canonical identity;
- core notes do not gain an unintended ad hoc read path;
- generated notes stay read-only;
- `sase artifact list/prune/reclaim` does not treat live memory as retained snapshots;
- `gm` lands on the correct scope and note in Artifacts;
- hidden Memory does no startup scan;
- navigation remains below the established p95 target and the Artifacts conformance and
  PNG suites cover the new pane.

## 8. When this is not worth doing

Do not undertake even the hybrid work merely because “memory sounds more like an
artifact than configuration.” The current system is coherent, and the Admin Center
surface is new. The change earns its cost only if at least one of these is a real user
need:

- users look for durable knowledge beside plans/research/beads and fail to find it;
- memory needs canonical references that can be copied, opened, and cited;
- agent-to-memory consumption needs to appear in unified artifact provenance;
- memory needs typed cross-artifact relationships.

If none is currently painful, keep the status quo and revisit after the corpus produces
that evidence. UI taxonomy alone is not enough reason to churn a recently unified pane.

## Sources

Internal evidence was read at `bcd6813d2`, principally:

- `docs/memory.md`, `docs/artifacts_pane_contract.md`,
  `docs/artifacts_pane_visual_grammar.md`, and `docs/ace.md`;
- `src/sase/memory/`;
- `src/sase/ace/tui/memory_panel_catalog.py` and
  `src/sase/ace/tui/modals/memory_*.py`;
- `src/sase/ace/tui/modals/config_hub_catalog.py` and
  `src/sase/ace/tui/actions/agent_workflow/_prompt_bar_memory_panel.py`;
- `src/sase/ace/tui/_artifact_tab_*.py` and
  `src/sase/ace/tui/widgets/artifacts/`;
- `src/sase/artifact_providers/`, `src/sase/artifact_cli/read.py`,
  `src/sase/sdd/_artifact_link_projection.py`, and
  `src/sase/sdd/_artifact_link_store_*.py`;
- audited project decisions `decisions:memory-webs` and
  `decisions:corpus-before-mechanism`.

External comparisons:

- [Backstage: The Life of an Entity](https://backstage.io/docs/features/software-catalog/life-of-an-entity/)
  describes a catalog that ingests authoritative, owner-maintained YAML from version
  control and keeps its indexed representation synchronized.
- [Backstage: Descriptor Format of Catalog Entities](https://backstage.io/docs/features/software-catalog/descriptor-format/)
  uses the same entity semantics in human-maintained YAML and the catalog API.
- [SLSA 1.2 Terminology](https://slsa.dev/spec/v1.2/terminology) distinguishes source,
  build, dependency, and package roles while treating reviewed source itself as an
  artifact.
- [GitHub Actions: Workflow artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts)
  illustrates the narrower output-and-retention meaning that SASE should avoid
  accidentally imposing on live memory.

## Recommended solution

**Adopt a hybrid “source artifact” model and reject physical migration.** Keep
canonical memory in `sase/memory/` and `~/sase/memory/`, governed by the existing
proposal, audit, validation, Git, and `sase memory init` workflows. Add a scope-explicit
`memory:` identity and artifact facade, then rehost the existing specialized
`MemoryPane` as a built-in Artifacts subtab with lazy activation. Route the Config entry
to that pane temporarily and remove the duplicate route after a compatibility window.

Do not put memory into the indexed-file store, retention system, generic document pane,
or a dedicated sidecar. Defer durable manual artifact-link projection until real links
justify generalizing the link store for primary/Home source roots. This captures the
valuable part of the idea—durable identity, better information architecture, and a
future relationship boundary—without sacrificing revision locality or creating a
second source of truth.
