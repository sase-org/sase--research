---
create_time: 2026-08-24
updated_time: 2026-08-24
status: research
tags: [memory, glossary, zettelkasten, adr, agent-context, architecture, sase-core]
---

# Generalizing the Glossary into Memory Webs and Strands

**Research question:** Should SASE generalize its glossary into file-backed "memory webs"
(hub notes) holding "memory strands" (zettel-sized notes), rendered as core or structured
memory per web and addressed by `sase memory read <web>:<keyword>`? If so, what is the
cheapest correct implementation, and what else is web-shaped?

**Scope:** Consolidation of two independent reports plus lead-researcher verification.
Architecture research only; no behavior changed. Evidence measured at `sase@6ca6e798e`,
`sase-core` and `bob-cli` at their opened checkouts, on 2026-08-24.

**Sources merged:** `glossary_to_memory_webs__a.md` (report A) and
`glossary_to_memory_webs__b.md` (report B), in this directory. Where they disagree, the
resolution below is decided on measured evidence, not by splitting the difference.

---

## Bottom line

**Proceed.** Both reports independently reached that verdict and so do I, for the same
reason report B stated best: this is not a speculative generalization, it is the
extraction of a pattern SASE has already implemented three separate times by hand
(§2.2). That framing is far more defensible than the Zettelkasten analogy and should
lead any internal write-up.

Seven decisions, in descending order of how much they change the plan:

1. **Drop the `webs/` path segment.** Put the web note at `sase/memory/<web>.md` and its
   strands at `sase/memory/<web>/<strand>.md`. This is my main departure from the
   proposal and from both reports, and it is worth roughly half the implementation cost.
   Six separate regexes in the AMD document layer hard-code a memory path as
   `memory/[A-Za-z0-9_.-]+\.md` — a character class that excludes `/`. Keeping web notes
   flat means none of them change, `#memory/<web>` keeps working, and today's
   `sase/memory/glossary.md` *becomes* the glossary web note in place. §4.1.

2. **Build `decisions` first; migrate the glossary last.** Report B's sequencing is
   right and report A's is not. A broken ADR web costs nothing. A broken glossary breaks
   core memory in three projects at once and is simultaneously the most coupled surface
   in the repo (5,866 src LOC, 124 modules, LSP, completion, ACE, a Rust wire). §5.

3. **The flag is `beta`, not `sunset`.** Report B called this a "textbook `sunset`
   flag." `sase/memory/sase_flags.md` defines `sunset` as default **on** — "the behavior
   is already the default." At creation the web-backed glossary is unproven and must be
   opt-in, which is exactly `beta`. Both kinds remove identically (delete the Off branch,
   make On unconditional), so `beta` gets the right default with no downside. §5.

4. **Do not build a new link model in v1.** Report A proposed a three-valued
   `linking:` knob; report B proposed running both closure engines always. Neither is
   needed. Keep mention-closure as the glossary's behavior (reuse
   `resolve_glossary_closure` and the Rust matcher unchanged) and ship `decisions` with
   *no* closure. Explicit links already exist as `supersedes` / `superseded-by` in the
   artifact relation registry; adopt them in v2 when there is a corpus that needs them.
   §3.4.

5. **Scope resolution is per-strand merge, project wins** — report B's answer, but the
   reasoning in both reports was wrong. Flat notes are not "shadowed"; they are resolved
   *per path*, project root then home root (`_memory_read_roots`). Per-strand merge is
   therefore the choice that is *consistent* with the existing contract, not a divergence
   from it. §3.2.

6. **A core web inlines the web note's body only, never strand bodies.** Report B's
   invariant, and it is the one that prevents the obvious catastrophic implementation.
   The glossary's 34 definitions are 1,831 words against a measured 2,273-word total core
   budget. §3.6.

7. **`core` yes; `structured` is your call but both reports and I recommend
   `reference`.** Three independent analyses converged on this. It is a vocabulary
   decision with identical migration cost either way, so make it once, now. §3.1.

**The honest failure mode**, from report B and worth keeping: phases 1–3 land, the
`decisions` web reaches six ADRs and stalls, the glossary migration never justifies its
cost, and SASE carries both a webs subsystem and a config glossary forever. The phase
gate is the mitigation — do not start the glossary migration until you would miss the
`decisions` web if it vanished.

---

## 1. Verified state

Every number below was measured, not recalled. Where the two reports disagreed on a
figure, the measurement is given.

### 1.1 Corpus

