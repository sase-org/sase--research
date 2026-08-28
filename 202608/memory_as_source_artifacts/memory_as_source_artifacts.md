---
create_time: 2026-08-28
updated_time: 2026-08-28
status: research
tags: [memory, artifacts, artifact-refs, ace, architecture, sase-core]
---

# Should SASE Memory Migrate From Configuration Into Artifacts?

**Research question:** SASE memory notes are treated as configuration today — they live
under `sase/memory/`, they are browsed and edited from the **Memory** sub-tab of the
**Config** hub, and `sase memory init` compiles them into `AGENTS.md` plus four provider
instruction shims. Should memory instead become an artifact, with a canonical
`<kind>:<argument>` identity, typed links, artifact reads, and a **Memory** sub-tab under
**Artifacts**? If so, how much of it; if not, what is the right smaller change?

**Scope:** Three independent investigations against `sase` at `bcd6813d2`/`52327ed78`,
`sase-core`, and the `plans`, `research`, and `agents` sidecars, all read 2026-08-28.
Architecture research only; no behavior changed.

**Sources merged.** `memory_as_source_artifacts__a.md` (report A, `research.1c.cdx`) and
`memory_as_source_artifacts__b.md` (report B, `research.1c.cld`), both in this directory,
plus a third pass by the lead researcher. A supplies the external precedent and the design
invariants; B supplies the measurements; the lead pass targeted the one place the two
disagree and the claims neither verified. That third pass changed the analysis in four
places — §2.1 (why the corpus cites memory by path), §3.1 (the real blocker for a Memory
sub-tab), §3.2 (a load-bearing claim in report B that is false), and §2.3 (the rename base
rate) — so this is not a summary of the two drafts. Where a number is re-measured it is
marked; report B's originals are in its appendix.

---

## Bottom line

**Give memory an artifact *identity*. Do not move its bytes. Do not build a Memory
sub-tab under Artifacts. And fix the renderer first, because it is nearly free and it
determines whether any of the rest gets used.**

| # | Sub-proposal | Verdict | Basis |
| --- | --- | --- | --- |
| **P0** | **Render reference notes as `@memory:` refs in `AGENTS.md`** | **Do it first** | New (§2.1). One line. It is what actually drives adoption of P1. |
| P1 | A `memory:` artifact-reference kind — identity, typed links, rename-following, pointer expansion | **Do it** | Both reports; the `rust-core-required` path (§4) |
| P2 | Read-log consolidation — memory reads reach the artifact read channel | **Narrow version** | Both; B specifies it (§3.3) |
| P3 | A Memory sub-tab under Artifacts | **Not now** | Reports disagree; resolved in §3.1 on new evidence |
| P4 | Memory files into the artifact store, with `create`/`prune`/`reclaim`/`trash` | **Never** | Both, emphatically (§2.4) |

Both reports independently decomposed "migrate memory into artifacts" into separable
changes with opposite answers, and both landed on report A's principle: **promote, do not
relocate.** Artifact should be an identity, catalog, and relationship boundary for memory,
not a storage mandate. That framing survives all three passes intact and is the single
most useful thing in this report.

What the third pass adds is that the *ordering* is wrong in both drafts. The scarce
resource is not implementation effort, it is agent adoption — and adoption is controlled
by one line in a renderer, not by the ref kind.

---

## 1. What all three passes agree on

### 1.1 Memory is policy-bearing source, not inert configuration

Report A, analytically: core notes compile into `AGENTS.md` and the provider shims,
reference notes are addressed by audited `sase memory read`, every flat note is a
`#memory/<stem>` composition source, webs add strands with scope merging and validation,
and agent writes go through proposals and human review. "Configuration" undersells it;
memory is closer to reviewed, executable documentation.

Report B, from the other end (re-measured 2026-08-28): `memory_reads.jsonl` holds **8,788**
read events against **286** artifact reads — memory is the most-read context class in SASE
by ~31×. Filing the most-read context class under "Config" is defensible historically and
indefensible on first principles.

