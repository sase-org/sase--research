---
create_time: 2026-08-24
updated_time: 2026-08-24
status: research
tags:
  - artifacts
  - artifact-links
  - adoption
  - agent-context
  - chops
  - finalizers
---

# Artifact Link Adoption: Getting a Real Graph Without Taxing Every Agent

**Research question.** Plans and research reports are not being linked consistently or
well. How should SASE fix that — and improve artifact links generally — without adding
instruction weight to the average agent's context?

**Method.** Everything below is measured against the live tree on 2026-08-24: `sase` at
`cbea4f23b`, the live link store (`sase artifact link list -j -l 0`, 137 rows), the
`plans` / `research` / `beads` / `agents` sidecars opened through `sase repo open`, the
bead event streams (24,249 events), the archived prompt corpus (4,604 prompts), the
audited read log (184 events), and `sase artifact doctor`. Where a claim is an inference
rather than a measurement, it says so.

---

## Bottom line

The graph is not underused because agents were told too little. It is underused because
**almost every link worth having is already implied by data SASE owns, and SASE is
asking a language model to retype it.**

Four numbers make the case:

| Measure | Value |
| --- | ---: |
| Total rows in the link graph (all time) | **137** |
| Bead dependency edges (`sase bead dep`) | **3,091** |
| `implements` rows ever written | **0** |
| `supersedes` rows ever written | **0** |

`implements` and `supersedes` are the two relations `AGENTS.md` §1.1 puts in front of
*every* agent on *every* turn, at a cost of 893 characters of Tier 1 budget. In the
month since they shipped, they have been written zero times. Meanwhile the *scheduling*
graph next door has 3,091 edges, because a bead dependency does something: it gates a
launch. That contrast is the whole finding. **Edges get written when they are
load-bearing, not when they are documented.**

So: do not add instruction text. Derive the mechanical links, promote the ones SASE
already observes, and route the genuinely judgment-based ones to a bulk, off-critical-path
curator. Doing only the mechanical derivation takes the graph from 137 rows to roughly
1,100 without adding one token to any agent prompt. Sections 4–8 lay that out; §2 lists
five defects found while measuring that must be fixed first, or the derived rows will
leak and misfile the same way the current ones do.

---

## 1. Ground truth

### 1.1 The graph today

137 rows, every one created between 2026-08-22 and 2026-08-24. Composition:

| Origin | Relation | Rows | Written by |
| --- | --- | ---: | --- |
| `read` | `read` | 78 | `sase artifact read` (automatic) |
| `manual` | `related` | 41 | CLI |
| `manual` | `derives-from` | 17 | CLI |
| `prompt_ref` | `cites` | 1 | prompt expansion (automatic) |

By node kind: 79 `agent:` sources, 28 `research:`, 26 `bead:`, 4 `file:`; targets are 51
`research:`, 41 `plan:`, 31 `bead:`, 13 `file:`, 1 `agent:`.

Per-artifact truth in the sidecars (119 rows across `plans/links/` and
`research/links/`) reconciles exactly with the aggregate — zero rows in truth are absent
from the aggregate. The storage design is sound. It is the *inflow* that is broken.

### 1.2 Coverage against the linkable universe

| Population | Size | Has ≥1 edge | Coverage |
| --- | ---: | ---: | ---: |
| Research `.md` files | 423 | 26 | **6.1%** |
| Plan `.md` files | 3,971 | 29 | **0.7%** |
| Research swarm consolidations (`<stem>` + `<stem>__a`) | 55 | 1 | **1.8%** |
| Plans carrying `bead_id:` in frontmatter | 589 | 0 `implements` | **0%** |
| `RELATED:` bead notes awaiting migration | 303 | — | **0% applied** |

The swarm row is the sharpest. `#research_swarm` produces a rigid, machine-known shape:
a lead agent moves two reports to `<name>__a.md` and `<name>__b.md` and writes
`<name>.md` merging them. That is a `derives-from` edge pair by construction, 110 edges
across 55 consolidations. **One** consolidation has them
(`202608/finalizer_completion_contracts`). The single most mechanically derivable link in
the entire system has 1.8% coverage — and the xprompt that creates the shape
(`sase-research-artifacts/src/sase_research_artifacts/xprompts/research_swarm.md`) never
mentions links at all. The 13 `derives-from` rows that do exist were improvised by
individual research agents on their own initiative, mostly pointing at *topically* prior
reports rather than at their own `__a` / `__b` inputs.

### 1.3 Who actually writes links

