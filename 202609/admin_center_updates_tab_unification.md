---
create_time: 2026-09-02
updated_time: 2026-09-02
status: research
---

# One Updates Tab: Merging Core, Plugins, And Agent CLIs Into A Single Inventory

**Research question:** the SASE Admin Center's **Updates** tab (`#` then `6`) is split into
three pane-local sub-tabs — **Core**, **Plugins**, **Agent CLIs** — cycled with `]` / `[`.
Merge them into one view that keeps every capability of all three. What is the correct UX
for that view, and what is the best way to implement it?

**Scope:** `sase` at master `8b0c65476`. Read paths: the whole `plugins_browser_*` module
family that implements the pane, the Admin Center tab catalog and session state, the
aggregate update model in `sase/updates/`, the `,U` Update panel and its comprehensive-update
plumbing, the shared query-profile stack, the pane's CSS block, and the test + PNG-snapshot
suites that pin the current layout. Live inventory magnitudes were sampled from this machine
with `sase plugin list -o` and `sase agent-cli list`. No TUI instrumentation was collected;
every structural claim below is cited to source.

---

## Executive summary

The three sub-tabs are **not three domains**. They are one domain — *versioned things SASE
can upgrade* — cut along an axis (which subsystem owns the package manager) that the user
does not care about, and the split is already contradicted by the code underneath it:

- **One load already produces all three.** `load_plugins_catalog_for_pane`
  (`src/sase/ace/tui/modals/plugins_browser_loading.py:99`) returns core versions, the
  plugin catalog, and agent-CLI statuses in a single `PluginsLoadResult`, and computes a
  single composite `UpdateStatus` from them.
- **One aggregate model already exists.** `UpdateStatus`
  (`src/sase/updates/status.py:96`) already flattens host / core / plugin into
  `components` and agent CLIs into `provider_candidates`, with per-source freshness. The
  `,U` Update panel is a projection of exactly that (`src/sase/ace/tui/update_panel_state.py:83`).
- **The cardinalities make the split absurd.** Core is *exactly two rows*, forever
  (`_CORE_PACKAGES`, `src/sase/uv_tool/versions.py:38`). Agent CLIs is registry-bounded —
  seven on this machine. Plugins is the only unbounded list. Today a static two-row panel
  gets a third of the tab's navigation budget and is the **default landing sub-tab**
  (`config_center_session.py:82`), where `j`/`k` and `'` are disabled by design
  (`plugins_browser_layout.py:164`, `plugins_browser_jump.py:1`).

The split also costs real UX: three summary lines, three hint lines, three status lines,
three empty states, **two mark sets that share the `Space` key with different meanings**
(`plugins_browser_agent_clis_actions.py:87`), and hint lines the source comments themselves
describe as out of room — `"u core+plugins" gave up its slot here so "' jump" fits`
(`plugins_browser_agent_clis.py:257`) and *"the browse-only variant of this line is exactly
as wide as the pane"* (`plugins_browser_status.py:246`).

**Recommendation (§6): one master/detail list of update rows, where capabilities are a
property of the row rather than of the active sub-tab, and `]` / `[` is repurposed from a
mode switch into a *scope* filter (Outdated → Installed → All).** The unbounded plugin
catalog moves behind the non-default `All` scope, so the landing list is ~13 rows and is
*cheaper* than today's Plugins sub-tab. Marks collapse to one set with one meaning
("include in the next run"), `i` / `I` / `A` / `U` collapse into `Space` / `Enter` / `u`,
and `u` submits the existing `ComprehensiveUpdateRequest` so the tab and `,U` become the
same model at two zoom levels instead of two half-overlapping surfaces.

---

## 1. What the three sub-tabs actually are today

All three live in one Textual widget, `PluginsBrowserPane`
(`src/sase/ace/tui/modals/plugins_browser_pane.py:183`), composed eagerly into a single
`ContentSwitcher` (`plugins_browser_layout.py:85`). There is no lazy mounting and no
per-sub-tab data source — merging them costs no extra I/O and removes widgets.

```python
_SUBTAB_ORDER: tuple[UpdatesSubTab, ...] = ("core", "plugins", "agent-clis")
```
— `plugins_browser_layout.py:29`

### 1.1 Core — a static panel with no cursor

`compose` yields three `Static`s: an all-current banner (hidden by default), a
`#sase-core-versions` Rich `Panel`, and a docked hint line
(`plugins_browser_layout.py:100-105`). There is **no list**, so:

- `j`, `k`, `'`, `Space`, `Ctrl+D/U`, `g`, `G` are all explicitly disabled here —
  `check_action` returns `False` for the whole `browse_only` set when
  `self._active_subtab == "core"` (`plugins_browser_layout.py:184-195`).
- `focus_default` falls through to focusing the pane itself
  (`plugins_browser_controls.py:47-54`).
- The pane's jump adapter documents the consequence in its module docstring: *"Core hosts
  no list at all, so it reports zero targets and `'` is a silent no-op there."*
  (`plugins_browser_jump.py:5`).

Its content is `_core_versions_panel` (`plugins_browser_rendering.py:455`): a two-row table
over `CoreVersions.packages`, an optional mode line (`PyPI (managed)` / `Dev (editable) ·
<root>` / `Mixed`), optional incoming-commit sections per outdated package, and a call to
action for `u`. `CoreVersions` is fixed at two entries:

```python
_CORE_PACKAGES: tuple[tuple[str, str], ...] = (
    ("sase", HOST_DISTRIBUTION_NAME),
    ("sase-core", CORE_DISTRIBUTION_NAME),
)
```
— `src/sase/uv_tool/versions.py:38`

