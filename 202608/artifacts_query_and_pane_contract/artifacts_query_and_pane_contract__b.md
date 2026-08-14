---
create_time: 2026-08-14
updated_time: 2026-08-14
status: research
tags: [ace, artifacts, artifact-refs, patch, contract, query-language, tui]
---

# A Unified Artifacts Pane Contract, With Patch Inside It

**Research question.** Unify every ACE Artifacts sub-tab behind one API/contract so a
sidecar or artifact repo can declare how its tab behaves, and so any new sub-tab feature
is implemented once and inherited by every configured provider — including providers
belonging to users we will never see. **Patch is in scope**, and must be migrated to the
same look and feel as its siblings. Before that migration, generalize the Patch pane's
best features — the boolean search syntax, saved queries, the ancestors/children/siblings
jumpers — so they become contract features rather than Patch features.

**Scope and evidence.** Source read at `sase` `e4baf0771` (master, clean) and `sase-core`
`4170150` (`v0.27.2`, opened via `/sase_repo`). Every defect and behavioural claim below
was re-verified by executing code in workspace `sase_12` after `just install`, not
inferred from reading. This report supersedes and extends
[`artifacts_pane_contract.md`](../artifacts_pane_contract/artifacts_pane_contract.md)
(2026-08-12, written at `888453d39`); §1 records exactly what changed underneath it,
because roughly half of that report's defect inventory has since been fixed and one of
its central recommendations — keep Patch out — is the thing the owner has now overruled.

---

## Bottom line

The prior report excluded Patch on the grounds that it "uses the separate ACE query
language" and "has its own selection and marking model". That framing inverts the
problem. **Patch is not an exception because it owns a query language — the query
language is the single most valuable asset in the Artifacts tab, and the reason to bring
Patch in is to take it away from Patch.** Once querying is a contract layer instead of a
pane feature, the only genuinely Patch-shaped things left are mutation verbs and PR
lifecycle, and those are already covered by the `MUTATE` capability that Beads needs
regardless.

So the contract is **five layers, in strict dependency order**. Each is independently
landable and each is useless without the one below it:

| Layer | What it fixes | Who declares it |
| --- | --- | --- |
| **L0 · Identity** | One stable `ArtifactEntryTarget` per row on *every* pane. Patches' `set[int]` marks and `int` jump anchors become targets. | Host, built-in |
| **L1 · Pane contract** | `ArtifactsPaneContract` + closed `PaneCapability`. Footer, availability, help, palette, copy registry stop comparing pane ids. | Host table + provider spec |
| **L2 · Query** | One field-schema-driven query engine replacing three dialects; one inline filter bar; saved slots, history and selection memory namespaced per pane. | Provider `properties` + host schema |
| **L3 · Relations** | `<` / `>` / `~` jumpers generalized to named relation families over any pane's graph, including the query-rewrite fallback. | Provider `relations` block |
| **L4 · Presentation** | The declarative `ref.pane` block: row template, grouping, sort, facets, empty state, safe capability subset. | Provider, no code |

**Patch joins at L0–L3 as a built-in pane and never gets an L4 spec** — `patch` is a
reserved ref kind in `sase-core` (`provider_spec.rs:27`), so it can never be a document
provider, and it should not pretend to be. It consumes the contract; it does not declare
one.

Three findings change the plan the prior report proposed:

1. **There are three query languages, not two, and one of them is a fork of another.**
   `sase/ace/agent_query/tokenizer.py:1-11` says so in its own docstring: *"Adapted from
   `sase.ace.query.tokenizer`."* The fork already added the one thing the unified design
   needs — a **typed property-key registry** (substring / enum / bool / duration). Most of
   the L2 abstraction has already been written once, by hand, for the Agents tab.
2. **The Rust wire schema version must not be bumped**, and the reason is documented in
   the crate (`provider_spec.rs:18-25`): CI installs the *published floor* `sase-core-rs`
   and runs it against the checkout, so a `schema_version: 2` spec would be rejected before
   the core carrying the bump ships. This makes the prior report's "Python-side
   presentation digest" not merely prudent but mandatory, and it kills the option of
   modelling `ref.pane` in Rust at all for now.
3. **The generic fold registry the contract needs already exists and is already shared.**
   `models/group_fold.py:1` — *"Generic per-group fold registry, shared by Agents and
   Patches"* — keyed on `tuple[str, ...]`, the exact shape of `ArtifactEntryTarget`. The
   grouping/folding layer needs a third consumer, not a design.

Sequence: **L0 first** (mechanical, invisible, unblocks everything), then L1, then L2 —
and land L2 *before* adding any new sub-tab functionality, because every feature added
before the query layer exists gets written five times.

---

## 1. What changed under the prior report

Re-verified at `e4baf0771`. Half the defect inventory is fixed; the half that is left is
the half that matters for this epic.

| Prior finding | Status now | Evidence |
| --- | --- | --- |
| **A** — Files renders out of digit order | **Fixed** | `artifact_tabs.py:144` `_assign_artifacts_digit_shortcuts` numbers by visual position with Files last; `tests/ace/tui/test_artifact_tab_digits.py` locks the invariant. Live: `stitches(1) patches(2) beads(3) ref:plan(4) ref:research(5) files(6)` |
| **B** — provider digits unstable | **Fixed** | Digits are positional, not `enumerate(sorted(...), start=5)` |
| **C** — accent collision + leaky module global | **Live, and worse than reported** | See below |
| **D** — provider discovery fails silently and caches the degraded result | **Live, reproduced** | See below |
| **E** — `_provider_label` produces "Researchs" | **Fixed** | Labels are now singular by design (`bd6167875 feat(ace): rename Artifacts sub-tab labels to singular form`). Live: `Stitch, Patch, Bead, Plan, Research, File` |
| §9's "Patches stays contract-exempt" | **Overruled by the owner** | This report, §6 |
| `provider_spec` stored but never read | **Unchanged** | `grep -rn provider_spec src/sase/ace/tui/` → 10 hits: two dataclass fields, one assignment (`plans_pane.py:67`), and `view.py` passing it in. Nothing reads it for presentation |
| "the `ref:*` → `artifacts_plans` shim is hard-coded in five places" | **Understated — 13 sites** | `_app_action_availability.py:139`, `copy_targets.py:511,513`, `_keybinding_modes.py:500,505`, `view.py:203`, `clipboard/_palette.py:40`, `clipboard/_artifacts.py:31,46,104`, `clipboard/_palette_artifact_previews.py:63`, `clipboard/_palette_artifacts.py:95,132,162,171,228,249`, `actions/base.py:465`, `artifacts_plans.py:37` |

