# Dynamic Agents tabs: `%tab`, machine tabs, and the `o`/`O` layout ladder

**Consolidated research · lead synthesis · 2026-09-27**

**Inputs:**

- Five independent reports, preserved beside this file as `__cdx`, `__cld`, `__grk`, `__mus`, and `__gem`.
- The prior synthesis
  `research:202609/agent_machine_tabs_and_cluster_semantics/agent_machine_tabs_and_cluster_semantics.md`.
- My own verification pass over the current `sase` tree (TUI, launch, dispatch, and keymaps) and the linked `sase-core` checkout (fleet contract, typed launch units, directive metadata, tribe and scan wires).

Where the reports disagreed on a fact, I checked the code. §2 lists the results, including five corrections to claims made in the reports.

---

## 0. Decision in brief

**Build it.** The request is a better idea than the prior machine-tabs design. It makes **named, launch-assigned working sets** the primary concept. Machine tabs become the *default placement rule* for agents that did not choose a tab. I would take this approach, with the adjustments in §3.

The model in one sentence:

> An **agent tab** is an exclusive, root-level, presentation-only placement. It is authored at launch with `%tab:<name>` and stored on the owning machine's agent record. An agent without one is resolved *at view time* to the default tab: `main`, or, when this machine has remotes configured, its **machine tab** (`⌨ local` or `⌨ <alias>`).

Six rules make the feature intuitive, reliable, and beautiful:

1. **One agent, one tab, decided by the presentation root.**
   - Sessions, clans, and workflows never split across tabs.
   - Tabs are never `%wait`, `%hold`, fork, or dispatch targets. They only say *where an agent is shown*.
2. **The default is never stored.**
   - Only an explicit tab name is persisted.
   - `main`, `local`, and machine aliases are view-time labels. Enrolling or renaming a machine therefore relabels tabs without migrating any data.
3. **Tabs stay coherent without typing `%tab` on every launch.**
   - A TUI launch from a named tab inherits that tab through a visible, removable prompt chip.
   - An agent launched *by an agent* inherits its parent's tab.
   - Both are written into the prompt as an explicit `%tab`, so retries, forks, and `%dispatch` all replay to the same tab. This is the most important addition to the request.
4. **The strip is invisible until it is useful, and it never hides something that needs you.**
   - It appears only when two or more tabs have agents.
   - Inactive tabs carry attention badges.
   - Every global jump (unread, stopped, Node Finder, notifications, relation numbers) switches tabs for you.
5. **`o` becomes a zoom ladder: Split by tribe → Merged → All tabs.**
   - `O` walks the ladder backwards.
   - With only one tab, the ladder collapses back to today's two-state toggle.
   - There is no ALL tab.
6. **`[` / `]` switch tabs**, as they already do on Artifacts. Card-block stepping moves to `(` / `)`.

---

## 1. Critique: is this a good idea?

### 1.1 Why yes

The Agents tab already has two organizers, and neither one answers "which working set am I in?":

- **Tribes** say what an agent is *for*: `@review`, `@epic`, `@job`. They are also wait and fork targets.
- **Grouping modes** say how rows are *sorted*: by project, date, status, or machine.

The `machine:` query facet is a filter, and `BY_MACHINE` makes one long tree. Some users already overload tribes as project buckets because nothing else can pin a working set.

A dynamic, exclusive tab fills that gap:

- It costs nothing until it is used, because the strip stays hidden with one tab.
- It scales to more machines and projects without deeper nesting.
- It supports the request's headline case: `%tab:sase` gathers one project's agents from athena, apollo, and mac.

Machine tabs cannot express that last case. It needs the opposite predicate: ignore where an agent ran, and honor a name the user assigned.

### 1.2 What to keep from the prior research, and what to drop

**Keep** these rules, all of which transfer unchanged:

- A tab switch is an in-memory projection over one warm roster, on one widget surface.
- Selection is restored by identity.
- Membership is decided by the structural root.
- Attention stays visible on inactive tabs.
- The tab scope and the committed query compose, and neither ever edits the other.
- Machine identity comes from the stable installation, not the alias.
- `[`/`]` move tabs and `(`/`)` move card blocks.
- A viewing choice never triggers an automatic `%dispatch`.
- The dead Focus/Fleet sub-tab state is deleted.

**Drop** these:

- **The `All` tab.** It is a projection, not a membership. Put in the strip, it makes every agent live on two tabs, which confuses counts and bulk-action scope.
- **Always-visible tabs for empty enrolled machines.** They contradict the user's rule of hiding the strip when only one tab has agents. Admin Center already owns machine health.
- **The "Agent Cluster" umbrella.** All five reports agree it is unnecessary. Tabs are a view scope with a narrow contract, so leave clans and tribes alone.

### 1.3 Weak spots in the request as written

1. **"No `%tab` → main" leaks agents out of their tab.** Suppose you are on tab `blog` and launch "fix the typo". Read literally, the rule sends the agent to `main`, and it vanishes from the view you are looking at. The same happens to every helper, swarm, or epic worker spawned by a `blog` agent. This is the biggest usability hole in the request. Adjustments R1 and R2 fix it.
2. **Named tabs and machine tabs are different kinds of partition in one strip.** An apollo agent launched with `%tab:sase` is *not* on `⌨ apollo`, so someone looking for "everything on apollo" can miss it. Three things mitigate this:
   - the machine tab's tooltip says "+5 apollo agents on other tabs";
   - `machine:apollo` still finds every apollo agent;
   - the All-tabs view grouped by machine shows the whole fleet per machine.
3. **The requested three-state cycle degenerates.** With one tab, "merge tribes" and "merge tribes and tabs" are the same view, so the cycle would have a dead step (R6).
4. **Vocabulary drift.** The request says `local`, but the TUI says `here` in the BY_MACHINE banner, the Launch Target picker, the Machines pane, and `machine:here` (R9).
5. **Version skew is real, and there is nothing to catch it.**
   - An older remote leaves `%tab:foo` in the model prompt as literal text.
   - An older controller rejects a newer contract's rows outright.
   - No capability check runs before each dispatch (§6.3–6.4).
6. **Key scarcity.** `[`/`]` is the only pair that matches the rest of the app, and it currently steps card blocks (R7).

### 1.4 Alternatives considered

| Approach | Verdict |
| --- | --- |
| **Machine tabs plus an `All` tab** (the prior research) | Rejected. It solves fleet density only, and `All` is a projection pretending to be a place. |
| **Saved-query tabs** | Rejected. An agent can match several tabs, which makes counts, marks, attention, and moves ambiguous. |
| **Tabs as groups of tribes** | Rejected as the primary mechanism, because it overloads tribes and requires config for every grouping. |
| **Automatic project tabs** (tab = `+project`) | Deferred as an opt-in default rule (§11). Cross-project and `#git:home` work would scatter, and the strip would appear as soon as two projects had agents. |
| **`%id(…, tab=)` instead of `%tab`** | Rejected. `%tribe` was folded into `%id` because a tribe is *identity*. A tab is *placement*, like `%dispatch`, and must also apply to clan declarers and workflows. |
| **An authored `%tab` with a view-time derived default (requested)** | **Chosen.** It is explicit, portable across machines, and root-scoped. |

