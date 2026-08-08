---
create_time: 2026-08-08
updated_time: 2026-08-08
status: research
---

# Xprompt-Defined Artifact References: Customize the Rendering, Not the Resolver

**Research question.** How should SASE let xprompts define artifact references
(`@commit:…`, `@research:…`) so a user controls the substituted text — and whatever
else is worth exposing — while every kind keeps the builtin machinery (usage tracking,
staging, archive linking, completion) for free?

**Scope.** `sase` at `010b01a41` and the linked `sase-core` checkout at `origin/master`,
read 2026-08-08. Precedent is `sase-hb` (canonical `skills/`, `#skills/<name>`, landed)
and `sase-hf` (xprompt memories, `#memory/<stem>`, phases `.3` and `.5` still
IN_PROGRESS). This consolidates two independent reports (`__a` by `research.02.cdx`,
`__b` by `research.02.cld`) plus verification of every load-bearing claim in both.

## Recommendation

Build it, and scope it to one layer: **make the render step a template; leave everything
else alone.**

1. **Reserved `artifact_refs/` xprompt namespace.** `sase/artifact_refs/<kind>.md`
   declares `artifact_ref: true`, filename stem *is* the kind, body is the substitution
   template. Project → home → plugin → package, first-wins, two-way placement rule —
   copied verbatim from `sase-hb`/`sase-hf`.
2. **Ship the seven builtin renderings as packaged templates** (`src/sase/artifact_refs/`,
   matching the real packaged-skills location `src/sase/skills/`), so "customize
   `@commit`" is "shadow a file" and the default and custom paths are the same code from
   day one. Golden tests pin byte-identical output.
3. **Rust keeps grammar, payload parsing, resolution, placement/precedence rules, and
   the reserved-namespace diagnostic. Python renders** (Jinja lives in Python) and
   assembles per-launch context, exactly as it does today.
4. **No programmable resolvers.** No `bash:`/`python:` steps at launch time.
5. **Protect rendered output from the top-level Jinja pass** (§6.1) — a 10-line fix that
   is safer than either source report's proposal.
6. **Phase 1 alone delivers the stated ask.** Start it after `sase-hf` lands.

Recommended source directory is `sase/artifact_refs/`, **not** `sase/artifacts/` — see
§7.1.

## 1. Verified ground truth: the seam is already cut correctly

The layer worth opening is unusually small, and the machinery worth preserving is
already independent of it.

`_expand_artifact_references()` (`src/sase/artifact_ref_prompt.py:88`) runs one launch:
Rust scans (`scan_artifact_refs`) → Python drops literal-zone hits and **any candidate
whose kind is not in `context.known_kinds`** (`:120`) → Rust parses and resolves →
**Python `_artifact_ref_replacement()` (`:201`, ~50 lines) produces the text** → failures
`sys.exit(1)` (`:156`) → successes are staged and appended to the consumption ledger.

The structural fact that makes this project tractable: `_artifact_ref_replacement()`
returns `tuple[str, Path | None]`, and **only the `Path` reaches the tracking layers.**

| Concern | Keyed on | Location |
| --- | --- | --- |
| Consumption ledger | fragment-free canonical ref | `core/artifact_consumption.py` |
| File-ref dedupe | `resolved_path`, not emitted text | `artifact_ref_prompt.py:311` |
| Archive linkification | staged record (`pool_relpath`/`sha256`/vcs/locator/`ref_kind`) | `agents_sync/prompt_archive/preparation.py:162` |
| Retention protection | consumed artifact IDs | consumption collector |

A template that emits pure prose therefore cannot corrupt telemetry, dedupe, links, or
retention. That is the whole safety argument, and it holds without any additional
enforcement.

**The registry seam is Python, not Rust.** Both source reports say "Rust owns the
registry." The code says otherwise: `known_kinds` is a Python property
(`artifact_ref_models.py:290`) unioning Rust's `BUILTIN_ARTIFACT_REF_KINDS`
(`sase-core .../editor/at_reference.rs:23`) with document roots that **Python** discovers
from the SDD store (`artifact_ref_context.py:37`). Declaring template-backed kinds
extends an existing Python seam. This makes the work smaller than "move the registry to
Rust," and it does not violate the Rust-core boundary: grammar, resolution, and the
source-discovery/precedence rules belong in Rust (like `resolve_skill_file_sources`);
per-launch context assembly is legitimately Python.

