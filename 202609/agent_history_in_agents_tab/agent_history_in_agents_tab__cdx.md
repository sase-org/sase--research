# Unifying local and project-published agent history in the Agents tab

Date: 2026-09-28

Researcher: `cdx`

## Executive judgment

Removing **Artifacts → Agent** is a good idea, with one important qualification: do
not replace it by putting the complete historical catalog into the Agents tab's default
roster. The Agents tab should remain a fast operational inbox when no historical scope
is requested, and become the one place to find and inspect agents through an explicit
**history lens**.

That conclusion follows from both the product trajectory and the data:

- The original `plan:202608/artifacts_agents_pane.md` explicitly called migrating the
  main Agents tab onto the shared query dialect the “natural successor” to the Agent
  pane. Most of that enabling work has now landed: the top-level tab has an
  `agents-live` profile, Rust-backed matching, completion, saved queries, history, and
  an auto-hiding filter bar (currently protected by the default-on
  `agents_unified_query` sunset flag).
- The two surfaces now ask users to search the same entity in two places. Link following
  exposes the split particularly clearly: an `agent:` link first tries the Agents tab
  and falls back to Artifacts → Agent when the live roster or its filter cannot reveal
  the target.
- The current project sidecar adds substantial genuinely new coverage. On this machine,
  the complete local registry-backed catalog has 1,662 rows (the default CLI view hides
  206 workflow-child rows and therefore shows 1,456). The current project's
  validated v2 hood snapshots contain 14,734 runs and 3,197 containers; only 562
  canonical names overlap the local catalog. A union therefore makes roughly 15,834
  distinct local-or-published identities accessible instead of forcing the user to know
  which machine owns them.
- That same scale makes a naïve merge unacceptable. The checked-out agents sidecar is
  809 MB under `agents/`, contains 2,451 hood snapshots, and has more than 15,000
  per-agent directories. It must never be scanned on the event loop or injected into
  the unfiltered operational roster.

The best design is therefore one Agents tab with two presentation states over one
catalog: an unchanged **Inbox** for operational work and an explicit **History** scope
for the union of locally owned history and the current project's published history.
This is a lens, not another root tab or an agent tab.

## What exists today

### Agents tab: already more than a “live-only” surface

The Agents tab's data path is centered on `src/sase/ace/tui/models/agent_loader.py` and
the persistent agent-artifact index. It loads running work and completed artifacts,
supports bounded first paint followed by full-history reconciliation, and merges remote
fleet projections. Its detail experience is substantially richer than the Artifacts
pane: session/clan trees, tribes, agent tabs, Main/Files/Tools/FINAL decks, artifact
viewing, live actions, unread state, neighbors, and remote-operation capability gates.

Its query surface is also converging with the catalog surface:

- `src/sase/ace/query_profile/profiles/_agents_live.py` declares the shared Boolean
  grammar plus live fields such as `machine`, `tab`, `pinned`, `unread`, `needs`, and
  `source`.
- `src/sase/ace/tui/models/agent_live_query_engine.py` compiles and evaluates a Rust
  query corpus off-thread.
- `src/sase/ace/tui/models/agent_live_query_pushdown.py` pushes supported terms into
  the persistent artifact index and schedules a quiet full-history reconcile for the
  rest.

In other words, the product distinction in the August plan—“live control room” versus
“historical catalog”—no longer requires two navigation homes. It does still require two
different *default presentations*.

### Artifacts → Agent: useful catalog, wrong long-term home

`src/sase/agents/catalog/` builds a Textual-free local catalog whose spine is
`~/.sase/agent_name_registry.json`, enriched by the local agent-artifact index and the
dismissed bundle archive. The pane supplies archive-specific fields and actions:

- `state`, `dismissed`, `revivable`, archive capability facts, and retry lineage;
- typed artifact-link facets (`linked`, `relation`, `artifact`);
- project/state/session grouping;
- revival of locally archived rows;
- durable `agent:` reference, prompt, chat, and published-page details.

This is valuable behavior. The problem is its placement and its source coverage, not
the behavior itself. It is machine-local, so the label “durable historical catalog” is
easy to overread as project-wide. Its registry spine also includes names that were
reserved but never ran: in the complete local sample, 709 of 1,662 rows had neither an
artifact-index record nor a dismissed archive record. Those thin rows were deliberately
kept to resolve old `agent:` references, but they should not be presented as “agents
ever run locally.”

