# Retire Artifacts ▸ Agent: destination unification, not a list union

**Researcher:** grk (independent swarm report)
**Date:** 2026-09-28
**Repo state:** workspace `sase_24` checkout of `sase`; live index and `sase agent search` measured on this machine the same day
**Question:** Should the Artifacts tab's Agent sub-tab be removed, with its function moved onto the Agents tab so that any agent ever run locally, or published to the current project's agents sidecar, is accessible? What should the UX be? Is the idea good?

---

## Verdict

**Do the destination merge. Do not dump the catalog into the live tree.**

Retiring Artifacts ▸ Agent is a good idea *if* the Agents tab becomes the only place `agent:` identity lands, and historical / sidecar rows are *reachable* through a History lens plus the existing Boolean agent query language. It is a bad idea if "accessible" is implemented as "always listed in the working tree."

The current split is not accidental duplication. Epic `sase-tj` (`plan:202608/artifacts_agents_pane.md`) shipped the Agent pane as a **different product** from the live Agents tab: a registry-spined catalog for dismissed, thin, and link-addressable names. That split solved a real problem (the live tree excludes dismissed rows by construction). The cost is that "where is this agent?" now has two answers, and `$` link-follow already prefers the Agents tab, bouncing to Artifacts ▸ Agent only when the live filter hides the row.

The right next product is the successor that epic named but did not ship: **one agent destination, two lenses.** The query language already exists (two profiles, one Boolean grammar). Use it as the History search, not as a reason to paint 3,000+ dismissed rows into the control room.

Sidecar-published current-project agents are a **second epic**, not part of the pane move. The catalog today does not read the agents sidecar. The original pane plan rejected sidecar pages as the spine. Re-importing them as live nodes would reverse `agents-sync-publish-only`.

---

## 1. What exists today

### 1.1 Two agent surfaces, two jobs

sase's TUI has three top-level tabs. Agents is the startup default. Artifacts opens on **Stitch**, not Agent (`DEFAULT_ARTIFACTS_SUBTAB = "stitches"`). Agent is still digit `1` on the Artifacts strip.

| Surface | Job | Row model | Default contents | Query profile |
| --- | --- | --- | --- | --- |
| **Agents tab** | Live control room: run, kill, unread, decks, tribes, presentation tabs, folds | Full `Agent` objects in a clan/session/workflow **tree** | Running + bounded recent completed. Dismissed rows are gone. | `agents-live` |
| **Artifacts ▸ Agent** | Durable catalog: find, inspect, revive, follow `agent:` refs the live tab does not hold | One `AgentCatalogRow` per **name-registry** entry, newest-first **list** | First 500, then the full catalog off-thread | `agents` (catalog) |
| **`sase agent search`** | Same catalog as Artifacts ▸ Agent, CLI | Same `AgentCatalogRow` snapshot | Default presentation hides `hidden` and `kind:workflow-child`; cap 40 | catalog dialect |

Docs state the split in so many words (`docs/ace.md` Agent Pane): the live tab is operational; the pane is prior runs, dismissed agents, sessions, clans, workflows, and workflow children.

### 1.2 The live tab is already a bounded inbox, not "every agent"

The Agents-tab loader (`src/sase/ace/tui/models/_agent_loader_artifacts.py`) is explicitly tiered:

- 200 most-recent completed on a source-scan fallback
- 2,000 visible-inbox safety cap
- 1,000 active cap
- First paint must not wait on O(archive) work (`tui_perf.md` rule 9)

A committed `agents-live` query can select from the **whole archive** only when every term is index-pushdown-safe (`cl:`, `model:`, `provider:`, `project:`, `kind:agent`/`kind:workflow`, `machine:`). Anything else (`status:`, `name:`, free text, `tribe:`, `tab:`) first matches the recent window and then schedules a quiet-window full-history reconcile. The header says so.

