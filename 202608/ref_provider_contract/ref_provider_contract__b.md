---
create_time: 2026-08-11
updated_time: 2026-08-11
status: research
---

# Replacing Ref XPrompts With an Artifact-Ref Contract

**Research question:** how should SASE retire the `#ref/<kind>` xprompt surface delivered
by epic `sase-ho` and replace it with a pluggable *ref contract* fulfilled by a small set
of builtin refs, a special `@file` ref, and artifact-repo (today: sidecar-repo)
configurations — including the ACE "Artifacts" tab redesign, `@file` tracking, prompt-time
ref→link conversion, and `Referenced By` back-links?

**Scope:** the `sase` repo at master `87cffa3b8`, `sase-core` at master (`sase-core-rs`
v0.21.0 installed), the `chezmoi` linked repo's global `sase.yml` and
`home/sase/xprompts/`, and the empty `sase-org/sase-research` repo (single commit,
0-byte README). Every file path and symbol below was read at that revision.

## Bottom line

**Four recommendations, in priority order.**

1. **Do not `git revert` `sase-ho`.** Its ~3,500 inserted lines are three separable
   layers, and only one of them is the thing you want gone. The *path-filter contract*
   (`filter_artifact_ref_path_payloads`, `path_globs`, the `filtered` resolution status)
   and the *document-role plumbing* (`ArtifactRefDocumentRoot`, `effective_sidecar_ref_policies`)
   are precisely the primitives the new ref contract needs. Reverting them means building
   them again. Do a **surgical retirement** of the xprompt surface (~1,200–1,600 LOC),
   keep the rest, and re-point it at the new contract. §3 lists the exact delete set.

2. **Make the provider contract declarative-first, with optional code.** Every existing
   sase plugin domain (`sase_vcs`, `sase_workspace`, `sase_llm`) is pure pluggy, and
   copying that shape here would force the research provider to ship Python for behavior
   that is 100% describable as data. Instead: `use: <provider>` resolves to a
   `RefProviderMetadata` **literal** (name, path globs, expansion template, property
   schema, sub-tab presentation, `Referenced By` columns, file-hook defaults), and the
   pluggy hooks are *optional overrides* that default to the declarative path-backed
   implementation. Result: `sase-research` is ~60 lines of metadata and no custom
   resolution code, while a genuinely exotic provider can still implement everything.
   §4 has the contract.

3. **Reuse three pieces of machinery that already do exactly what you asked for.**
   - `commit_footer.rs::allocate_numeric_id` / `reference_ids_in_body` already implements
     "first available positive integer not taken by a different link in that file," and
     already reuses one `[N]` per distinct destination. Lift it into a shared
     `markdown_link_refs` module rather than writing a second allocator.
   - `prompt_artifact.rs::rewrite_prompt_artifact_links` already rewrites live `@refs` in
     published prompts, idempotently, skipping fenced blocks, inline code, and existing
     Markdown links. It needs one change: emit reference-style `[…][N]` + a definition
     block instead of inline `[…](target)`.
   - `sdd/plan_links_refresh.py::refresh_plan_links` already reconciles projected
     provenance sections across a whole sidecar tree under a git write lock in one
     batched commit. Generalize it into the `Referenced By` writer instead of inventing a
     new cross-repo write path.

4. **Sequence the work as a 7-phase epic** where the ACE tab redesign lands *last* and the
   `sase-research` plugin repo lands *after* the provider hook. §9 gives the phase graph,
   §10 the risks. The single highest-risk item is not any of the new features — it is that
   `commit:` and `file:` reference strings are **persisted** in bead `refs:` lists, the
   consumption ledger, and prompt manifests, so `@stitch` and the new `@file` payload need
   permanent parse aliases, not a rename.

---

## 1. What exists today

### 1.1 Rust core (`sase-core`, ~3,000 LOC in `artifact_ref/`)

| File                             | LOC   | Owns                                                            |
| -------------------------------- | ----- | --------------------------------------------------------------- |
| `artifact_ref/mod.rs`            | 2,028 | parse / render / resolve / canonicalize, payload validation     |
| `artifact_ref/filter.rs`         | 324   | `ArtifactPathFilter`, `filter_artifact_ref_path_payloads`       |
| `artifact_ref/wire.rs`           | 285   | serde wires, 5 schema-version constants                         |
| `artifact_ref/list.rs`           | 257   | bead/Patch reference-list normalization + resolution            |
| `artifact_ref/scanner.rs`        | 96    | `@` candidate scanning with spans for the LSP                   |

Kinds are a closed enum, `ArtifactRefKindWire`: `Commit`, `Chat`, `Bug`, `File`, `Bead`,
`Agent`, `Document { role }`. Payloads: `Commit{repo,sha}`, `Chat{path}`,
`Bug{project,number}`, `File{source: explicit|default, digest}`, `Bead{id}`,
`Agent{name}`, `Document{path}`. `ArtifactRefContext` carries `document_roots` (each with
`path_globs`), `repositories`, `projects`, `bead_stores`, `agent_roots`, `agent_owner`.

Adjacent and directly reusable:

- `prompt_artifact.rs` (435 LOC) — manifest parse/select, `artifact_pool_filename(sha256,
  name)` (content-addressed, collision-disambiguated, length-bounded), and
  `rewrite_prompt_artifact_links`. Its tests already pin idempotency, literal-zone
  skipping, and "existing Markdown link is left alone."
- `commit_footer.rs` — `assign_reference_id` / `allocate_numeric_id` /
  `reference_ids_in_body` / `parse_reference_definition`: the exact numbering semantics
  requested for `[@ref:arg][N]`.
