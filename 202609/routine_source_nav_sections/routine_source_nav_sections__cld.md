# Grouping Scheduled Routines Into Services-Tab Nav Sections

_Researcher: cld · 2026-09-26 · sase `master` @ `ff5412bbb6`_

## TL;DR

- **The idea is sound, and "builtin vs. not builtin" is the right first cut.** Today one
  **Scheduled Routines** nav section holds 8 routines and 32 jobs (about 40 rows). It
  overflows a normal terminal. It is sorted alphabetically, so the one routine you wrote
  yourself (`telegram`) is buried between `housekeeping` and `usage`, below the fold.
- **Group the other routines by where they come from, not by labels you invent.** Every
  routine is declared by one config layer: builtin defaults, a plugin, or you (the user
  layer, a machine overlay, or a project-local file). Service procs already use exactly
  this split (`builtin` / `plugin` / `user`, from `classify_source` in sase-core), so
  routines would reuse the same words and rules.
- **Keep the panels static.** At most three routine panels exist, one per source, and an
  empty one is hidden. That means none of the Agents tab's dynamic mount/retire
  machinery (about 6.2k lines). The epic that split the sidebar into two panels
  (sase-17a) avoided that machinery on purpose.
- **Compute each routine's source in the Rust core, not in the TUI.** A routine's source
  is backend behavior: `sase axe routine list` and the TUI must agree. It also cannot be
  derived reliably in Python, because the per-layer contributions it gets list only the
  writable layers.
- **Hold off on labels you write yourself** (a tribe-like `group:` key). They are the
  expensive part: an open-ended set of panels means dynamic panels. With only one
  routine that isn't builtin, there is nothing yet to group. Add labels when enough
  routines exist to need them, following the same logic as the project's "no mechanism
  before its corpus" decision.
- **Two changes I'd add that you didn't ask for:**
  - Builtin routines start with their job rows folded.
  - Each routine row gets a count of its failed jobs, so a folded routine still shows
    that something broke.

  The biggest readability gain comes from these, not from the split itself.

---

## 1. What exists today

### 1.1 The sidebar

- **Two fixed panels.** The Services sidebar is two statically composed `BgCmdList`
  panels: `#service-procs-panel` and `#scheduled-routines-panel`
  (`src/sase/ace/tui/_app_layout.py:147-151`). They landed 2026-09-23 in epic sase-17a
  (`3f5d34e9fd`, then `37bf264296` for `J`/`K`).
  - The plan for that epic says: _"There are always exactly two, so the Agents tab's
    dynamic mount/retire machinery is not needed."_
- **One global item list, split into panels.** All rows live in one flat list,
  `_axe_items`, which is split into panels by `build_services_panel_index`
  (`actions/axe_display/_panels.py`).
  - Which panel a row belongs to depends only on its **class name**
    (`ServiceProcItem`/`BgCmdItem` go to procs, `LumberjackItem`/`ChopItem` go to
    routines).
  - An unknown class raises `TypeError`.
  - `SERVICES_PANEL_ORDER` is a fixed 2-tuple.
- **Routines are sorted alphabetically**
  (`_loader_items.py:_load_lumberjack_names`). Each routine's fold is **expanded the
  first time it is seen** (`_append_lumberjack_items`).
- **Folding exists only per routine:** `h`/`l` fold one routine and `H`/`L` fold all of
  them (`actions/agents/_folding_axe.py`). There is no whole-panel collapse on Services.
- **Hard-coded two-panel assumptions** live in:
  - `_render_panels.py`: `_axe_panel_widgets` returns exactly two widgets, and
    `_apply_axe_panel_heights` passes `[False, False]` with `filler_idx=1`.
  - The "scheduler not running" badge on the Scheduled Routines title
    (`_panel_titles.py`).
  - The empty-state placeholder `No routines configured · a to add`.
- **Routine rows already carry a warning count** (`⚠N`) of jobs over their time budget.
  It exists _"so a collapsed fold still tells the operator something under this
  lumberjack needs attention"_ (`widgets/_bgcmd_list_rows.py:84-90`). There is **no**
  equivalent count for failed jobs.

