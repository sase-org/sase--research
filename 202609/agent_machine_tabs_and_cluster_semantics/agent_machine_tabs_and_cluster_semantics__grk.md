# Agent clusters, machine sub-tabs, and the Agents-tab grouping model

- **Researcher:** grk (`research.2p.grk`)
- **Date:** 2026-09-26
- **Question:** How should the Agents tab grow a sub-tab grouping surface so one TUI can manage a multi-machine fleet, what should happen to `[` / `]` card-block keys, and how should clans, tribes, and those new tabs become one movable “agent cluster” idea?
- **Inspected:** sase workspace `sase_41` (Agents tab, fleet projection, grouping, clans/tribes, keymaps, `PanelTabStrip`), glossary strands via `sase memory read`, `tui_perf.md`, `docs/agent_sessions.md`, `docs/ace.md`, `docs/remote_dispatch.md`, `docs/xprompt.md`, and prior fleet research `research:202609/agents_across_machines/` plus `research:202609/remote_machine_management_enablement.md`. Independent of the other three swarm reports.

## Recommended solution

Ship this as **two sequenced products** that share a glossary and a keymap, and keep a third thing (agent sessions) out of the unification.

1. **Agents machine scopes as sub-tabs** — a one-row `PanelTabStrip` on the Agents tab: `all · here · apollo · …`. `[` / `]` cycle those tabs, matching Projects, Artifacts, Config, and Statistics. Each tab is an exclusive view of the existing unified Agents list. Membership is derived from `fleet_origin_alias` (local rows are `here`). Switching a tab writes or clears the existing `machine:` live-query term. Inactive machines are not rendered. Attention badges on inactive tabs stay live from the durable inbox, independent of which tab is open.
2. **Card-block keys move to `(` / `)`** — so square brackets are free on Agents for the strip. That is the right call. The nested-bracket mnemonic is `[` scope `]` / `{` panel geometry `}` / `(` card block `)`. Artifacts Files already binds `(` / `)` to file versions; keep that tab-disambiguated, the same way `[` / `]` already mean sub-tabs on Artifacts and blocks on Agents today.
3. **Agent cluster as the glossary umbrella for assigned grouping** — clans and tribes become two *policies* of one membership object you can move. Machine tabs stay a *derived view scope*. Sessions stay a sequential execution identity. The unique clan rules that make membership unmovable (hood-qualified names, create-only `%clan`, reserved container name, `%id` keyword mutual exclusion, no post-launch clan CLI, `%dispatch` rejected with `%clan`) are the ones to remove. Clan wait-all, generations, summaries, cascade cleanup, and the synthetic container row stay.

Default after enrollment: land on `all` (today’s unified list). `here` and each enrolled alias become named working sets. With no remotes enrolled, hide the strip so the Agents tab looks as it does today.

Do this in two epics. Epic A is the scaling UX (sub-tabs + keymap) and can land without a core identity rewrite. Epic B is the cluster membership model in Python + sase-core.

---

## Verdict on the request

The scaling motivation is right. One TUI already merges local and remote rows; BY_MACHINE banners and `machine:` filters exist; they still leave every origin in play at once, or they hide the scope in a query the chrome does not treat as a destination. Named, cycleable, exclusive scopes are how Artifacts and Projects already scale, and they are how this tab should scale too.

The unification instinct is also right, and it is aimed at the wrong object if machine tabs are treated as the same thing as clans and tribes.

Clans and tribes are **assigned** groups. A machine tab is a **derived** slice of where a node runs. You can re-tribe an agent with `N` or `sase agent tribe set`. You cannot put an athena runner onto the apollo tab without dispatching it there. A single “move this cluster onto a tab / into a clan / into a tribe” verb that covers apollo-the-machine will feel broken the first time someone tries it.

**Requirement adjustments** (these change the request; they are the load-bearing ones):