Both also agree on the counterweight, and it matters for P3: `sase memory list`'s
loaded / referenced-only / available / missing inventory, instruction roots, line counts,
and token approximations is a *compiler inventory* for generated agent instructions — a
build-and-render concern, closer to `sase config` than `sase artifact list`. Half of what
memory is really is configuration, and no artifact framing improves that half.

### 1.2 The corpus is small and dense

70 project memory files (17 flat notes — 6 core, 10 reference, plus `README.md` — and 53
strands across `decisions` 7, `glossary` 41, `task_types` 5), 3 Home notes, and a
**341-line / ~4,522-token** always-loaded budget across 10 instruction roots (re-measured;
report B recorded 382 / ~5,098 earlier the same day). Every core note is paid for on every
turn of every agent, which is why the memory subsystem's dominant design pressure is token
budget, not retrieval.

### 1.3 Managed link tables must never reach a memory note

The most important shared design constraint, found by both reports from different
directions. Artifact links render *into* the Markdown: a `Links` table near the top and a
bottom-anchored `Referenced By` block. Memory note bodies are inlined verbatim into
`AGENTS.md` and four provider shims. A naive registration writes link metadata into every
agent's always-loaded context against a ~4,522-token budget — and report A adds that it
would also make a graph update mutate a policy-bearing source file and mark the memory
scope unpublished.

The two remedies are compatible and both should be adopted: report B's **publication
suppressed from day one** (links render on the other endpoint, the treatment `stitch`
already gets, plus a `sase doctor` check that fails if a managed block appears under
`sase/memory/`), and report A's **deferral** of durable memory-side link storage until real
links justify generalizing the store for primary-repo and Home roots.

### 1.4 The base rate for building memory machinery here is poor

`sase memory write` proposals plus the `sase memory review` TUI are 2,362 LOC, and
`memory_proposals.jsonl` **exists in 0 of 32 registered projects** (re-measured) — zero
proposals ever written, with only a stale lock file in the flagship project. That is a
fourth unused retrieval mechanism after the three the `corpus-before-mechanism` record
documents, and it was built *after* that record was accepted. Any new memory machinery
must be sized to its evidence. This is the strongest argument in the whole file and it
applies to P1 as much as to P3 — which is why P0 exists.

---

## 2. What the third pass changes

### 2.1 The demand signal is largely manufactured by SASE's own renderer

Report B's headline evidence is that **625 documents cite memory notes as hand-typed
`sase/memory/<note>.md` strings** — 392 of 4,051 plans, 97 of 450 research reports, 136 of
4,853 archived prompts — with the plan rate accelerating 12% (July) → 31% (August). B read
this as measured demand for citation that clears the `corpus-before-mechanism` bar. Report
A reached the same gap analytically: memory has three address shapes and none is a
canonical link endpoint.

Neither asked **where the string comes from.** It comes from SASE.
`render_long_memory_sections` (`src/sase/memory/notes.py:534`) emits every Tier 2 note as:

```python
lines.append(f"### `{note.relative_path}`")
```

So `AGENTS.md` §2 — and therefore every provider shim, and therefore every agent's
always-loaded context on every turn — presents reference memory as a list of H3 headings
spelled `sase/memory/cli_rules.md`. Agents are not reaching for an identity SASE lacks.
They are echoing the only spelling SASE shows them.

The prediction this makes is testable and it holds. Core notes are inlined into `AGENTS.md`
*without* a visible path; reference notes are rendered *as* their path. If the citations
are echo, reference notes should be cited far more often. Measured across the plans sidecar
(exact `sase/memory/<name>`, `--include=*.md`):

| Tier | Notes | Plans citing | Mean per note |
| --- | --- | --- | --- |
| **reference** (path rendered as an H3 heading) | 10 | **303** | **30.3** |
| **core** (inlined, no path shown) | 6 | 66 | 11.0 |
| core, excluding `glossary.md` (a reference note until the 2026-08-18→25 web migration) | 5 | 38 | 7.6 |