Non-automatic rows, by author:

| Author | Rows | Note |
| --- | ---: | --- |
| `bryanbugyi34@gmail.com` | 23 | the project owner, by hand, all `bead → related → bead` |
| `research.*` agents | 24 | four members of two research swarms |
| Everyone else (`0c3`, `0bt`, `sase-ru.4`, `bbugyi200.athena.002--1`) | 5 | four agents, one row each |

In the same window (2026-08-20 → 08-24) SASE executed **803 agent runs**. Five
deliberate links came out of the 749 runs that were not the owner or a research swarm —
**0.7%**. The graph is currently a hand-curated artifact of one human plus whichever
research agents felt inspired.

### 1.4 Instruction reach is not the bottleneck

The obvious hypothesis is that agents do not know. Measured, they do:

- `sase/memory/sase_artifacts.md` — which contains four worked `sase artifact link add`
  examples including `implements` and `supersedes` — was read **135 times** through
  `sase memory read`, every one of them since 2026-08-20. That is ~17% of all agent runs
  in the window, the second-highest read rate of any Tier 2 memory relative to its age.
- `AGENTS.md` §1.1 puts the full relation registry in Tier 1: 22 lines, 893 characters,
  loaded into every turn of every agent on every provider.

135 agents read the detailed guidance in five days and produced **five** deliberate
links between them. The channel is open and the message is being delivered. Louder is not
the fix; nothing about a fifth restatement of the vocabulary changes the incentive.

### 1.5 The citation channel is starved

`cites` rows come from `@ref` expansion in prompts. Across the 4,604 archived prompts:

| Prompt property | Count | Share |
| --- | ---: | ---: |
| Contains an `@<kind>:` artifact ref | 12 | **0.3%** |
| Mentions a plan or research file **by path, in prose** | 219 | **4.8%** |

437 individual prose mentions of plan/research paths against 12 prompts that used the
machine-readable form. Humans and launching agents *do* cite artifacts constantly; they
type `sase/repos/plans/202608/foo.md`, not `@plan:202608/foo.md`. The `cites` writer is
correct and idle. This is the cheapest untapped inflow in the system, and it needs no
agent behavior change at all — only a resolver on the publication path.

### 1.6 Nothing consumes links, so nothing rewards writing them

- **ACE.** `links` / `linked_by` are declared on every Artifacts pane and
  `relations/artifact_links.py` maps refs to panes correctly, including cross-kind. But
  `agent:` refs resolve to `ArtifactEntryTarget("agents", …)` and the Artifacts tab
  configures no `agents` pane (`stitches, patches, beads, ref:plan, ref:research, files`).
  57% of the graph — the entire `read` corpus — points at a pane that does not exist. The
  original design named the Agents sub-tab an explicit non-goal, so this is a known,
  deliberate gap, not a regression.
- **Prompts.** Expanding `@plan:x` does not surface `x`'s neighborhood.
- **Reads.** `sase artifact read` strips the managed Links block before printing
  (`_strip_managed_text`), so an agent reading an artifact through the sanctioned audited
  path sees *fewer* links than one that runs `cat`.
- **Authoring.** There is no ACE action to add a link. Every deliberate edge in the store
  was typed at a shell.

An agent that writes a link gets nothing back, and neither does the next agent. That is
the difference from `sase bead dep`.

---

## 2. Five defects found while measuring

These are prerequisites. Derived rows will leak exactly like the current ones until 2.1
and 2.2 are fixed, and will land on only one endpoint until 2.5 is fixed. 2.1, 2.2, and
2.5 were each confirmed by direct reproduction while writing this report.

### 2.1 `sase artifact read` records links that are silently discarded — ~45% loss

**Confirmed.** The read log has 145 events with `recorded_link: true`, covering 140
distinct `(agent, ref)` pairs. The graph holds **78** read rows. 63 recorded pairs (45%)
have no durable row — 56 of them plan targets.

Root cause, in code: `handle_link_add` calls `store.upsert_row(...)` **and then**
`_persist_link_mutation(...)` → `persist_artifact_link_graph_mutation`, which commits each
sidecar it changed. `_record_read_link` in `src/sase/artifact_cli/read.py:243` calls
`store.upsert_row(...)` and stops. `persist_artifact_link_graph_mutation` has exactly two
call sites, both in `artifact_cli/link_ops.py`.

