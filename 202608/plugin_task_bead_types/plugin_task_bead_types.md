---
create_time: 2026-08-17
updated_time: 2026-08-17
status: research
tags: [beads, plugins, task-types, project-config, agent-instructions]
---

# Plugin-Configurable Task Bead Types

**Research question:** How should SASE let plugins define new kinds of task beads
— with required structured fields, description templates, project-deterministic
agent instructions, and a project-local required-plugin list — without colliding
with the existing bead type system or making `sase memory init` depend on whatever
happens to be installed on the current machine?

**Scope:** `sase` at `88a840063`, `sase-core` at `49efcca`, `sase-github` at
`bcc4c4f`, `sase-research-artifacts` at its linked checkout. This is architecture
research, not an implementation plan. No runtime behavior was changed.

**Prior art in this tree.** Feature-flag research
([architecture](../feature_flag_architecture.md),
[lifecycle](../feature_flag_lifecycle_governance/feature_flag_lifecycle_governance.md),
[field guide](../feature_flag_field_guide/feature_flag_field_guide.md)) already
decided that flag removal is a first-class local bead, not a GitHub issue.
[Ref provider contract](../ref_provider_contract/ref_provider_contract.md)
already decided the plugin shape this design should copy: declarative JSON specs,
Rust validation, pluggy used only for registration.

---

## Bottom line

Build **task kinds**, not a second `type` field and not a fifth `issue_type`.

1. **Keep `issue_type` as the lifecycle family** (`plan` / `phase` / `task` /
   `flag`). Do not fold `flag` into a task kind. Flag beads cannot be `ready` or
   `snoozed`, cannot carry `+1`, use `FlagTriage` instead of `TaskTriage`, and
   are deliberately excluded from GitHub mirroring. That is a different object
   than a discovered-work task.

2. **Add a required-on-create `kind` on `issue_type=task` only.** Do not name
   the wire/CLI field `type`. `-T/--type`, `type:` filters, search field
   `type`, TUI chips, and mobile `bead_type` already mean `issue_type`. Call the
   new field `kind` in the store and `--kind` / `task(<kind>)` on the CLI.
   User-facing prose can still say "task type."

3. **Plugins register kinds with a declarative spec hook**, copied from
   artifact-ref / file-hook providers. Python discovers; Rust validates the spec
   and the field payload. Plugins do not get per-create callbacks on the write
   path.

4. **Project config lists required plugins.** `sase memory init`, `sase init`,
   `sase doctor`, workspace open, and agent launch resolve the kind catalog from
   **builtin kinds + kinds contributed by the project's required plugins** — not
   from whatever happens to be installed. Missing required plugins are a
   blocker with an install offer, not a silent catalog shrink.

5. **Do not extract flag beads to a `sase-flag-tasks` GitHub repo.** Keep flag
   as `issue_type=flag` in core. A later, separate epic can let plugins register
   *first-class issue types* (custom payload + custom gate). That is not v1.

6. **Do not add `IssueType.GITHUB`.** Mirrored GitHub issues are already
   `task` beads with `external_ref`. Give them `kind=github` whose *spec* lives
   in `sase-github`. The mirror stays in sase core.

The rest of this note is the evidence and the rejected alternatives.

---

## 1. What exists today

### 1.1 Beads already have a type

`IssueType` / `IssueTypeWire` is a closed enum: `plan`, `phase`, `task`, `flag`.
It is stored as `issue_type`, required on every bead, and immutable after
create. There is no `kind`, `category`, `labels`, or free-form metadata map.

| Family | Parent | Size | `ready` / `snooze` / `+1` | Extra payload | Gate |
| --- | --- | --- | --- | --- | --- |
| `plan` | optional | no | no | Patch metadata, `design`, `tier` | Plan approval |
| `phase` | required | yes | no | phase-slug description prefix | epic launch |
| `task` | forbidden | required on new create | yes | `external_ref`, `+1`, snooze | `TaskTriage` |
| `flag` | forbidden | optional in CLI; SQLite CHECK disagrees | **no** | `FlagRecord` (`key`, `remove_by_date`, `remove_by_release`) | `FlagTriage` |

The CLI already uses `-T/--type` for this family:

```
task
plan(<file>[,<parent>])
phase(<parent>)
flag(<key>,<YYYY-MM-DD>,<release>)
```

`sase bead list --type task`, ACE `type:`, and search field `type` all mean
`issue_type`. Presentation lives in `src/sase/bead_type_presentation.py`
(`▸ plan`, `↳ phase`, `◆ task`, `⚑ flag`).