Dismiss is a working-set mutation: `x` / save-group hides the row. Getting it back is revive (`!R` saved groups on the Agents tab; `w` on Artifacts ▸ Agent). Node-finder research already classified dismissed rows as correctly unreachable from `"`, because revival is a mutation.

### 1.3 The catalog is registry-spined and local

`build_agent_catalog_snapshot()` (`src/sase/agents/catalog/_build.py`) left-joins:

1. the permanent agent-name registry (the only complete name index)
2. the persistent artifact SQLite index (projected columns only; never `record_json`)
3. dismissed-bundle summaries (top-level only)

There is **no sidecar reader** in `src/sase/agents/catalog/`. A thin row with neither enrichment still renders ("no run data") rather than disappearing. That is why `agent:` refs that name a reservation with no surviving run still resolve.

Catalog grouping is Session / State / Project (`o`/`O`). Detail is identity, lifecycle, timing, model/provider, lineage, prompt preview, chat path, and a best-effort hosted sidecar **URL** for an already-local row. Revival (`w`) seeds `state:dismissed AND revivable:true`.

### 1.4 Two Boolean query profiles, one grammar

There *is* an agent query language. It is not a third syntax. It is the shared Boolean profile dialect (`docs/query_language.md`, `docs/ace.md` Agent Search).

**Shared fields:** `name`, `kind`, `session`, `clan`, `project`, `role`, `workflow`, `model`, `provider`, `status`, `attempt`, `hidden`, `attention`, `retry`, `since`/`until`/`after`/`before`, `min`/`max`, `text`. Grammar: implicit AND, `OR`, `NOT`/`!`, parentheses, quoting, `*` globs.

**Live-only (`agents-live`):** `machine`, `tribe` (user-defined), `tab`, `pinned`, `unread`, `needs`, `source`, `cl`. No `limit:` token. Idle filter bar is hidden.

**Catalog-only (`agents`):** `state`, `dismissed`, `revivable`, `historically_viewable`, `durably_revivable`, `restartable`, `linked`, `relation`, `artifact`, `parent`, `label`. Persistent idle filter row. Host-owned `limit:N` / `limit:all`. Catalog `tribe` is the clan enum `epic`/`chop`/`research`, not the live user-defined tribe — same key, different meaning.

The three advertised archive-capability fields (`historically_viewable`, `durably_revivable`, `restartable`) are in the schema but **not populated** in the query index; both `true` and `false` match nothing. Inspect the revive modal; use `revivable:true` to find restorable rows. Do not design new UX around those three keys until they are real.

`sase agent search` is the CLI of the catalog profile. Examples from `--help`:

```text
revivable:true AND project:sase AND role:code
provider:codex AND status:FAILED AND since:7d
session:"research.12" AND NOT kind:workflow-child
linked:true AND relation:read
```

The Agents tab already uses this grammar through `agents-live`. The remaining gap is corpus and field-set, not syntax.

### 1.5 Link-follow already treats Agents tab as primary

An `agent:` link lands on the Agents tab when the agent is loaded there, opening folds/tribes around it. **The Agents-tab filter is never rewritten.** If that filter hides the row, the jump falls through to Artifacts ▸ Agent and the toast says `Agents tab filter hides it — showing Artifacts ▸ Agent` (`_link_follow_targets.py`, `_link_follow_toast.py`, `docs/ace.md` Link Jumps).

Files-pane `a` already "Jump to the producing agent on the Agents tab, reviving it first when dismissed."

So the product already wants Agents tab as the `agent:` destination. Artifacts ▸ Agent is overflow for rows the live inbox does not hold.

### 1.6 Revival is already split

| Path | Where | What it restores |
| --- | --- | --- |
| `!R` | Agents tab | Saved **groups** of dismissed bundles, with paging and a custom archive search |
| `w` | Artifacts ▸ Agent | Query-first **catalog rows** (`state:dismissed AND revivable:true`) |
| `a` | Artifacts ▸ File | Producing agent, revive-then-jump to Agents tab |