| ID | Adjustment |
| --- | --- |
| A1 | Treat Agents sub-tabs as **view scopes**. Default dimension is machine origin. Membership is derived. The strip is a chrome for the existing `machine:` query facet. |
| A2 | Add **agent cluster** to the glossary as the umbrella for *assigned* grouping (today’s clan + tribe). A cluster can be *presented* as a tree container, a stacked panel, or a sub-tab. Machine scopes are outside that object. |
| A3 | Keep **agent sessions** out of the cluster model. Sequential `--` turns are execution identity, the same way a sase turn is. |
| A4 | Keep clan **policies** that are real: newest-generation wait-all, cascade cleanup, launch-time summaries, generation records, synthetic container + CLAN summary card. Remove the **membership traps** listed in §5. |
| A5 | Always include an **`all`** tab, and keep cross-tab **attention** visible on inactive tabs. Exclusive scopes that hide unanswered gates recreate the Focus/Fleet failure. |
| A6 | Do not give Agents sub-tabs digit shortcuts. `0`–`9` / `00`–`99` are already agent-relation jump targets. Cycle with `[` / `]`, click the strip, and include tab titles in `'` jump. |
| A7 | Split delivery: **Epic A** (sub-tabs + keymap) then **Epic B** (cluster membership). Combining them into one identity rewrite will stall the scaling UX on core work the TUI does not need. |
| A8 | Hide the strip when fewer than two origins exist (local only, no enrolled remotes). Reserve `[` / `]` for sub-tabs anyway so the keymap is stable; with the strip hidden they no-op. Card blocks use `(` / `)` even in that state. |

A different approach I would *not* take: resurrect Focus/Fleet (`focus` vs `fleet` modes). That chrome is already retired in code (`AgentsSubTab` still exists as a leftover `Literal["focus", "fleet"]` that is forced back to `"focus"`). Per-machine named tabs with `all` are a different idea, and they compose with the unified list that replaced Focus/Fleet.

---

## 1. What the Agents tab already is

The tab is already a stack of grouping systems. Adding sub-tabs without collapsing some of that stack is how the surface gets worse while trying to scale.

| Layer | What it groups | Membership | Presentation today | Movable? |
| --- | --- | --- | --- | --- |
| Sase turn / session | Sequential execution | `%i(..., session=)` / `--` names | Tree under a session node | No (identity) |
| Agent hood | Dotted-name neighborhood | Derived from the name | Name-root / prefix banners; NEIGHBORS jump roster | No (derived) |
| Agent clan | Parallel bag + wait/cleanup unit | `%clan` / `clan=`; hood-qualified names | Synthetic clan node; CLAN summary card | Launch-time only |
| Agent tribe | User label across clans/sessions | `tribe=` / `#tribe` / `N` / `sase agent tribe` | Vertically stacked side panels `@review`, `@job`, `@default` | Yes |
| GroupingMode | Project / date / status / machine | Derived | In-panel banners (`o` picker) | View-only |
| Live query | Arbitrary facets including `machine:` / `tribe:` | Query text | Auto-hiding `AgentsFilterBar`; resting readout on the info row | Yes (query) |
| Saved dismissed group | Revival batch | `s` on marks | Revival modal | After dismiss |
| Marks | Ephemeral selection | `m` | Highlight | Session-local |
| Leftover `AgentsSubTab` | Historical Focus/Fleet | Forced `"focus"` | `#agents-header` is now a fleet *diagnostic* strip, hidden when quiet | Dead |

Evidence, current HEAD:

- Tribe panels are the outer assigned grouping. Every descendant inherits the presentation root’s tribe, so a clan or session is never split across panels (`src/sase/ace/tui/models/agent_panels.py`).
- `GroupingMode.BY_MACHINE` already puts the fleet alias at L0 (`here` first, remotes alphabetical), then status, then name-root (`src/sase/ace/tui/models/agent_groups/_buckets.py`, `_keys.py`). It still renders **every** machine in one tree.
- The live query already understands `machine:here`, `machine:apollo`, and bare `machine:` (any remote) (`src/sase/ace/agent_query/evaluator.py`). Admin Center Machines `Enter` already returns to Agents with that filter (`docs/remote_dispatch.md`, `docs/configuration.md`).
- Focus/Fleet as two modes is gone. `_set_agents_subtab` ignores its argument and sets `"focus"`; `cycle_agents_subtab` is absent from the command catalog (`src/sase/ace/tui/actions/agents/_fleet_projection.py`, `tests/test_command_availability_agents_fleet.py`). The unified list is the product. Remote rows carry an alias chip; local rows do not carry `here`.
- `%dispatch` v1 **strips** wait/queue/clan rather than combining with them (`docs/remote_dispatch.md`). Clans are also machine-owned: joining a clan whose name belongs to another machine is an error (`src/sase/agent/clan_membership.py`).
- Full list rebuilds are the expensive UI operation; STANDARD / BY_STATUS / BY_MACHINE stay on the incremental `patch_row` path when membership is stable (`tui_perf.md` rule 6). Exclusive scopes that *drop* other machines from the rendered set make that path cheaper.

