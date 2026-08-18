---
create_time: 2026-08-18
updated_time: 2026-08-18
status: research
tags:
  - artifacts
  - artifact-refs
  - linking
  - beads
  - cli
  - glossary
---

# The Artifact Link Graph

**Research question.** How should SASE add first-class artifact→artifact links — an
"artifact markdown file" for every artifact, a rendered link table with GitHub
hyperlinks, `sase artifact link` with a required relation and description, migration of
the `RELATED:` bead-note convention, automatic links from prompt refs and from a new
`sase artifact read` — given what the just-closed `sase-js` ref contract already
provides, and without painting the future Agents sub-tab into a corner?

**Method.** Consolidation of two independent research passes
([`__a`](artifact_link_graph__a.md), grok-4.6; [`__b`](artifact_link_graph__b.md),
claude/opus) plus a third verification pass by the lead. Every number and code claim
below was re-measured against the live tree on 2026-08-18: `sase` at `4c5c06278`,
`sase-core` opened via `sase repo open`, the `plans` / `beads` / `research` / `agents`
sidecars, the live artifact store, and the live bead store. Where the two source reports
disagreed, the tie is broken by measurement, and the measurement is shown.

---

## Bottom line

Both source reports converge on the same object — a directed edge
`(from, to, relation, description)`, host-owned, with the Markdown table as a
*projection* — and they are right. They disagree about where the truth lives and how
much new machinery this needs. Three verified facts settle both disagreements, and one
of them is a blocker that neither report found:

1. **`.sase/` is in `.git/info/exclude` in every sidecar clone.** The structured
   `.sase/referenced-by/<provider>/<path>.json` index that `docs/artifact_references.md`
   calls the durable record has **never been committed anywhere** and does not exist in
   any sidecar. Report `__b`'s central premise — "the per-repo JSON index is truth and
   it is already paid for" — is currently false in practice. This is a live defect in
   landed code and a **phase-0 blocker** for any design that stores link truth there.

2. **`render_referenced_by_block` is already column-generic.** Columns are data
   (`key` / `label` / `numeric`), rows are `BTreeMap<String,String>` plus per-cell
   `link_targets`. Only `START_MARKER`, `END_MARKER`, `HEADING`, and one line of
   bottom-concat in `upsert` are hardcoded. The requested "nice table" is a
   **parameterization of ~50 lines**, not the new module `__b` scopes or the verbatim
   fork `__a` scopes.

3. **There are exactly 4 rendered `Referenced By` blocks and ~9 recorded use rows in
   the entire project.** The row schema can be changed today at zero migration cost.
   This is the cheapest moment this decision will ever be available, and it is a
   decisive argument for *one* row schema rather than `__a`'s two parallel ledgers.

**The recommendation.** One link graph, one row schema, three layers, stated explicitly
so nobody confuses them:

| Layer | What it is | Where |
| --- | --- | --- |
| **Truth** | committed, per-artifact, in the repo that owns the artifact — **and for beads, the bead event stream** | tracked sidecar path (not `.sase/`); `link_added` / `link_removed` bead events |
| **Read model** | one project-local aggregate index, rebuildable from truth | `~/.sase/projects/<key>/artifact-links.json` |
| **Projection** | the managed Markdown table, never parsed back for state | `<!-- sase:links:start -->` at the top; `Referenced By` stays at the bottom |

`links:` frontmatter is an **authoring inlet** that the refresh pass ingests and
normalizes away — not the source of truth. Three independent reasons, all verified in
§3.1.

---

## 1. Ground truth (re-measured)

### 1.1 What `sase-js` actually landed

Epic `sase-js` closed 2026-08-12; phase `sase-js.6` shipped reference links and
`Referenced By`. Verified in `sase-core`:

- `crates/sase_core/src/referenced_by.rs` — **659 lines**. Markers
  `<!-- sase:referenced-by:start -->` / `:end`, heading `## Referenced By`, deterministic
  row sort, `MAX_RENDERED_REFERENCED_BY_ROWS = 50` with an `_… and N more_` line,
  idempotent upsert, tolerant parse with marker recovery, and numbered link definitions
  allocated through the shared `markdown_link_refs.rs` (464 lines) so the block never
  renumbers the document's own reference links. Its module doc says, verbatim, that it
  mirrors `plan/artifact_link.rs` "but anchored at the bottom of the document instead of
  the top, since citations are appended as they accumulate rather than declared up
  front."
- `crates/sase_core/src/plan/artifact_link.rs` — **2062 lines**, the top-anchored plan
  header block (`PLAN · PROMPT · PARENT · BEAD · AGENTS · ARTIFACTS · COMMITS`), schema
  v3, frontmatter-aware, with a `header-invalid` validator every plan gate runs.
- `provider_spec.rs` validates `publication.referenced_by ∈ {markdown_table, none}` —
  a ready-made extension point for provider opt-in.
