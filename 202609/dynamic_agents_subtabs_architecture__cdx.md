# Dynamic Agents sub-tabs: durable semantics and TUI architecture

**Independent research report · 2026-09-27 · researcher cdx**

## Decision in brief

Proceed. Dynamic, launch-assigned sub-tabs are a good addition to the Agents tab, and
the requested design is materially better than a machine-only tab system. The right
model is a two-level presentation hierarchy:

```text
Agents tab
  -> one exclusive view tab per top-level Sase Agent
  -> zero or more tribe panels inside the selected tab
  -> the existing project/date/status/machine grouping tree inside each panel
```

Tabs answer “which working set?”, tribes answer “which team/purpose within that working
set?”, and grouping answers “how should this panel be organized?”. They should remain
separate concepts. In particular, a tab is not a saved query, a tribe, a dispatch
target, or a new mutable execution object.

Add `%tab:<tab_name>` as an exclusive, durable launch classification. Persist only an
explicitly authored tab slug. Absence remains the special implicit `main` value, so all
existing agents are compatible without migration. When the viewer has any configured
remote machine, project an implicit local `main` as a typed machine tab labeled `local`
and an implicit remote `main` as a typed machine tab labeled with that remote's current
configured alias. An explicit `%tab:foo` always remains the named tab `foo`, regardless
of execution machine.

Do not add an `ALL` tab. Replace the current split/merged boolean with a three-state
view-layout enum and cycle it from the grouping picker:

1. **Tabs + tribes** — one active tab, tribe panels split (default).
2. **Tabs, merged tribes** — one active tab, one combined panel.
3. **Merged all** — all tabs and all tribes in one panel; the tab strip disappears.

Lowercase `o` moves forward and uppercase `O` moves backward. Preserve the selected tab
and its cursor while “Merged all” is active so returning to a tabbed state restores the
user's place.

The durable tab contract belongs in `sase_core`, including typed-launch planning, scan
wires, root-membership rules, and fleet publication. Python should parse legacy launch
paths and render the TUI, but it should not invent a second tab-membership policy.

## What the current system implies

The code already has most of the presentation machinery this feature needs, but it also
exposes several traps that a cosmetic-only implementation would miss.

- The Agents list is already a unified local/fleet roster. The legacy `focus`/`fleet`
  state in `src/sase/ace/tui/app.py` and
  `actions/agents/_fleet_projection.py` is forcibly normalized back to `focus`; it is
  compatibility residue, not a pair of views to revive.
- Tribe panels are root-anchored. `models/agent_panels.py` deliberately keeps clans,
  workflows, and agent sessions intact by assigning every descendant to its
  presentation root's effective tribe. Tabs need the same indivisibility rule.
- The hot refresh path assumes a single mounted Agents surface. Incremental updates are
  supported for `STANDARD`, `BY_STATUS`, and `BY_MACHINE`, while full rebuilds are an
  important performance cost. A tab switch must be an in-memory reprojection of the
  already loaded roster, not a new scan, network request, or separately mounted tree.
- The `o` key opens `AgentGroupingModal`. A second lowercase `o` currently toggles the
  `_agent_panels_grouped` boolean between split tribes and one merged panel. Capital
  `O` is intentionally a no-op on Agents today. This is a clean place to introduce the
  requested three-state cycle.
- `PanelTabStrip` already supplies consistent styling, icons, tooltips, compact tiers,
  and cell-correct click ranges. It does not, however, provide bounded overflow; its
  micro tier can still exceed the terminal width with many dynamic tabs.
- Remote rows already carry both a renameable alias and a stable
  `fleet_origin_installation_id`. Machine-tab identity must use the latter and render
  the former. Otherwise a rename loses selection and alias reuse can attach old rows to
  the wrong machine.
- The existing remote machine chip uses `⇄` with cyan (`#5FD7FF`) in the detail header.
  Reusing that glyph and accent gives machine tabs a consistent, terminal-safe visual
  language without an emoji-width or Nerd Font dependency.
- The Python directive parser is not the only parser. Typed launch planning and prompt
  rebuilding are in the linked Rust core. A new directive that is added only to
  `_KNOWN_DIRECTIVES` would be silently lost by typed fan-out or remote dispatch.
- Fleet summaries are strict `deny_unknown_fields` Rust wires. Adding a field to the
  current response without protocol negotiation would break an older controller talking
  to a newer remote. Upgrade skew is part of the feature, not an edge case.

