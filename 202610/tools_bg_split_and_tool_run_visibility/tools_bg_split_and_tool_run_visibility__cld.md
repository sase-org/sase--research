# `tools:` and `bg:` — giving agent tool runs their own identity in the TUI

_Researcher: cld · 2026-10-08 · sase master `3412a9f1bd`_

## TL;DR

The idea is good, and the data on this machine backs it up. The blue `procs:` gear is
mostly agent `sase tool run check` executions, not work the TUI started. Taken
literally, though, the request has four problems:

1. **It counts the wrong noun.** Whether an agent's `sase tool run` becomes a proc
   depends on its LLM provider. Claude and muse agents have a sync ceiling, so their
   runs are "inline-escalated" into detached `tool-run` procs. Other providers run in
   the foreground with no proc at all. A `tools:` count built from procs would depend on
   which model an agent uses. **Count live ToolRuns from the ledger, not procs.**
2. **The tribe/node problem is a bug, not a styling gap.** Today a ⚒ row chip only goes
   to runs with *no owner*. Every inline-escalated run is owned by a `tool-run` proc,
   and that proc has no Agents-tab row. So **none of the three `check` runs live on this
   machine right now shows a ⚒ on any row**, even though the identity header (which
   uses an inclusive matcher) would show it. Fix attribution first. That fix also covers
   clans.
3. **The orange monitor chip needs a home.** About 81% of retained monitor procs exist
   to carry a ToolRun (`_adopt` or `_join`). One agent-owned check shows as blue ⚙ plus
   orange ⚙ today when a monitor joins it, and would show as ⚒ plus orange ⚙ under the
   literal plan. I recommend one rule everywhere: **"⚒ beats ⚙"**. A live tool run is
   always drawn as ⚒, and an orange ⚙ appears only for a monitor that is *not* carrying a
   tool run. Those monitors move into `tools:` with the runs.
4. **`bg:` will not be "TUI-only" by construction.** After tool runs leave, the blue
   lane still counts `cli`, `api`, `telegram`, `axe`, `prompt-proc`, gate/sudo-answer
   and other procs. On this machine it is roughly 100% TUI `ace` procs in practice. I
   recommend keeping the "everything else" rule and saying so in the tooltip, rather
   than narrowing the lane.

Two reliability bugs have to be fixed along the way:

- Agent-submitted `tool-run` procs are stamped with whichever TUI session started most
  recently. They silently drop out of the count after every TUI restart.
- The live ToolRun snapshot only refreshes while the Agents tab is showing.

**Recommended top bar:** `tools: ⚒ 3 · bg: ⚙ 1 · stash: ≡ 2 · inbox: ⚑1 ✉18`. The
`tools:` group can also hold a red `⚒⚠ N` chip for silent runs and an orange `⚙ N` for
monitors that carry no run. Rows, clan rows, and tribe-panel titles get ⚒ through the
same attribution. §9 has the full recommendation.

---

## 1. What I examined

- **Code:** top-bar groups (`widgets/top_bar.py`, `top_bar_group.py`,
  `proc_indicator.py`, `proc_gear_chips.py`); proc lanes and scoping
  (`_proc_observer_models.py`, `_proc_observer_store.py`, `_proc_action_observer.py`);
  how `sase tool` creates procs (`tool/handoff_launch.py`, `tool/detach.py`,
  `tool/inline_escalation.py`, `tool/executor_entry.py`, `tool/handoff.py`); monitor
  start, adopt and join (`monitor/start_launch.py`); the ToolRun glance pipeline
  (`tool_runs/snapshot.py`, `loader.py`, `attribution.py`, `header_chip.py`,
  `core/tool_run_views.py`); tribe-panel titles (`_display_panel_titles.py`); clan
  aggregation (`models/_agent_clan.py`, `_agent_tree_clan.py`); quit and restart guards
  (`quit_impact.py`, `update_restart.py`); `docs/ace.md`.
- **Prior design:** `plan:202609/tool_runs_tui_surfaces.md`, read through
  `sase artifact read`. Its decisions D1, D3, D8, D15, the §3.3 attribution table and
  the §6 deferral table all bear directly on this request.
