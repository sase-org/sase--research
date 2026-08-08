---
create_time: 2026-08-08
updated_time: 2026-08-08
status: research
---

# Defining Artifact References With XPrompts

**Research question:** what is the best way to let xprompts define SASE artifact
references (`@commit:…`, `@research:…`), so a user controls the text substituted at
launch — and any other customization worth exposing — while every kind keeps the
builtin machinery (usage tracking, staging, linking, completion) for free?

**Scope:** the `sase` repo at master `5f0da4b33` and the linked `sase-core` checkout at
`origin/master`, read 2026-08-08. Precedent is the two in-flight namespace migrations:
`sase-hb` (canonical `skills/` directories, `#skills/<name>`) and `sase-hf` (xprompt
memories, `#memory/<stem>`, plan `plans:202608/xprompt_memories.md`). This note covers
design only; nothing here has been implemented.

## Bottom line

Do it, but scope it deliberately: **make the render step a template, not the resolver.**

1. The artifact-reference pipeline is already cleanly layered, and the layer you want
   to open up is unusually small. Grammar, scanning, canonicalization, and resolution
   are ~2,300 lines of Rust in `sase-core`. The per-kind *rendering* — the entire "what
   text replaces `@commit:sase@abc`" decision — is **43 lines of Python** in one
   function, `_artifact_ref_replacement()` (`src/sase/artifact_ref_prompt.py:201`).
   That function is the whole ask.
2. Everything the user called "builtin functionality useful for all artifacts" already
   exists and is *already* template-independent, because it is keyed on the resolution
   result rather than on the rendered text: the consumption ledger
   (`src/sase/core/artifact_consumption.py`), prompt-artifact staging
   (`_stage_artifact_references`, `artifact_ref_prompt.py:293`), and prompt-archive
   linkification (`src/sase/agents_sync/prompt_archive/preparation.py:139`). Making
   rendering a template does not endanger any of it, provided one invariant is enforced:
   **the template owns the substituted text and nothing else.**
3. The right shape is a reserved `artifacts/` xprompt namespace mirroring `skills/` and
   `memory/`: `sase/artifacts/<kind>.md` declares `artifact: <kind>`, its body is the
   substitution template, and its frontmatter declares the handful of per-kind policy
   facts that are hardcoded today. Ship the six builtin renderings as **packaged
   templates** so "customize `@commit`" is just "shadow the packaged file," and so the
   default path and the custom path are the same code path from day one.
4. Keep the resolver in Rust. Do **not** let a template define how a kind is located
   (bash/python resolvers at launch time, per reference). The one resolver extension
   worth having later is declarative: a `roots:` field that registers a path-rooted kind
   without requiring an SDD document sidecar.
5. There is one real hazard that a naive design walks straight into: **declaring a new
   kind silently reinterprets existing prose.** Today `@notes:todo` is left completely
   alone; the moment `notes` is a known kind, the same text becomes a hard launch
   failure. Section 6.3 has the evidence and the mitigation.

## 1. Verified current behavior

### 1.1 The pipeline

Artifact references are resolved in the *late* preprocessing phase, after command
substitution and immediately before plain `@path` file references
(`src/sase/llm_provider/preprocessing.py:164`):

| Phase | Step                | Syntax            | Owner                                    |
| ----- | ------------------- | ----------------- | ---------------------------------------- |
| Early | xprompt references  | `#name`           | `process_xprompt_references`             |
| Early | prompt directives   | `%model`, …       | `extract_prompt_directives`              |
| Late  | command sub         | `$(cmd)`          | `file_references.py`                     |
| Late  | artifact references | `@kind:payload`   | `artifact_ref_prompt.py`                 |
| Late  | file references     | `@path`           | `file_references.py`                     |
| Late  | top-level Jinja2    | `{{ var }}`       | `_jinja.render_toplevel_jinja2`          |

`_expand_artifact_references()` (`artifact_ref_prompt.py:88`) drives one launch:

1. `scan_artifact_refs(text)` — Rust (`artifact_ref/scanner.rs`) returns every
   `@<kind>:<payload>[#<fragment>]` candidate with byte spans and a `well_formed` flag.
2. Python drops candidates inside literal zones (fenced/inline code) and — critically —
   **drops any candidate whose kind is not in `context.known_kinds`**
   (`artifact_ref_prompt.py:120`).