### Agents sidecar: the missing project-wide read model

The v2 sidecar is owner-sharded and project-scoped. Its authoritative data is the set of
owner manifests and their referenced `users/.../hoods/.../snapshot.json` files. Each
snapshot already carries:

- owner and project identity;
- runs with global/local name, `source_run_id`, state, times, portable metadata,
  capabilities, commits, and references to prompt/chat payloads;
- session and clan containers;
- parent, workflow-parent, retry, and wait relationships.

This is almost exactly the portable historical record needed by the Agents tab. The
derived `agents/<global-name>/...` pages should not be the catalog source: they are
larger, can contain retained/orphaned generated pages, and exist for browsing. The
validated owner manifests and hood snapshots are the compact authority set.

The sidecar is intentionally **publish-only**. The accepted decision
`decisions:agents-sync-publish-only` deleted the import leg and says a future need to
sync agent state back onto local disk is a new design, not a resurrection. A unified UI
must therefore read sidecar rows in place. It must not create local registry entries,
artifact directories, dismissed bundles, notifications, or live agent state for them.

## Critique of the proposed plan

### What is good about it

1. **It puts an entity in one place.** An agent is an artifact in the domain model, but
   users act on agents as agents. Search, link following, prompt/chat inspection,
   revival, retry, and live control are easier to understand in one entity-oriented
   home than split across Agents and Artifacts.
2. **It removes a growing parity tax.** The two surfaces have separate row models,
   detail renderers, grouping rules, query profiles, selection state, copy targets,
   loading lifecycles, and link destinations. Every session/clan terminology change or
   query feature currently touches both.
3. **It matches recent architecture.** Query unification, full-history reconciliation,
   cross-tab link reveal, rich decks, and fleet rows have already moved the Agents tab
   toward being the canonical agent browser.
4. **It makes project history genuinely useful.** The measured overlap is small: 562
   names shared between 1,662 local rows and 14,734 published runs. The sidecar is not a
   redundant copy of the local catalog; it is the only available view of most runs from
   other machines.
5. **It simplifies artifact navigation.** `agent:` links no longer need the surprising
   rule “try Agents, then send filtered or unloaded rows to Artifacts → Agent.” The one
   destination can acquire the target and temporarily enter the right history scope.

### What would go wrong with a literal implementation

1. **“Show every agent” would destroy the operational default.** Adding about 14,000
   mostly historical published rows to the current roster would bury running work,
   produce many new machine/tribe panels, and expand startup and refresh work by an
   order of magnitude.
2. **Published state is not liveness.** A sidecar row may say `active`, but the clone
   may not have been pulled recently and publication itself can lag. Rendering that row
   as RUNNING, counting it as active/attention/unread, or enabling stop/retry would be
   false. It is “active in snapshot,” not a live fleet observation.
3. **Published rows lack required placement identity.** Machine tabs are keyed by an
   owner's installation id. V2 sidecar owner identity contains `username` and
   `machine_name`, not installation id. The strict portable metadata allowlist also
   does not currently publish `agent_tab`. Putting published rows into existing machine
   or authored agent tabs would invent semantics and could merge renamed/reused
   machines incorrectly.
4. **The sidecar cannot be scanned directly during startup.** A shell parse of the
   2,451 snapshots took about 1.06 seconds warm on this machine; `git ls-tree` over the
   per-agent tree took about 0.31 seconds before any JSON detail was loaded. Both exceed
   the TUI rule that first paint must not wait on archive-scaled work. The full
   `agents/` tree is 809 MB.
5. **The local registry is broader than the requested set.** “Ever named” and “ever
   run” are not synonyms. Thin reservation-only rows should remain resolvable by exact
   ref/name lookup, but should not pollute ordinary history results.
6. **The current project's published corpus is not complete project execution
   history.** Publication includes eligible project hoods and preserves published
   history, but a never-published, non-associated run from another machine is absent.
   The UI should say “published for this project,” not “every project agent.”
7. **Immediate deletion would lose working affordances.** Artifacts → Agent owns saved
   catalog queries, query history, copy targets, group navigation, archive detail, and
   revival entry points. These need migration and parity tests before its descriptor and
   widgets are removed.

## External pattern check