- `sections.rs` + the plan-header block — `PLAN | PROMPT | PARENT | BEAD | AGENTS |
  ARTIFACTS | COMMITS`, a Rust-owned, capped (50 entries + `omitted` count), idempotent
  projected-section renderer sitting at the *top* of SDD documents.

### 1.2 Python

| Area                                          | LOC     | Note                                                       |
| --------------------------------------------- | ------- | ---------------------------------------------------------- |
| `artifact_ref_*.py` (13 modules) + facade     | ~2,700  | context assembly, prompt pipeline, renderers, LSP, lists   |
| `xprompt/loader_refs.py`                      | 364     | **the `ref/<kind>` registry — the thing to retire**         |
| `sidecar_ref_config.py`                       | 184     | `repos.sidecar.*.<role>.ref` policy → `SidecarRefPolicy`   |
| `src/sase/xprompts/refs/*.md`                 | 6 files | builtin renderer bodies (4 are `@{{ resolved_file_path }}`) |
| `artifact_ref_renderers.py`                   | 84      | Jinja protection + renderer registry lookup                |
| `core/prompt_artifact_staging.py`             | ~300    | launch-time staging: sha256, pool, size cap, VCS provenance |
| `agents_sync/prompt_archive/*` (11 modules)   | —       | publishes prompt docs + artifact copies to `agents`         |
| `sdd/plan_links_refresh.py`                   | 417     | batched, locked write-back into the plans sidecar           |
| `config/file_hooks.py`                        | ~380    | `file_hooks` parse/merge/match; fails soft per entry        |
| `ace/tui/artifact_tabs.py` + `widgets/artifacts/` | 63 files | static `Literal` sub-tabs, bespoke panes per kind      |

Plugin infrastructure: pluggy projects `sase_vcs`, `sase_workspace`, `sase_llm` (provider
*classes*); resource groups `sase_xprompts`, `sase_config`, `sase_plugin_manifest`
(package *modules*, read as package data). `main/plugin_discovery.py` is the shared
loader, with `SASE_DISABLE_PLUGINS` / `SASE_DISABLE_PLUGIN_<GROUP>` kill switches.
`workspace_provider/_registry.py` demonstrates the metadata-caching pattern
(`@functools.cache get_all_workflow_metadata()` + an explicit
`reset_workflow_metadata_caches()` that clears every derived cache together).

### 1.3 What `sase-ho` actually shipped

Python: `e0073528f`, `be6277b67`, `f164eee9a`, `ce8ea893f`, `0a45feebc` —
**3,488 insertions / 132 deletions across 83 files**. Rust: `4071bf0` —
2,040 insertions across 24 files, released as `sase-core-rs` v0.21.0 and already
installed. `ARTIFACT_REF_WIRE_SCHEMA_VERSION` is at 4.

Its user-visible surface: `#ref/<kind>` xprompts equivalent to `@kind:payload`, renderer
files in `sase/refs/` requiring `ref: true` frontmatter, a **seven-level** precedence
table, `repos.sidecar.*.<role>.ref.{xprompt,filters.path_globs}` config, and `kind: ref`
catalog entries across `sase xprompt list/show`, ACE, and the LSP.

---

## 2. Why the xprompt framing was the wrong abstraction

Worth stating plainly, because it explains which parts to keep.

1. **A seven-level precedence table for a one-line sentence.** Five of the six builtin
   renderers are a single interpolation (`@{{ resolved_file_path }}{{ fragment_annotation }}`).
   The generated sidecar default is one sentence. The precedence machinery costs far more
   than the customization it buys.
2. **Templates could only change wording, never behavior.** The plan explicitly forbade
   templates from registering kinds, changing resolution, filtering, staging, consumption
   tracking, or completion. So the extension point sat exactly where extension was *least*
   valuable, and nowhere near where you actually want it (properties, inventory, link
   targets, back-links).
3. **Filters already refused to follow renderer precedence.** The design says "the
   effective sidecar configuration always owns the path policy for its role, even when a
   file overrides its wording." That is the design admitting two different owners for one
   ref — which is exactly what a single provider contract fixes.
4. **It created synthetic xprompt sources that the rest of the system had to special-case.**
   `sidecar_ref_config:` and `generated_sidecar_ref:` are fake source paths; `0a45feebc`
   exists only because the ACE xprompt browser tried to open one for editing.
5. **It leaked into unrelated namespaces.** `reject_misplaced_ref()` now runs on every
   ordinary xprompt load to police the reserved `ref/` namespace.

None of these criticisms apply to the *filter contract* or the *document-root plumbing*,
which is why those should survive.

---

## 3. Retirement plan (not a revert)

### 3.1 Delete

| Target                                                                   | Approx. LOC |
| ------------------------------------------------------------------------ | ----------- |
| `src/sase/xprompts/refs/*.md` (6 files)                                  | ~40         |
| `src/sase/xprompt/loader_refs.py`                                        | 364         |
| `src/sase/artifact_ref_renderers.py` (keep the Jinja-protection helper)  | ~60 of 84   |
| `ref` / `ref_kind` / `ref_sidecar_role` fields on `XPrompt` + catalog wires | ~120     |
| `#ref/` rewriting in `artifact_ref_prompt_parsing.py`                    | ~80         |
| `sase/refs/` sources in `content_layout.py` + `resolve_ref_file_sources` | ~100        |
| `#ref/` completion in `ace/tui/prompt_catalog.py` + `_startup_prompt_catalog.py` | ~90 |
| `xprompt_browser_helpers.py` synthetic-source special cases (`0a45feebc`) | 22         |
| Rust: contextual-ref catalog entries in `xprompt_catalog.rs` / `sase_xprompt_lsp` | ~150 |
| `docs/xprompt.md#artifact-reference-xprompts`, `docs/content_layout.md` rows, `docs/plugins.md` refs row | ~120 |
| Associated tests (`test_xprompt_ref_sources.py`, `test_artifact_ref_xprompt_integration.py`, parts of others) | ~400 |

