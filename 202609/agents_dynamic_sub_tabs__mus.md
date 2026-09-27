# Dynamic Sub-Tabs for the Agents Tab

**Research report · mus · 2026-09-27**

Scope: design support for dynamic `%tab:<tab_name>` sub-tabs on the Agents tab,
including the default-`main` rule, single-tab suppression, machine-tab renaming,
icons, the no-`ALL` decision with the 3-view `o`/`O` panel cycle, and the new
"machine tabs" glossary term. Baseline prior research:
`202609/agent_machine_tabs_and_cluster_semantics/agent_machine_tabs_and_cluster_semantics.md`
(synthesis; read via audited artifact read) plus direct inspection of the current
tree (`src/sase/ace/tui/`, `src/sase/agent/`, `src/sase/xprompt/`,
`src/sase/core/agent_tribe.py`, `src/sase/default_config.yml`,
`docs/remote_dispatch.md`).

## 1. Verdict: good idea, ship it with adjustments

The plan is directionally right. Today the Agents tab has exactly one
tribe-panel axis (split vs. merged via `_agent_panels_grouped`, see
`src/sase/ace/tui/models/agent_panels.py` and the `o` → `AgentGroupingModal` →
`TOGGLE_PANELS` path in `src/sase/ace/tui/modals/agent_grouping_modal.py`) and
one grouping axis (`GroupingMode`: `STANDARD`/`BY_DATE`/`BY_STATUS`/`BY_MACHINE`,
see `src/sase/ace/grouping_strategy.py` and
`src/sase/ace/tui/models/agent_groups/_buckets.py`). Neither answers "group this
workstream's agents together regardless of tribe, clan, or machine." Tribes are
mutable labels with `@` display and wait/fork semantics; clans are
generation-scoped parallel cohorts with `%wait:<clan>` barriers and cascade
cleanup; `BY_MACHINE` buckets are derived execution ownership. None of them is a
free-form, user-named view scope. A lightweight dynamic tab fills that gap
without disturbing any of those contracts.

I recommend proceeding, with the adjustments in §8 (all called out explicitly).
The two most important: (a) separate stable tab **identity** from **display
label** so `main` never renames out from under persisted state, and (b) make
the tab a launch-time **view hint stored on the agent record**, not a second
tribe/clan membership system.

## 2. What the prior research gets right, and where this request diverges

The machine-tabs synthesis proposes `All` / `here` / one-tab-per-machine with
query-composition semantics, overflow handling, health-aware counts, and a
typed "Agent Cluster" presentation vocabulary. That is the right answer to the
*fleet-navigation* problem and I endorse its constraints: tab switching must be
an in-memory projection (no I/O), digits stay reserved for agent-relation jumps,
`machine:` query text stays authored (tab scope composes with it, never rewrites
it), and no universal "Move to cluster" operation.

This request is a different, larger feature: **user-named dynamic tabs** that
exist whether or not any remote machine is enrolled. Machine scoping becomes
one population rule for one special tab (`main`), not the whole tab catalog.
Consequences:

- The prior synthesis says "default to `All`." This request says "default to
  `main`" and explicitly rejects an `ALL` tab. I agree with the request (see
  §6), but the team should consciously retire the `All`-default assumption:
  `main` is a *tab like any other*, not a scope over tabs.
- The prior synthesis defers arbitrary saved-query/tribe-as-tab providers as
  needing count/attention/mark policies. `%tab` is narrower and safe to ship
  now precisely because it is **launch-authored, one-agent-one-tab** (like a
  tribe, unlike a saved query). Keep it that way; do not generalize to
  multi-membership tabs in v1.
- Keep the prior synthesis's non-negotiables: single-widget surface with
  per-tab lightweight state (selected identity, focused panel, fold/scroll
  anchor, detail target), attention markers on inactive tabs, explicit
  query-conflict empty states, and rename-safe selection keys.

## 3. The `%tab:<tab_name>` directive

### 3.1 Syntax and parsing

