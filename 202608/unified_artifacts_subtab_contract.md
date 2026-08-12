---
create_time: 2026-08-12
updated_time: 2026-08-12
status: research
---

# A Unified Artifacts Sub-Tab Contract

**Research question:** before adding new functionality to the ACE "Artifacts" sub-tabs
delivered by epic [`sase-js`](https://github.com/sase-org/sase--beads), how should SASE
unify them — so that users get one predictable interface across every sub-tab, and
artifact-ref type designers get a practical, enforceable contract that a new sidecar-repo
tab automatically satisfies?

**Scope and evidence.** Direct source reading of the `sase` repo at `6b139a0d4`, the
`sase-research` plugin at `f499469` (opened through `sase repo open`), the closed
`sase-js` epic bead and its nine phase beads, and the prior consolidated report
[`ref_provider_contract.md`](ref_provider_contract/ref_provider_contract.md) §9, which
is what the epic was built against. Live tab resolution was exercised through
`sase.ace.tui.artifact_tabs.resolve_artifacts_subtabs()`. This report deliberately
re-reads §9 of the prior report and reports **what actually shipped versus what was
planned**, because the gap between the two is most of the problem.

---

## Bottom line

**Six findings and one recommendation.**

1. **The epic shipped a dynamic tab *registry* but not a dynamic *pane*.** A configured
   provider gets a tab, an accent, a digit, and a working list. What it does **not** get
   is its own label in the pane chrome, its own status counters, its own hints, its own
   copy-mode targets, its own help section, or any use of the `properties` / `detail`
   blocks it declared. `@research` today renders inside a pane that calls itself
   "Plans", counts "proposals · active · archived", offers `A`pprove / `X` reject, and
   copies an "owning bead id". The provider spec is a **resolution** contract; there is
   no **presentation** contract at all (§3).

2. **The unification that exists is at the wrong layer.** `ArtifactEntryNavigator` is a
   `Protocol` that two of five panes only partially implement, and every call site
   reaches it through `getattr(pane, "...", None)` — so it documents an intent without
   enforcing it (§2.3). Meanwhile `FilterBar` (`widgets/filter_bar.py`) *is* a real,
   declarative, class-var-driven contract that all four filter bars satisfy. **`FilterBar`
   is the model to copy for the pane as a whole**, not something to replace.

3. **The keymap is the most visible inconsistency and the cheapest to fix.** 47 keymap
   entries describe four panes. Sixteen of them are four copies of the same four verbs
   (`j` / `k` / `enter` / `f`), and four more are four copies of `R`. Where the panes
   genuinely differ, the same key means different things: `s` is cycle-merges /
   cycle-status / cycle-kind, `a` is toggle-all-projects on Stitches but open-agent on
   Files, `o` is open-linked-issue on Beads but open-externally on Files, `y` is
   copy-SHA / copy-*linked-issue* / copy-reference and is absent on document panes (§2.4).

4. **Two live defects are already user-visible.** Files carries digit `4` but renders
   last, after the provider tabs (the owner reported this on the `sase-js` bead and it is
   still open); and provider digits are assigned by alphabetical position at offset 5, so
   **installing a new provider renumbers the existing ones** — the exact regression §9.1
   of the prior report warned against. A third latent defect: the first provider accent
   falls back to `#AF87FF`, which is also the pinned `ref:plan` accent, so a kind sorting
   before `plan` collides with it (§2.1).

5. **The cost of the current shape is concrete.** `widgets/artifacts/` is 13,413 lines
   across 46 code modules: 3,634 in `plan*`, 3,914 in `bead*`, 2,755 in `file*`, 2,320 in
   `commit*`, and only **691 shared**. The load-coalescing worker dance
   (`_request_load` + `on_worker_state_changed` + reload-pending + generation guards) is
   written three times, near-identically, in `beads_pane.py`, `plans_pane.py`, and
   `files_pane.py` (§2.2). Every new sub-tab feature is therefore a 3–4× edit.

6. **Provider discovery fails silently.** `_load_project_provider_records` wraps both
   the project read and the per-workspace policy resolution in bare `except Exception`
   and drops the provider. Verified live: in a workspace whose venv was stale,
   `resolve_artifacts_subtabs()` returned only the four fixed tabs, and the Plans and
   Research tabs simply were not there — no toast, no `sase doctor` finding (§2.1).

**Recommendation (§5): build an `ArtifactsPaneContract` inside sase that all five panes
satisfy, express the provider-facing half of it as a declarative `ref.pane` block at
provider-spec `schema_version: 2`, collapse the four per-pane verb keymaps into one
verb-based keymap with aliases, and gate the whole thing with a parametrized conformance
test that iterates `resolve_artifacts_subtabs()`.** Sequence it as five phases, the first
of which is a same-day defect fix. Details, phasing, and the exact designer-facing
contract are in §5.

---

## 1. What shipped versus what §9 planned

The prior report's §9 set three targets. Reading the code at `6b139a0d4`:

| §9 target | Status | Evidence |
| --- | --- | --- |
| `ArtifactsSubTab` becomes `str` + runtime registry, cached on a config token | **Done** | `artifact_tabs.py:133` `resolve_artifacts_subtabs()`, cached on `_provider_source_token()` |
| Stable ids `ref:plan` / `ref:research`, not display names | **Done** | `_provider_descriptors` builds `f"ref:{kind}"`; `LEGACY_ARTIFACTS_SUBTABS` maps `plans` → `ref:plan` |
| Persisted sub-tab naming an uninstalled provider falls back to default | **Done** | `normalize_artifacts_subtab` |
| `current_files_subtab` disappears; nested Files panes flattened | **Done** | `FILES_SUBTAB_ORDER == ()`, `cycle_files_subtab` is a no-op |
| Number keys stay stable; new tabs never renumber existing ones | **Not done** | `enumerate(sorted(by_kind, ...), start=5)` — §2.1 |
| "Collapse `plans_*` into one `ArtifactsDocumentsPane(provider)` **driven by the spec's `properties` (filter tokens) and presentation block (label, accent, grouping)**" | **Half done** | `ArtifactsDocumentsPane` exists and is instantiated per kind, but takes `provider_spec` and **never reads it**; there is no presentation block in the spec to read |
| "`research` costs zero new pane code" | **True but misleading** | It costs zero new code *and* gets zero correct chrome |
| New Files pane with version toggling and origin | **Done** | `files_pane.py`, `(` / `)` bound to `files_prev_version` / `files_next_version` |

The single most important line in §9.2 was *"driven by the spec's `properties` and
presentation block"*. `properties`, `detail`, and `identity` all exist in the spec, are
validated by `doctor/checks_config_repos.py`, are carried into `SidecarRefPolicy.spec`,
are passed to `ArtifactsDocumentsPane.__init__` as `provider_spec` — and then are read by
nothing. `grep -rn 'provider_spec' src/sase/ace/tui/widgets/artifacts/` returns only the
constructor, the assignment, and `view.py` passing it in. That is the whole gap.

---

## 2. The five pane families and where they diverge

Today's Artifacts tab hosts five kinds of pane: **Patches** (legacy Patch surface),
**Stitches** (`CommitsPane`), **Beads**, **Files**, and **Documents**
(`ArtifactsDocumentsPane`, one instance per configured ref kind). Live resolution for the
`sase` project — which configures `plans: ref.use: plan` and `research: ref.use: research`
in `sase/sase.yml` — yields:

```text
Stitches(1) │ Patches(2) │ Beads(3) │ Plans(5) │ Research(6) │ Files(4)
```

### 2.1 Tab registry, ordering, digits, and accents

`resolve_artifacts_subtabs()` (`artifact_tabs.py:133`) builds:

```python
descriptors = (
    _fixed_descriptor("stitches"),
    _fixed_descriptor("patches"),
    _fixed_descriptor("beads"),
    *providers,
    _fixed_descriptor("files"),
)
```

**Defect A — Files renders out of digit order.** `FIXED_ARTIFACTS_DIGITS` assigns Files
`"4"`, immediately after Beads, but the tuple places it after every provider. The strip
therefore reads `1 2 3 5 6 4`. This is the defect the project owner reported on the
`sase-js` bead on 2026-08-12 and it is still open. Note that
`tests/ace/tui/test_artifacts_scaffold.py:546` **asserts** `descriptor_ids[-1:] ==
("files",)`, so the fix must update that test — it currently locks the bug in.

**Defect B — provider digits are unstable.** Providers are numbered
`enumerate(sorted(by_kind, key=_natural_label_key), start=5)`. With `plan` + `research`
installed, Plans is `5` and Research is `6`. Configure a `design` sidecar and the
assignment becomes `design=5, plan=6, research=7` — every existing muscle-memory digit
shifts. §9.1 of the prior report named this explicitly: *"Unstable number keys are a
worse regression than no number keys."*

**Defect C — latent accent collision.** The fallback is
`_PROVIDER_ACCENTS[(offset - 5) % 6]`, whose element 0 is `#AF87FF` — the same value
pinned for `ref:plan` in `ARTIFACTS_ACCENTS`. Any kind sorting before `plan` takes offset
5, gets `#AF87FF`, and renders in the same colour as the Plans tab. Relatedly,
`ARTIFACTS_ACCENTS.setdefault(tab_id, accent)` mutates a module-level dict during
resolution, and `reset_artifacts_subtabs_cache()` does not undo it, so a kind removed
from config keeps its accent entry for the life of the process.

**Defect D — silent provider loss.** `_load_project_provider_records` catches
`Exception` around `list_project_records` (returning `[]`) and around the entire
per-workspace policy block (`continue`). Verified live in a workspace with a stale venv:
`resolve_artifacts_subtabs()` returned exactly the four fixed tabs and the Plans and
Research tabs vanished with no diagnostic anywhere. A user cannot distinguish "not
configured" from "broken".

### 2.2 Lifecycle and loading

`ArtifactsPaneLifecycle` (`lifecycle.py`, 60 lines) is a clean shared seam:
`activate()` / `deactivate()` / `request_refresh()` dispatching to `on_first_activate` /
`on_activate` / `on_deactivate` / `on_refresh`. Every pane uses it. That part works.

What is **not** shared is everything underneath it. `beads_pane.py`, `plans_pane.py`, and
`files_pane.py` each carry their own copy of the same off-thread coalescing machine:
`_loading` / `_reload_pending` / `_force_pending` flags, a `_request_load(force=...)` that
early-returns into the pending flags, a `run_worker(task, thread=True, exclusive=False,
exit_on_error=False)`, and an `on_worker_state_changed` that checks worker identity,
classifies terminal states, validates `result.project == self.project_scope`, preserves
the selected id, calls `_cancel_artifacts_jump_mode_for_model_change`, and replays the
pending request through `call_later`. Files adds generation counters and a `full` flag;
Stitches replaces it with `CommitsCollectionMixin`. Roughly 200 lines triplicated, and
three places to fix any bug in it.

The panes also disagree on activation semantics without any stated reason:

| Pane | `on_activate` behaviour |
| --- | --- |
| Beads | always `_request_load(force=False)` |
| Documents | reload only if snapshot missing or project changed; else schedule deep archive |
| Files | reload only if not already loading **and** snapshot missing or project changed |
| Stitches | always `_schedule_collection()` |
| Patches | just refocus the list |

### 2.3 The navigation protocol is advisory, not enforced

`ArtifactEntryNavigator` (`entry_navigation.py`) declares seven methods.
Actual conformance:

| Method | Beads | Documents | Files | Stitches | Patches |
| --- | :-: | :-: | :-: | :-: | :-: |
| `entry_targets` | ✓ | ✓ | ✓ | ✓ | — |
| `selected_entry_target` | ✓ | ✓ | ✓ | ✓ | — |
| `select_entry_target` | ✓ | ✓ | ✓ | ✓ | — |
| `apply_entry_jump_hints` | ✓ | ✓ | ✓ | ✓ | — |
| `apply_entry_marks` | ✓ | ✓ | ✓ | ✓ | — |
| `request_entry_target` | ✓ | ✓ | **✗** | **✗** | — |
| `conditional_footer_entries` | ✓ | ✓ | **✗** | **✗** | — |

`ArtifactsView.entry_navigator()` raises for Patches by design. The two missing methods
are papered over at every call site with `getattr(pane, "request_entry_target", None)` and
`getattr(pane, "conditional_footer_entries", None)`. The user-visible consequence:
**cross-pane deep links and conditional footer hints work on Beads and Documents and
silently do nothing on Files and Stitches.** There is no cross-pane test that would catch
a sixth pane forgetting a method.

### 2.4 Keymaps: 47 entries, four copies of five verbs, four key collisions

`app_keymaps.py:38-88` declares 47 pane-scoped actions. Grouped by whether the verb is
shared or genuinely pane-specific:

| Verb | Stitches | Documents | Beads | Files |
| --- | --- | --- | --- | --- |
| next / prev | `j` / `k` | `j` / `k` | `j` / `k` | `j` / `k` |
| open selected | `enter` | `enter` | `enter` | `enter` |
| filters | `f` | `f` | `f` | `f` |
| refresh | `R` | `R` | `R` | `R` |
| copy primary | `y` (SHA) | **absent** | `y` (*linked issue*) | `y` (reference) |
| copy secondary | — | — | — | `Y` (stored path) |
| cycle a facet | `s` (merges) | — | `s` (status) | `s` (kind) |
| open externally | — | — | `o` (*linked issue*) | `o` (file) |
| `a` | toggle all projects | — | — | open producing agent |
| go to linked | — | `L` (bead) | `L` (plan) | — |
| pane-specific | `d` sidecars, `F` fetch | `A`/`X` approve/reject | `l`/`h` expand, `e`/`N`/`n`/`c`/`z`/`w` | `Z` viewer, `(`/`)` versions |

Four observations:

- **Twenty of the 47 entries are duplicates of five shared verbs.** They can only ever be
  configured to differ, never to agree — rebinding "next" means editing four keys.
- **`y` is the worst offender.** On Stitches and Files it copies the row's own identity;
  on Beads it copies a *linked external issue reference*, and copying the bead's own id
  requires copy mode (`% %`). On document panes `y` does nothing at all.
- **`o` and `a` are outright collisions** — the same key, unrelated verbs, adjacent tabs.
- **Document panes are missing verbs that are obviously wanted for research documents**:
  no open-externally, no copy-path, no copy-reference outside copy mode.

The action names are also leaky: every document pane, including `@research`, is driven by
`plans_next`, `plans_filters`, `plans_approve`, `plans_reject`, `plans_open_bead`. The
help modal has already been generalized to say "Document Panes", but the keys inside it
still read `plans_*` and two of them are plan-only — `_app_action_availability.py:139`
disables `plans_approve` / `plans_reject` / `plans_open_bead` unless
`pane.provider_kind == "plan"`, and `artifacts_plans.py` also notifies *"Plan proposal
approval is only available for plans"* if you get there anyway.

### 2.5 Filters: one good abstraction, four grammars, two arbitrary gaps

`widgets/filter_bar.py::FilterBar` is the best thing in this subsystem. It is a
Static-based inline query editor with a fully declarative subclass surface:
`ACCENT`, `KEY_COMPLETIONS`, `STATIC_VALUE_COMPLETIONS`, `VALUE_HINTS`,
`REPEATABLE_VALUE_KINDS`, `NEGATABLE_KEYS`, `FREE_TEXT_HINT`, `PERSISTENT`, plus one
abstract `_completion_context`. All four bars subclass it in under 100 lines each.
`sase/filter_tokens.py` shares the tokenizer and error type across all four grammars.

The gaps are in what the subclasses declare, not in the abstraction:

| | Stitches | Documents | Beads | Files |
| --- | --- | --- | --- | --- |
| `NEGATABLE_KEYS` | repo, author, origin | all repeatable | all repeatable | **unset — no `-key:` at all** |
| `PERSISTENT` | **`True`** | `False` | `False` | `False` |
| Values type | `CommitLogFilterValues` | `PlanFilterValues` | `BeadFilterValues` | `FilesFilterValues` |
| `excluded_*` fields | yes | yes | yes | **none** |
| `ACCENT` | `stitches` | **`plans`, hard-coded** | `beads` | `files` |

So negation silently works on three panes and not the fourth; the filter line is
permanently visible on one pane and hidden behind `f` on the other three; and a Research
tab's filter bar is coloured with the Plans accent because `plan_filter_bar.py:31` reads
`ARTIFACTS_ACCENTS["plans"]` at class-definition time.

Four separate `FilterValues` dataclasses is *not* obviously wrong — the facets really do
differ. But the **document** grammar (`PlanFilterValues`: kinds, statuses, tiers,
projects, since/until, text) is plan-shaped and fixed, so a `research` provider that
declares `properties: {status, tags, create_time, updated_time}` gets `tier:` (meaningless)
and no `tags:` (meaningful).

### 2.6 Copy mode: the `ref:*` → `artifacts_plans` shim, in three places

Copy mode has five per-pane groups. Provider panes have none of their own; the mapping
`ref:<anything>` → `artifacts_plans` is hard-coded **three separate times**:

- `copy_targets.py:512` `_normalize_copy_group`
- `commands/availability.py:225` `_artifacts_copy_group`
- `actions/clipboard/_artifacts.py:31` `_copy_group_for_artifacts_subtab`

The consequence is that `% %` on a Research row copies *"the owning bead id"* and `% d`
copies *"design reference"* — both plan-only concepts.

Within the groups, the keys drift for no reason:

| Target | Stitches | Documents | Beads | Files |
| --- | --- | --- | --- | --- |
| `@ref` | `@` | `@` | `@` | `@` |
| handoff | `!` | `!` | `!` | `!` |
| Markdown link | `l` | `l` | `l` | **`L`** |
| metadata JSON | `J` | `J` | `J` | **`j`** |
| snapshot | `s` | `s` | `s` | `s` |
| primary (`%`) | SHA | **bead id** | bead id | contents |

And **Patches has no `@ref` target at all** — `@patch:<name>` is a live ref kind
(`docs/artifact_references.md`), the Patches pane is inside the Artifacts tab, and there
is no way to copy `@patch:` for the selected Patch. Its copy group is
`raw / with_snapshot / bug / pr_number / name / link / spec / snapshot`; no `reference`,
no `handoff`, no `json`.

### 2.7 The detail band ignores the spec that describes it

`ArtifactsDocumentsPane` renders a properties band (`#plans-detail-properties`) fed by
`plans_detail.py`, which composes properties via
`sase.sdd.plan_properties.ordered_plan_property_items` and hard-codes rows like
`("Owning bead", ...)`, `("Bead status", ...)`, `("Design reference", ...)`, `("Tier", ...)`.

Meanwhile the provider spec already declares exactly this:

```python
# sase_research/provider.py
"properties": {
    "create_time":  {"type": "datetime",    "source": "markdown_frontmatter"},
    "updated_time": {"type": "datetime",    "source": "markdown_frontmatter"},
    "status":       {"type": "string",      "source": "markdown_frontmatter"},
    "tags":         {"type": "string_list", "source": "markdown_frontmatter"},
},
"detail": {"fields": ["status", "create_time", "updated_time", "tags"]},
```

`detail.fields` is a field whose entire purpose is "which properties the detail view
shows, in order". Nothing reads it. Making the properties band and filter facets read
`ref.properties` + `ref.detail.fields` is the single highest value-per-line change
available, and it needs **no spec change at all**.

The rest of the chrome is equally plan-shaped. For a Research tab, `plans_rendering.py`
produces: a `" Plans "` chip in the pane header; a status line reading
`N proposals · N active · N archived`; a hint bar advertising approve/reject; and an empty
state reading `# Plans / Select a proposal, active plan, or archived plan.`

### 2.8 The long tail: help, footer, palette, CSS, action allowlists

- **Help modal** (`help_modal/patches_artifact_bindings.py`) has one hard-coded section
  per pane, plus a literal `"1 / 2 / 3 / 4"` row. A new provider gets no section and
  inherits the plan-only rows in "Document Panes".
- **Action allowlist.** `NON_PRS_ARTIFACT_ACTIONS` is a static frozenset union of four
  hard-coded per-pane sets plus `{f"show_artifacts_{s}" for s in
  FIXED_ARTIFACTS_SUBTAB_ORDER}`. A pane action not added here is silently dead. Provider
  tabs get no `show_artifacts_<kind>` action at all — only `show_artifacts_digit`.
- **Availability** (`_app_action_availability.py`) is a linear chain of
  `if action in X_ARTIFACT_ACTIONS and pane_key != "x": return False`, one arm per pane.
- **Stylesheet.** `styles.tcss` carries near-identical `#plans-*`, `#beads-*`, `#files-*`,
  `#stitches-*` rule blocks; `#plans-*` and `#beads-*` are already partly merged, which
  shows the merge is safe.
- **Tests.** There is no pane-contract test. The closest is
  `test_artifacts_marking.py`, parametrized over `["stitches", "beads", "ref:plan",
  "files"]` — a hard-coded list, not `resolve_artifacts_subtabs()`, so a new provider is
  never exercised.

---

## 3. The provider spec is a resolution contract, not a presentation contract

This is the root cause, stated plainly. `schema_version: 1` of the ref provider spec
describes **how a reference resolves and publishes**:

```yaml
ref:
  kind: research
  expansion_format: "the {checkout_path} file in the {sidecar_role} artifact repo"
  properties:  {...}        # typed frontmatter schema
  detail:      {fields: [...]}
  identity:    {}
  inventory:   {globs: [...]}
  publication: {link: vcs_permalink, referenced_by: markdown_table}
```

Every one of those keys answers a question about prompt expansion, use recording, or
back-link publication. **None answers a question about the ACE pane**, except `detail`,
which answers one and is ignored. There is nowhere for a designer to say what the tab is
called, where it sits, what colour it is, how rows group, which facets are filterable,
or which verbs the pane supports.

So `view.py:103` compensates with an `if/elif` ladder on `descriptor.id` and
`descriptor.provider_kind == "plan"`, and everything downstream compensates with
`startswith("ref:")` special cases. That is not a missing feature in one module; it is a
missing layer.

The prior report's §4 already settled the shape this layer must take: *"Declarative-first
provider spec... Plugins do not get per-resolution callbacks on the launch, completion,
or TUI paths. `sase-research` ships ~60 lines of metadata and zero resolution code."*
A plugin therefore **cannot** ship a Textual widget, and the presentation contract must
be data. That constraint is a feature: it forces the pane to be general.

---

## 4. Options considered

**Option A — Leave the panes alone; fix only the two live defects.**
Cheapest (a day). Does nothing for the user-facing inconsistency or the 3–4× edit cost,
and the next provider still renders as "Plans". Rejected as a stopping point, but its
content is worth doing *first* — it becomes Phase 0.

**Option B — Shared Python base class only.** Extract `ArtifactsSnapshotPane` with the
loader/coalescing/lifecycle, make `ArtifactEntryNavigator` an ABC, unify the keymap.
Removes the triplication and the protocol drift. Does **not** fix the presentation
problem, because the base class has nothing to read: the document pane still hard-codes
plan chrome. Necessary but not sufficient.

**Option C — Fully declarative pane, spec-driven end to end.** Add a `ref.pane` block and
render every pane from it, including Beads and Stitches. Maximal uniformity, but Beads
(epic expand/collapse, issue mode, status mutation, launch) and Stitches (timeline graph,
diff loader, fetch) carry irreducible behaviour that no JSON block will express. Pushing
them through a declarative renderer would either bloat the schema into a UI toolkit or
lose function. Rejected.

**Option D — Capability registry + declarative presentation (recommended).** Two layers:
a Python-side `ArtifactsPaneContract` that *all five* panes produce, and a declarative
`ref.pane` block that a **plugin-configured** provider fills in, which sase converts into
that same contract. Built-in panes construct their contract in Python and may declare
capabilities the schema cannot express; provider panes construct theirs from data. The
action layer, footer, help modal, copy registry, palette, and conformance test all read
the contract and never special-case a pane id again.

Option D is the one that makes both halves of the request true at once: users see one
interface because one contract drives the chrome, and designers get a contract because
that same contract is what they fill in.

---

## 5. Recommended solution

### 5.1 Layer 1 — `ArtifactsPaneContract` (in `sase`, not in the spec)

One frozen dataclass, produced for every descriptor returned by
`resolve_artifacts_subtabs()`, living beside `ArtifactsTabDescriptor` in
`artifact_tabs.py` (which is already widget-free — keep it that way):

```python
@dataclass(frozen=True, slots=True)
class ArtifactsPaneContract:
    # identity — already on ArtifactsTabDescriptor, folded in
    id: str                          # "beads", "ref:research"
    label: str                       # "Beads", "Research"
    accent: str
    pane_id: str
    order: int                       # stable sort key; digits derive from this
    digit_shortcut: str | None

    # data
    ref_kind: str | None             # None for panes with no @kind (patches)
    target_prefix: str               # entry-target tuple[0], e.g. "bead", "research"
    project_scoped: bool

    # capabilities — the vocabulary the shared action layer knows
    capabilities: frozenset[PaneCapability]

    # presentation
    row_title: str | None            # property name, or None for pane-owned rendering
    detail_fields: tuple[str, ...]   # ordered property names for the detail band
    filter_facets: tuple[FilterFacet, ...]
    date_property: str | None
    status_counters: tuple[StatusCounter, ...]
    empty_state: EmptyState
    filter_bar_persistent: bool
    copy_targets: tuple[CopyTargetSpec, ...]
```

`PaneCapability` is a closed enum of verbs the shared layer implements — `OPEN`,
`FILTER`, `REFRESH`, `MARK`, `JUMP`, `SCOPE_PROJECT`, `COPY_REFERENCE`, `COPY_PATH`,
`COPY_LINK`, `COPY_JSON`, `OPEN_EXTERNAL`, `OPEN_AGENT`, `LINK_JUMP`, `VERSIONS`,
`EXPAND_TREE`, `CYCLE_FACET`, `MUTATE`, `APPROVE`. A pane's footer, help section, palette
entries, copy-mode rows, and action availability all derive from this set. Nothing
downstream ever compares a pane id again.

Built-in panes get their contract from a module-level table in Python and are free to
declare `MUTATE` / `EXPAND_TREE` / `VERSIONS`. Provider panes get theirs from §5.3, and
the schema deliberately cannot request `MUTATE` or `APPROVE`.

### 5.2 Layer 2 — one verb-based keymap

Replace the four copies of each shared verb with one:

| New action | Replaces | Default |
| --- | --- | --- |
| `artifacts_next` | `stitches_next`, `plans_next`, `beads_next`, `files_next` | `j` |
| `artifacts_prev` | ×4 | `k` |
| `artifacts_open` | `*_view_selected` ×4 | `enter` |
| `artifacts_filters` | `*_filters` ×4 | `f` |
| `artifacts_refresh` | `*_refresh` ×4 | `R` |
| `artifacts_copy_reference` | `stitches_copy_sha`, `files_copy_reference` | `y` |
| `artifacts_copy_path` | `files_copy_path` | `Y` |
| `artifacts_open_external` | `files_open_external` | `o` |
| `artifacts_link_jump` | `plans_open_bead`, `beads_open_plan` | `L` |
| `artifacts_cycle_facet` | `stitches_cycle_merges`, `beads_cycle_status`, `files_cycle_kind` | `s` |

Twenty-two entries collapse to ten. Keep the old names as **aliases** in the keymap
loader so existing `~/.config/sase/sase.yml` overrides keep working, and emit a
`sase doctor` advisory naming the replacement. Rename the remaining `plans_*` actions to
`documents_*` under the same alias policy — `plans_approve` / `plans_reject` stay
plan-only and become `documents_approve` / `documents_reject`, still gated on
`provider_kind == "plan"` via the `APPROVE` capability.

Three deliberate consequences: `y` copies the row's **own** reference on every pane
(Beads' current `y` becomes `beads_copy_linked_issue`, which is what it always was);
`o` opens the selected row's underlying artifact on every pane that declares
`OPEN_EXTERNAL`, so document panes gain it for free; and Stitches' `a`
(toggle-all-projects) moves off `a`, freeing it for `OPEN_AGENT` uniformly.

### 5.3 Layer 3 — the provider-facing contract: `ref.pane` at `schema_version: 2`

This is the artifact a ref-type designer writes. Everything is optional; every default is
derivable, so `schema_version: 1` specs keep working unchanged.

```yaml
ref:
  kind: research
  # ... existing schema_version 1 keys ...
  properties:
    status:       {type: string,      source: markdown_frontmatter}
    tags:         {type: string_list, source: markdown_frontmatter}
    create_time:  {type: datetime,    source: markdown_frontmatter}
    updated_time: {type: datetime,    source: markdown_frontmatter}
  detail: {fields: [status, create_time, updated_time, tags]}

  pane:
    label: Research               # default: titleized, pluralized kind
    accent: "#5FAFFF"             # default: allocated, collision-checked
    order: 60                     # default: 50 + config order; digits derive from this
    row:
      title: title                # a property name, or `filename`
      badges: [status, tags]      # properties rendered as row chips
      timestamp: create_time      # drives the row's relative-age column
    group_by: year                # none | year | month | status | <property>
    filters:
      facets: [status, tags, project]   # default: every `properties` key + project
      date_property: create_time        # default: first datetime property
    capabilities: [open_external, copy_path, copy_link]   # additive, from a safe subset
    empty_state:
      title: Research
      body: "Select a research report from the research sidecar."
```

Guarantees, stated as the designer-facing contract:

**What you must declare:** `ref.kind` and an `inventory.globs`. Nothing else.

**What you get for free, identically to every other tab:** a tab in the strip with a
stable digit and a non-colliding accent; lazy activation and off-thread loading with
coalescing; the shared project scope (`p`); `j`/`k`/`enter`/`f`/`R`; marks (`space`,
`clear_marks`), hint-jump (`'`), and detail scrolling; a filter bar with completion,
negation, `since:` / `until:`, and free text; a copy-mode group with `@ref`, handoff,
Markdown link, path, title, body, JSON, and snapshot; a help-modal section generated from
your capability set; command-palette entries; `@kind:<path>` round-tripping through
`reference_for_entry_target`; and `Referenced By` write-back.

**What you may declare:** the row template, grouping, filter facets, detail field order,
empty-state copy, and any capability in the safe subset
`{open_external, open_agent, copy_path, copy_link, link_jump, cycle_facet, versions}`.

**What you cannot have:** mutation actions, approval flows, bespoke widgets, per-row
Python callbacks, or a resolution hook. Anything needing those is a built-in pane, and
that is a sase change, not a plugin change.

Two concrete wins land immediately from this: `sase-research` becomes a correct Research
tab with ~12 added lines of YAML-shaped metadata and zero Python; and `plan` stops being
special — the builtin plan provider declares
`capabilities: [approve, link_jump]`, `group_by: status`, and the proposal/active/archive
counters, and `ArtifactsPlansPane` disappears as a distinct class.

### 5.4 Layer 4 — enforcement

**A parametrized conformance test** — `tests/ace/tui/test_artifacts_pane_contract.py` —
that iterates `resolve_artifacts_subtabs()` (not a hard-coded list) and, for each
descriptor, mounts the pane and asserts: all seven `ArtifactEntryNavigator` methods exist
and are callable; a copy group is registered and every declared target resolves; a help
section is generated; the filter bar declares `NEGATABLE_KEYS` covering its repeatable
keys; `conditional_footer_entries()` returns action names that exist in the keymap and in
`NON_PRS_ARTIFACT_ACTIONS`; the digit shortcut is unique and matches strip position; the
accent is unique; and a synthetic row round-trips through `reference_for_entry_target`.
Add a session-scoped fixture that registers a **synthetic third provider** so the suite
proves the contract on a kind no built-in code knows about.

**A `sase doctor` check** under `-C config.repos`: report a configured sidecar whose ref
provider is missing or whose spec fails validation, instead of dropping the tab silently
(Defect D). Replace the two bare `except Exception` blocks in
`_load_project_provider_records` with narrow catches that record a diagnostic on the
descriptor, and render a degraded tab with the error in its empty state rather than no
tab at all.

**A docs section** in `docs/artifact_references.md` — "What a provider gets in ACE" —
that is the §5.3 table verbatim. That file currently documents resolution and publication
and says nothing about the tab.

### 5.5 Phasing

| Phase | Content | Size | User-visible |
| --- | --- | --- | --- |
| **0** | Defects A–D: Files renders at position 4; provider digits derive from a stable `order`, never renumbering an existing tab; provider accents allocated with a collision check against `ARTIFACTS_ACCENTS`; narrow the two `except Exception` blocks and surface a diagnostic. Update `test_artifacts_scaffold.py:546`. | S | Yes — fixes the reported bug |
| **1** | `ArtifactsPaneContract` + `PaneCapability`; `ArtifactsSnapshotPane` base absorbing the triplicated loader/coalescing; `ArtifactEntryNavigator` becomes an ABC; Files and Stitches gain `request_entry_target` and `conditional_footer_entries`. | L | No (pure de-dup) |
| **2** | Verb keymap with aliases; `plans_* → documents_*`; footer, availability, palette, and copy registry read `capabilities` instead of pane ids; delete the three `ref:* → artifacts_plans` shims; give provider panes their own copy group; add a `@patch` reference target to the Patches group. | M | Yes — this is the unification users feel |
| **3** | Spec `schema_version: 2` with `ref.pane`; properties band and filter facets read `ref.properties` + `ref.detail.fields`; document-pane chrome (label, counters, hints, empty state) driven by the contract; `sase-research` ships its `pane` block. | L | Yes — Research stops calling itself Plans |
| **4** | Conformance test with synthetic provider; doctor check; `docs/artifact_references.md` section; visual snapshot refresh. | M | No |

Phases 0 and 4 are worth doing even if 1–3 slip. Phase 2 is where the "similar interface
for each" promise is actually delivered; Phase 3 is where the "practical contract for
designers" promise is.

`sase/memory/tui_perf.md` governs Phases 1 and 3 — read it before implementing. The
contract must not turn lazy panes eager: keep `ContentSwitcher` + `activate()`-on-visible,
keep one worker per pane, and key any new inventory cache on
(provider-spec digest, project config token, repo HEAD). Expect
`tests/ace/tui/visual/snapshots/png/` goldens to need `--sase-update-visual-snapshots`
in Phases 2 and 3.

---

## 6. What should stay different

Uniformity is not the goal; *predictability* is. These divergences are correct and the
contract should express them rather than erase them:

- **Beads' mutation surface** (`e`, `N`, `n`, `c`, `z`, `w`, issue mode). Beads is the one
  pane that writes to its corpus. Capability `MUTATE`, built-in only.
- **Stitches' timeline and diff loader.** A commit graph is not a list of documents.
  Keep `CommitsTimeline`; expose it through the same contract.
- **Files' version toggling** (`(` / `)`). Genuinely file-specific today — but declare it
  as capability `VERSIONS` rather than hard-coding it, because a git-backed document
  provider could reasonably want it later.
- **Stitches' persistent filter bar.** Defensible for a timeline where the query *is* the
  view. Make it the declared `filter_bar_persistent: true` rather than an accident of
  `PERSISTENT = True` on one subclass, so the difference is a decision on the record.
- **Patches.** Recommend declaring it **contract-exempt (legacy)** and saying so in the
  docs: it predates the Artifacts tab, uses the separate ACE query language, has its own
  selection and marking model, and folding it in is a much larger change with a data
  migration. Give it the two cheap wins anyway — a `@patch` copy-reference target and a
  help-modal note that it does not participate in project scope — and revisit after
  Phase 3.

---

## 7. Risks

- **Keymap churn.** Phase 2 renames 22 actions. Mitigated by aliases plus a doctor
  advisory, but any personal `sase.yml` binding `beads_next` will keep working while
  silently no longer being the canonical name. Consider a one-shot `sase config` migration
  that rewrites the user's file.
- **`y` semantics change on Beads.** Today `y` copies the *linked issue* ref; after
  Phase 2 it copies the bead's own `@bead:` ref. This is the correct behaviour and matches
  the other three panes, but it is a live behaviour change for the one user of this TUI
  and should be called out in `CHANGELOG.md`.
- **Snapshot goldens.** Phases 2–3 will move chrome text on four panes. Budget for
  `just test-visual --sase-update-visual-snapshots` and review the diffs rather than
  accepting blind.
- **Scope creep into Rust.** `ref.pane` is presentation, so it belongs in the Python spec
  normalizer (`sidecar_ref_config.py`) and the ACE layer, **not** in
  `sase-core`'s wire types — per the `rust_core_backend_boundary` rule, this is
  Textual-presentation state, which the rule places on the Python side. Do not bump the
  artifact-ref wire schema for it; bump only
  `DOCUMENT_REF_PROVIDER_SPEC_SCHEMA_VERSION` (currently `1`) in `sidecar_ref_config.py`.
  A future web or editor frontend that needs the same tab metadata is the trigger to
  reconsider, and `pane` being pure data makes that move cheap.
- **Test-suite size.** Phase 1 touches `tests/ace/tui/test_artifacts_*` broadly. Expect
  `just check`'s scoped lane to escalate; run `just check-full` before landing each phase.

---

## 8. Open decisions for you

1. **Digits for provider tabs: stable-by-`order`, or drop them?** §9.1 of the prior
   report leaned toward dropping them and promoting `[` / `]`. Recommendation above keeps
   them but derives them from a declared `order`, because you have only two providers and
   digits are fast. Confirm which you prefer.
2. **Is Patches in or out?** Recommendation is out (legacy-exempt, documented). If you
   want it in, that is its own epic with a data migration and should not block this one.
3. **`y` on Beads.** Confirm the change from linked-issue to own-reference; it is the
   only behaviour regression in the plan.
4. **Does `ref.pane` justify a spec major bump?** Recommendation is
   `DOCUMENT_REF_PROVIDER_SPEC_SCHEMA_VERSION: 1 → 2` with full backward compatibility
   (every `pane` key optional and defaulted). Confirm you want the bump rather than
   treating `pane` as an additive `schema_version: 1` key.
5. **How much of Phase 2 should land before you add new sub-tab functionality?** The
   argument for landing at least Phases 0–2 first is that every new feature added before
   the verb keymap exists gets written four times and then has to be rewritten once.

---

## Recommended solution

Adopt **Option D**. Build an `ArtifactsPaneContract` with a closed `PaneCapability`
vocabulary inside `sase`, have all five pane families produce one, and make every
downstream surface — footer, availability, help modal, command palette, copy-mode
registry, conformance test — read the contract instead of comparing pane ids. Express the
provider-facing half as a declarative `ref.pane` block at document-ref provider spec
`schema_version: 2`, keeping every key optional so existing specs are untouched, and make
the already-declared `ref.properties` and `ref.detail.fields` finally drive the detail
band and filter facets. Collapse the four per-pane verb keymaps into one verb-based
keymap with backward-compatible aliases. Enforce all of it with a parametrized
conformance test that iterates `resolve_artifacts_subtabs()` and includes a synthetic
third provider, plus a `sase doctor` check that turns today's silent provider loss into a
finding.

Sequence it as Phase 0 (fix the reported Files-ordering defect, stable provider digits,
accent collisions, silent provider loss), Phase 1 (contract type and shared snapshot-pane
base; pure de-duplication), Phase 2 (verb keymap and capability-driven surfaces — this is
the phase users feel), Phase 3 (`ref.pane` and spec-driven document chrome — this is the
phase where `@research` stops calling itself Plans), and Phase 4 (conformance test,
doctor check, and a "What a provider gets in ACE" section in
`docs/artifact_references.md`). Land Phases 0–2 before adding new sub-tab functionality,
because features added before the verb keymap exists must be written four times and
rewritten once.
