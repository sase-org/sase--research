---
create_time: 2026-08-17
updated_time: 2026-08-17
status: research
---

# Plugin-Extensible Task Bead Types

**Research question:** What is the best way to give SASE task beads a required `type`
field whose catalog is extensible through plugins, while keeping generated agent
instructions deterministic per *project* rather than per *machine*?

**Scope:** `sase` at `88a840063` (0.16.0), `sase-core` at `49efcca`. This is
architecture research, not an implementation plan; no runtime behavior was changed.

## Bottom line

Add a **second, orthogonal axis** to the bead model — `task_type` — instead of widening
the existing `IssueType` enum. Populate its catalog from a **declarative registry** fed
by three sources with provenance (builtin → plugin pluggy hook → project config),
exactly mirroring `sase.artifact_providers`. Store type-specific data as a **generic
string map on the wire**, not a typed struct, so a bead authored on a machine with a
plugin stays readable on a machine without it. Make the store **accept any well-formed
slug** and enforce the catalog only at *creation* time in the host.

Solve determinism with a **committed snapshot**, not with "whatever is installed":
`sase memory init` writes a lockfile-shaped `sase/task_types.lock.json`, generated
agent instructions render from that lock, and a new `plugins.required` config field
makes a missing plugin an actionable error rather than silent drift. This is required,
not optional: `just check` already runs `sase validate` → `sase init memory --check`,
so a machine-dependent AGENTS.md would break the build for whoever has the "wrong"
plugin set.

Ship `bug`, `feature`, `memory`, `flake`, and `ci` as builtins; ship `github` from
`sase-github`. **Do not migrate `flag` in the first change** — flag beads are a distinct
`IssueType` with a different lifecycle today, and folding them in requires a per-type
triage-policy hook that should be proven on cheaper types first.

---

## 1. What exists today

### 1.1 `IssueType` is a closed enum in two languages

`src/sase/bead/model.py:20` defines `IssueType = {plan, phase, task, flag}`, mirrored by
`IssueTypeWire` at `crates/sase_core/src/bead/wire.rs:25`. The enum is not a label — it
is the carrier of nearly every structural invariant in the model:

| Invariant | Enforced at |
| --- | --- |
| phase needs `parent_id`; task/flag must not have one | `model.py:310-321`, `_db_schema.py:45-52` |
| only `plan` carries `tier`, `is_ready_to_work`, Patch metadata | `model.py:312-341` |
| only `task` carries `+1` evidence, `ready`, `snoozed` | `model.py:322-345`, `_db_schema.py:57-58` |
| `flag` ⇔ `FlagRecord` present | `model.py:352-355`, `_db_schema.py:60` |

The SQLite `CHECK(issue_type IN ('plan','phase','task','flag'))` is duplicated in Rust at
`crates/sase_core/src/bead/schema.rs:11`. `IssueTypeWire` appears **245 times** across
`sase-core`; `IssueType` appears in **56 Python modules**.

**Consequence:** making `IssueType` open is not a refactor, it is a rewrite — and it
cannot work anyway, because a compiled Rust enum can never learn a slug a Python plugin
invented at runtime.

### 1.2 `flag` is already the proof-of-concept for a typed bead

The `flag` bead is what the user is asking for, hard-coded once:

- a required typed payload (`FlagRecord{key, remove_by_date, remove_by_release}`,
  `model.py:180`, `wire.rs:426`);
- a dedicated creator that collects those fields (`sase flag new`,
  `src/sase/feature_flags/cli_new.py`);
- a dedicated gate with due-date semantics (`FlagTriage`, `src/sase/bead/flag_gate.py`,
  `flag_due.py`);
- dedicated presentation (`⚑`, `#FF875F` — `src/sase/bead_type_presentation.py:56`);
- a CLI type grammar that already takes arguments:
  `-T "flag(<key>,<YYYY-MM-DD>,<release>)"` (`cli_crud_create.py:51,80`).

Generalizing this one shape is the whole feature. The `-T "type(args)"` grammar in
particular is a gift — see §5.4.

### 1.3 The plugin substrate is mature, and one subsystem is the right template

Entry-point groups are enumerated at `src/sase/plugins/inventory.py:17`:
`sase_artifact_refs`, `sase_config`, `sase_file_hooks`, `sase_llm`,
`sase_plugin_manifest`, `sase_vcs`, `sase_workspace`, `sase_xprompts`. `pluggy` is a hard
dependency (`pyproject.toml:41`) and already backs four hookspecs: artifact providers,
workspace providers, LLM providers, VCS providers.