### 1.2 Live state on this machine

From `sase axe routine list`, `sase config layers`, and a live `sase screenshot -t
services`:

| Routine           | Declared by                           | Jobs |
| ----------------- | ------------------------------------- | ---- |
| `checks`          | builtin (`default`)                   | 4    |
| `comments`        | builtin                               | 1    |
| `external_mirror` | builtin                               | 4 (generated per project) |
| `hooks`           | builtin                               | 8    |
| `housekeeping`    | builtin                               | 9    |
| `usage`           | builtin                               | 1    |
| `waits`           | builtin                               | 4    |
| `telegram`        | **user** (`~/.config/sase/sase.yml`)  | 1 (`tg_outbound`) |

- The screenshot shows the Scheduled Routines panel scrolling, with its title reading
  `8 [R8] · 32 jobs`.
- `telegram` is not visible without scrolling.
- The Service Procs panel above it holds only 3 rows.

### 1.3 Where each routine comes from

- **Config layers.** Layers are discovered in precedence order: `default`,
  `plugin:<module>`, `user`, `overlay:<file>`, `local` (`src/sase/config/layers.py`).
  Each is serialized with a `kind` of `builtin|plugin|user|overlay|local`
  (`config/inventory.py:_layer_kind`).
- **Service procs already record their source.** Each proc has `source ∈ {builtin,
  plugin, user}` plus a `declared_by` layer label (sase-core
  `service/config.rs:classify_source`, where overlay and local count as `user`).
  - The TUI shows this in the detail pane (`Source: builtin (default)`) and in row chips
    (`disabled by plugin sase_telegram`).
  - Plugin-declared procs even get different default behavior: `enabled` defaults to
    false.
- **Routines have no equivalent field.**
  - `LumberjackConfig` has no source or group.
  - The routine schema is `additionalProperties: false` and validated fail-closed in
    Rust. Adding any new routine key (such as `group:`) is therefore a schema change in
    sase-core, not a Python-only tweak.
- **The core can compute a routine's source with a small change.**
  - In sase-core `config/axe.rs`, `build_inventory` creates one
    `AxeInventoryEntryWire` per routine.
  - `raw_routine_value(layer, name)` already finds a routine's raw value in any single
    layer. The declaring layer is simply the first layer in order where that returns
    `Some`.
- **Python cannot derive it correctly today.**
  - `contributions` lists only writable layers, so the builtin and plugin layers never
    appear in it.
  - `field_provenance` is per field. If you override every field of a builtin routine,
    it would look user-declared.

### 1.4 The Agents tab: how it handles a variable number of panels

The Agents tab renders one panel per agent tribe:

- Each panel is an `AgentList` keyed by tribe, mounted and retired dynamically, with
  "sticky" retention (`actions/agents/_display_panel_widgets_mount.py`).
- Display config comes from `ace.tribes.<name>`: icon, color, description,
  `initially_expanded`.
- Panel order is fixed: `@default` first, then alphabetical, with collapsed panels moved
  last.
- It supports whole-panel collapse, `=` to isolate one panel, a merged "All agents"
  view, and selecting a whole panel (`❖`).
- The machinery totals about 6.2k lines. That is the benchmark for what "arbitrary
  groups as nav sections" costs.

---

## 2. Critique: is this a good idea?

**Yes, in the narrow form.** Three reasons:

1. **The builtin routines are SASE's own plumbing,** not your automation. The seven
   builtin routines (hooks, waits, checks, …) are infrastructure you act on only when
   they break. Mixing them alphabetically with your own routines hurts both: your
   routines are hard to find, and the plumbing takes up the space.
2. **Nav sections are the right unit.** They give you things banners inside one panel
   cannot:
   - `J`/`K` lands directly on your routines.
   - Each group gets its own title stats (running/error/idle chip, failed-job badges).
     So "is anything in SASE's plumbing broken?" is answered by reading one title.
   - Height allocation keeps a small panel whole while the large one scrolls.
