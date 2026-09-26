# Scheduled routine navigation sections

## Executive summary

Grouping routines by where they originate is a good idea, but the useful product
boundary is not “one nav section for every config layer.” I recommend three stacked
Services-tab nav sections in total:

1. **Service Procs** (unchanged)
2. **Built-in Routines**
3. **Additional Routines** (plugin-, user-, machine-, and project-declared routines)

Empty routine sections should disappear. If no routines exist at all, one neutral
**Scheduled Routines** empty-state section should remain so the add action is
discoverable.

This is preferable to mere divider rows in the current Scheduled Routines panel. On
the current machine, the effective configuration contains seven built-in routines with
29 jobs and one user routine with one job. With routine trees initially expanded, that
is 36 built-in rows before the two additional rows. An in-list divider would label the
additional routine but still leave it below the fold; a true nav section keeps the
small additional set visible and makes it reachable with the existing `J`/`K` section
jumps.

The implementation must first add stable routine-origin metadata to the Rust config
domain. It must not infer “built-in” from routine names or from the layer that supplied
the last effective field. A built-in routine that a user overrides is still a built-in
routine. The service-proc config domain already implements the right precedent with
stable `source` and `declared_by` fields.

## Scope and evidence

I inspected the current routine config model, Rust-owned AXE composition and
provenance, the Services sidebar item/index/render paths, navigation behavior, dynamic
panel sizing, documentation, unit tests, and existing 120x40 and 70x36 visual goldens.
The relevant implementation is concentrated in:

- `src/sase/ace/tui/actions/axe_display/_panels.py`
- `src/sase/ace/tui/actions/axe_display/_panel_navigation.py`
- `src/sase/ace/tui/actions/axe_display/_render_panels.py`
- `src/sase/ace/tui/actions/axe_display/_loader_items.py`
- `src/sase/ace/tui/actions/axe_display/_data.py`
- `src/sase/ace/tui/widgets/bgcmd_list.py`
- `src/sase/ace/tui/util/panel_heights.py`
- `src/sase/axe/config_backend.py`
- linked `sase-core/crates/sase_core/src/config/axe.rs`
- linked `sase-core/crates/sase_core/src/service/config.rs`

The two-panel Services sidebar was introduced only recently in commits `3f5d34e9fd`
and `37bf264296`. It was deliberately designed around a single global `_axe_items`
sequence partitioned into panel-local slices, stable identity restoration, cache-only
navigation, per-panel metadata titles, dynamic height allocation, and `J`/`K` jumps.
That architecture is extensible, but a new nav section is not merely a heading: it has
selection, focus, height, title, empty-state, mouse-index, documentation, and visual
snapshot semantics.

The live effective configuration observed during this research was:

| Origin | Routines | Jobs | Expanded tree rows |
|---|---:|---:|---:|
| Built-in default layer | 7 | 29 | 36 |
| User layer | 1 | 1 | 2 |

The eight routines are currently sorted globally by name. The additional `telegram`
routine happens to sort near the end, after a large built-in tree. This distribution is
important: the proposed split is useful not just as visual taxonomy, but as a way to
keep a small non-built-in set independently visible and directly navigable.

## What “built-in” should mean

“Built-in” is ambiguous unless the requirement defines it. There are at least three
possible interpretations:

1. The routine name appears in SASE's default config.
2. Every effective field currently comes from the default config.
3. The routine was first declared by the built-in config layer, even if later layers
   override some fields.

The third definition is the stable and useful one. It describes ownership/origin,
matches how service procs behave, and avoids surprising section moves after an edit.
For example, changing the interval of built-in `checks` in user config should not move
`checks` into Additional Routines.

The current AXE inventory does not expose this entity-level origin. It exposes
effective per-field provenance and raw contributions for writable layers. Deriving a
routine's origin in Python from those structures would be fragile:

- effective provenance can omit the original declaration after a complete override;
- writable contributions intentionally omit built-in and plugin layers;
- AXE accepts canonical `routines`/`jobs` and legacy `lumberjacks`/`chops` spellings;
- reproducing first-declaration logic in the TUI would cross the project's Rust core
  boundary and risk disagreement with CLI or future web clients.

