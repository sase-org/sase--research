---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
tags:
  - ace
  - tui
  - updates
  - ux
---

# One Updates Tab: Consolidated Research And Recommendation

**Research question:** merge the SASE Admin Center **Updates** tab's three sub-tabs —
Core, Plugins, Agent CLIs — into one excellent view that keeps every capability of all
three. What is the correct UX, and how should it be built?

**Answer in one sentence:** replace the sub-tabs with **one master/detail inventory —
sections by domain, a cycled scope filter (Outdated / Installed / All) on the existing
`]`/`[` keys, capabilities carried on the row instead of the hidden active-sub-tab
variable, and every existing keybinding and action path kept exactly as-is** — which
ships the entire UX win with no feature flag, no keymap deprecation, and no re-opened
epic. Full design in §4; sequence in §6.

## Provenance

Three research documents preceded this one, and this report supersedes all three as the
actionable summary:

| File | Author round | Position |
| --- | --- | --- |
| `202609/admin_center_updates_tab_unification.md` | earliest | Scope filter + verb collapse (`Space`/`Enter`/`u`) + route `u` through `ComprehensiveUpdateRequest` |
| `updates_tab_unified_inventory__a.md` | researcher A | "Needs action" promoted section + token filter dialect + keep verbs explicit + adaptive narrow layout |
| `updates_tab_unified_inventory__b.md` | researcher B | Adjudication of the two above: take the first doc's structure and scoping, doc A's restraint about mutations, reject the comprehensive-update rewiring |

(Researcher B's internal "Doc A" is `__a` here; its "Doc B" is the earliest doc, which
remains at the month-directory root.)

For this consolidation I independently re-verified every load-bearing claim at `sase`
master `58d3ed746`: the `sase-r1` bead record and commit `f1914962c`, the cited pane
code, the two squeeze comments, the bench and PNG-suite inventory, the
`docs/ace.md:6543` snapshot-gating sentence, and — through the audited memory path —
the `tui_perf.md` rule-12 and `sase_flags.md` sunset-flag quotes. **All of researcher
B's citations check out**, and my own verification closed the one gap in its
adjudication (§3.1, manual-only updates). The recommendation below is researcher B's
design, confirmed, with researcher A's acceptance criteria and test scenarios restored
and one invariant added.

---

## 1. The settled foundation

All three documents agree, and the code confirms: **the three sub-tabs are a
presentation seam over a single data seam.**

- One threaded worker already loads all three sources into one `PluginsLoadResult`
  (`src/sase/ace/tui/modals/plugins_browser_loading.py:99`), and `UpdateStatus`
  (`src/sase/updates/status.py:96`) is already the aggregate across host/core/plugin
  `components` plus agent-CLI `provider_candidates`. Merging costs no extra I/O and
  deletes widgets.
- The cardinalities are wildly asymmetric and mostly permanent. Core is hard-coded at
  exactly two rows (`_CORE_PACKAGES`, `src/sase/uv_tool/versions.py:38`); Agent CLIs is
  registry-bounded (~7); installed plugins are a handful. Only the plugin *catalog* is
  unbounded (GitHub topic search; benched to 2,000 entries with a 16 ms p95 budget —
  `CATALOG_SCALE_SIZES`/`TARGET_P95_MS`, `tests/perf/plugin_catalog_scale.py:33,39`).
  The installed inventory is ~13 rows.

The split causes six verified concrete problems:

1. **The landing surface cannot be navigated.** The default sub-tab is Core
   (`UpdatesSessionState.active_subtab = "core"`, `config_center_session.py:82`), a
   static panel with no list where `j`/`k`/`'`/`Space`/`g`/`G` are disabled by
   `check_action`'s `browse_only` set (`plugins_browser_layout.py:186`).
2. **"Am I up to date?" is answered on a sub-tab you may not be on.** The all-current
   predicate spans all three sources (`_all_up_to_date`,
   `plugins_browser_status.py:54`) but its banner is mounted only inside the Core
   container (`plugins_browser_layout.py:101` — verified).
3. **`Space` means two different things.** Install mark for not-installed plugins
   (`_can_install_entry`, `plugins_browser_rendering.py:614`) vs. update mark for
   ready-updatable CLIs (`_can_mark_agent_cli`,
   `plugins_browser_agent_clis_actions.py:110`). Two disjoint mark sets; `Esc` clears
   only the active one.