Add `tab` to `_KNOWN_DIRECTIVES` in `src/sase/xprompt/_directive_types.py`
alongside `clan`/`id`/`dispatch`/`wait`, with the colon form canonical:
`%tab:<tab_name>`. For consistency with `%clan:<name>` / `%id:<name>` /
`%dispatch:<alias>`, accept the backtick-quoted colon form
(`%tab:`my tab``) for names with spaces. Do **not** add a paren form with
kwargs in v1 — there is nothing to configure yet, and a bare `%tab(...)` would
invite a second metadata schema. Reserve (but do not implement)
`tab=<name>` as a future `%id(...)`/`%clan(...)` keyword for symmetry with
`tribe=`; v1 keeps one spelling so prompt cleanup, completion, and diagnostics
stay simple.

Validation should reuse the tribe-name grammar
(`src/sase/core/agent_tribe.py`: `validate_tribe_name`), not invent a new one:
non-empty, same character class, same length cap. Differences from tribe: `tab`
is **not** a wait/fork target, never takes an `@` prefix, and the reserved
names are `main` (or whatever the canonical default id is) plus whatever the
machine-alias namespace needs. Decide explicitly: can a user name a tab
`apollo` when `apollo` is also a machine alias? I recommend **yes** (explicit
`%tab` always wins, §5.4) but the display must then disambiguate machine-derived
vs. user-authored tabs (different icon/accent, §7).

### 3.2 Where the value lives (Rust boundary)

Tribe validation already lives behind the Rust boundary
(`sase.core.agent_tribe` delegates to `sase_core_rs`; clan records live in
`src/sase/core/agent_clan_*.py`). A tab is the same kind of shared-backend
concept by the project's own litmus test: a CLI (`sase agent list`), an editor
integration, or a future web client would all need to agree on "which tab is
this agent on." So:

- Canonical grammar + normalization (case folding? trim? `local` reservation?)
  belong in `sase_core` (new `agent_tab` module mirroring `agent_tribe`), with
  Python calling through the binding. No Python fallback, no env-var switch,
  per the rust-core-required decision.
- The per-agent assignment itself is launch metadata, exactly like `tribe` on
  the agent/session record (`tribe` field in
  `src/sase/ace/tui/models/_agent_state_session.py`; `fleet_origin_alias` in
  `.../_agent_state_fleet.py`). Add a sibling nullable `agent_tab` field
  populated at launch admission from the parsed directive, defaulting to unset
  (= `main` by rule). It must survive the same paths tribe survives: relaunch
  prompt rewriting (`src/sase/agent/relaunch_prompt.py` currently drops
  `%clan`/`clan=` deliberately — `%tab` must be **preserved**, since it is view
  state, not execution topology), restart preview, import/follow promotion
  (`_agent_imported_agent_session.py`), and dispatch provisionals.
- Presentation (catalog derivation, display labels, icons, counts) stays in
  this repo (`src/sase/ace/tui/models/` + `actions/agents/`), mirroring how
  `agent_panels.py` renders tribes without owning tribe storage.

### 3.3 Interaction with existing directives

- `%id` / `%clan` / `#tribe`: orthogonal. An agent can be in clan `research`,
  tribe `@web`, tab `frontend` simultaneously. Tribe panels continue to
  partition *within* a tab (§6). Clan subtrees never split across tabs: the
  tab is read off the structural root's assignment (same anchor-inheritance
  rule `agent_panels.py` already uses for tribes: "every structural descendant
  inherits its outer rendered root's effective tribe"). If members of one clan
  somehow carry different tabs (relaunch edge, imported rows), show the whole
  root under the root's tab and optionally emit the same mixed-origin
  diagnostic the prior synthesis prescribes for cross-machine clans. Never
  silently split a clan.
- `%dispatch:<alias>`: orthogonal at launch, composed at display. Dispatch
  decides *where it runs*; `%tab` decides *where it shows*. A dispatched agent
  without `%tab` lands on the dispatch machine's `main`-equivalent (§5.2); a
  dispatched agent with `%tab:frontend` lands on `frontend`.
- Fenced-code and disabled-region protection: reuse the exact
  `protect_fenced_blocks` / `protect_disabled_regions` +
  `collect_prompt_directive_matches` pipeline that
  `extract_static_clan_directive` uses, so `%tab` in a code sample never
  creates a tab.

## 4. Default `main` and single-tab suppression