---

## 2. Verified ground truth

This table records what the code does today. **Bold** rows correct or settle claims made in the reports.

| Area | Finding | Evidence |
| --- | --- | --- |
| **Tribe storage (split-brain)** | A `%id(tribe=)` launch always writes `agent_meta.json["tribe"]`. It also writes `~/.sase/agent_tribes.json`, but only when `cl_name` is set. In the TUI, the store overrides the metadata. The `sase agent tribe` CLI writes **only the store**. The fleet serves the tribe from **meta**, so remote viewers never see CLI edits. **grk's "mirror tribe with a mutable `agent_tabs.json` store" would copy this defect.** | `run_agent_directive_metadata.py:294`, `run_agent_directives.py:101-117, 639-648`, `_loading_helpers.py:400-404`, `agents/cli_tribe.py:137-157` |
| **Fleet wire strictness** | Every summary and owner wire uses `#[serde(deny_unknown_fields)]` (`OwnerResolutionFactsWire`, `ResolvedAgentSummaryWire`, catalog pages, snapshot). Every row is stamped with the writer's contract `schema_version`, and a reader rejects any version above its own. **Any contract bump therefore breaks older readers, even one that adds no field.** An older controller marks the whole host `invalid` (`fleet_envelope_invalid`). Other hosts keep working. | sase-core `fleet_contract/resolution.rs:56-141`, `error.rs:11-17`, `validation.rs:203-216`, `federation.rs:230-243` |
| **How `tribe` reached the fleet** | Commit `d0ec62c` added `tribe`/`clan_tribe` as `#[serde(default)]` and bumped the contract from 1 to 2. **There was no negotiation and no capability flag.** The protocol version is matched exactly (`FLEET_PROTOCOL_VERSION = 2`). **cdx's "fleet v2 negotiation" is not how the codebase evolves this contract** (§6.3). | sase-core `git show d0ec62c`, `fleet_auth.rs:749-757` |
| **Unknown directives** | An unknown `%tab:foo` stays **verbatim in the prompt**. It is not stripped and raises no error, both in Python (`_directive_collect.py:71`) and in Rust typed units (`typed_units.rs:468 _ => {}`). **So cdx's "silently lost by typed fan-out" is wrong.** The real risk is literal directive text reaching the model on a target that has not been upgraded. | as cited |
| Dispatch | The controller strips only `%dispatch`, and the target re-parses the full prompt. There is **no per-dispatch capability or version check**: the preview checks only enrollment and quarantine. The remote's contract version is known only through `sase machine status` (`fleet_contract_schema_version`). | `_directive_scan.py:74-125`, `dispatch/launch.py:248-262`, `dispatch/models.py:431` |
| **Panel merge flag** | `_agent_panels_grouped` is **session-only and never saved**. **mus's claim that it is persisted is wrong.** Fold snapshots only record `merged` as part of the scope key. | `_state_init_agents.py:290`, `_panel_navigation.py:350`, `agent_fold_persistence.py:251-259` |
| Grouping modal | Pressing `o` in the modal toggles the panels and dismisses the modal. Uppercase `O` is lowercased, misses the choice table, and is **swallowed**. The only enum value is `AgentGroupingAction.TOGGLE_PANELS`. | `agent_grouping_modal.py:19-25, 161-175, 219-222` |
| `o` / `O` keys | `o` is `choose_agent_grouping`. App-level `O` (`cycle_grouping_mode_reverse`) is **disabled on Agents**, so it is effectively free there. | `default_config.yml:860-862`, `_app_action_availability.py:222-224` |
| Brackets | `[`/`]` are `prev_card_block`/`next_card_block`. They share a collision allowance with Artifacts sub-tab cycling. `(`/`)` are used only by Artifacts Files version stepping and are **free on Agents**. `{`/`}` resize deck panels. | `default_config.yml:670-694`, `keymaps/registry.py:146-151` |
| `PanelTabStrip` | Supports icons, accents, full/compact/micro tiers, `reflow_to_fit`, tooltips, and cell-correct click ranges. It has **no count badges, no attention markers, and no overflow window.** Artifacts, Projects, Config, Help, and Statistics use it; Agents does not. | `widgets/panel_tab_strip.py` |
| Agents layout | The order is: info row, filter bar, `#agents-header` (hidden unless fleet problems exist, holds `#agents-fleet-status`), then content. | `_app_layout.py:122-146`, `_fleet_header.py:32-54` |
| Dead state | `AgentsSubTab = Literal["focus","fleet"]`, `current_agents_subtab`, and `_AGENTS_SUBTABS` are always forced back to `"focus"`. | `app.py:108,197`, `_fleet_projection.py:91-133` |
| **Glyphs** | `⌂` is **already the default-tribe icon** (`default_config.yml:359`) **and the command-line project chip**. `▣` means workspace/xprompt. `⇄` is the remote machine chip in the compact detail header, and is also `RELATION_GLYPH` and the "restore" toggle. `◌` means **hidden**. `◇` is the bead "ready" glyph. `⌨`, `⊞`, `☰`, `☁`, and `⌗` are unused. The TUI uses **no Nerd Font glyphs**; the goldens use Fira Code, then DejaVu Sans, then Noto Emoji. `🖥` measures one cell in Rich but draws two in emoji-presentation terminals. | `rg` over `src/sase`, `ace/tui/fonts/README.md` |
| Count chip | `format_agent_count_chip` letters are `S` for **stopped** (needs you), `R` running, `Q` queued, `W` waiting, `F` failed, `U` unread (gold background), and `D` done. **cld's "S = asking" is a misreading**, although the design intent is the same. | `ace/tui/agent_count_chip.py` |
| Hide pipeline | The load stage applies dismiss rules, auto-dismiss, `%hide`, and `hide_non_run_agents`. After that come folds, then the committed query, then panel build, which excludes `STARTING` rows. | `_loading_compute.py:377-510`, `_loading_finalize.py:404-433`, `agent_panels.py:109-117` |
| Root anchoring | Every descendant takes its outer root's tribe (`anchors.get(id(agent), agent).tribe`). `@default` comes first, and the rest are sorted case-insensitively. The merged title is `All agents`. | `agent_panels.py:18-155`, `_display_panel_titles.py:154` |
| Machines | `MachineRecord` has `alias` and `pinned_installation_id` and lives under `dispatch.machines.<alias>`. Remote rows carry `fleet_origin_alias` and `fleet_origin_installation_id`, and provisional dispatch rows set both from the target. `%dispatch:local` is already reserved. | `dispatch/models.py:111-123`, `_directive_values.py:124`, `dispatch_launch_rows.py:163` |
| Precedents | `SASE_EPIC_CLAN_TRIBE` passes a tribe down through the environment. Artifacts provider tabs use hashed accents (`palette_hash`). `PROJECT_ACCENTS` is an 18-color palette with matched luminance. Commit `12ae3014b9` introduced anchor-preserving deck view transitions (capture an anchor, bump a generation, restore). | `bead/work_types.py:18`, `_artifact_tab_descriptors.py`, `project_accents.py` |
| Tribe grammar | `^[A-Za-z0-9_.-]+$`, with **no length cap and no case folding**. `default` is reserved only for display. | sase-core `agent_tribe.rs:44-57` |

