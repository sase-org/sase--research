---
create_time: 2026-08-28
updated_time: 2026-08-28
status: research
tags: [memory, artifacts, artifact-refs, ace, architecture, sase-core]
---

# Should SASE Memory Migrate From Configuration Into Artifacts?

**Research question:** SASE memory notes are treated as configuration today — they live
under `sase/memory/`, they are browsed and edited from the **Memory** sub-tab of the
**Config** hub, and `sase memory init` compiles them into `AGENTS.md` plus the provider
instruction shims. Should memory instead become an artifact, with a canonical
`<kind>:<argument>` identity, typed links, artifact reads, and a **Memory** sub-tab under
**Artifacts**? If so, how much of it; if not, what is the right smaller change?

**Scope:** Consolidation of two independent reports written the same day against `sase`
at `bcd6813d2`, plus the `sase-core` checkout and the `plans`, `research`, and `agents`
sidecars, all read 2026-08-28. Architecture research only; no behavior changed.

**Sources merged:** `memory_as_artifacts__a.md` (report A) and
`memory_as_artifacts__b.md` (report B), in this directory. The two were written in
parallel and collided at the same path. They reached compatible verdicts on three of the
four sub-proposals and genuinely disagree on the fourth; §3 resolves that disagreement on
report B's measured evidence rather than by splitting the difference. Report A supplies
the external precedent and the design constraints; report B supplies the measurements.
Numbers below are report B's unless stated otherwise, and the commands that produced them
are in `memory_as_artifacts__b.md`'s appendix.

---

## Bottom line

**Give memory an artifact *identity*. Do not move memory's bytes, and do not build a
Memory sub-tab under Artifacts yet.**

Both reports independently concluded that "move memory into artifacts" is not one
proposal but several with opposite answers, and both landed on the same principle. Report
A names it **promote, do not relocate**: artifact should be an identity, catalog, and
relationship boundary for memory — not a storage mandate. Report B reaches the same place
from measurement and adds the sharper negative: the demand signal in the corpus is a
demand for *citation*, not for browsing.

| # | Sub-proposal | Verdict | Agreement |
| --- | --- | --- | --- |
| P1 | A `memory:` artifact-reference kind — identity, typed links, rename-following, pointer expansion | **Do it** | Both reports (A §6.2, B Phase A) |
| P2 | Read-log consolidation — memory reads reach the artifact read channel | **Do a narrow version** | Both (A §6.3, B Phase B); B specifies it |
| P3 | A Memory sub-tab under Artifacts | **Not now** | **Reports disagree**; resolved in §3.1 |
| P4 | Memory files into the artifact store, with `create`/`prune`/`reclaim`/`trash` | **Never** | Both, emphatically (A §4.3, B §5) |

The value is heavily front-loaded: P1 is roughly 4 medium phases, P2 roughly 2, and P3 —
if it is ever justified — is a separate epic on the order of `sase-tj` (9 phases plus a
follow-on child epic) that must be scoped on its own evidence.

---

## 1. What both reports established independently

Where two researchers working separately reached the same conclusion, the finding is
worth more than either report's framing of it.

### 1.1 Memory is policy-bearing source, not inert configuration

Report A: core notes compile into `AGENTS.md` and the provider shims, reference notes are
addressed by audited `sase memory read`, every flat note is a `#memory/<stem>` composition
source, webs add strands with scope merging and validation, and agent writes go through
proposals and human review. "Configuration" undersells it; memory is closer to reviewed,
executable documentation.

Report B measures the same claim from the other end: `memory_reads.jsonl` holds **8,772**
read events from **3,848 distinct agents**, against **284** artifact reads — memory is the
most-read context class in SASE by 31×. Filing the most-read context class under "Config"
is, in B's words, defensible historically and indefensible on first principles.

Both also agree on the counterweight, which matters for P3: `sase memory list`'s
loaded / referenced-only / available / missing inventory, instruction roots, line counts,
and token approximations is a *compiler inventory* for generated agent instructions
(B §4.5). Half of what memory is really is configuration.

### 1.2 The corpus is small, dense, and already citing itself by hand

70 project memory files (17 flat notes — 7 core, 9 reference — plus 53 strands across
`decisions` 7, `glossary` 41, `task_types` 5), 3 Home notes, and a ~382-line /
~5,098-token always-loaded core budget. Report A counted the same 70 and drew the same
conclusion: a real corpus, not a speculative category.