### 3.2 Keep, and re-point at the new contract

- `artifact_ref/filter.rs` + `filter_artifact_ref_path_payloads` +
  `ARTIFACT_REF_PATH_FILTER_WIRE_SCHEMA_VERSION` — this *is* the ref contract's filter half.
  Its documented semantics (normalized repo-relative POSIX, case-sensitive, `**/` matches
  zero dirs, OR-ed positives, `!` vetoes, negative-only starts allow-all) become the one
  filter vocabulary for sidecar path globs, `@file` allow-lists, and `file_hooks`.
- The `filtered` resolution status and its non-leaking diagnostic.
- `ArtifactRefDocumentRoot { kind, path, path_globs }` and `ArtifactRefContext`.
- `sidecar_ref_config.py`'s `effective_sidecar_ref_policies` shape — replace the `xprompt`
  field with the provider-resolved metadata, keep the role merge/disable logic.
- `sase_core_rs` v0.21.0 itself. Reverting the Rust would mean a wire-schema *downgrade*
  against an already-released, already-installed binding; `tools/validate_sase_core_rs`
  gates this.

### 3.3 Sequencing note

Do the deletion as **its own phase**, before the provider hook lands, with the builtin
refs temporarily falling back to the pre-`sase-ho` hardcoded rendering path (still present
in `artifact_ref_prompt_rendering.py`). This keeps the delete diff reviewable on its own
and keeps `master` shippable between phases.

---

## 4. The ref contract

### 4.1 Shape: declarative metadata + optional hooks

```python
@dataclass(frozen=True)
class RefProviderMetadata:
    """Everything a ref type declares. A provider that ships only this works."""

    name: str                       # provider id, e.g. "research"
    ref_name: str                   # default @<ref>, e.g. "research"
    display_name: str               # "Research"
    description: str

    backing: Literal["path", "entry"] = "path"

    # --- (a) what text replaces @<ref>:<arg> ---
    expand: str = "the {{ path }} file in the {{ repo }} artifact repo"

    # --- (b) which entries are tracked / supported ---
    path_globs: tuple[str, ...] = ("**/*.md",)

    # --- (c) which properties exist and how they parse ---
    properties: tuple[RefProperty, ...] = ()   # source: frontmatter | derived
    property_source: Literal["frontmatter", "provider"] = "frontmatter"

    # --- presentation + linking ---
    subtab: RefSubTabSpec | None = None        # label, accent, sort, group-by
    link: RefLinkSpec = RefLinkSpec.PERMALINK  # blob permalink at the pinned revision
    referenced_by: tuple[str, ...] = ("Agent", "Project", "Reference", "Date", "Prompt")

    # --- optional companion ---
    file_hook: FileHookDefaults | None = None
```

```python
@dataclass(frozen=True)
class RefProperty:
    key: str                                   # frontmatter key
    type: Literal["word", "line", "text", "int", "bool", "date", "list"]
    label: str | None = None
    filterable: bool = True                    # exposes a filter token in ACE
    facet: bool = False                        # groupable in the sub-tab
```

The pluggy hookspec then exists purely to *override* defaults:

```python
hookspec = pluggy.HookspecMarker("sase_artifact")
hookimpl = pluggy.HookimplMarker("sase_artifact")

class ArtifactHookSpec:
    @hookspec
    def ref_provider_metadata(self) -> RefProviderMetadata | None: ...

    @hookspec(firstresult=True)
    def ref_expand(self, provider: str, request: RefExpandRequest) -> str | None: ...

    @hookspec(firstresult=True)
    def ref_inventory(self, provider: str, request: RefInventoryRequest) -> RefInventory | None: ...

    @hookspec(firstresult=True)
    def ref_properties(self, provider: str, entry: RefEntry) -> Mapping[str, object] | None: ...

    @hookspec(firstresult=True)
    def ref_link_target(self, provider: str, entry: RefEntry, revision: str | None) -> str | None: ...

    @hookspec(firstresult=True)
    def ref_backlink_row(self, provider: str, entry: RefEntry, usage: RefUsage) -> Mapping[str, str] | None: ...

    @hookspec
    def file_hook_provider_metadata(self) -> FileHookProviderMetadata | None: ...
```

`ref_expand` returning `None` (or being absent) → render `metadata.expand` with the
declarative context. `ref_inventory` absent → walk the artifact repo's document roots
through `filter_artifact_ref_path_payloads(path_globs)`. `ref_properties` absent → parse
YAML frontmatter per `metadata.properties`. This is what makes the research provider
codeless.

**Why one pluggy project (`sase_artifact`) rather than two:** file-hook providers and ref
providers ship together in practice (`sase-research` needs both), the discovery/caching
code is identical, and sase already tolerates one project exposing several unrelated hook
families (`sase_workspace` covers ref resolution, submit, SDD materialization, and repo
completion). Name it for the domain — artifact repos — which also anticipates the
sidecar→artifact-repo rename.

### 4.2 The four behaviors you listed, mapped