- **Live data on athena:**
  - Retained proc store: `~/.sase/procs/procs.jsonl`, 180 rows.
  - Live ToolRun glance: the read-only `tool_run_live_glance()`.
- **Visuals:**
  - Existing PNG goldens: `tool_runs_rows_120x40`, `tool_runs_header_live_120x40`,
    `agents_named_procs_120x40`, `agents_tribe_panel_clan_summaries_glance_120x40`,
    `config_center_procs_tab_monitors_120x40`.
  - Static Rich mockups of the proposed top bar, rasterized with the project renderer
    (`render_svg_to_png`).
- **Not done:** I deliberately did not launch a live TUI or `sase screenshot`. A newly
  registered TUI session becomes `latest_session()`, so agent tool-run procs submitted
  meanwhile would be stamped with the throwaway session (see §2.3). That would perturb
  your real TUI's counts.

## 2. How it works today

### 2.1 The top bar

Row 1 is `UsageHeader`: title plus provider usage. Row 2 is `TopBar`, which holds the
tab strip and a right-aligned cluster of labeled groups (`widgets/top_bar.py:28-34`):

```
procs: [⚙ 3][⚙ 1] · updates: … · overrides: … · stash: [≡ 2] · inbox: ⚑1 ✉18
```

So the requested `tools:` group belongs in this cluster, next to the renamed group.

- The blue chip (`PROC_GEAR_HUE = "#48CAE4"`, `proc_gear_chips.py:23`) counts active
  rows in the `"proc"` lane.
- The orange chip (`#FFAF5F`) counts monitor turns.
- `proc_gear_lane` (`_proc_observer_models.py:227`) sends a row to `"monitor"` when
  `origin == "monitor"`, to `None` for service rows, to `"update"` for update rows, and
  to `"proc"` for everything else.
- Tool runs are not special-cased anywhere. Nothing in the lane code reads the
  `tool-run` tag or origin.
- Counts are pushed from `_update_proc_indicator` (`actions/_proc_action_observer.py`,
  around line 141) after each observer snapshot (0.5 s poll).

`docs/ace.md` (around line 5216) already promises that the blue chip is "sase's TUI own
procs". Tool runs break that promise today.

### 2.2 The four ways `sase tool` creates a proc (origin `tool-run`)

All four go through `submit_handoff_run` (`tool/handoff_launch.py`). It writes
`origin="tool-run"` (line 113) and the tags `tool-run`, `tool-run:<run_id>`, and
optionally `tool-run-detached` (`tool/handoff.py:188-194`).

| Path | Who triggers it | Notes |
| --- | --- | --- |
| **Inline escalation**: a plain `sase tool run X` inside an agent whose provider exports a sync ceiling | Agent | Claude always does (`llm_provider/claude.py:85-100`, resolved in `executor_entry.py:98-110`); muse too. The run is detached (`inline_escalation.py:112`) and followed within the budget. **This is the dominant path.** |
| `sase tool run -d` | Agent | Explicit detach; records a `starter` |
| `sase tool run -H` | Human shell | Refused when `SASE_AGENT` is set |
| Admin Center → Tools catalog `r` | **Human, from the TUI** | `launch_catalog_tool` calls `-H` in-process (`actions/agents/_tool_run_actions.py:190-220`) |

So "tool-run procs are created by agents" is *mostly* true, but not always. The catalog
`r` path is a TUI user action that produces the same kind of proc.

Many ToolRuns create **no** `tool-run` proc at all:

- Foreground runs from providers without a sync ceiling: the owner is `None` and
  `agent` is the agent's name.
- Foreground runs from a human shell.
- Monitor-owned runs from `sase monitor start -- sase tool run …`. The monitor proc
  itself adopts the run (`sase tool _adopt`).
- `: tool run X` from the Command Line, which becomes an `origin="ace"` proc that owns a
  foreground run.

### 2.3 What the blue gear actually counts, and a session bug

`ProcProjection.active_rows` (`_proc_observer_models.py:314`) counts active rows that
either have no `session_id` or have this TUI's live session.

`submit_handoff_run` stamps `session_id = resolve_session_ref(None)`
(`handoff_launch.py:101`). In an agent or shell process the process's own id is never
registered as a session, so `_resolve_current()` falls through to **`latest_session()`**
(`sessions/registry.py:206-211`), which is the most recently started live TUI.
Consequences:

- **Agent tool runs are attributed to a TUI that never started them.** This is how they
  end up in "this session" and in the blue gear.
- **After each TUI restart, still-running tool procs disappear from the count.** Their
  session is now dead (`session_live=False`), and `active_rows` drops them.
- **With two TUIs open, the newest one claims all of them.**

Evidence from the retained store on athena:

| origin | rows | session-stamped |
| --- | --- | --- |
| `service-host` | 63 | 0 |
| **`tool-run`** | **49** | **49** (spread over 6+ TUI session ids today, one per restart) |
| `ace` | 36 | 36 |
| `monitor` | 32 | 0 |

All 49 `tool-run` rows are `tool:check` and all are tagged `tool-run-detached`, which is
inline escalation from agents. **Tool runs outnumber the TUI's own procs in the blue
lane.** Your premise holds.

The quit and restart guards already ignore these procs. `quit_impact.py` excludes all
durable procs (module docstring, lines 3-6). `update_restart.py:192` says: "Independent
durable commands, tool runs, monitors, oneshots, and service daemons are not restart
dependencies." The rename is about meaning, not about guards.

### 2.4 The ToolRun glance and why rows don't show ⚒

`tool_runs/snapshot.py` holds an app-level snapshot of every unsettled run on the machine
(Rust `tool_run_live_glance`). Each run carries:

- `owner_kind` / `owner_id`
- `agent` (for hand-offs this is the starter)
- `launch_mode` (`"handoff"` or `None`)
- `parent_run_id`, stage progress, `typical_ms` and `last_activity_ts`

Silent means no sample for at least 60 s.

Row chips come from `select_live_runs` (`tool_runs/attribution.py:117-172`). Its rules
are exclusive:

- A monitor row takes runs owned by that monitor.
- A named-proc row takes runs owned by that proc.
- An agent or session row takes **only runs with no owner** (lines 162, 169).
- Clan and remote rows get nothing.

An escalated or `-d` run is owned by a `tool-run` proc. Those procs never become
Agents-tab rows; only `prompt-proc` procs do. So the run is attributed to nobody. The
glance taken during this research shows exactly that:

```
3 live runs, 0 silent, not truncated
check  running  owner=proc:6nnsaqrjmgwk  mode=handoff  agent=sase-1i5.9.1.2.1.5
check  running  owner=proc:552ydt23v6zc  mode=handoff  agent=sase-1id.5--1
check  running  owner=proc:kq2cdsrh94n0  mode=handoff  agent=toobig-7f.plan_decisions.0
```

None of these three gets a row chip. The identity header *would* show them, because
`node_live_runs` in `summaries.py` matches on `agent` **or** owner. So the row and the
header disagree. One of the three starters is a clan member, so clan support matters in
practice.

The join case is also invisible. When a monitor joins a detached run
(`sase tool _join RUN`):

- The run stays owned by the `tool-run` proc.
- The joining monitor proc carries **no** `tool-run:<id>` tag; `proc_tags` stays `[]`
  on the join branch (`monitor/start_launch.py:276-298`).
- The glance has no join field.

As a result the chip lands on neither the monitor row nor the starter.

Finally, the glance is only probed and applied while the Agents tab is current
(`loader.py:154` and `:181`), gated from the 1 s countdown tick. Off that tab the
snapshot goes stale. That is fine for rows but not for a top-bar chip.

### 2.5 Monitors overlap heavily with tool runs

Of the 32 retained monitor procs on athena:

- 16 are `sase tool _adopt <run>` (monitor-owned ToolRuns, tagged `tool-run:<id>`).
- 10 are `sase tool _join <run>` (joined detached runs, untagged).
- 6 are something else: dev-update `code_swap_guard`, epic-launch monitors, and one raw
  `just fix-tui-screenshots`.

So **26 of 32 monitors (81%) exist to carry a ToolRun.** A joined check today shows as
**blue ⚙1 plus orange ⚙1** for what is one tool run.

### 2.6 Prior decisions this request touches

From `plan:202609/tool_runs_tui_surfaces.md`:

- **D1:** "One noun, one glyph. `⚒` means ToolRun everywhere." The request applies this
  rule to the top bar. ✅
- **D3:** "No counts on rows … ever in v1." This still holds. Rows keep the existing
  `+N` overflow form, not a count. Panel *titles* are not rows and already carry lane
  counts.
- **§3.3:** "Clan container, tribe: None in v1 (members carry their own)." **Reopened**
  by your explicit ask.
- **D15:** remote rows get no chip because the ledger is machine-local. **Keep.**
- **§6 deferral:** "a top-bar `⚒N` live count — reopen when … E7 admission gives the
  count a capacity meaning." I argue it is reopened, for two reasons:
  - Tool runs are *already* counted in the top bar, anonymously, as blue gears. This
    change reclassifies an existing count; it does not add a new one.
  - Concurrent `check` runs are the host-load signal the project already treats as the
    constraint (decision `two-speed-verification`: "host capacity is the constraint").
    When tool admission lands, the chip can become a `⚒ 2/4` gauge.

## 3. Critique: is this a good idea?

**Yes.** The blue gear currently answers "is an agent running `just check`?" while
claiming to answer "is my TUI busy?". Separating the two is a real improvement, and the
⚒ identity already exists across rows, headers, cards, the Procs pane and notifications.
What needs correcting:

| # | Issue in the literal plan | Why it matters | Correction |
| --- | --- | --- | --- |
| C1 | `tools:` counts `tool-run` **procs** | Proc creation depends on the provider. Codex/Gemini foreground runs and monitor-adopted runs would be missing, and the count would change if you switched an agent's model | Count **live ToolRuns** from the ledger glance |
| C2 | The orange monitor chip stays in `bg:` | Monitors are agent-created and not TUI-linked, so by your own criterion they don't belong in `bg:`. 81% of them are tool-run carriers and would double-count | Move into `tools:` under "⚒ beats ⚙" |
| C3 | "`bg:` = only TUI-associated procs" | Not true by construction; other origins remain (§2.3) | Keep the "everything else" rule and make the tooltip list initiators (or narrow it, §8 Q1) |
| C4 | "Make it clearer in panels/nodes" is treated as styling | The real blocker is attribution: escalated and joined runs show on no row | Fix attribution, then add the clan aggregate and title counts |
| C5 | Silent on session attribution | Tool procs are stamped with a TUI session they don't belong to and vanish from counts after a restart | Stamp `session_id=None` unless the submitter *is* the TUI |
| C6 | Silent on freshness | The glance refreshes on the Agents tab only | Make the stat probe tab-independent |
| C7 | Silent on zombies | The plan's own evidence includes a 52-hour "running" zombie; an unsettled ledger row would inflate ⚒ forever | Split silent runs into a red `⚒⚠ N` chip; the TUI never reconciles (D4) |

## 4. Requirement adjustments (called out explicitly)

- **R1 — `tools:` counts live ToolRuns, not tool procs.** It counts every run in state
  `created` or `running` on this machine. Child runs whose parent is also live are
  folded in. Owner and launch mode don't matter (foreground, proc hand-off, monitor
  adopt or join, shell, TUI catalog). *Why:* one noun and one glyph (D1), independent of
  provider.
- **R2 — One rule: "⚒ beats ⚙."** Any proc that is carrying a live tool run is shown
  only as that ⚒. This covers a `tool-run` proc, an adopt or join monitor, and a TUI proc
  that owns a run. Orange ⚙ means "a monitor turn running something that is not a tool
  run". Blue ⚙ means "other background procs". It applies to the top bar, the Procs-tab
  header and tribe-panel titles. *Why:* removes today's blue-plus-orange double count
  and makes every glyph mean exactly one thing.
- **R3 — The orange monitor chip moves from `procs:` to `tools:`.** *Why:* monitors are
  agent-created and outlive the TUI, and the glossary frames a monitor turn as "a tool
  result arriving". After R2 it is rare (about 19% of monitors).
- **R4 — `bg:` means "background procs that aren't tool runs, monitors, SASE updates, or
  service procs".** In practice that is roughly the TUI's own work. The tooltip says who
  started each one. I am *not* narrowing it to `origin == "ace"`; see §8 Q1.
