# Grouping scheduled routines on the Services tab

Researcher: mus (independent swarm report, `__mus` suffix).
Question: the requester wants sets of scheduled routines grouped in different
nav sections — e.g. all builtin routines together — and asks whether the plan
is good, how to group the non-builtin routines, and what the best
implementation would be.

## TL;DR

- The literal plan (one nav section per routine group) is implementable but I
  do not recommend it as stated. A nav section is a whole panel, and every new
  panel pays for itself in layout, navigation, titles, and tests.
- The cheaper mechanism the codebase already prefers for exactly this shape is
  **collapsible in-panel grouping inside the single Scheduled Routines panel**
  (precedent: the `── oneshots ──` divider, per-routine fold keys,
  Agents-tab group banners).
- I also recommend against a single "all builtins" grab-bag group: the seven
  shipped routines span 5-second lifecycle reconciliation and hourly cleanup,
  so "builtin" hides the axis (cadence/function) that actually helps an
  operator scan the list.
- Recommended solution: an optional per-routine `group:` key, functional
  default groups for the shipped routines, one `custom` catch-all for
  ungrouped user routines, rendered as collapsible banners in the existing
  panel. Details in §5.

## 1. Current state (verified in-tree)

### 1.1 What "routine" and "nav section" mean here

- A **routine** is an independently supervised scheduler process running its
  configured jobs on a fixed interval (`sase/memory/glossary/lumberjack.md`;
  `Lumberjack` survives only as a lookup alias, code, and legacy state-path
  spelling). Public contract is routine/job; `axe_routine_job_contract` is a
  sunset flag, on by default (`docs/axe.md`, compatibility-aliases table).
- A **nav section is one whole panel** in the left nav column. On the Services
  tab there are exactly two: Service Procs and Scheduled Routines
  (`sase/memory/glossary/nav-section.md`). Grouping banners, in-list headers,
  and the `── oneshots ──` divider are explicitly *not* nav sections. So
  "grouping in different nav sections" literally means adding more panels,
  not adding headers inside the existing panel.

### 1.2 The shipped routine inventory

All seven default routines ship in `src/sase/default_config.yml` under
`axe.routines` (no other routine source exists in the default install):

| routine | interval | character |
|---|---|---|
| `hooks` | 5s | latency-sensitive Patch lifecycle (hook/mentor/workflow checks, zombie marking, suffix repair, claim release) |
| `waits` | 10s | agent wait dependencies, bead claims, sidecar sync, epic flush |
| `checks` | 5min | slow PR-submission checks, bead triage gates, plugin gates |
| `usage` | 60s | subscription-usage window refresh (inline, no procs) |
| `external_mirror` | 15min | external issue/PR mirroring per project |
| `comments` | 60s | launch background critique-comment checks |
| `housekeeping` | 1hr | error digests, store compaction, tmp/proc sweeping, retention previews |

Two facts matter for the proposal. First, **there is no builtin/user marker
on any routine**: `LumberjackConfig` (`src/sase/axe/_config_types.py`,
`src/sase/axe/_config_targets.py`) carries name, description, interval,
timeouts, and jobs — no `group`/`section`/`category`/`tag`, no origin flag.
"Builtin" today can only mean "a name that ships in `default_config.yml`",
which is a name-list heuristic, not a first-class property. Second, layer
composition (which layer defined what) is owned by the **Rust core**
(`compose_axe_config` via `src/sase/axe/config_backend.py`; per-chop
provenance is threaded through `parse_lumberjacks`), so any grouping that
depends on config origin crosses the Rust boundary (§4.3 of the task's repo
rules: shared behavior belongs in `sase-core`, TUI rendering stays here).

### 1.3 How the Services sidebar is built today

- Layout (`src/sase/ace/tui/_app_layout.py`): `#bgcmd-list-container` holds
  exactly two `BgCmdList` widgets (`service-procs-panel`,
  `scheduled-routines-panel`).
- One flat global `_axe_items` list preserves row identity; each panel
  renders a slice computed by `build_services_panel_index`
  (`src/sase/ace/tui/actions/axe_display/_panels.py`). Membership is by item
  class name (`LumberjackItem`/`ChopItem` → routines panel); unknown classes
  raise `TypeError` loudly.
- Rows are built in `_loader_items.py`: routines in **sorted name order**,
  each followed by its jobs when its `lumberjack:<name>` fold is expanded
  (first sighting defaults to expanded).
