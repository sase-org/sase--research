---
create_time: 2026-08-24
updated_time: 2026-08-24
status: research
tags: [memory, glossary, agent-instructions, zettelkasten, project-config, sase-core]
---

# Memory Webs and Strands: Generalizing the Glossary into a Memory Kind

**Research question:** Should SASE generalize its project glossary into a new memory kind — "memory
webs" (hub notes) containing "memory strands" (zettel-sized notes) — rendered as either core or
structured memory per web, addressed by `sase memory read <web>:<keyword>`? If so, what is the
smallest correct implementation, and what else would be web-shaped?

**Scope:** `sase` at `6ca6e798e`, `sase-core` at its linked checkout, `bob-cli` at its opened project
checkout. Architecture research; no runtime behavior changed. Every load-bearing count below was
measured against the tree, not recalled.

---

## Bottom line

1. **Proceed.** The idea is not a speculative generalization — it is the extraction of a pattern SASE
   has already implemented three separate times by hand. The glossary, the task-type catalog, and the
   artifact-relation registry are all "generated roster in core memory + per-item on-demand read
   command + hidden detail store." That is a memory web, built three times with three different
   mechanisms. §2.2.

2. **But do not build it in the order proposed.** Build the `decisions` web *first* on greenfield,
   migrate the glossary *last*. A broken ADR web costs nothing; a broken glossary breaks core memory
   in three projects simultaneously. §4.5.

3. **The one design gap that matters: a web must declare how strands link.** The glossary's most
   valuable machinery is `resolve_glossary_closure` — BFS over definitions using a Rust-compiled alias
   phrase matcher. That works only because glossary terms appear *verbatim* inside each other's prose.
   ADR titles do not. Support both an implicit keyword-phrase closure and an explicit link closure, in
   every web, and let content decide which fires. §2.3.

4. **Rename `short-term` → `core`: yes. Rename `long-term` → `structured`: no.** "Structured" is the S
   in SASE; it describes all of it, and it does not contrast with "core." The generated Tier 2 intro
   already says "detailed **reference** material." **`core` / `reference`** costs zero explanation.
   §2.5.

5. **Keep one address per thing.** `sase memory read <note>.md` (structured note), `sase memory read
   <web>` (whole web), `sase memory read <web>:<keyword> …` (strands + closure). Never let a
   `webs/…` filesystem path resolve through `memory read`. §2.6.

6. **State one invariant loudly: a web never inlines strand bodies into core memory.** A core-rendered
   web inlines only the *web note's own body* (the hub roster). Violating this puts 1,831 words of
   glossary definitions into every provider shim on every turn, against a 2,323-word core budget. §2.7.

7. **Cost is real: ~5,900 LOC of glossary source, ~10,900 LOC of glossary tests, 124 Python modules
   that mention `glossary`, 28 landed glossary plans, and a `sase-core` wire change.** This is a
   multi-phase epic with a `sunset` feature flag, not a tale. §2.8, §4.5.

8. **Highest-value non-glossary web is `gotchas`, not `decisions`.** `gotchas.md` is a core note whose
   full body is inlined on every turn and which grows monotonically. As a web it becomes a roster in
   core and bodies on demand. `decisions` is the better *first* web (safe); `gotchas` is the better
   *first payoff*. §5.1.

---

## 1. What exists today

### 1.1 Two tiers, one axis

`sase memory init` renders `AGENTS.md` from a flat directory of Markdown notes, each carrying
`type: short | long` frontmatter:

| Tier | Frontmatter | Rendering | Read path |
| --- | --- | --- | --- |
| Tier 1 (short-term) | `type: short` | Full body inlined into `AGENTS.md` + every provider shim | Always in context |
| Tier 2 (long-term) | `type: long` | `description` only, as an H3 | `sase memory read <note>.md -r "<why>"` (audited) |

Discovery is `memory_root.glob("*.md")` — **one level, no recursion**
(`src/sase/memory/notes.py:_iter_discoverable_memory_paths`). Read validation enforces the same:
`_is_flat_note_path(parts)` is literally `len(parts) == 1`
(`src/sase/memory/read_log.py:158`). Nested notes are not merely unsupported; they are actively
rejected.

The tier headings are **structural anchors**, not decoration. `src/sase/amd/_agents_doc.py:13-17`
parses generated documents with:

```python
_SHORT_SECTION_RE = re.compile(r"^##\s+(?:\d+(?:\.\d+)*\.?\s+)?Tier 1 \(short-term\) Memory$")
_LONG_SECTION_RE  = re.compile(r"^##\s+(?:\d+(?:\.\d+)*\.?\s+)?Tier 2 \(long-term\) Memory$")
```

