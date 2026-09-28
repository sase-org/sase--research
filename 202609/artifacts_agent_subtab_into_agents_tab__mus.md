# Retiring the Artifacts → Agent sub-tab into the Agents tab

**Researcher:** mus · **Date:** 2026‑09‑28 · **Status:** research only, no product changes.

**Question:** remove the fixed **Agent** sub-tab of the **Artifacts** tab and make
"any agent ever run locally or on the current project (a sase agent published to the
agents sidecar)" accessible from the top-level **Agents** tab instead, possibly via
"the sase agent query language, if there is one". Is this a good idea, what should
the UX be, and how should it be implemented?

**Short answer:** the direction is sound but the proposal as stated is under-scoped
in exactly the places that will hurt: *data scope*, *query dialect*, *performance*,
and *which Agent-pane affordances must survive the move*. There **is** a sase agent
query language — in fact there are **two profiles** of one shared Boolean grammar —
and the right move is to reuse it, not invent a third dialect. The recommended end
state is **one Agents tab with an explicit Live / History scope switch**, where
History mode reuses the catalog query index, grouping, detail, and revive flows from
the retired pane. Do **not** merge everything into a single undifferentiated roster,
and do **not** default the Agents tab to full-history scope. Details and phasing
below.

---

## 1. What exists today (verified at HEAD)

### 1.1 Two surfaces, deliberately different jobs

`docs/ace.md` states the split explicitly:

- **Top-level Agents tab** — the *operational* view: running work, unread
  completions, clan/session panels, tribe panels (`@default`, `@job`, user tribes),
  deck/card detail. Optimized for "what needs me now".
- **Artifacts → Agent pane** — the *durable historical catalog*: queryable rows for
  prior runs, dismissed agents, sessions, clans, workflows, workflow children,
  newest-first. Optimized for "what ever happened".

This is a principled split (live attention vs. archive), but it has a real
discoverability cost: the archive is hidden as one of five fixed Artifacts sub-tabs
(`agents`, `stitches`, `patches`, `beads`, `files` — `FIXED_ARTIFACTS_SUBTAB_ORDER`
in `src/sase/ace/tui/_artifact_tab_model.py`, default `stitches`), and users must
know which of the two places to look. Unifying the entry point while preserving the
operational/archive distinction inside one tab is therefore a reasonable goal.

### 1.2 The Agent catalog: registry-spined, index-enriched

The Artifacts → Agent pane is a thin view over `build_agent_catalog_snapshot()`
(`src/sase/agents/catalog/_build.py`):

- **Spine:** the agent name registry — every registered name becomes exactly one
  row, degraded (thin, name-only) rather than dropped when enrichment is missing.
- **Enrichment 1:** a *projected* read of the agent artifact index
  (`src/sase/agents/catalog/_sources.py`) — selected columns only, never
  `record_json` (the ~117 MB blob column), never raw bundle JSON. Empty mapping on
  any failure (absent file, wrong schema version, unreadable DB).
- **Enrichment 2:** the dismissed-bundle summary index (top-level, plus a
  child-fallback for leftover suffixes), with a hard uniqueness invariant on
  `raw_suffix` (collisions raise `AgentCatalogBuildError`).

Scale note: on this machine `sase agent search` reports **40 of 1453, 1659 scoped**
rows — i.e. a low-thousands catalog is normal. The pane copes by painting the
newest **500 rows first** (`AGENTS_FIRST_PAGE_LIMIT` in
`src/sase/ace/tui/widgets/artifacts/agents_data.py`), then extending to the full
corpus and building the query index off-thread. Any replacement must preserve this
budget behavior.

Pane affordances that must be accounted for (from `docs/ace.md` § Agent Pane and
`src/sase/ace/tui/widgets/artifacts/agents_*.py`):

- Grouping: **Session / State / Project** (`o`/`O`), fold keys, group banners.
- Detail: durable `agent:` reference, identity, lifecycle/timing, model/provider,
  session+retry lineage, provenance, prompt preview, chat path, hosted agent page.
- Relation rail (collapsed by default, `.` to expand): session/clan/parent/retry
  chain plus typed artifact links (`cites`, `read`, `implements`, inverses).
- Revive: `w` (with mark support `m`/`u`), including the aggregate-session/clan
  narrowing behavior and the revive modal's **Viewable / Revivable / Restart /
  Missing** capability lines. Note `revivable:true` now means *dismissed **and**
  backed by a readable top-level bundle **and** `durably_revivable`* — the `w`
  seed query (`state:dismissed AND revivable:true`) deliberately excludes
  unrestorable rows.