**Implication.** "Task beads do not have a type field" is true only if "type"
means *subtype*. They already have `issue_type=task`. A new classification
must not reuse the name `type` on the wire or as `-T`.

### 1.2 Task beads are one bucket

`/sase_new_task` and `sase/memory/sase.md` tell agents to file every discovered
follow-up as a generic task:

- flaky or failing lint/test the agent did not cause
- stale memory / skill
- out-of-scope bug or tool improvement

There is no structured distinction among those. Duplicate detection searches
`--type task`. Semantic-duplicate policy is "same defect or same remediation,"
which can legitimately cross kinds (a flake that is actually a CI failure).

Epic phase workers still must not create beads; they write
`PROPOSED FOLLOW-UP:` notes. That rule is independent of kinds.

### 1.3 Flag is not a task

`sase flag new` creates `IssueType.FLAG` with an embedded `FlagRecord`. The
registry (`FeatureFlagDefinition`) owns `kind` (`beta`/`wip`/`sunset`/`ops`),
scope, default, description, and bead id. The bead owns only the removal
thresholds.

Flag-specific machinery that would break if flag became `task` + `kind=flag`:

- cannot be `ready` or `snoozed`; cannot carry `+1`
- `FlagTriage` (Remove launches a removal agent; Extend / Keep / Close) rather
  than `TaskTriage` (Launch / Close / Snooze)
- unique `external_ref` index **excludes** flags
- `external_issue_mirror` **skips** flags on purpose
- `tools/check_feature_flags` requires type `flag`, matching key, and errors
  if a closed bead's registry entry survives
- `sase flag new` is the create path, not `/sase_new_task`

Existing flag research is unanimous: a flag is a scheduled deletion with a
switch attached, keyed to a dedicated local bead. It must not become GitHub
issue noise.

There is also a small existing inconsistency: the Rust wire allows `size` on
flags (`sase flag new -z` works), but the SQLite CHECK only allows size on
`phase`/`task`. Any new field design should not repeat that split-brain.

### 1.4 GitHub issues are already mirrored as tasks

`external_issue_mirror` (AXE, 15-minute) and `sase bead sync-external` create
`task` beads, `size=small`, status `open` (never `ready`), with
`external_ref=bug:<project-key>#<n>` and a matching `bug:<display-name>#<n>`
ref. Upstream close/reopen updates the bead when safe.

The split of labor is already clean:

| Concern | Owner |
| --- | --- |
| Provider-neutral `IssueWire` (tracker issues) | sase `vcs_provider` |
| `gh issue *` | **sase-github** |
| Reconcile tracker ↔ beads | sase `external_mirror` |
| `external_ref` uniqueness / store | **sase-core** |

sase-github has no bead types and no issue-filing xprompt. The sase org
checkouts have no `.github/ISSUE_TEMPLATE`. ACE's issue editor is free-form
title + body + labels.

A bead with only a `bug:` ref is a human-owned reference. Only `external_ref`
is the mirror key.

### 1.5 Plugins are Python packages; there is no bead-type hook

Eight entry-point groups exist (`docs/plugins.md`):

| Group | Shape | Example |
| --- | --- | --- |
| `sase_artifact_refs` | pluggy class, declarative spec | builtin `plan`; `sase-research-artifacts` `research` |
| `sase_file_hooks` | pluggy class, declarative template | `research-highlights` |
| `sase_vcs` / `sase_workspace` | pluggy class, behavioral hooks | `sase-github` |
| `sase_llm` | pluggy class | grok, claude, … |
| `sase_xprompts` / `sase_config` | package resources | plugin xprompts and `default_config.yml` |
| `sase_plugin_manifest` | package metadata | diagnostics only |

There is **no** `plugins.enabled` or `plugins.required` in project config.
Install membership is the uv tool receipt (`sase plugin install`). Missing
providers fail lazily: `ref.use` without an EP is a doctor diagnostic;
`file_hooks.use` without a template raises at config load; a forced
`vcs_provider.provider: github` without the EP raises
`VCSProviderNotFoundError`.

`sase-core` has **no plugin loader**. It validates some plugin-produced JSON
(artifact-ref specs) and owns the closed bead-type enum / SQLite CHECKs.

Closest precedent for "plugin defines a new kind" is
`sase-research-artifacts`: a versioned JSON spec, unique `provider` +
`ref.kind`, Rust-validated, selected from project YAML via `ref.use`.

