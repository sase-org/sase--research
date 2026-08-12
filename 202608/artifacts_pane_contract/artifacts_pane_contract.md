---
create_time: 2026-08-12
updated_time: 2026-08-12
status: research
tags: [ace, artifacts, artifact-refs, contract, tui]
---

# A Unified Contract for ACE Artifacts Sub-tabs

**Research question:** epic [`sase-js`](https://github.com/sase-org/sase--beads) made the
ACE Artifacts sub-tabs dynamic. Before adding new sub-tab functionality, what should SASE
standardize so that Stitches, Patches, Beads, Files, and every future sidecar-repo
document tab feel like one product — and so an artifact-ref type designer can add a tab
without writing or understanding ACE widget code?

**Scope and evidence.** Consolidated from two independent reports (`__a`, `__b`) plus a
third verification pass. Source read at `sase` `888453d39`, `sase-core` `2519b429`
(`crates/sase_core/src/artifact_ref/`), `sase-research` `f499469`; the closed `sase-js`
epic and its nine phase beads; and the prior consolidated report
[`ref_provider_contract.md`](../ref_provider_contract/ref_provider_contract.md) §9, which
is what the epic was built against. Every defect below was reproduced live in workspace
`sase_20` by executing `resolve_artifacts_subtabs()` and `_provider_label()`, not inferred
from reading.

---

## Bottom line

The epic shipped a dynamic tab **registry** but not a dynamic **pane**. A configured
provider gets a tab, an accent, a digit, and a working list. It does not get its own pane
chrome, status counters, hints, copy targets, help section, or any use of the
`properties` / `detail` blocks it declared. `@research` today renders inside a pane that
calls itself "Plans", counts "proposals · active · archived", offers `A`pprove / `X`
reject, and copies an "owning bead id". The provider spec is a **resolution** contract;
there is no **presentation** contract at all.

The fix is two layers, and the layer split is what resolves the disagreement between the
two source reports:

1. **A host-owned pane contract in Python** — `ArtifactsPaneContract` with a closed
   `PaneCapability` vocabulary that all five pane families produce, and which every
   downstream surface (footer, availability, help modal, command palette, copy registry,
   conformance test) reads *instead of comparing pane ids*. Behind it, a shared browser
   shell absorbing the loading/filter/detail/marks/jump machinery that is currently
   written three times.
2. **A declarative `ref.pane` block at document-ref provider spec `schema_version: 2`** —
   the designer-facing half. Providers supply data and presentation *hints*, never Textual
   code, keybindings, callbacks, or colors.

Patches stays a deliberate exception: it is a query-driven workflow board, not another
artifact collection. It keeps the top-level tab and lifecycle conventions and gets two
cheap wins, but not the list/detail browser.

Sequence it in five phases. **Phase 0 is a same-day defect fix worth doing regardless.**
Land Phases 0–2 before adding new sub-tab functionality, because anything added before
the verb keymap exists gets written four times and rewritten once.

---

## 1. What shipped versus what §9 planned

Reading the code at `888453d39` against §9 of the prior report:

| §9 target | Status | Evidence |
| --- | --- | --- |
| `ArtifactsSubTab` becomes `str` + runtime registry, cached on a config token | **Done** | `artifact_tabs.py:133` `resolve_artifacts_subtabs()`, cached on `_provider_source_token()` |
| Stable ids `ref:plan` / `ref:research`, not display names | **Done** | `_provider_descriptors` builds `f"ref:{kind}"`; `LEGACY_ARTIFACTS_SUBTABS` maps `plans` → `ref:plan` |
| Persisted sub-tab naming an uninstalled provider falls back to default | **Done** | `normalize_artifacts_subtab` |
| `current_files_subtab` disappears; nested Files panes flattened | **Done** | `FILES_SUBTAB_ORDER == ()` |
| New Files pane with version toggling and origin | **Done** | `files_pane.py`; `(` / `)` bound to `files_prev/next_version` |
| Number keys stay stable; new tabs never renumber existing ones | **Not done** | `enumerate(sorted(by_kind, ...), start=5)` — §2 Defect B |
| Collapse `plans_*` into one `ArtifactsDocumentsPane(provider)` **driven by the spec's `properties` and presentation block** | **Half done** | The class exists and is instantiated per kind, takes `provider_spec`, and **never reads it**; there is no presentation block to read |
| "`research` costs zero new pane code" | **True but misleading** | Zero new code *and* zero correct chrome |

`grep -rn 'provider_spec' src/sase/ace/tui/` returns exactly six hits: two dataclass
fields, one assignment in `plans_pane.py:67`, and `view.py` passing it in. Nothing reads
it. That single fact is most of the problem.

The prior report's own §9.1 is worth re-reading before deciding on digits, because it
already anticipated this: *"Unstable number keys are a worse regression than no number
keys."* Note also that §9.1 targeted `... | Plans | Research | Files` with Files **last** —
the implementation matched the plan, and the owner's `sase-js` note of 2026-08-12T14:28
is a deliberate reversal of that decision, not a coding slip.

---

## 2. Verified defect inventory

Five defects. A–D were reported by `__b` and independently reproduced here; E is new.

**Defect A — Files renders out of digit order.** `resolve_artifacts_subtabs()` builds
`(stitches, patches, beads, *providers, files)` (`artifact_tabs.py:143-149`) while
`FIXED_ARTIFACTS_DIGITS` assigns Files `"4"`. Live output in this workspace:

```text
stitches(1) │ patches(2) │ beads(3) │ ref:plan(5) │ files(4)
```

This is the defect the project owner reported on the `sase-js` bead. Two things matter
for planning it: `tests/ace/tui/test_artifacts_scaffold.py` currently **asserts**
`descriptor_ids[-1:] == ("files",)`, so the fix must update the test that locks the bug
in; and `sase-js.land` explicitly left it unfiled — **there is no task bead for it**
(`sase bead list --status open` → none; the only related ready bead is `sase-k6`, which is
a different wire, see §4).

**Defect B — provider digits are unstable.** Providers are numbered
`enumerate(sorted(by_kind, key=_natural_label_key), start=5)`. Configure a `design`
sidecar and the assignment becomes `design=5, plan=6, research=7` — every existing
muscle-memory digit shifts. This is the exact regression §9.1 warned against.

**Defect C — latent accent collision, plus a leaky module global.** The fallback is
`_PROVIDER_ACCENTS[(offset - 5) % 6]`, whose element 0 is `#AF87FF` — the value pinned for
`ref:plan` in `ARTIFACTS_ACCENTS`. Any kind sorting before `plan` takes offset 5 and
renders in the Plans colour. Separately, `ARTIFACTS_ACCENTS.setdefault(tab_id, accent)`
(`artifact_tabs.py:294`) mutates a module-level dict during resolution and
`reset_artifacts_subtabs_cache()` does not undo it, so a kind removed from config keeps
its accent for the life of the process.

**Defect D — provider discovery fails silently, and the failure is not exotic.**
`_load_project_provider_records` wraps both the project read and the entire per-workspace
policy block in bare `except Exception`. Reproduced here with the precise cause: with
`sase_core_rs` not importable, `list_project_records` raises
`ImportError: sase_core_rs is not importable in this environment but is a hard runtime
dependency of sase`, the bare `except` swallows it, and `resolve_artifacts_subtabs()`
returns only the four fixed tabs. A user cannot distinguish "not configured" from
"broken". Worse, `_provider_source_token()` returns a *stable* `("unavailable",)` token in
that state, so the degraded four-tab result is **cached** and never retried in-process.

Two corrections to `__b`'s framing here, both of which make Phase 0 cheaper than it
implied:

- A diagnostic already exists. `_normalize_document_ref_spec` emits
  `code="missing_ref_provider"` with actionable text, and `sase doctor -C config.repos`
  already fires on it — verified live in this workspace (`WARN · 1 sidecar repo config
  issue(s) found`) because `sase-research` is not installed in its venv. `docs/artifact_references.md`
  even documents this as the intended behaviour. **The check is not missing; ACE is
  discarding it.** The work is plumbing an existing diagnostic through to a degraded tab,
  not inventing a doctor check.
- The `sase_core_rs` case is the one genuinely uncovered path, because it kills discovery
  before any spec is read. That deserves a distinct, loud failure — not a silent tab.

**Defect E (new) — the generated provider label is grammatically wrong.**
`_provider_label` pluralizes with `if label.endswith("s"): return label; return f"{label}s"`.
Verified live:

```text
'research' -> 'Researchs'      'sketch' -> 'Sketchs'
'plan'     -> 'Plans'          'design' -> 'Designs'
```

`sase-research` ships no `label` key, so **the Research tab is actually labelled
"Researchs"**. (`__b` reported the strip as reading "Research"; that was inferred, not
executed.) Two fixes, both wanted: make the fallback sibilant-aware (`s`, `x`, `z`, `ch`,
`sh` → `es`), and make `label` a first-class declared key so a provider never depends on
the host's guess. Note `_provider_label` already reads `spec["label"]` and
`spec["ref"]["label"]` — so a de-facto presentation key already exists and is already
honoured; §5's `ref.pane.label` regularizes it rather than inventing it.

---

## 3. Where the divergence costs

`widgets/artifacts/` is **13,413 lines across 52 modules**, of which only ~691 are shared.

| Surface | Modules | Lines |
| --- | ---: | ---: |
| Beads | 11 | 3,661 |
| Plans / Documents | 13 | 3,536 |
| Files | 8 | 2,652 |
| Stitches | 7 | 2,052 |

Another ~5,100 lines of Artifacts actions, clipboard dispatch, copy targets, and palette
code switch on pane-specific ids and groups.

**The loader is written three times.** `beads_pane.py`, `plans_pane.py`, and
`files_pane.py` each carry their own copy of the same off-thread coalescing machine:
`_loading` / `_reload_pending` / `_force_pending` flags, a `_request_load(force=...)` that
early-returns into the pending flags, `run_worker(task, thread=True, exclusive=False,
exit_on_error=False)`, and an `on_worker_state_changed` that checks worker identity,
classifies terminal states, validates `result.project == self.project_scope`, preserves the
selected id, cancels jump mode, and replays through `call_later`. Roughly 200 lines
triplicated, three places to fix any bug in it. The panes also disagree on activation
semantics with no stated reason (Beads always reloads; Documents and Files reload only on
missing snapshot or project change; Stitches always reschedules; Patches just refocuses).

**The navigation protocol is advisory, not enforced.** `ArtifactEntryNavigator` declares
seven methods; `request_entry_target` and `conditional_footer_entries` are defined only in
`plans_navigation.py` and `beads_navigation.py`. Files and Stitches lack both, and the two
call sites paper over it with `getattr(pane, ..., None)`
(`actions/artifacts_navigation.py:98,114`). User-visible consequence: **cross-pane deep
links and conditional footer hints work on Beads and Documents and silently do nothing on
Files and Stitches.** No test would catch a sixth pane forgetting a method.

**47 pane-scoped keymap entries, 20 of them four copies of five verbs.** Exact counts:
Stitches 10, Documents 8, Beads 18, Files 11. `j`/`k`/`enter`/`f`/`R` are each declared
four times — they can only ever be configured to differ, never to agree. Where the panes
genuinely differ, the same key means different things:

| Key | Stitches | Documents | Beads | Files |
| --- | --- | --- | --- | --- |
| `y` | copy SHA | **absent** | copy *linked issue* | copy reference |
| `s` | cycle merges | — | cycle status | cycle kind |
| `o` | — | — | open *linked issue* | open file externally |
| `a` | toggle all projects | — | — | open producing agent |

`y` is the worst: on Stitches and Files it copies the row's own identity, on Beads it
copies a *linked external issue*, and on document panes it does nothing. Every document
pane, including `@research`, is driven by `plans_next`, `plans_filters`, `plans_approve`,
`plans_open_bead`.

**The `ref:*` → `artifacts_plans` copy shim is hard-coded in five places**, not three as
`__b` reported: `copy_targets.py:510`, `commands/availability.py:224`,
`actions/clipboard/_artifacts.py:30`, `actions/clipboard/_palette_artifacts.py:250`, and
inline in `widgets/_keybinding_modes.py:505`. A sixth site,
`_copy_label_for_artifacts_subtab`, returns the literal string `"Plans"` for any `ref:`
sub-tab. Consequence: `% %` on a Research row copies "the owning bead id" and `% d` copies
"design reference". Within groups the keys drift for no reason (Markdown link is `l` on
three panes and `L` on Files; metadata JSON is `J` on three and `j` on Files).

**Patches has no `@ref` copy target at all.** `@patch:<name>` is a live ref kind, the
Patches pane sits inside the Artifacts tab, and there is no way to copy `@patch:` for the
selected Patch.

**One abstraction is already right.** `widgets/filter_bar.py::FilterBar` is a declarative,
class-var-driven contract (`ACCENT`, `KEY_COMPLETIONS`, `STATIC_VALUE_COMPLETIONS`,
`VALUE_HINTS`, `REPEATABLE_VALUE_KINDS`, `NEGATABLE_KEYS`, `FREE_TEXT_HINT`, `PERSISTENT`,
plus one abstract `_completion_context`) that all four bars satisfy in under 100 lines
each. **`FilterBar` is the pattern to copy upward for the pane as a whole**, not something
to replace. The gaps are in what subclasses declare, not in the abstraction: Files alone
leaves `NEGATABLE_KEYS` unset (so `-key:` silently works on three panes and not the
fourth), Stitches alone sets `PERSISTENT = True`, and `plan_filter_bar.py:31` reads
`ARTIFACTS_ACCENTS["plans"]` at class-definition time, so a Research filter bar is
coloured Plans-purple.

---

## 4. The layer split — resolving the two reports' disagreement

The sharpest conflict between the source reports is where the contract lives. `__a` put
typed property coercion, identity, inventory filtering, and a normalized browse wire in
`sase-core`; `__b` argued that `ref.pane` is Textual presentation and therefore belongs in
Python per the repo's `rust_core_backend_boundary` rule, with no Rust wire bump. Reading
`crates/sase_core/src/artifact_ref/` shows **both are right about different halves**:

**Presentation is Python.** `provider_spec.rs` validates a spec that has no notion of a
tab: no label, no order, no columns, no facets, no grouping, no empty state. Adding those
to the Rust wire would put Textual layout concerns in the core crate, which the boundary
rule places on the Python side. `ref.pane` belongs in `sidecar_ref_config.py`, bumping
`DOCUMENT_REF_PROVIDER_SPEC_SCHEMA_VERSION` (currently `1`), not
`ARTIFACT_REF_PROVIDER_SPEC_WIRE_SCHEMA_VERSION`.

**Typed property *values* are core, and are genuinely missing.** `entry.rs` already
defines `ArtifactEntryWire` with exactly the shape `__a` proposed for
`ArtifactBrowseEntry` — `stable_id`, `ref_kind`, `canonical_argument`, `display_label`,
`project_display_name`, `repository`, `repo_relative_path`, `captured_revision`,
`captured_digest`, `logical_path`, `properties`, `origin`. `__a` was right that this
should be *extended*, not competed with. But two facts change the plan:

- `properties` is `BTreeMap<String, String>`. The spec validates that a property declares
  type `datetime` / `string_list` / `integer`, and the entry wire then flattens every
  value to a string. Sorting by a real `updated_time`, or filtering `tags:` as a list, is
  not expressible today. **This is the one part of `__a`'s "core owns coercion" claim that
  survives, and it is a real `sase-core` change.**
- `ArtifactEntryWire` is constructed only in a Rust unit test. Production frontmatter
  parsing is Python (`sase.sdd.frontmatter.parse_frontmatter`). So "move coercion to core"
  is not a refactor of a working path; it is new work, and it should be scheduled on its
  merits rather than as a prerequisite.

**A trap neither report caught: the spec digest will not see the pane block.**
`validate_ref_provider_spec` calls Rust `artifact_ref_provider_spec_digest`, which
serializes the *Rust* struct — so any key Rust does not model is dropped before hashing.
A Python-only `ref.pane` block therefore **does not change `provider_spec_digest`**. Both
reports recommend caching normalized snapshots keyed on the spec digest; done naively that
cache would not invalidate when a provider changes its pane block. Fix: compute a
Python-side `presentation_digest` over the normalized `pane` block and fold it into
`ArtifactsTabDescriptor` and every pane cache key. Cheap, but it must be designed in, not
discovered later.

**Two more implementation facts that will otherwise bite:**

- `_ref_override` rejects unknown keys against a `_KNOWN_REF_CONFIG_KEYS` allowlist
  (`sidecar_ref_config.py:46-59`), so an **inline** `ref: pane: ...` fails validation
  today. A `use:`-provided plugin spec takes a different path (`base = _plain_mapping(provider.spec)`)
  with no allowlist check, which is exactly why `_provider_label` can already read a
  plugin-supplied `label`. Adding `pane` means adding `REF_PANE_CONFIG_KEY` to that
  allowlist, or inline and `use:` specs will silently diverge in capability.
- Name the version carefully. `sase-k6` (READY, large) already proposes *"Extend
  artifact-ref use wire to schema 2"* — a different wire in the same subsystem. Say
  "document-ref **provider spec** schema 2" in bead and plan text to avoid collision with
  it and with `sase-k5`.

**The cheapest high-value change needs no schema work at all.** `plans_data_documents.py`
already parses each document's frontmatter into `frontmatter: dict[str, str]` and carries
it on the row; `plans_detail.py:152` renders it through
`sase.sdd.plan_properties.ordered_plan_property_items`, which is a pure sort against a
plan-specific `PLAN_PROPERTY_ORDER` constant. The provider already declares
`detail.fields: [status, create_time, updated_time, tags]`. **The data plumbing exists end
to end; only the ordering constant is hard-coded.** Parameterizing that one function by
`provider_spec["ref"]["detail"]["fields"]` (falling back to plan order for
`provider_kind == "plan"`) makes the detail band spec-driven with no spec change, no Rust
change, and no new data path — the single highest value-per-line change available.

---

## 5. The contract

### 5.1 Layer 1 — `ArtifactsPaneContract` (Python)

One frozen dataclass, produced for every descriptor `resolve_artifacts_subtabs()` returns,
living beside `ArtifactsTabDescriptor` in `artifact_tabs.py` (already widget-free — keep
it that way):

```python
@dataclass(frozen=True, slots=True)
class ArtifactsPaneContract:
    id: str                          # "beads", "ref:research"
    label: str
    accent: str
    pane_id: str
    order: int                       # stable sort key; digits derive from this
    digit_shortcut: str | None

    ref_kind: str | None             # None for panes with no @kind (patches)
    target_prefix: str               # entry-target tuple[0]
    project_scoped: bool
    presentation_digest: str         # see §4 — cache key, not the Rust spec digest

    capabilities: frozenset[PaneCapability]

    row_title: str | None
    detail_fields: tuple[str, ...]
    filter_facets: tuple[FilterFacet, ...]
    date_property: str | None
    status_counters: tuple[StatusCounter, ...]
    empty_state: EmptyState
    filter_bar_persistent: bool
    copy_targets: tuple[CopyTargetSpec, ...]
```

`PaneCapability` is a **closed enum** of verbs the shared layer implements: `OPEN`,
`FILTER`, `REFRESH`, `MARK`, `JUMP`, `SCOPE_PROJECT`, `COPY_REFERENCE`, `COPY_PATH`,
`COPY_LINK`, `COPY_JSON`, `OPEN_EXTERNAL`, `OPEN_AGENT`, `LINK_JUMP`, `VERSIONS`,
`EXPAND_TREE`, `CYCLE_FACET`, `MUTATE`, `APPROVE`. A capability **only enables an action
already registered by the host**; it never carries executable code. Footer, help section,
palette entries, copy-mode rows, and action availability all derive from this set, and
nothing downstream compares a pane id again — deleting the five copy-group shims and the
`if action in X_ARTIFACT_ACTIONS and pane_key != "x"` availability chain.

Built-in panes build their contract from a module-level table in Python and may declare
`MUTATE` / `EXPAND_TREE` / `VERSIONS`. Provider panes build theirs from §5.3, and the
schema deliberately cannot request `MUTATE` or `APPROVE`.

### 5.2 Layer 2 — one verb-based keymap

| New action | Replaces | Default |
| --- | --- | --- |
| `artifacts_next` / `artifacts_prev` | `{stitches,plans,beads,files}_next` / `_prev` | `j` / `k` |
| `artifacts_open` | `*_view_selected` ×4 | `enter` |
| `artifacts_filters` | `*_filters` ×4 | `f` |
| `artifacts_refresh` | `*_refresh` ×4 | `R` |
| `artifacts_copy_reference` | `stitches_copy_sha`, `files_copy_reference` | `y` |
| `artifacts_copy_path` | `files_copy_path` | `Y` |
| `artifacts_open_external` | `files_open_external` | `o` |
| `artifacts_link_jump` | `plans_open_bead`, `beads_open_plan` | `L` |
| `artifacts_cycle_facet` | `stitches_cycle_merges`, `beads_cycle_status`, `files_cycle_kind` | `s` |

Twenty-two entries collapse to ten. Keep old names as **aliases** in the keymap loader so
existing `~/.config/sase/sase.yml` overrides keep working, and emit a `sase doctor`
advisory naming the replacement. Rename remaining `plans_*` to `documents_*` under the
same alias policy; `plans_approve` / `plans_reject` become `documents_approve` /
`documents_reject`, still gated — now via the `APPROVE` capability rather than
`pane.provider_kind == "plan"` string comparison.

Three deliberate consequences: `y` copies the row's **own** reference on every pane (Beads'
current `y` becomes `beads_copy_linked_issue`, which is what it always was); `o` opens the
selected row's artifact on every pane declaring `OPEN_EXTERNAL`, so document panes gain it
for free; and Stitches' `a` (toggle-all-projects) moves off `a`, freeing it for
`OPEN_AGENT` uniformly.

