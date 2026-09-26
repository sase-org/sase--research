# Agent cluster tabs: design research and recommended architecture

**Researcher:** cdx  
**Date:** 2026-09-26  
**Primary SASE revision inspected:** `acbd5999adb3ea16f2b1f27187a5ddc046067277`  
**sase-core revision inspected:** `e44af7d40a6c24b447b258cac831d9ede4262980`

## Executive conclusion

Adding sub-tabs to the Agents tab is a good idea. Machine tabs in particular solve a
real scaling problem better than the existing `BY_MACHINE` tree grouping: they reduce
the amount of navigation chrome visible at once, give remote-host failures a natural
home, and let arrivals on other machines become visible without displacing the user's
current selection.

I would **not**, however, make clans, tribes, and tabs interchangeable persisted
objects. They all group nodes, but that is the end of their common contract:

- a clan is a generation-scoped parallel cohort with aggregate completion, cleanup,
  summary, retry, wait, and fork behavior;
- a tribe is a mutable organizational label that is also a temporal “next completed
  entity” wait/fork target;
- a machine tab is a derived presentation partition and must have no launch or wait
  semantics;
- an agent session is deliberately not in this family: it is one sase agent whose
  turns form a strict sequence.

The right unification is therefore a **typed agent-cluster projection**, not a single
untyped cluster entity or store. A shared cluster interface can describe identity,
membership, counts, presentation, and capabilities while each kind retains its own
invariants. The first implementation should add an `All` tab plus exclusive `here` and
remote-machine tabs, backed by stable machine identities and rendered through one
reused Agents surface. It should not duplicate the whole Agents widget tree in a
`ContentSwitcher`.

I recommend separating the work into two changes:

1. ship machine cluster tabs and the shared read-model vocabulary, with no clan storage
   migration;
2. pursue a later clan simplification that removes naming/hood and unique-declarer
   accidents while retaining generation and aggregate semantics.

That split delivers the scalability benefit early and avoids coupling a tractable TUI
feature to a high-risk launch/wait migration.

## What the codebase already does

The current implementation has more grouping structure than the proposal initially
suggests. There are four distinct layers:

| Layer | Current mechanism | Meaning |
| --- | --- | --- |
| Roster partition | Tribe side panels | Mutable organizational grouping, one vertically stacked `AgentList` per effective tribe |
| Tree grouping | `GroupingMode` | Project/Patch, date, status, or machine/status banners inside each tribe panel |
| Structural nodes | Clan, session, workflow | Semantic parent/child structure with folding and aggregate behavior |
| Query | Agents live query | Global selection of loaded records, including `machine`, `tribe`, `clan`, `session`, and `project` fields |

Important implementation facts:

- `agent_panels.py` derives a stable panel key from the outer presentation anchor, so a
  structural subtree is not split across tribe panels. Panel focus is keyed by identity
  rather than list index, and panel order is deterministic.
- Tribe panels are session-sticky under a committed query and retire only after
  authoritative removal. This is careful protection against bounded and incomplete
  history loads.
- `GroupingMode.BY_MACHINE` already places `here` first, then remote aliases, with
  status buckets below each machine. It is a useful source of ordering and test
  semantics, but it remains an in-list grouping and does not reduce the visible panel
  stack.
- The live query row already exposes exact `machine`, `tribe`, `clan`, and `session`
  fields. Exact machine predicates are eligible for index pushdown.
- The Artifacts tab already has a good reusable visual primitive:
  `PanelTabStrip`, including click targets, responsive full/compact/micro labels, and
  active styling. Its present micro mode does not solve unbounded tab overflow, though.
- Agent list refresh has an optimized incremental path, stable widget reuse, selection
  memory, and strict event-loop performance rules. A tab implementation must preserve
  these rather than introducing a second loading path.
- Fleet rows already carry logical owner data separately from viewer-facing aliases.
  That distinction should become the stable tab key versus display label.

The existing left column also demonstrates why tabs are timely. Multiple tribe panels
are vertically stacked and dynamically height-balanced. That works well for a few
tribes, but machine banners inside every tribe panel multiply navigation depth as both
machines and tribes grow.

## Critique of the proposal

### What is strong

The sub-tab idea is directionally right.