3. **The builtin line is operationally real, not just cosmetic.**
   - Builtin and plugin routines can only be **overridden sparsely** from a writable
     layer. You cannot delete them.
   - Routines you declare are yours to edit or delete.
   - The `a` / `e` flows already behave differently along this line.

**Where the plan as stated could go wrong:**

- **"How do I group the rest?" is the actual design decision.** "All builtin together"
  is easy. The other routines raise the choice that decides the cost:
  - Groups derived from data are a small, fixed set, so the panels can stay static.
  - Groups you write yourself are an open-ended set, so the panels must be dynamic.
- **You have almost nothing to group yet.** Exactly one routine isn't builtin. Building
  a labelled-group system for one routine repeats the pattern the decision record
  `decisions:corpus-before-mechanism` warns about: mechanism built ahead of the data
  that justifies its shape, later deleted at real cost.
- **Declaring layer ≠ owning package.** `telegram` is conceptually the sase-telegram
  plugin's routine. Its job script ships in that plugin, and the plugin README says the
  routine is meant to be "configured globally (on every machine)". It lives in your
  user config only because nobody moved it.
  - Grouping by layer would show it as **user**. That is technically true but
    semantically off.
  - The right fix is in the data (the plugin should declare the routine), not a label
    that papers over it.
- **Vertical space.** Every extra nav section costs about 3 rows of chrome (2 border
  rows plus 1 separator). Three routine panels plus Service Procs is fine. N
  user-labelled panels in a 35-80-column-wide sidebar is not.
- **Splitting alone won't stop the scrolling.** The builtin group alone is 7 routines
  and 31 jobs, about 38 rows. It still overflows unless its job rows start folded.

---

## 3. Ways to group the routines that aren't builtin

| # | Option | What it gets you | Cost | Verdict |
| --- | --- | --- | --- | --- |
| A | **By source: builtin / plugin / user** (derived from the declaring layer) | Accurate. No config needed. Uses the same words as service procs. Matches what you can do to each routine (override vs. own it). Fixed set of at most 3 panels, so they stay static. | Small Rust change and small TUI change | **Recommended now** |
| B | One panel per plugin | Finer ownership | Open-ended set, so dynamic panels. Today 0 plugins declare routines. | Reject for now. Use a per-row plugin chip inside the Plugin panel instead. |
| C | Your own label (`group:` on the routine plus `ace.routine_groups` display config, like `ace.tribes`) | Maximum flexibility; follows the tribe precedent | Rust schema change, dynamic panels, a display-config surface, docs. Also lets config claim a builtin routine is something else. | **Defer** until enough routines exist to need it (§6) |
| D | By how often they run (fast / minute / hourly) | Shows how often work runs | Not the question you're asking. Interval is already in the detail pane. | Reject |
| E | Two buckets: "Builtin" + "Custom" (plugin and user merged) | Simplest | Hides whether a routine is yours to delete | Acceptable fallback. A is only marginally more work and more accurate. |
| F | Banners inside one panel instead of nav sections (like `── oneshots ──`) | Cheapest | No `J`/`K` stops, no per-group title stats, no per-group sizing | Reject: you asked for nav sections, and they are the better fit. |

---

## 4. Adjustments to your requirements (called out explicitly)

1. **ADJUSTMENT — group the other routines by declaring source, not by label.** Two
   tiers besides builtin, **Plugin** and **User**, with the same classification rules
   as service procs (`user`, `overlay:*`, and `local` all count as **User**).
2. **ADJUSTMENT — a fixed, static set of panels.** Service Procs plus at most three
   routine panels. A routine panel with no routines is hidden, and `J`/`K` already skip
   empty panels. If _no_ routines exist at all, show one panel with today's
   `No routines configured · a to add` placeholder.
3. **ADJUSTMENT — panel order: Service Procs → User → Plugin → Builtin.** This is a
   taste call, and reversing it is trivial. The reasons for this order:
   - The routines you own and act on come right after Service Procs, so `J` lands on
     them.
   - It reads as "most specific first", the reverse of config precedence (user
     overrides plugin, which overrides builtin).
   - The big builtin panel sits at the bottom, where it absorbs the spare rows. The
     height allocator keeps small panels whole and makes large ones scroll.
