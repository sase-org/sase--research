---
create_time: 2026-08-11
updated_time: 2026-08-11
status: research
---

# Replacing Ref XPrompts With a Ref Provider Contract

**Research question:** how should SASE retire the `#ref/<kind>` xprompt surface
delivered by epic `sase-ho` and replace it with a _ref contract_ fulfilled by a small
set of builtin refs, the special `@file` ref, and artifact-repo (today: sidecar-repo)
configurations — including pluggable providers, `@file` tracking, prompt-time ref→link
conversion, `Referenced By` back-links, and the ACE "Artifacts" tab redesign?

**Sources.** This report merges two independent research passes
([`__a`](ref_provider_contract__a.md), [`__b`](ref_provider_contract__b.md)) with a
third verification pass that re-read the disputed code directly. Repository states:
`sase` at `a3ec2a014`, `sase-core` at master (`sase-core-rs` v0.21.0 installed),
`chezmoi` linked, `sase-org/sase-research` at its single `6b63282` commit. Where the two
source reports disagreed, §2 states which one the code supports and why.

---

## Bottom line

**Five recommendations, in priority order.**

1. **Do not `git revert` `sase-ho`.** Both researchers reached this independently and
   the code supports it. The epic is three separable layers, and only one — the xprompt
   adapter — is the thing to remove. The path-filter contract (`artifact_ref/filter.rs`,
   `filter_artifact_ref_path_payloads`, the `filtered` resolution status) and the
   document-root plumbing (`ArtifactRefDocumentRoot`, `effective_sidecar_ref_policies`)
   are precisely the primitives the new contract needs. Reverting the Rust would also be
   a **wire-schema downgrade** against an already-released, already-installed binding
   that `tools/validate_sase_core_rs` gates. Do a surgical retirement of ~1,200–1,600
   LOC (§3), keep the rest, re-point it.

2. **Declarative-first provider spec, owned by Rust, with pluggy used only for
   registration.** This resolves the two reports' central disagreement. A provider
   declares an immutable, versioned, JSON-shaped spec; the shared core executes a small
   set of strategies. Plugins do **not** get per-resolution callbacks on the launch,
   completion, or TUI paths. `sase-research` then ships ~60 lines of metadata and zero
   resolution code.

3. **Three primitives you asked for already exist — and two need a specific extension.**
   `commit_footer.rs::assign_reference_id` really does allocate "the first available
   positive integer" and reuses one `[N]` per distinct destination. But its companion
   `reference_ids_in_body` scans **definition lines only** (`[n]: dest`), not numeric
   _uses_ (`[text][n]`), and has no fenced-code awareness — both must be added before it
   is safe on prompt documents. `rewrite_prompt_artifact_links` already rewrites refs
   idempotently while skipping literal zones; it needs only a reference-style emitter.
   `refresh_plan_links` is already a locked, batched, cross-repo section reconciler —
   that is the `Referenced By` writer.

4. **The current artifact pool cannot satisfy "exactly one location per unique
   contents."** It has _two_ independent duplication vectors, not one:
   `artifact_pool_filename` is `{12-hex-digest-prefix}-{basename}`, so identical bytes
   under different basenames get different filenames; and `relative_artifact_link`
   publishes to `artifacts/<yyyymm>/<name>`, so identical bytes referenced in different
   months land in different directories. A true full-SHA-256 content-addressed store is
   required, not a reshuffle of the existing pool.

5. **The biggest risk is persisted data, not any new feature.** `commit:`, `file:`,
   `chat:`, `bug:`, and `agent:` reference strings are persisted in bead `refs:` lists,
   `consumption.jsonl`, prompt manifests, and Patch files. `@stitch` needs a
   **permanent** parse alias for `commit:`, never a rename.

---

## 1. Verified ground truth

Everything in this section was read or executed at the stated revisions.

### 1.1 The eight refs today

`sase xprompt list` reports exactly eight ref-kind entries:

| Ref             | Kind       | Source                                             |
| --------------- | ---------- | -------------------------------------------------- |
| `#ref/agent`    | `agent`    | `src/sase/xprompts/refs/agent.md`                  |
| `#ref/bead`     | `bead`     | `src/sase/xprompts/refs/bead.md`                   |
| `#ref/bug`      | `bug`      | `src/sase/xprompts/refs/bug.md`                    |
| `#ref/chat`     | `chat`     | `src/sase/xprompts/refs/chat.md`                   |
| `#ref/commit`   | `commit`   | `src/sase/xprompts/refs/commit.md`                 |
| `#ref/file`     | `file`     | `src/sase/xprompts/refs/file.md`                   |
| `#ref/plans`    | `plans`    | `generated_sidecar_ref:plans` (globs `**/*.md`)    |
| `#ref/research` | `research` | `generated_sidecar_ref:research` (globs `**/*.md`) |

Three consequences that matter for the redesign:

- **The authored plans ref is `@plans`, plural.**
  `sidecar_ref_config._sidecar_role_ref_kind` defaults the ref kind to the sidecar
  _role_, and `PLANS_SIDECAR_ROLE = "plans"`. Your request says `@plan`. That is a
  **rename with a deprecation path**, not a no-op. Role (`plans`), authored ref
  (`plan`), and tab label (`Plans`) must become three separate fields; deriving all
  three from one string is exactly what produced today's behavior.
- The research ref's path globs are today the plain default `**/*.md`, and **not** the
  file hook's tighter `["20*/**/*.md", "!20*/*/*__*.md"]`. Both source reports proposed
  giving the research _ref provider_ those tighter globs. That is a deliberate behavior
  change — it would drop `__a`/`__b` sibling reports from `@research:` completion, which
  is desirable and consistent with the hook — and should be called out as such rather
  than described as a port.
- `sase-hv` (the `gd` definition-jump follow-up) is **already closed as `canceled`**,
  with the close reason naming this very redesign. No action needed there.

### 1.2 Numbering primitives (`commit_footer.rs`)

```rust
fn allocate_numeric_id(reserved_ids: &BTreeSet<String>, used_ids: &BTreeMap<String, String>) -> String {
    let mut number = 1_u64;
    loop {
        let candidate = number.to_string();
        if !reserved_ids.contains(&candidate) && !used_ids.contains_key(&candidate) { return candidate; }
        number += 1;
    }
}
fn reference_ids_in_body(body: &str) -> BTreeSet<String> {
    body.lines().filter_map(|line| parse_reference_definition(line.trim())).map(...).collect()
}
```

`assign_reference_id` prefers an id already bound to the same destination before
allocating, so repeated refs to one target share one `[N]`. **Verified: matches the
requirement.**

**Two gaps.** `reference_ids_in_body` only parses `[id]: destination` _definitions_. A
prompt containing a dangling numeric use (`[see][3]` with no `[3]:` line) would let the
allocator hand `3` out again, producing a collision. And `body.lines()` has no
fenced-code awareness, so a `[1]: http://…` inside a fence is (harmlessly) reserved
while a `[2]` use inside a fence is invisible. For commit messages neither matters; for
prompt documents both do. Extend the scan to numeric _uses_ outside literal zones —
reusing the zone logic that `rewrite_prompt_artifact_links` already has.

**CommonMark caveat:** the spec uses the _first_ matching definition, so emitting a
duplicate `[N]:` and hoping the last wins is incorrect. Footnote labels (`[^1]`) are a
separate namespace and should not consume plain `[1]`.

### 1.3 The `@file` grammar already anticipates two segments

```rust
// scanner.rs::trim_candidate_end
if colon_count == 1 || kind == Some("file") && colon_count == 2 { break; }
```

The current payload is `(explicit|default):<hex24>` — a 24-hex-char artifact digest, not
a full SHA-256. Fragments are supported (`file:default:52895d…#t=90`), because the
scanner splits the payload at the first `#`.