### 1.6 Agent instructions are project files, not plugin output

`sase memory init` renders `AGENTS.md` (and provider shims) from
`sase/memory/` notes plus packaged templates (`sase.md`, `sase_beads.md`,
`sase_sizes.md`). Linked-repo blurbs come from `repos.linked[].description`
in **project YAML**, not from installed entry points.

`/sase_new_task` is a chezmoi-global skill generated from
`src/sase/xprompts/skills/sase_new_task.md`. It is machine-global. It
must not list this project's kinds.

`sase skill init` *does* depend on installed LLM plugins (deploy targets).
That is the anti-pattern to avoid for task kinds.

`sase init` runs config → memory → repo → skills. Project management
requires `is_sase_managed: true` in the repo's own `sase/sase.yml`.

### 1.7 Store and migration patterns

Canonical state is the event store (`beads/events/**`). `issues.jsonl` is a
projection. `issue_created` embeds a full `IssueWire`. `issue_updated` is a
sparse field list that **cannot change `issue_type`**.

Serde does not `deny_unknown_fields`; unknown keys are dropped.

Two established patterns:

- **`size`:** optional on the wire, required only inside `create_issue` for
  new tasks. Legacy sizeless tasks still load. This is the right pattern for
  a new required-going-forward field.
- **`flag`:** new `IssueType` + embedded record required iff type is flag +
  SQLite rebuild. This is the right pattern for a new *lifecycle family*, not
  for a task subtype.

A true required field on every historical task `IssueCreated` would break
event replay unless defaulted.

---

## 2. External analogies (useful, not binding)

GitHub now ships the same three layers this design needs:

| GitHub (2024–2026) | Proposed SASE equivalent |
| --- | --- |
| Issue types (org-level: bug / task / feature) | Task `kind` |
| Issue fields (text / number / date / single-select; pinable per type) | Kind `fields` with `role: data` |
| Issue forms (YAML templates that fill the body) | Kind `template` rendered **below** description |

GitHub caps types at 25 and fields at 25. SASE does not need those caps, but
the split is the right one: classification, structured metadata, and a
create-time form are three things.

Linear/Jira custom issue types mix workflow with classification. SASE should
not: every task kind keeps the existing task lifecycle (`open` → `ready` →
`TaskTriage` → work / close / snooze). Kinds that need a different lifecycle
are issue types, not task kinds. That is why flag stays an issue type.

---

## 3. The decisions that actually matter

### 3.1 What is being typed?

Three designs were considered.

| Option | What a plugin registers | v1 cost | Verdict |
| --- | --- | --- | --- |
| **A. Task kinds only** | Subtype of `issue_type=task` | One new field + spec hook | **Do this** |
| **B. Collapse flag into task+kind** | Flag becomes a kind | Rewrite FlagTriage, status rules, lint, mirror exclusion | Reject |
| **C. Plugin-defined issue types** | New `issue_type` values with custom payload + gate | Open the SQLite CHECK, reducer, TUI, CLI | Later epic |

Option B looks like what the prompt asked for ("flag is a task type") and is
the wrong object model. Flag is a scheduled-deletion work item with a
dedicated gate that *launches a removal agent*. Giving it `ready` / `+1` /
`TaskTriage` would either flood triage or require per-kind gate overrides —
which is option C in disguise.

Option C is the honest extraction path for `sase-flag-tasks` as a *plugin that
owns `issue_type=flag`*. It is a multi-epic rewrite of core. Do not couple it
to v1.

### 3.2 What is the field named?

Call it **`kind`** on the wire and in Rust/Python.

Do not call it `type`. The collision list is not theoretical:

- CLI `-T/--type` = `issue_type`
- `sase bead list --type task`
- ACE / search `type:`
- `BeadTypeValue` / `bead_type` in TUI and mobile JSON
- memory text "Types, Tiers, And Launching"

User-facing docs and agent prose can say "task type" and "choose a kind."
Agents will type `task(bug)` or `--kind bug`. That is enough.

### 3.3 Required now vs required in history

Follow `size`:

- New task creates **require** `kind`.
- Stored field is `Option<String>` (or a newtype) so old `issue_created`
  events still reduce.
- Legacy tasks load as `kind=None` and present as `unspecified` / `legacy`.
- Doctor can offer a one-shot backfill to a builtin `general` kind later.
  Do not invent a historical rewrite in v1.

