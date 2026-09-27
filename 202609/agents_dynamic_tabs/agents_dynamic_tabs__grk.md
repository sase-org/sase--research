# Dynamic Agents sub-tabs, `%tab`, and machine-tab aliasing

- **Researcher:** grk (`research.2q.grk`)
- **Date:** 2026-09-27
- **Question:** How should the Agents tab grow *dynamic* sub-tabs (`%tab:<name>`), how should implicit placement become machine-aware without an ALL tab, and how should the `o` grouping picker grow a third “see everything” view?
- **Inspected:** sase workspace `sase_23` (Agents layout, tribe panels, grouping picker, keymaps, directives, live query, `PanelTabStrip`, fleet projection), sase-core (`editor/directive/metadata.rs`, `fleet_catalog.rs`, `agent_scan` tribe fields, `agent_tribe.rs`), glossary via `sase memory read`, `tui_perf.md`, `docs/ace.md`, `docs/xprompt.md`, `docs/agent_sessions.md`, `docs/remote_dispatch.md`, and prior research `research:202609/agent_machine_tabs_and_cluster_semantics/agent_machine_tabs_and_cluster_semantics.md`. Independent of the other four swarm reports.

## Recommended solution

Ship **assigned workspace tabs** as the product, and treat machine names as a *display alias of the unassigned bucket*.

1. **`%tab:<name>` is a first-class launch placement directive.** An agent with no `%tab` is implicit `main`. Explicit names always win, on every machine, so `+%sase %tab:sase` groups that project’s agents even when some of them `%dispatch` to apollo.
2. **The strip is occupancy-derived and hidden when only one tab has visible agents.** That preserves today’s Agents tab for local-only, no-`%tab` use. Empty enrolled machines do not get empty tabs; Admin Center already owns machine health.
3. **Machine tabs are not a second grouping dimension.** When remotes are enrolled, implicit `main` *displays* as `local` on this machine and as `<alias>` on a remote. A computer/home icon marks those shards. `%tab:foo` never relabels to a machine.
4. **There is no ALL tab.** The grouping picker’s panel-layout control becomes a 3-view cycle: split tribes on this tab → merge tribes on this tab → merge tribes *and* tabs. `o` / `O` inside the picker walk that cycle. App-level `O` (today a no-op on Agents) reverse-cycles the same views without opening the picker.
5. **`[` / `]` cycle occupied tabs.** Card-block stepping moves to `(` / `)`, matching every other sub-tabbed surface. Digit keys stay agent-relation jumps.

Do this as one TUI epic plus a small core/directive epic. Do **not** wait on the previous swarm’s “agent cluster” membership rewrite, and do **not** revive Focus/Fleet.

---

## Verdict

This is a good idea, and it is a better idea than the 2026-09-26 machine-tabs research.

The Agents tab already has too many grouping layers that try to answer “where is my work?”: tribe side panels, `GroupingMode.BY_MACHINE` banners, a `machine:` query facet, remote-row chips, and a retired Focus/Fleet mode bit (`AgentsSubTab = Literal["focus", "fleet"]` is still in `app.py` and is forced back to `"focus"`). The missing object is a **named, exclusive, cycleable workspace** whose chrome matches Projects / Artifacts / Config / Prompts, and whose membership the user can assign.

Tribes are the wrong object for that job. `@review` / `@epic` / `@job` are *kinds of work*. People already overload them as project buckets because there is nothing else to pin a working set to. Tabs should take the workspace job and leave tribes as kinds.

Machine-as-the-primary-strip, with a permanent ALL tab, is the less ambitious inversion of this. It solves fleet density and then stops. Dynamic `%tab` solves fleet density *and* the everyday “keep the sase work together, keep the dotdrop work together” problem, including when those agents ran on different machines.

I would take this approach. The adjustments below are where the request as written would otherwise get in the way of being intuitive, reliable, or beautiful.

---

## Requirement adjustments

These change the request. Each is load-bearing.

