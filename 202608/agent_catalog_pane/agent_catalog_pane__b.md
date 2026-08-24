---
create_time: 2026-08-24
updated_time: 2026-08-24
status: research
tags:
  - ace
  - artifacts
  - agents
  - query-language
  - artifact-links
  - revival
  - tui
---

# The Artifacts "Agents" Pane: One Identity Spine, One Dialect, Two Verbs

**Research question.** The `Agents` sub-tab of the ACE `Artifacts` tab is the missing
piece that blocks artifact links from paying off
([`artifact_link_derivation.md`](artifact_link_derivation/artifact_link_derivation.md)
§5, §9 item 13). How should it be implemented — what backs a row, what is its query
dialect, how does revival work from it, and what does it have to do so `agent:` link
edges stop pointing at nothing?

**Scope and evidence.** `sase` at `9abe1967b` (master, clean, `0.16.0+1437`),
`sase-core` via the installed `sase_core_rs` binding, research sidecar at the checkout
opened through `sase repo open`. Every count below was measured on this machine on
2026-08-24 against live stores (`~/.sase/agent_name_registry.json`,
`~/.sase/agent_artifact_index.sqlite`, `~/.sase/dismissed_bundles/index.sqlite`,
`~/.sase/chats_catalog.sqlite`, the agents sidecar clone, and the project's
`artifact-links.json`). Timings are wall-clock from this machine. Where a claim is a
design inference rather than a measurement, it says so.

**Out of scope by the owner's framing:** the artifact-link defect fixes (`sase-t0`,
`sase-t1`, the lossy rebuild, rename following) and the rich per-tab link integration.
§6 states only what the Agents pane must *not* foreclose for those.

---

## Bottom line

**A row is a named agent run, and the row's identity comes from the agent name
registry — not from the artifact index, not from the agents sidecar, and not from the
live Agents tab's in-memory list.**

That single decision resolves most of the design, because it is the only choice that
satisfies all three jobs the pane has to do at once:

| Job | Registry | Artifact index | Dismissed bundles | Agents sidecar |
| --- | ---: | ---: | ---: | ---: |
| Resolve the 55 distinct `agent:` refs in the live link graph | **55/55** | 4/55 | 33/55 | 46/55 |
| Cover every agent that ever ran locally | **12,318** | 8,054 (hot) | 26,657 (runs) | 9,602 (published) |
| Carry the attributes a query language needs | **poor** | rich | rich | thin |

No single store does the job. The registry is the only **complete spine** (98% by raw
key, 100% after normalizing the owner prefix — the one miss is `agent:bbugyi200.athena.002--1`,
whose registry key is the bare local name `002--1`). The artifact index and the dismissed
bundle index are the **attribute sources**, and together they enrich 92.7% of registry
entries. So: **spine from the registry, left-join attributes, degrade a row rather than
drop it.**

Everything else follows:

- **One dialect, authored as an `ArtifactQuerySchema`.** Do not extend
  `sase/ace/agent_query/`; author `agents_query_schema()` in
  `sase/ace/query_profile/profiles.py` and point *both* the new pane and the existing
  Agents tab at it. `agent_query` is a self-declared fork of `ace/query` that already
  invented the typed-key registry the profile system later shipped
  ([`artifacts_query_and_pane_contract.md`](artifacts_query_and_pane_contract/artifacts_query_and_pane_contract.md)
  §L2). Shipping a *third* agent dialect to fix a duplicate dialect problem is the
  single worst outcome available here.
- **Revive stays where it is; the pane gets a second door.** `_do_revive_agent` is an
  `AceApp` mixin method reachable from any widget. The pane calls it. Keep `R` on the
  Agents tab: the saved-group flow is a different, faster gesture than a query.
- **Ship the pane before the link fixes, not after.** Every `agent:` edge already
  resolves to `ArtifactEntryTarget("agents", …)` today and lands nowhere. The pane is
  the consumer that makes fixing the graph worth doing.

The pane is genuinely cheap: the contract, capability, conformance, filter-bar,
saved-query, query-history, relation-panel, and shell machinery are all already
pane-parameterized. **The expensive part is the row model, not the widget.**

---

## 1. What already exists (measured)

### 1.1 The Artifacts pane substrate is fully parameterized

Six panes are configured today — `stitches`, `patches`, `beads`, `ref:plan`,
`ref:research`, `files` (verified via `sase artifact pane show bogus`). A new fixed pane
needs one `_BuiltinAdapter` entry, one `ArtifactQuerySchema`, one pane widget, and one
`_compose_pane` branch. Everything else is derived:

