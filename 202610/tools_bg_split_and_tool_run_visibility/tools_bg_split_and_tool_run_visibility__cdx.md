# Tool activity indicators and clan visibility

**Researcher:** cdx  
**Date:** 2026-10-08  
**Scope:** Independent implementation research and design critique; no product changes.  
**Source revisions:** sase `3412a9f1bdc51737beb8ed38449530e1ea0b4c60`; sase-core `646058197f5ced5231ed478b8a716678007f0156`.

## Assessment

This is a good change. The existing display groups unrelated concepts under the same gear: TUI operations, independent tool execution, and monitor supervision. Giving tools their established identity makes activity easier to locate and makes the blue gear's meaning more useful.

I recommend a ToolRun-centered design: a global `tools: ⚒ N` indicator, a live `⚒N` rollup on tribe panels and clan nodes, and the existing tool-name/progress badge on concrete nodes. Use the durable run ID as identity. Treat tool activity as an additional dimension beside agent status; an agent can remain RUNNING, WAITING, or FINALIZING while a tool runs.

The main adjustment is that `tools:` should describe **active SASE ToolRuns**, rather than only detached processes created by agents. Foreground, detached, and monitored execution should keep the same tool identity. The process executor and the agent/container are related views of one execution, not extra tools.

Two details make a cosmetic implementation insufficient:

- Detached runs currently fall through to the blue proc lane, while agent/clan row attribution intentionally excludes them.
- A monitor that joins a detached run does **not** become its execution owner. Any design that assumes ownership transfers will lose the activity indicator on that monitor.

## What the current implementation actually does

The observations below come from local source inspection, existing visual baselines, and a small read-only helper probe. I did not consult any other report or researcher in this swarm.

### 1. The requested icon and color already exist

The canonical glyph is `⚒`, with the Tools accent `#87D7FF`. It is shared by ToolRun row/header vocabulary and the Tools deck switcher. The switcher can display `tools ⚒N M`, where N is the run count and M is the provider-call count; it emphasizes live activity. Consequently, the new top-bar count needs an explicit tooltip saying **active SASE tool runs**, since the deck count can include history and provider calls. [S1, S2]

The blue background gear currently uses `#48CAE4`; monitor gears use orange `#FFAF5F`. Reuse these identities. Introducing a wrench emoji, a new hue, or a spinner would weaken an already established visual language.

### 2. The blue gear is a catch-all, not an ownership test

`is_gear_eligible_row()` excludes monitor and service rows. `proc_gear_lane()` then separates update rows and puts everything else in the proc lane. A tool execution proc therefore counts as a blue gear even though it has no TUI completion dependency. Session IDs govern visibility but are deliberately not ownership proof. [S3]

Tool handoff submission already records `origin="tool-run"` and tags `tool-run`, `tool-run:<run_id>`, and, for detached launches, `tool-run-detached`. These are stronger evidence than a command string or display label. [S4]

This also means merely excluding tool-origin rows is not enough to make the remaining blue count strictly “TUI work”: arbitrary standalone or independently launched procs can still enter the fallback lane.

### 3. Restart behavior already has a separate, more precise model

`collect_restart_blockers()` explicitly excludes independent durable commands, tools, monitors, service oneshots, and daemons. It considers TUI worker/submission/completion dependencies and installation mutations instead. Independent work can carry a session ID and still be safe across restart. Existing tests cover that distinction. [S5]

Therefore **do not use the new badge classifier to decide whether restart is safe**. Conversely, do not define the blue count as “restart blockers”: installation work has its own update surface, and completion callbacks can block after the underlying process stops.

### 4. ToolRun glance data is already loaded once for the app

The existing glance snapshot contains active `created` and `running` ledger rows, attribution, owner IDs, parent IDs, progress, stop requests, and timing. Loading is off-thread, coalesced, and protected by store change tokens. Rendering reads the snapshot without opening SQLite or logs. [S6]