Also fold in the two free FilterBar fixes: set `NEGATABLE_KEYS` on the Files bar, and make
the document bar read its accent from the contract rather than `ARTIFACTS_ACCENTS["plans"]`
at class-definition time.

### 5.3 Layer 3 — `ref.pane` at document-ref provider spec `schema_version: 2`

This is what a ref-type designer writes. Everything is optional and every default is
derivable, so `schema_version: 1` specs keep working unchanged.

```yaml
ref:
  kind: research
  # ... existing schema_version 1 keys ...
  properties:
    status:       {type: string,      source: markdown_frontmatter, label: Status, facet: true}
    tags:         {type: string_list, source: markdown_frontmatter, label: Tags,   facet: true}
    create_time:  {type: datetime,    source: markdown_frontmatter, label: Created}
    updated_time: {type: datetime,    source: markdown_frontmatter, label: Updated}
  detail: {fields: [status, create_time, updated_time, tags]}

  pane:
    label: Research               # default: humanized kind (fix Defect E's fallback too)
    description: Durable research reports and generated media
    order: 60                     # default: 50 + config order; digits derive from this
    row:
      title: title                # a property name, or `filename`
      badges: [status, tags]
      timestamp: updated_time
      fields:                     # prioritized list columns, Kubernetes-style
        - {field: status,       priority: 0}
        - {field: updated_time, priority: 1}
    group_by: year                # none | year | month | status | <property>
    default_sort:
      - {field: updated_time, direction: desc}
      - {field: repo_path,    direction: asc}
    filters:
      facets: [status, tags, project]   # default: every facet-marked property + project
      date_property: updated_time
    capabilities: [open_external, copy_path, copy_link]
    empty_state:
      title: Research
      body: "Select a research report from the research sidecar."
```