- One hash-strip call site: `src/sase/core/prompt_artifact_staging.py:424` calls
  `referenced_by_block_strip` before digesting a clean `.md`/`.markdown` VCS-backed
  prompt artifact. Both reports describe this as a general invariant; it is narrower
  than that. The principle stands, the blast radius is one function.

### 1.2 The index that was never committed

`src/sase/sdd/referenced_by_refresh.py:203-205` writes the index and appends it to
`changed_paths`, which `commit_sdd_store_files` then commits. But:

```
$ cat sase/repos/{plans,research,beads}/.git/info/exclude
.sase/
/sase/repos/
```

`.sase/` is excluded in **every** sidecar clone (plans, research, beads, agents),
written by SASE's own `src/sase/workspace_provider/git_exclude.py`. The global
`~/.gitignore_global:52` also carries `.sase/*`. The one real projection commit in the
plans sidecar confirms it:

```
$ git -C sase/repos/plans show --stat 39d94718
    Update Referenced By projections
 202608/monitor_followup_wait_release.md | 12 ++++++++++++
 1 file changed, 12 insertions(+)
```

Twelve lines of Markdown, no index. `find` turns up zero
`.sase/referenced-by/**/*.json` anywhere on this machine. The commit path reports
`commit-failed` only when *no* commit is created, so the missing index is silent.
Bead `sase-ka`'s close reason corroborates it from the other side: referenced-by
write-back "works from the local manifest." Local is the whole problem.

**Consequences.** (a) Today the only durable, shared record of a citation is the
rendered Markdown table, which means SASE *is* reverse-engineering state from Markdown
via `parse_referenced_by_block` — exactly what the design said it would not do. (b) Any
link design that puts truth under `.sase/` inherits report `__b`'s own hazard #6
(machine-local state) as its foundation. (c) `docs/artifact_references.md` §Publication
documents behavior that does not happen. This is worth a `bug` bead independent of
whether the linking feature ships.

**Fix, one of:** narrow `git_exclude` so artifact sidecars do not exclude `.sase/`, or
move the index to a tracked path (`links/` or `.artifact-links/`). Either way it is
**phase 0**, before any link row is written.

### 1.3 Scale, and what is actually linkable

`sase artifact stats`, live:

```
Rows 10,300 · 1.3 GiB      Explicit 802 / 32.8 MiB      Automatic 9,498 / 1.3 GiB
By kind: image 9,494 · markdown 752 · file 54
Window 44 days · 234.1 rows/day · 30.4 MiB/day
```

Plus 3,903 beads, 8,581 agent directories, 565 bead page lineages.

Report `__b` uses these numbers to reject a companion `.md` per artifact, and is right.
The sharper framing neither report used: the store *already* separates **explicit (802)**
from **automatic (9,498)**, and the automatic population is precisely what
`sase artifact prune` exists to trash. The artifacts a human would ever deliberately
link are ~800 files plus beads, plans, research, and agents. Materializing 9,494
companion files for screenshots would create a permanent commit-rate tax on rows
designed to be deleted, and each deletion would then dangle.

### 1.4 Citation volume is currently negligible

Four rendered `Referenced By` blocks exist in the whole project:

```
sase/repos/plans/202608/monitor_followup_wait_release.md
sase/repos/plans/202608/artifact_ref_contract.md
sase/repos/research/202608/ref_provider_contract/ref_provider_contract.md
sase/repos/research/202608/ref_provider_contract/ref_provider_contract__a.md
```

`~/.sase/artifacts/consumption.jsonl` has 8 rows; all `ref-uses.jsonl` files together
have 9. Both source reports treat "link spam" as a live hazard; it is **hypothetical
today**. The population that will actually generate volume is `sase artifact read`, once
agents are told to prefer it — and that is a design input, not a discovered constraint.
The upside is large: the row schema is free to change right now.

### 1.5 The `RELATED:` corpus — corrected

Report `__a` says 279 notes / 150 beads; `__b` says 272 with 92.6% parseable and 26
multi-bead. Measured directly against `sase/repos/beads/issues.jsonl`, splitting each
note at the first spaced em/en dash:

| Measure | Count | Share |
| --- | ---: | ---: |
| `RELATED:` occurrences | **261** | 100% |
| Beads carrying at least one | **146** | — |
| Head names exactly one bead id | **240** | 92.0% |
| Head names more than one bead (fan-out) | **18** | 6.9% |
| Head names no bead id (manual worklist) | **3** | 1.1% |
| Head id **and** a non-empty rationale | **248** | 95.0% |
| Note names a commit rather than a bead | **28** | — |
| **Edges the migration would generate** | **292** | — |

`__b`'s conclusion holds: this is a tractable, ~92%-mechanical, one-shot migration
producing ~292 edges with a ~5% manual worklist. Expect drift; re-measure at
implementation time.

Two structural facts that matter for the migration design:

- **Bead notes are append-only events.** The event store records `note_appended` 4,150
  times and projects them into the issue's concatenated `notes` string. `__a`'s "do not
  delete the note" is therefore not just good manners; the store has no delete.
- **The bead event vocabulary already has `reference_added` (52) and
  `reference_removed` (8).** `link_added` / `link_removed` is a precedented extension,
  not a new concept — which is the strongest argument for keeping bead link truth in the
  bead store.

### 1.6 The audited-read family, and the rule it breaks

`sase memory read`, `sase glossary read`, and `sase repo open` all implement
"print content, record who read it and why," sharing the `repo_open_log.py` house
pattern: frozen event dataclass, `discover_agent_identity`, `locked_file(LOCK_EX)`,
JSONL append, `schema_version`. `sase glossary read` refuses to print unless the read was
recorded; `sase memory read` strips frontmatter before printing.

All three use a **required `-r/--reason` option**. `sase/memory/cli_rules.md:11-12` says:

> Options must not be required. A value that is required for the command to execute
> belongs in a positional argument; options represent optional controls or modifiers.

`sase flag new` also requires three options. So this is the project's most-violated CLI
rule, in at least four commands. `__a` says follow the siblings; `__b` raises it as an
open question. See §4.1 for the resolution.

### 1.7 Glossary and pane facts

- **There is no `Artifact` glossary term.** Only `Artifact Reference` (alias `ref`).
  `__a` caught this; `__b` did not. The requested "artifact markdown file" term will be
  unanchored unless the parent term lands with it.
- **The ACE relation graph is real and declarative.** `sase artifact pane show beads`
  prints four relations with `kind ∈ {hierarchy, family, link}`, `source`, `target_pane`,
  `inverse`, and `directed` / `transitive` flags. Sources live in
  `src/sase/ace/tui/relations/{beads,documents,files,patches,stitches,provider}.py` and
  are **pure snapshot→edge projections with no I/O**. One new relation source plus a
  `links` / `linked_by` declaration per pane earns the relation rail and `<` / `>` / `~`
  navigation for free — including on the future Agents sub-tab.
- **`sase/memory/tui_perf.md` rule 1: never block the event loop — no synchronous disk
  I/O or JSON parsing.** This is a hard constraint on the read model (§3.2) that neither
  source report connected to the storage decision.

---

## 2. Six existing surfaces, and why none of them is this feature

Condensed from `__a` §2, all re-verified. Each already has a job; none should be
stretched.

| Surface | What it answers | Why it is not this |
| --- | --- | --- |
| Bead `refs` (`sase bead ref add`) | "this bead cites that artifact" | no relation, no description |
| `RELATED:` notes | "this bead relates to that one, because…" | free text, no schema, no index, no inverse, no URL |
| Plan header `ARTIFACTS`/`AGENTS`/`COMMITS` | SDD provenance for one plan | closed section set + `header-invalid` validator; a general link table is a different block |
| `Referenced By` | "who cited me, when, how often" | citation-shaped columns, bottom-anchored, no relation or why — **but see §3.3: it is the right substrate, generalized** |
| ACE relation panel | presentation index over declared properties | derives edges; stores none; no CLI, no write path |
| Prompt-ref use rows / `consumption.jsonl` | citation counting | records the use, not the described edge |

The hole is precise: `sase artifact path` / `show` / `open` resolve an artifact and
leave **no durable trace**. An agent that runs `sase artifact path research:…` and then
reads the file is invisible. That is what `sase artifact read` fills.

---

## 3. The design

### 3.1 `links:` frontmatter is an inlet, not the truth

This is the sharpest conflict: `__a` makes frontmatter the authored store for Markdown
documents; `__b` makes it an inlet the refresh pass normalizes away. **`__b` is right**,
for three independently verified reasons:

1. **It breaks the digest strip.** `prompt_artifact_staging.py:424` strips only the
   managed block. A `links:` key in frontmatter is inside the hashed region, so every
   inbound link would register as a semantic edit of the target document — the exact
   feedback loop `referenced_by_block_strip` was written to prevent.
2. **The key is already taken.** Ten-plus files under `docs/blog/posts/*.md` carry a
   `links:` frontmatter list in the mkdocs-material related-links shape
   (`- Label: path`), which does not parse as `{ref, relation, description}`. `__a`
   noticed this and proposed a path guard; a guard on a key that already means something
   else in the same repo is a smell, not a mitigation.
3. **SASE already decided this once.** The prior research report
   [`sase_sites_hub_and_pages`](../../202607/sase_sites_hub_and_pages/sase_sites_hub_and_pages__b.md)
   §7.1 models the unified artifact record with
   `links: [...]  # DERIVED, read-only, never authored (Backstage relations)`. Neither
   source report cited it. That is a third independent vote.

Keep the ergonomics `__a` wants without the coupling: a hand-written `links:` list is
**read** by the refresh pass, folded into the index, and normalized out of the
frontmatter into the rendered block. Hand-authoring works; hand-authored state does not
survive as a second truth. The `markdown_frontmatter` property source already exists in
the provider spec, so the reader is not new machinery.