The required prior report,
`research:202609/agent_machine_tabs_and_cluster_semantics/agent_machine_tabs_and_cluster_semantics.md`,
correctly emphasized stable machine identity, a single warm roster, query/tab
separation, overflow, and cross-tab attention. Its main recommendation—permanent
`All`/`here`/remote tabs—should not be carried forward. It solves only the machine case,
uses an `All` tab the present request explicitly rejects, and would make named project
tabs a second, competing navigation system. The broader `%tab` model can subsume the
useful machine behavior with fewer concepts.

## Critique of the proposal

### What is strong

The idea is sound because it adds an exclusive, low-cost working-set axis that the
current system lacks. Tribes are user-managed labels with operational semantics;
queries are authored filters; machine grouping produces a long tree. None is a good
substitute for “keep these agents together while I work.” `%tab:project-x` gives that
intent a concise launch-time spelling and works across machines without changing agent
identity or tribe behavior.

The conditional strip is also correct. Showing a one-item tab bar wastes vertical space
and makes a simple local setup feel more complex. Deriving machine tabs only after
remote configuration preserves today's local-only appearance.

Rejecting an `ALL` tab is the right call. “All” is not another mutually exclusive
membership; it is a different projection. Putting it beside membership tabs makes
counts, keyboard cycling, and bulk-action scope harder to explain. A third layout state
in the existing grouping picker makes the distinction explicit.

### Where the requirements need tightening

The draft leaves five dangerous ambiguities:

1. **Name collision.** A configured machine alias can equal an explicit tab name. The
   implementation must not infer semantic kind from the rendered label.
2. **Structural roots.** A session, clan generation, or workflow tree cannot be split
   across tabs without duplicating or tearing apart its container.
3. **Catalog stability.** If tab existence is derived from the currently filtered
   rows, typing a query makes tabs disappear and reappear. “Has agents” must refer to
   the loaded authoritative roster before the committed query and ordinary display
   filters.
4. **History completeness.** The Agents loader is intentionally bounded. A tab that
   exists only in older completed history may not be known at first paint; the UI must
   not claim the catalog is exhaustive while reconciliation is still incomplete.
5. **Distributed compatibility.** A new remote field cannot simply be inserted into a
   strict fleet v1 response.

These are design requirements, not implementation details.

## Semantic model

### Stored value versus effective view tab

Store one optional field on an agent launch:

```text
agent_tab: Option<TabSlug>
```

- `None` means the directive was omitted and therefore denotes **implicit main**.
- `Some("foo")` means `%tab:foo` was explicitly authored.
- Never persist `main`, `local`, or a machine alias on behalf of the implicit case.
- An explicit `%tab:main` is `Some("main")` and remains a named tab literally labeled
  `main`; it is not eligible for machine relabeling.

That absent-versus-present distinction is enough; a second `tab_explicit` boolean would
duplicate state and create invalid combinations.

The viewer maps each top-level presentation root to a typed key:

```text
NamedTab(slug)                         if agent_tab is present
ImplicitMain                           if agent_tab is absent and machine mode is off
MachineTab(Local)                      if absent, local, and machine mode is on
MachineTab(remote_installation_id)     if absent, remote, and machine mode is on
```

`MachineTab` and `NamedTab` are distinct even when their labels are identical. Thus a
custom `%tab:apollo` can sit beside `⇄ apollo`; the icon is meaningful
disambiguation, and the custom tab still groups explicit agents from every machine.
Do not merge by display string and do not reserve every configured alias as a forbidden
custom name—remote configurations differ by controller and aliases can be renamed.

Machine mode should be stable under connectivity failures. Enable it when the local
configuration contains at least one remote record, including a quarantined/offline
record, or while the roster still contains a projected remote row. Do not key it on a
successful fleet refresh.

### Tab slug contract

Use a deliberately narrow V1 grammar: lowercase ASCII slugs matching
`^[a-z0-9][a-z0-9_.-]{0,63}$`. This is a justified adjustment to the unstated naming
rules. It gives deterministic cross-machine equality, avoids `Foo`/`foo` duplicate tabs,
and fits the existing directive/machine identifier vocabulary. Preserve the slug as
authored; there is no human title field in V1.

Support `%tab:name` as canonical syntax and `%tab(name)` for consistency with other
single-value directives. Reject bare `%tab`, `%tab+`, keyword arguments, empty names,
whitespace, invalid characters, and duplicates—even duplicates with the same value.
Do not add a one-letter alias; `%t` has migration history from the retired tribe
directive and is not worth reopening.

