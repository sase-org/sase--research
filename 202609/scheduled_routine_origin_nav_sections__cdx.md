# Scheduled routine navigation sections

**Researcher:** cdx  
**Date:** 2026-09-26  
**Primary repository snapshot:** `013a170720270ac4996122bbdb1026f9468d6042`  
**sase-core snapshot:** `9d049aac62ff173e41c9fec59734fcfc4af982d8`

## Executive conclusion

Grouping scheduled routines is a good idea, and true nav sections are justified here rather than being merely decorative. The current machine-level configuration has seven built-in routines containing 31 jobs, versus one custom routine containing one job. With all routine folds initially expanded, that is a 38-row built-in tree beside a two-row custom tree. Separate panels give those sets independent scroll regions and let `J`/`K` jump between them; an in-list divider would still leave the small custom set buried below the large built-in tree.

The grouping axis should be **configuration ownership/origin**, not current status, cadence, function, or the layer that most recently overrode a field. I recommend three fixed routine sections:

1. **Built-in Routines** — introduced by SASE's built-in default layer.
2. **Plugin Routines** — introduced by an installed plugin's default layer.
3. **Custom Routines** — introduced by user, machine-overlay, or project-local configuration.

Only nonempty Plugin and Custom sections should be shown. A built-in routine that the user customizes must remain in Built-in Routines; similarly, a plugin routine with a user override must remain in Plugin Routines. This needs a stable `source`/`declared_by` contract from `sase_core`, following the precedent already used by service procs. The TUI should not infer origin from winning field provenance.

I would not add arbitrary user-defined routine groups in the first version. That creates unresolved ordering, naming, empty-group, ownership, and UI-versus-runtime configuration questions before there is a demonstrated need. The fixed source buckets solve the concrete problem cleanly and leave room for a later explicit display-group facility.

## Scope and method

I traced the current Services-tab composition, item model, navigation, panel sizing, title statistics, refresh path, configuration layering, and Rust composition wire. I also inspected the current machine-level effective routine inventory with project-local configuration disabled, matching `sase tui` behavior. Relevant implementation points include:

- `src/sase/ace/tui/_app_layout.py`
- `src/sase/ace/tui/actions/axe_display/_panels.py`
- `src/sase/ace/tui/actions/axe_display/_loader_items.py`
- `src/sase/ace/tui/actions/axe_display/_panel_navigation.py`
- `src/sase/ace/tui/actions/axe_display/_render_panels.py`
- `src/sase/ace/tui/actions/axe_display/_panel_titles.py`
- `src/sase/ace/tui/actions/axe_display/_data.py`
- `src/sase/ace/tui/util/panel_heights.py`
- `src/sase/default_config.yml`
- `src/sase/axe/config_backend.py`
- `src/sase/config/inventory.py`
- `crates/sase_core/src/config/axe.rs` in `sase-core`
- `crates/sase_core/src/service/config.rs` in `sase-core`

No other swarm research report was consulted.

## Current implementation

### The Services sidebar has exactly two nav sections

The layout statically mounts `service-procs-panel` and `scheduled-routines-panel`. `SERVICES_PANEL_ORDER` is the two-element tuple `("service_procs", "scheduled_routines")`. A single global `_axe_items` list preserves selection and action semantics, while `ServicesPanelIndex` partitions that list into panel-local slices and maps local clicks back to global row indices.

This is a strong foundation. Stable item identity is already separated from visual placement, and most rendering/navigation loops already iterate `SERVICES_PANEL_ORDER`. `J` and `K` use `adjacent_nonempty_panel`, so the navigation behavior naturally generalizes to more sections.

The parts that remain hard-coded to two panels are localized:

- static widget composition and widget lookup;
- the `ServicesPanelKey` literal and item-to-panel classifier;
- the two title builders and placeholder dictionaries;
- `[False, False]` and `filler_idx=1` in height allocation;
- CSS targeting the second panel's top margin;
- tests and visual goldens that assert the two-panel shape.