### 1.1 The inventory a template layer displaces

Every row is a per-kind decision with no user-facing knob today:

| Decision | Today | Location |
| --- | --- | --- |
| Substituted text | doc/chat/file/bead/agent → `@<abspath>`; commit → `<repo>@<sha> (checkout: <p>)`; bug → `#<n> <url>` | `artifact_ref_prompt.py:201` |
| Fragment annotation | ` (lines 3-9)`, ` (page 2)`, ` (time 90s)` | `artifact_ref_prompt.py:360` |
| Staging label | filename, else payload field, else `<project>#<n>`, else `<repo>@<sha>` | `artifact_ref_prompt.py:316` |
| Consumption role | `chat`/`document` → report; `file` → mime sniff; else source | `core/artifact_consumption.py:56` |
| Hosted archive link | per-kind switch on `ref_kind` | `prompt_archive/preparation.py:187` |
| Whether bytes are pooled | `_NON_FILE_REF_KINDS = {"agent","bug","commit"}` | `core/prompt_artifact_staging.py:33` |
| Fragments allowed? | commit/bug/bead/agent reject them | `sase-core .../artifact_ref/mod.rs:887` |
| Builtin kind list + menu order | `["commit","chat","bug","file","bead","agent"]` | `at_reference.rs:23` (+ duplicated in `artifact_ref_models.py:12`) |
| `@` menu detail | `"document · ~/path"`, derived | `_artifact_ref_completion_catalog.py:106` |
| Unresolved hint | bead → `sase bead page refresh`; agent → `sase agent sync` | `artifact_ref_prompt.py:457` |

### 1.2 The only extension point today

A kind can be added exactly one way: declare a document sidecar under
`repos.sidecar.custom`. That yields `@<role>:<relpath>` and nothing else — no rendering
control, no description, no link policy. A kind that is not a directory of Markdown in a
sidecar repo cannot exist at all. Every non-builtin kind string falls through
`classify_kind()` (`mod.rs:281`) into `Document { role }`, which is why one packaged
`document.md` already covers `plans:`, `research:`, and every future sidecar.

## 2. What "defined by xprompts" could mean

**A — Render templates for existing kinds.** The template owns step 5 only. Small, safe,
and the literal ask. **Recommended as Phase 1.**

**B — Render + per-kind policy frontmatter.** Displaces most of §1.1. **Phase 2.**

**C — Declarative new kinds.** `roots:` registers a path-rooted kind without an SDD
sidecar. Resolution stays in Rust; the file supplies data. **Phase 3, optional.**

**D — Programmable resolvers** (`bash:`/`python:` locate the artifact). **Reject.**
Arbitrary code once per reference on the launch path, unbounded failure surface in a
function that currently ends in `sys.exit(1)`, no possible native (Rust) parity for
editor completion, and a direct violation of the Rust-core boundary rule. Both source
reports reject this independently.

**E — `@kind:x` as sugar for early `#artifact_refs/kind(x)` expansion.** **Reject.** The
`#` pass runs in `preprocess_prompt_early`, before the artifact context exists; the
template would have to rediscover roots, repos, and URLs; direct `#` invocation would
bypass consumption tracking; and template output re-entering command substitution and
directive extraction is an injection surface. `#artifact_refs/commit` must be a **load
diagnostic, not an expansion.**

**F — Config-only (`artifacts.kinds.<kind>.template` in `sase.yml`).** **Reject.**
Config-defined xprompts already cannot be skills for exactly this reason
(`config_skill_destination()`, `xprompt/loader_skills.py:200`): a multi-line Markdown
template wants a Markdown file with its own diagnostics, `sase xprompt show` entry,
editor support, and per-file provenance. It also forfeits the scope-precedence chain.

**G — A new top-level concept, not an xprompt.** Defensible (a kind template is not
really a prompt fragment) but rejected on cost: the xprompt subsystem already supplies
source discovery, precedence, frontmatter validation, load-issue reporting, catalog
presentation, LSP integration, and two migrations' worth of proven patterns.

## 3. Recommended design

### 3.1 Shape