Dismissed storage is O(1) per agent under `~/.sase/dismissed_bundles/YYYYMM/` plus a SQLite summary index. There is no cap.

### 1.7 Sidecar publication is not a second live roster

The agents sidecar (`docs/agents_sidecar.md`) publishes deterministic hood snapshots and prompt archives to `sase--agents`. `@agent:foo` / `@agent:<username>.<machine>.foo` addresses `agents/<global-name>/README.md` in the **selected project's** sidecar.

Decision `agents-sync-publish-only`: the import leg is deleted. Sync publishes outward. Leftover imported local state has one explicit purge. A published page is a document, not a reconstituted Agents-tab node. Missing published pages hint `run sase agent sync`, not "import this run."

Catalog detail may show a hosted URL for a local row. It does not enumerate other machines' published hoods.

### 1.8 Naming collision: "Agent tab" vs "Agent sub-tab"

Glossary **Agent Tab** means a presentation placement on the Agents tab (`%tab:<name>`, `[`/`]`, default `main` or a derived machine tab). Artifacts ▸ Agent is a different object: an Artifacts **nav section**. Any design that adds a History lens or a History presentation tab must not reuse `agent_tab` for it.

---

## 2. Live scale on this machine (2026-09-28)

These numbers are from this host today, not the August epic snapshot.

| Corpus | Count | Command / source |
| --- | --- | --- |
| Visible artifact-index rows (Agents-tab working inbox) | **239** | `sase agent index status` |
| Dismissed identities in that index | **3,438** | same |
| Hidden terminal rows retained | **378** | same |
| Default `sase agent search -l 0` rows | **1,456** | hides hidden + workflow-child |
| Epic `sase-tj` registry measurement (2026-08-25) | **12,525** names | `plan:202608/artifacts_agents_pane.md` |
| Catalog first-paint page | 500 | `AGENTS_FIRST_PAGE_LIMIT` |
| Catalog snapshot budget (epic, synthetic) | ≤ 400 ms worker | same plan; repaired bench later measured ~1.5 s with real sources |

Dismissed identities are about **14×** the visible inbox. The full name registry is about **50×**. A union list on the default Agents tab would bury running work.

The catalog's own first paint already refuses to wait for the full corpus: 500 rows, then an off-thread extension. The live tab is stricter still.

---

## 3. Why the Agent pane was put on Artifacts

`plan:202608/artifacts_agents_pane.md` (epic `sase-tj`) is explicit:

> The **Agents tab** is the live control room… The **Artifacts → Agent pane** is the historical catalog: complete, queryable, revivable, link-addressable. They share the query dialect and one revival implementation. They do not share a widget, and this epic does not deprecate either.

Reasons that still hold:

1. **The live list cannot be the `agent:` spine.** Measured against 47 distinct live `agent:` payloads on `gh_sase-org__sase`, the name registry resolved 47/47; artifact index + dismissed archive together ~28/47; the live Agents list only the visible working set. 19/47 refs (40%) named a **container** (then "family", now session), not a run.
2. **Do not spine on sidecar pages.** They git-sync, lag, and can be absent on a fresh machine.
3. **Do not spine on the live list.** It excludes dismissed rows — the rows revival exists for.
4. **Migrating the main Agents tab onto the catalog dialect was out of scope** because it touches the startup tab and had to be revertible alone. That successor (`agents_unified_query` / `sase-zg`) has since landed: the live tab now uses the shared Boolean profile. The *dialect* unification is done. The *destination* unification is not.

The pane was the right epic for "give `agent:` a catalog." It is no longer the right steady-state IA now that `$` prefers the Agents tab and users have two places named Agent.

---

## 4. Critique of the request

### 4.1 What is right

