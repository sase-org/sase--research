# Grouping scheduled routines: nav sections vs in-panel groups

**Researcher:** `research.e.grk` (independent swarm report)
**Date:** 2026-09-26
**Question:** How should sets of scheduled routines be grouped in the Services-tab sidebar, including a builtin-together bucket, and is splitting those groups into different nav sections a good idea?

## Recommendation (up front)

Group routines. Do **not** turn every group into its own nav section.

The real UX bug is that the Scheduled Routines panel is a single alphabetized list. Builtin lanes (`hooks`, `waits`, `checks`, `comments`, `usage`, `external_mirror`, `housekeeping`) interleave with anything the user or a plugin later adds. Putting builtins in one block is the right instinct.

The wrong upgrade is “one bordered panel per group.” On this tab a **nav section is a whole stacked `BgCmdList`**, with a two-row border title, a separator, `J`/`K` as a hop, and a share of the left-column height. The product already has a cheaper grouping primitive on this same tab: the `── oneshots ──` divider inside Service Procs, which the glossary explicitly says is **not** a nav section.

Ship this:

1. **Keep the two nav sections that exist today:** Service Procs and Scheduled Routines.
2. **Inside Scheduled Routines, partition by introducing config layer** (builtin / plugin / custom), using the same chrome pattern as the oneshot divider. Hide empty buckets.
3. **Sort builtins by tick interval, then name.** Leave custom routines alphabetical inside their bucket.
4. **Only promote a third nav section** (`Custom Routines`) if non-builtin routines exist *and* in-panel grouping still feels cramped after (2)–(3) plus a better default-fold policy for high-cardinality job trees.

Do not add a `group:` config field in v1. Origin is already in the AXE composition inventory.

---

## Critique of the plan

The plan as stated — “group sets of scheduled routines in different nav sections; start with all builtins together; figure out the other buckets later” — is half-right.

**Grouping builtins together is a good idea.** It matches how the operator actually thinks about this tree: the seven shipped lanes are the product’s own automation, and everything else is an extension. Today `_load_lumberjack_names` and the collector both do `sorted(config.lumberjacks.keys())` (`src/sase/ace/tui/actions/axe_display/_loader_items.py`, `_data.py`). A user routine named `docs` lands between `comments` and `external_mirror`. That is the mixing the grouping is for.

**Using nav sections as the grouping mechanism is the expensive part, and it is not justified by the current inventory.** Evidence:

- The Services sidebar is **statically two panels**. `ServicesPanelKey` is a two-value `Literal`, `SERVICES_PANEL_ORDER` is a two-tuple, and `_app_layout.py` mounts exactly two `BgCmdList` widgets. Membership is by **item class** (`ServiceProcItem`/`BgCmdItem` vs `LumberjackItem`/`ChopItem`), not by origin (`src/sase/ace/tui/actions/axe_display/_panels.py`).
- Height allocation already treats extra panels as costly. `allocate_panel_heights` charges **2 border rows per panel plus 1 separator between them**. Three routine groups plus Service Procs is four panels: 8 border rows + 3 separators = 11 chrome cells before any routine or job row. Agents can pay that tax because tribe panels collapse and isolate (`=` / `h`). Services currently passes `collapsed=[False, False]` and has **no whole-panel collapse**.
- The glossary already drew the line this request is about to cross. A nav section is “one panel in the left-side navigation column.” Grouping banners, Beads `Tasks` headers, and the Services `── oneshots ──` divider “are not nav sections” (`glossary:nav-section`). Service Procs already mixed two kinds of row **inside** one nav section rather than minting a third panel for oneshots.
- Agents tribe panels are the wrong analog unless the groups are **user-assigned, first-class collections**. A tribe is something you name, isolate, fold as a unit, and jump to with `J`/`K`. Config-layer origin is derived metadata. Elevating it to tribe-like panels over-builds a fact the composition already knows.