| Measure | Value |
| --- | --- |
| Glossary terms, `sase` | **34** (report A said 19 — incorrect; report B said 34 — correct) |
| Glossary terms, `bob-cli` | 4 |
| Glossary definitions, total | 1,831 words / 11,582 bytes |
| Terms carrying aliases | 16 of 34 |
| Definition length | min 9 / median 50.5 / max 118 words |
| Core memory (`type: short`), 8 notes | **2,273 words** |
| Structured memory (`type: long`), 9 notes | 5,119 words |

Core notes by size: `task_types.md` 612, `build_and_run.md` 486, `sase.md` 471,
`gotchas.md` 225, `glossary.md` 163, `artifact_relations.md` 116,
`rust_core_backend_boundary.md` 110, `feature_flags.md` 90.

### 1.2 Cost

| Measure | Value |
| --- | --- |
| Source modules named `*glossary*` | 29 (5,866 LOC) |
| Python modules mentioning `glossary` | 124 |
| `crates/sase_core/src/glossary.rs` | 1,186 LOC, `GLOSSARY_WIRE_SCHEMA_VERSION = 1` |
| `short-term`/`long-term` occurrences in `src/`, `tests/`, `sase/memory/` | 84 |
| `Tier 1 (short-term)` literal occurrences | 46 |

Report B's figures (5,866 / 124 / 1,186) reproduce exactly. Its test-LOC figure is the
one number I could not reproduce (I measure 20,574 for `find tests -name "*glossary*"`);
either way the order of magnitude — tests roughly 2–3× the source — is the load-bearing
fact.

### 1.3 Mechanisms both reports characterized correctly

- Discovery is `memory_root.glob("*.md")` — one level, no recursion
  (`src/sase/memory/notes.py:220`).
- `_is_flat_note_path(parts)` is literally `len(parts) == 1`
  (`src/sase/memory/read_log.py:158`). Nesting is actively rejected, not merely absent.
- Tier anchors are structural: `_SHORT_SECTION_RE` / `_LONG_SECTION_RE` in
  `src/sase/amd/_agents_doc.py:13-19`, and `_render_managed_agents` fails without them.
  Both regexes tolerate a numbered prefix (`## 1. Tier 1 …`).
- `resolve_glossary_closure` is a BFS over definitions using the Rust alias matcher, with
  provenance; this is why batched reads are advertised as cheaper.
- `sase/memory/glossary.md` is fully generated, carries `sase_generated: glossary`
  frontmatter, and `_glossary_collision_blocker`
  (`src/sase/main/init_memory/root_planning.py:142`) hard-fails `sase memory init` if a
  hand-authored `glossary.md` exists.
- `sase memory write` → `sase memory review` is a real, built proposal ledger
  (`src/sase/memory/proposals/{ledger,review,validation,write}.py`). Report A did not
  mention it; report B's point stands — agents have a sanctioned path to propose *note*
  content and no path at all to propose a glossary term.
- `sase/task_types.json` and `sase/artifact_relations.json` exist, confirming report B's
  "three hand-built webs" claim structurally.
- Flag kinds are `beta` (default off) and `sunset` (default on). Removing either deletes
  the Off branch and makes On unconditional.
- Artifact identity is `<kind>:<argument>` — the same grammar as the proposed
  `<web>:<keyword>`.

### 1.4 Facts neither report established

These are new and several change the plan.

**(a) Six regexes, not one nesting check, are the real cost of nesting.** Every AMD path
matcher hard-codes a flat filename:

| Location | Purpose |
| --- | --- |
| `amd/_agents_doc.py:22` | legacy `- @memory/<f>.md` core bullet |
| `amd/_agents_doc.py:28` | `### Title (<basename>)` inlined-core header |
| `amd/_agents_doc.py:30` | `**\`memory/<f>.md\`** description` Tier 2 entry |
| `amd/_agents_doc.py:33` | H3/H4 `` `memory/<f>.md` `` form |
| `amd/inventory.py:60` | memory-path reference scanning |
| `memory/inventory_references.py:25` | note-to-note link parsing (`/` explicitly excluded) |

Verified directly: `**\`sase/memory/cli_rules.md\`**` matches; `**\`sase/memory/webs/decisions.md\`**`
does not. Any nested path that reaches a generated document breaks round-trip parsing of
every already-emitted `AGENTS.md` and provider shim.

**(b) The inlined-core header carries a basename only** — `### {title} ({basename})`
(`src/sase/amd/inline_memory.py:115-119`). So `glossary.md` and `webs/glossary.md` both
render as `(glossary.md)`. This is a genuine round-trip ambiguity, and it is a sharper
justification for report B's Q7 collision rule than the xprompt-name argument B gave.

**(c) Home and project instruction files are separate documents.** `~/AGENTS.md` and
`~/CLAUDE.md` exist alongside the project's, each with its own Tier 1 / Tier 2 sections,
and *both* render a `sase.md`-derived section from their own scope. There is no
merge at generation time. This reframes the whole scope debate (§3.2): only three
surfaces ever force a single winner, and they resolve differently.