`tui_perf.md` 79 · `symvision.md` 71 · `cli_rules.md` 43 · `generated_skills.md` 31 ·
`sase_beads.md` 26 · `sase_flags.md` 23 — the six most-cited notes in the corpus are all
Tier 2, all rendered as raw-path headings. A note is cited **~4× more** once its path is
printed into the instruction context. The 12%→31% jump is consistent with the August
memory-tier and web work reshaping that section, not with a spontaneous rise in felt need.

This cuts both ways, and both directions matter:

- **It weakens B's `corpus-before-mechanism` clearance.** The corpus is not demonstrating
  that plain audited reads are insufficient. It is demonstrating that agents copy what
  they are shown. As evidence of felt need for typed identity, 625 is inflated.
- **It makes P1's adoption problem tractable, which is the more valuable half.** Report B's
  own pre-committed falsification test is "six months after `memory:` ships, fewer than 50
  documents use it" — the `#memory/` outcome repeating (6 uses in 4,853 prompts). That risk
  is real *if* adoption depends on agents choosing the new spelling. It does not. Change
  one f-string to render `@memory:cli_rules.md`, and every agent's always-loaded context
  teaches the canonical form on every turn. The mechanism that produced 303 hand-rolled
  citations will produce typed ones just as reliably.

**Therefore P0 comes first, and it is the phase that carries P1's risk.** It is also
independently useful: even with no ref kind at all, rendering a stable, resolvable spelling
into `AGENTS.md` is strictly better than rendering a bare path.

### 2.2 The problem is real even though the demand is manufactured

Do not over-correct. Manufactured demand still produces genuine breakage, and there is a
live instance as of today.

`52327ed78` (2026-08-28, the current `HEAD`) renamed `sase/memory/build_and_run.md` →
`sase/memory/lint_and_test.md`. Right now:

- **17 plans** and **5 research reports** cite `sase/memory/build_and_run.md`;
- **1 plan** cites `sase/memory/lint_and_test.md`.

Twenty-two committed documents point at a file that no longer exists, hours after the
rename, and nothing in SASE notices. That is a far better piece of evidence for P1 than
the 625 count, because it is the actual failure mode rather than a proxy for it.

### 2.3 The rename base rate is one, not "routine"

Report B supports rename-following with: "notes *do* get renamed: beads `sase-te` and
`sase-tf` (both filed 2026-08-25) are open right now for residue from the `short`/`long` →
`core`/`reference` tier rename." Checked: **neither bead is about a memory note being
renamed.** `sase-te` is a stale PNG infographic label; `sase-tf` is 121 internal
identifiers still spelling the *tier vocabulary* `short`/`long`. Both concern a vocabulary
rename inside the codebase, not a note path, and neither involves a dangling citation.

The actual base rate, from `git log --diff-filter=R -- 'sase/memory/*.md'`, is **exactly one
memory-note rename in the corpus's entire history** — the one from §2.2, today.

This should be read as calibration, not refutation. One rename in the corpus's lifetime
producing 22 dangling documents in a single day is a poor ratio of events to damage, which
is a decent argument for cheap detection. It is a weak argument for a Rust wire change
justified primarily on rename-following. P1's case rests on identity, typed links, and the
`memory-webs` reopen clause — not on rename frequency.

There is a cheaper adjacent option worth pricing against P1, which neither report
considered. `sase memory list` **already** resolves raw `sase/memory/<x>.md` tokens and
reports a `missing` status — `inventory_reachability.py:81` builds exactly that token and
calls `resolve_reference`. It is scoped to instruction roots today. Pointed at the plans and
research corpora it would have caught all 22 dangling citations this morning, with no
`sase-core` change, no new kind, and no wire work. (It would need one fix first: the two
`missing` rows `sase memory list` reports today are false positives — `sase/memory/<web>.md`
is a *prose placeholder* in `AGENTS.md`, and the scanner cannot tell a placeholder from a
citation.) This does not replace P1, but it captures P1's most concrete near-term benefit
for a fraction of the cost, and it is the right thing to build if P1 slips.