Constraints that make this safe:

1. **Common fields stay implicit.** Project, canonical ref, repo-relative path, identity,
   and diagnostics are never redeclared.
2. **Presentation refers only to declared properties or host common fields.** No format
   string can run code.
3. **List fields are hints with priorities.** The host may drop low-priority fields in a
   narrow terminal; detail stays lossless.
4. **Facets are typed.** Boolean / enum / string / string-list may be facets; date and
   datetime opt into `since:` / `until:`. Free text searches `searchable` fields plus
   common title/path/body.
5. **Identity must be stable across content edits.** Repo-relative path is the default; a
   provider-selected identity property must be scalar and documented immutable. Missing or
   duplicate values fall back with a diagnostic rather than merging rows wrongly.
6. **Missing or mistyped values fail per entry.** One malformed document must never remove
   a whole provider tab; the field is absent and the snapshot records a bounded diagnostic.
7. **No colours and no keybindings from providers.** Accent is derived deterministically
   from the kind (stateless and stable), then collision-resolved against the pinned set —
   this is the synthesis of `__a`'s "derive from kind" and `__b`'s "collision-checked".
8. **No arbitrary actions.** `capabilities` selects from a safe subset
   `{open_external, open_agent, copy_path, copy_link, link_jump, cycle_facet, versions}`.
   Command strings and Python entry points are not accepted at any version.
