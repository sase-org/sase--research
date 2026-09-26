# Grouping Scheduled Routines Into Services-Tab Nav Sections

_Consolidated report · lead researcher · 2026-09-26_
_Snapshots: sase `31ba8e4dd`, sase-core `9d049aa`_
_Inputs: `routine_source_nav_sections__{cdx,cld,grk,mus,gem}.md` (this directory), plus
the lead's own checks: code reads, `sase axe routine list`, `sase config layers`, and
live `sase screenshot` captures of the Services tab at 120x40 and 100x30._

## TL;DR

- **Yes, group them. Group by where each routine is declared.** Every routine comes
  from one config layer: SASE's builtin defaults, a plugin, or you (user config, a
  machine overlay, or a project-local file). That gives three fixed buckets:
  **Builtin**, **Plugin**, and **User**. This is how "the other routines" should be
  grouped. Service procs already use exactly this split (`source: builtin|plugin|user`
  plus `declared_by`, computed in sase-core).
- **Keep your "nav sections" wording: use real panels.** Researchers split 2–3 on this.
  Three of them wanted in-list dividers inside the one Scheduled Routines panel. I side
  with panels, for two reasons measured this turn:
  - On this machine, only one extra panel would ever show, because no installed plugin
    declares a routine. That costs 3 rows of chrome.
  - The dividers design those three proposed (builtin first) does not fix the actual
    problem. Your `telegram` routine would still sit below 38 builtin rows, off-screen
    at 120x40.
- **Keep the panels static and capped at three routine panels, and hide empty ones.**
  Do not build one panel per plugin or panels you label yourself. That would need the
  Agents tab's dynamic mount/retire machinery.
- **Compute each routine's source in sase-core, not the TUI.** I verified that Python
  cannot derive it. The only per-layer data the TUI gets covers writable layers, and
  the builtin and plugin layers are never writable.
- **Adjustments I'm making to your requirements** (all called out in §4):
  - A builtin routine you override stays builtin.
  - Panel order is User → Plugin → Builtin.
  - Labels you write yourself (a `group:` key) are deferred.
  - Builtin routines start folded, but only after routine rows can show failed jobs.

## 1. What exists today (verified)

**The sidebar.**

- The Services sidebar holds two statically composed `BgCmdList` panels,
  `#service-procs-panel` and `#scheduled-routines-panel` (`_app_layout.py`). They
  landed in epic sase-17a.
- All rows live in one global `_axe_items` list, which `build_services_panel_index`
  (`actions/axe_display/_panels.py`) splits into panels.
- Which panel a row goes to depends only on its **item class**. `SERVICES_PANEL_ORDER`
  is a fixed 2-tuple.
- The machinery mostly generalizes already:
  - `J`/`K` use `adjacent_nonempty_panel`, which skips empty panels.
  - `allocate_panel_heights` (`util/panel_heights.py`) takes any number of panels and
    already has `collapsed` flags.
  - When space overflows, the allocator gives the **smallest panels their natural
    height first**, and the large ones scroll.
- The hard-coded two-panel spots are:
  - `_render_panels.py:260-262`: `[False, False]` and `filler_idx=1`.
  - The two title builders.
  - The CSS aimed at the second panel.
  - Tests and goldens.

**Routine ordering and folds.**

- Routines are sorted alphabetically.
- Each routine's fold is expanded the first time it is seen (`_loader_items.py:170-188`).
- Fold state lives only in memory. A fresh `FoldStateManager` is created at startup
  (`_state_init_late.py:117`), so every TUI session starts fully expanded.
- Routine rows carry an overrun count (`⚠N`) but **no failed-job count**.

**Live inventory** (`sase axe routine list`, `sase config layers`):

| Routine | Declared by | Jobs |
|---|---|---:|
| `checks`, `comments`, `external_mirror`, `hooks`, `housekeeping`, `usage`, `waits` | builtin (`default`) | 31 total (`external_mirror` generates one job per project) |
| `telegram` | user (`~/.config/sase/sase.yml`) | 1 |