| ID | Adjustment | Why |
| --- | --- | --- |
| A1 | **Tabs are assigned presentation, not execution.** `%tab` never dispatches, never retargets a launch from the viewed tab, and is not a wait/fork target. `%dispatch` still chooses the machine. | Viewing is not targeting. Clans, `%wait`, and `%dispatch` already own coordination and execution. A tab that silently launched onto apollo would repeat the Focus/Fleet mistake. |
| A2 | **Store implicit placement as absent/null, never as the string `main` or `local`.** Display mapping happens at catalog time. | `local` and machine aliases are *labels of the unassigned bucket*, not names the user assigned. Persisting them would freeze a rename and collide with a later `%tab:local`. |
| A3 | **Machine tabs appear only when that shard is occupied.** Enrollment changes *labeling* (`main` → `local`) whenever the strip is visible; it does not pin empty remote tabs. | The request also says hide the strip when only one tab has agents. Empty machine tabs would violate that and duplicate Admin Center. |
| A4 | **Show all three panel views as labeled rows in the `o` picker, and let `o`/`O` cycle them.** Do not hide view 3 inside a mute toggle. | A 3-state cycle nobody can see is how the “see everything” escape hatch stays undiscovered. Fleet users who lose the unified list need a visible door. |
| A5 | **Move card-block keys to `(` / `)` and give occupied tabs `[` / `]`.** The request is silent on this; it is still required. | Square brackets already mean “cycle the strip” on every other sub-tabbed surface. They cannot stay on card blocks once Agents has a strip. Digits are already agent-relation jumps. |
| A6 | **Inherit tab down a clan, session, follow-up, and `%repeat` chain unless a member sets `%tab` explicitly. Disagreeing clan members are a launch error.** | A clan split across tabs would fork the synthetic container. Tribe panels already inherit from the presentation root (`agent_panels.py`); tabs must do the same. |
| A7 | **Ship `sase agent tab {set,unset,list}` and a TUI retab action, mirroring tribe.** Launch-only tabs would be strictly worse than tribes. | Tribe without `N` / `sase agent tribe` is a trap. Tabs are the same kind of assigned label. |
| A8 | **Keep tab scope out of the committed query.** Switching tabs does not rewrite `machine:` / `tab:` query text. Compose the two predicates for display. | The live query already drives history loading and other lookups (`agents_live_query_schema`). Tab switching must stay an in-memory projection (`tui_perf.md` rules 5–6). |
| A9 | **Do not introduce an Agent Cluster type for this feature.** | Yesterday’s research spent its ambition on unifying clans, tribes, and tabs. Clans have wait-all / generation / hood physics; tribes have wait-next; tabs are a view. Forcing one object stalls the TUI on a core identity rewrite this feature does not need. |
| A10 | **Add a `#tab:<name>` xprompt** (`%id` is not required), and accept `%id(..., tab=)` / `%clan(..., tab=)` as aliases of `%tab`. Keep `%tab` as the advertised spelling. | `%tribe` was retired as a standalone directive because tribe is identity. Tab is *placement*, like `%dispatch`, so a standalone directive is right. `#tribe` already exists as `src/sase/xprompts/tribe.md`; copy that shape. `%t` stays the retired tribe alias. |
| A11 | **Node finder (`"`) and `'` jump search across every tab; landing on a foreign-tab row switches the strip.** | Exclusive scopes that hide unanswered gates already failed once (Focus/Fleet). Finder and attention have to see the whole roster. |
| A12 | **No feature flag.** Occupancy-hide makes the strip invisible until it has work to do. Persist the 3-view, including merge-all, so fleet users who want the old unified list keep it. | A flag would hide the one-time migration. A first-fleet-strip tip is enough. |

A smaller adjustment I am *not* taking in v1: auto-assigning `%tab` from `+<project>`. The request’s own example (group a project across machines) is exactly what `%tab:sase` is for. Auto-project tabs would make the strip appear the moment two projects have agents, which is tempting and too magical for a first release. A later `ace.agent_tabs.default: main | project` is the right place for that.

---

## 1. What the Agents tab already is

Adding a strip without giving it a job that the other layers do not already do is how the surface gets worse.

| Layer | Job today | Membership | Presentation | Movable? |
| --- | --- | --- | --- | --- |
| Sase turn / session | Sequential execution | `%i(..., session=)` / `--` names | Tree under a session node | No (identity) |
| Agent hood | Dotted-name neighborhood | Derived from the name | Name-root banners; NEIGHBORS roster | No (derived) |
| Agent clan | Parallel bag + wait/cleanup | `%clan` / `clan=` | Synthetic clan node | Launch-time only |
| Agent tribe | Kind-of-work label | `tribe=` / `#tribe` / `N` | Vertical side panels `@review` | Yes |
| GroupingMode | Sort the tree | Derived | In-panel banners (`o` then `p`/`d`/`s`/`m`) | View-only |
| Live query | Authored filter | Query text | Auto-hiding filter bar | Yes |
| Fleet chips | Where it ran | `fleet_origin_alias` | Remote-row alias chip; local rows have none | Derived |
| Leftover `AgentsSubTab` | Historical Focus/Fleet | Forced `"focus"` | `#agents-header` is a *diagnostic* row, hidden when quiet | Dead |