There are two important limits:

- Rust caps the machine-wide glance list at **200** rows and exposes `truncated`. `len(snapshot.runs)` is not always an exact count, and it includes nested runs. [S7]
- The fast drift probe is Agents-tab-specific, the initial load waits for the first Agents load, and snapshot application patches agent rows but does not directly update tribe titles or a global Tools indicator. Reusing the loader requires broadening its app-level publication, not just mounting another widget. [S6]

### 5. Individual row badges exist, but detached and clan activity have gaps

The current matcher applies exclusive rules: execution owner first; otherwise the exact agent turn; session containers aggregate unowned runs. It returns no runs for clan and remote rows. The header selector and Runs-card availability similarly exclude clans. Tests assert these exclusions. [S8]

A read-only probe using the checkout's `.venv/bin/python` reproduced this exact case:

```text
Input: one running ToolRun, agent=research.cdx, owner=(proc, p1)

initiating agent row -> []
owner proc row       -> [detached]
clan row             -> []
tool execution proc  -> blue "proc" lane
canonical ⚒ width    -> 1 Rich terminal cell
```

There is another practical gap: Agents-tab named-proc projection only creates rows for standalone macro named procs. A plain `origin="tool-run"` execution proc need not have an Agents-tab node at all. Owner-first attribution can therefore point at a node that is absent. [S9]

### 6. Clan membership and tribe title rendering already provide good extension points

Clan containers keep loaded members in `runtime_children`, plus clan identity and generation. Their primary status intentionally mirrors a lone running member unless user-attention states outrank it. Tool activity should use the membership graph but leave this status rule intact. [S10]

Tribe border titles already append independent monitor, gate, and named-proc badges after agent status metrics. Add a live tool rollup in the same part of the title; do not fold tools into the agent total or `[R… D…]` metrics. [S11]

### 7. Monitor joins require an explicit relationship

Joining a detached ToolRun creates a following monitor while the original proc remains the executor. The existing glance wire has owner information but no join relationship. A join must remain one counted run, and its monitor should still expose that run's activity and detail link. [S12]

This relationship can come from existing authoritative monitor metadata for a TUI adapter, or from an additive Rust projection field for reuse by other frontends. Do not rewrite ownership merely to simplify rendering.

## Adjustments to the requirements

These are deliberate design changes or clarifications, rather than implied original requirements.

| Adjustment | Recommendation and reason |
| --- | --- |
| Tools count scope | Count active top-level ToolRun executions across foreground, detached, handoff, and monitored modes. An identical `sase tool run check` should not change visual category when its execution mode changes. |
| Who launched the tool | Include tools launched from CLI or the TUI catalog too. Launch source is metadata; it should not decide the tool's icon. A tool launched from the TUI can still run independently. |
| Meaning of `bg:` | Make it TUI-associated background operations, using explicit producer/operation evidence and TUI worker overlays. Do not classify every remaining proc as TUI-owned, and do not infer this from `session_id`. |
| Orange monitor gears | Move them into a conditional `mon:` group, retaining their current orange identity. They do not belong under a label reserved for TUI background work. This adds a group, so use existing compact-density rules and hide it at zero. |
| Relationship between counts | Tools count executions; `mon:` counts supervisors; `bg:` counts TUI operations. They are not a grand-total process partition. A monitored tool can appear once in Tools and once in Monitors without being counted twice as a tool. |
| Container counts | A tribe/clan/session shows the union of its members' tool execution IDs, including folded descendants. Collapse changes presentation, not the count. Explicit filters change the represented membership. |
| Unknown and stale data | A failed or capped observation must not silently become “0 tools.” Show a marked last-known value or an unknown/lower-bound value. |
| Process inventory | Keep tool executor rows available in the existing Procs pane and CLI. This feature changes their identity and summaries, not their supervision or inspectability. Independent non-tool procs remain in that inventory and their existing nodes; they are no longer falsely summarized as TUI work. |