- **No plugin declares any `axe` routine.** `plugin:sase_telegram` contributes only
  `service` (the `telegram_receiver` proc, `enabled: false`). `plugin:sase_github`
  contributes only `xprompts`.
- The Plugin bucket is therefore empty on this machine today.

**What you see right now** (live screenshots):

- At **120x40**, the Scheduled Routines panel (`8 [R8] · 32 jobs`) shows about 28 of
  its 40 rows. The list ends inside `housekeeping`, and **`telegram` is off-screen.**
- At **100x30**, about 18 routine rows are visible.
- Service Procs uses 5 rows.
- The detail pane already shows `Source: builtin (default)` for service procs.

**Where a routine comes from: the data available today.**

- **No origin field exists.** `AxeInventoryEntryWire` (sase-core
  `config/axe.rs:113-127`) has no `source` or `declared_by`.
- **`contributions` cannot supply it.** They come from `writable_contributions`, which
  filters on `layer.writable` (`axe.rs:1992-1998`), and the builtin and plugin layers
  are never writable (`config/inventory.py:116`).
- **`field_provenance` cannot supply it either.** It records the last layer that wrote
  each field.
- **The pattern to copy already exists.** Service procs set `source` and `declared_by`
  when an entry is first inserted, via `classify_source` in `service/config.rs:118`
  (overlay and local count as `user`). Later layers still override individual fields
  without changing the source.
- **The TUI has no grouping model for this tab yet.** The shared grouping mixin is a
  deliberate no-op on Services ("AXE has no grouping model", `agents/_grouping.py:10`).

## 2. Disagreements and how I resolved them

| Question | cdx | cld | grk | mus | gem | Resolution |
|---|---|---|---|---|---|---|
| Panels or in-list dividers? | panels | panels | dividers (a panel later) | collapsible banners | dividers | **Panels**, static, capped, empty ones hidden |
| What to group by | source | source | source | function (`group:`) | function (`category:`) | **Source** |
| Where source is computed | Rust | Rust | Python, from `contributions` | Rust (for `group:`) | Python table / schema | **Rust**; grk's Python route is impossible |
| Panel order | Builtin first | User first | — | — | — | **User → Plugin → Builtin** (taste call) |
| Start builtin routines folded? | no (hides failures) | yes | fold 2 big routines | fold housekeeping (optional) | — | **Yes, but only after a failed-job count exists** |
| Your own labels now? | defer | defer | defer | yes | yes | **Defer** |

### 2.1 Panels versus dividers

The divider camp (grk, mus, gem) makes four good points:

- The glossary says dividers are not nav sections.
- The `── oneshots ──` divider is a precedent on this very tab.
- Every panel costs a border and a separator.
- An open-ended number of panels would need dynamic mounting.

They lose on the facts, for five reasons:

1. **You asked for nav sections.** That is a project term with a precise meaning (a
   whole panel). Replacing it needs a strong reason, and the cost is small.
2. **The cost is 3 rows per visible extra panel** (2 border rows plus 1 separator, per
   `allocate_panel_heights`).
   - With the Plugin panel hidden when empty, today's real layout adds exactly one
     panel.
   - gem's table (4 panels, 11 rows of chrome, "unusable at 24 rows", "Tab/Shift-Tab
     cycle panels") describes a layout nobody is proposing. Its key claim is also wrong:
     `Tab` switches TUI tabs, and `J`/`K` jump between panels.
3. **Dividers in grk's order don't fix the problem.** They emit builtin first and
   custom after, so `telegram` stays about 38 rows down.
4. **Panels guarantee the small group stays visible, whatever the order.** When space
   overflows, the allocator gives the smallest panels their full height first.
5. **Panels add things a divider cannot:**
   - A title per group (for example, "is any of SASE's own plumbing failing?" answered
     in one glance).
   - `J`/`K` stops.
   - An independent scroll viewport per group.

The oneshot precedent does not carry over. Oneshots are transient command history
tucked under a 3-row daemon list. Routine groups are persistent sets you navigate to.

What the divider camp gets right, and this plan keeps:

- Cap the set of panels.
- Hide empty panels.
- Don't copy the Agents tab's dynamic machinery.
- Update the glossary.

