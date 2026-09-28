# Retiring Artifacts ▸ Agent: Give the Agents Tab a History Scope

_Researcher: cld · 2026-09-28 · measured on `apollo`_

## TL;DR

- **The goal is right: retire the pane.** Agents should have one home, and the Agents tab
  already has the better viewer. The Artifacts ▸ Agent pane is a second agent list with its
  own row model, query profile, revive key and link-follow fallback. Its detail panel shows
  only metadata: no reply, no chat content, and a prompt cut off at 4,000 characters. On the
  Agents tab, reading an old agent's reply today means **reviving** it first, which changes
  state just to look at something.
- **The request is really two projects.** They have very different risk, so they should
  ship separately:
  1. **Local history.** The Agents tab already shows every local agent that is not
     dismissed or hidden. The only local gap is **dismissed and hidden agents**: 755 of
     1,456 catalog rows on apollo. This is a relocation of a feature that already exists,
     and it can ship now.
  2. **Published (sidecar) history.** This is a new capability, and the pane never had it.
     On apollo the `sase` agents sidecar holds 15,457 run records: 14,306 from athena, 836
     from apollo and 315 from kellys_mbp. That is about 10× the local corpus. The data is
     **not yet trustworthy**:
     - 8,659 records still say `active` or `waiting` even though they started more than
       two days ago.
     - 35% have no `prompt.md`.
     - Hoods with no commits are never published.
     - The local clone is only refreshed when this machine publishes.

     Ship this second, after a publisher freshness fix.
- **There is already an agent query language, and it is the right UX lever.** Both
  surfaces use the same Boolean grammar (`AND`/`OR`/`NOT`, parentheses, `key:value`,
  time bounds) through two profiles: `agents-live` for the Agents tab and `agents` for the
  pane and `sase agent search`. What the Agents tab lacks is a **scope**, not a language.
- **Recommendation.** Add a Gmail-style scope field to the `agents-live` profile:
  `in:inbox` (the implicit default), `in:archive` (local dismissed/hidden), `in:published`
  (sidecar-only) and `in:*` (all). Show out-of-inbox matches as read-only **ghost nodes**
  that you can inspect with the normal Agents decks without reviving them. Revive moves
  into the Enter chooser. A leader chord cycles the scope as a shortcut for editing the
  query. Then retire the pane behind a `sunset` flag, and keep the catalog package and
  `sase agent search`. The full recommendation is in §8.

---

## 1. What exists today

### 1.1 The Artifacts ▸ Agent pane (epic `sase-tj`, landed 2026-08-25)

**Data source.** The pane uses `sase.agents.catalog.build_agent_catalog_snapshot()`
(`src/sase/agents/catalog/_build.py:41-91`), which is plain Python. It starts from
`~/.sase/agent_name_registry.json` and fills in detail from two places:

- a 19-column projection of `~/.sase/agent_artifact_index.sqlite`;
- the dismissed-bundle summary index, top-level bundles only.

It is **local only**:

- It does not read the agents sidecar or fleet feeds.
- Sibling-machine names show up only as thin "no run data" placeholder rows.

**Rows.** Rows include agents, sessions, clans, workflows and workflow children in every
state (active, done, dismissed, reserved), newest first. First paint shows 500 rows
(`widgets/artifacts/agents_data.py:21`). The full catalog and the Rust query index are
then built off-thread.

**Query.** The Boolean `agents` profile (`query_profile/profiles/_agents.py`) has the
shared fields plus fields only the catalog has:

- `state`, `dismissed`, `revivable`
- `historically_viewable`, `durably_revivable`, `restartable`
- `linked`, `relation`, `artifact`, `parent`, `label`

The pane also supports `limit:` paging (`Ctrl+J`/`Ctrl+K`), saved slots and history.

**Detail panel** (`widgets/artifacts/agents_detail.py:110-199`): reference, identity,
lifecycle, timing, model/provider, lineage, provenance, a **prompt preview capped at
4,000 characters**, and the chat **path**. It never shows the reply, the chat content or
diffs. The published-page URL is computed but never checked to exist.

**What only this pane does:**

1. It lists dismissed and past agents. The Agents tab excludes them by construction.
2. It has the only single-key revive, `w` (`actions/artifacts_agents.py:58-161`). On
   the Agents tab the only revive is the `!R` modal.
3. It is where `agent:` link-follow lands when the Agents tab doesn't have the row
   (`_link_follow_targets.py:228-256` → `relations/artifact_links.py:260`, with the
   toast "Agents tab filter hides it — showing Artifacts ▸ Agent",
   `_link_follow_toast.py:124`).