---

## 3. Requirement adjustments

Each adjustment is labeled by type: **Addition** adds something the request did not ask for, **Change** alters a stated requirement, and **Clarification** pins down something the request left open.

| # | Type | Adjustment | Why |
| --- | --- | --- | --- |
| **R1** | Addition | **Launch-from-view inheritance.** A TUI launch while a *named* tab is active gets that tab. It shows as a `tab: blog` chip in the prompt bar and is written into the prompt as `%tab:blog` on submit. `%tab:main` or the chip's clear action removes it. It never applies from `main`, from a machine tab, or from the All-tabs view. | Without it, a new agent disappears from the tab you are looking at. The chip is visible and the tab is written into the prompt, which honors the launch-context rule that context is "not silently applied to prompts". |
| **R2** | Addition | **Lineage inheritance.** An agent launched by an agent (`sase run`, LaunchApproval, `sase bead work`) inherits its launcher's tab through `SASE_AGENT_TAB`. The tab is written into the child's prompt, so it also survives `%dispatch`. | Epics, swarms, and helpers stay with the work that spawned them. `SASE_EPIC_CLAN_TRIBE` is the precedent. |
| **R3** | Clarification | **Tabs belong to the root.** Session follow-ups, monitor turns, and gate turns inherit the session root's tab. Clan joiners inherit the declarer's tab. Workflow children inherit the workflow's tab. An explicit mismatch is a directive error that says "move the session or clan instead". | A tab filter must never split a container or duplicate it. grk's "allow a follow-up to split off" is rejected. |
| **R4** | Change | **Name grammar:** input is lowercased, then must match `^[a-z0-9][a-z0-9_.-]{0,31}$`. Colon and paren forms (`%tab:sase`, `%tab(sase)`) are accepted. There are no keyword arguments, no backtick-quoted names, and no one-letter alias; `%t` keeps raising the retired-tribe migration error. | Tabs are highly visible and span machines, so `Sase` and `sase` must never become two tabs. A first-seen spelling (grk, gem) would differ from one machine to the next. 32 characters fits the strip. |
| **R5** | Change | **Reserved names:** `%tab:main` is an explicit spelling of the default placement and is stored as *no tab*; it is also how you opt out of R1 and R2. `%tab:local` and `%tab:all` are rejected with guidance ("machine tabs are derived; omit `%tab`" and "use `o` to see all tabs"). **Machine aliases are not reserved.** A `%tab:apollo` beside `⌨ apollo` is disambiguated by the icon, and the editor shows a non-fatal warning. | Aliases are local to each viewer's config and can be renamed. A prompt written on one machine must not become invalid on another. Rejects grk's "reserve enrolled aliases". |
| **R6** | Change | **The `o` ladder has three levels only when two or more tabs have agents.** Otherwise it is today's Split/Merged toggle. The chosen level is remembered, so it comes back when a second tab appears. | This avoids a dead step and changes nothing for single-tab users. |
| **R7** | Addition | **`[` / `]` cycle tabs (wrapping). Card blocks move to `(` / `)`.** A copied legacy `[`/`]` card-block override triggers a warning at config load. | This matches Artifacts sub-tabs. `(`/`)` are free on Agents, and digits remain agent-relation jumps. |
| **R8** | Clarification | **A tab exists when at least one visible root resolves to it.** Visible means after dismiss and hide rules, *before* the committed query, and including `STARTING` roots. The query changes each tab's count, never which tabs exist. | Typing a query must never make the strip pop in or out. Rejects grk's and mus's post-query occupancy. |
| **R9** | Change | **`local` becomes the display word for this machine**, on the machine tab, the BY_MACHINE banner, and the Launch Target picker. `machine:here` stays as a query alias, and `machine:local` is added. | One concept, one word. The user chose `local`, and `%dispatch:local` already reserves it. |
| **R10** | Clarification | **Machine mode** is on when this machine's config has at least one `dispatch.machines` record, quarantined ones included. It is computed from the config token, **never** from the first fleet refresh. `ace.agent_tabs.machine_tabs: auto \| on \| off` provides an override. | This keeps labels stable at startup (no flip from `main` to `local`). `off` is a legitimate lasting preference, so it is a config field, not a flag. |
| **R11** | Addition | **An emptied active tab stays put.** If the last agent on the active tab is dismissed or moved, the tab stays selected, showing an empty state, until you navigate away. Only then does the strip re-evaluate, and it may hide. | The place you are standing does not vanish under the cursor (gem). |
| **R12** | Addition | **Move to tab** after launch: the `N` modal becomes *Tribe & Tab*, and `sase agent tab {list,set,unset}` is added. A move rewrites the root's and members' meta and the stored prompt's `%tab`. It is disabled on remote rows in v1. | A tab that cannot be fixed after a mistake is not reliable. It ships in the epic's last phase, not the first slice. |
| **R13** | Clarification | **Tabs are never scoped by the dispatch target, and vice versa.** Selecting `⌨ apollo` never adds `%dispatch:apollo`. Instead, the prompt bar hints `runs on local · gD launch on apollo`. | Viewing is not targeting (the lesson of Focus/Fleet). |

---

## 4. Semantic model

### 4.1 Stored value versus effective tab

The agent record stores one optional field:

```text
agent_tab: Option<TabName>        # None = default placement; never "main"/"local"/alias
agent_tab_source: prompt | view | lineage | moved   # for detail metadata and debugging
```

Every viewer resolves the effective tab of each **presentation root** with the same pure function:

```text
effective_tab(root, viewer) -> AgentTabKey
  if root.agent_tab is set            -> Named(root.agent_tab)          # wins on every machine
  if not viewer.machine_mode          -> Main
  if root is owned by this machine    -> Machine(Local)
  else                                -> Machine(installation_id(root)) # alias is only the label
```