**The scanner has no quoting support.** Candidates run from `@` to a
trailing-punctuation trim. Any argument containing a space — a Patch name, a path — is
currently unrepresentable. Adding `@kind:"…"` is new grammar work, and it is a
prerequisite for `@patch` and for `@file` on real-world paths.

### 1.4 The artifact pool duplicates content two ways

```rust
pub fn artifact_pool_filename(sha256: &str, original_name: &str) -> String {
    // 12 hex chars of the digest, then the sanitized basename
    format!("{digest_prefix}-{basename}")
}
```

```python
# prompt_archive/paths.py
def relative_artifact_link(yyyymm: str, filename: str) -> str:
    return f"../../artifacts/{yyyymm}/{safe_name}"
```

- **Basename vector:** identical bytes named `gtd.md` and `gtd-copy.md` produce
  `abc123def456-gtd.md` and `abc123def456-gtd-copy.md`. Two paths, one content.
- **Month vector:** the same bytes cited in July and August land in `artifacts/202607/…`
  and `artifacts/202608/…`. Two paths, one content.

Also note the disambiguator fires only on _basename sanitization_ problems
(`sanitized != original_basename`, over-length, `.`/`..`) — **not** on digest-prefix
collision. Two different contents sharing a basename and the first 12 hex digits of
their SHA-256 would silently alias. At 48 bits that is a ~16M-artifact birthday bound,
so it is a low-severity note, not a live bug — but it is another reason not to build the
new store on this function.

### 1.5 Plumbing that exists and should be reused

| Asset                                                             | Location                                                  |
| ----------------------------------------------------------------- | --------------------------------------------------------- |
| Locked, batched cross-repo section reconciler                     | `sdd/plan_links_refresh.py::refresh_plan_links` (417 LOC) |
| Rust-owned idempotent projected section, capped at 50 + `omitted` | `sdd/plan_header_block.py` + `sections.rs`                |
| Deferred/quarantined publication machinery                        | `agents_sync/publication_outbox*.py` (6 modules)          |
| Launch-time staging: sha256, MIME, size cap, `fcntl` JSONL        | `core/prompt_artifact_staging.py`                         |
| Idempotent, literal-zone-aware ref rewriting                      | `prompt_artifact.rs::rewrite_prompt_artifact_links`       |
| Surgical `ruamel` writes to project `sase/sase.yml`               | `main/_repo_init_config.py`                               |
| Fail-soft-per-entry config parsing (the model to copy)            | `config/file_hooks.py` (`logger.warning` + `continue`)    |
| Plugin discovery + `SASE_DISABLE_PLUGIN_<GROUP>` switches         | `main/plugin_discovery.py`, `plugins/inventory.py`        |

Existing pluggy projects: `sase_vcs`, `sase_workspace`, `sase_llm` (provider _classes_).
Existing resource groups: `sase_xprompts`, `sase_config`, `sase_plugin_manifest`
(package data). `plugins/inventory.py` splits these into `PROVIDER_GROUPS` and
`RESOURCE_GROUPS`; a new artifact group joins the former.

### 1.6 `sase-org/sase-research` and the research xprompts

The repo is greenfield: one commit, a **0-byte README**, and the description
`sase--research Artifact Repo Plugin` — which is itself the ambiguity to fix.

The **complete** research xprompt inventory (neither source report had this exactly
right):

| Xprompt               | Where it actually lives                                      |
| --------------------- | ------------------------------------------------------------ |
| `#research`           | `xprompts:` block in chezmoi `home/dot_config/sase/sase.yml` |
| `#research/image`     | same config block                                            |
| `#research/more`      | same config block                                            |
| `#research/prompt`    | same config block                                            |
| `#research_swarm`     | file — `chezmoi/home/sase/xprompts/research_swarm.md`        |
| `#old_research_swarm` | file — `chezmoi/home/sase/xprompts/old_research_swarm.md`    |

Only **one** of the five is a `.md` file; four are inline YAML in the config block.
Report `__b` assumed all five were files under `home/sase/xprompts/`, which would
mis-scope the migration. `#old_research_swarm` is a legacy alias and should be dropped
rather than carried into the plugin.

Bryan's current file hook, verified verbatim:

```yaml
file_hooks:
  - name: research-highlights
    description:
      Render new research reports into Highlights PDFs for the Obsidian reading queue.
    command: bob highlights create --include-id
    filters:
      sidecars: [research]
      path_globs: ["20*/**/*.md", "!20*/*/*__*.md"]
      agent_name_globs: ["!research.*.cld", "!research.*.cdx"]
      ops: [ADD]
    timeout: 120s
```

---

## 2. Where the two reports conflicted, and what the code says

| #   | Question                    | `__a`                                                      | `__b`                                                   | Resolution                                                                                                                                                                                                                               |
| --- | --------------------------- | ---------------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Plugin dispatch model       | Declarative specs only; **no** per-use callbacks           | Declarative-first **plus** `firstresult` override hooks | **`__a`.** See below.                                                                                                                                                                                                                    |
| 2   | CAS layout                  | `files/objects/sha256/ab/<64hex>`                          | `files/<sha256[:2]>/<pool_filename>`                    | **`__a`.** `__b`'s scheme keeps the basename in the path and so keeps the duplication vector the requirement forbids (§1.4).                                                                                                             |
| 3   | Where the contract lives    | Rust `ArtifactRefProviderSpec`                             | Python `RefProviderMetadata` dataclass                  | **`__a`**, per `CLAUDE.md`'s Rust-core boundary. `__b` agrees in its own §12-F; the dataclass was a presentation choice, not a boundary claim.                                                                                           |
| 4   | `@file` old digest payload  | Parse only as path; digests via historical reader          | Both payloads live                                      | **`__b`.** `scanner.rs` already special-cases two-colon `file:` payloads, and `explicit`/`default` are reserved first segments, so disambiguation is total. Splitting would break persisted `file:` strings.                             |
| 5   | `@chat` / `@bug` / `@agent` | Retire from live authoring                                 | Keep as builtin providers                               | **`__b`**, but it is your call. They satisfy the contract with no special-casing, `@agent` is what makes agent-to-agent cross-links work, and their strings are persisted — removal is a data migration, so it belongs in its own phase. |
| 6   | Where `use:` goes           | `ref.use:` (inside the ref mapping)                        | sidecar-level `use:`                                    | **`__a`.** Today's config is `<role>.ref.{xprompt, filters.path_globs}`; `use:` replaces `xprompt` in place, keeps the ref surface self-contained, and matches your wording ("sidecar repo _ref_ configurations").                       |
| 7   | Provider id                 | `research`                                                 | `sase_research`                                         | **`__a`.** Ids are already namespaced by group; `research` reads better in `use:` and matches `plan`, `research-highlights`.                                                                                                             |
| 8   | Reference numbering         | Needs extension (uses + literal zones)                     | "Already does what you want"                            | **`__a`.** Verified in §1.2 — definitions-only scan is a real gap.                                                                                                                                                                       |
| 9   | Plugin repo template        | `sase-github`                                              | `sase-telegram`                                         | Either. `sase-telegram` is the closer structural match (hatchling, `src/`, release-please); `sase-github` is the closer _provider_ precedent. Take structure from `sase-telegram`, entry-point patterns from `sase-github`.              |
| 10  | `@plans` → `@plan`          | Flagged as a rename needing an alias                       | Not addressed                                           | **`__a`.** Confirmed in §1.1.                                                                                                                                                                                                            |
| 11  | Prompt project context      | Dedicated section: explicit `PromptRefContext` per segment | Not addressed                                           | **`__a`.** This is a direct requirement of your ask and is load-bearing for swarms.                                                                                                                                                      |

### On conflict 1 — the dispatch model

`__b`'s argument for override hooks is that a genuinely exotic provider should still be
able to compute things. `__a`'s counter is stronger and is the one to adopt:

- Completion and the ACE inventory call resolution at high frequency. Executing
  third-party Python there makes latency and failure modes unbounded, and `tui_perf.md`
  is the governing memory for exactly that surface.
- Config **validation** becomes impossible without importing plugin code. A declarative
  spec can be validated, cached, and diffed by digest; a callback cannot.
- Native and editor consumers (LSP, any future frontend) cannot call Python hooks, so
  per-use callbacks guarantee divergent semantics — the failure mode `CLAUDE.md`'s
  Rust-core boundary exists to prevent.

The escape hatch `__b` wanted is preserved without callbacks: the spec's strategy
families are extensible, and a provider needing genuinely novel behavior motivates a
_new declared strategy_ in core — a reviewable, shared change — rather than an opaque
plugin closure.

---

## 3. Retirement plan (not a revert)

### 3.1 Delete

| Target                                                                                                           | ~LOC |
| ---------------------------------------------------------------------------------------------------------------- | ---- |
| `src/sase/xprompts/refs/*.md` (6 renderer bodies)                                                                | 40   |
| `src/sase/xprompt/loader_refs.py` (the `ref/<kind>` registry)                                                    | 364  |
| `src/sase/artifact_ref_renderers.py` (keep the Jinja-protection helper)                                          | 60   |
| `ref` / `ref_kind` / `ref_sidecar_role` / `ref_path_globs` / `ref_shadowed_sources` on `XPrompt` + catalog wires | 120  |
| `#ref/` rewriting in `artifact_ref_prompt_parsing.py`                                                            | 80   |
| `sase/refs/` sources in `content_layout.py` + `resolve_ref_file_sources`                                         | 100  |
| `#ref/` completion in `ace/tui/prompt_catalog.py` + `_startup_prompt_catalog.py`                                 | 90   |
| `xprompt_browser_helpers.py` synthetic-source special cases (`0a45feebc`)                                        | 22   |
| Rust contextual-ref catalog entries (`xprompt_catalog.rs`, `sase_xprompt_lsp`)                                   | 150  |
| `reject_misplaced_ref()` namespace policing on ordinary xprompt load                                             | —    |
| Docs: `docs/xprompt.md#artifact-reference-xprompts`, `content_layout.md`, `plugins.md`                           | 120  |
| Tests (`test_xprompt_ref_sources.py`, `test_artifact_ref_xprompt_integration.py`, parts of others)               | 400  |

Also retire the synthetic source schemes `sidecar_ref_config:` and
`generated_sidecar_ref:`, and the seven-level renderer precedence table.

### 3.2 Keep and re-point

- `artifact_ref/filter.rs`, `filter_artifact_ref_path_payloads`, and
  `ARTIFACT_REF_PATH_FILTER_WIRE_SCHEMA_VERSION`. Its documented semantics (normalized
  repo-relative POSIX, case-sensitive, `**/` matches zero dirs, OR-ed positives, `!`
  vetoes, negative-only starts allow-all) become the **one** filter vocabulary across
  sidecar globs, `@file` allow-lists, and `file_hooks`.
- The `filtered` resolution status and its non-leaking diagnostic — it already refuses
  to leak absolute local paths into prompt text, which `@file` needs.
- `ArtifactRefDocumentRoot { kind, path, path_globs }` and `ArtifactRefContext`.
- `effective_sidecar_ref_policies`' shape — swap the `xprompt` field for the
  provider-resolved spec, keep the role merge/disable logic.
- `sase_core_rs` v0.21.0 itself. Reverting is a wire-schema downgrade.

### 3.3 Sequence the deletion as its own phase

Land the delete before the provider hook, with builtins falling back to the
pre-`sase-ho` hardcoded rendering path (still present in
`artifact_ref_prompt_rendering.py`). This keeps the delete diff reviewable alone and
`master` shippable between phases.

---

## 4. The ref contract

### 4.1 Runtime contract (Rust-owned)

```text
descriptor()             stable kind, labels, grammar, capabilities, schema version
inventory(context)       files or generic entries for completion and ACE
resolve(argument, ctx)   one normalized entry, or a structured diagnostic
prompt_text(resolved)    the text substituted into the launch prompt
properties(resolved)     typed values for filtering and detail rendering
publication_target(use)  durable link target for the captured version
```

Four strategy families implement it — no dynamic dispatch per provider:

1. **builtin structured entries** — `stitch`, `patch`, `bead` (and, if retained, `bug`);
2. **the special local-file provider** — `file`;
3. **declarative sidecar documents** — `plan`, `research`, third-party kinds (and, if
   retained, `chat`, `agent`);
4. **historical compatibility readers** — parse-only, absent from completion.

Normalized results:

```text
ArtifactEntry
  stable_id             provider-scoped logical identity
  ref_kind              stitch | patch | bead | file | plan | research | …
  canonical_argument, display_label, project_display_name
  repository, repo_relative_path
  captured_revision     full VCS commit, when applicable
  captured_digest       full SHA-256, when bytes were observed
  logical_path          portable configured-root identity (for @file)
  properties            typed map constrained by the provider schema
  origin                prompt_ref | agent_artifact | both

ResolvedArtifactRef
  raw_ref, canonical_ref, occurrence_span
  entry, prompt_text, publication_target, captured_file, diagnostics
```

`stable_id` is _logical_ identity; `captured_revision`/`captured_digest` is _version_
identity. That distinction is what lets the Files pane show one row for `~/bob/gtd.md`
while exposing every captured version.

### 4.2 Plugin registration

Two hookspecs on one new pluggy project, with matching entry-point groups registered in
`plugins/inventory.py::PLUGIN_GROUPS` as provider groups:

```python
sase_artifact_ref_providers() -> Iterable[ArtifactRefProviderSpec]
sase_file_hook_providers()    -> Iterable[FileHookProviderSpec]
```

Name the pluggy project `sase_artifact` (per `__b`) — ref providers and file-hook
providers ship together in practice, `sase_workspace` already precedents one project
covering several hook families, and the name anticipates the sidecar→artifact-repo
rename. Use two entry-point groups (`sase_artifact_refs`, `sase_file_hooks`) so
`SASE_DISABLE_PLUGIN_ARTIFACT_REFS` works independently and `sase plugin` inventory
stays legible.

Hooks are called once while assembling the config registry — never per ref, per
keystroke, or per file event. Returned specs are converted immediately to versioned wire
values. The registry enforces: lowercase provider id and ref kind; a host-understood
schema version; unique ids across distributions; reserved kinds
`stitch`/`patch`/`bead`/`file`; exactly one effective provider per kind per project;
deterministic ordering independent of pluggy call order; and a cache token of
(distribution name, version, spec digest).

**Fail soft, always.** An unresolvable `use:` must warn and degrade — never raise on the
launch path — exactly as `config/file_hooks.py` already does per entry. Pair that with a
hard `sase doctor` finding naming the config path and the install command. A project
whose `sase.yml` names an uninstalled provider must still launch agents.

### 4.3 The declarative sidecar spec

```yaml
schema_version: 1
provider: research
ref:
  kind: research
  display_name: Research
  description: Durable research reports and generated media
  argument: { type: repo_path, quoting: shell }
  expansion:
    format: "the {checkout_path} file in the {sidecar_role} artifact repo"
  inventory:
    path_globs: ["20*/**/*.md", "!20*/*/*__*.md"]
  identity: { property: id, fallback: repo_path }
  properties:
    source: markdown_frontmatter
    fields:
      create_time: { type: datetime, label: Created }
      updated_time: { type: datetime, label: Updated }
      status: { type: string, label: Status, facet: true }
      tags: { type: string_list, label: Tags }
  detail:
    title: title
    fields: [status, create_time, updated_time, tags]
    body: markdown
  publication:
    link: vcs_permalink
    referenced_by: markdown_table
```

`expansion.format` is a **small closed formatter**, not Jinja and not an xprompt: its
valid placeholders are declared by the contract and validated in Rust. It cannot run
commands, recursively expand directives, or touch the filesystem.