### 2.4 P4 is a category error — and this is the one place `prune`/`reclaim` belongs

Report B's table is the clearest statement, and it is correct: the artifact store is
immutable snapshots with `prune`/`reclaim`/`trash` retention, recording *what happened*,
where staleness is harmless; a memory note is continuously edited, git-versioned alongside
the code it describes, stating *what is currently believed*, where staleness actively
misinforms every agent.

Verified: `sase artifact` exposes `create`, `prune`, `reclaim`, and `trash` as store
lifecycle commands. Applying that lifecycle to live memory is exactly the contradiction B
names. Report A reaches the same verdict and adds three consequences a storage move would
create — broken revision locality between memory and the `AGENTS.md` generated from it
(which sidecar revision belongs to which code commit? can publish commit two repositories
atomically? can an ephemeral workspace start if the sidecar is stale or offline?), Home
memory that no project sidecar can represent without duplicating notes or changing scope
precedence, and the accepted **Memory Webs** decision having already rejected "a generic
artifact database," so a storage move needs a new superseding record rather than a
re-reading of the old one.

Report B supplies the constructive half: `plan:` and `research:` are already artifacts that
are **not** store-backed — living Markdown in a git sidecar, resolved by path. That is the
shape memory should borrow. **Memory should be artifact-referenced, never
artifact-stored.**

---

## 3. The disagreement, resolved

### 3.1 The Artifacts Memory sub-tab: not now — but not for the reason report B gives

This is the substantive conflict. Report A's recommended destination is to **rehost the
existing specialized `MemoryPane` as a built-in Artifacts adapter** on the Patch precedent
("contract-in, specialized implementation out"), with a temporary Config forwarding route
removed after one release. Report B recommends the opposite: no sub-tab, the pane stays in
Config, and Artifacts *reaches* memory through relations rails plus one navigation route.

The two reports priced **different things**, which is why they disagree. B costed a full
generic Artifacts pane against `sase-tj`; A costed a thin wrapper around a widget that
already exists. Neither checked whether A's thin wrapper is actually permitted. It is not:

```python
# src/sase/ace/tui/_artifact_tab_contract.py, compile_builtin_contract()
query_profile = compiled_profile_for_builtin_pane(adapter.pane_id)
assert query_profile is not None, (
    f"no compiled profile for pane {adapter.pane_id!r}"
)
```

**A built-in Artifacts pane is required to have a compiled query schema**, registered in
`_BUILTIN_SCHEMA_BUILDERS` (`query_profile/pane_registry.py`). Existing schemas run 46–206
LOC (median ~95). It must also supply a full `_BuiltinAdapter` fact block — the five current
ones are 86–107 lines each — covering inventory, fields, identity, revisions, mutation,
scope, detail, relations, grouping, status counters, copy targets, keymap group, detail
fields, and empty state. And memory cannot take the cheap provider path at all: document
ref kinds are built from `merged_sidecar_entries_from_config` filtered through
`document_sidecar_roles`, so they are keyed strictly to **sidecar roles**. Memory lives in
the primary repo, and must, because notes are versioned alongside the code they describe.

So report A's "the pane is already a child widget behind a small host protocol, rehosting
is feasible" understates the work by the entire contract surface. **B's conclusion is
right; A's cost model is wrong.** Combined with B's precedent — `sase-tj` added *one* fixed
pane for `agent`, a class that already had a ref kind, a store, publication, and link-graph
presence, and still took 9 phases plus a follow-on child epic `sase-tj.10` — and with a
5,741-LOC existing Memory pane across 19 modules to reconcile, P3 is an epic, not an
adapter.

**But B's third ground is false and must be struck.** B argues (its §5): "An Artifacts
Memory pane inherits an action surface whose most characteristic verbs — prune, reclaim,
restore from trash — are meaningless or dangerous for memory, and would need suppressing
via `PaneDeclaredFacts.suppressions`. A pane defined mostly by what it turns off is a
signal that the abstraction does not fit."