Do **not** put a closed SQLite `CHECK (kind IN (...))`. Plugin kinds are an
open set. Validate against the project's effective catalog at write time.

### 3.4 Where do specs live at validation time?

Rust cannot load Python plugins. Three ways to get specs into core:

| Approach | Deterministic? | Offline-safe? | Drift? |
| --- | --- | --- | --- |
| Python discovers plugins, passes spec into each `create`/`update` | Only if the caller uses the project catalog | No — missing plugin cannot create | Runtime |
| **Commit a generated catalog** (`sase/task_kinds.yml`) from required plugins | Yes | Yes — reads and creates use the snapshot | Regenerated by `sase memory init` / `sase init` |
| Hard-code builtin kinds in Rust; plugins only add display | Partial | Yes for builtins | Plugins cannot add fields |

**Recommend the generated catalog (plus builtins compiled into core).**

- Builtins (`bug`, `feature`, `memory`, `flake`, `ci`) ship in sase-core so a
  project with no required plugins still has a complete task-kind system.
- Required plugins' specs are snapshotted into project-local
  `sase/task_kinds.yml` (or a `task_kinds:` block in `sase/sase.yml`) when
  `sase init` / `sase memory init` runs.
- Rust validates creates against that snapshot + builtins.
- Existing beads with an unknown kind still **read**. Creates of an unknown
  kind fail.
- Extra plugins installed on the machine but not required by the project do
  **not** appear in the snapshot and cannot be used to create beads in that
  project.

This is the same idea as a lockfile, but for schemas, and it is what makes
agent instructions deterministic.

A lighter v1 is "no snapshot, Python passes specs on each write." That works
until a second frontend (web, editor) needs to create typed tasks without
Python plugin discovery. The snapshot is the rust-core-boundary-correct
choice. Ship the snapshot in the same epic as required plugins.

### 3.5 Data fields vs templates

The prompt asks for both:

- **Data** — queryable, like a flag's `remove_by_date`
- **Template** — rendered below the description, like a GitHub issue form

Do **not** bake the template into `description`. Agents and `update
--description` would overwrite it. Store structured fields; render the
template at display time (CLI show, TUI detail, TaskTriage preview, bead
pages).

Proposed field roles on the spec:

```yaml
fields:
  - name: node_id
    type: string          # string | text | date | enum | ref | uint
    role: [data, template]
    required: true
    description: Pytest node id
  - name: soak
    type: text
    role: [template]
    required: false
template: |
  ## Node
  `{{ node_id }}`

  ## Soak
  {{ soak }}
```

`role: data` fields are filterable (`kind:flake node_id:tests/foo.py::test_bar`)
and shown in compact rows. `role: template` fields exist to fill the body
block. Most useful fields are both.

Storage on `IssueWire`:

```text
kind: Option<String>                    # required on new task create
fields: BTreeMap<String, JsonValue>     # empty if none; validated vs spec
```

Do not add a new Rust struct per kind. Flag's dedicated `BeadFlagWire` stays
on `issue_type=flag`. Task-kind payloads are a generic map so plugins can
evolve fields without a core release.

Missing plugin at read time: dump `fields` as a definition list under the
description. Do not fail the load.

### 3.6 CLI grammar

CLI rules say options must not be required; required values are positionals.
`-T` is already an effectively-required option (pre-existing). Do not add a
second required option `--kind`.

Extend the existing `-T` grammar:

```
-T task(<kind>)
-T task(<kind>,k=v,k=v)
```

Examples:

```bash
sase bead create -T 'task(bug)' -t "…" -d "…" -z large
sase bead create -T 'task(flake,node_id=tests/foo.py::test_bar)' -t "…" -z medium
sase bead create -T 'task(memory,path=sase/memory/sase_beads.md)' -t "…" -z small
```

