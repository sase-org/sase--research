# Critique: Supersession in SASE Memory Webs

**Research question:** Should a memory strand be able to supersede another strand so
that generated memory-web rosters show only current strands while `sase memory
show/read` preserves access to the superseded history?

**Scope:** Product and data-model critique, including hub-note semantics, ADR practice,
the current SASE implementation, artifact-link reuse, rendering behavior, validation,
and agent authoring guidance. This is not an implementation plan.

**Evidence date:** 2026-08-30. Repository behavior was inspected at `sase@40cd8ce6eaf4`
and prior research at `sase--research@870f325c18dd`.

## Bottom line

The idea is worth doing, but for a narrower reason and with a narrower design than the
proposal initially suggests.

The important benefit is not saving a few roster tokens. It is preventing agents from
mistaking a historical decision for a current one while retaining the rationale that
made the historical record valuable. That is a real correctness property for the
`decisions` web and is consistent with established ADR practice: accepted records stay
immutable, replacements are new records, and old records remain available as history.

However, SASE should not describe the resulting roster as a faithful Bob Doto-style hub
note. Doto's hub points to the *first* note in a train of thought so a reader can traverse
the sequence. A roster that hides the old entry point and exposes the current replacement
is better understood as an **active index** or **current-state roster**. That divergence
is justified for agent instructions, whose first job is to communicate current policy,
but naming the distinction avoids drawing the wrong design conclusions from the hub-note
analogy.

I recommend proceeding only when there is a genuine whole-strand replacement to ship
with the feature. Add one intrinsic, directed `supersedes` relation to strand
frontmatter; derive active versus historical status from that relation; hide historical
strands only from generated rosters; and render one-hop typed references in both
directions during reads. Do not make the external artifact-link store authoritative for
memory initialization yet, do not automatically inline an entire history chain, and do
not mark the current partial amendment between SASE's two memory-web decisions as a
whole-record supersession.

## 1. What the hub-note analogy does and does not support

Bob Doto distinguishes finding from developing. A hub note points to the first note in
a linked train of thought and gives the reader a place to begin exploring; a structure
note reorganizes ideas into an argument. The cited article therefore supports three
useful properties for memory webs:

1. The descriptor is navigational rather than the place where strand bodies are
   developed.
2. The descriptor should expose useful entry points rather than reproduce every body.
3. Following an entry point should reveal related context.

It does **not** directly support hiding older entry points. In Doto's model, the first
note in a sequence is precisely what the hub exposes. If `old <- new` is treated as a
train, listing only `new` reverses that convention. The proposed behavior is still
appropriate, but it serves operational currency rather than exploratory chronology.
The generated `AGENTS.md` document is closer to an active policy index than a
zettelkasten exploration surface.

There is a second mismatch: SASE's descriptor currently carries an exhaustive,
automatically managed roster of every strand. That makes it more index-like than Doto's
selective hub even before supersession exists. Supersession would improve the active
view, but it would not by itself make the descriptor a hub in the stricter sense.