The row therefore lands in the *ephemeral workspace's* clone of the sidecar working tree.
`upsert_row` finishes by calling `rebuild_aggregate()`, which
"[rebuilds] `artifact-links.json` from sidecar JSON plus bead events" — a full rescan of
whatever the working tree currently holds. The next agent, in a different workspace whose
sidecar clone was just fast-forwarded to `origin`, rebuilds the aggregate from a clean
checkout and the uncommitted rows disappear from the machine-local index too. The rows
that survived are the ones whose workspace happened to run a `link add` or a projection
commit afterward.

This is hazard #1 of the original design (`202608/artifact_link_graph`, "index silently
uncommitted") re-emerging on the write path that generates 57% of the volume. Filed as
**`sase-t0`** (bug, medium).

### 2.2 Links do not survive renames, and the research workflow renames by design

**Confirmed.** `sase artifact doctor` reports 7 dangling `research:` refs. All seven are
files the research swarm's consolidation step moved. Example, commit `ac36494` in the
research sidecar:

```
A    202608/conditional_launch_admission/conditional_launch_admission.md
R100 …/conditional_launch_admission__a.md  ← 202608/conditional_launch_if_directive.md
R100 …/conditional_launch_admission__b.md  ← 202608/xprompt_if_directive.md
```

Git recorded both as pure renames (`R100`). The link rows still name the old paths, and
orphaned `links/202608/xprompt_if_directive.md.json` sidecar files are left behind. Since
step 3 of `#research_swarm` *always* moves the two source reports, the canonical research
workflow breaks its own links every time it runs. Doctor also reports 8 dangling `agent:`
refs (dismissed or pruned agents) and 4 missing companions under `~/tmp/screenshots`.

Any derivation scheme that writes edges before the swarm's move is worthless without
rename following. Git already gives the rename for free.

### 2.3 The `RELATED:` migration was built and never applied

`sase artifact link migrate-notes` reports **303 notes on 4,207 beads** as a dry run, and
`--apply` exists. The store holds 26 `link_added` bead events. The migration — designed,
implemented, tested, and estimated at ~92% mechanical — has not been run. It is the single
largest available backfill, roughly 290 edges, or 2.1× the current entire graph.

### 2.4 Beads carry two competing edge concepts

Bead event counts: `reference_added` **68**, `reference_removed` 8, `link_added` **26**,
`link_removed` 0. `sase artifact create --bead` writes the former
(`_attach_reference_to_bead`); `sase artifact link add bead:… …` writes the latter. Both
mean "this bead and this artifact are connected." Two vocabularies for one idea
guarantees neither gets used consistently and forces any consumer to read both. Worth
resolving before the volume grows; the natural answer is that `--bead` writes a typed
link (`implements` for a plan, `related` for a report) and `reference_added` becomes its
legacy alias.

---

### 2.5 A link whose *target* is a bead never reaches the bead

**Confirmed by reproduction.** Writing this report's own links surfaced it:

```bash
sase artifact link add research:202608/artifact_link_adoption.md related bead:sase-r8 "…"
```

The row is stored in `research/links/202608/artifact_link_adoption.md.json` and appears
in `sase artifact link list`. It does **not** appear on the bead. `sase-r8`'s event
stream gained no `link_added` event, and its generated page has no Links block.

Root cause, in `_artifact_link_store_impl.py:382`:

```python
issue_id = bead_id_from_ref(str(incoming["source_ref"]))
if issue_id is None:
    return None
```

`_upsert_bead` inspects **only** `source_ref`. A bead in the target position is skipped
entirely. Confirmed against the corpus: all 26 `link_added` events in the store have a
bead as source (23 → `bead`, 3 → `plan`); not one was written by an inbound edge.

This matters most for `related`, which the registry defines as *undirected*
(`inverse: related, directed: no`). An undirected edge stored on one endpoint only is
half an edge. It also splits the two consumers: the ACE beads pane reads the aggregate
and would show it, while `sase bead show` and the generated bead page read the event
stream and would not. Every `plan implements bead` edge derived in §4.1 lands on the plan
and is invisible from the bead — which is the direction a person browsing beads actually
wants.

Fix: `_upsert_bead` should write an endpoint event for a bead in **either** position,
with the relation stored in its registry-declared inverse form when the bead is the
target. Filed as **`sase-t1`** (bug, medium).

## 3. Why "tell the agents to link more" is the wrong instrument

Three arguments, in increasing order of force.