Evidence, current HEAD:

- Tribe panels are the outer *assigned* grouping. Every descendant inherits the presentation root’s tribe, so a clan or session is never split across panels (`src/sase/ace/tui/models/agent_panels.py`).
- Merged-tribe layout is a boolean, `_agent_panels_grouped`, toggled from the grouping picker’s local `o` (`AgentGroupingAction.TOGGLE_PANELS` → `action_toggle_agent_panel_grouping`). The merged title is the literal `All agents` (`_display_panel_titles.py`).
- `oo` is documented as “toggle split/merged, then close the picker” (`docs/ace.md`). App-level `O` is `cycle_grouping_mode_reverse`, which is a no-op on Agents (`_grouping.py`).
- `GroupingMode.BY_MACHINE` already puts `here` first, then remote aliases, then status. It still renders **every** machine in one tree (`docs/ace.md`).
- The live query already understands `machine:here` / `machine:apollo` and `tribe:` (`_agents_live.py`). Admin Center Machines `Enter` injects that filter.
- `#agents-header` is a single row, fleet diagnostics right-aligned, hidden when quiet (`_app_layout.py`, `_fleet_header.py`, `styles.tcss`).
- `PanelTabStrip` already supports icons, compact/micro labels, click geometry that counts terminal cells (so 2-cell glyphs hit-test correctly), and unnumbered strips (`panel_tab_strip.py`). Prompts, Artifacts, Config, Projects already use it.
- `%dispatch` is a standalone placement directive with no short alias (`_directive_types.py`, sase-core `metadata.rs`). `%tribe`/`%t` raise a migration error; tribe lives on `%id` / `%clan` / `#tribe`.
- Tribe assignments persist in `~/.sase/agent_tribes.json`, not in `agent_meta.json` (`agent_tribes.py`, written at launch from `run_agent_directives.py`). Fleet already serves `tribe` / `clan_tribe` on owner rows (`fleet_catalog.rs`).
- Full list rebuilds are the expensive UI operation; STANDARD / BY_STATUS / BY_MACHINE stay on `patch_row` when membership is stable (`tui_perf.md` rule 6).

The gap is specifically: a **named exclusive working set** that the user can assign, that machines can alias when unassigned, and that does not steal attention.

---

## 2. Critique of the plan, and of yesterday’s research

### 2.1 Dynamic `%tab` first — take this, make it the product

Yesterday’s synthesis (`agent_machine_tabs_and_cluster_semantics.md`) recommended `All · here · apollo · …`, derived membership, and an Agent Cluster glossary umbrella. That is a good fleet filter with chrome. It is not a workspace.

The request’s own example — group every agent for a project, regardless of machine — cannot be expressed by machine tabs. It is the opposite predicate: *ignore* origin, *honor* an assigned name.

So the primary object is:

> An **agent tab** is a user-assigned presentation workspace for sase agents. It is exclusive (one tab per agent), occupancy-derived (the strip lists tabs that currently have visible agents), and orthogonal to tribe, clan, session, and dispatch.

Machine tabs are a *view function* over agents whose assigned tab is absent.

### 2.2 Default implicit `main` — take this, never persist the word

Defaulting the unassigned bucket to a reserved display name is right. It matches `@default` for tribes: a presentation identity, not a stored assignment (`RESERVED_DEFAULT_TRIBE = "default"` is a panel label and is never a wait target).

Display mapping:

| Stored tab | Remotes enrolled? | Origin | Strip id | Strip label |
| --- | --- | --- | --- | --- |
| absent | no | local | `implicit:main` | `main` |
| absent | yes | local | `implicit:local` | `local` |
| absent | yes | remote `apollo` | `implicit:apollo` | `apollo` |
| `sase` | any | any | `assigned:sase` | `sase` |