The linked Rust core already contains the exact pattern to reuse. A
`ServiceProcConfigWire` has `source` (`builtin`, `plugin`, or `user`) and
`declared_by`; its builder sets them when an entry is first seen, while later layers
continue to override individual fields without changing origin. AXE inventory entries
should gain equivalent metadata. User, overlay, and local layers can continue to
coalesce to public source `user`, while `declared_by` preserves the precise layer label.

## Critique of the proposed idea

### What is good about it

- It exposes a meaningful trust and ownership boundary. Packaged automation is easier
  to distinguish from automation added by a plugin, user, machine overlay, or project.
- It improves reachability. A small additional set no longer sits beneath dozens of
  expanded built-in job rows.
- It uses navigation behavior users already have. `J`/`K` already means next/previous
  nav section and skips empty panels.
- It preserves routine/job hierarchy. Jobs remain children of their parent routine;
  no scheduler/runtime semantics need to change.
- It creates a natural home for per-group counts and health badges without adding
  source chips to every narrow sidebar row.

### What needs adjustment

The initial concept is underspecified in two ways.

First, origin should not automatically produce one section per config-layer kind.
`builtin`, `plugin`, `user`, `overlay`, and `local` could create several one-row panels,
each costing borders, separators, focus transitions, and title space. The 70x36 golden
already shows meaningful vertical pressure with two panels. A panel-per-layer design
would scale layout chrome with configuration complexity rather than user value.

Second, origin grouping is not a general semantic organization scheme. Built-in
routines cover hooks, waits, usage, remote mirrors, comments, and housekeeping; the
fact that they ship together does not say their work is related. Grouping by cadence,
health, or operational domain might sometimes be more useful, but those are different
features and should not be smuggled into this change.

I therefore recommend an intentionally narrow first version: two origin buckets,
Built-in and Additional. Preserve exact provenance in details, but do not expose
arbitrary user-defined sections yet.

## Alternatives considered

### Keep one panel and add divider headings

This is the smallest UI change. `BgCmdList` already prepends a non-selectable
`── oneshots ──` line to the first oneshot option, so a similar first-row header could
label Built-in and Additional groups without disturbing global item identities.

This option is attractive if the goal is only labeling. It does not satisfy the more
valuable navigation goal:

- `J`/`K` cannot jump between routine groups;
- the panel has one aggregate title rather than group-specific counts;
- one group cannot retain its own visible height;
- Additional Routines remain below the 36-row built-in tree on the current config.

It is a good fallback if terminal-height testing shows three real panels are unusable,
but it should not be the primary design.

### One panel per exact source kind

This would create Built-in, Plugin, User, Machine, and Project routine panels as needed.
It is precise but too granular for the evidence available. Most sections would be
empty or tiny, and their set could change as plugins or project config change. It also
forces more policy questions: whether a plugin routine overridden by a machine layer
belongs under Plugin or Machine, how to order project versus user, and how many panels
the sidebar may tolerate.

The stable answer to the override question is still “first declaration,” but displaying
all of those distinctions as peer nav sections is unnecessary. `declared_by` can show
the exact source in the routine detail view.

### User-configurable arbitrary sections

An explicit grouping facility could eventually be useful, but it is premature. Putting
`nav_section` on a scheduler routine mixes frontend presentation into scheduler domain
config. Putting a query-based section catalog under `ace` avoids that coupling but
introduces ordering, overlap, unmatched-routine, validation, persistence, editing, and
cross-frontend questions without a demonstrated second grouping need.

If arbitrary grouping is later justified, it should be an ACE display configuration
that selects routines using stable metadata, with a mandatory catch-all section. It
should not change routine execution or live in the AXE runtime schema.

### A toggleable grouping mode

Agents already have richer grouping behavior, so a future Services grouping mode is
conceivable. It would add another control and persisted/session state to solve a problem
that currently has one clear default. The source split should first prove useful as a
fixed layout.

## Adjusted requirements

These are deliberate changes to the tentative request:

1. **Use two routine origin buckets, not an open-ended bucket per source.** Built-in
   contains routines first declared by the built-in layer. Additional contains all
   others.