1. **It matches the user's spatial model.** A remote machine is a durable place, so a
   tab named `apollo` is easier to locate repeatedly than an `apollo` banner somewhere
   inside one or more tribe panels.
2. **It bounds visual complexity.** The active machine can show its tribes and inner
   grouping without every other machine consuming rows.
3. **It creates a natural diagnostic surface.** Feed-invalid, stale-cache, offline, and
   capacity information can appear on the owning machine's tab.
4. **Square-bracket navigation is consistent with existing SASE sub-tab navigation.**
   Moving card-block history to parentheses also preserves the left/older and
   right/newer mnemonic.
5. **“Agent cluster” is useful vocabulary.** “Group” is already overloaded by tree
   grouping and saved/dismissed agent groups. “Cluster” can name the shared set-like
   projection without claiming that all cluster kinds behave identically.

### Where I would change the requirements

#### Adjustment 1: do not promise literal clan/tribe/tab interchangeability

The premise that clans and tribes are “just” groups is not accurate today.

A clan's name is reserved, its members are hood-qualified, its metadata is scoped by a
generation, `%wait:<clan>` waits for every member of the newest generation, its fork
result is an aggregate summary, and kill/dismiss can cascade over the generation. A
tribe is also more than display metadata: `%wait:@review` selects the next successful
standalone agent or complete clan generation launched after the waiter, and `#fork`
uses that selected entity. Tabs must not acquire either behavior accidentally.

“Move a node from a clan to a tab” is also ill-defined. Machine membership is derived
from execution ownership, while clan membership affects the historical aggregate that
waits and forks observe. Retroactively moving a running or completed agent between
clans would rewrite history.

I would replace the requirement with:

> Clans, tribes, and agent view tabs conform to a common typed agent-cluster projection
> for membership, navigation, counts, styling, and capability discovery. Operations
> such as reassignment, wait, fork, cleanup, and conversion are available only when the
> cluster kind explicitly supports them.

This still enables an intuitive common UI. A cluster chooser can show the same chrome
and commands while disabling or relabeling invalid operations. “Move to tribe” is a
real mutation; “show in machine tab” is navigation; “create clan from selection” is a
new launch/cohort action, not reassignment.

#### Adjustment 2: make v1 tabs an exclusive machine partition plus `All`

Arbitrary saved-query tabs are attractive, but they immediately create overlapping
membership, double-counted unread state, ambiguous bulk scopes, and difficult empty-tab
lifecycle. Machine ownership is nearly exclusive and already present in the roster, so
it is the safest first axis.

V1 should contain:

- `All` — the union/current behavior;
- `here` — local presentation roots;
- one tab per enrolled remote machine, even if its current roster is empty or its feed
  is unavailable.

The strip can stay hidden when there is only one effective machine, avoiding wasted
vertical space for local-only users. Saved-query and tribe-as-tab providers can be
added later against the same descriptor interface after overlap semantics are designed.

#### Adjustment 3: preserve current global query semantics

Selecting a tab should be a presentation projection **after** the submitted Agents
query, not a query rewrite. Otherwise switching to `apollo` would silently change
unread candidates, prospective-clan lookup, and other consumers that intentionally read
the global committed query.

The pipeline should be:

```text
loaded/reconciled roster
  -> global Agents query
  -> structural presentation roots
  -> active cluster-tab projection
  -> tribe panels
  -> inner grouping mode
  -> visible AgentList rows
```

The Machines pane's current “show agents” action should switch to the matching machine
tab when tabs are enabled instead of injecting `machine:<alias>` into the global filter.
The explicit filter remains supported for scripting, saved history, and compound
queries.

#### Adjustment 4: keep `BY_MACHINE` for compatibility at first

Machine tabs make the old tree grouping less important, but removing it immediately
would break persisted grouping preference and the useful `All`-tab overview. Keep it
for at least one compatibility cycle and label it clearly as **Machine tree** in the
grouping picker. On a single-machine tab it may render one redundant machine banner;
that is preferable to a hidden automatic grouping-mode change in the first release.
Usage and feedback can determine whether it should later become an `All`-only view or
be retired.

## Proposed glossary definition

Add the following term through the memory workflow:

> **Agent Cluster** — A typed grouping of top-level agent presentation roots used for
> organization, coordination, or navigation. Clans, tribes, and agent view tabs are
> agent-cluster kinds. The shared cluster contract covers stable identity, membership
> projection, counts, presentation, and declared capabilities; it does not imply shared
> wait, fork, lifecycle, mutability, or persistence semantics. An agent session is not
> an agent cluster: it is one sase agent whose sase turns form a strict sequential
> chain.

This definition is intentionally narrow. It supports shared code without erasing the
reason the kinds exist.

## Recommended conceptual model

### Typed cluster descriptor

Use a shared value object/read model, preferably owned by `sase_core` because fleet,
CLI, TUI, editor, and future web surfaces need membership to agree:

```text
AgentClusterDescriptor
  key                 stable typed identity
  kind                clan | tribe | machine_view | all_view
  label               viewer-facing name
  membership_mode     explicit | inherited | derived
  cardinality         exclusive | overlapping
  capabilities        navigate, reassign, wait_all, wait_next, fork,
                      aggregate_status, cascade_cleanup, describe
  health              optional presentation status/diagnostics
  sort_key
```

The capability set is more important than a class hierarchy. Consumers ask whether a
cluster supports `wait_all` or `reassign`; they do not switch on a label and guess.

For the first phase, only `machine_view` and `all_view` need to flow through the new tab
catalog. Existing clan and tribe stores can expose adapters to the descriptor protocol
where shared UI needs them. Do not migrate those stores merely to make the type graph
look uniform.

### Stable machine membership

Tab keys should use the logical owner machine identity from the fleet contract, not the
viewer-local alias. The alias is a label and may be renamed. Conceptually:

```text
cluster key: machine:<owner-machine-identity>
label:       apollo
local key:   machine:local
union key:   all
```

Every workflow/session descendant inherits its outer presentation root's cluster key,
matching the existing tribe-panel rule. A clan should also remain structurally atomic.
Cross-machine clans are currently excluded by remote-launch constraints; if federation
later permits them, projection must not silently split one clan container. Put such a
root in a visible `mixed` cluster with a diagnostic until cross-host clan presentation
is explicitly designed.

### Mutation rules

The common cluster UI should communicate these different verbs:

| Kind | Valid membership action |
| --- | --- |
| Tribe | Assign/move an agent or whole clan generation |
| Machine tab | Navigate; launch new work on that machine; membership is derived |
| Clan | Create/join during launch; no retroactive move of historical members |
| All | None; synthetic union |

This is more intuitive than exposing a generic “move” command that sometimes rewrites
metadata, sometimes dispatches work, and sometimes cannot succeed.

## TUI design

### Placement and appearance

Place a one-row cluster tab strip below the Agents info row and above the filter bar.
Hide it when only one effective machine exists. A representative wide rendering:

```text
  ALL 42  │  ⌂ here 12  │  ◈ APOLLO 24 !2  │  ◈ mac 6
```

- Active label: uppercase/bold in the tab accent, following the Artifacts convention.
- Inactive tabs: muted label, semantic attention dot/count only when useful.
- `here`: stable home icon and local accent.
- Remote: deterministic palette or configured machine accent; do not reuse tribe color
  to imply tribe identity.
- Feed errors/staleness: compact `!`/`~` marker with the full reason in the tooltip and
  active-tab header.
- Counts: sase-agent counts, not raw rows, matching the Agents headline projection.
  When the source is bounded/incomplete, show `N+` rather than asserting a total.
- With an active filter, render `matched/known` when space allows (for example `3/24`)
  and use an explicit “No apollo agents match the filter” empty state.

Reuse `PanelTabStrip` styling and click behavior, but add a true overflow window. Its
current full/compact/micro ladder can still overflow if there are many icon-only tabs.
When the strip cannot fit every micro tab, center a window on the active tab and show
leading/trailing hidden counts such as `‹3` and `4›`. `[`/`]` must still cycle through
every hidden tab.

### State and navigation

- `[` selects the previous cluster tab; `]` selects the next; both wrap.
- Mouse click selects a visible tab.
- Store lightweight state per stable cluster key: selected node identity, focused tribe
  panel, grouping banner, scroll anchor, and detail/deck target.
- On return, restore by stable identity, never by row index. If the node no longer
  exists, select the nearest surviving navigation stop, then the first actionable row.
- An arriving agent in an inactive tab updates its count/attention marker but never
  steals the current tab or cursor.