New since that report: tab icons (`ref.icon`, `DEFAULT_DOCUMENT_TAB_ICON`, validated in
Rust `validate_tab_icon`), Artifacts split modes (`{` / `}`), and singular tab labels.

### 1.1 Defect C is now three defects

Executed live:

```text
providers = [design, plan, research]
  ref:design    accent=#AF87FF     <-- collides with ref:plan
  ref:plan      accent=#AF87FF
  ref:research  accent=#5FD7AF

providers = [plan, research]
  ref:plan      accent=#AF87FF
  ref:research  accent=#5FAFFF     <-- different accent for the same provider
```

- **Collision.** `_PROVIDER_ACCENTS[0]` is `#AF87FF`, the value pinned for `ref:plan` in
  `ARTIFACTS_ACCENTS`. Any kind sorting before `plan` renders in the Plans colour
  (`artifact_tabs.py:77-84,331-334`).
- **Instability (new).** Accents are assigned by `index % 6` over the sorted kind list, so
  installing a `design` sidecar silently repaints `research` from `#5FAFFF` to `#5FD7AF`.
  This is the *same* class of bug as Defect B, fixed for digits and left in place for
  accents.
- **Module-global leak.** `ARTIFACTS_ACCENTS.setdefault(tab_id, accent)`
  (`artifact_tabs.py:365`) mutates a module-level dict during resolution;
  `reset_artifacts_subtabs_cache()` does not undo it. Verified: `ref:design` survives the
  reset. `tests/ace/tui/test_artifact_tab_digits.py:141-151` works around this by popping
  keys by hand in a `try/finally`, which is the test acknowledging the leak rather than
  catching it.

Fix shape: derive the accent deterministically from a hash of the kind, then
collision-resolve against the pinned set; return it on the descriptor and never write to a
module global.

### 1.2 Defect D reproduced, with the failure the user actually sees

With `sase_core_rs` unimportable, executed live:

```text
_provider_source_token()            -> ('unavailable',)
_load_project_provider_records()    -> ()
resolve_artifacts_subtabs()         -> ('stitches', 'patches', 'beads', 'files')
reset_artifacts_subtabs_cache(); resolve_artifacts_subtabs()
                                    -> ('stitches', 'patches', 'beads', 'files')
```

Two things are worse than the prior report described. First, the loss is not confined to
third-party providers: **the built-in Plans tab disappears too**, with no error anywhere in
the UI. Second, the token is a *stable* sentinel, so the degraded four-tab answer is cached
and survives an explicit cache reset — the pane cannot recover in-process even after the
underlying cause is fixed.

Separately, with the `sase-research-artifacts` plugin absent from a workspace venv, the
`research` role falls through to `_default_document_spec` and the tab is built from a spec
with **empty `properties` and empty `detail`** — verified live. The diagnostic exists
(`code="missing_ref_provider"`, `sidecar_ref_config.py:324`) and `sase doctor -C
config.repos` fires on it; ACE simply discards it. The tab renders, so nothing looks wrong.

### 1.3 One new defect, unrelated to providers

`o` is double-booked on the Patch surface. `_BINDING_META` binds `mark_pr_origin` at index
27 and `cycle_grouping_mode` at index 154 (`keymaps/metadata.py:27,154`), both to `o`, both
`priority=False`. Textual's `App._check_bindings` (`app.py:3905-3915`) walks
`key_to_bindings[key]` in insertion order and stops at the first action whose
`check_action` passes; `mark_pr_origin` is enabled on the whole Artifacts tab
(`_app_action_availability.py:172-174`). So on the Patch pane `o` opens the PR-origin
modal and **forward grouping-cycle is unreachable**, while `O` (`cycle_grouping_mode_reverse`,
uncontested) works. `docs/ace.md:614` documents `o`/`O` as forward/reverse.

This is worth stating in a report about unification because it is direct evidence for §6's
central cost: **the Patch keyspace is already saturated today**, before the contract asks
it to give up `f`, `R`, `y`, `s`, `l`, and `h`.

---

## 2. The crux: three query languages

This is the finding that reorganizes the whole design. What the owner calls "the Patch
tab's powerful search syntax" is one of three incompatible implementations of the same
idea, and the Artifacts tab hosts all three at once.

| | **`ace/query`** (Patch) | **`ace/agent_query`** (Agents) | **`filter_tokens` + 4 modules** (every other Artifacts pane) |
| --- | --- | --- | --- |
| Lines | 1,762 | 1,162 | 263 shared + 1,133 in 3 `filter_query` modules + `files_filtering.py` |
| Grammar | full boolean | full boolean | flat token list |
| `AND` / juxtaposition | ✓ / ✓ | ✓ / ✓ | implicit only |
| `OR` | ✓ | ✓ | **✗** |
| Parentheses | ✓ | ✓ | **✗** |
| Negation | `!` / `NOT`, any expr | `!` / `NOT`, any expr | leading `-` on one token |
| Case-sensitive literal | `c"..."` | `c"..."` | **✗** |
| Typed keys | ✗ — flat `VALID_PROPERTY_KEYS` frozenset | **✓ — substring / enum / bool / duration** | per-module hand-rolled |
| Comparison ops | ✗ | `age<2h` etc. | `since:` / `until:` only |
| Repeatable / comma values | ✗ | ✗ | ✓ |
| Sigil shorthands | `%d +p ^a ~s &n !!! @@@ $$$ *` | ✗ | ✗ |
| Completion menu | ✗ | (agents search bar) | ✓ `FilterBar` |
| Syntax highlighting | ✓ `QUERY_TOKEN_STYLES` | ✓ `AGENT_QUERY_TOKEN_STYLES` | **✗** |
| Editing UI | **modal** (`QueryEditModal`) | inline | inline `FilterBar` |
| Live match count / coverage | ✗ | ✗ | ✓ `FilterBar.set_status` |
| Saved slots | ✓ 0–9, global file | ✗ | ✗ |
| Prev/next history | ✓ `^` / `_` | ✗ | ✗ |
| Per-query selection memory | ✓ | ✗ | ✗ |
| Canonical form | ✓ `to_canonical_string` | ✓ | ✓ per module |