and `_render_managed_agents` **fails the render** if those anchors are missing. That string appears 55
times across source, tests, and generated docs, and it is physically present in every already-emitted
`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `OPENCODE.md`, and `QWEN.md` on this machine.

Current core-memory footprint in this project — the text inlined into every provider shim, every turn:

| Note | Words | Generated? |
| --- | --- | --- |
| `task_types.md` | 618 | yes |
| `build_and_run.md` | 492 | no |
| `sase.md` | 477 | yes |
| `gotchas.md` | 231 | no |
| `glossary.md` | 171 | yes |
| `artifact_relations.md` | 122 | yes |
| `rust_core_backend_boundary.md` | 116 | no |
| `feature_flags.md` | 96 | no |
| **Total** | **2,323** | — |

### 1.2 The glossary is the one outlier

Every other piece of agent-facing project knowledge lives in `sase/memory/*.md`. The glossary lives in
`sase/sase.yml` under `memory.glossary`, and that single fact generates a large amount of bespoke
machinery:

| Concern | Glossary (config-backed) | Memory notes (file-backed) |
| --- | --- | --- |
| Storage | YAML map in `sase/sase.yml` | one `.md` per note |
| Mutation | `glossary/mutation.py` (390 LOC): source-preserving YAML edit + stale-write guard | write the file |
| Validation | `sase-core` `glossary_validate` over the whole entry set | frontmatter parse + reachability |
| Schema | `glossaryEntry` + `glossary` blocks in `sase.schema.json` | none needed |
| Completion | `glossary_candidates()`, invalidated on `sase.yml` mtime | `catalog_content.py` note fetcher |
| ACE panel | `GlossaryPane` 369 + `glossary_panel_catalog` 231 | `MemoryPane` 497 + `memory_panel_catalog` 493 |
| Audit log | `glossary/read_log.py`, `sase glossary log` | `memory/read_log.py`, `sase memory log` |
| Editor | LSP catalog materialized to `glossary_catalog.json`; go-to-definition lands in `sase.yml` | plain file |
| Agent read | `sase glossary read <term> … -r` | `sase memory read <note>.md -r` |
| Proposal flow | **none** — agents cannot propose terms | `sase memory write` → `sase memory review` |

That last row is the sharpest. An agent that discovers a missing definition today has no sanctioned
path to propose it: editing `sase/sase.yml` is a config edit, and the memory rules forbid touching
memory content without explicit user permission. For file-backed notes, `sase memory write` →
`sase memory review` already exists and is exactly that path.

### 1.3 Surface area

| Measure | Count |
| --- | --- |
| Source modules named `*glossary*` | 29 (5,866 LOC) |
| Python modules mentioning `glossary` | 124 |
| Test files named `*glossary*` | 10,934 LOC |
| Rust `crates/sase_core/src/glossary.rs` | 1,186 LOC |
| Landed plans named `*glossary*` | 28 |
| Occurrences of `short-term`/`long-term` in src/tests/memory | 88 |
| Glossary terms: `sase` / `bob-cli` | 34 / 4 |

### 1.4 The track record — read this before committing

Three memory features have been built and then removed from this repo:

- `c421c12c4 feat: implement dynamic memory generation` → `e8c2f14bb feat: remove dynamic memory
  runtime`
- `7377ec8e6 feat: add deterministic episodic recall` → `37973b8b3 feat(memory)!: remove the memory
  episodes feature`
- `a88331983 feat: support negative keywords in memory xprompts` → `21e1640ee feat(memory)!: remove
  keyword metadata`

And the glossary's own placement has oscillated four times: generated long note (`abc8a9ea8`) →
Tier 2 H3 alongside long-memory files (`445afde7c`) → retired entirely for an inline Tier 2 paragraph
(`eaafcbe72`) → generated Tier 1 short note (`fee21a898`).

Two readings of that history, both useful:

- **Cautionary.** The common failure mode was building a *retrieval mechanism* before there was
  content that needed retrieving. Dynamic memory, episodes, and keyword triggers were all machinery in
  search of a corpus.
- **Confirmatory.** The glossary oscillation is not indecision; it is a missing knob. The right tier
  for a collection is a *property of the collection*, and there has never been a place to say so.
  Per-web tier configuration is the direct fix. This is the single strongest argument in the
  proposal's favor.

---

## 2. Critique

### 2.1 The core insight is right

Three independent pieces of evidence, in ascending order of strength:

1. The glossary is the only agent-facing knowledge store outside `sase/memory/`, and it pays for that
   with ~1,000 LOC of config-specific machinery (§1.2) that files would delete outright.
2. ACE already carries two near-parallel panes with a *shared* numbered-link dispatcher, parallel
   keymap scopes, parallel catalogs, and identical `.1`–`.9` link semantics (plans
   `prefixed_glossary_memory_links.md`, `dot_prefixed_glossary_memory_links.md`). When two features
   need a shared dispatcher, they are one feature.
3. §2.2.

### 2.2 SASE has already built the web pattern three times

This is the finding that converts "reasonable idea" into "extract the pattern you already have."

| Existing note | Roster in core memory | Per-item detail | Detail store |
| --- | --- | --- | --- |
| `glossary.md` (generated) | `**GLOSSARY TERMS:** Agent Clan; Agent Family; …` | `sase glossary read <term> -r "<why>"` | `memory.glossary` in `sase.yml` |
| `task_types.md` (generated) | per-type H5 with `when_to_use` + required fields | `sase bead task-type show <slug>` | `sase/task_types.json` snapshot |
| `artifact_relations.md` (generated) | closed registry of 6 relations, inline | `sase artifact link add …` | `sase/artifact_relations.json` snapshot |

Same shape, three times: a **generated hub note in core memory**, a **keyed item set**, an
**on-demand per-item read command**, and a **snapshot store that is not a memory note**. Each was
built with its own generator, its own snapshot format, its own collision blocker, and its own
instruction prose.

A memory web is precisely the generalization of that shape. Two consequences:

- The design is validated by three existence proofs rather than by analogy to Zettelkasten. Lead with
  that framing internally; it is much harder to argue with.
- It implies a capability the proposal does not mention: **some webs should be generated, not
  authored** (§5.2). `task_types` and `artifact_relations` are computed from plugin registries. If
  webs only ever come from files, those two can never converge, and SASE keeps three generators
  forever.

### 2.3 The closure semantics do not generalize — a web must declare its link model

`sase glossary read Stitch` does not print one definition. It runs
`resolve_glossary_closure` (`src/sase/glossary/resolution.py`): a deterministic BFS that scans each
definition with the Rust alias matcher, pulls in every referenced term, and records provenance
(`referrer`, `matched_text`, `also_referenced_by`). That is why the generated instruction says
batching reads is cheaper — shared terms print once.

**That machinery is name-matching machinery.** It works because "Patch" literally occurs inside the
definition of "Stitch." An ADR titled *Use Rust for the core backend* does not occur as a phrase inside
another ADR's body. A `decisions` web would get an empty closure, and every claim in the generated
instruction prose about batched reads would become false for that web.

This is the one place the proposal is genuinely under-specified. Two link models exist:

- **Implicit / keyword-phrase** (glossary): closure derived by scanning strand bodies for other
  strands' keywords and aliases. Requires strands to declare keywords.
- **Explicit / link** (ADR, most zettelkasten): closure derived from authored links.

**Recommendation: support both in every web, and let the content decide which fires.** Always resolve
explicit links. Additionally resolve keyword phrases for strands that declare `keywords:`. The
glossary web then behaves exactly as today; the `decisions` web behaves as a normal zettelkasten;
neither needs a config knob and neither needs a second code path in the renderer.

Do not invent a third link syntax. Two already exist and both fit:

- Memory notes already link by plain `sase/memory/<note>.md` mention, parsed by `_MEMORY_PATH_RE` in
  `src/sase/memory/inventory_references.py:25`, and rendered as numbered chips in `MemoryPane`.
- The **artifact relation registry already contains `supersedes` / `superseded-by`** and `related`.
  ADR supersession — the one relation ADRs genuinely need — is therefore free if strands are artifacts.
  That is a strong argument for making strands addressable as artifacts rather than inventing
  strand-local relation metadata.

### 2.4 Config → files trades one enforced invariant for N unenforced ones

Today a glossary term is a YAML map key. Uniqueness is *structural*. Ordering is deterministic. Alias
ambiguity is rejected by `validate_glossary_entries` in Rust **before** anything is written.
`sase glossary add` is a single source-preserving edit with a stale-write guard. `sase memory init`
fails closed on any diagnostic.

Move to 34 files and every one of those invariants becomes something you have to write:

| Invariant | Today | After |
| --- | --- | --- |
| Keyword uniqueness | YAML key uniqueness | must be validated across files |
| Alias non-ambiguity | Rust, whole-set | must re-run Rust over the file-derived set |
| Filename ↔ keyword agreement | n/a | new failure mode |
| Orphan strand (dir, no web note) | n/a | new failure mode |
| Empty web (web note, no dir) | n/a | new failure mode |
| Case collision (`Agent Hood` / `agent hood`) | n/a | new failure mode on case-insensitive FS |
| Web name vs. flat note stem collision | n/a | new failure mode (§3, Q7) |
| Review diff | 1 file | 34 files |

None are hard. All must be *written*, must run inside `sase memory init` **and** `sase validate`, and
must fail closed with the same semantics as today. Budget for the validator as a first-class
deliverable, not as polish — it is the difference between this being a net win and a net regression.

The good news: `validate_glossary_entries` is reusable verbatim. Discovery changes; validation does
not. Feed it strand-derived entries instead of config-derived entries and the entire Rust diagnostic
surface, alias-plural derivation, and normalization carry over.

### 2.5 "Structured memory" is the wrong name

`core memory` is right and costs nothing: the generated Tier 1 preamble **already says** "The
following memories contain core (always loaded) context." Adopting it is a rename toward the word the
system already uses.

`structured memory` is the weakest of the four proposed names:

- **S**tructured **A**gentic **S**oftware **E**ngineering. "Structured memory" parses as "SASE
  memory," which is all of it.
- It does not contrast with "core." Core memory is also structured.
- The actual contrast is *always-loaded* vs. *fetched-on-demand*.

The generated Tier 2 intro already reads: *"The below files contain detailed **reference** material."*
**`reference memory`** is therefore a zero-explanation rename, symmetric with `core`, and it survives
the arrival of webs (a "reference web" reads correctly; a "structured web" does not).

Runners-up, in order: `deep memory`, `on-demand memory`, `archive memory`. `structured memory` is
workable — this is a recommendation, not a blocker, and it is your vocabulary — but if the rename is
being done once, do it with the better word.

**Second naming point, more important than the first.** After this change the vocabulary has two
orthogonal axes that are currently conflated in one frontmatter field:

- **What a memory *is***: note, web, strand.
- **How a memory *renders***: core, reference.

Today `type: short|long` conflates them because there was only one kind of thing. Keeping those axes
verbally and structurally separate is the single most important documentation decision in this
proposal. A web is not "a core memory"; a web *renders as* core memory. Write the definitions that way
from day one or every downstream sentence will be ambiguous.

### 2.6 `sase memory read` overload

`sase memory read` today takes exactly one positional `memory_path`, requires `.md`, and rejects
anything nested. The proposal adds `<web>:<keyword>`. Left unconstrained, that yields three ways to
name one strand:

```
sase memory read decisions:0007-rust-core
sase memory read webs/decisions/0007-rust-core.md    # would work if nesting is allowed
sase memory read sase/memory/webs/decisions/0007-rust-core.md
```

and one genuine ambiguity: `sase memory read glossary` — the `glossary` *web*, or `glossary.md`?

**Recommendation — exactly one address per thing:**

| Form | Meaning |
| --- | --- |
| `sase memory read <note>.md -r "<why>"` | one reference note (unchanged; `.md` required) |
| `sase memory read <web> -r "<why>"` | every strand in a web |
| `sase memory read <web>:<kw> [<web>:<kw> …] -r "<why>"` | named strands + their closure |

Keep `_is_flat_note_path` rejecting `webs/...` paths through `memory read`. The `.md` suffix already
disambiguates note-vs-web with no new rule. Make the positional variadic; keep `-r/--reason` required.

**Also unify the audit logs.** `glossary/read_log.py` records `terms`, `related_terms`, `depth_limit`,
`definition_bytes`, `source_path`; `memory/read_log.py` records path and content hash. One command must
not write to two logs with two shapes. Recommend one log with a discriminated `kind: note | web |
strand` field, `sase memory log --kind strand` as the general query, and `sase glossary log` retained
as a filtered alias during the sunset window.

### 2.7 The rendering invariant

A core-rendered web must inline **only the web note's own body**, never its strands. The glossary web's
34 strands hold 1,831 words of definitions; inlining them would grow today's entire 2,323-word core
footprint by ~79% from one web alone. State this as an invariant in the memory README and enforce it in the
renderer, because the natural naive implementation ("a web is core, so render the web") gets it wrong.

Pleasantly, this falls out of the existing model with no new machinery: a web note is a note, a
core note inlines its body, a reference note contributes its description. Strands are simply not
part of `AGENTS.md` rendering at all. The only new requirement is that the **web note's body stay
current** as strands are added — solved in §4.2 with a managed region rather than a fully generated
file.

### 2.8 This is four changes, not one

| Change | Blast radius | Independently shippable? |
| --- | --- | --- |
| Tier rename | 88 text occurrences + 55 anchor occurrences + 2 regexes + every emitted shim | yes |
| Webs + strands as memory notes | discovery, path validation, reachability, README, panel, xprompt loader | yes |
| Link/closure model | `glossary/resolution.py`, `relations.py`, Rust matcher inputs | yes |
| Glossary migration | 5,866 src LOC, 10,934 test LOC, 124 modules, 28 plans, `sase-core` wire | **no — needs a flag** |

Bundling them makes the change unreviewable and makes a partial revert impossible. The anchor rename
alone has an interesting property: `parse_amd_agents_document` reads *already-generated* documents, so
a newer `sase` must keep accepting the old anchors or every not-yet-reinitialized project's shims
break. The regex already carries a compatibility comment for a prior form; add, do not replace.

Per this project's flag rules, the glossary migration is a textbook `sunset` flag — the old branch
(`memory.glossary` config + `sase glossary`) must stay reachable while the new path lands — and
therefore needs `sase flag new` and its flag bead at creation time.

---

## 3. Open questions, answered

**Q1. How deep may webs nest?** One level: `webs/<web>/<name>.md`. No `webs/<web>/<sub>/...`.
`_is_flat_note_path` exists because unbounded nesting made path validation and reachability ambiguous;
one bounded level keeps `<web>:<keyword>` a total function and keeps the address space flat. A strand
that wants children should link, not nest — that is the zettelkasten answer and it is also the answer
that costs nothing to implement.

**Q2. Is the filename the keyword?** No — the filename is the *slug*; the strand declares its display
keyword and aliases in frontmatter. `Agent Hood` has aliases `hood` and `agent neighborhood`, which no
filename encodes. Existing normalization already bridges the two:
`normalize_glossary_reference` casefolds and collapses runs of `-`, `_`, and whitespace to a single
space, so `agent_hood.md` and `agent-hood.md` both resolve to `agent hood`. `sase memory init` should
validate that the declared keyword slugs to the filename.

**Q3. What frontmatter does a strand carry?** `keyword` (display form; defaults to the de-slugged
filename), `aliases` (list), `description` (optional, for roster rendering). Deliberately **not**
`type` — a strand's tier is its web's tier, and letting strands override it reintroduces exactly the
per-item tier confusion webs exist to remove.

Note the apparent relapse and disarm it in the docs: `keywords` was removed from memory notes in
`21e1640ee`. That was a **runtime trigger** for the dynamic-memory injection engine, removed together
with that engine in `e8c2f14bb`. This is an **addressing alias**, evaluated at read time by an explicit
command. Same word, different mechanism. Say so in the memory README or someone will file a bead
against it in six months.

**Q4. What frontmatter does a web note carry?** `type: core | reference` (required — this is the whole
point), `description` (required when `reference`, as for any reference note), `parent` (existing
semantics). Resist adding `closure: keyword | link | both`; default to both and let content decide
(§2.3).

**Q5. How does the web note's roster stay current?** A **managed region** inside the user-authored web
note:

```markdown
<!-- sase:strands -->
… generated roster, one line per strand …
<!-- /sase:strands -->
```

This is strictly better than today's fully-generated `glossary.md`. Today a hand-authored `glossary.md`
*blocks `sase memory init` entirely* (`_glossary_collision_blocker`, `src/sase/main/init_memory/
root_planning.py:142`), because the generator owns the whole file and refuses to clobber. With a
managed region the user owns the note, SASE owns one block, and the collision blocker, the
`sase_generated:` marker, and the retired-note deletion path all disappear. It also directly satisfies
the requirement that "users configure webs by adding files."

**Q6. What happens to `sase glossary add` / `del`?** It becomes writing a file — but the real upgrade
is routing it through the **existing** `sase memory write` → `sase memory review` proposal ledger.
Agents gain a sanctioned way to *propose* glossary terms with evidence, and you approve or reject them
in the review TUI. That capability does not exist today at any price (§1.2). Keep a thin
`sase memory strand add` for direct authoring.

**Q7. Do webs collide with `#memory/<stem>` xprompts?** Yes, and it must be blocked. `load_memory_
xprompts` derives `memory/<stem>` names from flat notes; a web at `webs/glossary.md` naturally wants
`#memory/glossary`, which collides with a flat `glossary.md`. Recommendation: **web notes get
`#memory/<web>`** (they are hub notes and are genuinely useful in prompts), **strands get no
xprompt** (they are for `sase memory read`), and `sase memory init` rejects a web whose name collides
with a flat note stem. This also gives the glossary migration a free deletion: the flat `glossary.md`
goes away exactly as `webs/glossary.md` arrives.

**Q8. Home vs. project webs: shadow or merge?** Existing flat notes are **first-wins by stem** —
project shadows home. For webs, shadowing is wrong: **merge per strand, project wins on keyword
collision.** Concretely, home `glossary` (Bryan's Obsidian vocabulary) and project `glossary` (SASE
vocabulary) must union, not shadow. This is a deliberate divergence from the flat-note contract and
needs to be a stated decision, not an accident.

This unlocks something impossible today. `bob-cli`'s four glossary terms — `Pomodoro`, `Schedule Log`,
`Task Link`, `Work Log` — are not bob-cli vocabulary. They are **Bryan's Obsidian workflow
vocabulary**, and they are stranded in one project's `sase.yml` because config-backed glossaries have
no home scope. As strands under `~/sase/memory/webs/glossary/`, they become available to every project
that touches the vault. That is a concrete capability gain from the file model, not a refactor.

**Q9. Case-insensitive filesystems?** `Agent Hood` and `agent hood` slug to the same path. Reject slug
collisions after normalization during init — which is exactly what `validate_glossary_entries` already
does for terms. Reuse it.

**Q10. Does `sase-core` change?** Yes, but modestly. `GlossarySourceWire` carries `config_path` +
`config_key_path` + editor ranges so LSP go-to-definition can land inside `sase.yml`. That generalizes
to a source path plus optional key path; bump `GLOSSARY_WIRE_SCHEMA_VERSION`. The matcher, alias-plural
derivation, normalization, and diagnostics are reused unchanged. This is coordinated-release work
across two repos — factor it into sequencing.

Worth noting this is the one place the migration *improves* editor UX: go-to-definition on a glossary
term currently lands on a YAML scalar; afterward it lands on a real Markdown note with its own
backlinks.

**Q11. What happens to `sase glossary all` / `list` / preview card / LSP hover / prompt highlighting?**
All keep working. Their data source changes from a config-derived catalog to a file-derived catalog;
the `EditorGlossaryCatalog` compile-and-scan path is untouched. Cache invalidation moves from
`sase.yml` mtime to the strand directory's mtime — cheaper and more precise.

**Q12. Should strands be artifacts?** Probably yes, eventually — it is how `supersedes` /
`superseded-by` becomes free for ADRs (§2.3), and how strand↔bead and strand↔plan links become
first-class. But it is **not** required for phases 1–3 and adding it early couples this epic to the
artifact store. Defer; design the strand address (`<web>:<keyword>`) so it can become an artifact
`<kind>:<argument>` later without changing.

---

## 4. Recommended solution

### 4.1 Vocabulary (lock this before writing code)

| Term | Definition |
| --- | --- |
| **core memory** | A memory rendered into Tier 1 of every agent instruction file; always in context. Replaces "short-term memory." |
| **reference memory** | A memory rendered into Tier 2 as a description only, fetched with an audited `sase memory read`. Replaces "long-term memory." (Recommended over "structured memory" — §2.5.) |
| **memory web** | A memory note at `sase/memory/webs/<web>.md` that indexes the strands in `sase/memory/webs/<web>/`. Renders as core or reference memory per its own frontmatter. |
| **memory strand** | A small, keyword-addressed memory note at `sase/memory/webs/<web>/<name>.md`. Never rendered into agent instruction files; read on demand as `<web>:<keyword>`. |
| **keyword** | A strand's display name plus its aliases; the address used after the `:` in `<web>:<keyword>`. |

Dogfood step: add these five as glossary terms **using the current glossary**, before any code lands.
If the definitions are hard to write against the existing vocabulary, the design is not settled.

### 4.2 On-disk contract

```
sase/memory/
  <note>.md                       # flat note; type: core | reference        (unchanged)
  webs/
    glossary.md                   # web note; type: core; managed roster region
    glossary/
      agent_hood.md               # strand; keyword: Agent Hood; aliases: [hood, …]
      stitch.md
    decisions.md                  # web note; type: reference
    decisions/
      0007_rust_core_backend.md   # strand; keyword: 0007-rust-core-backend
```

- Exactly one nesting level under `webs/`.
- `webs/<web>.md` and `webs/<web>/` must both exist; either alone is an init error.
- Web note frontmatter: `type: core | reference`, `description` (required when `reference`), `parent`.
- Strand frontmatter: `keyword`, `aliases`, `description`; no `type`.
- The web note owns its prose; SASE owns one `<!-- sase:strands -->` region (§3, Q5).

### 4.3 CLI contract

```bash
sase memory read <note>.md            -r "<why>"     # reference note        (unchanged)
sase memory read <web>                -r "<why>"     # every strand in a web (new)
sase memory read <web>:<kw> [<web>:<kw> …] -r "<why>"  # strands + closure   (new)

sase memory list                                     # learns webs and strand counts
sase memory strand add <web> <keyword> …             # direct authoring
sase memory write --target <web>:<kw> …              # proposal path, reviewed by the user
```

`sase glossary *` remains a working alias family behind the sunset flag, then is deleted.

### 4.4 Rendering contract

- Core web → inline the web note's body (roster + prose) into Tier 1. **Never strand bodies** (§2.7).
- Reference web → the web note's `description` becomes a Tier 2 H3, exactly like a flat reference note.
- Strands never appear in `AGENTS.md` or any provider shim, at any tier.
- Tier anchors become `## Tier 1 (core) Memory` / `## Tier 2 (reference) Memory`, with the old regexes
  **retained as accepted alternates** so already-emitted documents still parse.

### 4.5 Phasing

| Phase | Content | Size | Ships alone? |
| --- | --- | --- | --- |
| **0** | Lock vocabulary. Add the five terms to the *current* glossary. No code. | xsmall | yes |
| **1** | Tier rename only. New anchors + old regexes retained; `type: core\|reference` accepted alongside `short\|long`; regenerate all three projects. Verify with `sase memory init --check`. | small | yes |
| **2** | Webs + strands as pure memory notes. Discovery, path validation, reachability, README, `sase memory list`, `MemoryPane`, `#memory/<web>`, `sase memory read <web>` and `<web>:<kw>`. **Seed with a greenfield `decisions` web — no glossary involvement.** | medium | yes |
| **3** | Link model. Explicit link closure for all webs; keyword-phrase closure for strands declaring `keywords`. Reuse `resolve_glossary_closure` (rename to `resolve_strand_closure`) and the Rust matcher unchanged. | medium | yes |
| **4** | Glossary migration behind a `sunset` flag. `sase glossary migrate` generates strands from `memory.glossary`; `sase glossary` aliases to the web; init fails closed if both config terms and strand files exist. Flip after `sase` **and** `bob-cli` are migrated and green. | large | no — flagged |
| **5** | Retire. Delete `glossary/mutation.py`, `glossary_config.py`, the `glossary`/`glossaryEntry` schema blocks, the `sase.yml`-mtime completion source; merge `GlossaryPane` into `MemoryPane`; close the flag bead. | medium | yes |

**The load-bearing sequencing claim: `decisions` before `glossary`.** The proposal's instinct is
glossary-first because the glossary is the motivating case. That is the riskier order. A broken ADR
web costs nothing — nobody depends on it yet. A broken glossary web breaks core memory in three
projects at once, and the glossary is simultaneously the *most* coupled surface (LSP, prompt
highlighting, completion, ACE panel, Rust wire). Prove the machinery on the case where failure is free.

Also: §1.4's failure mode was mechanism-before-corpus. Phase 2 dodges it only if the `decisions` web
ships with ~10 real ADRs written from actual repo history — the Rust core boundary, the two-speed
verification split, the flat-memory decision, the task-type-vs-issue-type split, the episodes removal.
Those decisions exist and are currently only recoverable from commit messages. Writing them is worth
doing regardless of whether this epic proceeds.

### 4.6 Flags and beads

- Phase 4 needs `sase flag new <key>` (kind `sunset`) and its flag bead, with `remove_by_date` and
  `remove_by_release` set at creation.
- Phase 1's anchor change probably does *not* need a flag — the anchors are regenerated by
  `sase memory init` and keeping both regexes is a pure compatibility addition. Confirm against
  `sase/memory/sase_flags.md` before deciding; the "deprecation whose old branch must stay reachable"
  clause is arguably triggered.

---

## 5. Additional use cases

### 5.1 Near-term candidates

Ordered by payoff, not by ease. The test for "is this web-shaped" is: *many small keyed items, a few
read at a time, indexed by a hub that is worth having in core memory.*

| Web | Tier | Why web-shaped | Payoff |
| --- | --- | --- | --- |
| **`gotchas`** | core | 4 bolded subsections today, growing monotonically, **fully inlined every turn** (231 words and rising) | **Highest.** Roster in core, bodies on demand. Directly reduces per-turn tokens and removes the pressure to keep gotchas short. |
| **`decisions`** (ADRs) | reference | Many small keyed records; `supersedes`/`superseded-by` already in the artifact relation registry | Best *first* web: greenfield, zero migration risk, immediately useful |
| **`glossary`** | core | 34 keyed terms, aliases, phrase closure | The motivating case; do it last (§4.5) |
| **`commands`** | core | `build_and_run.md` is 492 inlined words describing ~8 commands | Roster of command names in core; `just check-full` semantics on demand |
| **`runbooks`** | reference | Keyed by *symptom* — and symptoms are phrases, so keyword closure genuinely fires | "CI failed with X" → strand, with links to related failures |
| **`apis`** | reference | `sase_core_rs` binding names and wire schemas appear verbatim in code and prose | Keyword closure works well; pairs with the Rust boundary rule |
| **`flags`** | reference | One strand per registered flag, keyed by flag key | Careful: link to the flag bead, do not duplicate it |
| **`plugins`** | reference | One strand per required plugin distribution | Replaces prose enumeration in `sase.md` |
| **`obsidian`** (home scope) | reference | `~/sase/memory/obsidian.md` is one reference note covering a vocabulary — `Pomodoro`, `Task Link`, `Work Log`, `Schedule Log` | Absorbs bob-cli's four stranded terms (§3, Q8) |
| **`incidents`** | reference | Date-keyed postmortems, `related`-linked to `decisions` | Only once there are incidents worth recording |

Sub-glossaries deserve a note: webs make `glossary_axe` and `glossary_ace` free. Today splitting the
SASE glossary means 34 keys in one map with no way to scope a read. With webs,
`sase memory read glossary_axe` is a scoped batch read and the ACE-focused agent never pays for AXE
vocabulary.

### 5.2 The extension worth designing for: generated webs

§2.2 showed that `task_types` and `artifact_relations` are hand-rolled webs whose items come from
*plugin registries*, not files. If webs are file-only, those two generators live forever.

Recommendation: design the web *discovery* seam so a web's strands can come from a **provider** rather
than a directory — the same pattern `ref:` artifact providers and `sase_task_types` plugins already
use (`use: <plugin>@<provider>`). Then:

- `task_types` becomes a generated web whose strands are the catalog entries; the roster renders into
  core memory and `sase memory read task_types:bug` replaces `sase bead task-type show bug`.
- `artifact_relations` becomes a generated web over the closed relation registry.
- Plugins gain a first-class way to contribute agent-facing knowledge without shipping their own memory
  generator.

Do not build this in phases 1–5. Just do not foreclose it: keep discovery behind an interface that
returns `(web, strands)` rather than hard-coding a `glob`.

### 5.3 What should *not* be a web

Stating the negative space prevents the failure mode where everything becomes a web:

- **Narrative or procedural notes.** `tui_perf.md`, `symvision.md`, and `xprompts.md` are arguments
  read start-to-finish. Chopping them into keyed strands destroys the reading order that carries the
  meaning. They stay reference notes.
- **Anything with exactly one item.** A web with one strand is a note with extra ceremony.
- **Anything already a first-class artifact.** Beads, plans, Patches, and stitches have their own
  stores, their own retention, and their own link tables. Link to them from a strand; do not mirror
  them into one.
- **Volatile state.** Webs are committed files. Anything that changes per-run belongs in `~/.sase/`,
  not in memory. This is the specific mistake the dynamic-memory and episodes features made (§1.4).

---

## 6. Risks and how this fails

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Core-memory blowup from a web inlining strand bodies | high | §2.7 invariant + a renderer test that asserts strand bodies never appear in `AGENTS.md` |
| Glossary migration lands broken across three projects | high | Phase 4 sunset flag; `decisions` web proves the machinery first; migrate `bob-cli` before flipping |
| Validator gap lets duplicate/ambiguous keywords through | medium | Reuse `validate_glossary_entries` over file-derived entries; fail closed in `sase memory init` **and** `sase validate` |
| Anchor rename breaks already-emitted provider shims | medium | Retain old regexes as alternates; never replace |
| `sase-core` wire change desynchronizes the two repos | medium | Bump `GLOSSARY_WIRE_SCHEMA_VERSION`; land the core change and its Python adapter before phase 4 |
| Mechanism-before-corpus (the §1.4 pattern) | medium | Phase 2 must ship ~10 real ADRs, not an empty web |
| Vocabulary drift: "web" used for both the kind and the rendering | low | §2.5's two-axis rule, written into the memory README before phase 2 |
| Scope creep into artifacts | low | §3 Q12: defer; keep the address shape forward-compatible |

The honest failure scenario: phases 1–3 land, the `decisions` web accumulates six ADRs and then
stalls, the glossary migration is never worth phase 4's cost, and SASE carries both a webs subsystem
and a config glossary indefinitely. Mitigation is the phase gate — **do not start phase 4 until the
`decisions` web has been in real use long enough that you would miss it.** Phases 1–3 are individually
worth their cost even if phase 4 never happens, which is what makes this sequencing safe.

---

## 7. What was checked

Verified against the tree at `6ca6e798e`:

- `src/sase/memory/notes.py` — flat `glob("*.md")` discovery; `type: short|long`; `_RETIRED_FRONTMATTER_KEYS = {"keywords"}`
- `src/sase/memory/read_log.py:158` — `_is_flat_note_path` is `len(parts) == 1`
- `src/sase/amd/_agents_doc.py:13-17` — tier anchor regexes; `_render_managed_agents` fails without them
- `src/sase/amd/inline_memory.py` — core notes inline full bodies, headings shifted +2
- `src/sase/glossary/resolution.py` — `resolve_glossary_closure` BFS with provenance
- `src/sase/glossary/relations.py` — inbound reference index via definition scanning
- `src/sase/glossary/mutation.py` — source-preserving YAML edit + stale-write guard
- `src/sase/main/init_memory/root_planning.py:96-160` — retired-note deletion and `_glossary_collision_blocker`
- `src/sase/main/init_memory/root_rendering_notes.py` — generated note specs for glossary, artifacts, beads, sizes
- `src/sase/memory/inventory_references.py:25` — `_MEMORY_PATH_RE` note-to-note link parsing
- `src/sase/xprompt/loader_memory.py` — `#memory/<stem>` derivation, first-wins by stem
- `src/sase/completion/candidates/catalog_content.py` — glossary candidates keyed on `sase.yml` mtime
- `src/sase/integrations/xprompt_lsp.py:348-369` — LSP glossary catalog materialization
- `crates/sase_core/src/glossary.rs` — `GlossarySourceWire` carries `config_path` + `config_key_path`
- `sase/sase.yml`, `bob-cli/sase/sase.yml` — 34 and 4 terms respectively
- Commit history: `21e1640ee`, `e8c2f14bb`, `37973b8b3`, `eaafcbe72`, `fee21a898`, `abc8a9ea8`, `445afde7c`
- Plans: `prefixed_glossary_memory_links.md`, `dot_prefixed_glossary_memory_links.md`, `glossary_tier1_memory_note.md`

Not verified (out of scope): whether the ACE keymap `glossary` scope can be renamed without a config
migration for existing users; the exact `sase validate` hook point for a web validator; whether
`sase-research-artifacts` or `sase-github` reference glossary APIs.