`here` (the BY_MACHINE L0 bucket and the `machine:here` query token) stays a query/grouping word. The strip says `local`, as the request asked. Do not alias `here` onto the strip; two words for “this machine” is how the chrome gets noisy.

### 2.3 Hide the strip when only one tab is occupied — take this

This is the beauty constraint, and it is the reason the feature can land without a flag. A local-only user who never types `%tab` must see today’s Agents tab, pixel-identical, including goldens.

Occupancy is computed from the **tab-unscoped** roster after the committed query and the hide-non-run filter, including `STARTING` agents (they already contribute to the `<N> starting` headline). A query of `tab:sase` must **not** hide sibling tabs: occupancy ignores the tab-scope predicate so the strip remains a destination.

Hidden (`%hide`) agents do not occupy a tab. A tab whose only members are hidden is absent from the strip.

### 2.4 No ALL tab — take this, and make the escape hatch visible

An ALL tab re-teaches Focus/Fleet: a mode that competes with the working sets. The 3rd panel view is the right replacement because it is a *layout*, not a *place*. You are still “on” the Agents tab; you have just asked the panels to flatten.

The request’s 3-cycle is the useful 3 of 4 cells of two independent bits:

|  | This tab | All tabs |
| --- | --- | --- |
| Split tribes | **View 1 (default)** | skipped |
| Merged tribes | **View 2 (today’s `oo`)** | **View 3 (new)** |

Skipping “split tribes × all tabs” is correct. That cell would mount every tribe panel mixed across machines and named tabs, which is the current overcrowded tree plus a strip. View 3 is the “I need everything, and I will accept one list” posture.

Discoverability is the actual risk. Today `oo` toggles and closes. A 3-state toggle with the same chrome would hide view 3 behind two round-trips. Adjustment A4 is the fix: the picker grows three labeled layout rows, `o`/`O` walk them, and the current row is badged `Current` the way grouping modes already are.

### 2.5 Machine icons, including `local` — take this, and use them as the visual grammar

Named tabs are *labels* (text-first). Machine tabs are *places* (icon-first). That single distinction is what makes a mixed strip readable when a user has `%tab:apollo` *and* a machine named apollo.

Internal ids are already disjoint (`assigned:apollo` vs `implicit:apollo`). The strip still needs a one-cell cue:

| Kind | Icon | Accent |
| --- | --- | --- |
| `local` | `⌂` | `#87D7FF` (the existing “here/default” cyan) |
| remote machine | `▣` | stable hash of the alias, fallback `#5FD7FF` |
| named / `main` | none | named: hash of the name; `main`: dim gold `#FFD75F` |

`⌂` already styles `@default`. That rhyme is useful: both mean “unassigned home.” They sit on different surfaces (strip vs panel title), so they do not collide in one row.

Avoid nerd-font private codepoints and wide emoji (`🖥`). `PanelTabStrip` hit-tests with `cell_len`, but a two-cell glyph still steals strip budget. One-cell geometric glyphs match the existing tribe/notification icon set (`⌂ ▲ † ◆ ◉ ⚑ ✖ ◈`).

Reserve `main`, `local`, `here`, `all`, and currently enrolled aliases at `%tab` parse time (case-insensitive). A later enrollment that collides with an existing named tab keeps both rows, with the machine icon as the disambiguator, and a tooltip `machine apollo` vs `tab apollo`. Do not silently merge them.

### 2.6 `%tab` as a directive — take this, and pair it with keywords

Standalone `%tab` is right. Tab is placement, the same family as `%dispatch`, not identity like tribe.

Grammar, mirroring `%dispatch` + tribe:

```text
%tab:sase
%tab(sase)
%id(worker, tab=sase)
%id(worker, tribe=review, tab=sase)   # tab does not conflict with tribe/clan/session
%clan(research, tribe=research, tab=sase)
#tab:sase                             # auto-named, like #tribe
```

Rules:

- One tab per launch. Two `%tab`s, or `%tab` disagreeing with `tab=`, is a `DirectiveError`.
- Name grammar reuses tribe: `^[A-Za-z0-9_.-]+$`, case-insensitive identity, first-seen spelling for display.
- No short alias. `%t` is the retired tribe spelling and must keep raising that migration error.
- `%tab` composes with `%dispatch`. v1 dispatch still strips `%wait` / `%queue` / `%clan`; it must **not** strip `%tab`. The remote owner persists the assignment so the controller can group it.
- `%tab:local`, `%tab:main`, `%tab:here`, `%tab:all`, and `%tab:<enrolled alias>` error at parse time with a pointer at the reserved set.
- Completion: colon and paren forms; candidates are existing assigned tab names plus a free-text row. Do not complete reserved machine names as assignments.