Read that table as a to-do list rather than an indictment. **Every column has at least one
implementation that is right**; no single pane has them all. `ace/query` has the grammar,
the sigils, the highlighting, the slots and the history. `agent_query` has the typed key
registry. `FilterBar` has the completion menu, the live count, the coverage label, the
negation-aware key filtering and the inline interaction. The unified layer is a *merge*,
not a rewrite, and it makes the strongest surface strictly better rather than levelling
down to the weakest.

Two structural details make this cheaper than it looks:

- **`FilterBar` is already the right shape.** It is class-var driven — `ACCENT`,
  `KEY_COMPLETIONS`, `STATIC_VALUE_COMPLETIONS`, `VALUE_HINTS`, `REPEATABLE_VALUE_KINDS`,
  `NEGATABLE_KEYS`, `FREE_TEXT_HINT`, `PERSISTENT`, plus one abstract
  `_completion_context` — and all four subclasses satisfy it in under 100 lines each.
  Those class vars are 80% of a field schema written as class attributes. Turning them
  into a data object is a refactor, not a design.
- **`agent_query` proves typed keys work.** `SUBSTRING_PROPERTY_KEYS`,
  `ENUM_PROPERTY_KEYS: dict[str, frozenset[str]]`, `BOOL_PROPERTY_KEYS`,
  `DURATION_PROPERTY_KEYS` (`agent_query/tokenizer.py:34-61`) is exactly the vocabulary a
  declared schema needs, and `sase-core`'s `PROPERTY_TYPES` already names the superset:
  `string, enum, boolean, integer, number, date, datetime, string_list`
  (`provider_spec.rs:28-37`).

The per-domain `FilterValues` dataclasses are where the cost of *not* doing this shows.
`BeadFilterValues` has 30 fields — fifteen `xxx` / `excluded_xxx` pairs — and a hand-written
30-clause `is_empty` (`bead/filter_query.py:84-160`). A schema-driven `QueryValues`
carrying `dict[str, FieldConstraint]` deletes that file's shape entirely, and the three
sibling files with it.

---

## 3. What the Patch pane owns that nothing else has

Each item below is one of the "coolest features" to be generalized, with its current
implementation, why it is Patch-shaped today, and the contract shape it becomes.

### 3.1 The boolean grammar and sigil shorthands

`ace/query/{tokenizer,parser,types,matchers,searchable,introspection,highlighting}.py`.
Property keys are a flat frozenset (`tokenizer.py:31`), matched by an
`if key == "status" / elif "project" / ...` ladder (`matchers.py:182-211`), against a
single flattened `str` corpus built by `get_searchable_text(patch)` (`searchable.py:14`).

**Contract shape.** A `QueryFieldSpec` per field — `name, type, matcher, sigil,
repeatable, negatable, completion_source, hint, searchable` — collected into an
`ArtifactQuerySchema` owned by the pane contract. The ladder becomes a dispatch on
`field.type`; `get_searchable_text` becomes "concatenate every field marked
`searchable=True`". Sigils become a per-schema `dict[str, str]` (`%`→`status`, `+`→`project`,
`^`→`ancestor`, `~`→`sibling`, `&`→`name`) so Beads could declare `#`→`type` without
touching the tokenizer.

The state-marker shorthands (`!!!`, `@@@`, `$$$`, `*`) are not properties — they are
**declared predicates**: named, zero-argument boolean matchers a pane registers with a
sigil, a label and a callable. Every pane has candidates the moment the mechanism exists
(`@@@` on Beads = has a launched agent; `!!!` on Stitches = has a failed hook).

### 3.2 Saved query slots

`ace/saved_queries.py` — a single global `~/.sase/saved_queries.json` mapping slot `"0"`–`"9"`
to a *Patch-canonical* query string. Reachable via the `0`-prefix mode
(`start_saved_query_mode`), the `*` picker, and ten `action_load_saved_query_<d>` methods.
The save syntax (`#3 <query>` to save, `#3` to delete, `#` for next free slot) is
implemented nowhere but the dismiss callback of `action_edit_query`
(`actions/base.py:493-544`) — it is undiscoverable and untestable in isolation.

`_load_saved_query` hard-switches to the Patches pane before loading
(`actions/patch/_query.py:58-67`), which is exactly what you would write if slots could
only ever mean one thing.

**Contract shape.** `saved_queries.json` becomes `{pane_id: {slot: query}}` with a one-shot
migration of the flat file into `{"patches": {...}}`. `PaneCapability.QUERY_SLOTS` gates the
`0`-prefix mode and the `*` picker; the picker gains a pane header. The `#N` save grammar
moves out of the modal callback into the shared filter bar's submit handler, where it is
testable and where the completion menu can advertise it. **Digit budget warning:** bare
digits are already spent on sub-tab selection and were deliberately re-namespaced under
`0` by `plans/202608/saved_query_zero_prefix.md`. Per-pane slots must stay behind the `0`
prefix and the `*` picker; do not reclaim bare digits.

### 3.3 Query history

`ace/query_history.py` — global prev/next stacks capped at 50, bound to `^` and `_`, saved
to `~/.sase/query_history.json`. Gated on `current_tab != "artifacts"` only, so pressing `^`
on the Beads pane rewinds the *Patch* query behind a hidden pane.

**Contract shape.** Same file, keyed by pane id, gated by `PaneCapability.QUERY_HISTORY`.
This is the smallest of the five generalizations and fixes a live cross-pane bug on the way.

### 3.4 Per-query selection memory

`ace/query_selection.py` (60 lines) — `canonical_query -> selected patch name`, restored on
every query change. A genuinely good idea that no other pane has: switch queries, come
back, and the cursor is where you left it.

**Contract shape.** `{pane_id: {canonical_query: entry_target}}`. This is the clearest
argument for doing **L0 identity first**: the persisted value must be an
`ArtifactEntryTarget`, and Patch does not have one yet.

### 3.5 The ancestors / children / siblings jumpers

The richest feature, and the one whose generalization is least obvious.

- `widgets/ancestors_children_panel.py` (612 lines) computes three relation families off a
  prebuilt `PatchGraphIndex`: the recursive parent chain, the full descendant *tree*, and
  the `__<N>` sibling family. It assigns key hints (`<`, `<<`, `<a`…; `>`, `>>`, `>a`…;
  `~`, `~~`, `~a`…), renders a box-drawing tree, and returns the three key maps.
- `actions/navigation/_tree.py` (346 lines) drives the modal key sequences, including the
  multi-character child buffer (`>2a.`) with prefix validation.