Prior fleet research (`research:202609/agents_across_machines/agents_across_machines.md`) argued for one list, machine as a field/filter/grouping, attention independent of the visible slice, and machine administration in Admin Center. That recommendation is about Focus/Fleet (asymmetric local-vs-remote *modes*). Per-machine exclusive scopes with an `all` tab are a filter with chrome. Copilot / JetBrains / Claude landing on one work list still leaves room for a host filter; they did not ship a second product surface per machine.

The gap that remains is specifically: **a named, cycleable, exclusive working set** whose chrome matches every other tab that already has sub-tabs, and whose inactive siblings can still show “needs you.”

---

## 2. Critique of the plan as stated

### 2.1 Sub-tabs for scale — take this, aimed at machines

BY_MACHINE banners keep apollo and athena in the same scroll. Isolation (`=`) and tribe-panel collapse hide *tribes*, and they still mount panels once shown (`docs/ace.md` tribe side panels: a panel stays mounted for the session after it has shown rows). Query `machine:apollo` already exclusive-filters, and it is invisible as a destination: the filter bar is editing-only and takes zero resting rows (`src/sase/ace/tui/widgets/agents_filter_bar.py`).

A sub-tab strip is the missing resting chrome for that facet. It also matches user-taught muscle memory: Projects (`Projects · Repos · Workspaces`), Artifacts (Patch / Stitch / Bead / …), Config, Statistics all cycle with `[` / `]`.

What would make this *not* a good idea: a second independent mode bit (the Focus/Fleet mistake), or sub-tabs that unmount attention. The strip must edit the live query (or an equivalent AND-composed scope the query displays), and inactive tabs must keep a needs-you pip from the durable inbox.

### 2.2 Migrating `[` / `]` off card blocks — take this

Today:

```yaml
# src/sase/default_config.yml
next_card_block: "right_square_bracket"
prev_card_block: "left_square_bracket"
# shares [ / ] with cycle_artifacts_subtab; disambiguated by tab availability
cycle_artifacts_subtab: "right_square_bracket"
files_next_version: "right_parenthesis"
files_prev_version: "left_parenthesis"
```

Card-block availability is already Agents-only and gated on `card_blocks_navigable` (`src/sase/ace/tui/_app_action_availability.py`). The conflict with sub-tabs is **on the same tab**, so tab-availability disambiguation cannot save `[` / `]`.

I considered scoping `[` / `]` by focus (list = tabs, deck = blocks). That keeps unshifted block keys, and it is the wrong product: every other sub-tabbed surface teaches “square brackets move the strip,” and `Ctrl+F` already owns deck focus. Agents should not be the exception.

`(` / `)` cost a Shift. Block stepping on a long Reply is real (card-blocks corpus: p90 Reply ~738 raw lines). Mitigations that keep the keymap beautiful:

- The block rail (epic `sase-19x.8`) remains the spatial map; `(` / `)` step it.
- Numeric relation jumps already land on session turns.
- Footer only shows `(`/`)` blocks when `card_blocks_navigable`, same as today.

Artifacts Files versions keep `(` / `)` because they are Artifacts-only. Same pattern as the current square-bracket share, just swapped which pair is Agents-inner vs Artifacts-inner.

`{` / `}` already grow/shrink the focused deck panel on Agents. The three bracket pairs then nest by scale, which is the beautiful part of this keymap, not a side effect:

| Keys | Layer | Already true? |
| --- | --- | --- |
| `[` / `]` | Outer scope (sub-tabs) | True on every other sub-tabbed surface; new on Agents |
| `{` / `}` | Deck panel geometry | True on Agents (`grow_deck_panel` / `shrink_deck_panel`) |
| `(` / `)` | Inner card block | New on Agents; already File versions on Artifacts |

Prompt insert-mode parenthesis pairing is unaffected (insert owns those keys).

### 2.3 Unifying clans, tribes, and tabs as one movable cluster — take the membership half, refuse the ontology half

The codebase does **not** treat clans and tribes as “just grouping,” and some of that difference is load-bearing.