`#tab` is a 10-line xprompt next to `tribe.md`:

```markdown
%id(tab={{ tab }})
```

### 2.7 The `o` / `O` 3-view cycle — take this, with visible rows and a live title

Current picker (`agent_grouping_modal.py`):

- Four grouping rows (`p`/`d`/`s`/`m`)
- A “Panel layout” section with one row whose `o` toggles split ↔ merge and dismisses

Replace that one row with three:

```text
Panel layout
  [o] Split by tribe · this tab          Current
      Each tribe is its own side panel, scoped to the active tab.
  [O] Merge tribes · this tab
      One panel of this tab’s agents. Tribe stays a row chip / `N` target.
  [a] Merge tribes · all tabs
      One panel of every tab’s agents. The strip stays; every tab looks selected.
```

Behavior:

- `o` applies the *next* view and dismisses (preserves `oo` as “one step”).
- `O` applies the *previous* view and dismisses.
- `a` (mnemonic: all) jumps to view 3 directly. Direct keys on the other two rows are the same `o`/`O` letters they already show, plus Enter on the highlighted row.
- App-level `O` on Agents reverse-cycles immediately and toasts `Agent panels: merged tribes · this tab`. App-level `o` still opens the picker.
- Persist the view like grouping mode (`save_agent_grouping_mode` analogue). View 3 survives restart.
- Isolation `=` is unavailable in views 2 and 3 (already true of merged panels). `J`/`K` panel hops likewise.

View 3 chrome, because this has to be beautiful rather than “the list got longer”:

- Strip stays mounted. Every occupied tab renders in its *active* accent, with a leading `Stacked` marker on the header row (`☰` or a light fill behind the whole strip). Clicking one tab exits view 3 into view 2 on that tab (you were already in a merged-tribe posture).
- The merged panel title becomes `All agents · all tabs` rather than `All agents`.
- Rows from a foreign tab grow a small tab chip, machine-icon-first when the source is an implicit shard, text-first when assigned. This is the same visual language as today’s remote-row alias chip, promoted to the tab identity.
- `[` / `]` from view 3 also exit to the cycled tab in view 2.

A trailing strip affordance (a dim `☰` after the last tab) that enters view 3 is worth adding. It is the thing you can click. The picker remains the keyboard teacher.

### 2.8 “Would you take a different approach?”

The alternative I would *not* take: two orthogonal keybindings (one for tribe merge, one for tab flatten) as the *only* UI. Orthogonality is cleaner on paper and teaches worse. The 3-cycle matches how people actually switch postures: “just this tab, split,” “just this tab, one list,” “everything, one list.”

The alternative I *would* take over the request-as-written: **the visible 3-row picker (A4)** plus **the strip-trailing flatten control**. The cycle keys still exist.

I would also delete the leftover `AgentsSubTab` type as part of this work. It is a footgun for the next person who greps “subtab.”

---

## 3. Proposed model

### 3.1 Identity

```text
AssignedTab = validated name
StoredTab   = AssignedTab | None          # None = implicit main
StripId     = "assigned:<name>" | "implicit:<label>"
StripLabel  = assigned name | "main" | "local" | machine alias
```

One agent, one stored tab. Presentation roots (clan container, session container) carry the tab. Members inherit it for display even if a stale store row disagrees; launch validation should have made disagreement impossible for new clans.

### 3.2 Catalog order

When the strip is visible:

1. Implicit `local` / `main` first, if occupied.
2. Other implicit machine shards, enrolled-alias alphabetical.
3. Assigned tabs, alphabetical (case-insensitive), first-seen spelling.

`local`/`main` is home. Named workspaces come after places. That is the same instinct as tribe panels putting `@default` first.

Default selection on open: last persisted strip id if still occupied, else the first occupied id (home). A newly launched agent on another tab updates that tab’s count and attention pip and does **not** steal the cursor.

### 3.3 Pipeline

```text
authoritative local + fleet roster
  → committed Agents query          # does not include tab scope
  → structural roots (clan/session/workflow intact)
  → agent-tab catalog + active strip scope
  → tribe panels (or one merged panel)
  → grouping tree and visible rows
```