**(d) `#memory/<stem>` xprompts are first-wins by stem** — "let project memory replace
same-stem home memory" (`src/sase/xprompt/loader_memory.py:43-45`). This is the surface
report B was describing; it is not how instruction rendering works.

**(e) `sase memory read` resolves per path: project root, then home root**
(`_memory_read_roots`, `src/sase/memory/read_log.py:161`). A project `foo.md` hides a
home `foo.md`, but a home `bar.md` with no project counterpart stays reachable. That is
already per-item merge with project-wins-on-collision.

**(f) `sase glossary read` is already variadic.** `nargs="+"`, plus `-d/--depth`
(unlimited default, `-d 0` = requested only), `-f/--format {json,markdown,rich}`,
`-p/--project`, required `-r`. `sase memory read` has a single positional, required `-r`,
and none of the rest. The CLI migration is therefore an enumerable gap — make the
positional variadic and port four options — not a redesign.

**(g) Reserved web names follow from the artifact grammar.** Because artifact identity is
`<kind>:<argument>`, and builtin kinds are `stitch`, `patch`, `bead`, `agent`, `file`
plus plugin kinds `plan` and `research`, a web named any of those forecloses ever
promoting strands to artifacts. Reserve them, plus `assets` (which already exists as a
directory under `sase/memory/`) and `README`.

**(h) bob-cli already receives generated memory notes from SASE** —
`artifact_relations.md`, `sase_beads.md`, `sase_sizes.md`, `task_types.md` are all
present in its `sase/memory/`. Any "generated webs" extension (§6.2) must work in
downstream projects, not just in `sase`.

**(i) There is directly relevant prior research.** `202608/directed_zettelkasten_first_post/`
(2026-08-02) is Bryan's own consolidated research on applying Zettelkasten, and its
conclusion transfers: *"The single mechanism that transfers is atomicity… Everything else
— emergent structure, dense linking, Folgezettel IDs, the fleeting→literature→permanent
pipeline — is built for a different problem and importing it is the main risk."* It also
names the failure mode: *"the methodology is the failure mode it treats."* Neither report
cited it. It independently corroborates report B's mechanism-before-corpus warning and it
is the strongest available argument for §3.4's minimal link model.

---

## 2. Why this is right

Report B's central argument is the one to lead with, and it survives verification.

### 2.1 SASE has already built this pattern three times

| Existing core note | Roster in core memory | Per-item read | Detail store |
| --- | --- | --- | --- |
| `glossary.md` (generated) | `**GLOSSARY TERMS:** Agent Clan; …` | `sase glossary read <term> -r` | `memory.glossary` in `sase.yml` |
| `task_types.md` (generated) | per-type H5 with `when_to_use` | `sase bead task-type show <slug>` | `sase/task_types.json` |
| `artifact_relations.md` (generated) | closed 6-relation registry | `sase artifact link add …` | `sase/artifact_relations.json` |

Same shape three times: generated hub in core memory, keyed item set, on-demand per-item
read, and a detail store that is not a memory note. Each shipped its own generator, its
own snapshot format, and its own collision blocker. A memory web is precisely that
pattern, named and built once.

### 2.2 The oscillation is a missing knob

The glossary note has moved between tiers four times (`abc8a9ea8` → `445afde7c` →
`eaafcbe72` → `fee21a898`). Report B's reading is correct: the right tier for a
collection is a property of the collection, and there has never been anywhere to say so.
Per-web tier configuration is the direct fix, and it is the single cleanest argument in
the proposal's favor.

### 2.3 The glossary is the only agent-facing knowledge store outside `sase/memory/`

That one fact generates ~1,000 LOC of config-specific machinery — source-preserving YAML
mutation with a stale-write guard, a JSON schema block, `sase.yml`-mtime completion
invalidation, and a second ACE pane — that files delete outright. The migration also
*improves* editor UX: go-to-definition currently lands on a YAML scalar; afterward it
lands on a real Markdown note.

### 2.4 What the Zettelkasten framing actually buys

Both reports invoked it; report A's treatment was more careful. Three properties
transfer: a note needs an address independent of its prose; small notes should be
independently retrievable; a hub is an entry point, not a folder label. ADRs are a strong
second case — Nygard's original proposal is small, sequentially identified, one decision
per file, superseded records retained, which is almost exactly a structured web.

What does not transfer: arbitrary backlinks, graph visualization, Folgezettel IDs, tag
taxonomies, wiki-link syntax. §1.4(i) says the same thing from prior in-house research.
Keep v1 narrow.

---

## 3. Conflicts between the reports, resolved