Property types stay modest — `string`, `enum`, `boolean`, `integer`, `number`, `date`,
`datetime`, `string_list`. Unknown frontmatter is preserved in raw detail data but is
not filterable; otherwise every arbitrary YAML value becomes a TUI query language.

Presentation entries are **hints, not widgets**. A generic pane renders `display_name`,
a title property, ordered detail fields, and a Markdown body. Provider packages must
never ship Python TUI classes to display a new artifact type.

For **entry-backed** builtins, `properties.source` is `provider` and the builtin
supplies values from the domain model — stitch:
repo/sha/subject/author/date/Patch/stitch-number; patch:
project/status/parent/PR/mentors/stitch-count; bead: project/id/title/type/tier/
status/priority/size/parent/assignee. That is what makes Artifacts filtering uniform
across path-backed and entry-backed refs without frontmatter existing everywhere.

### 4.4 `use:` and inline are the same thing

```yaml
# Provider-backed — one field
repos: { sidecar: { custom: { research: { ref: { use: research } } } } }

# Provider-backed with a field-level override
repos:
  sidecar:
    custom:
      research:
        ref:
          use: research
          inventory: { path_globs: ["20*/**/*.md", "!20*/*/*__*.md"] }

# Fully inline, no plugin installed — the §4.3 block verbatim under `ref:`
```

`use:` means "start from this registered spec." Merge rules: scalars replace, mappings
deep-merge, **lists replace rather than concatenate**. `schema_version`, provider
identity, and strategy type cannot be overridden. Diagnostics must name the supplying
distribution/ version and the config layer for each override — this is what makes a
seven-level precedence table unnecessary. Both spellings normalize to one spec, and
there is a golden test asserting inline/`use` parity.

Schema deltas in `src/sase/config/sase.schema.json`:

- `sidecarRef`: drop `xprompt`; add `use`, `kind`, `display_name`, `argument`,
  `expansion`, `inventory`, `identity`, `properties`, `detail`, `publication`. Keep
  `filters.path_globs` as a deprecated alias for `inventory.path_globs` for one release.
- `fileHook`: add `use`; relax `required: ["name","command"]` to `required: ["command"]`
  via `anyOf` when `use` is present.

The same machinery serves file hooks:

```yaml
file_hooks:
  - use: research-highlights
    command: bob highlights create --include-id
```

The `research-highlights` provider supplies name, description, `sidecars: [research]`,
the path globs, `agent_name_globs`, `ops: [ADD]`, and `timeout: 120s`, and marks
`command` as a **required user override** (portable policy, local executable). Bryan's
chezmoi keeps exactly the `command:` line above.

### 4.5 Builtin `plan` provider and `sase init`

Ship `plan` as an in-tree provider registered on the same group by the `sase` package
itself, so `use:` has no privileged builtin path. `sase init` then writes, idempotently,
via the existing `ruamel` writer in `main/_repo_init_config.py`:

```yaml
repos:
  sidecar:
    builtin:
      plans:
        auto_clone: true
        ref:
          use: plan
```

Skip when `use:` is already present; never clobber a user's inline `ref:`.

---

## 5. Builtin refs

### 5.1 Shared grammar

Every ref accepts a bare argument and a quoted argument:

```text
@kind:bare-argument
@kind:"argument containing spaces"
```

Quoting is **new work** (§1.3) and is a prerequisite for `@patch` and real-world `@file`
paths. Completion should insert quotes automatically when the argument requires them.
The scanner keeps protecting fenced blocks, inline code, literal launch zones, and
existing Markdown links, and keeps splitting a trailing `#fragment`.

### 5.2 `@stitch`

```text
@stitch:<short_hash>              # primary repo of the project in context
@stitch:<repo>@<short_hash>       # any repo in the SASE repo registry
```

`<repo>@<sha>` is already exactly how `commit` serializes (`format!("{repo}@{sha}")`),
and `scanner.rs` splits only on the first `:`, so a payload-internal `@` is already
tolerated. `parse_payload` disambiguates on the presence of `@`. Accept 7–40 hex
characters, resolve to a commit object, error on ambiguity, and store the **full** hash
plus canonical repo identity.

A Stitch may exist as a proposal without a commit (`(2a)`), but this ref's argument is a
VCS hash, so it denotes commit-bearing stitches only. Attach the containing Patch name
and stitch number when discoverable, without requiring them for an ordinary commit.

Expansion: `stitch <full-sha> in <repo> (checkout: <path>)`. Link: the VCS provider's
commit URL. **`commit:` remains a permanent parse alias** canonicalizing to `stitch:`.

### 5.3 `@patch`

`@patch:<name>` resolves in the current project's active and archive ProjectSpecs
(`<key>.sase`, `<key>-archive.sase`). Never silently select a same-named Patch from
another project; with no project context, accept a globally unique name but make
ambiguity a structured error listing candidate projects. Needs a new Patch kind/payload
in the Rust wire — the domain model already landed (`8344869`).

Expansion should be concise, not an inlined ProjectSpec:
`the <name> Patch in project <project> (inspect with \`sase patch show
<name>\`)`. Link to the PR when `PR:` is set; otherwise the published Patch/agent page;
otherwise render an unlinked code span. **Tracking must never depend on linkability.**

### 5.4 `@bead`

Accept a short id or a full bead id. A short id searches the in-context project's store
first; `ArtifactRefContext.bead_stores` is a cross-project tuple, so a cross-project
collision returns the existing `ambiguous` status with fully-qualified candidates.
Prefix ambiguity is an error, never first-match. Link to the hosted bead page.

### 5.5 `@file`

**One kind, two payload shapes** (conflict 4):

- `@file:~/bob/gtd.md` — an allow-listed local path, hashed and captured at launch.
- `@file:explicit:<hex24>` / `@file:default:<hex24>` — an already-indexed artifact,
  which is what `sase artifact create` emits today.

A payload whose first segment is `explicit` or `default` is a digest reference; anything
else is a path. Splitting off a separate `@artifact` kind would break every persisted
`file:` string for no user-visible gain.

Allow-list config — recommended for Bryan's home layer (`~/.config/sase/sase.yml`, since
`~/bob` is machine-global; project layers may append):

```yaml
artifact_refs:
  file:
    roots:
      - name: bob
        path: ~/bob
        path_globs: ["**/*.md"]
```

The **named root** gives a portable logical identity (`bob:gtd.md`) while the UI
displays the friendly `~/bob/gtd.md`. Extension filtering falls out of `path_globs` for
free, and multiple roots express different directory/file-type policies. Use the same
`filter_artifact_ref_path_payloads` vocabulary as everything else — one filter language
across the system is worth more than per-feature ergonomics.

Resolver obligations, in order:

1. expand `~`, parse the (possibly quoted) argument;
2. resolve the physical path and verify containment in exactly one configured root;
3. apply path globs to the root-relative POSIX path — a miss is `filtered`, not
   `missing`;
4. reject directories, devices, sockets, symlink escapes, unreadable files;
5. enforce the configurable size ceiling (`capture_file_exceeds_size_limit` exists);
6. read the bytes **once**, then hash _those_ bytes — never a later re-read of the
   source;
7. record logical path, authored spelling, size, MIME, capture time, and full SHA-256;
8. expand the prompt to the **immutable captured copy**, so the agent reads the same
   bytes publication later records.

Using `@file` is explicit publication intent, but the allow-list is still the
exfiltration boundary — gitignore rules are irrelevant and must never be read as
permission. Published metadata carries `bob:gtd.md` or `~/bob/gtd.md`; the physical
`/home/bryan/...` path stays private runtime metadata. Surface the target sidecar's
visibility in the launch preview.

---

## 6. Project context must come from the prompt