- **The critical part:** when the target is not in the current result set,
  `_change_query_for_navigation` (`_tree.py:293-346`) *rewrites the query* to
  `ancestor:<name>` or `sibling:<base>` and reloads. **The jumper and the query language
  are one feature.** You cannot generalize the jumpers without generalizing the query, which
  is why L3 depends on L2 and not the reverse.

Every other pane has relations it cannot express:

| Pane | Relations that exist in the data | Surfaced today |
| --- | --- | --- |
| Beads | epic → phases, `deps`, plan link | epic tree only, via `l`/`h` |
| Documents | proposal → active → archive, plan ↔ bead | section headings only |
| Files | logical file → versions | `(` / `)` only |
| Stitches | commit → parent, commit → patch | ✗ |
| Patch | parent chain, descendants, `__N` siblings | ✓ (all three) |

**Contract shape.** A `RelationSet` on the pane contract: named families, each yielding
ordered `ArtifactEntryTarget`s plus a display label and an optional
`query_template` used when the target is outside the current result set. The host owns
key assignment, the side panel, hint rendering and the fallback rewrite — the pane supplies
only the edges. Providers declare graph edges declaratively, by naming properties:

```yaml
relations:
  ancestors: {kind: parent_chain, property: parent}
  children:  {kind: inverse, of: ancestors}
  siblings:  {kind: family, property: repo_relative_path, suffix_pattern: '__(\d+)$'}
```