Report B then measured what the corpus does *without* an identity: **625 documents cite
memory notes as hand-typed `sase/memory/<note>.md` path strings** — 392 of 4,051 plans
(9.7%), 97 of 450 research reports (21.6%), 136 of 4,853 archived prompts — with the plan
rate accelerating 12% (July) → 31% (August). Those citations are untyped, unresolvable,
do not follow renames, and are invisible to a link graph that holds 14,209 rows and
exactly zero memory rows. Report A independently identified the same gap analytically:
memory has three address shapes (source path, `#memory/` trigger, read selector) and none
is a canonical artifact-link endpoint.

This is the evidence that clears the `corpus-before-mechanism` bar, and it clears it for
citation specifically.

### 1.3 Managed link tables must never reach a memory note

The single most important shared design constraint, found by both reports from different
directions. Artifact links render *into* the Markdown: a `Links` table near the top and a
bottom-anchored `Referenced By` block. Memory note bodies are inlined verbatim into
`AGENTS.md` and four provider instruction shims. A naive registration therefore writes
link metadata into every agent's always-loaded context, against a ~5,098-token core
budget — and report A adds that it would also make a graph update mutate a policy-bearing
source file and mark the memory scope unpublished.

Report A's remedy is to defer durable link projection entirely in the first slice
(`corpus-before-mechanism` again) and, when it arrives, to generalize the link store to a
non-invasive metadata location for primary-repo and Home roots. Report B's is to ship P1
with publication suppressed from day one — links render on the *other* endpoint, the
treatment `stitch` already gets — plus a `sase doctor` check that fails if a managed block
ever appears under `sase/memory/`. These are compatible: adopt B's suppression and doctor
check as the day-one invariant, and A's deferral as the policy for durable memory-side
link storage.

### 1.4 P4 is a category error

Report B's table is the clearest statement of it: the artifact store is immutable
snapshots with `prune`/`reclaim`/`trash` retention, recording *what happened*, where
staleness is harmless; a memory note is continuously edited, git-versioned alongside the
code it describes, stating *what is currently believed*, where staleness actively
misinforms every agent. Report A reaches the same conclusion and adds three consequences a
storage move would create: broken revision locality between memory and the `AGENTS.md` it
generates (which revision belongs to which code commit? can publish commit two repos
atomically? can an ephemeral workspace start if the sidecar is stale or offline?), Home
memory that no project sidecar can represent without duplicating notes or changing scope
precedence, and the accepted **Memory Webs** decision having already rejected "a generic
artifact database" — so a storage move needs a new superseding decision, not a
re-reading of the old one.

Report B supplies the constructive half: `plan:` and `research:` are already artifacts
that are *not* store-backed — living Markdown in a git sidecar, resolved by path. That is
the shape memory should borrow. **Memory should be artifact-referenced, never
artifact-stored.**

### 1.5 The base rate for building memory machinery here is poor

`sase memory write` proposals plus the `sase memory review` TUI are 2,362 LOC, and
`memory_proposals.jsonl` **does not exist in any of the 31 registered projects** — zero
proposals ever written, with only a stale lock file in the flagship project. That is a
fourth unused retrieval mechanism after the three the `corpus-before-mechanism` record
already documents, and it was built *after* that record was accepted. Any new memory
machinery should be sized to its evidence.

---

## 2. The unbundling

Report A frames the proposal as five independent axes; report B as four sub-proposals.
They are the same decomposition, and merging them gives the useful table: only the last
row is a physical migration.

| Axis | Change | Requires relocating files? | Verdict |
| --- | --- | --- | --- |
| Taxonomy | Call memory notes and strands source artifacts | No | Free; record it |
| Identity | Canonical `memory:` references and resolution | No | **P1 — do it** |
| Relationships | Memory participates in typed links and read provenance | No, but durable link storage needs design | **P2 — narrow version** |
| Presentation | Memory browsed under ACE's Artifacts tab | No | **P3 — not now (§3.1)** |
| Storage/lifecycle | Memory in a sidecar, CAS, indexed-file store, or retention | Yes | **P4 — never** |

Report A's external survey supports exactly this split. SLSA 1.2 defines an artifact
broadly as an immutable blob but explicitly treats reviewed *source* as an artifact, and
Backstage ingests version-controlled YAML into a catalog without the catalog becoming the
source of truth. GitHub Actions' narrower "output of a workflow run, retained" meaning is
the one SASE must not accidentally impose on live memory. Catalog membership does not
determine storage.

---

## 3. Conflicts between the reports, resolved

