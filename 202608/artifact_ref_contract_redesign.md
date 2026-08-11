---
create_time: 2026-08-11
updated_time: 2026-08-11
status: research
---

# Replacing Xprompt-Defined Artifact References with a Provider Contract

## Research question

How should SASE replace the xprompt-defined artifact-reference system introduced by the
`sase-ho` epic with a ref contract that supports core builtins, a safe local-file ref,
pluggable sidecar artifact refs and file hooks, durable publication links,
back-references, and dynamic Artifacts tabs?

This report is research and design only. It does not create the proposed
`sase-org/sase-research` repository, change configuration, modify a bead, or implement
any part of the design.

## Bottom line

Do not revert the `sase-ho` commits wholesale. The epic combined two different kinds of
work:

- useful shared machinery for scanning, parsing, resolving, filtering, completing,
  staging, and publishing refs; and
- an xprompt adapter that turned ref definitions into synthetic xprompt sources and made
  the xprompt catalog part of the ref registry.

The second part should be removed. Much of the first part should be kept and reshaped
around a Rust-owned, versioned `ArtifactRefProviderSpec` and a normalized
`ArtifactEntry`/`ResolvedArtifactRef` result. Builtin providers should be implemented
directly in the core. Installed Python plugins should use Pluggy hooks only to register
immutable, declarative provider specs; they should not execute arbitrary resolver or
renderer callbacks on the launch, completion, or TUI paths.

The most important architectural decisions are:

1. Ref parsing and semantics belong to the shared Rust core, not the xprompt loader.
2. The current project is an explicit input derived once from each prompt segment's VCS
   xprompt workflow. It must not be guessed from the process working directory.
3. Every resolved occurrence is recorded in an immutable per-agent use manifest at
   launch time, including its exact source revision or captured content digest.
4. Local files and dirty/untracked sidecar files are snapshotted into a true SHA-256
   content-addressed store. One byte sequence has exactly one object path.
5. Publication is two-stage: publish the agent and its linked prompt first, then update
   sidecar `Referenced By` sections through an idempotent, retryable outbox. Cross-repo
   atomicity is neither available nor necessary.
6. The Artifacts UI is driven by provider descriptors. `Files` remains a special
   aggregate view grouped by logical path and version; sidecar providers get generic,
   dynamic top-level panes such as `Plans` and `Research`.
7. The new `sase-research` repository is a plugin/source repository. The similarly named
   `sase--research` repository remains the project's artifact repository. Merely
   configuring a linked clone does not install the plugin, so installation and
   diagnostics must be designed explicitly.

## Scope and evidence

The source review used these repository states on 2026-08-11:

| Repository       | Revision       | Role in this research                                        |
| ---------------- | -------------- | ------------------------------------------------------------ |
| `sase`           | `87cffa3b8f5c` | launch pipeline, configuration, file hooks, publication, ACE |
| `sase-core`      | `b6a149349a4e` | ref grammar/resolution, completion, prompt link rewriting    |
| `chezmoi`        | `2c74d5d00e5c` | Bryan's research hook and research xprompts                  |
| `sase--research` | `5d12521cc21a` | report conventions and prior ref research                    |

The review also inspected the `sase-ho` epic, its plan, all five phase histories, the
`sase-github` plugin as first-party plugin/CI precedent, and the published `agents`
sidecar layout. The most relevant current source seams are:

- `src/sase/artifact_ref_models.py`, `artifact_ref_operations.py`,
  `artifact_ref_context.py`, and `artifact_ref_prompt.py`;
- `src/sase/sidecar_ref_config.py` and `src/sase/xprompt/loader_refs.py`;
- `src/sase/llm_provider/preprocessing.py`;
- `src/sase/core/prompt_artifact_staging.py` and
  `src/sase/core/artifact_consumption.py`;
- `src/sase/agents_sync/prompt_archive/`;
- `src/sase/config/file_hooks.py` and `src/sase/file_hooks/`;
- `src/sase/ace/tui/artifact_tabs.py` and `src/sase/ace/tui/widgets/artifacts/`;
- `sase-core/crates/sase_core/src/artifact_ref/`, `editor/completion.rs`, and
  `prompt_artifact.rs`.