**If you decide panels cost too much**, the correct cheap fallback is dividers with
**User first**, not builtin first. That fixes visibility by order alone. You lose only
the per-group titles and the `J`/`K` stops.

### 2.2 Group by source, not by function

mus and gem argue that "builtin" lumps a 5-second lane (`hooks`) together with hourly
cleanup (`housekeeping`). That's true, but grouping by function is the wrong fix:

- **Routines already are the functional grouping.** Each routine is one lane of related
  jobs with its own interval, and the defaults' descriptions say so ("Fast lane…";
  slower polling "belongs in the other lanes"). Grouping 7–8 lanes into super-lanes
  adds a third level of hierarchy over very little data.
- **The two function-first researchers disagree with each other.** For the same 7
  routines:
  - `checks` is "polling" for mus but "system" for gem.
  - `comments` and `external_mirror` are "polling" for mus but "integrations" for gem.

  A taxonomy two careful readers can't agree on will not survive users classifying
  their own routines.
- **A function key costs more than it seems.**
  - A new routine key means a sase-core schema change, because the schema is
    `additionalProperties: false` and validated fail-closed.
  - Every author then has to classify their routines.
  - The set of groups is open-ended, which again means dynamic panels.
- **Source is free and stable.**
  - It is derived from config you already have, and it never changes when you edit a
    field.
  - It uses the same words the service-proc rows and detail pane already use.
  - It matches a real difference in what you can do:
    - Builtin and plugin routines can only be overridden field by field; you cannot
      delete them.
    - Routines you declare are yours to edit or delete.

The cadence concern is about **ordering within a group**, not grouping. See §4 item 7.

### 2.3 Where source is computed

grk said Python could derive origin from `AxeInventoryEntry.contributions`. It cannot,
for the writable-only reason in §1. The other routes don't work either:

- **Field provenance** fails once a user overrides every field of a routine.
- **Checking the name against `default_config.yml`** is a heuristic that plugins break.

Source also passes the Rust-boundary test: `sase axe routine list` and the TUI must
agree. So:

- sase-core gains the fields.
- sase's `sase-core-revision.txt` pin moves past that commit.

### 2.4 Folding builtin routines by default

cld is right that splitting alone won't stop scrolling. The Builtin group alone is
7 routines and 31 jobs, about 38 rows, which still overflows at 120x40. Because folds
reset every session, a first-sighting default applies every time the TUI starts.

cdx is also right that folding hides failures. A folded routine row shows `⚠N`
overruns, but not failed jobs.

The two points are compatible if the work is ordered:

1. First, add a failed-job count (`!N`) to routine rows.
2. Then start builtin routines folded, behind one config value.

Once that ships, the Builtin panel is 7 rows plus its border, and a failure still shows
on the row and in the panel title.

## 3. Critique of the plan

**It is a good idea.** The seven builtin routines are SASE's own plumbing; you act on
them when they break. Mixing them alphabetically with routines you wrote hides yours and
takes up the space. The screenshot shows this concretely: your one routine is
off-screen.

**What the plan leaves unspecified:**

1. **What "builtin" means.** Three readings are possible:
   - (a) the name ships in `default_config.yml`;
   - (b) every effective field comes from defaults;
   - (c) the builtin layer declared it first.

   Only (c) is stable. Under (b), changing `hooks.interval` would move `hooks` out of
   the builtin panel, and resetting the override would move it back, mid-navigation.
2. **"How do I group the others?" is the decision that sets the cost.**
   - Groups derived from data form a small fixed set, so the panels can stay static
     (cheap).
   - Labels you write form an open-ended set, so the panels must be dynamic (about the
     cost of the Agents tribe panels).
   - Answer the question now, with source, rather than leaving it for later.
3. **There is almost nothing to group yet.** One routine is not builtin. That argues
   for the derived rule, not a labelling system; see the `corpus-before-mechanism`
   decision record.
4. **Declaring layer is not the same as owning package.** `telegram` is conceptually
   the sase-telegram plugin's routine: its job scripts ship with the plugin. It lives
   in your user config only because nobody moved it.
   - Grouping by source will show it as **User**. That is accurate about the config,
     but semantically it belongs to the plugin.
   - Fix the data rather than the label; see §6, "Separate follow-up".