### Routine rows are one alphabetically sorted tree

The collector loads effective runtime configuration, sorts routine names, and caches routine/job snapshots off the event loop. `_append_lumberjack_items` emits each routine row followed by its jobs when expanded. First sightings default to expanded. Routine and job identities are already stable (`("lumberjack", name)` and `("chop", routine, job)`), so reordering routines into source sections does not require changing action identities or persisted fold keys.

The current panel classifier uses only the Python class name: all `LumberjackItem` and `ChopItem` instances go to `scheduled_routines`. That classifier must gain source-group information, but the existing global/local index design should remain.

### The current data distribution favors real sections

The effective machine-level inventory observed during this research was:

| Routine | Origin | Jobs |
|---|---:|---:|
| `checks` | built-in | 4 |
| `comments` | built-in | 1 |
| `external_mirror` | built-in | 4 |
| `hooks` | built-in | 8 |
| `housekeeping` | built-in | 9 |
| `usage` | built-in | 1 |
| `waits` | built-in | 4 |
| `telegram` | custom/user | 1 |

There were no plugin-introduced routines in the effective inventory. This means a divider-only design would put a two-row custom tree after 38 expanded built-in rows. A separate Custom Routines panel can remain at its natural height while the Built-in Routines panel scrolls in the remaining space.

### The shared height allocator already supports more than two panels

`allocate_panel_heights` accepts arbitrary lists. When content overflows, it fixes the smallest panels at natural height first and gives larger panels fractional space. This is exactly the desired behavior: Service Procs and a small Custom Routines panel remain visible, while the large Built-in Routines panel absorbs scrolling.

The Services caller, not the allocator, is the limitation: it passes exactly two widgets, two collapse flags, and a fixed filler index. Generalizing the caller is preferable to inventing a second sizing algorithm.

## The origin-classification problem

### Winning provenance is not ownership

`AxeFieldProvenance` answers which layer supplied the effective value at a path. It is intentionally last-writer-oriented. In a synthetic composition where the built-in layer defines `hooks` and the user layer changes only `hooks.interval`, the root provenance for `axe.lumberjacks.hooks` becomes the user layer even though the routine was introduced by the built-in layer. Grouping from that root provenance would make a built-in routine jump into Custom Routines after a harmless override.

That behavior would be confusing and unstable:

- editing an interval could move the selected routine to another panel;
- resetting the override could move it back;
- refresh could reorder the sidebar during navigation;
- "Built-in" would really mean "not currently touched by a later layer," which is not what users mean;
- plugin routines customized by the user would lose their plugin ownership signal.

Scanning field provenance in Python for the lowest-priority contributor would also be wrong architecturally. It would duplicate config-domain semantics in one frontend and would have to understand public `routines`/`jobs`, compatibility `lumberjacks`/`chops`, keyed maps, legacy lists, generated jobs, and layer-kind normalization.

### Service procs already establish the right contract

`sase_core` service-proc composition exposes both:

- `source`: normalized to `builtin`, `plugin`, or `user` (where user includes user/overlay/local ownership); and
- `declared_by`: the exact first layer label that introduced the proc.

The builder sets these when an entry is first inserted, while field provenance continues to track later winners. This cleanly separates **identity ownership** from **effective field values**. Routine composition should use the same model.

### Proposed semantics

For every effective base routine, inspect ordered raw layers and select the first layer containing that routine identity under either public `axe.routines` or compatibility `axe.lumberjacks`:

- layer kind `builtin` -> source `builtin`;
- layer kind `plugin` -> source `plugin`;
- layer kind `user`, `overlay`, or `local` -> source `user`;
- retain the exact labeled layer as `declared_by` (for example, `plugin:sase_telegram` or a user-layer label with its path).

Later overrides never change these two fields. Jobs may receive the same fields for contract consistency, with generated jobs inheriting from their base job, but routine section membership depends only on the routine's source.