Default rule ("no `%tab` → `main`") is right and should be a **display-time
default for unset**, not a value written into every record. Rationale: keeps
the store migration trivial (nullable column, all legacy rows read as `main`),
keeps "rename the default" a presentation change, and avoids rewriting history
on upgrade.

Single-tab suppression ("one populated tab → no strip, current behavior") is
right and is the feature's best reliability property: every existing user with
no `%tab` and no remotes sees zero UI change. Specify it precisely:

- Count **populated** tabs (tabs with ≥1 rendered agent row after query +
  `STARTING` exclusion — `agent_is_rendered_in_agents_panel` already excludes
  `STARTING` rows while keeping them in the headline count), not catalog tabs.
  An enrolled-but-empty remote machine must not force the strip visible by
  itself; that would punish enrolling a machine. (If machine tabs are adopted
  per §5, the strip appears when ≥2 *populated* tabs exist, where
  machine-derived tabs count.)
- The strip is a pure function of the current roster per refresh; when it
  collapses to one tab, selection resets to that tab without persisting a
  stale choice. Persisted per-tab state (selection/focus/folds) is keyed by
  tab id and survives hiding, so returning to multi-tab restores gracefully.
- What counts as "agents on it": rendered rows, not raw records. Document the
  `STARTING` exclusion so a launch storm doesn't flicker the strip on and off.

## 5. Machine tabs

### 5.1 The renaming rule, restated safely

The request: with remotes configured, display `local` instead of `main` for
current-machine agents, and `<machine_name>` for each remote's agents. This is
good UX (matches the `here` intuition and the existing `BY_MACHINE` "local
rows under `here`" vocabulary) but dangerous if implemented as renaming the
tab's **identity**: persisted selection, per-tab fold registries
(`_group_fold_registries`, `_fold_persistence.py`), panel-focus keys, and any
future CLI `--tab main` filter would all break or need migration every time a
machine is enrolled, renamed, or unenrolled.

**Adjustment 1 (identity vs. label): keep the tab id stable as `main` (or
`tab:main` internally); only the *display label* (and icon) derives from
machine context.** Catalog key = `(kind=machine-default, owner=<stable
owner key>)`; label = `local` / `<alias>` / `main` per the rules below. The
fleet row model already carries the right stable material
(`fleet_origin_alias`, `fleet_origin_installation_id`, logical locator fields
per the prior synthesis) — implementation must specify the canonical
owner-key mapping (logical owner identity, not the renameable alias) before
persisting tab selection, exactly as the synthesis demands.

### 5.2 Label derivation

- No remotes enrolled → label `main` (status quo ante, zero churn).
- ≥1 remote enrolled → local agents' default tab labels `local`; each remote
  machine's default tab labels with its configured alias (`apollo`, `mac`).
- Explicit `%tab:<name>` agents always show `<name>` on every machine (§5.4).
- Alias rename → label follows the alias; selection follows the stable owner
  key (§5.1). Unenrolled machine while its tab is active → fall back to the
  local-default tab with a brief notice (same rule as the prior synthesis).
- Empty remote tab: keep it listed while its machine is enrolled (so it doesn't
  vanish when needed) but do not let empties alone force strip visibility
  (§4); label its empty state with the cause (no agents vs. query-excluded vs.
  feed unavailable, with a route to Machines diagnostics).

### 5.3 Icons

Agreed — every machine-derived tab (including `local`) gets an icon in the
sub-tab title bar; user-authored `%tab` tabs get either no icon or a distinct
generic one (e.g. a tag/folder glyph), never the machine glyph. This makes the
"why is this tab called apollo — is it the machine or my `%tab:apollo`?"
ambiguity (§3.1) visually resolvable. `PanelTabStrip.PanelTab` already supports
`icon` with proper two-cell width accounting (`_build_content` uses
`cell_len`), so this is a data choice, not a widget project. Pick the icon
from the existing fleet/machine vocabulary (whatever Machines diagnostics and
`BY_MACHINE` banners use — a host/computer glyph, **not** `⌂`, which reads as
"home project"): audit current glyphs first so the strip doesn't introduce a
third visual language. Inactive tabs render the icon dimmed (`#666666`) per
existing strip behavior; active renders in the tab accent.

### 5.4 Explicit `%tab` always wins (all machines)

Agreed, and this is the correct precedence. It enables the headline use case
(one project tab spanning local + remote agents). Two corollaries to lock in:

- A `%tab:frontend` agent running on `apollo` appears **only** on `frontend`,
  never also on `apollo`. One agent, one tab — the invariant that keeps
  counts, attention badges, marks, and bulk-action scope truthful.
- Machine-health signals for that agent (stale feed, offline) must surface on
  the `frontend` tab (row badge + header diagnostic), not hide on an unvisited
  machine tab. Cross-cutting health follows the agent, not the tab.

## 6. No `ALL` tab; 3-view `o` + `O`

### 6.1 Agree: no `ALL` sub-tab

Correct call. An `ALL` tab duplicates the merged view the `o` cycle already
provides, doubles the tab catalog, and creates the "which tab am I on / where
did my agent go" confusion the feature exists to remove. The merged-tribes +
merged-tabs view belongs in the *panel-layout* control (`o`), not the *tab*
control. This also preserves the single-tab-suppression invariant: with an
`ALL` tab the strip could never hide.

### 6.2 The `o` 3-state cycle

Today: `o` (`choose_agent_grouping`) opens `AgentGroupingModal`; pressing `o`
again inside it fires `TOGGLE_PANELS`, flipping the boolean
`_agent_panels_grouped` (split-by-tribe ⇄ one merged `All agents` panel; see
`panel_key_per_agent(..., merge_tribe_panels)` and
`AgentPanelGroup.from_agents(..., merge_tribe_panels)`). The request upgrades
that boolean to a 3-state panel scope:

1. **Split** (current default): panels per tribe, within the active tab.
2. **Merged tribes, current tab** (current `o` behavior): one panel, active
   tab's agents only.
3. **Merged tribes, all tabs** (new): one panel, every tab's agents (the
   honest replacement for `ALL`).