| Machinery | Where | What a new pane gets free |
| --- | --- | --- |
| Capability derivation | `_artifact_tab_contract_rules.py` | `has_inventory + has_fields` ⇒ `QUERY_HISTORY` **and** `SAVED_QUERIES` (verified rules `query_history_from_inventory_and_fields`, `saved_queries_from_inventory_and_fields`) |
| Query dialect | `ace/query_profile/` | tokenizer, parser, canonicalizer, digest, Rust corpus routing |
| Filter bar | `widgets/filter_bar.py` (485 lines) | completion, value hints, highlighting — all read from the profile |
| Saved queries / history | `ace/saved_queries.py`, `ace/query_history.py` | pane-namespaced by pane id, digest-stamped |
| Visual shell | `widgets/artifacts/shell.py` | loading / stale / empty / degraded / results precedence |
| Relations | `_artifact_link_contract.py` | `links` / `linked_by` appended to every built-in adapter automatically |
| Conformance | `tests/ace/tui/artifacts_contract/` | **12** checks auto-parametrize over `resolve_artifacts_subtabs()` |

That last row is worth stating plainly: **the new pane joins the conformance matrix the
moment it appears in `resolve_artifacts_subtabs()`.** Declared actions must be
registered, declared copy targets must be registered, declared relation edges must
resolve, declared keys must resolve to named actions, unavailable actions must carry OFF
verdicts, and the pane must render the shared shell. That is a real implementation
constraint and a real quality floor.

### 1.2 The link graph is already majority-`agent:` and majority-dangling

Live aggregate for `gh_sase-org__sase`, 2026-08-24:

| Measure | Value |
| --- | ---: |
| Total rows | 161 |
| Rows touching an `agent:` ref | **91 (56.5%)** |
| Distinct `agent:` refs | 55 |
| …in bare local form (`agent:0b4`) | **54** |
| …in owner-qualified form (`agent:bbugyi200.athena.002--1`) | 1 |
| Relations on those rows | `read` 90, `cites` 1 |

`_target_for_ref` (`ace/tui/relations/artifact_links.py`) maps every one of them to
`ArtifactEntryTarget("agents", (payload,))`. There is no `agents` pane, so the majority
of the graph resolves to a pane id that does not exist. This is the gap the consolidated
link report flagged as a *known non-goal*, not a regression — but it is now the largest
single reason the graph does not pay for itself.

### 1.3 The identity stores, measured

| Store | Path | Rows | Size | Full read |
| --- | --- | ---: | ---: | ---: |
| Agent name registry | `~/.sase/agent_name_registry.json` | **12,318** | 16 MB | 151 ms |
| Agent artifact index | `~/.sase/agent_artifact_index.sqlite` | 8,054 | 153 MB | 553 ms cold / **49 ms warm** (column projection) |
| Dismissed bundle summaries | `~/.sase/dismissed_bundles/index.sqlite` | **26,657** | 15 MB | **167 ms** |
| Dismissed bundle files | `~/.sase/dismissed_bundles/**/*.json` | 26,657 | — | one file per agent |
| Published agent pages | `…/repos/agents/agents/*/` | 9,602 | — | git sidecar |
| Published family pages | `…/repos/agents/families/*.md` | 1,459 | — | git sidecar |
| Chat transcripts | `~/.sase/chats_catalog.sqlite` | 22,613 | — | plus an `agent-links` generated index |

Two performance facts govern the row model:

1. **Never read `record_json`.** The artifact index's `record_json` column alone is
   **114 MB** across 8,054 rows. A column projection of the 14 useful columns is 49 ms
   warm. The pane must project, never `SELECT *`.
2. **The dismissed bundle summary index is the cheap, complete, query-ready table.**
   26,657 rows in 167 ms, with `agent_name`, `status`, `model`, `llm_provider`,
   `workflow`, `project_file`, `start_time`, `stop_time`, retry lineage, and
   `is_workflow_child` already columnar. Compare with the current custom revival modal,
   which pages 26,657 *JSON files* through `load_dismissed_bundles_page(limit, offset)`
   and can only filter what it has already paged in. **That is the actual defect the
   owner is feeling** when they say the sub-tab "should be much easier to query from."

### 1.4 Registry state distribution

`state` across 12,318 registry entries: `dismissed` 9,120 (74.0%), `done` 2,516 (20.4%),
`active` 682 (5.5%). `reservation_kind`: `claimed` 9,938, `family` 1,734, `clan` 594,
`auto_prefix` 51, `planned_clan` 1. `origin`: `local` 12,217, `import_v2` 101. Project
concentration: `gh_sase-org__sase` 11,439 of 12,318 (92.9%).

Three consequences: the pane is **mostly a dismissed-agent browser** by volume; it must
distinguish *named container* rows (family/clan, 2,328 of them) from *agent run* rows;
and project scoping is nearly a no-op on this machine but is still required for contract
conformance.