If malformed or compatibility data somehow produces an effective routine with no discoverable declaring layer, fail closed into Custom Routines and emit/retain a diagnostic rather than calling it built-in.

## Critique of the proposed idea

### What is good about it

The idea improves three things at once:

1. **Visibility:** small custom/plugin sets are not buried under the built-in job tree.
2. **Navigation:** `J`/`K` can move between operational ownership domains; each panel keeps its own scroll viewport.
3. **Comprehension:** users can distinguish SASE-shipped automation from integration-provided and locally-owned automation before opening an editor.

It also fits the project's definition of a nav section: each group is a left-column panel whose routine/job rows are nav items. This is semantically stronger than adding nonselectable divider chrome inside the existing panel.

### Where the initial plan is underspecified

"All built-in routines together" needs precise answers to these questions:

- Is a built-in routine with a user override still built-in? It should be.
- Are plugin routines built-in, custom, or separate? They should be separate.
- Do overlays create a machine section? Not initially; they belong in Custom.
- Are empty sections visible? Plugin and Custom should be hidden when empty.
- Does a section correspond to the routine's purpose or its owner? Use owner.
- Can a user assign arbitrary group names? Not in the first version.

Without these rules, the UI would be driven by accidental details of configuration merging and would move rows unexpectedly.

### Costs and risks

Every panel consumes two border rows plus a separator row, so unbounded grouping would perform poorly on narrow terminals. This is the main reason to cap the first version at three fixed routine buckets and suppress empty optional buckets.

Splitting the existing Scheduled Routines title also fragments its aggregate metrics. Counts should become per-section, while scheduler-level health must appear only once to avoid repeated `scheduler stopped` badges. The simplest policy is to attach the scheduler badge to the first visible routine section (normally Built-in Routines) and document that it governs all routine sections. The existing scheduler service-proc row and SVC health indicator continue to provide global visibility.

The wire change crosses `sase-core` and SASE. It requires core tests, Python facade updates, binding compatibility care, and advancing `sase-core-revision.txt` past the core commit before Python callers land.

## Alternatives considered

### Keep one panel and add in-list dividers

This is the smallest code change and preserves one aggregate title. It is inferior for the observed shape because the custom set remains below dozens of built-in rows, does not gain an independent viewport, and cannot be reached with section-level `J`/`K` navigation. It would be acceptable only if the goal were visual labeling rather than navigation grouping.

### Add arbitrary `group:` to routine configuration

This is flexible but premature. It mixes UI organization into scheduler configuration, requires merge semantics for inherited/overridden groups, invites empty and misspelled panels, needs an ordering mechanism, and still needs a default rule for ungrouped routines. If explicit grouping becomes necessary later, it should live in presentation configuration (for example, an ACE Services grouping declaration that selects routine identities), not in the scheduler's execution contract by default.

### Group by function or cadence

Labels such as lifecycle, polling, maintenance, messaging, fast, and slow sound attractive but are subjective and overlap. Cadence can be overridden, and function changes over time. Neither gives a stable ownership boundary.

### Group by live status

Running/error/idle sections would move rows during every refresh, undermine selection stability, and split parent routine context from the operator's mental model. Status belongs in title chips and row markers, as it does now.

### One section per plugin or config layer

This exposes exact provenance but creates panel explosion and leaks implementation details such as machine overlay filenames into primary navigation. Aggregate all plugins in one Plugin Routines section and all user-owned layers in Custom Routines; show exact `declared_by` only in detail/editor context.

### Make grouping a toggle

A grouped/ungrouped mode adds state, keybindings, persistence, docs, and duplicated visual coverage without a clear use case. Source grouping is stable enough to be the default. A toggle can be reconsidered only if users demonstrate that the extra panels hinder their workflow.

## Adjusted requirements

These are deliberate changes/clarifications to the initial request:

1. **Interpret "built-in" as first declaration, not current winning provenance.** User overrides do not move ownership.
2. **Use three fixed source buckets:** Built-in, Plugin, and Custom.
3. **Do not add arbitrary group configuration in v1.** Defer it until there are concrete desired groups and ordering rules.
4. **Hide empty Plugin and Custom sections.** Keep Built-in visible; if all routines are unexpectedly absent it can carry the existing empty-state treatment.
5. **Keep one global row identity/index model.** Section membership is a projection, not part of routine/job identity.
6. **Preserve alphabetical order within each source bucket.** Use fixed bucket order after Service Procs: Built-in, Plugin, Custom.
7. **Keep routines and their jobs together.** A job always belongs to its parent routine's section, regardless of the job's own declaration/override provenance.
8. **Keep global scheduler health singular.** Do not repeat a scheduler badge in every routine panel.
9. **Do not auto-collapse built-ins.** Hidden failures would be a worse default; independent scrolling and panel sizing solve the visibility problem without concealing work.
10. **Expose exact ownership in routine detail/editor context.** A concise `Source`/`Declared by` line makes section membership explainable, especially for overridden built-ins.

## Implementation outline

### 1. Add stable origin to the Rust AXE composition contract

In `crates/sase_core/src/config/axe.rs`:

- add `source` and `declared_by` to `AxeInventoryEntryWire`, modeled on `ServiceProcConfigWire`;
- derive them from the first raw layer containing the routine/job identity, using the existing ordered `ConfigLayerInputWire` list and `raw_routine_value` compatibility logic;
- normalize layer kinds with the same `builtin` / `plugin` / `user` vocabulary used by service procs;
- make generated job entries inherit the base job's ownership;
- test built-in, plugin, user, overlay, public-name, compatibility-name, partial override, and generated-job cases.

The critical regression test is: a user layer overrides one field of a built-in routine; effective field provenance points to the user for that field, while `source` remains `builtin` and `declared_by` remains `default`.

In SASE's `src/sase/axe/config_backend.py` and runtime config types:

- parse the two wire fields;
- project them onto the routine runtime record (the Python internals may still use `LumberjackConfig`, but user-facing additions should use routine terminology);
- advance the core revision pin after the core change lands.

### 2. Carry source through the existing async collector

Extend `AxeCollectedData` and the loader state with a cached `routine_name -> source` mapping, populated during the existing off-thread config load. Do not compose config or inspect layers in a render, highlight, click, or timer callback.

The current refresh path already caches everything navigation needs. Source should become one more small immutable field in that payload. The hot `j`/`k` path must remain read-only and disk-free.

### 3. Generalize the panel projection without changing row identity

Replace the two routine memberships with fixed keys such as:

```text
service_procs
routines_builtin
routines_plugin
routines_custom
```

Retain the current global `_axe_items` list and stable `axe_item_key` values. Build it in panel order, sorting routine names within each source bucket, and emit every job immediately after its parent. `LumberjackItem` can carry a normalized source/section field; `ChopItem` can either carry the inherited section or have the panel index consult the cached parent mapping. Carrying the section on both row types makes the partition function total and cheap.

Do not use class name alone for routine membership after this change. Unknown source values should map to Custom and remain observable in diagnostics/tests.

### 4. Mount fixed panels but suppress empty optional ones

Four statically known `BgCmdList` widgets are simpler and safer than dynamic mount/unmount churn during refresh. Toggle display for empty Plugin/Custom panels; do not include hidden panels in panel order, navigation, height allocation, or width settlement for that paint.

Derive a `visible_services_panel_order` from the fixed order plus nonempty slices. Use it consistently for:

- full panel paint;
- focused-panel lookup and focus transfer;
- `J`/`K` adjacency;
- title updates;
- height allocation;
- sidebar width settlement;
- local/global click translation.

The index object should own or expose this visible order rather than letting each caller independently filter it.