3. `parse_artifact_ref()` — Rust yields a typed `ArtifactRef`. Six builtin kind types
   (`commit`, `chat`, `bug`, `file`, `bead`, `agent`); *every other kind string* falls
   through `classify_kind()` (`sase-core .../artifact_ref/mod.rs:281`) into
   `Document { role }`.
4. `resolve_artifact_ref()` — Rust, filesystem/index reads only, returns one of
   `exact | drifted | vcs_backed | ambiguous | missing | unknown_kind | unknown_repo |
   unknown_project` plus `locator`, `resolved_path`, and `candidates`.
5. `_artifact_ref_replacement()` — **Python, 43 lines, the customization target.**
6. Any failure prints a block and calls `sys.exit(1)` (`artifact_ref_prompt.py:156`).
7. Successes are staged (`_stage_artifact_references`) and appended to the consumption
   ledger (`_record_artifact_ref_consumption`).

### 1.2 What is hardcoded, and where

This is the inventory a template layer has to displace. Every row is a per-kind decision
currently expressed in Python or Rust with no user-facing knob:

| Decision                        | Today                                                                             | Location                                          |
| ------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------- |
| Substituted text                | doc/chat/file/bead/agent → `@<abspath>`; commit → `<repo>@<sha> (checkout: <p>)`; bug → `#<n> <url>` | `artifact_ref_prompt.py:201`                      |
| Fragment annotation             | ` (lines 3-9)`, ` (page 2)`, ` (time 90s)`                                        | `artifact_ref_prompt.py:360`                      |
| Staging label                   | filename, else payload field, else `<project>#<n>`, else `<repo>@<sha>`           | `artifact_ref_prompt.py:316`                      |
| Consumption role                | `chat`/`document` → report; `file` → mime sniff; else source                      | `core/artifact_consumption.py:56`                 |
| Hosted link for prompt archives | per-kind switch on `ref_kind` (commit URL, issue URL, agent page)                 | `agents_sync/prompt_archive/preparation.py:162`   |
| Fragments allowed?              | commit/bug/bead/agent reject them                                                 | `sase-core .../artifact_ref/mod.rs:887`           |
| Kind name grammar               | `[a-z][a-z0-9_-]*`                                                                | `sase-core .../artifact_ref/mod.rs:867`           |
| Builtin kind list + menu order  | `["commit","chat","bug","file","bead","agent"]`                                   | `artifact_ref_models.py:12`, `sase-core .../editor/at_reference.rs:23` |
| `@` menu detail string          | `"document · ~/path"`, derived                                                    | `ace/tui/widgets/_artifact_ref_completion_catalog.py:106` |
| Unresolved-reference hint       | bead → "run `sase bead page refresh`"; agent → "run `sase agent sync`"            | `artifact_ref_prompt.py:457`                      |

### 1.3 The only extension point that exists today

A kind can be added exactly one way: declare a **document sidecar** under
`repos.sidecar.custom` in config. `artifact_ref_context()` walks
`document_sidecar_roles(store.split_sidecar_roles(), include_plans=True)` and turns each
role into an `ArtifactRefDocumentRoot` (`src/sase/artifact_ref_context.py:37`), which
becomes a known kind via `ArtifactRefContext.known_kinds`
(`src/sase/artifact_ref_models.py:289`). That gives you `@research:<relpath>` and
nothing else: no control over rendering, no description, no link policy. A kind that is
not a directory of Markdown in a sidecar repo cannot exist at all.

### 1.4 What is already generic (and must stay that way)

Three subsystems the user named as "builtin functionality for all artifacts" already
work off the *resolution*, not the rendering:

- **Usage tracking.** `~/.sase/artifacts/consumption.jsonl` records canonical ref,
  kind, fragment, role, resolved path, resolution status, and the attributed agent.
  `sase artifact show` surfaces `consumption_count`, `consumed_by_agents`,
  `consuming_agents`, `last_consumed_at`, and the retention protection collector unions
  consumed IDs so consumption keeps bytes alive.
- **Staging + linking.** `stage_prompt_artifact(raw_ref, expanded_ref, resolved_path,
  ref_kind, label, locator)` writes the workspace prompt-artifact manifest;
  `_ArtifactTargetResolver` later turns each record into a hosted URL when the prompt is
  archived to the agents sidecar.
- **Dedupe with the file-reference pass.** `staged_file_paths` is keyed on
  `resolved_path`, not on the emitted text (`artifact_ref_prompt.py:311`) — so a custom
  template cannot cause double-staging.

That last point is the structural reason this project is tractable: the seam between
"what the agent reads" and "what SASE records" is already cut in the right place.