4. Its relation panel shows session/clan/parent/retry-chain lineage next to typed
   artifact links. The Agents tab covers most of this with its `$` link rail and jump
   panel.

**Signs of low use (circumstantial):**

- The pane shipped with its `%` copy palette unreachable. Every copy target it declared
  was dead code until `sase-tj.10`.
- It also shipped with no `j`/`k` wiring and no PNG coverage (see the `sase-tj` bead
  notes).
- On apollo, `~/.sase/query_history.json` has history for `patches`, `stitches`,
  `agents-live` and `beads`, but **none for `agents`**.

I could not check athena, where most agents run.

**Tests.** About 42 tests are specific to the pane, about 47 cover the shared
catalog/profile/CLI, plus three benchmarks.

**The pane's own design rationale.** The epic's plan
(`plan:202608/artifacts_agents_pane.md` §1.1) said the two surfaces are "different
products": the Agents tab is the live control room, and the pane is the historical
catalog. It explicitly deferred migrating the Agents tab onto the shared dialect. That
migration has since happened (`sase-zf`). The rationale is addressed in §3.3.

### 1.2 The Agents tab

- **What it loads.** The Agents tab loads every active row plus every **non-hidden,
  non-dismissed** completed row. There is a first-paint safety cap
  (`_TIER1_ACTIVE_LIMIT=1000`, `_TIER1_VISIBLE_COMPLETED_LIMIT=2000`), and full history
  reconciles in the background (`docs/ace.md:1768-1789`). So **"every local agent ever
  run" already equals the Agents tab plus the dismissed/hidden archive.**
- **Remote rows** come from the fleet feed. Each owning machine serves "seven days, at
  most 200 completed rows" (`docs/remote_dispatch.md:239-310`). These rows are read-only
  unless a remote capability is advertised (`x`/`R`/`F` route to
  `sase machine agent …`).
- **Query.** This is the `agents-live` Boolean profile (`docs/ace.md:2821-2913`):
  - identity fields: `name`, `session`, `clan`, `project`, `kind`, `role`, `workflow`,
    `model`, `provider`
  - `status`, `attempt`, `hidden`, `attention`, `retry`
  - time and runtime bounds: `since`, `until`, `after`, `before`, `min`, `max`
  - `text` (full transcript haystack, capped at 512 KB per file)
  - operational fields: `cl`, `machine`, `tribe`, `tab`, `pinned`, `unread`, `needs`,
    `source`

  Parsing is in Python. Matching runs through the Rust index. Terms the index can answer
  are pushed down to SQLite (`agent_live_query_pushdown.py`). Anything else marks the
  view `query_incomplete` and triggers a quiet-time full-history reload.
- **Dismissal** (`actions/agents/_killing_utils.py:31-70`, `_dismiss_persistence.py`)
  does four things:
  - adds the identity to `dismissed_agents.json`;
  - writes a **full `Agent` serialization** to `~/.sase/dismissed_bundles/YYYYMM/`;
  - deletes only the loader markers (`done.json`, `workflow_state.json`,
    `prompt_step_*.json`) and the index row;
  - **leaves the rest of the artifact directory and the chat transcript in place.**

  Automatic deletion of old runs is disabled. So a dismissed agent can still be viewed
  after the fact: the bundle is the in-memory `Agent`, and the files are still on disk.
- **Revive**: the `!R` saved-group modal with "Custom revival search…", or `w` on the
  pane. Revival hydrates the row from the bundle.
- **Enter** is a context-aware target chooser (`actions/agents/_agent_enter_action.py:291`).
  That makes it a natural place to add revive and other archive actions.

### 1.3 The agents sidecar (published history)

**Layout.**
- `agents/<user>.<machine>.<name>/{meta.json, state.json, prompt.md?, chat.md?, commits.json, README.md}`
- `users/<u>/machines/<m>/hoods/<hood>/snapshot.json`: one file per hood, carrying every
  run's capabilities, commits, `dismissed_at` and file digests.

Reading every hood snapshot on apollo took **0.16 s** (2,377 athena hoods), so listing
the sidecar is cheap.

**Measured on apollo for `gh_sase-org__sase`:**

| Fact                                                | Value                                                                                          |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Run records                                         | 15,457 (athena 14,306 · apollo 836 · kellys_mbp 315)                                           |
| `state.json` states                                 | active 7,631 · completed 4,600 · failed 1,391 · waiting 1,109 · dismissed 726                  |
| Still `active`/`waiting` but started > 2 days ago   | **8,659** (stale; e.g. `bbugyi200.athena.zz--plan` has said `active` since 2026-08-13)          |
| With `prompt.md` / `chat.md`                        | 9,996 (65%) / 11,129 (72%)                                                                     |
| Local catalog on apollo (`sase agent search -l 0`)  | 1,456 rows: 34 active · 667 done · 755 dismissed (hidden rows and workflow children excluded)  |