View 3 skips the strip-scope filter and sets merge-tribes.

Tab switching is an in-memory projection. It must not trigger a network refresh, disk parse, or remount of inactive tribe panels (`tui_perf.md` rules 1, 5, 6). Cache per `(strip_id, committed_query)`: selected node identity, focused tribe panel, fold/scroll anchor, detail target. Session-sticky tribe-panel keys already scope to the committed query (`_session_sticky_query_value`); extend that key with `strip_id` so an empty `@review` on `local` does not linger on `sase`.

On return, restore by identity; fall back to a nearby surviving row. Marks stay global identities; bulk actions apply to **marks visible in the current view**, and the confirmation names any hidden marks (“3 marked agents are on other tabs”).

### 3.4 Query facet

Add `tab:` to the live Agents dialect, exact-match, alongside `machine:` and `tribe:`.

Tokens:

- `tab:sase` — assigned name
- `tab:main` — implicit, including when displayed as `local` / `apollo`
- `tab:local` — implicit local shard (only meaningful once remotes are enrolled)
- `tab:apollo` — ambiguous if both an assigned tab and a machine shard exist; match **assigned first**, and complete with distinct rows `apollo (tab)` / `apollo (machine)`

Tab-scope from the strip ANDs with an explicit `tab:` query. If they contradict, show the existing empty-state pattern with a one-line “clear tab filter” / “jump to matching tab” action. Do not rewrite the query.

### 3.5 Persistence

Mirror tribe, because the mutation story is the same:

| Layer | What | Where |
| --- | --- | --- |
| Launch provenance | The `%tab` / `tab=` that was authored | `agent_meta.json` key `tab` (absent if implicit) |
| Mutable assignment | Current tab, including post-launch moves | `~/.sase/agent_tabs.json`, same identity triple as tribes `(AgentType, cl_name, suffix)` |
| Fleet | Owner-served current tab | optional `tab` on the catalog row; omit when implicit so old readers stay valid |

Launch writes both meta and the assignment store, the way `%id(tribe=)` already calls `update_agent_tribe` after `write_agent_meta`. `sase agent tab unset` returns the agent to implicit `main` (machine-aliased on display).

Do not put tab validation in a new sase-core crate module unless the tribe grammar is reused through a shared “label name” helper. A Python-side validator matching `TRIBE_NAME_RE` is enough for v1; promote to core when the fleet field lands.

Fleet compatibility: old owners omit `tab` → controller treats the row as implicit → machine shard. New owners send `tab`. Adding a `deny_unknown_fields` key requires the sase-core pin to move first (`docs/rust_backend.md`, `sase-core-revision.txt`). Until that pin, local assigned tabs still work; remotes with `%tab` display on the machine shard. Call that gap out in the changelog so it is not a surprise.

### 3.6 Clans, sessions, dispatch

- `%clan(..., tab=sase)` or a `%tab` on the declaring segment assigns the clan. Joiners without `%tab` inherit. A joiner with a different `%tab` is a launch error (“clan research is on tab sase”).
- Session follow-ups inherit the parent’s stored tab. An explicit `%tab` on a follow-up is allowed and moves only that member; the session container stays on the root’s tab and still lists the member in SESSION TURNS (the member’s own row also exists on the other tab). Prefer inheritance. Document the split as an advanced escape.
- `%repeat` copies the tab. Swarm `---` segments each parse their own `%tab`.
- `%dispatch` + `%tab` is the headline composition. Keep the two concerns in the prompt: `%dispatch:apollo` `%tab:sase`.
- Viewing the `apollo` machine tab does **not** inject `%dispatch:apollo`. A launch-context chip may *hint* “viewing apollo” in dim text; a later opt-in “pin launch to this tab” toggle can exist, default off (A1).

---

## 4. TUI: intuitive, reliable, beautiful

### 4.1 One header row, not a second chrome band

Reuse `#agents-header`. Today it is hidden unless a fleet diagnostic exists. After this feature:

- Strip visible **or** fleet diagnostic → unhide the row.
- Strip occupies the left (`1fr`), fleet status stays right-aligned.
- Strip hidden and no diagnostic → the row stays `hidden`. **This is the golden-preserving path.**

Do not put the strip in the info row. That row already carries counts, load, and launch context. Do not put it above the filter bar: the filter is an editor, the strip is a destination.