### 3.2 Three layers, named

`__a` argues kind-native stores; `__b` argues one per-repo JSON index. Each is half
right, and §1.2 disqualifies `__b`'s chosen location outright.

**Truth — committed, in the repo that owns the artifact.**

- **Beads: the bead event stream.** `link_added` / `link_removed` beside the existing
  `reference_added` / `reference_removed`, written through the existing bead mutation
  path (lock → commit → page refresh), with a projected `links` field beside `refs`.
  `__a` is right that anything else creates two truths for one object and leaves
  `sase bead show` blind. Bead pages are regenerated; a link written into a page is gone
  on the next refresh.
- **Everything else: a tracked per-artifact JSON file in the owning sidecar**, at a path
  that is *not* `.sase/` until §1.2 is fixed. Holds every row touching that artifact,
  both directions, so one read answers "show me this artifact's links."
- **Agents:** rows whose `from` is an agent land in the agent's publication metadata
  next to the existing ref-uses payload. Note that bead `sase-ka`, which scoped
  `agents/<agent>/ref-uses.json` under a v2 publication contract, was **closed as
  canceled** on 2026-08-12 in an owner-requested backlog cut — so this plumbing is
  deferred, not queued, and this feature must either carry it or stay off it.
  (Report `__a` cites `sase-ka` as pending; it is not.)

**Read model — one project-local aggregate index.**
`~/.sase/projects/<key>/artifact-links.json`, rebuildable from truth, is what `sase
artifact link list`, the ACE snapshot, and the future Agents sub-tab actually read.
This layer is not optional and neither report scoped it: `tui_perf.md` forbids
synchronous disk I/O and JSON parsing on the event loop, and the relation sources in
`ace/tui/relations/` are pure snapshot projections with no I/O. Scanning per-artifact
JSON across four sidecars at snapshot time violates both. `__a` rejects a central index
as *truth* — correctly — but then leaves incoming-link queries requiring a global scan.
A rebuildable cache is not a second truth.

**Projection — the Markdown table.** Never parsed back for state. §3.3.

### 3.3 One row schema, two blocks, and a much smaller renderer

`__a` keeps `Referenced By` as a separate citation ledger *and* writes `cited` link
edges — storing every citation twice. `__b` unifies: one row schema with an `origin`
discriminator, routed to two rendered blocks. **`__b` is right**, and §1.4 makes it
nearly free: 4 blocks and 9 use rows is the entire migration cost. Adopt:

```json
{
  "schema_version": 1,
  "source_ref": "research:202608/artifact_link_graph/artifact_link_graph.md",
  "relation": "implements",
  "target_ref": "bead:sase-js",
  "description": "extends the ref contract this epic landed",
  "origin": "manual",
  "created_by": "bbugyi200.athena.y2",
  "created_at": "2026-08-18T23:40:00Z",
  "uses": 1
}
```

`origin ∈ {manual, migrated, prompt_ref, read, derived}`. Dedup key
`(source_ref, relation, target_ref)`; a rewrite updates the description; self-links
rejected; the same pair may carry several relations.

**Routing: by curation, not direction.** Top `## Links` renders `manual` + `migrated`
rows in both directions. Bottom `## Referenced By` keeps `prompt_ref` + `read`. The top
block closes with one line: `_Plus N automatic references — see [Referenced By](#referenced-by)._`
`__a`'s alternative — outgoing at top, an incoming sub-table below — splits on the axis
the user does not care about; the stated goal is seeing *why* two artifacts are linked,
and "which file you happened to open" is not that. Routing is one predicate; it can be
changed later without touching the model.

**Placement of the top block: after frontmatter, after the plan header block if one
exists, before the first ATX heading.** `__a` worked this out and `__b` did not specify
it. It matters: `plan/artifact_link.rs` already owns that region with a fixed section
order and a `header-invalid` validator that every plan gate runs.

**The renderer is a parameterization, not a module.** Neither report measured this.
`render_referenced_by_block` takes `columns: Vec<ReferencedByColumnWire{key,label,numeric}>`
and rows of `BTreeMap<String,String>` plus per-cell `link_targets`; sorting, the 50-row
cap, `omitted`, cell escaping, and label allocation are all column-agnostic. The only
hardcoded parts are three consts and this one line in `upsert`:

```rust
format!("{trimmed_body}\n\n{block}")   // ← the entire bottom-anchoring
```

Extract `ManagedTableBlock { start_marker, end_marker, heading, anchor }` and make
`Referenced By` (bottom) and `Links` (top) two instances. That is roughly 50 lines plus
a top-anchored placement function, against `__b`'s "new `sase_core::artifact_links`
module" and `__a`'s "copy `referenced_by.rs` almost verbatim."

Rendered shape (columns lead with the relation, because the relation is the reason):