- Project scope: shared Artifacts project scope (`p`) plus per-query `project:`.
- Copy-as palette (`%`), refresh via Refresh panel (`R`), cap controls
  (`Ctrl+J`/`Ctrl+K` rewriting `limit:`).

### 1.3 Yes, there is a sase agent query language — two profiles, one grammar

`docs/query_language.md` + `docs/ace.md` (§ filtering, § Agent Search) document a
**shared Boolean profile dialect**: implicit `AND` by juxtaposition, explicit
`AND`/`OR`/`NOT` (or `!`), parentheses, bare/quoted/case-sensitive (`c"…"`)
strings, `Tab` completions, history (`^`/`_`), saved slots (`#n`), non-fatal parse
errors. Two compiled profiles specialize it
(`src/sase/ace/query_profile/profiles/`):

| | Artifacts → Agent (`agents`, `_agents.py`) | Agents tab live (`agents-live`, `_agents_live.py`) |
|---|---|---|
| Identity/lifecycle | `name session clan project kind role workflow parent` | same shared set |
| Execution | `state` (active/done/dismissed), `status`, `provider`, `model`, `attempt` | `status`, `provider`, `model`, `attempt`, plus `cl` |
| Live-only ops | — | `machine` (alias/hostname, `here`), `tribe`, `tab`, `pinned`, `unread`, `needs`, `source` |
| Archive-only | `dismissed`, `revivable`, `historically_viewable`, `durably_revivable`, `restartable`, `linked`, `relation`, `artifact`, (`label` search-only) | — |
| Bounds | `since/until/after/before`, `min/max`, `text` | same shared set |
| Host cap | `limit:` accepted | `limit:` **not** accepted |

The CLI twin of the catalog dialect is `sase agent search [QUERY]` (same grammar,
`-p/--project`, `-l/--limit`, `-j/--json`). There is no third dialect to invent;
the design problem is how to **cover both field sets in one tab** (see §3).

### 1.4 The Agents tab already reaches into history — conditionally

Per `docs/ace.md` § Agent Search, a committed Agents-tab query decides how much
history loads: when the persistent artifact index can answer every term exactly
(`cl:`, `model:`, `provider:`, `project:`, `kind:agent`/`kind:workflow`,
`machine:`, incl. negated `machine:`, joined by `AND`/`OR`), the loader selects
from the **whole archive**; any other term first evaluates against a **bounded
recent-history window** with a `filtered on partial history; loading full
history...` header until a quiet-window full reconcile completes. Transcript
(`text:`) reads go through a background content-index worker (cached by
path+mtime, 512 KB cap per file).

Consequences: (a) the Agents tab is *already* a partial archive browser for
index-pushdown queries, so the proposal extends an existing trajectory rather than
bridging two disjoint worlds; (b) full-history-by-default would destroy the
performance contract in §1.2 — scope control is load-bearing, not cosmetic.

### 1.5 "Locally or on the current project (published to the sidecar)" = a union of three stores

The proposal's scope phrase maps to concrete stores:

1. **Local catalog** — registry + artifact index + dismissed archive (this
   machine). Already what both surfaces read.
2. **Current-project published pages** — the `agents` sidecar
   (`docs/agents_sidecar.md`): deterministic project-scoped agent-hood snapshots
   + canonical prompt archives, machine clone at
   `~/.sase/projects/<project-key>/repos/agents`, addressable as
   `@agent:<name>` refs. This is the *shareable, per-project* record and can
   include runs from **other machines** that published to the same project's
   sidecar.
3. **(Implicit) local runs on other projects** — the catalog already spans
   projects; "current project" scoping is a *filter*, not a store.

So "any agent ever run locally or on the current project" = **local catalog ∪
current-project sidecar publications**. The sidecar leg is the genuinely new data
work: the catalog builder has no sidecar reader today, and sidecar pages are
document-centric (Markdown + manifest) rather than row-centric. Treat sidecar
coverage as a **phase 2** (at minimum: link out to `@agent:` pages from history
rows; at most: sidecar-attributed rows in the roster), not as day-one roster
content — otherwise the "simple tab removal" inherits a cross-store join with its
own staleness, auth (other machines' pages), and dedup (same logical agent both
local and published) semantics.