- Panel chrome: per-panel border titles with count chips
  (`_panel_titles.py`), height sharing via `allocate_panel_heights` over
  `rendered_line_count` (`_render_panels.py`), `J`/`K` cross-panel jumps with
  wrap and empty-skip (`_panel_navigation.py`), identity-preserving selection
  restore, and a jump-all modal over the same flat list.
- Direct precedent for grouping *without* a new panel: oneshot rows render
  under a `── oneshots ──` divider inside Service Procs
  (`src/sase/ace/tui/widgets/bgcmd_list.py`, `show_bgcmd_divider`).
- Direct precedent for *refusing* grouping here: the Agents/Artifacts
  grouping mixin is a documented silent no-op on the Services tab —
  "AXE has no grouping model"
  (`src/sase/ace/tui/actions/agents/_grouping.py`). Any proposal adds the
  first grouping model this tab has ever had.

## 2. Critique of the plan as stated

**Is it a good idea?** The underlying itch is real: seven routines expanding
to ~30 job rows is already a long panel, and user routines drown among
shipped ones. But the plan as stated has three weaknesses:

1. **"Builtin" is the wrong grouping axis.** The shipped set mixes a 5s fast
   lane (`hooks`), 10–60s coordination (`waits`, `usage`, `comments`),
   5–15min polling (`checks`, `external_mirror`), and 1hr maintenance
   (`housekeeping`). Collapsing them into one "builtin" banner groups the
   two things an operator checks most often (lifecycle + errors) with the
   thing they check least (hourly sweeping). Cadence/function is the axis
   that matches how the defaults' own descriptions are written ("Put
   latency-sensitive reconciliation here; slower polling belongs in the other
   lanes" — `hooks` description). Origin is useful for *default placement*,
   not as the visible taxonomy.
2. **"Different nav sections" overpays.** Each new panel duplicates: a
   `BgCmdList` instance and layout slot, a `SERVICES_PANEL_ORDER` entry and
   partition rule, title-stats builder, height-allocation share, `J`/`K` stop
   behavior, focused-panel bookkeeping, jump-modal entries, and coverage in
   `test_services_panels.py`, `test_axe_panels.py`,
   `test_services_panel_heights.py`, `test_services_panel_titles.py`, plus
   visual-snapshot fixtures. Panels are the right unit when groups need
   distinct title stats or independent scrolling focus (Service Procs vs
   Routines genuinely differ). Routine groups do not.
3. **"I'm not sure how to group the others" is the load-bearing gap.**
   Without a default-placement rule for user routines, any implementation
   either strands them in a miscellaneous bucket (recreating today's
   problem) or forces every user author to opt into a taxonomy they did not
   ask for. The proposal needs an explicit answer here, not a follow-up.

## 3. Options considered