```text
sase/artifact_refs/<kind>.md          project scope   (wins)
~/sase/artifact_refs/<kind>.md        home scope
<plugin>/artifact_refs/<kind>.md      plugin scope
src/sase/artifact_refs/<kind>.md      packaged (six builtins + document fallback)
```

- **Filename stem is the kind.** Frontmatter must not rename it — this avoids a second
  name-versus-source identity split and keeps `research.md` deterministically bound to
  `@research:`.
- **Reserved namespace.** `artifact_refs/…` claimed by an ordinary xprompt, workflow,
  config entry, plugin, or skill is a load diagnostic — mirroring
  `reserved_memory_namespace_issue` (`content_layout.py:314`, Rust-backed).
- **Two-way placement.** A definition in `artifact_refs/` without `artifact_ref:` is
  rejected with a migration diagnostic, and `artifact_ref:` outside `artifact_refs/` is
  rejected the same way — `SkillPlacementRuleWire::SkillOutsideSkillSource`
  (`sase-core .../content_layout.rs:325`) is exact prior art.
- **Precedence** reuses `resolve_*_file_sources`: a new
  `resolve_artifact_ref_file_sources()` beside `content_layout.py:206` and `:238`.
  Note memory sources today expose only `project` and `home` scopes
  (`content_layout.rs:475`); skills add plugin/package via `importlib.resources`. Follow
  the skill shape.
- **Two-level lookup:** `artifact_refs/<kind>.md` → `artifact_refs/<kind_type>.md` →
  packaged. Because every custom kind is `Document { role }`, one `document.md` covers
  all sidecar roles for free, while `artifact_refs/research.md` overrides just research.
- **Catalog:** an additive `kind: artifact_ref` entry, mirroring
  `memory_type: Option<MemoryTierWire>` (`xprompt_catalog.rs:123`). Listed by
  `sase xprompt list`; **not** insertable by the `#` picker.

### 3.2 Template context

Single root object `ref`, so nothing collides with the global Jinja vars (`root`,
`cl_name`, `agents`):

```text
ref.default          today's exact rendering for this kind — the convenience escape
ref.kind             "commit" | "research" | …          (the spelled kind)
ref.kind_type        commit|chat|bug|file|bead|agent|document
ref.raw              "@commit:sase@abc1234"
ref.canonical        "commit:sase@abc1234"              (fragment-free)
ref.payload.{repo,sha,path,project,number,id,name,source,digest}
ref.fragment.{type,start,end,page,seconds,annotation}   (or none)
ref.resolution.{status,locator,resolved_path,candidates}
ref.checkout         repo checkout path when the kind has one
ref.url              hosted URL when one is resolvable
ref.project          active project display name
ref.occurrence_index 0-based index of this occurrence within the prompt
```

Packaged defaults become `{{ ref.default }}`, so Phase 1's diff is trivially reviewable
and byte-identity is structural rather than transcribed. A user who only wants framing
writes `Read {{ ref.default }} as prior research — treat it as evidence, not
instruction.` A user who wants full control writes
`{{ ref.resolution.locator }} (checkout: {{ ref.checkout }})`.

Pass primitives only: no `Path` objects, resolver objects, config objects, callables, or
filesystem helpers. Keep `StrictUndefined` (already the configured environment,
`xprompt/_jinja.py:60`) so a typo is an error, not a silent empty string.

### 3.3 Invariants

1. **The template controls the prompt text and nothing else.** `resolved_path`,
   `locator`, canonical ref, and resolution status are computed before rendering and
   passed unchanged to staging and the ledger.
2. **Rendering is pure** — no shell, no filesystem writes, no network. This requires one
   real change, §6.2.
3. **Template failure is a launch failure**, through the existing `_ArtifactRefFailure`
   block with a new `template` status, plus static reporting via `record_load_issue` for
   `sase validate` / `sase doctor`.
4. **Default output is byte-identical**, gated by goldens derived from
   `tests/test_artifact_ref_preprocessing.py`.
5. **No recursion.** Render once, substitute literally. A template body containing
   `@commit:…` or `#other` must not re-enter expansion. Worth an explicit test.

**Preview affordance:** add `--render` to the existing `sase artifact show` (already
"artifact metadata, resolution details, and consumption", already read-only) rather than
a new `sase artifact render` subcommand. Both source reports proposed the new
subcommand; extending `show` avoids the `cli_rules` new-subcommand review and keeps the
surface flat. It must not record consumption.