**This sub-tab is the default landing surface.** `UpdatesSessionState.active_subtab`
defaults to `"core"` (`config_center_session.py:82`) and `AdminCenterSessionState` is
constructed fresh per ACE process (`src/sase/ace/tui/actions/_state_init_runtime.py:55`) —
only the *top-level* Admin Center tab has durable resume
(`validated_center_tab`, `config_center_catalog.py:191`). So every ACE start, the first
keystroke in the Updates tab is `]`.

### 1.2 Plugins — the master/detail browser

Filter input, summary line, then a two-column `Horizontal`: a 52-column `OptionList`
(`styles.tcss:8591`) with disabled group headers (`── Built-in ──`, `── Community ──`) and
a scrollable detail panel (`plugins_browser_layout.py:106-126`).

Row-scoped verbs: `i` install (`plugins_browser_install.py:236`), `I` / `Space` mark
(`:264`), `x` uninstall (`plugins_browser_uninstall.py:132`), `U` update
(`plugins_browser_update.py:179`), `m` switch mode (`plugins_browser_mode_switch.py:95`),
`v` verbose columns, `/` filter, `'` jump.

The list is the only unbounded surface in the tab: community entries come from a GitHub
topic search (`GH_SEARCH_QUERY = f"topic:{SASE_PLUGIN_TOPIC}"`,
`src/sase/plugins/_github_source_gh.py:18`) and the pane is benchmarked against catalogs of
**10 / 250 / 1000 / 2000 entries** (`tests/perf/plugin_catalog_scale.py:33`).

### 1.3 Agent CLIs — a second, parallel master/detail browser

Summary line, then a 58-column `OptionList` and a detail panel that additionally hosts a
durable update-history `Static` (`plugins_browser_layout.py:127-145`). Rows are provider
CLIs from the registry; the detail is a property table plus `build_agent_cli_history_panel`
(`plugins_browser_agent_clis.py:75`, `:398`).

Row-scoped verbs: `Space` mark (`plugins_browser_agent_clis_actions.py:87-98`), `A` update
(`:195`), `H` history scope (`plugins_browser_agent_clis.py:373`).

Sampled magnitude on this machine:

```
CLI              BINARY    INSTALLED  LATEST         METHOD
Antigravity CLI  agy       1.0.16     unknown        self managed
Claude Code      claude    2.1.258    2.1.258        self managed
Codex CLI        codex     0.152.1    0.152.1        npm
Grok Build       grok      1.0.13     1.0.13         self managed
Muse Code        muse      —          1.0.1-R2006.1  not installed
OpenCode         opencode  —          1.18.26        not installed
Qwen Code        qwen      —          0.22.3         not installed
```

### 1.4 What all three already share

This is the part that decides the design. Everything below is already common code:

| Concern | Shared today | Citation |
| --- | --- | --- |
| Data load | one threaded worker, one `PluginsLoadResult` | `plugins_browser_loading.py:99`, `plugins_browser_workers.py:116` |
| Aggregate status | `UpdateStatus` over components + provider candidates | `src/sase/updates/status.py:96` |
| Detail debounce | one `DetailPanelDebouncer` for both lists | `plugins_browser_layout.py:154` |
| Selection restore | `restore_selection_by_identity` + `ProgrammaticSelectionGuard`, instantiated twice | `plugins_browser_rendering.py:178`, `plugins_browser_agent_clis.py:75` |
| Jump mode | one `PaneEntryJumpMixin`, dispatched by sub-tab | `plugins_browser_jump.py:70-105` |
| Incoming commits | `build_incoming_commits_renderable` used by core *and* plugin detail | `plugins_browser_rendering.py:503`, `src/sase/plugins/render_common.py` |
| Confirm modal | `PluginActionConfirmModal` for every mutation in all three | `plugins_browser_sase_update.py:135`, `plugins_browser_agent_clis_actions.py:243` |
| Offline / refresh | `o` and `r` are already pane-wide | `plugins_browser_controls.py:83-96` |

The sub-tab boundary is a **presentation seam over a single data seam.** Nothing below the
widget layer is partitioned the way the UI is.

---

## 2. Six concrete problems the split causes

**(1) The landing surface cannot be navigated.** §1.1. The tab opens on a static panel
whose only affordances are pane-wide keys that work identically from the other two
sub-tabs.

**(2) The single most important answer is hidden.** "Am I up to date?" is answered by
`_all_current_banner` (`plugins_browser_status.py:88`), which is mounted **only inside the
Core sub-tab's container** (`plugins_browser_layout.py:101`). A user sitting on Plugins or
Agent CLIs never sees it — even though `_all_up_to_date` (`:54`) is computed across all
three sources.

**(3) The same key means different things in different sub-tabs.** `Space` is an *install*
mark on Plugins (offered only for **not-installed** rows, `_can_install_entry`,
`plugins_browser_rendering.py:614`) and an *update* mark on Agent CLIs (offered only for
**updatable installed** rows, `_can_mark_agent_cli`,
`plugins_browser_agent_clis_actions.py:110`). Two disjoint mark sets, `_marked_install` and
`_marked_agent_clis`, with two prune routines, two "advance to next markable" routines, and
an `Esc` handler that clears only the active sub-tab's set
(`plugins_browser_agent_clis_actions.py:154`).

