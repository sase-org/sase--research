---
create_time: 2026-08-28
updated_time: 2026-08-28
status: research
---

# Should SASE Memory Migrate From Configuration Into Artifacts?

**Research question.** SASE memory notes are currently treated as configuration: they
live under `sase/memory/`, they are browsed and edited from a **Memory** sub-tab of the
**Config** hub, and they are compiled into `AGENTS.md` plus four provider instruction
shims by `sase memory init`. Should they instead become SASE artifacts — with a
canonical `<kind>:<argument>` identity, typed links, artifact reads, and a new **Memory**
sub-tab under the **Artifacts** tab? If so, how; if not, what is the right smaller
change?

**Scope.** `sase` at `bcd6813d2` (master, clean), `sase-core` at its opened checkout,
plus the `plans`, `research`, and `agents` sidecars, all read 2026-08-28. Architecture
research only; no behavior changed. Every number below was measured on this machine at
that time, not recalled.

**Provenance.** Single researcher, direct measurement. Where a claim rests on reading
code rather than running it, the file and symbol are named so it can be re-checked.

---

## Bottom line

**Do not migrate memory into artifacts. Do give memory an artifact *identity*, and do
not build a Memory sub-tab under Artifacts.**

The proposal bundles four separable changes that have wildly different value-to-cost
ratios. Unbundling them is the whole finding:

| # | Sub-proposal | Verdict | Why |
|---|---|---|---|
| P1 | A `memory:` **artifact-reference kind** (identity, typed links, rename-following, pointer expansion) | **Do it** | 625 documents already cite memory notes by raw path because there is no ref. Highest value in the bundle, lowest cost. |
| P2 | **Read-log consolidation** — memory reads join the artifact read channel | **Do a narrow version** | Three near-clone 280-line loaders and three JSONL logs exist today. Consolidate the *loaders*; do **not** push 8,772 memory reads into the link graph. |
| P3 | A **Memory sub-tab under Artifacts** | **Do not do it** | It duplicates a 5,741-LOC pane that already exists and works, costs an epic on the order of `sase-tj` (9 phases + a follow-on child epic), and answers a browsing need nobody has reported. |
| P4 | Moving memory **files into the artifact store** | **Never** | Store semantics are immutable-snapshot-plus-retention. Memory notes are mutable, git-versioned, and inlined into agent instructions. Direct semantic contradiction (§5). |

The single most important measured fact in this report: **392 of 4,051 plans (9.7%) and
97 of 450 research reports (21.6%) mention `sase/memory/<note>.md` as a hand-typed path
string** — 210 of the 679 plans written this month alone, a rate that has gone 12% →
31% in two months (§1.4). Those are untyped, unresolvable, non-rename-following, and
invisible to a link graph that currently holds 14,209 rows and exactly zero memory rows.
That is the demand signal, and it is a demand for *citation*, not for a browsing pane.

**The honest failure mode of my own recommendation:** P1 ships, the `memory:` kind gets
used as little as `#memory/` is used today (6 of 4,853 archived prompts, §1.5), and SASE
carries one more builtin ref kind for nothing. §8 gives the pre-committed test that would
prove that outcome, and the mitigation is in the P1 design: expand as a *pointer*, which
is what the 625 prose citations are actually hand-rolling, rather than as body text,
which is what `#memory/` does and what nobody wants.

---

## 1. Verified state

### 1.1 The corpus

| Measure | Value |
| --- | --- |
| Flat notes, `sase/memory/*.md` | **17** (7 `type: core`, 9 `type: reference`, plus `README.md`) |
| Web strands (`decisions`, `glossary`, `task_types`) | **53** (7 + 41 + 5) |
| Total project memory files | **70** |
| Home memory notes (`~/sase/memory/`) | **3** |
| Always-loaded core budget | 382 lines / ~5,098 approx tokens across 10 instruction roots (`sase memory list`) |
| Context files tracked by `sase memory list` | 22 (10 loaded, 9 referenced-only, 1 available, 2 missing) |

This is a small corpus. It is also a *dense* one: every core note is paid for on every
turn of every agent, which is why the memory subsystem's dominant design pressure is
token budget, not retrieval.

### 1.2 Usage — memory is the most-read context class in SASE, by 31×