### 1.5 The existing dialects

| Dialect | Module | Used by | Shape |
| --- | --- | --- | --- |
| Boolean profile | `ace/query` + `query_profile` | Patches | AND/OR/NOT, parens, sigils, macros, predicates |
| Flat profile | same | Stitches, Beads, Plans, Files, providers, **Procs** | `key:a,b` OR-lists, `-key:x` negation, free text |
| **Agents fork** | `ace/agent_query` (**1,189 LOC**, 6 modules) | Agents tab only | AND/OR/NOT, parens, typed keys, `age>2h` |

`agent_query/tokenizer.py` says in its own docstring that it is "Adapted from
`sase.ace.query.tokenizer`". The prior consolidated report already identified it as the
third language to fold in, and noted that its typed-key registry
(`SUBSTRING_PROPERTY_KEYS` / `ENUM_PROPERTY_KEYS` / `BOOL_PROPERTY_KEYS` /
`DURATION_PROPERTY_KEYS`) is "exactly the vocabulary a profile needs" — most of the
typed-key design was written once, by hand, for the Agents tab.

`Procs` is the load-bearing precedent that a profile dialect does **not** require an
Artifacts pane: `procs_query_schema()` is registered in `pane_registry.py`, compiled by
`ProcQueryFilter` (`ace/tui/_proc_query.py`), and evaluated through
`evaluate_query_for_profile` with a per-row cache and lazy output loading. That is
exactly the shape an Agents dialect should take.

---

## 2. The central choice: what is a row?

Four candidate row sources. Only one survives all the constraints.

### 2.1 Candidate A — the live Agents tab's in-memory agents

**Reject.** Zero extra I/O and perfect fidelity with the Agents tab, but it holds only
the *visible working set*. Revival is impossible from it by construction (dismissed
agents are exactly the ones it excludes), and it resolves 4 of 55 live `agent:` refs.
It also couples an Artifacts pane to Agents-tab load state, which every other pane
deliberately avoids.

### 2.2 Candidate B — `agent_artifact_index.sqlite` alone

**Reject as the spine.** It is the right *attribute* source: 46 indexed columns
including `status`, `agent_type`, `agent_name`, `model`, `llm_provider`, `started_at`,
`finished_at`, `hidden`, `workflow_name`, `agent_family`, `agent_clan`, `clan_tribe`,
and the full retry lineage. But it is a **hot window**, not history:
`prune_hidden_terminal_agent_artifact_index_rows` exists precisely to keep it small, and
open bead `sase-kh` is about its hidden rows growing unbounded anyway. Measured: of the
9 link-graph `agent:` refs with no published page, **8 have zero index rows** — they were
dismissed and pruned. Overall it resolves 4 of 55 refs (7%).

### 2.3 Candidate C — the agents sidecar (`agent:` refs' actual resolution target)

**Reject as the spine, keep as the open target.** `sase artifact path agent:0b4` resolves
to `…/repos/agents/agents/bbugyi200.athena.0b4/README.md`, and 9,602 such pages exist.
But it covers only 46 of 55 live refs (84%), it is git-synced and can lag or be absent on
a fresh machine, and — verified — it can be **wrong**: `agent:0b4` resolves to a page
whose `state.json` says the run finished 2026-07-01, while the local registry says `0b4`
is a *family* container created 2026-08-22 whose member `0b4--0` wrote the actual link
row on 2026-08-22. Short local names are recycled; the sidecar page and the local
registry disagree about who `0b4` is.

That is a real defect worth filing on its own, and it is a reason the pane must not treat
the published page as identity. It is a **detail-panel enrichment and an open target**.

### 2.4 Candidate D — the agent name registry as spine, everything else left-joined

**Recommend.** Measured coverage of the 12,318 registry entries:

| Enrichment | Entries matched | % |
| --- | ---: | ---: |
| Artifact-index row (by `artifacts_dir`) | 9,513 | 77.2% |
| Dismissed-bundle row (by `raw_suffix`) | 8,675 | 70.4% |
| **Either** | **11,422** | **92.7%** |
| Neither (name-only row) | 896 | 7.3% |

The join itself costs **16 ms** in Python over the whole corpus. Registry load is 151 ms.
So a cold, complete, fully-enriched snapshot is roughly **150 ms + 170 ms + 50 ms ≈ 370 ms
on a worker thread** — comfortably inside the snapshot-pane pattern every other Artifacts
pane already uses (`ArtifactsSnapshotPane` + `SnapshotRequest`), and an order of magnitude
better than paging 26,657 JSON files.