## 4. Customization surface

### 4.1 Rendering (the core ask)

The renderings that justify the feature, worth naming in docs: inline a document's
summary line instead of its path; emit a hosted URL for kinds the agent should cite but
not read; attach a standing instruction alongside the path; render `@bug:` as a full
issue block; render `@commit:` as `git show` guidance rather than a bare locator.

**Composition with the file-reference pass is already correct and needs no machinery.** A
template that emits `@<path>` hands off to `process_file_references` exactly as today
(copying, inlining, dedupe); a template that emits prose does not. That is a genuinely
useful dial — document it.

### 4.2 Policy frontmatter (Phase 2–3)

| Field | Replaces | Notes |
| --- | --- | --- |
| `artifact_ref` | — | Two-way placement marker, mirroring `skill:` |
| `description` | derived `"document · ~/path"` | `@` menu detail, LSP detail, `sase xprompt show` |
| `example` | — | Shown in the kind stage of the `@` menu |
| `label` | `_artifact_ref_label` | Staging manifest, prompt archive, ACE rows |
| `link` | `_ArtifactTargetResolver` per-kind switch | Hosted URL template for archives and `sase artifact open` |
| `role` | `artifact_consumption_role` | `source｜report｜image｜test-result` for the ledger |
| `fragments` | `kind_rejects_fragments` | `none｜lines｜page｜time` |
| `stage` | `_NON_FILE_REF_KINDS` | Whether resolved bytes enter the prompt-artifact pool |
| `hint` | `artifact_ref_resolution_hint` | Per-kind unresolved-reference guidance |
| `on_missing` | unconditional `sys.exit(1)` | `error｜warn｜literal` — see §6.3 |
| `roots` | document-sidecar-only extension | Phase 3: path-rooted kind without a sidecar |

`link`, `role`, and `stage` are the three that make "builtin functionality for all
artifacts" actually *general*. Concretely: a non-file-backed custom kind today falls
through `stage_prompt_artifact`'s `source is None` branch
(`prompt_artifact_staging.py:99`) and is **never staged, therefore never linked in the
prompt archive**. Only frontmatter fixes that.

**One addition neither source report proposed: `ref.occurrence_index`.** Dedupe today is
by canonical ref for the *ledger*, but the full text is substituted at every occurrence.
Exposing the occurrence index lets a template render fully on first mention and a short
form thereafter — meaningful prompt-bloat reduction for repeated refs, expressed in the
template rather than as another policy knob.

### 4.3 Deliberately out of scope

- **Payload grammar.** Kinds cannot invent syntax; payload shape stays one of the
  Rust-owned forms. Otherwise the scanner, the fuzzy `@` menu, and the LSP all need
  per-kind parsers.
- **Resolution.** No launch-time code (§2, option D).
- **Menu ordering.** `BUILTIN_ARTIFACT_REF_KINDS` is documented as append-only so
  existing rows keep position; custom kinds sort after, alphabetically.
- **`aliases:`.** Drop or defer. A second name for a kind multiplies the §6.3 blast
  radius and the completion catalog for little gain over fuzzy completion.
- **Sandboxed Jinja + filter allowlist + output caps.** `__a` proposes a
  `SandboxedEnvironment`; it buys nothing against a threat model in which xprompt bodies
  already run `$(...)` shell. Adopt the *hygiene* (primitives only) and skip the sandbox
  as premature. The one real asymmetry is worth stating: an xprompt's shell runs when
  *you* invoke `#name`, whereas a renderer runs whenever *anyone's* prompt mentions
  `@commit:` — which argues for keeping renderers pure, not for sandboxing a pure render
  of primitive data.

## 5. Provenance (from `__a`, trimmed)

Once output is customizable, "which renderer framed this?" becomes answerable only if
recorded. Add to the **staging manifest** (which already carries `expanded_ref`, the
rendered text) as additive fields:

```text
renderer_scope     project | home | plugin | package
renderer_source    sase/artifact_refs/research.md
renderer_sha256    <digest of normalized definition>
```