The monitor adjustment is the most debatable one. A smaller implementation could leave both gear colors under `bg:`, but then “background” would need to mean all non-tool background activity, contradicting the requested TUI-only meaning. I prefer the precise label and a small conditional monitor group.

For the row location, use the existing `TopBarIndicators` containing `procs:`. The app composes that global strip directly below `UsageHeader`; do not accidentally put Tools into the per-tab `AgentInfoRow` with launch defaults. [S13]

## Proposed visual design

### Global strip: immediate recognition, little movement

Wide layout:

```text
tools: [ ⚒ 3 ] · bg: [ ⚙ 1 ] · mon: [ ⚙ 1 ] · updates: … · stash: … · inbox: …
```

Square brackets here stand for the existing filled-chip style, not literal border characters.

- Tools: dark ink `#1a1a1a` on `#87D7FF`.
- TUI background work: keep the blue gear style.
- Monitors: keep the orange gear style.
- Labels and separators: dim, as in the current strip.
- Zero counts: disappear after a successful authoritative load.
- Tools opens the Tools pane's **Runs** view with the matching active local scope. BG opens the corresponding TUI-operation slice in Procs; Monitors opens the monitor slice.
- Keep position/order stable. Count changes should not reorder widgets.
- Use the existing full/compact density machinery. At compact density retain the monitor label if its otherwise-identical gear would be distinguished only by color.

Tooltip examples:

```text
3 active SASE tool runs on this machine
1 starting · 2 running
Includes foreground, detached, and monitored runs
Open active runs
```

```text
1 TUI background operation in this session
Open background work
```

The Tools indicator is local-machine-wide and independent of Agents filters, tribe selection, and the launch-default project chip. Opening it must use that same scope. An unattributed tool still belongs in the global count; it should be listed as “No agent” rather than attached by a guessed prefix.

If the terminal becomes too narrow for even compact chips, truncate expendable label text first and preserve the Tools glyph/count and notification access. Test actual cell budgets with all groups populated; adding the two short labels is not permission to wrap the global strip onto another row.

### Tribe panels: make collapsed work visible

```text
⌂ @research · 5 [R3 W2] ⚒3
```

Use one sky-blue `⚒3` badge at the end of the existing title metrics. It means **three active tool executions**, not three agents. The title retains tribe identity and selection styling; do not recolor the whole border whenever tool activity starts.

On whole-panel selection, offer the existing Tools action with that panel's run set. It should open an owner-labelled active list. Clicking the Tools badge may provide the same shortcut if the border-title implementation supports reliable hit targets; do not promise a click target that is only decorative Rich text.

Folded panels retain the rollup. Explicit filtering narrows the panel's represented membership, while collapse never drops descendants from the count.

### Clan and session nodes: aggregate activity without changing status

Multiple runs:

```text
▸ research.43 (RUNNING) ⚒3
```

One run:

```text
▸ research.43 (RUNNING) ⚒ check 7/11
```

A clan with one live run can reuse the established name/progress badge. With multiple runs, prefer the short aggregate `⚒3` rather than selecting one member's command and making it look representative of the whole clan. The detail list names the owners and tools.

An asking or failed member still wins primary clan status:

```text
▸ research.43 (ASKING) ⚒2
```

This is useful information: the clan needs input and other members are still executing tools. Tool activity must never suppress the asking/error cue.

### Concrete nodes: improve attribution, preserve familiar vocabulary

Reuse the established adjacent row badge:

```text
cdx (RUNNING) ⚒ check 7/11
cdx (RUNNING) ⚒ test starting
cdx (RUNNING) ⚒ test stopping
cdx (RUNNING) ⚒ check 2m+1
```

Place it immediately after status/finalizer cues, before low-priority metadata that can be truncated. Reserve space for at least `⚒N` when width is constrained; truncate the command label before losing the activity identity.