The registry also carries exactly the fields identity needs and nothing it doesn't:
`name`, `canonical_global_name`, `artifacts_dir`, `bundle_path`, `raw_suffix`,
`created_at`, `project_name`, `workflow_dir`, `state`, `origin`, `reservation_kind`,
`container_kind`, `clan_generation`, `source_owner`, `collision_owners`.

**The 7.3% with no enrichment still appear**, showing name, state, project, and created
time, with an explicit "no run data" detail state. A row that exists but is thin is
strictly better than a link target that resolves to nothing — which is the status quo.

### 2.5 Row identity and the entry target

`ArtifactEntryTarget("agents", parts)` is already what `_target_for_ref` produces, with
`parts == (name,)`. Keep that. Do **not** key rows on `artifacts_dir`: `agent:` refs
address *names*, and `_known_target_for_ref` has no `agent` branch today, so a
`parts=(project, artifacts_dir)` shape would silently never match an incoming ref.

Recommended: `ArtifactEntryTarget("agents", (name,))`, plus an `agent` branch in
`_known_target_for_ref` that (a) matches the bare local name exactly and (b) matches a
row whose `canonical_global_name` equals the payload. That one branch makes 55 of 55 live
refs land, including the owner-qualified one.

---

## 3. The query dialect

### 3.1 Author it as a profile, and migrate the Agents tab onto it

Add `agents_query_schema()` to `ace/query_profile/profiles.py`, register
`"agents"` in `_BUILTIN_SCHEMA_BUILDERS`, and compile it into the pane contract. Then
replace `sase/ace/agent_query/`'s parser/tokenizer/evaluator with a thin
`AgentQueryFilter` modeled on `ProcQueryFilter`, so the Agents tab and the Agents pane
speak **one dialect with one digest**.

Why this and not "extend `agent_query`":

- Saved queries and query history are **pane-namespaced by pane id and digest-stamped**
  (`ace/saved_queries.py`, `ace/query_record.py`). A profile dialect gets both stores,
  slot picker, `^`/`_` history navigation, and dialect-change invalidation for free. A
  forked dialect gets none of them, forever.
- The profile-driven `FilterBar` supplies completion, static value lists, per-key hints,
  and syntax highlighting from the schema. `agent_query` has a hand-written
  `highlighting.py` and a modal-based query editor with a one-line hint string.
- Rust routing (`query_profile_corpus_facade`) becomes available for the corpus if the
  row count ever justifies it, with a cross-language conformance golden already in
  `tests/ace/tui/artifacts_contract/test_query_conformance.py`.
- It deletes 1,189 LOC of forked language rather than adding to it.

### 3.2 The one real regression, and how to pay for it

`agent_query` supports `age>2h`, `age<=15s`, `age:1d`. The shared profile grammar has
**no general comparison operator** — comparisons exist only as fixed *bound key names*:
`HOST_DATE_BOUND_KEYS = {since, after: ">=", until, before: "<="}` and
`HOST_DURATION_BOUND_KEYS = {min: ">=", max: "<="}`.

Three options:

1. **Map `age` onto the host duration bounds.** `age>2h` becomes `min:2h`
   (runtime/age at least 2h) and `age<30m` becomes `max:30m`. Procs already does exactly
   this (`min`/`max` int fields with a `"runtime at least N seconds (or 5m, 2h, 1d)"`
   hint). Zero host changes. Costs the `age` spelling.
2. **Add `age` to `HOST_DURATION_BOUND_KEYS`** as an alias family. Small, contained host
   change; but bound keys are a *closed host vocabulary* whose whole point is that no
   dialect invents comparison behavior, and `age` is semantically two bounds, not one.
3. **Add a general comparison operator to the shared grammar.** Largest blast radius —
   it changes canonical form for every pane and invalidates every saved query digest.

**Recommend option 1**, plus retaining `age>…`/`age<…` as *input sugar* that the Agents
schema's own pre-parse rewrites into `min:`/`max:` before handing text to the profile
parser, exactly as `limit:` is stripped by `_membership_query` today. Users keep the
spelling they know; the canonical form and the digest stay pure profile. Note this
explicitly in the schema docstring so it is not mistaken for a private dialect.

### 3.3 Proposed field set

Flat mode (`boolean=False`) is the wrong default here — Patches is boolean because its
users write real expressions, and the Agents tab **already has** AND/OR/NOT with parens.
Removing it would be a downgrade. **Declare `boolean=True`.**

The schema should not be a mechanical dump of `AgentState`'s 168 fields. Group by the
question a user is actually asking:

**Identity and lineage**