**(4) Pane-wide verbs are silently sub-tab-sensitive.** `A` updates "marked agent CLIs on
that sub-tab, or every safely updatable installed agent CLI otherwise"
(`plugins_browser_agent_clis_actions.py:199-204`). From Core or Plugins the marks you set
on Agent CLIs are ignored. That is invisible from the hint line.

**(5) The hint lines are provably out of room.** The source itself documents the squeeze:

```python
# ``u core+plugins`` gave up its slot here so ``' jump`` fits ahead of
# the sub-tab hint; the Core sub-tab still advertises that key.
```
— `plugins_browser_agent_clis.py:257`

```python
# Wording is squeezed here: the browse-only variant of this line is
# exactly as wide as the pane, so ``' jump`` only fits alongside
# ``[ / ] sub-tab`` once the agent-CLI segment loses its verb.
```
— `plugins_browser_status.py:246`

Nineteen bindings (`plugins_browser_pane.py:205-232`) contend for one centered line. Any
new capability has to evict an existing one.

**(6) Answering "what do I need to update?" requires visiting three places and pressing
three verbs.** `u` for core+plugins (`plugins_browser_sase_update.py:78`), `A` for agent
CLIs, `a` for agents repositories (`plugins_browser_layout.py:245`). Three previews, three
tracked procs — while `,U` already does all of it as one confirmed, sectioned, ordered run
(§4).

---

## 3. The two facts that decide the design

### 3.1 The domain is already one aggregate

`sase/updates/status.py` flattens the whole tab into two typed row families plus per-source
freshness:

```python
@dataclass(frozen=True)
class UpdateStatus:
    checked_at: float
    components: tuple[OutdatedComponent, ...]          # role: host | core | plugin
    provider_candidates: tuple[ProviderUpdateCandidate, ...]
    core_source: UpdateSourceStatus = ...
    plugin_source: UpdateSourceStatus = ...
    agent_cli_source: UpdateSourceStatus = ...
```
— `src/sase/updates/status.py:96`

`OutdatedComponent` carries `display_name`, `role`, `installed_version`, `latest_version`,
`distribution_name`, `install_type`, `source_root`, `upstream_ref` (`:36`). That is already
a discriminated union across *core and plugins*, and `ProviderUpdateCandidate` (`:50`) is
the third arm. A merged row model is a generalization of a model that exists, not a new
invention. `PluginsLoadResult.update_status` is already computed on the pane's own load
thread (`plugins_browser_loading.py:154-168`); today the pane forwards it to the top-bar
badge and then discards it (`plugins_browser_workers.py:277-284`).

### 3.2 The cardinalities are wildly asymmetric

| Source | Bound | On this machine |
| --- | --- | --- |
| Core | **fixed at 2**, hard-coded | 2 |
| Agent CLIs | registry-bounded | 7 (4 installed) |
| Plugins — installed | your choice | 3 built-in + 0 community |
| Plugins — catalog | **unbounded** (GitHub topic search) | 4 today; benched to 2000 |

So the *installed* inventory is **13 rows**, and the only thing that can ever be big is the
part you are browsing rather than maintaining. A naive "concatenate everything into one
list" would bury 9 important rows under a catalog. The correct merge is therefore not
"remove the partition" but **"repartition along the axis the user actually uses: what I
have vs. what I could add."**

---

## 4. The neighbouring surface: the `,U` Update panel

There is already a second, newer update surface. Leader `,U`
(`update_sase: "U"`, `src/sase/default_config.yml:747` →
`_leader_mode.py:293` → `action_update_sase_shortcut`, `src/sase/ace/tui/actions/base.py:153`)
opens a modal with **four rows**:

```python
_ROW_COPY: dict[UpdateOptionScope, tuple[str, str, str]] = {
    "everything": ("e", "Everything", "SASE, providers, and published agents in one tracked update."),
    "sase":       ("s", "SASE, core & plugins", "Upgrade the sase host package, sase-core, and every installed plugin."),
    "providers":  ("p", "Providers", "Update every installed LLM / agent CLI provider."),
    "agents":     ("a", "Agents", "Import agent hoods your other machines published."),
}
```
— `src/sase/ace/tui/update_panel_state.py:27`

Each row carries a status chip (`available` / `current` / `unknown` / `failed`), a count,
and a detail line, projected purely from two cached snapshots with **no I/O on the
keystroke** (`base.py:155-161`). Choosing a row submits a `ComprehensiveUpdateRequest`
(`UpdateScope`, `src/sase/ace/update_scope.py:21`), which plans one sectioned preview and
runs one tracked proc with ordered legs — agent CLIs first, SASE second, agents sync last
(`docs/ace.md:6524-6537`).

**This matters twice.**

First, it is the aggregate view the Updates tab lacks. `,U` answers "what's outdated, run
it" in one screen; the tab, which is the surface with all the *inventory*, cannot.

Second, it establishes the deliberate constraint the merge must not break. From
`docs/ace.md:6543-6545`:

> The providers leg still captures the agent-CLI candidates from the latest completed
> automatic result, revalidates exactly those names, and **never broadens the captured set
> from an Updates-pane load.**

That snapshot-gating is a design decision, not an accident. Any wiring of the merged pane's
`u` into the comprehensive path has to supply pane evidence *explicitly* rather than let it
leak into the cached-capture path (§6.7, §9).

The fortunate part: the preview's inputs are already an injectable dataclass —

```python
@dataclass(frozen=True)
class UpdatePreviewInputs:
    uv_tool: object | None
    agent_cli_statuses: tuple[AgentCliStatus, ...]
    agent_cli_error: str | None
    offline: bool
    cached_status: UpdateStatus | None
```
— `src/sase/ace/tui/update_preview_inputs.py:19`