Your `@stitch` requirement — "determine what project is in context by checking what VCS
xprompt workflow is used in the prompt" — is load-bearing and deserves its own plumbing.
The launch planner already resolves a VCS context per prompt segment; promote that into
an explicit `PromptRefContext` threaded into late preprocessing:

```text
raw prompt segment
  → identify #git/#gh VCS workflow and project
  → expand ordinary xprompts / workflow steps
  → assemble provider registry + PromptRefContext
  → scan, resolve, capture, expand refs
  → launch agent
```

The context carries: project key and display name, primary repo, all resolvable SASE
repos, Patch store, bead stores, enabled sidecar providers, `@file` roots, and VCS
hosted-link capabilities. Unqualified `@stitch`, short `@bead`, and `@patch` all consume
exactly this value.

**Do not infer the project from `cwd`.** It happens to work for a simple single-segment
launch, but it is wrong for xprompt swarms and `---`-separated multi-agent prompts
(where segments can target different projects in one process), and it is unavailable in
home mode, in validation, and in editor completion. When a segment has no VCS project
and a short form needs one, the error should ask for a qualified form or a VCS workflow
— never search whichever workspace happens to be current.

---

## 7. Capture, publication, and linking

### 7.1 Per-occurrence use manifests

`prompt-artifacts.jsonl` records raw/expanded refs, kind, path, digest, MIME, and VCS
provenance; `artifact_consumption.jsonl` records a global agent/project association.
Neither is sufficient: prompt-time selection deduplicates by raw ref (losing
occurrences) and publication can resolve a non-primary repo against its _current_ HEAD,
linking bytes the agent never saw.

Add an immutable per-agent `ref-uses` manifest, one row per occurrence:

```json
{
  "schema_version": 1,
  "use_id": "…",
  "agent": "research.09.cld",
  "project": "sase",
  "provider": "research",
  "raw_ref": "@research:202608/x.md",
  "canonical_ref": "research:202608/x.md",
  "span": { "start": 120, "end": 156 },
  "entry_id": "research:202608/x.md",
  "logical_path": null,
  "captured_revision": "<full sha>",
  "captured_digest": "<sha256>",
  "origin": "prompt_ref",
  "properties": { "status": "research" },
  "captured_at": "2026-08-11T…Z"
}
```

The global consumption index stays as a derived query accelerator, not the source of
truth. Repeated refs in one prompt produce repeated rows but share one captured object
and one backref row carrying an occurrence count.

For clean tracked files capture both revision and content digest. For **dirty or
untracked** sidecar files, do not manufacture a permalink to HEAD — snapshot the bytes
into the agents object store, record provenance as local, and surface that no sidecar
permalink exists.

### 7.2 A true content-addressed store

Full SHA-256 as the only object identity, killing both duplication vectors from §1.4:

```text
files/objects/sha256/ab/abcdef…<64 hex>      # one byte sequence → exactly one path
agents/<agent>/ref-uses.json
agents/<agent>/artifacts.json
```

Write atomically to a temp file, verify the digest, rename into place only if absent; an
existing path at that digest requires byte verification, never a blind overwrite.
Metadata and logical names (MIME, original basename, labels) live in manifests, not in
the path. The missing extension is a presentation tradeoff — the UI renders from MIME
and downloads synthesize a friendly name — not a reason to duplicate bytes.

One store serves both `@file` captures and `sase artifact create` outputs; they differ
in provenance records, not in byte storage. Existing artifact ids become compatibility
aliases to the new object/version records. A **relative** link from a prompt to the
digest object (as `relative_artifact_link` already does) avoids a commit-hash circular
dependency and resolves both at HEAD and when browsing the prompt at an older commit.

### 7.3 Reference-style links

```markdown
Read [@research:202608/x.md][2] and [@file:~/bob/gtd.md][4].

[2]: https://github.com/sase-org/sase--research/blob/<captured-sha>/202608/x.md
[4]: ../../files/objects/sha256/ab/abcdef…
```

Extend `rewrite_prompt_artifact_links` (which already guarantees idempotency,
literal-zone skipping, and leaving pre-existing links alone) to emit reference style,
and lift `assign_reference_id` / `allocate_numeric_id` / `parse_reference_definition`
out of `commit_footer.rs` into a shared `markdown_link_refs.rs`. The allocator must
then:

1. collect numeric reference **definitions and uses**, outside protected zones (§1.2
   gap);
2. reuse an existing label whose destination already matches;
3. otherwise take the lowest positive integer not used by a different link or
   definition;
4. rewrite every live occurrence, preserving visible text exactly;
5. append new definitions in numeric order at the bottom;
6. return the linked use ids and labels so the `ARTIFACTS` header section stays in sync;
7. be byte-identical on a second run.

**Destinations:**

| Ref                         | Target                                                            |
| --------------------------- | ----------------------------------------------------------------- |
| `@stitch`                   | hosted commit URL for the captured full SHA                       |
| `@patch`                    | PR URL if present; else published Patch/agent page; else unlinked |
| `@bead`                     | hosted bead page (`bead_links.py` already resolves these)         |
| clean sidecar ref           | `blob/<captured-full-SHA>/<repo-relative-path>`                   |
| dirty/untracked sidecar ref | agents-sidecar SHA-256 snapshot                                   |
| `@file` (both payloads)     | relative link to the agents-sidecar SHA-256 object                |
| `@agent` (if retained)      | agent page (`agent_lanes.lane_page_path`)                         |

The pinned revision must be written at **resolution** time. A `main`-branch link rots as
soon as the artifact is edited, and the point of the citation is to name what the agent
actually read. `prompt_archive/preparation.py` already threads `primary_revision` and a
`HostedLinkResolver` into `_ArtifactTargetResolver`, so the plumbing exists. The VCS
provider constructs the URL — the ref contract requests `vcs_permalink` and never
hardcodes GitHub.

---

## 8. `Referenced By`

### 8.1 Render

At the **bottom** of an artifact file, only when citations exist, inside managed
markers:

```markdown
<!-- sase:referenced-by:start -->

## Referenced By

| Agent                | Project | Reference               | Published  | Uses |
| -------------------- | ------- | ----------------------- | ---------- | ---: |
| [research.09.cld][7] | sase    | `@research:202608/x.md` | 2026-08-11 |    2 |

<!-- sase:referenced-by:end -->
```

Columns come from the provider spec; rows from a default row builder. Reuse the
plan-header block's proven properties — Rust-owned rendering, deterministic sort, a hard
cap (50) with an `omitted: N` line, full idempotency — as a new _footer_ block module,
since `plan_header_block` is anchored to the top.

Back the table with a machine-readable sidecar index (e.g.
`.sase/referenced-by/<artifact-id>.json`) holding exact use ids, destinations, and
timestamps, so SASE never reverse-engineers its state from Markdown. The table is a
projection.

**Two invariants that are easy to miss:**

- **Backref metadata must not redefine an artifact's semantic version.** Content digests
  and change detection must ignore the managed block — otherwise every citation creates
  a "new version" whose only change is being cited, and citations form a feedback loop.
- **Backref commits must not run ordinary user `file_hooks`.** Add a
  `system_projection: referenced_by` cause and exclude it by default. Bryan's hook
  happens to filter `ops: [ADD]` while backrefs are modifications, but relying on that
  incidental filter would make the generic feature unsafe for the next hook someone
  writes.

`Referenced By` is a _different relation_ from the plans sidecar's existing `AGENTS`
section (agents that _worked on_ a plan vs. agents that _cited_ it). Keep both; document
the distinction; a `@plan:` citation must never add an `AGENTS` entry.

### 8.2 Write path

Generalize `refresh_plan_links` — it already resolves the sidecar root from the
`SddStore`, takes `store_git_write_lock(..., mutates_worktree=True)`, re-renders each
document, and writes one batched commit with a structured report. The generalization is
"operate on any artifact-repo role using the provider's row builder."

Trigger it from agent publication but **route it through `publication_outbox*`** rather
than calling it inline: a locked, offline, or contended research sidecar must never fail
the agents-sidecar publication that is the actual deliverable.