- **R5 — Silent runs get their own red chip** (`⚒⚠ N`) in `tools:` and in tribe titles,
  using the existing silent vocabulary. Being past the typical duration (amber) stays a
  row-only signal; the top bar shows only live vs silent.
- **R6 — Clan nodes get an aggregate ⚒ chip** that mirrors the existing clan *status*
  rule. With exactly one live run among the members, the clan row shows that run's chip.
  With more, it shows the primary run plus `+N`. Remote clans still get nothing (D15).
- **R7 — Correctness fixes are in scope:**
  - session stamping of tool procs
  - `tool-run:<id>` tags on join monitors
  - starter and join attribution for row chips
  - a tab-independent glance probe

  Without these the new indicators would be wrong in the most common case.

## 5. Design

### 5.1 Vocabulary (one glyph per noun)

| Glyph | Fill | Means | Where |
| --- | --- | --- | --- |
| `⚒` | `#87D7FF` (`TOOL_RUN_ACCENT`, the Tools-deck identity) | live tool run | top bar `tools:`, rows, titles, Procs pane marker, header, cards |
| `⚒⚠` | `#FF5F5F` | silent tool run (no activity for 60 s or more; "silent is not lost", D4) | same |
| `⚙` | `#FFAF5F` | monitor turn **not** carrying a tool run | top bar `tools:`, titles, monitor rows |
| `⚙` | `#48CAE4` | other background proc (TUI work) | top bar `bg:`, Procs header |

Chips keep the existing filled grammar from `icon_count_chip`: dark ink `#1a1a1a` on
the hue, hidden at zero.

### 5.2 Top bar: the `tools:` group

```
today        procs: [⚙ 3][⚙ 1] · stash: [≡ 2] · inbox: ⚑1 ✉18
recommended  tools: [⚒ 2][⚒⚠ 1][⚙ 1] · bg: [⚙ 1] · stash: [≡ 2] · inbox: ⚑1 ✉18
common case  tools: [⚒ 3] · stash: [≡ 2] · inbox: ⚑1 ✉18
compact      [⚒ 2][⚒⚠ 1][⚙ 1] · [⚙ 1] · [≡ 2] · ⚑1 ✉18
```

I rendered these with the project rasterizer.

- The filled `#87D7FF` ⚒ chip and the `#48CAE4` ⚙ chip are clearly distinct: the tool
  chip is lighter, and the glyph and the ` · ` separator separate them at compact
  density.
- An *unfilled* ⚒ variant read as weak and out of family. **Use filled chips.**
- `tools:` goes immediately left of `bg:`, so the agents' verification load sits apart
  from the TUI's own work but next to it.

**Specification:**

- **Count source.** Live runs come from the glance snapshot and are authoritative.
  - A run counts as live when its state is `created` or `running`, including
    "starting" and "stopping".
  - It is silent when `now − last_activity_ts ≥ silent_after_s`.
  - Children are folded when the parent is live.
  - If `truncated`, render `⚒ N+`.
- **Fallback.** If the glance is unavailable (binding missing, store absent, load
  failing), count the distinct `tool-run:<id>` tags among active procs. Never render 0
  because of a read failure. The tooltip says "ledger unavailable — counting tool procs".
- **Monitor chip.** Count active monitor rows that carry no `tool-run` tag (after fix
  P0b), so this needs no glance at all.
- **Tooltip.** Up to 5 runs, silent first, then oldest, using the existing chip text,
  followed by a footer:

  ```
  3 live tool runs on athena
    ⚒ check  sase-1id.5--1               7/11 · 20m
    ⚒ check  toobig-7f.plan_decisions.0  9/11 · 31m
    ⚒⚠ test  0y9--mon                    silent 48m
  1 monitor turn not running a tool: acme--mon
  Click to open Admin Center › Tools
  ```

- **Click** opens Admin Center → Tools → Runs, live runs first and all projects. The
  count is machine-wide, so the pane must not open project-filtered, or it would show
  fewer runs than the chip claims.
- **Scope** is machine-wide, matching the ledger and the all-projects Agents tab. It is
  never session-scoped: tool runs are not TUI-owned, which was the point of the request.

### 5.3 Top bar: the `bg:` group