The closed `PaneCapability` vocabulary is: `entry_navigation`, `entry_open`,
`filter_session`, `refresh`, `project_scope`, `stable_marks`, `detail_scroll`,
`stable_reference_copy`, `query_history`, `saved_queries`, `versions`, `mutation`,
`plan_approve`, `plan_reject`, `relations`, `grouping`, `status_counters`, `shell`.
There is **no `prune`, `reclaim`, or `trash`.** Those are `sase artifact` store commands;
panes never had them, and neither do Bead, Agent, Stitch, or Patch. Empirically, exactly
one adapter uses `suppressions` at all today — `agents`, for the single capability
`entry_open` (`sase-tj.10.2`). A Memory adapter would turn *on* most of the vocabulary and
turn off perhaps `versions` and the two `plan_*` verbs. It would look like a normal pane.

This matters beyond bookkeeping: B's §5 conflates *store lifecycle* with *pane capability*,
and that conflation is the same category error B correctly identifies in P4. The P4
argument is sound because it is about the store. The P3 version of it is not.

**Resolution: P3 is deferred on two grounds, not three** — measured cost (now better
grounded, via the query-profile and adapter-fact requirements), and the absence of any
demand signal pointing at browsing. Report A's own §8 sets the bar for doing this work at
all: users look for durable knowledge beside plans/research/beads and fail to find it, or
memory needs copyable references, unified provenance, or typed relationships. Three of
those four are satisfied by P0+P1 alone. The fourth is unevidenced.

Two of report A's contributions survive as binding constraints **if** P3 is revisited:

- **The information-architecture critique stands.** "Config" is an incomplete mental model
  for a corpus read 8,788 times as context. P0+P1 plus B's navigation seam addresses
  discovery without a second pane; if it does not, that is evidence for reopening, and §6
  names the threshold.
- **The startup constraint is real, but it is a one-line concern, not an architectural
  one.** `MemoryPane.on_mount` calls `_start_initial_load()` unconditionally, while
  Artifacts mounts every pane inside a `ContentSwitcher` and activates lazily — so dropping
  the pane in unchanged would scan scopes and memory files during startup while hidden,
  against the rule that first paint must not wait on data-scaled work. Report B missed this
  entirely and report A raised it as a design hazard; in fact the pane **already accepts
  `activate_on_mount`** (`memory_pane.py:142`) and the Config hub **already passes
  `activate_on_mount=hub._host_visible`** (`config_hub_catalog.py:98`). The deferral
  pattern exists and is in use; only the `_start_initial_load()` call is ungated. Record it
  as a checklist item, not a blocker.

Both reports agree on the one thing that must not happen either way: **do not run two
Memory surfaces.** Report A: move or rehost the pane, never clone it; a temporary
forwarding entry is fine, two permanent primary surfaces are not. Report B: keep the one
that exists. Under this recommendation the question does not arise.

### 3.2 Identity spelling: report A's invariants, report B's selector shape

Report B proposes `memory:<note>.md` and `memory:<web>:<strand>`, deliberately matching the
selector spelling agents already know, and files project/Home ambiguity as an open
question. Report A argues the persisted identity must be scope-explicit and path-based
rather than resolved by first-wins lookup, sketching
`memory:<scope>@<memory-relative-path>` (`memory:gh_sase-org__sase@glossary/stitch.md`,
`memory:home@obsidian.md`).

These reconcile, and A's invariants should govern — because B's own framing of the risk
argues for A's conclusion: *"a citation that silently means different files in different
projects is a worse failure than a read that does."*

- persisted references always carry an unambiguous scope, using a stable project key rather
  than a display label;
- a strand's canonical identity is its source path, so renaming a keyword alias does not
  silently change graph identity;
- `glossary:stitch` stays a friendly `sase memory read` selector, and interactive shorthand
  may resolve project-first, but both canonicalize before storage.

The delimiter is a vocabulary decision to settle once with the Rust grammar (§7). B's
two-colon concern is a spelling question inside those invariants, not a challenge to them.