Source: Bob Doto,
[The Difference Between Hub Notes and Structure Notes Explained](https://writing.bobdoto.computer/the-difference-between-hub-notes-and-structure-notes-explained/).

## 2. The lifecycle idea is sound

The strongest external analogy is ADR lifecycle, not hub-note structure.

Michael Nygard's original ADR proposal says to retain a reversed decision, mark it
superseded, and reference its replacement. AWS's ADR guidance likewise treats accepted
records as immutable: changed direction is recorded in a new ADR that supersedes the
old one, while the collection remains the project's decision history. Those properties
map cleanly to SASE:

- the active roster is the skimmable current-decision view;
- the strand body is the detailed record;
- the old strand remains addressable by its stable slug;
- the directed relation explains why the old record left the active view; and
- a direct read of historical identity still returns that historical record.

The RFC Series offers an especially useful semantic warning. It distinguishes a
replacement that can stand alone from an update that must be read together with the old
document. The current RFC Editor guidance similarly says an obsolete RFC remains in the
archive even though the replacement should normally be used for current practice. SASE
needs the same whole-versus-partial distinction. “Supersedes” must mean the newer strand
is the current replacement for the older strand as a whole; a correction to one
sentence, an addendum, or a narrower decision does not qualify.

Sources:

- Michael Nygard,
  [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
- AWS Prescriptive Guidance,
  [Architectural decision record process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html).
- RFC Editor,
  [RFC relationships and changes](https://www.rfc-editor.org/series/rfc/) and
  [RFC 1111 section 6](https://www.rfc-editor.org/rfc/rfc1111.html#section-6).

## 3. The current SASE corpus exposes the need—and the main trap

The `decisions` web currently has eight strands. Its descriptor says accepted records
are immutable and that a change of course creates a new record while the old one is
marked superseded in prose. Yet the generated roster lists every record without status,
and exact `show/read` output has no typed supersession neighborhood.

The pair that looks like a ready-made example is not actually a whole-record
supersession:

- `memory-webs` chooses the descriptor-plus-strand storage and addressing model.
- `webs-render-in-their-own-section` changes one earlier sentence about where a
  descriptor body renders while leaving the storage and addressing decision intact.

The newer record explicitly says that it supersedes a *sentence* in the older record.
Under the whole-document distinction above, the older decision remains current and must
stay in the active roster. Hiding it would remove the still-authoritative decision that
memory webs exist as flat descriptors plus sibling strand directories. This is evidence
that a plain `status: superseded` convention would be too easy to misuse.

The prior research report
[`decision_web_seed_adrs.md`](decision_web_seed_adrs.md) correctly anticipated a small
supersession chain for ADRs, but it also recommended waiting until decision strands
became artifacts before using the artifact relation. The current implementation now has
more native memory-link machinery than that report assumed, which changes the best
near-term design.

## 4. What SASE already has

Most rendering mechanics now exist:

- A strand has stable filename identity (`slug`), mutable display identity (`keyword`),
  aliases, opaque metadata, and body content.
- `sase memory show/read` resolves exact strands before rendering and supports project
  over home scope merging.
- Authored `[[...]]` links render as references, while `![[...]]` or an inline rendering
  policy can expand linked memory through the existing closure walk.
- The closure engine is breadth-first, depth-aware, deduplicated, and able to report
  referrers.
- The managed roster is generated from the complete ordered strand tuple.
- Validation already fails closed for malformed descriptors, invalid strands, missing
  directories, collisions, and other memory-web invariants.

The missing piece is not generic graph traversal. It is an authoritative typed edge
that affects lifecycle state. Today:

- `metadata.status: accepted` is parsed but not given lifecycle semantics;
- prose such as “supersedes the sentence in `memory-webs`” is not a typed link;
- the roster has no active/historical filter;
- a bare web selector still means every strand; and
- `sase_memory_write` explains authorization and publication but not strand lifecycle.

That makes the proposed feature medium-sized rather than foundational. It touches the
strand model/parser, scope and graph validation, roster generation, Markdown/rich/JSON
renderers, web inspection, memory initialization and doctor checks, the memory panel,
tests, generated documentation, and the source xprompt skill. It does not require a new
closure engine.

## 5. Why the artifact relation store should not own this yet

The existing `supersedes` / `superseded-by` artifact vocabulary is exactly the right
direction and meaning: the replacement is the source and the old artifact is the
target. Reusing that vocabulary is desirable. Reusing the current storage path as the
authoritative source is not.

Artifact-link truth for document artifacts is stored in per-artifact JSON indexes under
document sidecar repositories, with a machine-local aggregate as a rebuildable read
model. Memory strands are not currently artifact-reference kinds, the primary memory
tree is not one of those document sidecars, and `sase memory init` renders agent
instructions from committed memory files without requiring artifact-link sidecars or a
machine-local aggregate.

Making roster generation consult the artifact graph would introduce several problems:

- the same primary commit could render different agent instructions depending on which
  sidecars or aggregate generation are present;
- adding one successor would no longer be atomic with the memory files that define both
  endpoints;
- home memory would need an artifact ownership and publication model it does not have;
- initialization and doctor would acquire cross-subsystem failure modes; and
- an unavailable relation store could accidentally resurrect obsolete entries or hide
  current ones unless generation failed closed.

The existing `memory-webs` decision says that artifact relations are the adopted
mechanism once supersession outgrows prose. That sentence should be revisited before
implementation. It chose the right semantic registry but did not account for the
source-of-truth and deterministic-generation boundary. The new design should explicitly
distinguish **shared relation semantics** from **shared persistence**.

## 6. Alternatives considered

### A. Keep prose and list every strand

This has no implementation cost and is adequate while supersession is hypothetical.
It fails as soon as a real replacement exists: the always-loaded roster cannot tell an
agent which decision is current, and exact reads cannot reliably discover the other end
of the relationship. It also puts correctness on wording conventions that validators
cannot check.

**Verdict:** acceptable until the first true replacement, not a durable solution.

### B. Set `metadata.status: superseded` on the old strand and add a wiki link to the new

This uses existing parser and renderer pieces, but it creates two writable facts: the
old status and the new link. They can disagree. It also edits a record whose body is
supposed to be immutable and does not establish a typed direction unless prose is
parsed. A status flag answers “is this active?” but not “what replaced it?”

**Verdict:** too drift-prone for a lifecycle invariant.

### C. Make memory strands first-class artifacts and use `sase artifact link add`

This produces one graph vocabulary and enables existing artifact browsing. It also
requires a memory artifact provider, canonical identity rules, storage ownership for
project and home memory, deterministic projection into initialization, publication and
repair behavior, and a decision about whether memory reads are also artifact reads.
That is much more mechanism than this corpus currently justifies.

**Verdict:** plausible long-term convergence, excessive as the first implementation.

### D. Add a local, typed `supersedes` field to successor frontmatter

For example:

```yaml
---
keyword: Prefer explicit audited memory retrieval
supersedes: [automatic-runtime-memory-recall]
---
```

The edge is stored with its source, committed atomically with the successor, uses stable
slug identity, and is available to initialization without another store. Active status
is derived: a strand is historical when it is the target of a valid supersedes edge.
The relation can later project into the artifact graph if memory strands acquire a
first-class artifact kind. Until then, the frontmatter edge is the only authority.

This is technically a memory-specific encoding, so it conflicts with the literal “not
a new, parallel link syntax” language in the existing decision. That cost is smaller
than creating two authorities or making deterministic initialization depend on an
external graph. Reusing the artifact relation's slug, direction, inverse label, and
one-hop rendering rules prevents a parallel *meaning* even though persistence is local.

**Verdict:** recommended.

### E. Remove superseded files or redirect old selectors to the new strand

Deletion destroys rationale. Redirecting changes the meaning of stable identity and
makes an audited read of the old record impossible. Both contradict ADR history and
the archival behavior of mature immutable-document systems.

**Verdict:** reject.

## 7. Recommended semantics

### 7.1 Relation and validation

Use a top-level `supersedes` list on the successor. In the first version:

- Targets are canonical filename slugs, not keywords or aliases.
- Both endpoints must be in the same web and the same source root. Project-over-home
  shadowing remains a separate mechanism, not implicit supersession.
- Self-edges, missing targets, duplicate targets, and cycles are blockers in both
  `sase memory init` and `sase doctor`.
- One successor may supersede several older strands, allowing consolidation.
- One older strand may have at most one immediate successor. Competing replacements
  would make “current” ambiguous and should require a later consolidating decision.
- Supersession means whole-strand replacement. Partial amendments stay as ordinary
  linked prose and leave both records active.
- Derived lifecycle state, not hand-authored `metadata.status`, controls roster
  membership. Existing values such as `status: accepted` may continue to describe how
  the decision was adopted; they do not need to be rewritten when a later edge makes
  the record historical. A hand-authored `status: superseded` without a matching edge
  should be rejected rather than treated as a second authority.

These constraints produce a set of chains or converging chains with unambiguous active
heads. They are intentionally stricter than a general graph.

### 7.2 Views and reads

Different surfaces serve different jobs:

| Surface | Recommended behavior |
| --- | --- |
| Generated `Memory Webs` roster | List active strands only. The shared intro should say that superseded history is exposed on reads. |
| `sase memory web show <web>` | Show all strands, grouped or labeled as active/superseded, with immediate relation endpoints. This is an inspector, not the active hub. |
| `show/read <web>:<active>` | Render the requested body and a typed, one-hop `supersedes` reference to each immediate predecessor. Do not inline predecessor bodies by default. |
| `show/read <web>:<old>` | Render the exact old body, plus a prominent `superseded-by <web>:<new>` warning/reference. Never silently redirect. |
| Bare `show/read <web>` | Preserve the current “all strands” contract initially, but label lifecycle state. Add an active-only flag later only if real web size makes it useful. |
| JSON output | Include stable `supersedes`, `superseded_by`, and derived `lifecycle` fields. |

One hop is enough. It matches SASE's artifact-neighborhood precedent, bounds context,
and lets a reader follow a long history deliberately. A successor may still contain an
explicit `![[old-slug]]` when the author has a specific reason to inline the old body,
but supersession itself should add a typed reference rather than unconditionally pulling
history into every read.

### 7.3 Authoring guidance

Update the source `/sase_memory_write` xprompt skill in the same implementation. It
should tell agents:

1. Use `supersedes` only when the new strand stands alone as the current replacement
   for the old strand as a whole.
2. Put the edge on the successor and target the old file's slug; never delete the old
   file or rely on a mutable keyword/alias.
3. Do not edit the accepted old body merely to announce supersession; the inverse view
   is derived.
4. For a partial correction or narrower follow-on, use ordinary linked prose and keep
   both strands active.
5. Prefer the default reference rendering; add an explicit inline link only when every
   read of the successor genuinely needs the old body.
6. Run `sase memory init` after an authorized edit and treat graph-validation failures
   as blockers.
7. Remember that superseding a strand changes always-loaded agent instructions by
   removing its roster entry, even though the old body remains readable.

The generated memory README, the memory-read skill, and the shared Memory Webs intro
should also explain that rosters are active views. Updating only the write skill would
teach authors the syntax but leave readers with the old “roster names every strand”
mental model.

## 8. Rollout and stopping rule

Do not implement this solely to hide the older `memory-webs` decision: that would be a
semantic regression because the newer record changes only one of its claims. The
current corpus therefore yields essentially no correct roster reduction today.

Instead, land the feature alongside the first genuine whole-record replacement. A good
acceptance example would be the prior research's proposed transition from automatic
runtime memory recall to explicit audited retrieval, provided the successor restates
the complete current choice and can stand alone. That gives the mechanism a real corpus
and exercises the exact history-preserving behavior it exists to provide.

The first release should stop at intrinsic memory semantics. Do not add cross-web
supersession, multiple competing successors, transitive automatic inlining, a generic
memory relation registry, or artifact-provider integration. Revisit artifact projection
only when memory strands need other artifact relations or other artifact surfaces need
to address them. At that point, keep one authority: either project the frontmatter edge
into the artifact graph or migrate ownership to the artifact store, never allow both to
be edited independently.

## Final recommendation

**Proceed, but implement an active-roster lifecycle rather than a generalized history
graph.** Use a validated, same-web `supersedes` edge stored on the successor; derive the
old strand's historical state; omit it only from generated rosters; preserve exact reads
with a superseded-by warning; and expose immediate predecessors as references when the
successor is read. Update `/sase_memory_write` and the reader-facing memory guidance in
the same change.

Gate the implementation on the first true whole-strand replacement. Until then, keep
the current records visible and use ordinary explicit links for partial amendments.
This preserves the project's corpus-before-mechanism discipline while establishing a
clear solution for the point at which the decisions web genuinely needs history-aware
navigation.

## Internal evidence reviewed

- `sase/memory/decisions.md`
- `sase/memory/decisions/memory-webs.md`
- `sase/memory/decisions/webs-render-in-their-own-section.md`
- `src/sase/memory/web/frontmatter.py`
- `src/sase/memory/web/models.py`
- `src/sase/memory/web/roster.py`
- `src/sase/memory/web/scope.py`
- `src/sase/memory/selector.py`
- `src/sase/memory/selector_render.py`
- `src/sase/xprompts/skills/sase_memory_write.md`
- `docs/artifact_links.md`
- [`decision_web_seed_adrs.md`](decision_web_seed_adrs.md)