### 5. Make title statistics group-local

Reuse `scheduled_routines_panel_stats` with each section's routine-name subset. Build titles such as:

```text
Built-in Routines · 7 [R…] · 31 jobs …
Plugin Routines · 2 [R…] · 5 jobs …
Custom Routines · 1 [I1] · 1 job
```

Pluralize `job` if this is touched. Render the scheduler-level badge once on the first visible routine panel, not once per group. Exact provider/layer belongs in the selected routine's detail, not every row title.

### 6. Generalize sizing

Pass only visible widgets to `allocate_panel_heights`. Use each widget's rendered line count and choose the largest routine panel as the filler when everything fits; on overflow, the existing smallest-first logic naturally preserves compact panels. Do not hard-code a filler index or a two-element collapse list.

Apply inter-panel margin by class (for example, every visible panel after the first) instead of targeting `#scheduled-routines-panel` specifically.

### 7. Preserve navigation and refresh invariants

Acceptance criteria should include:

- `j`/`k` walks the global visual order across section boundaries without an extra chrome stop;
- `J` lands on the first row of the next visible section and `K` on the last row of the previous visible section, wrapping and skipping empty/hidden sections;
- `Ctrl+O` returns to the prior logical row;
- clicking a row in any section maps to the correct global identity;
- folding a routine changes only its own section and preserves selection by identity;
- a config refresh that changes an entry's fields but not its first-declaration source does not move it;
- a newly introduced custom/plugin routine appears in the correct section without stealing focus;
- same-panel highlights remain O(1) widget work and perform no disk I/O;
- sidebar width still follows the widest visible panel;
- narrow terminals allocate usable space without showing empty two-row panels.

## Verification plan

### Core and Python model tests

- first-declaration source for built-in/plugin/user/overlay/local layers;
- built-in with user override remains built-in;
- plugin with overlay override remains plugin;
- exact `declared_by` label/path is retained;
- public `routines`/`jobs` and compatibility `lumberjacks`/`chops` agree;
- generated jobs inherit base ownership;
- unknown/missing source degrades to Custom in the TUI projection;
- deterministic source-section and alphabetical ordering.

### Panel and navigation tests

- partition/global-local round trips across all four keys;
- fixed order and skipping absent Plugin/Custom sections;
- click translation in each section;
- `J`/`K` forward/backward wrapping with one, two, three, and four visible sections;
- identity restoration when a section appears or disappears;
- title counts limited to the section's routines/jobs;
- scheduler badge rendered exactly once;
- height allocation gives small sections natural height and the large section scrolling space;
- highlight path remains disk-free and does not rebuild panel options.

### Visual coverage

Regenerate focused visual cases rather than relying only on broad golden churn:

- current-like Built-in + Custom layout at 120x40;
- Built-in + Plugin + Custom;
- no Plugin/Custom sections;
- narrow 70x36 layout;
- selection/focus chrome in each routine section;
- failure badges distributed across different source sections;
- long provider/custom routine names and sidebar-width clamping.

Documentation and glossary examples must be updated so the Services tab no longer claims there are exactly two nav sections. `Nav Section` should describe Service Procs plus each visible routine-source panel.

## Recommended solution

Implement source-based routine nav sections now, with **Built-in Routines**, **Plugin Routines**, and **Custom Routines** after **Service Procs**; suppress empty optional sections and keep jobs with their parent routine. Add immutable first-declaration `source` and `declared_by` fields to the Rust AXE inventory, following the existing service-proc contract, and carry that cached metadata through the current off-thread collector into a generalized multi-panel projection. Preserve the global row identity/index, `j`/`k`, `J`/`K`, click, fold, and selection-restore machinery; generalize only panel membership, visible order, titles, and sizing. Defer arbitrary user-defined groups, semantic/status grouping, and a grouping toggle until a real use case demonstrates that the three stable ownership buckets are insufficient.