Measured from `~/.sase/projects/gh_sase-org__sase/`:

| Channel | Events | Detail |
| --- | --- | --- |
| `memory_reads.jsonl` | **8,772** | 8,694 note · 74 strand · 4 web; **3,848 distinct agents**; 2,401 in July, 6,371 in August |
| `artifact_reads.jsonl` | **284** | plan 202 · research 55 · file 19 · bead 5 · agent 3; 245 recorded a `read` link edge |
| `glossary_reads.jsonl` (legacy) | 357 | superseded by the glossary→web migration |
| `skill_uses.jsonl`, `sase_memory_read` | 342 | vs `sase_artifact_file` 208 |

Most-read notes: `sase_beads.md` 2,476 · `tui_perf.md` 1,539 · `symvision.md` 1,336 ·
`sase_sizes.md` 1,193 · `xprompts.md` 637.

The asymmetry matters in both directions. It is the best argument *for* taking memory
seriously as a first-class artifact class — and, in §4.3, the reason its reads must not
be poured into the link graph.

### 1.3 The link graph memory is absent from

`artifact-links.json` is 6.0 MB / **14,209 rows**:

| Relation | Rows |
| --- | --- |
| `implements` | 7,283 |
| `produced-by` | 6,014 |
| `related` | 376 |
| `derives-from` | 151 |
| `cites` | 142 |
| `read` | 127 |
| `launched` | 116 |

Memory contributes **0**, because the artifact-reference kind catalog compiled into
`sase-core` (`crates/sase_core/src/artifact_ref/kinds.rs`) has no `memory` entry, and
`ArtifactRef.from_wire` (`src/sase/artifact_ref_models.py:162-176`) validates against a
closed set of nine kind types: `commit`, `chat`, `bug`, `file`, `bead`, `agent`,
`stitch`, `patch`, `document`.

### 1.4 The demand signal — 625 documents citing memory by raw path

| Corpus | Documents mentioning `sase/memory/*.md` | Total | Rate |
| --- | --- | --- | --- |
| Plans sidecar | **392** | 4,051 | 9.7% |
| Research sidecar | **97** | 450 | 21.6% |
| Archived agent prompts | **136** | 4,853 | 2.8% |

Plans, by month: 202604 26/671 · 202605 25/823 · 202606 10/566 · **202607 121/1,003
(12%)** · **202608 210/679 (31%)**.

Most-cited in plans: `tui_perf.md` 105 · `symvision.md` 80 · `glossary.md` 77 ·
`sase_beads.md` 65 · `cli_rules.md` 54 · `generated_skills.md` 39.

The citations are overwhelmingly *pointers*, not quotes. Representative samples:

> ``Read `sase/memory/tui_perf.md` before starting.``
> ``Do **not** touch `sase/memory/*.md`, `AGENTS.md`, or the generated provider instruction shims.``
> ``…symvision findings for the new public symbols — read `sase/memory/symvision.md` with…``

This is a hand-rolled `@memory:` ref. Every one of these strings dangles silently when a
note is renamed — and notes *do* get renamed: beads `sase-te` and `sase-tf` (both filed
2026-08-25) are open right now for residue from the `short`/`long` → `core`/`reference`
tier rename.

### 1.5 The identity memory already has, and nobody uses