— and the pane already holds every field (`_uv_tool`, `_agent_cli_statuses`,
`_agent_cli_error`, `_offline`, plus the discarded `update_status`). A pane-sourced
`UpdatePreviewInputs` is a constructor call, not a new collection path.

---

## 5. The design space

Six candidate shapes, judged against: *does it answer "am I current?" on open*, *does it
keep every existing capability*, *does it survive a 2000-row catalog*, *how much width does
it burn*, and *how many modes does the user have to hold in their head*.

### A — One list, section headers

One `OptionList`; disabled group headers `── SASE ──`, `── Plugins ──`, `── Agent CLIs ──`;
one detail panel dispatching on row kind. The header-plus-item mechanism already exists
(`_HEADER_PREFIX`, `_create_options`, `plugins_browser_rendering.py:254`) and the jump
mixin already skips headers (`_is_item`, `plugins_browser_controls.py:224`).

*Wins:* one cursor, one mark set, one hint line, one detail panel, minimal new machinery.
*Loses:* on its own it puts 9 meaningful rows above a 2000-row catalog. Needs §C's or §D's
scoping to be viable.

### B — Three columns: source rail + list + detail

A narrow left rail listing the sources with counts (the Logs pane's source-list shape),
then the row list, then detail.

*Wins:* honest about heterogeneity; counts always visible.
*Loses:* the Admin Center container is 95% width with `padding: 1 2`
(`styles.tcss:7395`); the list is already 52-58 columns and the detail takes `1fr`. A third
column costs ~20 more. Worse, it **re-introduces a mode** — rail focus vs. list focus, two
cursors — which is the thing we are trying to delete. This is the sub-tab strip rotated 90°.

### C — "Needs attention" digest on top, browse list below

Two stacked lists: outdated rows and source errors up top, full inventory beneath.

*Wins:* the answer is at the top where the eye lands.
*Loses:* two cursors again, and every outdated row appears twice. Strictly worse than one
list that simply *sorts* outdated first.

### D — One list + a real query dialect

Replace the substring `Input` with the shared query stack — `ArtifactQuerySchema` /
`compile_query_profile` (`src/sase/ace/query_profile/`) — giving `kind:plugin`,
`status:outdated`, `installed`, `-source:catalog`, negation, completion, and highlighting,
exactly as the Procs pane has (`src/sase/ace/tui/_proc_query.py`,
`src/sase/ace/query_profile/profiles/_procs.py`).

*Wins:* the most expressive answer; scoping becomes data, not a mode; consistent with the
main ACE panes.
*Loses:* no Admin Center pane uses the query stack today. It is a ~150-line schema plus a
row adapter plus filter-bar wiring plus a `pane_registry` entry
(`src/sase/ace/query_profile/pane_registry.py:25`) — a real increment, and one that is much
cheaper *after* a merged row model exists than before it.

### E — Keep the sub-tabs, turn Core into an "Overview"

The minimal change: leave the partition, make the landing sub-tab an aggregate dashboard.

*Loses:* it does not merge anything. Every problem in §2 except (1) and (2) survives, and
it adds a fourth thing to maintain.

### F — Delete the tab; grow `,U`

`,U` already answers the aggregate question with zero latency.

*Loses:* `,U` deliberately cannot browse or inspect and never touches the plugin catalog,
so install / uninstall / mode-switch / per-CLI history would have no home. But the option is
instructive: it says the right relationship between the two surfaces is *the same model at
two zoom levels*, not two overlapping half-models.

**Verdict:** A is the right skeleton, but only once the scope problem from §3.2 is solved.
D is the right long-term filter but is not the cheapest way to solve scoping today. The
recommendation is **A, scoped by a cycled scope token, with D as the natural follow-on.**

---

## 6. Recommended solution — "One inventory, capability per row, scope-filtered"

The one-sentence version: **make capabilities a property of the highlighted row instead of
the active sub-tab, put every row in one list, and repurpose `]` / `[` from a mode switch
into a scope filter.**

### 6.1 The row model

A single discriminated row, built once per load from the three sources the loader already
returns:

```python
UpdateRowKind = Literal["core", "plugin", "agent-cli"]
UpdateRowSection = Literal["sase", "plugins", "agent-clis", "available"]

@dataclass(frozen=True, slots=True)
class UpdateRow:
    key: str                       # "core:sase", "plugin:github", "cli:claude"
    kind: UpdateRowKind
    section: UpdateRowSection
    label: str
    accent: str
    installed: bool
    installed_version: str | None
    latest_version: str | None
    update_available: bool
    source: str                    # managed | editable | git | npm | self managed | manual…
    capabilities: frozenset[UpdateCapability]   # update | install | uninstall | switch_mode | manual
    error: str | None
    payload: CorePackageVersion | PluginCatalogEntry | AgentCliStatus
```

`capabilities` is the load-bearing field. Every gate in the pane today is already a
predicate that could be folded into it:

| Today | Becomes |
| --- | --- |
| `_can_install_entry` (`rendering.py:614`) | `install in row.capabilities` |
| `_can_update_highlighted` (`status.py:286`) | `update in row.capabilities` |
| `_can_uninstall_highlighted` (`status.py:306`) | `uninstall in row.capabilities` |
| `_can_switch_mode` (`status.py:302`) | `switch_mode in row.capabilities` |
| `_can_mark_agent_cli` (`agent_clis_actions.py:110`) | `update in row.capabilities` |
| `check_action`'s `plugin_only` / `browse_only` sets (`layout.py:173-195`) | capability lookup on the highlighted row |

`payload` keeps the existing detail renderers working untouched (§6.5). The `NotUvToolInstall`
gate stays a pane-level fact that *subtracts* capabilities at build time, so the "not a `uv
tool` install" warning is computed once instead of in four predicates.

### 6.2 Layout

```
┌─ Updates ─────────────────────────────────────────────────────────────────┐
│  ↑ 3 updates · sase v0.17.0 → v0.17.1 · 1 plugin · 1 agent CLI            │  header digest
│  ⇅ 2 hoods from 1 project · checked 4m ago · Dev (editable)               │  (or the green
│                                                                            │   all-current banner)
│  ⟨ Outdated │ INSTALLED │ All ⟩                    / filter…              │  scope strip + filter
├────────────────────────────────┬───────────────────────────────────────────┤
│ ── SASE ──                     │                                           │
│   ↑ sase        v0.17.0→0.17.1 │   ┌─ sase ───────────────────────────┐   │
│   · sase-core   v0.2.9    dev  │   │ Installed   0.17.0                │   │
│ ── Plugins ──                  │   │ Latest      0.17.1                │   │
│   ↑ github      v0.2.9→0.3.0   │   │ Install     editable · ~/projects…│   │
│   · telegram    v0.4.9         │   │ Upstream    origin/master         │   │
│ ── Agent CLIs ──               │   │                                   │   │
│   ↑ Claude Code v2.1.2→2.1.3   │   │ Incoming commits (3)              │   │
│   · Codex CLI   v0.152.1  npm  │   │  abc1234 fix(x): …                │   │
│                                │   └───────────────────────────────────┘   │
├────────────────────────────────┴───────────────────────────────────────────┤
│ Space mark · ⏎ update · u update all (2) · m mode · r reload · / ' [ ] esc │  one hint line
└────────────────────────────────────────────────────────────────────────────┘
```

Structurally this is today's Plugins sub-tab with the Core panel folded into rows, the
Agent CLIs list appended as a section, and the sub-tab strip demoted to a scope strip. The
CSS block (`styles.tcss:8536-8674`) collapses from three sub-tab containers plus two
list/detail pairs to one pair.

### 6.3 Scopes and the landing state

Three scopes, cycled with `]` / `[` — the same keys, so muscle memory survives, but they
now filter instead of switching modes:

1. **Outdated** — rows with `update_available`, **plus** rows whose source errored, so a
   failed probe is never silently hidden by a filter that means "problems".
2. **Installed** *(default)* — SASE + installed plugins + installed agent CLIs. ~13 rows.
3. **All** — adds the `── Available ──` section: catalog plugins you do not have, and
   registered CLIs you have not installed. **This is the only scope that can be large**,
   and it is never the default.

**Landing behavior:** open on **Installed**, and place the cursor on the *first outdated
row* when one exists, otherwise the first row.

The alternative — landing on **Outdated** — was considered and rejected. Outdated is empty
most of the time, so the tab would usually open on an empty list; and the contents would
change shape between opens, which makes the surface feel unstable. Landing on a stable,
complete, small list and *moving the cursor to the problem* delivers the same "take me to
it" behavior without the instability. The header already states the count, and outdated
rows sort first within each section and carry the existing `↑` glyph.

Persist the chosen scope in `UpdatesSessionState` (replacing `active_subtab`) so a
deliberate `All` survives the session, while a fresh ACE still starts on Installed.

### 6.4 The keymap

Today: nineteen bindings, two overloaded by sub-tab. Proposed:

| Key | Action | Offered when |
| --- | --- | --- |
| `Space` | mark / unmark for the next run | row has `update` **or** `install` |
| `⏎` | act on the highlighted row now (preview + confirm) | same |
| `u` | run everything actionable — the marked set, or all actionable rows when nothing is marked | any actionable row exists |
| `x` | uninstall | row has `uninstall` |
| `m` | switch install mode | row has `switch_mode` |
| `a` | sync agents repositories (app-level, unchanged) | always |
| `H` | toggle update-history scope | highlighted row is an agent CLI |
| `]` / `[` | cycle scope | always |
| `j` `k` `'` `/` `r` `o` `v` `g` `G` `Ctrl+D/U` `Esc` | unchanged | — |

**Retired:** `i` (install), `I` (install-mark), `A` (update agent CLIs), `U` (update
plugin). All four are special cases of `Space` / `⏎` / `u` once the verb is derived from
the row. Keep them as hidden aliases for at least one release — they are documented in
`docs/configuration.md:415-424` and in muscle memory.

**The mark set collapses to one**, `_marked: set[str]` keyed by `UpdateRow.key`, with a
single meaning: *include this row in the next run*. The verb is derived — `update` for an
outdated installed row, `install` for an Available row. This deletes `_marked_install` /
`_marked_agent_clis`, both prune routines, both advance routines, and the split `Esc`
handler.

The resulting hint line is **shorter** than today's, because `[ / ] sub-tab` becomes
`[ ] scope`, `u core+plugins` and `A upd CLIs` become one `u update all (N)`, and `i` / `I`
/ `U` collapse into `Space` / `⏎`. That reclaims the width the comments at
`plugins_browser_status.py:246` and `plugins_browser_agent_clis.py:257` are fighting over.

### 6.5 The detail panel — dispatch, not rewrite

One `#updates-detail` scroll, switching on `row.kind`:

- **core** → the existing `_core_versions_table` row logic (`rendering.py:523`) rendered for
  a single package, plus the existing `_core_incoming_sections` block (`:503`) and the mode
  line (`:485`).
- **plugin** → the existing `build_detail_panel` + `build_community_warning_panel`
  (`_detail_renderable`, `rendering.py:440`), unchanged.
- **agent-cli** → the existing `_agent_cli_detail_panel` (`agent_clis.py:394`), plus
  `build_agent_cli_history_panel` beneath it, still gated by `H` (`agent_clis.py:387`).

No renderer changes. The Core panel actually *gains* from the move: today its incoming
commits are crammed into a shared panel for both packages; as per-row detail each package
gets the full detail column.

### 6.6 The header

One region, two states, always visible in every scope:

- **All current** → the existing `_all_current_banner` (`status.py:88`), promoted out of the
  Core container so it is finally visible from anywhere. `_all_up_to_date` (`:54`) already
  computes across all three sources.
- **Otherwise** → a digest line built from the retained `UpdateStatus`: total count, a
  short per-source breakdown, any failed source with its error, the cache age, and the
  offline badge. Plus a second line for install mode and the agents-sync count.

The digest is deliberately the same information `,U` shows (`update_panel_state.py:83`) —
that is the point of §6.7.

### 6.7 What `u` should do, and how the tab relates to `,U`

`u` should submit a **`ComprehensiveUpdateRequest`** (`src/sase/ace/update_scope.py:21`) built
from the marks:

- nothing marked → `UpdateScope.EVERYTHING` restricted to legs that have actionable rows;
- marks confined to one kind → the matching single-leg scope (`SASE` / `PROVIDERS`);
- mixed marks → `EVERYTHING`, with the preview's sections naturally showing only what was
  selected.

The preview is built with a **pane-sourced `UpdatePreviewInputs`** (`update_preview_inputs.py:19`)
constructed from `_uv_tool`, `_agent_cli_statuses`, `_agent_cli_error`, `_offline`, and the
`update_status` the load already computes and currently throws away
(`plugins_browser_workers.py:277`). No new collection path, no extra I/O, and — critically —
**no widening of the cached capture set** that `,U` gates on (§4, §9).

The two surfaces then divide cleanly:

| | `,U` Update panel | Admin Center Updates tab |
| --- | --- | --- |
| Latency | zero I/O on the keystroke | live load |
| Granularity | four scopes | every row, individually |
| Can browse the catalog | no | yes (`All` scope) |
| Can install / uninstall / switch mode | no | yes |
| Shares | `UpdateStatus`, `UpdateScope`, `ComprehensiveUpdateRequest`, `PluginActionConfirmModal` | ← same |

Same model, two zoom levels.

### 6.8 Where Agents fits

The `,U` panel has a fourth leg — **Agents**, importing hoods other machines published —
that the Updates tab binds (`a`, `plugins_browser_layout.py:245`) but never displays.

**Recommendation: surface it in the header digest, not as list rows.** Agent hoods are not
versioned components: they have no installed/latest pair, no per-row update command, and no
detail that belongs in this pane (`agents_sidecar.md` owns that). Giving them rows would
re-introduce exactly the heterogeneity the merge is removing, for no browse value. A
`⇅ 2 hoods from 1 project` chip in the digest, with `a` advertised in the hint line, gives
the user the complete "what is out of date" picture with a one-key path to act.

*The alternative* — a fourth `── Agents ──` section whose rows are projects with pending
hoods — is defensible if you want the tab to be a literal superset of `,U`. It is a
judgment call worth confirming (§10, Q2).

---

## 7. Why this is the right UX

Four questions bring a user to this tab. Rank them:

1. **"Am I up to date?"** — very frequent, often arrived at by clicking the top-bar badge
   (`updates_indicator.py:104`). Today: answered on a sub-tab you may not be on. Proposed:
   answered by the header, in every scope, before you press a key.
2. **"Update the things that are behind."** — frequent. Today: `]`-navigate, then `u`, then
   `A`, then `a`, three previews. Proposed: `u`, one preview, one proc — or `Space`-mark a
   subset first.
3. **"What exactly is the state of X?"** — occasional. Today: know which sub-tab X lives on.
   Proposed: `/` or `'`, one list, one detail panel.
4. **"What plugins could I install?"** — rare and deliberate. Today: the *largest and most
   prominent* surface in the tab. Proposed: one `]` press into the `All` scope.

The current design has the frequency ranking exactly inverted: the rarest task owns the
biggest surface, and the most common task owns a sub-tab with no cursor. The proposed design
sorts the surface by frequency, which is the whole argument.

Two secondary properties fall out for free:

**It is faster, not slower.** The default landing list is ~13 rows instead of the entire
catalog. The O(1) identity maps built per rebuild (`_rebuild_plugin_identity_maps`,
`rendering.py:220`) generalize to the merged row list unchanged; the debouncer, the
selection guard, and the jump mixin all become *single*-instance instead of paired. The
2000-entry benches (`tests/perf/plugin_catalog_scale.py:33`) now exercise a non-default
scope, so the common path gets strictly cheaper.

**It removes a mode.** Today the pane has a hidden mode variable, `_active_subtab`, read by
`check_action`, `_active_option_list`, `_detail_scroll`, `_jump_repaint`,
`action_toggle_mark`, `action_clear_marks_or_close`, and `action_update_agent_clis`. Every
one of those reads disappears or becomes a row-capability lookup. Modes that change what a
key means without changing what the key *looks like* are the most expensive kind, and
`Space` is currently exactly that.

---

## 8. Implementation shape

Four phases, each landable and verifiable on its own. Phases 1 and 2 are the whole UX win;
3 and 4 are polish and cleanup.

### Phase 1 — Capabilities move from the sub-tab to the row *(no visible change)*

New module `plugins_browser_rows.py`: `UpdateRow`, `UpdateCapability`, and a pure
`build_update_rows(load_result, *, uv_tool, offline) -> tuple[UpdateRow, ...]`. Rewrite
`check_action` (`layout.py:164`) and both hint builders to consult the highlighted row's
capabilities instead of `_active_subtab`. The three sub-tabs stay exactly as they are.

*Why first:* it is the only structurally risky step, and it can be landed with the UI frozen,
so the existing 6,200 lines of pane tests are the safety net rather than the casualty.

### Phase 2 — One list, sections, scopes

- Replace the two `OptionList`s with one `#updates-list`; keep the existing
  header/item option mechanism (`_HEADER_PREFIX`, `rendering.py:254`).
- Replace `ContentSwitcher` + `_SUBTAB_ORDER` with a scope enum and a `PanelTabStrip` of
  scopes; `_switch_to_subtab` (`layout.py:204`) becomes `_set_scope`.
- Collapse the two selection bookmarks into one; delete one `ProgrammaticSelectionGuard`.
- `_jump_repaint` (`jump.py:103`) loses its sub-tab branch.
- Detail panel dispatches on `row.kind` (§6.5).
- Promote the all-current banner and build the digest header (§6.6).
- `UpdatesSessionState.active_subtab` → `scope` + one `SelectionBookmark`.

### Phase 3 — Unify marks and verbs

One `_marked` set keyed by `UpdateRow.key`; `Space` / `⏎` / `u` per §6.4; `i` / `I` / `A` /
`U` become hidden aliases. Wire `u` to a pane-sourced `ComprehensiveUpdateRequest` (§6.7)
and retain `update_status` on the pane.

**Read `sase/memory/sase_flags.md` before starting this phase.** It is the note that governs
"deprecating user-reaching behavior [and] landing code whose old branch must stay reachable
for backward compatibility" (`CLAUDE.md` §2.6) — which is precisely what retiring four
documented keybindings and changing `Space`'s meaning is. My attempt to read it was blocked
by an environment fault, not by its contents (§10, note).

### Phase 4 — Docs, snapshots, and the follow-on filter

Docs, PNG rebaseline (§9), then optionally §5-D: an `updates` query profile
(`ArtifactQuerySchema` + row adapter + `pane_registry` entry) so the scope strip becomes a
convenience over a real query language, matching the Procs pane.

### Rust core boundary

Per `CLAUDE.md` §1.3, shared backend behavior belongs in `../sase-core`. The update domain
is currently **entirely Python** — there is no `sase_core_rs` call anywhere in
`sase/updates/`, `sase/plugins/`, `sase/agent_clis/`, or `sase/uv_tool/`. `UpdateRow` as
specified is a *presentation projection* over models that already exist on the Python side,
so it stays here. If it later grows into the canonical "what can be updated" inventory that
a web frontend or the CLI would need to match, that is the moment it crosses the boundary —
worth stating in the phase-1 plan so the decision is deliberate rather than accidental.

---

## 9. Risks, migration, and what must not break

**(1) The snapshot-gating contract.** `docs/ace.md:6543-6545` states the providers leg "never
broadens the captured set from an Updates-pane load." §6.7's pane-sourced
`UpdatePreviewInputs` must be passed *explicitly* into
`build_comprehensive_update_preview`, never written back into
`_automatic_update_status` / `_automatic_update_provider_names`. Add a regression test that
asserts a pane-initiated `u` leaves the app's cached capture untouched.

**(2) The test surface is large.** 16 pane test modules and 2 helper modules, 6,246 lines
(`tests/ace/tui/test_plugins_browser_pane*.py`, `_plugins_browser_pane_helpers.py`). Phase 1
should not touch them; phases 2-3 will. The ones that pin layout by widget id or call
`pane._switch_to_subtab(...)` directly are the ones to plan for.

**(3) The PNG snapshot suite.** `tests/ace/tui/visual/test_ace_png_snapshots_config_center_plugins.py`
has 15 snapshot tests, 7 of which call `pane._switch_to_subtab("core")` or
`("agent-clis")` explicitly (lines 83, 113, 138, 169, 199, 230, 256). Each needs
rewriting to a scope selection plus a rebaseline. `sase/memory/lint_and_test.md` covers the
PNG suite's mechanics and the `just check` / `just check-full` split — read it before the
phase-2 verification plan.

**(4) User-reaching keymap change.** Four retired bindings, plus `Space` changing meaning on
one of the two sub-tabs it currently serves. Aliases + a flag; see phase 3.

**(5) Docs to update.** `docs/ace.md:6495-6565` ("Updates Tab"),
`docs/configuration.md:413-438` (the keymap table) and `:977` (`agent_cli_history`),
`docs/plugins.md:276` and `:403`, `docs/agent_providers.md:261` and `:364`,
`docs/fakey.md:38`.

**(6) The `Available` scope must stay lazy in spirit.** The catalog is already loaded on
every pane load; the win is that it is not *rendered* by default. Do not let the row builder
materialize 2000 `UpdateRow`s on every load when the scope is `Installed` — build rows for
the active scope, or keep the catalog entries as `payload` references and build rows on
scope change. The existing benches (`tests/perf/plugin_catalog_scale.py`) should be re-pointed
at the `All` scope so the regression net stays in place.

**(7) `UpdatesSubTab` is an exported literal** (`config_center_session.py:11`, re-exported at
`:109`). Session-only, so no durable-state migration is needed — but grep before deleting.

---

## 10. Open questions

**Q1 — Default landing scope.** §6.3 recommends **Installed**, with the cursor placed on the
first outdated row. The alternative is an adaptive default (Outdated when anything is
outdated, Installed otherwise), which is more "helpful" but makes the tab's contents
unpredictable between opens. Confirm the preference.

**Q2 — Agents as rows or as a header chip.** §6.8 recommends the header chip. Rows would make
the tab a literal superset of `,U` at the cost of a fourth heterogeneous row kind.

**Q3 — Should `u` really route through the comprehensive path?** §6.7 says yes, because it
unifies the tab with `,U` and inherits the sectioned preview, ordered legs, restart handling,
and post-update toast. The conservative alternative is to keep `u` and `A` as today's two
separate legs and merely present them behind one key — less unification, less risk.

**Q4 — Query profile now or later?** §5-D is the strongest long-term filter, and §8 phase 4
defers it. It could instead replace the scope strip outright in phase 2, at the cost of a
larger single step.

**Environment note (not a finding):** `sase memory read tui_perf.md` and
`sase memory read sase_flags.md` both fail on this machine before printing anything:

```
sase.core.content_layout_wire.LayoutCollisionError: memory exists in multiple
canonical/legacy locations: /Users/bbugyi/sase/memory, /Users/bbugyi/memory;
migrate to the canonical path instead of merging split state
```

The failure is in home-memory link-universe discovery (`sase/memory/selector.py:251`), so it
affects every selector and is not worked around by `-p` or `-d 0`. Two reference notes this
work should consult — `tui_perf.md` (required before changing anything affecting TUI
navigation, refresh, or rendering) and `sase_flags.md` (required before deprecating
user-reaching behavior) — are therefore **unread**. The performance and backward-compatibility
claims above are derived from the source and from `docs/`, not from those notes. Resolve the
home-memory collision before the implementation plan is written.

---

## Appendix — file inventory

The Updates tab today, by module and line count:

| Module | Lines | Role in the merge |
| --- | --- | --- |
| `plugins_browser_rendering.py` | 666 | detail + row text + core panel — mostly survives as kind-dispatched renderers |
| `plugins_browser_comprehensive_update_preview.py` | 651 | shared with `,U`; unchanged |
| `plugins_browser_install.py` | 529 | verb collapses into `Space`/`⏎`; planning survives |
| `plugins_browser_incoming.py` | 498 | unchanged |
| `plugins_browser_agent_clis.py` | 426 | list-building folds into the shared list; detail survives |
| `plugins_browser_comprehensive_update_execution.py` | 410 | unchanged |
| `plugins_browser_dev_update.py` | 385 | unchanged |
| `plugins_browser_update.py` | 377 | verb collapses; planning survives |
| `plugins_browser_agent_clis_actions.py` | 346 | mark machinery **deleted**; planning survives |
| `plugins_browser_pane.py` | 320 | BINDINGS shrink; two mark sets → one |
| `plugins_browser_status.py` | 319 | three summaries + hints → one digest + one hint line |
| `plugins_browser_sase_update_procs.py` | 318 | unchanged |
| `plugins_browser_workers.py` | 311 | retains `update_status`; otherwise unchanged |
| `plugins_browser_loading.py` | 301 | **unchanged — already produces all three sources** |
| `plugins_browser_agent_clis_history.py` | 294 | unchanged |
| `plugins_browser_layout.py` | 249 | **the main rewrite**: `ContentSwitcher` → one list + scope strip |
| `plugins_browser_uninstall.py` | 246 | unchanged |
| `plugins_browser_sase_update.py` | 243 | `u` re-targets to the comprehensive request |
| `plugins_browser_controls.py` | 242 | `_active_option_list` / `_detail_scroll` lose their branches |
| `plugins_browser_sase_update_summary.py` | 221 | unchanged |
| `plugins_browser_mode_switch.py` | 219 | gating moves to a capability |
| `plugins_browser_operations.py` | 188 | unchanged |
| `plugins_browser_latest.py` | 130 | unchanged |
| `plugins_browser_jump.py` | 112 | **simplifies** — one list, no sub-tab dispatch |
| `plugins_browser_comprehensive_update_models.py` | 101 | unchanged |
| `plugins_browser_list.py` | 87 | unchanged |
| `plugins_browser_agent_clis_config.py` | 66 | unchanged |
| `plugins_browser_input.py` | 50 | filter input; grows scope tokens in §5-D |
| `plugins_browser_constants.py` | 15 | `_SUBTAB_NAV_HINT` → scope hint |
| **total** | **8,553** | |

Adjacent, unchanged, and shared with the merged pane:

- `src/sase/updates/status.py` — the aggregate the merged row model generalizes
- `src/sase/ace/update_scope.py`, `src/sase/ace/tui/actions/update_run.py` — the
  comprehensive path `u` should target
- `src/sase/ace/tui/update_panel_state.py`, `modals/update_panel.py` — the `,U` sibling
- `src/sase/ace/tui/widgets/updates_indicator.py` — the top-bar badge that opens this tab
- `src/sase/ace/tui/styles.tcss:8536-8674` — the pane's CSS block