```text
1. Resolve refs and capture immutable use records at launch.
2. Copy missing SHA-256 objects; publish agent page, prompt, manifests.
3. Push the agents commit; obtain its permalink.
4. Enqueue one backref update per affected sidecar artifact.
5. Group by sidecar repo; update all managed blocks + indexes in one commit per repo.
6. Pull/rebase and retry on non-fast-forward.
7. Mark outbox rows complete only after the sidecar push succeeds.
```

Fix a **lock order — artifact repos first, `agents` last** — so a publication writing
back to two sidecars can never deadlock against a concurrent `sase plan links --write`.
Agent publication is the source of truth; a failed sidecar push stays a visible
retryable diagnostic and never rolls back or hides the agent. If an artifact moved,
locate it by the provider's identity property; if it was deleted, leave a visible outbox
error rather than attaching the row to a guessed path.

There is no cross-repo transaction and no need to simulate one. One commit per affected
sidecar repo per agent publication, batching all of that agent's refs; add debounce only
if publication bursts prove noisy.

---

## 9. ACE "Artifacts" tab

### 9.1 What must become dynamic

Today: `ArtifactsSubTab = Literal["prs","stitches","bugs","beads","files"]`,
`FilesSubTab = Literal["plans","chats","other"]`, static `PanelTab` tuples,
`show_numbers=True`, and reactive attributes typed with those `Literal`s in `app.py` and
`ace/testing/ace_page.py`.

Target: `["stitches","beads","bugs","prs", *provider_tabs, "files"]`, where
`provider_tabs` is the union of sidecar ref kinds configured by **enabled** projects, in
deterministic config order:

```text
Stitches | Beads | Bugs | PRs | Plans | Research | Files
```

`Plans` appears only if some enabled project configures the plans sidecar ref;
`Research` only if some enabled project sets `ref.use: research`. **Installing a
provider does not create a tab** — configuration does.

Mechanics:

- `ArtifactsSubTab` → `str` plus a runtime registry; `artifact_tabs.py` grows
  `resolve_artifacts_subtabs()` cached on `current_config_token()`, mirroring
  `get_all_workflow_metadata()` + `reset_workflow_metadata_caches()`.
- **Stable ids, not display names** (`ref:plan`, `ref:research`) for selection and
  persistence.
- Number keys: keep `1..N` stable for the fixed tabs, assign provider tabs the numbers
  after them, and promote `[` / `]` (`cycle_artifacts_subtab`) as the primary affordance
  in the help modal. Unstable number keys are a worse regression than no number keys.
- `current_files_subtab` disappears; a persisted `current_artifacts_subtab` naming an
  uninstalled provider falls back to `DEFAULT_ARTIFACTS_SUBTAB` rather than erroring.
- `default_config.yml`: `cycle_files_subtab` / `_reverse` (`(` / `)`) free up —
  repurpose them for version toggling on the new Files tab (§9.3).

Keep Bugs and PRs. Consolidating them into Beads/Patches is a separate feature with its
own data migration; folding it in here would inflate an already large change.

### 9.2 Generalize the Plans pane

`widgets/artifacts/` currently holds **13 `plans_*`, 9 `files_*`, and 8 `chats_*`
modules** — three parallel implementations of list + filter-bar + filter-session +
detail + rendering + navigation. Collapse `plans_*` into one
`ArtifactsDocumentsPane(provider)` driven by the spec's `properties` (filter tokens) and
presentation block (label, accent, grouping). `plan` becomes its first instance;
`research` costs **zero new pane code**. Delete `chats_*` and the old `files_*`. Net ACE
LOC likely _drops_ despite gaining dynamic tabs.

`plans_filtering.py::_PlanFilterRecord` is already a generic (project, status labels,
tier labels, kind labels, timestamp, haystack) record — it becomes
`(project, {property: labels}, timestamp, haystack)` driven by the declared schema.

### 9.3 The new Files pane

- **One row per unique logical file.** Group key: the named-root logical path for
  `@file:<path>`, the artifact id (or original source path when meaningful) for
  `sase artifact create` rows. Physical `/home/...` paths never become identity.
- **Version toggling on the selected row.** Versions are
  `(sha256, first_seen_at, agents[])` tuples; `(` / `)` are the natural bindings. The
  detail header shows `version i/n`, digest, capture time, agent, project, origin, MIME,
  and size. Repeated captures with an unchanged digest do not create a version but do
  add provenance records. Reuse the existing MIME-aware artifact viewer — do not build a
  second renderer.
- **Origin must be visible.** Three origins: `ref` (cited in a prompt), `created`
  (`sase artifact create`), `capture` (automatic staging). The index already carries an
  `explicit` boolean (`FilesSnapshot.explicit_count`); **widen it to an enum** rather
  than adding a parallel flag. Render as a badge/column and make it a filter facet.

This satisfies the `~/bob/gtd.md` case exactly: one row, multiple content digests, every
capturing agent visible.

### 9.4 Two gaps to close

- **Version index location.** Prompt-staged files land in the _workspace_
  `.sase/artifacts` pool and manifest, not the durable index that `query_artifact_files`
  reads. Promote `@file` versions into the durable index (or a sibling `ref_files`
  index) keyed by `(logical_path, sha256)` **at publication time** — that keeps the
  launch path cheap and gives the right semantics (only published runs contribute
  versions).
- **Performance.** `sase/memory/tui_perf.md` governs here; read it before implementing.
  N artifact repos means N tree scans, and dynamic tabs invite eager construction. Keep
  `ContentSwitcher` + `activate()`-on-visible laziness (`ArtifactsView.on_mount` already
  only activates when Artifacts is current), share one off-thread loader keyed by
  provider, and cache inventory by (provider-spec digest, project config, repo HEAD). Do
  **not** rebuild the previously removed global artifact graph; disposable
  revision-keyed indexes suffice. Expect `tests/ace/tui/visual/snapshots/png/` goldens
  to need `--sase-update-visual-snapshots`.

---

## 10. `sase-org/sase-research`

### 10.1 The naming problem, and where the fix has to land

`sase-org/sase-research` (plugin code) vs `sase-org/sase--research` (this project's
research _content_ sidecar) differ by one hyphen, and the plugin repo's current GitHub
description is literally `sase--research Artifact Repo Plugin`. State the distinction in
three places:

1. **GitHub description** — e.g. _"sase plugin — research artifact-repo provider (ref +
   file hook) and #research xprompts. Not the sase--research content sidecar."_
2. **`repos.linked[].description` in this project's `sase/sase.yml`** — this is the
   string `sase memory init` renders into the Repositories section of `AGENTS.md` /
   `CLAUDE.md`, so it is the description _agents actually read_. It must carry the
   disambiguation.
3. **README first paragraph.**

Also add a `description:` to the research sidecar entry pointing back the other way.

### 10.2 Contents

Structure from `sase-telegram` (hatchling, `src/` layout, ruff + strict mypy, pytest
with `--strict-markers --strict-config`, `.github/`, `Justfile`, release-please,
`docs/`); entry-point and provider patterns from `sase-github`.

```toml
[project.entry-points."sase_artifact_refs"]
research = "sase_research.provider:ResearchRefProvider"

[project.entry-points."sase_file_hooks"]
research-highlights = "sase_research.provider:ResearchHighlightsHook"

[project.entry-points."sase_xprompts"]
sase_research = "sase_research"

[project.entry-points."sase_config"]
sase_research = "sase_research"
```

- `src/sase_research/provider.py` — one ref spec literal (kind `research`, globs
  `["20*/**/*.md", "!20*/*/*__*.md"]`, properties `create_time`/`updated_time`/`status`,
  presentation, `Referenced By` columns) and one file-hook spec literal
  (`research-highlights`, `sidecars: [research]`, same globs,
  `agent_name_globs: ["!research.*.cld", "!research.*.cdx"]`, `ops: [ADD]`,
  `timeout: 120s`), with **`command` deliberately unset and required**.