| Your requirement                        | Contract member                                  | Default when unset                                     |
| ---------------------------------------- | ------------------------------------------------ | ------------------------------------------------------ |
| What text replaces `@<ref>:<arg>`?       | `expand` / `ref_expand`                          | `the {{ path }} file in the {{ repo }} artifact repo`  |
| Which entries are tracked & supported?   | `path_globs` / `ref_inventory`                   | `**/*.md` under the repo's document roots              |
| Which properties, parsed how?            | `properties` / `ref_properties`                  | frontmatter keys, typed, all filterable                |
| (implied) link destination & back-link   | `link`, `referenced_by` / `ref_link_target`, `ref_backlink_row` | GitHub blob permalink at the pinned revision |

For **entry-backed** builtins (`stitch`, `patch`, `bead`) `property_source` is
`"provider"` and the builtin implementation supplies properties from the domain model —
stitch: repo/author/date/subject/Patch; patch: status/PR/parent/stitch count; bead:
type/tier/status/assignee/size/epic. This is what makes `Artifacts` filtering uniform
across path- and entry-backed refs without frontmatter existing everywhere.

### 4.3 Config: `use:` vs inline

```yaml
# Provider-backed (one field is enough)
repos:
  sidecar:
    custom:
      research:
        use: sase_research

# Provider-backed with overrides (field-by-field, provider supplies the rest)
      research:
        use: sase_research
        ref:
          path_globs: ["20*/**/*.md", "!20*/*/*__*.md"]

# Fully inline, no plugin installed
      notes:
        ref:
          name: note
          expand: "the {{ path }} note"
          path_globs: ["**/*.md"]
          properties:
            - { key: status, type: word }
            - { key: created, type: date }
```

Merge rule: `use:` supplies a `RefProviderMetadata` default; sibling `ref:` keys override
field-by-field (not wholesale replacement). This matches
`llm_provider.model_aliases.builtin/custom` and the existing `default_config.yml` layering,
so it will read as familiar.

Schema deltas in `src/sase/config/sase.schema.json`:

- `sidecarRepo.properties.use` — `{"type": "string"}`, the provider name.
- `sidecarRef` — drop `xprompt`; add `name`, `expand`, `properties`, `subtab`,
  `referenced_by`; keep `filters.path_globs` (consider promoting it to a bare
  `path_globs` for symmetry with `fileHookFilters`, but a rename costs a deprecation
  path — recommend keeping `filters.path_globs`).
- `fileHook.properties.use` — `{"type": "string"}`; relax `required: ["name","command"]`
  to `required: ["command"]` when `use` is present (an `anyOf`), since the provider
  supplies `name`, `description`, `filters`, and `timeout`.

**Graceful degradation is mandatory.** `config/file_hooks.py` already fails soft per entry
with a `logger.warning` and skips. Do the same for an unresolvable `use:` — a project whose
`sase.yml` names an uninstalled provider must still launch agents, with the ref reported
as unknown-kind and a `sase doctor` finding. Never raise on the launch path.

### 4.4 Builtin refs

| Ref       | Payload                                | Status                                                              |
| --------- | -------------------------------------- | ------------------------------------------------------------------- |
| `@stitch` | `<short_hash>` or `<repo>@<short_hash>` | renames `commit`; adds the bare-hash form resolved against the project in context |
| `@patch`  | `<patch_name>`                          | **new** — needs a `Patch` kind + payload in the Rust wire            |
| `@bead`   | `<short_id>` or `<full_bead_id>`        | exists as `Bead{id}`; needs short-id resolution + `ambiguous` status |
| `@file`   | `<path>` or `<source>:<digest>`         | see §5                                                               |

Three notes on grammar:

- **`@stitch:<repo>@<sha>` is already how `commit` works** (`format!("{repo}@{sha}")`), and
  `scanner.rs` splits only on the *first* `:`, so a payload-internal `@` is already
  tolerated. Adding a bare-hash form means `parse_payload` must disambiguate on the
  presence of `@`, and `ArtifactRefContext` must expose the in-context primary repo (it
  already carries `repositories` with `kind` and the resolved project filter).
- **`@patch:<name>` resolves to no single file.** Patches are sections in ProjectSpec
  `<key>.sase` / `<key>-archive.sase`. `sase-core` gained a Patch/stitch wire in `8344869`
  (`wire.rs` +434, `parser.rs` +113, `sections.rs` +33), so the model exists. Recommend:
  expansion names the Patch plus status; `ref_link_target` returns the PR URL when `PR:`
  is set, and `None` otherwise (render an unlinked code span rather than inventing a
  destination). `@patch` is entry-backed, so it never participates in path filtering.
- **`@bead:<short_id>` needs an ordering rule.** `ArtifactRefContext.bead_stores` is a
  tuple across projects; short-id lookup must try the in-context project first and return
  the existing `ambiguous` status on a cross-project collision, with the fully-qualified
  candidates in the diagnostic.

**Open decision — `@chat`, `@bug`, `@agent`.** Your list names only `stitch`, `patch`,
`bead` (+ `file`). Taken literally, three kinds disappear. Recommend **keeping them as
builtin providers** rather than deleting them, for three reasons: (a) they satisfy the new
contract with no special-casing — `agent` and `chat` are path-backed, `bug` is
entry-backed; (b) `commit:`/`chat:`/`bug:`/`agent:` strings are persisted in bead `refs:`
lists (`sase bead ref add`), in `consumption.jsonl`, and in prompt manifests, so removal is
a data migration, not a code deletion; (c) `@agent` is what makes agent-to-agent
cross-links work in the `agents` sidecar. The count of builtins is not the design
constraint — the contract is. If you do want them gone, that is a separate,
migration-shaped decision and should be its own phase.

### 4.5 Builtin `plans` provider + `sase init`