Bare `-T task` becomes an error on new creates ("kind required; try
`task(bug)`"). `--field key=value` is an optional repeatable modifier for
fields that are awkward inside parentheses.

`sase bead type` is already taken by `--type`. Add:

```
sase bead kind list
sase bead kind show <kind>
```

(or `sase task-kind list` if you want a new group). Default-list convention
applies if this becomes a group.

### 3.7 Duplicate detection and triage

`/sase_new_task` should:

1. Search existing tasks **of the same kind first**, then all tasks.
2. Still apply the semantic-duplicate test across kinds. A `ci` and a `flake`
   can be the same failure.
3. Still check in-progress epics.

`TaskTriage` stays one gate for every task kind. Kind and rendered template
appear in the preview. Do not let v1 kinds register custom gates.

`+1` / snooze / ready rules stay task-wide. A kind must not opt out of them.
If it needs to, it is an issue type (option C), not a kind.

### 3.8 Agent instructions

**Never generate AGENTS.md or the global skill from "all installed plugins."**

| Surface | What it contains | Source of truth |
| --- | --- | --- |
| `/sase_new_task` (chezmoi-global) | Workflow only: evidence, search, +1, epic note, then "choose a kind from this project's catalog" | Skill template |
| Generated `sase/memory/sase_task_kinds.md` | This project's kinds, when to use each, create examples, required fields | `sase memory init` from builtins + required plugins |
| Short-term `sase.md` bullets | Point at the kinds note and `/sase_new_task` | Existing generated short memory |
| `sase bead kind list` | Runtime catalog (same snapshot) | Project snapshot + builtins |

`sase memory init` is already the place that writes project-deterministic
agent docs from project YAML (linked-repo list). Adding a generated long note
for kinds is the same mechanism.

If a required plugin is missing, memory init is a **blocker**, not a
best-effort catalog. That is what makes two machines produce the same
`AGENTS.md`.

---

## 4. Required plugins

### 4.1 Why this is a config field, not a feature flag

Feature-flag memory: a flag is a temporary route. Users are meant to choose
required plugins forever, per project. That is an ordinary config field.

### 4.2 Proposed project-local schema

In the repo's own `sase/sase.yml` only (same authorization rule as
`is_sase_managed`):

```yaml
plugins:
  required:
    - name: sase-github
      # optional; omit to mean "any installed version"
      version: ">=0.2.0"
    - name: sase-research-artifacts
```

`name` matches the catalog / distribution name (`sase-github`, not the
ProjectSpec key). This is **not** `repos.linked`. Linked repos are source
checkouts. Required plugins are **runtime packages in the sase environment**.

A project can have a linked checkout of sase-github and still fail the
required-plugin check if the uv tool install does not include `sase-github`.

### 4.3 When to check

| Moment | Severity | UX |
| --- | --- | --- |
| `sase init` / `sase memory init` | blocker | cannot generate the kind catalog |
| `sase doctor` | ERROR | `plugins.required` check |
| Workspace open / `#gh:` / agent launch into the project | warning → gate | offer `sase plugin install …` |
| `sase bead create -T 'task(<plugin-kind>)'` | error | name the missing plugin |

Offer install through the existing catalog path (`sase plugin install
<name>` / ACE Updates tab). Do not invent a second installer.

A missing plugin should present:

1. which plugins are required
2. which are missing (and version mismatch, if pinned)
3. the exact install command
4. in interactive contexts, a confirmation to run it

Non-interactive / agent contexts: fail closed with the install command. Do
not auto-install from an agent without a gate.

### 4.4 What required plugins are *for*

Required plugins contribute:

- task-kind specs (this design)
- anything else the project already depends on (`#gh`, `@research`,
  `ref.use`, file-hook `use:`)

They are not a general "enable this plugin for this project" switch for
behavior that should stay user-global (LLM providers, telegram). Keep the
field's meaning "this project will not work correctly without these
packages."

---

## 5. Recommended hook

Copy the artifact-provider shape. New entry-point group:

```toml
[project.entry-points."sase_task_kinds"]
github = "sase_github.task_kinds:GitHubTaskKinds"
```

```python
class TaskKindHookSpec:
    @hookspec
    def task_kind_specs(self) -> Iterable[Mapping[str, Any]] | None:
        """Return declarative task-kind specs."""
```

Spec sketch (schema_version 1):

```json
{
  "schema_version": 1,
  "kind": "github",
  "label": "GitHub",
  "description": "Task bead synced with an external GitHub issue.",
  "when_to_use": "Only for beads whose source of truth is a GitHub issue.",
  "provider": "sase-github",
  "fields": [
    {
      "name": "issue_number",
      "type": "uint",
      "role": ["data"],
      "required": false,
      "description": "Repository-local issue number. Prefer external_ref."
    }
  ],
  "template": "",
  "presentation": { "glyph": "⌥", "accent": "#58A6FF" },
  "create": {
    "default_size": "small",
    "default_status": "open",
    "skip_triage": true
  }
}
```

`create.skip_triage` / `default_status: open` is how the GitHub mirror keeps
today's "never flood TaskTriage" behavior without a new issue type.