`%tab` is stripped before the model sees the prompt, just like `%dispatch` and `%id`.
It must work when introduced by an xprompt, inside fan-out branches, and in the typed
launch planner. It is not valid on a stand-alone `%proc` unit.

### Structural-root invariants

Tab membership belongs to a **top-level Sase Agent presentation root**, not to an
arbitrary rendered turn. Descendants inherit it:

- agent-session turns, monitor turns, and gate turns inherit the session root;
- workflow children inherit the workflow root;
- every member of one clan generation shares one tab;
- retry members retain the source root's explicit tab;
- a fork is a new agent and follows the fork prompt (normally reconstructed with the
  source `%tab`, but deliberately editable before launch).

For session attachment, an omitted `%tab` inherits the parent. An explicit matching
tab is allowed; an explicit mismatch fails with a clear error. For a clan generation,
the declarer's tab is authoritative; joiners may omit it or match it, and a mismatch is
rejected. A multi-unit workflow or fan-out whose members form one structural root must
similarly agree before dispatch. This prevents a tab filter from splitting one visible
container or forcing duplicate containers.

These rules should be resolved and validated in core launch/session/clan logic, then
persisted to each concrete turn's `agent_meta.json` for robust scans and non-TUI
consumers. The TUI should still root-anchor membership defensively, as it does for
tribes, so partial historical metadata cannot tear a tree apart.

## Machine tabs

The machine behavior is a presentation of implicit main, not authored metadata:

| Agent metadata/origin | No configured remote | Remote configured |
| --- | --- | --- |
| no `%tab`, local | `main` | `⇄ local` |
| no `%tab`, remote `apollo` | `main` (transient/legacy case) | `⇄ apollo` |
| `%tab:project-x`, any origin | `project-x` | `project-x` |
| `%tab:apollo`, any origin | `apollo` | named `apollo`, distinct from `⇄ apollo` |

Use `fleet_origin_installation_id` as the remote tab key and the current configured
alias as its label. A rename updates the label without losing active-tab state. If a
legacy row lacks an installation ID, use an explicitly degraded session-only fallback
key derived from the alias and never persist selection against it.

The local machine key can be the stable in-process `MachineTab(Local)` discriminator;
there is no need to synchronously create/read an installation identity in a render
path. The label is exactly `local`, as requested. A tooltip can include the configured
local machine name.

Reuse `⇄` and `#5FD7FF` from the existing remote-machine chip for every machine tab,
including local. Named tabs have no machine icon. This is more reliable than an emoji
or private-use glyph and visually answers the collision case.

Suggested glossary strand:

> **Machine Tab** (machine tabs) — A machine-derived sub-tab on the Agents tab. When a
> controller has a configured remote machine, an agent with no explicit `%tab`
> appears under `local` if it ran on the controller or under the remote machine's
> configured alias if it ran remotely. Machine-tab identity follows the stable machine
> installation, while the displayed alias may change. A machine tab is a viewing scope,
> not a dispatch target: selecting it never changes where a launch runs. An explicit
> `%tab:<name>` always selects a named tab instead, even when its label matches a
> machine alias. Machine tabs render with the `⇄` machine icon.

Implementation must add this through the audited SASE memory-write workflow; the
research report itself should not edit canonical memory.

## TUI behavior

### Projection pipeline

Maintain one authoritative roster and one mounted Agents surface:

```text
loaded local + fleet roster
  -> build structural presentation roots and a pre-query tab catalog
  -> apply committed Agents query and existing visibility policy
  -> apply active tab scope (unless layout is Merged all)
  -> partition into tribe panels (unless layout merges tribes)
  -> apply project/date/status/machine grouping
  -> render through the existing incremental diff path
```

The tab catalog is built from the loaded, non-dismissed roster before the current query
and `hide_non_run_agents` projection. Consequently a query can empty a tab without
making its navigation target disappear. The empty state should say whether the tab has
no loaded agents or the current query hides them, and offer the existing query editor.

A bounded first load may omit old, completed-only tabs. Reconciliation can add them
later without changing the active tab. Counts should use `N+` while the backing history
is known incomplete. Never perform disk I/O, config discovery, or a fleet call when the
user changes tabs.

Count top-level Sase Agents, not turns or rendered rows. Show attention on inactive tabs
(`!N` or an equivalent badge), sourced from the global roster, so tab scoping does not
hide a question or gate that needs the user. Machine feed errors remain in the existing
header and can also appear in the machine tab's tooltip/accent.