Related prior art worth reading (ordinary prior research, not peer reports):
`202609/agents_across_machines*`, `202609/agent_machine_tabs_and_cluster_semantics*`,
`202609/agents_tab_decks_and_cards*` — especially anything on `machine:` scoping,
fleet/remote rows, and Rust-core counting/query boundaries.

---

## 2. Critique of the plan as stated

### 2.1 What's good about it

- **One front door for agents.** Two places to look (live tab vs. catalog sub-tab)
  is the kind of split users never internalize. An Agents tab that answers both
  "what needs me" and "what happened" reduces navigation debt and matches how
  competing agent products present session history (inbox + searchable archive).
- **Removes a tab-order wart.** `agents` is first in
  `FIXED_ARTIFACTS_SUBTAB_ORDER` but the default is `stitches`; the Agent pane is
  simultaneously prominent and usually not what you want on Artifacts open. Deleting
  it simplifies Artifacts chrome, digit shortcuts (`assign_artifacts_digit_shortcuts`),
  keymap surface, and the pane-capability matrix.
- **Query language reuse is the right instinct.** The Boolean dialect already has
  completions, history, saved slots, and a CLI twin. Folding history access into the
  tab with the strongest query bar avoids a second search UX.
- **Revive gets closer to where revived agents live.** Revival already lands the
  user back in live-agent land; hosting the trigger there shortens the loop.

### 2.2 What's risky or missing

1. **Scope ≠ filter.** "Any agent ever run locally or on the current project" is
   doing three jobs: choosing *stores* (local vs. sidecar), choosing *lifecycle*
   (live vs. dismissed vs. thin), and choosing *project filter* (all vs. current).
   These need independent controls or the tab will surprise (e.g. a current-project
   seed hiding the unread completion from another project — the exact reason
   `ace.current_project.seed_agents_query` defaults **off**: the same query drives
   unread jumps and prospective clans).
2. **Two dialects, one bar.** The `agents` and `agents-live` field sets are
   incompatible in both directions. A naive union schema breaks saved queries
   (namespaces are per-profile: `agents` vs `agents-live`), completions (archive
   fields offered on live rows that lack them, and vice versa), and validation
   (the three `historically_viewable`-family fields famously match *nothing* until
   the index populates them — a trap for a merged profile). A mode-switched bar
   (live profile in Live scope, catalog profile in History scope) is simpler and
   preserves saved-query compatibility.
3. **Performance is a correctness issue here.** 1.4 k+ rows, thin name-only rows,
   the 500-row first paint, off-thread index build, viewport-bounded live loads,
   quiet-window reconciles, transcript worker caps — all exist because full history
   is expensive. Making full history the default Agents-tab scope, or evaluating
   non-pushdown queries against the whole archive synchronously, regresses startup
   and keystroke latency. Scope must default to live; history must be opt-in per
   session with the existing bounded-window → full-reconcile pipeline reused, not
   bypassed.
4. **Affordance loss inventory.** The Agent pane's Session/State/Project grouping,
   relation rail + `linked:/relation:/artifact:` facets, capability-graded revive
   modal, copy-as palette, and `limit:` cap controls have no live-tab equivalents.
   "Integrate the sub-tab's functionality" must mean porting or explicitly
   deprecating each (see §4), not just making old names searchable.
5. **Keybinding and chrome collisions.** `/` edits the query on both, but the
   pane-local `f` explicitly *excludes* Artifacts → Agent; the live tab hides its
   filter bar when idle while every Artifacts pane shows a persistent filter row;
   `w/m/u/./%/R/Ctrl+J/Ctrl+K/p` are pane bindings with no live-tab meaning.
   Each needs a ruling.
6. **Persistence and migration.** Machine-local SASE state remembers Agents-tab
   queries per `agents-live` namespace and each Artifacts pane remembers its own;
   persisted Artifacts selections use stable ids (`ref:plan`, …) with fallback to
   Stitch when a provider is missing (`LEGACY_ARTIFACTS_SUBTABS` has entries for
   `prs/bugs/plans/other/chats` but **no `agents` entry** — one must be added,
   mapping to the new history scope or to `stitches`). Startup seeding
   (`seed_filters` vs `seed_agents_query`) needs a single coherent rule.