Anything needing a real traversal (Beads' dependency graph) stays a built-in
`RelationSource`, gated by capability. Note that `PatchGraphIndex` already exists as the
prebuilt-index pattern (`update_relationships_from_index` exists *precisely* so 100
selections do not rebuild the graph 100 times) — that hot-path discipline is the thing the
shared layer must preserve.

### 3.6 Foldable grouping with switchable modes

`o`/`O` cycles `BY_PROJECT ↔ BY_DATE ↔ BY_STATUS`; `l`/`h`/`L`/`H` fold; collapsed banners
are first-class navigation stops that `'` jump-hints land on. This is the most polished
list presentation in the app — and it already sits on the **generic**
`GroupFoldRegistry` (`models/group_fold.py`), explicitly documented as *"shared by Agents
and Patches"*, keyed on `tuple[str, ...]`.

Meanwhile Files does flat date separators (`files_rendering.py:191`), Documents does
section headers, Beads does an epic tree, Stitches does day headings. Four
implementations, one of which is already generic and has two consumers.

**Contract shape.** `grouping: tuple[GroupingMode, ...]` on the contract; the shared shell
renders banners through `GroupFoldRegistry`; `o`/`O` cycles whatever the pane declared, and
is a no-op where only one mode exists. Providers declare `group_by: none | year | month |
status | <property>` and get folding for free.

### 3.7 The one thing that must be replaced, not generalized

`marked_indices: set[int]` (`actions/marking.py`) and `int` jump anchors
(`navigation/jump_hints.py:52` — `EntryJumpAnchor = int | PatchBannerJumpAnchor`). Every
other pane already uses stable `ArtifactEntryTarget` tuples
(`_artifacts_marked_targets: dict[ArtifactsPaneKey, set[ArtifactEntryTarget]]`).
`action_toggle_mark` branches on the pane key to pick a model
(`actions/marking.py:42-53`), and `ArtifactsView.entry_navigator` raises outright for
Patches (`view.py:193-195`).

Index marks break under refresh, re-sort and query change. This is not a Patch feature to
preserve; it is L0.

---

## 4. The contract

### 4.0 L0 — one identity

`Patch` already has a stable artifact identity *outside* the TUI:
`builtin_entry_patch.py:60` mints `stable_id=f"patch:{project}/{patch.name}"` with a
typed property bag. The TUI just does not use it. L0 is:

- `patch_row_target(patch) -> ("patch", project, name)`, matching `bead_row_target`,
  `plan_row_target`, `file_row_target`, `commit_row_target`.
- `ArtifactsPatchesPane` implements all seven `ArtifactEntryNavigator` methods; `view.py`
  stops raising for `patches`.
- `marked_indices` → `_artifacts_marked_targets["patches"]`; `action_toggle_mark` loses its
  branch.
- `EntryJumpAnchor` becomes `ArtifactEntryTarget | PatchBannerJumpAnchor`.
- Patches gains `accepts_marks=True` copy targets and, finally, an `@ref` copy target —
  `@patch:` is a live ref kind with a resolver and there is still no way to copy one from
  the pane that shows them.

No user-visible change except marks surviving refresh, which is a fix.

**While here, close the protocol hole.** `ArtifactEntryNavigator` is a `Protocol`, and
`request_entry_target` / `conditional_footer_entries` are implemented only in
`beads_navigation.py` and `plans_navigation.py`. Verified: `files_navigation.py` and the
Stitches panes have neither, and the two call sites paper over it with
`getattr(pane, ..., None)` (`actions/artifacts_navigation.py:101,117`). Cross-pane deep
links and conditional footer hints therefore work on two panes and silently do nothing on
two others. Make it an ABC.

### 4.1 L1 — `ArtifactsPaneContract`

Substantially the prior report's Layer 1, kept, living beside `ArtifactsTabDescriptor` in
the widget-free `artifact_tabs.py`:

```python
@dataclass(frozen=True, slots=True)
class ArtifactsPaneContract:
    id: str                       # "patches", "beads", "ref:research"
    label: str
    icon: str
    accent: str                   # derived from id, collision-resolved, never a global
    pane_id: str
    order: int
    digit_shortcut: str | None

    ref_kind: str | None          # "patch", "bead", "research"; None if unaddressable
    target_prefix: str
    project_scoped: bool
    presentation_digest: str      # Python-side; see §5

    capabilities: frozenset[PaneCapability]
    query_schema: ArtifactQuerySchema | None      # L2
    relations: RelationSet                        # L3
    grouping: tuple[GroupingMode, ...]            # L3.6
    detail_fields: tuple[str, ...]
    status_counters: tuple[StatusCounter, ...]
    empty_state: EmptyState
    copy_targets: tuple[CopyTargetSpec, ...]
```

`PaneCapability` is a **closed enum of verbs the host already implements**; a capability
enables a registered action and never carries executable code. The prior report's set plus
what Patch inclusion requires:

```
OPEN  FILTER  REFRESH  MARK  JUMP  SCOPE_PROJECT
COPY_REFERENCE  COPY_PATH  COPY_LINK  COPY_JSON
OPEN_EXTERNAL  OPEN_AGENT  LINK_JUMP  VERSIONS  EXPAND_TREE  CYCLE_FACET
QUERY_BOOLEAN  QUERY_SLOTS  QUERY_HISTORY  QUERY_SELECTION_MEMORY   # new, L2
RELATIONS  GROUPING                                                  # new, L3
MUTATE  APPROVE                                                      # built-in only
```

Every downstream surface reads `capabilities` instead of comparing pane ids: the footer,
`_app_action_availability.py`'s chain, the help modal's per-pane sections
(`help_modal/patches_artifact_bindings.py` is hand-written per pane today and needs a new
stanza for every provider), the command palette, the copy registry, and the conformance
test. All 13 `startswith("ref:")` sites collapse.

### 4.2 L2 — one query engine

New package `sase/artifact_query/`:

```python
@dataclass(frozen=True, slots=True)
class QueryFieldSpec:
    name: str
    type: Literal["string","enum","boolean","integer","number",
                  "date","datetime","string_list","duration"]
    match: Literal["exact","substring","prefix","compare","membership"]
    values: tuple[str, ...] = ()          # enum
    sigil: str | None = None              # "%", "+", "^", "~", "&"
    aliases: tuple[str, ...] = ()
    repeatable: bool = False
    negatable: bool = True
    searchable: bool = False              # part of the free-text corpus
    hint: str = ""
    completion_source: str | None = None  # runtime-populated values

@dataclass(frozen=True, slots=True)
class QueryPredicateSpec:               # !!! @@@ $$$ * — declared, not hard-coded
    name: str
    sigil: str
    label: str

@dataclass(frozen=True, slots=True)
class ArtifactQuerySchema:
    fields: tuple[QueryFieldSpec, ...]
    predicates: tuple[QueryPredicateSpec, ...] = ()
    boolean: bool = True                 # OR / parens / c"" available
    default_query: str = ""
    persistent_bar: bool = False
```

One tokenizer, one parser to the existing `AndExpr / OrExpr / NotExpr / PropertyMatch /
StringMatch` AST, one evaluator dispatching on `field.type`, one canonicalizer, one
highlighter driven by `field.type` rather than a per-language style dict, and one
`FilterBar` subclass configured from the schema instead of from class vars.

Three properties make this safe to land incrementally:

1. **It is a superset of all three dialects.** `boolean=False` degrades to exactly today's
   flat token language, so Beads/Stitches/Files/Documents can migrate one at a time with
   byte-identical behaviour, then opt into `OR` and parentheses.
2. **Every dialect's canonical form is preserved.** `to_canonical_string` becomes
   schema-driven; saved queries and history files stay readable.
3. **Free text stops being special.** `get_searchable_text` is `" ".join(field values
   where field.searchable)`; Patch's 112-line hand-rolled corpus builder
   (`query/searchable.py`) becomes a set of `searchable=True` flags.

Patch's schema is then a ~40-line literal, and the migration is mechanical:

```python
PATCH_QUERY_SCHEMA = ArtifactQuerySchema(
    fields=(
        QueryFieldSpec("status",   "enum",   "exact",     sigil="%", searchable=True, ...),
        QueryFieldSpec("project",  "string", "exact",     sigil="+", searchable=True),
        QueryFieldSpec("ancestor", "string", "membership",sigil="^"),
        QueryFieldSpec("sibling",  "string", "membership",sigil="~"),
        QueryFieldSpec("name",     "string", "exact",     sigil="&", searchable=True),
        QueryFieldSpec("origin",   "enum",   "exact", values=("sase","external","unknown")),
        QueryFieldSpec("description", "string", "substring", searchable=True),
        ...
    ),
    predicates=(
        QueryPredicateSpec("error_suffix",    "!!!", "has an error suffix"),
        QueryPredicateSpec("running_agent",   "@@@", "has a running agent"),
        QueryPredicateSpec("running_process", "$$$", "has a running process"),
    ),
)
```

Providers declare their schema for free: `ref.properties` **already** carries `type`,
`values` and `source`, is **already** validated by Rust (`provider_spec.rs:120-138`), and is
**already** carried on the descriptor. The whole of `ref.properties` becomes queryable and
completable the moment L2 reads it — no spec change required. That is the highest
value-per-line change in this report.

**Also fix while here:** the Files bar alone leaves `NEGATABLE_KEYS` unset, so `-key:`
silently works on three panes and not the fourth; and `plan_filter_bar.py:31` reads
`ARTIFACTS_ACCENTS["plans"]` at class-definition time, so a Research filter bar is
Plans-purple. Both disappear when the bar is configured from the contract.

### 4.3 L3 — relations and grouping

```python
@dataclass(frozen=True, slots=True)
class RelationFamily:
    name: str                       # "ancestors" | "children" | "siblings" | "versions" ...
    label: str                      # panel heading
    prefix: str                     # "<" | ">" | "~"
    ordered: bool                   # tree vs flat list
    query_template: str | None      # "ancestor:{name}" — the out-of-set fallback

class RelationSource(Protocol):
    def relations_for(
        self, target: ArtifactEntryTarget
    ) -> Mapping[str, tuple[RelationNode, ...]]: ...
```

The host owns key assignment, the multi-key buffer, the panel widget, hint rendering, and
the query-rewrite fallback — all of which exist today in `ancestors_children_panel.py` and
`navigation/_tree.py` and need only to be lifted off `Patch` and onto
`ArtifactEntryTarget`. `AncestorsChildrenPanel` becomes `RelationPanel` and moves from
`ArtifactsPatchesPane.compose` into the shared shell.

Grouping reuses `GroupFoldRegistry` unchanged, with `GroupingMode` declared on the
contract and providers declaring `group_by`.

### 4.4 L4 — the declarative `ref.pane` block

Unchanged in substance from the prior report §5.3 — row template, `group_by`,
`default_sort`, `filters.facets`, `capabilities` from a safe subset, `empty_state`, `label`,
`description`, `order`. Two additions this report's scope requires:

```yaml
ref:
  pane:
    query:
      boolean: true                     # opt into OR / parens / c""
      default: "-status:archived"
      persistent_bar: false
      searchable: [title, body, tags]
      slots: true                       # participate in saved-query slots
    relations:
      ancestors: {kind: parent_chain, property: parent}
      siblings:  {kind: family, suffix_pattern: '__(\d+)$'}
```

The constraints from the prior report all still hold and are worth restating because they
are what keeps a plugin surface bounded: presentation refers only to declared properties;
list fields are priority hints, detail stays lossless; facets are typed; identity must be
stable across content edits; a malformed document degrades per entry and never removes the
tab; **no colours, no keybindings, no command strings, no Python entry points, no
mutation, no approval flows**. Anything needing those is a built-in pane — a `sase` change,
not a plugin change.

The designer-facing guarantee becomes materially larger than it was: declare `ref.kind` and
`inventory.globs`, and you inherit a tab with a stable digit and non-colliding accent;
lazy off-thread coalesced loading; shared project scope; `j`/`k`/`enter`/`f`/`R`; marks,
hint-jump, detail scrolling; **a boolean query language over your declared properties, with
completion, negation, canonicalization, highlighting, saved slots, prev/next history and
per-query selection memory**; **relation jumpers over any parent/family property you
declare**; grouping and folding; a copy-mode group; a generated help section; palette
entries; `@kind:<path>` round-tripping; and `Referenced By` write-back.

---

## 5. Where each layer lives — Rust or Python

**Presentation stays Python, and the Rust wire version must not move.** The prior report
reached the first half of that conclusion; the crate now states the second half outright
(`provider_spec.rs:18-25`): adding a required field would be a breaking wire change, and
the textbook bump from 1 to 2 is *explicitly rejected* because CI installs the published
floor `sase-core-rs` and runs it against the checkout, which would reject a
`schema_version: 2` spec before the core carrying the bump is ever released. A floor core
ignores unknown fields under serde defaults, so enforcement simply does not apply until the
new core is installed.

Two consequences the plan must design in:

1. **`ref.pane` is Python-only, at `DOCUMENT_REF_PROVIDER_SPEC_SCHEMA_VERSION`
   (`sidecar_ref_config.py:39`, currently `1`).** Leave
   `ARTIFACT_REF_PROVIDER_SPEC_WIRE_SCHEMA_VERSION` at `1`. Add `REF_PANE_CONFIG_KEY` to
   `_KNOWN_REF_CONFIG_KEYS` (`sidecar_ref_config.py:65`) or inline `ref: pane:` will fail
   validation while a `use:`-provided plugin spec silently succeeds — the two paths already
   diverge, which is why `_provider_label` can read a plugin-supplied `label` today but an
   inline one is rejected.
2. **The presentation digest is mandatory, and for a sharper reason than "Rust drops the
   key".** `validate_ref_provider_spec` digests the *Rust* struct as serialized by
   *whichever core is installed*. So a Rust-modelled `pane` block would produce a
   digest that changes with the core version — worse than a Python-only block, which
   produces a digest that ignores `pane` consistently. Compute a Python-side
   `presentation_digest` over the normalized pane block, fold it into
   `ArtifactsTabDescriptor` and into every pane cache key.

**Does the query engine belong in `sase-core`?** By the repo's own litmus test — *"if a web
app, CLI, editor integration, or another frontend would need the behavior to match the
TUI"* — yes, unambiguously. `sase axe start --query` already parses Patch queries;
`sase bead list` and `sase stitch list` already share the token dialect with their panes;
`sase-nvim` would want the same completion.

**But not yet, and the reason is sequencing.** Lifting a query engine into a wire freezes
its field-schema shape. Today there are three incompatible shapes, and one of them
(`agent_query`) got the design right by accident while the other two did not. Build
`sase/artifact_query/` in Python, prove one schema across five Artifacts panes plus the
Agents tab plus the three CLI surfaces, *then* lift the tokenizer, parser, evaluator and
canonicalizer into `sase-core` as one module — leaving completion, highlighting and the
Textual bar in Python. That lift is the natural successor to the cancelled `sase-k6`
("Extend artifact-ref use wire to schema 2"), which the owner's 2026-08-12 backlog cut
explicitly asked to be **re-proposed as one follow-on epic** rather than worked as six
overlapping large tasks. This is that epic.

The one thing genuinely blocked in core today: `ArtifactEntryWire.properties` is
`BTreeMap<String, String>` (`entry.rs`), so a spec may declare `type: datetime` /
`string_list` and the entry wire then flattens every value to a string. Sorting by a real
`updated_time` or filtering `tags:` as a list is not expressible. L2 can work around it in
Python by coercing on read; doing it properly is a `sase-core` change and should be
scheduled with the lift, not before it.

---

## 6. Patch inside the contract: what it actually costs

### 6.1 The keymap collision table

This is the sharp edge, and it is sharper than the prior report's analysis of the four
non-Patch panes, because **the two surfaces assign the same keys to inverted meanings**.

| Key | Patch today | Other panes today | Contract verb | Resolution |
| --- | --- | --- | --- | --- |
| `y` | **`refresh`** | `stitches_copy_sha`, `files_copy_reference` | `artifacts_copy_reference` | Patch's refresh moves to `R`; `y` copies `@patch:` — a target Patch does not even have today |
| `R` | `start_rewind` | `*_refresh` | `artifacts_refresh` | `start_rewind` moves into bang mode (`!R`) or leader mode |
| `f` | `edit_hooks` | `*_filters` | `artifacts_filters` | `edit_hooks` moves to leader mode; `f` opens the filter bar everywhere |
| `s` | `change_status` | `stitches_cycle_merges`, `beads_cycle_status`, `files_cycle_kind` | `artifacts_cycle_facet` | Genuine conflict: Patch's `s` *mutates*, the others *filter*. Keep `s` = mutate on `MUTATE` panes (Beads' `s` already mutates), and move facet-cycling to `S`-shift or a `CYCLE_FACET` verb on another key |
| `l`/`h` | fold in / out | `beads_expand` / `beads_collapse` | `artifacts_expand` / `artifacts_collapse` | Already the same concept; unify |
| `L` | `expand_all_folds` | `plans_open_bead`, `beads_open_plan` | `artifacts_link_jump` | Conflict. `L`/`H` fold-snap moves under the `z` fold-mode prefix, which Patch already owns |
| `o` | `mark_pr_origin` **and** `cycle_grouping_mode` (§1.3) | `files_open_external`, `beads_open_bug` | `artifacts_open_external` | Already broken; fix by moving `mark_pr_origin` into bang mode |
| `d` | `show_diff` | `stitches_toggle_sdd` | — | Both stay pane-local; `d` is a legitimate per-pane key |
| `m`, `u`, `'`, `enter`, `j`, `k`, `g`, `G` | ✓ | ✓ | unchanged | Already agree |