### Ordering, selection, and disappearance

Use deterministic order:

1. implicit `main`, or `⇄ local` when machine mode is enabled;
2. remote machine tabs in configured inventory order (unconfigured stale origins
   follow by alias);
3. named tabs in natural, case-insensitive slug order.

Only populated typed keys appear. Hide the entire strip when the catalog has zero or
one key, exactly preserving current behavior. “Populated” is evaluated before the
current query, not from currently rendered rows.

Keep active selection by typed key across refreshes. On first display prefer the
implicit local/main tab when populated; otherwise select the tab containing the newest
attention/running root, then the first tab. If the active tab truly disappears after
cleanup or machine removal, choose the nearest surviving tab and show a short toast.
Do not jump tabs merely because a new agent arrives.

Keep a small per-tab navigation state keyed by `(tab_key, committed_query)`:
selected root identity, focused tribe panel, and scroll/fold anchor. Fold registries can
remain shared where their keys are already stable, but transient panel focus must not
leak between tabs. Cross-tab jumps should switch the tab, reveal the target, and retain
the previous location for jump-back.

### Strip layout and overflow

Place the sub-tab strip between the Agents filter bar and the fleet-problem header.
This keeps the information hierarchy clear: global view/query controls, then the active
working set, then exceptional machine health, then content.

Use `PanelTabStrip` styling but add a bounded visible window for this dynamic surface.
Compact/micro labels alone do not bound a user-created catalog. Keep the active tab and
as many neighbors as fit; render clickable `‹N`/`N›` overflow affordances and open a
small searchable picker from either affordance. There should be no numeric tab
shortcuts because digits already select agent relations.

Add previous/next tab actions on `[` and `]`. This requires moving Agents card-block
stepping to `(` and `)`, which is safe because the existing Files version actions on
parentheses live on a different main tab. Update default config, fallback bindings,
collision allowances, availability, help/footer text, and visual snapshots together.
This keymap change is a justified requirement addition: mouse-only sub-tabs would be a
regression in a keyboard-first TUI.

On a typed machine tab, suppress the redundant top-level machine banner in
`BY_MACHINE` mode and omit repeated list-row machine chips; retain the machine chip in
the detail header. A named tab can span machines, so `BY_MACHINE` remains fully useful
there.

Selecting a machine tab is navigation only. It must never inject `%dispatch`, mutate a
`machine:` query, or change a launch target. Change the Admin Center Machines “show
agents” action to select the corresponding machine tab when present, falling back to
its current query behavior only when the row is not in the tab catalog.

### Three layout states and `o`/`O`

Replace `_agent_panels_grouped: bool` with an enum, for example:

```text
AgentPanelLayout.SPLIT_TRIBES
AgentPanelLayout.MERGE_TRIBES
AgentPanelLayout.MERGE_ALL
```

The grouping modal's panel-layout row becomes a view-layout row. While the modal is
open, `o` advances and `O` reverses; Enter advances. Render the direction and current
state in one line, for example:

```text
[O] <- Tabs + tribes -> [o]
```

with the adjacent states named in dim text. The Agents info line should always expose a
short state label (`view: tabs+tribes`, `view: tab merged`, or `view: all merged`) so the
third state is not a hidden mode.

Transitions are:

```text
o:  Tabs+tribes -> Tab merged -> All merged -> Tabs+tribes
O:  Tabs+tribes <- Tab merged <- All merged <- Tabs+tribes
```

In `MERGE_ALL`, skip tab filtering, merge tribe panels, and hide the tab strip. Remember
the last active tab and per-tab navigation state. Marks stay global. Any destructive or
bulk action whose scope changes with the view must name `all tabs` in its confirmation;
otherwise a user can mistake a merged-all panel for the previously selected tab.

For migration, a false legacy `_agent_panels_grouped` maps to `SPLIT_TRIBES` and true
maps to `MERGE_TRIBES`. The layout is session-local today and should remain so in V1;
do not add a persistence format merely for this feature.

## Durable data and ownership boundaries

### Rust core

The shared contract should add an optional explicit tab field throughout the existing
agent domains:

- `AgentUnitWire.agent_tab` plus typed planner parsing, validation, diagnostics,
  fingerprints, and `agent_unit_dispatch_prompt` reconstruction;
- agent-session/clan/root consistency and inheritance;
- `AgentMetaWire.agent_tab` in the scan contract;
- owner/fleet projection into `ResolvedAgentSummaryWire.agent_tab`;
- schema fixtures, Python binding round trips, and wire-version getters.