7. **Backend boundary.** Per the repo's Rust-core boundary rule, shared
   query/count semantics belong in `sase-core` (the fleet-counts move in
   `sase-xe.16.11.6.1` is precedent). A merged roster whose counts, grouping, and
   matching differ between Python and Rust callers will drift; the wire/API change
   should land in the linked `sase-core` checkout first, with the
   `sase-core-revision.txt` pin moved accordingly.

### 2.3 A different approach worth weighing (and why it still loses)

The cheapest alternative — **keep the pane, add bidirectional jumps**
(`JumpToAgent` from history rows; "show in catalog" from live rows, reusing the
existing jump machinery in `actions/navigation/`) — fixes discoverability without
any data, dialect, or perf risk. Recommend doing its *link* half anyway (deep links
are useful in both designs). But it keeps two query bars, two saved-query
namespaces, two grouping models, and the tab-order wart forever. Since the Agents
tab already conditionally loads archive history (§1.4), the scoped-union design
(§3) captures most of the jump proposal's value with a cleaner end state. Treat
jumps as phase 0, not the destination.

---

## 3. UX options considered

### Option A — Single undifferentiated roster (not recommended)

All live + catalog rows in one list, one merged query schema, `state:` picks the
lifecycle. Simplest to describe, worst in practice: unread/attention semantics
drown in thousands of dismissed rows; grouping (tribe panels vs.
Session/State/Project) has no coherent merge; the merged schema inherits the
`historically_viewable`-family trap; startup pays full-history cost or lies about
completeness. Reject.

### Option B — Agents tab with Live / History scope switch (recommended)

One tab, two explicit scopes, each keeping its current data pipeline, query
profile, grouping, and detail renderer:

- **Live** (default; today's Agents tab unchanged): tribe panels, decks/cards,
  unread/attention, `agents-live` profile, no `limit:` token, current behavior
  incl. conditional archive pushdown.
- **History** (the retired pane, relocated): newest-first catalog roster,
  Session/State/Project grouping, `agents` catalog profile, persistent filter row
  with `limit:`, relation rail, detail, revive, copy-as — i.e. the
  `ArtifactsAgentsPane` component re-hosted, not rewritten.
- Switch: a visible segmented control (and a key, e.g. `g`-prefixed or `tab`-local
  toggle — *not* a bare letter already bound in either surface) plus per-scope
  remembered query, grouping, and marks. Switching scopes never rewrites the other
  scope's committed query. A `JumpToAgent`-style reveal crosses scopes (selecting
  a live row from a history `agent:` ref and vice versa).
- Sidecar: History rows gain an **agent-page affordance** (`@agent:` link →
  published page) in phase 1; sidecar-only (other-machine) rows arrive in phase 2
  behind an explicit `scope:`/project control, clearly badged by provenance.

Why this wins: zero regression to live startup/attention (default scope unchanged);
both dialects survive untouched (saved queries keep working); the port is mostly
re-hosting (`agents_data/snapshot → query index → grouping → detail → revival`
already compose as mixins on `ArtifactsSnapshotPane`); perf architecture transfers
wholesale (500-row head, off-thread extension, transcript worker).

### Option C — History as an Agents-tab "panel" alongside tribes (fallback)

Render catalog history as one more bottom panel/section inside the live scroll.
Cheaper chrome than a scope switch but reintroduces Option A's mixing at the
render layer (fold/jump/count semantics across live + archive panels) while saving
little code. Prefer B; take C only if the scope-switch chrome proves too costly in
the TUI layout.

---

## 4. Requirement adjustments (what "integrate that sub-tab's functionality" must concretely mean)

1. **Scope the data promise down, in two phases.** Phase 1: local catalog only
   (registry + artifact index + dismissed archive — today's pane contents,
   re-hosted). Phase 2: current-project sidecar publications as badged,
   explicitly-scoped rows or page links. Do not promise "every agent from every
   machine ever" in phase 1; the sidecar join (staleness, dedup, non-local pages)
   is its own design task.
2. **Keep both query profiles; switch the bar with the scope.** No third dialect,
   no merged schema. `sase agent search` keeps the catalog dialect; the Agents tab
   uses `agents-live` in Live, `agents` in History.
3. **Port, don't drop:** Session/State/Project grouping + folds; relation rail and
   `linked:/relation:/artifact:` facets; capability-graded revive modal (`w`, marks,
   aggregate narrowing); copy-as palette; `limit:` cap + `Ctrl+J`/`Ctrl+K` (History
   only); project scope (`p` + `project:`, with the `seed_agents_query: false`
   default preserved for Live and a documented rule for History).
