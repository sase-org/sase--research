---
create_time: 2026-08-24
updated_time: 2026-08-24
status: research
tags:
  - artifacts
  - artifact-links
  - adoption
  - agent-context
  - provenance
  - chops
  - finalizers
---

# Artifact Link Derivation: Fix the Index, Derive the Edges, Never Tax the Turn

**Research question.** Plans and research reports are not being linked consistently or
well. How should SASE fix that — and improve artifact links generally — without adding
instruction weight to the average agent's context?

**Sources.** Consolidates two independent studies:
`artifact_link_derivation__a.md` (research.11.cdx — architecture, relation semantics,
external prior art) and `artifact_link_derivation__b.md` (research.11.cld — live
measurement, defect discovery, injection-point analysis), plus lead verification that
confirmed both reports' central claims, resolved four disagreements, and found one defect
neither report identified.

**Method.** Code inspection at `d88994bd8`; live measurement of the link store, the
`plans` / `research` / `beads` sidecars, and the bead event stream on 2026-08-24. Every
count below was re-measured by the lead unless attributed. Where a claim is an inference,
it says so.

---

## Bottom line

Both researchers converged on the same core answer from opposite directions, and the
convergence is the strongest result here: **do not tell agents to link more. Derive the
links from data SASE already owns.** The evidence for that is measured, not predicted
(§2).

But consolidation surfaced a problem that changes the sequencing. **The link index is
lossy in a way neither report caught.** The aggregate is rebuilt destructively from
whichever *workspace clone* happens to trigger it, and it does not preserve rows it cannot
see. Right now, this workspace's committed sidecar truth holds **134 rows** while the
machine-global index holds **84** — **66 rows of durable, committed truth are missing from
the index** (§3.1). The graph shrank from 137 rows to 84 in the hours between the two
researchers measuring it and this consolidation.

That inverts one of report **b**'s conclusions ("the storage design is sound; it is the
*inflow* that is broken") and makes its Phase 0 insufficient on its own. Deriving ~1,700
new edges into a store that silently drops committed rows on an unlucky rebuild is
building on sand.

**Revised order: make the index non-lossy, then derive, then make it pay, then curate.**

---

## 1. What SASE has, and what is actually missing

The substrate is well-built and mostly correct. Report **a**'s architectural read holds up
under verification:

- **Two-layer persistence with the right ownership boundary.** Durable truth lives with
  the artifact provider — sidecar `links/**/*.json` for file artifacts, bead events for
  beads. The machine-local aggregate under the SASE state directory is declared a
  rebuildable cache. A cloned artifact repo brings its links with it. This is the correct
  design; §3.1 is a bug in the cache-rebuild rule, not in the design.
- **A deliberately small closed vocabulary.** Two automatic provenance relations
  (`cites`, `read`) and four curated semantic ones (`derives-from`, `implements`,
  `supersedes`, `related`). `blocks` / `depends-on` correctly remain bead scheduling
  concepts.
- **Managed Markdown projections** render curated links into a `## Links` block and
  automatic references into `## Referenced By`, so Markdown is a projection, not the
  database.

What is missing is not storage and not vocabulary. It is **inflow, retention, and
payoff** — and three half-finished paths:

| Built | State | Verified |
| --- | --- | --- |
| `artifact_link_frontmatter_inlet` (Rust `links:` parser) | **No production caller.** Appears only in `tools/validate_sase_core_rs:145` and its test. | ✅ lead |
| `derived` row origin | Schema-valid and documented in `sase artifact link list --origin` help. **Zero live rows.** Projection classifier renders `manual`/`migrated` as curated and `prompt_ref`/`read` as automatic; a `derived` row is neither class. | ✅ lead |
| `sase artifact link migrate-notes --apply` | Fully wired (`apply_related_note_migration` + `bead_store_mutation.commit`). **Never run.** Its own help still says "that mutation path lands with the beads phase." | ✅ lead |

`sase artifact link` has exactly four subcommands — `add`, `list`, `migrate-notes`, `rm`.
There is no `suggest` and no `relation list/show`; both reports' proposals for those are
net-new.

---

## 2. The measured case against instruction

This is report **b**'s central contribution and it is decisive. The obvious hypothesis —
agents do not link because they were not told — is falsified by the data.