**Not** to the consumption ledger. `__a` proposes both; the ledger's value is a stable
artifact-identity join key, and renderer digests churn on every template edit. Staging is
per-launch and is where the rendered text already lives.

Keep `xprompts.json` (launch-boundary `#` composition) and the artifact consumption
ledger as separate measures — do not count renderer use as an xprompt use. ACE can add an
Artifact References view grouped by kind, role, renderer, project, and consuming agent
over the existing ledger.

The durable prompt archive continues to link the original `@kind:payload` from
`raw_ref`, regardless of what the model received.

## 6. Hazards

### 6.1 Rendered output can hijack the top-level Jinja pass — resolved

The two source reports disagree here and **both are wrong**.

Verified mechanism: `is_jinja2_template()` (`xprompt/_jinja.py:42`) is a **whole-prompt**
regex for `{{…}}` / `{%…%}` / `{#…#}`. Artifact replacement happens at late step 3;
top-level Jinja at late step 5. So a template emitting `{{` does not merely get itself
re-rendered — it **flips the entire prompt into Jinja rendering**, and
`render_toplevel_jinja2` uses `StrictUndefined` and `sys.exit(1)` on error. One custom
`@commit` template could kill launches for prompts that merely contain a literal `{{ }}`
somewhere outside a fence.

- `__b`'s "escape it and test for it" underestimates this: the damage is to *other*
  people's text, not the template's own.
- `__a`'s fix — move top-level Jinja before artifact resolution — works but silently
  changes two unrelated behaviors: content inlined by `process_file_references` would
  stop being Jinja-rendered, and artifact refs emitted by top-level Jinja would newly
  start resolving. That is a semantic change to existing prompts for a problem that only
  exists in the new feature.

**Recommended instead:** protect rendered artifact spans between late step 4 (file refs)
and step 5 (Jinja), using the existing `protect_fenced_blocks` /
`protect_disabled_regions` placeholder machinery, and unprotect immediately after. The
output still reaches `process_file_references` (so the `@path` handoff of §4.1 keeps
working) and still reaches prettier at step 6, but is opaque to Jinja. Default templates
are unaffected; no reorder; ~10 lines.

### 6.2 Rendering is not pure today

`_artifact_ref_replacement()` calls `_materialize_vcs_file_reference()`
(`artifact_ref_prompt.py:209`) for `file` refs with `vcs_backed` status — it **writes a
materialized file**. Neither source report caught this. Invariant 3.3.2 requires moving
that materialization out of the render step into the resolve/prepare step and passing the
resulting path into the context. Otherwise either a template controls whether a file gets
materialized (and one that drops the pointer silently skips it) or you need lazy
evaluation inside Jinja, which is impure by construction.

### 6.3 Declaring a kind reinterprets existing prose — real, but smaller than `__b` claims

The mechanism is exactly as `__b` describes, and it verifies. `_FILE_REF_PATTERN`
(`file_references.py:31`) excludes `:` from its capture class, so `@notes:todo` captures
only `notes`; the bare-word skip (`file_references.py:91`, no `/` and no `.`) then leaves
it alone, and unknown artifact kinds are skipped outright
(`artifact_ref_prompt.py:120`). **Net effect today: any `@word:payload` with an
unrecognized `word` is left completely alone.** Declare `notes` as a kind and the same
text becomes a resolution attempt that ends the launch at `sys.exit(1)`.

Two corrections to `__b`'s framing:

- **Narrower blast radius.** Only `preprocess_prompt_late` touches artifact references,
  and it is reached from agent launch (`llm_provider/_invoke.py:144`), workflow prompt
  steps (`workflow_executor_steps_prompt.py:242`), and `sase xprompt expand` /
  `xprompt_handler.py:57` (validate mode — confirmed live: `sase xprompt expand 'see
  @file:foo'` already exits 1). `sdd/_expand.py` and `run_agent_exec_plan_accept.py` use
  the **early** phase only, so plan expansion and follow-up prompts are *not* affected.
  Expanded `#memory/…` and `#skills/…` bodies **are**, since `#` expands early and its
  output flows into the late phase.
- **Zero current exposure in this repo.** Scanning `sase/memory/`, `src/sase/skills/`,
  `src/sase/xprompts/`, and `docs/` for `@<word>:<payload>` finds only `@file` (2
  occurrences), which is already a builtin kind.

