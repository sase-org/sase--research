# Agent sub-tabs and agent clusters: research and recommendation (__mus)

Researcher: mus. Independent report for the 4-researcher swarm on grouping agents
on the Agents tab with sub-tabs, the `[`/`]` → `(`/`)` keymap migration, and
unifying clans/tribes/tabs as "agent clusters".

## 1. What the request actually asks for

1. New sub-tabs on the Agents tab as a grouping mechanism (motivating example:
   one sub-tab per machine, e.g. `apollo`, for remote-node scale-up).
2. Migrate existing `[`/`]` card-block navigation to `(`/`)` to free `[`/`]`
   for the new sub-tabs.
3. Reframe clans, tribes, and sub-tabs as one concept ("agent clusters", new
   glossary term), removing clan-specific requirements so members move
   seamlessly between clans/tribes/tabs.
4. A design that is intuitive, reliable, and beautiful, led by the researcher.

## 2. Current state (observed in this checkout)

### 2.1 The Agents tab already has three grouping mechanisms

- **Grouping tree** (`src/sase/ace/tui/models/agent_groups/`): `GroupingMode`
  is `STANDARD` (project → patch → name-root → name-prefix), `BY_DATE`,
  `BY_STATUS`, and — critically — **`BY_MACHINE`**. `BY_MACHINE` already puts
  the fleet machine alias at L0 (local rows under `here`), then the same
  status-bucket subgroup as `BY_STATUS`, then name-root/prefix
  (`_buckets.py`, `_keys.py::_machine_name` reads `fleet_origin_alias`).
  There is a `machine_grouping_signature` in-place patch guard, degraded-feed
  banner support in `_tree.py`, and a "Machine: This machine and remotes,
  grouped by status" choice in the grouping modal
  (`modals/agent_grouping_modal.py`). So the `apollo`-tab motivating example
  is ~80% solved today as a grouping mode, without any new chrome.
- **Tribe panels** (`models/agent_panels.py`): each Agents-tab panel renders
  one tribe bucket, sorted alphabetically. Tribes are the current "many
  buckets side by side" mechanism.
- **Decks/cards/blocks** (`widgets/decks/`, glossary `agent-data-deck`,
  `agent-data-card-block`): Main / Files / Tools decks about the *selected*
  node; a session Reply card holds one `CardBlock` per concrete turn with
  `[`/`]` stepping and a block rail.

Sub-tabs would be a *fourth* mechanism and a *second* partition dimension
(tribe panels × machine sub-tabs × grouping L0). That product fact dominates
the design: whatever we add must compose with, or replace, one of the above —
not stack on top of all three.

### 2.2 The `[`/`]` conflict is real but the proposed destination is occupied

`src/sase/default_config.yml` (app keys):

- `next_card_block: right_square_bracket` / `prev_card_block:
  left_square_bracket`, with the comment "shares `[`/`]` with
  `cycle_artifacts_subtab` (Artifacts); disambiguated by tab availability".
- `cycle_artifacts_subtab[_reverse]` owns the same keys on Artifacts.
- **`files_next_version: right_parenthesis` / `files_prev_version:
  left_parenthesis`** — `(`/`)` is already taken on the Files sub-tab /
  Artifacts file views.

So the plan as written does not free a key so much as *move* a collision from
(Artifacts sub-tab) to (Files version stepping). It also breaks a TUI-wide
convention: `[`/`]` already means "cycle sub-tab" in the Config hub
(`config_hub_keys.py`), prompts modal, notification tag tabs, gate-debug tabs,
and plugins browser. Users will expect `[`/`]` to cycle Agents sub-tabs *and*
will be surprised that card-block stepping — an intra-card micro-navigation —
ever owned those keys. Additional ergonomics: `(`/`)` requires Shift on US
layouts (they are `Shift+9/0`), making rapid block stepping strictly worse,
and paren keys already read as "version stepping" to Files users.

### 2.3 Clans, tribes, sessions are different kinds of thing

Glossary (read directly from `sase/memory/glossary/`):

- **Agent clan**: "a named, rootless container for agents that run in
  parallel. Every member is named inside the clan's hood (`<clan>.<suffix>`)
  and declares `%clan:<clan>`; the clan name is reserved and is never itself
  an agent."
- **Agent tribe**: "a user-facing label for related agents across clans and
  sessions", assignable at launch (`%id(tribe=…)`, `#tribe:…`,
  `%clan(<clan>, tribe=…)`) or post-hoc via `sase agent tribe`, displayed
  `@`-prefixed.
- **Agent session**: "a sase agent whose agent turns run as a strictly
  sequential chain", `<session>--<suffix>` naming, bare-name container
  reservation — an *execution topology* with ordering semantics.
- **Agent node**: session node, or turn node when there is no session; session
  members render as turn nodes.

