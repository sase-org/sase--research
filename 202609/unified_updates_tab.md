---
create_time: 2026-09-02
updated_time: 2026-09-02
status: research
tags:
  - ace
  - tui
  - updates
  - ux
---

# A Unified Updates View for SASE Admin Center

## Executive summary

The three current Updates sub-tabs—Core, Plugins, and Agent CLIs—should be replaced by
one searchable, action-first inventory with a shared summary, one master list, and one
contextual detail pane.

The key UX decision is that the primary grouping should be **what needs the user's
attention**, not which subsystem owns an item. Core, plugin, and Agent CLI updates are
all update-related objects, and users often need to assess them together. The current
sub-tabs conceal that shared state: a badge may indicate an Agent CLI update while the
opened view defaults to Core; the global “all current” calculation is displayed only on
Core; and marks can survive in a hidden sub-tab. Simply stacking today's three views
would technically expose everything, but it would leave Agent CLIs below a plugin
catalog that can contain thousands of entries and would waste most of the viewport on
Core when it is current.

The recommended view has these properties:

- A persistent summary reports actionable updates, manual actions, errors, current
  items, source freshness, connectivity, and install mode.
- One filter searches all update domains and accepts a small set of composable tokens
  such as `@updates`, `type:cli`, and `status:error`.
- One list contains every entity exactly once. Its first section, **Needs action**,
  interleaves core, plugin, and Agent CLI items that require attention. Remaining items
  are separated into stable domain and trust sections.
- One detail pane dispatches to the existing rich Core, Plugin, or Agent CLI detail
  renderer. Update operations retain their existing, explicit key bindings because the
  operations have different scope and safety characteristics.
- Wide terminals use master/detail; narrow terminals use list-to-detail drill-down
  while preserving filter, highlight, and marks.
- Implementation introduces a typed presentation adapter over the already unified load
  result. It should reuse the domain-specific renderers and actions rather than merging
  the existing modules into a monolith.

This gives users one honest answer to “what needs updating?” while preserving the
important differences between changing the SASE environment, installing a plugin, and
running a third-party CLI's update command.

## The product problem

### The current tabs divide one user task by implementation domain

The user enters Updates to answer a small set of questions:

1. Is anything out of date or broken?
2. What requires my attention now?
3. What will a particular action change?
4. Can I inspect or manage the rest of the installed/available inventory?

Core, Plugins, and Agent CLIs are meaningful object types, but they are not separate
user journeys. The top-level update badge already combines them, and the underlying
`UpdateStatus` already models component and provider candidates together. Dividing the
destination by type makes the user translate a global signal back into three places.

The split also creates concrete inconsistencies:

- `UpdatesSessionState` defaults to the Core sub-tab, even when only an Agent CLI or
  plugin has an available update.
- The “all up to date” predicate considers Core, plugins, Agent CLIs, and source errors,
  but its banner is mounted only in Core.
- Each inventory has independent selection, bookmark, mark, and hint state. Marks can
  persist after leaving a sub-tab, while Escape only clears marks in the active one.
- `/` filters plugins only. There is no way to search the full set represented by the
  Updates badge.
- The meaning and availability of `Space`, `A`, `H`, `U`, and `m` depend partly on a
  hidden active-sub-tab variable rather than on the selected object.
- Footer text has been compressed to leave room for the sub-tab hint, making the pane's
  already-rich actions harder to discover.

These are symptoms of the same mismatch: the data and the user's mental model are
unified, while the presentation state is fragmented.

### The three views are not symmetric

The existing sub-tabs should not be treated as three interchangeable datasets for one
template:

- **Core** is a single status card with installed and latest versions, install mode,
  incoming commits, and one broad update action.
- **Plugins** is a potentially very large searchable catalog with built-in/community
  trust boundaries, installation state, latest-version lookups, selection marks, and
  install/uninstall/update actions.
- **Agent CLIs** is a small provider inventory whose rows expose installed/latest
  versions and install methods, with rich per-provider details and update history.

This asymmetry rules out two tempting designs.