That reframes this from a blocker to a pre-flight check. Mitigations, in order of value:

1. A `sase doctor` check that reports newly declared kinds alongside a count of
   `@<kind>:` occurrences in the project's corpora, so reinterpretation is visible before
   it bites.
2. `on_missing:` per kind, **defaulting to `error` everywhere** — matching today's
   strictness — with `warn` as an explicit opt-in. `__b` proposes `warn` as the default
   for user-declared kinds and then correctly doubts it in its own open question #2:
   a silently unexpanded reference is a second failure mode in a pipeline that is strict
   everywhere else, and §6.3's measured exposure does not justify it.
3. Naming guidance: prefer distinctive kind names over `notes`, `todo`, `ref`, `doc`.

### 6.4 Schema bumps — with a live cautionary tale

`ARTIFACT_REF_WIRE_SCHEMA_VERSION` is 3 and asserted exactly on both sides
(`artifact_ref_models.py:11`, `artifact_ref_operations.py:192`);
`CONTENT_LAYOUT_SCHEMA_VERSION` just moved 2→3 for `sase-hf`. This work touches both,
plus the xprompt catalog and LSP catalog wires.

`sase-hf`'s open bead note is the exact failure to avoid: the core-side bump landed on
`sase-core` master ahead of a release, and because the `Justfile` builds `sase-core-rs`
from the linked checkout whenever `Cargo.toml` + cargo exist, every workspace that ran
`just install` picked up schema 3 while `pyproject` still pinned `<0.21.0` — breaking
`just check-full` repo-wide. **Release the core version, raise the floor, and update the
assertions in the same landing.**

### 6.5 Kind-list duplication

`BUILTIN_ARTIFACT_REF_KINDS` (`at_reference.rs:23`) is documented as "the single source
of truth; nothing else may hardcode the list" — and is already duplicated at
`artifact_ref_models.py:12`, with menu order a third expression. A registry should
collapse these to one Rust source with a Python projection, not add a fourth.

## 7. Resolved disagreements

### 7.1 Directory name: `artifact_refs/` (`__a`) beats `artifacts/` (`__b`)