Ship `sase_plans` as an in-tree provider registered on the `sase_artifact` group by the
`sase` package itself, so `use:` has no privileged builtin path. `sase init` then writes:

```yaml
repos:
  sidecar:
    builtin:
      plans:
        auto_clone: true
        use: sase_plans
```

`src/sase/main/_repo_init_config.py` already does surgical `ruamel` edits of the project
`sase/sase.yml` (`make_yaml()` / `dump_yaml()` at lines 117–216), so this is an addition to
an existing writer, not a new one. Make it idempotent (skip when `use:` is already present,
never clobber a user's inline `ref:`).

---

## 5. The special `@file` ref

### 5.1 Grammar: one kind, two payload shapes

Keep a single `@file:` kind:

- `@file:~/bob/gtd.md` — an allow-listed local path, hashed and staged at launch.
- `@file:explicit:<digest>` / `@file:default:<digest>` — an already-indexed artifact file,
  which is what `sase artifact create` prints today (`ref: file:<id>`).

This is not a compromise: `scanner.rs::trim_candidate_end` **already** special-cases
`kind == "file"` with two colons, so the grammar was built anticipating a two-segment file
payload. Disambiguation is unambiguous — a payload whose first segment is `explicit` or
`default` is a digest reference, anything else is a path. Splitting into `@file` + a new
`@artifact` kind would instead break every persisted `file:` string and every
`sase artifact create` output line.

### 5.2 Allow-list config

```yaml
refs:
  file:
    sources:
      - root: ~/bob
        path_globs: ["**/*.md"]
```

Put it in `~/.config/sase/sase.yml` (home layer) for your case, since `~/bob` is
machine-global; project layers may append. Use the *same* `path_globs` vocabulary as
sidecar refs and `file_hooks` (`wcmatch` with `DOTGLOB | GLOBSTAR | NEGATE | NEGATEALL`) —
one filter language across the whole system is worth more than per-feature ergonomics.
`root` is expanded and resolved; globs are matched against the root-relative POSIX path;
a path outside every root is `filtered`, not `missing` (the status already exists and
already refuses to leak absolute local paths into prompt text).

### 5.3 Staging and versioning

`core/prompt_artifact_staging.py` already does the hard parts: sha256, mime type, size cap
(`capture_file_exceeds_size_limit`), content-addressed pool via
`artifact_pool_filename(sha256, name)`, clean-VCS-provenance short-circuit, and a
`fcntl`-locked JSONL manifest. `@file:<path>` slots straight into it — the only change is
that the record's `raw_ref` is `@file:~/bob/gtd.md` rather than a digest form.

**Gap to close:** prompt-staged files land in the *workspace* `.sase/artifacts` pool +
manifest, not the durable artifact index that ACE's Files pane queries
(`query_artifact_files`). For the Files sub-tab to show every version of `~/bob/gtd.md`
across agents, promote `@file` versions into the durable index (or a sibling `ref_files`
index) **at publication time**, keyed by `(logical_path, sha256)`. Doing it at publication
rather than at launch keeps the launch path cheap and means only published runs contribute
versions — which is also the right semantics.

### 5.4 Publication into the `agents` sidecar

Store under `files/<sha256[:2]>/<pool_filename>` using the *existing*
`artifact_pool_filename`, so identical content across agents and across months lands in
exactly one location. Git deduplicates identical blobs anyway; the sharded prefix keeps
directory sizes sane. Write-if-absent (compare sha256, never overwrite).

---

## 6. Ref → link conversion in published prompts

### 6.1 What changes

`render_prompt_document` → `rewrite_prompt_artifact_links` currently emits **inline**
links: `[@~/diagram.png](artifact.png)`. You want **reference-style**:

```markdown
Please read [@file:~/bob/gtd.md][1] and [@research:202608/foo/foo.md][2].

[1]: files/ab/ab12…-gtd.md
[2]: https://github.com/sase-org/sase--research/blob/<sha>/202608/foo/foo.md
```

Two changes, both small because the primitives exist:

1. **Numbering.** Lift `allocate_numeric_id` / `reference_ids_in_body` /
   `parse_reference_definition` out of `commit_footer.rs` into a shared
   `markdown_link_refs.rs`, then call it from both. It already scans the document for
   taken `[n]:` definitions, allocates the first free positive integer, and — importantly —
   *reuses* one id per distinct destination, which is what you want when the same file is
   referenced twice.
2. **Emission.** `rewrite_prompt_artifact_links` swaps its inline formatter for
   `[…][N]` + an appended definition block. Its existing guarantees carry over unchanged:
   idempotent on a second pass, skips fenced blocks and inline code, leaves pre-existing
   Markdown links alone, and reports `linked_records` so the `ARTIFACTS` header section
   stays in sync.

### 6.2 Link destinations by ref kind

| Kind                | Destination                                                                 |
| ------------------- | --------------------------------------------------------------------------- |
| `@file:<path>`      | repo-relative `files/<shard>/<pool_filename>` in the `agents` sidecar        |
| `@file:<src>:<dig>` | same (the artifact is copied in by the existing prepare step)                |
| artifact-repo refs  | GitHub blob **permalink at the pinned revision**, via `HostedLinkResolver`   |
| `@stitch`           | commit URL for the resolved repo                                            |
| `@patch`            | PR URL when present, else unlinked                                          |
| `@bead`             | bead page in the `beads` sidecar (`bead_links.py` already resolves these)   |
| `@agent`            | agent page in the `agents` sidecar (`agent_lanes.lane_page_path`)           |

The pinned-revision permalink matters: a `main`-branch link rots as soon as the artifact is
edited, and the whole point of the citation is to name what the agent actually read.
`prompt_archive/preparation.py` already threads `primary_revision` and a
`HostedLinkResolver` into `_ArtifactTargetResolver`, so the plumbing is present.

---

## 7. `Referenced By` back-links

### 7.1 Design

Render at the **bottom** of an artifact file, only when citations exist:

```markdown
## Referenced By

| Agent                      | Project | Reference                     | Date       | Prompt              |
| -------------------------- | ------- | ----------------------------- | ---------- | ------------------- |
| [bbugyi200.athena.xy][7]   | sase    | `@research:202608/foo/foo.md` | 2026-08-11 | [refs_redesign][8]  |
```

Columns come from `RefProviderMetadata.referenced_by`, rows from `ref_backlink_row` (with a
sensible default). Reuse the plan-header block's proven properties: Rust-owned rendering,
deterministic sort, a hard cap (`MAX_RENDERED_PLAN_HEADER_ENTRIES` is 50) with an
`omitted: N` line, and full idempotency so re-running produces a byte-identical file.
Implement it as a new footer-block module rather than extending `plan_header_block`, since
that one is anchored to the top of the document.

### 7.2 Write path

Generalize `sdd/plan_links_refresh.py`. It already: resolves the sidecar root from the
`SddStore`, takes `store_git_write_lock(..., mutates_worktree=True)`, parses + re-renders
each document, and writes one batched commit with a structured report. The generalization
is "operate on any artifact-repo role, using the provider's row builder" — most of the
file is reusable as-is.

Trigger it from agent publication, but **route it through `agents_sync/publication_outbox*`**
(8 modules, already handling deferred/quarantined publication) rather than calling it
inline. Rationale: a locked, offline, or contended research sidecar must never fail the
agents-sidecar publication that is the actual deliverable. Same reason `bead_links.py`
wraps everything in a best-effort `except Exception` returning a diagnostic string.

Fix a **lock order** — artifact repos first, `agents` last — so an agent publication that
writes back to two sidecars can never deadlock against a concurrent
`sase plan links --write`.

### 7.3 Interaction with the existing `AGENTS` section

Plans already carry an `AGENTS` header section (agents that *worked on* the plan).
`Referenced By` is a different relation (agents that *cited* the document). Keep both;
document the distinction; do not let a `@plan:` citation silently add an `AGENTS` entry.

---

## 8. ACE "Artifacts" tab

### 8.1 What has to become dynamic

Today: `ArtifactsSubTab = Literal["prs","stitches","bugs","beads","files"]`,
`FilesSubTab = Literal["plans","chats","other"]`, static `PanelTab` tuples, `show_numbers=True`,
and reactive attributes typed with those `Literal`s in `app.py` and `ace/testing/ace_page.py`.

Target: `["stitches","beads","bugs","prs", *provider_tabs, "files"]`, where `provider_tabs`
is the union of document-ref providers configured by **enabled** projects, in deterministic
config order. That forces:

- `ArtifactsSubTab` → `str` plus a runtime registry (`artifact_tabs.py` grows a
  `resolve_artifacts_subtabs()` cached on the config token, mirroring
  `get_all_workflow_metadata()` + `reset_workflow_metadata_caches()`).
- Number keys: keep `1..N` stable for the fixed tabs and assign provider tabs the numbers
  after them; make `[` / `]` (`cycle_artifacts_subtab`) the primary affordance and say so
  in the help modal. Unstable number keys are a worse regression than no number keys.
- `default_config.yml` keymaps: `cycle_files_subtab` / `_reverse` (`(` and `)`) become free
  once the nested Files view is gone — either retire them or repurpose them for
  version-toggling on the new Files tab (see §8.3), which is the better use.
- Persisted selection: `current_files_subtab` disappears; `current_artifacts_subtab` may
  now hold a value whose provider was uninstalled — fall back to `DEFAULT_ARTIFACTS_SUBTAB`
  rather than erroring.

### 8.2 Generalize the Plans pane

`widgets/artifacts/` has ~12 `plans_*` modules, ~9 `chats_*`, ~9 `files_*` — three parallel
implementations of list + filter-bar + filter-session + detail + rendering + navigation.
Collapse `plans_*` into `ArtifactsDocumentsPane(provider)` driven by
`RefProviderMetadata.properties` (filter tokens) and `.subtab` (label, accent, grouping);
`plans` becomes its first instance and `research` costs zero new pane code. Delete
`chats_*` and the old `files_*` per your instruction. Net effect is likely a *reduction* in
ACE LOC despite adding dynamic tabs.

The existing filter machinery generalizes cleanly: `plans_filtering.py`'s
`_PlanFilterRecord` is already a generic (project, status labels, tier labels, kind labels,
timestamp, haystack) record — that becomes `(project, {property: labels}, timestamp,
haystack)` driven by the declared property schema.

### 8.3 The new Files sub-tab

- **One row per unique logical file.** Group key: the source path for `@file:<path>` rows,
  the artifact id for `sase artifact create` rows.
- **Version toggling on the selected row.** Versions are `(sha256, first_seen_at,
  agents[])` tuples from the promoted index (§5.3). `(` / `)` are the natural bindings.
- **Origin must be visible.** Three origins: `ref` (cited in a prompt), `created`
  (`sase artifact create`), `capture` (automatic staging). The index already carries an
  `explicit` boolean (`FilesSnapshot.explicit_count`); it needs a third value, so widen it
  to an enum rather than adding a parallel flag. Render it as a distinct badge/column and
  make it a filter facet.

### 8.4 Performance

`sase/memory/tui_perf.md` is the governing memory here (read it before implementing). Two
specific hazards: N document sidecars means N tree scans, and dynamic tabs tempt eager
construction. Mitigations that match existing patterns: keep `ContentSwitcher` +
`activate()`-on-visible laziness (`ArtifactsView.on_mount` already only activates when
Artifacts is the current tab), share one off-thread loader keyed by provider, and cache
provider metadata on `current_config_token()`.

Expect `tests/ace/tui/visual/snapshots/png/` goldens to need `--sase-update-visual-snapshots`.

---

## 9. Recommended phase plan

```
1. core-ref-contract (sase-core, large)
   Stitch kind + `commit` parse alias; Patch kind/payload; bead short-id resolution;
   @file path payload; markdown_link_refs extraction; Referenced-By footer block.
   Keep artifact_ref/filter.rs untouched.
        │
2. retire-ref-xprompts (large)  ──── independent of 1; land either order
   Delete §3.1. Builtins fall back to the pre-sase-ho rendering path.
        │
        ├──► 3. ref-provider-contract (large)
        │       sase_artifact pluggy project; RefProviderMetadata; use: + inline merge;
        │       schema; builtin sase_plans provider; sase init writes use:; doctor checks.
        │            │
        │            ├──► 7. sase-research plugin repo (medium)
        │            │       new repo, CI, tests, docs; move #research* xprompts;
        │            │       link it here; chezmoi switches to use: + keeps command:.
        │            │
        │            └──► 6. ace-artifacts-tabs (large)  ◄── also needs 4
        │
        ├──► 4. file-refs (large)
        │       allow-list config; staging; version promotion; files/ publication.
        │            │
        └────────────┴──► 5. publication-linking (medium)
                            [@ref][N] reference-style links; Referenced By write-back
                            through the publication outbox.
```

Phase 2 is deliberately separate from 3 so the deletion is reviewable alone. Phase 6 is
last because it is the only phase whose blast radius includes visual snapshots and
keymaps.

---

## 10. Risks

| Risk                                                                                                    | Severity | Mitigation                                                                                       |
| ------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------ |
| **Persisted `commit:` / `file:` strings** in bead `refs:`, `consumption.jsonl`, prompt manifests, Patch files | **High** | Permanent parse aliases canonicalizing to `stitch:`; never a hard rename. Add a `sase artifact doctor` normalization report. |
| Wire schema churn (`ARTIFACT_REF_WIRE_SCHEMA_VERSION` 4→5) + `sase-core-rs` release/roll                | High     | One Rust phase, one release; `tools/validate_sase_core_rs` already gates the binding.            |
| Uninstalled provider named by `use:`                                                                     | High     | Fail soft with a warning + `sase doctor` finding, exactly like `config/file_hooks.py`. Never raise on launch. |
| Cross-sidecar write-back deadlock / publication failure                                                  | Medium   | Fixed lock order (artifact repos → agents); route back-links through `publication_outbox`.       |
| ACE regression surface (keymaps, snapshots, persisted subtab)                                            | Medium   | Land last; keep number keys stable for fixed tabs; fall back on unknown persisted subtab.        |
| ACE latency from N artifact repos                                                                        | Medium   | Lazy activation, shared off-thread loader, config-token-cached metadata. Read `tui_perf.md`.     |
| `@file` allow-list widening the capture surface / leaking private files into a public sidecar            | Medium   | Allow-list is opt-in and root-scoped; reuse `capture_file_exceeds_size_limit`; surface the target sidecar's visibility in the launch preview. |
| Provider metadata importing arbitrary plugin code at config load                                         | Low      | Declarative-first means the common path reads a literal; `SASE_DISABLE_PLUGINS` remains the escape hatch. |
| `sase-research` vs `sase--research` confusion                                                            | Low      | See §11.                                                                                          |

---

## 11. The `sase-research` plugin repo

`sase-org/sase-research` exists with one commit and a **0-byte README**; it is greenfield.
`sase-org/sase--research` is this project's research *content* sidecar. The names differ by
one hyphen, so the distinction has to be stated everywhere it appears:

- **Repo description** — change from the current `sase--research Artifact Repo Plugin` to
  something unambiguous, e.g. *"sase plugin — research artifact-repo provider (ref + file
  hook). Not the sase--research content sidecar."*