**Tribe** is already the movable grouping model: a label, a panel, `N` to retarget, `sase agent tribe set/unset/list`, wait/fork as *next completed entity*, `@default` display-only, `@job`/`chop` compatibility, configurable icons/colors/initial fold (`docs/agent_sessions.md`).

**Clan** is a container with extra physics:

- Rootless: the clan name is reserved and is never an agent.
- Members must be named `<clan>.<suffix>` (hood-coupled). Launch planning rejects out-of-hood names.
- `%clan` is create-only and errors if that clan exists; joiners use `clan=` and cannot declare a summary.
- `clan=`, `session=`, and `tribe=` on `%id` are mutually exclusive; joining a clan also joins its tribe.
- `%wait:<clan>` waits for **every member of the newest generation**.
- Killing the synthetic row cascades; `%wait:@tribe` waits for the **next** successful entity.
- Durable `~/.sase/agent_clans/<clan>.json` records, keyed by generation, with summary scripts and tribe tombstones (`src/sase/core/agent_clan_record.py`).
- Clans are machine-owned; `%dispatch` does not combine with `%clan`.
- There is no `sase agent clan` analogue of `sase agent tribe`. You cannot move a running agent into a clan without a rename/relaunch that satisfies the hood rule.

The user’s “clans are just grouping, like tabs” is true of the *display intent* and false of the *wait, cleanup, generation, and naming* contracts. Unifying the **membership API** (assign, move, list, present) is the win. Flattening wait-all into wait-next, or deleting the container node, would break epic clans and `%wait:release`.

Machine tabs are a third kind of thing. A clan is already forbidden from spanning machines. That invariant is *convenient* for machine scopes: a container cluster always sits entirely inside one machine tab. A tribe *may* span machines; on `apollo` the `@review` panel shows apollo members, on `all` it shows the whole tribe.

“Move a cluster to the apollo tab” should mean one of:

- set that cluster’s **presentation** to sub-tab (an assigned cluster you chose to show as a tab), or
- **dispatch** work onto apollo (derived scope).

Those must be different verbs in the UI. One toast is enough: “This agent runs on athena. Open the athena tab, or launch with `%dispatch:apollo`.”

### 2.4 Would I take a different approach?

Yes: **do not design machine tabs as clusters.** Design them as the Agents-tab instance of a pattern the TUI already has (sub-tab strip + query facet + `[` / `]`). Then, separately, lift clan membership toward the tribe assignment model and call the pair *agent cluster*.

I would also keep tribe **panels** inside a machine tab rather than converting tribes into sub-tabs in v1. Two dimensions of sub-tabs (machine × tribe) is a 2-D tab control, which this TUI does not have and should not grow. Nested structure that already works: machine scope → tribe panel → clan container → session → turns.

---

## 3. Target information architecture

Three kinds of “many nodes together.” Only the middle one is the new glossary term.

```text
execution identity          assigned grouping              derived view
─────────────────          ─────────────────              ────────────
sase turn                  agent cluster                  view scope
sase agent session           policy: wait-all (clan)        machine: here|apollo|…
sase agent                   policy: wait-next (tribe)      (later: maybe status)
agent hood (name)            presentation:
                               tree container
                               stacked panel
                               sub-tab (opt-in)
```

**View scope (Epic A).** Exclusive filter. Default dimension: machine. Built-in tabs: `all`, then `here`, then enrolled aliases in the same order BY_MACHINE already uses (local first, remotes case-insensitive alphabetical). Hidden with a single origin. Composes with project/status/tribe queries: `apollo` + `status:running` is the running work on apollo. A query that names two machines, or a machine the strip does not know, lights a `custom` chip rather than lying about which tab you are on.

**Agent cluster (Epic B).** Assigned bag of sase nodes. One cluster has:

- a name
- a member set (agents, and sessions as units; turns stay inside their session)
- a wait policy: `all_generation` (today’s clan) or `next_entity` (today’s tribe)
- a cleanup policy: cascade container vs member-only
- a presentation: `container` | `panel` | `tab`
- optional summary / summary_script (container policy)
- optional generation key (wait-all policy)

Changing presentation is how a cluster “becomes a tab” or “becomes a clan row.” Changing membership is how nodes move between clusters. Changing wait policy is a cluster setting, with a confirm when it would alter in-flight `%wait` / `#fork` meaning.

**Session and hood stay outside.** Hoods remain derived neighbors. Sessions remain sequential agents.

Saved dismissed groups and marks stay what they are (revival batches and ephemeral selection). They are not clusters.