For detached execution, show the badge on its initiating concrete agent, then aggregate it into its session/clan/tribe, even when there is no executor node. If an executor node is shown elsewhere, it may carry the same badge and run ID. Rollups union IDs rather than summing the rendered badges.

For monitor-owned or joined execution, the monitor node exposes the run and the session/clan/tribe rolls it up. A historical starter turn can show the relationship in details, but should not acquire a misleading “currently executing here” badge after the handoff.

Keep `starting`, `stopping`, elapsed fallback, and existing silence wording. Silence is an activity/observation warning, not proof that a tool failed or is stuck. The global category chip should remain recognizable as Tools; do not turn every live count red because one command is quiet.

### Why this should look better

The design gains coherence by repeating one established identity at three scales: filled global count, restrained container count, and explanatory leaf badge. It adds no persistent progress bars, animation, new palette, or command text to the global strip.

The existing 120×40 ToolRun baseline already shows readable tool/progress badges. The 60×40 baseline shows how readily surrounding metadata clips and detail panes disappear, supporting explicit priority for the icon/count rather than longer row prose. These are existing baselines, not previews of this proposal. [S14]

Distinct glyphs and words also avoid making color the only way to recognize a category. This applies the W3C's [Use of Color guidance](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html) as a terminal design principle, not a claim of terminal WCAG conformance. Tooltips supplement visible labels and keyboard-accessible detail; information must remain available without hover. The W3C's [hover/focus guidance](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html) supports predictable, persistent supplemental content.

## Data and implementation design

### Keep execution identity separate from its display locations

Use two deliberately different operations:

1. **Classify process records.** Recognize a ToolRun executor using recorded `origin`, the exact run tag, and owner relationships. Never inspect label substrings such as `tool:`, command prefixes, or missing session IDs. Update/service precedence remains explicit. TUI-local overlays and known TUI-origin operations provide the remaining BG evidence.
2. **Project run activity into scopes.** Select a scope's related run IDs using exact agent-turn/session membership, proc/monitor ownership, and explicit monitor joins. Dedupe and normalize these IDs into executions, then produce a count and optional primary-run summary.

Shared classification, root/descendant normalization, attribution rules, and completeness semantics belong in **sase-core**, per the repository's backend boundary. Textual state, membership-to-selector glue, rendering, navigation, and repaint scheduling remain in Python. Do not introduce a new Python domain implementation beside the Rust ledger.

There is no need for a new persistent proc kind, another process store, or a migration that rewrites historic rows. These are view categories over existing facts. Use exact tags as a compatibility signal when older rows lack sufficient origin metadata; if facts conflict, mark the row unclassified rather than invent TUI ownership.

### Count executions, not wrappers, stages, or visible rows

Within a scope, count one execution represented by an active ToolRun ancestor and its nested live descendants. A joining monitor is not a second execution. Multiple OS child processes or stages under one ToolRun do not add to the count.

Existing matching folds a child when its live parent is present on the same node. For a robust global/container count, normalize lineage in core before bounded detail truncation. In unusual cases where the parent has settled but a descendant is active, count the remaining live execution branch rather than making it disappear. Do not blindly omit every row with `parent_run_id`.

Keep the three count domains distinct:

- Agent status totals retain the existing agent-only contract.
- Tool totals count normalized active executions.
- A node's Tools deck may show settled history and provider calls as well as active runs.

A short “active” label in the opened Runs list and tooltips makes those differences legible.

### Use explicit memberships, including hidden descendants

A clan is rootless; its name is not an executing agent. Build its selector from the actual generation's members and their session turns/monitor relations, not a name-prefix search.

Calculate rollups from the represented membership before presentation-only collapse. Union execution IDs at every parent:

```text
tribe
  clan
    session
      turn -- detached tool A
      joined monitor -- follows A
    member -- tool B

tribe=2, clan=2, session=1
```