**A. One nav section (panel) per group.** Literal reading. Pros: strongest
visual separation, per-group title chips, `J`/`K` stops per group. Cons:
full cost list in §2.2; N=1 groups render a panel with a single routine
(the likely fate of a user's first custom routine); vertical space fragments
as each panel keeps its own border and minimum height. Reject as the
default; keep in reserve only if per-group title stats ever become a
requirement.

**B. Collapsible group banners inside the Scheduled Routines panel
(recommended shape).** One panel stays one nav section; groups render like
the Agents tab's tribe banners / the oneshots divider, collapsible through
the existing `FoldStateManager` (new keys `routine-group:<name>` alongside
`lumberjack:<name>`). Pros: no layout, navigation, or title-stats surgery;
graceful N=1 (a banner with one routine, not a whole panel); fold state
already has persistence patterns to copy. Cons: no per-group title chips
(mitigate: routine/job counts inline in the banner text); slightly more
complex `_append_lumberjack_items`. This is the right cost level for the
problem size (~7 shipped routines + a handful of custom ones).

**C. Provenance-derived builtin/custom split, no config key.** Group by
which config layer defined the routine (default layer → "shipped", anything
else → "custom"). Pros: zero user configuration; directly answers "group the
others". Cons: crosses into Rust composition work for a two-bucket taxonomy
that §2.1 already argues is the wrong visible axis; brittle around overrides
(a user who tweaks one field of `hooks` arguably now owns it — which bucket
does it render in?). Reject as the *visible* taxonomy; provenance may still
inform *default placement* (see §5).

**D. Fixed functional groups hardcoded in the TUI.** E.g. fast-lane /
polling / maintenance buckets by interval threshold. Pros: no schema change.
Cons: thresholds rot (a user routine at 30s is which lane?); hardcodes
policy in the presentation layer, violating the Rust-boundary litmus test
(any CLI or second frontend would want the same grouping). Reject; if
cadence ever drives grouping, the mapping belongs in config, not the
widget.

## 4. How to group the non-builtin routines

Three sub-problems, each with an answer:

1. **Default placement without user effort.** Every routine without an
   explicit group renders in a single `custom` (or `other`) group at the
   bottom, in today's sorted-name order. No strandings, no forced taxonomy.
2. **Opt-in taxonomy.** An optional `group: <name>` key per routine lets
   authors place routines into shipped groups or invent their own. Group
   ordering rule must be specified: config-first-seen order for grouped
   routines, `custom` last (documented in `docs/axe.md` + JSON schema
   `src/sase/config/sase.schema.json`).
3. **What the shipped routines default to.** Not one `builtin` bucket (per
   §2.1) but functional defaults matching their documented lane semantics:
   `hooks`+`waits` → fast lane; `usage`+`comments`+`checks`+`external_mirror`
   → polling; `housekeeping` → maintenance. Exact names are bikesheddable;
   the point is that the defaults teach the taxonomy, so a user adding a
   30s reconciliation routine can see where it belongs.

## 5. Recommended solution

**Render groups as collapsible banners in the existing Scheduled Routines
panel (Option B), driven by an optional `group:` key with functional
shipped defaults and a `custom` catch-all (§4).**

Concrete work items:

1. **Config (crosses the Rust boundary).** Add optional `group: <string>`
   to the routine schema; default it per-routine in `default_config.yml`
   using the three functional groups from §4.3; validate (non-empty,
   reasonable length) in the Rust composition with diagnostics following the
   existing `AxeConfigDiagnostic` pattern. Move the
   `sase-core-revision.txt` pin past the core commit, per repo rules.
   *Adjustment called out:* this adds a schema key the request did not name;
   without it there is no durable, frontend-independent notion of a group,
   and a TUI-only name-list heuristic for "builtin" would rot.
2. **TUI items.** Extend `_append_lumberjack_items` to emit group banners
   and honor `routine-group:<name>` fold keys (default expanded; persist
   like routine folds). Keep the flat `_axe_items` + partition-index
   architecture untouched — banners are chrome within the routines slice,
   exactly like the oneshots divider, so `_panels.py`, `_panel_navigation.py`,
   heights, titles, and selection-restore keep working unchanged.
   *Adjustment called out:* groups are **not** new nav sections despite the
   request's wording; the glossary reserves that term for whole panels, and
   the cost/benefit (§2.2) favors banners at this scale. If per-group stats
   later demand panels, the `group:` key transfers unchanged.
3. **Docs + schema.** Document `group`, group order, and the `custom`
   catch-all in `docs/axe.md` (Services Tab Views) and `docs/ace.md`
   (sidebar taxonomy), plus the JSON schema description.
4. **Tests.** Extend `test_services_panels.py` (banner emission/order),
   `test_axe_panels.py`, title/height suites (unchanged-behavior guards),
   and one visual-snapshot case for a collapsed group. Do not narrow or skip
   existing suites.
5. **Explicit non-goals for v1.** No per-group title chips (banner inline
   counts only); no grouping cycle key (`g`-style mode cycling stays
   Agents/Artifacts-only); no migration of legacy `lumberjack:` state paths;
   no CLI grouping flags until the TUI behavior settles.

## 6. Risks and open questions

- **Name bikeshed:** `group` vs `section` vs `lane`. `lane` matches the
  defaults' own vocabulary ("the other lanes"); `group` matches the
  requester's. Either is fine — pick one and put it in the schema.
- **Routine-level provenance** (whether the Rust composition can report
  "this routine came from the default layer" for smarter defaults) was
  verified for chops, not routines; confirm in the `sase-core` checkout
  before promising provenance-based defaults. The recommendation does not
  depend on it.
- If the operator's real complaint turns out to be panel *length* rather
  than *findability*, a cheaper first step exists within current
  architecture: default-collapse `housekeeping` jobs (8 rows rarely
  inspected) and document routine folding. Worth asking before building.