**The cost is attention, not tokens.** `AGENTS.md` is 18,011 characters (~4.5k tokens,
368 lines) across 8 Tier 1 sections and 8 Tier 2 pointers. Adding 300 characters costs
~$0 at 800 runs/day. What it actually costs is a slice of a fixed instruction budget that
already contains a mandatory finalizer protocol, a repo-access protocol, a task-bead
protocol, and a two-speed verification protocol. Every additional standing obligation
dilutes the ones that are load-bearing. The correct question is not "can we afford the
tokens" but "is this the highest-value 300 characters we could put in front of every
agent." It is not.

**The experiment has already run.** §1.4: 893 Tier 1 characters and 135 Tier 2 reads
produced 0 `implements`, 0 `supersedes`, and 5 agent-authored links in 803 runs. This is
not a prediction about what exhortation would achieve. It is a measurement of what it did
achieve.

**Linking is the wrong job for the agent that is busy.** An agent finishing a plan is
mid-task, holding a large working set, and about to hand off. Asking it to also survey the
artifact corpus for topical neighbors is a context-expensive, low-precision request at the
worst possible moment — and the resulting `related` edge is exactly the kind of judgment
that gets rubber-stamped when it is a checklist item. The links it *could* write reliably
are the ones it does not need to think about, and those are the ones SASE can derive
without asking.

That yields the taxonomy the design rests on:

| Tier | Definition | Who should write it | Volume available |
| --- | --- | --- | ---: |
| **Derivable** | Fully implied by data SASE already owns | The host, at the moment of creation | ~1,000 |
| **Observable** | SASE watched it happen but has not promoted it to an edge | The host, from its own logs | ~200 |
| **Judgment** | Requires reading two artifacts and forming an opinion | A batch curator, off the critical path | unbounded |

---

## 4. Tier 1 — derive it, no agent involvement

Every item below is a pure function of committed data. None requires an agent to do or
know anything.

### 4.1 `plan implements bead:<id>`

589 plans carry `bead_id:` in frontmatter; 808 render a `- **BEAD:**` line in the
projected plan header. Zero `implements` rows exist. The plan header projection
(`sdd/plan_links_refresh.py`, `sdd/associations/`) already maintains this association
tree-wide and rewrites it on demand. It is a rendering of provenance the link graph
should also hold.

Available today: **589–808 edges.**

### 4.2 `research:<name> derives-from research:<name>__a | __b`

55 consolidations, 110 edges, 2 present. Derivable from filename shape alone, and better
still from the rename commit itself (§4.4), which knows the pre-move identity.

Available today: **108 edges.**

### 4.3 The rest of the plan header

Plan headers already render `- **PROMPT:**` on **3,065 plans (77%)**, `AGENTS` on 987,
and `COMMITS` on 1,290. These are `plan ↔ agent` and `plan ↔ stitch` provenance edges
maintained by machine, rendered as Markdown, and absent from the graph. Promoting them is
a projection-to-store mapping, not new inference. Note the volume asymmetry: this alone is
~5,300 edges against a current total of 137, so it should land behind the `agent:` pane
work (§6.1) and probably with a rendering cap, or the Links block on every plan becomes
noise. Recommend deriving `PROMPT` (the highest-value, agent→plan provenance) first and
holding `AGENTS` / `COMMITS` until there is a consumer.

### 4.4 Rename following

Teach the link refresh pass to consume git rename detection for the sidecar commit it is
reacting to, rewriting `source_ref` / `target_ref` and moving the `links/<path>.json`
companion. This converts §2.2 from a permanent decay rate into a non-issue, and makes
§4.2 exact rather than filename-heuristic.

---

## 5. Tier 2 — promote what SASE already observed

### 5.1 The read log is a provenance ledger nobody is reading

`~/.sase/projects/<key>/artifact_reads.jsonl` records, per agent, every artifact read,
**with the agent's own stated reason**:

```json
{"agent_name": "sase-r8.9.land", "ref": "plan:202608/artifact_link_core_release.md",
 "reason": "Verify sase-r8.9 scope and completion requirements before landing", …}
```

When that same agent then produces an artifact — proposes a plan, writes a research
report, runs `sase artifact create` — SASE knows exactly what went into it and why. That
is a `derives-from` edge with a hand-written justification, already collected, currently
used for nothing but the `agent → read → artifact` row.

Concretely: at `sase plan propose`, emit `plan:<new> derives-from <each artifact the
proposing agent read this turn>`, carrying the recorded reason as the row description.
Same at `sase artifact create`. This is the highest-quality inflow available anywhere in
the system, because the description is a real human-authored sentence about why the source
mattered, captured at the moment it mattered.