2. **Treat first declaration as origin.** Later overrides never move a routine between
   sections.
3. **Keep grouping presentation-only.** Scheduler process structure, routine IDs,
   state paths, commands, edit targets, and runtime ordering remain unchanged.
4. **Suppress empty grouped panels.** Do not render an empty Additional Routines panel
   on a default-only installation or an empty Built-in panel in an additional-only
   test/configuration.
5. **Preserve one neutral zero-state.** When no routines exist, show a single Scheduled
   Routines empty section with the existing add hint.
6. **Do not add arbitrary grouping configuration in the first implementation.** Keep
   that as a future extension driven by another concrete use case.
7. **Expose exact origin in details.** A selected routine should show a `Source` line,
   analogous to service procs, so an Additional routine can be distinguished as plugin,
   user, machine overlay, or project config without widening every sidebar row.

## Implementation design

### 1. Add origin to the Rust AXE inventory

In `sase-core`, extend `AxeInventoryEntryWire` with stable entity-level `source` and
`declared_by` fields. Determine them from the first ordered layer that declares the
routine or job identity after canonical/legacy alias normalization. Use the same public
source classification as service procs:

- layer kind `builtin` -> source `builtin`
- layer kind `plugin` -> source `plugin`
- layer kinds `user`, `overlay`, and `local` -> source `user`

`declared_by` should retain the concrete layer label/path. Base jobs inherit their own
first declaration; generated `for_each` instances inherit their base job's origin.

This belongs in the Rust core because other frontends need the same classification and
because the core already owns layer order, aliases, merge behavior, and provenance.
Update the Python `AxeInventoryEntry` facade, binding round-trip tests, and SASE's
`sase-core-revision.txt` pin as required by the core boundary.

### 2. Carry routine origin through the cached Python model

Add `source` and `declared_by` to `LumberjackConfig`, and pass the Rust inventory's
routine metadata into `parse_lumberjacks`. Then carry it through the off-thread
collector into either:

- `LumberjackSnapshot`, plus a cached name-to-group map; or
- `AxeCollectedData` as explicit routine metadata.

The collector already loads config off the event loop. Rendering and `j`/`k` navigation
must continue to read only cached state; no provenance lookup, file read, or config
composition belongs on a keypress path.

### 3. Partition into three fixed panel keys

Replace the two-key panel taxonomy with:

```text
service_procs
builtin_routines
additional_routines
```

Add a routine-group field to `LumberjackItem` and `ChopItem` (with safe defaults for
tests/compatibility), or otherwise make parent group membership available to
`build_services_panel_index`. Keep `axe_item_key` based only on semantic identity:
routine name, or routine/job name. That allows identity restoration to preserve the
selection if regrouping or a config refresh moves an item to a different panel.

Build the global list in visual order: service procs, oneshots, built-in routine trees,
then additional routine trees. Sort routine names alphabetically within each routine
bucket. Per-routine fold keys remain unchanged.

### 4. Mount fixed widgets but display only meaningful sections

Static widgets are preferable to mounting and unmounting panels during refresh. They
keep focus objects stable and avoid turning a config reload into Textual tree churn.
Mount the two routine widgets up front, hide empty group widgets, and exclude hidden
widgets from height and width calculations. When both groups are empty, display one of
the widgets with a neutral Scheduled Routines title and the existing empty placeholder.

Generalize `_axe_panel_widgets`, `SERVICES_PANEL_ORDER`, title construction, local/global
index maps, focus chrome, mouse selection translation, and the startup painted-panel
default. The current `adjacent_nonempty_panel` logic already generalizes to more than
two keys and should continue skipping empty sections.

### 5. Preserve small sections in height allocation

`allocate_panel_heights` already supports an arbitrary number of panels and fixes
smaller natural-height panels before giving overflow to fractional panels. Feed it only
visible panels. Choose the largest visible routine section as the filler rather than
hard-coding an index. In the current distribution, Built-in Routines scrolls while the
two-row Additional Routines section remains fully visible.

This is the main UX reason to prefer real sections. Confirm it at both existing golden
sizes; border and separator overhead should not cause Service Procs or Additional
Routines to collapse below useful content.