Memory notes are already prompt-expandable. `sase/memory/foo.md` is loaded as an xprompt
named `memory/foo` (`src/sase/xprompt/loader_memory.py:118`, using
`memory_reference_name` from `sase-core`'s `content_layout.rs:251`), and the `memory/`
namespace is reserved against collision (`is_reserved_memory_reference`,
`reserved_memory_namespace_issue`).

Adoption: **6 of 4,853 archived prompts** contain `#memory/`. Against 136 prompts that
name a memory path in prose.

The reason is visible in `_memory_note_to_xprompt`: `content=note.body`. `#memory/foo`
inlines the *entire note body* into the prompt. Nobody wants that; they want to tell the
agent where to look. Meanwhile the builtin plan provider's expansion format
(`src/sase/artifact_providers/_builtin.py:26-28`) is
`"the {repo_relative_path} file in the {sidecar_role} sidecar repo"` — a pointer. The
mechanism the corpus is asking for already exists on the artifact side and is missing on
the memory side.

Unlike artifact refs, xprompt expansions are not recorded anywhere: `sase-core` keeps
per-occurrence `ArtifactRefUseRecordWire` rows (`artifact_ref/uses.rs`) with agent name,
canonical ref, and prompt text, and there is no xprompt equivalent. SASE can tell you
every plan an agent cited but not that an agent was handed all 91 lines of `tui_perf.md`
in its prompt.

### 1.6 Code mass on both sides

| Surface | Measure |
| --- | --- |
| Memory-related Python (`src/sase/memory`, ACE memory panes, `init_memory`) | **21,047 LOC** |
| — of which the ACE Memory pane and its mixins | **5,741 LOC** across 19 modules |
| — of which proposals + review TUI | **2,362 LOC** (1,476 + 886) |
| Memory tests | 87 files / 21,535 LOC |
| Artifact tests | 289 files / 61,512 LOC |
| `sase-core` `artifact_ref/` | 5,817 LOC across 12 modules |

### 1.7 One memory mechanism has already been built and never used

`sase memory write` creates an attributable, evidence-backed proposal; `sase memory
review` is a Textual review TUI; there is a ledger, an identity module, a validator, and
a `--notify` path. Combined: 2,362 LOC.

`memory_proposals.jsonl` **does not exist in any of the 31 registered projects** — only a
stale `memory_proposals.lock` in the flagship project. Zero proposals have ever been
written. (A bead, `sase-uu`, was filed 2026-08-27 for a crash in the review notification
path, so the surface is reachable; it is just unused.)

This is the same failure mode the `corpus-before-mechanism` decision record was written
about, and it happened *after* that record. It should weigh directly on any proposal to
build more memory machinery.

---

## 2. What "migrate memory into artifacts" actually means

The phrase covers four independent changes. Conflating them is why the idea feels both
obviously right and vaguely alarming.

1. **Identity (P1).** Memory notes get a canonical `memory:<note>` / `memory:<web>:<strand>`
   reference: resolvable, expandable in prompts, citable from plans and beads,
   rename-following, and eligible for typed links.
2. **Audit consolidation (P2).** `sase memory read` events stop being a private JSONL
   channel with a private ACE loader and join the artifact read channel.
3. **Surface (P3).** The Memory pane moves (or is duplicated) from the Config hub to a
   new Artifacts sub-tab with the shared query dialect, saved queries, relations rail,
   grouping, and status counters.
4. **Storage (P4).** Memory content moves into the artifact store, acquiring `create`,
   `prune`, `reclaim`, and `trash` lifecycle.

P1 is a `sase-core` change plus a Python resolver. P2 is a refactor. P3 is an epic. P4 is
a category error (§5). They can be shipped independently and in that order, and the value
is very front-loaded.

---

## 3. The case for

Stated as strongly as the evidence allows.

**3.1 The demand is measured, not hypothetical.** §1.4: 625 documents, an accelerating
9.7%→31% monthly rate in plans, all hand-rolling a citation SASE cannot type-check. The
`corpus-before-mechanism` record's own reopen condition is *"a specific, already-existing
corpus demonstrably needs a mechanism that plain audited reads cannot serve."* "Which
plans depend on `tui_perf.md`?" and "this note supersedes that one" are not answerable by
audited reads. This clears the bar the project set for itself.

**3.2 The `memory-webs` decision already names the mechanism.** Its reopen clause: *"A
web's strand count or supersession rate outgrows prose cross-references, at which point
the existing `supersedes` / `superseded-by` **artifact relations** are the adopted
mechanism — not a new, parallel link syntax."* The accepted direction of travel for
memory linking is *artifact relations*. P1 is the prerequisite for that clause ever being
executable; today it names a mechanism memory cannot reach.

**3.3 There is real, quantified duplication.** Three ACE loaders —
`memory_reads.py` (279), `artifact_reads.py` (287), `glossary_reads.py` (279) — are
near-identical clones, 845 LOC, differing chiefly in which JSONL they open and which
dataclass they emit. Three JSONL channels, three locks, three summarizers, three agent-detail
sections (`MEMORY`, `GLOSSARY`, artifact reads) in `_agent_context.py`. One of the three
(`glossary`) is already legacy.

**3.4 Memory's evidence vocabulary is a private reimplementation of artifact refs.**
`sase memory write --evidence` accepts `path`, `chat:<id>`, `url:<url>`, and `note:<text>`
(`EvidenceKind` in `src/sase/memory/proposals/models.py:13`). `chat:` **is** an artifact
ref kind. Memory reinvented a citation vocabulary because it could not use the real one.

**3.5 Discovery is genuinely mismatched.** Config is where you change settings. Memory is
read 8,772 times as *context*. Filing the most-read context class in SASE under "Config"
is defensible historically and indefensible on first principles.

**3.6 The Artifacts pane framework is more capable than the Config pane.** Artifacts
panes get the shared boolean query dialect, saved queries, query history, a relations
rail, grouping, status counters, stable-reference copy, and versions — a closed
capability vocabulary (`PaneCapability`) derived by named rules. The Memory pane has
filter, scope, parent/child travel, and publish.

---

## 4. The case against — six concrete hazards

**4.1 The cheap path does not exist.** The obvious implementation — declare memory as a
document ref provider, the way `@plan` and `@research` work, and get a `ref:memory`
Artifacts pane for free from `provider_descriptors()` — **cannot work**. Document ref
kinds are keyed strictly to `repos.sidecar` roles: `sidecar_ref_policy_report` builds
policies from `merged_sidecar_entries_from_config` and filters through
`document_sidecar_roles`. Memory lives in the *primary* repo, and must, because notes are
versioned alongside the code they describe. So P1 requires a new kind-type variant in
`sase-core`'s closed `ArtifactRefKindWire` enum, a `KindRegistration` in `kinds.rs`, wire
and binding changes, and a Python builtin entry resolver modeled on
`builtin_entry_bead.py` — the `rust-core-required` path, not a config edit.

**4.2 Managed link tables would land in every agent's always-loaded context.** An
artifact's typed links are rendered *into* the Markdown file: a `Links` table near the
top and a bottom-anchored `Referenced By` block (`sase-core`
`crates/sase_core/src/referenced_by.rs`, `artifact_link/managed_table.rs`). Memory note
bodies are inlined verbatim into `AGENTS.md` and four provider instruction shims
(`CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `OPENCODE.md`) by `sase memory init`. A naive
migration writes a link table into `sase/memory/sase.md` and
ships it to every agent on every turn, against a measured ~5,098-token core budget. Any
`memory:` kind must ship with publication suppressed from day one. This is a
five-line design constraint that is catastrophic if discovered late.

**4.3 Memory read edges would swamp the link graph with near-zero signal.** The graph has
127 `read` rows. Memory's 8,772 reads dedup to **7,137 distinct (agent, note) pairs** —
measured, not estimated — accruing 1,969 new pairs in July and **5,171 in August**. That is
a 50% increase in total graph size and **56× the entire existing `read` relation**, for rows
that say "some agent read `sase_beads.md`", a fact already answered by
`memory_reads.jsonl` and already rendered by the Memory pane's
`summarize_memory_reads_by_path`. `artifact-links.json` is already 6.0 MB and already has
an open bead (`sase-ua`) about the aggregate being stale and dropping `read` rows. The
valuable memory edges are the rare manual ones — `bead:sase-x implements
decisions:two-speed-verification`, `plan:… derives-from memory:tui_perf.md` — perhaps
dozens per year, not thousands per month.

**4.4 The Memory pane already exists, and it is not small.** 5,741 LOC across 19 modules
with scope picking, worker-backed loads, debouncing, parent/child chip travel,
add/edit/delete, publish, source/copy/help actions, and its own keymap registry. Its own
module docstring anticipated the Config hub mount. A second pane under Artifacts means
either a fork (two panes drifting) or a second migration of a widget that was migrated
into its current home eight days ago (`4daa8b019`, `1382a43d8`, 2026-08-20).

**4.5 `sase memory list` is a config surface, and correctly so.** Its output is *loaded /
referenced-only / available / missing*, instruction roots, lines, and approximate tokens.
That is a compiler inventory for generated agent instructions — a build-and-render
concern, closer to `sase config` than to `sase artifact list`. Half of what memory *is*
is genuinely configuration, and no artifact framing improves it.

**4.6 One speculative memory mechanism is already sitting unused.** §1.7: 2,362 LOC of
proposals and review TUI, zero proposals in 31 projects. The base rate for "build memory
machinery, agents will use it" in this repo is poor: the `corpus-before-mechanism` record
documents three prior retrieval mechanisms built and deleted (2026-04-12→2026-05-31,
2026-05-23→2026-06-15, keywords removed 2026-07-13). A fourth should be sized to its
evidence, and the evidence supports citation, not browsing.

---

## 5. Where the two models genuinely disagree

This is the part that a UI framing hides, and it is why P4 must never happen.

| | Artifact store | Memory note |
| --- | --- | --- |
| Mutability | Explicit snapshots are **immutable and permanent** | Edited continuously; the point is that it is current |
| Lifecycle | `prune`, `reclaim`, `trash`, retention policy | Lives as long as the claim is true |
| Truth model | A record of **what happened** | A statement of **what is currently believed** |
| Versioning | Object store + VCS-backed locators | Plain git, alongside the code it describes |
| Failure of staleness | Harmless — a snapshot is *supposed* to be old | Actively harmful — a stale note misinforms every agent |

An Artifacts Memory pane inherits an action surface whose most characteristic verbs —
prune, reclaim, restore from trash — are meaningless or dangerous for memory, and would
need suppressing via `PaneDeclaredFacts.suppressions`. A pane defined mostly by what it
turns off is a signal that the abstraction does not fit.

The exception, and it is instructive: **`plan:` and `research:` are artifacts that are
*not* store-backed** — they are living Markdown in a git sidecar, resolved by path. That
is the shape memory should borrow. Memory should be artifact-*referenced*, never
artifact-*stored*.

There is a real seam here worth naming. The `decisions` web is the one part of memory
that is genuinely artifact-shaped: a decision record is immutable once accepted, and a
course change is a *new* record that supersedes the old one in prose. That is
`supersedes` / `superseded-by` verbatim. Seven records today — small, but it is the
corpus §3.2's reopen clause was written for.

---

## 6. Cost, calibrated against three precedents

Not estimated — measured from work this repo actually did.

**`sase-tj`, "Artifacts Agent pane"** (2026-08-25 → 2026-08-28). Adding **one** fixed
Artifacts pane for `agent`, an artifact class that *already had* a ref kind, a store,
publication, and link-graph presence: **9 phases** (query dialect widening, row model,
query profile, flag + pane contract + mounted list, filter bar + Rust evaluation + saved
queries + history, detail panel + grouping + relations + copy, mutation, `sase agent
search`, flag removal) **plus a follow-on child epic `sase-tj.10`** for landing gaps
(reachable navigation, a working CLI, real visual coverage). It also broke an unrelated
ACE test because `FIXED_ARTIFACTS_PANE_IDS` is not flag-gated (bead `sase-tj` note #1).

A Memory pane starts *behind* where the Agent pane started: no ref kind, no store rows,
no query profile, and an existing 5,741-LOC pane to reconcile. **P3 is ≥ `sase-tj`, so
9–12 medium phases.**

**`sase-tw`, "Artifact links that survive, derive themselves, and pay for the turn"**
(closed 2026-08-26): **14 phases** to make the link graph load-bearing — durable reads,
rename-following, relation semantics, derivation, the citation channel, and the ACE
relation type. This is the machinery P1 would plug memory into; it is new and its
integration seams are still settling (`sase-ua`, `sase-u3`, `sase-u9` are open against it).

**The glossary → memory-web migration** (2026-08-18 → 2026-08-25) is the closest
structural analogue: moving a corpus *out of* config into a first-class substrate.
Consolidated research report of 2,061 lines across three files, then ~16 commits — a
migration command, a compat shim, fail-closed dual truth, a panel migration, symbol
retirement, doc retirement — and it *still* leaves two open beads (`sase-te`, `sase-tf`)
for rename residue. That report's own lead finding is worth quoting, because it applies
here almost unchanged: the migration was defensible *"not as a speculative generalization
[but as] the extraction of a pattern SASE has already implemented three separate times by
hand."*

By that test, P1 passes — 625 hand-rolled citations are the same "implemented by hand"
evidence — and P3 fails, because nothing about the current Memory pane has been
hand-rolled three times.

Rough sizing for the recommendation in §7: **P1 ≈ 4 medium phases** (core kind + wire +
bindings; Python resolver + CLI resolution; pointer expansion + publication suppression;
docs, memory notes, and skill updates). **P2 ≈ 2 medium phases.** P3, if it is ever
justified, is a separate epic to be scoped on its own evidence.

---

## 7. Recommended solution

### Phase A — `memory:` becomes an artifact-reference kind (do this)

1. **`sase-core`:** add a `Memory` variant to `ArtifactRefKindWire` and a
   `KindRegistration` in `artifact_ref/kinds.rs` — `kind: "memory"`, `display_name:
   "Memory"`, `status: Live`, `reserved: true`, `argument_summary: "memory:<note>.md or
   memory:<web>:<strand>"`, `offered_in_completion: true`. Extend the wire and the
   binding; add the kind to the closed set in `src/sase/artifact_ref_models.py:162-176`.
2. **Python:** add `src/sase/artifact_providers/builtin_entry_memory.py` modeled on
   `builtin_entry_bead.py`, registered in `resolve_builtin_entry`. Resolve against the
   existing selector — `sase.memory.selector` already resolves note / `web` /
   `web:keyword` selectors across project-then-home roots, and `memory_read_root`
   already handles the canonical/legacy layout. **Reuse it; do not write a second
   resolver.** Entry properties come from note frontmatter: `type` (core/reference),
   `parent`, `priority`, `description`.
3. **Expansion is a pointer, not a body.** Follow the plan provider's format — *"the
   `sase/memory/tui_perf.md` reference memory note; read it with `sase memory read`"*.
   This is the single most important design choice in the phase: it is what the 625 prose
   citations are hand-rolling, and it is precisely where `#memory/` (body expansion, 6
   uses in 4,853 prompts) went wrong.
4. **Publication suppressed.** No `Links` table, no `Referenced By` block written into
   any file under `sase/memory/`. Links for a memory ref render on the *other* endpoint —
   the same treatment `stitch` already gets ("A commit has none — links to a stitch render
   on the other artifact"). Add a `sase doctor` check that fails if a managed block ever
   appears in a memory note.
5. **Decide `#memory/` explicitly.** Recommended: keep it, deprecate it in docs, and let
   `@memory:` be the documented form. It has six uses; a hard retirement is not worth a
   compat shim, but shipping two live, differently-behaved citation syntaxes without
   saying which is canonical is exactly the "parallel link syntax" the `memory-webs`
   record warns against.

Immediately unlocked: `sase artifact link add bead:sase-x implements
memory:decisions:two-speed-verification "…"`; rename-following for the 625 citations via
`sase-tw.4`'s repair pass; `@memory:` completion in the editor and ACE from
`completion_artifact_ref_kinds()`; and the `memory-webs` reopen clause becomes executable.

### Phase B — one read channel, two logs (do a narrow version)

6. **Collapse the loaders, not the logs.** Generalize `memory_reads.py`,
   `artifact_reads.py`, and `glossary_reads.py` into one parameterized loader over
   `(log path, event schema, display shape)`. ~845 LOC → ~350. Behavior-preserving,
   independently testable, and it retires the legacy `glossary` clone as a side effect.
7. **Record memory reads in the artifact channel *only* when the read is citational.** A
   `sase memory read` keeps writing `memory_reads.jsonl` (the volume channel; it is
   working, and the ACE loader and `memory log` depend on its shape). It additionally
   emits a `read` **link edge** only when it resolves through a `memory:` ref. Do not
   backfill the 8,772 historical reads (§4.3).
8. **Replace the private evidence vocabulary.** `sase memory write --evidence` should
   accept canonical artifact refs, with `path`/`chat:`/`url:`/`note:` kept as accepted
   legacy spellings. Given zero proposals in 31 projects, consider instead whether the
   2,362-LOC proposal subsystem should be retired rather than improved — that question
   deserves its own decision, and it is a cheaper win than anything in P3.

### Phase C — Artifacts *reaches* memory; memory keeps its home (do this instead of P3)

9. **No new sub-tab.** The Memory pane stays in the Config hub, where authoring, tiering,
   priority, `parent`, publish, and `sase memory init` legitimately live (§4.5).
10. **Make memory a link *target* everywhere.** Once `memory:` refs exist, memory rows
    appear in the relations rail of the Bead, Plan, and Agent panes for free — that is
    where "which memory does this bead implement?" gets answered, and it is the actual
    browsing need.
11. **One navigation seam.** Selecting a `memory:` row in any relations rail routes to
    the Config hub's Memory pane at that note. The Config hub already accepts a target
    note (`ConfigHubEntry.note`, `_entry_note`), so this is a route, not a pane.

### Never

12. Do not put memory files in the artifact store, and do not give memory notes
    `prune` / `reclaim` / `trash` (§5).

---

## 8. What would change my mind

Pre-committed, so this is falsifiable rather than rhetorical. Revisit the full P3 sub-tab
when **any** of these becomes true:

- **Manual memory link rows exceed ~50** (excluding `read` edges). At that density the
  relations rail stops being enough and a queryable catalog earns itself.
- **A second project's memory corpus exceeds ~40 notes.** Today: 70 files in `sase`, 3 at
  home. The Config pane's flat list is adequate at that size and will not be at 200.
- **Memory supersession becomes routine** — the `decisions` web reaching, say, 25 records
  with active supersession chains. That is the `memory-webs` reopen condition arriving.
- **Someone actually asks for a memory query.** "Which reference notes has no agent read
  in 90 days?" is a real question the Config pane cannot answer and the query dialect can.
  Nobody has asked it yet.

And the test that would prove **Phase A itself** was a mistake: **six months after
`memory:` ships, fewer than 50 documents use it** while raw `sase/memory/…` path strings
keep growing. That is the `#memory/` outcome repeating, and it would mean the demand in
§1.4 was for prose emphasis, not for typed identity. Re-measure with the same commands
used for §1.4 and §1.5.

---

## 9. Open questions for the project owner

1. **Scope in the ref.** Should `memory:tui_perf.md` mean "project memory, falling back
   to home" (matching `sase memory read`), or should home memory need an explicit
   spelling? The read path merges silently today; a *citation* that silently means
   different files in different projects is a worse failure than a read that does.
2. **Strand addressing.** `memory:glossary:stitch` reuses the memory selector's own
   `web:keyword` syntax inside an artifact argument, which means two colons in one ref.
   `memory:glossary/stitch` avoids that at the cost of diverging from the selector
   spelling agents already know. I lean to the first — matching the selector matters more
   than colon aesthetics — but it is a vocabulary decision worth making once.
3. **The proposal subsystem.** Retire it, or wire it to artifact refs (§B8)? 2,362 LOC
   with zero use across 31 projects is a standing invitation to the `corpus-before-mechanism`
   record.
4. **`#memory/` deprecation.** Docs-only deprecation as recommended, or an actual
   removal with a compat window?

---

## Appendix — how to re-measure

```bash
# Corpus
ls sase/memory/*.md | wc -l
find sase/memory/decisions sase/memory/glossary sase/memory/task_types -name '*.md' | wc -l
sase memory list

# Usage
wc -l ~/.sase/projects/gh_sase-org__sase/{memory,artifact,glossary}_reads.jsonl

# Link graph
python3 -c "import json,collections;d=json.load(open('$HOME/.sase/projects/gh_sase-org__sase/artifact-links.json'));print(len(d['rows']),collections.Counter(r['relation'] for r in d['rows']).most_common())"

# Demand signal (run from the opened sidecar checkouts)
grep -rl 'sase/memory/' "$(sase repo path plans)" --include=*.md | wc -l
grep -rl 'sase/memory/' "$(sase repo path research)" --include=*.md | wc -l
grep -rl '#memory/' "$(sase repo path agents)/prompts" | wc -l

# Unused mechanism
find ~/.sase/projects -maxdepth 2 -name 'memory_proposals.jsonl' | wc -l
```

**Related artifacts.** `research:202608/glossary_to_memory_webs/glossary_to_memory_webs.md`
(the closest structural precedent), `research:202608/artifact_link_graph`,
`research:202608/agent_catalog_pane`, `research:202608/artifacts_pane_contract`,
`bead:sase-tj`, `bead:sase-tw`, and the `corpus-before-mechanism` and `memory-webs`
decision records.