```markdown
<!-- sase:links:start -->

## Links

| Relation   | Artifact                              | Why                                       |
| ---------- | ------------------------------------- | ----------------------------------------- |
| implements | [bead:sase-js][1]                     | extends the ref contract this epic landed |
| supersedes | [research:202608/ref_provider_…][2]   | replaces its §7–§9 write-back design      |

_Plus 12 automatic references — see [Referenced By](#referenced-by)._

[1]: https://github.com/sase-org/sase--beads/blob/main/pages/sase-js/README.md
[2]: https://github.com/sase-org/sase--research/blob/<sha>/202608/ref_provider_contract/…

<!-- sase:links:end -->
```

URLs come from the existing `HostedLinkResolver` (`src/sase/sdd/hosted_links.py`), which
already builds GitHub URLs for plans, beads, agents, commits, and sidecar blobs and
degrades to an unlinked label. Do not build a second resolver. Extend the strip at
`prompt_artifact_staging.py:424` to both marker pairs, and use a non-user file-hook cause
`artifact_links` alongside `referenced_by`.

### 3.4 The artifact md file: addressing total, materialization lazy

Adopt `__b`'s D1(b). Define `artifact_md_path(ref) → path` for every kind; create the
file the first time the artifact acquires a link.

| Kind | Artifact md file | Status |
| --- | --- | --- |
| markdown document (`plan:`, `research:`, other document kinds) | itself | exists |
| `bead:` | `pages/<lineage>/README.md` (epic) or `<id>.md` (phase) — projection; truth is the event stream | exists |
| `agent:` | `agents/<name>/README.md` / `families/<name>.md` — projection | exists |
| `patch:` | the published Patch page | exists |
| `file:` markdown | the file itself | exists |
| `file:` binary (png, pdf, …) | sibling `<stem>.md` — `diagram.png` → `diagram.md` | **new** |
| `stitch:` | **none** — SASE does not own a commit; links render on the peer | documented exception |

Two disciplines from `__a`, both worth keeping:

- **Companion naming uses the stem, not the basename** (`diagram.md`, not
  `diagram.png.md`). On collision with an existing first-class document, refuse and fall
  back to the disambiguated `diagram.png.md`. Never silently overwrite a research report.
- **Exclude companions from document inventory.** The research provider's inventory glob
  is `20*/**/*.md`; without an exclusion, `foo_infographic.md` becomes a listed research
  report. Fix this before the first binary companion is created.

Unpublished `file:` artifacts under `~/.sase/artifacts/` have no git home and no
permalink. Their links are local-only until publication. Say so in the glossary entry
rather than fabricating a `main` URL — the landed design already refuses to do that.

### 3.5 Relations: a registry, not an enum and not free text

`__a` proposes closed slugs plus a free-slug escape hatch; `__b` proposes a
task-type-shaped registry (builtins + plugins + config, snapshotted to JSON, rendered
into `AGENTS.md`). **Take `__b`'s shape and `__a`'s restraint**: the task-type precedent
is exactly the mechanism that makes agents use the right slug, because the snapshot lands
in the always-loaded instruction file. But ship **no free-slug escape hatch in v1** — an
escape hatch fragments the vocabulary on day one, and the registry is the principled way
to extend.

| Slug | Inverse | Directed | Written by |
| --- | --- | --- | --- |
| `cites` | `cited-by` | yes | prompt-ref expansion (`origin: prompt_ref`) |
| `read` | `read-by` | yes | `sase artifact read` (`origin: read`) |
| `related` | `related` | no | CLI; the `RELATED:` migration |
| `supersedes` | `superseded-by` | yes | CLI |
| `implements` | `implemented-by` | yes | CLI |
| `derives-from` | `derived-into` | yes | CLI |

Snapshot to `sase/artifact_relations.json`, regenerated by `sase memory init`, rendered
as an `AGENTS.md` section.

**Reserve `blocks` and `depends-on`.** Both reports agree and both are right:
`sase bead dep` already models blocking, affects readiness and scheduling, and is
declared on the beads pane. `sase artifact link add` must **error** on those slugs with
a pointer to `sase bead dep`, or a second scheduling truth appears.

`__b`'s treatment of `duplicates` is worth dropping entirely: `sase bead +1` already
models corroboration, and `/sase_new_task` routes duplicates there.

**Descriptions on machine rows.** The user's requirement is that every link says why.
`__a` satisfies it with a constant string ("Cited in launch prompt"), which is not a why.
`__b`'s approach is right: `ArtifactRefUseRecord` already captures `prompt_text`, so
synthesize a bounded excerpt (or the xprompt / bead title when available). The invariant
then holds uniformly without demanding a reason from a code path that has no human in it.

---

## 4. CLI

### 4.1 Shape, and the required-option question