4. **ADJUSTMENT — compute the source in sase-core, not the TUI.** The routine inventory
   entry gets `source` and `declared_by` fields, and `sase axe routine list` shows them.
   This follows the Rust-core rule: the CLI and TUI must agree.
5. **ADDITION (recommended, can be dropped) — fold the builtin job rows by default.**
   - On first sight, builtin routines start with their job rows folded; user and plugin
     routines stay expanded.
   - Pair this with a new **failed-job count** on routine rows (`!N`), next to the
     existing `⚠N`.
   - Result: the builtin panel is 7 rows plus its border, and a broken job still shows
     on a folded routine and in the panel title (`!N`).
   - This changes the current "expanded on first sighting" default, so put it behind
     one config value in `default_config.yml`. An illustrative name:
     `ace.services_fold_builtin_jobs: true`.
6. **ADDITION — `H`/`L` act on the focused routine panel only.** Today they fold every
   routine. With separate panels, "fold all builtin job rows without touching mine" is
   the useful version. It matches the Agents tab, where `-` acts on one panel and `_`
   on all. Optional; the current global behavior is acceptable.
7. **FOLLOW-UP (separate repo) — sase-telegram should declare the `telegram` routine.**
   - It moves into the plugin's `default_config.yml`.
   - The bot username and chat id `env` stays in your user layer as a small override.
   - It then lands in the **Plugin** tier automatically.
   - The jobs already do nothing unless `~/.sase/telegram_is_enabled` exists, so a
     plugin-shipped routine is safe on machines where Telegram isn't enabled.
   - File this as a task bead in sase-telegram. It is not a prerequisite.
8. **NON-GOAL — splitting Service Procs by source.** It has 3 rows. Its detail pane and
   chips already show where each proc comes from.

---

## 5. Recommended design

### 5.1 Core (sase-core, then bump sase's `sase-core-revision.txt` pin)

- **New fields on each inventory entry:** `AxeInventoryEntryWire` (in
  `crates/sase_core/src/config/axe.rs`) gains `source: String` and
  `declared_by: String`.
  - Fill both for **routine** entries. Fill them for **job** entries too; that is cheap
    and lets the TUI mark a job you added under a builtin routine.
- **Computing them:**
  - `declared_by` is the label of the first layer, in composition order, where
    `raw_routine_value(layer, name)` (or, for a job, the job lookup already in
    `raw_contribution`) is `Some`.
  - `source` is `classify_source(layer.kind)`. Move service's `classify_source` into a
    shared config helper rather than duplicating it.
  - A generated job's `declared_by` should follow the job it was generated from.
- **Tests:**
  - A builtin routine you override in part stays `builtin`.
  - A routine declared in an overlay or local file is `user`.
  - A plugin routine that you give extra `env` stays `plugin`.
  - A job you add under a builtin routine is `user` while its routine stays `builtin`.
  - The legacy `lumberjacks:` key is classified the same as `routines:`.
- **No schema change is needed.** Nothing new is authored; the fields are derived.

### 5.2 Python plumbing

- `AxeInventoryEntry.from_wire` reads `source` and `declared_by`. Old bindings may lack
  them; the Rust-core-required decision means you can require them once the pin moves.
- `LumberjackConfig` / `ChopConfig` gain `source` and `declared_by`, filled in
  `load_axe_config` from the composition entries.
- `sase axe routine list` shows `hooks (builtin)`-style tags. Optionally add
  `--source builtin|plugin|user`, reading the `cli_rules.md` memory note before adding
  the option.

### 5.3 TUI (Services tab)

- **Panel keys:** `ServicesPanelKey = Literal["service_procs", "user_routines",
  "plugin_routines", "builtin_routines"]`, with `SERVICES_PANEL_ORDER` in that order.