5. **Splitting divides the panel-title stats.** Counts become per group, but health of
   the scheduler itself must render once. Don't repeat `scheduler stopped` on every
   routine panel.
6. **Row order within a panel must stay contiguous.** Plain `j`/`k` moves by ±1 on the
   global item list. Each panel's rows therefore have to be emitted as one contiguous
   run, in panel order. Today's global alphabetical sort breaks this, so it's a real
   change and needs a test.

## 4. Adjusted requirements (deliberate changes, called out)

1. **CHANGED: "builtin" means first declared by the builtin layer.** Overrides never
   move a routine to another panel. The same holds for plugin routines you override.
2. **ANSWERED: the other routines are grouped by source too.** They split into Plugin
   and User, with service procs' rules: `user`, `overlay:*`, and `local` all count as
   User.
3. **CONSTRAINED: a fixed set of panels.** Service Procs plus at most three routine
   panels.
   - An empty routine panel is hidden, and `J`/`K` already skip it.
   - If there are no routines at all, show one panel with today's placeholder,
     `No routines configured · a to add`.
4. **CHOSEN: panel order is Service Procs → User → Plugin → Builtin.** This is a taste
   call and trivial to flip. The reasons for this order:
   - The routines you own come first.
   - It reads most-specific first, the reverse of config precedence.
   - The largest panel sits last, where it absorbs spare rows. The rule is simply "the
     filler is the last visible panel".
5. **CHANGED: jobs always stay with their parent routine's panel.** A job you add under
   a builtin routine stays in Builtin, and gets a `user` chip from the job-level
   `declared_by`.
6. **DEFERRED: labels you write yourself** (`group:` on routines, or `ace.routine_groups`
   display config like `ace.tribes`). Revisit only when you have three or more non-builtin
   routines that form natural clusters, or a plugin ships several routines. Even then:
   - A label may only **subdivide** the User or Plugin tier.
   - Builtin routines always stay in Builtin.
   - Put labels in presentation config, not the scheduler's execution config.
7. **KEPT: alphabetical order within each group.** grk's interval-first order for
   builtins is defensible (it puts `hooks` and `waits` on top). But an interval
   override would reorder rows, and alphabetical order is predictable. Reconsider
   after the folding default ships.
8. **ADDED (phase 3): a failed-job count `!N` on routine rows, then builtin routines
   start folded** behind one `default_config.yml` value. Folding waits for the count;
   see §2.4.
9. **ADDED: source is visible outside the grouping.**
   - The routine and job detail panes get `Source: builtin (default)` (same wording as
     service procs).
   - `sase axe routine list` shows a source tag.
10. **NON-GOALS:**
    - Splitting Service Procs by source (3 rows, and it already shows provenance
      chips).
    - Grouping by status or cadence.
    - A grouped/ungrouped toggle.
    - One panel per plugin (use a dim `plugin <name>` chip on rows in the Plugin panel
      instead).

## 5. Alternatives rejected

| Option | Why not |
|---|---|
| Dividers inside the one panel | Cheapest. No `J`/`K` stops, no per-group titles or viewport. In builtin-first order it leaves the observed bug. Acceptable fallback **only** with User first. |
| Two buckets (Builtin + Custom) | Simplest honest split. Merges "yours to delete" with "override only". Three buckets cost almost the same. Fine if you prefer fewer words. |
| Functional groups (`group:`/`category:`) | Subjective (the two researchers disagree), needs a schema key, is open-ended, and adds a layer on top of lanes. |
| One panel per plugin or config layer | Too many panels; leaks overlay filenames into navigation; zero plugins declare routines today. |
| Group by status (running/error/idle) | Rows would move on every refresh; status already appears in title chips and row markers. |
| Group by cadence band | Each routine already is a cadence lane; thresholds go stale. |
| Filter/scope bar | Hides rows instead of grouping them. Could complement groups later. |

## 6. Recommended design