Sketch, 120 cells:

```text
⌂ local 12  │  ▣ apollo 8 !2  │  sase 24  │  dotdrop 3          apollo unknown
```

Active tab: bold accent, one-cell left pad already provided by `PanelTabStrip`’s full tier. Inactive: `#888888`. Attention: `!N` in `#FF8700` immediately after the count, sourced from the durable inbox / `fleet_attention`, independent of which tab is open.

Counts are sase-agent counts, not rendered rows. Bounded or incomplete sources show `N+`. Stale machine shards keep their last count and pick up the host’s freshness marker in the tooltip (`stale · cached 5h ago`), matching remote-row copy in `docs/ace.md`.

### 4.2 Overflow

`PanelTabStrip` compact/micro tiers still overflow on a 20-machine fleet plus a handful of named tabs. Compact/micro alone is not a bound (yesterday’s research was right about this).

Add a real overflow: when the fitted tier still exceeds width, keep home + the active tab + as many others as fit, then a `+N` chip. Click or `[` wrapping into overflow opens a picker whose rows reuse the same icon/label/count/attention. Include those titles in `'` jump. No digit shortcuts.

`reflow_to_fit=True` is already on the widget. Use it.

### 4.3 Keys

| Action | Key | Notes |
| --- | --- | --- |
| Next / prev occupied tab | `]` / `[` | Hidden strip: no-op, no toast |
| Next / prev card block | `)` / `(` | Footer shows these only when `card_blocks_navigable` |
| Open grouping picker | `o` | Unchanged |
| Cycle panel view forward (in picker) | `o` | One step + dismiss |
| Cycle panel view reverse (in picker *and* on Agents) | `O` | App-level `O` is currently dead on Agents |
| Jump to merge-all (in picker) | `a` | Discoverability for view 3 |
| Retab selected agent | `B` | `B` is unbound in `default_config.yml`; mnemonic “bin / bucket.” Mirrors `N` for tribe |
| Isolate tribe panel | `=` | Unchanged; unavailable in views 2–3 |

The nested-bracket mnemonic, which is the beautiful part of the keymap:

| Keys | Layer |
| --- | --- |
| `[` / `]` | Outer scope (sub-tabs), now including Agents |
| `{` / `}` | Deck panel geometry (already) |
| `(` / `)` | Inner card block (new on Agents; already file versions on Artifacts) |

Update `default_config.yml`, availability, collision allowances (`next_card_block` currently shares `[` with `cycle_artifacts_subtab`), help/footer/quickstart, the block-rail hint, docs, glossary card-block wording, and goldens together. Detect a copied legacy `[`/`]` card-block override at config load and warn. Artifacts Files keeps `(`/`)` for versions; that conflict is tab-disjoint, the same pattern square brackets use today.

### 4.4 Empty and conflict states

| Situation | Copy |
| --- | --- |
| Named tab whose agents are all excluded by the query | `No agents on sase match this query` + `clear filter` |
| Machine shard with a stale/invalid feed and no cached rows | `apollo: feed invalid` + route to Machines |
| View 3 with a query that matches nothing | existing empty query state |
| `%tab` reserved-name error | `Cannot assign tab 'apollo': that name is the machine tab for enrolled host apollo. Use a project or workspace name, or omit %tab to land on apollo.` |

### 4.5 Reliability gates

- Tab switch does no I/O. Measure paint; keep `j`/`k` p95 < 16 ms on a loaded fleet (`tui_perf.md`).
- Quiet refresh must not rebuild inactive tab widget trees or increase fleet/file-open work.
- Re-read selection and strip id after every await (rule 4).
- Incremental `patch_row` stays valid while tab membership of a *row* is stable. A row moving tabs (retab, or a remote whose `%tab` arrives after implicit display) is a membership change → rebuild that row’s source and target, same as a tribe move (`test_tribe_move_between_existing_panels_rebuilds_source_and_target`).
- First paint never waits on tab-store I/O; serve implicit `main` from meta/absence, then merge the assignment store off-thread.

---

## 5. Glossary (to add through the memory-write workflow at implementation)

Two strands. The request asked for **machine tabs**; the product also needs the general term.

**Agent Tab** (aka tab, agents sub-tab):

