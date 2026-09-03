# Merging The Updates Tab: A Decision Document

**Question:** merge the SASE Admin Center **Updates** tab's three sub-tabs — Core,
Plugins, Agent CLIs — into one view that keeps every capability of all three. What is the
correct UX, and how should it be built?

**Status of this document:** two prior research reports already answer that question and
**disagree with each other on the parts that matter**. This document does not re-derive
their shared analysis. It adjudicates the disagreement, supplies the evidence both were
missing, and ends with a single recommendation you can act on.

Prior art (read in full before writing this):

- `research:202609/unified_updates_tab.md` — hereafter **Doc A**
- `research:202609/admin_center_updates_tab_unification.md` — hereafter **Doc B**

**Scope of new work:** `sase` at `58d3ed746`. Independent re-verification of both docs'
load-bearing citations, plus three things neither doc had: the two reference-memory notes
Doc B was blocked from reading (`tui_perf.md`, `sase_flags.md`), the bead history of the
adjacent `,U` surface, and the current test/snapshot cost measured rather than estimated.

---

## 1. Executive summary

Both prior docs reach the same structural conclusion, and it is correct: **the three
sub-tabs are a presentation seam over a single data seam.** One worker already returns
core versions, the plugin catalog, and agent-CLI statuses in one `PluginsLoadResult`
(`src/sase/ace/tui/modals/plugins_browser_loading.py:99`), and `UpdateStatus`
(`src/sase/updates/status.py:96`) is already the aggregate across all three. Merging costs
no extra I/O and deletes widgets. That part is settled; adopt it.

They diverge on three decisions, and my adjudication is:

| Decision | Doc A | Doc B | **Verdict** |
| --- | --- | --- | --- |
| How to keep the 2000-row catalog from burying 13 important rows | "Needs action" section on top; whole catalog always in the list; scope via a bespoke filter dialect (`@updates`, `type:cli`) | Cycled **scope** filter on `]`/`[` — Outdated / **Installed** (default) / All | **Doc B.** Cardinality is asymmetric and permanent; a default that renders 13 rows is both better UX and strictly faster. Doc A's dialect is a worse version of the project's real query stack. |
| Whether to collapse `i`/`I`/`A`/`U` into `Space`/`Enter`/`u` | No — operations differ in scope and safety; keep them explicit | Yes — derive the verb from the row | **Doc A.** Doc B replaces a sub-tab mode with a cursor-position mode, and `sase_flags.md` makes it a mandatory `sunset` flag for a win the scope merge already delivers. |
| Whether the tab's `u` should submit a `ComprehensiveUpdateRequest` | Not addressed; says `,U` stays distinct | Yes (§6.7) | **Doc A, emphatically.** Bead `sase-r1` was an epic whose stated goal was "**no option opens the SASE Admin Center**", and whose final phase `sase-r1.6` was literally "Retire the Admin Center auto-update path" (landed `f1914962c`, 5 commits ago). Doc B proposes undoing it. |

**The recommendation (§6):** one master/detail list, sections by domain, outdated sorted
first *within* each section, a cycled scope filter defaulting to Installed, capabilities
carried on the row instead of read off `_active_subtab`, the all-current banner promoted
out of the Core container, agents surfaced as a header chip. **Keep every existing
keybinding and every existing action path exactly as-is.** This ships the entire UX win
with **no feature flag, no keymap deprecation, and no re-litigation of `sase-r1`** — and
it leaves Doc B's verb collapse available later as a separate, flagged, independently
arguable change.

One additional finding, separable from the merge and cheaper than it, in §7: **the top-bar
badge click currently opens the heavyweight tab, while the `,U` chord opens the
zero-latency panel.** That is inverted, and fixing it removes most of the pressure on the
merged tab to be a fast "am I up to date?" surface.

---

## 2. Verification of the prior docs

I re-checked every claim this document leans on. Both docs are substantially accurate;
the corrections are minor.

**Confirmed:**

- Core is permanently two rows — `_CORE_PACKAGES` is a hard-coded 2-tuple of
  `("sase", HOST_DISTRIBUTION_NAME)` and `("sase-core", CORE_DISTRIBUTION_NAME)`
  (`src/sase/uv_tool/versions.py:38`). Doc B's central cardinality argument holds.
