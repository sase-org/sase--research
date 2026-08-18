---
create_time: 2026-08-18
updated_time: 2026-08-18
status: research
---

# Linking Artifacts to Artifacts

**Research question:** how should SASE add first-class artifact→artifact links — a new
"artifact markdown file" concept, a rendered link table, a `sase artifact link` command
with required relations, automatic links from prompt refs and from a new
`sase artifact read` command, and a migration of the `RELATED:` bead-note convention —
given what the just-landed `sase-js` artifact-reference contract already provides?

**Method.** Direct reading of the current tree (`sase` at `4c5c06278`), the sibling
`sase-core` checkout, the four artifact sidecars (`plans`, `beads`, `research`,
`agents`), the live artifact store, the live bead store, and the prior research report
[`ref_provider_contract`](ref_provider_contract/ref_provider_contract.md), whose §7–§9
designed the machinery this feature must extend rather than duplicate.

---

## Bottom line

**Most of this feature already exists, pointed in the opposite direction.** The
`sase-js` epic (closed 2026-08-12) landed a durable, cross-repo, idempotent,
outbox-driven write-back that puts a `Referenced By` table into every cited artifact
document, backed by a structured `.sase/referenced-by/<provider>/<path>.json` index in
the artifact's own repo. That is an artifact→artifact link store with a rendered
Markdown projection. What it lacks is exactly the four things asked for: a **relation
vocabulary**, a **required description**, a **manual write path**, and **coverage of
artifacts that are not documents in an artifact repo**.

So the right shape is not a new subsystem. It is:

1. **Generalize `Referenced By` into `artifact links`** — same outbox, same per-repo
   JSON index, same Rust-owned managed-block renderer — by adding `relation` and
   `description` to the row and letting rows originate from more than prompt
   publication.
2. **Do not make the Markdown the source of truth.** Accept `links:` frontmatter as an
   *authoring inlet* that a refresh pass ingests, but keep the JSON index authoritative.
   The landed design deliberately made the table a projection so that being cited does
   not change a document's semantic version; a frontmatter source of truth reintroduces
   exactly that feedback loop.
3. **Do not materialize an `.md` file per artifact.** The store holds **10,299 rows,
   9,494 of them automatic PNG captures**, growing at ~234 rows/day. Define the artifact
   md file as a *total addressing function* (`ref → path`) that is *materialized lazily*
   when the artifact first acquires a link. Four of the seven artifact kinds already
   have a generated md file today; the concept should name them, not replace them.
4. **Split the rendered table by curation, not by direction.** A curated `## Links`
   table at the top; the existing high-volume automatic citations stay in the bottom
   `Referenced By` block with a one-line pointer from the top. Both are rows in one
   store with one relation vocabulary.
5. **`sase artifact read <ref> "<reason>"`** slots exactly into the existing audited-read
   family (`sase memory read`, `sase glossary read`, `sase repo open`), and its required
   reason *is* the required link description. That is the cleanest part of the proposal.

Sections 1–2 establish ground truth; §3 states the seven decisions; §4 lists the hazards
that will bite; §5 gives the recommended solution and a phase plan; §6 lists what needs
your decision.

---

## 1. What already exists (verified in the tree)

### 1.1 The `sase-js` epic landed six days ago

`sase bead show sase-js` reports **closed 2026-08-12** with all nine phases closed:

| Phase       | Delivered                                                     |
| ----------- | ------------------------------------------------------------- |
| `sase-js.1` | Ref contract wire types in `sase-core`                        |
| `sase-js.2` | Retired the ref xprompt surface                               |
| `sase-js.3` | Provider registry, plugin hooks, config                       |
| `sase-js.4` | Builtin refs and prompt ref context                           |
| `sase-js.5` | `@file` ref and the content-addressed store                   |
| `sase-js.6` | **Reference links and `Referenced By` write-back**             |
| `sase-js.7` | Generated Artifacts sub-tabs and the Files pane               |
| `sase-js.8` | The `sase-research` plugin repository                         |
| `sase-js.9` | Adoption, glossary, documentation                             |

Phase `sase-js.6` is the direct ancestor of this feature.

### 1.2 `Referenced By` is a working artifact→artifact link system

The pipeline, verified end to end in code:

```
prompt ref  →  core/artifact_ref_uses.py   (ref-uses.jsonl, per occurrence, immutable)
            →  core/artifact_consumption.py (consumption.jsonl, deduped, global)
            →  agents_sync/prompt_archive/publish.py  (enqueue_referenced_by_request)
            →  agents_sync/referenced_by_outbox*.py   (durable per-project outbox)
            →  sdd/referenced_by_refresh.py           (git lock, pull --rebase, commit)
            →  sdd/referenced_by_index.py             (.sase/referenced-by/<p>/<path>.json)
            →  sase_core::referenced_by               (render/upsert/remove/strip)
```