> An agent tab is a user-assigned presentation workspace on the Agents tab. Assign one at launch with `%tab:<name>`, `%id(..., tab=<name>)`, `%clan(..., tab=<name>)`, or `#tab:<name>`. Agents with no assignment belong to the reserved implicit tab, displayed as `main`, or as a [[glossary:machine-tab]] when remote machines are enrolled. An agent has at most one tab. The sub-tab strip lists occupied tabs and hides itself when only one tab has visible agents. Tabs are presentation: they are not wait targets, dispatch targets, or execution identity.

**Machine Tab** (aka machine tabs):

> A machine tab is the display identity of the implicit agent tab once remote machines are enrolled: `local` for agents on this machine, and `<alias>` for agents on an enrolled remote. Implicit placement is stored as absent, never as `local` or the alias. An explicit `%tab:<name>` always uses `<name>`, on every machine, so a project’s agents can share one tab across hosts. Machine tabs carry a place icon (`⌂` local, `▣` remote) in the Agents sub-tab strip. They appear only while that shard has visible agents.

Do not add **Agent Cluster** as part of this feature.

---

## 6. Delivery

### Epic 1 — Directive, store, inheritance (sase + sase-core pin)

- `%tab` / `tab=` / `#tab` parse, validate, complete.
- `agent_meta.tab` + `~/.sase/agent_tabs.json`.
- Clan/session/`%repeat` inheritance and disagreement errors.
- `sase agent tab {set,unset,list}`.
- Live query `tab:` facet (can land even before the strip).
- sase-core: directive metadata (`name: "tab"`, colon+paren, no alias), optional fleet `tab` field behind the revision pin.
- Tests: extract/conflict/reserved names, inheritance, CLI, query, dispatch composition.

This epic is user-visible only in `sase agent tab list` and query. The TUI still looks like today.

### Epic 2 — Strip, 3-view, keys (sase TUI)

- Catalog + occupancy + display mapping.
- `#agents-header` hosts `PanelTabStrip` + existing fleet status.
- `[`/`]` / `(`/`)` keymap migration.
- Grouping picker 3-view + app-level `O` + persist.
- View 3 chrome, foreign-tab chips, overflow picker.
- `B` retab modal (seed from occupied assigned names; allow new names).
- Node finder / `'` cross-tab.
- Delete leftover `AgentsSubTab`.
- Goldens: hidden-strip path must match current Agents screenshots; add strip, overflow, view 3, mixed named+machine, reserved-collision, attention-on-inactive.

### Epic 3 — Polish, only if Epic 2 usage shows the need

- `ace.tabs.<name> {icon,color,description}` parallel to `ace.tribes` (do not require it to ship).
- `ace.agent_tabs.default: main | project`.
- Opt-in “pin launches to the viewed tab.”
- Byte-none of this is required to answer the request.

Verify: local-only hidden strip; one named tab + main; remotes enrolled with only local agents (strip hidden, label mapping unused); remotes with local+apollo implicit; `%tab:sase` mixed with local and apollo implicit; reserved-name errors; enrollment after a named `apollo` tab; view 1/2/3 cycling both directions; `O` with the picker closed; `[`/`]` with strip hidden; legacy `[` card-block override; Artifacts `(`/`)` versions still work; query conflict; cross-tab finder; retab of a clan root; fleet old-owner implicit fallback; j/k p95; tab-switch paint; quiet-tick file opens.

---

## 7. What I would not do

- An ALL sub-tab, a Focus/Fleet revival, or a per-machine *mode*.
- Numbered tab shortcuts.
- Silently injecting `%dispatch` from the viewed machine tab.
- Showing empty enrolled machines on the strip.
- Making tabs wait/fork targets, or folding them into clan membership.
- Auto-`%tab` from `+project` in v1.
- A feature flag whose off-state is identical to occupancy-hide.
- Unifying clans, tribes, and tabs under Agent Cluster as a prerequisite.

---

## Recommendation

Implement dynamic assigned tabs as the Agents-tab workspace layer, with machine names as the display of implicit `main`, occupancy-hide so today’s layout is the zero-state, no ALL tab, a visible 3-view panel cycle as the “see everything” hatch, and `[`/`]` on the strip.

That is more ambitious than machine-scoped tabs with ALL, and it is the design I would actually want to use: `%tab:sase` for the project, `⌂ local` / `▣ apollo` for everything I did not bother to name, `oo` when I want one list, and a strip that disappears the moment it would be lying.