First, three vertically stacked cards would restore visibility but make the screen
uneven and poorly scalable. The project previously placed Core above Plugins; adding
Agent CLIs to that arrangement would either bury a high-value status below up to 2,000
plugins or require nested scrolling regions.

Second, a uniform table would flatten essential differences. A plugin can be available
but not installed; a CLI update may be manual; a Core update can rebuild or restart the
running environment. The rows can share identity, status, filtering, and navigation,
but they should not imply a single interchangeable action.

### Repository evidence

The recommendation is grounded in the current implementation rather than only in
general UI patterns:

- `src/sase/ace/tui/modals/plugins_browser_layout.py` defines the Core, Plugins, and
  Agent CLIs `PanelTabStrip`/`ContentSwitcher` structure. The Core child is primarily a
  versions panel; Plugins and Agent CLIs each own a separate master/detail layout.
- `src/sase/ace/tui/modals/config_center_session.py` stores `active_subtab` plus separate
  Plugin and Agent CLI bookmarks. Core is the default.
- `src/sase/ace/tui/modals/plugins_browser_loading.py` already loads the plugin catalog,
  Core versions, composite `UpdateStatus`, Agent CLI statuses, errors, colors, and
  history into one result. Independent failures are already representable.
- `src/sase/ace/tui/modals/plugins_browser_status.py` computes “all up to date” across
  Core, plugins, Agent CLIs, and their errors. The corresponding banner is nevertheless
  displayed only in the Core child.
- `src/sase/ace/tui/modals/plugins_browser_rendering.py` has the mature Plugin
  `OptionList`, disabled built-in/community headings, cached filter haystacks, identity
  maps, community warnings, and lazy latest/incoming detail.
- `src/sase/ace/tui/modals/plugins_browser_agent_clis.py` supplies Agent CLI rows,
  automatic/manual command detail, errors, last outcomes, and selected/all update
  history.
- `src/sase/ace/tui/modals/plugins_browser_agent_clis_actions.py` dispatches Space and
  batch behavior from `active_subtab`. Plugin and CLI marks can coexist, but only the
  active domain's marks are cleared first by Escape.
- `src/sase/updates/status.py` is already a composite domain model for component and
  provider candidates. The top Updates badge therefore reports a broader scope than
  the first screen users see after opening it.
- `tests/perf/README.md` and the plugin-browser performance fixtures explicitly cover
  catalogs through 2,000 entries and enforce a 16 ms p95 budget for filtering and
  navigation.
- `docs/configuration.md` and `docs/ace.md` document the different action scopes and the
  separate global `,U` Update panel, which should remain a fast broad-action surface.

History also explains the current shape. Core was added as a status/update panel, and
the later Agent CLI browser introduced the three-way split. Before that split, Core and
Plugins were vertically combined. Returning to the old vertical structure and appending
Agent CLIs would recover visibility but not solve prioritization or catalog scale.

## What external patterns suggest

The relevant design guidance converges on one view with explicit grouping and
progressive detail:

- [GOV.UK's tabs guidance](https://design-system.service.gov.uk/components/tabs/)
  cautions that tabs hide content and recommends headings or a table of contents when
  users need to compare or read across sections. Updates are specifically a cross-domain
  assessment task.
- [Carbon's tabs guidance](https://carbondesignsystem.com/components/tabs/usage/)
  says tabs are for related content groups, not information comparison, and recommends
  a lower-hierarchy control when users are filtering the same content. Core, plugins,
  and CLIs are better expressed as row types and filters than navigation destinations.
- [Visual Studio Code's Extensions view](https://code.visualstudio.com/docs/configure/extensions/extension-marketplace)
  combines discovery and management in one searchable inventory. Queries such as
  `@updates`, `@installed`, and `@builtin`, plus an Update All action and a selected-item
  detail surface, scale better than parallel Installed/Available/Updates destinations.
- [PatternFly's toolbar guidance](https://v4-archive.patternfly.org/v4/components/toolbar/design-guidelines/)
  groups item count, filters, selection state, and global actions immediately above the
  data, with responsive overflow instead of exposing many equal-weight buttons.
- [Apple's list and table guidance](https://developer.apple.com/design/human-interface-guidelines/lists-and-tables)
  supports grouped lists for distinct kinds of content and a split view when selecting
  an item reveals substantial detail.
- [Microsoft's adaptive master/detail sample](https://learn.microsoft.com/en-us/samples/microsoft/windows-universal-samples/xamlmasterdetail/)
  changes from side-by-side panes to separate list and detail surfaces at narrow widths
  without changing the underlying navigation model.
- The [WAI-ARIA listbox pattern](https://www.w3.org/WAI/ARIA/apg/patterns/listbox/)
  distinguishes focus from selection and supports grouped options. It also reinforces
  that Space should have one intelligible selection meaning in a multiselect list.
  SASE should therefore retain typed marks and make their different operations visible,
  rather than presenting every update entity as a generic checkbox.
- Textual's [OptionList](https://textual.textualize.io/widgets/option_list/) already
  supports rich options, disabled headings, a highlight, and efficient keyboard
  navigation. Its [SelectionList](https://textual.textualize.io/widgets/selection_list/)
  is less suitable here because not every row participates in the same batch operation.

The lesson is not to imitate a graphical package manager literally. It is to preserve
one searchable information space, make status and scope visible, and use detail plus
explicit actions for heterogeneous operations.

## Proposed information architecture

### 1. A persistent status and control band

The first line should summarize the whole truth represented by the Updates badge. For
example:

```text
↑ 4 updates  ·  ! 1 manual  ·  6 current  ·  18 available   Checked just now   ONLINE
PyPI managed
```

The vocabulary should distinguish:

- **updates**: actions SASE can perform;
- **manual**: known newer versions that require a command or intervention SASE cannot
  safely execute;
- **errors**: sources or status checks that failed;
- **current**: installed entities verified current;
- **available**: known but uninstalled plugins or CLIs, not pending updates.

When every source was checked successfully and no action is needed, this compresses to
a green `All sources current` state. When a source failed, the UI must never claim that
everything is current. It should say, for example, `No known updates · Agent CLI source
unavailable`. This is more honest than making the user infer uncertainty from an empty
domain view.

The SASE install mode belongs here because it changes the interpretation of the broad
Core/plugins update operation. Moving it out of a Plugin-only context also makes `m`
coherently global within the Updates pane.

Immediately below, use one full-width filter:

```text
/ Filter components, plugins, and agent CLIs…
```

Plain text should match name, provider, type, installed/latest versions, install method,
and status. A deliberately small query vocabulary can cover the common scopes:

- `@updates`, `@installed`, `@available`
- `type:core`, `type:plugin`, `type:cli`
- `status:manual`, `status:error`, `status:current`
- `trust:official`, `trust:community`

These are filters, not tabs or chips. Empty input always restores the full list, filters
compose, and the current query remains visible. Adding clickable scope controls that
hide the other domains would recreate the original problem with different styling.

### 2. One action-first master list

Every known entity should appear exactly once. The default ordering should be:

1. **Needs action**
2. **SASE core**
3. **Agent CLIs**
4. **Installed plugins**
5. **Available · built-in**
6. **Available · community**

`Needs action` contains every actionable update, manual update, and blocking/error item
across all three domains. Within it, sort by severity first, then type and display name
for stability. The other sections contain only entities not already promoted into
Needs action.

This ordering answers the urgent question without forcing the user to know the item's
domain. It also ensures that a CLI update or Core source error cannot be buried below a
large plugin catalog. The later sections preserve useful inventory structure and the
community-plugin trust boundary.

Rows should expose a compact type cue plus their most decision-relevant status:

```text
NEEDS ACTION
 ↑  CORE     SASE                 0.14.2 → 0.15.0
 !  CLI      Claude Code          1.2.3 → 1.4.0   manual
 ↑  PLUGIN   sase-github          0.8.1 → 0.9.0

AGENT CLIS
 ✓  CLI      Codex                0.42.0           current
 –  CLI      Gemini CLI           not installed
```

Color and icons should reinforce, not replace, the text. Use stable typed identities
such as `core:sase`, `plugin:sase-github`, and `agent-cli:claude` so refreshing an item
or moving it into/out of Needs action does not lose the user's highlight.

Section headings should be disabled `OptionList` items, as current plugin headings are.
Repurpose `]` and `[` from sub-tab switching to next/previous section, selecting the
first selectable item there. Keep `'` as a jump picker, now over every visible entity.
Do not make sections collapsible initially: search and section jumps solve navigation
without introducing more hidden state.

### 3. One contextual detail pane

The right pane should be a dispatcher, not a lowest-common-denominator component:

- **Core detail**: installed/latest versions, install mode, upstream status, incoming
  commits, rebuild/restart implications, a clear reason when blocked, and the `u`
  action.
- **Plugin detail**: the existing description, source, installed/latest versions,
  incoming changes, built-in/community status, community warning, and exact contextual
  actions.
- **Agent CLI detail**: the existing provider, binary and executable, installed/latest
  versions, install method, exact automatic or manual command, skip reason, docs link,
  errors, and last outcome. Preserve the `H` selected/all history panel below it.

Loading a lazy latest version or incoming changes should update the selected entity in
place. It must not reorder the list under the user's cursor until a deliberate refresh
or until the identity-based selection can be restored reliably.

### 4. Adaptive, not category-based, navigation

At wide widths, retain the efficient split view: list on the left, detail on the right.
At narrow widths—approximately below 100 columns, tuned through snapshots—show the
list full-width. Enter or Right opens the selected item's full-width detail; Escape or
Left returns to the list with filter, highlight, scroll position, and marks intact.

That temporary list/detail transition is not another tab system. It is a standard
master/detail adaptation based on space, and it never changes which update entities are
in scope.

## Interaction model

### Keep operations explicit

The current operations are materially different:

- `u` updates the coherent SASE Core and installed-plugin environment and can rebuild or
  restart running software.
- `U` updates one installed plugin.
- `i` installs selected or marked plugins; `I` installs every eligible plugin.
- `x` uninstalls the selected plugin.
- `A` runs provider-specific Agent CLI updates, potentially as several sequential
  external commands.
- `a` performs a full-network agents-repository sync.
- `m` changes the SASE installation mode.
- `r` refreshes status; `o` changes online/offline mode; `v` exposes version-related
  detail; `H` changes Agent CLI history scope.

The unified view should not map Enter to “do the likely update” or invent one generic
mutation. Highlighting a row is inspection. Mutating commands remain mnemonic,
explicit, and gated by the selected row's typed capabilities.

Global commands (`u`, `A`, `a`, `m`, `r`, `o`, `/`, `'`, `[`, `]`) are available from
the whole pane when their prerequisites are satisfied. Contextual commands (`i`, `I`,
`x`, `U`, `v`, `H`) are exposed only for applicable selections. The ACE help modal must
document global bindings; the footer should obey the project's conditional-keymap rule
and show contextual bindings only when they can be used.

The existing global `,U` Update panel should remain distinct. It is a quick action
surface built from cached status and offers broad choices such as Everything, SASE, or
providers. The Admin Center Updates view remains the slower, live inspection and
inventory-management surface. The implementation should call the same underlying
operations rather than duplicating update logic.

### Make mixed marks visible and predictable

`Space` can continue to toggle a mark only on rows with a natural deferred batch action:

- an installable plugin gets a visibly typed `[+]` install mark;
- an automatically updatable Agent CLI gets a visibly typed `[↑]` update mark.

Core and manual-only CLI rows cannot be marked. Plugin-update marks should not be added
in the first iteration; the existing `U` single-plugin and `u` coherent-environment
operations already have intentional scope.

A persistent selection summary prevents filters from hiding work:

```text
Selected: 2 plugin installs · 1 CLI update (1 hidden by filter)
```

`i` consumes plugin install marks and `A` consumes CLI update marks. If no matching
marks exist, preserve the current documented fallback behavior only after showing the
resulting scope in the confirmation/plan. In the unified pane, the first Escape clears
**all** marks, including filtered-out marks; a subsequent Escape closes or navigates
back. This replaces today's active-sub-tab-dependent clearing behavior.

## Loading, failures, and freshness

The current loader already returns Core versions, plugin catalog state, composite
update status, Agent CLI statuses, per-source errors, colors, and history in one
`PluginsLoadResult`. The unification is therefore a presentation change, not a reason
to serialize new network work or move shared backend behavior into Python.

Use stale-while-revalidate behavior:

1. Keep the last painted inventory visible.
2. Change the status band to `Checking…` and disable only actions whose inputs are
   uncertain.
3. Refresh independent sources off the UI thread.
4. Patch successful sources into the typed inventory.
5. Surface a failed source in the summary and as an actionable synthetic error row or
   state, without blanking successful domains.

Offline mode should retain known data and label its age. “Latest unknown” is not the
same as “current.” The all-current state is valid only when every enabled source
completed successfully and every installed entity was evaluated.

## Implementation design

### Add a typed presentation adapter

Introduce a pure module such as `updates_inventory.py` (or initially
`plugins_browser_inventory.py`) whose central type has fields equivalent to:

```text
UpdatesRow
  identity             # core:sase | plugin:<name> | agent-cli:<provider>
  kind                 # core | plugin | agent_cli | source_error
  display_name
  installed_version
  latest_version
  status               # update | manual | error | current | available | unknown
  section
  sort_key
  filter_haystack
  capabilities         # inspect, install, uninstall, update_one, mark_install, ...
  payload               # typed reference to the domain object
```

The adapter projects the existing shared load result into rows, classifies them, and
orders them. It must be deterministic and independently testable. Capabilities should
drive key availability and action dispatch; `active_subtab` should disappear from
those decisions.

Keep the current Core, plugin, and Agent CLI capability modules and pure Rich
renderables. The plugin-browser family is already substantial; unifying the UX is not
an invitation to merge thousands of lines into one class. The layout owns the shared
list, status/filter band, and detail slot, while a small dispatcher calls the existing
domain-specific detail and action code.

### Collapse UI state, not domain behavior

Replace:

- `PanelTabStrip` and the three Updates `ContentSwitcher` children;
- separate Plugin and Agent CLI `OptionList` widgets;
- separate programmatic-selection guards;
- `active_subtab` action branches;
- separate selection bookmarks in `UpdatesSessionState`.

With:

- one `OptionList`;
- one identity-to-row map and identity-to-option-index map;
- one first-option index per section;
- one programmatic-selection guard;
- one identity-based bookmark;
- typed plugin-install and CLI-update mark sets with one visible aggregate summary.

The session state is process-local, so no durable migration is required. During the
transition, selecting the old plugin or CLI bookmark as a fallback can make in-process
reloads and tests less surprising.

### Preserve the Rust boundary

No new shared update policy is required for this design. Classification into visual
sections, terminal layout, key hints, filter parsing, and detail dispatch are
presentation concerns and belong in the Python/TUI layer. Existing update discovery
and execution should continue through `UpdateStatus`, `sase_core_rs`, and the existing
adapters. If implementation discovers a rule that another frontend would need to
match—such as a new canonical definition of “manual update”—that rule should be added
to the Rust core rather than duplicated in the inventory adapter.

## Performance constraints

The repository's plugin-browser benchmarks cover catalogs of 10, 250, 1,000, and 2,000
entries and enforce sub-16 ms p95 targets for filter keystrokes and `j` navigation at
2,000 entries. The unified view must retain those targets.

Concretely:

- Build row objects and lowercase filter haystacks once per catalog/source refresh,
  not on every render.
- Rebuilding a filtered projection may be O(n); selection, jump lookup, navigation,
  mark toggling, and detail lookup should remain O(1).
- Keep identity and option-index maps rather than scanning widgets.
- Patch the smallest possible row when a lazy version/latest lookup finishes.
- Preserve the existing detail debounce and lazy incoming/latest queries.
- Avoid per-row reactive widgets; continue using Rich-renderable `OptionList` options.
- Do not recompute all section counts or row markup for every highlight movement.

Core and Agent CLI rows add nearly constant overhead. The main regression risk is
rebuilding or reclassifying the plugin projection during navigation, not the act of
placing all three domains in one list.

## Validation strategy

### Pure behavior tests

Add focused tests for:

- section classification and stable ordering;
- every entity appearing exactly once;
- cross-domain text and token filters;
- partial-source failure versus truthful all-current state;
- stable identity selection when an item moves into or out of Needs action;
- capability-derived action availability;
- mixed typed marks, hidden-mark counts, consumption, and Escape clearing;
- section jumps skipping disabled headings;
- manual CLI updates and community-plugin warnings remaining prominent.

### Interaction and visual tests

Exercise these user-visible scenarios:

- only Core has an update;
- only a plugin has an update;
- only an Agent CLI has an update;
- mixed actionable and manual updates;
- all sources current;
- one source failed while the others are current;
- online, offline, development, managed, and non-`uv` modes;
- marked items hidden by a filter;
- plugin detail, community warning, CLI detail, and selected/all CLI history;
- refresh that changes the selected item's section;
- opening Updates from the global badge with a non-Core-only update.

Keep the current 120×40 visual coverage and add narrow 100×24 and 80×24 snapshots for
the adaptive list/detail transition. Update the performance fixture to project the full
unified inventory at 10/250/1,000/2,000 plugins and preserve the existing p95 budgets.

Documentation in `docs/configuration.md`, `docs/ace.md`, the help modal, keymap hints,
and relevant snapshots must change together. Default keymap configuration needs review
if any binding changes rather than merely changing context.

## Suggested implementation sequence

1. Add the pure typed inventory adapter, classification/filter logic, stable identities,
   and exhaustive unit tests without changing the screen.
2. Replace the sub-tab strip and switcher with the shared summary/filter/list/detail
   layout; reuse the existing detail renderers.
3. Dispatch actions from typed row capabilities, unify selection state, and make mixed
   marks visible and globally clearable.
4. Add adaptive narrow behavior, update help and documentation, refresh snapshots, and
   run the unified 2,000-row performance benchmarks.

This sequence separates information-model risk from widget and action risk while still
shipping the feature as one coherent UX change.

## Acceptance criteria

The design is successful when:

- Opening Updates reveals every known actionable update and every source failure
  without another keystroke.
- Every Core, plugin, and Agent CLI entity appears exactly once.
- The screen never claims “all current” when any enabled source is unknown or failed.
- A user can jump between semantic sections with one key and search all domains with
  one filter.
- Highlight, scroll position, filter, and marks survive refreshes and narrow-detail
  navigation.
- Filtered-out marks remain visible in the aggregate selection summary and Escape
  clears all marks predictably.
- Existing update plans and execution paths retain their present scopes; UI unification
  does not silently combine heterogeneous mutations.
- Plugin community trust warnings and Agent CLI manual commands/history remain at least
  as visible as they are today.
- Filter and navigation performance remains below the existing 16 ms p95 budget at a
  2,000-plugin catalog.

## Research limitation

The audited SASE reference-memory read for the TUI performance note could not complete
because `sase memory read` detected a pre-existing split/colliding home memory layout
and refused to choose one. The canonical memory files were not bypassed or modified.
Performance conclusions above were instead checked against the repository's committed
performance README, benchmark fixtures, and current rendering implementation. Before
implementation lands, the memory-layout collision should be resolved through the
normal SASE memory workflow and the required reference read should be repeated.

## Recommended solution

Replace the Core, Plugins, and Agent CLIs sub-tabs with **one action-first,
searchable master/detail inventory**. Put cross-domain updates, manual actions, and
errors together in a top-level Needs action section; follow it with Core, Agent CLI,
installed-plugin, built-in-available, and community-available sections so that all
entities remain discoverable without hiding high-priority state. Use a persistent
truthful summary, one global filter, section-jump keys, typed identities, and a
domain-specific detail dispatcher. Preserve explicit existing update commands and
their underlying execution paths, while unifying highlight, bookmarks, marks, error
reporting, and responsive navigation. Implement it as a thin typed presentation layer
over the already unified load result, keeping the mature domain renderers and Rust
backend boundary intact.