Properties already paid for, which any link design should inherit rather than re-earn:

- **Rust-owned managed block** (`crates/sase_core/src/referenced_by.rs`, 659 lines):
  markers `<!-- sase:referenced-by:start -->` / `:end`, heading `## Referenced By`,
  deterministic row sort, hard cap of 50 rows with an `omitted: N` line, idempotent
  upsert, tolerant parse, and numbered link definitions allocated through the shared
  `markdown_link_refs.rs` allocator (so link numbering never collides with the
  document's own links).
- **JSON index is the truth, Markdown is the projection.** `referenced_by_index.py`
  merges rows keyed by `(agent, canonical_ref)` into
  `.sase/referenced-by/<provider>/<relpath>.json`. `refresh_referenced_by` renders from
  that index. SASE never parses its own table back.
- **The managed block is excluded from content hashing.**
  `core/prompt_artifact_staging.py:424` calls `referenced_by_block_strip` before hashing
  a clean Markdown input, so a back-reference does not make the cited document look
  edited. This is the invariant that a frontmatter source of truth would break.
- **A dedicated non-user file-hook cause.** Write-back commits use cause
  `referenced_by`, so ordinary project file hooks ignore them unless they opt in via
  `filters.causes`.
- **Cross-repo safety.** `store_git_write_lock(..., mutates_worktree=True)`, pull with
  rebase, one commit per affected sidecar per publication, detached push, and a
  quarantine/retry path shared with agent publication.
- **Provider opt-in.** `publication.referenced_by` is a validated provider-spec field
  (`crates/sase_core/src/artifact_ref/provider_spec.rs`), accepting `markdown_table` or
  `none`; `publication.link` accepts `vcs_permalink`, `agents_object`, or `none`.

The outbox is currently drained (`referenced-by-outbox.json` is empty) and no
`.sase/referenced-by/` directories exist in the local sidecar clones yet, so the feature
is live but has not yet accumulated data — a *very* favorable moment to change its row
schema.

### 1.3 Four of the seven artifact kinds already have an "artifact md file"

| Ref kind    | Existing Markdown page                                      | Has a link block today                |
| ----------- | ----------------------------------------------------------- | ------------------------------------- |
| `plan:`     | the plan `.md` itself, in the `plans` sidecar               | **yes** — the plan header block       |
| `research:` | the document `.md` itself, in the `research` sidecar        | inbound only (`Referenced By`)        |
| `bead:`     | `pages/<lineage>/<id>.md` in the `beads` sidecar            | generated Phases/Agents/Commits tables |
| `agent:`    | `agents/<name>/README.md`, `families/<name>.md`             | generated Lineage/Commits tables      |
| `stitch:`   | none (a commit is external)                                 | no                                    |
| `patch:`    | PR page / published Patch page                              | no                                    |
| `file:`     | none unless the file is itself Markdown                     | no                                    |

The plan header block (`sase_core::plan::artifact_link`, exposed via
`sdd/plan_header_block.py`) is the closest existing thing to the requested top-of-file
link table. It is schema v3, Rust-owned, top-anchored, with a fixed section order:

```
PLAN · PROMPT · PARENT · BEAD · AGENTS · ARTIFACTS · COMMITS
```

rendered as bullets with resolved GitHub permalinks:

```markdown
- **PROMPT:**
  [prompts/202608/ace_app_boot_amortization.md](https://github.com/sase-org/sase--agents/blob/main/prompts/...)
- **PARENT:**
  [202608/fast_test_suite_1.md](https://github.com/sase-org/sase--plans/blob/main/202608/fast_test_suite_1.md)
- **BEAD:**
  [sase-ib.3](https://github.com/sase-org/sase--beads/blob/main/pages/sase-ib/sase-ib.3.md)
```

It already has `PlanHeaderEntry`/`PlanHeaderSection` list-shaped sections, a 50-entry
cap, `omitted`, and idempotent `upsert_plan_header_section`. **It is a table renderer
away from being the requested links block**, and it already carries reciprocal
cross-repo links (`update_source_aware_artifact_link` handles both local relative hrefs
and cross-repository hosted hrefs).

### 1.4 The Artifacts pane already has a declared relation graph

`sase artifact pane show beads` prints:

```
NAME          KIND       SOURCE            TARGET     INVERSE     FLAGS
parent        hierarchy  bead_parent_id    same-pane  children    directed, transitive
children      hierarchy  bead_parent_id    same-pane  parent      directed, transitive
plans         link       bead_plan_links   ref:plan   beads       directed
dependencies  link       bead_dependencies same-pane  dependents  directed
```

`PaneRelationDecl` (`ace/tui/_artifact_tab_model.py:136`) carries `name`, `kind`
(`HIERARCHY`/`FAMILY`/`LINK`), `label`, `source`, `target_pane`, `inverse`, `directed`,
`transitive`. `core/artifact_relations.py` builds an immutable per-snapshot
`RelationIndex` with inverse/symmetric derivation, dangling-edge diagnostics, and a
cycle-safe `chain()` walk. Concrete sources live in `ace/tui/relations/{beads,
documents, files, patches, stitches}.py` and each is a pure snapshot→edge projection
with no I/O.

**This is the integration point for the TUI half of the feature.** A single new relation
source that reads the link store, plus one `links`/`linked_by` relation declared on
every pane, gives the relation rail, `<`/`>`/`~` navigation modes, and the relation
panel for free — including on the future Agents sub-tab.

### 1.5 The audited-read family is an exact template for `sase artifact read`

Three commands already implement "print content, but record who read it and why":

| Command              | Required reason | Audit log                                      |
| -------------------- | --------------- | ---------------------------------------------- |
| `sase memory read`   | `-r/--reason`   | `~/.sase/projects/<key>/memory_reads.jsonl`    |
| `sase glossary read` | `-r/--reason`   | `~/.sase/projects/<key>/glossary_reads.jsonl`  |
| `sase repo open`     | `-r/--reason`   | `~/.sase/projects/<key>/repo_opens.jsonl`      |

All three share the house pattern in `repo_open_log.py`: a frozen event dataclass, agent
identity discovered from the environment with an interactive-user fallback
(`discover_agent_identity`), `locked_file(..., LOCK_EX)`, JSONL append, and a
`schema_version`. `sase glossary read` even refuses to print unless the read was
recorded. `sase memory read` also strips frontmatter before printing — precisely what
`sase artifact read` should do with frontmatter and managed blocks.

### 1.6 Scale facts that constrain the design

From `sase artifact stats` (live):

```
Rows              10,299          Explicit    801  /  32.7 MiB
Recorded bytes    1.3 GiB         Automatic 9,498  /   1.3 GiB
By kind           image 9,494 · markdown 751 · file 54
Observed growth   234.1 rows/day · 30.4 MiB/day over a 44-day window
```

The agents sidecar holds **8,581 agent directories**. The beads sidecar holds a page per
bead lineage. Any design whose cost is O(artifacts) in files, commits, or index entries
is a design that adds ~234 files/day forever.

### 1.7 The `RELATED:` corpus is real and largely machine-parseable

Measured against `sase/repos/beads/issues.jsonl`:

| Measure                                            | Count | Share  |
| -------------------------------------------------- | ----: | -----: |
| `RELATED:` note occurrences                         |   272 |   100% |
| Begin with a parseable bead id                      |   252 |  92.6% |
| Contain the `—` separator between id and rationale  |   250 |  91.9% |
| Mention more than one bead in the note              |    26 |   9.6% |

The convention is written into `/sase_new_task` in two places (step 4's retired-umbrella
branch and step 7's related-but-not-duplicate branch), both as
`sase bead note <id> "RELATED: <bead-id> — <how it bears on this task>"`. Beads
separately already have `sase bead ref add|list|rm` (artifact references stored without
the `@` prefix) and `sase bead dep add` (blocking dependencies).

---

## 2. Where the request and the landed design disagree

Three points of genuine tension, stated plainly before the decisions:

1. **Top vs. bottom.** `referenced_by.rs`'s own module doc says it is bottom-anchored
   "since citations are appended as they accumulate rather than declared up front."
   The request is for a table at the top. Both are right about different row
   populations.
2. **Frontmatter vs. index as truth.** The request proposes a `links:` frontmatter field
   as the mechanism for Markdown artifacts. The landed design explicitly chose the
   opposite ("Back the table with a machine-readable sidecar index … so SASE never
   reverse-engineers its state from Markdown. The table is a projection") and enforces
   it with `referenced_by_block_strip` at hash time.
3. **Every artifact vs. every *durable* artifact.** "Every sase artifact should have a
   corresponding artifact md file" is 10,299 files today and +234/day, of which 92% are
   automatic screenshot captures that retention is designed to trash.

None of these makes the request wrong. Each has a resolution that keeps the intent.

---

## 3. The seven decisions

### D1 — What an "artifact md file" is

**Options.**

- **(a) Literal companion file per artifact.** Every artifact gets a real `.md` on disk.
  Matches the request most directly. Costs 10k files now, +234/day, most of them
  companions to PNGs that `sase artifact prune` will trash — and then the companion
  dangles.
- **(b) Total addressing, lazy materialization.** Define a total function
  `artifact_md_path(ref) → path` for every ref kind. The file is created the first time
  the artifact acquires a link (or on explicit `sase artifact md --ensure`). Conceptually
  "every artifact has one"; physically, only linked artifacts do.
- **(c) Only artifact-repo documents get one.** Simplest, but excludes `file:` artifacts,
  which are the ones with no page today and the ones the future Agents sub-tab will want
  to link.

**Recommendation: (b).** Register the mapping per kind, reusing what exists:

| Kind                    | Artifact md file                                                  | Status  |
| ----------------------- | ----------------------------------------------------------------- | ------- |
| document providers      | the document itself                                               | exists  |
| `plan:`                 | the plan itself                                                   | exists  |
| `bead:`                 | `pages/<lineage>/<id>.md` in the beads sidecar                    | exists  |
| `agent:`                | `agents/<name>/README.md` / `families/<name>.md`                  | exists  |
| `patch:`                | the published Patch page                                          | exists  |
| `file:` markdown        | the file itself once published                                    | exists  |
| `file:` image/pdf/other | **new** `<basename>.md` beside the published artifact             | new     |
| `stitch:`               | **none** — a commit's page is the host's; links render on the peer | n/a     |

The `stitch:` exception matters: SASE does not own a commit's Markdown, so a
commit→artifact link is stored once and rendered on the artifact side only. Making
`stitch:` the single documented exception is much cheaper than inventing a
`stitches/<sha>.md` directory that nothing reads.

For unpublished `file:` artifacts living in `~/.sase/artifacts/agents/<project>/<ts>/`,
there is no git-shareable home and no permalink. Their links live in the project-local
store and their md file is local-only until the artifact is published. Say so in the
glossary entry rather than pretending otherwise.

### D2 — Where link state lives

**Options.**

- **(a) `links:` frontmatter in each Markdown artifact.** Travels with the file, is
  hand-editable, is committed. But: 9.5k artifacts have no frontmatter; a link's two
  endpoints usually live in two different repos, so one side would always be missing or
  duplicated; and every inbound link becomes a semantic edit of the target document,
  breaking the hashing invariant `prompt_artifact_staging.py` currently enforces.
- **(b) One project-local JSONL (`~/.sase/projects/<key>/artifact-links.jsonl`).**
  Matches `consumption.jsonl`, `repo_opens.jsonl`. Simple, fast, single writer. But it is
  machine-local — links written on one host would be invisible on another, and the
  sidecars exist precisely so this state is shared through git.
- **(c) Per-repo, per-artifact JSON index — the landed `Referenced By` model,
  generalized.** `.sase/artifact-links/<provider>/<relpath>.json` inside the artifact's
  own repo, holding that artifact's rows in both directions. Git-shareable, already has
  a write-back outbox, already has lock ordering and rebase handling.

**Recommendation: (c) as the truth, (b) as the outbox and audit journal, (a) as an
authoring inlet.**

Concretely:

- Truth: `.sase/artifact-links/<provider>/<relpath>.json` in the repo that owns the
  artifact, superseding `.sase/referenced-by/`. Each artifact's file holds every row
  touching it, with a `direction` discriminator, so one read answers "show me this
  artifact's links" without a global scan.
- Journal + outbox: `~/.sase/projects/<key>/artifact-links.jsonl` (append-only, audited,
  agent-attributed) plus the existing outbox JSON, renamed. This is what makes
  `sase artifact link` return immediately even when a sidecar is locked or offline.
- Inlet: a `links:` frontmatter list is *read* by the refresh pass and folded into the
  index, then normalized out of the frontmatter into the rendered block. This gives you
  the hand-authoring ergonomics you asked for without a second source of truth. The
  `markdown_frontmatter` property source already exists in the provider spec, so the
  reader is not new machinery.

Row schema (one row, wire-versioned, Rust-owned):

```json
{
  "schema_version": 1,
  "id": "…",
  "source_ref": "research:202608/artifact_links.md",
  "relation": "cites",
  "target_ref": "bead:sase-js",
  "description": "the ref contract this design extends",
  "origin": "manual",
  "created_by": "bbugyi200.athena.k3",
  "created_at": "2026-08-18T20:11:04Z",
  "uses": 1,
  "source_url": "https://github.com/…",
  "target_url": "https://github.com/…"
}
```

`origin ∈ {manual, prompt_ref, read, migrated, derived}` is what lets §D3 route rows to
different rendered blocks and lets `sase artifact link --rm` refuse to delete a machine
row.

**Identity must be the canonical artifact ref, not the TUI `ArtifactEntryTarget`.**
`ArtifactEntryTarget` is pane-scoped (`pane_id + parts`) and exists for row selection;
the canonical ref (`research:202608/x.md`, `bead:sase-js`, `agent:…`, `file:explicit:…`)
is the one name every subsystem already agrees on and the one that will still be correct
when the Agents sub-tab lands.

### D3 — Top table vs. the landed bottom block

**Options.**

- **(a) Move everything to the top.** Literal reading of the request. A research report
  cited by 60 agents would open with a 50-row table and an `omitted: 10` line before the
  first sentence.
- **(b) Two blocks split by direction** — outbound at top, inbound at bottom. Confusing:
  `A cites B` and `B cited-by A` are one fact, and which block it lands in depends on
  which file you opened.
- **(c) Two blocks split by curation.** Top `## Links` renders rows whose `origin` is
  `manual`/`migrated` — the deliberate, reason-bearing links, in both directions. Bottom
  `## Referenced By` keeps `prompt_ref`/`read` rows. The top block ends with one line:
  `_Plus 47 automatic references — see [Referenced By](#referenced-by)._`

**Recommendation: (c).** It satisfies "all links rendered at top in a nice table" for
every link a reader was asked to care about, preserves the landed block and its
50-row/`omitted` discipline for the unbounded population, and keeps the document
readable at 200 citations. Both blocks project from one store with one relation
vocabulary and one CLI, so this is a rendering decision, not a modelling one — and it is
reversible later by changing which origins route where.

Rendered top block (new managed markers, table-shaped, generated by a new
`sase_core::artifact_links` module that reuses `markdown_link_refs.rs`):

```markdown
<!-- sase:links:start -->

## Links

| Relation      | Artifact                          | Why                                    |
| ------------- | --------------------------------- | -------------------------------------- |
| supersedes    | [research:202608/ref_provider…][1] | this design extends its §7–§9 write-back |
| implements    | [bead:sase-js][2]                  | the epic that introduced the ref contract |
| cited-by      | [agent:bbugyi200.athena.k3][3]     | authored this report                   |

_Plus 47 automatic references — see [Referenced By](#referenced-by)._

[1]: https://github.com/sase-org/sase--research/blob/<sha>/202608/ref_provider_contract/…
[2]: https://github.com/sase-org/sase--beads/blob/main/pages/sase-js/README.md
[3]: https://github.com/sase-org/sase--agents/blob/main/agents/bbugyi200.athena.k3/README.md

<!-- sase:links:end -->
```

Three properties to preserve from the existing blocks: the block must be stripped before
content hashing (extend `prompt_artifact_staging.py`'s strip to both markers); the
write-back cause must be non-user (`artifact_links`, alongside `referenced_by`); and
numbering must go through the shared allocator so a document's own reference links are
never renumbered.

### D4 — Relation vocabulary and the required description

**Options.**

- **(a) Free text only.** Zero ceremony, no inverse derivation, no grouping, no TUI
  relation rail, no way to ask "what supersedes this?".
- **(b) Closed builtin enum.** Predictable, but the plugin ecosystem (`sase-github`,
  `sase-research-artifacts`) will want its own.
- **(c) Builtins + plugin/config extension, snapshotted to a committed JSON file.**
  Exactly the shape you already built for **task types**: builtins + `sase_task_types`
  plugins + `bead.task_types` config, assembled and snapshotted to `sase/task_types.json`
  so generated instructions are a function of committed files.

**Recommendation: (c), plus a required free-text description.** The slug gives the
inverse, the sort order, and the TUI relation declaration; the description gives the
"why" you asked for. Snapshot to `sase/artifact_relations.json`, regenerated by
`sase memory init`, and render a `## Artifact Relations` section into `AGENTS.md` the
same way task types are rendered — that is what makes agents actually use the right slug.

A starting vocabulary, each with an inverse:

| Slug            | Inverse           | Directed | When to use                                            |
| --------------- | ----------------- | -------- | ------------------------------------------------------- |
| `cites`         | `cited-by`        | yes      | an agent prompt referenced this artifact (`prompt_ref`) |
| `read`          | `read-by`         | yes      | an agent read this artifact (`sase artifact read`)      |
| `related`       | `related`         | no       | the `RELATED:` note migration target                    |
| `supersedes`    | `superseded-by`   | yes      | this artifact replaces an earlier one                   |
| `implements`    | `implemented-by`  | yes      | plan/patch ↔ the bead or design it realizes             |
| `derives-from`  | `derived-into`    | yes      | generated or extracted from another artifact            |
| `duplicates`    | `duplicated-by`   | yes      | bead triage found a semantic duplicate                  |

**Reserve `blocks`/`depends-on`.** Bead dependencies already exist as
`sase bead dep add`, they affect readiness and scheduling, and the beads pane already
declares a `dependencies`/`dependents` relation. `sase artifact link` should refuse those
slugs with an error pointing at `sase bead dep`, or a second scheduling truth appears.

**On the required description for machine-created rows.** `sase artifact link` and
`sase artifact read` both take a mandatory reason from their caller. Prompt-ref rows have
no caller-supplied reason — but `ArtifactRefUseRecord` already captures `prompt_text`,
so synthesize the description from a bounded excerpt (or the xprompt/bead title when
available). The invariant "every link says why it exists" then holds uniformly at read
time, without demanding a reason from a code path that has no human in it.

### D5 — `sase artifact link` and the `RELATED:` migration

**CLI shape.** `sase/memory/cli_rules.md` is explicit: *"Options must not be required. A
value that is required for the command to execute belongs in a positional argument."*
That argues against `-w/--why` and for a sentence-shaped positional form:

```bash
sase artifact link <source-ref> <relation> <target-ref> "<why>"
sase artifact link list <ref> [-d in|out|both] [-j] [-R <relation>]
sase artifact link rm <source-ref> <relation> <target-ref>
```

which reads as subject–verb–object–reason:

```bash
sase artifact link bead:sase-m4 related bead:sase-ct \
  "shares the ACE-TUI flake root cause; fix order matters"
```

Note the friction: `sase memory read` and `sase glossary read` both use a **required
`-r/--reason` option**, contradicting that rule. Either the rule has a documented
carve-out for audited reads, or those two commands are drifted. Worth settling before a
third command picks a side (see §6).

Because `sase artifact link` is a group with an exact `list` child, bare
`sase artifact link` would delegate to `list` under the central `_default_list_subcommands()`
convention — which collides with the bare linking form above. Cleanest resolution:
make linking its own verb, `sase artifact link add …`, and let bare `sase artifact link`
mean `list`. Slightly more typing, zero ambiguity, consistent with `sase bead ref
add|list|rm`.

**Migration of the 272 `RELATED:` notes.** Ship it as a one-shot, dry-run-by-default
command (`sase artifact link migrate-notes [--apply]`) that:

1. Scans every bead note matching `^RELATED: <bead-id>\s*[—-]\s*(?<why>.+)$`.
2. Emits `link <this-bead> related <that-bead> "<why>"` rows with `origin: migrated`.
3. Leaves the note text in place — notes are attributed, append-only history and
   `sase bead history --lost-notes` depends on them — and appends one
   `MIGRATED: linked as related/<id>` note per converted row.
4. Reports the ~8% that do not parse (multi-bead notes, prose-first notes) as a manual
   worklist rather than guessing.

Then update `/sase_new_task` — both the step-4 retired-umbrella branch and the step-7
related-but-not-duplicate branch — to emit `sase artifact link add` instead of
`sase bead note "RELATED: …"`. That is a skill-source edit under
`src/sase/xprompts/skills/sase_new_task.md`, which requires explicit user permission and
a `sase memory init` run.

### D6 — `sase artifact read`

**Recommendation.** Follow `sase memory read` almost exactly:

```bash
sase artifact read <ref> "<reason>"          # positional reason, per cli_rules
sase artifact read <ref> "<reason>" -f json  # -f {json,markdown,rich}, default markdown
sase artifact read <ref> "<reason>" -n 400   # bounded output for large documents
```

Behavior:

- Resolves through the existing `show`/`path` resolution, so every kind and every
  `#L`/`#page=`/`#t=` fragment works on day one, including VCS-backed materialization.
- Strips leading frontmatter and both managed blocks before printing — otherwise every
  read prints the link table it just contributed to, and context windows pay for it.
- Appends an audited row to `~/.sase/projects/<key>/artifact_reads.jsonl` using the
  `repo_open_log.py` house pattern, then inserts a link row
  `agent:<me> --read--> <ref>` with the reason as the description and `origin: read`.
- Refuses to print if the read could not be recorded, matching `sase glossary read`.
- For images, video, and PDFs, prints metadata plus a pointer to `sase artifact open`
  rather than dumping bytes, and still records the read.

**Scope discipline: only `read` links.** `show`, `path`, and `open` must stay silent.
`path` is the composition primitive (exactly one absolute path on stdout) and is called
from scripts and from other SASE code; linking from it would generate noise links from
every internal resolution. This is the same reason `sase memory show` records nothing
while `sase memory read` does.

**Skill guidance.** `/sase_artifact_file` gains a "Read an Artifact" section; `/sase_repo`
gains a one-line pointer that a single tracked artifact read should go through
`sase artifact read`, with `sase repo open` reserved for modification and broad
exploration. Both are memory-adjacent edits requiring your explicit go-ahead and a
`sase memory init`.

### D7 — Prompt refs become links

This is the smallest change of the seven, because the pipeline exists. In
`agents_sync/prompt_archive/publish.py`, `enqueue_referenced_by_request` becomes
`enqueue_artifact_link_request`, carrying `relation: "cites"`, `origin: "prompt_ref"`,
and a synthesized description; the drain writes into the generalized index. The
`Referenced By` table then renders from `origin ∈ {prompt_ref, read}` rows instead of
from its own parallel index.

Two things to get right:

- **Both endpoints.** Today only the *target* repo gets a row (the cited document's
  `.sase/referenced-by/`). Under a symmetric model the *source* (the agent) also owns a
  row, in the agents sidecar. That doubles the write-back fan-out per publication. The
  cheap resolution: write the target row through the outbox as today, and let the
  agent's own page render its outbound links from the local `ref-uses.jsonl` it already
  has, since agent pages are generated at publication anyway.
- **Lock order.** The prior report already fixed this: **artifact repos first, `agents`
  last**, so a publication writing back to two sidecars cannot deadlock against a
  concurrent `sase plan links --write`. Keep that ordering when the outbox generalizes.

---

## 4. Hazards

| # | Hazard | Why it bites | Mitigation |
| - | ------ | ------------ | ---------- |
| 1 | **File explosion.** 10,299 artifacts, +234/day, 92% automatic PNGs. | A companion `.md` per artifact is ~10k files now and a permanent commit-rate tax on the agents sidecar. | D1(b): lazy materialization; md file exists only once a link does. |
| 2 | **Hash feedback loop.** | If `links:` frontmatter is truth, being linked edits the document, which changes its digest, which can re-trigger capture and re-linking. `referenced_by_block_strip` exists precisely to prevent this. | D2: index is truth; extend the strip to the new `sase:links` markers before hashing. |
| 3 | **Dangling links after retention.** | `sase artifact prune`/`reclaim` trash rows, and **`reclaim` changes a row's ID** because a VCS-backed id derives from its VCS identity. Every `file:` link would silently rot. | Add the link store to the lifecycle protection collector, exactly as consumed refs are protected today; make `reclaim` skip linked rows. |
| 4 | **Link spam.** | Auto-linking every prompt ref *and* every read means a hot document accumulates hundreds of rows; a top-anchored table would bury the content. | D3: curated rows top, automatic rows bottom, 50-row cap with `omitted` on both. |
| 5 | **Two truths for bead relations.** | `sase bead dep` (scheduling) and `sase artifact link` (semantic) would both claim bead↔bead edges. | Reserve `blocks`/`depends-on`; error with a pointer to `sase bead dep`. |
| 6 | **Machine-local vs. shared state.** | A project-local JSONL as truth means links written on one host are invisible on another. | D2: per-repo JSON index is truth; the JSONL is journal + outbox only. |
| 7 | **Unlinkable artifacts.** | `stitch:` has no SASE-owned page; unpublished `file:` artifacts have no repo and no permalink. | D1: `stitch:` is a documented exception; unpublished `file:` links are local-only until publication. Do not fabricate a permalink to `main` — the landed design already refuses to. |
| 8 | **File hooks firing on projection commits.** | A user file hook that does not filter `causes` would run on every link write-back. | Reuse the `referenced_by` precedent: a non-user cause `artifact_links`, excluded by default. |
| 9 | **Unflagged user-reaching behavior.** | `sase/memory/gotchas.md` requires a feature flag on user-reaching behavior before it is ready. | `sase flag new artifact_links` before the first user-visible block renders; it also files its own removal bead. |
| 10 | **Rust boundary drift.** | The link model, relation registry, and block render/parse/upsert are shared backend behavior that a future web or editor frontend must match. | Land them in `../sase-core` (`crates/sase_core/src/artifact_link*`), with Python as adapter + CLI, per `sase/memory/` boundary guidance. |

---

## 5. Recommended solution

### 5.1 The shape

**Generalize `Referenced By` into an artifact-link graph keyed by canonical artifact ref,
stored per-artifact in the owning repo, projected into two managed Markdown blocks, and
written through the outbox that already exists.**

Five commitments:

1. **One store, one vocabulary, many origins.** A link row is
   `(source_ref, relation, target_ref, description, origin, created_by, created_at)`.
   `sase artifact link add` writes `origin: manual`; the note migration writes
   `migrated`; prompt publication writes `prompt_ref`; `sase artifact read` writes
   `read`. Nothing else invents an edge.
2. **The artifact md file is an addressing rule, not a materialization rule.** Every ref
   maps to a path; the file is created when the artifact first acquires a link. Four
   kinds already have one, `stitch:` documentedly has none, and only binary `file:`
   artifacts get a genuinely new `<basename>.md` companion.
3. **Truth in `.sase/artifact-links/<provider>/<relpath>.json`; Markdown is a
   projection; `links:` frontmatter is an authoring inlet the refresh pass ingests and
   normalizes away.**
4. **Curated links at the top, automatic citations at the bottom, one pointer line
   between them.**
5. **Relations are a task-type-shaped registry**: builtins + plugin + config, snapshotted
   to `sase/artifact_relations.json`, rendered into `AGENTS.md`, each with an inverse.

### 5.2 Phase plan

| Phase | Repo | Scope |
| ----- | ---- | ----- |
| **core** | `sase-core` | `artifact_link` wire types (row, relation descriptor, index document); the relation registry with inverse derivation and validation; `artifact_links_block_{render,parse,upsert,remove,strip}` reusing `markdown_link_refs.rs`; generalize `referenced_by.rs` rows to carry `relation`/`description`/`origin`; one coordinated wire-version bump. No behavior change in `sase`. |
| **store** | `sase` | Python adapter over the core types; `.sase/artifact-links/` index read/write; project-local journal + audited log; migrate `.sase/referenced-by/` readers to the new index with the old path accepted read-only. Feature flag `artifact_links`. |
| **cli** | `sase` | `sase artifact link add\|list\|rm`, `sase artifact read`, `sase artifact md --ensure`; audited `artifact_reads.jsonl`; `sase artifact doctor` checks for dangling and orphaned link rows; retention protection for link targets. |
| **render** | `sase` | The `## Links` top block; generalized refresh/outbox drain writing both blocks; `artifact_links` file-hook cause; extend the hash strip; lock order artifact-repos-first. |
| **refs** | `sase` | Prompt publication emits `cites` rows through the generalized outbox; `Referenced By` renders from the shared index; agent pages render outbound links from `ref-uses.jsonl`. |
| **ace** | `sase` | One `artifact_links` relation source in `ace/tui/relations/`; declare `links`/`linked_by` on every pane contract; the relation panel and `<`/`>`/`~` modes then work unchanged. |
| **migrate** | `sase` | `sase artifact link migrate-notes` with dry-run default; report the ~8% unparseable; update `/sase_new_task`, `/sase_artifact_file`, `/sase_repo`; add the **Artifact Markdown File** glossary term and a `docs/artifact_links.md` page; `sase memory init`. |

`core` gates everything. `store`→`cli`→`render` is the critical path; `refs`, `ace`, and
`migrate` are independent once `render` lands.

### 5.3 Why this beats the literal reading

| Literal request | Recommended | Reason |
| --------------- | ----------- | ------ |
| `.md` companion for every artifact | addressing total, materialization lazy | 10,299 artifacts, +234/day, 92% prunable PNGs |
| `links:` frontmatter is the mechanism | frontmatter is an inlet; index is truth | keeps the hash-strip invariant; works for the 9.5k artifacts with no frontmatter; one truth per fact across two repos |
| all links at the top | curated at top, automatic at bottom | a 60-citation report stays readable; reuses the landed 50-row/`omitted` block |
| `sase artifact link` as a new subsystem | one new relation/description field on landed rows | the outbox, git locking, rebase, idempotency, and cause-tagging are already paid for |

Every deviation is reversible by changing one routing predicate (which origins render
where) or one config value, not by rewriting the model.

---

## 6. Open questions for the project owner

1. **Top-block population.** Confirm the curated/automatic split (D3c), or say you want
   every row at the top and accept that a heavily-cited document opens with a 50-row
   table and an `omitted` line.
2. **`cli_rules.md` and required reasons.** `sase memory read` and `sase glossary read`
   use a required `-r/--reason` option, which the rule forbids. Should
   `sase artifact read` take a positional reason (rule-compliant, inconsistent with its
   two siblings) or a required `-r` (consistent, rule-violating)? A one-line carve-out in
   `cli_rules.md` for audited reads would settle all three.
3. **Bare `sase artifact link`.** Confirm `link add|list|rm` (so bare `link` can delegate
   to `list` per the default-`list` convention) rather than a bare four-positional
   linking form.
4. **Relation vocabulary.** Is the seven-slug starting set in D4 right, and should
   `duplicates` exist at all given `sase bead +1` already models corroboration?
5. **`RELATED:` notes after migration.** Leave the historical notes in place with a
   `MIGRATED:` marker (recommended, preserves attributed history), or rewrite them?
6. **Unpublished `file:` artifacts.** Accept that their links are machine-local until
   publication, or block linking to an unpublished `file:` artifact entirely?
7. **Agents sub-tab timing.** The recommendation keys links by canonical ref specifically
   so the Agents pane needs no new link plumbing. Confirm that is the intent, so the
   `ace` phase declares `links`/`linked_by` on a pane contract that does not exist yet.