### 5.2 Prose path citations → `cites`

219 prompts mention a plan/research path in prose (437 mentions) against 12 using `@refs`
(§1.5). The prompt publication path already rewrites and archives prompts; resolving
`(repos/)?(plans|research)/20\d{4}/<file>.md` to a canonical ref there yields ~437 `cites`
edges with no author behavior change. Keep it conservative — exact path match only, no
fuzzy title matching — and mark the origin so it is distinguishable from a real `@ref`.

---

## 6. Make the graph load-bearing

Derivation fills the graph. This is what makes it stay filled, and what makes the
judgment tier worth anyone's time.

1. **An Agents pane, or at minimum an `agent:` target that resolves.** 57% of edges point
   there. Until then the read corpus is write-only.
2. **`sase artifact read` should print the neighborhood.** It currently *strips* the Links
   block. Printing `Links: implements bead:sase-r8 · derives-from research:…` in a footer
   turns every audited read into a discovery moment and makes the graph pay the reader
   back immediately. This is the smallest change on this list and probably the highest
   leverage.
3. **Launch context should expand one hop.** When a prompt cites `@plan:x`, include `x`'s
   deliberate links in the resolved context. This is what makes a curator's `related` edge
   change what a future agent sees — the actual payoff loop.
4. **Doctor as a ratchet.** `sase artifact doctor` already reports dangling refs, stale
   tables, and missing companions. Add derived-coverage counters (plans with a bead and no
   `implements`, consolidations without their pair) so regressions in the derivation
   pipeline are visible.

---

## 7. Where to attach the machinery

Six candidate injection points, scored on what matters: cost to the average agent's
context, coverage achieved, and how it fails.

| Point | Agent context cost | Coverage | Failure mode | Verdict |
| --- | --- | --- | --- | --- |
| Tier 1 `AGENTS.md` | every turn, permanent | measured at ~0 | dilutes real obligations | **No** |
| Tier 2 `sase_artifacts.md` | on demand, already paid | measured at ~0 | already tried | **Already there; leave it** |
| `/sase_plan`, `#research_swarm` step | only the producing agents | narrow, still exhortation | forgotten under load | **One line each, yes** |
| `/sase_final` + a link obligation | zero static; per-turn friction | high, but on the critical path | new obligation kind is a `sase-core` change; adds a step to the most protocol-heavy moment of every turn | **No** |
| File hook on sidecar commit | **zero** | event-driven, exact | needs a `--cause` exclusion to avoid self-triggering | **Yes, for reactive repair** |
| Lumberjack `housekeeping` chop | **zero** | bulk, retroactive | hourly latency | **Yes, for backfill** |

Two of these deserve emphasis because they are existing, proven SASE mechanisms that cost
nothing at all:

**File hooks.** `sase file-hook` runs configured commands against sidecar commits with
path globs and producer-cause filters. `research-highlights` already does exactly this in
production: a research report lands, a command runs, an artifact is produced. A hook on
the plans and research sidecars that runs the derivation pass (with cause `artifact_links`
excluded so the projection commit does not re-trigger it) gives exact-moment derivation
with zero agent involvement.

**Chops.** `default_config.yml` defines a `housekeeping` lumberjack bucket at a 3,600s
interval, documented as the home for "durable maintenance that may scan substantial local
state." A `sase_chop_artifact_link_backfill` chop is the natural owner of the retroactive
sweep and the dangling-ref repair.

**The judgment tier goes to a batch curator, never to a working agent.** Add
`sase artifact link suggest`, which proposes candidate edges with evidence (shared beads,
shared epic, overlapping read sets, filename lineage) and writes nothing. Then either
surface a batched digest through a notification gate for the owner to accept in one pass,
or hand it to one small weekly curator agent whose entire job is that list. Either way the
cost is bounded and paid once, not spread across 800 runs a day.

---

## 8. Recommended solution

**Phase 0 — stop the leak (prerequisite, `sase-t0`).**
Make `_record_read_link` persist like `link_add` does: call
`persist_artifact_link_graph_mutation` so read rows are committed to the sidecar rather
than left in an ephemeral workspace clone (§2.1). File it as a `bug` task bead. Add a
doctor counter comparing `recorded_link: true` events against durable rows so the leak
cannot silently return. Without this, everything below leaks at 45%.