`sase artifact` currently exposes `create doctor list open pane path prune reclaim show
stats trash`, and bare `sase artifact` defaults to `list` via
`_default_list_subcommands` (`src/sase/main/parser.py:543`). Alphabetical insertion puts
`link` between `doctor` and `list`, and `read` between `prune` and `reclaim`.

Because `link` is a group with an exact `list` child, bare `sase artifact link` will
delegate to `list` under the central convention. So linking needs its own verb:

```text
sase artifact link add  <source-ref> <relation> <target-ref> <why>
sase artifact link add  <relation> <target-ref> <why>        # source = current agent
sase artifact link list <ref> [-d in|out|both] [-j] [-R <relation>]
sase artifact link rm   <source-ref> <relation> <target-ref>

sase artifact read <ref> <reason> [-f {json,markdown,rich}] [-n LINES]
```

**Recommendation: positional reason, not `-r/--reason`.** `__a` says follow
`sase memory read`'s required `-r`; `__b` raises it as an open question. Take the
positional: `cli_rules.md:11-12` forbids required options, the rule is already violated
in four commands, and adding a fifth entrenches drift that is cheaper to stop than to
unwind. `sase artifact link add bead:sase-m4 related bead:sase-ct "shares the ACE-TUI
flake root cause"` reads as subject–verb–object–why, which is the argument order the
required-relation requirement wants anyway. Settle the sibling inconsistency separately:
either carve out audited reads in `cli_rules.md` or file a bead to convert
`memory read` / `glossary read`. **Do not let it block this feature.**

Other CLI details: `-j/--json` on `list`; idempotent `add` prints "unchanged" and exits
0; `rm` without a relation removes every edge between the pair and says so; refs
canonicalize through the existing path, with or without a leading `@`; default `source`
is the current agent, and its absence outside an agent run is an error.

### 4.2 `sase artifact read`

Behavior, in order:

1. Require a non-empty reason.
2. Resolve through the same path as `show` / `path`, so every kind and every
   `#L10-20` / `#page=2` / `#t=` fragment works on day one, including VCS-backed
   materialization.
3. **Strip leading frontmatter and both managed blocks before printing.** Otherwise
   every read prints the link table it just contributed to and the context window pays
   for it. `sase memory read` already strips frontmatter; this is the same call.
4. Print. Text to stdout, paged when a TTY, raw when piped — agents need the bytes.
   Images, PDFs, and video print a metadata block plus a pointer to `sase artifact open`
   and still record the read. `stitch:` prints the `show` payload plus the commit
   subject rather than claiming there is nothing to read.
5. Append an audited row (`~/.sase/projects/<key>/artifact_reads.jsonl`, `repo_open_log`
   house pattern) and a consumption event, so `show` and `list --unused` stay honest.
6. Write the link: `from = current agent`, `to = <ref>`, `relation = read`,
   `description = <reason>`, `origin = read`.
7. Refuse to print if the read could not be recorded, matching `sase glossary read`.

**Only `read` links.** `show`, `path`, and `open` stay silent. `path` is the composition
primitive — exactly one absolute path on stdout, called from scripts and from other SASE
code — and linking from it would manufacture noise from every internal resolution. This
is the same split that makes `sase memory show` silent while `sase memory read` records.

`sase repo open` keeps its job: **modifying** files in a sidecar / linked / external
repo, or **broad exploration** of a repo's artifacts as a tree. `read` is "give me this
one artifact and remember that I used it."

### 4.3 The `RELATED:` migration

One command, dry-run by default: `sase artifact link migrate-notes [--apply]`.

1. Scan bead notes for `^RELATED:\s*<bead-id>(\s*,\s*<bead-id>)*\s*[—–]\s*<why>$`.
2. Emit one `related` edge per named target with `origin: migrated`, fanning out the
   18 multi-target notes (§1.5) with the shared rationale.
3. Route the 28 notes naming a commit to `stitch:<repo>@<sha>` rather than a bead.
4. **Leave the note text in place** — the event store is append-only (`note_appended`)
   and `sase bead history --lost-notes` depends on it. Append one
   `MIGRATED: linked as related/<id>` note per converted row.
5. Report the ~5% that do not parse as a manual worklist, not a guess.

Then update `/sase_new_task` at both call sites — `src/sase/xprompts/skills/sase_new_task.md:58`
(retired umbrella) and `:139` (related-but-not-duplicate) — to emit
`sase artifact link add`. That edit and the `/sase_artifact_file` and `/sase_repo`
updates are memory-file changes requiring **explicit user permission in the
conversation**, followed by a mandatory `sase memory init`.

---

## 5. Automatic writers, the Rust boundary, and the TUI

**Prompt refs.** The pipeline exists; this is the smallest change of the set. In
`agents_sync/prompt_archive/publish.py`, `enqueue_referenced_by_request` becomes
`enqueue_artifact_link_request` carrying `relation: cites`, `origin: prompt_ref`, and a
synthesized description; the drain writes into the generalized index; `Referenced By`
renders from `origin ∈ {prompt_ref, read}` rows. Idempotent across retries and
`%repeat`. Pointer kinds still create the edge — the target needs no local checkout.
Keep the prior report's lock order: **artifact repos first, `agents` last.**