- **One place to look for an agent.** The bounce `Agents tab filter hides it — showing Artifacts ▸ Agent` is the design confessing that the destination should have been the Agents tab all along.
- **Dismissed and historical runs belong in the agent product**, not next to Stitches and Beads. Artifacts already defaults to Stitch. Agent as digit `1` of a tab that opens on pane `2` is a leftover of "every durable kind gets a pane."
- **The query language is the right finder's UI.** `revivable:true AND project:sase AND role:code` is the flagship gesture of the catalog. Putting that bar on the Agents tab is more discoverable than a second top-level tab.
- **Local-ever + current-project published is a coherent *reachability* rule** once it is implemented as a default History *scope*, not a default *list*.

### 4.2 What is wrong if taken literally

**"Any agent ever" as the Agents-tab contents.** The working tree, decks, unread jumps, `,j`/`,J`, tribes, presentation tabs, and j/k performance budget are built for an inbox of hundreds, not thousands. `tui_perf.md` forbids O(archive) first paint. Full-tree rebuilds are the most expensive UI operation. Mixing dismissed/thin/sidecar rows into clan folds would also break container status derivation (a clan with one running member shows that member's status).

**Treating sidecar-published agents as the same kind of row as local runs.** A sidecar page is a snapshot document: prompt, meta, optional chat, commits JSON. It has no PID, no workspace, no live decks, no kill. The import path that used to materialize remote runs locally was deleted on purpose. "Accessible" for those rows means **open the published page**, not **rehydrate an Agent object into the tree**.

**Assuming one query profile already covers both corpora.** The grammar is shared; the field sets and the *meaning of `tribe`* are not. A naive merge of schemas will make `tribe:epic` and `tribe:@review` collide, and will make `unread:true` silently match nothing in History.

**Deleting catalog capability along with the pane.** Revival search, `linked:`/`relation:`/`artifact:`, thin name-only rows, Session/State/Project grouping, and `sase agent search` are load-bearing. The pane is the TUI front-end of that catalog. Moving the front-end is the request. Deleting the catalog is not.

### 4.3 The Artifacts-tab consistency argument is weaker than it looks

Yes, an agent is an artifact (`agent:<name>`). Beads, stitches, patches, and files are too, and they stay on Artifacts because that tab is the **cross-kind catalog** with a shared project scope, relation rail, `limit:`, and persistent filter chrome.

Agents are the exception: they are also the thing the default tab *operates*. The link engine already special-cases `agent:` to leave Artifacts. Files `a` already leaves Artifacts. Keeping a second agent list "for catalog consistency" preserves a chrome pattern at the cost of a split mental model.

Cross-kind `$` from a stitch `produced-by agent:foo` should still work. After the move it should land on the Agents tab's History lens when the working set misses, using the same reveal engine the live tab already has.

---

## 5. Requirement adjustments (called out)

These change the request. They are justified by the measurements and the existing contracts.

### A. Reachable, not listed

**Adjust:** "any agent ever run locally or published to the current project's sidecar" means those rows can be found and opened from the Agents tab. It does **not** mean they occupy the default tree.

Default Agents-tab contents stay the working set (running + bounded recent + unread). History is opt-in via query or an explicit lens switch.

### B. Split the pane move from the sidecar expansion

**Adjust:** Epic 1 relocates the existing local catalog (registry + artifact index + dismissed archive) onto the Agents tab and retires the Artifacts pane. Epic 2 adds **read-only** History rows sourced from the current project's agents sidecar.

Do not spine History on sidecar pages in epic 1. The August plan's reasons still hold: lag, absence, and incomplete coverage of `agent:` refs. Sidecar rows are an origin overlay, not a replacement spine.

### C. Sidecar rows stay documents

**Adjust:** Published-only agents (no local artifacts, no dismissed bundle) are inspectable and copyable. They are not killable, not revivable, not deck-complete, and not imported. Opening one shows the sidecar page (prompt / chat.md / snapshot) in the existing deck chrome or the preview reader. This respects `agents-sync-publish-only`.

### D. Default History scope is a union of two *filters*, not two *universes*

**Adjust:** History's default constraint is:

```text
machine:here OR project:<current>
```

interpreted as:

- local archive rows whose origin machine is this host (all local projects), **or**
- rows that belong to the current project (local plus sidecar-published)

Widen with query (`project:bob`, no `machine:` bound, `origin:sidecar`). Do not load every project's sidecar, and do not load every other machine's unpublished local disk.

`ace.current_project.seed_agents_query` already exists for the live tab and defaults **off** because that query also drives unread jumps and prospective clans. History seeding can default **on**; Working must stay off unless the user opts in.

### E. One grammar, two field-sets, honest unknown keys

**Adjust:** Keep a single Boolean bar on the Agents tab. Catalog-only keys are legal. Live-only keys are legal. A key that does not apply to the active lens is ignored with the same warning already used for inactive-dialect restored queries. Do not silently reinterpret `tribe:`.

Rename or qualify if needed: live `tribe:` stays user-defined; catalog clan-tribe becomes `clan_tribe:` or stays catalog-only. Colliding keys are worse than a longer name.

### F. Reverse the `agent:` overflow policy

**Adjust:** When the working set or its filter hides an `agent:` target, **rewrite the Agents-tab query into a History identity/context query** (`name:x`, `session:x`, hood `name:x.*`) and switch to the History lens. Stop falling through to Artifacts ▸ Agent.

Keep one `^` history entry and the existing lens-chip / `Ctrl+O` trail. The toast currently used for Artifacts reveals already describes this; point it at Agents.

### G. Keep both revival gestures, on one tab

**Adjust:** `!R` remains saved-group revival (Working). `w` moves with the catalog onto History. Do not make `w` on a running row mean revive. Files `a` keeps revive-then-jump, now landing in Working after a successful revive.

### H. Do not make History rows into live sase nodes by default

**Adjust:** Glossary: a sase node is an Agents-tab tree row (clan, agent, turn, step, named proc). Catalog rows today are Artifacts nav items, not nodes. History can present as a **list with grouping banners** (the pane we already have) inside the Agents tab, or as a distinct History nav section. Promoting every registry name to a foldable tree node is a model change with no payoff for thin and sidecar rows.

Revive is the promotion: a successful `w` inserts a real node into Working.

### I. Digit strip and default Artifacts landing

**Adjust:** After removal, Stitch becomes digit `1` (it is already the default pane). Remap help, command palette `show_artifacts_agents`, copy-group `artifacts_agents`, and golden screenshots. Persist a migration of saved Artifacts sub-tab `agents` → Agents History lens, the way `chats` already redirects to Stitch.

---

## 6. UX alternatives considered

| Option | Sketch | Verdict |
| --- | --- | --- |
| **0. Status quo** | Keep Agent pane; maybe improve the bounce toast | Reject. The split is the problem. |
| **1. Naive tree union** | Load every local + sidecar agent into the Agents tree | Reject. 14×–50× inbox, perf contract, clan status lies, decks empty on thin rows. |
| **2. Query-driven archive inside the same tree** | Empty `/` is Working; `state:dismissed` hydrates catalog rows into the tree | Tempting, mixed. Mixing archive rows into live folds is the failure mode. Query as *switch*, not as *insert*. |
| **3. History lens (recommended)** | Agents tab grows Working / History. History *is* today's Agent pane chrome, hosted on the default tab. Query keys can auto-switch. | Accept. |
| **4. History as a presentation `agent_tab`** | A `history` tab beside `main` / machine tabs | Reject. `%tab` is launch placement of live roots. Archive rows have no presentation root. Overloads a just-landed concept. |
| **5. Extend Node Finder (`"`)** | Finder lists dismissed + sidecar too | Partial. Finder is a jump modal over the **loaded tree**. Archive search needs grouping, `limit:`, revive, relations, and a persistent result list. Finder can later include History hits as a second section; it cannot replace the catalog. |
| **6. Keep the pane, move only `$` overflow onto Agents** | Smallest code change | Reject as the end state. Users still have two Agent lists. Acceptable only as an intermediate behind a flag. |
| **7. Artifacts keeps Agent as a thin alias** | Pane remains, always redirects | Reject. Extra chrome for a redirect. |

Option 3 is the one I would actually ship.

---

## 7. Recommended solution

### 7.1 One sentence

**Retire Artifacts ▸ Agent. Put that pane's catalog, query, grouping, relations, and `w` revive on the Agents tab as a History lens. Leave the Working lens as today's control room. Make every `agent:` jump land there. Add sidecar-published current-project rows later, as read-only History origin, not as imported live agents.**

### 7.2 Working lens (default, unchanged job)

Unchanged from today:

- Tree of running, queued, waiting, and bounded recent completed agents
- Decks and cards (Main / Files / Tools / FINAL)
- Tribes, presentation tabs, folds, machine grouping
- `agents-live` fields including `unread`, `pinned`, `needs`, `tab`, `machine:here`
- `,j` / `,J` / `,u` on loaded terminal rows
- `!R` saved-group revival
- First paint bounded; no O(archive) on the pump

Header chip: `Working` (or omitted when History has never been used this session).

### 7.3 History lens (the relocated Agent pane)

Visual: the Artifacts Agent pane, hosted in the Agents tab's node-panel slot (list + grouping banners + relation rail). Detail uses the existing catalog detail for thin/sidecar rows, and the existing decks when a local artifact dir or bundle can fill them.

Chrome that moves with it:

- Persistent Boolean filter row (History keeps the idle bar; Working keeps auto-hide)
- `limit:` + `Ctrl+J`/`Ctrl+K`
- `o`/`O` Session / State / Project grouping (Working keeps its own grouping cycle)
- `w` revive
- `m`/`u` marks
- `%` copy-as (reference, name, chat, prompt, json, handoff)
- `.` relation rail (session, clan, parent, retry, typed artifact links)
- Project scope: History honors the Agents header / a History-local scope control. Do not steal Working's `p` (deck picker). Use a History-scoped `P` or the command palette for project scope.

Default History query:

```text
limit:<ace.page_size>
```

plus the scope in §5.D applied as a presentation constraint (chip), not necessarily as tokens the user must delete. Mirror how Artifacts panes seed current project on first open.

Empty state: "No matching history. Working still has the live inbox. `revivable:true` finds restorable dismissed runs."

### 7.4 Switching lenses

Three equivalent doors, one state:

1. **Header chip** `Working | History` (click / a dedicated key). Suggested key: `H` on the Agents tab, if the keymap audit finds it free in that scope; otherwise a leader `,h` is already "run from home" — do not steal it. Palette: `show agents history`.
2. **Query auto-switch.** Committing a catalog-only field (`state:`, `dismissed:`, `revivable:`, `linked:`, `relation:`, `artifact:`) switches to History and evaluates there. Committing a live-only field while in History stays in History and warns that the field does not apply, *unless* the query is otherwise empty of catalog constraints and the user is clearly asking for Working (`unread:true`, `needs:input`). Prefer explicit chip + query over clever heuristics when unsure.
3. **`$` / Files `a` / `agent:` reveal.** Miss in Working → History identity/context query, one `^` restore.

Working and History remember their own query, selection, and grouping. Switching lenses is not a destructive filter on the other corpus. This is the same "per-tab selection/folds" pattern presentation tabs already use.

Node Finder (`"`) stays Working-tree. A later increment can add a History section to it; it is not v1.

### 7.5 Query language in this design

Yes, use it. Precisely:

| User intent | Query | Lens |
| --- | --- | --- |
| Failed Codex this week (history) | `provider:codex AND status:FAILED AND since:7d` | History |
| Restorable dismissed code members on sase | `revivable:true AND project:sase AND role:code` | History |
| This hood, including containers | `name:sase-16n OR name:sase-16n.*` | History (or Working if loaded) |
| Session turns | `session:research.12 AND NOT kind:workflow-child` | History |
| Linked to a plan | `linked:true AND artifact:plan:202608/foo.md` | History |
| Needs me now | `needs:input` | Working |
| Unread completions | `unread:true` | Working |
| Here vs apollo | `machine:here` / `machine:apollo` | Working (live); History once origin is indexed |
| Sidecar-only (epic 2) | `origin:sidecar` | History |

`sase agent search` remains the CLI of History. After epic 1 it is unchanged. After epic 2 it should grow `-o/--origin` and the same default scope as the lens, documented as such — not as "the Artifacts Agent pane."

### 7.6 What the user sees instead of Artifacts ▸ Agent

```text
Agents | Artifacts | Services
Working | History          filter: revivable:true AND project:sase    12/143  [H]
project: sase · machine: here · limit:100

Session  research.m          3
  research.m.grk     agent   DONE    [sase]  ↺ revivable
  research.m.grk--0  member  DONE    [sase]
Session  sase-tj             2
  sase-tj            session dismissed
  sase-tj.5          member  DONE    [sase]  no run data

REFERENCE  agent:bbugyi200.apollo.research.m.grk
STATE      dismissed · revivable
PROMPT     (bounded preview)
CHAT       ~/.sase/chats/…
PAGE       (hosted sidecar URL if published)
```

Working is one keystroke away. Running agents never appear as a 3,000-row list behind the thing you are trying to kill.

### 7.7 Phasing

**Epic 1 — destination unification (the request, adjusted)**

1. Host `ArtifactsAgentsPane` (or its snapshot/query/revival mixins) as the Agents History lens. Do not rewrite the catalog in the same change.
2. Remove Agent from `FIXED_ARTIFACTS_SUBTAB_ORDER`. Remap digits. Migrate persisted `agents` sub-tab.
3. Reverse `agent:` overflow: History identity reveal on the Agents tab; delete `agents_tab_fallback` toast.
4. Move `w`, catalog copy targets, and Agent relation rail with the pane.
5. Keep `sase agent search` as-is.
6. Flag-gate (`beta`) until goldens, j/k benches, and link-follow conformance pass. Artifacts Agent goldens become History goldens; Working goldens must not regress first-paint.

**Epic 2 — sidecar origin (the extra requirement)**

1. Index current-project sidecar `agents/<global-name>/` pages that are not already represented by a registry row.
2. New field `origin:local|sidecar` (and keep `machine:` for local).
3. Read-only row: open page, copy `@agent:<global>`, no `w`.
4. Default scope chip: here ∪ current project.
5. Still no import.

**Non-goals for both epics**

- Rebuilding the Working tree as a catalog
- Re-enabling agents-sync import
- Populating `historically_viewable` / `durably_revivable` / `restartable` as query fields (revive modal already shows them; do not advertise dead keys)
- Making Node Finder the archive UI
- Putting History on a `%tab`

---

## 8. Implementation risks (so the plan is honest)

- **Startup tab complexity.** History must not run the catalog snapshot on Agents first paint. Working paints as today. History loads on first switch, with the same 500-then-extend pattern the pane already uses.
- **Two grouping keymaps.** Working `o`/`O` is the tribe/tab zoom ladder (dynamic tabs research). History `o`/`O` is Session/State/Project. Scope the bindings to the active lens. This is mandatory, not polish.
- **`p` collision.** Working: deck picker. Artifacts: project scope. History needs project scope without stealing decks. Use a different key.
- **`tribe:` collision.** Resolve in the schema before merging bars (adjustment E).
- **Link conformance.** `tests/ace/tui/artifacts_contract/` and link-follow goldens assume pane id `agents` on Artifacts. History must keep a stable identity field `name` so `agent:foo` still compiles. Prefer keeping compiled profile id `agents` for the catalog and `agents-live` for Working, even after the pane moves.
- **Rust core boundary.** Catalog build is Python because the name registry is a Python-owned JSON store (`plan:202608/artifacts_agents_pane.md` §2.5). Query eval already goes through Rust. Epic 1 should not "fix" that. Epic 2's sidecar index *is* a candidate for `sase-core` if a CLI and the TUI must match — `sase agent search` growing sidecar origin is that litmus test.
- **Goldens / screenshots.** Agent is in the Artifacts strip. Removing it shifts every Artifacts micro-tier capture. Budget that as part of epic 1, not cleanup.
- **Thin rows in decks.** Do not mount empty Files/Tools/FINAL decks for "no run data" rows. Catalog detail is the honest UI; decks appear when artifacts exist.

---

## 9. Would I take a different approach?

I would **not** keep Artifacts ▸ Agent as a third place to find agents.

I would **not** implement the request as "the Agents tab lists every local run plus every sidecar page."

I would **not** fold History into `%tab` or into Node Finder as the primary UI.

I **would** treat this as the successor to `sase-tj` + `sase-zg`: the catalog was built as a separate product so the live tab could stay an inbox; the dialect is now shared; the remaining mistake is two destinations. History lens on Agents is that successor. Sidecar browsing is a new corpus and a new origin field, scheduled after the move.

If epic 1 slipped, the fallback is option 6 (only reverse `$` overflow onto a still-existing pane). That is a patch, not the product.

---

## 10. Recommended solution (restated)

**Ship a History lens on the Agents tab, retire Artifacts ▸ Agent, and keep the working tree as an inbox.**

- Use the existing Boolean agent query language as History search (`sase agent search` / catalog profile), with live fields remaining on Working.
- Make every agent that ever ran **on this machine** findable in History via the name registry + artifact index + dismissed archive (the catalog we already have).
- Make current-project **sidecar-published** agents findable in a follow-up epic as read-only `origin:sidecar` rows. Do not import them.
- Default History scope: this machine ∪ current project. Default Working contents: unchanged.
- `agent:` links that miss Working rewrite into History on the Agents tab. They never bounce to Artifacts.

That is the integration the request is reaching for. The list union it literally describes would make the default tab worse at the job it already does well.

---

## Sources

- `plan:202608/artifacts_agents_pane.md` (epic `sase-tj`) — original two-product split, registry spine, sidecar rejection, successor-epic note
- `docs/ace.md` — Agent Pane, Agent Search, Link Jumps, Agent Revival, tab system
- `docs/query_language.md` — Boolean vs flat dialects; live vs catalog field split
- `docs/agents_sidecar.md` — publish-only hood snapshots; `@agent:` pages
- `docs/cli.md` — `sase agent list` vs `sase agent search`
- `src/sase/agents/catalog/_build.py`, `_models.py`, `_sources.py`
- `src/sase/ace/query_profile/profiles/_agents.py`, `_agents_live.py`, `_agents_shared.py`
- `src/sase/ace/tui/models/_agent_loader_artifacts.py`, `agent_live_query.py`, `agent_live_query_pushdown.py`
- `src/sase/ace/tui/widgets/artifacts/agents_pane.py`, `agents_data.py`, `agents_list.py`, `agents_revival.py`, `agents_detail.py`
- `src/sase/ace/tui/actions/_link_follow_targets.py`, `_link_follow_toast.py`
- `src/sase/ace/tui/_artifact_tab_model.py` — fixed pane order, Stitch default
- Decision `agents-sync-publish-only`; glossary strands Agent Tab, Artifact, Sase Node, Nav Section, Current Project
- Live: `sase agent index status` (239 visible / 3438 dismissed / 378 hidden); `sase agent search -l 0` (1456 rows)
- `sase/memory/tui_perf.md` rules 5, 6, 9
- Prior independent research used only as context, not as this swarm's peers: Agents-tab Node Finder (dismissed ≠ finder target); agents-across-machines (one operational list, bounded history); dynamic Agents tabs (`agent_tab` is presentation placement)