4. **Rule on every binding collision** (`f` excluded on the old pane; idle-hidden
   vs. persistent filter row; `w/m/u/./%/R/Ctrl+J/Ctrl+K/p`) — as a keymap table
   in the change spec, with `default_config.yml` updates (per repo keymap rules).
5. **Migrate persisted state:** add `agents → <new history scope>` to
   `LEGACY_ARTIFACTS_SUBTABS`; renumber digit shortcuts and announce the change;
   keep both saved-query namespaces; unify the `seed_filters`/`seed_agents_query`
   startup rule and document it.
6. **Keep the CLI stable:** `sase agent search` unchanged (it is the scriptable
   backstop during the TUI transition); add scope flags only if phase-2 sidecar
   rows need them.
7. **Put shared semantics in Rust core** (counts, matching, grouping keys) behind
   the `sase-core` wire + pin move, not as Python-only TUI logic.

---

## 5. Implementation sketch (phases; no code changed by this report)

- **Phase 0 — links (small, reversible):** cross-jump actions between live rows
  and catalog rows via existing `JumpToAgent`/link-reveal machinery; agent-page
  (`@agent:`) link on catalog detail. Proves the join keys before moving UI.
- **Phase 1 — re-host (the actual retirement):** move `ArtifactsAgentsPane`'s
  mixin stack (snapshot/query/grouping/detail/relation/revival) under the Agents
  tab as History scope; scope-switched filter bars with per-scope profiles,
  remembered queries, grouping, marks; keymap table + `default_config.yml`;
  `LEGACY_ARTIFACTS_SUBTABS["agents"]` migration; remove `fixed_descriptor("agents")`
  + `agents` from `FIXED_ARTIFACTS_SUBTAB_ORDER`/accents/icons/contracts; update
  `docs/ace.md`, `docs/query_language.md`, `docs/artifacts_pane_contract.md`
  (+ visual grammar), `docs/agents_sidecar.md` links, help modals, and
  `sase artifact`/pane-capability tests (pane contract, palette, shortcut,
  provider-ordering, catalog-build suites).
- **Phase 2 — sidecar scope (separate design):** provenance-badged
  other-machine/current-project rows or page-level integration; staleness + dedup
  rules; CLI flags if needed.
- **Verification:** existing suites for artifact tabs (`tests/ace/tui/…`), agent
  catalog (`tests/…catalog…`), query profiles, plus new tests for scope switching
  (query/grouping/marks isolation), legacy-`agents` migration, shortcut
  renumbering, and History-scope perf budgets (first-paint head, off-thread
  index). Run the repo's configured check recipe on completion.

---

## 6. Recommended solution

Adopt **Option B**: retire the fixed Artifacts → Agent pane and re-host it as an
explicit **History scope inside the Agents tab**, keeping Live as the default
scope with today's behavior, pipelines, and `agents-live` dialect untouched, and
running the catalog profile, grouping, detail, relation rail, and revive flows in
History scope. Ship Phase 0 links first, then the Phase 1 re-host + pane removal
(+ legacy-id migration and docs), and treat sidecar (other-machine,
current-project) roster rows as a separately-scoped Phase 2. This delivers the
ask — one front door for "any agent ever run locally", with current-project
publications linked from day one and joined in phase 2 — without merging the two
query dialects, without regressing live startup or unread semantics, and without
losing any catalog affordance that users rely on for revival and provenance.

*Verification performed for this report:* read `docs/ace.md` (Agent Pane,
Agent Search, Agents-tab layout, filtering sections), `docs/query_language.md`,
`docs/agents_sidecar.md` (overview), `src/sase/ace/tui/_artifact_tab_model.py`
(tab order/accents/icons/legacy map), `src/sase/ace/tui/artifact_tabs.py` +
`_artifact_tab_descriptors.py` (fixed `agents` descriptor), `src/sase/ace/tui/widgets/artifacts/agents_{pane,data,query,revival}.py`,
`src/sase/agents/catalog/{_build,_sources,_models}.py`,
`src/sase/ace/query_profile/profiles/_agents{,_live,_shared}.py`, and `sase agent
search` help + live output (1453-row catalog observed). No TUI session was
launched; no usability testing was run — this is a source- and docs-grounded
architecture assessment, and the Phase 1 estimate should be confirmed with a
change spec before scheduling.