**`sase.artifact_providers` is the model to copy.** It is the newest and the only one
built for *declarative* contributions rather than provider classes:

- the hook returns plain `Mapping[str, Any]` specs, not objects
  (`_hookspec.py:19-30`);
- discovery collects builtin specs and plugin specs into one candidate list with
  `ArtifactProviderProvenance` (group, name, package, version, builtin)
  (`_discovery.py:47-105`);
- validation is centralized, emits structured `ArtifactProviderDiagnostic`s, and drops
  duplicates by both id and kind with distinct codes (`duplicate_ref_provider`,
  `duplicate_ref_kind` — `_validation.py:68-88`);
- specs get a **stable digest computed in Rust**
  (`artifact_ref_provider_spec_digest`, `_validation.py:25-29`);
- `FileHookProviderRecord` already carries exactly the shape this feature needs:
  `template` + `required_fields` (`_models.py:59-64`).

That last point matters: "a set of fields, some data and some forming a template that
renders below the description" is a shape SASE has already designed, validated, and
shipped once.

### 1.4 Agent instructions are generated, committed, and drift-checked

`sase/memory/*.md` → `AGENTS.md` + provider shims via `sase memory init`
(`src/sase/amd/_memory.py`, templates in `src/sase/main/init_memory/templates/`).

Two facts dominate the design:

1. **The output is committed and gated.** `just check` → `sase validate` →
   `("init", "memory", "--check")` (`src/sase/main/validate_handler.py:33`). Generated
   instruction files are in the repo (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, …).
2. **Non-determinism here is a known, already-painful failure mode.**
   `src/sase/main/init_memory/staleness.py` exists solely to warn that "a foreign sase
   build can silently answer a memory-drift check with different generator templates."

So: if the task-type list feeds AGENTS.md and is read from the live plugin environment,
then every machine with a different plugin set fails `just check` with a diff it did not
cause. **The user's instinct about required plugins is not a nice-to-have; it is the
thing that makes the feature safe.** §6 goes further and argues a lock file is needed on
top of it.

There is already a precedent for config-derived dynamic content in generated
instructions: the glossary. `sase memory init` reads `memory.glossary` from project
config, validates it through Rust, and renders a `**GLOSSARY TERMS:**` paragraph into
Tier 2 (`_memory.py:287-294`, `main/init_memory/glossary.py`). Crucially it renders only
*term names plus aliases* and tells the agent to run `sase glossary read <term>` for the
body. That two-level split is directly reusable (§6.3).

### 1.5 The existing instruction text already implies the taxonomy

`sase/memory/sase.md` → "File Discovered Work As Task Beads" lists three bullets that map
one-to-one onto the proposed types:

| Existing bullet | Proposed type |
| --- | --- |
| "a linter or test is flaky or failing and you did not cause it" | `flake` / `ci` |
| "a sase memory file or skill contains out-of-date information" | `memory` |
| "a tool… has a bug or a clear, objective improvement" | `bug` / `feature` |

The rewrite is a table, not a new concept. This is a good sign the taxonomy is real.

### 1.6 Adjacent machinery that already half-exists

- **GitHub sync:** `Issue.external_ref` is a core field, `src/sase/external_mirror/`
  runs the reconciliation, `bug_links.py` normalizes `bug:<project>/<id>`. A `github`
  task type mostly *labels* something that already works.
- **Triage:** `task_triage_policy.py` has one global `bead.task_triage.min_plus_ones`
  threshold for every task bead. Typing tasks is what makes a per-type threshold
  expressible — see §7.

---

## 2. Where the type should live

| Option | Verdict |
| --- | --- |
| **A1.** Widen `IssueType` to include `bug`, `feature`, … | **Reject.** 245 Rust sites, a compiled enum plugins can never extend, and it destroys the invariant table in §1.1 (is a `bug` allowed a `parent_id`? does it get `ready`?). |
| **A2.** Free-form string `issue_type` | **Reject.** Same invariant loss, plus every one of the 56 Python modules and the SQL CHECKs lose their guarantee. |
| **A3.** New orthogonal field `task_type`, valid only when `issue_type == task` | **Recommend.** `IssueType` keeps meaning "structural kind"; `task_type` means "what flavor of discovered work". Additive migration, no invariant loss. |