- A jump, notification, neighbor link, or node finder result may cross tabs. It should
  atomically select the target tab, reveal the target through folds, and add the prior
  `(tab, panel, node, detail)` location to jump-back history.
- Removing or renaming the active machine falls back to `All`, then `here`, with one
  concise toast. A display rename should normally retain the tab because the key is not
  the alias.
- Marks remain global and visible when returning to another tab. Mark-based operations
  state their cross-tab count. An operation scoped to the current tab must say
  “current tab” explicitly in its confirmation; tabs must not silently narrow a
  formerly global destructive action.

### Rendering architecture

Do not create one complete Agents pane per tab. That would duplicate `AgentList`
widgets, tribe panels, render caches, sticky-panel bookkeeping, detail state, and refresh
work—the opposite of the scaling goal.

Instead, keep one active Agents surface:

1. retain the authoritative `_agents` roster and existing reload/reconcile path;
2. derive a cached `AgentClusterCatalog` off the event loop when the roster/fleet
   inventory changes;
3. select an active cluster slice by stable root identity;
4. feed that slice into the existing tribe-panel and grouping-tree projection;
5. reuse/remount only the active slice's panel widgets, with tab key included in widget
   and fold-state scope where necessary.

Tab switching is then an in-memory projection change, not disk I/O, network I/O, JSON
parsing, or a full history refresh. Highlight paint should be immediate; detail repaint
should continue through the existing 150 ms debouncer.

The current session-sticky tribe-panel store must be scoped by `(cluster_tab_key,
committed_query)` rather than only the query. Otherwise visiting `@review` on `apollo`
could keep an empty `@review` panel alive on `here`. Cache only identities and selection
state for inactive tabs, not mounted widgets.

## Keymap migration

The requested defaults are sensible:

| Action | Old | New |
| --- | --- | --- |
| Previous card block | `[` | `(` |
| Next card block | `]` | `)` |
| Previous agent cluster tab | — | `[` |
| Next agent cluster tab | — | `]` |

Implementation must update all keymap surfaces, not only the static `BINDINGS`:

- `src/sase/default_config.yml` (explicitly required by project instructions);
- app keymap dataclasses, metadata, registry collision allowlist, fallback bindings, and
  action availability;
- footer/help/quickstart/command palette text;
- config documentation and key display tests;
- card-block rail hints and visual snapshots.

Parentheses are already used by Files version navigation on the Artifacts tab, so add a
tab-disjoint collision allowance for card blocks versus Files versions. Likewise,
square brackets remain Artifacts sub-tab navigation, so the new Agents-tab actions are
tab-disjoint from that pair.

Existing user overrides require an explicit compatibility rule. A user who copied the
old card-block `[`/`]` bindings would otherwise have two active Agents actions on the
same keys. Detect the exact legacy pair during keymap loading, ignore it in favor of the
new card-block defaults, and emit a targeted warning that names `(`/`)`. Nonstandard
custom collisions should continue through normal duplicate-binding validation. Do not
silently guess at arbitrary custom mappings or mutate the user's file.

## Clan simplification: what to remove and what to keep

The instinct that clan requirements can be simplified is correct, but only some are
accidental.

### Good candidates to remove in a separate migration

1. **Name/hood coupling.** Membership should not require every member name to begin
   `<clan>.`, nor should the clan's display name permanently reserve the ordinary agent
   name. Give the cohort a typed identity namespace independent of agent names. Keep
   qualified-name derivation as convenient backward-compatible shorthand.
2. **The unique declaring member.** The create-only `%clan` declarer exists partly to
   own tribe and summary metadata. Launch planning should atomically ensure a clan
   generation record first, then attach members. Conflicting metadata should produce a
   deterministic planning error rather than depend on which member declared it.
3. **Metadata copied through member artifacts as authority.** The durable generation
   record should be authoritative. Member metadata remains compatibility evidence, not
   a distributed last-writer election.
4. **Directive mutual exclusion caused only by syntax.** Once cluster identity is
   independent, an agent can have a session identity and an organizational tribe while
   participating as a clan member; validation should prohibit only semantically
   contradictory combinations.

### Semantics that must remain

1. **Generation identity.** Reusing a clan name must not make an old completed member
   satisfy or block a new wait.