- `GROUP_LABEL = "bg"` (was `"procs"`). Body: the blue chip only.
- Count: gear-eligible active rows (as today) **minus** rows tagged `tool-run`. When the
  glance is available, also minus procs that are the `owner_id` of a live run; that
  covers the `: tool run` case.
- Tooltip: "2 background procs · 1 from this TUI · 1 from `sase proc run`. Click to open
  the Procs tab."
- Click: the Procs tab, unchanged.

### 5.4 Agents tab: nodes, clans, tribe panels

**Attribution.** These rules extend `select_live_runs`. They are exclusive and applied
in order:

1. Owner has a node: a monitor row for `owner_kind=monitor`, a named-proc row for
   `owner_kind=proc` when that proc is a node.
2. **Joined monitor** (new). The monitor row whose monitor joined the run. This bypasses
   the node's `since_ts` guard, because the run predates the monitor.
3. **Hand-off starter** (new). `owner_kind=proc`, `launch_mode=handoff` and `agent` set
   go to the starter's agent row, or to its session container by the existing name
   matching. This rule fixes the three runs that are invisible today.
4. No owner: the agent row whose name matches `agent` (existing).
5. Session container: the union of its members (existing).
6. **Clan container** (new). The union of its members, deduplicated by `run_id`, with
   children folded. Remote clans get nothing (D15).

Build the `run_id → node` map **once per snapshot generation** and reuse it for rows,
clan rows and titles. Never scan per row inside a render.

**Rows.** The chip format is unchanged (it already looks right in the
`tool_runs_rows_120x40` golden):

```
[agent] 🤖 sase-1id.5--1 (RUNNING) ⚒ check 7/11 …          ← now visible (rule 3)
▸ toobig-7f (RUNNING) ×3 [R2 D1] ⚒ check 9/11+1 …           ← new clan aggregate
    ⚙ 0y9--mon (RUNNING) ⚒ check 9/11 …                     ← joined run on monitor (rule 2)
```

- The status word stays a lifecycle word. Do not add a `TOOLING` status: ⚒ is activity,
  not lifecycle, and a new status would fight the clan status-mirroring rule.
- Clan rows show the aggregate whether collapsed or expanded, matching how session
  containers aggregate today.

**Tribe- and clan-panel titles.** `AgentPanelCounts` gains `live_tool_runs` and
`silent_tool_runs`. They render immediately after the status chip and before the other
lane badges, as text glyphs in title style:

```
⌂ @default · 9 [R2 D7] ⚒1 ⚒⚠1
❖ ▲ @epic · 5 [R2 D3] ⚒2 ⚙1 ⋔1
```

- Under R2, the orange "running monitors" badge excludes monitors that carry a live run.
  Settled monitors (grey) are unchanged.
- Collapsed and rail titles (`rail_panel_title`) also show `⚒N` while any run is live.
  A collapsed panel hides its rows, so the title is the only signal left.
- These counts stay out of `metric_items`, which keeps the "status counts sum to lanes"
  invariant.

**Optional:** in the tribe and clan Summary cards, add a line such as
`⚒ 2 live tool runs`.

**Refresh.** When a snapshot is applied:

- patch rows whose chip changed (existing)
- patch clan rows whose aggregate changed (new; today they are never patched)
- repaint only the titles of panels whose ⚒ counts changed

Keep it off the 1 s title path. Titles already rebuild on row patches.

### 5.5 Procs tab header

- Show `[⚒ n][⚙ bg][⚙ mon]`, where ⚒ counts procs carrying a run, with tooltip copy to
  that effect.
- This ⚒ can legitimately be smaller than the top bar's, because foreground runs have
  no proc.
- Keep the existing invariant comment ("blue chip must equal the top-bar blue gear") for
  `bg:`.

### 5.6 Reliability and performance contract

- **The glance probe runs on every tab.**
  - It remains stat-only (two `stat` calls, ≤ 1 per 2 s) and keeps the NavigationGate
    and prompt deferrals.
  - Loads stay off-thread and pump-free with the 250 ms busy timeout (`tui_perf` rules
    2, 8 and 14).
  - Applying a snapshot updates the top-bar chip on every tab. Row and title patches
    happen only on the Agents tab, with one reconcile on switching back to it.