**Why the state is stale.** Publication is targeted at commit time: it covers the whole
hood of the agent that is committing, so running siblings are captured mid-run. The
terminal state only gets republished by a later commit in the same hood or by an explicit
`sase agent sync` (`docs/agents_sidecar.md:178-199, 310-335`). Nothing schedules that
reconciliation, so running-state snapshots pile up.

**The sidecar is publish-only.** No TUI surface lists sidecar agents. The local clone is
updated only by `git pull --rebase` inside a publication run; nothing auto-syncs it.
Where the TUI does read the clone today:
- `@agent:` completion (capped at 500);
- `@agent:` resolution, which **only** resolves to the sidecar page;
- link projections.

**Constraint:** `decisions:agents-sync-publish-only` deleted the import leg. A
**read-only** projection that never writes local registry, index or bundle state is not
an import, so it does not reopen that decision. It must be designed so it never turns
into one.

---

## 2. Is there an agent query language?

Yes, and it is already unified at the grammar level. Both profiles share
`profile_reference_boolean.py`: implicit AND, `AND`/`OR`/`NOT`/`!`, parentheses,
`key:value`, `*` globs, `c"…"` case-sensitive strings, date bounds such as `Nd` or
`YYYY-MM-DD`, and duration bounds such as `Nm` or `Nh`. The profiles differ in fields:

| Only in `agents` (catalog / pane / CLI)                                                                                                        | Only in `agents-live` (Agents tab)                                    |
| --------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `state`, `dismissed`, `revivable`, `historically_viewable`, `durably_revivable`, `restartable`, `linked`, `relation`, `artifact`, `parent`, `label`, `limit:` | `machine`, `tab`, `pinned`, `unread`, `needs`, `source`, `cl`, `text` (content haystack) |

The CLI already solves the scope problem in a way the Agents tab can copy.
`sase agent search` silently adds `NOT hidden:true AND NOT kind:workflow-child` unless
the query mentions them (`agents/cli_search.py` `_presentation_scoped_query`). That
"implicit default scope unless mentioned" rule is the model for §5.1.

---

## 3. Critique: is this a good idea?

### 3.1 Yes, on the core

1. **One place to look for an agent.** Today, "where is agent X?" depends on hidden
   state, namely whether X was dismissed. Link-follow even has to explain that with a
   toast. Users shouldn't need to know how dismissal is stored in order to find
   something.
2. **The Agents tab is the better viewer, by a wide margin.** It has the Main deck (Reply,
   Context lanes), Files (diffs), Tools (tool runs, LLM calls), FINAL, and the jump panel
   and link rail. The pane shows paths. Being able to **read without reviving** is the
   single most valuable result of this change.
3. **There is duplication to delete:**
   - two row models (`Agent` vs `AgentCatalogRow`);
   - two query profiles that are drifting apart;
   - two builders for query rows over the same catalog. The pane's `query_rows.py`
     drops three archive-capability fields that `catalog/_query.py` fills in, and
     `docs/ace.md:503-507` still says those fields are never filled in.
   - two revive entry points;
   - a link-follow fallback between them.
4. **The Artifacts tab is about documents and changes** (Patch, Stitch, Bead, Plan,
   Research, File). An agent pane there was always a misfit, and link-follow has already
   moved toward "Agents tab first" (`60b236b5b3`).
5. **The query language is already shared.** What's left is porting fields and adding
   scope, not designing a new language.

### 3.2 Where the plan as stated is risky