**Phase 1 — both endpoints (`sase-t1`), and rename following.**
Make `_upsert_bead` fire for a bead in either position, storing the registry inverse when
the bead is the target (§2.5), and backfill the endpoint events the current one-sided
writes never produced.
Consume git rename detection in the link refresh pass; rewrite refs and move the
`links/<path>.json` companion (§2.2, §4.4). Repair the 7 dangling research refs. This is
independent of Phase 0 and can run in parallel.

**Phase 2 — derive the mechanical edges.**
One derivation module, called from three places: (a) `sase plan propose` and
`sase artifact create` at creation time; (b) a file hook on the plans and research
sidecars for anything that lands another way; (c) `sase_chop_artifact_link_backfill` in
the hourly `housekeeping` bucket for the retroactive sweep and ongoing repair. Derive, in
order of value: `plan implements bead` (589), swarm `derives-from` (108),
`derives-from` from the turn's read log (§5.1), `plan ← cites ← agent` from the `PROMPT`
header (3,065, gated on §6.1 landing). Hold `AGENTS` / `COMMITS` promotion until there is
a consumer.

**Phase 3 — run the backfills.**
`sase artifact link migrate-notes --apply` (~290 edges, §2.3) and the prose-path `cites`
resolver on the publication path (~437 edges, §5.2).

**Phase 4 — make it pay.**
In priority order: print the neighborhood in `sase artifact read` (§6.2), give `agent:`
refs a real target (§6.1), expand one hop in launch context (§6.3), add derived-coverage
counters to doctor (§6.4).

**Phase 5 — the judgment tier.**
`sase artifact link suggest` plus a batched gate or a weekly curator agent (§7). Only
after Phases 2–4, because a suggester with no derived baseline will mostly re-propose
edges the derivation should have produced.

**The only agent-facing text this adds** is one line in `/sase_plan` and one line in the
`#research_swarm` lead step — both already-loaded contexts, read only by the agents that
produce linkable artifacts, and both stating a *fact* ("SASE derives your plan's links
from the artifacts you read this turn; use `sase artifact read` for context you actually
used") rather than adding an obligation. Nothing is added to `AGENTS.md`. Nothing is
added to `/sase_final`.

### Projected outcome

| Source | Edges | Agent instruction added |
| --- | ---: | --- |
| Today | 137 | — |
| `plan implements bead` | +589 | none |
| Swarm `derives-from` | +108 | none |
| `RELATED:` migration | +290 | none |
| Prose-path `cites` | +437 | none |
| Read-log `derives-from` | ~+150/mo | none |
| Read rows retained instead of lost | +62 | none |
| **Total** | **~1,770** | **none** |

A 13× graph, entirely from data SASE already owns.

---

## 9. What I would not do

- **Do not add a linking obligation to `AGENTS.md`.** §1.4 and §3 are the argument; the
  experiment has run.
- **Do not add a link step to `/sase_final`.** It is the correct *mechanism* — a
  host-computed obligation costs nothing when it does not fire — but it puts a judgment
  task at the moment an agent is closing out, which is where checklist-compliance behavior
  is worst, and it needs a new obligation kind in `sase-core`. Derivation gets the same
  edges without asking.
- **Do not widen the relation registry yet.** Six slugs with two of them at zero usage is
  not a vocabulary problem. Revisit only after the derived graph shows what is actually
  missing.
- **Do not promote `AGENTS` / `COMMITS` plan-header edges in the first pass.** ~2,300
  additional edges with no consumer would bury the deliberate ones in every rendered Links
  block.
- **Do not build a fuzzy topical suggester.** `sase artifact link suggest` should propose
  only from hard evidence (shared bead, shared epic, overlapping read sets, filename
  lineage). A semantic-similarity suggester generates plausible `related` edges at a rate
  no human will audit, and unaudited `related` edges are worse than no edges — they make
  the graph untrustworthy exactly where its only value is trust.

---

## Open questions for the owner

1. **`reference_added` vs `link_added` on beads (§2.4).** Should `sase artifact create
   --bead` start writing a typed link, with `reference_added` retained as a legacy alias?
   That consolidation is cheap now (68 + 26 rows) and expensive later.
2. **Agents pane.** 57% of the graph points at it. Is it worth scheduling now, or should
   `agent:` edges stay write-only until the Agents sub-tab has its own reason to exist?
3. **Read-log derivation scope.** Should `plan derives-from <everything read this turn>`
   include *every* read, or only reads of `plan:` and `research:` artifacts? Every read is
   more faithful; filtered is more legible. Recommend filtered for the first pass, with
   the full set recoverable from the read log regardless.