**“I’m not sure how to group the other routines” is a design signal, not a later TODO.** If the second axis is unclear, do not invent purpose taxonomies (lifecycle / remote / housekeeping) or cadence bands as nav sections. Those already exist: **each builtin routine is itself a cadence lane**, and the descriptions in `src/sase/default_config.yml` say so (“Fast lane…”, “belong in the other lanes”). Splitting the seven builtins across more panels would partition a set that should stay one block.

**Plugins today add service procs, not routines.** `sase-telegram`’s `default_config.yml` registers `telegram_receiver` under `service.procs`. Its job scripts (`sase_job_tg_inbound` / `sase_job_tg_outbound`) are installed executables the user attaches under `axe.routines`. `sase-github` ships no `axe.routines` block either. A “plugin routines” nav section would be empty on a normal machine. A “custom” bucket is where user-authored routines and future plugin-shipped routines both belong until that set is large.

I would take the in-panel origin split rather than a stack of new `BgCmdList`s, a `group:` schema field, or grouping by health/status (membership would flap on every tick).

---

## Requirement adjustments

These are deliberate changes to the request. Each one is required for the recommendation to stay small.

1. **Treat “nav section” as a whole Services sidebar panel, not an in-list heading.** The glossary, `J`/`K` hops, border titles, and height allocator all agree. In-list grouping is allowed and already used here; calling it a nav section would force the expensive widget.

2. **Group by introducing config layer, not by a new `group:` field.** A routine is builtin when the `default` layer introduced its key, plugin when the first introducing layer is `plugin:<name>`, custom otherwise (user config or machine overlay). A user who only changes `hooks.interval` does **not** move `hooks` out of builtin. A plugin that adds a job *under* `hooks` does **not** move the routine either. Jobs stay nested under their parent routine’s group.

3. **Do not split the seven builtins into multiple groups.** They are the builtin bucket. Their internal order should be operational (interval, then name), not a second taxonomy.

4. **Hide empty buckets.** No empty “Plugins” or “Custom” chrome when the inventory is the seven shipped lanes. The existing `adjacent_nonempty_panel` skip is the right behavior if a third panel is added later.

5. **Do not group service procs in the same change.** Daemon procs already mix builtin (`scheduler`, `gateway`), plugin (`telegram_receiver`), and user entries in one panel, with enablement provenance on the row. Mirror that: origin is a chip or a divider, not a new Services panel.

6. **Keep grouping membership off the render path.** Compute origin when AXE config is loaded (the collector already calls `load_axe_config()` / composition). Cache a `name → origin` map next to `_axe_lumberjack_names`. Do not re-walk layers per `j`/`k`.

7. **Default-collapse high-cardinality job trees as a related density fix, not as a substitute for grouping.** First-time sightings currently `expand` every routine (`_append_lumberjack_items`). Housekeeping is 10 jobs; `external_mirror`’s `for_each: projects` expands one row per enabled git/gh project. Grouping routines does not shrink that tree. Default-expand the fast lanes (`hooks`, `waits`); default-collapse `housekeeping` and `external_mirror` until the user opens them.

8. **Do not put grouping in `sase-core` unless a first-class `group:` field is accepted.** Origin can be derived from `AxeInventoryEntry.contributions` in Python. A named group is shared backend config (schema, exact-key composition, CLI) and would need the Rust AXE authority. v1 does not need that.

9. **If a third nav section is ever added, add Services panel collapse first.** Reuse `allocate_panel_heights`’s existing `collapsed` flags (Agents already uses them). Without collapse, extra panels steal height from the job tree the operator is trying to scan.

10. **Update `glossary:nav-section` only if extra panels actually ship.** In-panel dividers do not change the definition. A `Custom Routines` panel would.

---

## Current architecture

### What a nav section is on this tab

The Services tab left column is two stacked, bordered lists (`docs/ace.md` “Keybindings: Services Tab”, `_app_layout.py`):

| Nav section | Widget id | Rows | `J`/`K` |
| --- | --- | --- | --- |
| Service Procs | `#service-procs-panel` | Daemon `ServiceProcItem`s, then oneshot `BgCmdItem`s | First/last nav item of the adjacent non-empty panel, with wrap |
| Scheduled Routines | `#scheduled-routines-panel` | `LumberjackItem` plus indented `ChopItem` children | Same |

