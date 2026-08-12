---
create_time: 2026-08-12
updated_time: 2026-08-12
status: research
---

# A Unified Contract for ACE Artifacts Sub-tabs

**Research question:** after epic `sase-js` made ACE's Artifacts sub-tabs dynamic, what
should SASE standardize so Stitches, Patches, Beads, Files, and future artifact-repo
document tabs feel like one product—and so an artifact-ref provider author can add a
sidecar tab without writing or understanding ACE widget code?

**Scope and repository state.** This report reviews `sase-js`, especially phase
`sase-js.7`, the landed `feat(ace): add dynamic artifact panes` change (`f14b98c08`),
and the follow-up cleanup (`ad11756e6`). Code was read at `sase` `6b139a0d`,
`sase-core` `2519b429`, `sase-research` `f499469`, and the research sidecar
`eacf763`. The epic plan was read at plans sidecar `bac093f`. The report also compares
the design with official extension contracts from Kubernetes, VS Code, Backstage, and
Textual.

## Bottom line

The right abstraction is **not one pane class that knows every artifact type**, and it
is not a slightly larger `ArtifactEntryNavigator` protocol. It is a host-owned
**Artifact Browser** composed of:

1. one shared Textual shell for scope, loading/error/empty states, filtering, list,
   detail, selection, marks, jump history, preview, copy, and refresh;
2. one normalized, immutable browse snapshot and entry model;
3. host-owned adapters for structured builtin resources (Stitches, Beads, Files, and
   eventually Patches where its workflow allows); and
4. a versioned, declarative presentation section in the artifact-ref provider spec for
   document providers.

Third-party providers should continue to return data declarations only. They should
never ship Textual widgets, keybindings, action callbacks, render callbacks, or
per-keystroke resolvers. SASE owns the interaction standard; a provider owns identity,
inventory, typed properties, and modest presentation hints.

Patches should remain a deliberate exception to the list/detail browser. It is a
query-driven workflow board with saved queries, folds, hooks, mentors, and lifecycle
mutations, not merely another artifact collection. It should obey the top-level pane
lifecycle and tab conventions, but forcing it into the same internal widget would make
the common abstraction worse.

## 1. What `sase-js` accomplished

The epic established several good foundations that should be kept.

### Dynamic discovery is real

`artifact_tabs.py` now discovers configured document-provider kinds across enabled
projects, gives them stable tab ids such as `ref:plan` and `ref:research`, and mounts a
pane for each kind. Missing persisted providers fall back to Stitches instead of
crashing. The lookup is cached and document roots are resolved by provider kind and
project scope.

This is the correct discovery boundary: tabs come from the effective configuration of
enabled projects, not merely from installed packages. A provider can be installed but
unused, and an inline provider can be used without an installed package.

### The shared interaction primitives are already useful

Two small contracts already work across non-Patches panes:

- `ArtifactsPaneLifecycle` provides lazy first activation, activation/deactivation,
  and non-blocking refresh hooks.
- `ArtifactEntryNavigator` provides stable entry targets, selection, pending
  selection, jump hints, marks, and conditional footer entries.

App-level code uses those contracts to provide shared `g`/`G`, `Ctrl+F`/`Ctrl+B`,
detail scrolling, adaptive hints, jump-back, and stable marks. Project scope is also
distributed from one app-owned selection to Stitches, Beads, Files, and every document
pane. These are valuable seams and should be absorbed into the new shell rather than
discarded.

### Lazy loading follows the right performance model

Each mounted pane loads only on first activation, does disk work through a thread
worker, coalesces overlapping refreshes, and debounces the detail panel rather than the
highlight. That matches the governing TUI performance rules: never block Textual's
message pump, keep first paint away from archive-scaled work, cache disk reads, and
preserve a sub-16 ms navigation path.

### Files now has the right domain model