Under A3 the model constraint is a two-line addition next to the existing flag rule:

```python
if self.issue_type != IssueType.TASK and self.task_type:
    raise ValueError("Only task issues can carry a task type")
```

and one SQL CHECK, `CHECK(task_type IS NULL OR issue_type = 'task')`, added by an
`ALTER TABLE` migration (the cheap kind — see `_db_migrations.py:87` for the
`close_history` precedent, versus the table-rebuild at `_db_migrations.py:206`).

### 2.1 The forward-compatibility rule that must not be violated

`IssueWire.issue_type: IssueTypeWire` is a plain serde enum with no `#[serde(other)]`
fallback (`wire.rs:571`). An unknown value is a **hard deserialization failure**, not a
degraded read.

Bead stores are git-synced sidecars shared across machines (`beads/events/**` is
canonical). A bead created on a laptop with `sase-github` installed *will* be read on a
machine without it.

**Therefore:**

- `task_type` must be `Option<String>` / `String` on the wire, never an enum;
- `sase-core` must validate only the *shape* of the slug (non-empty, kebab/snake,
  bounded length) and never a membership list;
- the catalog check belongs in the host, and applies **only on create/update**, never on
  read.

This is the same division already used for artifact-ref provider specs: Rust validates
and digests a spec whose *content* it does not enumerate (`_validation.py:24-29`).

---

## 3. How a type declares its fields

### 3.1 The spec shape

Follow `FileHookProviderRecord` (`template` + `required_fields`). A declarative spec,
identical whether it comes from a plugin hook or project config:

```yaml
task_type: flake
label: Flaky test
summary: A test that passes and fails without a code change.
glyph: "≈"
accent_color: "#5FD7AF"
when_to_use: >-
  Use when a test failed and a rerun on the same tree passed.
fields:
  - name: test_id
    label: Test node ID
    kind: text
    required: true
    help: The pytest node ID, e.g. tests/foo.py::test_bar
  - name: failure_rate
    kind: text
    required: false
  - name: first_seen
    kind: date
    required: true
body_template: |
  ## Flake report

  - **Test:** {{ test_id }}
  - **First seen:** {{ first_seen }}
  {% if failure_rate %}- **Observed rate:** {{ failure_rate }}{% endif %}
```