## 2. What "defined by xprompts" could mean

Four readings, in increasing order of power and risk.

**A — Render templates for existing kinds.** The xprompt owns step 5 only. `@commit:`
still parses and resolves exactly as today; the substitution comes from a template.
Small, safe, and it is the literal ask.

**B — Render + per-kind policy.** A adds frontmatter for the facts in §1.2: label,
link, consumption role, allowed fragments, description, failure policy. Displaces most
of the hardcoded per-kind switches.

**C — Declarative new kinds.** B plus a way to register a kind that is not an SDD
sidecar: `roots:` (ordered directories to resolve a relative payload under), and
optionally kind aliases. Resolution logic stays in Rust; the xprompt supplies data.

**D — Programmable resolvers.** The xprompt is a workflow whose `bash:`/`python:` steps
locate the artifact and produce the substitution. Maximum power. Also: arbitrary code
execution once per reference on the launch path, an unbounded failure surface in a
function that currently ends in `sys.exit(1)`, no possible native (Rust) parity for
editor completion, and a direct violation of the repo's Rust-core boundary rule
("if a web app, CLI, or another frontend would need the behavior to match the TUI, treat
it as core backend logic"). Recommend against.

## 3. The customization surface worth exposing

The user asked to think about what else is worth making customizable. Grouped by what
it buys, and tied to the hardcoded thing it replaces.

### 3.1 Rendering (the core ask)

- **Body = substitution template.** Jinja2, rendered with a documented, versioned
  context. Proposed namespace (single root object `ref`, so nothing collides with the
  global Jinja vars `root`/`cl_name`/`agents`):

  ```
  ref.kind            "commit" | "research" | …            (the spelled kind)
  ref.kind_type       commit|chat|bug|file|bead|agent|document
  ref.raw             "@commit:sase@abc1234"
  ref.canonical       "commit:sase@abc1234"                (fragment-free)
  ref.payload.{repo,sha,path,project,number,id,name,source,digest}
  ref.fragment.{type,start,end,page,seconds,rendered}      (or none)
  ref.resolution.{status,locator,resolved_path,candidates}
  ref.checkout        repo checkout path when the kind has one
  ref.url             hosted URL when one is resolvable
  ref.project         active project display name
  ```

  Today's outputs then become one-liners: `@{{ ref.resolution.resolved_path }}{{
  ref.fragment.annotation }}` for documents, `{{ ref.resolution.locator }} (checkout:
  {{ ref.checkout }})` for commits, `#{{ ref.payload.number }} {{ ref.url }}` for bugs.

- **Two-level lookup.** `artifacts/<kind>.md` → `artifacts/<kind_type>.md` → packaged
  default. Because every custom kind is `Document { role }`, one packaged `document.md`
  already covers `plans:`, `research:`, `designs:`, and every future sidecar, while
  `artifacts/research.md` can override just research. This falls out of the existing
  type system for free.