A run's badge can appear on both the container and a child without increasing the parent's count. Deduping by UI row identity is insufficient; the dedupe key is normalized execution identity.

Do not reuse `status_display_source` to obtain a clan's tools. That pointer identifies the member responsible for a status word, and may point at an asking agent while tools run on other members.

Use existing generation/start guards for reused names and exact current member names for session promotion. A long detached run should survive a turn becoming a session; avoid a selector based only on the newest successor's start time.

### Extend the existing projection rather than invent a new poller per surface

Build on the app glance snapshot and Rust lean projection. Add the minimum additive fields/query support needed for:

- exact normalized active totals before the 200-detail-row cap;
- per-scope membership/owner selection;
- the joining monitor relationship;
- known, unknown, stale, and partial coverage.

A practical shape is one app-level immutable activity snapshot containing active summaries keyed by exact agent/owner identities, a local-machine total, a store token/generation, and coverage metadata. If a bounded first version cannot provide exact totals, display a lower bound such as `⚒200+`, never an apparently exact 200. A container whose member is outside the detail cap cannot be declared empty merely because it found no rows in that page.

Any new Rust binding needs binding registration/round-trip coverage and sase's `sase-core-revision.txt` pin advanced past the core commit. The proposed query should remain read-only; liveness reconciliation and settlement stay with the existing backend services.

### Update every relevant surface from one published generation

The current snapshot publication is a good base, but needs to update:

- the global Tools widget on **all tabs**;
- concrete rows whose run badges changed or disappeared;
- clan/session rows affected by changed descendants;
- tribe border titles, including folded panels;
- selected-node detail availability and content.

Do not return early simply because Agents is not selected or has no rows. Publish the global state after startup without waiting for Agents history, while keeping first paint independent of archive-sized work.

Keep existing change-token revalidation and coalescing. For visible active work, aim for changes to appear within approximately two seconds, matching the existing drift cadence; measure this as a target rather than treating it as a guarantee. Idle ticks should not repeatedly reopen SQLite. Do not perform per-panel queries in render, navigation, or a serial awaited timer callback.

Textual's [Workers documentation](https://textual.textualize.io/guide/workers/) recommends running slow operations concurrently and marshaling thread-driven UI changes onto the main thread. SASE's audited `tui_perf.md` adds stricter pump-free scheduling, selective patching, and unchanged-surface rules; preserve those.

Patch affected titles/rows without rebuilding all tribe panels. Badge appearance/disappearance must invalidate width/layout caches as well as text tokens. Preserve selection, scroll position, and any pending selected-run reveal after asynchronous loads.

### Make stale and absent data visibly different

Suggested states:

| Observation | Global display |
| --- | --- |
| Successful, complete, no active runs | Hide Tools |
| Successful, complete, 3 active executions | `tools: ⚒ 3` |
| Initial load pending | Dim `tools: ⚒ …` |
| Read failed after last known 3 | Dim `tools: ⚒ 3?`; tooltip gives last successful observation |
| Read failed before any successful observation | Dim `tools: ⚒ ?` |
| Detail list capped without exact aggregate | `tools: ⚒ N+`; opened view explains partial coverage |
| Required binding unavailable | `tools: ⚒ ?`; details explain unavailability once, no toast loop |
| Remote node with no remote ToolRun projection | “Tool activity unavailable on <machine>,” not zero |

Start-up placeholders can be brief, but unknown cannot be represented as a known zero. Preserve last-known data during transient failures and remove its certainty marker only when a successful new observation arrives.

Remote fleet aggregation is a separate transport problem. Support local clan nodes now. For mixed local/remote membership, report a marked local subset or unknown total; do not advertise a complete zero or full count from the machine-local ledger.

### Reuse existing drill-down and stop flows

Global Tools opens the existing Admin Center Tools Runs view. Concrete badges reveal the corresponding Runs card/block. Containers open a scoped active list with agent/owner labels; they must not offer an action that reveals a blank clan deck.