Cycling `o` advances 1→2→3→1; new `O` (`cycle_grouping_mode_reverse` exists in
`default_config.yml` for Artifacts panes but Agents currently resolves `o` to
the picker — wire the Agents equivalents) goes backward. Details to specify:

- **Scope composition order.** Pipeline:
  committed query → **tab scope** (skipped entirely in view 3) → tribe panels
  (skipped in views 2–3) → grouping tree → rows. View 3 composes the query
  across tabs (tabs never rewrite query text); a query that excludes a whole
  tab yields the explicit conflict empty-state pattern, not silent omission.
- **Grouping modes interplay.** `GroupingMode` (`BY_MACHINE` etc.) is
  orthogonal and keeps working in all three views; in view 3, `BY_MACHINE`
  will naturally show per-machine sections inside the one merged panel, which
  is a feature (the "fleet overview" the prior synthesis wanted from `All`
  without a dedicated tab).
- **Modal rows.** The `AgentGroupingModal` "Panel layout" row becomes a
  3-state row showing the action *and* the current state (existing pattern:
  "Split panels by tribe / Merge panels" + "Current: …"). Pressing `o`
  inside the picker advances one step (matching today's "press o to toggle"
  affordance); `O` (shift) inside the picker steps back. Footer and
  `help_modal/agents_bindings.py` text, `default_config.yml` comments, and the
  block-rail hint update together.
- **Persistence.** Today's boolean persists via panel snapshots
  (`agent_fold_persistence.py` `"merged"` scope,
  `_loading_compute_finalize.py`). Migrate to a 3-value enum with the old
  `true`→"merged-tab", `false`→"split" mapping; default "split". Persist per
  session, not per tab (it is a layout choice, and per-tab would make view 3
  unrepresentable).
- **Focus/selection.** Views 2–3 render a single panel (`panel_keys=[None]`
  convention already exists in `AgentPanelGroup.from_agents` merged path);
  focus falls back to first panel; `J`/`K` panel navigation becomes a no-op
  with a hint (existing `_panel_navigation.py` already no-ops when grouped —
  extend the guard to the new state). Node-finder, jump panel, and cleanup
  modals read the same `merge` flag plumbing (`_node_finder_builder.py`,
  `agent_cleanup_*_modal.py`) — thread the new enum through, with view 3
  additionally widening the agent set to all tabs.