### 6. Make titles local and details precise

Generalize the Scheduled Routines title builder to accept a label and a subset of
routine names. Each routine panel should show counts/status for only its own routines
and jobs. Avoid adding a source suffix to each sidebar row; the narrow golden has little
horizontal headroom.

Add `Source: builtin (default)`, `Source: plugin (...)`, or the precise user/overlay/
local declaration to the selected routine overview. The service-proc detail renderer is
the existing visual and semantic precedent.

The scheduler-health badge applies to both buckets. To avoid duplicated noisy text,
show it on the first visible routine panel (normally Built-in), while the existing SVC
health pill continues to provide tab-wide status.

## Risks and edge cases

- **Override stability:** a full user override must not reclassify a built-in routine.
- **Name collision:** a user contribution using a built-in routine name is an override,
  not a new Additional routine.
- **Plugin override:** plugin-origin routines remain Additional after user/machine
  overrides; details retain the plugin declaration and effective field provenance.
- **Legacy spelling:** origin must agree for `axe.routines` and
  `axe.lumberjacks`, including mixed-layer alias use.
- **Generated jobs:** every generated row must stay in its parent routine's section.
- **Selection restoration:** config refreshes and source changes must preserve selected
  routine/job identity even if its global index and panel-local index change.
- **Empty groups:** `J`/`K` must skip them and focus must never target a hidden widget.
- **All-empty state:** the add call-to-action must remain visible and non-selectable.
- **Narrow terminals:** an extra border and separator consume vertical space; the
  70x36 golden is a required acceptance case, not optional polish.
- **Hot path:** no source classification, config parsing, `stat`, or disk I/O may enter
  navigation or rendering.
- **Terminology:** update the Nav Section glossary and docs that currently state there
  is exactly one Scheduled Routines panel.

## Verification strategy

The implementation should add focused coverage before updating goldens:

### Rust/core tests

- built-in, plugin, user, overlay, and local first declarations;
- later overrides preserve first-declaration `source`/`declared_by`;
- a new higher-layer identity gets that higher-layer origin;
- canonical and legacy AXE spellings classify identically;
- base and generated jobs receive correct origin metadata;
- Python binding round-trip includes the new fields.

### Python/model tests

- `AxeInventoryEntry` and `LumberjackConfig` receive origin correctly;
- collector output contains cached grouping metadata;
- no navigation path loads config or reads disk.

### Panel/navigation tests

- global-to-local partitioning across all three panel keys;
- visual order is Service Procs -> Built-in -> Additional;
- `J`/`K` advances and wraps across three panels;
- empty groups are skipped;
- mouse selection maps panel-local rows to the right global identity;
- source regrouping restores the same selected routine/job;
- per-panel titles count only their subset;
- height allocation leaves the small Additional panel at natural height while the
  built-in tree scrolls.

### Visual/docs coverage

- 120x40 with both groups;
- 70x36 with both groups;
- built-in only (no empty Additional panel);
- additional only (no empty Built-in panel);
- no routines (one neutral empty state);
- focus after `J` lands on the first item of each visible section;
- update `docs/ace.md`, `docs/axe.md`, onboarding copy, and the Nav Section glossary.

## Recommended solution

Implement **two origin-based routine nav sections: Built-in Routines and Additional
Routines**, alongside the existing Service Procs section. Hide empty routine sections,
retain one neutral Scheduled Routines empty state, sort alphabetically within each
bucket, and preserve the existing global identity/fold model. Define origin as the
first config layer that declares the routine; later overrides do not change it.

Add `source` and `declared_by` to the Rust-owned AXE inventory by following the existing
service-proc precedent, carry that metadata through `LumberjackConfig` and the off-thread
TUI cache, and show exact source in the routine detail view. Let the largest routine
panel absorb overflow so small Additional sets stay visible, and keep `J`/`K` as the
navigation contract across the three panels.

Do **not** add arbitrary user-defined sections or one panel per exact config layer in
this iteration. If a second real grouping need emerges, add an ACE-only display grouping
facility later; do not put presentation metadata into scheduler runtime config.