| Key | Kind | Notes |
| --- | --- | --- |
| `name` | string, exact | local name; also matches `canonical_global_name` |
| `project` | string, exact | display name, never the ProjectSpec key |
| `family` | string, exact | `agent_family`; bare `family:` ⇒ any family member |
| `clan` | string, exact | `agent_clan` |
| `tribe` | string, exact | user tribe or `clan_tribe`; bare `tribe:` ⇒ any tribe |
| `workflow` | string, exact | `workflow_dir_name` / `workflow_name` |
| `role` | string | `agent_family_role` (`monitor`, `plan`, `coder`, …) |
| `parent` | string | `parent_agent_name` / `parent_timestamp` |

**Lifecycle**

| Key | Kind | Notes |
| --- | --- | --- |
| `state` | enum | `active`, `done`, `dismissed` — the *registry* state |
| `status` | string | the display status (`DONE`, `FAILED`, `WAITING`, `MONITORED`, …) |
| `outcome` | enum | `completed`, `failed`, `stopped`, `plan_rejected`, `noop`, … |
| `kind` | enum | `agent`, `workflow`, `family`, `clan`, `monitor`, `proc` |
| `hidden` | bool | workflow children and hidden steps |
| `revivable` | bool | **derived**: dismissed **and** a readable bundle exists |
| `retry` | int | `retry_attempt`; **equality only** — see the note below |

**Execution**

| Key | Kind | Notes |
| --- | --- | --- |
| `model` | string | |
| `provider` | string | `llm_provider` |
| `effort` | enum | `reasoning_effort` |
| `alias` | string | `model_alias` |
| `workspace` | int | `workspace_num` |
| `patch` | string | `cl_name` |
| `bead` | string | `bead_id` / `epic_bead_id` / `phase_bead_id` |

**Time**

`since` / `until` (date, started-at), `after` / `before` (date, finished-at),
`min` / `max` (duration bounds over runtime — see §3.2).

**A constraint worth naming.** `HOST_DURATION_BOUND_KEYS` has exactly one pair,
`min` / `max`, and `_match_int_field` gives *every other* `int`-kind field
equality-only matching (verified in `ace/query/profile_evaluator.py`). So a dialect gets
**one** numeric range, and this schema spends it on runtime. `retry:2` means exactly two
attempts; "at least one retry" has no spelling. That is a second instance of the same gap
§3.2 describes, and if a third appears the calculus shifts toward option 2 (widening the
host bound vocabulary) or option 3 (a real comparison operator). Two instances is not yet
enough to justify changing a closed host vocabulary; note it and move on.

**Search-only** (`filterable=False, searchable=True`)

`prompt` (raw xprompt snippet), `reply` (response/transcript), `error`, `text` (the union).

Two of these deserve a defence:

- **`revivable` is the highest-value key in the whole schema.** The pane's flagship
  gesture is "find the dismissed agent I want back". `revivable:true state:dismissed
  project:sase bead:sase-r5` is a one-line answer to a question that currently requires
  paging an archive modal.
- **`kind` must distinguish containers from runs.** 2,328 of 12,318 registry entries are
  family or clan reservations, not agent runs. Without `kind`, a naive `name:0b4` search
  returns a container and an unrelated recycled run with equal weight — which is exactly
  the `0b4` confusion §2.3 documents.

### 3.4 Content search must be lazy

`agent_query`'s `text:` / bare-string search already reads prompt and reply files through
`AgentContentSearchCache`, capped at 512 KB per file and keyed by `(path, mtime_ns)`.
`ProcQueryFilter._query_needs_output` shows the right pattern at profile scale: parse
first, walk the AST for output-needing keys, and only build the expensive haystack when
the query actually asks for it. Do the same here — with 12,318 rows, eagerly reading
transcripts is not an option.

The `chats_catalog.sqlite` `agent-links` generated index (chat path →
`artifact_dir` / `global_name` / `local_name` / `project_key`, over 22,613 transcripts)
is the right lookup for finding a row's transcript without touching the filesystem, and
its `prompt_snippet` / `response_snippet` payload fields are a cheap first-pass haystack
before opening a full transcript.

---

## 4. Revival from the pane

### 4.1 Mechanically, it already works

`_do_revive_agent(agent)` and `_do_revive_agents(agents)` live on `AgentReviveExecutionMixin`,
which is mixed into `AceApp`. They take `Agent` objects, restore the on-disk markers
(`done.json`, `workflow_state.json`, `prompt_step_*.json`, `agent_meta.json`) via
`ArtifactRestorationMixin`, clear the dismissed set, upsert the artifact index, and
schedule a refresh. A pane widget reaches them with `self.app._do_revive_agent(...)`.
`read_bundle(bundle_path)` reconstructs the `Agent` from the archive.

So the pane needs: the row's `bundle_path` (registry carries it), a confirm gesture, and
a refresh. **It does not need a second revival implementation**, and building one would
be the classic third-copy mistake.