1. **"Every agent ever run, accessible" must not mean "visible by default."** The
   Agents tab is an inbox, and dismissal is its inbox-zero gesture. If history leaks
   into the default view, dismissal stops meaning anything. Unread jumps, prospective
   clans, the `load:` gauge, attention counts, tab counts, `,u` and `X` cleanup all key
   off the loaded list (`docs/ace.md:2836-2838` notes that the query "also drives unread
   jumps and prospective clans"). History has to be **opt-in scope**, and history rows
   have to be excluded from every operational signal **by construction**.
2. **Performance.** Building an `Agent` object costs about 2.0 s per 13k rows, plus
   2.9 s for query rows (`docs/perf_runbook.md:142-147`). Athena's archive is about
   12.5k names plus 27k bundles, and the sidecar adds 15k records. The archive can never
   be loaded as `Agent` objects in bulk. Search it with the light catalog rows and the
   Rust index, and **hydrate only the visible window**. A committed query is persisted
   and restored at startup, so a leftover `in:*` must not put archive-sized work in
   front of first paint (TUI perf rule 9).
3. **Sidecar data quality is not ready to show.**
   - 56% of records claim an active or waiting state that has almost certainly ended.
   - Displaying them with live-looking statuses would be actively misleading.
   - Refreshing the clone is a network git operation, which must never be on a
     keystroke path (TUI perf rule 11: a git credential prompt can seize the tty).
4. **Full-text search over history.** The live `text:` haystack reads transcripts
   (512 KB per file). Running that over tens of thousands of archived or published rows
   means tens of thousands of file reads. The pane's plan (§3.6) deliberately avoided
   this. In history scope, free text must stay metadata-only until a real full-text
   index exists.
5. **Vocabulary and glossary.** The glossary defines an **Agent Node** as "the
   Agents-tab node for a _non-dismissed_ sase agent." Showing dismissed agents as nodes
   changes a canonical definition. It also affects Nav Item and Nav Section, which list
   "an agent" entry on the Artifacts tab. These need `/sase_memory_write`. This is a
   real cost of the change.
6. **The catalog is used elsewhere.** `sase agent search` (`agents/cli_search.py`) and
   the artifact-link outbox drain (`sdd/_artifact_link_outbox_drain.py:328-330`) both use
   `sase.agents.catalog`. **Delete the pane widget, not the catalog.**
7. **Rust-core boundary.**
   - The catalog is Python. The pane's plan §2.5 records why and when to promote it:
     the registry's writer is Python.
   - A new sidecar reader is logic the CLI would also need, so the litmus test points to
     `sase-core`.
   - Rust already takes part in v2 publication planning (`plan_agent_publication_batches`,
     `validate_agent_relationship_batch`), and the sidecar has a versioned `schema.json`.
     So a Rust reader does not create the "second schema owner" problem that justified
     keeping the registry reader in Python.

### 3.3 Is the pane's original "two products" argument still valid?

Partly. The **distinction** is valid: an operational inbox and a historical archive are
different jobs. Having **two surfaces** for them no longer is:

- The pane existed partly because the Agents tab had a different, older query dialect.
  That is fixed.
- The pane never showed agent content, so users still had to go to the Agents tab to
  actually read an agent, and reviving was the only way to get there.

The right way to keep the distinction is a **scope inside one surface**, like Gmail's
Inbox vs. All Mail, not a separate tab 1 on another screen.

---

## 4. Requirement adjustments

Each of these changes the request as literally stated.

- **R1. Split local history from published history.** Ship local history plus pane
  retirement first. Published sidecar history is a separate, later epic, gated on R6. The
  pane never covered sidecar agents, so retiring it doesn't depend on them.
- **R2. "Accessible" means reachable through scope, not shown by default.** The default
  Agents view stays the inbox. History rows appear only when the committed query's scope
  includes them.
- **R3. Reading must not require reviving.** Archived rows open in the normal decks,
  read-only. Revive becomes an explicit action on them.
- **R4. History rows are ghosts.** They never feed operational signals: unread,
  attention, `load:`, prospective clans, bare `%wait`, auto-dismiss, `x`/`X`/`s`
  bulk actions, or tab counts for an inbox-scope query.
- **R5. Keep `sase agent search` and the `sase.agents.catalog` package.** Add the same
  scope vocabulary to the CLI so TUI and CLI stay in step. Converging the two profiles
  onto one is a good follow-up, but it isn't required to delete the pane.
- **R6. Fix published-state freshness before showing sidecar rows.** Either republish a
  hood's terminal state when each run finishes, or schedule a periodic full `sase agent
  sync` reconciliation (a routine job). Until then, any sidecar row older than its
  publish time must be labelled with its publish time (`WAS RUNNING · published 6w ago`,
  mirroring the fleet `WAS RUNNING … last seen` precedent), never shown as `RUNNING`.
- **R7. Scope all projects, not just "the current project."** The Agents tab is
  cross-project and narrows with `project:`. The sidecar source should cover the clones
  of every enabled project that has one, and `project:` narrows it. This matches local
  behavior and avoids a special case where the current project behaves differently.
- **R8. No content search in history scope for now.** In archive or published scope,
  free text and `text:` match metadata (name, model, workflow, prompt title). A
  persistent full-text index over transcripts is a separate, optional epic.

---

## 5. UX options considered

| Option                                                                                                  | Summary                                                                                                                                                      | Verdict                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A. Scope field in the query** (`in:inbox` / `in:archive` / `in:published` / `in:*`)                   | The committed query decides the scope; the default is `in:inbox`; a leader chord cycles the scope as a shortcut for editing the query.                         | **Recommended.** Uses machinery that already exists: query history, saved slots, and the header that shows the query. The scope is always visible as text, and the CLI can share it.                                                                                                                                          |
| B. A derived "⌸ History" agent tab                                                                      | Like machine tabs: a derived tab holding every out-of-inbox row.                                                                                              | Rejected. Agent tabs are _presentation-only_ placements, and membership follows the presentation root. A tab based on lifecycle breaks that definition, leaves an agent's authored `%tab:`, multiplies with machine tabs (athena history?), and hides scope in which tab you're on, even though there is only one global query. |
| C. A "history mode" toggle that embeds the old pane widget in the Agents tab                             | Move the widget, keep the catalog row model.                                                                                                                  | Rejected. It keeps two row models and a detail panel that shows only metadata, so it has all the cost and misses the main benefit (reading in the real decks).                                                                                                                                                               |
| D. Keep the pane and improve it                                                                         | Add a real detail view and "open in Agents tab".                                                                                                              | Rejected. It keeps a second agent surface and still needs ghost rows on the Agents tab to open anything without reviving it, so it does most of A's work anyway.                                                                                                                                                              |

---

## 6. Recommended design

### 6.1 Scope model

Add a derived enum row field `in` to `agents-live`:

| Value       | Rows                                                                                                                                 |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `inbox`     | Today's Agents-tab set: local non-dismissed and non-hidden rows, plus fleet rows.                                                     |
| `archive`   | Local rows outside the inbox: dismissed and hidden (from the catalog, backed by bundles).                                            |
| `published` | Sidecar runs that are neither local nor present in the fleet feed. Deduplicated on `canonical_global_name`.                          |

**Implicit scope.** The rule follows `_presentation_scoped_query`:

- A query with no `in:` term runs as `in:inbox AND (…)`.
- If it mentions an archive-only field (`dismissed`, `revivable`, `state`), the implicit
  scope widens to `(in:inbox OR in:archive)`.
- An explicit `in:` is honored exactly. `in:*` means everything.
- Published rows are only ever included explicitly, because they are the remote,
  expensive and lower-trust source.

**Port the catalog's lifecycle fields** into `agents-live`: `state`, `dismissed`,
`revivable`, `historically_viewable`, `durably_revivable`, `restartable`. Also port
`linked`, `relation` and `artifact`, which the link rail already makes meaningful on the
Agents tab. Each new field must declare pushdown or be added to `KNOWN_FALLBACK_FIELDS`;
the coverage test enforces this.

**Show the effective scope.** When the scope is not `inbox`, the Agents header shows a
chip (`⌸ archive`, `⇡ published`, or `∗ all`) next to `filter:`, so there is never
hidden state.

**Examples:**

```text
in:archive since:7d project:sase role:code          # what did I dismiss this week?
revivable:true provider:codex status:FAILED         # implicit local-history scope
in:* name:"research.12*"                             # every run of that hood, anywhere
in:published machine:athena after:2026-09-01 kind:session
in:archive linked:true relation:implements
```

**Shortcut.** A leader chord (proposed `,a` for "archive", which is currently unbound in
`leader_mode`) cycles the scope `inbox → +archive → +published → inbox` by rewriting the
committed query's `in:` term. It goes through the same commit path, so query history
and `^` still work.

**Zero-result hint.** When an inbox-scope query matches 0 rows (or only a few), a cheap
catalog-index count runs off-thread. The header then shows
`0 in inbox · 7 in archive — ,a to include`. This is where most people will discover the
feature.

### 6.2 Ghost nodes (how history rows look)

- **Status overlay.** Archived rows keep their terminal status and add an `ARCHIVED`
  overlay plus a dim style. Published rows show `PUBLISHED`. A published row whose
  published state is non-terminal and older than its publish time shows
  `WAS RUNNING · published <age>` (R6).
- **Placement.**
  - A ghost member of a session or clan that is in the inbox nests inside that
    container, which makes history visible in context.
  - Top-level ghost nodes collect in a trailing `⌸ archived (N)` banner group in each
    tribe panel, so inbox rows stay on top.
  - When the scope is `in:archive` alone, the list shows only ghosts.
  - `BY_DATE` grouping is the natural way to browse history.
- **Tabs.**
  - Ghosts land on the `%tab:` stored with them, so tab membership stays
    presentation-only.
  - With machine tabs on, published rows land on their owner's `⌨ <alias>` tab. The
    fleet key is the installation id and the sidecar key is `user.machine`, so the two
    need a mapping. Owners that aren't enrolled get a derived
    `⌨ <machine> (published)` tab.
- **Exclusions (R4).** Ghosts never count toward or trigger any of these:
  - unread jumps or `,u`;
  - attention and needs;
  - prospective clans or bare `%wait` anchoring;
  - the `load:` gauge or runner slots;
  - auto-dismiss or the self-healing marker deletion;
  - `x`/`X`/`s` bulk actions;
  - the Node Finder's live set, unless the scope includes them.

### 6.3 Data path and performance

1. **Archive corpus.**
   - Use the existing catalog snapshot (about 550 ms per 12.5k names by the benchmark
     budget) and the Rust query index (`compile_corpus_with_profile` /
     `evaluate_many`), cached by index and registry signatures exactly as the pane does
     now.
   - Treat the archive part of a query as a **separate pushdown target**. Inbox terms
     still go through the SQLite pushdown. The archive part is evaluated against the
     catalog corpus and **returns identities only**.
2. **Lazy hydration.**
   - Turn only the newest N matches into `Agent` objects: the viewport, plus prefetch
     reusing `_loading_disk_viewport.py`, with a first page of about 200.
   - Hydrate from the dismissed bundle's full `Agent` serialization, the same path
     revive uses. Fall back to the artifact index row for hidden, non-dismissed rows.
   - Moving focus near the end fetches more, exactly as the inbox viewport does. There
     is no `limit:` token on the Agents tab.
3. **Startup.** If the restored committed query has an archive or published scope,
   paint the inbox part first and fill in the ghost part in the background with the
   existing "loading history…" header, following the `query_incomplete` pattern. First
   paint never waits on archive work (rule 9).
4. **Published corpus.**
   - Build it from `users/*/machines/*/hoods/*/snapshot.json`: 0.16 s to read every
     athena hood cold, much less than opening about 30k `agents/*/*.json` files.
   - Cache it keyed by the clone's `HEAD` ref, a stat-only token (rules 8 and 14).
   - Put the reader in **`sase-core`** behind a thin adapter (§3.2 item 7), so
     `sase agent search --in published` and any web or mobile surface get the same
     rows.
5. **Pulling the clone.** Never on a keystroke or render path. Pull only:
   - on the Refresh panel's **Full history** (`r f`/`,y f`), done as a durable proc;
   - or from a low-cadence routine job.

   The header shows `published history as of <HEAD commit age>`.

### 6.4 The detail deck for a ghost row

- **Archived (local).**
  - The `Agent` comes from the bundle.
  - Reply, Context and Files read from the artifact directory, which remains after
    dismissal, and from `~/.sase/chats`.
  - Missing files degrade to `revival_inputs` and then to "not retained", instead of
    failing the render.
  - The deck header carries a one-line `ARCHIVED · dismissed <age> · revivable` banner.
- **Published.**
  - Main shows `meta.json` and `state.json` with their publish-time provenance.
  - Reply renders `chat.md`, and the prompt comes from `prompt.md`.
  - Files lists `commits.json` and renders diffs through the local project repo when
    the commits are present.
  - Tools and FINAL show "not published".
  - Everything is read-only.

### 6.5 Actions on ghost rows

| Action                      | Archived (local)                                                                                                               | Published                                                                                                                                                                                                                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Enter** (context chooser) | Adds a **Revive** target, the default when `revivable:true`, alongside view chat/prompt. Replaces the pane's `w`.             | View chat/prompt; open the published page.                                                                                                                                                                                                                                        |
| Revive (bulk)               | `m` marks, then revive marked. `!R` stays the saved-group flow.                                                                | Not available (no local bundle).                                                                                                                                                                                                                                                  |
| `F` fork                    | Works today through `find_named_agent`, which falls back to bundles. Switch that fallback from rglob over every bundle to the summary index. | On an enrolled owner: `sase machine agent fork ALIAS AGENT`. **Unverified:** it is documented to find settled rows, but I did not check whether that holds outside the 7-day remote window. Otherwise, a later "fork from published transcript" seeded from `chat.md`. |
| `%` copy                    | Must reach parity with the pane's nine `artifacts_agents` targets: `@` ref, name, link, path, chat, **full** prompt (not truncated), JSON, handoff, snapshot. | `@agent:` ref. It resolves directly, because `@agent:` resolution is already sidecar-backed. Name, link, prompt, chat.                                                                                                                                                             |
| `x` / `X` / `s`             | Disabled (R4).                                                                                                                 | Disabled.                                                                                                                                                                                                                                                                         |

### 6.6 Link-follow

- `agent:` follow first reveals a loaded inbox row, as it does today.
- If the row isn't loaded or is filtered out, it commits `in:* name:"<payload>"` and
  pushes the previous query to history. The toast says "showing archived agent — `^`
  restores your filter". This follows the Node Finder precedent, where jumping to a
  hidden row clears the query.
- `target_for_ref_kind("agent")` (`relations/artifact_links.py:260`) points at the
  Agents tab. The "showing Artifacts ▸ Agent" fallback and its toast are deleted.
- **What published history adds.** On apollo, links to athena agents today land on thin
  "no run data" placeholders. With published history they land on real data.

### 6.7 Retiring the pane

**Delete:**
- `widgets/artifacts/agents_*.py` and `actions/artifacts_agents.py`;
- the `agents` entry in `FIXED_ARTIFACTS_*`, its descriptor, contract adapter and
  description;
- the bindings `agents_next`/`agents_prev`/`agents_revive`, including
  `src/sase/default_config.yml` (the core gotcha);
- the help-modal rows, the `docs/ace.md` "Agent Pane" section (723-761) and its
  cross-references;
- the pane's visual goldens and roughly 42 pane tests.

**Keep:**
- `sase.agents.catalog`;
- the `agents` query profile until the CLI converges on `agents-live` plus `in:`;
- the link-outbox drain's use of the catalog.

**Migrate:**
- Map a persisted Artifacts subtab of `agents` to the default pane through
  `LEGACY_ARTIFACTS_SUBTABS`, the same precedent used when the Chats pane was retired.
- Rewrite saved slots and history in the `agents` namespace into `agents-live` with
  `(in:inbox OR in:archive) AND (…)`.
- Renumber the Artifacts digit shortcuts: Agent is `1` today.
- `sase artifact pane show agents` stops listing the pane; note it in the CHANGELOG.

**Flag.** Gate the removal with a `sunset` flag (default on, meaning the pane is hidden).
The `sase_flags.md` memory note requires one when a user-reaching behavior is deprecated
and the old branch must stay reachable. Create it with `sase flag new`. The removal phase later
deletes the Off branch.

**Memory.** Update the glossary strands Agent Node, Sase Node, Nav Item and Nav Section
(and add "Ghost Node" or "History Scope" if adopted) through `/sase_memory_write`.

---

## 7. Phased plan

| #   | Phase                                                                                                                                                                                                                                                                                                                    | Size | Depends on |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---- | ---------- |
| P0  | **Published-state freshness.** Republish the hood on run termination, or add a routine that runs full reconciliation. Also backfill the 8.6k stale records. This is independent and useful now: the published pages themselves are misleading.                                                                           | M    | —          |
| P1  | **Dialect.** Port the lifecycle and link fields into `agents-live`; add the `in` field, the implicit-scope rule, and pushdown or fallback coverage; add `sase agent search --in` (or the `in:` term) for CLI parity. Behind a `beta` epic flag.                                                                          | M    | —          |
| P2  | **Archive corpus and ghost nodes.** Catalog-corpus evaluation, lazy bundle hydration, the viewport and startup rules, ghost rendering and overlays, the R4 exclusions, and read-only decks.                                                                                                                              | L    | P1         |
| P3  | **Actions and navigation.** Revive in the Enter chooser, bulk revive of marked rows, fork fallback through the summary index, copy parity with the full prompt, link-follow retarget, the `,a` scope cycle, and the zero-result hint.                                                                                    | M    | P2         |
| P4  | **Retire the pane.** Add the `sunset` flag, delete the widget, bindings, config, docs and tests, migrate state and queries, update the glossary. Remove the P1 `beta` flag.                                                                                                                                             | M    | P3         |
| P5  | **Published history.** Rust sidecar reader over hood snapshots, dedup (local > fleet > sidecar), clone-pull policy, `PUBLISHED` / `WAS RUNNING` presentation, published decks, and remote-fork routing.                                                                                                                  | L    | P0, P2     |
| P6  | _(Optional)_ **Full-text history search.** A persistent full-text index over transcripts (`chats_catalog.sqlite` is the starting point), unlocking `text:` in history scope.                                                                                                                                              | L    | P2         |

P1 through P4 make one epic ("History scope on the Agents tab; retire Artifacts ▸ Agent").
P0 and P5 make a second epic ("Published agent history"). P6 is optional and needs its own
justification.

---

## 8. Open questions

1. **Scope keyword.** `in:` follows Gmail and GitHub and is short. The alternative
   `scope:` is more literal. Either works; pick one and never alias.
2. **Hidden, non-dismissed rows.** Hidden rows that succeed are auto-dismissed on load.
   Hidden rows that fail may not be. Confirm they belong in `archive` and not `inbox`.
3. **Workflow children.** The CLI excludes `kind:workflow-child` by default; the archive
   holds about 20k of them on athena. Keep that implicit exclusion in history scope
   unless it is mentioned.
4. **Enrolled-remote fork outside the 7-day window.** Verify whether
   `sase machine agent fork` can reach older settled runs on the owner machine.
5. **Usage on athena.** Check `~/.sase/query_history.json` for an `agents` namespace
   there. If you use the pane heavily on athena, P4's migration of saved queries
   matters more.

---

## 9. Recommended solution

**Do it, but frame it as "the Agents tab gets a history scope," not "the Agents tab shows
every agent."** Concretely:

1. **Add the scope field.** Add `in:inbox | in:archive | in:published | in:*` to the
   existing `agents-live` query dialect. The default is `in:inbox`, applied implicitly
   and widened when an archive field is mentioned, following the
   `sase agent search` precedent. Port the catalog's lifecycle and link fields so every
   pane query has a direct equivalent. The header always shows the effective scope, and
   `,a` cycles it.
2. **Show history as ghost nodes.** History rows are read-only ghost nodes, hydrated
   lazily from dismissed bundles through the catalog's Rust query index, and shown in
   the normal decks. That gives **read without revive**. Ghosts are excluded from every
   operational signal. Revive moves into the Enter chooser.
3. **Retire the pane.** Retire Artifacts ▸ Agent behind a `sunset` flag after step 2
   lands. Keep `sase.agents.catalog` and `sase agent search`, and give the CLI the same
   scope term. Retarget `agent:` link-follow to the Agents tab. Update the glossary.
4. **Treat published history as a second epic.** Put a `sase-core` reader over hood
   snapshots behind the same `in:published` scope. It comes **after** the publisher
   stops leaving thousands of runs frozen at `active`, and it has an explicit, never
   keystroke-driven pull policy. It is read-only by design, so the publish-only decision
   stays closed.

This reaches your end state (one agent surface, where any local or published agent can
be found with the query language) without turning the inbox into an archive, without
putting archive-sized work in front of first paint, and without presenting stale
published state as live.

---

### Appendix: Key references

- Pane: `src/sase/ace/tui/widgets/artifacts/agents_pane.py`, `agents_data.py:21`,
  `agents_detail.py:89-199`, `src/sase/ace/tui/actions/artifacts_agents.py`,
  `_artifact_tab_model.py`, `_artifact_tab_contract_adapters.py:342-448`,
  `docs/ace.md:723-761`.
- Catalog and CLI: `src/sase/agents/catalog/_build.py`, `_sources.py`, `_query.py`,
  `src/sase/agents/cli_search.py` (`_presentation_scoped_query`).
- Profiles: `src/sase/ace/query_profile/profiles/_agents.py`, `_agents_live.py`,
  `_agents_shared.py`; grammar in `src/sase/ace/query/profile_reference_boolean.py`.
- Agents-tab loading: `models/agent_loader.py`, `_agent_loader_artifacts.py:34-35`,
  `agent_live_query_pushdown.py:41`, `actions/agents/_loading_*`,
  `docs/ace.md:1768-1789, 2821-2913`, `docs/perf_runbook.md:85-180`.
- Dismissal and revive: `actions/agents/_killing_utils.py:31-70`,
  `_dismiss_persistence.py`, `_dismiss_memory.py:24`, `docs/ace.md:5469-5515`.
- Link follow: `actions/_link_follow_targets.py:228-256`, `_link_follow_toast.py:124`,
  `relations/artifact_links.py:236-261`.
- Enter chooser: `actions/agents/_agent_enter_action.py:291`.
- Sidecar: `docs/agents_sidecar.md` (§Scope and reconciliation, 178-199; sync, 310-335),
  `src/sase/agents_sync/`, and the `~/.sase/projects/<key>/repos/agents` clone.
- Fleet: `docs/remote_dispatch.md:232-310`, `models/_agent_state_fleet.py`.
- Prior design: `plan:202608/artifacts_agents_pane.md` (§1.1, §2.5, §3.6); beads
  `sase-tj`, `sase-zf`; `decisions:agents-sync-publish-only`.