This covers both halves of the user's requirement in one mechanism: `fields` are the
data (a `flag` type's `remove_by_date`), and `body_template` is the GitHub-issue-template
half. `flag`'s current hard-coded `FlagRecord` is expressible as a three-field spec with
no `body_template`, which is a useful sanity check on the design.

Jinja2 with `StrictUndefined` is already the house template engine
(`src/sase/mdtemplates.py:13`), so `body_template` needs no new dependency and gets
existing "missing variable is an error" behavior.

### 3.2 How field values are stored

| Option | Assessment |
| --- | --- |
| **D1.** Render at create time, append to `description`, keep nothing | Simplest, degrades perfectly. But the data is unqueryable, the template can never be corrected retroactively, and `sase bead update` cannot fix one field. |
| **D2.** Store `task_type_fields: BTreeMap<String,String>`, render at display time | **Recommend.** Queryable (`sase bead list --type task --task-type flake --field test_id=...`), re-renderable, editable per field. |
| **D3.** Typed per-type structs like `FlagRecord` | Impossible for plugin types — Rust cannot know the struct. |

D2's degradation story: when a bead's `task_type` has no registry entry (plugin absent),
`sase bead show` renders the raw key/value pairs under a `Task type: github (unknown to
this machine)` header instead of the template. The agent still reads every fact; only the
prose formatting is lost. Rendering at display also means `sase bead show` output on any
machine is a pure function of (stored payload, installed spec), which is the honest
model.

One nuance worth deciding explicitly: **`description` stays the human/agent free-text
field.** The rendered template appends *below* it, as the user described, and is never
merged into it. Otherwise `sase bead update -d` would silently destroy typed data.

---

## 4. Where the catalog comes from

### 4.1 Three sources, one registry

```
builtin specs (sase)  ─┐
plugin hook specs     ─┼─→ validate + dedupe + provenance ─→ TaskTypeRegistry
project config specs  ─┘         (+ diagnostics)
```

| Source | Mechanism | For |
| --- | --- | --- |
| Builtin | a `BuiltinTaskTypes` class implementing the hookspec, as `_builtin.py` does for artifact providers | `bug`, `feature`, `memory`, `flake`, `ci` |
| Plugin | new `pluggy` hookspec `sase_task_types` + entry-point group, added to `ENTRY_POINT_GROUPS` in `plugins/inventory.py:17` | `github` (from `sase-github`), later `flag` |
| Project config | `bead.task_types:` in `sase/sase.yml`, validated by the same code | project-specific types that need no code |

Including project config as a first-class source is a deliberate recommendation, not
scope creep. The glossary proved that a project often wants pure-data vocabulary without
publishing a Python package, and it costs nothing here: the same validator, the same
record, a different `provenance.group`. It also gives a zero-friction escape hatch when
someone wants a type before anyone wants a plugin.

### 4.2 Conflict policy

Copy `_validation.py` exactly: first candidate wins, later duplicates are dropped with a
`duplicate_task_type` diagnostic naming the winner's `provenance.label`. Additionally,
**builtin slugs are reserved** — a plugin or project cannot shadow `bug`, and attempting
it is an error diagnostic, not a silent override. Reserved slugs keep the generated
agent instructions meaningful across projects.

Ordering must be deterministic: builtin first, then plugins sorted by entry-point name
(as `discover_plugin_resources` already does, `main/plugin_discovery.py:44`), then
project config in file order.

### 4.3 Why pluggy over the `sase_config` module pattern

`sase_config` plugins export a module and callers read attributes off it
(`config/loading.py:111`). That works but yields no per-contribution provenance, no
structured diagnostics, and no partial-failure isolation — one bad plugin is a debug-log
line (`plugin_discovery.py:52`). Task types feed *generated, committed agent
instructions*; a silently dropped type is a silently wrong AGENTS.md. Use the pluggy
path, which already produces `error`-severity diagnostics surfaced by `sase doctor`.

---

## 5. Making the field required

### 5.1 The precedent to copy is `--size`

`--size` was introduced on task beads exactly this way and the memory note records the
outcome: "Every new task requires an intentional size… **Legacy sizeless tasks remain
readable and launch through the small-task fallback.**" The CLI already errors on a
missing size (`cli_crud_create.py:116-121`).

Apply the same three-part rule:

1. **Wire/read:** `task_type` is optional. Existing beads without one stay valid forever.
2. **Create:** required. `sase bead create -T task` without a type is an error that
   *prints the available types*.
3. **Display:** a typeless legacy task renders as `untyped` — a presentation label, not
   a registry member, and never offered at creation.

Do **not** backfill by heuristic. A wrong type on 500 historical beads is worse than an
honest `untyped`, and the beads are event-sourced (`beads/events/**`), so a bulk rewrite
is a real event-stream mutation, not a column update.

### 5.2 Required-ness and the triage bar interact

`task_gate_suppressed` withholds a ready task from triage below `min_plus_ones`
(`task_triage_policy.py:24`). Types make that bar expressible per type (§7). But note
the ordering constraint: **a type must be required before per-type policy is useful**,
and per-type policy is the main reason to want types at all. That argues for shipping
required-ness in the same change as the registry, not after.

### 5.3 What the agent-facing instructions become

`memory-sase.template.md`'s three bullets become a generated table plus a pointer, in the
glossary's two-level style:

```
**TASK TYPES:** every new task bead requires a type. Run `sase bead type show <slug>`
for a type's required fields before creating one. Types: bug; ci; feature; flake;
github; memory.
```

with `/sase_new_task` step 7 gaining a `sase bead type show <slug>` call and the
`-T "task(<type>)"` form. The list is short enough to inline and long enough that
inlining every type's field spec would bloat every agent's context — the same tradeoff
the glossary already resolved this way.

### 5.4 CLI grammar: reuse `-T "type(args)"`

`-T` already parses `plan(<file>[,<parent>])`, `phase(<parent>)`, and
`flag(<key>,<date>,<release>)` (`cli_crud_create.py:33-90`). So:

```bash
sase bead create -T "task(flake)" -t "..." -d "..." -z small \
    --field test_id=tests/foo.py::test_bar --field first_seen=2026-08-17
```

Bare `-T task` fails with the type list. This needs **no new short flag**, no `-T`/
`--task-type` confusion, and it makes `flag` foldable later without a grammar change:
`-T "task(flag)" --field key=... --field remove_by_date=...` is the same shape as today's
`-T "flag(key,date,release)"`.

`--field k=v` (repeatable) is the agent-friendly, non-interactive form. The ACE TUI's
`bead_create_modal.py` and the notification-gate declared-input machinery (which already
took a declared `snooze duration` input) can both drive off the same spec for humans.
Per `sase/memory/cli_rules.md`, confirm flag naming there before implementing.

---

## 6. Determinism: required plugins, and why that is not sufficient alone

### 6.1 The failure this prevents

Without intervention: agent A on a machine with `sase-github` runs `sase memory init`,
AGENTS.md gains `github`, A commits it. Agent B on a machine without it runs
`just check` → `sase init memory --check` → drift → red build, for a change B did not
make. Worse, B "fixes" it by regenerating, and A's build goes red.

### 6.2 `plugins.required` in project config

New top-level key in `sase/sase.yml` (register it in
`src/sase/config/sase.schema.json`, which is `additionalProperties: false`):

```yaml
plugins:
  required:
    - name: sase-github
      version: ">=0.4,<1.0"
    - name: sase-flag-tasks
```

Enforcement, graded by blast radius:

| Surface | Behavior |
| --- | --- |
| `sase memory init` / `sase validate` | **Hard error.** Generated instructions depend on it; refusing to write a knowingly-incomplete AGENTS.md is the whole point. |
| `sase bead create -T "task(<slug>)"` for a missing plugin's slug | **Hard error** naming the plugin and the install command. |
| `sase doctor` | New `plugins.required` check, `ERROR` status, listing missing/version-mismatched plugins. Sits beside the existing `plugins.resources` and `plugins.github` checks (`doctor/checks_plugins.py:29-42`). |
| Project enable / workspace prepare / ACE startup | **Warning + offer to install** via the existing `sase plugin install` path (`plugins/_operations_install.py`). |
| `sase bead show` / list of an unknown type | **Never fails.** Degraded render (§3.2). |

The version spec should be checked against the installed distribution version, which
`plugins/inventory.py:188` already extracts.

### 6.3 A lock file is the part that actually buys determinism

`plugins.required` guarantees the plugin is *present*. It does not guarantee the
*content* of its specs: bump `sase-github` from 0.4.1 to 0.5.0 with a reworded `summary`
and AGENTS.md drifts again, on one machine first.

Add a committed snapshot, written by `sase memory init`:

```json
{
  "version": 1,
  "types": [
    {"slug": "bug", "label": "Bug", "summary": "…",
     "source": "builtin:sase", "digest": "…"},
    {"slug": "github", "label": "GitHub issue", "summary": "…",
     "source": "sase_task_types:github", "package": "sase-github",
     "version": "0.4.1", "digest": "…"}
  ]
}
```

- **AGENTS.md renders from the lock**, so it is a pure function of committed files. Any
  two machines produce byte-identical output.
- **`sase memory init --check` compares lock vs live registry** and reports a precise,
  actionable diff ("`github` spec digest changed: sase-github 0.4.1 → 0.5.0; run
  `sase memory init`") instead of an opaque AGENTS.md diff.
- `digest` reuses the pattern already shipped for artifact-ref specs
  (`artifact_ref_provider_spec_digest`, `_validation.py:29`) — a Rust-computed stable
  hash of the normalized spec, so the digest does not change on key reordering or
  whitespace.

This is the same reason lockfiles exist generally, and it converts "your machine differs"
from a mystery into a one-line instruction. Recommended location:
`sase/task_types.lock.json`, beside the project config.

**Trade-off, stated honestly:** this is one more generated file to keep in sync, and one
more thing `sase memory init` can fail on. The alternative — reading the live registry —
is simpler but reintroduces exactly the class of bug `staleness.py` was written to warn
about. Given that the drift check is wired into `just check` for every agent, the lock is
worth its cost.

### 6.4 The skill is machine-global; only AGENTS.md is per-project

`/sase_new_task` is a generated skill deployed to managed locations (the chezmoi repo) —
one copy per *machine*, shared by every project. It therefore **must not** contain a
project's type list. It should instruct the agent to discover types at runtime:

```bash
sase bead type list          # slugs + one-line summaries for this project
sase bead type show flake    # required fields, template, when-to-use
```

Per-project inlining lives in AGENTS.md (from the lock); per-type detail is fetched on
demand. This is precisely the glossary split, and it is also what keeps the skill from
needing regeneration whenever a project's plugin set changes.

---

## 7. The payoff that justifies the work: per-type policy

A type field that only labels beads is worth little. The value is that it becomes a
dispatch key. Concrete hooks the registry enables, roughly in order of value:

1. **Per-type `+1` threshold.** `bead.task_triage.min_plus_ones` is global today
   (`task_triage_policy.py`). A `ci` failure should raise a gate at zero corroboration;
   a `feature` suggestion should probably need two. Expressible as
   `min_plus_ones: 0` in the spec, overridable per project.
2. **Per-type staleness sweep.** `stale_task_bead` likewise — a stale `flake` report can
   expire in a week, a `bug` should not.
3. **Per-type gate policy.** `flag` beads today use a *due-date* gate (`flag_due.py`)
   rather than a corroboration gate. A `gate: due_date` variant in the spec is what makes
   §8's flag migration possible at all.
4. **Per-type default size.** `flake` is almost always `small`; `feature` rarely is.
5. **Per-type sync.** The `github` type declares that its beads participate in
   `external_mirror` reconciliation, replacing the current implicit `external_ref`
   convention.
6. **Presentation.** `bead_type_presentation.py` currently hard-codes four glyph/color
   entries; the spec's `glyph`/`accent_color` feed the same renderer for task subtypes.

Items 1–2 are worth doing in the first change, because they are the reason to make the
field required rather than optional.

---

## 8. Should `flag` become a task type?

The user proposes it, and long-term it is the right shape. But it is the most expensive
item on the list and it should not gate the rest.

**What makes it hard:**

- `flag` is an `IssueType`, not a task subtype. Migrating means every flag bead changes
  `issue_type` in an event-sourced store, and every one of the invariants in §1.1 shifts:
  flag beads would suddenly be eligible for `ready`, `snoozed`, and `+1` evidence, none
  of which is meaningful for them.
- Its gate is due-date-driven (`FlagTriage`), not corroboration-driven. That needs
  registry item §7.3 to exist first.
- `FlagRecord` is a typed Rust struct with real validators (snake_case key, ISO date,
  semver-ish release — `wire.rs:435-495`). Moving to a generic string map loses that
  typing unless the spec's `fields` grow a `validator` concept.
- Only the *bead* side can move to `sase-flag-tasks`. The flag **registry** is code-owned
  in the sase source tree (`feature_flags/registry.py`, 18 modules, plus
  `tools/check_feature_flags --static` in `just validate` and `doctor/checks_flags.py`),
  and `sase flag new` refuses to run outside a SASE-managed checkout
  (`cli_new.py:33-38`). A plugin owning the bead while core owns the registry is a
  workable but genuinely awkward seam — worth deciding deliberately rather than by
  default.

**Recommendation:** stage it.

- **Phase 1:** registry + `task_type` + builtins + `github`. `flag` untouched.
- **Phase 2:** add per-type gate policy (§7.3) and field validators, proven on builtins.
- **Phase 3:** migrate `flag` to `task(flag)` behind a feature flag (`sase flag new`
  per `sase/memory/sase_flags.md`), with a one-way event-stream migration and a
  `sunset` branch keeping the old `IssueType.FLAG` readable.

Extracting to `sase-flag-tasks` should be a Phase 3 decision informed by whether Phase 2
actually made the flag lifecycle expressible declaratively. If it did not, keeping `flag`
in core as a task type is a perfectly good outcome.

---

## 9. Type assignments

| Type | Location | Notes |
| --- | --- | --- |
| `bug` | builtin | Agent-discovered defect in unrelated work. Pure data; no code. |
| `feature` | builtin | Out-of-scope improvement. Pure data. |
| `memory` | builtin | Memory-file update proposal. Field for the target note path — worth validating against `sase/memory/*.md`, which is a builtin-only capability. |
| `flake` | builtin | Fields: test id, first seen, observed rate. Low `min_plus_ones`? No — flakes want corroboration; use the default. |
| `ci` | builtin | Confirmed true failure. Recommend `min_plus_ones: 0` — a real red build should not wait for a second reporter. |
| `github` | `sase-github` | The provider-specific auth already lives there (`external_mirror/auth.py:63` references `sase_github`'s exception classes), even though the mirror engine is core. Declares participation in `external_mirror` and carries `external_ref`. |
| `flag` | core for now → revisit in Phase 3 | See §8. |

`ci` had no stated location; builtin is right — it pairs with `flake`, needs no external
system, and every SASE project wants it.

---

## 10. Recommended solution

**1. Model (`sase-core` + Python mirror).** Add `task_type: Option<String>` and
`task_type_fields: BTreeMap<String,String>` to `IssueWire`/`Issue`. Rust validates slug
*shape* only and never a membership list; unknown slugs deserialize cleanly. Add
`CHECK(task_type IS NULL OR issue_type = 'task')` via a plain `ALTER TABLE` migration.
`IssueType` is untouched.

**2. Registry (`sase.task_types`, modeled on `sase.artifact_providers`).** A pluggy
hookspec returning declarative `Mapping[str, Any]` specs; a `BuiltinTaskTypes`
implementation; a new `sase_task_types` entry-point group added to `ENTRY_POINT_GROUPS`;
project config `bead.task_types` as a third source. One central validator producing
`TaskTypeRecord{slug, label, summary, fields, required_fields, body_template, digest,
provenance}` plus `TaskTypeDiagnostic`s. Builtin slugs reserved; duplicates dropped with
a named diagnostic. Digest computed in Rust.

**3. Storage of field data.** Generic string map, rendered through the type's Jinja2
`body_template` **at display time**, appended below `description`, never merged into it.
Unknown type → raw key/value fallback render, never a read failure.

**4. Required at creation, optional on read.** `-T "task(<slug>)"` reusing the existing
parameterized `-T` grammar; `--field k=v` repeatable; bare `-T task` errors with the type
list. Legacy typeless beads render as `untyped`. No heuristic backfill.

**5. Determinism.** `plugins.required` in `sase/sase.yml` (schema-registered), enforced
as a hard error in `sase memory init`/`sase validate` and in typed bead creation, as an
`ERROR` in a new `sase doctor` `plugins.required` check, and as a warning-plus-install-
offer at project enable and ACE startup. On top of it, a committed
`sase/task_types.lock.json` snapshot: AGENTS.md renders from the lock, and
`sase memory init --check` diffs lock against live registry with an actionable message.

**6. Agent instructions, two levels.** AGENTS.md (per-project, from the lock) carries a
`**TASK TYPES:**` line listing slugs and one-line summaries, replacing the three bullets
in `memory-sase.template.md` with a generated table. `/sase_new_task` (machine-global)
gains `sase bead type list` / `sase bead type show <slug>` steps and never inlines a
project's types.

**7. Policy hooks.** Ship per-type `min_plus_ones` and staleness overrides in the first
change — they are the reason the field is worth making required. Defer per-type gate
kind, field validators, and the `flag` migration to Phases 2–3 (§8).

### Why this over the alternatives

Widening `IssueType` cannot work (compiled enum, 245 sites, invariant loss). A pure
config approach with no plugin hook cannot express `github` (which needs code for mirror
participation) and forfeits the diagnostics that make a silently-dropped type visible in
a *generated, committed* file. Rendering AGENTS.md from the live plugin environment is
simpler than a lock file but reintroduces exactly the cross-machine drift that
`staleness.py` already documents as a real failure. And migrating `flag` first maximizes
risk on the least-understood part of the design before the cheap types have proven the
registry.

The recommended path is additive at every layer, reuses one already-shipped and
already-validated pattern (`artifact_providers`) rather than inventing a second, and
makes the one genuinely new risk — machine-dependent agent instructions — impossible by
construction rather than by convention.

---

## Open questions for the owner

1. **Lock file:** accept `sase/task_types.lock.json` as a committed artifact, or accept
   version drift and rely on `plugins.required` alone? (§6.3 argues for the lock; it is
   the one recommendation here with a real maintenance cost.)
2. **Project-config task types** as a third source — in scope, or plugins only?
3. **`ci` and `flake` triage bars:** should `ci` bypass the `+1` threshold entirely?
4. **`flag` end state:** stays core as a task type, or moves to `sase-flag-tasks` with
   the registry staying in core (§8's awkward seam)?
5. **Field validators:** ship in Phase 1 (needed to express `flag` faithfully later) or
   Phase 2?