For a first implementation, a clan or whole tribe can route to the scoped Runs pane rather than require a complete historical clan Tools deck. This makes the badge useful without broadening the feature into history aggregation.

Pass run IDs and selectors through the action. The click must not merely reopen whichever stale project/filter bookmark happened to be used previously. If a run settles between observation and activation, keep its row/detail available as the recent result. Reuse `sase tool stop` and the existing owner-aware confirmation path; do not invent a separate kill action tied to the icon.

## Alternatives and tradeoffs

| Approach | Strength | Limitation | Judgment |
| --- | --- | --- | --- |
| Origin-only split: remove `tool-run` procs from blue count and add a proc-based hammer count | Smallest diff; directly fixes the reported detached case | Misses foreground tools, join relationships, clan attribution, partial counts, and strict TUI-only BG semantics | Suitable only as a clearly limited interim step |
| ToolRun projection plus process classification, reusing existing views | Consistent identity across modes; accurate scope/count semantics; solves clan and absent-owner-node gaps | Some Rust/API and refresh work, plus more precise BG/monitor labeling | Recommended |
| New universal Activity tab/pane | Could unify all agents, tools, procs, and monitors | Navigation and lifecycle scope far exceed this request; duplicates existing Runs/Procs surfaces | Defer |

I would not add a second row badge at the start of every agent name, replace RUNNING with a new TOOL status, animate borders, or create dedicated tool nodes by default. The existing adjacent badge and aggregate hierarchy provide discovery without rewriting the tree.

## Verification that matters for implementation

The following are proposed acceptance checks, not claims that the feature was implemented or tested in this research turn.

1. **Classification and scope:** detached `tool-run` procs leave the blue lane even with a session ID; TUI `tool.stop` control operations remain BG when appropriate; update/service identities retain precedence; independent non-tool procs are not relabelled TUI-owned.
2. **Execution identity:** nested runs, repeated display locations, and a monitor join count one execution; parallel independent roots count separately; a live descendant with a settled/missing ancestor stays visible.
3. **Attribution:** detached tools appear on initiating agent nodes when no executor node exists; monitored/joined tools appear on their monitor and aggregate through sessions/clans/tribes; clan status precedence remains intact.
4. **Membership changes:** collapse preserves counts; an explicit panel filter changes scope; reused clan/agent names and session promotion do not leak historical runs or lose ongoing ones; merged tribe panels dedupe IDs.
5. **Refresh:** starting/stopping/settlement updates all badges and titles without selection jumps; switching tabs does not freeze the global count; startup on Services still discovers tools; a settled last run removes the container badge.
6. **Uncertainty:** a locked/busy store, missing binding, missing store, more than 200 live rows, or unavailable remote data cannot produce a false exact zero/count.
7. **Navigation:** each indicator opens its advertised scope; a settled-between-click-and-open run remains inspectable; container drill-down works; keyboard users can perform the same actions.
8. **Visuals and performance:** review 60/80/120/160-column captures with tools, BG, monitors, updates, stash, and inbox populated; inspect collapsed clans/panels, mixed asking-plus-tool activity, digit-width transitions, and monochrome meaning. Check idle file-open counts and navigation latency; avoid per-row ledger reads.

Existing starting points include `test_proc_gear_lanes.py`, `test_tool_runs_glance.py`, `test_tool_runs_header_chip.py`, top-bar/panel-title tests, and restart lifecycle tests. Rewrite the explicit “clans never match” assertions for the new supported behavior. Inspect targeted visual golden changes using the project's screenshot workflow, and follow the prescribed implementation verification gate; a research-only report does not require running the product suite.

## Evidence references

These links point to the exact source revisions inspected locally. They are citations, not web-fetched repository content.