### 6.3 Why `O` matters beyond symmetry

`O` isn't just reverse — it's the escape hatch from view 3. A user who taps
into "everything merged" with a large fleet needs one keystroke back to their
tab, not a full 1→2→3 cycle through the heaviest view. Also note the keymap
comment in `default_config.yml` already reserves the `o`/`O` pair semantics
for Artifacts panes ("Artifacts panes with grouping still cycle with o/O; the
shared o key is resolved by tab availability") — giving Agents the same pair
removes a cross-tab inconsistency.

## 7. Beauty: making it intuitive and legible

- **Reuse `PanelTabStrip`, don't build a tab widget.** It already handles
  click geometry, full/compact/micro tiers, icons, accent colors, and
  `TabClicked`. Prior synthesis correctly warns micro-tier alone doesn't bound
  width for many machines — but dynamic tabs make this *more* urgent (tab
  count is now user-driven). Add the overflow window/picker with hidden-tab
  counts the synthesis prescribes from day one, plus a named jump target
  (node-finder-style) for hidden tabs. Never fall back to numbered shortcuts:
  digits are agent-relation jumps.
- **Placement.** One row in the existing Agents header area (where
  `_fleet_header.py` / `_update_agents_header` render), above tribe panels,
  below the main tab bar. Hidden entirely when suppressed (§4) — no reserved
  whitespace, no "Tabs: main" single chip.
- **Color discipline.** Tribe colors stay on tribe panels; machine accents
  only on machine-derived tabs; user `%tab` tabs share one neutral accent (or
  a stable hash from the existing tribe-palette helper, clearly distinct from
  both). Active tab bold + accent; inactive dim; attention (unanswered
  gate/needs-you, failed/stopped) as a count/dot on the inactive tab using
  existing global attention data — never cleared by switching away.
- **Counts.** Count agents (roots), not rendered rows; `N+` for bounded or
  incomplete sources; stale/offline marker with cause in header/tooltip. These
  are the prior synthesis's rules and they transfer unchanged.
- **Empty states.** Each empty tab says which of the three causes applies
  (no agents on this tab / query excludes them [with clear-filter action] /
  feed unavailable [with Machines-diagnostics route]). Never a bare blank
  panel.
- **Keyboard.** `o`/`O` for panel scope; `[`/`]` for tab cycling is the
  natural fit *only if* the pending bracket migration (prior synthesis: `(`
  /`)` for card blocks, `[`/`]` for machine tabs) lands first — otherwise
  pick unused keys and click + picker. Do not ship tab cycling on keys that
  currently step card blocks without landing that migration in the same
  release; focus-dependent key meaning was rightly rejected in the synthesis.
- **Motion.** Tab switch = in-memory reprojection + restore-by-identity with
  nearby fallback; no network, no disk, no widget-tree remount of inactive
  panels (cache only tab catalog + per-tab lightweight state). Preserve the
  `j`/`k` p95 <16ms target; gate release on tab-switch paint for a loaded
  large fleet.

## 8. Explicit adjustments to the requirements (normative)

1. **Stable id, derived label (Adjustment).** `main` is never renamed to
   `local` as an identity; only its display label (and icon) changes with
   machine context (§5.1). Same for `<machine_name>` labels: alias is display,
   stable owner key is identity.
2. **Tab is view hint, not membership (Adjustment).** One agent, exactly one
   tab, read off the structural root; clans/sessions never split. Mixed-tab
   clans render whole with a diagnostic (§3.3).
3. **No paren-form `%tab(...)` in v1; reserve `tab=` keyword (Adjustment).**
   One spelling (`%tab:<name>`, backtick-quoted for spaces); tribe-grammar
   validation; not a wait target; no `@` prefix (§3.1).
4. **Suppression counts rendered rows (Clarification).** `STARTING` agents
   don't force the strip; empty-but-enrolled machines don't force it (§4).
5. **`O` wires the existing reverse-cycle pair on Agents (Clarification).**
   Not a new concept — `cycle_grouping_mode_reverse` already exists for
   Artifacts; Agents gets the symmetric binding and the picker honors `O`
   as step-back (§6.2).
6. **Panel scope persists as a 3-enum with boolean migration (Adjustment).**
   Old `merged=true` → merged-current-tab, never silently to merged-all-tabs
   (§6.2).
7. **Overflow picker ships in v1, not later (Adjustment).** User-driven tab
   counts make the prior synthesis's "compact/micro alone doesn't bound
   width" warning a release blocker here (§7).
8. **Glossary term is "machine tabs" as requested, but scope it narrowly
   (Adjustment).** Define the machine-derived subset; define the general
   "agent tab" (dynamic sub-tab) term alongside so docs don't overload one
   phrase for both the mechanism and one population rule. Draft wording in §9.

## 9. Glossary: draft "machine tabs" strand

Proposed strand (to add through the audited SASE memory workflow during
implementation, with `[[glossary:agent-tribe]]` / `[[glossary:agent-clan]]`
links as appropriate):

> **Machine Tabs** — The Agents tab's default sub-tabs when remote machines
> are enrolled. Each enrolled machine's unassigned agents (those launched
> without `%tab:<tab_name>`) appear on a tab labeled with that machine's
> configured alias, and current-machine agents appear on a tab labeled
> `local`; with no remotes enrolled the same tab is labeled `main`. Machine
> tabs are derived view scope (execution ownership), not membership: selecting
> one never moves an agent, and an explicit `%tab:<tab_name>` always places
> its agent on `<tab_name>` on every machine. A companion **agent tab**
> (dynamic sub-tab) is any user-named `%tab:<tab_name>` scope; one agent
> belongs to exactly one agent tab, read off its structural root.

