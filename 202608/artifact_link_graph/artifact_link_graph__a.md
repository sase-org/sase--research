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

# Linking Artifacts to Artifacts

**Research question.** SASE now has a real artifact-reference contract, a
Referenced By projection, and a host-owned Artifacts relation panel. What is
the right way to add *typed, described links between artifacts*, including:
an "artifact markdown file" for every artifact, a `links` frontmatter field,
GitHub-rendered link tables, `sase artifact link`, conversion of task-bead
`RELATED:` notes, automatic agent→artifact links from prompt refs and from a
new `sase artifact read`, and a design that will later host completed agents
as first-class artifacts?

**Scope.** `sase` at `4c5c06278`, `sase-core` at `35c09db`,
`sase-research-artifacts` on `origin/master`, the research sidecar at
`ae87170`, and the plans sidecar epic
`plan:202608/artifact_ref_contract.md` (`sase-js`, closed). Read 2026-08-18.
This is a single research pass, not a swarm consolidation.

**Prior work this report sits on.**

- [`ref_provider_contract`](ref_provider_contract/ref_provider_contract.md)
  (2026-08-11) — the redesign that became epic `sase-js`.
- [`docs/artifact_references.md`](https://github.com/sase-org/sase/blob/master/docs/artifact_references.md)
  — the landed contract: prompt refs, publication links, Referenced By.
- [`docs/artifacts_pane_contract.md`](https://github.com/sase-org/sase/blob/master/docs/artifacts_pane_contract.md)
  — host-owned `hierarchy` / `family` / `link` relation primitives.
- `plan:202607/artifact_read_cli.md` (`sase-ax`) — today's
  `sase artifact {list,show,path,open}` surface. Those are *inspect*
  commands. They are not an audited read and they create no links.

---

## Bottom line

Build a **host-owned artifact-link graph** whose *authoring surface* is the
artifact markdown file, not a new sidecar database and not another
free-text note convention.

The one-sentence rule: **every artifact has exactly one artifact markdown
file; every link is a directed edge `(from, to, relation, description)`
written through `sase artifact link`; the file renders those edges as a
managed table at the top of the body, with GitHub hyperlinks.**

Five decisions that make the rest fall out:

1. **Do not store the graph only in frontmatter, and do not store it only
   in a central JSONL.** Markdown documents author links in `links:`
   frontmatter. Beads, agents, and other generated pages store links in
   their *native mutable store* and *project* them onto their generated
   markdown file. A Rust-owned wire type plus per-kind writers is the
   contract; the markdown table is a projection, like Referenced By.
2. **Do not reuse bead `refs`, `RELATED:` notes, plan-header `ARTIFACTS`,
   or Referenced By as the new link.** Each of those already has a job.
   The new object is a typed edge with a required why.
3. **`sase artifact read` is the audited analog of `sase memory read` /
   `sase glossary read`.** `path` / `show` / `open` stay untracked.
   `sase repo open` stays the door into a sidecar when the agent will
   *modify* files or *browse the repo*, not when it wants one artifact.
4. **Prompt refs already record a use row and a Referenced By projection.
   Keep that, and *also* write an agent→artifact link** with the closed
   relation `cited`. The future Agents sub-tab then has something to
   hang off without a second invention.
5. **The Agents sub-tab is out of scope, but the link model must treat
   `agent:<name>` as an ordinary node from day one.** Completed agents
   already have generated pages. Those pages are their artifact markdown
   files.

Ship it as a `wip` feature flag (`sase flag new artifact-links`). Writing
tables into published sidecar files is user-reaching and mutating; the
disabled branch must leave documents and the bead event stream untouched.

---

## 1. What "artifact" is today

There is a glossary term for **Artifact Reference** and none for
**Artifact**. That gap is why the new "artifact markdown file" term will
feel unanchored unless both are added together.

Live addressable kinds, from `docs/artifact_references.md` and the
`sase artifact` CLI:

| Kind | Where the bytes / record live | Has a markdown file today? |
| --- | --- | --- |
| `plan:` | plans sidecar `*.md` | Yes — the plan *is* the file |
| `research:` | research sidecar `*.md` | Yes — the report *is* the file |
| other document kinds | configured sidecar | Yes, if the inventory glob is markdown |
| `bead:` | beads event store | Yes, but *generated*: `pages/<id>/…md` |
| `agent:` | agents sidecar pages | Yes, but *generated* |
| `patch:` | ProjectSpec / archive | No markdown page |
| `stitch:` | a git commit | No markdown page (immutable) |
| `file:` | `~/.sase/artifacts/` or VCS-backed | Only if the stored file is markdown |
| binary sidecar files | e.g. `*_infographic.png` next to a report | No |

So "every artifact should have a corresponding artifact md file" is a
*new invariant*, not a description of the current tree. It is already
true for the document kinds this feature will be judged on (research,
plans). It is *almost* true for beads and agents — they have pages, but
those pages are projections and cannot be the source of truth. It is
false for stitches, patches, and binary files.

The TUI already treats all of the above as Artifacts-tab rows, with a
typed `ArtifactEntryTarget` and a compiled `ArtifactsPaneContract`.
Completed agents are *not* an Artifacts sub-tab yet; they live on the
Agents tab. The request to keep an Agents-as-artifacts sub-tab in mind
is therefore a node-type decision, not a storage invention.

---

## 2. Six existing "link" surfaces — and why none of them is this feature

Verified against the code on 2026-08-18.

### 2.1 Bead `refs`

`Issue.refs` is `list[str]` (`src/sase/bead/model.py`).
`sase bead ref add` stores canonical artifact references with **no
relation and no description**. Published bead pages render them as a
`## References` bullet list
(`src/sase/bead_pages/rendering_identity.py`). This is "this bead cites
that artifact," not "this bead is related to that bead because…".

Keep `refs` for evidence attachments (`sase artifact create --bead`,
`sase bead +1 --ref`). Do not stretch them to carry a why.

### 2.2 `RELATED:` notes

`/sase_new_task` tells agents to write:

```bash
sase bead note <task-id> "RELATED: <bead-id> — <how it bears on this task>"
```

That is the only official producer. The same skill uses the same shape
to point at a *retired umbrella* that must not be `+1`'d. There is no
parser, no index, no inverse, and no GitHub link. The text lives in the
append-only notes field and is rendered as prose on the bead page.

This is not rare. On this machine's sase bead store there are **279
`RELATED:` note events across 150 beads**. The format is already
`RELATED: <id> — <description>`, which is almost the new link record —
it just was never a first-class object.

### 2.3 Plan-header `ARTIFACTS` / `AGENTS` / `COMMITS`

Rust-owned (`sase-core` `plan/artifact_link.rs` + `sections.rs`).
Canonical bullets at the top of a plan or prompt, with hosted GitHub
hrefs. `ARTIFACTS` means "files this plan/prompt produced or captured,"
not "typed edges to other artifacts." `BEAD` / `AGENTS` / `COMMITS` are
projections of durable state, refreshed by `sase plan links refresh`,
never accumulators.

Do not add a `LINKS` section to this header. The header is SDD
provenance with a closed section set and a `header-invalid` validator
that every plan gate already runs. A general artifact-link table is a
different block.

### 2.4 Referenced By

Rust-owned (`sase-core` `referenced_by.rs`). Bottom-anchored managed
block with HTML comment markers, a markdown table, numbered GitHub /
object-store links, a 50-row cap, `strip` for content hashing, and a
structured index at `.sase/referenced-by/<kind>/<path>.json`. Written
through the publication outbox after a prompt archive push
(`src/sase/agents_sync/referenced_by_publication.py`).

This answers **"who cited me, when, how many times?"** It is a
citation ledger, not a semantic graph. Rows are `(agent, project,
canonical_ref, date, use_count)`. There is no relation slug and no
why.

Keep it. Prompt refs should continue to write use rows. The new Links
table answers a different question.

The `referenced_by.rs` module comment is the blueprint the new table
should copy, with one change of anchor:

> Mirrors the proven properties of `plan/artifact_link.rs`'s header
> block — deterministic render, tolerant parse, idempotent upsert —
> but anchored at the bottom of the document instead of the top.

The new Links block is the same primitive, anchored at the top.

### 2.5 ACE relation panel

Host-owned `hierarchy` / `family` / `link` kinds
(`docs/artifacts_pane_contract.md`). Derived from *already-declared
properties*: bead parent, Patch parent, filename families
(`bundle.md` / `bundle__a.md`), or a provider property such as
`related: bundle.md`. Providers declare facts; they do not store a
graph.

This is a *presentation* index over existing fields. It has no
description, no CLI, and no write path. The new link graph should
*feed* a `link`-kind relation on every pane that has an artifact
markdown file. It should not be implemented as another
`ref.relations` property that each plugin must remember to declare.

### 2.6 Prompt-ref consumption / use rows

Launch-time `@kind:arg` expansion already:

- records `~/.sase/artifacts/consumption.jsonl`
  (`src/sase/core/artifact_consumption.py`);
- records per-occurrence use rows
  (`sase-core` `artifact_ref/uses.rs`);
- rewrites published prompts to `[@kind:arg][N]` with revision-pinned
  destinations;
- queues Referenced By write-back.

`sase artifact path`, `show`, and `open` do **none** of that. An agent
that does `sase artifact path research:…` and then `read_file` leaves
no durable trace. That is the hole `sase artifact read` fills.

---

## 3. Recommended object model

### 3.1 Artifact markdown file

Add two glossary terms. The second is the requested one; the first is
the missing parent.

**Artifact.** A SASE artifact is any durable record addressable by an
artifact reference: a sidecar document (`plan:`, `research:`, or a
configured document kind), a bead, a completed agent, a Patch, a
stitch, or an indexed file. Every artifact has a canonical
`<kind>:<argument>` identity. User-facing text uses the configured
project name, never a ProjectSpec key.

**Artifact Markdown File** (aka artifact md file). The Markdown
document that carries one artifact's typed links and, for
non-markdown artifacts, a short human-readable identity. Rules:

| Artifact | Artifact md file |
| --- | --- |
| A markdown document (`*.md` / `*.markdown`) | **Itself.** It is its own artifact md file. |
| A non-markdown file in a repo (`diagram.png`, `report.pdf`) | Sibling `<stem>.md` in the same directory. `diagram.png` → `diagram.md`. |
| A bead | Its generated bead page. The page is a *projection*; the store is the bead event stream. |
| An agent | Its generated agent page. Same split: page is projection, agents-sidecar metadata is store. |
| A Patch | A generated companion page (phase 2). Not required to land the graph. |
| A stitch | No mutable file. Outgoing links from a stitch are not authored; incoming links *to* a stitch render on the source's table and use `HostedLinkResolver` commit URLs. |

**Companion naming.** Use the file *stem*, not the full basename:
`diagram.png` → `diagram.md`, not `diagram.png.md`. That matches how
humans already pair research reports with media
(`foo.md` + `foo_infographic.png` already avoids a stem collision).
If `<stem>.md` already exists as a first-class markdown artifact,
refuse and tell the caller to use the disambiguated
`<filename>.md` form (`diagram.png.md`). Never silently overwrite a
research report or plan.

**Host-owned, not a provider property.** Do not add `links` to each
plugin's `ref.properties`. Today's research provider declares only
`create_time`, `updated_time`, `status`, `tags`
(`sase-research-artifacts` `provider.py`), and those types are
`datetime` / `enum` / `string_list`. A structured link list would
force a schema bump on every document provider. Links are as
fundamental as Referenced By: the host parses them, renders them, and
indexes them. A provider may later *display* them through the existing
`ref.relations` `link` kind; it must not be required to declare the
field to get linking.

Watch the name collision with blog-post frontmatter. Several
`docs/blog/posts/*.md` files already have a `links:` list of
`label: path` related-docs entries. Those posts are not SASE artifacts
today. The artifact-link schema below is a list of mappings with
`ref` / `relation` / `description` and will not parse as the blog
shape; keep the two worlds separate and do not run the artifact-md
writer over `docs/blog/`.

### 3.2 The link record

One directed edge:

```text
from          canonical artifact ref   (bead:sase-oz, research:202608/artifact_linking.md, agent:bbugyi200.athena.y2)
to            canonical artifact ref
relation      short slug, required
description   non-empty prose, required
source        authored | cited | read | migrated
created_at    RFC-3339
created_by    agent name or "interactive"
```

Dedup key: `(from, to, relation)`. A second write with a new
description updates the edge (last write wins). The same pair may
carry several relations (`related` and `supersedes` at once). A link
to self is rejected.

**Relation catalog.** Closed slugs plus an escape hatch:

| Slug | Who writes it | Meaning |
| --- | --- | --- |
| `related` | humans / agents via CLI; RELATED migrator | Adjacent but not a duplicate |
| `cited` | prompt-ref expansion | This agent/document cited that artifact in a launch prompt |
| `read` | `sase artifact read` | This agent read that artifact, with `-r` as the description |
| `supersedes` | authored | Replaces the target |
| `depends-on` | authored | Distinct from bead `dep` (work-blocking). Semantic only. |
| `evidence` | authored | Target is evidence for the source |
| `implements` | authored | Source implements the target (plan, research, bead) |
| custom | authored | Any other `[a-z][a-z0-9-]*` slug, still requires a description |

Do not invent a parallel to bead dependencies. `sase bead dep` remains
the work-blocking graph. A `depends-on` *link* is documentation.

### 3.3 Where the bytes live (kind-native store + host projection)

This is the decision that makes generated pages and markdown documents
the same feature.

```text
                    ┌─────────────────────────────┐
                    │  ArtifactLink (Rust wire)   │
                    └─────────────┬───────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            ▼                     ▼                     ▼
   markdown sidecar         bead event stream      agent publication
   frontmatter `links:`     link_added/removed     metadata / index
            │                     │                     │
            └─────────────┬───────┴─────────────────────┘
                          ▼
              artifact md file projection
         <!-- sase:links:start --> table <!-- sase:links:end -->
                          │
                          ▼
              ACE relation panel (kind: link)
              sase artifact link list
              future Agents sub-tab
```

**Markdown sidecar documents (research, plans, custom docs).**
`links:` in YAML frontmatter is the authored store:

```yaml
---
create_time: 2026-08-18
status: research
links:
  - ref: research:202608/ref_provider_contract/ref_provider_contract.md
    relation: related
    description: Prior redesign this feature extends, not replaces.
  - ref: bead:sase-js
    relation: implements
    description: Lands on the artifact-reference contract shipped by sase-js.
---
```

`sase artifact link add` mutates that list through a Rust upsert, then
refreshes the managed table. Hand-edits of `links:` are first-class;
the next `sase artifact link` or doctor refresh reconciles the table
to the frontmatter.

**Binary sidecar files.** Create or update the companion `<stem>.md`
with the same frontmatter schema. The companion may be nothing but
frontmatter plus a one-line title. Inventory globs for document
providers must **not** start treating every companion as a new
first-class document of that kind. The host knows a file is a
companion when a non-markdown sibling with that stem exists.
Research's current inventory `20*/**/*.md` would otherwise list
`foo_infographic.md` as a research report — exclude companions from
document inventory, or give them a `status:` / `role: companion`
marker the inventory filter drops.

**Beads.** Add `link_added` / `link_removed` events and a projected
`links` field on the issue, beside `refs` but not mixed into it.
`sase artifact link add bead:sase-oz bead:sase-ct related "…"` writes
those events through the existing bead mutation path (lock, commit,
page refresh). The generated bead page grows a Links table at the top
of the body, *before* `## Description`. Do **not** hand-edit bead
pages; they are overwritten on refresh, which is why the event stream
must be the store.

**Agents.** Same split. Prompt-ref and `sase artifact read` links whose
`from` is the current agent write into the agent's publication
metadata (the natural home is next to the existing ref-uses payload;
follow-up bead `sase-ka` already wants `agents/<agent>/ref-uses.json`
via the v2 publication contract). The generated agent page projects
the table. This is what makes the future Agents sub-tab free: the
node and the edges already exist.

**Stitches and Patches in v1.** Accept incoming links (the source
artifact's table points at `stitch:<repo>@<sha>` or `patch:<name>`
with a hosted URL). Do not require an artifact md file for them until
someone wants to author *outgoing* links from a commit or a Patch.
Forcing a generated page for every stitch just to satisfy the slogan
is a large epic of its own.

**Indexed `file:` artifacts.** If the stored file is markdown, it is
its own artifact md file (and lives under `~/.sase/artifacts/`, so the
table is local, not on GitHub). If it is not markdown, write a
companion next to the stored copy. VCS-backed rows already have a
repo path; the companion belongs next to the source file in that repo
when the repo is writable, otherwise next to the materialized cache
copy and *not* claimed as a GitHub-visible page.

### 3.4 The rendered table

Copy `referenced_by.rs` almost verbatim: markers, deterministic
column order, numbered reference-style links through
`markdown_link_refs`, 50-row cap, `_… and N more_`, idempotent
upsert, `strip` for hashing / file-hooks.

Place it **after YAML frontmatter and after a plan-header block if
one exists, before the first ATX heading.** That is "the top of the
readable document" without breaking SDD provenance or putting a table
above `---`.

Shape:

```markdown
<!-- sase:links:start -->

## Links

| Artifact | Relation | Description |
| --- | --- | --- |
| [research:202608/ref_provider_contract/ref_provider_contract.md][1] | related | Prior redesign this feature extends, not replaces. |
| [bead:sase-js][2] | implements | Lands on the artifact-reference contract shipped by sase-js. |

[1]: https://github.com/sase-org/sase--research/blob/main/202608/ref_provider_contract/ref_provider_contract.md
[2]: https://github.com/sase-org/sase--beads/blob/main/pages/sase-js/README.md

<!-- sase:links:end -->
```

Hrefs come from the existing `HostedLinkResolver`
(`src/sase/sdd/hosted_links.py`): plans, beads, agents, commits, and
sidecar blobs already know how to form a GitHub URL and degrade to an
unlinked label when they cannot. Do not invent a second URL builder.

**Incoming edges.** The top table is *outgoing*. Incoming non-citation
links (B was linked *from* A) belong in a second, smaller
`### Linked From` table inside the same managed block, or as a
column. Do **not** fold this into Referenced By: a `related` edge is
not a citation and has no use-count. Citations stay at the bottom.

**Strip for hashing.** File-hooks, research-highlights, and
content-addressed capture must hash `strip_links_block(strip_referenced_by_block(doc))`.
Adding a link must not look like the research report changed. Reuse
the non-user cause pattern (`referenced_by`) with a new cause
`artifact_link` so ordinary hooks ignore projection commits unless
they opt in.

**Write-back.** Reuse the Referenced By outbox / drain / detached-push
pipeline. A `sase artifact link` that touches a sidecar document
should not invent a third publication mechanism. Group by sidecar
role, pull-rebase, upsert only the managed block *and* the
frontmatter `links:` list, commit
`Update artifact link projections`, push detached. Failures stay
queued for `sase agent sync`.

---

## 4. CLI

`cli_rules.md`: subcommands and options alphabetical; every public
long option gets a short alias; values required to execute are
positionals, not options. Existing audited-read commands
(`sase memory read`, `sase glossary read`, `sase repo open`) already
violate that last rule for `-r/--reason`. Follow *those* for `read`,
because the reason *is* the link description and agents already know
the flag.

### 4.1 `sase artifact link`

A group, so it can grow `add` / `rm` / `list` the way
`sase bead ref` and `sase bead dep` already do. Bare
`sase artifact link` cannot default to `list` without a target; print
usage.

```text
sase artifact link add  <from> <to> <relation> <description>
sase artifact link add  <to> <relation> <description>          # from = current agent
sase artifact link rm   <from> <to> [<relation>]
sase artifact link list <ref>          # outgoing + incoming
sase artifact link list <ref> -j
```

- `<from>` / `<to>` are artifact references, with or without a
  leading `@`. Canonicalize through the existing
  `canonicalize_artifact_ref` path.
- `<relation>` is a positional slug. `<description>` is a positional
  string. Both required on `add`.
- `-j/--json` on `list`. No required options.
- Idempotent `add`: same triple prints "unchanged" and exits 0.
- Default-`from` when omitted is the current agent
  (`SASE_AGENT` / discoverable identity). Interactive use without an
  agent and without `<from>` is an error, same as
  `sase artifact create --bead` outside a run.
- `rm` without `<relation>` removes every edge between the pair, and
  says so.

Alphabetical fit in the `sase artifact` group: `create`, `doctor`,
**`link`**, `list`, `open`, `pane`, `path`, `prune`, `read`,
`reclaim`, `show`, `stats`, `trash`.

### 4.2 `sase artifact read`

```text
sase artifact read <ref> -r "<why this artifact is being read>"
sase artifact read <ref> -r "…" -j
```

Behavior, in order:

1. Require a non-empty reason (`normalize_read_reason`, same helper
   memory uses).
2. Resolve the reference through the same path as `show` / `path`.
3. Print the artifact. Text / markdown goes to stdout (paged with
   `bat` when stdout is a TTY, raw when piped — agents need the
   bytes). Binary kinds print a short metadata block and the
   materialized path, then exit 0; they do not dump PNG bytes into a
   prompt. Fragments (`#L10-20`, `#page=2`) slice the text the way
   prompt expansion already annotates them.
4. Append a consumption event (so `sase artifact show` and
   `list --unused` stay honest).
5. Write an artifact link `from=current agent`, `to=<ref>`,
   `relation=read`, `description=<reason>`, `source=read`.

Exit codes match `path`: 0 ok, 1 missing/ambiguous/malformed, 2 no
readable identity (`stitch:` still has a GitHub URL and a `show`
payload — `read` should print the `show` metadata plus the commit
subject rather than claiming there is nothing to read).

**What this is not.**

- Not a rename of `path`. `path` stays the compose-with-other-tools
  primitive and stays untracked.
- Not a replacement for `sase repo open`. `repo open` remains
  mandatory when the agent will *modify* files in a sidecar / linked
  / external repo, or when it is asked to *explore the artifacts in
  that repo as a tree*. `read` is "give me this one artifact and
  remember that I used it."
- Not an unauthenticated dump of `~/bob` or other `@file` roots.
  Path-backed `@file:` stays inside the existing allow-list.

### 4.3 Skill and instruction changes

When the feature lands (not in this research):

- `/sase_artifact_file` — document `read` as the default way to
  consume an artifact; keep `path` / `open` / `show` for composition
  and humans; document `link add|rm|list`.
- `/sase_new_task` — replace the `RELATED:` note recipe with
  `sase artifact link add bead:<new> bead:<old> related "<how>"`.
  Keep a one-line note that the historical `RELATED:` string is
  obsolete. The retired-umbrella path uses the same `link add`,
  relation `related`, description starting with "retired umbrella; do
  not +1".
- `/sase_repo` — one sentence: do not open a sidecar just to read a
  single `@research:` / `@plan:` / `@bead:`; use
  `sase artifact read`.
- Generated `AGENTS.md` glossary snapshot — add Artifact and
  Artifact Markdown File after `sase memory init`.
- Do **not** hand-edit memory files in the implementing epic unless
  the user explicitly asks. File a `memory` task bead for
  `generated_skills.md` / `cli_rules.md` if the new verbs need to be
  mentioned there.

---

## 5. Automatic writers

### 5.1 Prompt refs → links

In `_record_artifact_ref_uses` / the existing expansion success path
(`src/sase/artifact_ref_prompt.py`), after a successful resolve,
also `link add` from the launching agent to each canonical ref with
`relation=cited` and description
`Cited in launch prompt` (or, if a fragment is present,
`Cited in launch prompt (lines 10-20)`).

This is cheap: the agent identity, canonical ref, and fragment are
already in hand. It is the whole reason the future Agents sub-tab
can show "this research was used by these agents" as ordinary
incoming links, not as a special case.

Idempotent across retries and `%repeat`. The use-row ledger remains
the citation *count*; the link is the edge.

Pointer kinds (`@research:…` today expands without cloning) still
create the link. The target does not need a local checkout for an
edge to exist. The Links table on that research file is updated the
next time the research sidecar is materialized and the outbox
drains — same as Referenced By.

### 5.2 `sase artifact read` → links

Covered in §4.2. The reason *is* the description, so the
required-why rule holds without a second prompt.

### 5.3 RELATED → links

One migrator, `sase artifact link migrate-related` (or
`sase artifact doctor --fix-related-links`), not a silent rewrite of
history.

Parser for existing notes, already regular enough to be mechanical:

```text
RELATED: <id>[, <id> …] — <description>
RELATED: <id> — <description>
```

Some notes name a commit (`RELATED: commit 2959d3992 — …`). Those
become links to `stitch:sase@2959d3992`, not beads. Some name two
beads in one sentence; emit one edge per target, same description.

Rules:

- Source bead is the issue the note is attached to.
- Relation is `related`, source is `migrated`, description is the
  dash-clause (required; skip the rare note that has no dash-clause
  and report it).
- **Do not delete the note.** The bead event stream is append-only.
  The note stays as historical prose; the edge becomes the
  queryable object. New agents stop writing the note.
- Dry-run by default; `-a/--apply` writes. Print a table of
  parsed / skipped / applied.
- 279 notes / 150 beads on this project is a bounded, once-per-store
  job. Put it in the adoption phase, not in the wire-type phase.

---

## 6. Rust / Python split

Litmus test from `rust_core_backend_boundary`: if a web app, CLI,
editor, or another frontend would need the behavior to match the TUI,
it is core.

**sase-core (Rust + bindings)**

- `ArtifactLinkWire` and validation.
- Artifact-md-file resolution: given a ref, return the markdown path
  (self / companion / generated page) or `None`.
- Frontmatter `links:` parse / upsert (tolerant YAML subset, same
  posture as plan-header legacy YAML).
- `links` block parse / render / upsert / remove / strip — sibling
  of `referenced_by.rs`, top-anchored.
- Companion-name helper (`stem.md` vs `filename.md` on collision).
- Bead `link_added` / `link_removed` events and the projected field,
  if the bead schema is the chosen bead store (it should be).
- Query: outgoing and incoming edges for one ref.

**Python (this repo)**

- `sase artifact link` / `read` parsers and handlers.
- Prompt-ref hook and consumption+link write.
- RELATED migrator.
- Outbox drain / sidecar commit (clone the Referenced By modules,
  do not generalize them in the same PR unless it is free).
- Bead-page and agent-page renderers: emit the managed table from
  the store.
- ACE: build `link`-kind relation edges from the graph so `<` / `>`
  / `~` and the rail show described links, not just filename
  families.
- Skill templates and docs.
- Research-plugin inventory exclusion for companions (small follow-up
  in `sase-research-artifacts`).

Do not put the link graph in Python dataclasses that the TUI
re-derives from snapshots. That is how today's relation panel works
for parent/child, and it is why it cannot be queried from the CLI.

---

## 7. TUI and the future Agents sub-tab

Out of scope to *build* the tab. In scope to not paint the model
into a corner.

- Every compiled pane that can resolve an artifact md file earns
  `PaneCapability.relations` from a host-owned `links` source, in
  addition to whatever `hierarchy` / `family` it already declared.
  Label the section `Links`. Show `relation` as the row badge and
  `description` as the secondary text.
- Reveal-lens behavior already exists
  (`docs/artifacts_pane_contract.md`): jumping to a same-pane target
  hidden by the current query rewrites the query and is reversible.
  Cross-pane jumps (research → bead) already have `target_pane`.
  Use them.
- Completed agents become a document-like pane later, kind
  `agent`, inventory = published agent pages, same Links table, same
  `sase artifact read agent:<name>`. Because prompt refs and reads
  have been writing `from=agent` edges all along, the tab lights up
  with real data on the day it ships instead of waiting for a
  backfill.
- Do not block this feature on that tab. Do not store links in a
  TUI-only index that the tab would then have to scrape.

---

## 8. Alternatives considered

### A. Frontmatter-only, every kind

The request's first sketch. Works for research and plans. Dies on
beads and agents: their markdown is generated and refreshed. A link
written to `pages/sase-oz/sase-oz.md` is gone on the next
`sase bead page refresh`. Also gives no query API without walking
every sidecar.

**Reject as the only store.** Keep frontmatter as the *authored*
store for real markdown documents.

### B. Central `~/.sase/artifacts/links.jsonl` only

Easy to append from prompt refs and `read`. Invisible on GitHub
unless a projection step exists anyway. Splits "what GitHub shows"
from "what SASE believes" the moment someone hand-edits frontmatter.
Bead links would live outside the bead store, so `sase bead show`
and page refresh would not see them.

**Reject as the only store.** A global ledger is a fine *cache* or
*audit log*; it is a bad source of truth for documents that already
have a git history.

### C. Stretch bead `refs` and `RELATED:` notes

`refs` has no why. Notes have a why and no schema. Putting a YAML
document inside a note would be worse than what we have. Encoding
`bead:sase-ct?rel=related` in `refs` is a hack that breaks every
current ref parser.

**Reject.**

### D. Add a `LINKS` section to the plan header

Reuses a battle-tested renderer. Couples a general feature to SDD
provenance, forces every plan through `header-invalid` if an agent
adds a link, and does nothing for research, beads, or images.

**Reject.**

### E. Make Referenced By the link table

Tempting because it is already a GitHub table with agent names. Wrong
columns, wrong question, wrong anchor (bottom, citation-shaped).
Merging would destroy the citation ledger the moment a `related`
edge needed a description column.

**Reject.** Keep both blocks.

### F. Provider-declared `ref.properties.links`

Fits the pane-contract story and would light up the relation panel
with no host special case. Forces every plugin to opt in, cannot
express bead/agent/file links, and the current property type system
cannot hold a list of `{ref, relation, description}` without a
schema-v2 bump.

**Reject as the store.** Optionally *project* host links into the
relation panel through a host-owned synthetic source named `links`,
the same way status counters are earned from a `status` property
today.

### G. Require an artifact md file for stitches and patches in v1

Satisfies the slogan, costs a generated-pages epic, and nobody can
edit a commit. Incoming links already work via hosted commit / Patch
URLs.

**Defer.**

---

## 9. Recommended sequencing

One epic, four phases. Sizes assume the kind-native split above, not
a greenfield graph database.

1. **Core wire + markdown documents** (large). `ArtifactLinkWire`,
   frontmatter parse/upsert, top-anchored table primitive, companion
   naming, `sase artifact link add|rm|list` for `plan:` / `research:`
   / other sidecar markdown, hosted hrefs, strip+file-hook cause,
   `wip` flag. No bead schema change yet. This is enough to link two
   research reports and see the table on GitHub.

2. **Beads + RELATED migration** (large). Bead events + projected
   field, page renderer, `/sase_new_task` recipe swap, migrator
   dry-run/apply. This is the conversion the request names.

3. **Read + prompt-ref links** (medium). `sase artifact read -r`,
   consumption+link, prompt-ref `cited` edges onto the current
   agent, skill updates for `/sase_artifact_file` and `/sase_repo`.
   Agent-page projection can be a thin "links:" section on the
   existing generated README; a full Agents tab is still later.

4. **Adopt** (medium). Glossary terms (Artifact, Artifact Markdown
   File), `docs/artifact_references.md` chapter, research-plugin
   companion exclusion, doctor checks (missing companion, stale
   table, RELATED leftovers), turn the flag off-by-default `wip`
   into removal once both states have tests.

Feature flag: `sase flag new artifact-links` (`wip`). Disabled:
parsers exist and print "disabled", no sidecar writes, no bead
events, no prompt-ref edges. Enabled: full behavior. Both states
tested from phase 1.

---

## 10. Risks and non-goals

**Risks**

- **Dual representation** (frontmatter vs table) is the same class of
  bug SDD already paid for with `canonical` / `legacy` / `mixed`.
  Mitigate by making the table a pure projection: doctor
  `--fix-links` rebuilds it from the store; a hand-edited table is
  overwritten, a hand-edited `links:` list is respected.
- **Generated-page clobber** if anyone implements bead/agent linking
  by writing the page. The page renderer must be the only writer of
  the bead/agent table.
- **Research inventory pollution** from companion `*.md` files.
  Exclude them before the first binary companion is created.
- **Outbox delay.** A `sase artifact link` against a pointer
  `@research:` may return success on the graph write before GitHub
  shows the table, exactly like Referenced By. Document that.
- **Reason-flag vs cli_rules.** Call the inconsistency out in the
  implementing plan and follow `memory read` / `repo open` anyway.
- **Blog `links:` collision** if someone later makes blog posts
  artifacts. Different schema; keep a kind/path guard.

**Non-goals for this feature**

- The Agents Artifacts sub-tab.
- Generated stitch / Patch pages.
- Replacing bead dependencies, plan-header `ARTIFACTS`, or Referenced
  By.
- Deleting historical `RELATED:` notes.
- A user-facing link browser outside ACE's existing relation panel.
- Bidirectional *authored* edges (writing B when you link A→B).
  Inverse is computed, not stored.

---

## 11. Glossary text to add at adopt time

Recommended bodies, ready for `sase glossary add`:

**Artifact**

> A SASE artifact is any durable record addressable by an artifact
> reference: a sidecar document such as a plan or a research report, a
> bead, a completed agent, a Patch, a stitch, or an indexed file.
> Every artifact has a canonical typed reference and an artifact
> markdown file that holds its typed links.

Aliases: none. (Do not alias `artifact` to `ref`; that term is
already taken.)

**Artifact Markdown File** (aliases: `artifact md file`,
`artifact md`)

> An artifact markdown file is the Markdown document that carries one
> artifact's typed links. A Markdown artifact is its own artifact md
> file, via a `links` field in its frontmatter. Any other artifact
> uses a sibling `<stem>.md` next to the artifact file, or — for
> beads and agents — the generated page that is projected from the
> native store. The host renders those links at the top of the file
> as a table of GitHub hyperlinks. Agents create and read links with
> `sase artifact link` and `sase artifact read`; they do not
> hand-edit generated pages.

---

## Recommendation

Implement **kind-native stores + a host-owned Links projection**, not
a frontmatter-only scheme and not a new global database.

- Artifact markdown file = the document itself, or `<stem>.md`, or a
  generated bead/agent page.
- One Rust `ArtifactLink` edge with required `relation` +
  `description`.
- `sase artifact link add|rm|list` is the writer.
- `sase artifact read -r` is the tracked reader and always links the
  current agent.
- Prompt refs add `cited` edges from the launching agent; Referenced
  By stays the citation ledger.
- `RELATED:` notes are migrated once and then retired from
  `/sase_new_task`.
- Keep stitches/patches as link *targets* in v1.
- Flag it `wip` as `artifact-links`.
- Design the graph so `agent:<name>` is a normal node, then add the
  Agents sub-tab later for free.