- **The high-value renderings users will actually want.** Worth naming in docs because
  they justify the feature: inline a document's summary line instead of its path; emit a
  hosted URL instead of a local path for kinds the agent should cite but not read; add a
  standing instruction alongside the path ("this is a research report — read the Bottom
  line section first"); render `@bug:` as a full issue block; render `@commit:` as
  `git show` guidance rather than a bare locator.

- **Composition with the file-reference pass is already correct.** A template that emits
  `@<path>` hands off to `process_file_references` exactly as today (copying, inlining,
  dedupe); a template that emits prose does not. That is a genuinely useful dial and it
  needs no new machinery — only documentation.

### 3.2 Policy and identity (frontmatter)

| Field         | Replaces                                            | Notes                                                     |
| ------------- | --------------------------------------------------- | --------------------------------------------------------- |
| `artifact`    | —                                                   | Two-way placement marker, mirroring `skill:`               |
| `description` | derived `"document · ~/path"`                       | `@` menu detail, LSP completion detail, `sase xprompt show` |
| `example`     | —                                                   | Shown in the kind stage of the `@` menu                    |
| `label`       | `_artifact_ref_label` (`artifact_ref_prompt.py:316`) | Staging manifest, prompt archive, ACE rows                 |
| `link`        | `_ArtifactTargetResolver` per-kind switch           | Hosted URL template for archives and `sase artifact open`  |
| `role`        | `artifact_consumption_role`                         | `source｜report｜image｜test-result` for the ledger        |
| `fragments`   | `kind_rejects_fragments`                            | `none｜lines｜page｜time` (list)                            |
| `on_missing`  | unconditional `sys.exit(1)`                         | `error｜warn｜literal` — see §6.3                          |
| `stage`       | implicit for file-backed kinds                      | Whether resolved bytes enter the prompt-artifact pool      |
| `hint`        | `artifact_ref_resolution_hint`                      | "no published page for X; run `sase bead page refresh`"    |
| `aliases`     | —                                                   | `@rsch:` → `@research:` (distinct from fuzzy completion)   |

`link`, `role`, and `stage` are the three that make "builtin functionality for all
artifacts" actually *general*: today a new kind inherits `document` semantics whether
they fit or not, and gets no hosted link at all.

### 3.3 Deliberately out of scope

- **Payload grammar.** Kinds cannot invent syntax. Payload shape stays one of the seven
  Rust-owned forms; a declarative kind is a path payload. Otherwise the scanner, the
  fuzzy `@` menu, and the LSP all need per-kind parsers.
- **Resolution.** No `bash:`/`python:` at launch time (§2, option D).
- **Menu ordering.** Builtin kinds are ranked by a Rust constant that is documented as
  append-only so existing rows keep position; custom kinds sort after, alphabetically.

## 4. Recommended design

### 4.1 Shape

A reserved `artifacts/` xprompt namespace, following the `sase-hb`/`sase-hf` template
exactly — which matters, because those two migrations have already paid the cost of
discovering what a "special xprompt type" needs.

```
sase/artifacts/<kind>.md          project scope   (wins)
~/sase/artifacts/<kind>.md        home scope
src/sase/artifacts/<kind>.md      packaged        (ships the six builtins + document)
<plugin>/artifacts/<kind>.md      plugin scope
```

- Reference name is `artifacts/<kind>`, reserved the way `memory/` is: an ordinary
  xprompt, workflow, config entry, plugin, or skill that claims `artifacts/…` is a load
  diagnostic, not a silent winner.
- Placement is two-way, the way `skills/` is: a definition in `artifacts/` that does not
  declare `artifact:` is rejected with a migration diagnostic, and an `artifact:`
  declaration outside `artifacts/` is rejected the same way
  (`content_layout.skill_placement_issue` is the exact prior art).
- Precedence is first-wins across scopes, reusing `resolve_*_file_sources` — a new
  `resolve_artifact_file_sources()` beside the skill and memory resolvers
  (`src/sase/content_layout.py:206` and `:238`).
- `#artifacts/commit` as an ordinary xprompt call is a **diagnostic**, not an expansion.
  These templates require a resolution context that `#` invocation cannot supply.
  Previewing gets a purpose-built affordance instead (§4.3).

### 4.2 Division of labor

| Concern                              | Owner                                                     |
| ------------------------------------ | ---------------------------------------------------------- |
| Kind grammar, payload, resolution    | Rust (`sase-core`), unchanged                             |
| Kind **registry** (which kinds exist)| Rust: content-layout source records + catalog frontmatter parse |
| Kind metadata (description, example) | Rust parses frontmatter; both catalogs carry it            |
| **Template rendering**               | Python (Jinja2 lives in Python; Rust has no renderer)      |
| Staging / ledger / archive links     | Python, driven by declared metadata rather than a switch   |

The rendering split is not a compromise — it matches skills precisely. Rust discovers
and validates skill sources; Python renders `SKILL.md` through
`SKILL.frame.template.md`. The consequence to accept and document: the native editor
fallback can complete and navigate a custom kind but cannot preview its *rendered*
substitution. That is the same gap skills already have.

### 4.3 Invariants

1. **The template controls the prompt text and nothing else.** `resolved_path`,
   `locator`, canonical ref, and resolution status are computed before rendering and
   passed unchanged to staging and the ledger. A broken template cannot corrupt
   telemetry or protection.
2. **Rendering is pure.** No shell, no filesystem writes, no network. Jinja2 with
   `StrictUndefined` (already the configured environment, `xprompt/_jinja.py:60`), so a
   typo is an error rather than a silent empty string.
3. **Template failure is a launch failure**, reported through the existing
   `_ArtifactRefFailure` block with a new `template` status, and reported statically by
   `sase validate` / `sase doctor` through `record_load_issue`.
4. **Default output is byte-identical to today.** The packaged templates are gated by
   golden tests derived from the current expectations in
   `tests/test_artifact_ref_preprocessing.py`.

New affordance, and the single best thing for template authors:

```bash
sase artifact render @commit:sase@abc1234        # show the substitution, no launch
sase artifact render @research:202608/x.md --json # dump the whole `ref` context
```

### 4.4 Phasing

**Phase 1 — Rendering (delivers the ask).** Rust: `artifacts/` source records in the
content-layout wire, `artifact_reference_name()`, reserved-namespace and placement
diagnostics, catalog entry type (`kind: artifact`, mirroring `memory_type`'s additive
field at `xprompt_catalog.rs:494`). Python: loader, `ArtifactKindTemplate` registry,
`_artifact_ref_replacement()` reduced to "build context → render template," packaged
templates for the six builtins plus `document`, `sase artifact render`. Golden tests.

**Phase 2 — Policy metadata.** `description`, `example`, `label`, `role`, `fragments`,
`hint`, `stage`, `on_missing`. Rewire `_artifact_ref_label`,
`artifact_consumption_role`, `kind_rejects_fragments`, and `document_kind_details` to
read the registry. `@` menu and LSP detail strings come from `description`.

**Phase 3 — Links and new kinds.** `link:` templates feeding `_ArtifactTargetResolver`
and `sase artifact open`. `roots:` for declaring a path-rooted kind without an SDD
sidecar. `aliases:`.

**Phase 4 — Surfaces.** ACE `@` menu, prompt catalog, LSP watched paths and cache
invalidation for `sase/artifacts/`, `sase xprompt list/show`, docs
(`docs/prompt.md`, `docs/llms.md`, `docs/configuration.md`, `docs/editor.md`), glossary
term, `sase memory init`.

Phase 1 is independently shippable and is the whole user-visible ask. Phases 2–3 are
where a *new* kind stops being a second-class citizen.

## 5. Why not the alternatives

**Config-only (`artifacts.kinds.<kind>.template` in `sase.yml`).** Cheapest to build,
and genuinely tempting. Rejected: config-defined xprompts already cannot be skills for
the same reason (`config_skill_destination()`, `xprompt/loader_skills.py:200`) — a
multi-line Markdown template wants a Markdown file, with its own diagnostics, its own
`sase xprompt show` entry, editor support, and per-file provenance. It also forfeits the
scope-precedence chain that project/home/package/plugin sources give for free.

**A new top-level concept, not an xprompt.** Defensible — a kind template is not really
a prompt fragment. Rejected on cost: the xprompt subsystem already supplies source
discovery, precedence, frontmatter validation, load-issue reporting, catalog
presentation, LSP integration, and two recent migrations' worth of proven patterns.
Reusing it is roughly a third of the work, and the user's framing ("defined by
xprompts") is the same instinct.

**Extend document sidecars instead.** Add render config to `repos.sidecar.custom`.
Rejected: it only ever helps document roles. `@commit` and `@bug` — the two the user
named first — are not sidecars and would stay hardcoded.

**Programmable resolvers.** See §2, option D.

## 6. Hazards

### 6.1 Phase ordering

`#xprompt` expands early; `@artifact` resolves late. An artifact-kind xprompt is
therefore never touched by `process_xprompt_references` — it is an xprompt by *file
format and discovery*, not by expansion. Two consequences: `#artifacts/commit` must be a
diagnostic rather than a surprise, and template output lands *before* the top-level
Jinja pass, so a template emitting literal `{{` will be re-rendered. Escape it, and test
for it.

### 6.2 Recursion

A template body containing `@commit:…` or `#other_xprompt` must not re-enter expansion.
Render once, substitute literally. Worth an explicit test.

### 6.3 Declaring a kind reinterprets existing prose — the real one

The `@path` file-reference regex excludes `:` from its capture
(`src/sase/file_references.py:31`):

```python
_FILE_REF_PATTERN = r"(?:^|(?<=\s)|(?<=[\"']))@((?:[^\s,;:()[\]{}\"'`])+)"
```

So `@notes:todo` captures only `notes` — a bare word with no `/` and no `.`, which the
parser skips as a literal marker (`file_references.py:91`). And unknown artifact kinds
are skipped outright (`artifact_ref_prompt.py:120`). **Net effect today: any
`@word:payload` with an unrecognized `word` is left completely alone.**

The moment `notes` becomes a declared kind, every `@notes:…` in every prompt, plan,
bead note, and ChangeSpec that flows through preprocessing becomes a resolution attempt,
and an unresolvable one ends the launch at `sys.exit(1)`. Declaring a kind is therefore
a **breaking change to the meaning of existing text**, and the blast radius scales with
how ordinary the kind name is (`notes`, `todo`, `ref`, `doc`, `time`).

Mitigations, in order of value:

1. `on_missing:` per kind, defaulting to `error` for the packaged builtins (preserving
   today's behavior exactly) and `warn` for newly declared kinds — warn leaves the text
   literal and prints once. Users opt into `error` when they trust the kind.
2. A `sase doctor` check that reports newly declared kinds alongside a count of
   `@<kind>:` occurrences found in the project's SDD corpora, so the reinterpretation is
   visible before it bites.
3. Document the naming guidance: prefer distinctive kind names.

### 6.4 Schema bumps

`ARTIFACT_REF_WIRE_SCHEMA_VERSION` is 3 and asserted exactly on both sides
(`artifact_ref_models.py:11`, `artifact_ref_operations.py:189`);
`CONTENT_LAYOUT_SCHEMA_VERSION` just moved 2→3 for `sase-hf`. This work touches both,
plus the xprompt catalog wire and the LSP catalog. `sase-hf`'s open note is the cautionary
tale: a core-side bump landed on `sase-core` master ahead of a release, and every
workspace that ran `just install` picked up schema 3 while `pyproject` still pinned
`>=0.20.0,<0.21.0`, breaking `just check-full` repo-wide. **Release the core version,
raise the floor, and update the assertions in the same landing.**

### 6.5 Kind-list duplication

Three places assert the builtin list: `artifact_ref_models.py:12`,
`sase-core .../editor/at_reference.rs:23` (documented as "the single source of truth;
nothing else may hardcode the list" — and it is already duplicated), and the menu-order
constant. A registry should collapse these to one Rust source with a Python projection,
not add a fourth.

### 6.6 Naming

`artifacts/` is overloaded: `~/.sase/artifacts/` is the artifact-*file* index and trash,
and `SASE_ARTIFACTS_DIR` is a per-agent run directory. A `sase/artifacts/` directory
that holds *reference-kind definitions* is a third meaning. Alternatives considered:
`sase/refs/` (`#refs/commit`) reads accurately but buries the connection to `@`;
`sase/artifact_kinds/` is unambiguous but ugly and breaks the one-word pattern set by
`skills/` and `memory/`. **Recommend `sase/artifacts/` with the docs being explicit
about the three meanings** — the discoverability of matching `@<kind>` to
`artifacts/<kind>.md` outweighs the collision, which is between a project-source
directory and two runtime state directories that users rarely type.