Rules:

- Kind ids are `snake_case`, unique across builtins + required plugins.
- Reserved: do not allow kinds named `plan`, `phase`, `task`, `flag`, `type`.
- Duplicate kind ids: later plugin loses; doctor ERROR.
- Plugins return specs only. No `on_create` / `on_show` Python callbacks on
  the bead write/read path. Sync behavior stays in `external_mirror` and
  sase-github VCS hooks.
- Rust validates the spec (digest, like artifact providers) and validates
  field values on create/update.

Builtin kinds are registered through the same spec type, from a host path
inside sase, so they do not depend on an extra package.

---

## 6. Candidate kinds

| Kind | Location | Fields (v1) | Notes |
| --- | --- | --- | --- |
| `bug` | **builtin** | `location` (path/symbol), `repro` (template) | Agent-found defect while doing other work. Not an external tracker bug. |
| `feature` | **builtin** | `why_now` (template), `out_of_scope_of` (optional bead ref) | Recommended improvement, explicitly out of current work. |
| `memory` | **builtin** | `path` (required, `sase/memory/…` or skill name), `proposed_change` (template) | Close ritual stays "user permission + `sase memory init`." |
| `flake` | **builtin** | `node_id` (required), `repro_cmd`, `fail_rate`, `last_green` | Distinguishes contention/intermittent from a true fail. |
| `ci` | **builtin** | `node_id` / job, `sha`, `log_ref` | Confirmed deterministic failure. User left LOCATION blank; it belongs next to `flake`. |
| `github` | **sase-github** | none required beyond existing `external_ref` | Spec + presentation + "when to use" live in the plugin. Mirror sets `kind=github`. |
| `flag` | **do not add as a kind** | — | Keep `issue_type=flag`. See §7. |

`general` / `unspecified` is a **legacy presentation label**, not a kind
agents may choose. New creates must pick a real kind.

### 6.1 Why `ci` is builtin

The prompt did not give `ci` a LOCATION. It is the complement of `flake`,
used by the same agents on the same test/lint path, with no plugin
dependency. Putting it in a plugin would make the sase project's own
instructions require that plugin. Builtin.

### 6.2 Why `github` belongs in sase-github

The *operations* already live there (`vcs_list_issues`, create/edit/close).
The *identity* already lives in core (`external_ref`). The *kind spec*
(label, when-to-use, presentation, default create policy) is the only new
piece, and it should travel with the plugin that implements the tracker.

Do **not** move `external_mirror` into sase-github. The chop is multi-project
hygiene and already talks to VCS plugins through a provider-neutral
`IssueWire`. If another host (GitLab, …) appears, it registers its own kind
and the mirror looks up "the kind that claims this provider."

Until a second host exists, hardcoding `kind=github` when the VCS plugin
name is `github` is fine.

A project that does not require `sase-github` does not get the `github` kind
in its catalog. Its mirror, if somehow enabled, should refuse or fall back to
a builtin `external` kind. Prefer refuse: a GitHub-hosted SASE project that
mirrors issues should list `sase-github` as required.

### 6.3 Suggested builtin field sets (minimum)

These are starting schemas, not a freeze.

**`bug`**

- `location` (string, required, data+template) — file, symbol, or command
- `repro` (text, required, template)
- `impact` (text, optional, template)

**`feature`**

- `proposal` (text, required, template)
- `why_out_of_scope` (text, required, template)

**`memory`**

- `path` (string, required, data+template)
- `proposed_change` (text, required, template)

**`flake`**

- `node_id` (string, required, data+template)
- `repro_cmd` (string, optional, data+template)
- `evidence` (text, required, template) — fail rate, soak, serial vs parallel

**`ci`**

- `node_id` (string, required, data+template)
- `sha` (string, optional, data)
- `why_not_flake` (text, required, template)

Keep field counts small. GitHub's lesson is that unused fields rot. Kinds
can grow fields additively; removing a required field is a spec major
version.

---

## 7. Flag extraction

The prompt proposes `sase-flag-tasks` as a GitHub repo that owns the flag
task type. That conflicts with three already-settled decisions:

1. Flag is `issue_type=flag`, not a task (`sase-core` validation, FlagTriage,
   lint).
2. Flag beads must not be mirrored to GitHub (`docs/beads.md`).
3. Flag research: the scarce resource is *deletion*, enforced by a local
   bead + gate + lint. A GitHub repo cannot replace that loop.