### 4.2 Keep the `R` panel

The `R` flow on the Agents tab is not "a worse search". It opens
`SavedAgentGroupRevivalModal` — saved dismissal *groups* plus recent dismissal groups,
with `custom_search` as an escape hatch into the archive modal. Reviving a whole
previously-saved group is a different, faster gesture than composing a query, and it has
its own durable store (`~/.sase/dismissed_agent_groups`, `times_revived`, `revived_at`).

**Recommend:** keep `R` exactly as is. Change one thing — make the modal's
`custom_search` action **navigate to the Artifacts Agents pane with a seeded query**
(`state:dismissed revivable:true`) instead of pushing `DismissedAgentSelectModal`. That
retires the weakest of the three surfaces (the offset-paged archive modal) without
touching the strong one, and it gives the new pane an immediate reason to be reached.
Deleting `DismissedAgentSelectModal` outright is a later, separate call — the retired
Chats pane (`ad11756e6`) is the precedent for what "delete rather than merely unmount"
should look like when the time comes.

### 4.3 Marks and bulk revive

`STABLE_MARKS` is derived from `has_inventory` (rule `stable_marks_from_inventory`), so
`m` / `u` come free, and `_do_revive_agents` already takes a list. Bulk revive from marks is the natural
multi-select story and needs no new selection model — unlike the archive modal, which
hand-rolls `tab` / `ctrl+a` marking.

### 4.4 Mutation, capability, and key

Revive is a `PaneCapability.MUTATION` verb. That means `can_mutate=True` on the adapter,
and `agents_revive` must be added to `CAPABILITY_HOST_ACTIONS[PaneCapability.MUTATION]`
or conformance fails (`check_declared_actions_are_registered`).

Key choice: `R` is taken on the Artifacts tab (`refresh`). Pane-scoped actions may reuse
a key another tab binds (the config comments cite `beads_open_bug` / `files_open_external`
sharing `E`), but reusing `R` for a *different* verb on a sibling tab is a genuine
muscle-memory trap given `R` means "revive" one tab over. **Default recommendation:
`agents_revive: "w"`**, matching `beads_launch_work: "w"` as "the pane's launch-ish
verb". See Q7.

---

## 5. What the pane must do so `agent:` edges resolve

Three concrete items, all small, all inside the pane's own scope:

1. **Add the `agent` branch to `_known_target_for_ref`** so an incoming
   `agent:<local>` or `agent:<owner.machine.local>` matches a loaded row. Without it the
   fallback in `_target_for_ref` still constructs `("agents", (payload,))`, but it will
   only accidentally match rows whose parts happen to be the bare payload.
2. **Declare `links` / `linked_by`.** `with_artifact_link_relations` appends them to
   every built-in adapter automatically, so this is free — but the pane must load an
   `ArtifactLinksSnapshot` on its worker and pass `known_targets` to
   `artifact_link_edges`, the way `files_pane` does.
3. **Normalize the ref form on read, not on write.** 54 of 55 live refs are bare local
   names and 1 is owner-qualified. The pane should match either. Do **not** rewrite
   stored rows as part of this work — that is link-graph scope, and `sase-t0`/`sase-t1`
   are already open on the write path.

What the pane must *not* foreclose, for step 2 of the owner's plan:

- Do not assume `agent:<name>` is unique across time. §2.3 shows it is not. Any row
  identity, cache key, or copy target must carry the run behind the name
  (`raw_suffix` / `artifacts_dir`) even when the *display* identity is the name.
- Do not resolve `agent:` refs through the agents sidecar alone. 16% of live refs have
  no published page.
- Do not flatten relation metadata further. §5 of the link report already flags that
  ACE discards `relation`, `description`, `origin`, and `uses`. The Agents pane will
  carry the graph's largest edge population; it is the natural place for the typed
  relation rail to land, so leave the seams open.

---

## 6. Implementation shape and cost

Following `files_pane.py` as the template (342 lines, the closest structural analogue —
index-backed, snapshot-loaded, no mutation-heavy detail):

| Piece | New/changed | Est. size |
| --- | --- | --- |
| `agents_query_schema()` in `query_profile/profiles.py` | new | ~120 lines |
| `"agents"` in `_BUILTIN_SCHEMA_BUILDERS` | changed | 1 line |
| `_BuiltinAdapter("agents", …)` in `_artifact_tab_contract_adapters.py` | new | ~70 lines |
| `fixed_descriptor` labels/icons/accents | changed | ~5 lines |
| `resolve_artifacts_subtabs()` insertion | changed | 1 line |
| `agents_data.py` — registry load + two left joins | new | ~250 lines |
| `agents_query_rows.py` — row adapter | new | ~120 lines |
| `agents_pane.py` + list/detail/navigation/filter-session mixins | new | ~600 lines |
| `agent_filter_bar.py` | new | ~30 lines |
| `_known_target_for_ref` agent branch | changed | ~8 lines |
| Keymaps + `CAPABILITY_HOST_ACTIONS` + help modal rows | changed | ~30 lines |
| Migrate Agents tab onto the profile; delete `ace/agent_query/` | changed | **−1,189**, +180 |
| Tests: conformance is automatic; goldens + row-model + dialect tests | new | ~600 lines |