- **Lane classification is tag-based** and needs no glance. `bg:` and the orange chip
  therefore stay correct even if the ledger is unreadable, and `bg:` can never
  double-count a tool run.
- **Bounded latency.** A run appears or disappears within about 2 s of a ledger write.
  Today it never appears off the Agents tab.
- **No UI path reconciles or settles runs** (D4). Silent runs stay red until their owner
  or a backend reconcile settles them. The tooltip names the run and points at stop
  (D12).
- **Render paths read memory only**, so there is no new I/O and no new timer.

## 6. Alternatives considered

| Option | Verdict |
| --- | --- |
| **Literal ask.** `tools:` counts active `tool-run` procs; orange stays in `bg:` | Rejected as the end state. It is provider-dependent, misses foreground and adopted runs, keeps the join double count and the restart drop-out, and leaves `bg:` holding agent monitors. Fine as a stepping stone only. |
| One group `bg: [⚒][⚙][⚙]` | Rejected. It is narrower, but files agent verification under "background" again, which is the confusion being fixed. |
| `⚒N` next to `load:` on the Agents info row instead of the top bar | Not instead of, but a good later complement once tool admission exists (`tools: 2/4` gauge). Alone, it vanishes on other tabs and leaves the top-bar blue gear wrong. |
| Drop the orange chip from the top bar entirely | A reasonable fallback if "⚒ beats ⚙" feels too clever. It is simpler, but non-tool monitors (CI waits, dev-update guards, epic launches) lose their glanceable count. |
| A `TOOLING` status word or a spinning ⚒ | Rejected. Status is lifecycle, and the clan status-mirroring rule would conflict. No new repaint loops (D6, `tui_perf`). |
| Narrow `bg:` to `origin == "ace"` plus session workers | Defensible, see §8 Q1. Costs: `sase proc run`, Telegram epic launches and gate/sudo-answer procs vanish from the top bar. |

## 7. Implementation plan

**Phase 0 — fix at the source** (small; Python plus one sase-core wire field)

- **P0a.** `tool/handoff_launch.py:100-104`: stamp `session_id` only when the current
  process *is* a live registered TUI session (the catalog `r` path). Otherwise use
  `None`. Never fall back to `latest_session()` for tool procs.
- **P0b.** `monitor/start_launch.py` join branch (276-298): set
  `proc_tags = ["tool-run", f"tool-run:{run_id}", "tool-run-join"]`. Only the Procs
  pane reads `tool-run:<id>` today, and it will then mark joined monitors with ⚒ and
  open the run on Enter, which is the desired behavior.
- **P0c.** In the linked `sase-core` checkout:
  - Expose `joined_monitor_id` on the `tool_run_live_glance` wire.
  - Add the field to `ToolRunGlance` (`core/tool_run_views.py:97-122`).
  - Move sase's `sase-core-revision.txt` pin.

  This belongs in core under the Rust boundary rule, because attribution facts must
  match across frontends.

**Phase 1 — top bar** (lands atomically; no flag needed)

- `_proc_observer_models.py`:
  - add `is_tool_run_row` (tag `tool-run` or origin `tool-run`)
  - add a `"tool"` lane
  - `ProcGearLanes` gains `tool_run_ids`, `bg`, and `monitors` (non-carrying)
  - keep one pure helper for "⚒ beats ⚙", shared by the top bar, the Procs header and
    titles
- New `widgets/tools_indicator.py`, a `ToolsIndicator(TopBarGroup)` with
  `GROUP_LABEL = "tools"`. `ProcIndicator` becomes `bg`, blue only.
- `widgets/top_bar.py`: six group ids with `tools-indicator` before
  `proc-indicator`/`bg-indicator`, and the docstrings that say "five".
- `tool_runs/loader.py:145-186` and `actions/_event_countdown.py:57-63`:
  tab-independent probe; apply updates the top bar everywhere, rows and titles on
  Agents.
- `actions/_proc_action_observer.py` feeds both indicators.
- Procs-tab header chips (`modals/procs_pane_selection.py`).
- Docs and help:
  - `docs/ace.md` (the "Proc Indicator" section near line 5214; the paragraph near 8867;
    the monitors section that mentions "the top bar's `procs:` group")
  - the `?` help popup and tooltips, per `src/sase/ace/CLAUDE.md`
