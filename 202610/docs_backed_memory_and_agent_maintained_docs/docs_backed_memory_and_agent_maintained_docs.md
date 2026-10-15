# Docs as Memory: Move Facts to `docs/`, Keep Rules in Memory, Generate the Tables

> **Research query:** Should some SASE memories (such as `sase/memory/macros.md`) be
> migrated into Markdown documentation under `docs/`, should project documentation become
> a first-class representation of memory that is managed in a similar way, and how should
> the docs be structured so that maintaining them is more intuitive and scriptable by
> agents? Critique the plan, clearly call out any justified changes to the requirements,
> and end with a recommended solution.

![Infographic titled "Read docs like memory. Write docs like code.", summarizing why to change (duplicate facts drift, six docs pages over 30k tokens, 24 of 64 recent Codex sessions reading docs without an audit trail), one home for each kind of knowledge (memory, docs, code contracts), the proposed docs-backed reference entries, and the phased plan from fixing drift to scaling maintenance](docs_backed_memory_and_agent_maintained_docs_infographic.png)

## Bottom line

**The direction is right, but the plan is framed around the wrong problem.** The
problem isn't that memory lives in the wrong directory. Three things are wrong:

1. **The same facts are maintained by hand in two places, and both copies are drifting.**
   The lead found both `docs/macros.md` and `sase/memory/macros.md`
   [wrong about macro discovery order](#drift-between-the-two-copies), each in a
   different way. The memory note also omits the `%if` directive entirely.
2. **Docs pages are too large for agents to read or edit precisely.**
   [Six pages exceed 30k tokens](#size-and-shape). `ace.md` alone is about 160k tokens.
3. **Agents already read `docs/` all the time, with no routing and no audit trail.**
   About [38% of recent Codex sessions](#usage-and-churn) in sase workspaces shelled
   into a sase docs page.

Moving files fixes none of these. The fix that works can be summarized as **"read docs
like memory, write docs like code, and generate whatever is really a registry."**

The verdict on each of your three ideas:

- **Migrate some memories into `docs/`**
  - *Verdict:* **Yes, but only descriptive facts, and only if the trigger stays in
    memory.** Most memory is rules, not facts, and stays.
  - *Why:* Rule notes get the most reads (`lint_and_test.md` 665, `sase_beads.md` 314).
    The two descriptive digests are rarely read (`macros.md` 88 across both names,
    `dispatch.md` 4). Deleting a digest and saying "read the docs" makes each triggered
    read cost 15–20× more.
- **Make docs a first-class representation of memory, managed similarly**
  - *Verdict:* **Yes for reads, no for writes.** Docs should be an audited, routable
    *read target* of reference memory. They should not inherit memory's write
    authorization.
  - *Why:* 541 of 1,492 `src/` commits in the last 30 days also edited docs (36%). That
    co-editing is what keeps docs accurate, and gating it would increase drift. Normative
    rules in ungated docs would let any agent silently rewrite policy.
- **Structure docs so agents can maintain them with scripts**
  - *Verdict:* **Yes. This is the biggest win and should come first.**
  - *Why:* "Scriptable" needs metadata a script can join (kind, `covers`, description)
    and generated blocks for registry-shaped facts. Pages must be small enough to own,
    and the gardener needs a channel for defects other than the docs themselves.

**Recommended solution in brief:**

- Keep `sase/memory/` for rules, rationale (decisions), vocabulary (glossary), routing
  triggers, and private home context.
- Make `docs/` the single canonical home for descriptive facts about product behavior.
- [Generate registry-shaped facts](#generate-the-registries) from the contracts that own
  them: directives, discovery order, config keys, glossary, and the decisions index.
- Give docs pages a [small, lint-enforced contract](#the-docs-contract).
- Let a reference-memory **descriptor**
  [take its body from a docs page](#docs-backed-reference-entries) or an explicitly
  anchored section. One resolver in sase-core serves both `sase memory read` and
  `#memory/<stem>` expansion, and every read is audited.
- [Rebuild the docs gardener](#a-scoped-gardener) around code→docs `covers` mappings,
  bootstrapped from git co-change, and send code/docs disagreements to `bug` beads.
- [Pilot with `macros.md` and `dispatch.md`](#disposition-of-the-current-memory-notes).

Full details are in [Recommended solution](#recommended-solution).

## Critique of the plan

**What's right:**

- You noticed real duplication, and real drift is already happening (see
  [Drift between the two copies](#drift-between-the-two-copies)).
- You noticed that docs are already part of the agent loop.
- You noticed that maintaining docs is hard to script.

**What's off:**

1. **"Migrate memories to docs" treats storage as the problem.** Most memory is
   normative (procedures, landmines, routing) and heavily read. Only two notes are
   descriptive digests of docs: `macros.md` and `dispatch.md`. The work is small and
   targeted, not a rehoming of memory.
2. **"Manage docs like memory" has to separate the read side from the write side.** On
   the read side, docs need what memory has: a trigger, an audit trail, addressability,
   and validation. On the write side they need the opposite. Docs must co-change freely
   with code, while memory edits need authorization because every future agent pays for
   them.
3. **Moving files breaks things unless the delivery paths are rebuilt.** Today a memory
   read can't reach `docs/` (the validator rejects it). `#memory/<stem>` expansion is a
   separate Rust path (see [Two memory resolvers today](#two-memory-resolvers-today)).
   The instruction cache doesn't fingerprint docs. A naive move loses the trigger, the
   audit trail, and expansion all at once.
4. **The structure work is what makes the other two pay off.** A docs-backed trigger
   pointing into a 55k-token page is worse than the current digest. Splits and
   generated tables have to come first.
5. **`corpus-before-mechanism` actually permits a small mechanism here.** Its reopen
   condition is "a specific, already-existing corpus demonstrably needs a mechanism that
   plain audited reads cannot serve". `docs/` is that corpus:
   - 57 pages;
   - read in 38% or more of recent Codex sessions;
   - already cited by memory in plain text;
   - unreachable by audited reads.

   It does **not** permit docs webs, embeddings, keyword triggers, or a new CLI family.
   Those repeat the three failures the decision records.

## Requirement adjustments

These change what you asked for. Each is justified in the
[critique](#critique-of-the-plan), the [verified facts](#verified-facts), and the
[resolution of the researchers' disagreements](#where-the-researchers-disagreed-and-how-this-report-resolves-it).

- **R1**
  - *Your requirement, as read:* Migrate memories such as `macros.md` into `docs/`.
  - *Adjusted requirement:* **Route content by kind.** Descriptive facts go to docs.
    Rules, rationale, vocabulary, routing triggers, and private context stay in memory.
    Registry-shaped facts are **generated** into docs from the contracts that own them.
    A migrated entry keeps its memory trigger.
- **R2**
  - *Your requirement, as read:* Make docs first-class memory, managed similarly.
  - *Adjusted requirement:* **First class means routable, audited, addressable, and
    validated, not governed.** A reference-memory descriptor may take its body from a
    same-repo docs page or an explicit-id section. The descriptor is governed by
    `/sase_memory_write`; the body is docs-as-code. Only descriptive pages may be bodies.
- **R3**
  - *Your requirement, as read:* Structure docs for intuitive, scriptable maintenance.
  - *Adjusted requirement:* **A lint-enforced contract, not a tidier tree.**
    Requirements: `description` / `kind` / `covers` frontmatter, a token budget with a
    ratchet, generated blocks for registries, validated anchors and nav, and the docs
    build in the landing path.
- **R4**
  - *Your requirement, as read:* *(new)*
  - *Adjusted requirement:* **The gardener must not write defects into docs.** A
    code/docs disagreement becomes a `bug` task bead, never a "this help text is stale"
    sentence.
- **R5**
  - *Your requirement, as read:* *(new)*
  - *Adjusted requirement:* **Project in both directions.** Memory webs that humans need
    (`glossary`, the `decisions` index) render into **generated, read-only** docs pages.
    Their source stays in memory.
- **R6**
  - *Your requirement, as read:* *(new)*
  - *Adjusted requirement:* **Same repo, opt-in, no always-loaded docs.** Docs-backed
    entries resolve only inside the descriptor's own project repo. Unenrolled pages stay
    ordinary docs. Nothing from `docs/` enters the instruction bundle except
    existing-style one-line triggers. This makes the feature project-generic for free.
    Home notes cannot use it.
- **R7**
  - *Your requirement, as read:* *(new)*
  - *Adjusted requirement:* **Measure before generalizing.** Pilot on `macros.md` and
    `dispatch.md` with stated exit criteria and a reopen condition
    ([Metrics and reopen conditions](#metrics-and-reopen-conditions)).

## Options considered

- **A. Status quo plus drift tests (`grk`'s core):** Necessary but not enough. Lock
  tests catch named facts. They leave two hand-written grammars and unaudited docs reads.
  Fold the lock tests into the generation work.
- **B. Wholesale move (delete digests, point at docs):** **Reject.** Loses triggers,
  makes each read cost 15–20× more, and puts rules in ungoverned files.
- **C. Docs as a full memory kind (governed, webs, closure):** **Reject.** Throttles
  docs co-change, and it is mechanism with no corpus that needs it.
- **D. New `sase doc` CLI family (`gem`):** **Reject for now.** It duplicates
  `sase memory read`, its audit log, the Memory panel, and skills. `gem`'s useful ideas
  survive inside F: section-capped, audited reads.
- **E. Docs map in instructions (`grk`'s agent index):** **Defer.** Run it as a measured
  experiment after the splits (see
  [Why there is no docs map in v1](#why-there-is-no-docs-map-in-v1)).
- **F. Generation + docs contract + docs-backed reference entries:**
  **[Recommended](#recommended-solution).** It reuses selectors, audit, the panel, and
  governance, and adds one field plus one resolver.
- **G. LLM-generated digests (GitLab's distiller pattern, `cld` option E):** **Reject as
  a build step.** Non-deterministic and hard to review. Deterministic generation covers
  the registry facts.

## Recommended solution

### Principle written down first as a decision record

**Claim:**

- `docs/` is the canonical home of descriptive facts.
- Memory holds rules, rationale, vocabulary, private context, and **triggers**.
- A reference-memory descriptor may take its body from a same-repo docs page or an
  explicit-id section. Reads through it are audited like note reads.
- Registry-shaped facts are generated from the contracts that own them.
- Write governance follows the file:
  - descriptors are memory-governed;
  - doc bodies are docs-as-code;
  - normative rules may not live in a doc body.

**Rejected:** [options B, C, D, and G](#options-considered).

**Cost:**

- a resolver and binding in sase-core;
- a frontmatter lint;
- a generalized renderer;
- page splits with redirects;
- anchor ids become a stable interface.

**Reopens when:** either of the following happens. In that case, revert those entries to
notes and keep the generation and contract work, which pays off on its own.

- Docs-backed entries raise tokens per triggered read, or lower read rates, compared
  with the note baseline.
- A rule change reaches agents through an ungoverned doc body.

### Where content goes

- **Always-true agent rules and landmines**
  - *Home:* Core memory
  - *Delivery:* Inlined
- **Agent procedures and conventions (`lint_and_test`, `symvision`, `sase_flags`,
  `cli_rules`, `tui*`, `generated_skills`)**
  - *Home:* Reference memory notes
  - *Delivery:* Trigger plus audited read
- **Rationale, vocabulary, task types**
  - *Home:* Memory webs
  - *Delivery:* Descriptor plus strands. Generated read-only docs pages for humans
- **Product behavior: how macros, dispatch, config, and the TUI work**
  - *Home:* `docs/`
  - *Delivery:* Ordinary docs. Selected pages or sections are enrolled as reference
    bodies
- **Registries: directives, discovery order, config keys, CLI flags, model tables**
  - *Home:* Their code or contract
  - *Delivery:* Generated blocks in docs
- **Investigations**
  - *Home:* Research sidecar
  - *Delivery:* Promoted to docs or decisions deliberately, never automatically
- **Private machine and person context (`tailnet`, `obsidian`)**
  - *Home:* Home memory
  - *Delivery:* Never published, never docs-backed

### Generate the registries

*Component 1: first, highest return, no memory change.*

Generalize `tools/render_model_docs` into one renderer with named providers, the same
`BEGIN GENERATED` markers, and the `--check` mode that `fmt-docs-check` already runs in
`just check` and the master gate. The Python tool can call `sase_core_rs`.

The first providers:

1. **Directive table rows** from `sase_core_rs.directive_contract()`. Generated columns:
   name, alias, synopsis, and short description. A hand-written *Effect* column is fine.
   A coverage check fails when a contract directive has no row, which would have caught
   `%if`.
2. **Discovery order** from `resolve_macro_file_sources`. This permanently fixes the
   drift found in [Verified facts](#drift-between-the-two-copies).
3. **`docs/glossary.md` and a decisions index** from the webs, both read-only and marked
   "generated from memory".
4. **Then config key tables** from `sase.schema.json`, one block per top-level key
   family. This is the biggest lever on `configuration.md`, which is co-edited with
   every subsystem.

Generate tables, not chapters (`grk`). A fully generated handbook would be unreadably
complete.

### The docs contract

*Component 2.*

**Frontmatter**, lint-checked by a fast Python tool in `just check`:

```yaml
---
description: >- # one line; also feeds Material's meta description and any llms.txt
  Macro invocation grammar, argument quoting, and the directive quick reference.
kind: reference # tutorial | how-to | reference | explanation | runbook | mixed
covers: # repo globs whose behavior this page documents
  - src/sase/macro/**
---
```

- **`kind: mixed`** is an explicit, counted debt marker for pages not yet split. The
  lint reports the count as a ratchet that may only go down. This follows Diátaxis'
  "improve incrementally" advice and avoids labeling a mixed page with a false kind
  (`cdx`).
- **`covers`** must match at least one path.
- **Bootstrap `covers` with a one-time co-change mining script**
  ([Verified facts](#code-to-docs-mapping-can-be-bootstrapped-from-git) shows it already
  picks the right page). Then curate it by hand. Don't expect anyone to write 57 pages
  of globs from scratch.
- **Token budget:** warn above 15k tokens (whitespace-squeezed). Fail when a new page is
  over budget or an over-budget page grows. Today that's 12 pages, with the 6 over 30k
  split first.

**MkDocs:**

```yaml
validation:
  omitted_files: warn
  anchors: warn
exclude_docs: |
  images/**/*.md
```

- Add `agent_auto_restart.md` to the nav, or delete it.
- Use `attr_list`, which is already enabled, for explicit heading ids on any section
  that is enrolled or linked from memory: `## Hold directive {#macro-hold}`.

**Landing path:**

- Add `just docs-check` to the master gate (or run it when `docs/` or `mkdocs.yml`
  changes). With zero PRs, the PR-only CI job never protects `master`.
- Keep the agent default at `just check` plus the new fast lint. That follows
  `check-full-is-explicit`.

### Docs-backed reference entries

*Component 3: the "first-class" piece.*

This is a **proposed** descriptor field. It is not supported yet.

```yaml
# sase/memory/macros.md  (descriptor; governed by /sase_memory_write)
---
type: reference
description: Read before macros, prompt directives, or launching agents with git/gh VCS workflow blocks.
body_source: docs/macros/reference.md#macro-quick-reference
---
```

**Rules:**

- **Reference notes only, same repo only.** The path resolves relative to the
  descriptor's project root and must stay under `docs/`. Real paths and containment are
  checked, and symlinks can't escape. Home notes can't use the field.
- **Exclusive body.** A descriptor that has both `body_source` and its own body is
  rejected. Routing metadata lives in the descriptor; the reference prose lives in one
  place.
- **Whole page or explicit id only.** No slug-derived anchors, line ranges, or include
  fences. A missing or duplicate id is an error. The read must never quietly fall back to
  the whole page or to stale cached bytes (`cdx`).
- **One resolver, in sase-core.** It serves `sase memory read`, `#memory/<stem>`
  expansion, `sase memory show`, and Memory panel navigation. Python calls it through
  `sase_core_rs` and bumps the `sase-core-revision.txt` pin. Otherwise a launch-time
  expansion and a mid-turn read can deliver different text under the same name.
- **The audit record** includes:
  - the descriptor path and blob;
  - the resolved doc path and id;
  - the doc blob OID;
  - a digest of the delivered bytes, since a blob OID doesn't prove which uncommitted
    bytes were served (`cdx`).

  Launch-time `#memory/` expansion keeps producing no read event, as it does today.
- **Cache:** only the descriptor's description enters the bundle, so body-only docs
  edits don't invalidate bundles. That is correct. The expansion and preview caches must
  key on the resolved source.
- **Panel:** a docs-backed entry shows its source. "Edit body" opens the doc, and
  "Edit routing" opens the descriptor.
- **Rollout order:** ship reader and binding support before any live descriptor uses
  `body_source`. Older readers ignore unknown frontmatter and would expand to an empty
  body.
- **Links (deferred):** a new `[[docs:…]]` link syntax waits for evidence. First add a
  `sase doctor` check that validates the existing plain `docs/<page>.md#id` mentions in
  memory.

### Split the monoliths

*Component 4: `macros.md` first.*

`docs/macros.md` (55k tokens, mixed):

```text
docs/macros.md -> redirect to macros/index.md
docs/macros/
  index.md        # explanation: mental model and resolution diagram
  authoring.md    # how-to: writing .md/.yml macros and workflows
  reference.md    # reference: invocation grammar + generated directive and discovery tables
                  #   ({#macro-quick-reference} section is the memory body, ≤ ~4k tokens)
  directives.md   # reference: full per-directive contracts (split per directive only if over budget)
  cli.md          # reference: sase macro expand/explain/list/show/graph
```

**`mkdocs-redirects`** is already installed. It doesn't preserve fragment links, so map
the important old `#anchors` explicitly (`cdx`).

**Later splits:**

- `configuration.md`: one page per top-level key family, mostly generated tables.
- `ace.md`: one page per tab or panel.
- Then `llms.md`, `beads.md`, and `notifications.md`.

Smaller pages also cut edit collisions between concurrent workspaces. `ace.md` and
`configuration.md` took 465 commits between them in 30 days.

### A scoped gardener

*Component 5.*

- **`sase docs affected [--since <rev>] [--json]`** joins a diff against `covers`. When
  nothing matches, it falls back to co-change history.
- **Rewrite the `refresh_docs` builtin to emit one proposal per affected page cluster.**
  Each proposal carries:
  - the page paths and the hunks that touched their `covers`;
  - an instruction to re-run the renderers;
  - an instruction to **file a `bug` task bead through `/sase_new_task`** for any
    disagreement between code and docs, instead of documenting the defect.
- **Polish** then verifies only that cluster.
- **History-language lint (warning only):** flag phrases like "still mentions", "is
  stale", or "no longer" outside migration and explanation pages, so they get cleaned up.
- **Optional advisory:** when a commit touches covered code without touching its page,
  print a one-line, **non-blocking** notice. This follows the
  annotate-don't-block spirit of `triage-annotates-does-not-change-exit-codes`.

### Disposition of the current memory notes

- **`sase.md`, `gotchas.md`, `rust_core_backend_boundary.md` (core):** Stay core.
- **`lint_and_test`, `symvision`, `sase_flags`, `cli_rules`, `generated_skills`, `tui`,
  `tui_perf`:** Stay as reference notes. They are contributor and agent policy. Where
  they repeat docs facts, replace the repetition with validated `docs/…#id` pointers.
- **`tui_screenshot.md`:** Check its overlap with `docs/development.md`. Usage facts can
  move; the procedure stays.
- **`sase_artifacts`, `sase_beads`, `sase_sizes`, `task_types`:** Stay generated. They
  already follow the "CLI/docs own the encyclopedia, memory owns the remainder" pattern.
- **`decisions`, `glossary` webs:** Stay in memory. Add generated docs pages for humans.
- **`macros.md`:** **Pilot.** Becomes a descriptor whose `body_source` is
  `docs/macros/reference.md#macro-quick-reference`. The `#memory/macros` and
  `[[macros.md]]` names stay.
- **`dispatch.md`:** **Pilot.** Becomes a descriptor over a quick-reference section of
  `docs/remote_dispatch.md`.
- **`tailnet.md`, `obsidian.md` (home):** Never published, never docs-backed.

**Memory governance for the plan that implements this:**

- Fixing the discovery order in `macros.md` is a correction of a false claim. Its memory
  decision defaults to yes, with the wrong text quoted in `corrects:`.
- Adding `%if`, and converting the pilot notes into descriptors, are new content. Those
  decisions default to no unless you explicitly request them.

### Phasing

0. **Hygiene** (days, no mechanism)
   - *Scope:* Write the decision record. Fix the discovery-order drift in docs and
     memory. Change the gardener prompts to send defects to beads. Turn the stale-caveat
     lines into beads and fix the `sase memory` help blurb. Add the MkDocs `validation`
     and `exclude_docs` settings, and resolve the unlisted page. Add `docs-check` to the
     master gate. Write the content-kind rule into `docs/development.md` → Documentation
     Workflow.
   - *Exit criteria:* The strict build checks anchors and omitted files on every
     landing. Zero "help text is stale"-style lines.
1. **Generation**
   - *Scope:* Build the generalized renderer with directives, discovery order, glossary,
     and the decisions index. Add the coverage check.
   - *Exit criteria:* No hand-maintained directive or discovery tables remain. The
     glossary and decisions pages are published.
2. **Contract + macros split**
   - *Scope:* Add the frontmatter lint (with the `mixed` ratchet), the token budget, and
     `covers` bootstrapped from co-change. Split `docs/macros.md` and add explicit ids.
   - *Exit criteria:* The lint is green. The macros pages are under budget. The
     quick-reference section is about 4k tokens or less.
3. **Docs-backed entries + pilot**
   - *Scope:* sase-core resolver and binding. Python read and Rust expansion. Audit
     fields, the panel, and the doctor pointer check. Convert `macros.md` and
     `dispatch.md`.
   - *Exit criteria:* See [Metrics and reopen conditions](#metrics-and-reopen-conditions).
4. **Gardener + monoliths**
   - *Scope:* `sase docs affected`, the scoped `refresh_docs`, config tables from the
     schema, and the `configuration.md` / `ace.md` splits.
   - *Exit criteria:* No page over budget. Gardener proposals are scoped per cluster.
     The `mixed` count trends to zero.
5. **Optional, demand-driven**
   - *Scope:* Docs-map experiment, `/llms.txt` from `description`, more docs-backed
     entries, `kind: policy` pages for contributor conventions.
   - *Exit criteria:* Each needs its own measured trigger.

Phases 0–2 pay off even if Phase 3 never ships. If you want the cheapest version, stop
after Phase 2 and let `macros.md` keep its body with generated tables inside it. That is
`gem`'s Option C. You lose audited docs reads and one-home grammar, but you keep most of
the drift fix.

### Metrics and reopen conditions

Measure each on the pilot entries against the note baseline:

- **Read cost:** tokens per triggered read. The baseline is ~2.6–3.7k for `macros.md`
  and ~0.7k for `dispatch.md`. Target: no higher.
- **Routing:** the read rate of `macros.md` and `dispatch.md` before and after, and the
  share of `docs/` access that shifts from shell greps to audited reads. The lead's
  transcript scan from [Verified facts](#usage-and-churn) can be re-run for this.
- **Freshness:**
  - hand-maintained registry tables, target 0;
  - stale-caveat lines, target 0;
  - `bug` beads filed by the gardener, which should be above 0;
  - lint debt from `mixed` and over-budget pages, which may only go down.
- **Behavior:** a small acceptance set of 12–20 tasks (`cdx`). It should include:
  - finding the argument-escaping rules;
  - editing a directive;
  - writing a valid macro;
  - a renamed or missing anchor, which must fail visibly;
  - an uncommitted doc edit;
  - unrelated work that must not load macro docs.

  Same model, same snapshot, and repeat a subset to see variance. This is exploratory,
  not a benchmark.
- **Reopen:** if read cost or read rate gets worse, or a rule change slips through an
  ungoverned body, revert the pilot entries to notes and keep Phases 0–2.

### What not to do

- Don't move rules or procedures into ungoverned docs.
- Don't put a docs map, or any doc content, into always-loaded instructions without a
  measured miss rate.
- Don't build docs webs, embeddings, keyword triggers, or a `sase doc` command family.
- Don't put every docs edit behind memory authorization.
- Don't generate digests with an LLM.
- Don't build a four-folder Diátaxis tree from the top down. Split pages as the
  contract and budget call for it.

### Open choices for you

1. **Do you want Phase 3, the mechanism, at all?** The case for it is audited, routable
   docs reads and one home for the grammar. The case against is a cross-repo feature (a
   sase-core resolver, a binding pin bump, and two access paths to keep consistent) for
   two pilot notes. This report recommends it, because agents
   already read docs in a large share of sessions. But Phases 0–2 alone are a solid
   outcome.
2. **Should contributor docs (`development.md`, `perf_runbook.md`, `rust_backend.md`)
   stay on the public site?** Publishing them is already the status quo. If that
   changes, any future `kind: policy` pages need a non-published docs root.

## Where the researchers disagreed and how this report resolves it

Positions of the four researcher reports (see [Scope and inputs](#scope-and-inputs)),
question by question:

- **Migrate `macros.md`?**
  - *`cdx`:* Pilot: the descriptor sources its body from a docs page
  - *`cld`:* Pilot: becomes `docs/macros_quick_reference.md` with a trigger
  - *`grk`:* **No.** Keep, tighten, add drift tests
  - *`gem`:* **No.** Keep, codegen shared tables
  - *Resolution:* **Split it by content kind.** Generate the registry rows, drop the
    duplicated normative rule (already in core), and move the grammar to a dense docs
    reference page backed by the same trigger.
    [See below](#why-the-macros-note-should-be-split-rather-than-kept-or-moved).
- **How agents reach docs**
  - *`cdx`:* Existing `sase memory read <note>`; descriptor has `content_source`
  - *`cld`:* New `docs:<page>#<anchor>` selector; trigger in doc frontmatter
  - *`grk`:* Plain `Read`, plus a generated docs map in reference memory
  - *`gem`:* New `sase doc read` CLI with a token cap
  - *Resolution:* **`cdx`'s descriptor** (no new selector family or CLI), plus
    **explicit-id sections** (a middle ground between `cdx`'s whole pages and `cld`'s
    slugs).
- **Where write governance lives**
  - *`cdx`:* Effective content role
  - *`cld`:* By content kind: the doc's `memory:` block and `kind: policy` pages are
    governed
  - *`grk`:* A thin docs write convention
  - *`gem`:* Not addressed
  - *Resolution:* **Falls out of the descriptor design.** The descriptor is memory and
    governed; the body is docs-as-code. Only descriptive pages may be bodies. No
    `kind: policy` docs in v1.
- **Docs map in agent context**
  - *`cdx`:* No
  - *`cld`:* No
  - *`grk`:* Yes: an on-demand `docs_map.md`, promoted to core if needed
  - *`gem`:* No
  - *Resolution:* **Not in v1. Optional later experiment.**
    [See below](#why-there-is-no-docs-map-in-v1).
- **Page size budget**
  - *`cdx`:* Split at meaningful boundaries
  - *`cld`:* Warn at ~30k tokens
  - *`grk`:* 800–1,000 lines
  - *`gem`:* Under 400 lines
  - *Resolution:* **Token-based: warn above 15k tokens.** No grandfathered page may
    grow. Lines mislead (`cli.md`), and a 400-line cap would force 33 of 57 pages to
    split.
- **Frontmatter**
  - *`cdx`:* `doc_kind` and `summary`, minimal
  - *`cld`:* `description`, `kind`, `covers`, `memory`, `derived_from`
  - *`grk`:* `kind`, `audience`, `when_to_read`, `related_memory`, `owner`,
    `size_budget_lines`
  - *`gem`:* `title`, `description`, `doc_type`, `domain`, `related_code`,
    `related_memory`, `status`
  - *Resolution:* **`description`, `kind`, `covers` only.** Each one has a consumer on
    day one. Skip ownership fields for a solo maintainer, skip `status` and `audience`,
    and skip per-page budgets in favor of a global one.
- **Source for generated directive tables**
  - *`cdx`:* n/a
  - *`cld`:* The Rust directive contract
  - *`grk`:* One shared list
  - *`gem`:* A new registry in `_directive_types.py`
  - *Resolution:* **The Rust `directive_contract`, which already exists.** No new
    registry. Respects the backend boundary.

### Why the macros note should be split rather than kept or moved

*Applies to `macros.md`.*

`grk` and `gem` argue that humans and agents need different texts, so the cheat sheet
must stay. That holds only while `docs/macros.md` is one mixed 55k-token page. Once
the page is split along Diátaxis lines, its **reference** part can be as dense as the
cheat sheet, because Diátaxis reference material is meant to be consulted, not read
through. The narrative moves to explanation and how-to pages.

The memory note has four parts. Each goes somewhere different:

1. **Directive rows and discovery order** are registries. Generate them from the Rust
   contract and the resolver.
2. **The host-owned-completion rule** is already in core `sase.md` and in
   `decisions:host-owned-completion`. Drop the duplicate copy.
3. **The invocation grammar** is the one truly shared piece of prose. Give it one home:
   a dense docs reference page or anchored section.
4. **The trigger** ("Read before macros, prompt directives…") stays in memory and now
   points at that page.

### Why there is no docs map in v1

Vercel's eval is real (checked against the primary source). An always-loaded 8 KB
**index of doc paths** reached 100% pass, against 53% for a skill the agent had to
choose to open (it went unopened in 56% of cases). The caveats: Vercel didn't publish
the task count, and they call their explanation a "working theory".

For SASE, three things weaken the case:

1. The always-loaded Reference Memory list already plays the role of Vercel's index.
2. Agents already find the right page by grep. In one week of Claude sessions, 46 shell
   reads (grep, sed, cat and similar) targeted `docs/macros.md`. The bottleneck is cost
   and precision inside huge pages, not discovery.
3. The ETH study (Gloaguen et al., v3) found that repository overviews in context files
   don't help and add more than 20% inference cost.

`grk`'s on-demand map sits behind a trigger the agent has to choose to follow. That is
the same arrangement as Vercel's "skill, agent decides" case. So treat the map as a
measured experiment after the splits, not a v1 component.

## Verified facts

Every item below was checked by the lead. "New" marks findings that none of the four
reports had.

### Size and shape

- **Docs pages (excluding blog and image briefs):** 57, about 0.88M tokens with table
  padding removed (1.03M by raw bytes/4)
- **Pages over 30k tokens:** 6, all padding-adjusted: `ace.md` ~161k,
  `configuration.md` ~122k, `macros.md` ~55k, `llms.md` ~49k, `beads.md` ~46k,
  `notifications.md` ~30k
- **Pages over 15k tokens:** 12
- **Pages over 400 lines:** 33
- **Lines are a bad size measure (new):** `cli.md` is only 1,026 lines but ~26k tokens,
  because Prettier pads its wide tables (~53k by raw bytes)
- **Page frontmatter:** Only `index.md` and `getting_started.md` have any, outside blog
  posts and image briefs
- **Memory corpus:** 19 flat notes, about 22k tokens. `sase/memory/macros.md` is 167
  lines, ~2.6–3.7k tokens
- **Memory→docs pointers:** 6 plain-text `docs/…` mentions in memory notes. Nothing
  validates them

### Drift between the two copies

**Macro discovery order (confirmed).** The live
`resolve_macro_file_sources(project="sase")` returns 11 sources. All three canonical
sources come first (project `sase/macros/`, then `~/sase/macros/`, then
`~/sase/macros/<project>/`), followed by all eight legacy `xprompts` sources.

- **`docs/macros.md`** names `.macros/`, `macros/`, `~/.macros/`, `~/macros/`, and
  `~/.config/sase/macros/{project}/`. **The resolver reads none of these.** The docs
  also place legacy project directories ahead of the canonical home directory.
- **The memory note** uses the right legacy names. It gets the order wrong and omits
  three sources: `sase/xprompts/`, `~/sase/xprompts/`, and
  `~/sase/xprompts/<project>/`.
- **Origin:** the 2026-10-03 bulk rename commit `fe53ae4fc4`, according to `cld`.

**`%if` missing from memory (new).** The Rust `directive_contract` binding returns 17
structured rows (name, alias, description, synopsis, keywords, examples), including
`%if`. `docs/macros.md` mentions `%if` 31 times. The memory note's directive table
never mentions it.

### Usage and churn

**Audited memory reads (all time):**

- 2,095 reads by 890 agents across 125 paths.
- Rule and procedure notes dominate: `lint_and_test.md` 665, `sase_sizes.md` 328,
  `sase_beads.md` 314.
- Descriptive digests are rare: `macros.md` 40 plus 48 under its old name
  `xprompts.md`, and `dispatch.md` 4.

**Unaudited docs reads (refined from `cld`'s figure).** Transcripts from the last 7
days:

- **Codex:** 24 of 64 sessions in sase workspaces shell-read a sase docs page. 56 ran
  `sase memory read`.
- **Claude:** 36 of 61 sessions shell-read docs. But those sessions are mostly
  research agents (143 web searches), so `cld`'s 44% figure overstates how often
  *coding* agents look things up there. The direction holds; the size is smaller.

**Churn over 30 days:**

- 1,889 commits in total.
- 624 touched `docs/`. 541 of the 1,492 `src/` commits also touched docs (36%).
- 77 touched `sase/memory/`.
- `ace.md` had 260 commits and `configuration.md` had 205.
- **Zero merge commits.** Everything lands directly on `master`.

### The gardener writes defects into docs

**Confirmed.** `docs/memory.md:256–257` and `docs/cli.md:22` describe stale help text
instead of fixing it. Both came from gardener commit `341d17739b` on 2026-08-30. **New:**
the underlying defect is still live. `sase -h` still says `memory` can "review
proposals". The gardener prompt tells the agent to "describe it in your final response",
and a final response is not a tracked work item.

### Gaps in docs checks

**New.**

- `mkdocs build --strict` runs only in `ci.yml`, which triggers on `pull_request`, and in
  `docs-deploy`, which runs after a push to `master`. With no PRs, **a broken docs build
  is first seen after it lands.**
- `just check` and the master gate run only `fmt-docs-check` (the model-table renderer).
- `mkdocs.yml` has no `validation:` block. MkDocs 1.6 defaults `links.anchors` and
  `nav.omitted_files` to `info`, so `--strict` ignores both.
- As a result, nothing catches the unlisted `agent_auto_restart.md`.
- It also misses the 21 `docs/images/**/*.md` prompt and critique files. They are not
  excluded, so MkDocs builds them as orphan pages.

### Contracts that already exist for generation

**New.** Each contract and what it covers:

- **Rust `directive_contract`:** All 17 directives
- **`resolve_macro_file_sources`:** Discovery order
- **`src/sase/config/sase.schema.json`:** 1,014 properties, 875 with descriptions, 65
  top-level keys. `configuration.md` has 1,587 table lines
- **`glossary` and `decisions` webs:** Vocabulary and the decisions index
- **`tools/render_model_docs`:** Precedent: `BEGIN GENERATED` blocks plus a `--check`
  that already runs in `just check`

### Two memory resolvers today

**Confirmed (`cdx`).**

- `sase memory read` is pure Python (`src/sase/memory/_read_log_paths.py`). It rejects
  any path outside the memory root.
- `#memory/<stem>` expansion goes through the Rust macro catalog
  (`macro_catalog/loader.rs`).
- Any docs-backed body must go through both paths, or the two will disagree.

### Code-to-docs mapping can be bootstrapped from git

**New.** Over the last 3 months, the most co-edited docs page for each code area is the
obvious one:

- **`src/sase/macro`:** `macros.md`
- **`src/sase/memory`:** `memory.md`
- **TUI widgets:** `ace.md`
- **`src/sase/notifications`:** `notifications.md`
- **`src/sase/bead`:** `beads.md`

`configuration.md` is the #2 page for **every** area. That makes it the cross-cutting
hotspot, and the strongest case for generating it from the schema.

### History

The May 2026 draft post `whats-next-memory-mobile-web.md` sketched "canonical zettel +
generated memory projections". It was shelved over poisoning and projection cost. Your
proposal is the same idea, using the `docs/` corpus that already exists instead of a new
store (`grk`). That corpus is what makes it viable now.

## Scope and inputs

> **Research question:** Some SASE memories (for example `sase/memory/macros.md`) should
> perhaps move into Markdown docs under `docs/`. Project documentation might become a
> first-class representation of memory, managed in a similar way. Documentation should
> also be structured so that agents can maintain it more intuitively and with scripts.
> Research the best way to implement this, critique the plan, adjust the requirements
> where justified (and say so), and end with a recommended solution.

This report consolidates four independent reports (`cdx`, `cld`, `grk`, `gem`) and adds
the lead's own checks, run on 2026-10-15 against sase `c2c2ffd4df` and sase-core
`6f422072`. The lead's checks covered:

- the macro-source resolver and the Rust directive contract, run live;
- `sase memory log`;
- 30-day git churn and code-to-docs co-change mining;
- 125 recent Claude and Codex transcripts from `sase_<N>` workspaces;
- the MkDocs config, `Justfile`, and CI workflows;
- the `refresh_docs` gardener;
- the memory read path in both sase and sase-core;
- the Vercel, MkDocs, and GitLab primary sources.

The researchers' raw reports sit next to this file as
`docs_backed_memory_and_agent_maintained_docs__<suffix>.md`.

## Evidence and sources

### Lead checks

Run against sase `c2c2ffd4df` and sase-core `6f422072`.

- **Resolver and contract:** live `resolve_macro_file_sources(project="sase")` and
  `sase_core_rs.directive_contract([])`.
- **Memory reads:** `sase memory log --json`.
- **Audited memory reads:** `macros.md`, `decisions:corpus-before-mechanism`,
  `decisions:memory-links-are-authored`, `decisions:instructions-per-invocation`.
- **Git history:** churn since 2026-09-15; co-change since 2026-07-15; `git blame` on
  the stale-caveat lines.
- **Transcripts:** Claude (`~/.claude/projects/*sase-org-sase-sase*`) and Codex
  (`~/.codex/sessions`) sessions since 2026-10-08, filtered to sase workspace cwds and
  sase docs pages.
- **Files read:**
  - `mkdocs.yml`;
  - `Justfile` (`check`, `fmt-docs-check`, `docs-check`);
  - `.github/workflows/{ci,master-gate,docs-deploy}.yml`;
  - `src/sase/scripts/sase_chop_refresh_docs.py`;
  - `src/sase/memory/_read_log_paths.py`;
  - sase-core `crates/sase_core/src/macro_catalog/loader.rs`;
  - `src/sase/config/sase.schema.json`;
  - `docs/blog/posts/whats-next-memory-mobile-web.md`.

### External primary sources checked by the lead

- Vercel, "AGENTS.md outperforms skills in our agent evals" (2026-01-27):
  <https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals>
- MkDocs configuration, `validation` (1.6 defaults; anchors at `info`):
  <https://www.mkdocs.org/user-guide/configuration/#validation>
- GitLab, AI instruction files for documentation. The style guide is canonical;
  distilled files are generated and must not be hand-edited:
  <https://docs.gitlab.com/development/documentation/ai-instruction-files-documentation/>

### External sources from the researcher reports

- Diátaxis: <https://diataxis.fr/> and <https://diataxis.fr/how-to-use-diataxis/>
- Gloaguen et al., "Evaluating AGENTS.md" (arXiv 2602.11988, v3):
  <https://arxiv.org/abs/2602.11988>
- Lulla et al., "On the Impact of AGENTS.md Files" (arXiv 2601.20404):
  <https://arxiv.org/abs/2601.20404>
- Anthropic, "Effective context engineering for AI agents":
  <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- Claude Code memory (path-scoped rules, `@imports`): <https://code.claude.com/docs/en/memory>
- GitLab topic types and docs testing:
  <https://docs.gitlab.com/development/documentation/topic_types/> and
  <https://docs.gitlab.com/development/documentation/testing/>
- llms.txt: <https://llmstxt.org/>
- Swimm, code-coupled documentation:
  <https://docs.swimm.io/new-to-swimm/benefits-of-code-coupled-documentation>
- Google developer style, timeless documentation:
  <https://developers.google.com/style/timeless-documentation>
- Cyrille Martraire, *Living Documentation* (Addison-Wesley, 2019)