The focused panel is **derived** from `current_idx` through `ServicesPanelIndex`; it is not stored as a mode. The global `_axe_items` list stays flat so identity restore, the jump-all modal (`'`), and row actions keep one address space. Each widget renders a slice.

Panel titles already copy the Agents tribe-panel grammar (`{icon} {Label} · {count} [chip] badges`) from caches only (`_panel_titles.py`). That is the chrome you would duplicate per extra group.

### Grouping that already exists (and is not a nav section)

**Oneshots** live in Service Procs. When both daemon rows and oneshots are present, `format_bgcmd_option(..., show_divider=True)` prepends `── oneshots ──` onto the **first oneshot row**. The divider is extra line height on that option; it is not a selectable row (`_bgcmd_list_rows.py`). Glossary cites this as the canonical “in-list divider ≠ nav section” example.

**Jobs** already nest under routines. Fold keys are `lumberjack:<name>`. First sighting defaults to expanded. Collapsing a routine hides its jobs without changing panel membership.

**Beads** use disabled `── Tasks ──` / `── Epics ──` header options inside one Artifacts pane (`beads_list.py`). Those headers are also not nav sections; each Artifacts pane’s list is one nav section.

**Agents** use two layers: tribe **panels** (nav sections) for user-assigned collections, and grouping **banners** inside a panel for project/Patch/status. Collapsed banners are nav items; expanded banners are skipped chrome. That two-layer split is the pattern to copy: origin grouping is a banner/divider; a user-named routine tribe would be a panel, and no such tribe exists yet.

### Builtin inventory (the thing that would fill a “Builtin” panel)

Shipped under `axe.routines` in `src/sase/default_config.yml`, documented as seven default routines in `docs/axe.md`:

| Routine | Interval | Jobs (base) | Role |
| --- | --- | --- | --- |
| `hooks` | 5s | 8 | Patch lifecycle, fast |
| `waits` | 10s | 4 | Wait/claim/sidecar |
| `usage` | 60s | 1 | Subscription windows |
| `comments` | 60s | 1 | Critique-comment launches |
| `checks` | 5m | 4 | Triage, plugins, PR-submitted |
| `external_mirror` | 15m | 2 × projects | Tracker/PR mirror |
| `housekeeping` | 1h | 10 | Digest, reclaim, prune |

Fully expanded, that is 7 routine rows + ~30 job rows before `for_each` fan-out. `external_mirror` and any user `for_each: projects` job (the `docs` example in `docs/configuration.md`) multiply job rows by enabled git/gh project count. The collector walks `config.lumberjacks[name].chops`, which already includes generated instances (`ChopConfig.target_key` / `parent_name`).

Alphabetical builtin order today: `checks`, `comments`, `external_mirror`, `hooks`, `housekeeping`, `usage`, `waits`. Cadence order would put the lanes the operator debugs most (`hooks`, `waits`) at the top.

### Provenance already answers “what is builtin?”

`AxeConfigComposition.entries` is a per-entity inventory. Each `AxeInventoryEntry` carries `contributions: tuple[AxeRawContribution, ...]`, and each contribution has `layer` (`default`, `plugin:…`, `user`, `overlay:…`). `_layer_kind()` in `src/sase/config/inventory.py` maps those names to `builtin` / `plugin` / `user` / `overlay`.

Introducing layer = the lowest-priority contribution that actually defines the routine key, not the layer that last patched a field. That is the same distinction Config Center already uses for sparse edits. No schema change.

Service procs already surface a weaker form of this as enablement chips (`disabled here`, `disabled by <layer>`). Routines have no origin chip today.

### Implementation surface if extra panels were forced

A third (or Nth) nav section is not a sort-key change. It touches:

- `ServicesPanelKey` / `SERVICES_PANEL_ORDER` (currently a 2-tuple `Literal`)
- `_app_layout.py` compose (static two widgets vs Agents’ dynamic tribe mount)
- `_services_panel_key_for_item` (class-name dispatch is not enough; a `LumberjackItem` would belong to different panels)
- `_append_lumberjack_items` / `_build_axe_items` visual order
- `_apply_axe_panel_heights` (`filler_idx=1` hard-codes “routines absorb leftover”)
- `_axe_panel_widgets` queries by fixed CSS ids
- `J`/`K`, jump hints, visual snapshots, `docs/ace.md`, `docs/axe.md`, `glossary:nav-section`

Agents already solved dynamic panel counts. Copying that machinery onto Services is real work, and it is the wrong first increment.

---

## Grouping axes considered

| Axis | What it groups | Verdict |
| --- | --- | --- |
| **Introducing layer** (builtin / plugin / custom) | Matches the user’s “builtins together”; other routines have a default home | **Use this.** Derived, stable, empty-hideable. |
| **Cadence band** (sub-minute / minute / hourly) | Operational scan | Reject as a *group*. Each routine already *is* a cadence. Re-sort builtins by interval instead. |
| **Purpose** (lifecycle / remote / maintenance / custom) | Matches some description prose | Reject. Over-partitions the seven builtins; “other” still undefined. |
| **Health** (error / running / idle) | Attractive for ops | Reject as primary. Membership flaps every tick; `tui_perf.md` wants stable grouping membership on the incremental path. Title chips already show R/E/I. |
| **User-named groups** (tribe analog, `group:` field) | Most flexible | Defer. Needs schema + Rust composition. No evidence operators want named routine collections yet. Revisit if people start maintaining a dozen custom routines. |
| **One panel per builtin routine** | Maximum isolation | Reject. Seven extra borders on a tree that already has parent rows. |

For “the other routines” specifically:

- Plugin-introduced **whole routines** → one bucket labeled `plugin:<short-name>` if more than one plugin ships routines; otherwise a single `Plugins` label, or fold into Custom if the count is one.
- User- and overlay-introduced routines → `Custom`.
- Plugin-introduced **jobs on a builtin routine** → stay under that builtin. The operator still thinks of `hooks` as the hooks lane.

Until plugins actually ship `axe.routines` blocks, Custom is the only non-empty “other.”

---

## Alternatives

### A. In-panel origin dividers (recommended)

Keep two nav sections. In `_append_lumberjack_items`, emit routines in bucket order (builtin, plugin, custom), each bucket internally sorted (interval then name for builtin; name for the others). On the first routine of each non-first non-empty bucket, prepend a `── custom ──` / `── plugin:telegram ──` line the same way oneshots do.

- `j`/`k` still walk every routine and job.
- `J`/`K` still have two stops.
- Zero extra border chrome.
- Empty buckets emit nothing.
- Visual snapshot churn is one panel, not a new widget.

Use the oneshot prepend (chrome on the first row of the group), not Beads disabled headers and not Agents collapsed banners. On this tab, chrome-on-first-row is the established pattern and stays off the nav-item list.

### B. Third nav section, only when Custom is non-empty

`Service Procs` / `Scheduled Routines` (builtin only) / `Custom Routines` (plugin + user). Hide the third panel when empty so a default machine looks as it does today.

This is the **smallest honest reading** of “different nav sections” plus “builtins together.” It buys a per-group title chip (`Custom · 2 [E1]`) and a `J` hop that skips the seven expanded builtins.

Pay the cost only after A is in use and the custom set is actually large, and only after Services panels can collapse. Otherwise the third border eats the height the hop was meant to save.

### C. Full Agents-style tribe panels

User-assignable routine groups, isolate, fold, dynamic mount. This is a product feature (“routine tribes”), not a sorting of the shipped lanes. Reject until someone is managing many custom routines as collections.

### D. Status quo plus origin chips on the row

A `builtin` / `custom` chip on each routine row without reordering. Cheap, and it does **not** fix alphabetical interleave. Insufficient.

### E. Query / filter instead of groups

