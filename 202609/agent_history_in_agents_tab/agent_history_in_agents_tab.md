# Retiring Artifacts ▸ Agent: one agent home with an explicit history scope

**Consolidated report** · 2026-09-28 · lead researcher, measured on `apollo`

**Inputs:** five independent reports in this directory (`__cdx`, `__cld`, `__grk`,
`__mus`, `__gem`), plus the lead's own checks of the code, local stores, and the
`gh_sase-org__sase` agents sidecar clone. Anything marked **[lead]** is new in this
report, or corrects a claim in one of the five.

**The request:** delete the Artifacts tab's **Agent** sub-tab and move its job into
the top-level **Agents** tab. Make every agent that ever ran on this machine, or was
published to the current project's agents sidecar, reachable there. Use the agent query
language if there is one. Critique the plan, adjust the requirements where that is
justified, and recommend a solution.

---

## 1. Verdict

**Do it.** Frame it as *"the Agents tab gets a history scope,"* not *"the Agents tab
lists every agent."* All five researchers reached this conclusion independently, and my
own checks back it up.

- **The goal is right.** Today an agent has two homes, and which one you use depends on
  hidden state: whether the agent was dismissed or filtered out. The code admits this.
  When `agent:` link-follow can't find a row, it shows the toast *"Agents tab filter
  hides it — showing Artifacts ▸ Agent."* The Agents tab's own **Custom revival
  search** (`!R`) just jumps to the pane.
- **The pane is the weaker viewer.** Its detail panel shows only metadata: a prompt cut
  off at 4,000 characters, the chat *path*, and no reply, diff, or tool content.
  Reading an old agent in the good viewer (the Agents decks) currently means
  **reviving it first**. The biggest user-facing win here is **read without revive**.
- **The literal wording would break the Agents tab.** "Every agent accessible" must mean
  *searchable and revealable*, not *listed by default*. On apollo, the working inbox is
  228 rows. There are 3,438 dismissed identities in the local index and 14,734
  published runs in the sidecar. The default view must stay an inbox.
- **There is already an agent query language.** It is one Boolean grammar with two
  profiles: `agents-live` for the Agents tab, and `agents` for the pane and
  `sase agent search`. What the Agents tab lacks is a **scope**, not a language.
- **Sidecar history is a second project, and its data isn't ready to show as-is.**
  - The pane never covered sidecar rows, so retiring it doesn't depend on them.
  - Every non-terminal state in the sidecar is stale.
  - 221 runs are published twice under different owner names.

---

## 2. What exists today (verified)

| Surface | Job | Rows | Query profile | Notable |
| --- | --- | --- | --- | --- |
| **Agents tab** | Live control room: attention, unread, decks, tribes, agent tabs, folds | Full `Agent` objects in a session/clan tree; bounded tiers (1,000 active / 2,000 visible completed) plus a background full-history reconcile | `agents-live` (Rust-evaluated; SQLite pushdown for index-answerable terms; `query_incomplete` → quiet reconcile) | Excludes dismissed rows by construction. `!R` revives saved groups. Its custom search opens the pane. |
| **Artifacts ▸ Agent** | Historical catalog: find, inspect, revive, resolve `agent:` refs | One lightweight `AgentCatalogRow` per name-registry entry, enriched from the artifact index and dismissed-bundle summaries. First paint 500 rows, then the rest off-thread. | `agents` (catalog fields, host-owned `limit:`) | `w` revive, Session/State/Project grouping, relation rail, `%` copy. Metadata-only detail. Local only, no sidecar reader. |
| **`sase agent search`** | CLI for the catalog | Same snapshot | `agents` | Implicitly adds `NOT hidden:true AND NOT kind:workflow-child` unless the query mentions them (`_presentation_scoped_query`) |
| **Agents sidecar** | Publish-only project record | Owner-sharded `users/<u>/machines/<m>/hoods/<h>/snapshot.json` plus derived `agents/<global-name>/` pages | none | Hidden sidecar role, explicitly **excluded from auto-sync** (`HIDDEN_SIDECAR_ROLES`). The clone only moves when this machine publishes. |

**How the fields differ between profiles:**

- **Only in `agents`:** `state`, `dismissed`, `revivable`, `historically_viewable`,
  `durably_revivable`, `restartable`, `linked`, `relation`, `artifact`, `parent`,
  `label`, plus `limit:`.
- **Only in `agents-live`:** `machine`, `tribe` (user-defined), `tab`, `pinned`,
  `unread`, `needs`, `source`, `cl`, plus a transcript `text:` haystack.
- **`tribe` means different things in the two profiles** [verified]. In the catalog it
  is the clan tribe enum (`epic|chop|research`); on the live tab it is a user-defined
  tribe.

