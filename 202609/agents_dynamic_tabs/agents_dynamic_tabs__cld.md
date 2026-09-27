# Dynamic Agents sub-tabs: `%tab`, machine tabs, and a three-level panel view

**Researcher:** cld · **Date:** 2026-09-27 · **Status:** research and design recommendation

**Inputs:**

- The request. It asks for a `%tab:<name>` directive, a default `main` tab, machine tabs (`local` or the machine's name), no strip when only one tab has agents, no "ALL" tab, and a 3-way `o` cycle with an `O` reverse.
- Prior research `research:202609/agent_machine_tabs_and_cluster_semantics/agent_machine_tabs_and_cluster_semantics.md`, read through `sase artifact read`.
- The current `sase` TUI, launch, and fleet code.
- The linked `sase-core` checkout: tribe validation, the scan wire, fleet owner facts, typed launch units, and directive metadata.
- A glyph-coverage check against the TUI's bundled fonts.

---

## 0. Decision in brief

**Build it.** Treat an **agent tab** as a first-class, presentation-only partition of the Agents tab's top-level nodes. The launching machine records it with the agent, and every viewer resolves it the same way. Four rules keep this intuitive and reliable:

1. **The tab belongs to the whole presentation root and is stored with the agent.** `%tab` is written to `agent_meta.json`, and served in the fleet feed so every machine agrees. Only the root decides the tab, so a clan, session, or workflow never splits across tabs. Tabs are never `%wait`, `%hold`, or fork targets. That is what makes them safe to rename, move, and hide.
2. **The default is resolved at view time and never stored.** An agent without `%tab` shows on the default tab: `main`, or its machine tab (`local` or `<alias>`) when this machine has enrolled remotes. Nothing named `main` or `local` is ever written to a record, so enrolling a machine or renaming an alias relabels tabs without migrating data.
3. **Tabs appear on their own and never hide something that needs you.** The strip appears only when two or more tabs have agents. Each tab shows a count plus a needs-you badge. Global jumps (unread, stopped, Node Finder, notifications, relation numbers) switch tabs automatically.
4. **`o` becomes a zoom ladder: Tribes → Tab → Everything.** `O` walks it in reverse. When only one tab exists the ladder shrinks back to today's two-state toggle, so current behavior is unchanged.

Beyond the literal request, I make these changes; each is called out in §3:

- **(A1)** A launch from a named tab inherits that tab. It is visible in the prompt bar and written into the prompt as an explicit `%tab`.
- **(A2)** An agent launched by another agent inherits its launcher's tab.
- **(A8)** `[`/`]` switch sub-tabs, matching Artifacts, and card blocks move to `(`/`)`.
- **(A10)** Agents can be moved between tabs after launch.
- **(A6)** `local` becomes the TUI's single word for "this machine".

Without A1 and A2, users have to type `%tab` on every launch to keep a tab coherent, and the feature becomes a chore.

---

## 1. What exists today (evidence)

| Area | Current behavior | Where |
| --- | --- | --- |
| Tribe panels | One `AgentList` per tribe key. A root's tribe decides the panel for its whole subtree (`anchors.get(id(agent), agent).tribe`). `@default` (key `None`) comes first; the rest are sorted. | `src/sase/ace/tui/models/agent_panels.py:93-155` |
| Merge toggle | `_agent_panels_grouped: bool`, initialized `False` and **not persisted**. It flips `from_agents(merge_tribe_panels=True)` → a single `"All agents"` panel whose rows carry tribe labels. | `actions/_state_init_agents.py:290`, `actions/agents/_panel_navigation.py:337-360`, `actions/agents/_display_panel_titles.py:154-155` |
| `o` picker | `AgentGroupingModal`: `p`/`d`/`s`/`m` choose a grouping mode, and a "Panel layout" row `[o]` toggles merge. `on_key` checks `o` first, lowercases other letters, and **swallows `O`** and every other printable key. | `src/sase/ace/tui/modals/agent_grouping_modal.py` |
| `O` globally | `cycle_grouping_mode_reverse: "O"`, but disabled on Agents, so `O` is effectively free there. It needs a `_CONTEXTUAL_APP_DUPLICATES` entry. | `default_config.yml:855-862`, `_app_action_availability.py:222-224`, `keymaps/registry.py:101+` |
| Grouping mode | STANDARD / BY_DATE / BY_STATUS / BY_MACHINE, persisted to `sase_home()/grouping_mode.txt`. | `models/agent_groups/_buckets.py`, `ace/grouping_strategy.py` |
| `[` / `]` | Card-block stepping on Agents (only when the focused deck has blocks); `cycle_artifacts_subtab` on Artifacts. `(`/`)` are Artifacts-Files-only and free on Agents. | `default_config.yml:670-686`, `keymaps/registry.py:150-151` |
| Tab strip widget | `PanelTabStrip`: full/compact/micro tiers, click → `TabClicked`, tooltips. It has **no count badges, no attention markers, and no overflow window**. Used by the Artifacts header and several modals, never by Agents. | `widgets/panel_tab_strip.py` |
| Dynamic tab precedent | Artifacts provider tabs are descriptor-driven, with hashed accent colors that avoid reserved colors (`palette_hash.hash_palette_index`) and icons sanitized to ≤2 cells. | `_artifact_tab_model.py`, `_artifact_tab_descriptors.py:280-320` |
| Agents layout | Info row → filter bar → `#agents-header` (hidden by default, holds `#agents-fleet-status`) → content. | `_app_layout.py:122-145`, `actions/agents/_fleet_header.py` |
| Retired sub-tabs | `AgentsSubTab = Literal["focus","fleet"]`, `current_agents_subtab`, `_AGENTS_SUBTABS`, always forced back to `"focus"`. Dead code whose name collides with this feature. | `app.py:108,197,289-291`, `actions/agents/_fleet_projection.py:83-133`, `_fleet_common.py:14` |
| Remote rows | `fleet_origin_alias` (viewer-local alias), `fleet_origin_installation_id`, locators, health. `is_remote_fleet_agent` = alias present. Row chip is `bold #5FD7FF`. | `models/_agent_state_fleet.py`, `actions/agents/_remote_lifecycle.py:13`, `widgets/_agent_list_render_agent_prefix.py:71-75` |
| "This machine" wording | `here` everywhere: BY_MACHINE banner, Launch Target picker, Machines pane, `machine:here`. `%dispatch:local` is reserved. | `agent_groups/_keys.py:235-252`, `docs/remote_dispatch.md` |
| Machine registry | `dispatch.machines.<alias>` in merged config. Each `MachineRecord` has `alias` and `installation_pin` (stable). The local name comes from `get_machine_name()`. | `src/sase/dispatch/{config,models}.py`, `src/sase/config/_owner.py` |
| Directive pipeline | Parsing is in Python (`_directive_types.py`, `_directive_collect.py`, `_directive_extract.py`). The directive contract, completion, LSP, and typed-launch re-emission are in Rust (`editor/directive/metadata.rs`, `agent_launch/typed_units.rs`). A parity test asserts that the two agree. | `src/sase/xprompt/`, sase-core `crates/sase_core/src/…`, `tests/test_xprompt_directive_contract.py` |
| Tribe storage | Launch writes `agent_meta.json["tribe"]`. `sase agent tribe` writes only `~/.sase/agent_tribes.json`, which overlays meta in the TUI. The fleet feed's `tribe` comes from **meta** (gateway `fleet_reads/resolution.rs`), so a CLI tribe edit is invisible to remote viewers. | `axe/run_agent_directive_metadata.py:294`, `agents/cli_tribe.py`, sase-core gateway |
| `%tribe` history | The standalone `%tribe`/`%t` was folded into `%id(tribe=)` because "%id should be the single **identity** directive" (epic sase-7o). `%t` is still bound to a migration error. | `_directive_types.py:84-110`, `plan:202607/id_kwargs_tribe_family.md` |
| Dispatch | The controller strips only `%dispatch`; every other directive runs on the target. The target owns the agent. Viewers see everything an enrolled machine owns (no controller filter). | `docs/remote_dispatch.md:197-248`, `_fleet_refresh.py:298-302` |
| Env precedent | `SASE_EPIC_CLAN_TRIBE` sets an epic clan's tribe through the environment. | `src/sase/bead/work_types.py:18`, `axe/run_agent_directive_metadata.py:46` |
| Launch-context principle | "The current project seeds filters and preselects the `+` picker row, **it is not silently applied to prompts**." | `widgets/launch_context_bar.py:1-30` |

Glyph coverage: every one of these is covered by the bundled FiraCode/DejaVu/NotoEmoji stack and is one cell wide:

- `⌨` (U+2328) is **unused anywhere in the TUI**.
- `◇` appears in one help legend.
- `⊞` is unused.
- `◌` is covered.
- `⌂` is already the default-tribe icon.
- `▣` is the workspace/xprompt glyph.
- `🖥` measures one cell in Rich but renders as two in emoji-presentation terminals, so avoid it.

---

## 2. What the prior research got right, and what I would change

Keep:

- Tab switching as an **in-memory projection**: no I/O, one widget surface, per-tab selection memory, identity-based restore.
- Root-level membership. A clan is never split.
- Attention visible on inactive tabs.
- Query and tab composed as independent predicates. Selecting a tab never rewrites `machine:`.
- Machine tabs keyed by a **stable identity** rather than the alias.
- `[`/`]` for tabs, with card blocks moved to `(`/`)`.
- Retiring the dead Focus/Fleet state.
- No auto-`%dispatch` from a viewing choice.

Change:

- **The `All` tab is replaced by the view ladder**, as the user asked. A pseudo-tab makes "which tab is this agent on?" ambiguous (every agent would be on two). It also invites double-counting and still needs a tab-chip row model. A view level has none of those problems.
- **Empty machine tabs:** the prior design always showed a tab for every enrolled machine, and made machine tabs the whole feature. The user's model is **dynamic**: a tab exists because it has agents. I agree. A machine with a broken feed keeps its tab while cached rows exist (with a stale or failed marker). A machine that never loaded is reported in the header diagnostic, which already exists.
- **Tabs are authored, and machines are just the default.** The prior design had no authored tabs. The more ambitious and more useful model is the reverse: named tabs (`%tab:sase`) are the primary concept, and machine tabs are the *default placement rule* for agents that did not choose one.
- **"Agent Cluster"** is out of scope. Nothing here needs it. Tabs are a view scope with a clear, narrow contract.

---

## 3. Critique of the requested plan

### Is this a good idea?

Yes. The Agents tab already has two orthogonal organizers, tribes (what an agent is *for*) and grouping modes (how rows are *sorted*). It has no way to say "this is a separate working context". The fleet made that pressure acute: a single list now mixes athena, apollo, and mac agents, plus several projects. A dynamic tab strip:

- costs nothing until it is useful, because it is invisible with one tab;
- scales to more machines and projects without deeper nesting;
- gives muscle-memory navigation;
- lets a project's agents from several machines sit together, which neither tribes nor `machine:` filters do well today.

### Risks and weaknesses I see

1. **Three organizing axes.** Tab, tribe, and grouping mode could overload users. The hierarchy has to be strict and visible: **tab → tribe panel → grouping banners → rows**, with one-line guidance: *a tab is where you are working; a tribe is what the agents are for.* Tabs must never also be wait targets, or the two concepts blur.
2. **"No `%tab` → main" alone makes tabs leak.** If I am on `◇ blog` and launch "fix the typo", the literal rule sends it to `main`. My new agent disappears from view, and the only fix is typing `%tab:blog` on every launch. The same happens when an agent on `blog` spawns helpers or an epic: they all land on `main`. That is the biggest usability hole in the request. Adjustments A1 and A2 close it without making tabs implicit or silent.
3. **Machine tabs and named tabs are different kinds of partition in one strip.** An apollo agent launched with `%tab:sase` is *not* on `⌨ apollo`. Someone looking for "everything on apollo" can miss it. Mitigations:
   - the machine tab's panel footer and tooltip say "`+5 apollo agents on other tabs: ◇ sase 4, ◇ blog 1`";
   - `machine:apollo` still finds everything;
   - the Everything view grouped **by machine** shows the whole fleet per machine.
4. **Vocabulary drift.** The request says `local`, and the TUI says `here` in four places. Shipping both is sloppy; see A6.
5. **The 3-state cycle degenerates.** With one tab, "merge tribes" and "merge tribes and tabs" are identical, so a 3-cycle would have a dead step; see A4.
6. **Cross-machine consistency depends on the owner's record and wire.** Today's tribe split (a CLI edit goes to a local store that remote viewers never see) must not be repeated. Tab edits therefore write agent meta, which the fleet feed serves.
7. **Version skew.** An older target that does not know `%tab` would leave the literal text `%tab:foo` in the model prompt, because unknown directives are not matched. Dispatch must check the target's capability, and older gateways must degrade visibly.
8. **Keys are scarce.** `[`/`]` is the only convention-consistent pair (Artifacts sub-tabs and lazygit both use it), and it is taken by card blocks; see A8.

### Alternatives considered

| Approach | Verdict |
| --- | --- |
| **Saved-query tabs** (a tab is a query) | Rejected. An agent can match several tabs, so counts, marks, attention, and "move to tab" become ambiguous, and nothing is assigned at launch. |
| **Tabs as groups of tribes** (`ace.tribes.x.tab: y`) | Rejected as the primary mechanism, because it overloads tribes and needs config for every grouping. It could return later as an optional *default rule*. |
| **Automatic project tabs** (tab = `+project`) | Rejected as the default: cross-project work scatters, and many agents use `#git:home`. Worth offering later as an opt-in default rule (§9, follow-ups). |
| **An `ALL` pseudo-tab** | Rejected, per the user and for the reasons in §2. |
| **Authored `%tab` label with a view-time derived default (requested)** | **Chosen.** It is simple, explicit, portable across machines, and matches existing tribe precedents. |
| `%tab` as a kwarg of `%id` (like `tribe=`) | Rejected. sase-7o folded `%tribe` into `%id` because tribe was treated as *identity*. A tab is *placement*, not identity, and it must also apply to clan declarers and workflows. A standalone `%tab` is the right shape, as the user asked. |

### Requirement adjustments (explicit)

| # | Adjustment | Why |
| --- | --- | --- |
| **A1** | **Launch-from-view inheritance.** A prompt launched from the TUI while a *named* tab is active gets that tab, shown as a `tab: ◇ blog` context chip in the prompt bar and written into the stored prompt as `%tab:blog` on submit. It is cleared with `%tab:main` or changed with `gb`. It never applies from the default or machine tabs or from the Everything view. Config: `ace.agent_tabs.launch_from_view` (default `true`). | Otherwise a new agent disappears from the tab you are looking at. It is visible and materialized, which honors the "context is never silently applied" principle, and retries, forks, and dispatch stay deterministic. |
| **A2** | **Lineage inheritance.** An agent launched *by an agent* (via `sase run` or LaunchApproval) inherits the launcher's tab through `SASE_AGENT_TAB`. It is materialized into the child's prompt as `%tab:<t>` so it also crosses `%dispatch`. | Epics, swarms, and helpers stay with the work that spawned them. `SASE_EPIC_CLAN_TRIBE` is the precedent. |
| **A3** | `%tab:main` is a legal explicit spelling of "the default tab" and is stored as *no tab*, as tribe `default` normalizes to none. `%tab:local` is an error ("machine tabs are derived; omit `%tab` or use `%tab:main`"). | This gives A1 and A2 an opt-out and keeps reserved names unambiguous across machines. |
| **A4** | The `o` ladder has **three levels only when ≥2 tabs have agents**. Otherwise it is today's two-state Split/Merged toggle. | No dead cycle step; zero change for single-tab users. |
| **A5** | Tab names use the tribe character set `[A-Za-z0-9_.-]`, are **case-folded to lowercase** on write, and are capped at 32 characters. | Tabs are highly visible and span machines, so `Sase` and `sase` should never become two tabs. |
| **A6** | Use **`local`** as the display word for this machine everywhere: machine tab, BY_MACHINE banner, Launch Target picker, Machines pane. `machine:here` stays a query alias and `machine:local` is added. | One word for one concept. The user chose `local`, and `%dispatch:local` already reserves it. |
| **A7** | Machine tabs are enabled when dispatch config has ≥1 enrolled machine. Add an escape hatch, `ace.agent_tabs.machine_tabs: auto \| on \| off` (default `auto`). | This matches "configured", is cheap and stable at startup (no dependence on the first fleet refresh), and lets a user keep a single `main`. |
| **A8** | **`[` / `]` switch sub-tabs** (wrapping). Card-block stepping moves to **`(` / `)`**. Copied legacy `[`/`]` card-block overrides are detected with a warning. | Consistent with Artifacts sub-tabs. `(`/`)` are free on Agents. This matches the prior research. |
| **A9** | Tabs are **root-level and presentation-only**. A `%tab` on a session attach or clan join must equal the root's tab (otherwise it is a directive error pointing at "move the session/clan instead"). An inherited (A1/A2) tab is silently ignored for non-root launches. Tabs are never `%wait`, `%hold`, or fork targets. | A node never splits, launches never "move" things, and tabs stay safe to rename or move. |
| **A10** | **Move to tab** after launch: the `N` modal gains a Tab field, the palette gets "Agents: move to tab…", and a `sase agent tab {list,set,unset}` CLI is added. It rewrites meta (every clan member plus the clan record) and the stored prompt's `%tab`. Remote rows are owner-only in v1. | Mistakes happen, and a tab that cannot be fixed is not reliable. |
| **A11** | "Tabs that have agents" is computed **before the committed query**, after hide rules. The query changes per-tab *counts*, never which tabs exist. | Typing a query must never make the strip pop in or out. |

---

## 4. Proposed design

### 4.1 Vocabulary and hierarchy

- **Agent tab.** A named partition of the Agents tab's top-level nodes. Its kind is:
  - `main`: the default when machine tabs are off;
  - `machine`: `local` or a remote alias, the default when machine tabs are on;
  - `named`: from `%tab`.
- **Tab key (typed, stable):** `main`, `machine:local`, `machine:<installation_pin>`, `named:<name>`. The key is used for persistence, memory, folds, and jump targets. The label is derived.
- **Order on screen:** default and machine tabs first (`main`, or `local` then remotes in dispatch-config order), a thin kind divider `┊`, then named tabs by configured `order` and then natural alphabetical order. The order is the same on every machine and every session. First-seen ordering would shuffle between sessions.

Hierarchy on screen: **tab strip → (tribe panels | one merged panel) → grouping banners → rows.**

### 4.2 The `%tab` directive

| Form | Meaning |
| --- | --- |
| `%tab:<name>` / `%tab(<name>)` | Place this launch's root on tab `<name>` (validated, lowercased) |
| `%tab:main` | Explicit default tab, stored as *no tab*; opts out of A1/A2 inheritance |
| `%tab:local` | Error: reserved |
| two `%tab` in one prompt | Error: single-valued like `%model` (fan out with `%{%tab:a \| %tab:b}`) |
| `%tab` + `%clan(<c>)` declarer | Sets the clan's tab (clan record `clan_tab`). New generations inherit the remembered tab unless overridden, following the precedent of remembered clan tribes. |
| `%tab` + `%id(x, clan=c)` / `%id(x, session=p)` | Allowed only if it equals the root's current tab; otherwise a directive error (A9) |
| `%tab` + `%dispatch:<alias>` | Allowed. The prompt is forwarded and the owner records it. The controller preflight requires the target to advertise the `launch_tab` capability, and refuses with an upgrade hint otherwise. |
| alias | **None.** `%t` still raises the `%tribe` migration error, and reusing it would silently change what old prompts mean. |

`%proc` units: v1 covers agents and workflows. Named-proc nodes stay on the default tab until a follow-up adds the field to proc records.

Swarm prompts: each segment is its own launch. A1 covers TUI-launched swarms. For CLI swarms, a *leading* `%tab` could later inherit into every segment, the way embedded swarms inherit leading workspace refs; this is optional.

### 4.3 Data model and ownership

| Field | Where | Notes |
| --- | --- | --- |
| `tab` | `agent_meta.json` | Absent means default. Always the canonical lowercase name. |
| `tab_source` | `agent_meta.json` | `prompt` \| `view` \| `lineage` \| `moved`. Shown in the detail metadata ("Tab: ◇ blog, from launch view") and tooltips. |
| `clan_tab` | clan record `<sase_home>/agent_clans/<clan>.json` | Mirrors `clan_tribe`. Members also get `tab` materialized at launch, so any row agrees with its root. |
| session attach | `_add_agent_session_metadata` | Copies the parent's *current* `tab` into the new turn's meta. It does not copy tribe today, so this is new. |
| scan wire | sase-core `AgentMetaWire.tab`/`tab_source` plus index column | Enables `tab:` query pushdown and cheap catalogs. |
| fleet wire | `OwnerResolutionFactsWire.tab` (additive, like the v4 `tribe`/`clan_tribe`) | The gateway serves it from meta. An older gateway omits it, so rows fall back to their machine tab, with a header note "apollo: tab data unavailable (upgrade sase)". |
| **No separate tab store** | none | Avoids the tribe split-brain in which `agent_tribes.json` edits never reach remote viewers. |

**Rust core boundary.** A web app, the CLI, Telegram, or an editor would need the same answers, so the following belong in `sase_core` (in a new `agent_tab.rs`), with Python calling through `sase_core_rs`:

- tab-name validation and canonicalization, and reserved names;
- the `AgentTabKey` type;
- effective-tab resolution;
- the catalog builder;
- the directive metadata (`DirectiveValueRole::Tab`, which completes known tab names);
- typed-unit parsing plus `agent_unit_dispatch_prompt` re-emission, **without which `%tab` would be silently dropped under typed launch units**;
- the scan and fleet wire fields;
- the gateway capability.

After that lands, sase's `sase-core-revision.txt` pin must move past it.

### 4.4 Effective-tab resolution (core, pure)

```text
effective_tab(root, ctx) -> AgentTabKey
  if root.tab is set:            return named(root.tab)          # explicit wins on every machine
  if not ctx.machine_tabs:       return main
  if root is owned locally:      return machine(local)
  return machine(installation_pin_for(root.origin))             # alias is only the label

label(named(n)) = n     label(main) = "main"     label(machine(local)) = "local"
label(machine(pin)) = viewer alias for pin  (fallback: fleet_origin_alias, then "remote-N")
```

- `ctx.machine_tabs` comes from config (A7). It is computed at startup and when the config token changes, and never on a render path.
- Provisional `%dispatch` rows carry `fleet_origin_alias = target`, so they are keyed through `alias → installation_pin` from config. They land on the same tab as the authoritative row that replaces them, with no tab hop.
- Renaming an alias changes the label and keeps the key, the selection, and the memory.

### 4.5 Tab catalog and visibility

- **Existence (A11).** A tab exists iff at least one **visible** root (after `%hide` and auto-hide rules, before the committed query, not dismissed) resolves to it.
- **The strip shows iff ≥2 tabs exist.** Otherwise the Agents tab looks exactly as it does today.
- **Counts:** `lane_count` (agent nodes, matching the tribe panel's `· N`), plus the zero-suppressed hot tokens `S` (asking), `R` (running), `F` (failed), and `U` (unread). These reuse `format_agent_count_chip`'s letters and colors, so the strip and panel titles speak one language. With a committed query, counts show *matches*, which turns the strip into a "where are my search hits" map.
- **Arrivals:** a new agent on an inactive tab updates its count and shows a small `•` "new" dot until the tab is visited. The cursor never moves.
- **The last agent leaves the active tab** (dismissed or moved): switch to the nearest surviving tab (the previous tab, else the default), restoring its memory. If only one tab remains, the strip disappears; that is the requested rule.

### 4.6 Presentation pipeline

```text
local roster ∪ fleet rows (+ provisional dispatch rows)
  → hide rules
  → presentation roots (clan / session / workflow anchors)
  → effective tab per root ─────────► tab catalog (existence, order)       ← pre-query
  → committed query ────────────────► per-tab counts + attention          ← query-aware
  → scope: active tab | every tab (Everything level)
  → tribe panels (Tribes level) | one merged panel (Tab / Everything level)
  → grouping-mode tree → rows
```

Implementation notes:

- Compute the tab per root in the roster projection (`_refilter_agents` / `project_clan_tree`), which is O(roots). Only then does `finalize_agent_list` apply the query.
- Pass the scoped slice into `AgentPanelGroup.from_agents(…, merge_tribe_panels=level ≠ TRIBES)`.
- Add `(tab_key, level)` to the `_agent_panel_index()` memo key.
- Scope these by tab: `AgentPanelFoldScope` (→ `(tab_key, panel_key, merged)`), session-sticky tribe panels (`_session_mounted_panel_identities` keyed `(tab_key, tribe)`), and `_panel_selection_memory`.
- Delete `current_agents_subtab`, `_AGENTS_SUBTABS`, and the focus/fleet watcher first. Reuse nothing from them.

### 4.7 The strip: layout, anatomy, styling

**Placement.** Reuse the existing `#agents-header` row. It sits above `#agents-content` at full width and is currently hidden unless fleet problems exist. The tabs go on the left. The right side shows the *active tab's* health, falling back to the global fleet diagnostic. The row stays hidden when there is one tab and no problem, so single-tab users see nothing new. One line, no extra chrome.

**Anatomy (full tier):**

```text
▐⌨ local 9 R3▌ │ ⌨ apollo 14 R2 ◌ │ ⌨ mac 2  ┊  ◇ blog 3 S1 │ ◇ sase 12 R4 U2 •        apollo: stale · cached 2m ago
 └ active pill: accent background, dark bold text        └ kind divider      └ new-arrival dot
```

- **Active tab:** a pill (accent background, near-black bold text). The active tab is unmistakable even without color, because it is the only reversed segment.
- **Inactive tabs:** icon in accent and label `#888888`. Separators `#444444` follow `PanelTabStrip`'s conventions.
- **Icons**, all audited single-cell and bundled:
  - `⌨` for **every machine tab, including `local`**. It is unused elsewhere and reads as "a computer". Its accent is `#5FD7FF`, the color remote rows already use for their machine chip, so the strip and the rows agree.
  - `⌂` for `main`. It is the same "unassigned/home" glyph as the `@default` tribe: an untabbed agent is to tabs what an untribed agent is to tribes. `main` never coexists with machine tabs, so there is no collision.
  - `◇` for named tabs by default, overridable per tab.
  - Named-tab accents are hashed with `palette_hash.hash_palette_index` over a palette with the machine, main, and default-tribe colors removed (the Artifacts provider precedent). A tab has the **same color on every machine with zero config**.
- **Health (machine tabs):**
  - `◌` for aging or stale, and `✖` for an invalid feed or offline host, in the existing fleet warning colors;
  - the tooltip names the cause;
  - the header's right side repeats the active tab's issue.
- **Tooltips** (hover, via `PanelTab.description`): `local · this machine (athena)`, `apollo · sase_inst_v1_3f9a… · stale 2m`, `sase · configured description · 12 agents (4 running)`.

**Width tiers** (a fit ladder, as `PanelTabStrip._reflow_tier_for_width` does today):

| Tier | Inactive tab shows | Active tab shows |
| --- | --- | --- |
| full | icon, label, count, hot tokens | same, as a pill |
| compact | icon, label, `S` only | icon, label, count, `S` |
| micro | icon (colored red/amber if it has `S`/`F`) | icon, label |
| overflow | a window around the active tab with `‹3` / `2›` chips; the chip turns attention-colored if a hidden tab needs you; clicking opens the tab picker | pill |

A new `AgentTabStrip` widget should extend `PanelTab` with `badges` and `health` fields and share the render helpers. Forking the whole widget is unnecessary.

**Everything level** (§4.9). The strip stays as a legend:

```text
⊞ all tabs 40   ⌨ local 9 │ ⌨ apollo 14 │ ⌨ mac 2  ┊  ◇ blog 3 │ ◇ sase 12
```

No pill; every tab is lit at normal intensity, because all are included. `⊞` (unused, bundled) marks the level. It is a status chip, not a tab, and cannot be selected.

**Panel titles and row chips:**

- *Tribes* level: unchanged tribe panels (the tribe slice of the active tab).
- *Tab* level: the single panel is titled with the tab (`⌨ apollo · 14 [R2]`), not "All agents", which would be false while other tabs exist. With one tab it stays "All agents", as today.
- *Everything* level: the panel is titled `⊞ All agents · 40`, and each root row gets a **tab chip** (`◇ sase`, in the tab's accent) before its tribe label.
- **The machine chip is suppressed on machine tabs**, because every row there is from the same machine. It is kept on named tabs (which can span machines) and at the Everything level.

**Empty or filtered states** (a tab exists but the query excludes everything):

```text
No agents on ◇ sase match  status:running
3 matches on ⌨ local · 1 on ◇ blog        ] next tab   o all tabs
```

**Optional delight:** the main TUI tab label shows the active sub-tab (`Agents ◇ sase`) whenever the strip is visible.

### 4.8 Navigation and keys

| Action | Key | Notes |
| --- | --- | --- |
| Next / previous tab | `]` / `[` (A8) | Wraps. Walks hidden overflow tabs too, scrolling the window. |
| Card block next / previous | `)` / `(` (A8) | Moved from `]`/`[`. Update config, keymap types and metadata, fallback bindings, availability, `_CONTEXTUAL_APP_DUPLICATES` (Agents tabs vs Artifacts sub-tabs on `[`/`]`; Agents blocks vs Artifacts Files versions on `(`/`)`), help, footer, quickstart, block-rail hint, docs, the card-block glossary wording, and goldens. |
| Jump to a tab | `'` jump hints | Add a `TabJumpTarget = ("tab", AgentTabKey)` to `jump_hints.py` next to `PanelJumpTarget`, so `'` labels tabs as well as panels and rows. No new key needed. |
| Tab picker | click an overflow chip; palette "Agents: go to tab…" | Unbound keymap field `pick_agents_tab` for users who want one. |
| Mouse | click a tab | `TabClicked`, as today. |
| Digits | unchanged | They stay agent relation jumps; no numbered tabs. |

**Cross-tab jumps are transparent.** These all switch to the target's tab (or stay put at the Everything level), reveal folds, and keep the previous location for jump-back:

- `,j` / `,J` (unread / stopped);
- `"` Node Finder;
- relation numbers (a NEIGHBORS or TRIBE MEMBERS target can live on another tab; its roster row shows the tab chip);
- notification "go to agent";
- Admin Center Machines `Enter`, which **selects the machine tab** instead of rewriting the query. A secondary action keeps the old `machine:<alias>` filter at the Everything level.

**Per-tab memory:** the selected node identity, focused tribe panel, fold and scroll anchor, and deck target. Restore by identity and fall back to the nearest surviving row (tui_perf rule 4: re-read the active tab after every await). Marks stay global. Bulk actions that act on "visible" rows name their scope in the confirmation ("on ◇ sase").

**Persistence:** the active tab key is saved (off-thread, like `grouping_mode.txt`) and falls back to the default tab if it is gone. The panel level stays session-scoped, as the merge flag is today, so behavior does not change.

### 4.9 The `o` / `O` zoom ladder

```text
        o →                        o →                         o → (wraps)
Tribes ─────────► Tab (merged) ─────────► Everything (merged, all tabs)
        ← O                        ← O
```

- **Tribes:** tribe panels for the active tab (today's default).
- **Tab:** one merged panel for the active tab (today's "Merge panels", scoped to the tab).
- **Everything:** one merged panel across every tab (new), with tab chips on rows.
- **With ≤1 tab (A4):** just Tribes ↔ Merged. The stored level is kept, so reaching two tabs restores the user's choice.

**In the modal** the "Panel layout" row becomes a segmented control:

```text
Panel layout
> [o] ◉ Tribes   ○ Tab   ○ Everything        [O] back
```

`o` selects the next level and `O` the previous one, then the modal dismisses. That makes `o o` and `o O` two-keystroke cycles. `on_key` currently checks `event.character == "o"` and swallows uppercase, so add an explicit `O` branch. Click targets per segment work too. The info row adds `panels: tab` or `panels: all` only when the level is not Tribes, which keeps the row dense in the default case.

**Transitions are anchor-preserving.** They follow the same pattern as the recent "main deck honors view policies with anchor-preserving transitions" work:

- **Zooming out** keeps the selected node.
- **Zooming in from Everything with `o`** lands on the **selected node's tab**, because the anchor decides.
- **Choosing a tab at the Everything level** (click, `[`/`]` relative to the selected node's tab, or a jump hint) returns to the last per-tab level (Tribes or Tab) on that tab. This is how a zoom toggle usually behaves (compare `Z`).

### 4.10 Interactions

- **Query:** add a `tab:` field to the Agents live query profile, with pushdown declared through the new index column (tui_perf rule 9: every field declares pushdown or a known fallback). The tab scope and the query compose. The query never edits the scope, and the scope never edits the query.
- **Grouping modes:** all work within any scope. BY_MACHINE is newly valuable on **named** tabs (one project across machines) and at the Everything level. On a machine tab, suppress its lone redundant machine banner and keep the status subgroups.
- **Tribes span tabs.** A tribe's panel on a tab shows that tab's members. `%wait:@tribe` and tribe summaries stay global. The TRIBE MEMBERS roster lists every member, with tab chips on those that live elsewhere.
- **Notifications and Telegram:** notification rows can carry the tab chip later. Nothing is required for v1.

### 4.11 Launch experience

- **Prompt bar context (A1).** When the active tab is named, the prompt's context line (the one that already appears for `%dispatch` Target/Source) shows `tab: ◇ blog  (gb change · %tab:main for default)`. `gb` / `Ctrl+G b` ("ta**b**") opens a **Launch Tab picker**, the placement sibling of the `gD` Launch Target picker. `gt`/`gT` are taken by the snippet target and snippets panel; the prompt `g`-prefix table today holds `d f G m D j k J K s S t T w x X L p`, so `b` is free. The picker lists existing tabs, `main`/default, and "new tab…". On submit, `%tab:<t>` is inserted unless the prompt already has one.
- **On a machine tab** there is no inheritance. If the active tab is a *remote* machine, the context line hints `runs here → ⌨ local · gD launch on apollo`, the explicit affordance the prior research wanted.
- **Landing toast.** When a TUI launch lands on a tab other than the active one, a toast names it (`blog-fix → ◇ blog`) and that tab gets the `•` new dot.
- **LaunchApproval** shows the inherited tab (A2) in the approval card, so the human sees where the agent will appear.

### 4.12 Moving agents (A10)

- The `N` modal becomes **Tribe & Tab**, with two fields; `Tab` switches between them. Bulk marks work as they do for tribes.
- `sase agent tab {list,set,unset}` follows the CLI rules: `list` is the default, output is colored, subcommands are alphabetical, and every long option has a short alias.
- A move rewrites the root's and members' meta (`tab`, `tab_source: moved`), the clan record, and the stored prompt's `%tab`, using the `directive_edit` machinery that the tribe `N` path already uses. Future session turns inherit the new tab.
- On a remote row the action is disabled with the reason "tab moves run on the owning machine". A fleet mutation capability can lift this later.

### 4.13 Configuration

```yaml
ace:
  agent_tabs:
    machine_tabs: auto        # auto | on | off   (A7)
    launch_from_view: true    # A1
    tabs:                     # optional per-tab styling; never creates tabs
      sase:
        icon: "◆"
        color: "#AF87FF"
        order: 10
        description: "Everything touching the sase repos, on any machine."
```

These are permanent user choices, so they are **config fields, not feature flags**. The implementation epic should carry one **beta flag** as scaffolding (`agent_tabs`), removed before landing per `sase_flags.md`.

### 4.14 Glossary strands (draft; add through `/sase_memory_write` during implementation)

> **Agent Tab** *(aka sub-tab, Agents sub-tab)*: An agent tab is one sub-tab of the Agents tab, a named partition of its top-level sase nodes. A launch prompt assigns one with `%tab:<name>`. An agent without one lands on the default tab: `main`, or its machine tab when remote machines are enrolled. Membership belongs to the whole agent clan, agent session, or workflow, so a node never splits across tabs. Tribe panels divide a tab, and `o`/`O` step the panel view between tribe panels, one merged panel for the tab, and one merged panel for every tab. The tab strip appears only while two or more agent tabs have agents. An agent tab is presentation only: it never changes where an agent runs, its identity, clan, session, or tribe, or what `%wait` can target. It is not the Agents tab itself, which is a main TUI tab.

> **Machine Tab**: A machine tab is an agent tab derived from where an agent runs rather than from `%tab`. When the current machine has enrolled remote machines, an agent launched without `%tab` appears on the `local` machine tab if this machine owns it, or on a tab labeled with the owning machine's configured alias. Machine tabs show the `⌨` icon. They are keyed by the machine's installation identity, so renaming an alias only relabels the tab, and they mark stale or failing feeds. An explicit `%tab` always wins, so a named agent tab can gather one project's agents from several machines. With no enrolled remote machines, the same agents share the `main` tab instead.

Also update these memory notes:

- the `xprompts.md` directive table (`%tab`);
- the Nav Section and Node Panel strands (tribe panels are per tab);
- the Agent Data Card Block key wording (`(`/`)`);
- `dispatch.md` (`%tab` forwarding and capability).

---

## 5. Reliability and performance checklist

1. **One source of truth.** The owner's `agent_meta.json` holds the tab, and it is served in the fleet feed. There is no viewer-local override store.
2. **Deterministic placement.** Membership is root-level, keys are typed and stable, and inheritance is materialized, so retry, fork, history, and dispatch replay to the same tab.
3. **Version skew is loud, not silent.** Dispatch requires the target's `launch_tab` capability. An old gateway degrades to machine tabs with a header note.
4. **A tab switch does no I/O.** It is a projection plus a panel re-slice. Widgets are reused by tribe key across tabs, and only the panels whose key set differs are mounted or unmounted. Inactive tabs are never painted, and the catalog and strip repaint only when the membership signature changes.
5. **Targets:**
   - keep the j/k p95 below 16 ms on every tab;
   - add a tab-switch key-to-paint measurement to `SASE_TUI_PERF` with a target p95 below 50 ms at 500 roots, and warm-cache per-tab panel sets only if measurement demands it;
   - idle ticks: no additional surface reloads (tui_perf rule 14).
6. **No layout jitter.**
   - The strip's existence ignores the query (A11).
   - At startup, machine mode comes from config, not from the first async fleet refresh. `_agents_fleet_available` starts `False`, so relying on it would flip the label `main`→`local`.
   - The strip appears when the second tab gains an agent, which is a real membership change and not a filter echo.
7. **Attention never hides.** Tab badges, a colored overflow chip, and tab-transparent global jumps.
8. **Tests:**
   - directive contract parity (Python and Rust);
   - typed-unit re-emission;
   - A9 conflict errors;
   - scan and fleet wire round-trips, including a missing field;
   - provisional → authoritative dispatch rows staying on one tab;
   - alias rename preserving selection;
   - last-agent-leaves-tab fallback;
   - `o`/`O` ladder with 1 and 2+ tabs;
   - anchor-preserving zoom;
   - a glyph audit extended to `⌨ ◇ ⊞ ◌ ⌂`;
   - PNG goldens: hidden strip, main+named, machine mode, overflow, Everything, empty/filtered, stale host;
   - legacy card-block override warning;
   - both states of the scaffolding flag.

---

## 6. Implementation plan (suggested epic phases)

| Phase | Repo | Scope |
| --- | --- | --- |
| **P0 Cleanup and keys** | sase | Delete the Focus/Fleet sub-tab remnants. Move card blocks to `(`/`)` with legacy-override warning, help, goldens, and glossary wording. `[`/`]` stay unbound on Agents until P3. |
| **P1 Core contract** | sase-core | `agent_tab.rs` (validation, canonicalization, reserved names, `AgentTabKey`, `effective_tab`, catalog builder); `tab` directive metadata and `DirectiveValueRole::Tab`; typed-unit parse and dispatch re-emit; `AgentMetaWire.tab/tab_source` and index column; fleet owner fact `tab`; gateway capability `launch_tab`; Python bindings. Then move sase's core pin. |
| **P2 Launch path** | sase | Python directive parse and validation (A3, A5, A9); meta, clan-record, and session inheritance writes; `SASE_AGENT_TAB` lineage (A2); dispatch capability preflight; `sase agent tab` CLI; `tab:` query field with pushdown; `docs/xprompt.md` Tab Directive section. |
| **P3 Tabs in the TUI** (behind the beta flag) | sase | Tab-per-root projection, catalog, `AgentTabStrip` in `#agents-header`, `[`/`]`, per-tab memory, scoped folds, sticky panels and selection, `'` tab hints, cross-tab jumps, empty states, arrival dots, tooltips. |
| **P4 Zoom ladder** | sase | `o`/`O` three-level ladder in the modal (A4), panel titles, Everything-level tab chips, info row, anchor-preserving transitions. |
| **P5 Machine tabs** | sase | Config-derived machine mode (A7), `local` vocabulary (A6), `⌨` icons and health, machine-chip suppression, "+N on other tabs" footer, Admin Center `Enter` → tab, glossary strands. |
| **P6 Launch UX and moves** | sase | Prompt-bar tab chip and `gb` picker (A1), landing toast, LaunchApproval display, `N` Tribe & Tab modal (A10), docs (`ace.md`, `remote_dispatch.md`, `agent_sessions.md`), perf bench, remove the flag. |

P1 must land (and the pin move) before P2. P3 through P6 are sase-only and can be reviewed visually one at a time.

---

## 7. Open questions for Bryan

1. **A1 default.** Should launch-from-view inheritance be on by default (my recommendation) or opt-in?
2. **Named-tab order.** Configured order then alphabetical (recommended), or most-recently-active first? Recency is handy, but tabs would move under your fingers.
3. **`here` → `local` everywhere (A6).** Is that OK, or should the change stay confined to the tab strip?
4. **Everything-level `[`/`]`.** Leave to the adjacent tab (recommended), or no-op with a hint?
5. **Project-default rule (follow-up).** Should `+project` (or project config) optionally supply a default tab, so `+blog` agents land on `◇ blog` with no directive? That fulfills "group a project on one tab" with zero typing, but it is a second placement rule. I would ship it later and opt-in.

---

## 8. Recommendation

Implement **dynamic agent tabs as an authored, root-level, presentation-only label (`%tab`) with a view-time default**. The default is `main`, or when remotes are enrolled the machine tab: `⌨ local` or `⌨ <alias>`.

- **Storage and resolution:** the tab lives in the owner's agent meta and in the fleet feed, and a small `sase_core` resolver and catalog give every frontend and every machine the same answer.
- **Strip:** the existing `#agents-header` row hosts an icon-and-badge strip that appears only with two or more tabs and uses `[`/`]` (card blocks move to `(`/`)`).
- **`o` ladder:** `o` becomes a three-level zoom ladder (**Tribes → Tab → Everything**) with `O` reversing it. It stays today's toggle when there is one tab.
- **Coherence:** launch-from-view and lineage inheritance, both visible and written into the prompt, plus a Move-to-tab action, keep tabs coherent without constant typing.
- **Reliability:** tab switches are pure projections, attention is badged, and jumps are tab-transparent.

This meets every stated requirement. The deliberate adjustments (A1–A11) make the feature feel native rather than bolted on.