- **`repos.linked[].description`** in this project's `sase/sase.yml` — this string is what
  `sase memory init` renders into the `Repositories` section of `AGENTS.md` / `CLAUDE.md`,
  so it is the description agents actually read. Make it carry the disambiguation.
- **README first paragraph.**

### 11.1 Structure

Model it on `sase-telegram` (hatchling, `src/` layout, ruff + mypy strict, pytest with
`--strict-markers --strict-config`, `.github/`, `Justfile`, release-please,
`.release-please-manifest.json`, `docs/`, `sase.yml`, `sdd/` + `plans/`).

```toml
[project.entry-points."sase_artifact"]
research = "sase_research.provider:ResearchArtifactPlugin"

[project.entry-points."sase_xprompts"]
sase_research = "sase_research"

[project.entry-points."sase_config"]
sase_research = "sase_research"
```

Contents:

- `src/sase_research/provider.py` — one `RefProviderMetadata` literal (ref `research`,
  `path_globs: ["20*/**/*.md", "!20*/*/*__*.md"]`, properties `create_time`,
  `updated_time`, `status`, sub-tab label/accent, `Referenced By` columns) plus one
  `FileHookProviderMetadata` literal (`name: research-highlights`, `filters.sidecars:
  [research]`, the same path globs, `agent_name_globs: ["!research.*.cld",
  "!research.*.cdx"]`, `ops: [ADD]`, `timeout: 120s`) with **`command` deliberately left
  unset and required**, so your chezmoi `sase.yml` keeps supplying
  `command: bob highlights create --include-id`.