Mitigation is the prior report's: keep old action names as **aliases** in the keymap
loader so existing `~/.config/sase/sase.yml` overrides keep working, emit a `sase doctor`
advisory naming each replacement, and consider a one-shot `sase config` migration. `y`
changing from refresh to copy on the pane the owner uses most is the single most jarring
change in this plan and deserves a `CHANGELOG.md` line and a startup toast on first run.

### 6.2 Project scope

Patch is currently excluded from the shared scope key: `pick_artifacts_project` returns
`False` for `patches` (`_app_action_availability.py:157-162`). But the coupling already
exists in the other direction — `_resolve_initial_artifacts_scope` reads
`get_sole_project_filter(self.parsed_query)` (`actions/artifacts.py:194`), so the Patch
query *seeds* the shared scope at startup.

Under the contract this becomes symmetric, and **Stitches already proves the pattern**:
`docs/ace.md:243` — *"The project picker replaces that token while preserving every other
committed token; its All projects choice removes it."* Patch adopts exactly that. `p`
rewrites the `project:` / `+` token in the Patch query. No new concept, no new state.

### 6.3 Query editing UI

Patch is the only Artifacts pane that edits its query in a **modal**
(`QueryEditModal`, pushed from `actions/base.py:566`). Migrating to the inline `FilterBar`
is most of what "same look and feel" means, and it delivers four things Patch does not
have: a completion menu over its own property keys and values, a live match count, a
coverage label, and `Escape`-restores-last-committed. The `#N` save grammar moves with it.