### 3.1 The Artifacts Memory sub-tab: report B is right — not now

This is the substantive disagreement. Report A's fifth option — keep storage, add
source-artifact identity, **and rehost the existing specialized `MemoryPane` as a built-in
Artifacts adapter** on the Patch precedent, with a temporary Config forwarding route
removed after one release — is its recommended destination. Report B recommends the
opposite (Phase C): no new sub-tab, the pane stays in Config, and Artifacts *reaches*
memory through relations rails plus one navigation route.

**Resolved for report B**, on three grounds:

1. **Measured cost.** `sase-tj` added *one* fixed Artifacts pane for `agent` — a class that
   already had a ref kind, a store, publication, and link-graph presence — and still took
   9 phases plus a follow-on child epic `sase-tj.10` for landing gaps. A Memory pane starts
   *behind* that: no ref kind, no store rows, no query profile, and a 5,741-LOC existing
   pane across 19 modules to reconcile. Report A acknowledges the same pane and the same
   reconciliation risk (its §2.2 and §4.6) but does not price the work.
2. **No demand signal points at browsing.** The 625 hand-rolled citations are demand for
   citation. Report A's own §8 sets the bar — do this only if users look for durable
   knowledge beside plans/research/beads and fail to find it, or memory needs copyable
   references, unified provenance, or typed relationships — and three of those four are
   satisfied by P1 alone. The remaining one is unevidenced.
3. **The abstraction fits poorly where it would land.** An Artifacts pane's characteristic
   verbs — prune, reclaim, restore from trash — are meaningless or dangerous for memory and
   would need suppressing via `PaneDeclaredFacts.suppressions`. A pane defined mostly by
   what it turns off is a signal the abstraction does not fit. Report A reaches an adjacent
   version of this point in its §4.5 (a generic document pane would lose project/Home
   resolution, webs, mention closure, proposal review, generated-note protection, and
   publish semantics) but answers it with a built-in adapter rather than by declining.

Report A's framing is not discarded, and two of its contributions survive as binding
constraints **if** P3 is ever revisited:

- **The information-architecture critique stands.** "Config" is an incomplete mental model
  for a corpus read 8,772 times as context. P1 plus report B's Phase C navigation seam
  addresses the discovery problem without a second pane; if it does not, that is evidence
  for reopening, and §5 names the threshold.
- **The startup constraint is real and specific.** `MemoryPane` starts its initial load on
  mount, while Artifacts mounts every pane inside a `ContentSwitcher` and activates lazily.
  Dropping the pane in unchanged would scan scopes and memory files during startup even
  while hidden, violating the rule that first paint must not wait on data-scaled work. Any
  future adapter must defer first load to first activation, keep disk work off the event
  loop, preserve the mtime cache, and hold the p95 <16 ms navigation target. Report B does
  not identify this hazard; it is report A's and it should be carried forward verbatim.

Both reports agree on the one thing that must not happen either way: **do not run two
Memory surfaces.** Report A: move or rehost the pane, do not clone it; a temporary
forwarding entry is fine, two permanent primary surfaces are not. Report B: keep the one
that exists. Under this recommendation the question does not arise.

### 3.2 Identity spelling: adopt report A's scope invariants, report B's selector shape

Report B proposes `memory:<note>.md` and `memory:<web>:<strand>`, deliberately matching
the selector spelling agents already know, and files the project/Home ambiguity as open
question #1. Report A goes further and argues the persisted identity must be
scope-explicit and path-based rather than resolved by first-wins lookup, sketching
`memory:<scope>@<memory-relative-path>` (`memory:gh_sase-org__sase@glossary/stitch.md`,
`memory:home@obsidian.md`).

These are reconcilable and report A's invariants should govern, because B's own framing of
the risk — "a citation that silently means different files in different projects is a
worse failure than a read that does" — argues for A's conclusion:

- persisted references always carry an unambiguous scope, using a stable project key
  rather than a display label;
- a strand's canonical identity is its source path, so renaming a keyword alias does not
  silently change graph identity;
- `glossary:stitch` stays a friendly `sase memory read` selector, and interactive
  shorthand may resolve project-first, but both canonicalize before storage.

The exact delimiter is a vocabulary decision to settle once with the Rust grammar
(§6, question 1). Report B's two-colon concern is real but is a spelling question inside
those invariants, not a challenge to them.

### 3.3 Read provenance: report B's narrow version, for report A's reason