- `src/sase_research/xprompts/` — `research.md`, `research/image.md`, `research/more.md`,
  `research/prompt.md`, `research_swarm.md`, moved out of
  `chezmoi/home/sase/xprompts/` and the chezmoi `xprompts:` config block.
- `src/sase_research/default_config.yml` — the `researchers` model-alias bucket and the
  `research` tribe display config, so `#research_swarm` works on a fresh install; your
  chezmoi values still win by layer precedence.
- `docs/` + `tests/` covering: metadata validity, glob semantics against real path
  fixtures, frontmatter property parsing, expansion snapshot, back-link row shape, and an
  end-to-end "`use: sase_research` resolves to the expected effective config" test.
- `.github/workflows/ci.yml` — ruff, mypy, pytest, and a matrix pin against the minimum
  supported `sase` version.

One migration wrinkle: `research_swarm.md` references `%model:@research_a` /
`@research_b` / `@research_lead` and `$(sase repo path research --ensure)`. Shipping the
aliases in the plugin's `default_config.yml` (pointing at logical aliases like `@smartest`)
is what makes the moved xprompt work for anyone who installs the plugin.

---

## 12. Alternatives considered and rejected

**A. Keep ref xprompts, layer providers on top.** Rejected: two overlapping definition
systems for one concept, and the precedence table is already seven levels deep. Adding an
eighth source makes `sase xprompt show`'s provenance output unreadable.