**The instruction channel is open and saturated.** `AGENTS.md` §1.1 puts the full relation
registry in Tier 1: 893 characters in front of every agent on every turn, on every
provider. Separately, `sase/memory/sase_artifacts.md` — which contains four worked
`link add` examples including `implements` and `supersedes` — was read **135 times** in
five days through `sase memory read`, roughly 17% of all agent runs in the window.

**The output was ~zero.** In that same window SASE executed 803 agent runs. Excluding the
project owner and two research swarms, **five deliberate links** came out of the remaining
749 runs — 0.7%. `implements` has been written **zero** times. `supersedes` has been
written **zero** times. Those are the two relations the Tier 1 budget pays for on every
turn.

**The control group is next door.** The bead scheduling graph holds **~3,097 live
dependency edges** (6,194 `dependency_added` events; lead-verified, matching **b**'s 3,091
within a day's drift). Same agents, same runtimes, no memory file evangelizing it. The
difference is that a bead dependency *does something* — it gates a launch.

> **Edges get written when they are load-bearing, not when they are documented.**

Report **a** reaches the same place by a different route: link quality tracks *workflow*
guidance, not *global* guidance. The `/sase_new_task` skill teaches `related` links, and
bead→bead `related` is the single largest curated cluster (23 rows). Research consolidation
produces obvious source/output pairs, and research→research `derives-from` is the second
(13 rows). The two workflows with a link step have links; the ones without have none. The
`#research_swarm` xprompt never mentions links at all, and neither does `/sase_plan`
(lead-verified).

That is evidence *for* narrow workflow instruction and *against* broad standing
instruction — the same conclusion, arrived at independently.

**The cost argument is attention, not tokens.** `AGENTS.md` is ~18k characters across 8
Tier 1 sections. Another 300 characters costs approximately nothing in dollars. What it
costs is a slice of a fixed instruction budget that already carries a mandatory finalizer
protocol, a repo-access protocol, a task-bead protocol, and a two-speed verification
protocol. Every additional standing obligation dilutes the load-bearing ones.

**And linking is the wrong job for a busy agent.** An agent finishing a plan is mid-task,
holding a large working set, and about to hand off. Asking it to also survey the corpus for
topical neighbors is context-expensive and low-precision at the worst possible moment — and
a `related` edge produced as a checklist item is exactly the kind that gets rubber-stamped.

---

## 3. Defects found — three confirmed, one new and severe

### 3.1 The aggregate is destructively rebuilt from one workspace's clone — **new**

**Confirmed by lead measurement and code inspection. Neither report identified this.**

`Sdd ArtifactLinkStore.preview_aggregate()`
(`src/sase/sdd/_artifact_link_store_impl.py:233`) builds the replacement aggregate from:

1. `self._iter_sidecar_rows()` — the **current workspace's** sidecar working tree;
2. `self._iter_bead_rows()` — bead events; and
3. from the *previous* aggregate, only rows where `_is_aggregate_only(row)` is true —
   i.e. rows where **neither endpoint owns sidecar JSON**.

`rebuild_aggregate()` then writes that over the machine-global index. Every `upsert_row`
call ends in `rebuild_aggregate()`.

The consequence: any row whose endpoint *would* own a sidecar — every `plan:` and
`research:` edge, which is the great majority of the graph — is **dropped from the index**
unless it is visible in the triggering workspace's clone at that instant. It is not carried
forward from the prior aggregate. Since agents run from ephemeral numbered workspaces whose
sidecar clones fast-forward independently, **any agent in any workspace can silently shrink
the machine-global graph** by writing one link.

Measured on 2026-08-24 from workspace `sase_22`:

| Store | Rows |
| --- | ---: |
| Committed sidecar truth in this workspace (`sase/repos/*/links/**/*.json`) | **134** |
| Machine-global aggregate (`~/.sase/projects/gh_sase-org__sase/artifact-links.json`) | **84** |
| Durable rows **missing** from the index | **66** |

By relation, the index holds `read` 50, `related` 31, `derives-from` **2**, `cites` 1 —
against sidecar truth of `read` 69, `related` 29, `derives-from` **35**, `cites` 1. Both
researchers measured 137 rows a few hours earlier, with 17 `derives-from`. Every
`research:`-targeted row is currently absent from the index.

This **falsifies report b §1.1** ("Per-artifact truth in the sidecars reconciles exactly
with the aggregate — zero rows in truth are absent from the aggregate. The storage design
is sound. It is the *inflow* that is broken."). That reconciliation was true in that
workspace at that moment; it is not a property of the design. The durable layer is sound.
The **index layer is lossy**, and it is the layer every consumer reads.

**Fix.** `preview_aggregate` must preserve prior-aggregate rows whose sidecar root is not
resolvable *in this workspace*, rather than only rows that own no sidecar anywhere.
Equivalently: a rebuild may only delete a row it can prove was deleted, not one it merely
cannot see. Add a doctor counter comparing durable sidecar row count against index row
count, so any future divergence is visible.

**This is Phase 0.** Everything else leaks through it.

### 3.2 `sase artifact read` records link rows that are never committed — ~45% loss

**Confirmed (report b, re-verified by lead).**

`handle_link_add` calls `store.upsert_row(...)` **and then**
`persist_artifact_link_graph_mutation(...)`, which commits each sidecar it changed.
`_record_read_link` (`src/sase/artifact_cli/read.py:243`) calls `store.upsert_row(...)`
and stops. `persist_artifact_link_graph_mutation` has exactly two call sites, both in
`artifact_cli/link_ops.py` (lead-verified).

The row lands only in the ephemeral workspace's sidecar working tree. **b** measured 145
read events with `recorded_link: true` covering 140 distinct `(agent, ref)` pairs against
78 durable rows — 63 pairs (45%) lost.

This is hazard #1 of the original design (`202608/artifact_link_graph`, "index silently
uncommitted") re-emerging on the write path that generates the majority of the volume.
Filed as **`sase-t0`**.

Note that 3.1 and 3.2 compound: 3.2 leaves rows uncommitted in a workspace, and 3.1 then
deletes even the *committed* ones from the index when a different workspace rebuilds.
Fixing 3.2 alone does not make the graph durable.

### 3.3 A link whose *target* is a bead never reaches the bead

**Confirmed by reproduction (report b) and code inspection (lead).**

`_upsert_bead` (`_artifact_link_store_impl.py:373`) does:

```python
issue_id = bead_id_from_ref(str(incoming["source_ref"]))
if issue_id is None:
    return None
```

Only `source_ref` is inspected. A bead in the **target** position is skipped entirely. All
26 existing `link_added` events in the store have a bead as source; not one was written by
an inbound edge.

This matters most for `related`, which the registry defines as **undirected**
(`inverse: related, directed: no`) — an undirected edge stored on one endpoint only is half
an edge. It also splits consumers: the ACE beads pane reads the aggregate and would show
it, while `sase bead show` and the generated bead page read the event stream and would not.
Critically, **every `plan implements bead` edge derived in §4.1 would land on the plan and
be invisible from the bead** — the direction a person browsing beads actually wants.

Fix: write an endpoint event for a bead in **either** position, storing the registry-
declared inverse when the bead is the target. Filed as **`sase-t1`**.

### 3.4 Links do not survive renames, and the research workflow renames by design

**Confirmed by report b, and reproduced live by this consolidation.**

`sase artifact doctor` reports dangling `research:` refs; **b** traced all seven to files
the research swarm's consolidation step moved.

The lead reproduced it while producing *this* report. Before the move, the two source
reports carried six live link rows between them (one `derives-from` to
`artifact_link_graph`, three `related` to beads `sase-r8` / `sase-t0` / `sase-t1`, and two
`derives-from` on the other report). After `git mv` into
`artifact_link_derivation/`, git recorded both as pure renames:

```
R  artifact_link_adoption_and_quality.md -> artifact_link_derivation/artifact_link_derivation__a.md
R  artifact_link_adoption.md             -> artifact_link_derivation/artifact_link_derivation__b.md
```

All six rows are now dangling, `links/202608/artifact_link_adoption.md.json` and
`links/202608/artifact_link_adoption_and_quality.md.json` are orphaned companions, and the
new paths have no `links/` companion at all.

**Step 3 of `#research_swarm` always moves the two source reports.** The canonical research
workflow breaks its own links every time it runs — including this run. Git already provides
the rename for free (`R100`); the link refresh pass simply does not consume it.

Any derivation scheme that writes edges before the swarm's move is worthless without rename
following.

### 3.5 Beads carry two competing edge concepts

`reference_added` **68** events vs `link_added` **26**. `sase artifact create --bead` writes
the former (`_attach_reference_to_bead`); `sase artifact link add bead:… …` writes the
latter. Both mean "this bead and this artifact are connected." Two vocabularies for one idea
guarantees neither is used consistently and forces every consumer to read both. Cheap to
consolidate now at 94 rows; expensive later. Natural answer: `--bead` writes a typed link
and `reference_added` becomes a legacy alias.

---

## 4. Coverage: what is mechanically derivable today

Both reports measured coverage; their denominators differ because **a** scoped to August
sidecars and **b** to the full corpus. Lead-verified full-corpus figures:

| Population | Size | Linked | Coverage |
| --- | ---: | ---: | ---: |
| Plan `.md` files | 3,976 | ~29 | **0.7%** |
| Research `.md` files | 425 | ~26 | **6.1%** |
| Plans carrying `bead_id:` in frontmatter | **602** | 0 `implements` | **0%** |
| Research swarm consolidations (`__a` + `__b` pairs) | **55** | 1 | **1.8%** |
| Bead `RELATED:` notes awaiting migration | **303** | 0 applied | **0%** |
| Prompts citing an artifact by prose path vs `@ref` | 219 vs 12 | — | — |

Scoped to artifacts created after the CLI shipped on 2026-08-20, report **a** found 2 of
114 new plans (1.8%) with a curated link versus 10 of 26 new research artifacts (38.5%) —
again showing the workflow-guidance effect rather than a corpus-wide constant.

**The swarm row is the sharpest single fact in either report.** `#research_swarm` produces a
rigid, machine-known shape: two reports become `<name>__a.md` / `<name>__b.md`, and a third
merges them. That is a `derives-from` pair by construction — 110 edges across 55
consolidations. **One** consolidation has them. The most mechanically derivable link in the
entire system has 1.8% coverage, and the xprompt that creates the shape never mentions
links.

**The citation channel is starved.** 4,604 archived prompts contain 12 `@<kind>:` artifact
refs (0.3%) against 219 prompts making 437 prose mentions of plan/research paths (4.8%).
Humans and launching agents cite artifacts constantly; they type
`sase/repos/plans/202608/foo.md`, not `@plan:202608/foo.md`. The `cites` writer is correct
and idle. This needs no agent behavior change — only a resolver on the publication path.

---

## 5. Nothing consumes links, so nothing rewards writing them

This is the causal root beneath §2, and both reports found pieces of it. Verified:

- **ACE drops the relation type.** `_emit_link_edge`
  (`src/sase/ace/tui/relations/artifact_links.py`) constructs `RelationEdge` from
  `decl.kind` / `decl.name` / `decl.label` — the *pane declaration's* generic
  `links` / `linked_by` — and discards `row["relation"]`, `row["description"]`,
  `row["origin"]`, and `row["uses"]`. The relation slug survives only inside `_edge_key`
  for deduplication. **The Markdown projection preserves more semantic information than the
  interactive UI.** (report **a**, lead-verified)
- **…and most edges point at a pane that does not exist.** `_target_for_ref` maps `agent:`
  refs to `ArtifactEntryTarget("agents", …)`, but the Artifacts tab configures no `agents`
  pane. The entire `read` corpus — the majority of the graph — resolves to nothing. The
  original design named the Agents sub-tab an explicit non-goal, so this is a known gap,
  not a regression. (report **b**, lead-verified)
- **The sanctioned read path hides links.** `sase artifact read` calls `_strip_managed_text`,
  which applies `links_block_strip`, then `referenced_by_block_strip`, then drops
  frontmatter. An agent reading an artifact through the audited path sees **fewer** links
  than one that runs `cat`.
- **Prompt expansion does not expand the neighborhood.** Resolving `@plan:x` surfaces
  nothing about `x`'s links.
- **There is no authoring affordance in ACE.** Every deliberate edge in the store was typed
  at a shell.

The two reports disagreed on the third item — **a** framed stripping as a deliberate
context-saving feature, **b** as the highest-leverage defect on the list. **Both are
correct, and the fix satisfies both:** keep stripping the multi-line managed *block* (it
would genuinely bloat context), and print a single-line typed footer instead —
`Links: implements bead:sase-r8 · derives-from research:…`. That costs ~20 tokens, turns
every audited read into a discovery moment, and preserves **a**'s constraint that richer
projections must not inflate model context.

---

## 6. Design principles

Report **a**'s survey of external prior art supplies the discipline that keeps a derived
graph from becoming noise. Four principles, each with a live consequence for SASE:

**Do not infer semantic lineage from access.** [W3C PROV-O](https://www.w3.org/TR/prov-o/)
distinguishes an activity *using* an entity from the output being a *derivation* of it. An
agent reads a plan to compare, reject, debug, or merely understand it. Promoting every
`read` to `derives-from` would produce a dense and misleading graph. Keep an **observational
plane** (`read`, `cites`) separate from a **semantic plane** (`derives-from`, `implements`,
`supersedes`, `related`).

**Attribute outputs to inputs, not inputs to outputs.**
[OpenLineage](https://openlineage.io/docs/) pushes collection into schedulers rather than
job authors, and its
[lineage job facet](https://openlineage.io/docs/next/spec/facets/job-facets/lineage/)
records sources *per output* precisely to avoid false Cartesian-product lineage when a job
has several inputs and outputs. SASE's rule follows: **a run's read set is a candidate pool,
not a set of automatic `derives-from` edges.**

**Keep authoritative input compact; derive the graph.** Backstage treats catalog relations
as read-only output derived by processors from authoritative descriptors, and warns that a
catalog should capture the human mental model rather than become an exhaustive inventory.
GitHub follows the same lifecycle-boundary pattern: a compact keyword in a PR description is
interpreted by the host, which creates the relationship. Authors declare a fact; the host
materializes the edges.

**Materialize from the native association; never store a second editable copy.** Where SASE
already owns the relationship (a plan's `bead_id`, a swarm's `__a`/`__b` shape), the link
row is a projection of that fact, not an independent assertion that can drift.

Together these give the design constraints:

- **Zero steady-state context cost** — an agent not producing an artifact sees nothing new.
- **Near-zero deterministic cost** — if the workflow knows the relation, the host writes it
  without asking a model.
- **One durable truth** — Markdown is an inlet and a projection; provider-owned indexes and
  events remain authoritative.
- **Explainable provenance** — distinguish observed, declared, migrated, and host-derived.
- **No false completeness** — coverage metrics identify opportunity; they never become a
  quota. The denominator is "artifacts for which the workflow had a credible candidate,"
  not all Markdown files.

---

## 7. The three-tier taxonomy

Report **b**'s taxonomy is the organizing idea, refined with **a**'s semantic constraint:

| Tier | Definition | Who writes it | Available today |
| --- | --- | --- | ---: |
| **Derivable** | Fully implied by data SASE already owns | The host, at the moment of creation | ~1,000 |
| **Observable** | SASE watched it happen but has not promoted it | The host, from its own logs — as *candidates*, per §6 | ~600 |
| **Judgment** | Requires reading two artifacts and forming an opinion | A batch curator, off the critical path | unbounded |

The important amendment: **a**'s PROV argument means the Observable tier must not
auto-promote. The read log is the best candidate source in the system precisely *because*
each entry carries the agent's own stated reason — but a candidate is not an edge.

### 7.1 Tier 1 — derive, no agent involvement

| Edge | Available | Notes |
| --- | ---: | --- |
| `plan implements bead:<id>` | **602** | From `bead_id:` frontmatter; already rendered as `- **BEAD:**` on 808 plans. |
| `research:<n> derives-from research:<n>__a\|__b` | **108** | Derivable from filename shape, exactly from the rename commit (§3.4). |
| `plan ← cites ← agent` from the `PROMPT:` header | ~3,065 | Already rendered on 77% of plans. **Gate on the `agent:` pane landing (§5).** |
| `AGENTS` / `COMMITS` plan-header edges | ~2,300 | **Hold.** No consumer; would bury deliberate edges. |

**Unresolved semantics — needs an owner decision.** Report **b** asserts
`plan implements bead`. Report **a** flags, correctly, that the direction is ambiguous: if a
plan is the *realization* of a bead's requirement, `plan implements bead` is right; if the
native record means only "this bead was created from this plan," `implements` is being
overloaded and a different relation is needed. The registry's own guidance is thin here —
`implements` has zero live examples, and a *patch* or *stitch* implementing a plan is the
more intuitive reading. **Settle this before deriving 602 rows of it.**

### 7.2 Tier 2 — promote what SASE already observed, as candidates

**The read log is an unread provenance ledger.**
`~/.sase/projects/<key>/artifact_reads.jsonl` records, per agent, every artifact read **with
the agent's own stated reason**:

```json
{"agent_name": "sase-r8.9.land", "ref": "plan:202608/artifact_link_core_release.md",
 "reason": "Verify sase-r8.9 scope and completion requirements before landing", …}
```

When that agent then produces an artifact, SASE knows what went into it and why — a
`derives-from` edge with a hand-written justification, already collected, currently used for
nothing. This is the highest-quality inflow available anywhere in the system.

Per §6, emit these as **ranked candidates at the artifact's lifecycle boundary**, carrying
the recorded reason as the row description — not as automatic edges. Recommend filtering to
`plan:` and `research:` targets on the first pass (more legible; the full set stays
recoverable from the log regardless).

**Prose path citations → `cites`.** Resolve `(repos/)?(plans|research)/20\d{4}/<file>.md` on
the prompt publication path. ~437 edges, no author behavior change. Keep it conservative —
exact path match only, no fuzzy title matching — and mark the origin so it is
distinguishable from a real `@ref`.

### 7.3 Tier 3 — judgment goes to a batch curator, never to a working agent

Add `sase artifact link suggest`, which proposes candidates with evidence and **writes
nothing**. Surface a batched digest through a notification gate, or hand it to one small
weekly curator agent. Bounded cost, paid once, not spread across 800 runs a day.

Restrict evidence to **hard signals only**: shared bead, shared epic, overlapping read sets,
filename lineage. A semantic-similarity suggester generates plausible `related` edges faster
than any human will audit them, and unaudited `related` edges are worse than no edges —
they destroy the graph's only real asset, which is trust.

**Do not persist suggestions as rows.** Report **a** identified a concrete reason: the
upsert key is `(source, relation, target)` and retains the row's original origin, creator,
and creation time, updating only the description. Writing a speculative `derived` row and
later "confirming" it would therefore never record the promotion to a human-declared
assertion. Keep candidates ephemeral until accepted.

---

## 8. Where to attach the machinery

Report **b**'s injection-point scoring, with the `/sase_final` row corrected by lead
verification:

| Point | Agent context cost | Coverage | Failure mode | Verdict |
| --- | --- | --- | --- | --- |
| Tier 1 `AGENTS.md` | every turn, permanent | measured at ~0 | dilutes real obligations | **No** |
| Tier 2 `sase_artifacts.md` | on demand, already paid | measured at ~0 | already tried | **Leave as is** |
| `/sase_plan`, `#research_swarm` step | only the producing agents | narrow | forgotten under load | **One line each, yes** |
| `sase plan propose` / `sase artifact create` | zero static; bounded, at the boundary | high, exact | command-local work | **Yes — primary** |
| `/sase_final` conditional finalizer | zero static; per-turn friction | high | needs new machinery; judgment at the worst moment | **No** |
| File hook on sidecar commit | **zero** | event-driven, exact | needs `--cause` exclusion | **Yes — reactive repair** |
| Lumberjack `housekeeping` chop | **zero** | bulk, retroactive | hourly latency | **Yes — backfill** |

**Resolving the finalizer disagreement.** Report **a** recommended a conditional
`artifact-links` finalizer selected only when a run produced a linkable artifact; report
**b** rejected adding anything to `/sase_final`. Lead verification settles it on cost:
finalizer selection is resolved from a **config plan**
(`_resolve_default_plan(config)` in `src/sase/finalizers/cli.py:156`), not from run state.
A run-state-conditional finalizer is not free today — it needs a new obligation kind, as
**b** argued. **a**'s underlying instinct is nonetheless right: the decision belongs at the
artifact's *lifecycle boundary*. That boundary is `sase plan propose` and
`sase artifact create` — which **a** independently identified as necessary for plans anyway,
since a plan handoff terminates the runner mechanically and skips finalizers entirely.
So: keep the boundary, drop the finalizer.

**Two mechanisms cost literally nothing and both already exist in production.**

- **File hooks.** `sase file-hook` runs configured commands against sidecar commits with
  path globs and producer-cause filters (`_run_file_hooks` in the commit workflow;
  `file_hooks:` in `default_config.yml`). `research-highlights` already does exactly this
  shape in production: a research report lands, a command runs, an artifact is produced. A
  hook on the plans and research sidecars — with cause `artifact_links` excluded so the
  projection commit does not re-trigger it — gives exact-moment derivation with zero agent
  involvement. **This is also where rename following (§3.4) belongs**, since the hook sees
  the commit that contains the rename.
- **Chops.** `default_config.yml` defines a `housekeeping` lumberjack bucket at a 3,600s
  interval, documented for "durable maintenance that may scan substantial local state." A
  `sase_chop_artifact_link_backfill` chop is the natural owner of the retroactive sweep and
  dangling-ref repair.

---

## 9. Recommended solution

**Phase 0 — make the index non-lossy. Prerequisite for everything.**

1. Fix `preview_aggregate` to preserve prior-aggregate rows whose sidecar root is not
   resolvable in the current workspace (§3.1). A rebuild may delete only what it can prove
   was deleted.
2. Fix `_record_read_link` to call `persist_artifact_link_graph_mutation` like `link_add`
   does (§3.2, `sase-t0`).
3. Add doctor counters: durable sidecar rows vs index rows, and `recorded_link: true`
   events vs durable read rows. Both leaks become visible instead of silent.

Without this the graph does not retain what it already has, let alone 1,700 new rows.

**Phase 1 — both endpoints, and rename following.** Independent of Phase 0; can run in
parallel.

4. `_upsert_bead` fires for a bead in **either** position, storing the registry inverse when
   the bead is the target (§3.3, `sase-t1`); backfill the endpoint events the one-sided
   writes never produced.
5. Consume git rename detection in the link refresh pass — rewrite `source_ref` /
   `target_ref` and move the `links/<path>.json` companion (§3.4). Repair the existing
   dangling research refs, **including the six this consolidation just created.**

**Phase 2 — decide the semantics, then derive.**

6. Settle `plan implements bead` vs a new relation (§7.1). Add direction, one positive and
   one negative example, and recommended endpoint kinds to the relation registry — surfaced
   through `sase artifact link relation list/show` and completions, **not** through core
   memory. Give `derived` a projection class so host-derived semantic edges render as
   curated.
7. One derivation module, called from three places: (a) `sase plan propose` and
   `sase artifact create` at creation time; (b) a file hook on the plans and research
   sidecars for anything that lands another way; (c) `sase_chop_artifact_link_backfill` in
   the hourly `housekeeping` bucket for the retroactive sweep. Derive in order of value:
   swarm `derives-from` (108), `plan implements bead` (602), read-log `derives-from`
   candidates (§7.2), then `PROMPT`-header `cites` gated on §5. Hold `AGENTS` / `COMMITS`.
8. Finish the `links:` frontmatter inlet as the *authoring* path: allow and strictly
   validate the field in plan frontmatter, resolve the canonical source ref after archiving,
   validate relation/direction/description, upsert the durable row, **remove the consumed
   inlet**, and refresh the projection. Persist inlet entries as `manual`; reserve `derived`
   for host facts. The inlet must never remain as a second editable representation.

**Phase 3 — run the backfills.**

9. `sase artifact link migrate-notes --apply`. Lead-measured: 4,216 beads scanned, **303**
   `RELATED:` notes, **269 auto-convertible (88.8%)**, 34 needing manual review. (Report
   **b**'s "~290" is ~8% high.) Verify the apply path on a scratch tree first — its own help
   text still describes the mutation as pending.
10. The prose-path `cites` resolver on the publication path (~437 edges, §7.2).

**Phase 4 — make it pay.** In priority order:

11. Print a one-line typed neighborhood footer in `sase artifact read` (§5). Smallest change
    on this list, probably the highest leverage, and it satisfies both reports.
12. Preserve the relation slug, inverse label, description, origin, and use count in ACE
    instead of flattening to `links` / `linked_by`; add a typed "link marked artifact to
    current artifact" action with a required reason.
13. Give `agent:` refs a real target, or stop emitting edges into a pane that does not exist.
14. Expand **one hop** in launch context when a prompt cites `@plan:x`, preferring
    `implements` / `derives-from` / `supersedes` and filtering observational edges. **Never
    expand transitively by default** — a one-hop typed neighborhood is predictable;
    unconstrained traversal is a context explosion.
15. Surface `supersedes` warnings when an agent opens a superseded artifact.
16. Add derived-coverage counters to doctor as a **report, not a gate**.

**Phase 5 — the judgment tier.** `sase artifact link suggest` plus a batched gate or a weekly
curator (§7.3). Only after Phases 2–4: a suggester with no derived baseline will mostly
re-propose edges the derivation should have produced.

### The only agent-facing text this adds

One line in `/sase_plan` and one line in the `#research_swarm` lead step. Both are
already-loaded contexts read only by agents that produce linkable artifacts, and both state
a **fact** rather than adding an obligation:

> SASE derives your plan's links from the artifacts you read this turn; use
> `sase artifact read` for context you actually used.

**Nothing is added to `AGENTS.md`. Nothing is added to `/sase_final`.** The average agent's
context does not change by one token.

### Projected outcome

| Source | Edges | Agent instruction added |
| --- | ---: | --- |
| Index today | 84 | — |
| Rows recovered by fixing the lossy rebuild (§3.1) | +50 | none |
| Read rows retained instead of lost (§3.2) | +62 | none |
| `plan implements bead` | +602 | none |
| Swarm `derives-from` | +108 | none |
| `RELATED:` migration | +269 | none |
| Prose-path `cites` | +437 | none |
| Read-log `derives-from` candidates | ~+150/mo, accepted subset | none |
| **Total** | **~1,600+** | **none** |

A ~19× graph against today's index, entirely from data SASE already owns — and, unlike the
current 84 rows, one that does not evaporate on the next rebuild.

---

## 10. What not to do

- **Do not add a linking obligation to `AGENTS.md`.** §2 is the argument. The experiment has
  already run: 893 Tier 1 characters and 135 Tier 2 reads produced 5 links in 803 runs.
- **Do not add a link step to `/sase_final`.** It puts a judgment task at the moment
  checklist-compliance behavior is worst, and selection is config-driven today so it is not
  even cheap (§8).
- **Do not promote every `read` to `derives-from`.** PROV and OpenLineage both warn against
  it; a read is a candidate, not a derivation (§6).
- **Do not widen the relation registry yet.** Six slugs with two at zero usage is not a
  vocabulary problem. Revisit after the derived graph shows what is actually missing.
- **Do not promote `AGENTS` / `COMMITS` plan-header edges in the first pass.** ~2,300 edges
  with no consumer would bury the deliberate ones in every rendered Links block.
- **Do not build a fuzzy topical suggester.** Hard evidence only (§7.3).
- **Do not turn coverage into a quota.** The denominator is artifacts with a credible
  candidate, not all Markdown. Run the audit as a report until false-positive rates are
  understood.

---

## Open questions for the owner

1. **`plan implements bead` semantics (§7.1).** Does a plan *implement* a bead's
   requirement, or is `bead_id:` merely "this bead was created from this plan"? 602 derived
   rows depend on the answer, and `implements` has no live example to disambiguate it.
2. **`reference_added` vs `link_added` on beads (§3.5).** Should `sase artifact create
   --bead` write a typed link, with `reference_added` retained as a legacy alias?
   Consolidation is cheap now at 94 rows.
3. **Agents pane (§5).** The majority of edges point at it. Schedule it, or stop emitting
   `agent:` edges until it has its own reason to exist?
4. **Read-log derivation scope (§7.2).** Every read, or only `plan:` / `research:` targets?
   Recommend filtered for the first pass.
5. **Was the index loss (§3.1) ever worse than measured?** The graph fell 137 → 84 in hours.
   A one-time reconciliation sweep across all workspace clones may recover rows that no
   single clone currently holds.