### 6.4 Patch is contract-in, spec-out

`patch` is in `RESERVED_KINDS` alongside `stitch`, `bead`, `agent`, `file`
(`provider_spec.rs:27`) — a document provider can never claim it. Patch therefore
*consumes* `ArtifactsPaneContract` and declares its contract from a module-level Python
table, exactly like Beads and Stitches. It is a first-class citizen of L0–L3 and absent
from L4. That is the correct asymmetry and should be written into the docs so the next
reader does not try to fix it.

### 6.5 Data migration

Small but real, and easy to forget:

- `~/.sase/saved_queries.json`: flat `{slot: query}` → `{pane_id: {slot: query}}`; migrate
  the existing file into `{"patches": {...}}`.
- `~/.sase/query_history.json`: `{prev, next}` → `{pane_id: {prev, next}}`, same shape.
- `~/.sase/query_selections.json`: values become entry targets, not Patch names.

All three are caches of user convenience state; a read-time migration with a silent
fallback to empty is sufficient. No bead or plan data is touched.

---

## 7. Options considered

| Option | Benefit | Failure mode | Verdict |
| --- | --- | --- | --- |
| Prior report's plan, Patch exempt | Smaller; ships sooner | The best features stay locked in one pane; providers never get search, slots or jumpers; the exemption becomes permanent because each new feature widens the gap | **Superseded** by the owner's decision, and the right call regardless |
| Bring Patch in, keep three query languages | Avoids the biggest refactor | Patch keeps a modal editor and no completion; providers keep a flat dialect with no `OR`; "unified" is only skin-deep | Reject |
| Adopt the flat token language everywhere (delete the boolean grammar) | Simplest; one small language | Loses `OR`, parens, case-sensitive literals and every sigil. A strict downgrade for the owner's primary surface | Reject |
| Adopt the Patch boolean language everywhere as-is | Keeps the good grammar | Its property keys are a hard-coded frozenset and its corpus is a hand-written flattener; a provider cannot extend either. Also loses `FilterBar`'s completion and live count | Reject |
| **Schema-driven engine that is a superset of all three, `boolean` opt-in per pane** | One language; each pane migrates with byte-identical behaviour then opts in; `ref.properties` becomes queryable with no spec change | Largest single refactor in the plan; needs alias/migration care | **Best fit** |
| Lift the query engine to `sase-core` first | Right long-term home per the boundary rule; CLI parity immediately | Freezes a field-schema shape that three existing dialects disagree about; near-certain rework | Right destination, **wrong order** |
| Providers ship Textual widgets or callbacks | Maximum flexibility | Inconsistent UX, unbounded hot-path work, no failure isolation, no future-frontend parity | Reject |

---

## 8. Phasing

| Phase | Content | Size | User-visible |
| --- | --- | --- | --- |
| **0** | Live defects: derive accents from the kind and collision-resolve, stop mutating `ARTIFACTS_ACCENTS`; narrow the two bare `except Exception` blocks in `_load_project_provider_records` and render a **degraded tab carrying its own error** instead of no tab; stop caching the `("unavailable",)` sentinel; unbreak `o` on the Patch pane (§1.3) | S | **Yes** — fixes silently-missing tabs |
| **0.5** | Parameterize `ordered_plan_property_items` by `ref.detail.fields`. No spec change, no Rust change, no new data path | XS | **Yes** — Research shows its own properties |
| **1 · L0** | One `ArtifactEntryTarget` everywhere; Patch implements the navigator; marks and jump anchors migrate; `ArtifactEntryNavigator` becomes an ABC; Files and Stitches gain the two missing methods; `@patch` copy target added | M | Marks survive refresh; deep links work on Files/Stitches |
| **2 · L1** | `ArtifactsPaneContract` + `PaneCapability`; `ArtifactsSnapshotPane` base absorbing the loader written three times; every downstream surface reads capabilities; delete all 13 `ref:`-prefix shims; per-provider copy groups and help sections | L | Provider panes stop calling themselves Plans |
| **3 · L2** | `sase/artifact_query/`; migrate the four token panes with `boolean=False` (behaviour-identical), then Patch with `boolean=True`; inline filter bar replaces `QueryEditModal`; saved slots / history / selection memory namespaced per pane with file migration; `ref.properties` drives completion | XL — **split into an epic** | **Yes** — the phase users feel |
| **4 · L3** | `RelationSet` + `RelationPanel`; Patch's three families move onto it; Beads gets epic/phase and deps, Files gets versions, Documents gets the plan↔bead link; grouping declared on the contract, `GroupFoldRegistry` as the one implementation | L | Jumpers on every pane |
| **5 · L4** | `ref.pane` at document-spec schema 2 (Python only), `REF_PANE_CONFIG_KEY` in the allowlist, `presentation_digest`; `sase-research` ships its `pane` block | L | Research is a real Research tab |
| **6** | Parametrized conformance test over `resolve_artifacts_subtabs()` with a **synthetic third provider**; ACE-surfaced provider diagnostics; docs section; visual snapshot refresh | M | No |
| **later** | Lift tokenizer/parser/evaluator into `sase-core`; widen `ArtifactEntryWire.properties` to typed values | L | No |