## 7. Open questions for the project owner

1. **Namespace name** — `artifacts/` (recommended), `refs/`, or something else? This is
   the one decision that is expensive to reverse, since it becomes a reserved namespace.
2. **Should `on_missing: warn` be the default for user-declared kinds?** It is the safe
   answer to §6.3 but it introduces a second failure mode (a silently unexpanded
   reference) into a pipeline that is currently strict everywhere.
3. **Is Phase 3 (`roots:`, declaring kinds outside SDD sidecars) actually wanted**, or
   is "a kind is a document sidecar" a constraint worth keeping? Phases 1–2 deliver the
   stated ask without it.
4. **Should packaged builtin templates be user-visible files** (shipped under
   `src/sase/artifacts/`, listed by `sase xprompt list`) or an internal default that
   only materializes when overridden? Visible is better for discoverability and makes
   `sase artifact render` self-documenting; it also means the defaults become a public
   contract that must be versioned.

## Appendix: primary sources

- `src/sase/artifact_ref_prompt.py` — expansion, rendering, staging, ledger, hints
- `src/sase/artifact_ref_models.py`, `artifact_ref_operations.py`, `artifact_ref_context.py`
- `src/sase/core/artifact_consumption.py`, `src/sase/core/prompt_artifact_staging.py`
- `src/sase/agents_sync/prompt_archive/preparation.py` — hosted-link resolution
- `src/sase/llm_provider/preprocessing.py`, `src/sase/file_references.py`
- `src/sase/content_layout.py`, `src/sase/xprompt/loader_skills.py`,
  `src/sase/xprompt/loader_memory.py`, `src/sase/xprompt/reserved_namespaces.py`
- `src/sase/ace/tui/widgets/_artifact_ref_completion_catalog.py`
- `sase-core`: `crates/sase_core/src/artifact_ref/{mod,scanner,wire,list}.rs`,
  `crates/sase_core/src/editor/at_reference.rs`, `crates/sase_core/src/xprompt_catalog.rs`
- `plans:202608/xprompt_memories.md` (bead `sase-hf`) — the migration template followed here