One addition from §2.1: **whatever spelling is chosen, `render_long_memory_sections` must
emit it.** The canonical form and the form printed into `AGENTS.md` must be the same string,
or P0's adoption mechanism does not fire.

### 3.3 Read provenance: report B's narrow version, for report A's reason

Report A's constraint: the memory read ledger stays authoritative, and unified
agent-to-memory `read` edges must be *derived or transactionally projected* from successful
memory reads — never two independent audit events that can disagree. Report B supplies the
measurement that turns this into a hard limit: memory's 8,772 reads dedup to **7,137
distinct (agent, note) pairs**, a ~50% increase in total graph size and **56× the entire
existing `read` relation**, into a 6.0 MB `artifact-links.json` (re-measured: **14,221
rows**, `read` = 129) that already has an open bead (`sase-ua`) about the aggregate going
stale and dropping `read` rows.

Resolution: `sase memory read` keeps writing `memory_reads.jsonl` as the volume channel, and
emits a `read` link edge **only** when the read resolves through a `memory:` ref. Do not
backfill history. Separately, collapse the three near-clone ACE loaders — `memory_reads.py`
(279), `artifact_reads.py` (287), `glossary_reads.py` (279) — into one parameterized loader
(~845 → ~350 LOC), retiring the legacy `glossary` clone as a side effect. That refactor is
behavior-preserving, independently testable, and pays for itself regardless of P1.

---

## 4. Recommended solution

**Adopt a source-artifact model for memory: teach the instruction renderer the canonical
spelling, make `memory:` a real reference kind, and leave both the bytes and the browse
surface where they are.**

### Phase 0 — the renderer teaches the spelling (do this first; ~1 small phase)

Change `render_long_memory_sections` (`src/sase/memory/notes.py:534`) to render each Tier 2
note by its canonical reference rather than its raw relative path, and re-run
`sase memory init`. Do the same for any other generated surface that prints
`sase/memory/<x>.md` into agent-visible text.

Sequencing note: P0 depends on the spelling chosen in §3.2, so land the *grammar decision*
before P0 even though the *implementation* of P1 can follow. If P1 slips, ship P0 anyway
with the raw path plus a resolvable form — a stable spelling in the instruction context is
worth having on its own.

Why first: §2.1. This is the mechanism that produced 303 hand-rolled citations, and it is
the mechanism that will produce typed ones. Every later phase's adoption risk is
concentrated here, and it costs one f-string.

### Phase 1 — `memory:` becomes an artifact-reference kind (~4 medium phases)

The cheap path does not exist and should not be attempted (§3.1): document ref kinds are
keyed to `repos.sidecar` roles, and memory lives in the primary repo. This is the
`rust-core-required` path.

1. **`sase-core`:** add a `Memory` variant to `ArtifactRefKindWire` and a
   `KindRegistration` in `artifact_ref/kinds.rs`; extend the wire and the binding; add the
   kind to the closed set validated by `ArtifactRef.from_wire`
   (`src/sase/artifact_ref_models.py:162-176`).
2. **Python:** add a builtin entry resolver modeled on `builtin_entry_bead.py`, registered
   in `resolve_builtin_entry`. **Reuse `sase.memory.selector` and `memory_read_root`; do
   not write a second resolver.** Entry properties come from note frontmatter (`type`,
   `parent`, `priority`, `description`).
3. **Scope-explicit canonicalization** per §3.2: persisted refs always name a scope, strand
   identity is path-based, friendly selectors canonicalize before storage.
4. **Expansion is a pointer, not a body** — the plan provider's format ("the
   `sase/memory/tui_perf.md` reference memory note; read it with `sase memory read`"). This
   is where `#memory/` went wrong by inlining `note.body` (6 uses in 4,853 prompts), and it
   is what the corpus is already hand-rolling.
5. **Publication suppressed from day one** — no `Links` table or `Referenced By` block ever
   written under `sase/memory/`; links render on the other endpoint; a `sase doctor` check
   fails if a managed block appears. Defer durable memory-side link storage until real links
   justify generalizing the store for primary-repo and Home roots (§1.3).