9. **Inventory is side-effect free and bounded.** It may inspect already-resolved artifact
   roots; it never clones, prompts, networks, or takes unbounded locks.

**The designer-facing guarantee, stated plainly:**

- *You must declare:* `ref.kind` and `inventory.globs`. Nothing else.
- *You get for free, identically to every other tab:* a tab with a stable digit and
  non-colliding accent; lazy activation and off-thread coalesced loading; shared project
  scope (`p`); `j`/`k`/`enter`/`f`/`R`; marks, hint-jump (`'`), detail scrolling; a filter
  bar with completion, negation, `since:`/`until:`, and free text; a copy-mode group with
  `@ref`, handoff, Markdown link, path, title, body, JSON, and snapshot; a generated
  help-modal section; command-palette entries; `@kind:<path>` round-tripping through
  `reference_for_entry_target`; and `Referenced By` write-back.
- *You may declare:* row template, grouping, sort, filter facets, detail field order,
  empty-state copy, and any capability in the safe subset.
- *You cannot have:* mutation actions, approval flows, bespoke widgets, per-row callbacks,
  or a resolution hook. Anything needing those is a built-in pane — a sase change, not a
  plugin change.

Two wins land immediately: `sase-research` becomes a correct Research tab with ~12 lines
of added metadata and zero Python, and `plan` stops being special — the builtin plan
provider declares `capabilities: [approve, link_jump]`, `group_by: status`, and its
proposal/active/archive counters, and `ArtifactsPlansPane` ceases to exist as a distinct
class.