**Phase 1: core contract (sase-core, then the pin bump in sase).**

- Add `source` and `declared_by` to `AxeInventoryEntryWire` for routine **and** job
  entries.
- `declared_by` is the first layer, in composition order, whose raw value for that
  routine or job is `Some`. For a routine, use `raw_routine_value`; for a job, use the
  job lookup in `raw_contribution`. Both must honor the public (`routines`/`jobs`) and
  legacy (`lumberjacks`/`chops`) spellings.
- A generated job's `declared_by` follows the job it was generated from.
- `source` comes from `classify_source`. Move that function out of `service/config.rs`
  into a shared config helper instead of copying it.
- **Tests:**
  - A builtin routine with one field overridden stays `builtin`, even though that
    field's provenance points to `user`.
  - A routine declared in an overlay or local file is `user`.
  - A plugin routine you override stays `plugin`.
  - A job you add under a builtin routine is `user`, while its routine stays `builtin`.
  - Legacy and public spellings classify the same.
  - Generated jobs inherit their source.
- **Python side:**
  - `AxeInventoryEntry.from_wire` reads both fields and validates `source` against a
    `Literal`. The TUI's panel lookup can then cover every case without a fallback
    branch; the Rust-core-required decision means no fallback for old bindings.
  - Carry the fields onto the routine and job config records.
  - Add the source tag to `sase axe routine list`. Read the `cli_rules` memory note
    before adding any `--source` filter.
  - Add the detail-pane `Source:` line.

**Phase 2: static source panels (TUI).**

- **Panel keys:** `service_procs`, `user_routines`, `plugin_routines`,
  `builtin_routines`.
  - Compose the four panels statically.
  - Retire `#scheduled-routines-panel` so any stale reference fails loudly.
  - Hide empty routine panels with `display = False`.
- **One owner for the visible panel order.** The panel index derives the visible order
  once (fixed order plus nonempty slices). Paint, focus, `J`/`K`, titles, heights,
  width settling, and click-to-row translation all consume it. None of them filter on
  their own.
- **Panel membership:**
  - A routine goes by its cached `routine → source` map.
  - A job follows its parent routine.
  - An unknown item class still raises `TypeError`.
- **`_build_axe_items`** emits rows grouped by panel order, alphabetical within each
  group, with jobs right after their routine. Add a test for this.
- **Caching:** build the `routine → source` map in the existing off-thread collector,
  next to `_axe_lumberjack_names`. It must refresh on `current_config_token()`. No
  layer walks or disk I/O in render, highlight, click, or timer callbacks.
- **Heights:** pass only the visible panels to `allocate_panel_heights`, with the
  filler set to the last visible panel. Set the margin between panels by class, not by
  panel id.
- **Titles:** call `scheduled_routines_panel_stats` once per group.
  - Show the scheduler badge only on the top-most visible routine panel.
  - Pluralize `job` correctly.
- **Add flow:** a routine created with `a` lands in User, and the cursor follows it via
  `_axe_pending_selection`.
- **Docs and memory:**
  - Update `docs/ace.md` ("two stacked panels", the Sidebar Row Taxonomy, the
    `x`-no-op sentence) and `docs/axe.md` (around lines 1385, 1650, 1667).
  - Update the `styles.tcss` comment near line 5721 and the `axe_onboarding.py` copy.
  - Update the glossary strands `nav-section` and `nav-item`. They are memory files, so
    change them through `/sase_memory_write`.
  - Optionally add a `decisions` record: "routine sections follow the declaring source;
    labels only subdivide, later".
- **Acceptance criteria:**
  - `j`/`k` crosses panel boundaries without stopping on chrome.
  - `J`/`K` wrap and skip hidden panels.
  - `Ctrl+O` still returns to where you jumped from.
  - Clicks map to the right row in every panel.
  - Folding keeps the selection by row identity.
  - A refresh that changes fields but not the declaring layer moves nothing.
  - A new routine appears in the right panel without stealing focus.
  - Same-panel highlighting stays O(1) with no disk I/O.