Report A's constraint: the memory read ledger stays authoritative, and unified
agent-to-memory `read` edges must be *derived or transactionally projected* from
successful memory reads — never two independent audit events that can disagree. Report B
supplies the measurement that turns this into a hard limit: memory's 8,772 reads dedup to
**7,137 distinct (agent, note) pairs**, which is a ~50% increase in total graph size and
**56× the entire existing `read` relation**, into a 6.0 MB `artifact-links.json` that
already has an open bead (`sase-ua`) about the aggregate going stale and dropping `read`
rows.

Resolution: `sase memory read` keeps writing `memory_reads.jsonl` as the volume channel,
and emits a `read` link edge **only** when the read resolves through a `memory:` ref. Do
not backfill history. Separately, collapse the three near-clone ACE loaders —
`memory_reads.py` (279), `artifact_reads.py` (287), `glossary_reads.py` (279) — into one
parameterized loader (~845 LOC → ~350), which retires the legacy `glossary` clone as a
side effect. That refactor is behavior-preserving and independently testable, and it is
the part of P2 that pays for itself regardless of what happens to P1.

### 3.4 Whether this is worth doing at all

Report A ends with a genuine "do not do this merely because memory sounds more like an
artifact than configuration." Report B ends with a pre-committed falsification test. They
point the same way, and B's is the more useful instrument, so §5 adopts it — but A's
caution applies to the *ordering*: nothing here justifies churn to a pane that was unified
into its current home eight days before both reports were written.

---

## 4. Recommended solution

**Adopt a source-artifact model for memory: `memory:` becomes a real reference kind, the
bytes and the browse surface stay where they are.**

### Phase 0 — record the boundary

Add a decision stating that memory notes are git-backed *source artifacts*, and that
artifact identity does not imply artifact-file storage or artifact-file lifecycle. This
complements the accepted `memory-webs` record rather than superseding it; a storage move
would need its own superseding record and new evidence.

### Phase A — `memory:` becomes an artifact-reference kind (~4 medium phases)

The cheap path does not exist and should not be attempted: document ref kinds are keyed to
`repos.sidecar` roles, and memory lives in the primary repo and must. This is the
`rust-core-required` path.

1. **`sase-core`:** add a `Memory` variant to `ArtifactRefKindWire` and a
   `KindRegistration` in `artifact_ref/kinds.rs`; extend the wire and binding; add the kind
   to the closed set validated by `ArtifactRef.from_wire`.
2. **Python:** add a builtin entry resolver modeled on `builtin_entry_bead.py`, registered
   in `resolve_builtin_entry`. **Reuse `sase.memory.selector` and `memory_read_root`; do
   not write a second resolver.** Entry properties come from note frontmatter (`type`,
   `parent`, `priority`, `description`).
3. **Scope-explicit canonicalization** per §3.2: persisted refs always name a scope, strand
   identity is path-based, and friendly selectors canonicalize before storage.
4. **Expansion is a pointer, not a body** — the plan provider's format ("the
   `sase/memory/tui_perf.md` reference memory note; read it with `sase memory read`"). This
   is the design choice the phase turns on: it is what the 625 prose citations are
   hand-rolling, and it is exactly where `#memory/` went wrong by inlining `note.body`
   (6 uses in 4,853 prompts).
5. **Publication suppressed from day one** — no `Links` table or `Referenced By` block ever
   written under `sase/memory/`, links render on the other endpoint, and a `sase doctor`
   check fails if a managed block appears. Defer durable memory-side link storage until real
   links justify generalizing the store for primary-repo and Home roots.
6. **Decide `#memory/` explicitly** — recommended: keep it, deprecate it in docs, document
   `@memory:` as the canonical form. Two live, differently-behaved citation syntaxes without
   a stated canonical one is the "parallel link syntax" the `memory-webs` record warns
   against.
7. **`sase artifact create` never creates or promotes memory**, and memory is explicitly
   excluded from artifact-file inventory, prune, reclaim, and retention commands. Canonical
   writes remain `sase memory write` proposals or the human Memory pane.

Immediately unlocked: `sase artifact link add bead:sase-x implements
memory:decisions:two-speed-verification`; rename-following for the 625 citations via
`sase-tw.4`'s repair pass; `@memory:` completion; and the `memory-webs` reopen clause —
which already names *artifact relations* as the adopted supersession mechanism — becomes
executable for the first time.

### Phase B — one read channel, two logs (~2 medium phases)