**The original rationale.** `plan:202608/artifacts_agents_pane.md` called the two
surfaces "different products" and deliberately left migrating the Agents tab onto the
shared dialect as "the natural successor epic." That migration has landed (`sase-zf`),
still behind the default-on `agents_unified_query` sunset flag. **The dialects are now
unified, but there are still two places to go.**

---

## 3. What the lead found that the reports missed or got wrong

1. **[lead] The catalog's artifact-index enrichment is broken on master.** This is why
   the Agent pane and `sase agent search` currently show no status, model, or timing for
   any non-dismissed agent.
   - `src/sase/agents/catalog/_sources.py` returns `{}` unless the index's
     `schema_version` equals the Python constant `AGENT_ARTIFACT_INDEX_SCHEMA_VERSION`.
   - That constant is **34** (`src/sase/core/agent_scan_wire_records.py:29`, and pinned
     by tests). Rust core has written **35** since `sase-core` 75e27f9 (2026-09-27).
     The on-disk index says 35.
   - Result: all 709 "thin" catalog rows on apollo are the 667 `done` rows, the 34
     `active` rows, and 8 dismissed rows. None of them came from the artifact index.
   - **Corrects cdx.** cdx read the 709 thin rows as "reserved but never ran." Most are
     real runs that lost their enrichment.
   - **Supports the core boundary.** A schema constant duplicated in Python drifted
     silently away from Rust. That is exactly the failure the Rust-core boundary rule
     exists to prevent.
   - **Low-usage signal.** Nobody noticed, which matches cld's evidence that the pane is
     barely used: apollo's `~/.sase/query_history.json` has entries for `patches`,
     `stitches`, `agents-live` and `beads`, but none for `agents`.
2. **[lead] 100% of non-terminal published states are stale.** 8,238 published runs say
   `active` or `waiting`, and every one of them started ≥ 2 days ago (athena 8,081,
   apollo 138, kellys_mbp 19). cld's "8,659" was measured from `agents/*/state.json`;
   this figure comes from hood snapshots. Either way, **a non-terminal published state
   carries no liveness information.** cdx's proposed `SNAPSHOT ACTIVE` label would be
   wrong essentially every time.
3. **[lead] Some runs are published twice under different owner names.**
   - 221 `source_run_id`s appear under two owners with different global names. Example:
     `bbugyi200.apollo.bbugyi200.kellys_mbp.sase-10j.1` and
     `bbugyi200.athena.bbugyi200.kellys_mbp.sase-10j.1`.
   - 117 names carry a second owner prefix, and 105 of those originals are also
     published. In 2 cases the copies disagree on state.
   - This looks like pre-deletion imported state being republished by the machine that
     imported it.
   - **Deduplication must key on `source_run_id`, not on global name.** Otherwise
     `in:all` shows duplicates.
4. **[lead] Sidecar timestamps come in mixed formats.** 903 of 14,734 runs use a compact
   `YYYYmmddHHMMSS` `started_at` instead of ISO-8601. The reader has to normalize both.
5. **[lead] Sidecar parse cost, reconciled.**
   - A warm Python `json` parse of all 2,451 snapshots (14,734 runs, 3,197 containers)
     took **0.66 s**.
   - cdx measured 1.06 s with `jq`. cld measured 0.16 s, which was probably one owner or
     a faster parser.
   - The conclusion doesn't change: this is fine on a background worker behind a
     HEAD-keyed cache, and never acceptable on the event loop or the message pump
     (`tui_perf` rules 1, 2, 9, 11).
6. **[lead] The two TUI/CLI disagreements are both confirmed.** The pane's
   `query_rows.agent_query_entry` leaves out `historically_viewable`,
   `durably_revivable` and `restartable`, but `catalog/_query.py` (CLI) fills them in.
   grk is right that those fields match nothing *in the pane*. cld is right that the CLI
   populates them. The same field behaves differently in TUI and CLI.
7. **[lead] The repo already has the building blocks for a scope token.**
   - `limit:` is a **host-owned** token, removed before dialect parse
     (`sase/ace/query/limit_token.py`).
   - Stitches has a `sidecar:true|false` field that widens *which repos are collected*,
     and its reveal engine writes `sidecar:true` into the query to reveal a sidecar
     commit.
   - The Plans pane runs a debounced, last-request-wins deep-archive fetch driven by the
     query.
   - The CLI's `_presentation_scoped_query` is the "implicit default unless mentioned"
     rule.
   - **Naming constraint:** `origin:` already means "how it was produced" in Stitches,
     Files, and Procs, and `source:` means `axe|manual`. Neither should be reused for
     provenance, so grk's `origin:sidecar` is out.
8. **[lead] Key collisions.**
   - `w` on the Agents tab is `reword`, so the pane's `w` revive can't move over as-is.
   - `H` is `hooks_or_collapse_all`, so grk's `H` lens key collides.
   - `p` is `pick_deck`.
   - `o`/`O` are Agents grouping.
   - Leader `,a` is **unbound** (cld is correct).