- **Visual goldens:** regenerate with `just fix-tui-screenshots` through `/sase_monitor`.
  Cover:
  - Builtin + User at 120x40.
  - All three routine panels.
  - Builtin only.
  - 70x36.

**Phase 3: density (can land independently, before or after phase 2).**

- Compute a `!N` failed-job count on routine rows from the already cached
  `_axe_chop_snapshots`.
- Start builtin routines folded on first sighting, behind one `default_config.yml`
  value (illustrative name: `ace.services_fold_builtin_routines`).
- Optional: scope `H`/`L` to the focused routine panel, like the Agents tab's `-`
  (one panel) versus `_` (all panels).
- Optional: whole-panel collapse for Services panels. The allocator's `collapsed` flags
  already support it. Check key conflicts in `default_config.yml` first.

**Separate follow-up (sase-telegram): the plugin should declare the `telegram`
routine.**

- The plugin ships the routine in its `default_config.yml`.
- Your user layer keeps only the `env` (bot username and chat id).
- The routine then lands in the Plugin tier on its own.
- Weigh one cost first: the routine would then tick every 5 seconds on every machine
  with the plugin installed. The jobs no-op without `~/.sase/telegram_is_enabled`, but
  the process still spawns.
- This is not a prerequisite. Before filing it, use `/sase_new_task`.

Sketch at 120x40 with all three phases:

```text
╭ ⚙ Service Procs · 3 [R2 S1] ──────────────╮
│▌[*] Gateway                                 │
│▌[*] Scheduler                               │
│▌[-] Telegram Receiver  disabled by plugin   │
╰─────────────────────────────────────────────╯
╭ ◷ User Routines · 1 [R1] · 1 job ─────────╮
│▌[*] telegram                                │
│   └─ [·] tg_outbound                        │
╰─────────────────────────────────────────────╯
╭ ◷ Builtin Routines · 7 [R7] · 31 jobs ────╮
│▌[*] checks  18c                             │
│▌[*] comments  85c                           │
│▌[*] external_mirror  6c                     │
│▌[*] hooks  710c                             │
│▌[*] housekeeping  2c  !1                    │
│▌[*] usage                                   │
│▌[*] waits                                   │
╰─────────────────────────────────────────────╯
```

Without phase 3, the Builtin panel still scrolls, but the User panel stays whole.

## 7. Risks and open questions

- **Panel order** (§4 item 4) is a taste call. Settle it at plan review.
- **Hidden User panel.** When the User panel is empty and hidden, adding a routine is
  discoverable only through the `a` footer hint and the help modal. If that feels too
  hidden, keep User always visible with a placeholder, at a cost of 3 rows.
- **Project-local routines.** Routines declared in a local file classify as User.
  Confirm whether the scheduler and the TUI actually load local `axe.routines` the same
  way. If the TUI shows a local routine the scheduler never runs, the User panel would
  mislead. Settle this in phase 1.
- **Wire change across repos.** Land the sase-core commit first, move the pin, then
  land the Python callers.
- **Golden churn.** Every Services golden changes in phase 2. Review each group in the
  report rather than bulk-accepting.

## Recommended solution

Split **Scheduled Routines** into up to three **statically composed nav sections**,
ordered **Service Procs → User Routines → Plugin Routines → Builtin Routines**, with
empty routine sections hidden:

- **Placement rule.** A routine's section is its declaring source: the first config
  layer that introduced it. sase-core computes this as new `source` and `declared_by`
  fields, modeled on service procs and exposed to both the TUI and
  `sase axe routine list`. User overrides never move a routine, and jobs stay with
  their routine.
- **What stays the same.** The global row list, row identity, `j`/`k`, `J`/`K`, click
  handling, and folding all keep working. Only panel membership, the visible panel
  order, titles, and height allocation are generalized.
- **Then shrink the plumbing.** Add a failed-job `!N` count to routine rows, then start
  builtin routines folded, so the Builtin panel stays quiet until something breaks.
- **Defer your own labels** until enough non-builtin routines exist to need them. When
  they come, they only subdivide the User and Plugin tiers.
- **Consider moving the `telegram` routine into the sase-telegram plugin** so it lands
  in the Plugin tier on its own.