Phase 3 is the only one that will not fit a single agent. Split it: one phase per migrated
pane, plus one for the persistence-file migration, plus one for the Patch cutover.

**Verification notes.** Phases 1–4 touch `tests/ace/tui/test_artifacts_*` broadly, so
`just check`'s scoped lane will escalate — run `just check-full` through `/sase_monitor`
before landing each. Expect `tests/ace/tui/visual/snapshots/png/` goldens to move in
Phases 3 and 5; review those diffs rather than accepting blind. Hold the existing
`SASE_TUI_PERF=1` navigation p95 under 16 ms on every converted pane, measured after each
conversion — `sase/memory/tui_perf.md` governs this work and should be read before
implementing. The relation panel is the specific hot-path risk: preserve the
prebuilt-index pattern (`update_relationships_from_index`) rather than rebuilding a graph
per selection.

---

## 9. Open decisions

1. **`s` on Patch.** The only verb where Patch's meaning (mutate status) and the other
   panes' meaning (cycle a filter facet) genuinely conflict, and Beads already sides with
   Patch. Recommendation: `s` = mutate wherever `MUTATE` is declared, facet-cycling moves
   to a different key everywhere. Confirm.
2. **`y` = copy on Patch.** Loses today's refresh binding on the owner's primary surface.
   Recommendation: do it — a pane full of `@patch:`-addressable rows with no way to copy one
   is the more surprising state. Confirm.
3. **Does Patch keep a persistent filter bar?** Stitches sets `PERSISTENT = True` because
   the query *is* the view; the same argument applies to Patch, whose query is currently
   always visible in `SearchQueryPanel`. Recommendation: `persistent_bar: true` for both,
   declared rather than accidental.
4. **Saved-query slots: per-pane, or global with a pane column?** Per-pane is cleaner and
   matches history/selection memory. Global-with-column preserves "slot 3 is always the
   same thing" muscle memory. Recommendation: per-pane, with the `*` picker showing the
   active pane's slots first and the rest below.
5. **How far does `boolean: true` go by default?** Recommendation: opt-in per pane, default
   `false` for providers so a schema-1 provider's behaviour never changes silently, default
   `true` for Patch and (after a settling period) the four built-ins.
6. **Fold the `sase-core` query lift into this epic, or propose it separately?** It is the
   natural successor to the cancelled `sase-k6`/`k5` batch, which the owner asked to be
   re-proposed as one follow-on epic. Recommendation: separate epic, sequenced after
   Phase 3 lands and the schema has stopped moving.

---

## 10. Risks

- **Phase 3 is the whole plan's risk.** Three languages, four panes, three persistence
  files and one modal-to-inline UI change. Mitigation: the `boolean=False` degradation path
  makes each pane migration byte-identical and independently revertable; migrate the four
  token panes before touching Patch, so the engine is proven on four surfaces before the
  hardest one.
- **Keymap churn is user-visible and unavoidable.** Aliases plus a doctor advisory plus a
  one-shot config migration; do not ship the rename without all three.
- **Providers gaining a query language enlarges the plugin blast radius.** A malformed
  `properties` block must degrade per entry, never remove a tab. This is already stated as
  constraint 6 in the prior report; L2 makes it load-bearing.
- **`o` is already broken and nobody noticed** (§1.3). That is the honest signal about how
  much of this surface is untested at the binding level. The conformance test in Phase 6
  should assert that every contract-declared key resolves to the action the contract names,
  on every pane, including built-ins.

---

## Recommended solution

Bring Patch into the Artifacts contract, and do it by **taking the query language away from
Patch first**.

Build the contract in five dependency-ordered layers. **L0** gives every pane, Patch
included, one stable `ArtifactEntryTarget`, replacing Patch's index-based marks and jump
anchors and making `ArtifactEntryNavigator` an enforced ABC — small, invisible, and a hard
prerequisite for everything else. **L1** is the prior report's `ArtifactsPaneContract` with
a closed `PaneCapability` vocabulary that every downstream surface reads instead of
comparing pane ids, deleting all thirteen `ref:`-prefix shims and the triplicated loader
behind it. **L2** replaces three query languages — `ace/query`, its self-declared fork
`ace/agent_query`, and the flat `filter_tokens` dialect — with one engine driven by a
declared `ArtifactQuerySchema`; it is a strict superset of all three, degrades to today's
exact behaviour with `boolean=False`, and makes the already-declared, already-Rust-validated
`ref.properties` queryable and completable with no spec change at all. **L3** generalizes
the ancestors/children/siblings jumpers into named relation families over any pane's graph —
including the query-rewrite fallback that makes them work outside the current result set,
which is why L3 cannot precede L2 — and folds Patch's three grouping modes onto the
`GroupFoldRegistry` that is already shared with Agents. **L4** is the declarative `ref.pane`
block, where a provider fills in row template, grouping, sort, facets, empty state and a
safe capability subset, and never ships code.

Keep the layer split honest: **presentation is Python**, and the Rust wire version stays at
1 because the crate documents why a bump would break CI against the published floor core —
which makes a Python-side `presentation_digest` mandatory rather than optional, since a
Rust-modelled pane block would produce a core-version-dependent digest. The query engine
genuinely belongs in `sase-core` by the repo's own boundary litmus test, but lifting it
before the field schema has settled would freeze a shape that three existing dialects
disagree about; build it in Python, prove it across five panes and three CLI surfaces, then
lift the tokenizer/parser/evaluator as the successor to the cancelled `sase-k6`.

Patch is contract-in and spec-out: `patch` is a reserved kind in core, so it consumes the
contract from a built-in Python table and never becomes a document provider. Its keymap
cost is real and concentrated in six keys — `y`, `R`, `f`, `s`, `L`, `o` — mitigated by
aliases, a doctor advisory and a one-shot config migration. Its project scope becomes
symmetric by copying the pattern Stitches already ships.

Land Phase 0 immediately regardless: accents that collide and drift, and provider discovery
that fails silently and caches its own failure, are live today and cost nothing to fix.
Land Phase 0.5 next — parameterizing the detail band by `ref.detail.fields` remains the
highest value-per-line change available. Then L0, L1, L2 in order, before any new sub-tab
functionality is added, because every feature added before the query layer exists gets
written five times.