Three adjacent products reinforce the distinction between one entity home and one
eagerly loaded list:

- GitHub keeps current and historical workflow runs in the same Actions surface, while
  bounding the initial list and providing explicit workflow/status/branch filters
  ([GitHub Actions run history](https://docs.github.com/en/actions/how-tos/monitor-workflows/view-workflow-run-history)).
- Temporal's Web UI uses one Workflows page for retained executions, with structured
  filters and saved views; archival is a storage distinction rather than a second
  competing workflow identity
  ([Temporal Web UI](https://docs.temporal.io/web-ui)).
- LangSmith exposes a structured trace query language and explicitly recommends
  selecting only the fields needed when querying large histories
  ([LangSmith trace query syntax](https://docs.langchain.com/langsmith/trace-query-syntax)).

The inference for SASE is not to copy any of these interfaces literally. It is to keep
one canonical home for an agent, make historical acquisition explicit and queryable,
and load a lightweight projection before fetching large prompt/chat/deck payloads.

## Adjustments I recommend to the requirements

These are deliberate changes to the prompt's initial framing:

1. **Replace “any agent ever run locally” with “any locally owned run with durable run
   evidence.”** Local artifact-index and dismissed-archive records qualify. Pure
   registry reservations do not appear in normal results, though an exact `agent:` ref
   may still reveal a thin diagnostic row.
2. **Replace “any agent on the current project” with “any validated agent snapshot
   published in the current project's agents sidecar.”** This is truthful about both
   coverage and freshness.
3. **Define “accessible” as searchable/revealable, not always visible.** The no-query
   Agents view remains the operational Inbox. History is loaded only for an explicit
   scope, query, link target, or command-palette action.
4. **Keep published rows read-only in the first release.** A published-only row may be
   inspected, copied, linked, and used as context. It may not be stopped, retried,
   dismissed, revived, moved between tabs/tribes, or opened in a local workspace. A
   later feature may *fork* a restartable published prompt into a new local agent, but
   that is not revival and must never materialize an import closure.
5. **Remove Artifacts → Agent only through a sunset cutover.** Finish the replacement
   before exposing it, then put the completed unified route behind one default-on
   sunset flag whose Off branch retains the old pane as rollback. Redirect jumps and
   custom-revival search, migrate saved queries, and compare results before deleting
   the Off branch and flag after full-release evidence. A beta flag is unnecessary
   unless incomplete phases must be exposed to users, and such a beta must be removed
   before the feature lands.

## UX options considered

| Option | Benefits | Problems | Verdict |
| --- | --- | --- | --- |
| Append sidecar rows to the existing roster | Smallest conceptual change | Floods the inbox; lies about liveness, agent-tab placement, and action capability; startup cost | Reject |
| Keep both surfaces and merely add sidecar rows to Artifacts → Agent | Low operational risk; pane already fits historical rows | Preserves duplicate navigation and detail systems; fails the main information-architecture goal | Acceptable fallback, not the target |
| Add a fourth root tab named History | Clear operational/history separation | Splits the same entity again and increases top-level navigation; duplicates much of Agents | Reject |
| One Agents tab with Inbox and History lenses | One entity home; preserves fast default; can reuse decks/tree/query; honest capability separation | Requires a real unified read model and a nontrivial cutover | **Recommend** |

## Proposed UX

### 1. Preserve the no-query Inbox

Launching the TUI should look and behave as it does now. The Inbox contains live fleet
rows and the existing bounded visible local history. Agent tabs, machine tabs, tribes,
unread counts, attention counts, and operational actions remain scoped to this roster.

This is important: “Agents is the one place for agents” does not imply “the Agents
startup screen displays the complete database.” Email clients make the same distinction
between an inbox and searchable mail without putting the archive on the first screen.

### 2. Add an explicit host-owned history scope

Extend the filter bar with a corpus selector analogous to the Artifacts host-owned
`limit:` token. A useful vocabulary is:

```text
scope:inbox     current operational roster (default)
scope:local     locally owned durable runs, including dismissed archives
scope:project   validated snapshots in the current project's agents sidecar
scope:all       union of local and current-project published records
```

`scope:` controls acquisition and therefore should be host-owned, singular, and not
negatable; it is not an ordinary property evaluated row by row. The UI should expose it
as a visible scope chip/picker as well as query completion, so users do not need to
remember syntax. A command-palette action such as **Agents: browse history** should
enter `scope:all`, focus the filter bar, and retain the previous Inbox selection for
return. I would not choose a permanent key until the live keymap collision audit is
done.

Examples:

```text
scope:all name:research.*
scope:project machine:athena since:30d provider:codex
scope:local state:dismissed revivable:true
scope:project session:sase-zf
```

The current `project:` field remains a row property. `scope:project` means the published
source for the project captured when the History lens is entered. The visible chip and
canonical query should expose that concrete project identity. Changing SASE's global
current-project default must not silently replace the corpus under an already-open
view; the user explicitly refreshes/reselects the project, and stale workers are
cancelled by generation.

Do not transplant the Artifacts pane's `limit:` interaction or its Ctrl+J/Ctrl+K
pagination into this screen: those keys already navigate Agents deck cards. History
should use the Agents loader's bounded first result, viewport prefetch, and cancellable
cursor/pushdown path. `scope:` chooses a corpus; it is not a page-size control.

Old Agents-tab saved queries should retain `scope:inbox`. Artifacts Agent saved queries
should migrate into the Agents namespace with `scope:local`. This prevents a saved
`status:FAILED` query from unexpectedly expanding from a few live rows to thousands of
published rows after upgrade.

### 3. Make the history state visibly different without making it a tab

When scope is not Inbox:

- replace the operational count line with a clear label such as
  `History · local + sase published · 314 matches`;
- show sidecar HEAD/freshness and a warning when the clone is unavailable or known to
  lag;
- suspend the authored/machine agent-tab strip and tribe panels, because published
  rows lack trustworthy installation ids and `agent_tab` placement;
- render one merged node panel with the existing session/clan tree semantics, initially
  newest-first, with optional grouping/filtering by machine, project, state, or
  provenance;
- keep query history/back navigation so leaving the lens restores the exact Inbox tab,
  tribe, fold, query, and selection.

This is a mode of the existing Agents view, not a second widget shell modeled after the
Artifacts pane.

### 4. Show provenance and capability, not just status

Every historical row should carry a compact provenance chip:

- `here` — locally owned durable data;
- `published · athena` — current-project sidecar snapshot only;
- `here + published` — deduplicated row present in both;
- existing fleet alias — live remote feed, when one exists.

Published terminal states can use normal terminal labels. Nonterminal published states
must be qualified, for example `SNAPSHOT ACTIVE`, and must not contribute to live
counts. The detail header should show the indexed sidecar HEAD and its commit time,
plus the run's source timestamps. The v2 snapshot does not currently record a distinct
publication timestamp, so the UI must not invent one; a machine-local `indexed at`
time may describe cache freshness but not source freshness.

Actions derive from capabilities:

| Capability | Local row | Live fleet row | Published-only row |
| --- | ---: | ---: | ---: |
| Inspect prompt/chat/commits | yes | when feed permits | yes, lazily from sidecar |
| Copy/follow `agent:` ref | yes | yes | yes |
| Stop/retry/answer | when live | when advertised | no |
| Open workspace/tmux | when local | no | no |
| Revive | only with local dismissed bundle | no | no |
| Move tribe/agent tab | local roots | currently restricted remotely | no |
| Fork into a new local run | existing rules | existing rules | later, if restartable |

Unavailable deck cards should say “not published” or “local data unavailable,” rather
than silently appearing empty. In particular, sidecar snapshots do not contain the
local LLM tool-call and FINAL ledgers required for full Tools/FINAL parity.

### 5. Make links acquire history in place

An `agent:` link should always target the Agents tab. If the target is outside the
Inbox or current scope, the existing reveal transaction should:

1. resolve the canonical name against the unified catalog;
2. acquire the exact local or sidecar row without loading the entire visible result;
3. enter the narrowest truthful scope;
4. rewrite the query to `name:<canonical-global-name>` while saving the prior state;
5. expand only the required session/clan folds and select the node.

The toast can say `Inbox did not contain this agent — showing project history`, and
`^`/`Ctrl+O` should return. There should be no fallback to a soon-to-be-deleted
Artifacts pane.

## Data and implementation architecture

### A core-owned unified catalog

The consolidation creates a third frontend consumer of the catalog row model: the
Artifacts pane and `sase agent search` already consume it, and the Agents tab would be
the third. The docstring in `src/sase/agents/catalog/__init__.py` names that exact event
as a promotion trigger for `sase-core`. Project core memory independently says shared
backend/domain behavior belongs in Rust when another frontend must agree.

The durable design should therefore introduce a Rust-owned catalog domain rather than
teaching the Textual loader a second pile of Python joins. Python can retain thin I/O
adapters during migration, but identity, validation, deduplication, merge precedence,
capabilities, and query-row projection should have one core implementation and one wire
contract.

A better model than today's flat `AgentCatalogRow` is a node-oriented record:

```text
CatalogNode
  stable node id
  canonical agent ref
  project + owner + machine
  node kind (agent/session/clan/turn)
  optional source_run_id for concrete turns
  lifecycle + timing + execution fields
  capabilities
  provenance set
  lazy locators for local artifacts, dismissed bundle, fleet feed, sidecar files/page
  lineage edges
```

This matches current terminology: a session is one sase agent node whose members are
turn nodes; it avoids pretending every sidecar run is a top-level agent. Deduplication
should use canonical global identity plus node/run kind and `source_run_id` where
applicable, not display name alone. Merge precedence should be:

```text
live local/fleet observation > local durable artifacts > published snapshot
```

The lower-priority source is retained as provenance and as a fallback locator rather
than discarded. Conflicting fields should produce a diagnostic, not silently blend.

### A compact sidecar projection, never an agent-tree scan

Build a read-only compact index from validated owner manifests and referenced hood
snapshots, keyed by:

```text
(project key, committed agents-sidecar HEAD, v2 schema version, catalog wire version)
```

Store the derived SQLite/index file under machine-local SASE cache state, not in the
sidecar. Rebuild it off-thread only when HEAD or schema changes. Query it with pushdown
for scope, owner/machine, name, kind, state/status, provider/model, and time bounds.
Load prompt/chat/commits only for the selected row through the snapshot's verified file
references.

The existing chat provenance catalog in
`src/sase/history/chat_catalog_provenance/sidecars.py` provides a useful precedent:
it reads the committed sidecar tree and caches by HEAD. The new agent projection should
be stricter and richer by using validated manifests/snapshots instead of inferring rows
from `agents/*/chat.md` paths.

Startup and idle-refresh rules are non-negotiable:

- no sidecar git subprocess, JSON parse, stat walk, or index build on the event loop;
- first paint uses the existing Inbox cache only;
- history scope shows a cached result immediately and refreshes through a coalesced
  worker;
- auto-refresh compares cheap tokens and never pulls the network;
- **Sync agents** remains the explicit network freshness action;
- a current-project change invalidates only the sidecar component and preserves local
  catalog cache.

### One query schema, two acquisition scopes

After the `agents_unified_query` flag's rollback period ends, remove the legacy
`src/sase/ace/agent_query/` branch. Then converge `_agents_live.py` and `_agents.py` into
one shared Agent schema containing both operational and archive fields. Keep
`scope:` host-owned because it controls which stores are opened.

Prefer one multi-valued `presence:local|published|fleet` facet, plus perhaps
`snapshot_stale`, over a growing family of Boolean provenance fields. Avoid reusing
`source`, which already means `axe` versus `manual`. Archive fields (`state`,
`dismissed`, `revivable`, capability facts, link facets) should be present but
false/absent where the underlying source cannot establish them.

`sase agent search` should use the same core catalog and grammar. Its compatibility
default can remain local; add an explicit scope option/token and require a resolvable
current project for `project`/`all`. That keeps CLI/TUI results comparable and prevents
the top-level UI from becoming a third private implementation.

## Suggested rollout

1. **Contract and measurements.** Specify node identity, provenance, precedence,
   capability rules, snapshot freshness, and `scope:` semantics. Pin fixture counts and
   dedup behavior for local-only, published-only, overlap, session, clan, thin, stale
   active, and malformed-owner cases.
2. **Core catalog and sidecar projection.** Add the Rust wire/API, compact HEAD-keyed
   sidecar index, local-source adapter, and union/dedup engine. Extend `sase agent
   search` first as the headless correctness oracle.
3. **Complete the Agents History lens off the user path.** Reuse the existing node
   tree, query bar, link trail, and decks. Preserve the no-query Inbox
   byte-for-byte/visually. Add provenance rendering and capability-gated actions. Do
   not stack this migration on the legacy Off branch of `agents_unified_query`; finish
   that sunset first so there is one query implementation to extend.
4. **Behavioral parity.** Port Artifacts Agent saved queries, history, revival entry,
   copy targets, relation navigation, exact link reveal, and degraded states. Shadow
   compare local `scope:local` results against the old pane on fixtures and a live
   catalog.
5. **Redirect and soak behind one sunset cutover.** Activate the completed unified
   route under a default-on sunset flag; its Off branch retains the old pane. Make
   `agent:` links and custom revival search land in Agents History. Collect load,
   query, and action diagnostics without network activity for a full release.
6. **Delete Artifacts → Agent.** Remove its pane descriptor, widgets/mixins, actions,
   copy group, docs, and visual goldens; renumber the remaining Artifacts panes. Delete
   the old Off branch and compatibility flag only with the usual sunset evidence.
7. **Later cleanup.** Remove duplicate Python catalog/query paths after the Rust API and
   unified Agents schema are the only production route. Consider published-prompt fork
   separately; do not smuggle an import feature into this work.

## Acceptance criteria that matter

- No-query Agents first paint and idle refresh do no sidecar-scaled work and do not
  change the visible roster or agent-tab/tribe layout.
- Agents navigation remains under the existing p95 `< 16 ms` target with a history
  query active.
- All local/published overlaps deduplicate deterministically; the measured live corpus
  would produce one row for each of the 562 shared canonical names, not two.
- A published-only `agent:` target can be revealed from any tab without opening
  Artifacts and without materializing local agent state.
- `SNAPSHOT ACTIVE` never counts as live or enables operational mutations.
- Revival is offered only when a readable local dismissed bundle proves it is valid.
- Missing, disabled, dirty, malformed, offline, and stale sidecars degrade visibly and
  never hide local history.
- Reselecting the project in History swaps only the `scope:project` corpus and cancels
  stale workers/results by generation; changing the global current-project default
  does not silently mutate an already-open History view.
- Saved-query migration preserves scope: old live queries remain Inbox-scoped; old
  Artifacts Agent queries become local-history-scoped.
- `sase agent search` and the TUI return the same ordered identities for the same
  explicit scope and query.
- The pane is not deleted until link navigation, query/history, copy, relation, and
  revival parity tests pass.

## Evidence reviewed

- `plan:202608/artifacts_agents_pane.md` (original product split, row model, query and
  revival rationale).
- `plan:202609/agents_query_unification.md` (current shared query migration and perf
  constraints).
- `docs/ace.md`, `docs/query_language.md`, `docs/agents_sidecar.md`, and
  `docs/artifacts_pane_contract.md`.
- `src/sase/agents/catalog/`, the Artifacts Agent pane widgets/actions, Agents loader
  and query engine, v2 agents-sidecar models/readers, and chat-provenance sidecar cache.
- Accepted `agents-sync publish-only` decision and the Agent/Agent Tab/Machine Tab/Sase
  Agent/Agent Node/Agent Data Deck glossary strands.
- Current-machine measurements on 2026-09-28: 1,662 complete local catalog rows (709
  thin; 961 dismissed; 206 workflow-child), 14,734 v2 sidecar runs, 3,197 containers,
  11,847 relationships, 562 local/published canonical-name overlaps, 2,451 snapshots,
  and an 809 MB derived per-agent tree. Snapshot JSON parsing through `jq` took about
  1.06 seconds warm; `git ls-tree` over `agents/` took about 0.31 seconds. These are
  directional TUI-design measurements, not formal benchmark gates.

## Recommended solution

Delete Artifacts → Agent **after** building a core-owned, read-only unified catalog and
an explicit History lens inside the Agents tab. Keep the default Agents Inbox exactly
as it is; add `scope:local`, `scope:project`, and `scope:all` acquisition through the
existing structured query UI; index validated sidecar hood snapshots off-thread and
cache them by committed HEAD; deduplicate with live/local data while retaining visible
provenance; and make published-only rows inspectable but non-operational. Once that
replacement is complete, activate it behind one default-on sunset cutover flag whose
Off branch is the old pane, migrate saved queries and affordances, and remove both the
pane and flag once links, revival, copy, relations, query parity, and performance are
proven through a full release.