Implementation reflects deeper splits the request underplays:

- Clans are **launch-time, artifact-derived, generational**:
  `agent/clan_membership.py` (`ClanMembershipPlan{clan_name, generation}`,
  `resolve_or_create` vs `declare` reservation paths, env-payload consumed so
  nested launches cannot inherit), `agent/names/_lookup_groups.py`
  (`AgentClan{name, generation, members}`, `is_complete` = all members
  success), hood-prefix naming with clan-name reservation
  (`_AgentNameClanCollisionError`), clan container status projection
  (`models/_agent_clan.py`), synthetic clan detail panels
  (`_agent_clan_sections.py`, Summary card for clans in the deck glossary).
- Tribes are **post-hoc, mutable, JSON-persisted labels**:
  `ace/agent_tribes.py` over `~/.sase/agent_tribes.json` (atomic write,
  cross-process lock, legacy `agent_tags.json` import, `chop`→`job`
  migration), `core/agent_tribe.py` validation (`TRIBE_NAME_RE`,
  reserved `default`, `InvalidTribeError`), and panel-driving
  (`agent_panels.py`).
- Sessions are **sequential chains** with attach/rename/reserve machinery
  (`agent/_agent_session_attach_*`, `plan_chain` helpers). The request is
  right that sessions are "deeper" — but clans are deeper than labels too:
  generation identity, name reservation, parallel-launch planning
  (`multi_prompt_launch_plan.py::_ClanPrepass`, `StaticClanDirective`), wait
  resolution, and clan-summary epics all key on clan execution facts.

"Move nodes to and from clans/tribes/tabs seamlessly" therefore conflates
three move types with different costs: re-label (tribe, cheap, reversible),
re-filter (tab, free, no identity change), and re-parent execution (clan,
requires renaming into the hood, minting a generation, rewriting artifact
`agent_meta.json` lineage — effectively a relaunch, not a move).

## 3. Critique: is this a good idea?

**The scale problem is real; sub-tabs are a reasonable answer, but the plan
as scoped has three flaws.**

1. **It duplicates `BY_MACHINE`.** If the first seeded sub-tab set is
   "one tab per machine", we will have two machine axes (a grouping mode and
   a tab strip) with subtly different semantics (filter vs. L0 bucket,
   `here`-first ordering vs. tab order, degraded-feed banners in one but not
   the other). Users managing an `apollo` fleet will reasonably ask which one
   is canonical. Either the sub-tab strip *replaces* `BY_MACHINE` as the
   machine story, or machines are the wrong seed content for sub-tabs.
2. **The keymap migration trades one collision for another and degrades
   ergonomics.** Card-block stepping on Shift-chords next to an existing
   Files-version binding is worse on both counts. The good instinct (sub-tabs
   deserve the prime `[`/`]` real estate, consistent with every other tab in
   the TUI) does not require punishing the much more frequent block-stepping
   action with a worse chord.
3. **Full clan/tribe/tab unification is the wrong abstraction.** A unified
   *display* primitive is valuable; unifying the *execution* primitives is
   not. Removing clan name reservation, generations, or hood naming "to make
   moves seamless" would break `%clan`, clan wait targets, clan completion
   semantics, and the clan Summary card — the reliable parts of the current
   system — while delivering a "move" that is secretly a relaunch. The
   codebase's logic is correct to treat sessions (and to a lesser extent
   clans) as deeper than labels.

There is also a scope risk the request names honestly ("beautiful!"): a new
persistent tab strip is new chrome on the most space-constrained tab in the
TUI. Done badly it squeezes the node panel, fights tribe-panel headers, and
adds a persistence/sync surface (per-tab selection, fold state, ordering)
that must work across remote feeds with skew. Worth doing, but the bar is a
generic, bounded tab strip — not bespoke machine tabs plus a parallel
grouping mode plus seamless execution migration in one change.

## 4. Adjustments to the requirements (explicit)

1. **Do not migrate card blocks to `(`/`)`.** That binding is taken
   (`files_next/prev_version`) and is a worse chord. Instead give Agents
   sub-tabs `[`/`]` (consistent with Artifacts/Config/prompts/notifications)
   and relocate card-block stepping to context-gated `[`/`]`-with-focus *or*
   to a non-colliding chord (recommendation §6).
2. **Do not seed machine-specific tabs as the model; seed a generic
   filter-preset tab strip, initially {All, Here, per-machine}.**
   `BY_MACHINE` stays as the "All machines, grouped" view until usage data
   says otherwise; per-machine tabs are *filters* over the same feed, not a
   second grouping implementation. If tabs succeed, *then* consider retiring
   `BY_MACHINE` mode — do not ship both as equals on day one without a
   deprecation note.