Net: roughly **+1,200 production lines, −1,189 deleted**, with the conformance and query
golden suites doing most of the regression work.

The sequencing risk worth naming: **the Agents-tab dialect migration is the part that can
go wrong**, because it changes behavior on the app's default startup tab. Land the pane
first with the new profile, prove the dialect against real queries, and migrate the
Agents tab in a follow-up change that is revertible on its own.

---

## 7. Open questions, each with a default answer

**Q1. Registry-as-spine, or artifact-index-as-spine?**
*Default: registry.* It is the only store that resolves 100% of live `agent:` refs and
the only one that is complete over time. §2.4. The counter-argument — the registry is a
16 MB JSON blob with no query index — is real but costs 151 ms once per snapshot, and the
join to both attribute sources costs 16 ms.
*Would reopen if:* the registry file grows past ~50 MB, at which point it wants the same
SQLite treatment the bundle archive already got.

**Q2. Is a row a name, or a run?**
*Default: a named run.* Display identity is the name; row identity carries the run
(`raw_suffix`). Family and clan reservations appear as rows with `kind:family` /
`kind:clan` and no run attributes, because `agent:` refs address them too (`agent:0b4`
is a family).
*Counter-argument:* pure-run rows would be cleaner. But then the 2,328 container
reservations have no row and their refs dangle.

**Q3. New profile dialect, or extend `ace/agent_query`?**
*Default: new profile dialect, and delete the fork.* §3.1. This is the strongest
recommendation in the report.
*Would reopen if:* the `age` regression (§3.2) proves unacceptable in practice **and**
options 1–2 both fail — which would mean the shared grammar genuinely lacks an
expressiveness the Agents domain needs, and that is worth knowing.

**Q4. `boolean=True` or flat?**
*Default: `boolean=True`.* The Agents tab already has AND/OR/NOT and parens; flat mode
would be a downgrade for the tab we are migrating. It also makes Agents the second
boolean pane, which is a healthy pressure test on the claim that boolean mode is not
Patch-specific.
*Cost:* boolean panes cannot use `key:a,b` OR-lists or `-key:x`; users write `key:a OR
key:b` and `NOT key:x`. Acceptable, and closer to what Agents users already type.

**Q5. Where in the sub-tab order, and what happens to digits?**
*Default: immediately before Files.* `assign_artifacts_digit_shortcuts` pins Files to the
last digit by rule, so inserting there keeps `stitches`=1, `patches`=2, `beads`=3,
`ref:plan`=4, `ref:research`=5, gives `agents`=6, and moves `files` 6→7. That is the
minimum disruption available, and Files' digit is *defined* as "the last one", so the
move is consistent with the documented rule rather than a surprise.
*Counter-argument:* grouping Agents with the other built-ins (after Beads) reads better,
but renumbers both provider panes.

**Q6. Label?**
*Default: `Agent`.* Fixed panes use singular labels — Patch, Stitch, Bead, File. Pane id
stays `agents`, because `_target_for_ref` already emits it and changing that would break
the one thing already wired.
*Note:* "Agents tab" vs "Artifacts → Agent pane" will still be ambiguous in prose. Worth
one sentence in the help modal.