**Rust / Python split**, per `rust_core_backend_boundary`. In `sase-core`: the link row
and index wire types; the relation registry with inverse derivation and validation; the
`ManagedTableBlock` primitive and both instances; `artifact_md_path` resolution;
companion naming; bead `link_added` / `link_removed` events and the projected field;
the tolerant frontmatter-`links:` reader. In `sase`: CLI parsers and handlers; the
outbox drain and sidecar commit; the aggregate read-model builder; bead- and agent-page
renderers; the ACE relation source; skill and doc updates; the research-plugin inventory
exclusion.

**TUI.** Out of scope to build the Agents sub-tab; in scope not to preclude it. One new
relation source in `src/sase/ace/tui/relations/` reading the aggregate index, plus a
`links` / `linked_by` declaration on every pane contract, earns the relation rail,
`<` / `>` / `~` navigation, and cross-pane reveal-lens jumps unchanged. Because prompt
refs and reads write `from = agent:<name>` edges from day one, the Agents sub-tab lights
up with real data when it ships instead of needing a backfill. Load the aggregate index
off-thread (`tui_perf.md` rule 1).

---

## 6. Phase plan

Flag first: `sase flag new artifact_links -k beta`. Note two corrections to `__a` here —
flag kinds are **`beta` | `sunset`; there is no `wip`**, and keys are snake_case.
Disabled: parsers exist and report disabled, no sidecar writes, no bead events, no
prompt-ref edges. Both states tested from phase 1.

| # | Phase | Repo | Scope |
| --- | --- | --- | --- |
| **0** | **unblock** | `sase` | Fix §1.2 — stop excluding the index path from sidecar commits (narrow `git_exclude`, or move off `.sase/`). Backfill the 4 existing blocks into a committed index. File the `bug` bead. **Everything else depends on this.** |
| 1 | core | `sase-core` | Link row + index wire types; relation registry with inverses; extract `ManagedTableBlock` and re-express `Referenced By` through it; add the top-anchored `Links` instance; `artifact_md_path`; companion naming. No behavior change in `sase`. |
| 2 | store | `sase` | Python adapter; per-artifact truth read/write; aggregate read model; audited log; feature flag. |
| 3 | cli | `sase` | `sase artifact link add\|list\|rm`; `sase artifact read`; `sase artifact doctor` checks for dangling rows, stale tables, and missing companions; retention protection for link targets. |
| 4 | render | `sase` | Top `## Links` block; generalized refresh + outbox writing both blocks; `artifact_links` file-hook cause; extend the hash strip to both marker pairs. |
| 5 | beads | `sase` + `sase-core` | `link_added` / `link_removed` events, projected field, bead-page table, `migrate-notes` dry-run/apply. |
| 6 | refs | `sase` | Prompt publication emits `cites` rows; `Referenced By` renders from the shared index; agent pages render outbound links. |
| 7 | ace | `sase` | One relation source; `links` / `linked_by` on every pane contract. |
| 8 | adopt | `sase` | Glossary **Artifact** and **Artifact Markdown File**; `docs/artifact_links.md`; research-plugin companion exclusion; `/sase_new_task`, `/sase_artifact_file`, `/sase_repo` updates; `sase memory init`. |

`0 → 1 → 2 → 3 → 4` is the critical path. Phases 5, 6, 7 are independent once 4 lands.

---

## 7. Hazards

| # | Hazard | Mitigation |
| --- | --- | --- |
| 1 | **Index silently uncommitted** (§1.2) — the design's durable layer does not survive a fresh clone | Phase 0. Add a doctor check that fails when a link row exists in the working tree but not in `HEAD`. |
| 2 | **Hash feedback loop** — a link that looks like a document edit | Index is truth; extend the strip at `prompt_artifact_staging.py:424` to both marker pairs; never put links in hashed frontmatter |
| 3 | **Dangling links after retention** — `prune` trashes rows and **`reclaim` changes a row's ID**, because VCS-backed ids derive from VCS identity | Add the link store to the lifecycle protection collector as consumed refs already are; make `reclaim` skip linked rows |
| 4 | **File explosion** — 9,494 automatic PNGs, +234/day | Lazy materialization (§3.4); companions only for linked binaries |
| 5 | **Two truths for bead relations** | Reserve `blocks` / `depends-on`; error with a pointer to `sase bead dep` |
| 6 | **Generated-page clobber** — bead/agent pages are regenerated | Page renderer is the only writer of those tables; truth is the event stream / publication metadata |
| 7 | **Document-inventory pollution** by companion `.md` files | Exclude companions from provider inventory globs before the first one is written |
| 8 | **File hooks firing on projection commits** | Non-user cause `artifact_links`, excluded by default, mirroring `referenced_by` |
| 9 | **TUI stall** from scanning per-artifact JSON at snapshot time | One aggregate index, loaded off-thread |
| 10 | **Outbox delay** — the graph write succeeds before GitHub shows the table | Document it; it is already true of `Referenced By` |
| 11 | **Unflagged user-reaching behavior** | `sase flag new artifact_links -k beta` before the first block renders |
| 12 | **Link spam once `read` is adopted** — hypothetical today (§1.4), not later | Curation routing (§3.3), 50-row cap with `omitted` on both blocks, dedup on `(source, relation, target)` |