### 3.1 Naming: `core` yes, `structured` contested

Both reports and I independently converged on the same recommendation, so it deserves a
straight statement rather than a hedge.

`core memory` is unambiguously right and nearly free: the generated Tier 1 preamble
already reads *"The following memories contain core (always loaded) context."*

`structured memory` is the weak one, for three reasons: "Structured" is the S in SASE, so
it parses as "SASE memory," which is all of it; it does not contrast with "core," since
core memory is also structured; and the actual contrast is always-loaded versus
fetched-on-demand. Meanwhile the Tier 2 preamble already reads *"The below files contain
detailed **reference** material."* `reference` is a zero-explanation rename, symmetric
with `core`, and it survives webs — "a reference web" reads correctly where "a structured
web" does not.

**This is your vocabulary and it is not a blocker.** The migration cost is identical
either way. But it is a one-time decision, and if it is being made once, three
independent analyses recommend `reference`.

**The more important naming point** (report B, and I agree): after this change there are
two orthogonal axes currently conflated in one frontmatter field — what a memory *is*
(note, web, strand) and how it *renders* (core, reference). A web is not "a core memory";
a web *renders as* core memory. Write it that way in the README from day one or every
downstream sentence is ambiguous.

### 3.2 Scope: per-strand merge, project wins

Report A recommended atomic whole-web shadowing; report B recommended per-strand merge.
Both justified their position by appeal to "the existing flat-note contract," and both
characterized that contract loosely.

Measured, there are three surfaces and they behave differently:

| Surface | Behavior |
| --- | --- |
| Instruction rendering | Home and project render **separate documents**; no merge, no shadowing (§1.4c) |
| `#memory/<stem>` xprompts | Single namespace, **first-wins by stem**, project replaces home (§1.4d) |
| `sase memory read <path>` | **Per-path** resolution: project root, then home root (§1.4e) |

The read path — the one that matters for `<web>:<keyword>` — is already per-item with
project-wins-on-collision. So **report B's answer is correct, and it is the
*conservative* choice, not the divergence B thought it was.** Report A's whole-web
shadowing would be a new and stricter rule.

The motivating case also holds up. bob-cli's four terms are `Pomodoro`, `Schedule Log`,
`Task Link`, `Work Log` — verified, and all four are plainly Obsidian-vault vocabulary
rather than bob-cli code vocabulary. Home scope already carries `~/sase/memory/obsidian.md`
covering exactly that domain. As home-scope strands they serve every project that touches
the vault. That is a capability gain, not a refactor.

**One consequence neither report drew:** because home and project render separate
instruction files, a home web and a project web of the same name each render their own
roster into their own document. The agent sees the union across both files, which is
correct, but a keyword defined at both scopes appears twice with different bodies while
reads resolve to the project one. Emit a warning at `sase memory init` for cross-scope
keyword collisions; do not fail.

### 3.3 Directory existence: the descriptor is the marker

Report A: the web note alone constitutes the web; a missing companion directory means
zero strands. Report B: both must exist or it is an init error.

**Report A is right, for the reason it gave:** git does not track empty directories, so
requiring the directory makes a valid, empty, newly created web unversionable. The
descriptor is the existence marker. A directory with no descriptor is the error case.
Once a strand exists the directory materializes naturally.

### 3.4 Link model: build neither proposal in v1

Report A proposed `linking: mentions | explicit | none` on the web note. Report B
proposed always resolving explicit links plus keyword-phrase closure for strands that
declare keywords.

Both reports correctly identified the real problem: `resolve_glossary_closure` is
*name-matching* machinery. It works because "Patch" literally occurs inside the
definition of "Stitch." ADR titles do not occur inside each other's prose, so a
`decisions` web gets an empty closure and the generated "batching is cheaper" prose
becomes false for it.

**My resolution is simpler than either.** In v1:

- Keep mention-closure exactly as it is, as the glossary web's behavior. Reuse
  `resolve_glossary_closure` and the Rust matcher unchanged; only discovery changes.
- Ship `decisions` with **no closure at all**. ADRs are read by name. A reader who wants
  the superseded record follows a prose reference — which is what an ADR log is for.
- Do not invent a strand-local link field.

This is not a compromise, it is the mechanism-after-corpus discipline that §1.4(i) and
report B's §1.4 both argue for. When the `decisions` web has enough records that manual
traversal hurts, adopt the **existing** `supersedes` / `superseded-by` relations from the
artifact relation registry rather than a parallel link syntax. The address shape
`<web>:<keyword>` is already artifact-compatible (§1.4g), so this costs nothing to defer
and everything to guess wrong now.

Report A's `-d/--depth` override already exists on `sase glossary read` and should carry
over verbatim.