Files is no longer a miscellaneous bucket. It has one row per logical file, separates
logical identity from content versions, exposes origin, and reuses the existing
MIME-aware artifact viewer. This is exactly the sort of type-specific domain model that
should sit behind a shared browser adapter rather than be flattened into a generic
Markdown-document model.

## 2. Where the implementation stops short of its stated contract

The dynamic tab strip is generalized. The document UI behind it mostly is not.

### `provider_spec` reaches the pane and then stops

`ArtifactsTabDescriptor` retains the effective provider spec, and `ArtifactsView`
passes it to `ArtifactsDocumentsPane`. The pane stores it as `self.provider_spec`, but
its load request passes only `provider_kind` and `provider_label` to
`load_plans_snapshot`. No property declarations or detail declarations participate in
loading, filtering, list rendering, or detail rendering.

That is the single clearest gap. The public docs say other providers reuse list,
filter, detail, preview, copy, and refresh behavior "from their declared properties and
detail fields." The current ACE path does not do that.

### The “generic” document pane is still Plans internally

The pane is named `ArtifactsDocumentsPane`, but it is composed from
`PlansFilterSessionMixin`, `PlansNavigationMixin`, and `PlansOptionsMixin`; uses
`PlansSnapshot`, `PlanRow`, and `PlanFilterBar`; renders DOM ids such as
`plans-list`, `plans-status`, and `plans-detail`; and is driven by thirteen
`plans_*` modules totaling 3,536 lines.

Its fixed query vocabulary is `kind`, `status`, `tier`, `project`, `since`, and
`until`. Completion still suggests plan values such as `proposal`, `active`,
`archive`, `tale`, `epic`, and `plan`. The filter index has dedicated
`status_labels` and `tier_labels` fields rather than a provider-declared property map.
The detail code contains separate proposal, active-plan, and archived-plan renderers.

For a non-plan provider, the loader suppresses proposals and active bead-linked plans
and treats every document as an archive row. That makes a Research tab appear, but it
does not make Research a first-class implementation of the declared provider contract.

### The shipped Research spec proves the mismatch

`sase-research` declares four properties:

| Property       | Type          | Intended use                         |
| -------------- | ------------- | ------------------------------------ |
| `create_time`  | `datetime`    | recency and detail                   |
| `updated_time` | `datetime`    | recency and detail                   |
| `status`       | `string`      | detail and a natural filter facet    |
| `tags`         | `string_list` | detail and a natural filter facet    |

It declares all four as ordered detail fields. ACE does not interpret this declaration.
`tags:` is not a filter, `updated_time` is not a selectable timestamp, and field order
comes from plan-specific rendering rather than the Research spec.

The Rust v1 schema validates that properties have supported types and sources, that
detail and identity fields refer to declared properties, and that inventory globs are
valid. That is a sound core, but it exposes only `detail.fields`; it has no tab label,
field labels, list columns, title/timestamp selection, facet declaration, list
priority, or default sort. In other words, schema v1 can validate data semantics but
cannot fully describe a consistent browse presentation.

### Cross-cutting behavior is shared by dispatch, not by composition

The widget directory contains roughly:

| Surface    | Modules | Lines |
| ---------- | ------: | ----: |
| Plans      |      13 | 3,536 |
| Beads      |      11 | 3,661 |
| Files      |       8 | 2,652 |
| Stitches   |       7 | 2,052 |

Another 5,141 lines of Artifacts actions, clipboard dispatch, copy targets, and
palette code switch on pane-specific ids and groups. The help modal, command palette,
keymap metadata, availability policy, copy registry, CSS, and tests all know names like
`plans_*`, `files_*`, `artifacts_plans`, `artifacts_other`, and `#plans-detail`.

This is why adding a behavior to “every Artifacts browser pane” is expensive even after
dynamic provider tabs landed. The shared interaction exists, but it is repeatedly
adapted at the app layer instead of being owned once by a browser shell.

### Generic-provider conformance is not tested end to end