- Tests:
  - lane and indicator unit tests: escalated, `-d`, adopt, join, `: tool run`, catalog
    `r`, glance-down fallback, truncated, silent
  - PNG goldens for the top bar at 120 and 80 columns
  - updated `config_center_procs_tab_*`

**Phase 2 — Agents tab**

- `tool_runs/attribution.py`: rules 2, 3 and 6 plus the per-generation `run → node` map.
- `_agent_list_render_agent_status.py:77-106` (`_append_tool_run_chip`): allow clan
  aggregates. Include the aggregate in the render-cache key
  (`_agent_list_render_cache.py`).
- `header_chip.py:275,340`: give clans a header chip and expanded field through the
  same aggregate. A clan Runs card can wait.
- `_display_panel_titles.py`: add the ⚒ and ⚒⚠ counts and the monitor exclusion; also
  `rail_panel_title`.
- Tests:
  - attribution matrix: escalated, `-d`, adopt, join, session member, clan with 1 and
    with N runs, remote clan
  - title-count tests
  - PNG goldens: update `tool_runs_rows_*`, add tribe and clan goldens with live runs
    (the existing clan and tribe goldens have none)

**Flags.** Phase 1 changes one indicator's meaning and label in a single landing. Phase
2 is additive. Per `sase_flags`, neither needs a beta or sunset flag unless the phases
are split so that half a surface would ship.

**Out of scope, but worth a task bead:** a backend reconcile job for silent ToolRuns.
This is the plan's own §6 follow-up, and it becomes more visible once silent runs show
red in the top bar.

## 8. Open questions for Bryan (with my defaults)

1. **How strict should `bg:` be?** My default is "everything that isn't
   tool/monitor/update/service" (R4), which is about equal to TUI work in practice.
   Choose "strict" if you want `sase proc run`, Telegram and API epic launches and
   gate/sudo-answer procs out of the top bar entirely.
2. **Where does the orange monitor chip go?** My default is `tools:` with "⚒ beats ⚙"
   (R2/R3). The fallback is to drop it from the top bar.
3. **Scope of `tools:`.** My default is machine-wide. The alternative is the current
   project only.
4. **Clan aggregate when expanded.** My default is always, for consistency with session
   containers. The alternative is collapsed only.
5. **Click target for `tools:`.** My default is Admin Center › Tools › Runs (all
   projects, live first). The alternative is the Procs tab filtered to `tool-run`.

## 9. Recommended solution

1. **Fix the facts first (Phase 0).**
   - Tool procs carry no TUI session unless the TUI submitted them.
   - Joining monitors are tagged `tool-run:<id>`.
   - The glance exposes `joined_monitor_id` (sase-core).
2. **Split the top bar by noun (Phase 1).** `tools:` shows:
   - a filled `⚒ N` chip (`#87D7FF`) for live ToolRuns, taken from the ledger,
     machine-wide, with children folded
   - a red `⚒⚠ N` chip for silent runs
   - an orange `⚙ N` chip only for monitors not carrying a run

   `procs:` becomes `bg:`, with a blue `⚙ N` for every other background proc. One shared
   helper enforces "⚒ beats ⚙", so no execution is ever counted twice. The glance probe
   becomes tab-independent; it stays stat-only, off-pump and ≤ 1 per 2 s.
3. **Make ⚒ land where the work is (Phase 2).** Attribute hand-off runs to their starter
   and joined runs to their monitor. That fixes today's missing chips for every Claude
   agent's `check`. Add a clan aggregate chip that mirrors the clan status rule (one run
   shows its chip; several show the primary plus `+N`). Add `⚒N` / `⚒⚠N` to tribe- and
   clan-panel titles, including collapsed and rail titles. Keep D3 (no raw counts on
   rows) and D15 (no remote chips).
4. **Later:** when tool admission exists, turn `⚒ N` into a `⚒ N/cap` gauge, and add a
   backend reconcile for silent runs.

This keeps your intent intact — tool runs get their icon and their own section, and
`bg:` means background — while making the count independent of provider, safe across
restarts, consistent between the top bar, rows and titles, and visually one glyph per
noun.