- **Panel membership becomes data-driven.** `build_services_panel_index(items, *,
  routine_sources)` maps routine name → source, and places each `LumberjackItem` or
  `ChopItem` by its routine's source.
  - Keep the loud `TypeError` for unknown item classes.
  - Treat an unknown source string as a bug (raise) rather than silently landing it in
    User.
- **Required ordering invariant.** `_build_axe_items` must emit routine rows **grouped
  by source in panel order**, alphabetical within each group. Plain `j`/`k` is
  `current_idx ± 1` on the global list, so a panel's rows must be contiguous or `j`
  jumps between panels unpredictably. Today routines are sorted globally by name, so
  this is a real change. Add a test.
- **Layout.** In `_app_layout.py`, compose the four `BgCmdList`s statically with ids
  `#service-procs-panel`, `#user-routines-panel`, `#plugin-routines-panel`,
  `#builtin-routines-panel`.
  - Hide empty routine panels with `display = False`.
  - Retire `#scheduled-routines-panel`, as sase-17a retired `#bgcmd-list-panel`, so any
    stale reference fails loudly.
- **Rendering** (`_render_panels.py`):
  - Generalize `_axe_panel_widgets` to return all four panels.
  - Pass only the visible panels to `allocate_panel_heights`. The filler panel should be
    the last visible routine panel (normally Builtin).
  - Build the width calculation over the visible panels.