At the reviewed revision, the ACE TUI test tree has no test that mounts a
`ref:research` pane or another non-plan provider and asserts its property-driven
filters, detail order, preview, copy targets, empty state, and visual result. Most
dynamic-tab tests inspect descriptors, routing, or whether a provider pane receives
Plans actions. This allowed the declarative contract and the actual presentation to
drift apart while both unit-test layers remained green.

### Ordering and shortcuts currently disagree with the product decision

The owner note on `sase-js` says Files is fixed shortcut `4`, so it should appear
immediately after Beads. Current code and docs instead place provider tabs between
Beads and Files while still painting Files as `4`; provider tabs are assigned dynamic
digits `5` through `9` according to current natural sort order.

The consistent strip is:

```text
1 Stitches | 2 Patches | 3 Beads | 4 Files | Plans | Research | ...
```

Only the four fixed tabs should own number shortcuts. Adding or enabling a provider can
otherwise move another provider's number, which makes a remembered accelerator
unreliable. Provider tabs already have stable command-palette ids and `[`/`]` cycling.
Their accents should likewise be derived deterministically from the provider kind, not
from its current ordinal position in a sorted provider list.

## 3. The user-facing standard

The goal should be **one interaction grammar**, not identical feature sets.

Every browser-style Artifacts pane—Stitches, Beads, Files, and all document
providers—should own the following standard surface:

| Area                    | Standard behavior                                                                 |
| ----------------------- | --------------------------------------------------------------------------------- |
| Header                  | provider label, shared project scope, committed filter summary, counts/diagnostics |
| Left panel              | stable selectable rows, optional non-selectable groups, immediate highlight paint  |
| Right panel             | typed properties followed by preview/detail content                                |
| Open                    | `Enter` opens the canonical full reader/viewer                                      |
| Movement                | `j/k`, `g/G`, `Ctrl+F/B`, adaptive `'` hints, per-pane back/forward history         |
| Detail scrolling        | `Ctrl+D/U`                                                                         |
| Filter                  | `/` or `f`, live in-memory filtering, completion, committed/cancel semantics        |
| Scope                   | `p` changes the shared Artifacts project scope                                      |
| Marks                   | `m` toggles and `u` clears; stable across refresh and sub-tab switches               |
| Copy                    | `%` opens the same palette shell; common representations keep the same accelerators  |
| Refresh                 | `R`, coalesced and off-thread                                                        |
| States                  | consistent loading, empty, filtered-empty, partial, stale, and error presentations   |

The shared copy representations should be capability-based rather than pane-group
based:

- artifact reference;
- Markdown link;
- metadata JSON;
- reference in a new agent prompt;
- title/label;
- body/contents when bounded and available;
- path when one exists.

The palette omits unavailable representations. Type-specific additions remain valid:
full SHA and `repo@sha` for Stitches, source/stored paths for Files, or bead design for
Plans. Their presence should not change how the palette itself behaves.

Similarly, type-specific actions remain first-class:

- Stitches can fetch and change merge visibility.
- Beads can mutate lifecycle, expand epics, and launch work.
- Files can cycle versions and choose an external viewer.
- Plans can approve proposals and jump to their owning bead.

These are **host capabilities attached to a builtin adapter or selected entry**, not
fields a third-party document provider can turn into arbitrary code. The footer and
command palette render them only when the current entry advertises the corresponding
host-known capability.

Patches keeps its own query/workflow layout and mutations. It should share tab ordering,
activation, refresh routing, help vocabulary, and consistent copy/presentation naming
where sensible, but not the list/detail browser implementation.

## 4. Prior art and the useful lesson from each system

### VS Code: providers supply data; the host supplies the view grammar