| Stored | Machine mode | Origin | Key | Label |
| --- | --- | --- | --- | --- |
| absent | off | any | `Main` | `main` |
| absent | on | this machine | `Machine(Local)` | `⌨ local` |
| absent | on | remote apollo | `Machine(sase_inst_v1_…)` | `⌨ apollo` (this viewer's alias) |
| `sase` | any | any | `Named("sase")` | `sase` |
| `apollo` | on | any | `Named("apollo")` | `apollo`, distinct from `⌨ apollo` |

Four details:

- **Provisional dispatch rows** carry the target alias. Resolve it to the installation ID through `dispatch.machines.<alias>.pinned_installation_id`, so the row lands on the same tab as the authoritative row that replaces it, with no tab hop.
- **Renaming an alias** changes the label and keeps the key, the selection, and the per-tab memory.
- **An origin with no configured record** gets the fallback label `fleet_origin_alias`. A session-only key is used, and selection is never persisted against it.
- **The local key** is an in-process discriminator. Do not read an installation identity on a render path.

### 4.2 The `%tab` directive

| Form | Meaning |
| --- | --- |
| `%tab:<name>` / `%tab(<name>)` | Place this launch's root on the named tab. The name is lowercased and validated (R4). |
| `%tab:main` | The default placement. Stored as absent, and opts out of R1 and R2. |
| `%tab:local`, `%tab:all` | Error with guidance (R5). |
| Two `%tab` directives | Error, even when they agree (single-valued like `%model`). Use fan-out for several tabs: `%{%tab:a \| %tab:b}`. |
| With a `%clan(<c>)` declarer | Sets the generation's tab, recorded as `clan_tab` on the clan record (mirrors `clan_tribe`). |
| With a session attach or clan join | Must equal the root's tab or be omitted (R3). An *inherited* R1/R2 tab is silently ignored for non-root launches. |
| With `%dispatch:<alias>` | Allowed. The target owns and records the tab. Preflight rules are in §6.4. |
| On a stand-alone `%proc` unit | Error in v1. Named procs stay on the default tab. |
| Inside fenced or disabled regions | Ignored, using the existing `protect_fenced_blocks` pipeline. |
| Swarm `---` segments | Each segment is its own launch. R1 applies to TUI swarms. |

`%tab` is stripped before the model sees the prompt, like `%dispatch`.

### 4.3 Lineage and replay

- **Retry and revive** keep the tab, because the metadata and prompt are preserved (add `agent_tab` to `preserved_agent_metadata`).
- **Fork** reconstructs the prompt with the source's `%tab`, which stays editable before launch.
- **Dismissed bundles** keep the field.
- Because R1 and R2 write the tab into the prompt, every replay path is deterministic.

---

## 5. TUI design

### 5.1 Hierarchy and pipeline

On screen: **tab strip → tribe panels (or one merged panel) → grouping banners → rows.**

Each layer has one job: *a tab is where you are working; a tribe is what the agents are for; grouping is how the rows are sorted.*

```text
local roster ∪ fleet rows ∪ provisional dispatch rows
  → dismiss / hide rules
  → presentation roots (session / clan / workflow anchors)
  → effective tab per root ─────────► tab catalog (existence, order)     ← pre-query (R8)
  → committed query ────────────────► per-tab counts + attention          ← query-aware
  → scope: active tab | every tab (All-tabs level)
  → tribe panels (Split) | one merged panel (Merged / All tabs)
  → grouping tree → rows (existing incremental diff path)
```

- Compute the tab per root in the roster projection. That is O(roots) and needs no I/O.
- Add `(tab_key, level)` to the `_agent_panel_index()` memo key.
- Key the fold scope, the session-sticky tribe panels, and `_panel_selection_memory` by `(tab_key, committed_query)`, so an empty `@review` from one tab does not linger on another.
- Delete `AgentsSubTab`, `current_agents_subtab`, `_AGENTS_SUBTABS`, and the focus/fleet watcher first. Reuse none of it; its name collides with this feature.

### 5.2 Catalog, order, and selection

- **Order** is the same on every machine and in every session. First-seen order would shuffle.
  1. The default tab: `main`, or `⌨ local` in machine mode.
  2. Remote machine tabs, in `dispatch.machines` order. Unconfigured origins follow, sorted by alias.
  3. A thin kind divider `┊`.
  4. Named tabs in natural, case-insensitive order. An optional `order` config value comes first.
- **The strip shows only when the catalog has two or more tabs**, or while the R11 latch holds.
- **Startup selection:**
  1. the persisted active key, saved off-thread like `grouping_mode.txt`;
  2. otherwise the default tab, if it has agents;
  3. otherwise the tab holding the newest root that needs attention;
  4. otherwise the first tab.
- **Arrivals** on an inactive tab update its count and add a `•` "new" dot until you visit. The cursor never moves.
- **Landing toast:** when a TUI launch lands on a tab other than the active one, a toast names the destination (`blog-fix → blog`) and offers a jump.
- **Machine tab disappears** (its machine is unenrolled while active): fall back to the default tab and show a toast.
- **Counts** are top-level sase agents, matching the tribe panel's `· N`, not rendered rows. Show `N+` while history is known to be incomplete (the bounded first load).

### 5.3 The strip: placement, anatomy, and style

**Placement.** Reuse the existing `#agents-header` row, which sits at full width above `#agents-content`.

- Tabs go on the left. The right side shows the active tab's machine health, falling back to the global fleet diagnostic.
- The row is shown when the strip is visible *or* a diagnostic exists.
- It stays hidden otherwise. **That is the golden-preserving path:** local-only users without `%tab` see a pixel-identical Agents tab.
- Do not use the info row (already dense) or the space above the filter bar (the filter is an editor; the strip is a destination).

**Anatomy, full tier** (active tab `sase`):

```text
 ⌨ local 9  │  ⌨ apollo 14 S1  │  ⌨ mac 2   ┊  ▐ sase 12 U2 ▌  │  blog 3 •          apollo: stale · cached 2m ago
 └ machine glyph, cyan                            └ active pill: accent background, dark bold text
```

- **Active tab:** a filled pill (accent background, near-black bold text). It is the only reversed segment, so it reads even without color.
- **Inactive tabs:** the label is drawn in the tab's accent at normal weight. This follows the `+project` chip grammar, where the colored name *is* the identity. Separators are `#444444`.
- **Machine tabs:** `⌨` (U+2328) in the existing remote-machine cyan `#5FD7FF`, for **every** machine tab including `local`.
  - It is one cell wide, covered by the bundled DejaVu fallback, and unused elsewhere. It reads as "a computer".
  - Rejected alternatives:
    - `⌂`: already the default-tribe icon and the project chip.
    - `▣`: already means workspace/xprompt.
    - `⇄`: already the relation glyph, and it means "remote", which is wrong for `local`.
    - `◌`: already means hidden.
    - `🖥`, `☁`, `🏷`: emoji width hazards.
    - Nerd Font glyphs: not used anywhere in the TUI.
  - Optional polish: move the compact detail header's machine chip from `⇄` to `⌨`, so one glyph means "machine" everywhere.
- **Named tabs:** no glyph by default; *the icon means "machine"*.
  - The accent is the project's accent from `project_accent()` when the tab name is an enabled project key, so `%tab:sase` matches the `+sase` chip.
  - Otherwise the accent is `PROJECT_ACCENTS[hash_palette_index(name)]`.
  - Either way, a tab has the same color on every machine with zero config.
- **`main`:** neutral `#AFAFAF`, no glyph. It never appears alongside machine tabs.
- **Badges:** the count in chip-neutral `#AFAFAF`. Then only the zero-suppressed **attention** tokens from `format_agent_count_chip`: `S` stopped, `F` failed, `U` unread, in their existing colors. So the strip and the panel titles use one vocabulary.
  - Running and done counts are omitted, because the strip is a "where do I need to go" map.
- **Machine health:** a stale host's label turns amber and an invalid or offline host's label turns red, using the existing fleet-header colors. The cause appears in the tooltip and on the right side of the header row. No new glyph (`◌` already means hidden).
- **Tooltips** (`PanelTab.description`):
  - `local · this machine (athena)`
  - `apollo · stale 2m · +5 apollo agents on other tabs: sase 4, blog 1`
  - `sase · 12 agents on athena, apollo`

**Width tiers and overflow.** Build an `AgentTabStrip` that extends `PanelTab` with `badges` and `health` fields and shares the render helpers; forking the widget is unnecessary.

| Tier | Inactive tab shows | Active tab shows |
| --- | --- | --- |
| full | glyph, label, count, attention | same, as a pill |
| compact | glyph, label, `S`/`F` only | glyph, label, count, attention |
| micro | glyph or the first 3 letters, colored red or amber if attention | glyph and label |
| overflow | a window around the active tab, with `‹3` and `2›` chips (attention-colored if a hidden tab needs you); clicking one opens a searchable tab picker | pill |

The overflow window ships in v1, because the tab count is user-driven: the compact and micro tiers alone do not bound width.

**On machine tabs, suppress the per-row remote alias chip** and the lone BY_MACHINE top banner, since every row is from the same machine. Keep both on named tabs and at the All-tabs level, where agents can come from several machines.

**Empty states** name one of three causes: no agents on this tab, the query hides them (with `clear filter` and "3 matches on `⌨ local`"), or the feed is unavailable (with a route to Machines). For example:

```text
No agents on sase match  status:running
3 matches on ⌨ local · 1 on blog          ] next tab   o all tabs
```

### 5.4 The `o` / `O` layout ladder

```text
            o →                  o →                    o → (wraps)
Split by tribe ─────────► Merged ─────────► All tabs
            ← O                  ← O
```

| Level | Scope | Panels | Title |
| --- | --- | --- | --- |
| **Split by tribe** (default) | the active tab | one per tribe | `@tribe · N`, as today |
| **Merged** | the active tab | one | the tab's label and count (`⌨ apollo · 14`). Stays `All agents` when the strip is hidden. |
| **All tabs** | every tab | one | `All agents · every tab · 40` |

**The modal.** The single "Panel layout" row becomes a segmented control:

```text
 Panel layout                                    o next · O back
   ◉ Split by tribe    ○ Merged    ○ All tabs
     One panel per tribe, showing sase only.
```

- `o` selects the next level and `O` the previous one, then the modal dismisses. That keeps `oo` as "one step forward" and makes `oO` "one step back".
- Enter or a click on a segment selects that level directly.
- Add an explicit `O` branch to `on_key`, which today lowercases `O` and swallows it.
- With one tab (R6), only `◉ Split by tribe  ○ Merged` is shown.
- **App-level `O` stays unbound on Agents in v1.** `o` is the opener, so an `O` that acted without opening the modal would be an asymmetry. grk's proposal is rejected.

**Level persistence.** The level stays session-scoped, as the merge flag is today (it was never persisted). The enum replaces the boolean: `False` maps to Split and `True` to Merged.

**Transitions preserve the anchor**, reusing the capture/generation/restore pattern from `12ae3014b9`:

- **Zooming out** keeps the selected node.
- **Zooming in from All tabs** with `o` (wrap) or `O` lands on the **selected node's tab**; the anchor decides.
- **Choosing a tab while at All tabs** (click, or `[`/`]` from the remembered active tab) drills into that tab at its last per-tab level.

**The strip at the All-tabs level stays mounted.** No row jumps, so the view is spatially stable.

- Every tab is drawn in its accent with no pill, which reads as "all of these are included".
- The info row adds `panels: all tabs`, and it shows `panels: merged` at the middle level.
- There is **no "ALL" chip.** A chip, even an unselectable one, would bring back the rejected ALL tab.
- Rows that belong to a **named** tab get a tab chip (`sase`, in its accent) before the tribe label. Rows on machine tabs need no chip, because the existing remote alias chip, or its absence for local rows, already says where they are.

**Scope honesty.** Marks stay global. Every bulk or cleanup confirmation names its scope: "on sase", or "across all tabs", or "3 marked agents are on other tabs".

### 5.5 Keys and navigation

| Action | Key | Notes |
| --- | --- | --- |
| Next / previous tab | `]` / `[` | Wraps and walks overflow tabs. A no-op when the strip is hidden. |
| Next / previous card block | `)` / `(` | Moved from `]`/`[`. |
| Jump to a tab | `'` jump hints | Add `TabJumpTarget = ("tab", AgentTabKey)` next to `PanelJumpTarget`. |
| Tab picker | overflow chip click; palette entry "Agents: go to tab…" | An unbound `pick_agents_tab` keymap field is available for users who want a key. |
| Mouse | click a tab | Emits `TabClicked`. |
| Digits | unchanged | They stay agent-relation jumps. There are no numbered tabs. |

**Changes that must land together with the key move:**

- `default_config.yml`
- keymap types and metadata, fallback bindings, and availability
- `_CONTEXTUAL_APP_DUPLICATES`, which becomes Agents tabs vs Artifacts sub-tabs on `[`/`]`, and Agents blocks vs Artifacts Files versions on `(`/`)`
- help, footer, quickstart, and the block-rail hint
- docs, the Agent Data Card Block glossary wording, and the goldens

**Cross-tab jumps are transparent.** These all switch to the target's tab (or stay put at the All-tabs level), reveal folds, and keep the previous location for jump-back:

- `,j` / `,J`
- Node Finder `"`
- relation numbers
- notification "go to agent"
- Admin Center Machines `Enter`, which **selects the machine tab** instead of injecting `machine:<alias>`. A secondary action keeps the old filter behavior.

**Per-tab memory:** the selected node identity, focused tribe panel, fold and scroll anchor, and deck target. Restore by identity, and fall back to the nearest surviving row. Re-read the active tab after every await (tui_perf rule 4).

### 5.6 Interactions

- **Query.** Add a `tab:` field to the Agents live query. It takes named tab names, plus `tab:main`, which matches every default-placed root. Machine scoping stays with `machine:` (`tab:main machine:here` is the local machine tab), so `tab:apollo` is never ambiguous.
  - The field needs an index column for pushdown; tui_perf rule 9 requires every field to declare pushdown or a known fallback.
  - The strip scope ANDs with the query. A contradiction produces the empty state; the query is never rewritten.
- **Grouping modes** work at every level. BY_MACHINE becomes *more* useful on named tabs and at the All-tabs level, because it shows one project across machines, or the whole fleet by machine.
- **Tribes span tabs.** A tribe panel shows that tab's slice. `%wait:@tribe`, tribe summaries, and the TRIBE MEMBERS roster stay global; the roster marks members that live on other tabs with a tab chip.

### 5.7 Launch experience (R1, R2)

**The prompt bar context line** shows the inherited tab while a named tab is active:

```text
tab: blog   (Ctrl+G b change · %tab:main for default)
```

- `gb` / `Ctrl+G b` opens a **Launch Tab picker**, the placement sibling of the `gD` Launch Target picker. It lists existing tabs, the default, and "new tab…". The implementer must confirm that `b` is free in the prompt `g`-prefix table.
- On submit, `%tab:<t>` is inserted unless the prompt already has one.
- On a remote machine tab, the line instead hints `runs on ⌨ local · gD launch on apollo`.

**LaunchApproval** cards show the inherited tab, so the approver sees where the agent will appear.

### 5.8 Moving agents (R12)

- **The `N` modal becomes *Tribe & Tab***, with two fields. Bulk marks work as they do for tribes.
- **`sase agent tab {list,set,unset}`** follows `cli_rules.md`: `list` is the default and every long option gets a short alias.
- **What a move rewrites:** the root's and every member's meta (`agent_tab`, `agent_tab_source: moved`), the clan record's `clan_tab`, and the stored prompt's `%tab`. It reuses the `sase agent persist-directive` path that the tribe `N` edit already uses, but writes **meta only**; there is no store. Future session turns inherit the new tab.
- **Remote rows:** the action is disabled with the reason "tab moves run on the owning machine".

---

## 6. Data, ownership, and compatibility

### 6.1 Rust core boundary

The litmus test is whether another surface needs the same answer. `sase agent tab list`, an editor, Telegram, or a web client would all need to know "which tab is this agent on?". So the following belong in `sase_core`, in a new `agent_tab.rs`, called from Python through `sase_core_rs`:

- **Name handling:** validation, canonicalization, and the reserved names.
- **Resolution:** the `AgentTabKey` type, `effective_tab`, and the catalog builder (existence and order).
- **Directive metadata:** a `tab` entry modeled on `dispatch`, using `COLON_PAREN` with no alias. Add `DirectiveValueRole::Tab` so completion offers known tab names. Update the explicit name lists in `editor/wire.rs`, the ordered-name tests, and the LSP special cases.
- **Typed launch units:**
  - Add `AgentUnitWire.agent_tab`.
  - Parse `%tab` into the typed field, including clan and fan-out agreement checks.
  - Re-emit it in `agent_unit_dispatch_prompt`.
  - Include it in fingerprints.
  - Today `%tab` would pass through as prose (`typed_units.rs:468`). That is survivable, but it cannot be validated.
- **Scan wire:** add `AgentMetaWire.agent_tab` / `agent_tab_source` (not strict), bump the scan schema from 10 to 11, and add an index column.
- **Fleet contract:** see §6.3.

After that lands, move sase's `sase-core-revision.txt` pin past it. The following stay in Python:

- the Textual strip and overflow rendering
- per-tab memory
- the prompt chip
- the `N` modal

The field is named **`agent_tab`**, not `tab`, everywhere. "Tab" already means main TUI tabs, notification tabs, and Artifacts sub-tabs, and an unqualified `tab` field would be ungreppable.

### 6.2 Storage: owner metadata only

- `agent_meta.json["agent_tab"]` is written only for an explicit tab. It is also written to the clan record (`clan_tab`) and copied into each session follow-up's meta.
- **No `~/.sase/agent_tabs.json` store.** The tribe store is a split-brain in practice (§2): CLI edits never reach remote viewers, and the TUI's store-wins overlay can disagree with the owner's meta. One source of truth, the owner's meta served by the owner's fleet feed, is what makes "same tab on every machine" true.

### 6.3 Fleet compatibility: follow the precedent, document lockstep

- **What to add:** add `agent_tab` to `OwnerResolutionFactsWire` and `ResolvedAgentSummaryWire` with `#[serde(default, skip_serializing_if = "Option::is_none")]`, and bump `FLEET_CONTRACT_SCHEMA_VERSION` from 6 to 7. This is exactly how `tribe`/`clan_tribe` arrived.
- **Consequence (true of every contract bump today):**
  - An *older controller* reading a *newer* remote marks that host `invalid`: loud, not silent.
  - A newer controller reads older remotes fine. Their rows simply have no tab, so they fall back to machine tabs.
  - **Upgrade controllers first, or the fleet in lockstep.** State this in the changelog.
- **Why not cdx's negotiated "fleet v2 / v1 without the field":** it would be the first negotiated contract change in a codebase whose protocol negotiation is exact-match and whose rows are version-stamped. It would add a permanent compatibility branch for a three-machine personal fleet. If one-way fleet compatibility becomes a real problem, fix it for *all* fields in the contract layer, not as a special case for tabs.

### 6.4 Dispatch skew

No per-dispatch capability check exists, and an older target leaves `%tab:foo` in the model's prompt. So a `%tab` + `%dispatch` launch should run a **preflight**:

- If the target's last-known `fleet_contract_schema_version` (from `sase machine status` / hello) is older than the tab-aware version, **refuse** with an upgrade hint.
- If the version is unknown, warn and proceed.

An older remote still degrades visibly, never corruptly: its agents appear on its machine tab, and the header notes "apollo: tab data unavailable (upgrade sase)".

### 6.5 Configuration

```yaml
ace:
  agent_tabs:
    machine_tabs: auto        # auto | on | off (R10)
    launch_from_view: true    # R1
    tabs:                     # optional styling; never creates a tab
      sase:
        icon: ""              # named tabs are glyph-less by default
        color: "#AF87FF"      # overrides the project/hash accent
        order: 10
        description: "Everything touching the sase repos, on any machine."
```

These are permanent user choices, so they are **config fields, not flags** (`sase_flags.md`). Update `src/sase/default_config.yml` with the defaults and comments.

---

## 7. Glossary strands

Add these during implementation through `/sase_memory_write`. They are drafts; this report does not edit memory.

> **Agent Tab** *(aka agents sub-tab)*: An agent tab is one sub-tab of the Agents tab: an exclusive, presentation-only placement of top-level sase agents. A launch assigns one with `%tab:<name>`. An agent launched from a named tab, or by an agent on one, inherits that tab. An agent with no tab lands on the default tab: `main`, or its [[glossary:machine-tab]] when remote machines are configured. Membership belongs to the whole agent session, clan, or workflow, so a node never splits across tabs. Tribe panels divide a tab, and `o`/`O` step the panel layout between split tribes, one merged panel, and all tabs merged. The strip appears only while two or more tabs have agents. A tab never changes where an agent runs, its identity, clan, session, or tribe, or what `%wait` can target.

> **Machine Tab** *(aka machine tabs)*: A machine tab is how the Agents tab shows the default agent tab when the current machine has remote machines configured. Agents launched without `%tab` appear on `⌨ local` if this machine owns them, or on `⌨ <alias>`, named by this machine's configured alias for the owner. The placement is derived at view time and never stored. A machine tab is keyed by the machine's installation identity, so renaming an alias only relabels it. It marks stale or failing feeds. Selecting one never changes where a launch runs. An explicit `%tab:<name>` always wins on every machine, so a named tab can gather one project's agents from several hosts. With no remotes configured, the same agents share the `main` tab.

Also update:

- the `xprompts.md` directive table (`%tab`);
- the Agent Data Card Block wording (`(`/`)`);
- the Node Panel strand (tribe panels are per tab);
- `dispatch.md` (`%tab` forwarding and the preflight).

---

## 8. Delivery plan

The implementation epic carries **one `beta` flag, `agent_tabs`, as epic scaffolding**. Create it with `sase flag new` and remove it before the epic lands.

grk argued that hiding the strip makes a flag unnecessary. That does not hold for Bryan's setup: remotes are configured, so machine tabs would expose a half-built strip as soon as phase 3 landed.

| Phase | Repo | Scope |
| --- | --- | --- |
| **P0 Cleanup and keys** | sase | Delete the Focus/Fleet remnants. Move card blocks to `(`/`)` with the legacy-override warning, help, goldens, and glossary wording. `[`/`]` stay unbound on Agents until P3. |
| **P1 Core contract** | sase-core | `agent_tab.rs`; directive metadata and `DirectiveValueRole::Tab`; typed-unit parse, agreement checks, and re-emit; scan wire 11 plus index column; fleet contract 7; bindings. Then move the pin. |
| **P2 Launch path** | sase | Python parse and validation (R4, R5); meta, clan-record, and session writes plus mismatch errors (R3); `SASE_AGENT_TAB` lineage (R2); dispatch preflight; `tab:` query field; `docs/xprompt.md` Tab section. |
| **P3 Strip and navigation** (flagged) | sase | Projection and catalog; `AgentTabStrip` in `#agents-header`; tiers and overflow picker; `[`/`]`; per-tab memory; scoped folds and sticky panels; `'` hints; cross-tab jumps; empty states; latch (R11); arrivals; tooltips. |
| **P4 Layout ladder** (flagged) | sase | Enum; segmented modal with `o`/`O` (R6); titles; All-tabs chips and strip state; anchor-preserving transitions; scoped confirmations. |
| **P5 Machine tabs** (flagged) | sase | Config-derived machine mode (R10); `local` vocabulary (R9); `⌨`, accents, and health; alias-chip and banner suppression; Admin Center `Enter` → tab; glossary strands. |
| **P6 Launch UX and moves, then unflag** | sase | Prompt-bar chip and `gb` picker (R1); landing toast; LaunchApproval display; *Tribe & Tab* modal and `sase agent tab` CLI (R12); docs (`ace.md`, `remote_dispatch.md`, `agent_sessions.md`); perf bench; delete the flag's Off branch. |

P1 must land, and the pin must move, before P2. P3 through P6 are sase-only and can be reviewed visually one at a time.

---

## 9. Validation and performance gates

**Directives and launch:**

- `%tab` absent, valid, invalid, uppercase, duplicated, reserved, or inside fenced regions.
- From xprompts, in fan-out, and in swarms.
- With `%dispatch`, and with `%proc` (rejected).
- Python and Rust directive-contract parity, and typed-unit re-emission.

**Inheritance:**

- View inheritance (R1) and lineage inheritance (R2), including opting out with `%tab:main`.
- Session, monitor, and gate turns; clan-generation agreement; and mismatch errors.
- Retry, fork, revive, and dismissed bundles.

**Wires:**

- Old and new scan records.
- Contract 6 and 7 readers, in both upgrade directions (an old controller shows the host invalid).
- A missing field falls back to the machine tab.
- The dispatch preflight when the target's version is older or unknown.

**Catalog:**

- Zero, one, two, and many tabs; hiding the strip; the R11 latch.
- A query that empties a tab without removing it (R8).
- `STARTING` roots; bounded history gaining a tab (`N+`).
- Alias rename keeps the selection; an unenrolled active machine.
- Provisional-to-authoritative dispatch rows stay on one tab.
- `%tab:apollo` beside `⌨ apollo`.

**TUI:**

- `[`/`]` wrap and overflow; `(`/`)` blocks; Artifacts Files `(`/`)` still works; legacy override warning.
- The `o`/`O` ladder with one and with two or more tabs, plus modal clicks.
- Anchor-preserving zoom, and drilling in from All tabs.
- Cross-tab Node Finder, `,j`/`,J`, notifications, and relations; jump-back.
- Scoped bulk confirmations.
- Every grouping mode at every level, especially BY_MACHINE on named tabs.

**Goldens:**

- The hidden strip matches current screenshots exactly.
- `main` plus named tabs; machine mode; the label collision; attention on inactive tabs.
- Overflow; the All-tabs level; empty and filtered states; a stale host.

**Performance** (tui_perf):

- A tab switch does no filesystem or network I/O and does not mount inactive trees.
- Widgets are reused by tribe key, so only panels whose key set differs are mounted or unmounted.
- `j`/`k` p95 stays under 16 ms on every tab.
- Add a tab-switch key-to-paint metric to `SASE_TUI_PERF`, with a proposed target of p95 under 50 ms at 500 roots.
- A quiet tick reloads no extra surfaces and opens no extra axe files.
- The strip repaints only when the catalog's membership signature changes.

---

## 10. How the reports' disagreements were resolved

| Topic | Positions | Resolution |
| --- | --- | --- |
| Where the tab lives | grk: meta plus a mutable store (like tribe). cdx, cld: meta only. | **Meta only.** The code shows the tribe store is a split-brain (§2). |
| Fleet compatibility | cdx: negotiated fleet v2. cld: additive. grk: an optional field behind the pin. | **Contract bump with `skip_serializing_if`**, matching the `d0ec62c` precedent; lockstep documented (§6.3). |
| Old-target dispatch | cld: capability refusal. The others are silent. | **A preflight on the known contract version** (§6.4). No per-dispatch check exists today. |
| Typed units | cdx: `%tab` would be "silently lost". | **Wrong:** unknown directives pass through as prose. A typed field is still needed for validation. |
| Name grammar | cdx: lowercase-only slugs up to 64. cld: fold to lowercase, up to 32. grk, gem: first-seen casing. mus: backtick names with spaces. | **Fold to lowercase, slug, up to 32** (R4). |
| `%tab:main` | cdx: a literal named tab. cld: the explicit default. grk: reserved as an error. | **The explicit default and inheritance opt-out** (R5). |
| Reserving aliases | grk: reserve enrolled aliases. cdx: never. | **Never; warn instead.** Aliases are local to each viewer. |
| Occupancy basis | cdx, cld: before the query. grk, mus: after the query. | **Before the query, after hide rules, including `STARTING`** (R8). |
| Empty machine tabs | prior research: always shown. mus: listed but not forcing visibility. grk, cld: occupancy only. | **Occupancy only**, plus the R11 latch for the active tab. |
| Inheritance | cdx: sessions and clans only. grk: adds `%repeat`. gem: adds a `--tab` CLI flag. cld: adds view and lineage inheritance. | **Root inheritance plus R1 and R2.** A `--tab` flag is deferred; the environment variable and prompt text cover scripted launches. |
| Session follow-up on another tab | grk: allowed as an escape. cdx, cld: an error. | **Error** (R3). |
| Retab after launch | cdx: not in V1. cld, grk: yes. | **Yes, in the last phase**, meta-only (R12). |
| Machine icon | cdx: `⇄`. cld: `⌨`. grk: `⌂` / `▣`. gem: `⌂` / `☁` / `⌗`. mus: a host glyph, not `⌂`. | **`⌨` for every machine tab.** The others collide with existing meanings or have width hazards (§5.3). |
| Named-tab glyph | cld: `◇`. grk: none. | **None; the accent-colored label carries identity.** `◇` is the bead "ready" glyph. |
| Strip placement | cdx: a new row. cld, grk: reuse `#agents-header`. gem: above the content. | **Reuse `#agents-header`**, which preserves the goldens. |
| Strip at All tabs | cdx: hidden. cld: a legend with a `⊞ all tabs` chip. grk: all tabs lit. gem: an `[ALL TABS]` chip. | **Mounted, all tabs lit, no chip.** Hiding it jumps the layout; a chip brings back the ALL tab. |
| Ladder with one tab | cld: two states. The others: always three. | **Two states** (R6). |
| App-level `O` | grk: cycle backwards directly. The others: modal only. | **Modal only in v1.** |
| Layout persistence | grk: persist. mus: "already persisted". cdx, cld: session-scoped. | **Session-scoped.** Nothing is persisted today. The active tab key *is* persisted. |
| Feature flag | grk: none. cld: beta scaffolding. | **Beta scaffolding**, because Bryan has remotes configured (§8). |
| `here` vs `local` | grk: `local` on the strip only. cld: `local` everywhere. | **`local` for display everywhere; `machine:here` kept as an alias** (R9). |
| Agent Cluster | prior research: an umbrella term. All five reports: drop it. | **Dropped.** |

---

## 11. Open questions for Bryan

1. **R1 default.** Should launch-from-view inheritance be on by default? I recommend yes, with the visible chip. The alternative is opt-in via `ace.agent_tabs.launch_from_view`.
2. **R9 scope.** Is renaming `here` to `local` in the BY_MACHINE banner and the Launch Target picker acceptable, or should the change stay confined to the strip?
3. **R12 timing.** Should Move-to-tab ship in this epic's last phase (my recommendation) or as a follow-up?
4. **Project-default tab (follow-up).** Should an opt-in rule (`ace.agent_tabs.default: main | project`) put `+blog` agents on the `blog` tab without a directive? It is powerful, but it is a second placement rule and would surface the strip for anyone with two active projects. Ship it later, opt-in.
5. **Named-tab order.** Alphabetical with an optional configured `order` (recommended), or most-recently-active first? Recency is handy but moves tabs under your fingers.

---

## 12. Recommended solution

Implement **dynamic agent tabs as an authored, root-level, presentation-only placement**.

- **The directive:** `%tab:<name>`, lowercase slugs up to 32 characters, with `%tab:main` as the explicit default.
- **Storage:** only in the owning machine's agent meta and the fleet feed (contract 7), with no mutable side store.
- **Resolution:** view time, through one `sase_core` resolver. An explicit tab wins on every machine. Otherwise the agent is on `main`, or, when remotes are configured, on its machine tab (`⌨ local` / `⌨ <alias>`), keyed by installation ID.
- **Coherence:** tabs stay coherent through visible launch-from-view inheritance and lineage inheritance, both written into the prompt. A meta-only *Move to tab* action fixes mistakes.
- **The strip:** reuses the `#agents-header` row and appears only while two or more tabs have agents.
  - Accent-colored labels, the `⌨` machine glyph, and an active pill.
  - Stopped, failed, and unread badges, and an overflow picker.
  - `[`/`]` to switch tabs, with card blocks moved to `(`/`)`.
  - Every global jump switches tabs for you.
- **`o`:** a three-level zoom ladder, **Split by tribe → Merged → All tabs**, shown as a segmented control. `O` reverses it, it collapses to today's toggle with one tab, and transitions preserve the anchor.
- **Tab switches:** pure in-memory projections.

This meets every stated requirement. The adjustments R1–R13 are what make it feel native rather than bolted on:

- The inheritance rules keep tabs from leaking.
- Root anchoring keeps containers whole.
- The pre-query catalog and the latch keep the layout still.
- Typed keys and the machine glyph make identical names unambiguous.

---

### Source reports

Each report is preserved beside this synthesis, and each was read through `sase artifact read`:

| File | Artifact ref |
| --- | --- |
| `agents_dynamic_tabs__cdx.md` | `file:explicit:067a815cc50917fdab5364b6` |
| `agents_dynamic_tabs__cld.md` | `file:explicit:8322f11f4bf601ff66079e47` |
| `agents_dynamic_tabs__grk.md` | `file:explicit:93ca93d25d8e0da07a12cca2` |
| `agents_dynamic_tabs__mus.md` | `file:explicit:0f1deba351f207e1a3470347` |
| `agents_dynamic_tabs__gem.md` | `file:explicit:7658a0da4aa563288f8f8322` |

Prior research:
`research:202609/agent_machine_tabs_and_cluster_semantics/agent_machine_tabs_and_cluster_semantics.md`.