- **Titles** (`_panel_titles.py): `scheduled_routines_panel_stats` already takes
  `routine_names`, so call it once per source. Parametrize the title builder by label:

  ```text
  ◷ User Routines · 1 [R1] · 1 job
  ◷ Plugin Routines · 1 [R1] · 1 job
  ◷ Builtin Routines · 7 [R7] · 31 jobs !1 ⚠1 · scheduler stopped
  ```

  - Show the scheduler-state badge on the **top-most visible** routine panel only, not
    on every panel.
  - The Plugin panel's routine rows carry a dim plugin chip (`telegram · sase_telegram`)
    so B's benefit comes without B's cost.
- **Detail pane.** The routine and job detail gains a `Source: builtin (default)` line,
  worded the same way as service procs.
- **Folding (adjustments 5 and 6):**
  - On first sighting, a builtin routine's fold key starts collapsed when the config
    value is on.
  - `format_lumberjack_option` gains `failed_job_count`, computed from the already
    cached `_axe_chop_snapshots` with no extra I/O.
- **Add flow.** After `a` saves a new routine, it lands in **User**. Reuse
  `_axe_pending_selection` so the cursor follows it across panels.

Rough picture at 36 rows tall, with adjustment 5 on:

```text
╭ ⚙ Service Procs · 3 [R2 S1] ────────────╮
│▌[*] Gateway                               │
│▌[*] Scheduler                             │
│▌[-] Telegram Receiver  disabled by plugin │
╰───────────────────────────────────────────╯
╭ ◷ User Routines · 1 [R1] · 1 job ───────╮
│▌[*] telegram  812c                        │
│   └─ [·] tg_outbound                      │
╰───────────────────────────────────────────╯
╭ ◷ Builtin Routines · 7 [R7] · 31 jobs ──╮
│▌[*] checks  10c                           │
│▌[*] comments  46c                         │
│▌[*] external_mirror  4c                   │
│▌[*] hooks  388c                           │
│▌[*] housekeeping  1c                      │
│▌[*] usage                                 │
│▌[*] waits                                 │
╰───────────────────────────────────────────╯
```

This fits with no scrolling, where today it takes about 40 rows in a scrolling panel.

### 5.4 Other places that must change

- **Docs:** `docs/ace.md` ("Keybindings: Services Tab", "Sidebar Row Taxonomy", the
  Navigation table) and `docs/axe.md` (Services Tab Views, around lines 1385, 1650, and
  1667).
- **Other text:** the `axe_onboarding.py` copy; the comments in `styles.tcss` around
  line 5721; and the `scheduler` service-proc description in `default_config.yml`, which
  says jobs "appear in the Scheduled Routines panel".
- **Glossary strands:** `glossary:nav section` and `glossary:nav item` both name "the
  Service Procs and Scheduled Routines panels". These are memory files, so change them
  through `/sase_memory_write`.
- **Visual goldens:** every Services-tab golden changes. Regenerate with
  `just fix-tui-screenshots` through `/sase_monitor`, and inspect every group in the
  report.
- **`default_config.yml`:** add the new fold config value (adjustment 5). No keymap
  changes are needed, since `J`/`K`/`H`/`L` keep their bindings.

### 5.5 Proposed epic shape

| Phase | Scope | Size |
| --- | --- | --- |
| 1 | sase-core `source`/`declared_by` on inventory entries, plus tests. Python wire, config plumbing, CLI tag. Pin bump. | small–medium |
| 2 | Static source-tier panels: panel keys, index, ordering invariant, layout, heights and width, titles, detail-pane source line, docs, glossary, goldens | medium |
| 3 | Builtin job rows folded by default (config value), failed-job `!N` count, `H`/`L` scoped to the focused panel | small |
| — | (separate, sase-telegram) The plugin declares the `telegram` routine | small |

Phase 3 is independent and could land first on its own. It gives most of the space
savings even before any split.

---

## 6. When to revisit labels you write yourself (option C)

Add a `group:` key on routines, with an `ace.routine_groups.<key>` display config that
mirrors `ace.tribes`, **only when** at least one of these holds:

- You have **three or more** plugin or user routines that fall into two or more natural
  clusters (for example "comms", "backups", "reports").
- A plugin ships **several** routines that should appear apart from other plugins'
  routines.

When that happens:

- A label should only **split up** the User and Plugin tiers. Builtin routines always
  stay in Builtin, so config cannot make SASE's plumbing look like user work.
- Build dynamic panels by reusing the Agents tab's keyed mount/retire approach. Don't
  write a second implementation.
- Record the choice as a `decisions` memory record: why sources come first and labels
  second.

---

## 7. Risks and open questions

- **Panel order preference.** User-first versus builtin-first is a taste call (§4.3).
  It is trivial to flip, so settle it at plan review.
- **Hidden panels versus the `a` affordance.** With the User panel hidden when empty,
  "add a routine" is discoverable only through the `a` footer hint and the help modal.
  If that feels too hidden, keep User always visible with a
  `No user routines · a to add` placeholder, at the cost of 3 rows.
- **Jobs you add under builtin routines.** They stay in the Builtin panel, since panel
  membership follows the routine. The per-job `+user` chip made possible by the Phase 1
  job `declared_by` field makes them visible. Without it, they are easy to forget.
- **Projects whose local config declares routines.** Local declarations count as
  **User**. Confirm the scheduler actually honors project-local `axe.routines` (the TUI
  path does load the local layer). If it doesn't, a local routine could appear in the
  User panel without actually running. Check this before Phase 2.
- **Performance.** Source lookup is a dict built once per config load. Panel membership
  stays O(n) at item-list build time, and `j`/`k` remain O(1) widget updates within a
  panel (the `tui_perf.md` memory note applies). Nothing new touches the disk on the
  render path.

---

## 8. Recommended solution

Split **Scheduled Routines** into up to three **statically composed** nav sections, one
per routine's source, ordered **Service Procs → User Routines → Plugin Routines →
Builtin Routines**, with empty tiers hidden:

- **Source classification** comes from the declaring config layer, computed in
  **sase-core**. It reuses service procs' `builtin`/`plugin`/`user` rules and is exposed
  to both the TUI and `sase axe routine list`.
- **Builtin routines start with their job rows folded** (behind one config value). Each
  routine row carries a new `!N` failed-job count, so the plumbing stays quiet until it
  breaks.
- **Labels you write yourself** (tribe-style `group:`) wait until enough non-builtin
  routines exist to need them.
- **The sase-telegram plugin should declare its own `telegram` routine,** so it lands in
  the Plugin tier on its own.

This delivers what you asked for: builtin routines grouped together. It answers "how do
I group the others?" with a rule that needs no configuration and matches what you can
actually do to each routine. And it avoids the dynamic-panel machinery until a real set
of routines calls for it.