Use the next agent-scan schema and keep the immediately previous schema readable. The
typed launch plan/wire version should also advance: allowing an older admission process
to deserialize a plan while silently dropping `agent_tab` is worse than a clean version
failure.

Fleet needs a rolling-compatible protocol transition. Because v1 summaries deny
unknown fields, do not emit `agent_tab` unconditionally. Introduce fleet protocol v2
(or equivalent explicit requester capability):

- new gateways accept v1 and v2 requests;
- v1 responses omit `agent_tab` exactly;
- v2 responses include the optional field;
- new controllers prefer v2 and fall back to v1, treating a missing field as implicit
  main;
- old controllers continue to request v1 from new gateways and therefore do not see an
  unknown field.

This is more work than an additive serde field, but it is the reliable design for
independently upgraded machines.

### Python launch/runtime

The non-typed parser still needs `PromptDirectives.agent_tab`, known-directive
registration, collection/value validation, prompt inspection/history handling, and
tests. Metadata assembly writes `agent_meta.json["agent_tab"]` only when explicit and
includes it in `preserved_agent_metadata` so dependency waits/re-execs do not erase it.

Add `agent_tab` to the Python scan mirror, wire conversion, `Agent` state, local
enrichment, dismissed bundles, retry/revive reconstruction, and remote row conversion.
Missing fields always mean implicit main. Avoid a separate mutable tab assignment store
in V1; it would create precedence questions with launch metadata and machine derivation.

### TUI-only model

Keep a small descriptor separate from `Agent` storage:

```text
AgentViewTab {
  key: Named(slug) | Machine(Local | installation_id) | ImplicitMain,
  label,
  icon,
  count,
  attention_count,
  completeness,
  health
}
```

The descriptor and root-to-tab projection are pure and testable. If another frontend
needs identical catalog/order/identity behavior, move that projection into core rather
than copying it. The Textual widget, overflow window, focus restoration, and rendering
remain Python presentation logic.

## Suggested delivery sequence

1. **Core contract and directive.** Define the slug type and root invariants; implement
   typed planning/reconstruction, scan metadata, session/clan inheritance, schema
   versions, and bindings. Add `%tab` to editor/LSP directive metadata.
2. **Python launch and local history.** Parse `%tab`, persist `agent_tab`, preserve it
   through waits/retries/revive, consume the new scan binding, and ratchet the
   `sase-core-revision.txt` pin after the core change lands.
3. **Fleet v2 negotiation.** Publish/consume explicit tab metadata without breaking v1
   controller/remote pairs; test both upgrade directions.
4. **Pure tab projection.** Implement typed keys, machine-mode derivation, root
   anchoring, deterministic catalog/order, counts, completeness, attention, and
   selection fallback without mounting UI.
5. **TUI strip and navigation.** Add the one-line strip, overflow/picker, click and
   bracket actions, per-tab cursor state, cross-tab reveals, machine icon, and empty
   states. Keep one roster and one widget tree.
6. **Three-state layout.** Replace the boolean, add `o`/`O` cycling, merged-all action
   scoping, and visible state text.
7. **Memory/docs/migration.** Add the Machine Tab glossary strand through
   `/sase_memory_write`; update xprompt docs, directive tables, generated skill source
   if relevant, help, keymaps, and the Admin Center machine jump behavior.

This sequence deliberately lands durable semantics before presentation. It also makes
local named tabs useful even if the fleet protocol work needs a separate patch.

## Validation matrix

At minimum, cover:

- `%tab` absent, valid, invalid, repeated, in literal zones, from xprompts, in fan-out,
  and combined with `%dispatch`;
- typed-plan serialization, digest/fingerprint changes, dispatch-prompt reconstruction,
  and proc rejection;
- wait/re-exec preservation, session attachment match/mismatch, monitor/gate
  inheritance, retry, fork, revive, dismissal bundles, and clan-generation agreement;
- old scan records, new scan records, old/new launch plans, and both fleet upgrade
  directions;
- no remotes, configured-but-offline remotes, remote rename, alias reuse, missing
  installation ID, explicit/machine label collision, and explicit cross-machine tabs;
- zero, one, two, and many populated tabs; strip hiding; active-tab removal; incoming
  background agents; bounded history gaining a tab; query-empty versus truly empty;
- attention on inactive tabs, stale feed diagnostics, local/remote counts, and tabs
  containing only completed agents;