External design claims were checked against primary documentation. Pluggy formally
separates host hook specifications, plugin implementations, registration, and entry
point loading; it also validates implementation signatures and permits hookspecs to grow
through opt-in arguments
([Pluggy documentation](https://pluggy.readthedocs.io/en/stable/)). CommonMark defines
reference-link definitions independently of their use sites and uses the first matching
definition, details that matter for deterministic numeric-link allocation
([CommonMark specification](https://spec.commonmark.org/0.31.2/)). Git's object model is
explicitly content-addressed
([Pro Git: Git Objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)), and
GitHub documents that a file URL containing a commit ID is the durable way to link the
exact version viewed
([GitHub permanent-link documentation](https://docs.github.com/en/repositories/working-with-files/using-files/getting-permanent-links-to-files)).

## 1. What `sase-ho` actually built

The closed epic “Artifact reference xprompts” had five phases:

| Phase                      | Commit                  | What it introduced                                             | Disposition                                                |
| -------------------------- | ----------------------- | -------------------------------------------------------------- | ---------------------------------------------------------- |
| Core ref/filter contract   | `4071bf0` (`sase-core`) | grammar, typed payloads, resolution context, path filtering    | Keep the algorithms; replace the kind model and wire shape |
| Python registry/config     | `e0073528f`             | builtin/document registry and sidecar ref config               | Refactor around provider specs                             |
| Rendering through xprompts | `be6277b67`             | packaged templates, generated sidecar xprompts, late rendering | Remove                                                     |
| Unified completion         | `f164eee9a`             | one `@` completion pipeline across builtins/documents          | Keep the pipeline; change its inventory source             |
| Integration/docs           | `ce8ea893f`             | `#ref/*` catalog behavior, diagnostics, docs and tests         | Rewrite or remove                                          |

The eight currently supported ref kinds are the six hardcoded builtins `commit`, `chat`,
`bug`, `file`, `bead`, and `agent`, plus path-backed `plans` and `research`. The latter
two are generated from sidecar configuration. Every ref renderer is exposed as a
contextual `#ref/<kind>` xprompt.

That architecture made ref definitions look reusable, but at the cost of making them
pretend to be something they are not. A ref is a typed resolver, inventory, property
schema, prompt projection, publication target, and usage event. An xprompt is a prompt
fragment or workflow. Rendering is only one small part of the ref contract.

The mismatch is visible in the accommodations added by the epic:

- synthetic source schemes such as `sidecar_ref_config:` and `generated_sidecar_ref:`;
- special read-only/write-target handling for generated xprompts;
- ref-specific xprompt catalog metadata and namespace rules;
- two names for the same operation (`@research:x` and `#ref/research(x)`);
- a follow-up (`sase-hv`) because definition jumping could not naturally resolve the
  synthetic `#ref/<kind>` source.

The current late preprocessing sequence is otherwise sound: expand ordinary xprompts
early, establish launch context, scan and resolve refs late, stage referenced bytes,
render replacements, then process ordinary file mentions. The redesign should preserve
that sequencing while replacing the registry and renderer.

### Why a literal Git revert is the wrong rollback

`4071bf0` contains both reusable domain behavior and assumptions that no longer fit.
Later phases and subsequent commits have also built on its scanner, filters, completion
inventory, staging manifest, and prompt rewriter. Reverting the historical commits would
either remove capabilities the new design still needs or force conflict-heavy
reconstruction of code that has evolved since the epic landed.

The right rollback is semantic:

- delete `loader_refs.py`, packaged `xprompts/refs/*.md`, `#ref/*` catalog exposure,
  generated sidecar xprompt sources, and ref-specific xprompt placement logic;
- remove `xprompt` from sidecar ref policy and replace it with a provider descriptor;
- retain the scanner, literal-zone protection, path-glob implementation, context
  assembly patterns, completion plumbing, staging, hosted-link resolver, consumption
  tracking, and publication rewriter;
- migrate the old enums and grammars to the new builtin/provider contract rather than
  deleting the subsystem.

This also makes `sase-hv` obsolete as currently framed; an implementation project should
close or replace that follow-up deliberately rather than carrying a definition jump for
a namespace that no longer exists.

## 2. Design requirements and invariants

The proposed contract should be judged against these invariants.

### One semantic result everywhere

Prompt preprocessing, CLI validation, editor completion, the ACE inventory, and
publication must consume the same normalized provider descriptor and entry identity. It
is acceptable for Python to collect project/plugin/config data and pass it across a wire
boundary. It is not acceptable for the TUI, prompt renderer, and LSP to each reimplement
provider-specific rules.

### Resolution is pure with respect to publication

Resolving a ref may read an already materialized repository/store and may capture a
local file. It must not commit, push, mutate an artifact document, or run a file hook.
Publication and back-reference updates happen later and are independently retryable.

### Every use is captured at the time it matters

For every occurrence, SASE records the raw spelling, canonical identity, project
context, provider, properties relevant to that version, resolved file/repository, exact
revision or digest, and prompt span. Publication must never reconstruct this by looking
at the then-current repository HEAD.

### Configuration activates providers; installation does not

Installing `sase-research` makes its provider definitions available. A project opts in
to `@research` only by configuring a research sidecar with `ref.use: research` (or the
fully inline equivalent). Likewise, a file-hook provider runs only when a `file_hooks`
entry activates it.

### Provider declarations are data, not launch-time programs

Third-party packages are already trusted code when installed, but arbitrary callbacks on
completion and prompt launch create avoidable inconsistency and latency. A plugin hook
should return a small, immutable, JSON-shaped spec. The shared core validates and
executes the supported strategies.

### Historical archives remain readable

Removing `chat`, `bug`, `agent`, and the old artifact-ID meaning of `file` from the live
authoring registry must not break already published prompts or old manifest rows.
Readers need schema-versioned compatibility even after completion stops offering those
kinds.

## 3. The recommended ref contract

There are two related contracts, and keeping them separate prevents the plugin system
from swallowing the core model.

### 3.1 Runtime provider contract

The core-facing runtime contract should conceptually expose these operations:

```text
descriptor()            stable kind, labels, grammar, capabilities, schema version
inventory(context)      files or generic entries available for completion and ACE
resolve(argument, ctx)  one exact normalized entry or a structured diagnostic
prompt_text(resolved)   the text substituted into the launch prompt
properties(resolved)    normalized typed values for filters and detail rendering
publication_target(use) durable link target for the captured version
```

That does not require a dynamically dispatched Python method for every provider. The
Rust core can implement four strategy families:

1. builtin structured entries (`stitch`, `patch`, `bead`);
2. the special local-file provider (`file`);
3. declarative sidecar documents (`plan`, `research`, third-party kinds);
4. historical compatibility readers, unavailable for new completion.

The normalized return types should look approximately like this:

```text
ArtifactEntry
  stable_id             provider-scoped logical identity
  ref_kind              stitch | patch | bead | file | plan | research | ...
  canonical_argument
  display_label
  project_display_name
  repository
  repo_relative_path
  captured_revision     full VCS commit, when applicable
  captured_digest       full SHA-256, when bytes were observed
  logical_path          portable configured-root identity, for @file
  properties            typed map constrained by the provider schema
  origin                prompt_ref | agent_artifact | both

ResolvedArtifactRef
  raw_ref
  canonical_ref
  occurrence_span
  entry
  prompt_text
  publication_target
  captured_file
  diagnostics
```

`stable_id` is logical identity; `captured_revision`/`captured_digest` is version
identity. The distinction is what lets `Files` show one row for `~/bob/gtd.md` while
still exposing every captured version.

### 3.2 Plugin registration contract

Add two Pluggy hook specifications and corresponding entry-point groups:

```text
sase_artifact_ref_providers() -> iterable[ArtifactRefProviderSpec]
sase_file_hook_providers()    -> iterable[FileHookProviderSpec]
```

Suggested entry-point group names are `sase_artifact_refs` and `sase_file_hooks`,
parallel to SASE's existing behavior-specific plugin groups. The plugin inventory and
doctor output must recognize both groups.

Each hook is called while assembling the configuration registry, not once per ref or
file event. Returned specs are converted immediately to versioned wire values and
validated. The registry should enforce:

- a lowercase provider ID and ref kind;
- one schema version understood by the host;
- unique provider IDs across installed distributions;
- reserved ref kinds `stitch`, `patch`, `bead`, and `file`;
- exactly one effective provider for a ref kind within a project;
- deterministic ordering independent of Pluggy's registration/call order;
- a cache token containing distribution name/version and a spec digest;
- a hard, source-located configuration error when `use` names a missing provider.

Pluggy's evolving-signature support is useful for the hook itself, but the returned data
still needs its own explicit schema version. That makes incompatibility visible before
an agent launches.

### 3.3 Declarative sidecar provider spec

A sidecar provider needs to describe all three behaviors in the request—expansion,
inventory, and properties—plus stable identity and publication presentation. A concrete
version-one shape should be:

```yaml
schema_version: 1
provider: research
ref:
  kind: research
  display_name: Research
  description: Durable research reports and generated media
  argument:
    type: repo_path
    quoting: shell
  expansion:
    format: "the {checkout_path} file in the {sidecar_role} artifact repo"
  inventory:
    path_globs:
      - "**/*.md"
  identity:
    property: id
    fallback: repo_path
  properties:
    source: markdown_frontmatter
    fields:
      create_time: { type: datetime, label: Created }
      updated_time: { type: datetime, label: Updated }
      status: { type: string, label: Status }
      tags: { type: string_list, label: Tags }
  detail:
    title: title
    fields: [status, create_time, updated_time, tags]
    body: markdown
  publication:
    link: vcs_permalink
    referenced_by: markdown_table
```

This is deliberately not an xprompt or unrestricted Jinja template. `expansion.format`
is a small formatter whose valid placeholders are declared by the contract and validated
in Rust. It cannot run commands, recursively expand directives, or inspect the
filesystem. Builtins may compute prompt text directly, but return the same normalized
result.

The initial property types should remain modest: `string`, `enum`, `boolean`, `integer`,
`number`, `date`, `datetime`, and `string_list`. Unknown frontmatter can be preserved in
raw detail data, but only declared properties are filterable or promoted into generic UI
fields. That prevents every arbitrary YAML value from becoming a TUI query language.

Presentation hints should be hints, not custom widgets. A generic sidecar pane can use
`display_name`, a title property, ordered detail fields, and a Markdown body. Provider
packages must not ship Python TUI classes merely to show a new artifact type.

### 3.4 Inline configuration and `use`

The sidecar's `ref` mapping is the activation point. These two configurations should
normalize to the same provider spec:

```yaml
repos:
  sidecar:
    custom:
      research:
        ref:
          use: research
```

```yaml
repos:
  sidecar:
    custom:
      research:
        ref:
          kind: research
          display_name: Research
          description: Durable research reports and generated media
          argument: { type: repo_path, quoting: shell }
          expansion:
            format: "the {checkout_path} file in the {sidecar_role} artifact repo"
          inventory:
            path_globs: ["**/*.md"]
          identity: { property: id, fallback: repo_path }
          properties:
            source: markdown_frontmatter
            fields:
              create_time: { type: datetime, label: Created }
              updated_time: { type: datetime, label: Updated }
              status: { type: string, label: Status }
              tags: { type: string_list, label: Tags }
          detail:
            title: title
            fields: [status, create_time, updated_time, tags]
            body: markdown
          publication:
            link: vcs_permalink
            referenced_by: markdown_table
```

`use` means “start with this registered provider spec.” Additional fields are optional
overrides, deep-merged with field-specific rules. Scalar values replace; mapping values
merge; lists replace rather than concatenate. `schema_version`, provider identity, and
strategy type cannot be changed by an override. Diagnostics must show the provider's
distribution/version and the config layer that supplied each override.

This gives users a compact normal case without making providers all-or-nothing. It is
also the right precedent for file hooks:

```yaml
file_hooks:
  - use: research-highlights
    command: bob highlights create --include-id
```

The `research-highlights` provider supplies name, description, research-sidecar filters,
path globs, agent exclusions, operations, and timeout. `command` remains an ordinary
overridable field. The provider may either supply a portable default or mark the field
as a required user override. For `sase-research`, requiring the override is cleaner: the
matching policy is reusable, while the executable and local workflow remain the user's
choice. Bryan's chezmoi config should retain exactly the command shown above.

File-hook provider activation should use the same merge and diagnostic machinery as ref
providers, not a second hand-written interpretation of `use`.

## 4. Builtin and special refs

### 4.1 Shared authored grammar

All refs should support an unquoted argument and a quoted argument:

```text
@kind:bare-argument
@kind:"argument containing spaces"
```

The scanner must continue protecting fenced code, inline code, literal launch zones, and
existing Markdown links. Quoted strings need explicit escape rules. Completion should
insert quotes automatically when a Patch name or path requires them. This is necessary
for `@file` and avoids inventing a separate grammar for Patch names.

### 4.2 `@stitch`

Accepted forms:

```text
@stitch:<short_hash>
@stitch:<repo>@<short_hash>
```

The unqualified form resolves in the primary repository of the project identified by the
current prompt segment's VCS workflow. The qualified form resolves `<repo>` through the
SASE repo registry and therefore works for linked or sidecar repositories as well as the
primary repo. Hashes should accept 7–40 hexadecimal characters, resolve to a commit
object, and fail on ambiguity. The normalized identity always stores the full hash and
canonical repository identity.

A Stitch can exist as a proposal without a commit, but this ref's argument is explicitly
a VCS hash. It therefore denotes only commit-bearing stitches. Resolution should attach
the containing Patch/stitch number when SASE can find one, without requiring that
metadata for an ordinary repository commit.

Suggested synthesized properties are repository, full hash, subject, author, authored
time, Patch name, stitch number, and hosted URL. Prompt expansion should identify the
full commit and checkout, for example:

```text
stitch <full-sha> in <repo> (checkout: <path>)
```

Publication links to the VCS provider's commit URL.

### 4.3 `@patch`

`@patch:<name>` resolves the named Patch in the current project's active and archive
ProjectSpecs. It should not silently select a same-named Patch from another project. If
the prompt has no project context, SASE may accept a globally unique name, but an
ambiguous or absent context is a structured error with candidate projects.

Properties should include project, status, parent, PR URL/origin, mentors, comments
summary, stitch count, and latest stitch. Prompt expansion should be concise and
actionable rather than inlining an entire ProjectSpec, for example:

```text
the <name> Patch in project <project> (inspect with `sase patch show <name>`)
```

If the Patch has a PR, publication should link to it. Otherwise it should link to the
published Patch/agent page if one exists. The ref use remains valid even if no hosted
destination is available; tracking must not depend on linkability.

### 4.4 `@bead`

Accepted arguments are a short ID suffix or a full bead ID. A short ID is searched only
in the current project's bead store. A full ID resolves through the owning project
store. Prefix ambiguity is an error, never a first-match rule.

Properties should expose project, full ID, title, type, tier, status, priority, size,
parent, assignee/agent, and references. Prompt expansion should name the exact bead and
the command that renders it. Publication should use the hosted bead page when available.

### 4.5 `@file`

`@file` changes meaning in the authored grammar. It accepts an allowed local path, not
the current internal `file:(explicit|default):<digest>` artifact ID. The old shape
remains readable only in schema-versioned historical manifests and CLI compatibility
paths.

Recommended home configuration for Bryan is:

```yaml
artifact_refs:
  file:
    roots:
      - name: bob
        path: ~/bob
        path_globs:
          - "**/*.md"
```

The named root gives SASE a portable logical identity (`bob:<relative-path>`) while the
UI can display the friendly authored path `~/bob/<relative-path>`. Extension filtering
falls naturally out of `path_globs`, and multiple roots can express different
directory/file-type policies.

The resolver must:

1. expand `~` and parse the quoted argument;
2. resolve the physical path and verify containment in one configured root;
3. apply path globs to the root-relative path;
4. reject directories, devices, sockets, symlink escapes, and unreadable files;
5. enforce a configurable size ceiling and regular-file policy;
6. read/snapshot the bytes once, then hash the captured bytes—not a later read of the
   source path;
7. store logical path, authored spelling, physical path privately, size, MIME, capture
   time, and SHA-256 in the use manifest;
8. expand the prompt to the immutable captured copy, ensuring the agent reads the same
   bytes that publication later records.

Using `@file` is explicit publication intent, but the allowlist is still an important
exfiltration boundary. Git ignore rules are irrelevant and must not be treated as
permission. Published metadata should contain `~/bob/gtd.md` or `bob:gtd.md`, never
`/home/bryan/...`.

## 5. Project context must come from the prompt

The launch planner already resolves a VCS context per prompt segment. That result should
become an explicit `PromptRefContext` passed into late preprocessing:

```text
raw prompt segment
  -> identify #git/#gh VCS workflow and project
  -> expand ordinary xprompts/workflow steps
  -> assemble provider registry and PromptRefContext
  -> scan, resolve, capture, and expand refs
  -> launch agent
```

This matters for swarms and multi-segment prompts: different segments can target
different projects even if preprocessing happens in one process. Looking at `cwd` after
a workspace is entered happens to work for simple launches, but it loses the causal fact
the user specified and is fragile in home mode, validation, editor completion, and
multi-project workflows.

The context should contain the current project key/display name, primary repo, all
resolvable SASE repos, Patch store, bead store, enabled sidecar providers, file roots,
and VCS hosted-link capabilities. Unqualified `@stitch`, short `@bead`, and `@patch` all
consume this exact value. When a segment has no VCS project and a short form requires
one, the error should ask for an explicit qualified form or VCS workflow; it should not
search whichever workspace happens to be current.

## 6. Capture and usage tracking

The existing systems contain most of the required substrate but do not yet preserve the
right identity.

`prompt-artifacts.jsonl` currently records raw/expanded refs, kind, path, digest, MIME,
VCS repository/path, and locator. `artifact_consumption.jsonl` records a global
agent/project association. However, prompt-time selection deduplicates by raw ref and
does not retain every occurrence or a captured repository revision. Publication can
resolve a non-primary repository against its current HEAD, which can produce a link to
different bytes than the agent saw.

Add an immutable per-agent `ref-uses` manifest, with one row per occurrence:

```json
{
  "schema_version": 1,
  "use_id": "<stable occurrence id>",
  "agent": "research.example",
  "project": "sase",
  "provider": "research",
  "raw_ref": "@research:202608/example.md",
  "canonical_ref": "research:202608/example.md",
  "span": { "start": 120, "end": 156 },
  "entry_id": "research:202608/example.md",
  "logical_path": null,
  "captured_revision": "<full commit sha>",
  "captured_digest": "<sha256>",
  "origin": "prompt_ref",
  "properties": { "status": "research" },
  "captured_at": "2026-08-11T...Z"
}
```

The global consumption index can remain as a derived query accelerator and retention
input. It should not be the source of truth for publication or backrefs. Repeated refs
in one prompt produce repeated use rows but may share one captured object and one
backref-table row with an occurrence count.

For clean tracked files, capture both the full repository revision and blob/content
digest. For dirty or untracked sidecar files, do not manufacture a GitHub permalink to
HEAD. Snapshot the bytes to the agents object store and record the provenance as local;
publication can link the snapshot and surface that no sidecar permalink existed.

## 7. A true content-addressed file store

The current pool filename combines a 12-character digest prefix with the original
basename. Consequently, identical bytes referenced through different basenames can
occupy multiple locations. That is friendly for browsing but does not satisfy “each new
contents exactly once.”

Use the full SHA-256 as the only object identity:

```text
files/
└── objects/
    └── sha256/
        └── ab/
            └── abcdef...<64 hex chars>
```

Metadata and logical names belong in manifests, not the object path:

```text
agents/<agent>/ref-uses.json
agents/<agent>/artifacts.json
files/index/by-logical-path/...       optional generated index
```

An object is written atomically to a temporary file, its digest is verified, and it is
renamed into place only if absent. A collision at an existing digest path requires byte
verification. The same object can be referenced by many paths, agents, and origins.

This store should serve both `@file` captures and files published from
`sase artifact create`. The two operations create different use/provenance records, not
different byte stores. Existing artifact IDs can remain compatibility aliases to the new
object/version records during migration.

The lack of a filename extension is a presentation tradeoff, not a reason to duplicate
bytes. MIME type, original basename, and labels live in manifests. The UI can render
from MIME; downloads can synthesize a friendly name. A relative link from an agent's
prompt to the immutable digest object avoids a commit-hash circular dependency and works
both at current HEAD and when browsing the prompt at an older commit.

## 8. Publishing prompt links

### 8.1 Reference-style link algorithm

The current Rust `prompt_artifact_rewrite_links` seam is the correct owner, but it
currently writes inline Markdown links. Extend it to produce the requested form:

```markdown
Read [@research:202608/example.md][2] and [@file:~/bob/gtd.md][4].

[2]: https://github.com/.../blob/<captured-sha>/202608/example.md
[4]: ../../files/objects/sha256/ab/abcdef...
```

Allocation must use CommonMark structure, not a regular expression:

1. parse numeric reference definitions and numeric reference uses outside protected
   literal/code zones;
2. if an existing numeric definition already has the same normalized destination, reuse
   its label;
3. otherwise choose the lowest positive integer not used by a different link or
   definition;
4. rewrite every matching live ref occurrence, preserving visible text exactly;
5. append new definitions in numeric order at the bottom of the prompt;
6. return the linked use IDs and selected labels;
7. be idempotent when run again.

CommonMark uses the first matching definition, so emitting a duplicate numeric
definition and hoping the last one wins would be incorrect. Footnote labels such as
`[^1]` are a different namespace and should not consume plain `[1]` unless SASE's
Markdown renderer proves otherwise.

### 8.2 Link destinations

| Ref                         | Publication target                                                       |
| --------------------------- | ------------------------------------------------------------------------ |
| `@stitch`                   | hosted commit URL for the captured full SHA                              |
| `@patch`                    | PR URL when present; otherwise published Patch/agent page when available |
| `@bead`                     | hosted bead page/permalink                                               |
| clean sidecar ref           | `blob/<captured-full-SHA>/<repo-relative-path>`                          |
| dirty/untracked sidecar ref | agents-sidecar SHA-256 snapshot                                          |
| `@file`                     | relative link to agents-sidecar SHA-256 object                           |
| `sase artifact create` file | same object link when represented in a prompt/page                       |

The VCS provider should construct hosted URLs. The generic ref contract requests a
`vcs_permalink`; it should not hardcode GitHub URLs into the sidecar provider. GitHub's
implementation uses a commit ID as documented, while another provider can implement
equivalent semantics.

The captured revision must be written at resolution time. Looking up HEAD during agent
publication is too late and can silently link a newer artifact version.

## 9. `Referenced By` tables

The table is a projection of structured usage data, not the only copy of that data. Each
artifact sidecar should contain a small machine-readable index, keyed by stable artifact
ID and use ID, plus a managed block at the bottom of each referenced Markdown artifact:

```markdown
<!-- sase:referenced-by:start -->

## Referenced By

| Agent                                                               | Project | Reference                     | Published  | Uses |
| ------------------------------------------------------------------- | ------- | ----------------------------- | ---------- | ---: |
| [research.example](https://github.com/.../agents/research.example/) | sase    | `@research:202608/example.md` | 2026-08-11 |    2 |

<!-- sase:referenced-by:end -->
```

The agent link should be a permalink to the publication commit when available. The
stable agent page URL is a reasonable fallback. A richer row may include the associated
Patch/stitch, but the first version should keep the table useful and narrow.

Managed markers make replacement deterministic. A sidecar-local structured index (for
example `.sase/referenced-by/<artifact-id>.json`) supplies exact use IDs, destinations,
and timestamps so SASE never needs to reverse-engineer its state from a Markdown table.
The rendered rows are sorted and deduplicated by published agent/use identity.

Backref metadata must not redefine the semantic version of an artifact. Content digests
and change detection should ignore the managed block; otherwise every reference creates
a “new version” whose only change is that it was referenced, and subsequent refs form a
metadata feedback loop.

### Publication ordering and failure handling

There is no atomic transaction across the agents repo and one or more artifact repos.
Use an outbox:

```text
1. Resolve refs and capture immutable use records at launch.
2. Copy missing SHA-256 objects and publish agent page, prompt, and manifests.
3. Push the agents-sidecar commit and obtain its stable URL/permalink.
4. Enqueue one backref update per affected sidecar artifact.
5. Group by sidecar repo; update all managed blocks/indexes in one commit per repo.
6. Pull/rebase and retry on non-fast-forward conflicts.
7. Mark outbox rows complete only after the sidecar push succeeds.
```

Agent publication is the source of truth. A failed sidecar push must not roll back or
hide the agent; it remains a visible retryable diagnostic. Re-running the worker is
idempotent.

Backref commits are system projections and must not run ordinary user `file_hooks`. Add
an event cause/flag such as `system_projection: referenced_by`, and exclude it from
normal hooks by default. The current research hook happens to filter to `ADD`, while
backrefs modify existing files, but relying on that incidental filter would make the
generic feature unsafe.

Concurrent updates must lock per sidecar checkout, refresh the branch, replace only the
managed block, preserve all semantic content, and retry. If a file was moved, the
provider's stable ID/frontmatter identity should locate it. If it was deleted or its
semantic content changed, the table still describes the historical reference; SASE
should update the current logical artifact when identity is known and otherwise leave a
visible outbox error rather than attach the row to a guessed path.

## 10. Artifacts UI redesign

### 10.1 Dynamic top-level tabs

The current tab model is statically typed and ordered as a fixed tuple, while `Files`
contains fixed `Plans`, `Chats`, and `Other` sub-sub-tabs. Dynamic provider tabs require
a descriptor-driven model.

Keep the useful non-provider top-level tabs—currently Stitches, Beads, Bugs, and PRs—
unless a separate feature deliberately consolidates Bugs/PRs. Add the union of sidecar
ref kinds configured by any enabled project, then add the special Files pane. For a
typical installation:

```text
Stitches | Beads | Bugs | PRs | Plans | Research | Files
```

`Plans` appears only if at least one enabled project configures the plans sidecar ref.
`Research` appears only if at least one enabled project configures `ref.use: research`.
Installing a provider alone does not create a tab.

Use stable IDs such as `ref:plan` and `ref:research`, not display names. When the
enabled-project set changes, preserve selection by stable ID or fall back to the nearest
remaining tab. Numeric shortcuts must be generated from the runtime descriptor list and
limited to available keys; fixed Literal types and hardcoded action names cannot be the
source of truth.

A generic `ArtifactRefPane` should:

- lazily load the active provider's normalized inventory;
- group/project-filter entries using project display names;
- expose typed property filters from the provider schema;
- show provider-defined title/field ordering and a generic Markdown body;
- reuse the shared entry viewer, copy/open/ref actions, and stable navigation identity;
- cache inventory by provider-spec digest, project configuration, and repository HEAD.

Do not rescan every configured Markdown tree on every ACE refresh. A local disposable
index/cache keyed by repository revision is enough; this feature does not justify
rebuilding the previously removed global artifact graph.

### 10.2 The new Files pane

Delete the nested `Plans`, `Chats`, and `Other` tabs. `Plans` is replaced by the dynamic
provider pane; Chats and the generic “Other” split do not earn their UI cost.

`Files` becomes a direct aggregate of:

- local versions captured through `@file`; and
- explicit/default files registered by agents through `sase artifact create`.

Rows are grouped by logical file identity, not artifact record ID or digest. For an
allowed local file that is the configured root name plus relative path; for an agent
artifact it is the original source path when meaningful, with a stable artifact label
fallback. Physical `/home/...` paths never become public identity.

Each row shows one path and an origin badge:

- `Prompt ref`;
- `Agent artifact`;
- `Both`.

Selecting a row opens its newest version. The detail header shows `version i/n`, digest,
capture time, agent, project, origin, MIME type, and size. Next/previous-version actions
cycle all known content versions; repeated captures with an unchanged digest do not
create duplicate versions but do contribute usage/provenance records. The viewer should
reuse the existing MIME-aware artifact viewing machinery rather than build a second
renderer.

This exactly satisfies the `~/bob/gtd.md` case: one row, multiple content digests, every
capturing agent visible.

## 11. `plan` and the new `sase-research` plugin

### 11.1 Builtin plan provider

Register a builtin provider named `plan` in SASE itself. `sase init` should idempotently
write the explicit activation when it initializes a plans sidecar:

```yaml
repos:
  sidecar:
    builtin:
      plans:
        auto_clone: true
        ref:
          use: plan
```

The role is plural (`plans`), the authored ref is singular (`@plan`), and the display
tab is plural (`Plans`). These are separate fields; deriving all three from one string
is what produced the current `@plans` behavior.

Existing projects need a migration that adds the explicit `use` without changing sidecar
repository identity. During one compatibility release, `@plans:path` can parse as a
deprecated alias for `@plan:path`, but completion and new output should use only the
singular form.

### 11.2 Repository responsibilities

Create `sase-org/sase-research` as an installable first-party plugin repository. It
owns:

- the `research` artifact-ref provider;
- the `research-highlights` file-hook provider;
- packaged ordinary xprompts `#research`, `#research/image`, `#research/more`,
  `#research/prompt`, and `#research_swarm`;
- a deprecated `#old_research_swarm` alias for one release, or an explicit migration
  that removes it—no research-related xprompt should remain in chezmoi;
- provider documentation, schemas/examples, tests, and release tooling.

Those research workflows remain xprompts. The design only stops using xprompts to
_define refs_; it does not stop distributing ordinary research workflows through the
existing `sase_xprompts` plugin resource group.

The current SASE project config should eventually contain descriptions that remove the
naming ambiguity:

```yaml
repos:
  linked:
    - name: sase-research
      path: ../sase-research
      description: >-
        Installable plugin and workflow source for the research ref, research file hook,
        and #research xprompts. It contains provider code, not project research
        artifacts; those live in the sase--research sidecar.
      auto_clone: true
  sidecar:
    custom:
      research:
        description: >-
          Project artifact repository containing durable research reports and media.
          Provider code and #research workflows live in the linked sase-research repo.
        ref:
          use: research
```

A linked repo clone is not an installed Python distribution and does not make Pluggy
entry points visible. The setup must therefore include an explicit installation path:
published package installation for normal users and an editable install/cachebuster flow
for linked development. `sase doctor` and config validation should report a missing
`research` provider with the supplying config path and an actionable plugin installation
command. Silently treating a missing provider as an inline default would hide deployment
errors.

### 11.3 Research file-hook provider

The provider should contain the current shareable policy:

- description;
- `sidecars: [research]`;
- `path_globs: ["20*/**/*.md", "!20*/*/*__*.md"]`;
- `agent_name_globs: ["!research.*.cld", "!research.*.cdx"]`;
- `ops: [ADD]`;
- `timeout: 120s`.

Bryan's chezmoi becomes:

```yaml
file_hooks:
  - use: research-highlights
    command: bob highlights create --include-id
```

His model aliases, tribes, and other personal presentation choices remain in chezmoi;
they are not provider behavior.

### 11.4 Repository quality bar

Follow the first-party `sase-github` structure and raise the test bar for the novel
configuration surface:

- `src/sase_research/` package with typed provider specs and packaged xprompt resources;
- `pyproject.toml` entry points for artifact refs, file hooks, and xprompts;
- Ruff formatting/linting, strict mypy, pytest, and a meaningful coverage gate;
- supported-Python matrix aligned with SASE, source-checkout integration against SASE
  and `sase-core`, and dependency caching;
- build sdist/wheel, install the wheel in a clean environment, enumerate entry points,
  and verify every packaged xprompt resource;
- unit tests for the provider schema, command override, filter behavior, frontmatter
  extraction, and duplicate/missing-provider diagnostics;
- inline-versus-`use` normalization golden tests;
- end-to-end tests for research completion, resolution, expansion, captured revision,
  permalink generation, and `Referenced By` projection;
- workflow parsing tests for `#research_swarm` segment boundaries and wait/fork
  directives;
- release-please/versioning, trusted PyPI publication, changelog, and installation smoke
  tests;
- README sections for the repository distinction, installation, configuration, provider
  contracts, xprompt inventory, security, troubleshooting, development, and migration
  from chezmoi.

CI should test the wheel, not only the source tree. Resource/entry-point packaging is
the most likely failure mode for this repository.

## 12. Migration and compatibility

Treat this as a schema migration, not a flag day or a historical Git rollback.

### Live authoring changes

| Current                   | New                           | Compatibility recommendation                                                               |
| ------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------ |
| `@commit:<repo>@<sha>`    | `@stitch:[<repo>@]<sha>`      | accept old spelling with warning for one release                                           |
| `@bead:<id>`              | `@bead:<short-or-full-id>`    | extend in place                                                                            |
| `@file:<artifact-id>`     | `@file:<allowed-local-path>`  | do not ambiguously accept both in the new parser; historical schema reader handles old IDs |
| `@plans:<path>`           | `@plan:<path>`                | read-only/deprecated alias for one release                                                 |
| `@research:<path>`        | provider-backed same spelling | no authored migration                                                                      |
| `@chat`, `@bug`, `@agent` | no live ref kind              | preserve archives/manifest readers only                                                    |
| `#ref/<kind>`             | removed                       | diagnostic with replacement guidance during compatibility window                           |

If `@file:explicit:<digest>` and local paths share the same lexer without schema
context, old prompt text can be misinterpreted. Historical archive rendering should use
the manifest schema recorded with the run; new prompt validation should interpret
`@file` only as a path.

### Data migration

- Preserve existing prompt-artifact and consumption manifests as version 1 readers.
- Start writing version 2 records with occurrence, provider, revision, stable ID,
  logical path, and origin.
- Populate the new agents-sidecar object store lazily during publication/migration;
  verify full hashes before deduplicating old basename-based objects.
- Build Files-pane logical/version indexes from both old artifact indexes and new use
  manifests. Do not rewrite all historical agent pages merely to change link style.
- Add explicit `ref.use: plan` to projects with plans sidecars and provider-backed
  `ref.use: research` where installed.
- Move all research xprompt definitions out of chezmoi only after the installed plugin
  passes resource-discovery smoke tests.
- Do not generate historical sidecar backrefs speculatively. Begin with newly published
  agents; offer an explicit audited backfill later if desired.

## 13. Implementation sequence and verification gates

Although this report does not implement the feature, sequencing matters because the
publication and UI work depend on stable identities.

### Phase 0: freeze behavior and migration fixtures

Capture golden fixtures for all eight old refs, xprompt/literal-zone interactions,
completion, prompt staging, old manifest parsing, and prompt publication. Mark which
fixtures are historical compatibility versus desired new behavior.

### Phase 1: core provider and entry contract

Add the versioned provider/entry/use wire types, safe formatter, quoted argument
grammar, typed property schema, and generic sidecar strategy in `sase-core`. Adapt the
current filters and scanner. Remove no old behavior yet.

### Phase 2: plugin hooks and configuration normalization

Add both hooks, entry-point discovery, inline/`use` merging, schema/duplicate/missing
diagnostics, cache tokens, and `doctor` output. Add the builtin plan provider and
`sase init` activation.

### Phase 3: builtin refs and explicit prompt context

Implement `stitch`, `patch`, `bead`, and local-path `file`; pass per-segment VCS context
to late preprocessing; switch completion and validation to provider descriptors.

### Phase 4: occurrence manifests, CAS, and publication links

Write versioned per-agent ref uses, capture revisions atomically, introduce full-digest
objects, and extend the Rust rewriter to CommonMark numeric references. This phase must
land before backrefs so the latter has an authoritative source.

### Phase 5: dynamic Artifacts panes

Replace static sidecar pane definitions with provider descriptors, promote Plans, remove
Files sub-sub-tabs, and implement logical-path/version grouping with origin badges. Run
the dedicated ACE PNG visual snapshot suite for this phase.

### Phase 6: sidecar backref outbox

Add the structured sidecar index, managed Markdown section, post-publication outbox,
retry/conflict handling, and system-projection hook suppression.

### Phase 7: `sase-research` extraction

Create and publish the plugin, install it in the development workflow, activate it in
the SASE project, reduce Bryan's file-hook config to `use` plus `command`, move all
research xprompts, and verify clean-wheel discovery before deleting chezmoi sources.

### Phase 8: remove the xprompt ref adapter

Delete `#ref/*`, synthetic sources, packaged ref xprompts, old live kinds, and their
docs after the compatibility period. Keep schema readers and explicit diagnostics.

### Essential tests

The combined suite should include:

- parser/scanner tests for quotes, escapes, fragments, punctuation, literal zones, and
  Markdown links;
- ambiguous short hash, Patch name, bead suffix, missing-project, and cross-project
  resolution tests;
- provider-spec version, collision, missing installation, override, and inline parity
  tests;
- symlink escape, path traversal, special file, size, unreadable file, changed-during-
  capture, and duplicate-content `@file` tests;
- exact one-object-per-full-digest tests across names, agents, and origins;
- captured-revision tests where sidecar HEAD advances before publication;
- dirty/untracked sidecar fallback tests;
- numeric-link allocation with gaps, preexisting definitions, same-target reuse,
  duplicate refs, code fences, inline code, footnotes, and repeat-run idempotence;
- backref projection idempotence, multiple uses, renamed artifact, concurrent update,
  push failure/retry, and “does not run user file hooks” tests;
- dynamic tab union, enabled/disabled projects, provider removal, selection fallback,
  typed filters, lazy caching, Files origin grouping, and version navigation tests;
- old-manifest/archive compatibility tests;
- `sase-research` wheel/resource/entry-point and end-to-end tests.

## 14. Alternatives considered

### Keep refs as xprompts and add more frontmatter

This maximizes reuse of the xprompt loader but preserves the category mistake. It still
needs synthetic sources, makes direct `#ref/*` invocation bypass or complicate usage
tracking, and cannot make a prompt fragment supply a cross-frontend inventory and
property schema cleanly. Reject.

### Let plugins implement arbitrary Python resolvers/renderers

This is maximally flexible, but completion and ACE would execute third-party Python at
high frequency, native/editor consumers would not share semantics, and provider errors
could make prompt launch nondeterministic. It also puts shared backend behavior on the
wrong side of the Rust boundary. Use plugin code to return declarative specs once;
reject per-use callbacks.

### Define every provider only in YAML

Inline YAML is necessary for local providers, but YAML alone cannot package reusable
defaults, hook policies, documentation, xprompt resources, versions, and tests as one
installable unit. Support full inline configuration and plugin `use`; do not choose
between them.

### Build a new global artifact database/graph

It would simplify some queries but repeat a large subsystem SASE already built and
removed. Provider inventories, immutable per-agent manifests, a digest object store, and
disposable indexes are sufficient. Reject until measured scale proves otherwise.

### Store backrefs only in a central index or Git notes

That avoids modifying artifact Markdown but does not meet the requested portable
`Referenced By` table. A structured sidecar index plus a generated managed block gets
both machine integrity and visible Markdown. Reject table-only parsing and central-only
storage.

### Make publication synchronously atomic across repos

Git repositories do not offer a shared transaction. Trying to simulate one would make
agent publication fragile and still leave partial pushes under network failure. Use an
agents-first source of truth and durable idempotent outbox.

## 15. Risks and decisions to make before implementation

### Compatibility duration

Recommended: one release in which `@commit`, `@plans`, and `#ref/*` produce actionable
deprecation diagnostics; historical readers remain indefinitely. Do not keep old kinds
in completion during the warning release, because that encourages new use.

### Backref commit volume

Recommended: one commit per affected sidecar repo per agent publication, batching all of
that agent's refs. Add a short debounce only if publication bursts prove noisy.

### Dirty sidecar policy

Recommended: allow the prompt use, snapshot exact bytes to the agents CAS, warn that a
sidecar permalink/backref cannot yet be guaranteed, and never link HEAD falsely. A
strict project option can turn the warning into an error.

### Bugs and PRs in ACE

This ref redesign does not require removing the existing Bugs or PRs tabs. Keep them
until the separate external-artifact ingestion/consolidation work establishes that Beads
and Patches are complete supersets. Removing them here would mix unrelated data
migration into an already large feature.

### Provider naming

Recommended initial IDs are `plan`, `research`, and `research-highlights`, with
distribution provenance shown in diagnostics. Duplicate IDs are hard errors. If the
ecosystem later needs namespacing, add provider aliases/versioned migration rather than
making the authored ref kind verbose.

### Privacy and retention

The visibility and retention policy of the agents sidecar applies to captured `@file`
bytes. The UI and publication manifests must say so clearly. Configured root names and
relative paths are publishable; physical home paths are private runtime metadata.

## Recommended solution

Proceed with a surgical replacement of the xprompt adapter, not a wholesale revert of
`sase-ho`.

Define a versioned ref-provider contract in `sase-core` with normalized descriptors,
entries, resolutions, typed properties, publication targets, and occurrence records.
Implement `@stitch`, `@patch`, `@bead`, and the special local-path `@file` directly in
the core. Implement sidecar refs through a declarative sidecar strategy. Let installed
plugins register immutable provider and file-hook specs through two Pluggy hooks, and
let project/home configuration activate those specs with `use` plus validated overrides.

Pass the project resolved from each prompt segment's VCS xprompt into late ref
processing explicitly. At launch, capture every occurrence and its exact revision or
SHA-256 snapshot. At agents-sidecar publication, use one full-digest object path per
unique byte sequence and have the existing Rust prompt-rewrite seam emit idempotent
numeric reference links. Use captured commit SHAs for sidecar permalinks. After the
agents commit is pushed, process sidecar `Referenced By` updates through an idempotent
outbox whose managed Markdown table is rendered from structured sidecar data and whose
commits bypass ordinary user file hooks.

Make ACE consume the same provider descriptors: dynamically create one generic top-level
pane per configured sidecar ref, promote Plans, add Research when active, and replace
the current nested Files panes with one logical-path/version browser combining `@file`
captures and `sase artifact create` outputs with explicit origin badges.

Finally, create `sase-org/sase-research` as a rigorously tested installable plugin that
owns the `research` ref provider, `research-highlights` file-hook provider, and all
ordinary `#research` workflows. Configure it as a linked plugin/source repo with a
description that contrasts it with the `sase--research` artifact sidecar, explicitly
install it in the development/runtime environment, activate `ref.use: research`, and
leave only `use: research-highlights` plus Bryan's customizable
`command: bob highlights create --include-id` in chezmoi.