- `src/sase_research/xprompts/` — the five research xprompts. **Four of them
  (`#research`, `#research/image`, `#research/more`, `#research/prompt`) must be lifted
  out of chezmoi's `xprompts:` YAML block, not moved as files** (§1.6); only
  `research_swarm.md` is already a file. Drop `#old_research_swarm` rather than porting
  it.
- `src/sase_research/default_config.yml` — the `researchers` model-alias bucket and the
  `research` tribe display config, so `#research_swarm` works on a fresh install.
  Bryan's chezmoi values still win by layer precedence. Without this, the moved
  `research_swarm.md` breaks: it references `%model:@research_a` / `@research_b` /
  `@research_lead` and `$(sase repo path research --ensure)`.
- `docs/`, `tests/`, `.github/workflows/ci.yml`.

### 10.3 Installation is not configuration

**A linked-repo clone is not an installed Python distribution and does not make entry
points visible.** This is the single most likely deployment failure and neither a linked
repo entry nor `auto_clone: true` solves it. Plan explicitly for: published-package
install for normal users, editable install for linked development, and a `sase doctor`
check that reports a missing `research` provider with the supplying config path and an
actionable install command. Silently falling back to an inline default would hide the
error.

### 10.4 Quality bar

CI must test the **wheel**, not just the source tree — resource and entry-point
packaging is this repo's most likely failure mode. Build sdist + wheel, install into a
clean env, enumerate entry points, and assert every packaged xprompt resource is
discoverable. Beyond that: unit tests for spec schema, command override, filter/glob
semantics against real path fixtures, frontmatter parsing, and
duplicate/missing-provider diagnostics; an inline-vs-`use` normalization golden test;
end-to-end tests for completion, resolution, expansion, captured revision, permalink
generation, and `Referenced By` projection; `#research_swarm` segment-boundary and
wait/fork directive parsing tests; a matrix pinned against the minimum supported `sase`
version; release-please + trusted PyPI publication.

---

## 11. Migration and risks

### 11.1 Authoring migration

| Current                   | New                            | Compatibility                                                    |
| ------------------------- | ------------------------------ | ---------------------------------------------------------------- |
| `@commit:<repo>@<sha>`    | `@stitch:[<repo>@]<sha>`       | **permanent** parse alias — persisted in bead refs and manifests |
| `@plans:<path>`           | `@plan:<path>`                 | deprecated alias for one release; completion offers only `@plan` |
| `@file:<src>:<hex24>`     | unchanged, plus `@file:<path>` | both live; `explicit`/`default` reserved as first segment        |
| `@bead:<id>`              | `@bead:<short-or-full-id>`     | extend in place                                                  |
| `@research:<path>`        | provider-backed, same spelling | no authoring change; globs tighten (§1.1)                        |
| `@chat`, `@bug`, `@agent` | retain as builtin providers    | removal is a separate migration-shaped decision                  |
| `#ref/<kind>`             | removed                        | actionable deprecation diagnostic during the window              |

Do not keep deprecated kinds in _completion_ during the warning release — that just
encourages new use. Historical archive rendering uses the manifest schema recorded with
the run; new prompt validation uses the new grammar.

### 11.2 Data migration

- Keep existing prompt-artifact and consumption manifests readable as version 1; start
  writing version 2 with occurrence, provider, revision, stable id, logical path,
  origin.
- Populate the SHA-256 object store lazily during publication; verify **full** hashes
  before deduplicating old 12-prefix-plus-basename objects.
- Build Files-pane logical/version indexes from both the old artifact index and new use
  manifests. Do not rewrite historical agent pages merely to change link style.
- Add explicit `ref.use: plan` to projects with plans sidecars; `ref.use: research`
  where the plugin is installed.
- Delete chezmoi's research xprompt sources **only after** clean-wheel
  resource-discovery smoke tests pass.
- Do not backfill historical sidecar backrefs speculatively. Start with newly published
  agents; offer an explicit audited backfill later.

### 11.3 Risks

| Risk                                                                                                                            | Severity | Mitigation                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Persisted `commit:`/`file:`/`chat:`/`bug:`/`agent:` strings in bead `refs:`, `consumption.jsonl`, prompt manifests, Patch files | **High** | Permanent parse aliases; never a hard rename. Add a `sase artifact doctor` normalization report.                                |
| Wire schema churn (v4→v5) + `sase-core-rs` release/roll                                                                         | High     | One Rust phase, one release; `tools/validate_sase_core_rs` already gates the binding.                                           |
| `use:` naming an uninstalled provider                                                                                           | High     | Fail soft + `sase doctor` finding, exactly like `config/file_hooks.py`. Never raise on launch.                                  |
| Linked-repo clone mistaken for plugin installation                                                                              | High     | Explicit install step + doctor check (§10.3).                                                                                   |
| Publication linking bytes the agent never read (HEAD drift)                                                                     | High     | Capture the revision at **resolution** time; never resolve HEAD at publication.                                                 |
| Cross-sidecar write-back deadlock or publication failure                                                                        | Medium   | Fixed lock order (artifact repos → agents); route backrefs through `publication_outbox`.                                        |
| Backref commits triggering user `file_hooks` / churning artifact versions                                                       | Medium   | `system_projection` cause excluded by default; managed block excluded from digests.                                             |
| ACE regression surface (keymaps, PNG snapshots, persisted subtab)                                                               | Medium   | Land last; stable number keys for fixed tabs; fall back on unknown persisted subtab.                                            |
| ACE latency from N artifact repos                                                                                               | Medium   | Lazy activation, shared off-thread loader, config-token-cached specs. Read `tui_perf.md`.                                       |
| `@file` allow-list leaking private files into a published sidecar                                                               | Medium   | Opt-in root-scoped allow-list; size cap; surface target visibility in launch preview; logical paths only in published metadata. |
| Numeric-label collision from dangling `[x][3]` uses                                                                             | Low      | Scan uses as well as definitions, outside literal zones (§1.2).                                                                 |
| `sase-research` vs `sase--research` confusion                                                                                   | Low      | Three-place disambiguation (§10.1).                                                                                             |

---

## 12. Phase plan

```text
1. core-ref-contract (sase-core, large)
   Versioned provider/entry/use wire types; safe formatter; quoted-argument grammar;
   typed property schema; stitch kind + permanent `commit` alias; patch kind/payload;
   bead short-id resolution; @file path payload; markdown_link_refs extraction
   (uses + literal zones); Referenced-By footer block. filter.rs untouched.
        │
2. retire-ref-xprompts (large) ── independent of 1; land in either order
   Delete §3.1. Builtins fall back to the pre-sase-ho rendering path.
        │
        ├──► 3. ref-provider-contract (large)
        │      sase_artifact hookspecs + two entry-point groups; spec validation;
        │      use:/inline merge + parity goldens; schema deltas; builtin `plan`
        │      provider; sase init writes ref.use: plan; doctor checks; fail-soft.
        │           │
        │           ├──► 7. sase-research plugin repo (medium)
        │           │      new repo, CI/wheel tests, docs; lift 4 xprompts out of
        │           │      chezmoi YAML + move research_swarm.md; link + install it;
        │           │      chezmoi keeps only `use:` + `command:`.
        │           │
        │           └──► 6. ace-artifacts-tabs (large)  ◄── also needs 4
        │
        ├──► 4. file-refs (large)
        │      allow-list config; capture/staging; SHA-256 object store; version
        │      promotion into the durable index at publication.
        │           │
        └───────────┴──► 5. publication-linking (medium)
                           per-occurrence ref-uses manifest; [@ref][N] reference-style
                           links; pinned permalinks; Referenced By write-back through
                           the outbox under the fixed lock order.
        │
8. remove-compatibility-shims (small, after the deprecation window)
   Drop `@plans` and `#ref/*` diagnostics. Keep schema readers forever.