**Recommendation:** do not create `sase-flag-tasks` for v1, and do not model
flag as a task kind.

If flag ownership should leave the sase repo later, the honest design is
option C: a plugin that registers a first-class issue type with a typed
payload (`BeadFlagWire`), a custom gate (`FlagTriage`), and create CLI
(`sase flag new`). That plugin would still write into the **project's** bead
store, not into a separate GitHub issues repo. The registry
(`FeatureFlagDefinition`) would stay in the SASE source tree or move with
the plugin as code, not as issues.

That extraction is a follow-up epic after task kinds have proven the spec
hook. It is not a reason to weaken FlagTriage now.

---

## 8. Surfaces that must learn `kind`

Anything that creates, lists, or shows a task:

| Surface | Change |
| --- | --- |
| `sase bead create` | `-T task(<kind>)`; reject bare `task` |
| ACE bead create modal | kind picker from project catalog |
| `external_issue_mirror` | set `kind=github` (or refuse if kind missing) |
| `sase bead list` / `search` / ACE `kind:` | filter + column |
| `sase bead show` / TUI detail / bead pages | kind chip + rendered template below description |
| TaskTriage preview | kind + fields |
| `/sase_new_task` | choose kind; search same kind first |
| Generated `sase_task_kinds.md` | catalog |
| Compact CLI glyph | keep `◆` for task; add a small kind label, do not invent 20 glyphs |
| JSON / mobile | add `kind` and `fields`; keep `bead_type` = `issue_type` |

Do not overload ACE `type:` or `label:` (`label:` is GitHub issue labels).

---

## 9. Rust-core boundary

Shared behavior a web app or editor would need to match the TUI:

- `kind` + `fields` on the wire
- create-time requirement
- spec validation
- template rendering from fields (pure)
- catalog snapshot schema

Stays in Python:

- plugin discovery (`sase_task_kinds` entry points)
- `sase plugin install` / required-plugin doctor
- `sase memory init` catalog generation
- ACE pickers, gates, chops

This matches Config Center and artifact-ref providers: Python finds files and
plugins; Rust owns the validated record.

Rollout order: sase-core wire + validation first, then Python callers. Same
as every prior bead field.

---

## 10. Rejected alternatives

**Name the field `type`.** Collides with `-T`, filters, and `issue_type`.
Agents will generate `sase bead create -T bug` and it will fail or, worse,
be parsed as an invalid issue type.

**Make `-T bug` imply `issue_type=task, kind=bug`.** Tempting UX, but it
collapses two axes into one token. `flag` would look like a kind. Bare
`task` disappears. Completions become ambiguous. Keep `-T` for the family
and put kind in `task(<kind>)`.

**Free-form `metadata` JSON with no spec.** Fights the flag/snooze design
("no flat field can drift") and gives agents nothing to be instructed on.

**New `IssueType` per kind.** SQLite CHECKs, TUI chips, and lifecycle rules
are closed for a reason. Kinds share the task lifecycle.

**Generate the global `/sase_new_task` skill from installed plugins.**
Chezmoi skills are machine-global. Two projects on one machine would fight.
The skill stays generic; the project memory note is the catalog.

**Generate AGENTS.md from whatever is installed.** The prompt already
identifies this as the bug. Required plugins + snapshot fix it.

**Custom per-kind gates in v1.** That is option C. `create.skip_triage` for
mirrored GitHub issues is the only policy knob v1 needs.

**Issue-form YAML stored in `description`.** Unqueryable; agents overwrite
it; TUI cannot filter on `node_id`.

**Put github kind in core.** Then uninstalling sase-github leaves a core
kind whose operations do not exist. Spec lives with the plugin.

---

## 11. Recommended solution (concrete)

### v1 — one epic, two repos

**sase-core**

- Add `kind: Option<String>` and `fields: BTreeMap<String, JsonValue>` to
  `IssueWire`.
- Validate: if `issue_type != task`, both must be empty; if task and this is
  `create_issue`, `kind` is required and must exist in the supplied catalog;
  `fields` must satisfy that kind's spec.
- Add `kind` / `fields` to create request and update-event fields (kind
  mutable — misfiles happen; log the change in history).
- Load project catalog snapshot when present; always include compiled-in
  builtins.
- Template render function: spec + fields → markdown.

**sase**

- New `sase_task_kinds` hook + builtin specs for `bug`, `feature`, `memory`,
  `flake`, `ci`.