6. **Decide `#memory/` explicitly** — recommended: keep it, deprecate it in docs, document
   `@memory:` as canonical. Two live, differently-behaved citation syntaxes without a stated
   canonical one is the "parallel link syntax" the `memory-webs` record warns against.
7. **`sase artifact create` never creates or promotes memory**, and memory is excluded from
   artifact-file inventory, prune, reclaim, and retention. Canonical writes remain
   `sase memory write` proposals or the human Memory pane.

Unlocked: `sase artifact link add bead:sase-x implements
memory:decisions:two-speed-verification`; rename-following via `sase-tw.4`'s repair pass;
`@memory:` completion; and the `memory-webs` reopen clause — which already names *artifact
relations* as the adopted supersession mechanism — becomes executable for the first time.

### Phase 1b — dangling-citation detection (~1 small phase; do it now if P1 slips)

Extend the existing memory reachability scan (`inventory_reachability.py`) beyond
instruction roots to the plans and research corpora, and report dangling
`sase/memory/*.md` citations from `sase doctor`. Fix the prose-placeholder false positive
first (§2.3). This would have caught all 22 documents broken by today's rename (§2.2), and
it does not depend on P1 landing.

### Phase 2 — one read channel, two logs (~2 medium phases)

Collapse the three ACE loaders; emit a `read` edge only for citational, ref-resolved reads;
do not backfill (§3.3). Let `sase memory write --evidence` accept canonical artifact refs
with `path`/`chat:`/`url:`/`note:` kept as legacy spellings — noting that `chat:` is already
a real ref kind that memory reimplemented privately. Given zero proposals across 32
projects, whether the 2,362-LOC proposal subsystem should be **retired** rather than
improved deserves its own decision, and is a cheaper win than anything in P3.

### Phase 3 — Artifacts reaches memory; memory keeps its home

No new sub-tab. Once `memory:` refs exist, memory rows appear in the relations rail of the
Bead, Plan, and Agent panes for free — that is where "which memory does this bead
implement?" gets answered, and it is the actual browsing need. Add one navigation seam:
selecting a `memory:` row in any relations rail routes to the Config hub's Memory pane at
that note, which `ConfigHubEntry.note` already supports. A route, not a pane.

### Phase 4 — record the boundary

Add a decision stating that memory notes are git-backed **source artifacts**, and that
artifact identity does not imply artifact-file storage or lifecycle. This complements the
accepted `memory-webs` record rather than superseding it; a storage move would need its own
superseding record and new evidence.

Deliberately last, not first. Both drafts put this first; on the evidence in §1.4 this
project's failure mode is writing the abstraction before the mechanism has earned it. Write
the record once P0+P1 have shipped and the boundary has been tested by real use.

### Never

Memory files do not enter the artifact store, and memory notes never acquire `prune`,
`reclaim`, or `trash` (§2.4).

### Acceptance criteria

- `sase memory read/show`, `#memory`, proposal, review, and `init` behavior is semantically
  unchanged;
- the canonical ref spelling and the spelling `AGENTS.md` renders are the same string;
- project and Home notes with the same relative path canonicalize to different identities,
  and a renamed keyword alias does not change a strand's canonical identity;
- core notes gain no ad hoc second read path, and generated notes stay read-only;
- `sase artifact list/prune/reclaim` never treats live memory as a retained snapshot;
- no managed link block is ever written under `sase/memory/`, enforced by `sase doctor`;
- the link graph gains no bulk memory `read` rows;
- the always-loaded core budget does not grow (re-run `sase memory list`; baseline 341
  lines / ~4,522 tokens).

---

## 5. What this costs, and when to stop

| Phase | Size | Stop condition |
| --- | --- | --- |
| P0 renderer | ~1 small | None — do it regardless |
| P1 `memory:` kind | ~4 medium | Stop if the grammar decision (§3.2) cannot be settled; P0 + P1b still deliver |
| P1b dangling detection | ~1 small | None — cheapest item here |
| P2 read channel | ~2 medium | The loader collapse is worth doing alone; the edge work is not, without P1 |
| P3 Artifacts pane | epic (≥ `sase-tj`: 9 phases + child epic) | Do not start; see §6 |
| P4 storage move | — | Never |