### 3.5 The roster: managed region, not a fully generated file

Report A: never write generated content into the user's note; emit the roster only into
agent instruction files. Report B: a `<!-- sase:strands -->` managed region inside the
user-authored web note.

**Report B is right, and its argument is the decisive one:** today a hand-authored
`sase/memory/glossary.md` *blocks `sase memory init` entirely*
(`_glossary_collision_blocker`, verified at `root_planning.py:142`) because the generator
owns the whole file. A managed region inverts that — the user owns the note, SASE owns
one block — and it deletes the collision blocker, the `sase_generated:` marker, and the
retired-note deletion path along with it. It is also the only version that satisfies the
stated requirement that users configure webs *by adding files*.

Report A's underlying concern is legitimate but is addressed by scoping: the managed
region is delimited, idempotent, and diffable.

### 3.6 The rendering invariant

Report B stated it; report A implied it. State it loudly: **a core-rendered web inlines
only the web note's own body, never strand bodies.** Inlining the glossary's 34
definitions would add 1,831 words to a measured 2,273-word core footprint — an 81%
increase from one web.

Pleasantly, this falls out of the existing model with no new machinery: a web note is a
note; a core note inlines its body; a structured note contributes its description; strands
are simply not part of instruction rendering at all. Enforce it with a renderer test that
asserts no strand body appears in any generated document.

### 3.7 Identity: slug is identity, keyword is display

Report A: filename stem is immutable identity, frontmatter `title` is mutable display,
durable links and audit records use the slug. Report B: filename is the slug, the strand
declares its display keyword, and `sase memory init` validates that the keyword slugs
back to the filename.

**Report A is right.** B's validation rule makes renaming a display keyword require a
file rename, which breaks links and audit history for a purely cosmetic change — exactly
the failure A's rule prevents. Precedence: exact slug, then exact keyword, then exact
alias, then unique normalized prefix. Audit events and links always record the slug even
when the user typed a keyword.

Report B's supporting observation is still useful and compatible: existing
`normalize_glossary_reference` casefolds and collapses `-`, `_`, and whitespace runs to a
single space, so `agent_hood.md` and `agent-hood.md` already resolve identically. Reuse
it; drop the filename-agreement requirement.

### 3.8 Sequencing: `decisions` first

Report A put glossary parity in phase 3 and the ADR pilot in phase 4. Report B inverted
it. **Report B is right**, and §1.2's numbers are why: the glossary is simultaneously the
motivating case and the single most coupled surface in the repo. Prove the machinery
where failure is free.

Report B's corollary is also right and easy to under-weight: the `decisions` web must
ship with roughly ten *real* ADRs written from actual history — the Rust core boundary,
the two-speed verification split, the flat-memory decision, the episodes removal. Those
decisions exist and are currently recoverable only from commit messages. Writing them is
worth doing whether or not this epic proceeds, and it is the specific antidote to the
mechanism-before-corpus failure that killed dynamic memory, episodes, and keyword
metadata.

### 3.9 Where report B overstated: `gotchas` is not the highest payoff

Report B ranked `gotchas` the highest-value non-glossary web on the grounds that it is
fully inlined every turn and grows monotonically. The structural argument is sound; the
ranking is not. Measured, `gotchas.md` is 225 words — the fourth-smallest core note.
`task_types.md` is **612 words**, 2.7× larger, and it is already one of the three
hand-built webs from §2.1, so converting it needs no new authoring at all.

If the goal is reducing per-turn core footprint, the order is `task_types` (612) →
`build_and_run` (486) → `sase` (471) → `gotchas` (225). Report B's growth argument
justifies `gotchas` eventually; it does not put it first.

---

## 4. Recommended design

### 4.1 Layout: drop `webs/`

This is the one place I depart from the proposal itself, and it is the largest single
cost reduction available.

```text
sase/memory/
  glossary.md          # web note: type: core, is_web: true, managed roster region
  glossary/
    agent-hood.md      # strand: keyword "Agent Hood", aliases [hood, agent neighborhood]
    stitch.md
  decisions.md         # web note: type: reference
  decisions/
    0007-rust-core-backend.md
  cli_rules.md         # ordinary structured note (unchanged)
```

Compared with `sase/memory/webs/<web>.md`:

| Consequence | With `webs/` | Without |
| --- | --- | --- |
| The six AMD path regexes (§1.4a) | all six must widen | **unchanged** |
| `### Title (basename)` ambiguity (§1.4b) | real; needs a collision rule | **cannot arise** |
| `_is_flat_note_path` | must accept depth 2 for web notes | **unchanged** for web notes |
| `#memory/<web>` xprompt | new derivation + collision rule (B's Q7) | **works today** |
| Glossary migration | new file, old file retired | today's `glossary.md` **becomes** the web note |
| Telling a web from a note | by path | by frontmatter |

Only the last row is a cost, and it is a one-line frontmatter field. Directories already
coexist with notes under `sase/memory/` (`assets/`), so the layout is not novel.

The decisive property: **strands never appear in a generated document at all**, so the
AMD layer never has to parse a nested path. The only code that walks into `<web>/` is the
web reader and the validator. `_is_flat_note_path` keeps rejecting nested paths through
`memory read`, and strands are reached only by the `<web>:<keyword>` selector — which
also cleanly resolves report B's `sase memory read glossary` ambiguity, since `.md`
means the web note and no suffix means the strands.

If you prefer the `webs/` namespace for legibility, the design below is unchanged;
§1.4(a)–(b) is the itemized bill.

### 4.2 Frontmatter

Web note:

```yaml
type: core # or reference/structured
is_web: true
description: Project vocabulary needed to interpret SASE prompts and artifacts.
keyword_noun: term # optional display noun, default "strand"
```

Strand:

```yaml
keyword: Agent Hood
aliases: [hood, agent neighborhood]
```

No `type` on a strand — a strand's tier is its web's tier, and letting strands override
it reintroduces exactly the per-item tier confusion webs exist to remove (report B, Q3).
No `references:` field in v1 (§3.4). ADR lifecycle fields go in an opaque `metadata:`
mapping that generic memory code must not interpret (report A's rule, kept).

Report B's caveat is worth honoring: `keywords` was removed from memory notes in
`21e1640ee` as a *runtime trigger* for the dynamic-memory engine. `keyword` here is an
*addressing alias* evaluated at read time by an explicit command. Say so in the README or
someone files a bead against it in six months.

### 4.3 CLI

```bash
sase memory read <note>.md               -r "<why>"   # unchanged
sase memory read <web>                   -r "<why>"   # every strand in the web
sase memory read <web>:<kw> [<web>:<kw> …] -r "<why>" # named strands + closure
sase memory read glossary:stitch cli_rules.md -r "…"  # mixed batch
```

Make the positional variadic and port `-d/--depth`, `-f/--format`, and `-p/--project`
from `sase glossary read` (§1.4f). Resolve the whole batch before writing an audit event
or emitting output; one unknown or ambiguous selector fails the request, matching current
glossary batch safety. `sase memory show` stays behaviorally identical with no audit
side effect.

`sase memory read <web>` with no keyword prints everything, literally — no silent
truncation, since an audited read must mean what its selector says. Report the strand and
byte count in JSON output and warn on very large results.

Unify the audit log rather than writing two shapes from one command: one event with a
discriminated `kind: note | web | strand`, recording original selectors, resolved slugs,
transitively included slugs, effective depth, scope origin, and bytes. Keep the old
readers so historical JSONL stays queryable.

### 4.4 Validation is a first-class deliverable

Report B's §2.4 is the most important practical warning in either report and should be
budgeted, not treated as polish. Config gives keyword uniqueness structurally; files do
not. What must now be *written*, running in both `sase memory init` and `sase validate`,
failing closed:

keyword uniqueness across strands · alias non-ambiguity (feed `validate_glossary_entries`
strand-derived entries — it is reusable verbatim) · case/normalization collisions ·
orphan strand directory with no web note · reserved web names (§1.4g) · web name versus
flat note stem · nested subdirectories under a web · symlink escape · malformed
frontmatter · cross-scope keyword collision warning (§3.2).

The good news is that the entire Rust diagnostic surface, alias-plural derivation, and
normalization carry over unchanged. Discovery changes; validation does not.

---

## 5. Phasing

| Phase | Content | Ships alone? |
| --- | --- | --- |
| **0** | Lock vocabulary. Add `core memory`, `reference memory`, `memory web`, `memory strand`, `keyword` to the *current* glossary. No code. | yes |
| **1** | Tier rename only. New anchors emitted; **old regexes retained as accepted alternates**; `type: core\|reference` accepted alongside `short\|long`; regenerate all three projects; verify with `sase memory init --check`. | yes |
| **2** | Web substrate: web-note recognition, strand discovery, validator (§4.4), `sase memory list`, `sase memory read <web>` and `<web>:<kw>`, unified audit event, `MemoryPane`. **Seed with a greenfield `decisions` web carrying ~10 real ADRs. No glossary involvement.** | yes |
| **3** | Glossary migration behind a **`beta`** flag. `sase glossary migrate` generates strands from `memory.glossary`; `sase glossary *` becomes an alias family; init fails closed if both config terms and strand files exist. Flip only after `sase` **and** `bob-cli` are migrated and green. | no — flagged |
| **4** | Retire. Delete `glossary/mutation.py`, the `glossary`/`glossaryEntry` schema blocks, the `sase.yml`-mtime completion source; merge `GlossaryPane` into `MemoryPane`; close the flag bead. | yes |

Phase 1's anchor change is a pure compatibility addition — both regexes accepted, new one
emitted — and needs no flag. Note the property report B identified: `parse_amd_agents_document`
reads *already-generated* documents, so a newer `sase` must keep accepting the old anchors
or every not-yet-reinitialized project's shims break. **Add, never replace.**

**On the flag kind.** Report B called phase 3 a "textbook `sunset` flag." Per
`sase/memory/sase_flags.md`, `sunset` is default **on** — for a behavior that is *already*
the default. At creation the web-backed glossary is unproven and must be opt-in, which is
`beta` (default off). Both kinds remove identically: delete the Off branch (the config
glossary), make the On branch (the web) unconditional. `beta` therefore gets the correct
default with no loss. Create it with `sase flag new`, which files the flag bead; do not
hand-add a registry member.

**Do not bundle.** Phases 1, 2, and 3 have disjoint blast radii and each is independently
worth its cost even if the next never lands. That property is what makes the sequencing
safe.

**Rust boundary.** Shared catalog, normalization, validation, matching, and closure belong
in `sase-core`; scope discovery, filesystem containment, rendering, audit persistence,
init planning, and compatibility adapters stay in Python. `GlossarySourceWire` currently
carries `config_path` + `config_key_path`; generalize to a source path plus optional key
path and bump `GLOSSARY_WIRE_SCHEMA_VERSION` from 1. Land the core change and its Python
adapter before phase 3 — this is coordinated two-repo work.

---

## 6. Additional use cases

### 6.1 Candidate webs

The test: *many small keyed items, a few read at a time, indexed by a hub worth having in
instructions.*

| Web | Renders as | Why web-shaped |
| --- | --- | --- |
| **`decisions`** (ADRs) | reference | Best *first* web: greenfield, zero migration risk, immediately useful |
| **`task_types`** | core | Already a hand-built web (§2.1); **largest core note at 612 words**; converting needs no new authoring |
| **`artifact_relations`** | core | The other hand-built web; closed 6-relation registry |
| **`commands`** | core | `build_and_run.md` is 486 inlined words describing ~8 commands |
| **`gotchas`** | core | Grows monotonically; roster in core, bodies on demand (payoff real but smaller than B claimed — §3.9) |
| **`runbooks`** | reference | Keyed by *symptom*, and symptoms are phrases, so mention-closure genuinely fires |
| **`failure_modes`** | reference | Symptom → diagnosis → remediation → prevention, one per strand |
| **`invariants`** | reference | One system invariant with rationale and enforcement points |
| **`apis`** | reference | `sase_core_rs` binding names and wire schemas appear verbatim in code and prose |
| **`integration_contracts`** | reference | One external service's assumptions, limits, and failure behavior per strand |
| **`threats`** | reference | One trust boundary, threat claim, or mitigation decision per strand |
| **`obsidian`** (home scope) | reference | Absorbs bob-cli's four stranded terms (§3.2) and serves every vault-touching project |
| **`incidents`** | reference | Date-keyed postmortems, `related` to `decisions` — only once there are incidents worth recording |

Sub-glossaries deserve mention: webs make `glossary_axe` and `glossary_ace` free. Today
splitting the SASE glossary means 34 keys in one map with no way to scope a read; with
webs, `sase memory read glossary_axe` is a scoped batch and an ACE-focused agent never
pays for AXE vocabulary.

### 6.2 The seam worth leaving open: generated webs

`task_types` and `artifact_relations` derive from plugin registries, not files. If webs
are file-only, those two generators live forever and SASE keeps three implementations of
one idea.

Do not build this in phases 1–4. Just do not foreclose it: keep discovery behind an
interface returning `(web, strands)` rather than a hard-coded `glob`, so a web's strands
can later come from a provider — the same pattern `ref:` providers and `sase_task_types`
plugins already use. Note §1.4(h): downstream projects like bob-cli already receive
generated notes, so the seam must work there too.

### 6.3 What should *not* be a web

- **Narrative notes.** `tui_perf.md`, `symvision.md`, and `xprompts.md` are arguments read
  start to finish. Chopping them into keyed strands destroys the reading order that
  carries the meaning.
- **Anything with one item.** A one-strand web is a note with ceremony.
- **Anything already a first-class artifact.** Beads, plans, Patches, and stitches have
  their own stores, retention, and link tables. Link to them; do not mirror them.
- **Volatile state.** Webs are committed files. Per-run state belongs in `~/.sase/`. This
  is the specific mistake dynamic memory and episodes made.

---

## 7. Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| A core web inlines strand bodies | high | §3.6 invariant + renderer test asserting no strand body reaches a generated document |
| Nested paths break AMD round-trip parsing | high | §4.1 — keep web notes flat; otherwise widen all six regexes (§1.4a) and add the basename collision rule (§1.4b) |
| Glossary migration lands broken across three projects | high | Phase 3 `beta` flag; `decisions` proves the machinery first; migrate `bob-cli` before flipping |
| Validator gap admits duplicate or ambiguous keywords | medium | §4.4 as a first-class deliverable, failing closed in init **and** validate |
| Anchor rename breaks already-emitted shims | medium | Retain old regexes as alternates; add, never replace |
| `sase-core` wire desync across repos | medium | Bump `GLOSSARY_WIRE_SCHEMA_VERSION`; land core + adapter before phase 3 |
| Mechanism before corpus | medium | Phase 2 ships ~10 real ADRs, not an empty web (§3.8, §1.4i) |
| Dual truth: YAML and files both live | medium | Fail closed when both are present; never dual-write |
| Vocabulary drift between "is a web" and "renders as core" | low | §3.1's two-axis rule, in the README before phase 2 |
| Premature coupling to the artifact store | low | Defer (§3.4); keep the `<web>:<keyword>` address artifact-compatible |

---

## 8. What was checked

Verified at `sase@6ca6e798e` on 2026-08-24: `src/sase/memory/notes.py:208-252` (flat
glob, `type: short|long`, `_RETIRED_FRONTMATTER_KEYS = {"keywords"}`) ·
`src/sase/memory/read_log.py:120-215` (`_is_flat_note_path`, `_memory_read_roots`
project-then-home) · `src/sase/memory/cli_read.py`, `cli_show.py` (single positional,
required reason) · `src/sase/memory/proposals/` (write→review ledger) ·
`src/sase/amd/_agents_doc.py:13-33` (tier anchors and all four path regexes, tested
against a nested path) · `src/sase/amd/inventory.py:60` ·
`src/sase/memory/inventory_references.py:25` · `src/sase/amd/inline_memory.py:115-119`
(`### {title} ({basename})`) · `src/sase/xprompt/loader_memory.py:43-45` (first-wins by
stem) · `src/sase/main/init_memory/root_planning.py:142` (`_glossary_collision_blocker`) ·
`src/sase/main/parser_glossary.py:319-345` (variadic terms, `--depth`) ·
`src/sase/main/parser_memory.py` (subcommand set) · `sase/memory/glossary.md`
(`sase_generated:` marker) · `sase/sase.yml` (34 terms, 1,831 words) ·
`sase/{task_types,artifact_relations}.json` · `crates/sase_core/src/glossary.rs:18-132`
(`GLOSSARY_WIRE_SCHEMA_VERSION = 1`, `GlossarySourceWire`, `validate_glossary_entries`) ·
`bob-cli/sase/sase.yml` (4 terms) and `bob-cli/sase/memory/` (generated notes present) ·
`~/AGENTS.md`, `~/CLAUDE.md`, `~/sase/memory/` (separate home-scope rendering) ·
`sase/memory/sase_flags.md` and `sase/memory/sase_artifacts.md` via audited reads ·
`202608/directed_zettelkasten_first_post/`.

Corrections to the source reports: report A's glossary term count (19) is wrong — it is
34. Report B's `sunset` flag kind is wrong — `beta` is correct. Report B's ranking of
`gotchas` as highest-payoff is not supported by measurement — `task_types` is 2.7× larger.
Report B's test-LOC figure (10,934) did not reproduce (I measure 20,574); the ratio, not
the absolute, is load-bearing.

Not verified, out of scope: whether the ACE keymap `glossary` scope can be renamed without
a user config migration; the exact `sase validate` hook point for a web validator; whether
`sase-research-artifacts` or `sase-github` consume glossary APIs.

## 9. Sources

Repository evidence as enumerated in §8. External:

- Zettelkasten Method, [Introduction to the Zettelkasten Method](https://zettelkasten.de/introduction/)
  — stable note addresses, hub/structure notes, cross-links.
- Michael Nygard, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
  — the original small-file ADR proposal.
- AWS Prescriptive Guidance, [Architectural decision record process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
  — decision-log overview/detail use, lifecycle, immutability, supersession.
- Packer et al., [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)
  — hierarchical in-context versus external memory.
- Anthropic, [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  and [How Claude remembers your project](https://code.claude.com/docs/en/memory)
  — progressive disclosure, concise startup memory, just-in-time retrieval.
- Prior in-house research: `202608/directed_zettelkasten_first_post/` (2026-08-02).