---

## 4. Epic A — machine sub-tabs (the scaling UX)

### 4.1 Chrome

Reuse `PanelTabStrip` / `PanelTab` (`src/sase/ace/tui/widgets/panel_tab_strip.py`). Artifacts already centers a numbered, accented, compact/micro-reflowing strip in `ArtifactsHeader`. Agents already has a one-row `#agents-header` that is hidden unless the fleet has a problem (`src/sase/ace/tui/_app_layout.py`, `styles.tcss`). Put the strip there.

Layout of that row when two or more origins exist:

```text
 all │ here │ apollo │ mac          apollo: feed stale · cached 5m ago
 ───   ────   ──────
                  ▲ active (bold + per-machine accent)
```

- Active tab: bold + accent (same language as Artifacts).
- Each tab: label, sase-agent count, compact status chip in the tribe-panel grammar `[S1 R2 W1 F1]` when counts are non-zero, and a needs-you pip when the durable inbox has a pending gate/question on that origin.
- `here` id stays `here`; if the controller has a configured machine name, that name is the compact/full label and `here` remains the query token (`machine:here` already matches local rows).
- Fleet diagnostics stay right-aligned in the same row (`#agents-fleet-status` already `content-align: right`).
- Overflow: `PanelTabStrip` already has full / compact / micro tiers and click ranges in cells. Past ~6 aliases, drop counts then status chips; remaining aliases collapse behind `…` that `'` jump can still name.
- Empty tab: “No agents on apollo” plus the existing Launch Target hint (`gD` / `%dispatch:apollo`). Do not invent a second enrollment flow; Admin Center Machines remains the administration door.

Vertical density: one row, the row that already exists. The filter bar stays editing-only. Do not add a second header.

### 4.2 Behavior

- Selecting a machine tab commits `machine:<alias>` into the agents-live query (or clears it for `all`), then takes the existing fast path: `_refilter_agents()` immediately, `_schedule_agents_async_refresh()` in the background (`tui_perf.md` rule 5).
- Render only in-scope rows. Remote catalog refresh for *attention and counts* continues for every enrolled origin (global attention, prior fleet research). Row bodies for inactive origins stay unloaded.
- Preserve the selected logical identity across a tab switch when it exists in the destination; otherwise select the first row of the new scope and record a `Ctrl+O` jump-back.
- `o` grouping still applies *inside* a tab. On a single-machine tab, BY_MACHINE’s L0 is redundant; keep the mode but collapse a lone L0 banner (the same singleton-suppression name-root already uses, inverted: one machine header is noise). Status subgroups can remain.
- Tribe panels remain, scoped to the tab. `@job` still starts collapsed. Isolation (`=`) isolates a tribe *within* the current machine scope.
- Clans and sessions that the owner reports stay intact; a clan cannot appear on two machine tabs under today’s machine-owned clan names. Good.
- Digit keys continue to mean relation jumps. Sub-tabs are `[` / `]`, click, and `'` titles.
- Persist the last scope per TUI session (and, if cheap, across restarts next to `grouping_mode.txt`). Restoring a machine that has been unenrolled falls back to `all`.

Replace the leftover `AgentsSubTab = Literal["focus", "fleet"]` with a real scope id (`all` | `here` | alias | `custom`). Delete `_AGENTS_SUBTABS = ("focus", "fleet")` and the force-back-to-focus watcher. Revive `cycle_agents_subtab` / `cycle_agents_subtab_reverse` as bound actions, square brackets, Agents-tab availability only, and only when the strip is visible (two or more origins, or `custom`).

### 4.3 Keymap migration (part of Epic A)

| Action | From | To |
| --- | --- | --- |
| `next_card_block` / `prev_card_block` | `]` / `[` | `)` / `(` |
| `cycle_agents_subtab` / `_reverse` | unbound / deleted | `]` / `[` |
| Artifacts sub-tabs | `]` / `[` | unchanged |
| Artifacts Files versions | `)` / `(` | unchanged |
| Deck grow/shrink | `}` / `{` | unchanged |

Docs, footer hints, quickstart, `docs/ace.md` card-block paragraph, glossary **Agent Data Card Block** (`[` / `]` stepping), and ACE goldens all move together. The glossary strand is the user-facing contract; update it in the same change as the keymap.

### 4.4 Beauty notes that are actually constraints