VS Code's Tree View API requires a data provider to return children and translate an
item into a host `TreeItem`; the resulting content conforms to built-in view styling.
Refresh is an event, commands are separately contributed, and activation occurs when
the user opens the view. That is close to SASE's desired split: provider data plus
host-owned navigation, lifecycle, and presentation—not provider-owned application
chrome. See the official [Tree View API](https://code.visualstudio.com/api/extension-guides/tree-view).

SASE should be stricter than VS Code about provider execution because artifact
inventory also feeds prompt completion and future non-Python frontends. The lesson to
adopt is the small data-provider boundary and lazy activation, not arbitrary extension
code in the hot path.

### Kubernetes: typed custom fields, implicit common fields, host formatting

Kubernetes custom resources can declare additional printer columns while `NAME`
remains an implicit standard column. Columns have declared types and a priority that
controls normal versus wide output; a value that violates its declared type is omitted
rather than destabilizing the whole listing. This is an excellent model for ACE:
stable host columns and behavior, plus a bounded number of typed provider fields. See
the official [CRD additional printer columns documentation](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/#additional-printer-columns).

SASE should use a terminal-width priority for list fields, validate all field references
against the property schema, and degrade one invalid value to missing plus a diagnostic.

### Backstage: typed extension data and lean activation

Backstage uses stable extension ids and typed data references for extension
input/output. Its documentation also warns that extension factories should remain lean
and defer expensive work rather than blocking initialization. Those support stable
provider ids, validated typed outputs, and lazy inventory work. See the official
[frontend extensions architecture](https://backstage.io/docs/frontend-system/architecture/extensions/).

Backstage also permits extensions to output arbitrary React elements. SASE should not
copy that part: it would let plugins bypass the common interface, introduce unbounded
startup and keypress work, and make a native frontend impossible to keep consistent.

### Textual: the widgets already provide the host mechanics

Textual's `OptionList` already owns highlight, first/last/page navigation, stable option
ids, and selected/highlighted messages while accepting Rich renderables. Its
`ContentSwitcher` selects uniquely identified child panes and deliberately provides no
bindings of its own. These APIs favor one SASE browser shell that composes standard
widgets and owns the bindings, while adapters provide immutable render data. See the
official [OptionList](https://textual.textualize.io/widgets/option_list/) and
[ContentSwitcher](https://textual.textualize.io/widgets/content_switcher/) references.

## 5. The internal browser contract

The current navigator and lifecycle protocols are necessary but too low-level. They
standardize app-to-pane control after each pane has independently implemented loading,
filters, rows, detail, preview, and copy. The new contract should move the reusable
behavior one layer down.

### Normalized request and snapshot

The shell should ask an adapter for one immutable snapshot:

```text
ArtifactBrowseRequest
  pane_id, provider_kind
  project_scope
  filter_expression
  page/cursor and bounded_initial_load
  previous_source_revision

ArtifactBrowseSnapshot
  source_revision
  entries[]
  groups[]
  facet_values{}
  complete, next_cursor
  diagnostics[]
  stale
```

`source_revision` should include the provider-spec digest, effective project config,
and the source repository revision or index generation. It is the cache key and the
guard against applying a worker result after scope/config changed.

### Normalized entry

Each selectable row should adapt to a shared entry model:

```text
ArtifactBrowseEntry
  stable_id                 provider-scoped logical identity
  kind, canonical_ref
  project, project_display_name
  title, subtitle
  timestamp
  properties{}              typed values declared by a schema
  body/preview locator      content is loaded lazily, not embedded without a bound
  path/publication target
  capabilities{}            host-known semantic capabilities
  diagnostics[]
```

This should reuse and extend the existing `ArtifactEntry` wire rather than introduce a
second competing notion of artifact identity. Logical identity remains separate from a
captured revision or digest, preserving the Files version model.

### Adapter boundary

An internal Python adapter can be as small as:

```python
class ArtifactBrowseSource(Protocol):
    descriptor: ArtifactBrowseDescriptor

    def load(
        self,
        request: ArtifactBrowseRequest,
        previous: ArtifactBrowseSnapshot | None,
    ) -> ArtifactBrowseSnapshot: ...
```

`load` is synchronous by design because the shell always invokes it on a worker thread;
it must be side-effect free, bounded for the initial page, and cancellation tolerant.
The adapter never receives a Textual widget. Builtin adapters may call domain backends:
VCS log, bead queries, artifact-file indexes, or document inventory. The shell owns
filter-bar sessions, rows, detail debouncing, marks, jumps, empty/error states, and
refresh coalescing.

This is an internal frontend adapter, not a plugin API. Third-party document providers
remain declarative and are served by one host `DocumentArtifactBrowseSource`.

### Core/Python/plugin boundary

The current Rust boundary should remain:

| Layer            | Responsibility                                                                                   |
| ---------------- | ------------------------------------------------------------------------------------------------ |
| `sase-core`      | spec wire/version/validation; typed property coercion; identity; inventory filtering and ordering; normalized browse/query wire |
| Python SASE host | plugin discovery and config merge; builtin adapters; Textual shell; off-thread scheduling; host actions; cache orchestration      |
| provider plugin  | immutable spec and fixtures/docs; no Textual code, callbacks, commands, or filesystem work on use                                 |

Typed frontmatter extraction belongs in core because every frontend must agree whether
`updated_time` is a valid datetime, how a `string_list` is normalized, and which value
becomes stable identity. Textual-specific width allocation, Rich styles, focus, and
keymaps remain in Python.

## 6. Artifact-ref provider contract v2

Schema v1 should not be stretched silently. It is released and hashed into effective
policies. Add a schema version 2 and retain a v1 reader with defined defaults.

The exact spelling can change during planning, but the semantics should look like this:

```yaml
schema_version: 2
provider: research
ref:
  kind: research
  expansion_format: "the {checkout_path} file in the {sidecar_role} artifact repo"

  inventory:
    globs: ["20*/**/*.md"]

  identity:
    property: id              # optional; repo_path remains the safe fallback

  properties:
    title:
      type: string
      source: markdown_frontmatter
      label: Title
      searchable: true
    create_time:
      type: datetime
      source: markdown_frontmatter
      label: Created
    updated_time:
      type: datetime
      source: markdown_frontmatter
      label: Updated
    status:
      type: string
      source: markdown_frontmatter
      label: Status
      facet: true
    tags:
      type: string_list
      source: markdown_frontmatter
      label: Tags
      facet: true

  presentation:
    label: Research
    description: Durable research reports and generated media
    title: title
    timestamp: updated_time
    list:
      fields:
        - {field: status, priority: 0}
        - {field: updated_time, priority: 1}
      default_sort:
        - {field: updated_time, direction: desc}
        - {field: repo_path, direction: asc}
    detail:
      fields: [status, create_time, updated_time, tags]
      body: markdown

  publication:
    link: vcs_permalink
    referenced_by: markdown_table
```

Important constraints:

1. **Common fields remain implicit.** Project, canonical ref, repo-relative path,
   identity, and diagnostics do not need to be redeclared by every provider.
2. **Presentation refers only to declared semantic properties or host common fields.**
   There is no format string capable of running code.
3. **Labels are optional.** Missing labels are humanized by the host.
4. **List fields are hints with priorities.** The host may omit low-priority fields in
   a narrow terminal; detail remains lossless.
5. **Facets are typed.** Boolean/enum/string/string-list fields may be facets. Date and
   datetime fields can opt into `since`/`until` semantics. Free text searches only
   fields marked searchable plus common title/path/body fields.
6. **Identity must be stable across content edits.** Repo-relative path is the default.
   A provider-selected identity property must be present, scalar, and documented as
   immutable; missing or duplicate values fall back with diagnostics rather than
   merging rows incorrectly.
7. **Missing or mistyped values fail per entry.** One bad document must not remove a
   whole provider tab. The invalid field is absent and the snapshot records a bounded
   diagnostic.
8. **No arbitrary actions.** A future declarative action vocabulary should be added
   only when the host has a safe, cross-frontend strategy. Schema v2 should not accept
   command strings or Python entry points.
9. **No provider colors or keybindings.** The host assigns a deterministic accent and
   the standard interaction grammar.
10. **Inventory is side-effect free and bounded.** It may inspect already-resolved
    artifact roots; it does not clone, prompt, network, or acquire unbounded locks.

The builtin Plan provider can declare ordinary document presentation through the same
schema, while SASE layers host-owned Plan capabilities—proposal approval and bead
links—onto entries coming from SASE's own plan adapter. This preserves `use:`/inline
parity without pretending third-party Research documents have proposal workflow.

## 7. Filtering, grouping, and actions should be capabilities, not forks

The filter grammar should have a universal base:

```text
project:  kind:  since:  until:  <free text>
```

Declared facet properties add keys by property name. A Research provider that marks
`status` and `tags` as facets receives `status:` and `tags:` completions automatically.
A Bead adapter can expose its richer `type`, `tier`, `size`, `assignee`, and linked-issue
facets through the same normalized schema. A Files adapter exposes `agent`, `workflow`,
`origin`, and stored kind. Stitches exposes `repo`, `author`, `origin`, `sidecar`, and
merge visibility.

This does not require every domain to share one parser implementation immediately, but
it does require one filter-session UI and one typed facet model. Over time, shared
boolean/negation/date behavior should move behind the Rust query contract so every
frontend agrees.

Grouping is similarly host-owned. An adapter or provider may declare a group key and
order, but groups normalize to non-selectable rows understood by one list model. Epics
with expandable phases and Files with time headings can remain specialized row
structures until the normalized group/tree model supports them without regression.
That argues for incremental adapters, not a single flag day.

Selected-entry actions should be identified by semantic capabilities such as:

```text
open, preview, copy_ref, copy_link, copy_body, open_external,
show_versions, open_owner, mutate_status, launch_work
```

The capability only enables an action implementation already registered by the host.
It never contains executable code. This unifies footer and command-palette availability
and removes the current parallel allowlists in app action checks and command predicates.

## 8. Performance and cache contract

Unifying the UI must not unify every load into one eager cross-project scan.

- Keep `ContentSwitcher` and first-activation laziness. Mounted hidden panes retain
  state but do not load until opened.
- Run every source load and content read off-thread. Pump/timer callbacks only schedule
  pump-free tasks or worker work; they never await the slow body.
- Paint the first bounded page, then extend in the background. Files already does this;
  document providers should adopt it instead of scanning every historical report before
  first paint.
- Cache normalized snapshots by provider kind/spec digest, effective project scope and
  config token, and repository HEAD/index generation.
- Re-read UI state after each asynchronous boundary. Apply a worker result only if its
  generation, pane, scope, and source revision still match.
- Debounce detail content, not list highlights. Detail content should be loaded by a
  content locator and bounded preview cache keyed by revision plus file stat/digest.
- Never parse frontmatter, glob trees, stat paths, or resolve providers during a row
  render or keypress.
- Preserve the performance acceptance target already used by ACE: `SASE_TUI_PERF=1`
  should show navigation p95 below 16 ms on every converted pane.

The adapter model helps here: the shell can enforce worker boundaries and generations
once, rather than depending on every future pane author to rediscover them.

## 9. Options considered

| Option | Benefit | Failure mode | Verdict |
| ------ | ------- | ------------ | ------- |
| Keep separate panes and enlarge `ArtifactEntryNavigator` | Smallest diff | Continues duplicate filters, detail, copy, actions, help, CSS, and tests; no provider-author contract | Insufficient |
| Generalize only the current Plans pane | Makes Research less fake quickly | Leaves four interaction implementations and plan terminology throughout cross-cutting code | Useful migration step, not destination |
| Let providers ship Textual widgets/callbacks | Maximum local flexibility | Inconsistent UX, arbitrary hot-path work, import/failure isolation problems, no native-frontend parity | Reject |
| Force every tab, including Patches, into one generic widget | Superficially maximal reuse | Lowest-common-denominator model damages the Patch workflow and complicates the browser | Reject |
| Shared host browser + builtin adapters + declarative document providers | Common UX, bounded plugin contract, incremental migration, preserves domain-specific power | Requires a normalized view model and careful compatibility aliases | Best fit |

## 10. Compatibility and conformance

The refactor should preserve user configuration and persisted state.

- Keep `current_artifacts_subtab` stable ids. Continue mapping legacy ids.
- Keep existing `plans_*`, `files_*`, `beads_*`, and `stitches_*` keymap names as
  aliases for at least one migration window, while introducing generic browser actions
  for common operations.
- Keep copy-mode accelerators stable. Replace the internal `artifacts_plans` and
  `artifacts_other` group names with capability resolution without changing user keys.
- Read provider spec v1 with deterministic defaults. Providers opt into v2 presentation
  explicitly; no silent digest reinterpretation.
- Keep Plan proposal and bead-link behavior as a builtin augmentation.
- Preserve Files logical identity/version semantics and the MIME viewer.

Provider authors need a conformance harness, not just schema validation. A fixture
helper should verify:

1. spec validation and stable digest;
2. `use:` and inline parity;
3. inventory glob behavior;
4. stable and unique identity across fixture edits;
5. property coercion, missing fields, malformed frontmatter, and duplicate identities;
6. generated facets, sort, list fields, detail order, and copy representations;
7. bounded initial inventory plus pagination/full extension;
8. empty, filtered-empty, partial, stale, and error snapshots; and
9. one generic ACE visual snapshot generated from the fixture provider.

SASE's own suite should add a real `ref:research` integration test so the shipped
provider is the golden external consumer. The plugin repo can consume a public contract
fixture helper without importing any Textual classes.

## Recommended solution

Implement a **shared Artifact Browser shell with adapters**, in four deliberately
separable stages.

1. **Correct and freeze the visible standard first.** Put Files immediately after
   Beads, keep fixed shortcuts `1`–`4`, remove dynamic provider digits, derive provider
   accents stably from kind, and update the contradictory docs/tests. Write a concise
   user-facing interaction contract for every browser pane.

2. **Extract the shell from existing proven behavior.** Introduce
   `ArtifactBrowseRequest`, `ArtifactBrowseSnapshot`, `ArtifactBrowseEntry`, typed
   facets, semantic capabilities, and `ArtifactBrowseSource`. Move lifecycle,
   loading/error/empty states, list/detail composition, filter-session UI, stable
   navigation, marks, jumps, preview, copy-palette assembly, project scope, and refresh
   coalescing into one `ArtifactsBrowserPane`. Convert the current generic document
   pane first, retaining Plan actions as a builtin capability augmentation.

3. **Ship provider spec v2 and a core document-inventory query.** Add labels, facets,
   title/timestamp selection, prioritized list fields, detail fields/body mode, and
   default sort as validated presentation hints. Make core coerce properties and return
   normalized entries with per-entry diagnostics. Update the builtin Plan and
   `sase-research` specs, then add a real Research conformance/visual test. A new
   document provider must require no ACE Python module.

4. **Migrate builtin browse panes incrementally.** Add adapters for Stitches, Files,
   and Beads one at a time, preserving each domain's richer capabilities and measuring
   navigation p95 after every conversion. Consolidate app action availability, command
   predicates, copy groups, CSS ids, help text, and tests only as each adapter lands.
   Leave Patches on its specialized workflow surface while retaining the common
   top-level lifecycle and tab contract.

This solution unifies what users should be able to rely on—navigation, filtering,
scope, detail, marks, copy, refresh, states, and performance—while keeping resource
semantics where they belong. It gives artifact-ref designers a small, testable,
cross-frontend contract and makes “add a sidecar document tab” a spec-only operation,
without sacrificing the specialized workflows that make Beads, Files, Stitches, and
Patches useful.