4. **`A` silently ignores marks from other sub-tabs.** Verified verbatim: the marked
   set is consumed only `if self._active_subtab == "agent-clis"`
   (`plugins_browser_agent_clis_actions.py:199-204`). From Core or Plugins, `A` updates
   everything regardless of what you marked.
5. **The hint lines are provably out of room** — the source comments say so themselves
   (`plugins_browser_agent_clis.py:257`, `plugins_browser_status.py:246`, both
   verified).
6. **The frequency ranking is inverted.** The rarest task (browsing installable
   plugins) owns the largest surface; the most common ("am I current? update what's
   behind") owns a cursor-less panel and requires visiting three places.

---

## 2. The neighbouring surface, and the decision it forces

`,U` (`update_sase: "U"`, `src/sase/default_config.yml:747`) opens the **Update
panel**: four scoped rows (Everything / SASE / Providers / Agents) with status chips
and counts, projected from two in-memory snapshots with **no I/O on the keystroke**
(`action_update_sase_shortcut`, `src/sase/ace/tui/actions/base.py:153` — verified).
Choosing a row submits a `ComprehensiveUpdateRequest` with one sectioned preview and
one tracked proc.

The earliest document proposed wiring the merged tab's `u` into that same
comprehensive path ("the same model at two zoom levels"). **Researcher B rejected this,
and the bead record — which I re-verified — makes the rejection decisive:**

- Epic `sase-r1` (*"The `,U` Update panel — scoped, cached, Admin-Center-free
  updates"*, closed 2026-08-19) states in its description: *"…and no option opens the
  SASE Admin Center."* (exact quote, `sase bead show sase-r1`).
- Its final phase `sase-r1.6`, *"Retire the Admin Center auto-update path"*, landed as
  `f1914962c` — six commits before HEAD — deleting `ComprehensiveUpdateActionsMixin`
  and the pane's comprehensive plumbing while explicitly keeping "Updates pane `u`/`A`/`a`".
- `docs/ace.md:6543` pins the contract: the providers leg *"never broadens the captured
  set from an Updates-pane load."*

The current separation — pane keeps `u`/`A`/`a` as its own legs; comprehensive scopes
live on `UpdateRunActionsMixin` — is the deliberate, recent, epic-scale end state.
Re-coupling them two weeks later would re-introduce exactly the plumbing `sase-r1.6`
deleted, on the strength of "it would be tidier".

**Decision: `u`, `A`, and `a` keep their present targets and separate previews.** If
three-preview friction is the real complaint, the answer is `,U`, which already fixes
it in one keystroke with zero I/O.

---

## 3. The other contested decisions, resolved

### 3.1 Scoping: a cycled scope filter beats a promoted "Needs action" section

Researcher A put a **Needs action** section atop one list containing the entire
catalog, scoped by a bespoke token dialect (`@updates`, `type:cli`, `status:error`).
The earliest doc put three cycled scopes on `]`/`[`. The scope design wins:

- **Promotion churns the list.** In the promoted design a row *changes section* when
  its status flips, so every refresh reorders the list under the cursor — researcher A
  itself warns against exactly that. Sorting outdated first *within* stable domain
  sections keeps "problems at the top" with far smaller displacement. (Honesty note:
  within-section resort on refresh moves rows too; the mitigation — lazy completions
  patch one row in place, reclassification happens only on a deliberate refresh, and
  identity-based selection restore covers the rest — applies to both designs, but
  section-membership churn is the larger jump.)
- **A Needs-action section duplicates the Outdated scope.** If a scope shows only
  outdated-or-errored rows, a promoted section is redundant.
- **The default view gets cheaper, which is the point.** ~13 rows instead of the whole
  catalog, under a 16 ms p95 budget enforced at n=2000.
- **The token dialect is the worst of three filter options.** It is neither the plain
  substring filter users have nor the project's real query stack
  (`src/sase/ace/query_profile/`, already used by the Procs pane). Keep the existing
  substring filter, widen its haystack to all three row kinds, and defer the query
  profile entirely — a fake dialect that later has to be replaced is strictly worse.

**Gap closed by this consolidation:** researcher A's Needs-action section explicitly
included *manual* updates, and neither later doc checked whether the Outdated scope
would. It does: agent-CLI `update_available` is a pure version comparison independent
of install method (`_update_available`, `src/sase/agent_clis/operations.py:88`, with an
`EXACT` comparator branch for channel-pinned distributions). A manual-only CLI with a
newer version is `update_available=True`; it lands in Outdated carrying a `manual`
capability — visible, not markable, with its suggested command in the detail. State
this as an invariant in the implementation plan: **Outdated = `update_available` rows ∪
source-error rows, and manual-only rows must appear there.**

### 3.2 Verbs: keep mutations explicit; unify only the mark set

The earliest doc collapsed `i`/`I`/`A`/`U` into `Space`/`Enter`/`u` with the verb
derived from the row. Researcher A refused; researcher B agreed with the refusal, on
four grounds that all verify:

- It replaces a sub-tab mode with a **cursor-position mode**: `Enter` on one row
  installs a community package from a GitHub topic search; `Enter` two rows up upgrades
  the `sase` host package and restarts ACE. The operations genuinely differ in scope
  and safety (community-trust warning, Rust rebuild/restart, vendor updaters,
  manual-only rows).
- `sase_flags.md` (read via the audited path; the quote is exact) makes retiring four
  documented bindings and re-meaning `Space` **mandatory `sunset`-flag territory**: "A
  flag is also mandatory for deprecated or backward-compatible branches while callers
  migrate." That means a flag bead, both-state test matrices, a registry entry, and a
  later removal change.
- The motivation — hint-line width — evaporates once the merge lands: three hint lines
  become one and `[ / ] sub-tab` becomes `[ ] scope`.

**What survives from the collapse:** one `_marked` set keyed by row identity, the
mark's *verb* derived from the row, but the *consuming keys* unchanged (`i` consumes
install marks, `A` consumes CLI-update marks). That deletes both prune routines, both
advance routines, and the split `Esc` handler — the real simplification — while
changing nothing a user has memorized. Add researcher A's visible aggregate so a filter
can never hide marked work:

```text
Marked: 2 plugin installs · 1 CLI update (1 hidden by filter)
```

### 3.3 Agents: a header chip, not rows

`,U`'s fourth leg — Agents (importing hoods other machines published) — is bound in the
tab via `a` (`plugins_browser_layout.py:245`) but never displayed; researcher A missed
it entirely. Surface it as a digest chip (`⇅ 2 hoods from 1 project`) with `a` in the
hint line. Hoods have no installed/latest pair and no per-row command; rows would
re-introduce the heterogeneity the merge removes. The data already exists
(`_agents_sync_last_status` → `build_update_panel_state`,
`update_panel_state.py:130`); the pane needs a read, not a collector.

---

## 4. Recommended design

**One master/detail inventory. Sections by domain. Scope-filtered. Capabilities on the
row. Every existing key keeps its meaning.**

```
┌─ Updates ──────────────────────────────────────────────────────────────────┐
│  ↑ 3 updates · sase v0.17.0→0.17.1 · 1 plugin · 1 agent CLI                 │  digest header
│  ⇅ 2 hoods from 1 project · checked 4m ago · Dev (editable) · ONLINE        │  (or all-current banner)
│  ⟨ Outdated │ INSTALLED │ All ⟩              / filter components, plugins…  │  scope strip + filter
├─────────────────────────────────┬──────────────────────────────────────────┤
│ ── SASE ──                      │  ┌─ sase ─────────────────────────────┐   │
│   ↑ sase         v0.17.0→0.17.1 │  │ Installed  0.17.0                   │   │
│   · sase-core    v0.2.9    dev  │  │ Latest     0.17.1                   │   │
│ ── Plugins ──                   │  │ Install    editable · ~/projects/…  │   │
│   ↑ github       v0.2.9→0.3.0   │  │ Upstream   origin/master            │   │
│   · telegram     v0.4.9         │  │ Incoming commits (3)                │   │
│ ── Agent CLIs ──                │  │  abc1234 fix(x): …                  │   │
│   ↑ Claude Code  v2.1.2→2.1.3   │  └─────────────────────────────────────┘   │
│   · Codex CLI    v0.152.1  npm  │                                            │
├─────────────────────────────────┴──────────────────────────────────────────┤
│ Marked: 1 CLI update · i install · A upd CLIs · u core+plugins · a sync …   │
└────────────────────────────────────────────────────────────────────────────┘
```

Structurally: today's Plugins sub-tab, with Core folded in as two rows, Agent CLIs
appended as a section, and the sub-tab strip demoted to a scope strip. The CSS block
(`styles.tcss:8536-8674`) collapses from three sub-tab containers plus two list/detail
pairs to one pair.

### 4.1 Row model

One discriminated row, built once per load on the worker thread:

```python
UpdateRowKind    = Literal["core", "plugin", "agent-cli"]
UpdateRowSection = Literal["sase", "plugins", "agent-clis", "available"]

@dataclass(frozen=True, slots=True)
class UpdateRow:
    key: str                                  # "core:sase" | "plugin:github" | "cli:claude"
    kind: UpdateRowKind
    section: UpdateRowSection
    label: str
    accent: str
    installed: bool
    installed_version: str | None
    latest_version: str | None
    update_available: bool
    source: str                               # managed | editable | git | npm | manual …
    capabilities: frozenset[UpdateCapability] # update | install | uninstall | switch_mode | manual
    error: str | None
    haystack: str                             # casefolded, built once per load
    payload: CorePackageVersion | PluginCatalogEntry | AgentCliStatus
```

`capabilities` is the load-bearing field: every gate that reads `_active_subtab` today
(`check_action`'s sets, `_can_install_entry`, `_can_update_highlighted`,
`_can_uninstall_highlighted`, `_can_switch_mode`, `_can_mark_agent_cli`) becomes a set
lookup on the highlighted row. The `NotUvToolInstall` gate becomes a pane-level fact
that *subtracts* capabilities at build time. `payload` keeps the existing detail
renderers working untouched.

### 4.2 Scopes, ordering, landing

Three scopes cycled on `]`/`[`, persisted in `UpdatesSessionState` (replacing
`active_subtab`):

1. **Outdated** — `update_available` rows (including manual-only, §3.1) **plus**
   source-error rows, so a failed probe is never hidden by a filter that means
   "problems". When empty *and* every source succeeded, render the all-current banner,
   never an empty list — an empty list that means "good news" is how this kind of
   surface lies to people.
2. **Installed** *(default)* — SASE + installed plugins + installed agent CLIs.
   ~13 rows.
3. **All** — adds `── Available ──`: catalog plugins you lack, registered CLIs you have
   not installed. The only scope that can be large; never the default. Do not
   materialize its 2,000 `UpdateRow`s when the active scope doesn't render them.

**Ordering:** sections in domain order; outdated first within each section, then
display name. Section headers are disabled `OptionList` options reusing
`_HEADER_PREFIX`/`_is_item` (`plugins_browser_controls.py:224`) so the jump mixin skips
them unchanged.

**Landing:** open on Installed with the cursor on the first outdated row, else the
first row — a stable small list with the cursor moved to the problem, rather than a
list whose contents change shape between opens.

**Filter:** the existing plain substring `Input`, haystack widened to all three row
kinds. No token dialect. The `query_profile` stack is the natural follow-on if richer
filtering is ever wanted, and it is much cheaper *after* the merged row model exists.

### 4.3 Keymap — unchanged; offering moves to capabilities

Every binding in `docs/configuration.md:413-438` keeps its meaning. Only *when it is
offered* changes, from `_active_subtab` to `row.capabilities`:

- `i`/`I` install and install-mark (rows with `install`); `x` uninstall; `U` update one
  plugin; `m` mode switch; `H` history scope on agent-CLI rows.
- `A` update agent CLIs — now consuming CLI marks from anywhere, instead of silently
  ignoring them off the Agent CLIs sub-tab (today's verified bug, §1 item 4).
- `u` core + plugins and `a` agents sync — pane-wide, unchanged, **not** rerouted
  (§2).
- `Space` marks the highlighted row; verb derived, consuming keys unchanged (§3.2).
- `Esc` clears **all** marks, including filter-hidden ones, then closes — the one
  deliberate behavior change, and strictly a bug fix.
- `j` `k` `'` `/` `r` `o` `v` `g` `G` `Ctrl+D/U` — unchanged, and now work everywhere,
  including where `'` is today a documented no-op (Core hosts no list).

The hint line gets shorter: three lines become one, `[ / ] sub-tab` becomes
`[ ] scope`, and both squeeze comments die with their workarounds.

### 4.4 Detail — dispatch, don't rewrite

One `#updates-detail` scroll switching on `row.kind`, calling today's renderers
unchanged: `_core_versions_table` per package plus `_core_incoming_sections` and the
mode line for core; `build_detail_panel` + `build_community_warning_panel` for plugins;
`_agent_cli_detail_panel` + `build_agent_cli_history_panel` (still gated by `H`) for
CLIs. Core *gains*: today both packages share one cramped panel; as per-row detail each
gets the full column. Lazy latest/incoming completions patch exactly one row in place
(the `replace_option_prompt_at_index` mechanism `_refresh_install_mark_row` already
uses) and never trigger reclassification under the cursor.

### 4.5 Header, and the truthfulness invariant

Two states, always visible in every scope:

- **All current** → the existing `_all_current_banner`, promoted out of the Core
  container.
- **Otherwise** → a digest built from the `update_status` the load already computes.
  Today the pane forwards it to the top-bar badge revalidation and does not retain it
  (`plugins_browser_workers.py:277` — verified); retaining it is a one-field change.
  Digest: total count, per-source breakdown, any failed source with its error, cache
  age, offline badge, install mode, agents chip.

**Invariant (researcher A's, worth stating explicitly): never render "all current"
while any enabled source is unknown or failed.** `_all_up_to_date` already encodes
this; the merge stops hiding its answer. Offline mode retains known data and labels its
age — "latest unknown" is not "current".

### 4.6 Rust core boundary

Sections, ordering, scopes, hint text, detail dispatch, and the filter haystack are
presentation; they stay in Python. The update domain is currently entirely Python (no
`sase_core_rs` calls in `sase/updates/`, `sase/plugins/`, `sase/agent_clis/`,
`sase/uv_tool/`), and `UpdateRow` is a projection over the existing `UpdateStatus`
aggregate. **Capability derivation is the line to watch:** keep it a thin composition
of today's predicates. The moment it encodes *new* policy — a canonical definition of
"manual update", an eligibility rule another frontend would need to match — that rule
belongs in `../sase-core`. State this in the phase-1 plan so any boundary crossing is a
decision, not a drift.

---

## 5. Constraints that bind the implementation

From `tui_perf.md` (read via the audited path; the earlier `LayoutCollisionError` that
blocked two research rounds no longer reproduces):

1. **Rule 12 — the single highest-risk line of the merge.** `OptionList` emits
   `OptionHighlighted` echoes on programmatic `highlighted = X`; the guard must be set
   and cleared **synchronously** (`finally:`), never via `call_later`. The merge
   collapses two `ProgrammaticSelectionGuard`s into one; the merged rebuild path is
   precisely where this bug class lives.
2. **Rule 7** — the kind-dispatching detail stays behind the existing pane-wide
   `DetailPanelDebouncer` (150 ms); the highlight and hint line stay immediate.
3. **Rule 6** — scope switch is a deliberate full rebuild (fine); lazy completions
   patch one row (§4.4).
4. **Rules 1/2** — row construction runs on the load worker, never in a pump callback.
5. **Rule 4** — re-read scope and highlighted identity when a worker result lands.
6. **Measure**: `SASE_TUI_PERF=1` per-keystroke JSONL; p95 < 16 ms. Re-point **both**
   catalog benches — `tests/perf/bench_plugin_catalog_scale.py` and
   `tests/ace/tui/bench_plugins_catalog_scale.py` (two files, not one; verified) — at
   the `All` scope so the n=2000 net survives the default change.

From `sase_flags.md`: everything in §4 ships **flag-free** — no binding changes
meaning, `]`/`[` keeps cycling "what the list shows", and the rest is additive
presentation or internal. The two proposals that *would* require a mandatory `sunset`
flag are exactly the two this report rejects (the verb collapse, §3.2; the `u`
rerouting, §2). Dropping them removes a flag bead, both-state test matrices, and a
future removal change from the critical path — the strongest practical argument for
this split.

---

## 6. Implementation sequence

Four phases; phases 1–3 are the whole recommendation.

1. **Capabilities move from the sub-tab to the row — no visible change.** *(medium)*
   New pure module `plugins_browser_rows.py` (`UpdateRow`, `UpdateCapability`,
   `build_update_rows(load_result, *, uv_tool, offline)`), exhaustive unit tests;
   rewrite `check_action` and both hint builders to consult the highlighted row. The
   sub-tabs stay. This is the only structurally risky step, and landing it with the UI
   frozen makes the existing ~6,246 lines of pane tests the safety net rather than the
   casualty.
2. **One list, sections, scopes.** *(large — consider splitting: list merge + sections
   first, scopes + header second)* Two `OptionList`s → one; `ContentSwitcher` +
   `_SUBTAB_ORDER` → scope enum + scope strip; one bookmark, one guard (rule-12 trap
   lives here); detail dispatch on `row.kind`; banner promoted; digest header; agents
   chip. `UpdatesSessionState.active_subtab` → `scope` (process-local, no durable
   migration — but grep the exported `UpdatesSubTab` literal,
   `config_center_session.py:11,109`).
3. **One mark set; `Esc` clears globally; marked-count summary.** *(small)* Delete both
   prune routines, both advance routines, the split `Esc` handler; `i`/`A` keep
   consuming their mark kinds.
4. **Docs, benches, snapshots.** *(medium)* `docs/ace.md:6495-6565`,
   `docs/configuration.md:405-438` (its "active sub-tab" language is now wrong),
   `docs/plugins.md:276,403`, `docs/agent_providers.md:261,364`; both benches (§5);
   rewrite the 7 `_switch_to_subtab` calls in the 15-test PNG suite
   (`tests/ace/tui/visual/test_ace_png_snapshots_config_center_plugins.py`; counts
   verified) to scope selections and rebaseline, adding scenarios where only a CLI or
   only a plugin is outdated, a source has failed, and marks are hidden by a filter.

**Deliberately excluded**, each later, separate, and independently arguable (the first
two need their own `sunset` flags): the verb collapse, the `u` rerouting, researcher
A's adaptive narrow layout, the `query_profile` filter. None is blocked by this work;
all are cheaper after it.

**Verification** (per `lint_and_test.md`): `just install` then `just check` inline per
phase; `just check-full` only through `/sase_monitor` before landing the combined tree.

### Acceptance criteria

- Opening Updates reveals every actionable update, every manual update, and every
  source failure without another keystroke.
- Every Core, plugin, and Agent CLI entity appears exactly once per scope; the screen
  never claims "all current" while any enabled source is unknown or failed.
- One filter searches all domains; `'` jumps across all rows; `]`/`[` cycles scopes.
- Highlight, scroll, filter, and marks survive refreshes; filtered-out marks stay
  visible in the aggregate summary; `Esc` clears all marks predictably; marks are
  consumed by `A`/`i` regardless of where they were set.
- Existing update plans and execution paths keep their present scopes; community-trust
  warnings and manual CLI commands/history remain at least as visible as today.
- Filter and navigation stay under the 16 ms p95 budget at a 2,000-plugin catalog
  (`All` scope).

---

## 7. Separable finding: the badge click is inverted

Verified: clicking the top-bar updates badge runs `open_updates_panel` →
`_open_config_center("updates")` (`updates_indicator.py:104`,
`actions/base.py:149`) — the heavyweight Admin Center tab with a live load — while `,U`
opens the zero-latency `UpdatePanel` built from cached snapshots. The surface that
instantly answers "3 updates available — what are they?" is behind a chord; the slow
one is behind the click. Fixing it (badge click → `UpdatePanel`, ideally with a
"browse inventory →" affordance into the tab) is cheaper than the merge, orthogonal to
it, most consistent with `sase-r1`'s intent, and — being a change to a learned click —
wants its own `sunset` flag. Decide it independently; do not silently bundle it.

---

## 8. Open questions

1. **Agents as a header chip (recommended) or a fourth section of project rows?** Rows
   would make the tab a literal superset of `,U` at the cost of a fourth heterogeneous
   row kind with no versions to show.
2. **The badge-click inversion (§7)** — fix, leave, or add the browse affordance?
3. **Is the verb collapse wanted *eventually*?** The design already leaves the seam (a
   single mark set + capability derivation); if yes it becomes a fifth, flagged phase.
4. **Split phase 2 into two landings?** Halves the snapshot-rebaseline blast radius per
   landing at the cost of one intermediate state where the default view is the full
   catalog.