- all grouping modes in all three layout states, especially `BY_MACHINE` inside a
  machine tab and named tabs spanning machines;
- `o` and `O` wraparound, modal click/Enter behavior, restored active tab after merged
  all, marks and cleanup confirmation scopes;
- bracket navigation, moved card-block keys, Artifacts Files parentheses, custom
  keymaps, collision validation, help/footer text, and narrow-terminal overflow;
- cross-tab node finder, notification jumps, jump-back, Admin Center “show agents”, and
  selection restoration after refresh;
- visual snapshots for local-only, mixed named/machine, collision, attention, overflow,
  and all-merged views.

Performance gates should assert that tab switching performs no filesystem or network
I/O, does not mount inactive agent trees, and does not trigger the full loader. Measure
tab-switch paint on a large warm roster and retain the existing `j`/`k` p95 target
below 16 ms. Quiet auto-refresh should not rebuild inactive panels or increase fleet
and artifact file opens.

## Explicit adjustments to the requested requirements

I recommend the following additions/clarifications:

1. Tabs are exclusive scopes of top-level Sase Agent roots; descendants cannot choose
   a conflicting tab.
2. Explicit and machine-derived tabs have typed identities, so identical labels remain
   distinct and visually disambiguated by `⇄`.
3. V1 tab names are lowercase ASCII slugs up to 64 characters; there is no `%t` alias.
4. `%tab(name)` is accepted alongside canonical `%tab:name`; `%tab` is invalid for
   stand-alone proc units.
5. The catalog is based on the pre-query loaded roster, with honest incomplete-history
   counts, rather than the currently rendered rows.
6. `[`/`]` cycle Agents tabs and Agents card-block navigation moves to `(`/`)`.
7. The machine icon is the existing terminal-safe `⇄` glyph in the existing machine
   cyan.
8. Machine-tab selection never changes dispatch or query text.
9. No post-launch “move tab” mutation is added in V1. Add it later only with explicit
   root/clan/session atomicity and audit semantics.
10. Fleet publication uses a negotiated protocol transition; it is not an unsafe
    additive change to strict v1 JSON.

## Recommended solution

Implement `%tab` as durable, optional **explicit tab metadata** owned by `sase_core`,
with absence representing implicit main. Build a typed, root-anchored tab projection in
the TUI: implicit local/remote agents become `⇄ local` and `⇄ <alias>` only when machine
mode is active, while explicit named tabs remain identical across machines. Render the
strip only for two or more populated typed tabs, keep it independent of the committed
query, and switch tabs entirely in memory over the unified roster.

Use the existing grouping picker to expose three honest view layouts, cycling forward
with `o` and backward with `O`; the third layout merges every tab and tribe without
inventing an `ALL` membership tab. Add bounded overflow, bracket navigation, global
attention badges, and explicit bulk-action scope. Carry the new metadata through scan,
retry/session/clan, fleet v2, and old-record compatibility before relying on it in the
UI.

This approach is intuitive because each control has one job, reliable because
membership is durable and structural roots never split, and visually coherent because
machine derivation is communicated by an existing icon rather than by overloaded names.
It is also ambitious in the useful sense: named tabs become a general cross-machine
working-set primitive, while the implementation avoids turning tabs into a second
query language or a new execution subsystem.

## Code and context reviewed

- Prior audited research artifact:
  `research:202609/agent_machine_tabs_and_cluster_semantics/agent_machine_tabs_and_cluster_semantics.md`
- Python directive and runtime paths: `src/sase/xprompt/_directive_*`,
  `src/sase/axe/run_agent_directives.py`,
  `src/sase/axe/run_agent_directive_metadata.py`
- Agents TUI model/rendering: `src/sase/ace/tui/app.py`, `_app_layout.py`,
  `actions/agents/{_fleet_projection,_fleet_refresh,_display,_grouping,_panel_navigation}.py`,
  `models/{agent_panels,_agent_state_fleet}.py`,
  `modals/agent_grouping_modal.py`, and `widgets/panel_tab_strip.py`
- Keymap/help/config surfaces: `src/sase/ace/tui/bindings.py`,
  `src/sase/ace/tui/keymaps/`, `src/sase/default_config.yml`, and Agents help tests
- Machine inventory/navigation: `src/sase/dispatch/`,
  `src/sase/ace/tui/modals/machines_pane*.py`
- Linked `sase-core`: typed launch wires/planner/admission, agent scan wires,
  editor directive metadata, fleet owner facts/resolution/federation, and gateway
  fleet-read contracts.