**Non-goals.** The Agents sub-tab. Generated `stitch:` / `patch:` pages. Replacing bead
dependencies, plan-header `ARTIFACTS`, or citation counting. Deleting historical
`RELATED:` notes. Stored inverse edges — inverse is computed from the registry.

---

## 8. Glossary text

**Artifact** *(new parent term — does not exist today)*

> A SASE artifact is any durable record addressable by an artifact reference: a sidecar
> document such as a plan or a research report, a bead, a completed agent, a Patch, a
> stitch, or an indexed file. Every artifact has a canonical `<kind>:<argument>` identity
> and an artifact markdown file that carries its typed links.

**Artifact Markdown File** (aliases: `artifact md file`, `artifact md`)

> An artifact markdown file is the Markdown document that carries one artifact's typed
> links. A Markdown artifact is its own artifact md file. A non-Markdown file uses a
> sibling `<stem>.md`; beads, agents, and Patches use their generated page, which is a
> projection of the artifact's own store. A commit has none — links to a stitch render on
> the other artifact. The file is created the first time the artifact acquires a link.
> SASE renders those links as a table of hyperlinks near the top of the file. Agents
> write links with `sase artifact link` and read artifacts with `sase artifact read`;
> they never hand-edit a generated page.

---

## 9. Recommendation

Build **one artifact-link graph with one row schema, three named layers, and two
rendered blocks.**

- **Phase 0 is not optional.** `.sase/` is excluded from every sidecar commit, so the
  `Referenced By` index that `docs/artifact_references.md` describes has never existed on
  any remote. Fix that before storing link truth anywhere near it, and file the bug —
  it is a defect in already-landed code.
- **Generalize `Referenced By`; do not run a second ledger beside it.** Four rendered
  blocks and nine use rows exist project-wide. Add `relation`, `description`, and
  `origin` to the row now, while the migration cost is zero.
- **Truth is committed and kind-native** — bead events for beads, per-artifact JSON in
  the owning sidecar otherwise, agent publication metadata for agents. **The read model
  is one rebuildable project-local aggregate**, because `tui_perf.md` forbids scanning
  JSON on the event loop. **The Markdown table is a projection**, never parsed back.
- **`links:` frontmatter is an authoring inlet, normalized away.** It breaks the digest
  strip, the key already means something else in `docs/blog/posts/`, and prior SASE
  research already ruled `links` derived-and-never-authored.
- **The renderer is a parameterization**, not a new module: `render_referenced_by_block`
  is already column-generic; extract `ManagedTableBlock { markers, heading, anchor }` and
  instantiate it twice. Place the `Links` block after frontmatter and after any plan
  header, before the first heading.
- **Route by curation, not direction** — deliberate links at the top, automatic
  citations at the bottom, one pointer line between them. It is a single predicate,
  reversible later.
- **`sase artifact read <ref> <reason>`** is the tracked reader; its reason *is* the link
  description. Only `read` links; `show` / `path` / `open` stay silent. `sase repo open`
  keeps modification and broad exploration.
- **Relations are a task-type-shaped registry** snapshotted into `AGENTS.md`, six slugs
  to start, no free-slug escape hatch, `blocks` / `depends-on` reserved for
  `sase bead dep`.
- **Migrate the 261 `RELATED:` notes** into ~292 `related` edges (92% mechanical,
  ~5% manual worklist), leaving the append-only notes intact, then retire the recipe from
  `/sase_new_task`.
- **Treat `agent:<name>` as an ordinary node from day one.** Prompt-ref and read edges
  accumulate from phase 6, so the Agents sub-tab ships with real data instead of a
  backfill.
- Ship behind `sase flag new artifact_links -k beta`.

### Three things to decide before implementation

1. **Where the committed index lives.** Narrow `git_exclude` so artifact sidecars track
   `.sase/`, or move the index to a tracked directory. The first is smaller; the second
   is harder to regress.
2. **`cli_rules.md` and required reasons.** Positional (recommended, rule-compliant) or
   required `-r` (consistent with `memory read` / `glossary read`, rule-violating). A
   one-line carve-out for audited reads would settle all four commands at once.
3. **Whether beads keep link truth in the event stream** (recommended: yes, `link_added`
   sits naturally beside the existing `reference_added`) or move to the generic
   per-artifact index for uniformity, accepting that `sase bead show` then reads a second
   store.