**Q7. Revive key on the pane?**
*Default: `agents_revive: "w"`.* §4.4. Alternatives: `A` (mirrors `plans_approve` as the
pane's affirmative verb) or leaving it on `enter` with a confirm. `R` is not available.

**Q8. Does the pane show hidden agents and workflow children by default?**
*Default: no — `hidden:false` is the implicit default scope, with `hidden:true` to
include them.* 4,583 of 8,054 indexed rows are hidden; showing them by default buries the
rows a person is looking for. This mirrors the artifact index's own
`include_hidden: False` default.
*Counter-argument:* a link edge can point at a hidden agent, and a hidden row must still
be reachable when navigated to from a relation. Handle that the way other panes handle
out-of-scope targets: navigating to a target that the current query excludes should clear
the query, not fail.

**Q9. Does the detail panel render the published agent page, or local data?**
*Default: local data first, published page as a section.* The page is 84%-available and
demonstrably can disagree with local truth (§2.3). Render local identity, status, timing,
model, family/clan/tribe, retry lineage, artifact reads, and links; then a "Published
page" section with the sidecar's commits table and a copy-`reference` target that emits
the canonical `agent:<global_name>` form.

**Q10. Should this pane also be a CLI (`sase agent search`)?**
*Default: not in the first pass, but author the row model so it can be.*
`agent_query/evaluator.py`'s docstring already anticipates `sase agent search`, and
`ProcQueryFilter` proves a profile dialect works headless. Keep the row builder in
`sase/core` or a Textual-free module so the CLI is a later thin wrapper, not a rewrite.

**Q11. Retire `DismissedAgentSelectModal`?**
*Default: not yet.* Reroute `custom_search` to the pane (§4.2), watch for a release, then
delete it the way the Chats pane was deleted — keymaps, commands, copy targets, help rows
and all.

**Q12. Should the `0b4` name-recycling collision be fixed as part of this?**
*Default: no — file it, don't fix it here.* It is an `agent:` **resolution** defect
(short local names are reused; the sidecar page and the local registry disagree), and it
belongs with step 2 of the owner's plan. The pane must merely not *depend* on the broken
assumption (§5).

---

## 8. Recommended solution

**Phase 1 — the dialect, headless.**
Author `agents_query_schema()` with the §3.3 field set, `boolean=True`, and the `age →
min/max` pre-parse rewrite. Register the pane id. Build `AgentQueryFilter` on the
`ProcQueryFilter` pattern with lazy content loading. Add dialect goldens to
`tests/ace/tui/artifacts_contract/goldens/query/`. **No UI yet** — this phase is
independently testable and independently revertible.

**Phase 2 — the row model, headless.**
`agents_data.py`: load the registry, left-join the artifact index (column projection
only — never `record_json`) and the dismissed bundle summary index, and emit an immutable
`AgentsSnapshot` of typed rows carrying `(name, canonical_global_name, raw_suffix,
artifacts_dir, bundle_path, project, state, kind, …)` plus every §3.3 attribute. Derive
`revivable` here. Target: complete snapshot under 400 ms on a worker thread; assert it
in a benchmark test alongside `bench_artifacts_jk.py`.

**Phase 3 — the pane.**
`_BuiltinAdapter` with `has_inventory=True`, `has_fields=True`, `has_stable_identity=True`,
`has_revisions=False`, `can_mutate=True`, `project_scoped=True`, `has_detail=True`;
relations `family` / `clan` / `retry_chain` plus the auto-appended `links` / `linked_by`;
grouping modes `by_state`, `by_project`, `by_family`; one status counter on `status`.
Widget on the `files_pane` template. Insert before Files. Add the `agent` branch to
`_known_target_for_ref`. Conformance runs automatically.

**Phase 4 — revival.**
`agents_revive` on marks and on the selected row, calling the existing app mixin through
`read_bundle`. Register the action under `MUTATION`. Reroute
`SavedAgentGroupRevivalModal`'s `custom_search` to the pane with a seeded query. Keep `R`.

**Phase 5 — migrate the Agents tab, delete the fork.**
Point `_edit_agent_search_query`, `_loading_compute_finalize`, and `_prospective_clan` at
the shared profile; give the Agents tab a real `FilterBar` instead of `QueryEditModal`;
delete `sase/ace/agent_query/`. Land this separately from Phases 1–4 so it can be
reverted alone.

**Then, and only then**, steps 2 and 3 of the owner's plan have a consumer worth building
for: the majority of the link graph resolves, `agent:` becomes a navigable endpoint, and
the "chops link to the agents they launched" story has somewhere to land.

---

## 9. What not to do

- **Do not build a third agent query dialect.** The whole reason `agent_query` is worth
  deleting is that it was built this way once already.
- **Do not back the pane with the live Agents tab's in-memory list.** It cannot revive,
  and it resolves 4 of 55 refs.
- **Do not `SELECT *` the artifact index.** `record_json` is 114 MB.
- **Do not treat the published agents sidecar page as identity.** 84% coverage, and it
  can be wrong about who a recycled name is.
- **Do not page JSON bundle files for filtering.** The SQLite summary index already
  exists, holds all 26,657 rows, and scans in 167 ms. The current modal's offset paging
  is the defect, not the data volume.
- **Do not delete the `R` revival panel in this work.** Saved dismissal groups are a
  distinct gesture with their own durable store and revival counters.
- **Do not rewrite stored `agent:` link rows to canonical form here.** Match both forms
  on read; leave write-path canonicalization to the link-graph work.
- **Do not show hidden rows by default.** 57% of indexed rows are hidden.
- **Do not let the pane depend on `agent:<name>` being unique across time.** It is not.