2. **Aggregate completion and explicit wait/fork behavior.** These are the core value of
   a parallel cohort.
3. **Atomic structural presentation and cascade confirmation.** A clan is not merely a
   colored label when killing or dismissing it can affect several live agents.
4. **Durable summary/description and tribe assignment for the generation.** These
   survive artifact deletion and are already valuable in the clan and tribe documents.
5. **No retroactive membership edits.** Historical wait/fork outcomes must remain
   reproducible.

This refactor belongs in `sase_core`, with wire/binding changes and a core revision
ratchet. The Textual layer should consume the normalized result rather than reproduce
cohort logic.

## Implementation outline

### Phase 1: cluster read model and machine tabs

1. Add the Agent Cluster glossary strand and a short decision record defining typed
   capabilities and excluding sessions.
2. In `sase_core`, add the stable cluster descriptor/catalog wire and machine-root
   projection. Reuse fleet logical owner identity and return diagnostics for inconsistent
   structural roots.
3. Bind the catalog into Python and ratchet `sase-core-revision.txt`.
4. Add a presentation-only `AgentClusterTabs` state model to the TUI. Keep `_agents`
   authoritative and cache only descriptors/membership/selection state.
5. Add the responsive strip to `_app_layout.py`, extend `PanelTabStrip` with overflow
   windowing, and route click plus bracket actions.
6. Scope tribe panel, selection, navigation-stop, fold, and sticky occupancy caches by
   active cluster key. Route cross-tab reveals through the existing reveal transaction.
7. Add `ace.agent_clusters.tab_axis: machine|none` and `include_all: bool`. Default to
   machine tabs, but hide the strip when no remote machine exists; this makes the feature
   effectively zero-chrome on local-only installations.
8. Keep existing `BY_MACHINE` grouping and persisted grouping mode unchanged.

### Phase 2: hardening and richer cluster UX

1. Make Machines “show agents” select a tab.
2. Add feed health, bounded-count notation, inactive-tab attention, and empty/error
   documents.
3. Add cluster capability adapters for clans and tribes so shared chooser/header code
   stops probing ad hoc fields.
4. Decide whether saved-query tabs are warranted. If added, specify overlap and bulk
   scope before implementation.

### Phase 3: clan identity cleanup

Treat this as its own design/epic. Introduce typed cohort identities and an atomic
generation record, preserve old directives as adapters, migrate wait/fork/cleanup one
surface at a time, and only then relax hood/name requirements. Do not make the tab
feature wait for this work.

## Reliability and test plan

### Pure model/core tests

- `All`, `here`, and remote ordering; aliases do not define identity.
- Empty enrolled remote and remote feed error still produce a tab.
- Session/workflow descendants inherit their presentation root's tab.
- Clan root remains atomic; inconsistent multi-machine membership yields `mixed` plus a
  diagnostic.
- Machine rename preserves key and state.
- Counts use sase-agent projection and report incompleteness.
- Global query is applied before tab projection and is not rewritten by tab selection.

### TUI state tests

- Bracket cycling, wrapping, click selection, hidden overflow tabs, and one-tab no-op.
- Per-tab node/panel/banner/scroll restoration by stable identity.
- Inactive arrival updates counts without focus theft.
- Active-tab removal fallback and query-change reconciliation.
- Cross-tab node finder, notification, neighbor, artifact link, and jump-back behavior.
- Marks and confirmations state whether scope crosses tabs.
- Tribe panel sticky state and fold registries do not leak between machine tabs.
- No programmatic `OptionList` highlight echo; no stale detail applied after rapid tab
  switching.

### Keymap tests

- Bundled defaults use parentheses for card blocks and brackets for agent tabs.
- Exact legacy user overrides receive the targeted migration warning.
- Card block/File-version and Agent-tab/Artifact-tab pairs are accepted as disjoint;
  genuine same-surface collisions are rejected.
- Help, footer, quickstart, command palette, configuration docs, and keycap rendering
  agree.

### Visual and performance tests

- PNG snapshots at narrow, standard, and wide sizes, including overflow, filter-empty,
  stale/error, unread, and many-machine states.
- Preserve the existing `j`/`k` p95 target below 16 ms.
- Set a tab-switch target (recommended p95 below 50 ms with cached rows) and assert that
  it performs no filesystem or network I/O.