| ID | Source and relevant responsibility |
| --- | --- |
| S1 | [view_vocabulary.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/tool/view_vocabulary.py#L20): canonical glyph/accent, state words, row chip |
| S2 | [tool_runs/deck.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/tool_runs/deck.py#L137): Tools switcher; run/history versus provider-call counts |
| S3 | [_proc_observer_models.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/_proc_observer_models.py#L153): eligibility, lane classification, session visibility |
| S4 | [handoff_launch.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/tool/handoff_launch.py#L103), [handoff.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/tool/handoff.py#L188), [detach.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/tool/detach.py): origin/tags and starter-bound detached lifetime |
| S5 | [update_restart.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/update_restart.py#L189), [_update_restart_blockers.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/tests/ace/tui/_update_restart_blockers.py#L105): restart dependency semantics |
| S6 | [snapshot.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/tool_runs/snapshot.py), [loader.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/tool_runs/loader.py#L64): cached glance, load gating, per-tab apply, row patching |
| S7 | [Rust glance.rs](https://github.com/sase-org/sase-core/blob/646058197f5ced5231ed478b8a716678007f0156/crates/sase_core/src/tool_run/projection/glance.rs#L22), [Rust projection wire.rs](https://github.com/sase-org/sase-core/blob/646058197f5ced5231ed478b8a716678007f0156/crates/sase_core/src/tool_run/projection/wire.rs#L24): active states, 200-row cap, attribution fields, node selectors |
| S8 | [attribution.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/tool_runs/attribution.py#L117), [summaries.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/tool_runs/summaries.py#L70), [test_tool_runs_glance.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/tests/ace/tui/test_tool_runs_glance.py#L98): owner-first chips, inclusive history, clan/remote exclusions |
| S9 | [agent_named_procs.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/models/agent_named_procs.py#L94): standalone macro proc projection |
| S10 | [_agent_tree_clan.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/models/_agent_tree_clan.py#L119), [_agent_clan.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/models/_agent_clan.py#L126): actual clan members/generation and status-source inheritance |
| S11 | [_display_panel_titles.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/actions/agents/_display_panel_titles.py#L96): panel-only counts and supplementary badges |
| S12 | [monitor/join.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/monitor/join.py#L1), [join_worker.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/tool/join_worker.py#L1): joining monitor follows the original executor |
| S13 | [_app_layout.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/_app_layout.py#L102), [top_bar.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/widgets/top_bar.py), [top_bar_group.py](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/src/sase/ace/tui/widgets/top_bar_group.py): global row placement, density, chip grammar |
| S14 | [120×40 baseline](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/tests/ace/tui/visual/snapshots/png/tool_runs_rows_120x40.png), [60×40 baseline](https://github.com/sase-org/sase/blob/3412a9f1bdc51737beb8ed38449530e1ea0b4c60/tests/ace/tui/visual/snapshots/png/tool_runs_rows_60x40.png): existing visual inspection, not new feature previews |

The probe verified current classification and attribution only. No live-host activity census, new UI prototype, implementation, or performance benchmark was run. Timing and aesthetics above are proposed acceptance targets and design judgments.

## Recommended solution

Implement the feature as a focused extension of the existing ToolRun surfaces: **one canonical ⚒ identity, one normalized active execution count, and the same run IDs projected into concrete nodes, sessions, clans, and tribe panels**.

Use `tools:` for all active local SASE ToolRuns, reserve `bg:` and blue gears for explicitly TUI-associated operations, and give independent monitors a conditional `mon:` label. Keep primary agent/clan status, restart policy, process lifetimes, and existing process inventory governed by their current models.

Build the shared classification/count/relationship behavior in sase-core; extend the existing app snapshot and selective refresh path; reuse the Runs pane/card for every badge's drill-down. Treat joins, collapsed membership, missing executor nodes, and incomplete observation as first-class acceptance cases. This is a worthwhile change when implemented as a clear activity model with restrained presentation, rather than as an icon substitution alone.