**B. Pure config, no plugin hook.** Rejected on your stated requirement (users defining and
sharing ref types) and on practical grounds — the research file hook and the `#research*`
xprompts need a distributable home regardless.

**C. Pure pluggy, matching `sase_vcs` / `sase_workspace` exactly.** Rejected as the
*primary* mechanism: it would force every provider to ship Python for behavior that is
entirely declarable, making the research provider ~300 lines instead of ~60, and making
config validation impossible without importing plugin code. Adopted as the *override*
mechanism (§4.1).

**D. Resource-only plugins (`ref.yml` package data, like `sase_xprompts`).** Attractive —
no code import, trivially cacheable — but it cannot express a computed link target or
provider-supplied properties for entry-backed refs. The hybrid in §4.1 gets the declarative
benefits for the common case without that ceiling.

**E. Split `@file` into `@file` (paths) + `@artifact` (digests).** Rejected: the scanner
already anticipates a two-segment `file:` payload, and a split breaks every persisted
`file:` string plus `sase artifact create`'s printed `ref:` line for no user-visible gain.

**F. Put the ref registry in Python only.** Rejected per `CLAUDE.md`'s Rust-core boundary:
grammar, resolution, filtering, link numbering, and footer rendering are cross-frontend
behavior and belong in `sase-core`. Provider discovery, config merge, pluggy dispatch, and
ACE presentation stay in Python — the same split the current code already uses.

---

## 13. Recommended solution (summary)

1. **Surgically retire** the `#ref/` xprompt surface (§3.1, ~1,200–1,600 LOC) in a
   standalone phase. **Keep** the path-filter contract, the `filtered` status, the
   document-root plumbing, and `sase-core-rs` v0.21.0.
2. **Define one ref contract**, declarative-first: a `RefProviderMetadata` literal covering
   expansion, inventory/filters, properties, sub-tab presentation, link target, and
   `Referenced By` columns — with optional `sase_artifact` pluggy hooks
   (`ref_expand`, `ref_inventory`, `ref_properties`, `ref_link_target`, `ref_backlink_row`,
   `file_hook_provider_metadata`) as overrides. Same pluggy project serves the
   `file_hooks: use:` requirement.
3. **Config**: `use: <provider>` supplies defaults, sibling `ref:` keys override
   field-by-field, fully-inline works with no plugin. Unresolvable `use:` fails soft.
   Ship `sase_plans` as an in-tree provider and have `sase init` write `use: sase_plans`
   via the existing `ruamel` config writer.
4. **Builtins**: `@stitch` (bare hash or `repo@hash`, `commit:` kept as a permanent parse
   alias), `@patch` (new Rust kind, PR-URL link or none), `@bead` (short-id with
   project-first ordering and `ambiguous` on collision), `@file` (one kind, path *or*
   digest payload, root-scoped allow-list). Recommend retaining `@chat`/`@bug`/`@agent` as
   builtin providers; removing them is a separate migration decision.
5. **Publication**: reference-style `[@ref:arg][N]` links using the numbering allocator
   lifted from `commit_footer.rs`; `@file` contents into `files/<shard>/<pool_filename>`
   via the existing `artifact_pool_filename`; artifact-repo refs linked as pinned-revision
   permalinks.
6. **`Referenced By`**: a Rust-owned, capped, idempotent footer block, written by a
   generalized `refresh_plan_links`, triggered from publication **through the outbox**,
   under a fixed artifact-repos-before-agents lock order.
7. **ACE**: dynamic sub-tabs from configured providers; generalize `plans_*` into one
   provider-driven documents pane; delete `chats_*` and the old `files_*`; rebuild Files as
   one row per logical file with version toggling and a visible origin badge. Land last.
8. **`sase-research`**: build it on the `sase-telegram` template, register on
   `sase_artifact` + `sase_xprompts` + `sase_config`, move the four `#research*` xprompts
   and `#research_swarm` in, keep `command:` user-supplied, and make the
   `sase-research` vs `sase--research` distinction explicit in the repo description, the
   README, and the linked-repo description that feeds generated agent memory.