`__b`'s own §6.6 makes the case against `__b`'s choice. "Artifacts" already has three
meanings: `~/.sase/artifacts/` (file index, trash, consumption ledger), `.sase/artifacts/`
(workspace prompt-artifact staging — literally `_ArtifactTargetResolver.staging_root`),
and `SASE_ARTIFACTS_DIR` (per-agent run dir). A fourth meaning in a project source
directory is a real cost, and `__b`'s discoverability argument — matching `@<kind>` to
`<dir>/<kind>.md` — survives intact under `artifact_refs/`. The decisive point is
semantic: `sase/artifact_refs/commit.md` does not describe an artifact; it describes how
`@commit:` *renders*. `refs/` is a worse third option (collides with git's `refs/`).

### 7.2 Mandatory opaque pointer (`__a`) — reject

`__a` requires `{{ artifact.pointer }}` exactly once, so a template cannot drop,
redirect, or multiply the artifact. The invariants this protects are **already protected
structurally** (§1): dedupe keys on `resolved_path`, the ledger keys on the canonical
ref, and archive links key on the staged record. A template that drops the path changes
only what the model reads — which is the customization being requested. Worse, the
mandatory pointer forbids several of the highest-value renderings **both** reports name
(hosted URL instead of local path; summary instead of path; `git show` guidance).

Keep the concern as a **lint**, not a rule: `sase doctor` warns when a template for a
file-backed kind renders output containing neither an `@`-path nor a URL, so silent
artifact-dropping is visible without being illegal. `ref.default` (§3.2) makes the safe
case a one-liner, which is what `__a` was really reaching for.

### 7.3 Frontmatter key

`artifact_ref: true` — a truthy two-way marker mirroring `skill:`, matching the directory
name. `__a`'s nested `artifact_ref: {family, semantic_role, …}` mapping is unnecessary
once the filename stem is the kind and policy fields are flat (§4.2).

### 7.4 Everything both reports agreed on, kept

Options D/E/F/G rejected; Markdown-file-per-kind with scope precedence; two-way placement;
additive catalog field; Rust grammar + Python rendering; packaged byte-identical defaults;
`#<ns>/<kind>` as a diagnostic; native editors can complete and navigate a custom kind but
cannot preview its *rendered* substitution — the same accepted gap skills already have.

## 8. Phasing, sequencing, and cost

**Phase 1 — Rendering (delivers the ask).** *sase-core:* `artifact_refs/` source records
in the content-layout wire, `artifact_ref_reference_name()`, reserved-namespace and
placement diagnostics, additive catalog entry type. *sase:* loader, kind→template
registry, `_artifact_ref_replacement()` reduced to "build context → render", seven
packaged templates, Jinja-protection fix (§6.1), materialization move (§6.2),
`sase artifact show --render`, golden tests.

**Phase 2 — Policy metadata.** `description`, `example`, `label`, `role`, `fragments`,
`hint`, `stage`, `on_missing`. Rewire `_artifact_ref_label`,
`artifact_consumption_role`, `kind_rejects_fragments`, `_NON_FILE_REF_KINDS`, and
`document_kind_details` to read the registry. Add renderer provenance to staging (§5).

**Phase 3 — Links and declarative kinds.** `link:` feeding `_ArtifactTargetResolver` and
`sase artifact open`; `roots:` for path-rooted kinds without an SDD sidecar; the
`sase doctor` kind-occurrence check (§6.3).

**Phase 4 — Surfaces.** ACE `@` menu, prompt catalog, **LSP watched paths and cache
invalidation for `sase/artifact_refs/` from the first implementation** — the refresh gap
found in `sase-hf.1` is the reason to front-load this. Then `sase xprompt list/show`,
docs (`prompt.md`, `llms.md`, `configuration.md`, `editor.md`), glossary term,
`sase memory init`.

**Cost:** roughly one medium bead per phase split across the two repos — an epic of
`sase-hf`'s shape and size.

**Sequencing:** start after `sase-hf` lands. Phases `.3` and `.5` are still IN_PROGRESS
and the `CONTENT_LAYOUT_SCHEMA_VERSION` 2→3 breakage on that bead is unresolved; this
work touches the same wire and would compound it.

## 9. Open questions for the project owner

1. **`sase/artifact_refs/` confirmed?** This is the one decision that is expensive to
   reverse, since the namespace becomes reserved. §7.1 recommends it over `artifacts/`.
2. **Is Phase 3 (`roots:`) wanted**, or is "a kind is a document sidecar" a constraint
   worth keeping? Phases 1–2 deliver the stated ask without it.
3. **Should packaged templates be user-visible files** (under `src/sase/artifact_refs/`,
   listed by `sase xprompt list`) or internal defaults that materialize only on
   override? Visible is better for discoverability and makes `--render` self-documenting;
   it also makes the defaults a public contract that must be versioned.
4. **Should `on_missing: warn` exist at all?** §6.3 recommends `error` as the universal
   default; `warn` is only worth building if you expect to declare common-word kinds.

## Appendix: primary sources

- `src/sase/artifact_ref_prompt.py` — expansion, rendering, staging, ledger, hints
- `src/sase/artifact_ref_models.py`, `artifact_ref_operations.py`, `artifact_ref_context.py`
- `src/sase/core/artifact_consumption.py`, `src/sase/core/prompt_artifact_staging.py`
- `src/sase/agents_sync/prompt_archive/preparation.py` — hosted-link resolution
- `src/sase/llm_provider/preprocessing.py`, `src/sase/file_references.py`,
  `src/sase/xprompt/_jinja.py`
- `src/sase/content_layout.py`, `src/sase/xprompt/loader_skills.py`,
  `src/sase/xprompt/reserved_namespaces.py`
- `src/sase/ace/tui/widgets/_artifact_ref_completion_catalog.py`
- `sase-core`: `crates/sase_core/src/artifact_ref/{mod,scanner,wire,list}.rs`,
  `crates/sase_core/src/editor/at_reference.rs`,
  `crates/sase_core/src/{xprompt_catalog,content_layout}.rs`
- `plans:202608/xprompt_memories.md` and bead `sase-hf` — the migration template followed
  here, including its open schema-version note
- Source reports: `artifact_reference_rendering__a.md` (`research.02.cdx`),
  `artifact_reference_rendering__b.md` (`research.02.cld`)