- Same strip widget as Artifacts/Projects, so the TUI has one tab language.
- Per-machine accent via the existing palette hasher (Artifacts provider accents already prove contrast on dark and light shells). Optional later: `ace.machines.<alias>` color/icon, mirroring `ace.tribes`.
- Needs-you pip color is the existing stopped/question accent, not a new hue.
- Inactive tabs dim to `#888888` (already the strip’s inactive style).
- Do not put `here` chips on local rows inside the `here` tab; the tab *is* the chip. On `all`, keep today’s “chip remotes only” rule, or label every row including `here` once mixed (prior fleet research preferred explicit origin in a mixed list). Recommendation: on `all`, chip remotes and leave local unlabeled; on a named remote tab, drop the repeated alias chip on every row (the tab is unambiguous). Detail headers always name the owner.

---

## 5. Epic B — agent clusters (the membership model)

### 5.1 Glossary strand (proposed)

```markdown
# Agent Cluster

aka cluster, agent clusters

An agent cluster is a named, user-assigned grouping of sase nodes. Membership
can be changed after launch. A cluster chooses a wait policy (every member of
the newest generation, or the next completed entity), a cleanup policy
(cascade from the container, or member-only), and a presentation (tree
container, stacked Agents-tab panel, or Agents-tab sub-tab).

Machine view scopes (`here`, `apollo`, …) are derived from where a node runs
and are not clusters: they filter the same nodes without being a user-assignable
group. A sase agent session is also not a cluster; its members are a sequential
chain of sase turns.

Agent clan and agent tribe are the two historical cluster policies: clan is
wait-all plus a synthetic container, tribe is wait-next plus a stacked panel.
Both remain valid names for those policies.
```

Add `[[glossary:agent-cluster]]` from the clan, tribe, and sase-node strands. Keep the clan and tribe strands; they become policy aliases, not deleted words. `%clan`, `#tribe`, `@review`, and `N` stay in the user’s fingers.

### 5.2 Unique clan requirements — remove vs keep

**Remove** (these are what make clans unmovable and unlike tribes):

1. **Hood-qualified member names.** Hoods already exist as derived neighbors. Coupling clan membership to `<clan>.<suffix>` is why you cannot place an existing `auth-fix` into clan `release` without renaming it. Membership becomes a field, like `tribe`.
2. **Create-only `%clan` that errors if the clan exists.** Joining and declaring share one path; a second `%clan:release` in a later launch adds members to the newest generation (or opens a new generation by explicit `generation=` / a dedicated verb). The current join form `clan=` remains as sugar.
3. **Permanent reservation of the clan name as “never an agent.”** Once membership is a field, the container row can be synthetic without stealing the bare name from the namespace. If a real agent named `release` exists, the container is still `release` the cluster, disambiguated the way session containers already are (bare name is the container, turns carry `--`). Colliding a cluster name with a live agent name is a directed error with a rename/offer, not a forever-reserved token.
4. **`clan=` / `session=` / `tribe=` mutual exclusion on `%id`.** A session can belong to a cluster. A cluster member can carry a tribe/panel cluster as well (container cluster *inside* a panel cluster), which the tree already allows via hood names. Make the keywords orthogonal: `session=` is execution, `clan=`/`cluster=` is assigned container, `tribe=` is assigned panel.
5. **Silent “join clan ⇒ join clan tribe” as a hard law.** Inherit the container’s panel cluster by default; allow an override so a generation can span panels when the user asks.
6. **No post-launch membership CLI / TUI.** Add `sase agent cluster` (set/unset/list/move/presentation/policy) and make `N` the cluster assigner. `sase agent tribe` remains a compatibility alias for panel-policy clusters.
7. **Joiners cannot set a summary.** Anyone in the generation can propose; the durable record’s precedence table already exists (`declared` / `edited` beat `propagated`).
8. **`%dispatch` rejected with `%clan`.** This blocks the motivating remote workflow. Remote launch should carry cluster membership to the target the way it already carries other directives the controller does not strip. Machine-owned *names* can remain; machine-owned *membership* should be explicit.
9. **One `%clan` declaration per launch for a resolved clan.** A swarm should be allowed to name the cluster on every segment; identical names collapse to one generation, which templates already do.

**Keep:**