3. **Narrow "agent clusters": add the glossary term, but define it as a
   presentation-level grouping view-model, not a replacement execution
   primitive.** Keep clan (parallel container), session (sequential chain),
   and tribe (mutable label) semantics intact. Unify only what the screen
   needs: one `Cluster` identity the tree, panels, and tabs can all render
   and move *views* across, with illegal execution moves explained, not
   silently relaunched.
4. **Cap the tab strip.** Unbounded "one tab per machine" does not scale to
   the fleets that motivate it. Tabs beyond N collapse into an overflow
   picker (the existing node-finder / jump-modal patterns), and degraded or
   unknown machines render the same degraded banner treatment `BY_MACHINE`
   already has — never a dangling empty tab.

## 5. Design sketch

- **Model**: `AgentsSubTab = {id, kind: all | machine | tribe | status…,
  title, filter predicate, icon/accent}` backed by the same feed and the same
  `fleet_origin_alias` / tribe / status fields the grouping tree already
  reads. Tabs filter; grouping modes bucket *within* the tab. Default tabs:
  `All`, `Here`, then one per known machine alias (alphabetical after Here,
  mirroring `_project_sort_key` for `BY_MACHINE`), plus optional pinned tribe
  tabs later. Tab set resolves from the Artifacts-tab-registry pattern
  (`ace/tui/artifact_tabs.py` + descriptors + digit shortcuts) rather than a
  new ad-hoc registry.
- **Behavior**: `[`/`]` cycles tabs (with digit jumps `1..n` like Artifacts);
  selection and per-tab fold state persist via the existing
  `ace/grouping_strategy.py` save/load pattern; empty/degraded machines show
  an inline empty-state with the degraded-banner copy, not a blank panel;
  overflow past ~8 tabs goes to a `g`-style picker reusing the grouping-modal
  component.
- **Cluster view-model**: `Cluster{id, kind: clan|session|tribe-set|machine,
  title, member identities}` used by tree banners, tribe panels, and tabs.
  Legal moves: retribe (any member), retab (view-only, always legal),
  clan-join (explicit relaunch with new hood name + generation — surfaced as
  "move via relaunch", never silent). Clan reservation, generations, and
  `is_complete` stay exactly as they are.
- **Beauty**: one tab strip above the node panel reusing Artifacts sub-tab
  accents/icons and the Config-hub bracket affordance; block rail unchanged;
  no new colors — machine tabs get the existing accent rotation, tribe tabs
  keep `@`, clan banners keep their Summary-card treatment.

## 6. Keymap recommendation (concrete)

- `[` / `]` → cycle Agents sub-tabs (all focus contexts on the Agents tab).
  Consistent with Artifacts, Config hub, prompts, notifications, gate-debug.
- Card-block stepping: keep `[`/`]` **only when the deck-panel detail has
  focus** (context-gated disambiguation, the same technique the current
  Artifacts comment documents), **and** bind a focus-independent fallback
  that does not collide: `{`/`}` is taken (deck grow/shrink, Artifacts
  split), `(`/`)` is taken (Files versions) — so use **`Ctrl+[` / `Ctrl+]`**…
  no; simplest collision-free pair consistent with deck navigation is
  **`Ctrl+J / Ctrl+K`-adjacent `Alt+J / Alt+K`?** No — keep it simple:
  **`,`/`.`** (unbound in the Agents context, adjacent, single-key,
  no Shift). Document both: detail-focused `[`/`]` keeps muscle memory;
  `,`/`.` works everywhere. Update `default_config.yml`, the help modal
  (`agents_bindings.py`), and the keybinding-modes hint bar
  (`_keybinding_bindings_agents.py`) together — the three places that
  currently render the `[`/`]` hints.

## 7. Recommended solution

1. Ship a **generic Agents sub-tab strip** (All / Here / per-machine filters),
   `[`/`]`-navigated with digit shortcuts, modeled on the Artifacts sub-tab
   registry; keep `BY_MACHINE` as the grouped "All" view for one release.
2. **Do not move card blocks to parens.** Context-gate `[`/`]` on detail
   focus and add `,`/`.` as the global block-stepping fallback.
3. **Add "agent cluster" to the glossary as a display-level term** and build
   the `Cluster` view-model for banners/panels/tabs; **do not remove clan
   execution semantics** (reservation, generations, hood naming, completion).
   "Seamless moves" = seamless re-label/re-filter; clan changes stay explicit
   relaunch flows.
4. Gate landing on: no new `[`-family collisions (sweep Config/prompts/
   notifications/file-version bindings in tests), bounded tab strip with
   overflow + degraded-feed states, persisted selection/fold per tab, and a
   glossary strand for the new term with `sase memory read` coverage.

The motivation (fleet scale, `apollo`-style per-machine views) is well
founded, and sub-tabs are the right chrome for it — but as generic filter
tabs reusing proven registry/keyboard/empty-state patterns, with clans kept
honest as execution containers underneath.