9. **[lead] Sidecar records carry no agent-tab or installation identity.** Owner
   identity is only `{username, machine_name}`, and the portable `metadata` keys include
   neither `agent_tab` nor an installation id. That confirms cdx. The existing
   `clan_tribe` metadata key supports renaming the catalog's `tribe` field to
   `clan_tribe`.
10. **[lead] Dismissal really does leave run files behind.** The Rust
    `delete_agent_artifacts` binding deletes only loader markers
    (`core_delete_agent_artifact_markers`). The full `Agent` is serialized into the
    dismissed bundle, and run retention defaults to `enabled: false`. **So read without
    revive is feasible.** It still has to degrade gracefully when retention is enabled.

**Measured numbers, reconciled (apollo, 2026-09-28):**

| Corpus | Count | Notes |
| --- | ---: | --- |
| Agents-tab visible inbox (artifact index) | 228 | `sase agent index status` (grk saw 239 earlier the same day) |
| Dismissed identities / hidden terminal rows (index) | 3,438 / 378 | Includes workflow children |
| Name registry entries | 1,662 | Every named top-level dismissed bundle (486) is in the registry. The registry spine is complete for named runs. |
| Catalog default rows (`sase agent search -l 0`) | 1,456 | 34 active · 667 done · 755 dismissed; 747 `revivable:true`; plus 206 workflow children |
| Local archive span | 2026-09-01 → today | Every dismissed bundle is under `202609/` |
| Sidecar runs / hoods / containers | 14,734 / 2,451 / 3,197 | athena 13,620 · apollo 799 · kellys_mbp 315. The sidecar HEAD was committed today. |
| Sidecar runs with `prompt` / `chat` files | 8,630 (59%) / 9,991 (68%) | Many runs have no prompt archive |

On apollo, published history is about 10× the local archive. I couldn't check athena,
where most agents run.

---

## 4. Where the researchers disagreed, and how I resolved it