- Wait-all on the newest generation (`%wait:<cluster>`).
- Wait-next on panel-policy clusters (`%wait:@review`).
- Cascade cleanup from a container presentation.
- Launch-time summaries, summary scripts, `::` text blocks, `~/.sase/agent_clans/` records (generalize the store, keep the generation keying).
- Synthetic container row, CLAN/cluster summary card, `l` to reveal members, `F`/`W` from the container.
- Execution-neutral membership (joining still does not insert waits).
- Machine locality of *container* clusters (a wait-all generation lives on one owner). Panel clusters may span machines.

### 5.3 Moving between presentations

This is the “seamless clans/tribes/tabs” request, with A2 applied.

| User gesture | Meaning |
| --- | --- |
| `N` on nodes / marks | Assign or clear cluster membership (picker lists clusters; `+` creates). On a container row, retarget the whole generation, as `N` on a clan does today. |
| Presentation picker (from the same modal, or `,n`) | `container` / `panel` / `tab`. Container requires wait-all or an explicit confirm to attach wait-all. Panel is today’s tribe panel. Tab adds the cluster to the Agents strip *after* the machine scopes, user-owned, assignable. |
| Drag in the list (if ever) | Reorder inside a container; membership changes go through `N`. |
| “Move onto apollo” | Refused for membership. Offer: switch view scope, or `%dispatch:apollo` a new launch. |

User-owned cluster tabs are **Epic B optional presentation**, not Epic A. Epic A’s strip is machine scopes only. Mixing assigned cluster tabs into the same strip before membership is movable will look like the ontology the adjustment forbids. When Epic B adds them, they sit to the right of machine scopes, visually quieter (no machine accent hasher; use the cluster’s configured identity color, which tribes already have).

### 5.4 Core / CLI sketch

- sase-core already owns tribe identity resolution and clan records (`docs/rust_backend.md`, `agent_clan_record.py`). Cluster membership and presentation belong there too (`decisions:rust-core-required` for identity). Python keeps TUI projection, the strip, and launch-directive sugar.
- Wire format: one assignment store (today `agent_tribes.json`) generalized, plus the per-container generation store (today `agent_clans/<name>.json`). Do not merge those files in v1; give them a shared reader.
- `%cluster(...)` can alias `%clan` for container policy and `#tribe` / `tribe=` for panel policy. Do not force a rename of `%clan` in the same epic as the membership change. Compatibility aliases are cheap; teaching a third directive while removing unique clan rules is not.

---

## 6. Why this scales, and where it can still fail

**Scale win.** Exclusive scopes cut rendered rows, which is the TUI’s most expensive operation. Five machines × 40 agents is 200 rows in `all` and 40 on `apollo`. Tribe panels on apollo are the tribes that actually have apollo members. BY_MACHINE-as-banners cannot do that.

**Attention.** The pip on `apollo` while you sit on `here` is the feature that makes exclusive scopes safe. Implement it from the durable remote-attention inbox, not from “rows we currently have hydrated.” Prior fleet research’s S4 finding still applies: the gateway must be able to inventory pending attention without the viewer already following those keys.

**Failure modes to design against:**

- **2-D chrome.** Machine tabs *and* converting every tribe into a tab. Keep tribes as panels in v1.
- **Strip always visible.** One local machine and no remotes: hide it. A lone `here` tab is noise.
- **Digit collision.** Numbered sub-tabs on Agents would steal jump targets.
- **Query vs strip drift.** The strip is the query’s machine facet. A `custom` chip is mandatory when they disagree.
- **Clan split across tabs.** Keep container clusters machine-local. If Epic B ever allows cross-machine wait-all, those generations live on `all` only and the container is hidden on a single-machine tab (with a “also on apollo” hint).
- **Keymap muscle memory.** `[` / `]` as blocks is recent (card-blocks epic). Move it in the same release as the strip so users learn one new pair, not two staggered ones. Update the glossary in the same stitch.
- **Header overcrowding.** Counts, chips, pips, diagnostics, launch-context bar on the info row above. The info row already exists; keep diagnostics on the strip row and identity on `AgentInfoRow`. If the strip overflows, drop chips before names.

---

## 7. Alternatives considered