---

## 6. What would reopen P3

Report B's thresholds, adopted because they are falsifiable. Revisit the Artifacts Memory
sub-tab when **any** becomes true:

- manual memory link rows (excluding `read` edges) exceed ~50;
- a second project's memory corpus exceeds ~40 notes (today: 70 in `sase`, 3 at Home);
- memory supersession becomes routine — say the `decisions` web reaching ~25 records with
  active supersession chains, which is the `memory-webs` reopen condition arriving. Note
  that `decisions` is the one part of memory that is genuinely artifact-shaped: a record is
  immutable once accepted and a course change is a *new* record superseding the old, which
  is `supersedes`/`superseded-by` verbatim. Seven records today;
- someone actually asks a memory *query* ("which reference notes has no agent read in 90
  days?") that the Config pane cannot answer.

**And the test that would prove P0+P1 were a mistake**, restated to account for §2.1: six
months after the renderer emits `@memory:` and the kind ships, **raw `sase/memory/…` path
strings in new plans have not fallen below ~20% of memory citations.** Report B's original
test — "fewer than 50 documents use `memory:`" — no longer measures the right thing once
P0 lands, because P0 makes usage near-automatic; the honest question is whether agents
*keep* hand-rolling paths anyway. Re-measure with report B's appendix commands plus the
per-tier split in §2.1.

---

## 7. Open questions for the project owner

1. **Scope in the ref.** §3.2 recommends scope-explicit persisted identity; the delimiter
   and project-key spelling should be settled once with the Rust grammar. **This blocks P0**,
   so it is the first decision to make.
2. **Strand addressing.** `memory:glossary:stitch` (matches the selector agents know, two
   colons in one ref) versus `memory:glossary/stitch` (cleaner, diverges). Both reports lean
   to matching the selector.
3. **The proposal subsystem.** Retire it, or wire it to artifact refs? 2,362 LOC with zero
   use across 32 projects.
4. **`#memory/` deprecation.** Docs-only, or removal with a compat window?
5. **New:** should P1b (dangling-citation detection) ship *before* P1, given it is ~1 small
   phase, has no `sase-core` dependency, and addresses the only failure that has actually
   occurred?

---

## 8. Sources

Repository evidence is enumerated in the two drafts: report A's **Sources** section (memory
domain, ACE memory catalog and panes, artifact providers and link projection, plus audited
reads of `decisions:memory-webs` and `decisions:corpus-before-mechanism`) and report B's
**Appendix — how to re-measure**.

Additional evidence read for this consolidation, all at `52327ed78`:
`src/sase/memory/notes.py:524-539` (`render_long_memory_sections`);
`src/sase/memory/inventory_reachability.py:60-95`; `src/sase/memory/cli_list.py:150-185`;
`src/sase/ace/tui/_artifact_tab_contract.py` (`compile_builtin_contract`);
`src/sase/ace/tui/_artifact_tab_contract_adapters.py` (`_BuiltinAdapter`, `BUILTIN_ADAPTERS`);
`src/sase/ace/tui/_artifact_tab_model.py` (`PaneCapability`, `FIXED_ARTIFACTS_PANE_IDS`);
`src/sase/ace/query_profile/pane_registry.py`; `src/sase/ace/query_profile/profiles/`;
`src/sase/ace/tui/modals/memory_pane.py:142-230`;
`src/sase/ace/tui/modals/config_hub_catalog.py:84-98`; `src/sase/sdd/_store_types.py:32-48`;
`src/sase/sidecar_ref_config.py`; `git log --diff-filter=R -- 'sase/memory/*.md'`;
`sase memory list`; `sase artifact --help`; `sase bead show sase-te sase-tf`; and citation
counts measured across the `plans` and `research` sidecars.

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