```

Phase 2 is deliberately separate from 3 so the deletion reviews alone. Phase 5 must
follow 4 so backrefs have an authoritative source. Phase 6 lands last — it is the only
phase whose blast radius includes visual snapshots and keymaps.

Before phase 1, capture golden fixtures for all eight current refs, xprompt/literal-zone
interactions, completion, staging, old manifest parsing, and prompt publication —
marking each as _historical compatibility_ or _desired new behavior_.

**Essential tests beyond the per-phase suites:** quoted/escaped/fragment/punctuation
parsing; ambiguous short hash, Patch name, and bead suffix; missing-project and
cross-project resolution; spec version/collision/missing-install/override/inline-parity;
`@file` symlink escape, traversal, special files, size, unreadable,
changed-during-capture, duplicate-content; exactly-one-object-per-full-digest across
names, agents, months, and origins; captured-revision correctness when sidecar HEAD
advances before publication; dirty/untracked fallback; numeric-link allocation with
gaps, pre-existing definitions, same-target reuse, code fences, footnotes, and
repeat-run idempotence; backref idempotence, renamed artifact, concurrent update, push
failure/retry, and "does not run user file hooks"; dynamic tab union, project
enable/disable, provider removal, selection fallback, Files origin grouping and version
navigation; old-manifest/archive compatibility.

---

## 13. Alternatives considered and rejected

**Keep refs as xprompts, add frontmatter.** Preserves the category mistake. A ref is a
typed resolver, inventory, property schema, prompt projection, publication target, and
usage event; an xprompt is a prompt fragment. Rendering is the smallest part of the
contract, and it is the only part the xprompt framing could extend. It still needs
synthetic sources, and direct `#ref/*` invocation bypasses usage tracking.

**Layer providers on top of ref xprompts.** Two overlapping definition systems for one
concept, and the precedence table is already seven levels deep.

**Pure pluggy, matching `sase_vcs` / `sase_workspace` exactly.** Forces every provider
to ship Python for entirely declarable behavior (~300 lines instead of ~60 for research)
and makes config validation impossible without importing plugin code.

**Plugins implement arbitrary resolvers/renderers.** Rejected as the dispatch model —
see §2. Plugin code returns declarative specs once; the core executes.

**Resource-only plugins (`ref.yml` package data, like `sase_xprompts`).** Attractive —
no code import, trivially cacheable — but cannot express provider-supplied properties
for entry-backed refs. The declarative-spec-via-hook shape gets the benefits without the
ceiling.

**Pure config, no plugin hook.** Fails your stated goal of users defining and _sharing_
ref types, and the research file hook plus `#research*` xprompts need a distributable
home regardless.

**Split `@file` into `@file` (paths) + `@artifact` (digests).** Breaks every persisted
`file:` string and `sase artifact create`'s printed `ref:` line for no user-visible
gain; the scanner already anticipates the two-segment payload.

**Reuse `artifact_pool_filename` for the new store.** Keeps the basename duplication
vector and therefore cannot satisfy "exactly one location per unique contents" (§1.4).

**Store backrefs only in a central index or Git notes.** Avoids touching artifact
Markdown but does not deliver the portable visible table you asked for. The structured
index _plus_ generated managed block gets both.

**Synchronously atomic cross-repo publication.** Git offers no shared transaction;
simulating one makes agent publication fragile and still leaves partial pushes.

**A new global artifact database/graph.** Repeats a large subsystem SASE already built
and removed. Provider inventories, per-agent manifests, a digest object store, and
disposable revision-keyed indexes suffice until measured scale says otherwise.

**Put the ref registry in Python only.** Violates `CLAUDE.md`'s Rust-core boundary:
grammar, resolution, filtering, link numbering, and footer rendering are cross-frontend
behavior. Provider discovery, config merge, pluggy dispatch, and ACE presentation stay
in Python.

---

## 14. Open decisions for you

1. **`@chat` / `@bug` / `@agent`** — recommendation is to retain them as builtin
   providers (they satisfy the contract with no special-casing, `@agent` powers agent
   cross-links, and their strings are persisted). Removal is a data migration and should
   be its own phase. Your call.
2. **`@plans` → `@plan` deprecation length** — recommendation: one release with an
   actionable diagnostic, completion offering only `@plan` from day one.
3. **Dirty-sidecar policy** — recommendation: allow the use, snapshot exact bytes to the
   agents store, warn that no sidecar permalink is guaranteed, never link HEAD falsely.
   A strict per-project option can promote the warning to an error.
4. **Research ref globs** — adopting `["20*/**/*.md", "!20*/*/*__*.md"]` changes today's
   `**/*.md` behavior by excluding `__a`/`__b` sibling reports from completion.
   Recommended, but it is a visible change.
5. **Bugs / PRs tabs** — recommendation: keep them. Consolidation into Beads/Patches is
   a separate feature.

---

## Recommended solution

Do a **surgical replacement of the xprompt adapter, not a revert of `sase-ho`.** Delete
`loader_refs.py`, the packaged `refs/*.md` renderers, the `#ref/*` catalog surface, the
synthetic `sidecar_ref_config:` / `generated_sidecar_ref:` sources, and the seven-level
precedence table (~1,200–1,600 LOC) in a standalone phase. Keep the path-filter
contract, the `filtered` status, the document-root plumbing, and `sase-core-rs` v0.21.0.

Define a **versioned ref-provider contract in `sase-core`** with normalized descriptors,
entries, resolutions, typed properties, publication targets, and occurrence records.
Implement `@stitch`, `@patch`, `@bead`, and local-path `@file` directly in core as
builtin strategies; implement sidecar refs through one declarative document strategy.
Let installed plugins register **immutable specs** through two pluggy hooks on a
`sase_artifact` project — no per-resolution callbacks — and let project/home config
activate them with `ref.use:` plus validated field-level overrides that normalize to the
same spec as fully inline configuration. An unresolvable `use:` fails soft with a doctor
finding; it never breaks a launch.

Thread the project resolved from each **prompt segment's VCS xprompt** into late ref
processing as an explicit `PromptRefContext` — never infer it from `cwd`. At launch,
record every occurrence with its exact revision or SHA-256 snapshot in an immutable
per-agent `ref-uses` manifest. At publication, write each unique byte sequence to
exactly one full-digest path (`files/objects/sha256/ab/<64hex>`), and have the existing
Rust rewrite seam emit idempotent reference-style `[@ref:arg][N]` links using the
`commit_footer.rs` allocator — extended to scan numeric _uses_ as well as definitions,
outside literal zones. Use captured commit SHAs for sidecar permalinks. After the agents
commit is pushed, process `Referenced By` updates through the existing publication
outbox: one commit per sidecar repo, managed-marker block rendered from a structured
sidecar index, artifact-repos-before- agents lock order, excluded from digests and from
user file hooks.

Make ACE consume the same specs: one generic documents pane instantiated per configured
sidecar ref (`Plans`, `Research`, …), Bugs and PRs retained, `chats_*` and the old
`files_*` deleted, and Files rebuilt as one row per logical file with version toggling
and a visible origin badge covering both `@file` captures and `sase artifact create`
outputs. Land it last, behind lazy activation and config-token caching.

Finally, build `sase-org/sase-research` as a rigorously tested installable plugin owning
the `research` ref provider, the `research-highlights` file-hook provider, and the five
`#research*` xprompts — remembering that four of them live in chezmoi's `xprompts:` YAML
block, not as files, and that a linked-repo clone is **not** an installation. Fix the
`sase-research` / `sase--research` ambiguity in the GitHub description, the README, and
above all the `repos.linked[].description` that `sase memory init` renders into agent
memory. Leave Bryan's chezmoi config with exactly two lines: `use: research-highlights`
and `command: bob highlights create --include-id`.