- Project schema `plugins.required[]` (`name`, optional `version`).
- `sase init` / `sase memory init` / `sase doctor` / workspace open: missing
  required plugins → blocker + install offer.
- Generate `sase/task_kinds.yml` (snapshot) and
  `sase/memory/sase_task_kinds.md` (agent catalog) from builtins + required
  plugins.
- CLI: `-T task(<kind>[,k=v…])`; `sase bead kind list|show`.
- `/sase_new_task` + `sase_beads.md` template: require a kind; do not list
  machine-specific kinds.
- Mirror: set `kind=github` when that kind is in the catalog.
- TUI/CLI/gates/pages: show kind + rendered template below description.

**sase-github**

- Register `kind=github` (presentation + `create.default_status=open` +
  `skip_triage`).
- No store changes. No new issue type.

**sase project `sase/sase.yml` (this repo)**

```yaml
plugins:
  required:
    - name: sase-github
    - name: sase-research-artifacts
```

(`sase-github` for `#gh` and `kind=github`; `sase-research-artifacts` is
already implied by `ref.use: research` — listing it makes init fail closed
instead of doctor-only.)

### v1 non-goals

- Extracting flag to a plugin or GitHub repo
- Plugin-defined issue types or custom gates
- Per-kind duplicate policy
- Historical rewrite of existing task events
- GitHub issue-form files in `.github/ISSUE_TEMPLATE`

### v2 (only after v1 is in use)

- Backfill tool: classify legacy `kind=None` tasks
- Optional `sase_issue_types` hook if flag (or something like it) truly
  leaves core
- Second host's external kind (`gitlab`, …) selected by VCS plugin name
- Kind-specific ACE filters saved as query profiles

---

## 12. Suggested create examples (what agents should type)

```bash
# Bug found while doing other work
sase bead create -T 'task(bug,location=src/sase/bead/cli_crud_create.py)' \
  -t "parse_type_arg treats unknown kinds as phase" \
  -d "…" -z large --ref file:…

# Flake
sase bead create -T 'task(flake,node_id=tests/test_foo.py::test_bar)' \
  -t "test_bar failed 3/20 under xdist" -z medium

# Memory update
sase bead create -T 'task(memory,path=sase/memory/sase_beads.md)' \
  -t "sase_beads.md still says -T task with no kind" -z small

# GitHub-mirrored issue (normally created by the chop, not by hand)
sase bead create -T 'task(github)' -t "…" -z small --external-ref 'bug:sase#42'
```

`/sase_new_task` still runs first. Kind is chosen in step 7, not instead of
the duplicate/epic sweep.

---

## 13. Risks

| Risk | Mitigation |
| --- | --- |
| Agents keep typing `-T task` | Hard error with the `task(<kind>)` hint; skill + generated kinds note |
| Catalog snapshot drifts from plugin | `sase memory init --check` / doctor compares digest to installed required plugins |
| Two plugins claim `bug` | First-wins + doctor ERROR; builtins reserved |
| Mirror creates tasks before github kind exists | Gate mirror on catalog membership; sase project requires sase-github |
| `fields` become a junk drawer | Small builtin schemas; required fields are few; template is display-only |
| Flag gets "kind-ified" in review | §7; keep the issue-type split in the plan's non-goals |
| SQLite CHECK temptation | Open `TEXT` column; validate in Rust, not SQL IN-lists |

---

## 14. Answer key (the original questions)

| Question | Answer |
| --- | --- |
| How do plugins define new task types? | Declarative `sase_task_kinds` specs, same shape as artifact-ref providers. |
| Add a required `type` field? | Add required-on-create **`kind`**. Do not name it `type`. |
| How do we update agent instructions? | Global skill stays generic. Project-generated `sase_task_kinds.md` lists this project's kinds. |
| Instructions depend on installed plugins? | No. They depend on **required** plugins + builtins, snapshotted at init. |
| Project-required plugins? | `plugins.required` in project `sase/sase.yml`. Missing → blocker + install offer. |
| Data fields vs templates? | Structured `fields` map + display template rendered below `description`. |
| `bug` / `feature` / `memory` / `flake`? | Builtin. |
| `ci`? | Builtin (LOCATION was unspecified; it pairs with `flake`). |
| `flag` in `sase-flag-tasks`? | **No.** Keep `issue_type=flag` in core. |
| `github` in sase-github? | **Yes, as a kind spec.** Store stays `task` + `external_ref`. Mirror stays in core. |

That is the implementation shape I would start from.