- Core is the default landing sub-tab (`UpdatesSessionState.active_subtab = "core"`,
  `config_center_session.py:82`) and has no list, so `j`/`k`/`'`/`Space`/`Ctrl+D`/`g`/`G`
  are all disabled there by `check_action`'s `browse_only` set
  (`plugins_browser_layout.py:186-196`).
- The all-current banner is computed across all three sources (`_all_up_to_date`,
  `plugins_browser_status.py:54`) but mounted only inside the Core container
  (`plugins_browser_layout.py:101`).
- `Space` genuinely means two different things: `_can_install_entry` offers it only for
  **not-installed** plugins (`plugins_browser_rendering.py:614`), while
  `_can_mark_agent_cli` offers it only for **updatable installed** CLIs
  (`plugins_browser_agent_clis_actions.py:110`). Two disjoint mark sets; `Esc` clears only
  the active one.
- The hint lines are provably out of room — both squeeze comments Doc B quotes are
  verbatim (`plugins_browser_agent_clis.py:257`, `plugins_browser_status.py:246`).
- Perf budget: `CATALOG_SCALE_SIZES = (10, 250, 1000, 2000)` and `TARGET_P95_MS = 16.0`
  (`tests/perf/plugin_catalog_scale.py:33,39`).
- `,U` is `update_sase: "U"` at `src/sase/default_config.yml:747`; the snapshot-gating
  sentence is at `docs/ace.md:6544`.
- `UpdatePreviewInputs` is an injectable dataclass whose every field the pane already
  holds (`src/sase/ace/tui/update_preview_inputs.py:19`).

**Corrections:**

- Doc B cites the bench as `tests/perf/plugin_catalog_scale.py:33`. That file is the
  *shared harness*; the runnable benches are `tests/perf/bench_plugin_catalog_scale.py`
  (non-TUI: fetch pages, enrich ops) and `tests/ace/tui/bench_plugins_catalog_scale.py`
  (the TUI one that enforces the 16 ms p95 on filter keystroke and `j`). Two files to
  re-point, not one.
- Doc B says the PNG suite "has 15 snapshot tests, 7 of which call `_switch_to_subtab`".
  Exactly right: 15 tests, 7 calls at lines 83, 113, 138, 169, 199, 230, 256 of
  `tests/ace/tui/visual/test_ace_png_snapshots_config_center_plugins.py`.
- Doc B's §10 environment note — that `sase memory read tui_perf.md` and `sase_flags.md`
  both failed with a `LayoutCollisionError` — **no longer reproduces.** Both notes read
  cleanly on this machine today. Doc B's performance and backward-compatibility claims
  were therefore derived without them; §4 and §5 below supply what they say.

---

## 3. The disagreement, decided

### 3.1 Scoping: Doc B's cycled scope beats Doc A's "Needs action" section

Doc A puts a **Needs action** section at the top of one list that also contains the entire
catalog, and scopes with a bespoke token dialect (`@updates`, `type:cli`, `status:error`,
`trust:community`). Doc B puts three cycled scopes on `]`/`[` and defaults to Installed.

Doc B is right, for three reasons:

**(a) Promotion breaks positional memory and complicates selection restore.** In Doc A a
row *moves out of its home section* when it becomes outdated. The pane's selection
machinery is identity-based (`restore_selection_by_identity` + `prior_visual_row`,
`plugins_browser_rendering.py:178`), so it survives — but the user's spatial memory does
not, and every refresh that flips a row's status reorders the list under the cursor. Doc A
itself warns against exactly this ("It must not reorder the list under the user's cursor
until a deliberate refresh"), then designs a section whose membership *is* status. Sorting
outdated first *within* a stable section gets the same "problems are at the top" property
with none of the instability.

**(b) A "Needs action" section duplicates the Outdated scope for free.** If you have a
scope that shows only outdated-or-errored rows, a promotion section is redundant.

**(c) The default view gets cheaper, which is the point.** Doc A's default renders the
whole catalog; Doc B's renders ~13 rows. Given a 16 ms p95 budget enforced at n=2000 and
`tui_perf.md` rule 6 ("prefer selective updates over full rebuilds"), making the common
path smaller is not a nice-to-have. The 2000-row benches then exercise a *non-default*
scope, so the regression net stays in place while the everyday path improves.

**On the filter dialect specifically:** Doc A's tokens are a hand-rolled mini-language
that is neither the plain substring filter users have now nor the project's actual query
stack (`src/sase/ace/query_profile/`, used by the Procs pane via
`src/sase/ace/tui/_proc_query.py`). Doc B is right that the real stack is the correct
long-term answer and wrong only in scheduling it as "phase 4, optional". My position:
**keep the existing plain substring filter, widen its haystack to all three row kinds, and
defer the query profile entirely.** Introducing a fake dialect that later has to be
replaced by the real one is the worst of the three options.

**One refinement to Doc B's scopes.** Doc B's landing rule is "open on Installed, put the
cursor on the first outdated row". Keep that, but make **Outdated non-empty-gated**: when
nothing is outdated and no source failed, the Outdated scope should still be reachable and
should render the all-current banner rather than an empty list. An empty list that means
"good news" is the single most common way this kind of surface lies to people.

### 3.2 Verb collapse: Doc A is right to refuse it

Doc B's §6.4 retires `i`, `I`, `A`, and `U`, and re-means `Space` as a single "include in
the next run" mark whose verb is derived from the row. It is an elegant model. It is also
the one part of Doc B I would not ship, for four reasons:

**(a) It moves the mode rather than deleting it.** Doc B's own §7 argues — correctly —
that "modes that change what a key means without changing what the key *looks like* are
the most expensive kind." But deriving `Enter`'s meaning from the highlighted row is
exactly that. Today `Space` is ambiguous across *two sub-tabs*, which at least have a
visible strip. In Doc B's design `Enter` on one row installs a third-party package from a
GitHub topic search, and `Enter` two rows up upgrades the `sase` host package and restarts
ACE. The disambiguator is a cursor position.

**(b) The operations are genuinely not interchangeable.** Installing a *community* plugin
carries a trust warning the pane renders deliberately
(`build_community_warning_panel`, `plugins_browser_rendering.py:440`). A core update can
trigger a Rust rebuild and an ACE restart. An agent-CLI update shells out to a vendor's own
updater, sequentially, and some are manual-only. Doc A's phrasing is the right one: unify
*inspection*, keep *mutation* explicit.

**(c) `sase_flags.md` makes it expensive.** Retiring four documented bindings and changing
`Space`'s meaning is user-reaching behavior whose old branch must stay reachable — the note
is unambiguous that this is mandatory `sunset` flag territory ("A flag is also mandatory
for deprecated or backward-compatible branches while callers migrate"). That means
`sase flag new`, a typed flag bead, three authored justification sentences, tests for
**both** states, a registry entry, and a later removal change that deletes the Off branch.
All four bindings are documented in `docs/configuration.md:413-424`.

**(d) The motivation evaporates once the scopes land.** Doc B's stated reason for the
collapse is hint-line width. But the merge alone already reclaims it: three hint lines
become one, `[ / ] sub-tab` becomes `[ ] scope`, and the three summary lines and three
status lines collapse. The width crisis is a symptom of the split, not of the verb count.

**What I would keep from Doc B's §6.4:** the single `_marked` set keyed by row identity,
with the mark's *verb* still derived from the row but the *consuming key* unchanged — `i`
consumes install marks, `A` consumes CLI-update marks, exactly as today. That deletes both
prune routines, both advance routines, and the split `Esc` handler (Doc B's real win) while
changing nothing a user has memorized. Add Doc A's visible aggregate so a filter can never
hide marked work:

```text
Marked: 2 plugin installs · 1 CLI update (1 hidden by filter)
```

### 3.3 Routing `u` through the comprehensive path: no

This is the clearest call in the document, and it rests on evidence neither prior doc
weighted.

Doc B §6.7 recommends wiring the pane's `u` to submit a `ComprehensiveUpdateRequest`, so
the tab and `,U` become "the same model at two zoom levels". Doc B then flags the risk
itself (§9.1): `docs/ace.md:6544` states the providers leg "never broadens the captured set
from an Updates-pane load."

The bead record makes it stronger than a risk. Epic **`sase-r1`** — *"The `,U` Update
panel — scoped, cached, Admin-Center-free updates"* — states in its description:

> Pressing `,U` opens a fast, keyboard-first Update panel rendered entirely from
> already-fetched update evidence. [...] **and no option opens the SASE Admin Center.**

Its final phase, `sase-r1.6`, is *"Retire the Admin Center auto-update path"*, landed as
`f1914962c` — five commits before HEAD:

> Remove `auto_update` and `comprehensive_provider_names` from `ConfigCenterModal`,
> `_open_config_center`, and the Updates pane factory. Delete
> `ComprehensiveUpdateActionsMixin` and the pane worker/incoming-commits handoff that only
> served the old `,U` dispatch. [...] **Keep Updates pane `u`/`A`/`a`** plus the extracted
> preview/execution helpers (now module-private).

The separation of the two surfaces is a deliberate, recent, epic-scale decision, and the
current shape — pane keeps `u`/`A`/`a` as its own legs; comprehensive scopes live on
`UpdateRunActionsMixin` — is its intended end state. Re-coupling them two weeks later needs
a much stronger argument than "it would be tidier", and it would re-introduce the exact
plumbing that phase deleted.

**Decision: `u`, `A`, and `a` keep their present targets and their present separate
previews.** If the three-preview friction is the real complaint, the answer is the `,U`
panel (which already fixes it in one keystroke with zero I/O), not a second implementation
of it inside the pane.

### 3.4 Agents: Doc B's header chip, and Doc A's silence is a gap

`,U` has a fourth leg — Agents (importing hoods other machines published) — that the
Updates tab binds via `a` (`plugins_browser_layout.py:245`) but never displays. Doc A does
not mention it at all.

Doc B's recommendation is right: **a digest chip in the header, not rows.** Agent hoods
have no installed/latest pair, no per-row update command, and no detail that belongs in
this pane. Giving them rows re-introduces the heterogeneity the merge removes, for no
browse value. `⇅ 2 hoods from 1 project` in the header plus `a` in the hint line gives the
complete "what is behind" picture with a one-key path to act.

The data is already in the app (`_agents_sync_last_status`, projected by
`build_update_panel_state`, `update_panel_state.py:130`); the pane needs a read, not a
collector.

---

## 4. What `tui_perf.md` requires (neither prior doc could cite it)

Doc B's §10 records that the audited read failed. It succeeds now. The rules that bind this
work, with the specific trap each one names:

1. **Rule 12 — guard programmatic widget updates.** `OptionList` emits `OptionHighlighted`
   echoes on programmatic `highlighted = X`; the guard must be set and cleared
   **synchronously** (`finally:`), never via `call_later`, or you get cursor jumps and
   freezes. The merge collapses two `ProgrammaticSelectionGuard`s
   (`plugins_browser_rendering.py:178`, `plugins_browser_agent_clis.py:75`) into one. That
   is a simplification, but the merged rebuild path is precisely where this bug class
   lives — it is the single highest-risk line of the whole change.
2. **Rule 7 — debounce the detail panel, never the highlight.** The kind-dispatching detail
   renderer must stay behind the existing pane-wide `DetailPanelDebouncer`
   (`plugins_browser_layout.py:154`, 150 ms). The hint line stays immediate, as today.
3. **Rule 6 — prefer selective updates over full rebuilds.** A scope switch is a full
   rebuild and is fine (it is a deliberate keypress). Lazy latest / incoming-commit
   completions must patch **one** row via `replace_option_prompt_at_index` — the mechanism
   `_refresh_install_mark_row` (`plugins_browser_rendering.py:625`) already uses — and must
   never trigger a reclassification that reorders under the cursor.
4. **Rules 1 and 2 — never block the loop, and off-the-loop is not off-the-pump.** Row
   construction runs on the load worker, not in a pump callback. This is already how the
   pane works; keep it.
5. **Rule 4 — re-capture UI state after every `await`.** The scope and highlighted identity
   must be re-read when a worker result lands, not captured before it.
6. **Measurement, not intuition.** `SASE_TUI_PERF=1` gives per-`j` key-to-paint JSONL;
   target p95 < 16 ms. The two catalog benches must be re-pointed at the `All` scope so the
   n=2000 net survives the default change (§2 correction: two files).

Doc B's claim that the merge is *faster* survives this review. The default list shrinks
from a full catalog to ~13 rows, and the O(1) identity maps (`_rebuild_plugin_identity_maps`,
`plugins_browser_rendering.py:220`) generalize unchanged.

---

## 5. What `sase_flags.md` requires

The note's rule: a flag is mandatory for "a deprecation whose old branch must stay
reachable" and for "deprecated or backward-compatible branches while callers migrate".
Applying it precisely to this change produces a clean seam:

| Change | Flag? | Why |
| --- | --- | --- |
| Three sub-tabs → one list with sections | **No** | Layout. No binding changes meaning; `]`/`[` keeps cycling something. |
| `]`/`[` cycles scopes instead of sub-tabs | **No** | Same key, same gesture, same mental category (change what the list shows). |
| All-current banner promoted; digest header; agents chip | **No** | Additive presentation. |
| One mark set, `i`/`A` still consume it | **No** | No user-visible key changes meaning. |
| Capabilities on rows instead of `_active_subtab` | **No** | Internal; observable only as *more* keys being correctly available. |
| **Retiring `i`/`I`/`A`/`U`; `Space`/`Enter` re-meaning** | **Yes — `sunset`** | Four documented bindings deprecated; old branch must stay reachable. |
| **`u` → `ComprehensiveUpdateRequest`** | **Yes — and don't** | Changes what a documented key does; also re-opens `sase-r1` (§3.3). |

This is the strongest practical argument for my split: **everything in §6 ships flag-free.**
The two items that need a flag are exactly the two I recommend against, and dropping them
removes a flag bead, both-state test matrices, a registry entry, and a future removal
change from the critical path.

---

## 6. Recommended solution

**One master/detail inventory. Sections by domain. Scope-filtered. Capabilities on the
row. Every existing key keeps its meaning.**

### 6.1 Layout

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

Structurally: today's Plugins sub-tab, with Core folded in as two rows, Agent CLIs appended
as a section, and the sub-tab strip demoted to a scope strip. The CSS block
(`styles.tcss:8536-8674`) collapses from three sub-tab containers plus two list/detail pairs
to one pair.

### 6.2 The row model

A single discriminated row, built once per load on the worker thread:

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
becomes a set lookup on the highlighted row. `payload` keeps the existing detail renderers
working untouched. The `NotUvToolInstall` gate becomes a pane-level fact that *subtracts*
capabilities at build time, computed once instead of in four predicates.

### 6.3 Scopes, ordering, and landing

Three scopes on `]`/`[`, persisted in `UpdatesSessionState` (replacing `active_subtab`):

1. **Outdated** — `update_available` rows **plus** rows whose source errored, so a failed
   probe is never hidden by a filter that means "problems". When empty *and* every source
   succeeded, render the all-current banner, not an empty list.
2. **Installed** *(default)* — SASE + installed plugins + installed agent CLIs. ~13 rows.
3. **All** — adds `── Available ──`: catalog plugins you do not have, registered CLIs you
   have not installed. The only scope that can be large; never the default.

**Ordering:** sections in the order above; **outdated first within each section**, then
display name. Section headers are disabled `OptionList` options, reusing `_HEADER_PREFIX`
and `_is_item` (`plugins_browser_controls.py:224`) so the jump mixin skips them unchanged.

**Landing:** open on Installed with the cursor on the first outdated row, else the first
row. (Doc B's Q1; I agree with its answer — a stable small list with the cursor moved to the
problem, rather than a list whose *contents* change shape between opens.)

### 6.4 Keymap — unchanged

Every binding in `docs/configuration.md:413-438` keeps its meaning. What changes is only
**when it is offered**, which moves from `_active_subtab` to `row.capabilities`:

- `i` / `I` install and install-mark, offered on rows with `install`.
- `x` uninstall, on rows with `uninstall`.
- `U` update one plugin, on plugin rows with `update`.
- `A` update agent CLIs — consuming CLI marks, which are now visible from everywhere
  instead of silently ignored off the Agent CLIs sub-tab (today's bug,
  `plugins_browser_agent_clis_actions.py:199-204`).
- `u` core + plugins; `a` agents sync; `m` mode switch — pane-wide, unchanged.
- `H` history scope, offered when the highlighted row is an agent CLI.
- `Space` marks the highlighted row; the mark's verb is derived (install for an available
  plugin, update for an updatable CLI) but the consuming keys are unchanged.
- `Esc` clears **all** marks, including filter-hidden ones, then closes. This is the one
  behavior change, and it is strictly a bug fix.
- `j` `k` `'` `/` `r` `o` `v` `g` `G` `Ctrl+D/U` — unchanged, and now work everywhere,
  including on the two SASE rows where `'` is a documented no-op today.

The hint line still gets shorter: three lines become one, `[ / ] sub-tab` becomes
`[ ] scope`, and the squeeze comments at `plugins_browser_status.py:246` and
`plugins_browser_agent_clis.py:257` can be deleted along with their workarounds.

### 6.5 Detail — dispatch, don't rewrite

One `#updates-detail` scroll switching on `row.kind`, calling the existing renderers
unchanged: `_core_versions_table` per package plus `_core_incoming_sections` and the mode
line for core; `build_detail_panel` + `build_community_warning_panel` for plugins;
`_agent_cli_detail_panel` + `build_agent_cli_history_panel` for CLIs. Core *gains* from the
move — today both packages share one cramped panel; as per-row detail each gets the full
column.

### 6.6 Header

Two states, always visible in every scope:

- **All current** → the existing `_all_current_banner`, promoted out of the Core container.
- **Otherwise** → a digest from the retained `update_status` (which the load already
  computes and the pane currently discards, `plugins_browser_workers.py:277`): total count,
  per-source breakdown, any failed source with its error, cache age, offline badge, install
  mode, and the agents-sync chip.

**Truthfulness rule (from Doc A, and worth stating as an invariant): never render "all
current" while any enabled source is unknown or failed.** `_all_up_to_date` already encodes
this; the merge just stops hiding its answer.

### 6.7 Rust core boundary

`CLAUDE.md` §1.3's litmus test: would a web app, CLI, or editor integration need this
behavior to match the TUI?

- **Sections, ordering, scopes, hint text, accents, detail dispatch, filter haystack** —
  no. Presentation. Stays in Python.
- **`UpdateRow` as a projection over `UpdateStatus`** — no. `UpdateStatus`
  (`src/sase/updates/status.py`) is already the shared aggregate, and the update domain is
  currently entirely Python (no `sase_core_rs` call in `sase/updates/`, `sase/plugins/`,
  `sase/agent_clis/`, or `sase/uv_tool/`).
- **Capability *derivation*** — this is the one to watch. Keep it a thin composition of the
  predicates that exist today (`_can_install_entry`, `_can_update_highlighted`,
  `_can_uninstall_highlighted`, `_can_switch_mode`, `_can_mark_agent_cli`). The moment it
  starts encoding *new* policy — a canonical definition of "manual update", say, or an
  eligibility rule the CLI would have to match — that rule belongs in `../sase-core`, not in
  the adapter. State this explicitly in the phase-1 plan so the boundary crossing is a
  decision rather than a drift.

---

## 7. Separable finding: the badge click is inverted

`UpdatesAvailableIndicator.on_click` runs `open_updates_panel`
(`src/sase/ace/tui/widgets/updates_indicator.py:105`), which resolves to
`action_open_updates_panel` → `_open_config_center("updates")`
(`src/sase/ace/tui/actions/base.py:149`) — the Admin Center tab, with a live threaded load.

Meanwhile `,U` → `action_update_sase_shortcut` (`base.py:153`) opens `UpdatePanel`, built
from two in-memory snapshots with **no I/O on the keystroke**, showing exactly the four
scopes with counts, chips, and freshness.

So: clicking the badge that says "3 updates available" takes you to the slow surface that
until now could not even tell you whether you were up to date, while the fast surface that
answers precisely that question is behind a chord.

This is worth deciding independently of the merge, and it is much cheaper:

- **Option 1** — badge click opens `UpdatePanel`. Most consistent with the badge's meaning
  and with `sase-r1`'s intent. Also *user-reaching*, so it wants a `sunset` flag under
  `sase_flags.md`.
- **Option 2** — leave it, and let §6's digest header make the tab a truthful landing spot.
- **Option 3** — badge click opens `UpdatePanel`; the panel grows a "browse inventory →"
  affordance into the tab.

I lean **Option 1**, but it is your call — it changes a click users have learned, and it is
genuinely orthogonal to the merge. Recording it here so it does not get silently bundled.

---

## 8. Implementation sequence

Four phases; **phases 1–3 are the whole recommendation and none of them needs a feature
flag.**

**Phase 1 — Capabilities move from the sub-tab to the row. No visible change.** *(medium)*

New pure module `plugins_browser_rows.py`: `UpdateRow`, `UpdateCapability`, and
`build_update_rows(load_result, *, uv_tool, offline) -> tuple[UpdateRow, ...]`. Rewrite
`check_action` (`layout.py:166`) and both hint builders to consult the highlighted row's
capabilities. **The three sub-tabs stay exactly as they are.**

*Why first:* it is the only structurally risky step, and landing it with the UI frozen makes
the existing ~6,246 lines of pane tests the safety net rather than the casualty. Verify with
`just check`.

**Phase 2 — One list, sections, scopes.** *(large — consider splitting)*

Two `OptionList`s → one `#updates-list`; `ContentSwitcher` + `_SUBTAB_ORDER` → a scope enum
and a `PanelTabStrip` of scopes; `_switch_to_subtab` → `_set_scope`; two selection bookmarks
→ one; one `ProgrammaticSelectionGuard`; `_jump_repaint` loses its branch; detail dispatches
on `row.kind`; banner promoted; digest header built; agents chip added.
`UpdatesSessionState.active_subtab` → `scope` + one `SelectionBookmark` (process-local, so
no durable migration — but grep for the exported `UpdatesSubTab` literal,
`config_center_session.py:11,109`).

This is where the `tui_perf.md` rule-12 trap lives (§4.1). Verify with `just check`, then
`just test-visual` and a snapshot rebaseline.

**Phase 3 — One mark set; `Esc` clears globally; marked-count summary.** *(small)*

`_marked_install` + `_marked_agent_clis` → one set keyed by `UpdateRow.key`; delete both
prune routines, both advance routines, and the split `Esc` handler. `i` and `A` keep
consuming their respective mark kinds. Add the aggregate summary with a hidden-by-filter
count.

**Phase 4 — Docs, benches, snapshots.** *(medium)*

`docs/ace.md:6495-6565` (Updates Tab), `docs/configuration.md:405-438` (keymap table — the
"active sub-tab" language throughout is now wrong), `docs/plugins.md:276,403`,
`docs/agent_providers.md:261,364`. Re-point **both** catalog benches at the `All` scope
(§2). Rewrite the 7 `_switch_to_subtab` calls in the PNG suite to scope selections and
rebaseline all 15 with `--sase-update-visual-snapshots`.

**Deliberately not in this plan** (available later, each separately arguable and each needing
its own `sunset` flag): Doc B's verb collapse (§3.2), Doc B's comprehensive-update rewiring
(§3.3), Doc A's adaptive narrow layout, and the `query_profile` filter (§3.1). None is
blocked by this work; all are cheaper after it.

**Verification.** Per `lint_and_test.md`: `just check` inline per phase (run `just install`
first — this is an ephemeral workspace clone whose venv may be stale); `just check-full`
**only through `/sase_monitor`** with the `TESTING`/`TESTED` pair before landing the combined
tree, since it routinely outruns a single agent turn.

---

## 9. Recommended solution (one paragraph)

Replace the Core / Plugins / Agent CLIs sub-tabs with **one master/detail inventory**: one
`OptionList` with disabled `── SASE ──` / `── Plugins ──` / `── Agent CLIs ──` /
`── Available ──` section headers, outdated rows sorted first within each section, a scope
filter cycled on the existing `]`/`[` keys (Outdated / **Installed** by default / All) so the
unbounded catalog stops owning the landing view, one kind-dispatching detail panel that calls
today's renderers unchanged, one mark set with a visible aggregate, and a digest header that
promotes the already-computed all-current banner out of the Core container and adds an agents
chip. Carry action availability on a typed `UpdateRow.capabilities` instead of the hidden
`_active_subtab`, and **keep every existing keybinding, every existing action, and the
`sase-r1` separation between this tab and the `,U` panel exactly as they are** — which lets
the entire change ship with no feature flag, no keymap deprecation, and no re-litigated
epic. Take Doc B's structure and scoping, Doc A's restraint about mutations, and neither
doc's optional extras.

---

## 10. Open questions for you

1. **Agents as a header chip (§3.4) or as a fourth section of project rows?** I recommend
   the chip. Rows would make the tab a literal superset of `,U` at the cost of a fourth
   heterogeneous row kind with no versions to show.
2. **The badge-click inversion (§7)** — fix it, leave it, or bundle a browse affordance into
   `UpdatePanel`? Orthogonal to the merge; needs its own flag if changed.
3. **Is Doc B's verb collapse something you want *eventually*?** If yes, phase 3 should be
   built so the mark set and capability derivation are the seam it later plugs into — which
   the design above already does — and it becomes a fifth, flagged phase.
4. **Phase 2 is large.** Splitting it (list merge + sections first; scopes + header second)
   halves the rebaseline blast radius per landing, at the cost of one intermediate state
   where the default view is the full catalog. Worth it if you want smaller landings.