## 10. Delivery and validation (recommended)

1. **Core contract first (sase-core):** tab-name grammar/normalization +
   reservation list; per-agent nullable field; migration (unset ⇒ `main`);
   relaunch/restart/import preservation rules. Move the `sase-core-revision.txt`
   pin past the binding commit per `docs/rust_backend.md`.
2. **Directive + launch:** `%tab` parse/collect/cleanup/completion/diagnostics;
   admission default; `%dispatch` × `%tab` composition tests; fenced-block
   immunity tests.
3. **TUI tabs:** catalog derivation (stable ids, display labels, icons),
   strip render + suppression + overflow picker + attention/counts, per-tab
   state cache, in-memory switch, cross-tab jump + jump-back, query-conflict
   states, empty/error states, `[`/`]`-or-chosen cycling coordinated with the
   bracket migration, `default_config.yml` + help/footer/quickstart + goldens.
4. **Panel scope 3-view:** enum + persistence migration, modal rows + `o`/`O`
   wiring on Agents, single-panel render paths, node-finder/jump/cleanup
   widening, `BY_MACHINE`-in-merged-view verification.
5. **Memory + docs:** `machine tabs` (+ `agent tab`) strands via memory
   workflow; `docs/remote_dispatch.md`, agent-session/launch docs, keymap
   docs.
6. **Gates:** local-only and many-machine terminals; alias rename/unenroll
   while tab active; stale/bounded feeds; empty filtered tabs; inactive
   needs-you; arrivals during navigation; folded clans/sessions; marks and
   destructive-action scope wording ("in this tab" vs. "all tabs");
   `STARTING` storms; legacy `_agent_panels_grouped=true` snapshot load; old
   `[`/`]` card-block overrides; perf (no-I/O switch, paint on loaded fleet).

## 11. Recommended solution (summary)

Ship dynamic sub-tabs with `%tab:<tab_name>` as a launch-authored, validated,
single-membership view hint defaulting (display-time) to a stable-identity
`main` tab; suppress the strip when only one tab is populated; derive
`local`/`<alias>` display labels + machine icons for the default tab when
remotes exist while explicit `%tab` always wins everywhere; reject `ALL` in
favor of the 3-state `o`/`O` panel scope (split / merged-tab / merged-all);
reuse `PanelTabStrip` with an overflow picker from day one; put grammar + field
in `sase_core` and rendering in this repo; and add the narrowly-scoped
"machine tabs" glossary strand (plus an "agent tab" companion). The §8
adjustments are the difference between a demo and a reliable, beautiful
feature — adopt them as stated.