| Alternative | Why it loses |
| --- | --- |
| Teach `machine:apollo` and stop | The filter bar is invisible at rest. Admin Center `Enter` is a detour. No `[` / `]` destination. |
| BY_MACHINE banners as the only machine grouping | All origins remain in one scroll. Does not scale the render set. |
| Replace tribe panels with machine panels | Tribes and machines are orthogonal; `@review` on two hosts is a real shape. |
| Focus-scoped `[` / `]` (list vs deck) | Breaks the TUI-wide “square brackets cycle sub-tabs” rule the request is trying to join. |
| Nested sub-tabs (machine then tribe) | No widget, no keymap, two exclusive dimensions. Panels inside a scope already nest. |
| One cluster type including sessions and machines | Sessions are sequential identity. Machines are derived origin. Forcing one verb for “move” lies. |
| Big-bang identity rewrite before the strip | The scaling UX does not need sase-core membership changes. It needs the leftover Focus/Fleet type deleted and `machine:` given chrome. |

---

## 8. Suggested delivery

**Epic A — Agents view scopes** (TUI-heavy, one sase-core touch only if attention inventory is still incomplete):

1. Keymap: card blocks → `(`/`)`; glossary card-block strand; footer; goldens.
2. Replace `AgentsSubTab` leftover with scope ids; bind `cycle_agents_subtab` to `[`/`]`.
3. `PanelTabStrip` on `#agents-header`; show at ≥2 origins; `all` / `here` / aliases.
4. Tab selection writes `machine:` on the agents-live query; `all` clears it; `custom` when the query disagrees.
5. Incremental refilter; do not render out-of-scope rows; keep global attention/count refresh.
6. Needs-you pips; empty states; `'` jump includes tab titles; persist last scope.
7. Docs: `docs/ace.md` Agents tab, `docs/remote_dispatch.md` “once enrolled” section, configuration keymap tables.

**Epic B — Agent clusters** (identity + CLI + TUI assigner):

1. Glossary strand `agent-cluster`; clan/tribe strands become policy aliases.
2. Relax hood / create-only / keyword exclusion / post-launch immutability.
3. `sase agent cluster` + `N` as the assigner; tribe CLI as alias.
4. Presentation: container / panel / (optional) user tab.
5. Allow `%dispatch` with cluster membership.
6. Compatibility: `%clan`, `#tribe`, `@name`, existing clan records and `agent_tribes.json`.

Epic A is the answer to “scale one TUI across apollo and athena.” Epic B is the answer to “clans and tribes are the same kind of assigned group, and the unique clan traps should go.”

---

## 9. Open questions for the lead / user

These are product choices, not blockers for Epic A:

1. On `all`, should local rows gain a `here` chip (prior fleet research said yes in a mixed list) or stay unlabeled (current shipping rule)? Recommendation: keep current shipping rule; the new `here` tab makes the local slice explicit.
2. Should `@job` / AXE work appear on machine tabs, or only on `all`? Recommendation: on every tab, still starting collapsed. Job agents have an origin too.
3. Epic B user-owned cluster tabs: ship with membership, or wait until someone uses `N` + presentation daily? Recommendation: wait (corpus-before-mechanism). Machine scopes first.
4. `%cluster` as a new directive versus keeping `%clan` / `#tribe` forever. Recommendation: keep the old directives as the spelled policies; add `%cluster` only if a third policy appears.

---

## 10. Sources (inspected)

- Glossary: `agent-clan`, `agent-tribe`, `agent-hood`, `agent-node`, `sase-node`, `sase-agent`, `sase-agent-session`, `agent-data-card-block`, `agent-relation-jump-target`; file `tui_perf.md`.
- `docs/agent_sessions.md`, `docs/ace.md` (Agents actions, tribe side panels), `docs/remote_dispatch.md`, `docs/xprompt.md` (`%clan`), `docs/configuration.md` (Projects/Machines sub-tabs).
- `src/sase/ace/tui/models/agent_panels.py`, `agent_groups/_buckets.py`, `agent_groups/_keys.py`, `actions/agents/_fleet.py`, `_fleet_projection.py`, `_fleet_header.py`, `_fleet_common.py`, `widgets/panel_tab_strip.py`, `widgets/agents_filter_bar.py`, `widgets/launch_context_bar.py`, `_app_layout.py`, `_app_action_availability.py`, `default_config.yml` keymaps, `agent/clan_membership.py`, `core/agent_clan_record.py`, `core/agent_tribe.py`, `ace/agent_query/evaluator.py`.
- Prior research: `202609/agents_across_machines/agents_across_machines.md`, `202609/agents_across_machines_review.md`, `202609/remote_machine_management_enablement.md`.