`axe.query` already filters Patches, not the sidebar tree. A Services-side filter box would hide rows rather than cluster them. Complementary later; it does not replace a stable builtin block.

---

## Implementation sketch (for A)

Stay in the sase TUI. No `sase-core` pin bump.

1. **Origin helper** next to AXE composition (Textual-free): given `AxeInventoryEntry` for `kind=lumberjack`, return `builtin` | `plugin:<name>` | `custom` from introducing contribution. Unit-test with a default+user overlay pair (user patches `hooks.interval` → still builtin; user adds `docs` → custom).

2. **Collector cache:** `_data.py` already builds `lumberjack_names = sorted(...)`. Also emit `lumberjack_origins` and a display order: builtin by `(interval, name)`, then plugin, then custom. `_load_lumberjack_names` must use the same order so the two loaders cannot drift.

3. **Divider:** extend `format_lumberjack_option` with `show_divider: str | None`, mirroring `format_bgcmd_option`. First custom/plugin routine in the slice gets the label. Divider line does not contribute to requested sidebar width (oneshot already documents this).

4. **Tests:** `test_services_panels.py` stays two-panel. New tests for order and “user patch does not rehome `hooks`.” Visual snapshots of the Services sidebar will shift when a custom routine is in the fixture; default-only goldens should be unchanged if empty buckets hide.

5. **Docs:** one paragraph in `docs/ace.md` Sidebar Row Taxonomy and `docs/axe.md` Services Tab Views. No glossary edit for A.

6. **Optional sibling (adjustment 7):** change first-sighting fold defaults for `housekeeping` and `external_mirror` to collapsed. Independent PR; do not couple it to grouping unless both are needed to make the builtin block scannable.

If B is later approved: generalize `ServicesPanelKey` to a sequence, mount the custom panel only when the origin map has a non-builtin key, put `ChopItem`s in the same panel as their parent `LumberjackItem`, and set `filler_idx` to the focused expanded panel (Agents already picks the first non-collapsed). Copy `panel_widget_id_for_key` rather than hard-coding `#scheduled-routines-panel`.

---

## Risks and limits

- **Chrome budget.** Extra nav sections steal rows from the job tree. Measure on a ~40-row terminal with all builtins expanded before adding a panel.
- **`for_each` fan-out.** Grouping routines does not cap job rows. `external_mirror[sase]`, `external_mirror[sase-core]`, … will still dominate if left expanded.
- **Stable identity.** Keep `_axe_items` keys as `("lumberjack", name)` / `("chop", lj, chop)`. Dividers must not become items or jump-all targets.
- **Config-token freshness.** Origin must ride `current_config_token()` the same way names do, or a newly added custom routine appears in the builtin block until restart.
- **Plugin jobs on builtin lanes.** If a future plugin injects a job into `hooks`, it will show under Builtin. That is correct. Do not split a routine across panels.
- **Name collisions.** Routine keys are unique in the merged map. A user cannot create a second `hooks`; they patch the builtin. Origin stays builtin.
- **Performance.** Do not walk `load_config_layers()` in `_paint_axe_panels`. Title stats already refuse disk I/O; grouping must too (`tui_perf.md` rules 1, 8, 14).
- **Visual goldens.** Services PNG snapshots will move if dividers appear in default fixtures. Keep default fixtures builtin-only so A is a no-op in goldens.

---

## Recommended solution

**Do group scheduled routines. Do it inside the existing Scheduled Routines nav section, by introducing config layer, with empty buckets omitted and builtins ordered by interval.**

That is the justified form of “all builtin routines together.” The “other” group is **Custom** (user/overlay), plus **Plugin** only when a plugin actually introduces a routine key. Jobs remain children of their parent routine.

Treat a `Custom Routines` nav section as a later increment, gated on a non-empty custom set, Services panel collapse, and evidence that `J` hopping over the builtin block is worth a third border. Do not add `group:`, purpose folders, or per-lane panels in v1.

The idea is good. The unit of grouping on this tab, for this inventory, is an in-list divider — the same unit Service Procs already uses for oneshots.