| Question | Positions | Resolution |
| --- | --- | --- |
| **Where do history rows appear?** | **mus, grk:** move the pane widget into the Agents tab as a History lens. **cld:** "ghost nodes" inside the existing tree and tribe panels, read in the real decks. **cdx:** a mode of the Agents view that suspends the tab strip and tribes and shows one merged panel. **gem:** a `[Catalog]` agent tab in `AgentTabStrip`. | **A History mode of the Agents tab** (cdx), with a lightweight results list (reusing the pane's list and grouping code, as mus/grk suggest) and **the real Agents decks for the selected row** (cld's read without revive). **Reject gem's Catalog agent tab:** the glossary says an agent tab is a *presentation-only placement of top-level agents*, and published rows carry no `agent_tab`. **Reject cld's nesting of ghosts inside inbox tribe panels for v1:** it risks full-tree rebuilds, tainted container status, and tab placement for rows that have none. |
| **How is scope chosen?** | **cdx:** host-owned `scope:inbox\|local\|project\|all`. **cld:** `in:` row field with implicit widening. **mus:** Live/History switch with separate profiles. **grk:** Working/History lens, query auto-switches. **gem:** `scope:` inside a merged profile. | **Host-owned `in:` token**, extracted before parse like `limit:`. It picks the *stores to load*, so it is singular and can't be negated. I chose `in:` over `scope:` because Artifacts already uses "project scope" for something else. The Gmail-style implicit widening follows cld and the CLI precedent. The scope always shows in the header. A key cycles it. |
| **One profile or two?** | **mus:** keep both and switch the bar. **grk:** one bar, both field sets, warn on fields that don't apply. **cld, cdx, gem:** converge. | **Converge on one Agents schema.** Add the catalog lifecycle and link fields to `agents-live`, and rename the catalog's `tribe` to `clan_tribe`. Keep the `agents` profile only until the CLI moves over. Fields that don't apply to a row are simply absent, and completion warns when they don't apply to the active scope. First finish the `agents_unified_query` sunset so there is only one query path to extend (cdx). |
| **Sidecar in the same epic?** | **cdx, gem:** yes. **cld, grk, mus:** a later epic; cld gates it on a publisher freshness fix. | **Separate, later epic.** The pane never showed sidecar rows. The data-quality issues (§3.2, §3.3) are real. Presentation can be made honest without the fix (`WAS ACTIVE · as of <sidecar HEAD age>`), but the publisher fix is worth doing anyway, because the published pages are misleading too. |
| **Where does sidecar data live locally?** | **gem:** a `sidecar_agents` table in the local artifact DB. **cdx, cld:** a separate cache keyed by HEAD. | **A separate machine-local cache keyed by `(project, sidecar HEAD, schema)`**, never in the artifact index. Mixing published rows into the local index would make them look local and edge toward the import leg that `decisions:agents-sync-publish-only` deleted. gem's path (`agent_artifacts.db`) isn't the real file either. |
| **Rust or Python?** | **cdx:** core-owned unified catalog. **cld:** sidecar reader in core. **grk:** epic 1 stays Python. **mus:** shared semantics in core. | **Split along ownership.** The local catalog builder stays Python for now, because the registry *writer* is Python (the August plan's §2.5 reasoning). The **sidecar reader, the union/dedup/precedence rules, and scope semantics go into `sase-core`**, because `sase agent search` must return what the TUI shows. The §3.1 schema drift shows the cost of duplicated constants. |
| **Thin rows** | **cdx:** hide reservation-only rows. **grk, mus:** keep them; they resolve `agent:` refs. | Keep them resolvable by exact name or link reveal. Hide them from ordinary history results by default, alongside hidden rows and workflow children. **First fix §3.1**, or "thin" will wrongly include most real runs. |
| **Which sidecars?** | **cdx, grk:** current project. **cld:** every enabled project. | **Current project in v1**, as the user asked, with one clone and a clear freshness story. Key the cache per project so adding "all enabled projects with materialized clones" later is purely additive. |
| **Revive a sidecar-only row** | **gem:** synthesize launch inputs from `prompt.md`. **cdx, cld, grk:** read-only; a fork is a later feature. | **Read-only.** "Revive" of a row with no local bundle isn't revival. A later **fork from a published prompt** can start a *new* local agent without importing anything. |
| **Flags** | **cdx:** a single default-on sunset flag at cutover. **cld, grk:** a `beta` epic flag for unfinished phases, then a `sunset` flag for removal. | Follow `sase_flags.md`. Use a `beta` flag **only** as epic scaffolding if a landed phase would expose unfinished History UI, and remove it before the epic lands. Put the pane removal behind a `sunset` flag (default on = pane hidden; Off keeps the pane) until the usual removal evidence exists. |
| **gem's claims** | "Universally perceived as confusing in user testing"; a `Tab` key to switch; a `[Catalog]` count in the strip | No evidence for the user-testing claim. `Tab` and agent-tab placement conflict with existing bindings and glossary terms. gem's point about lightweight rows and its harvester idea hold up. The implementation details do not. |

---

## 5. Critique of the plan as stated

### 5.1 What's right

1. **One home per entity.** Users act on agents as agents. Search, link-follow,
   prompt/chat inspection, revive, retry, and live control belong together.
2. **It deletes a parity tax.** Today there are:
   - two row models;
   - two query profiles that are drifting apart (the `tribe` meaning, the three
     capability fields);
   - two detail renderers;
   - two revive entry points;
   - a link-follow fallback between the two surfaces.

   §3.1 is that drift causing real breakage.
3. **The Artifacts tab gets simpler.** Agent is digit `1` on a strip whose default pane
   is Stitch (`2`). The Agents tab already special-cases `agent:` links, and Files `a`
   already jumps there.
4. **The sidecar adds real coverage.** Only 562 canonical names overlap between the
   local catalog and published runs (cdx). On apollo, most project history exists only
   in the sidecar.
5. **The query language is the right lever,** and it already has completion, history,
   saved slots, and a CLI twin.

### 5.2 What goes wrong if implemented literally

1. **An inbox flood.** Unread jumps, attention counts, `load:`, prospective clans, tab
   counts, `,u`, and `x`/`X`/`s` all key off the loaded list. With history mixed into
   the default view, dismissal (the inbox-zero gesture) stops meaning anything.
2. **Performance breaks.**
   - Building `Agent` objects costs about 2 s per 13k rows.
   - A persisted history query restored at startup must not put archive-sized work in
     front of first paint (rule 9).
   - Transcript `text:` search over tens of thousands of files is out of the question
     until a real full-text index exists.
3. **Published state is not liveness** (§3.2), and published rows can't be placed on
   agent or machine tabs (§3.9).
4. **Duplicates** unless deduplication keys on `source_run_id` (§3.3).
5. **Lost affordances.** The pane owns all of these today:
   - `w` revive and the target of `!R` custom search;
   - Session/State/Project grouping;
   - the relation rail and the `linked:`/`relation:`/`artifact:` facets;
   - `%` copy targets (including the *full* prompt);
   - saved queries;
   - the `agent:` fallback.

   Each one needs a new home or an explicit decision to drop it.
6. **Vocabulary.** The glossary defines an **Agent Node** as the node for a
   *non-dismissed* agent. It lists Artifacts' "Agent" among **Nav Sections**. If history
   rows are shown as agent nodes, a canonical definition changes. Keeping them as
   history rows in their own nav section avoids that. The Nav Section and Nav Item
   strands still need updates through `/sase_memory_write`.

---

## 6. Requirement adjustments (explicit changes to the request)

- **A1 — "Accessible" means reachable by scope, not shown by default.** With no scope,
  the Agents view stays today's inbox, byte for byte. History loads only for an explicit
  scope, a link reveal, or a palette action.
- **A2 — Split the work into two epics.** Epic 1 covers local history, read without
  revive, and retiring the pane. Epic 2 covers published sidecar history. Retiring the
  pane doesn't depend on the sidecar.
- **A3 — Narrow "every agent ever run locally"** to "every locally owned run with
  durable evidence": artifact-index rows and dismissed bundles. Pure registry
  reservations stay resolvable by exact ref but are hidden from ordinary results.
- **A4 — Narrow "every agent on the current project"** to "every validated snapshot
  published to the current project's agents sidecar, as of the local clone's HEAD." The
  UI says "published," not "all project agents." Hoods with no commits are never
  published, and the clone only moves when this machine publishes or an explicit sync
  runs.
- **A5 — Published rows are read-only documents.** You can inspect, copy, link, and use
  them as context. You can't stop, retry, dismiss, revive, move tabs or tribes on, or
  open a workspace for them. There is no import, and `decisions:agents-sync-publish-only`
  stays closed.
- **A6 — History rows are excluded from every operational signal by construction.**
  That covers unread, attention/needs, `load:`, runner slots, prospective clans, bare
  `%wait`, auto-dismiss, bulk `x`/`X`/`s`, and inbox counts.
- **A7 — Keep `sase.agents.catalog` and `sase agent search`.** Delete the pane widget,
  not the catalog. The CLI, the artifact-link outbox drain, and relation lookups all
  depend on it. Give the CLI the same `in:` scope so TUI and CLI stay comparable.
- **A8 — Prerequisite fixes are part of the scope.** Fix the §3.1 schema coupling before
  building on the catalog. Treat the §3.2 and §3.3 sidecar data-quality fixes as
  prerequisites for Epic 2.

---

## 7. Recommended UX

### 7.1 Scope: a host-owned `in:` token

| Value | Stores loaded | Default? |
| --- | --- | --- |
| `in:inbox` | Today's Agents-tab set: local non-dismissed, non-hidden rows plus fleet rows | Yes (implicit) |
| `in:local` | Inbox plus the local archive: dismissed and hidden rows from the catalog | — |
| `in:published` | Current-project sidecar snapshots, merged with local data where the same run exists | — |
| `in:all` | `local` ∪ `published`, deduplicated | — |

**Rules:**

- `in:` is extracted before the dialect parse, like `limit:`. It takes one value, can't
  be negated, and never appears inside an `OR`.
- **Implicit widening** (cld's rule, CLI precedent). A query with no `in:` term runs as
  `in:inbox`.
  - If it mentions a local-archive-only field (`state`, `dismissed`, `revivable`,
    `durably_revivable`, `restartable`, `historically_viewable`), it widens to
    `in:local`.
  - It **never** widens implicitly to published.
- **Provenance** is a separate row facet for filtering *within* a scope.
  - Proposed: `presence:local|published|fleet`, which can repeat.
  - Rejected names: `origin:` and `source:`, which are already taken.
  - Example: published-only runs from other machines are
    `in:all NOT presence:local`.
- **Always visible.** Outside the inbox, the header shows a chip such as
  `⌸ local history · 314 matches` or `⇡ published · sase @ a1b2c3 (2h ago)`. There is
  never hidden state.
- **Shortcut.** `,a` (currently unbound in leader mode) cycles inbox → local → all →
  inbox by rewriting the committed `in:` term through the normal commit path, so `^`
  history still works. Palette: **Agents: browse history**.
- **Per-scope memory.** Leaving history restores the exact inbox query, selection,
  folds, tab, and tribe (cdx). Re-entering history restores the last history query (grk's
  per-lens memory, built on query history).
- **Zero-result hint.** When an inbox query matches nothing, an off-thread count against
  the catalog index shows `0 in inbox · 7 in local history — ,a to include`. This is
  where most people will discover the feature.
- **Saved-query migration.** Existing `agents-live` saved queries stay inbox-scoped.
  Artifacts ▸ Agent saved slots and history move into the Agents namespace with
  `in:local` prepended, so they keep their meaning.

**Examples:**

```text
in:local since:7d project:sase role:code          # what did I dismiss or finish this week?
revivable:true provider:codex status:FAILED       # widens implicitly to in:local
in:all name:"research.12*"                        # every run of that hood, anywhere
in:published machine:athena after:2026-09-01 kind:session
in:local linked:true relation:implements
```

### 7.2 History mode presentation

When the effective scope isn't `inbox`, the Agents tab switches into History mode:

- **Left column.** The tribe panels and the agent-tab strip are replaced by one
  **History** nav section. It is a newest-first list of lightweight rows (the pane's list
  and grouping code, moved out of `widgets/artifacts/`), with Session / Date / State /
  Project / Machine grouping banners. It is not the live fold tree. This avoids
  full-tree rebuilds and keeps history rows out of container status.
- **Row chrome.**
  - Terminal status plus a dim style.
  - Provenance chips: `here`, `published · athena`, `here + published`.
  - Local archived rows show `ARCHIVED`.
  - Non-terminal published rows show **`WAS ACTIVE · as of <HEAD age>`** and never
    `RUNNING` (§3.2).
- **Right side.** The normal Agents decks, **hydrated lazily for the highlighted row
  only**, through the existing detail debouncer:
  - *Local archived:* the `Agent` comes from the dismissed bundle. Reply, context, and
    files come from the retained artifact dir and `~/.sase/chats`. Missing files show
    "not retained" instead of an empty card.
  - *Published:* Main shows the snapshot metadata and its provenance, Reply renders
    `chat.md`, and the prompt comes from `prompt.md`. Files lists the snapshot commits
    and renders diffs when the commits exist locally. Tools and FINAL say "not
    published."
  - *Thin (registry only):* one catalog card (identity, lineage, references). No empty
    decks.

### 7.3 Actions by capability

| Action | Inbox row | Local archived row | Published-only row |
| --- | --- | --- | --- |
| Read in decks | yes | **yes, without reviving** | yes, from sidecar files |
| Copy / follow `agent:` ref | yes | yes | yes (`@agent:` already resolves to the sidecar) |
| Revive | — | **Enter chooser → Revive** (default when `revivable:true`), plus marks with `m`/`u` for bulk | no |
| Stop / retry / answer / kill | when live | no | no |
| Fork into a new local run | existing rules | existing rules (bundle fallback) | later, if restartable. It's a new run, not revival. |
| Move tab / tribe, bulk `x`/`X`/`s` | yes | no | no |

The pane's `w` can't move over unchanged, because `w` is `reword` on the Agents tab.
Revive moves into the Enter chooser (cld). A History-mode-only binding needs a keymap
audit plus `default_config.yml` updates (per the core gotcha). `!R` stays the
saved-group flow. Its **Custom revival search** starts committing
`in:local state:dismissed revivable:true` on the Agents tab instead of opening the pane.

### 7.4 Link follow

`agent:` always targets the Agents tab:

1. If the row is loaded, reveal it as today.
2. Otherwise, resolve the canonical identity against the catalog or sidecar projection.
   Commit `in:<narrowest scope> name:"<canonical>"` and push the previous query onto
   history.
3. Expand only the folds the target needs and select it. Toast: *"Not in inbox — showing
   local history · `^` restores your filter."*

Delete the `agents_tab_fallback` route and its toast. Point
`target_for_ref_kind("agent")` at the Agents tab.

---

## 8. Architecture

### 8.1 Data path

```text
                         ┌─ inbox: existing loader + SQLite pushdown (unchanged)
committed query ─ in: ───┼─ local archive: catalog snapshot (Python) → Rust query index → identities
                         └─ published: sase-core sidecar projection (HEAD-keyed cache) → identities
                                          │
                     sase-core union / dedup / precedence → ordered identities
                                          │
                 hydrate the viewport window only (+ prefetch), then the selected row's decks
```

- **Local archive.** Reuse `build_agent_catalog_snapshot()` and the Rust query index,
  cached by index and registry signatures as the pane does today. Return **identities
  only**. Build `Agent` objects only for the visible window, from the bundle or the
  index row. First fix the §3.1 schema coupling. The durable fix is to get the version
  from the Rust binding or read through a Rust projection instead of a Python
  constant. Make degraded enrichment **visible** instead of silently returning `{}`.
- **Published projection, in `sase-core`.**
  - Read the validated owner manifests plus the hood `snapshot.json` files, never a walk
    of `agents/*`.
  - Normalize both timestamp formats.
  - Store the result in a compact SQLite/index file under machine-local SASE cache
    state, keyed by `(project key, sidecar HEAD, v2 schema, catalog wire version)`.
  - Rebuild off-thread only when HEAD or the schema changes.
  - Prompt, chat, and commits load lazily for the selected row, through the snapshot's
    file locators and digests.
  - The chat-provenance sidecar cache (`history/chat_catalog_provenance/sidecars.py`)
    is the precedent for keying by HEAD.
- **Dedup and precedence, in `sase-core`.** Key on `source_run_id`, falling back to the
  canonical global name only for containers and thin rows. Precedence:
  **live/fleet observation > local durable data > published snapshot**. The losing
  source stays as a provenance entry and a fallback locator. When sources disagree,
  record a diagnostic instead of silently blending the fields. For re-prefixed
  republished runs (§3.3), prefer the owner whose name isn't re-prefixed.
- **Startup.** If the restored committed query has a non-inbox scope, paint the inbox
  first, then fill in history in the background. Use the existing "loading history…"
  header in the `query_incomplete` style. Each new field declares either pushdown or
  `KNOWN_FALLBACK_FIELDS` (the coverage test enforces this).
- **Freshness.** No sidecar git subprocess, JSON parse, or stat walk ever runs on the
  event loop, the message pump, or a keystroke path. Idle ticks compare a stat-only HEAD
  token. Network pulls happen only through the Refresh panel's explicit full-history or
  **Sync agents** action (run as a durable proc) or a low-cadence routine job. The
  sidecar is deliberately excluded from generic auto-sync, so leave that rule alone.

### 8.2 Query schema and CLI

- Finish the `agents_unified_query` sunset first (delete the legacy
  `src/sase/ace/agent_query/` branch) so there is only one query path to extend.
- Add to `agents-live`:
  - the lifecycle fields: `state`, `dismissed`, `revivable`, and the three capability
    fields, now actually populated;
  - the link facets: `linked`, `relation`, `artifact`;
  - `parent`, `presence`, `clan_tribe`;
  - host-owned `in:`.
- `sase agent search` gains `in:` (default `local`, to stay compatible) and requires a
  resolvable current project for `published` and `all`. TUI and CLI must return the same
  ordered identities for the same scope and query. That is the headless correctness
  oracle.
- Retire the separate `agents` profile once the CLI uses the unified schema.

---

## 9. Phased plan

| # | Phase | Size | Depends on |
| --- | --- | --- | --- |
| **P0a** | **Catalog schema coupling fix.** Make the catalog accept the current index schema, read the version from the binding, and surface degraded enrichment. This should land now, independently. | S | — |
| **P0b** | **Published-state freshness.** Republish a hood's terminal state when each run ends, or run a scheduled full reconciliation; backfill the 8.2k stale records. **Republication identity:** stop republishing imported runs under a second owner prefix, and repair the 221 duplicate `source_run_id`s. | M | — |
| P1 | **Dialect.** Finish the `agents_unified_query` sunset. Port the catalog fields into `agents-live`, rename `tribe` → `clan_tribe` on the catalog side, add `presence`, host-owned `in:` with implicit widening, pushdown/fallback coverage, and `sase agent search` parity. | M | P0a |
| P2 | **Local history mode.** Catalog-corpus evaluation to identities, windowed hydration, the History nav section and grouping, ghost styling, A6 exclusions, read without revive in the decks, and the startup rule. | L | P1 |
| P3 | **Actions and navigation.** Revive in the Enter chooser, bulk revive of marked rows, the `!R` custom search retarget, `%` copy parity (full prompt), the `agent:` reveal retarget, `,a`, the zero-result hint, and saved-query migration. | M | P2 |
| P4 | **Retire the pane.** Behind a `sunset` flag, delete the Artifacts ▸ Agent widgets, actions, descriptor, bindings (`default_config.yml`), docs (`docs/ace.md` Agent Pane, `artifacts_pane_contract.md`), and goldens. Renumber the Artifacts digits (Stitch becomes `1`). Add `LEGACY_ARTIFACTS_SUBTABS["agents"] → "stitches"`, following the Chats precedent. Update the glossary Nav Section and Nav Item strands. | M | P3 |
| P5 | **Published history.** Rust sidecar projection, `source_run_id` dedup, `in:published`/`in:all`, `WAS ACTIVE` presentation, published decks, and the explicit pull policy. | L | P0b, P2 |
| P6 | *(Optional)* **Full-text history search.** A persistent transcript index; an empty `dismissed_bundle_search_fts` table and `chats_catalog` already exist as starting points. This unlocks `text:` outside the inbox. | L | P2 |

P1–P4 form one epic ("History scope on the Agents tab; retire Artifacts ▸ Agent").
P0b and P5 form a second ("Published agent history"). P0a is a standalone bug fix.

---

## 10. Acceptance criteria that matter

- First paint and idle refresh of the no-query Agents view do no archive-scaled or
  sidecar-scaled work, and the inbox, tab, and tribe layout is visually unchanged.
- j/k p95 stays under 16 ms with a history scope active.
- History rows never affect unread, attention, `load:`, clans, or bulk actions.
- A dismissed agent's reply and diffs can be read without reviving it.
- An `agent:` target outside the inbox, whether local or published, is revealed on the
  Agents tab without opening Artifacts and without creating any local agent state.
- Overlapping local and published runs produce exactly one row each, keyed by
  `source_run_id`.
- A non-terminal published state never renders as live and never enables a mutation.
- A missing, stale, dirty, or malformed sidecar degrades visibly and never hides local
  history.
- `sase agent search` and the TUI return the same ordered identities for the same `in:`
  and query.
- The pane isn't deleted until revive, copy, relations, saved queries, and link
  conformance all have parity tests.

---

## 11. Open questions for the owner

1. **Keyword:** `in:` (recommended; avoids clashing with Artifacts "project scope") or
   `scope:`? Pick one and never alias it.
2. **Hidden, non-dismissed rows:** should they count as inbox or local history? Hidden
   rows that fail may not be auto-dismissed.
3. **Athena usage:** check `~/.sase/query_history.json` on athena for an `agents`
   namespace. If the pane is used heavily there, the saved-query migration in P3 matters
   more.
4. **Sidecar scope beyond the current project:** is it wanted later? The cache design
   allows it either way.

---

## 12. Recommended solution

**Retire Artifacts ▸ Agent by giving the Agents tab an explicit, query-driven history
scope. Don't turn the inbox into an archive.**

1. **Fix the catalog's index-schema coupling now (P0a).** The pane and
   `sase agent search` are currently losing status, model, and timing for every
   non-dismissed agent.
2. **Add the scope to the existing query language.** Add host-owned
   `in:inbox|local|published|all` to the Agents tab's query language. `inbox` is the
   implicit default, and the scope widens to `local` when an archive field is mentioned.
   Port the catalog's lifecycle and link fields into one Agents schema, rename the
   catalog's `tribe` to `clan_tribe`, and give `sase agent search` the same token. The
   header always shows the effective scope, and `,a` cycles it.
3. **Show history in a History mode, not in the live tree.** Outside the inbox, the
   Agents tab shows one History list of lightweight rows with provenance chips. The
   selected row opens in the **real Agents decks**, loaded lazily from the dismissed
   bundle and the retained files, so you can **read without reviving**. History rows
   never feed operational signals. Revive moves into the Enter chooser. `agent:` links
   and `!R` custom search land here.
4. **Retire the pane behind a `sunset` flag once parity tests pass.** Keep the catalog
   package and CLI, migrate saved queries and persisted sub-tab state, and update the
   glossary.
5. **Deliver published sidecar history as a second epic.** It is a read-only
   `in:published` source built on a `sase-core` projection of hood snapshots, cached by
   sidecar HEAD, deduplicated by `source_run_id`, and pulled only by explicit action.
   Ship it after the publisher stops freezing runs at `active` and stops republishing
   imported runs under a second owner. Published rows are documents you can read and
   link, never imported agents. That keeps the publish-only decision closed.

This reaches the end state you described: one place for agents, where any local or
published run can be found with the query language. It does so without slowing the
default view, without showing stale published state as live, and without losing any
workflow the pane supports today.

---

## Sources

- **Peer reports (this directory):**
  - `__cdx`: core catalog, `scope:` token, provenance and capabilities, rollout
  - `__cld`: `in:` scope, ghost nodes, read without revive, freshness gate
  - `__grk`: destination unification, History lens, requirement adjustments A–I
  - `__mus`: Live/History switch, affordance inventory, migration checklist
  - `__gem`: lightweight-row and harvester ideas, and the rejected `[Catalog]` tab
- **Plans and decisions:** `plan:202608/artifacts_agents_pane.md` (§1, §1.1, §2.5
  promotion trigger); `decisions:agents-sync-publish-only`.
- **Memory:** `sase_flags.md`, `tui_perf.md`, and the glossary strands Agent Node,
  Agent Tab, and Nav Section.
- **Code checked by the lead:**
  - `src/sase/agents/catalog/_sources.py`
  - `src/sase/core/agent_scan_wire_records.py:29`
  - `sase-core` `agent_scan/index/index_wire.rs:4`
  - `src/sase/agents/cli_search.py` (`_presentation_scoped_query`)
  - `src/sase/ace/tui/widgets/artifacts/query_rows.py` and `agents_detail.py`
    (`_PROMPT_PREVIEW_CHARS = 4000`)
  - `src/sase/ace/tui/actions/link_follow.py` and `_link_follow_toast.py`
  - `src/sase/ace/tui/actions/agents/_revive_flow.py` (`_open_custom_revival_search`)
  - `src/sase/ace/tui/_artifact_tab_model.py`
  - `src/sase/ace/query/limit_token.py`
  - `src/sase/ace/query_profile/profiles/{_agents,_agents_live,_stitches,_files,_procs}.py`
  - `src/sase/ace/tui/widgets/artifacts/plans_deep_archive.py`
  - `src/sase/_sidecar_auto_sync.py` and `_linked_repo_config.py`
    (`HIDDEN_SIDECAR_ROLES`)
  - `src/sase/ace/tui/actions/agents/_killing_utils.py` and the `sase-core`
    `agent_custody` delete binding
  - `src/sase/default_config.yml` (keymaps, retention)
  - `src/sase/feature_flags/registry.py`
- **Live measurements on apollo, 2026-09-28:**
  - `sase agent index status` and `sase agent search -l 0 -j`
  - the dismissed-bundle index and name registry
  - a Python parse of all 2,451 hood snapshots in the `gh_sase-org__sase` agents
    sidecar clone