### 5.4 Layer 4 — the shared shell

Behind the contract, extract from proven behaviour rather than designing fresh. One
`ArtifactsSnapshotPane` base absorbs the triplicated loader (flags, worker launch,
identity/generation guards, scope validation, selection preservation, pending replay), and
`ArtifactEntryNavigator` becomes an ABC so Files and Stitches must implement
`request_entry_target` and `conditional_footer_entries` — deleting the two `getattr`
call sites and fixing deep links on those panes.

Where `__a`'s adapter model earns its keep is the *next* step, not this one: a normalized
`ArtifactBrowseRequest` / `Snapshot` / `Entry` triple with a synchronous, side-effect-free
`ArtifactBrowseSource.load()` that the shell always calls on a worker thread. That is the
right destination, and per §4 its entry type should **extend `ArtifactEntryWire`** rather
than introduce a second notion of artifact identity. It is not a prerequisite for the
user-visible unification, so it should follow rather than gate it.

---

## 6. Prior art worth copying

- **VS Code Tree View API** — a data provider returns children and a host `TreeItem`;
  styling, navigation, and lifecycle stay with the host, refresh is an event, commands are
  contributed separately. This is exactly the split above. SASE should be *stricter* than
  VS Code about provider execution, because artifact inventory also feeds prompt completion
  and any future non-Python frontend.
  ([docs](https://code.visualstudio.com/api/extension-guides/tree-view))
- **Kubernetes CRD additional printer columns** — implicit standard columns plus a bounded
  set of typed provider fields with a priority controlling normal-vs-wide output, and a
  value violating its declared type is omitted rather than destabilizing the listing. This
  is the model for `pane.row.fields` and for per-entry degradation.
  ([docs](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/#additional-printer-columns))
- **Backstage frontend extensions** — stable extension ids, typed data references, and
  explicit guidance that extension factories stay lean and defer expensive work. Adopt
  that; do **not** adopt its allowance of arbitrary React output, which would let plugins
  bypass the common interface entirely.
  ([docs](https://backstage.io/docs/frontend-system/architecture/extensions/))
- **Textual** — `OptionList` already owns highlight, first/last/page navigation, stable
  option ids, and selection messages while accepting Rich renderables; `ContentSwitcher`
  selects uniquely-identified children and deliberately ships no bindings. These favour one
  shell that composes standard widgets and owns the bindings, with adapters supplying
  immutable render data.
  ([OptionList](https://textual.textualize.io/widgets/option_list/) ·
  [ContentSwitcher](https://textual.textualize.io/widgets/content_switcher/))

---

## 7. Performance and cache contract

`sase/memory/tui_perf.md` governs this work — read it before implementing. Unifying the UI
must not unify every load into one eager cross-project scan.

- Keep `ContentSwitcher` and first-activation laziness. Mounted hidden panes retain state
  but do not load until opened.
- Run every source load and content read off-thread; pump and timer callbacks only schedule
  work, never await the slow body.
- Paint the first bounded page, then extend in the background. Files already does this;
  document providers should adopt it instead of scanning every historical report before
  first paint.
- Cache normalized snapshots on (Rust spec digest, **`presentation_digest`** from §4,
  effective project scope and config token, repo HEAD or index generation). Omitting the
  presentation digest silently breaks invalidation on pane-block edits.
- Re-read UI state after every async boundary; apply a worker result only if generation,
  pane, scope, and source revision still match.
- Debounce detail content, not list highlights. Never parse frontmatter, glob trees, stat
  paths, or resolve providers during a row render or keypress.
- Hold the existing acceptance target: `SASE_TUI_PERF=1` navigation p95 under 16 ms on
  every converted pane, measured after each conversion.

The shell earns its keep here: it enforces worker boundaries and generation guards once,
instead of every future pane author rediscovering them.

---

## 8. Enforcement

**A parametrized conformance test** — `tests/ace/tui/test_artifacts_pane_contract.py` —
that iterates `resolve_artifacts_subtabs()` (**not** a hard-coded list; the closest thing
today, `test_artifacts_marking.py`, is parametrized over a literal
`["stitches","beads","ref:plan","files"]` and so never exercises a new provider). For each
descriptor, mount the pane and assert: all seven `ArtifactEntryNavigator` methods exist and
are callable; a copy group is registered and every declared target resolves; a help section
is generated; the filter bar declares `NEGATABLE_KEYS` covering its repeatable keys;
`conditional_footer_entries()` returns action names present in both the keymap and
`NON_PRS_ARTIFACT_ACTIONS`; the digit shortcut is unique and matches strip position; the
accent is unique; and a synthetic row round-trips through `reference_for_entry_target`. Add
a session-scoped fixture registering a **synthetic third provider** so the contract is
proven on a kind no built-in code knows about.

**Surface provider loss in ACE.** Replace the two bare `except Exception` blocks in
`_load_project_provider_records` with narrow catches that record a diagnostic on the
descriptor, and render a **degraded tab carrying the error in its empty state** rather than
no tab. Reuse the existing `missing_ref_provider` diagnostic and the existing
`sase doctor -C config.repos` check (§2 Defect D) — the new work is a distinct, loud
failure for the `sase_core_rs`-unimportable case, which kills discovery before any spec is
read and currently caches its own degraded result.

**A docs section** in `docs/artifact_references.md` — "What a provider gets in ACE" — that
is the §5.3 guarantee verbatim. That file today documents resolution and publication and
says nothing about the tab.

**A `sase-research` integration test in sase's own suite**, so the shipped provider is the
golden external consumer, plus one generic visual snapshot generated from the fixture
provider.

---

## 9. What should stay different

Uniformity is not the goal; *predictability* is. The contract should express these
divergences rather than erase them:

- **Beads' mutation surface** (`e`, `N`, `n`, `c`, `z`, `w`, issue mode). Beads is the one
  pane that writes to its corpus. Capability `MUTATE`, built-in only.
- **Stitches' timeline and diff loader.** A commit graph is not a list of documents. Keep
  `CommitsTimeline`; expose it through the same contract.
- **Files' version toggling** (`(` / `)`), and its logical-identity/version model and MIME
  viewer. Declare it as capability `VERSIONS` rather than hard-coding it — a git-backed
  document provider could reasonably want it later.
- **Stitches' persistent filter bar.** Defensible where the query *is* the view. Make it a
  declared `filter_bar_persistent: true` rather than an accident of `PERSISTENT = True` on
  one subclass, so the difference is a decision on the record.
- **Patches — contract-exempt (legacy), documented as such.** It predates the Artifacts
  tab, uses the separate ACE query language, has its own selection and marking model, and
  folding it in needs a data migration. Forcing it into the browser would damage the Patch
  workflow *and* make the shared abstraction worse. Give it the two cheap wins now — a
  `@patch` copy-reference target and a help-modal note that it does not participate in
  project scope — and revisit after Phase 3.

---

## 10. Options considered

| Option | Benefit | Failure mode | Verdict |
| --- | --- | --- | --- |
| Fix only the live defects | One day's work | Next provider still renders as "Plans"; 3–4× edit cost stays | Do it **first**, as Phase 0; not a stopping point |
| Shared Python base class only | Kills the triplication and protocol drift | Base class has nothing to read; document chrome stays plan-hardcoded | Necessary, not sufficient |
| Enlarge `ArtifactEntryNavigator` | Smallest diff | Standardizes app→pane control *after* each pane reimplements everything; no designer contract | Insufficient |
| Fully declarative pane, spec-driven end to end | Maximal uniformity | Beads' mutation/epic tree and Stitches' graph are irreducible; schema bloats into a UI toolkit or loses function | Reject |
| Providers ship Textual widgets or callbacks | Maximum local flexibility | Inconsistent UX, unbounded hot-path work, no failure isolation, no future-frontend parity | Reject |
| **Capability contract + declarative presentation** | One contract drives chrome *and* is what designers fill in; bounded plugin surface; incremental | Needs a normalized view model and compatibility aliases | **Best fit** |

---

## 11. Phasing

| Phase | Content | Size | User-visible |
| --- | --- | --- | --- |
| **0** | Defects A–E: Files renders at position 4; provider digits derive from a stable `order` and never renumber an existing tab; accents derived from kind and collision-checked, with `ARTIFACTS_ACCENTS` no longer mutated as a module global; narrow the two `except Exception` blocks and surface a degraded tab; sibilant-aware label pluralization. Update `test_artifacts_scaffold.py`. | S | **Yes — fixes the reported bug** |
| **0.5** | Parameterize `ordered_plan_property_items` by `ref.detail.fields`, so the detail band is spec-driven. No spec change, no Rust change (§4). | XS | **Yes — Research shows its own properties** |
| **1** | `ArtifactsPaneContract` + `PaneCapability`; `ArtifactsSnapshotPane` base absorbing the triplicated loader; `ArtifactEntryNavigator` becomes an ABC; Files and Stitches gain the two missing methods. | L | No (pure de-dup) |
| **2** | Verb keymap with aliases; `plans_* → documents_*`; footer, availability, palette, and copy registry read `capabilities`; delete the five `ref:* → artifacts_plans` shims; provider panes get their own copy group; add a `@patch` reference target. | M | **Yes — this is the unification users feel** |
| **3** | Provider spec `schema_version: 2` with `ref.pane` (+ `REF_PANE_CONFIG_KEY` in the inline allowlist, + `presentation_digest`); document chrome driven by the contract; `sase-research` ships its `pane` block. | L | **Yes — Research stops calling itself Plans** |
| **4** | Conformance test with synthetic provider; ACE-surfaced diagnostics; docs section; visual snapshot refresh. Optionally begin the `ArtifactBrowseSource` adapter migration, one built-in pane at a time, measuring navigation p95 after each. | M | No |

Phases 0, 0.5, and 4 are worth doing even if 1–3 slip. Expect
`tests/ace/tui/visual/snapshots/png/` goldens to need `--sase-update-visual-snapshots` in
Phases 2 and 3 — review those diffs rather than accepting blind. Phase 1 touches
`tests/ace/tui/test_artifacts_*` broadly, so `just check`'s scoped lane will escalate; run
`just check-full` before landing each phase.

**Risks.** Phase 2 renames 22 actions — aliases plus a doctor advisory mitigate it, but
consider a one-shot `sase config` migration that rewrites the user's file. `y` on Beads
changes from linked-issue to own-reference; correct, but a live behaviour change for the
one user of this TUI and worth a `CHANGELOG.md` line.

---

## 12. Open decisions

1. **Provider digits: stable-by-`order`, persisted allocation, or dropped?** §9.1 leaned
   toward dropping them and promoting `[` / `]`. `order`-derived digits still shift if a
   new provider's order lands between two existing ones; the fully stable option is to
   **persist the digit allocation per ref kind** so a new provider always takes the next
   free digit. With only two providers today, the recommendation is order-derived digits
   plus persisted allocation, and `[` / `]` promoted in the help modal. Confirm.
2. **Is Patches in or out?** Recommendation: out (legacy-exempt, documented), with the two
   cheap wins. If you want it in, that is its own epic with a data migration and should not
   block this one.
3. **`y` on Beads** — confirm the change from linked-issue to own-reference. It is the only
   behaviour regression in the plan.
4. **Does `ref.pane` justify a version bump?** Recommendation: bump
   `DOCUMENT_REF_PROVIDER_SPEC_SCHEMA_VERSION` `1 → 2` in `sidecar_ref_config.py`, leave
   `ARTIFACT_REF_PROVIDER_SPEC_WIRE_SCHEMA_VERSION` at `1`, and add the
   `presentation_digest` (§4). Confirm you want the bump rather than treating `pane` as an
   additive v1 key.
5. **Do typed property *values* get scheduled now or later?** Widening
   `ArtifactEntryWire.properties` from `BTreeMap<String,String>` to typed values is the one
   real `sase-core` change here, and it is what makes `updated_time` sortable and `tags:`
   filterable as a list. It is independent of Phases 0–3 and overlaps `sase-k6`'s territory
   — decide whether to fold it into that bead or keep it separate.
6. **How much lands before new sub-tab functionality?** The argument for Phases 0–2 first
   is concrete: every feature added before the verb keymap exists gets written four times
   and rewritten once.

---

## Recommended solution

Build an **`ArtifactsPaneContract` with a closed `PaneCapability` vocabulary** inside
`sase`, have all five pane families produce one, and make every downstream surface —
footer, availability, help modal, command palette, copy-mode registry, conformance test —
read the contract instead of comparing pane ids. Express the designer-facing half as a
declarative **`ref.pane` block at document-ref provider spec `schema_version: 2`**, every
key optional so existing specs are untouched, and make the already-declared
`ref.properties` and `ref.detail.fields` finally drive the detail band and filter facets.
Collapse the four per-pane verb keymaps into one verb-based keymap with
backward-compatible aliases. Behind the contract, extract one `ArtifactsSnapshotPane`
holding the loader machinery that is currently written three times, and make
`ArtifactEntryNavigator` an ABC. Enforce it with a parametrized conformance test that
iterates `resolve_artifacts_subtabs()` including a synthetic third provider, and turn
today's silent provider loss into a degraded tab that shows its own error.

Keep the layer split clean: **presentation is Python** (`sidecar_ref_config.py` and ACE),
while the one thing that genuinely belongs in `sase-core` is widening
`ArtifactEntryWire.properties` from stringly-typed to typed values — schedule that on its
own merits, extending the existing entry wire rather than inventing a second notion of
artifact identity. Do not key caches on the Rust spec digest alone; it cannot see the pane
block.

Sequence it as Phase 0 (the five live defects — same-day, and the one the owner already
reported), Phase 0.5 (parameterize the detail band by `detail.fields` — highest
value-per-line change in the whole plan, and it needs no schema work), Phase 1 (contract
type and shared pane base; pure de-duplication), Phase 2 (verb keymap and
capability-driven surfaces — the phase users feel), Phase 3 (`ref.pane` and spec-driven
document chrome — the phase where `@research` stops calling itself Plans), and Phase 4
(conformance test, ACE-surfaced diagnostics, docs).

Land Phases 0–2 before adding new sub-tab functionality. Patches stays contract-exempt and
documented as legacy, with a `@patch` copy target added regardless.