- Quiet auto-refresh must not reload inactive tab surfaces or increase fleet/file-open
  counts. A changed remote roster updates only catalog/count state plus the active slice
  when relevant.

## Alternatives considered

### Keep only `BY_MACHINE`

This is the smallest change and already works, but it does not address the scaling
motivation. Every machine remains in the same navigable tree and is repeated inside
tribe panels. It is a useful fallback, not the desired UX.

### Turn tribes into tabs

This would reduce the vertical panel stack but does not solve the machine-oriented use
case and would remove the useful simultaneous tribe overview. It also makes tribe
wait/fork semantics look as if they belong to every tab kind.

### Generic saved-query tabs immediately

This is maximally flexible but premature. Overlapping tabs require policies for unread
counts, marks, bulk operations, arrival badges, default placement, and duplicate nodes.
Build the exclusive machine provider first, then generalize from measured demand.

### One `ContentSwitcher` pane per machine

This is visually straightforward but architecturally wrong for scale: it multiplies
widgets, caches, sticky panels, detail state, and refresh work. One projected surface
with per-tab lightweight state is both faster and easier to keep consistent.

## Evidence map

The conclusions above are grounded in these inspected sources:

- `src/sase/ace/tui/models/agent_panels.py` — tribe panel keys, structural-root
  inheritance, deterministic focus/order.
- `src/sase/ace/tui/actions/agents/_display_panel_collection.py` — sticky panel
  lifecycle and authoritative-removal rules.
- `src/sase/ace/tui/models/agent_groups/` — `BY_MACHINE`, status subgroups, fold keys,
  ordering, and incremental-patch signatures.
- `src/sase/ace/tui/models/agent_live_query.py` and
  `agent_live_query_pushdown.py` — machine/tribe/clan/session query fields and exact
  machine pushdown.
- `src/sase/ace/tui/widgets/panel_tab_strip.py` and
  `widgets/artifacts/view.py` — established sub-tab visual/navigation pattern.
- `src/sase/ace/tui/_app_layout.py` and `styles.tcss` — current Agents surface and
  stacked tribe-panel geometry.
- `docs/agent_sessions.md` — clan generation, records, summaries, waits, cleanup, tribe
  assignment, and tribe next-entity wait/fork semantics.
- `docs/remote_dispatch.md` — current fleet presentation, remote diagnostics, and
  `BY_MACHINE` workflow.
- `sase-core/crates/sase_core/src/agent_clan_record.rs`,
  `agent_clan_tribe.rs`, `agent_tribe.rs`, and `fleet_contract/` — durable clan
  attributes, deterministic resolution, tribe identity rules, and logical/display
  machine identities.

A lexical blast-radius check reinforces the need to separate the efforts: `agent_clan`
or `AgentClan` appears in 144 primary source files, 206 primary test files, and 45
sase-core crate files. A full unification migration is not a prerequisite-sized change
for a TUI tab feature.

## Recommended solution

Implement **typed agent-cluster tabs** as a presentation layer over the existing roster:

1. Define Agent Cluster as a capability-bearing umbrella term, explicitly excluding
   agent sessions and explicitly preserving kind-specific wait/fork/lifecycle semantics.
2. Ship an exclusive machine tab provider with `All`, `here`, and enrolled remote tabs.
   Use stable logical machine identity as the key and alias only as the label.
3. Render only the active tab through the existing tribe-panel and grouping pipeline;
   keep one widget surface and lightweight per-tab selection state.
4. Apply the global Agents query before tab projection, preserve `BY_MACHINE` during a
   compatibility period, and make cross-tab jumps transactional.
5. Move card blocks from `[`/`]` to `(`/`)`, add `[`/`]` agent-tab actions, and include
   a targeted compatibility warning for copied legacy overrides.
6. Defer generic saved-query tabs and clan storage migration. In a later clan-focused
   epic, remove hood/name reservation and unique-declarer coupling, but retain generation,
   aggregate completion, durable metadata, and historical immutability.

This approach is intuitive because each visible tab answers “where is this work
running?”, reliable because it reuses the authoritative roster and current incremental
paths, and beautiful because it adds one compact responsive navigation rail without
duplicating or flattening the rich tribe/clan/session structure underneath it.