Collapse the three ACE loaders; emit a `read` edge only for citational, ref-resolved reads;
do not backfill (§3.3). Let `sase memory write --evidence` accept canonical artifact refs
with `path`/`chat:`/`url:`/`note:` kept as legacy spellings — noting that `chat:` is
already a real ref kind that memory reimplemented privately. Given zero proposals across 31
projects, whether the 2,362-LOC proposal subsystem should be *retired* rather than improved
deserves its own decision and is a cheaper win than anything in P3.

### Phase C — Artifacts reaches memory; memory keeps its home

No new sub-tab. Once `memory:` refs exist, memory rows appear in the relations rail of the
Bead, Plan, and Agent panes for free — that is where "which memory does this bead
implement?" is answered. Add one navigation seam: selecting a `memory:` row in any
relations rail routes to the Config hub's Memory pane at that note, which
`ConfigHubEntry.note` already supports. A route, not a pane.

### Never

Memory files do not enter the artifact store, and memory notes never acquire `prune`,
`reclaim`, or `trash`.

### Acceptance criteria

- `sase memory read/show`, `#memory`, proposal, review, and `init` behavior is
  semantically unchanged;
- project and Home notes with the same relative path canonicalize to different identities,
  and a renamed keyword alias does not change a strand's canonical identity;
- core notes gain no ad hoc second read path, and generated notes stay read-only;
- `sase artifact list/prune/reclaim` never treats live memory as a retained snapshot;
- no managed link block is ever written under `sase/memory/`, enforced by `sase doctor`;
- the link graph gains no bulk memory `read` rows.

---

## 5. What would reopen P3

Report B's thresholds, adopted verbatim because they are falsifiable. Revisit the Artifacts
Memory sub-tab when **any** becomes true:

- manual memory link rows (excluding `read` edges) exceed ~50;
- a second project's memory corpus exceeds ~40 notes (today: 70 in `sase`, 3 at Home);
- memory supersession becomes routine — say the `decisions` web reaching ~25 records with
  active supersession chains, which is the `memory-webs` reopen condition arriving;
- someone actually asks a memory *query* ("which reference notes has no agent read in 90
  days?") that the Config pane cannot answer.

And the test that would prove **Phase A itself** was a mistake: six months after `memory:`
ships, fewer than 50 documents use it while raw `sase/memory/…` path strings keep growing.
That is the `#memory/` outcome repeating, and it would mean the demand measured in §1.2 was
for prose emphasis rather than typed identity. Re-measure with the appendix commands in
`memory_as_artifacts__b.md`.

---

## 6. Open questions for the project owner

1. **Scope in the ref.** §3.2 recommends scope-explicit persisted identity; the delimiter
   and project-key spelling should be settled once with the Rust grammar.
2. **Strand addressing.** `memory:glossary:stitch` (matching the selector, two colons in one
   ref) versus `memory:glossary/stitch` (cleaner, diverges from the spelling agents know).
   Both reports lean to matching the selector.
3. **The proposal subsystem.** Retire it, or wire it to artifact refs? 2,362 LOC with zero
   use across 31 projects.
4. **`#memory/` deprecation.** Docs-only, or an actual removal with a compat window?

---

## 7. Sources

Repository evidence is enumerated in the two drafts: report A's **Sources** section (memory
domain, ACE memory catalog and panes, artifact providers and link projection, plus audited
reads of `decisions:memory-webs` and `decisions:corpus-before-mechanism`) and report B's
**Appendix — how to re-measure** (the exact commands behind every number above).

External comparisons, from report A:

- [Backstage: The Life of an Entity](https://backstage.io/docs/features/software-catalog/life-of-an-entity/)
  and [Descriptor Format of Catalog Entities](https://backstage.io/docs/features/software-catalog/descriptor-format/)
  — a catalog that indexes authoritative version-controlled files without becoming their
  source of truth.
- [SLSA 1.2 Terminology](https://slsa.dev/spec/v1.2/terminology) — artifact as immutable
  blob, with reviewed source itself treated as an artifact.
- [GitHub Actions: Workflow artifacts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts)
  — the narrower output-and-retention meaning SASE should avoid imposing on live memory.

**Related artifacts.** `research:202608/glossary_to_memory_webs/glossary_to_memory_webs.md`
(the closest structural precedent — a corpus moved out of config into a first-class
substrate), `research:202608/artifact_link_graph`, `research:202608/agent_catalog_pane`,
`research:202608/artifacts_pane_contract`, `bead:sase-tj`, `bead:sase-tw`, and the
`corpus-before-mechanism` and `memory-webs` decision records.
