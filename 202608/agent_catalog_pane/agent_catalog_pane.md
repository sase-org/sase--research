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
  - sase-core
---

# The Artifacts Agents Pane: Registry Spine, Two Levels of Identity, One Shared Dialect

**Research question.** How should the **Agents** sub-tab of ACE's **Artifacts** tab be
implemented so that it is an excellent queryable agent catalog, makes `agent:` link
edges land somewhere, and can revive archived agents — without becoming a second copy of
the main Agents tab or a third agent query dialect?

**Scope.** This report designs the pane. The artifact-link defect fixes and the later
"every tab is link-aware" project stay out of scope per the owner's framing; §6 states
only the minimum link work the pane owes and what it must not foreclose.

**Method.** `sase` at `c09fe5170` (master, clean), `sase-core` opened via `sase repo
open`, agents sidecar likewise. Every number below was measured by the lead on this
machine on 2026-08-24 against live stores (`~/.sase/agent_name_registry.json`,
`~/.sase/agent_artifact_index.sqlite`, `~/.sase/dismissed_bundles/index.sqlite`,
`~/.sase/projects/gh_sase-org__sase/artifact-links.json`, the agents sidecar clone).
Where the lead's measurement differs from a researcher's, the lead's number and the
reason for the divergence are given. Timings are wall-clock, warm cache.

---

## Bottom line

**Report b's central call is correct and reproducible: the row spine is the agent name
registry.** Against the live link graph the registry resolves **45 of 45** distinct
`agent:` refs; report a's proposed stores (artifact index + dismissed archive) resolve
**27 of 45**. Building the pane on a's sources would leave 40% of the very edges the
pane exists to catch pointing at nothing.

**Report a's central call is also correct, and the registry already encodes it.** a
argued for two levels of identity — a family/solo banner over concrete runs. That is not
a modelling preference: **17 of the 45 live `agent:` refs (38%) name a family
container**, not a run. The registry distinguishes them natively via
`container_kind` (1,735 family + 596 clan reservations among 12,328 names). So the
synthesis is one spine with one `kind` field, not two record types and not a flat run
list.

The two reports were arguing about different halves of the same answer:

| Question | a | b | Resolution |
| --- | --- | --- | --- |
| What backs a row? | artifact index + dismissed archive + sidecar | name registry | **b** — measured 45/45 vs 27/45 |
| Is a row a name or a run? | family banner over runs | a named run | **both** — registry rows, `kind` separates containers from runs |
| Dialect | shared profile, `boolean=True` | shared profile, `boolean=True` | **agreed** |
| `age>2h` | extend the Rust grammar with a comparison operator | rewrite to `min:`/`max:` sugar | **neither** — `until:2h` already works (§3.2) |
| Evaluation engine | Rust `ArtifactQuerySession` | Python `ProcQueryFilter` pattern | **a** — Rust is the production path for every pane, incl. boolean Patches |
| Delete `ace/agent_query/`? | later, optional | yes, phase 5 | **b**, but strictly last and separately revertible |
| Revival | extract a widget-free backend operation | call the existing `AceApp` mixin | **middle** — one implementation, plus a completion delta (§5) |
| Sub-tab position | after Files | before Files | **b** — Files is pinned last by rule |
| Revive key | route `R` through the active pane | `w`; `R` is taken | **b** — `R` is `refresh` in the app keymap |
| Feature flag | required disabled beta | not mentioned | **a** — core memory mandates it |

Both reports also carried measurement errors that would become implementation bugs.
§1.2 corrects them; the two that matter most are that **`raw_suffix` is not unique in
the dismissed archive** (6,890 distinct keys across 26,657 rows) and that **the registry
does not carry `bundle_path`** for the rows revival needs (99 of 12,328 entries).

---

## 1. Evidence

### 1.1 What backs a row: the decisive measurement

The live aggregate for `gh_sase-org__sase` currently holds 95 rows, 59 of which touch an
`agent:` ref (62%), spanning 45 distinct agent payloads. Resolution by candidate spine:

| Candidate spine | Live `agent:` refs resolved | Rows in store |
| --- | ---: | ---: |
| **Agent name registry** | **45 / 45 (100%)** | 12,328 names |
| Agents sidecar published pages (via `canonical_global_name`) | 42 / 45 (93%) | 9,623 agent + 1,461 family pages |
| Artifact index **and** dismissed archive together | 27 / 45 (60%) | 8,062 hot + 6,703 top-level archived |
| Dismissed archive alone | 22 / 45 (49%) | 6,703 top-level runs |
| Artifact index alone | 5 / 45 (11%) | 8,062 rows |
| Live Agents tab in-memory list | ≈ visible working set only | ≤ 1,200 |

44 of the 45 refs resolve on the registry's bare local key; the last
(`agent:bbugyi200.athena.002--1`) resolves on `canonical_global_name`. **Zero
unresolved.** The registry is the only complete spine, and it is complete because it is
the store whose job is naming — the same job `agent:` refs do.

*Divergence note.* b measured 55 refs over 161 aggregate rows and 84% sidecar coverage;
the lead measures 45 over 95 rows and 93% sidecar coverage. Two causes: the aggregate
was rebuilt at 18:29:30 today and lost rows (§6.1), and b compared sidecar pages against
bare names rather than canonical global names. The **ranking is unchanged** under both
measurements, which is what the decision turns on.

### 1.2 Corrections to both reports' measurements

These are not pedantry — each one changes an implementation detail.

**(a) `raw_suffix` is not a run identity.** The dismissed archive has 26,657 rows but
only **6,890 distinct `raw_suffix`** values; `bundle_path` is the unique key. One suffix
carries up to **11** bundles. b's plan to "left-join the dismissed bundle index by
`raw_suffix`" is many-to-one and would attach an arbitrary sibling's attributes.

*Fix, verified:* join only top-level bundles (`is_workflow_child = 0`). That yields
6,652 distinct suffixes and **zero ambiguous joins** across all 12,328 registry names.

**(b) "26,657 runs" is 75% workflow children.** 19,953 bundles use the `__c<N>` filename
convention, 20,005 carry `is_workflow_child = 1`, and **19,781 have `agent_name =
NULL`**. The true count of top-level dismissed agents is **~6,703**. Both reports quoted
26,657 as the historical agent count; it is the bundle-file count.

**(c) The registry does not carry `bundle_path` where revival needs it.** Only **99 of
12,328** entries have a top-level `bundle_path` (they are the `source:
dismissed_bundle` entries). b's revival plan ("the row's `bundle_path` — registry
carries it") fails for 99.2% of rows. The path is available from the dismissed summary
index, and from `collision_owners` records (7,235 of those carry one).

**(d) The registry is a name→current-owner map with history, not a run list.**
**6,531 of 12,328 entries (53%) carry `collision_owners`**, 8,369 records in total, with
a maximum depth of **630** for a single name. Distinct `raw_suffix` across the whole
registry is only **10,418**. b's framing of the `0b4` case as a name-recycling *defect*
understates this: recycling is the majority condition, and the registry models it
deliberately.

**(e) `agent:0b4` is not a mis-resolution.** b reported that the sidecar and the registry
disagree about who `0b4` is. The registry says `0b4` is a **family container**
(`reservation_kind: family`, `container_kind: family`, created `20260822161630`) and
`0b4--0` is its member, sharing that suffix. `sase artifact path agent:0b4` resolves to
`agents/bbugyi200.athena.0b4/README.md`. So the ref names a family, and 38% of live refs
do the same. This is a's identity argument confirmed by data, not a bug to file.

**(f) Rust corpus evaluation is the production path, not a future option.** b proposed
modelling on `ProcQueryFilter`, which uses the pure-Python `evaluate_query_for_profile`
per row. That is fine for a Procs list of tens of rows. Every Artifacts pane — Files,
Beads, Plans, Stitches, and **boolean Patches** — builds a Rust `ArtifactQueryIndex` via
`compile_artifact_query_index()` and evaluates through `evaluate_artifact_query_many()`
behind `ArtifactQuerySession`. `query_profile_corpus_facade` states plainly that the
Python reference evaluator "stays parity-test-only, not a production fallback for
matching". At 12,328 rows the pane uses the Rust path. b's *lazy content gating* idea
(`_query_needs_output` walks the AST before building expensive haystacks) is still worth
porting.

**(g) Files is pinned last by rule.** `assign_artifacts_digit_shortcuts` documents that
the Files descriptor "always receives a digit shortcut, and it is always the highest
digit assigned", and `resolve_artifacts_subtabs()` composes `stitches, patches, beads,
*providers, files`. a's "add Agents after Files" contradicts both. Insert **before
Files**.

**(h) `R` is `refresh`.** `src/sase/default_config.yml` binds `refresh: "R"` in the
`app` keymap. a's proposal to route `R` through the active Artifacts pane would shadow
refresh on one pane only — a worse trap than a different key.

**(i) The artifact index can already answer full-history queries.** a is right that
`query_artifact_index_for_loader` returns `None` when `full_history=True`, forcing
`scan_artifacts()`. The useful corollary a did not draw: `include_full_history=True` is
**already used in production** by six callers (`agents_sync/inventory_sources.py`,
`agent/_family_attach_candidates.py`, `bead_pages/associations/_artifacts.py`,
`sdd/associations/_artifacts.py`, `monitor/store.py`, `main/var_cli.py`). The pane does
not need new index machinery — only the Tier-1 TUI loader declines the capability.

### 1.3 What the pane substrate already gives away

Both reports agree here and both are right. A new fixed pane needs one `_BuiltinAdapter`
entry, one `ArtifactQuerySchema`, one pane widget, and one `_compose_pane` branch;
everything else is derived:

| Machinery | Where | What the pane gets |
| --- | --- | --- |
| Capability derivation | `_artifact_tab_contract_rules.py` | `has_inventory + has_fields` ⇒ `QUERY_HISTORY` and `SAVED_QUERIES`; `has_inventory` ⇒ `STABLE_MARKS` |
| Dialect | `ace/query_profile/` + `ace/query/` | tokenizer, parser, canonicalizer, digest, Rust routing |
| Filter bar | `widgets/filter_bar.py` | completion, value hints, highlighting — all read from the profile |
| Saved queries / history | `ace/saved_queries.py`, `ace/query_history.py` | pane-namespaced, digest-stamped, dialect-change invalidation |
| Visual shell | `widgets/artifacts/shell.py` | loading / stale / empty / degraded / results precedence |
| Relations | `with_artifact_link_relations()` | `links` / `linked_by` appended to every built-in adapter automatically |
| Conformance | `tests/ace/tui/artifacts_contract/harness.py` | **12** checks auto-parametrize over `resolve_artifacts_subtabs()` |

That last row is a real constraint and a real quality floor: declared actions must be
registered, declared copy targets must be registered, declared relation edges must
resolve, declared keys must resolve to named actions, unavailable actions must carry OFF
verdicts, and the pane must render the shared shell — the moment the pane id appears in
`resolve_artifacts_subtabs()`.

`Procs` is the load-bearing precedent that a profile dialect does not require a pane:
`procs_query_schema()` is registered in `_BUILTIN_SCHEMA_BUILDERS` and consumed by
`ProcQueryFilter` with no Artifacts pane behind it. That is why the dialect can land and
be tested headless before any widget exists.

The live inventory today is `stitches, patches, beads, ref:plan, ref:research, files` —
`sase artifact pane show agents` errors with "unknown Artifacts pane 'agents'". And
`_target_for_ref` already emits `ArtifactEntryTarget("agents", (payload,))` for every
`agent:` ref, so the pane id is the one thing already wired.

---

## 2. The row model

### 2.1 One spine, one `kind`, two display levels

**A row is a registry entry.** Its display identity is the name; its run identity is
carried alongside so nothing downstream depends on a name being unique across time.

```text
AgentCatalogRow
  stable target : ArtifactEntryTarget("agents", (name,))
  identity      : name, canonical_global_name, kind
  run identity  : raw_suffix, artifacts_dir, bundle_path   (may be absent)
  attributes    : left-joined from the artifact index and the dismissed archive
  provenance    : which sources enriched this row, and which did not
```

`kind` is derived from the registry and is the field that makes the two levels work:

| `kind` | Source | Count | Role |
| --- | --- | ---: | --- |
| `family` | `container_kind == "family"` | 1,735 | banner; **38% of live `agent:` refs** |
| `clan` | `container_kind == "clan"` | 596 | banner |
| `agent` | `reservation_kind == "claimed"` and no `--` | ~6,200 | solo run |
| `member` | `reservation_kind == "claimed"` and name contains `--` | 3,782 | family member run |
| `workflow-child` | `is_workflow_child` from the archive | — | hidden by default |

Family/member linkage is derivable from the name (`0b4--0` → family `0b4`) and
corroborated by `agent_family` in the artifact index — no second record type is needed.
Default grouping renders members under their family banner, which is a's requested shape
achieved as a **grouping mode over one row set**, not as a second record.

`ArtifactEntryTarget("agents", (name,))` matches what `_target_for_ref` already
constructs. **Do not key rows on `artifacts_dir`** — a `(project, artifacts_dir)` shape
would silently never match an incoming ref, because refs address names.

### 2.2 Degrade a row, never drop it

Enrichment measured over all 12,328 registry names:

| Enrichment | Rows | % |
| --- | ---: | ---: |
| Artifact-index row (join on `artifacts_dir`) | 9,523 | 77.2% |
| Dismissed top-level bundle (join on `raw_suffix` where `is_workflow_child = 0`) | 8,438 | 68.4% |
| **Either** | **11,298** | **91.6%** |
| Neither — name-only row | 1,030 | 8.4% |

The 8.4% still appear, showing name, kind, state, project, and created time, with an
explicit "no run data" detail state. A thin row is strictly better than the status quo,
which is a link target that resolves to nothing.

### 2.3 What the row model must not assume

- **A name is not unique across time.** 53% of names carry collision history, one to a
  depth of 630. Row identity, cache keys, and copy targets must carry the run.
- **The published sidecar page is not identity.** 93% coverage of live refs, git-synced,
  can lag or be absent on a fresh machine. It is an *open target* and a detail-panel
  enrichment.
- **A container has no single status, model, or runtime.** A family banner shows a
  member timeline, not an invented aggregate state.

---

## 3. The query dialect

### 3.1 Author it as a profile; migrate the Agents tab onto it last

Add `agents_query_schema()` to `src/sase/ace/query_profile/profiles.py`, register
`"agents"` in `_BUILTIN_SCHEMA_BUILDERS`, and compile it into the pane contract.
Declare **`boolean=True`** — the main Agents tab already has AND/OR/NOT with
parentheses, and flat mode would be a downgrade for the tab that eventually migrates.

Then replace `sase/ace/agent_query/`'s parser/tokenizer/evaluator (1,189 LOC across 6
modules, whose own tokenizer docstring says it is "Adapted from
`sase.ace.query.tokenizer`") with a thin filter over the shared profile, so both
surfaces speak one dialect with one digest. Why, concretely:

- Saved queries and query history are pane-namespaced and digest-stamped. A profile
  dialect gets both stores, the slot picker, `^`/`_` history navigation, and
  dialect-change invalidation for free. A forked dialect gets none of them, ever.
- The profile-driven `FilterBar` supplies completion, static value lists, per-key hints,
  and highlighting from the schema. `agent_query` hand-writes `highlighting.py` and uses
  a modal query editor with a one-line hint.
- Rust corpus routing and the cross-language conformance golden
  (`tests/ace/tui/artifacts_contract/test_query_conformance.py`) come with the profile.

**Sequencing.** Land the pane on the new profile first; migrate the main Agents tab in a
change that is revertible on its own. The migration touches the app's default startup
tab and is the part most likely to go wrong.

### 3.2 The `age>2h` question: no host change, and no sugar either

Both reports mis-framed this. The facts:

- `HOST_DURATION_BOUND_KEYS = {"min": ">=", "max": "<="}` and
  `HOST_DATE_BOUND_KEYS = {"since": ">=", "after": ">=", "until": "<=", "before":
  "<="}`, mirrored byte-for-byte in `sase-core/crates/sase_core/src/query/profile.rs`.
  Comparison direction is keyed off the **field name**, not a separate operator.
- `_match_int_field` gives every non-`min`/`max` `int` field equality-only matching. So a
  dialect gets exactly **one** numeric range.
- **But date bounds come in two pairs**, so a dialect gets **two** date ranges.
- Date bounds accept relative `Nh` / `Nd` / `Nw`, `today`, `yesterday`, `YYYY-MM-DD`,
  and `YYYY-MM-DDTHH:MM` (`parse_time_bound`). Duration bounds accept seconds or one
  whole-unit literal (`30s`, `5m`, `2h`, `1d`).

Therefore `age` needs no new grammar and no rewrite layer:

| Intent | Spelling | Field |
| --- | --- | --- |
| Started at least 2h ago (`age>2h`) | `until:2h` | date bound on `started_at` |
| Started within the last 2h (`age<2h`) | `since:2h` | date bound on `started_at` |
| Finished in a window | `after:` / `before:` | date bound on `finished_at` |
| Ran at least 5 minutes | `min:5m` | duration bound on runtime |
| Ran at most 2 hours | `max:2h` | duration bound on runtime |

a's proposal to add a `duration` value kind and general `<`/`>` operators would touch
the Rust profile, parser, tokenizer, and evaluator plus the Python registry, compiler,
both reference parsers, evaluator, highlighting, and completion — for expressiveness the
host already has. (b's claim that it would invalidate every pane's saved-query digest is
overstated: the digest is computed per pane over its own schema payload, so other panes'
digests are stable. The blast radius is the parity surface, not the digests.)

**One trap neither report caught, and it must be documented in the hints.** In a **date**
bound, `_RELATIVE_MONTH_RE = ^(\d+)m$` means `5m` is **five months**; in a **duration**
bound, `5m` is **five minutes**. `since:5m` and `min:5m` differ by a factor of ~43,000.
This is also the reason **not** to add `age>5m` input sugar: the sugar would have to
pick a target silently. Spell the two concepts with the two key families the host
already distinguishes, and put the `m` collision in both hints.

**When to revisit.** b's counting rule is the right one. The `retry` field is
equality-only for the same reason (`retry:2` means exactly two attempts; "at least one
retry" has no spelling — use a derived `retry:true` bool instead). That is gap #2. If a
third appears, reopen a general comparison operator as a shared-infrastructure change
with its own justification, not as a rider on this pane.

### 3.3 Field set

Grouped by the question a user is actually asking, not by dumping `AgentState`.

**Identity and lineage**

| Key | Kind | Notes |
| --- | --- | --- |
| `name` | string, exact | local name; also matches `canonical_global_name` |
| `kind` | enum | `agent`, `member`, `family`, `clan`, `workflow-child`, `monitor` |
| `family` | string, exact | family name; bare `family:` ⇒ any family member |
| `clan` | string, exact | `agent_clan` |
| `tribe` | string, exact | user tribe or `clan_tribe` |
| `role` | string | `agent_family_role` (`plan`, `code`, `mon`, …) or the `--<role>` suffix |
| `workflow` | string | `workflow_name` |
| `parent` | string | parent agent name / timestamp |
| `project` | string, exact | **display name, never the ProjectSpec key** |

**Lifecycle**

| Key | Kind | Notes |
| --- | --- | --- |
| `state` | enum | registry state: `active`, `done`, `dismissed` |
| `status` | string | display status (`DONE`, `FAILED`, `WAITING`, `MONITORED`, …) |
| `hidden` | bool | hidden from the live inbox |
| `dismissed` | bool | derived from `state` |
| `revivable` | bool | **derived**: dismissed **and** a readable bundle exists |
| `attention` | bool | stopped / error / needs-input |
| `retry` | bool | participates in a retry chain |
| `attempt` | int | `retry_attempt`, equality-only (§3.2) |

**Execution**

| Key | Kind | Notes |
| --- | --- | --- |
| `model` | string | |
| `provider` | string | `llm_provider` |
| `effort` | enum | `reasoning_effort` |
| `patch` | string | `cl_name`; do not perpetuate the user-facing `cl` spelling |
| `bead` | string | `bead_id` / `epic_bead_id` / `phase_bead_id` |
| `workspace` | int | `workspace_num`, equality-only |

**Time.** `since` / `until` over `started_at`; `after` / `before` over `finished_at`;
`min` / `max` over runtime. See §3.2.

**Search-only** (`filterable=False, searchable=True`). `prompt`, `reply`, `error`, and
`text` as the union.

Two fields deserve a defence:

- **`revivable` is the highest-value key in the schema.** The pane's flagship gesture is
  "find the dismissed agent I want back". `revivable:true AND project:sase AND
  bead:sase-r5` is a one-line answer to a question that today requires paging an archive
  modal.
- **`kind` must distinguish containers from runs.** 2,331 of 12,328 names are family or
  clan reservations. Without `kind`, `name:0b4` returns a container and its member with
  equal weight — the exact confusion §1.2(e) documents.

Completions for `status`, `role`, `model`, `provider`, `project`, and `tribe` should
merge static canonical values with **observed snapshot facets**, so an unreleased model
or provider stays queryable.

Worked examples for the help text:

```text
revivable:true AND patch:sase-42 AND role:code
provider:codex AND status:FAILED AND since:7d
family:research.12 AND NOT kind:monitor
state:active AND (attention:true OR status:WAITING)
retry:true AND model:gpt-5.6-sol AND min:5m
```

### 3.4 Content search stays lazy

`AgentContentSearchCache` reads prompt, reply, and attempt replies, capped at 512 KiB
per file and keyed on `(path, mtime_ns)`. That is right for a 200-row inbox on a worker;
applied to 12,328 rows it turns a metadata keystroke into tens of thousands of file
stats.

Port `ProcQueryFilter._query_needs_output`'s gating shape: parse first, walk the AST for
content-needing keys, and only build the haystack when the query asks. Default free text
searches indexed metadata only. `chats_catalog.sqlite`'s `agent-links` generated index
(chat path → `artifact_dir` / `global_name` / `local_name` / `project_key`, over 22,613
transcripts) is the right lookup for a row's transcript, and its `prompt_snippet` /
`response_snippet` payloads are a cheap first-pass haystack before opening a full file.
A persistent FTS index over transcripts is the correct later answer; until it exists, do
not offer a `content:` key that silently walks the archive.

---

## 4. Data sources and the performance contract

### 4.1 The measured snapshot

Composite snapshot, warm, single-threaded Python, on this machine:

| Step | Cost | Result |
| --- | ---: | --- |
| Registry load + parse (16 MB JSON) | 123 ms | 12,328 names |
| Artifact index, 22-column projection | 64 ms | 8,062 rows |
| Dismissed summaries, `is_workflow_child = 0` | 36 ms | 6,652 suffixes |
| Join | 16 ms | 12,328 rows, **0 ambiguous** |
| **Total** | **239 ms** | complete, fully enriched |

That is comfortably inside the `ArtifactsSnapshotPane` + `SnapshotRequest` pattern every
other pane already uses, and roughly two orders of magnitude better than the current
revival modal's offset-paging of 26,657 JSON files.

**Never `SELECT *` the artifact index.** `record_json` alone is **117 MB** across 8,062
rows; reading it costs 193 ms versus 64 ms for the projection.

### 4.2 Rules

- **Index-only.** Build from the registry, the artifact index (via the existing
  `include_full_history=True` query path), and the dismissed summary index. Never
  `scan_artifacts()`.
- **Cached first, revalidate explicitly.** Activation consumes the last snapshot
  immediately and schedules refresh off-thread. Snapshot generation, index signatures,
  and project scope are part of the cache key; the profile digest and canonical query
  are already in `ArtifactQueryCacheKey`.
- **Full corpus, bounded presentation.** Queries evaluate across all 12,328 rows in the
  Rust index; the option list renders a bounded or virtualized window with an explicit
  `showing N of M`. Never create 12,000 Textual options.
- **Exact navigation bypasses the cap and the query.** A link jump to a row the current
  query excludes clears the query rather than failing — the pattern other panes use for
  out-of-scope targets.
- **Lazy detail.** Prompt, chat, reply, commits, diffs, output variables, and bundle
  JSON load for the selected stable id after the normal detail debounce.
- **Thin pump callback.** Worker completion swaps immutable state and refreshes affected
  rows only. No filesystem reads, subprocesses, or index rebuilds in render, watch, or
  callback paths.

### 4.3 Where the reconciliation code lives

a is right that identity reduction, deduplication, and revival semantics are backend
domain behavior a CLI or web frontend would need identically, and the project's
`rust-core-required` decision points at `sase-core`. b is right that a Textual-free
Python module unblocks the pane now and a later `sase agent search` equally well.

**Default: build it as a Textual-free Python module in this repo for v1, with the wire
shapes designed to move.** The registry is Python-owned JSON today; moving both the
store and the reconciliation to Rust in the same change would triple the scope of a pane
that does not yet exist. Promote to `sase-core` when the CLI lands (§8 Q10) — that is
the moment a second frontend actually needs it, which is exactly the
`corpus-before-mechanism` test.

---

## 5. Revival

### 5.1 The current shape, and the real coupling

`_do_revive_agent(agent)` and `_do_revive_agents(agents)` live on
`AgentReviveExecutionMixin` (`actions/agents/_revive_execution.py`, 394 lines), mixed
into `AceApp`. They take `Agent` objects, restore on-disk markers via
`ArtifactRestorationMixin`, clear the dismissed set, purge bundle summaries, upsert the
artifact index, and schedule a refresh. `read_bundle(bundle_path)` reconstructs the
`Agent` from the archive. So b is right that a pane widget can reach them.

But the coupling a warned about is real and specific, in both methods:

```python
self._refilter_agents()                    # main-tab work, run unconditionally

def _on_revive_loaded() -> None:
    if self.current_tab != "agents":       # pane callers get no refresh at all
        return
```

Calling the mixin from the Artifacts tab therefore does main-tab list work on every
revive and leaves the pane stale.

### 5.2 Recommendation: one implementation, plus a completion delta

Do **not** write a second revival implementation — that is the third-copy mistake. Do
**not** do a's full widget-free extraction in v1 either; it is a large refactor of a
394-line mutation path with a delicate ordering contract, and it is not what makes the
pane valuable.

Instead:

1. Keep `_do_revive_agent(s)` as the single mutation implementation.
2. Give it an explicit result/completion delta — revived identities and artifact dirs,
   skipped/failed identities with stages, and the dismissed/index generation change.
3. Make the main-tab refilter and reselect a *consumer* of that delta rather than an
   unconditional side effect, so the Artifacts pane can consume the same delta to
   invalidate its snapshot generation, re-run the current query, and select the revived
   row.

That is a contained change with the same architectural payoff as the extraction, and it
leaves the widget-free/`sase-core` move for the CLI phase, where a second caller
justifies it.

### 5.3 Selection semantics

- A dismissed run row revives that row and its workflow children by the existing parent
  rule.
- Marked rows revive as one batch — `STABLE_MARKS` is derived from `has_inventory`, so
  `m` / `u` come free and `_do_revive_agents` already takes a list. No hand-rolled
  multi-select, unlike the archive modal's `tab` / `ctrl+a`.
- A family/clan banner with exactly one revivable member revives it; with more than one,
  it seeds the pane query to that family and its revivable members rather than opening a
  modal.
- A non-dismissed row reports "not revivable" without mutation.
- A row whose registry entry exists but whose bundle is missing stays visible with a
  diagnostic and is not `revivable:true`.

Single-row revive proceeds on the key; batch revive shows the concrete count and names
first, because a collapsed group can hold more rows than fit on screen.

### 5.4 Keep the `R` panel; retire the weakest surface

`R` on the Agents tab opens `SavedAgentGroupRevivalModal` — saved dismissal *groups* plus
recent groups, with `custom_search` as an escape hatch into
`DismissedAgentSelectModal`. Reviving a previously-saved group is a genuinely different
and faster gesture than composing a query, and it has its own durable store
(`~/.sase/dismissed_agent_groups`, `times_revived`, `revived_at`).

**Keep `R` exactly as is. Change one thing:** point the modal's `custom_search` action at
the new pane with a seeded query (`state:dismissed revivable:true`) instead of pushing
`DismissedAgentSelectModal`. That retires the weakest of the three surfaces — the one
that offset-pages 26,657 JSON files and can only filter what it has already loaded,
which is the defect the owner is feeling — without touching the strong one, and it gives
the new pane an immediate route in. Deleting `DismissedAgentSelectModal` outright is a
later, separate call; the retired Chats pane (`ad11756e6`) is the precedent for doing it
properly when the time comes.

---

## 6. Link destination work: the minimum, and what not to foreclose

### 6.1 The graph is actively shrinking — this bounds what the pane may claim

The derivation report's §3.1 identified that `preview_aggregate()` rebuilds the
machine-global index from the *triggering workspace's* sidecar clone, carrying forward
only rows whose endpoints own no sidecar anywhere. Live confirmation today:

| Measurement | Rows |
| --- | ---: |
| Durable sidecar truth (derivation lead, workspace `sase_22`) | 134 |
| Aggregate as report b measured it (~18:29) | 161 |
| Aggregate now (mtime 18:29:30) | **95** |

The index lost roughly a third of its rows inside one afternoon. Consequence for this
pane: **ship link *navigation*, not link *filtering*.** A `linked:false` or `-has:links`
filter over an index that silently drops rows returns confidently wrong answers. Reserve
the field seam on the row; enable `relation:`, `artifact:`, and `linked:` only after the
derivation report's Phase 0 lands.

### 6.2 The three things the pane owes

1. **Add an `agent` branch to `_known_target_for_ref`.** It has no such branch today, so
   the `_target_for_ref` fallback only matches by accident. The branch should match (a)
   the bare local name and (b) a row whose `canonical_global_name` equals the payload.
   That one branch makes all 45 live refs land, containers included.
2. **Load an `ArtifactLinksSnapshot` on the pane worker and pass `known_targets` to
   `artifact_link_edges`**, the way `files_pane` does. `with_artifact_link_relations`
   appends `links` / `linked_by` automatically, so the declaration itself is free.
3. **Normalize the ref form on read, not on write.** 44 of 45 live refs are bare local
   names, 1 is owner-qualified; match either. Do not rewrite stored rows — that is
   link-graph scope with open work already on the write path.

### 6.3 Seams to leave open for steps 2 and 3

- Do not assume `agent:<name>` is unique across time (§1.2(d)).
- Do not resolve `agent:` refs through the sidecar alone (93%, and git-synced).
- Do not flatten relation metadata further. `_emit_link_edge` already discards
  `relation`, `description`, `origin`, and `uses`, keeping the slug only inside
  `_edge_key`. This pane will carry the graph's largest edge population, so it is the
  natural place for a typed relation rail to land — leave room for it.
- Every row should expose a stable `ArtifactEntryTarget`, a canonical artifact
  reference, source project, available relations, open/copy locators, and mutation
  capability facts separately from relation facts. That is enough for a later generic
  "link this artifact to …" host action — and for chops to point at canonical agent
  targets — without importing an Agents widget.

---

## 7. Pane contract details

| Fact | Value | Why |
| --- | --- | --- |
| `pane_id` | `agents` | `_target_for_ref` already emits it |
| Label | `Agent` | fixed panes use singular labels: Patch, Stitch, Bead, File |
| Position | **immediately before Files** | Files is pinned to the last digit by rule; this keeps `stitches`=1 … `ref:research`=5, `agents`=6, moves `files` 6→7 |
| `has_inventory` / `has_fields` / `has_stable_identity` | true | earns query history, saved queries, stable marks |
| `has_revisions` | false | shell lineage is a relation, not document versions |
| `can_mutate` | **true** | revive is a `PaneCapability.MUTATION` verb; `agents_revive` must be added to `CAPABILITY_HOST_ACTIONS[MUTATION]` or conformance fails |
| `project_scoped` | true | required for conformance; nearly a no-op on this machine (92.9% one project) but not on others |
| `has_detail` | true | |
| Relations | `family`, `clan`, `retry_chain`, `parent` + auto `links` / `linked_by` | |
| Grouping | `by_family` (default), `by_state`, `by_project`, `by_status`, `by_date` | grouping presents the query result; it is never a second filter |
| Status counters | active, attention, failed, dismissed, revivable | |
| Revive key | `agents_revive: "w"` | `R` is `refresh` in the `app` keymap; `w` matches `beads_launch_work: "w"` as the pane's launch-ish verb |
| Feature flag | disabled beta via `sase flag new` | core memory: user-reaching behavior landed before it is ready must be flagged |

The flag is not optional. Create it only through `sase flag new <key>` (which also files
its removal bead); a reasonable key is `artifacts_agents_pane`. The Off branch omits the
descriptor and preserves today's inventory exactly. The removal gate should require:
query correctness against the goldens, exact link navigation for solo/member/family/
owner-qualified spellings, revival from both surfaces, measured responsiveness at the
full 12k corpus, and no regression on the main Agents tab.

Add the pane id, icon, accent, descriptor, adapter, profile registry entry, and
`ArtifactsView._compose_pane()` branch together, so no half-configured target ever
exists.

**Naming.** "Agents tab" versus "Artifacts → Agent pane" will be ambiguous in prose and
in help text. Spend one sentence in the help modal distinguishing the live control room
from the historical catalog.

---

## 8. Open questions, each with a default

**Q1. Does this replace the main Agents tab?**
*Default: no.* The main tab is the live control room — attention state, folds,
orchestration, live workflow children. The pane is the durable, query-first catalog.
They share the dialect and the revival implementation, not a widget. Revisit deprecation
only after usage shows the catalog covers the saved-group revival gesture.

**Q2. What backs a row — registry, artifact index, sidecar, or the live list?**
*Default: the registry, with the artifact index and dismissed archive left-joined.*
45/45 versus 27/45 on live refs (§1.1); 91.6% enrichment; 239 ms complete snapshot.
*Would reopen if:* the registry JSON grows past ~50 MB, at which point it wants the same
SQLite treatment the bundle archive already got.

**Q3. Is a row a name or a run?**
*Default: a named run.* Display identity is the name; row identity carries
`raw_suffix` / `artifacts_dir`. Family and clan reservations are rows with
`kind:family` / `kind:clan` and no run attributes, because 38% of live refs address
them.

**Q4. New profile dialect, or extend `ace/agent_query`?**
*Default: new profile dialect, and delete the 1,189-LOC fork — but in a separate,
independently revertible change, after the pane ships.* Shipping a third agent dialect
to fix a duplicate-dialect problem is the worst outcome available.

**Q5. `boolean=True` or flat?**
*Default: `boolean=True`.* The Agents tab already has AND/OR/NOT and parens. Cost:
boolean panes lose `key:a,b` OR-lists and `-key:x`; users write `key:a OR key:b` and
`NOT key:x`, which is closer to what Agents users already type anyway.

**Q6. Is `age>2h` worth extending the shared grammar?**
*Default: no, and no sugar either.* `until:2h` / `since:2h` already express it with hour
granularity, and `min:` / `max:` cover runtime with minute granularity (§3.2). Document
the `Nm` months-versus-minutes collision in both hints. Revisit a general comparison
operator only if a third expressiveness gap appears; `retry` equality-only is gap #2.

**Q7. Does the corpus include dismissed, hidden, and workflow-child rows?**
*Default: the query corpus includes everything; the default presentation scope excludes
`hidden:true` and `kind:workflow-child`.* 4,583 of 8,062 indexed rows are hidden and
~20,000 archived bundles are workflow children — showing them by default buries what a
person is looking for. Navigating to an excluded target clears the query rather than
failing.

**Q8. Rust core or Python module for the reconciliation?**
*Default: Textual-free Python module now, wire shapes designed to move; promote to
`sase-core` when the CLI lands.* The registry is Python-owned JSON today; moving store
and reconciliation together would triple the pane's scope before a second frontend
exists to need it.

**Q9. Revive key, and does the pane get `R`?**
*Default: `agents_revive: "w"`; `R` stays `refresh`.* Alternatives are `A` (mirroring
`plans_approve`) or `enter` with a confirm. Do not shadow refresh on one pane.

**Q10. Should this also be a CLI (`sase agent search`)?**
*Default: not in the first pass, but author the row model so it can be.*
`agent_query/evaluator.py`'s docstring already anticipates it, and `ProcQueryFilter`
proves a profile dialect works headless. Keeping the row builder Textual-free makes the
CLI a thin wrapper rather than a rewrite — and it is the event that justifies promoting
the reconciliation to `sase-core` (Q8).

**Q11. Retire `DismissedAgentSelectModal` and the `R` panel?**
*Default: reroute now, retire later, and never both at once.* Point `custom_search` at
the pane with a seeded query; keep `R` and the saved-group flow untouched; delete the
archive modal — keymaps, commands, copy targets, help rows and all — after a release of
real use.

**Q12. Are artifact-link fields queryable in v1?**
*Default: navigation yes, filtering no.* The aggregate lost ~40% of its rows inside one
afternoon (§6.1). Enable `relation:`, `artifact:`, and `linked:` after the derivation
report's Phase 0 fix.

**Q13. Detail panel — published page or local data?**
*Default: local data first, published page as a section.* The page is 93%-available,
git-synced, and can disagree with local truth. Render local identity, kind, state,
timing, model, family/clan/tribe, retry lineage, and links; then a "Published page"
section, and a copy-`reference` target that emits the canonical
`agent:<canonical_global_name>` form.

**Q14. Is `agent:0b4` resolving to a family a defect to fix here?**
*Default: no — it is correct behavior, and the pane models it.* `0b4` *is* a family
container. What is worth filing separately is the write-path question of whether
`created_by` should record the member that did the work rather than the family — that
belongs with step 2.

**Q15. Does this need a feature flag?**
*Default: yes.* Core memory mandates one for user-reaching behavior landed before it is
ready. Create it with `sase flag new`, test both states, and gate removal on §7's list.

---

## 9. Implementation plan

Each phase is independently testable, and the risky one is last.

**Phase 0 — flag and contracts.** Create the disabled beta with `sase flag new`. Add
contract tests for the descriptor, capabilities, query profile, and stable-target shapes
in both flag states. Add identity fixtures covering solo, family, clan, member, an
owner-qualified name, a collision-history name, a workflow child, and a name-only row.

**Phase 1 — the dialect, headless.** Author `agents_query_schema()` with the §3.3 field
set and `boolean=True`; register `"agents"` in `_BUILTIN_SCHEMA_BUILDERS`. Add dialect
goldens to `tests/ace/tui/artifacts_contract/goldens/query/` and cross-language parity
cases for the two date-bound pairs and the duration pair. No UI. ~120 lines plus tests.

**Phase 2 — the row model, headless.** Load the registry; left-join the artifact index
by `artifacts_dir` (projection only, never `record_json`) and the dismissed summaries by
`raw_suffix` **filtered to `is_workflow_child = 0`**; derive `kind`, `revivable`,
`family`, `dismissed`, and `attention`; emit an immutable snapshot of typed rows.
Benchmark it beside `bench_artifacts_jk.py` with a ≤400 ms budget against the measured
239 ms. ~250 lines plus tests.

**Phase 3 — the pane.** Register the `_BuiltinAdapter` per §7 and insert before Files.
Build the widget on the `files_pane.py` template (342 lines, the closest structural
analogue: index-backed, snapshot-loaded), using `ArtifactQuerySession` +
`compile_artifact_query_index` for evaluation. Add the `agent` branch to
`_known_target_for_ref` and load an `ArtifactLinksSnapshot` on the worker. Conformance
runs automatically the moment the pane appears in `resolve_artifacts_subtabs()`.
~750 lines plus a filter bar.

**Phase 4 — revival.** Add a completion delta to `_do_revive_agent(s)` and make the
main-tab refilter a consumer of it rather than an unconditional side effect (§5.2).
Register `agents_revive` under `MUTATION` and bind `w`. Wire single, marked-batch, and
family-banner selection. Reroute `SavedAgentGroupRevivalModal`'s `custom_search` to the
pane with a seeded query. Keep `R`. Test partial batch failure and cross-surface cache
invalidation.

**Phase 5 — migrate the Agents tab, delete the fork.** Point the tab's query path at the
shared profile, give it a real `FilterBar` instead of the modal query editor, and delete
`sase/ace/agent_query/`. **Land this alone so it can be reverted alone** — it changes
behavior on the app's default startup tab.

Rough size: ~+1,200 production lines across phases 1–4, −1,189 in phase 5, with
conformance and query goldens doing most of the regression work.

---

## 10. Verification

| Area | Required evidence |
| --- | --- |
| Contract | `sase artifact pane show agents` reports the expected capabilities and profile; Off state reproduces today's inventory exactly |
| Dialect | Rust/Python parity corpus; boolean precedence; both date-bound pairs; the duration pair; the `Nm` collision documented and tested |
| Identity | bare local, canonical global, owner-qualified, member, family, clan, collision-history, and name-only rows all resolve and copy durable references |
| Row model | 0 ambiguous dismissed joins; 91.6% enrichment; thin rows render with a "no run data" state |
| Scale | 12k-row corpus; bounded option count; stale worker rejection; no `record_json` read |
| Detail | lazy hydration and cancellation; selection generation prevents late overwrite |
| Revival | single, marked batch, family banner, workflow children, partial failure, and correct index/bundle ordering; both surfaces refresh |
| Regression | the main Agents tab's `R` modal, saved groups, and selection behavior are unchanged |
| Relations | family/clan/retry edges; inbound and outbound `agent:` navigation; a jump to a row the current query excludes clears the query |
| Visual | narrow and wide layouts, family banners, status counters, empty/error/loading states |

This is a TUI change, so run the project's `just check` lane plus the dedicated visual
snapshot suite for intentional visual changes, and gate landing on monitored
`just check-full`.

---

## 11. What not to do

- **Do not build a third agent query dialect.** The reason `agent_query` is worth
  deleting is that it was built this way once already.
- **Do not back the pane with the artifact index alone.** 5 of 45 live refs.
- **Do not back it with the live Agents tab's in-memory list.** It cannot revive by
  construction — dismissed agents are exactly what it excludes.
- **Do not treat the published sidecar page as identity.** 93% coverage, git-synced,
  and a family page and a member page describe different things.
- **Do not join the dismissed archive on `raw_suffix` without `is_workflow_child = 0`.**
  6,890 distinct keys across 26,657 rows; one suffix carries up to 11 bundles.
- **Do not read `bundle_path` from the registry.** 99 of 12,328 entries have one.
- **Do not `SELECT *` the artifact index.** `record_json` is 117 MB.
- **Do not page JSON bundle files for filtering.** The SQLite summary index scans in
  36 ms for the rows that matter.
- **Do not use the pure-Python profile evaluator as the production matcher.** It is
  parity-test-only by design.
- **Do not delete the `R` revival panel in this work.** Saved dismissal groups are a
  distinct gesture with their own durable store and revival counters.
- **Do not ship completeness-sensitive link filters.** The aggregate lost ~40% of its
  rows in one afternoon.
- **Do not rewrite stored `agent:` link rows to canonical form here.** Match both forms
  on read.
- **Do not show hidden rows or workflow children by default.** 57% of indexed rows are
  hidden; ~75% of archived bundles are workflow children.
- **Do not migrate the main Agents tab in the same change as the pane.**

---

## Recommended solution

Implement **Artifacts → Agents** as a fifth built-in `ArtifactsPaneContract` adapter,
inserted immediately before Files, behind a disabled `artifacts_agents_pane` beta flag.
Keep the main Agents tab as the live control room; the pane is the complete, query-first
historical catalog.

**Back every row with the agent name registry**, left-joining the artifact index (column
projection only) and the dismissed bundle summary index (top-level bundles only). That
is the only spine that resolves 100% of live `agent:` refs, it enriches 91.6% of rows,
and a complete snapshot costs 239 ms on a worker thread. Rows that enrich from nothing
still appear, thin, with an explicit "no run data" state — a thin row beats today's
dangling target. A row's display identity is its name; its row identity carries the run,
because 53% of names have been recycled.

**Distinguish containers from runs with one `kind` field**, not two record types. 38% of
live `agent:` refs name a family, so families are first-class rows; the family banner
over member rows that report a asked for is the default *grouping* over that one row
set.

**Author `agents_query_schema()` as a shared profile with `boolean=True`**, and evaluate
through the Rust `ArtifactQueryIndex` + `ArtifactQuerySession` path every other pane
already uses. Spell time with the host's existing bound keys — `since` / `until` over
started-at, `after` / `before` over finished-at, `min` / `max` over runtime — which
covers `age>2h` as `until:2h` with no host grammar change and no rewrite layer, at the
cost of documenting that `5m` means months in a date bound and minutes in a duration
bound. Gate content search behind an AST walk; add `content:` only when a persistent FTS
index exists.

**Keep one revival implementation.** Add a completion delta to `_do_revive_agent(s)` and
make the main tab's refilter a consumer of it, so the pane can invalidate and reselect
without a second copy of a 394-line mutation path. Bind `w` on the pane; leave `R` as
refresh on Artifacts and as the saved-group modal on Agents. Reroute that modal's
`custom_search` into the pane with a seeded query — that retires the offset-paging
archive modal, which is the defect actually being felt, without touching the gesture
that works.

**Owe the link graph exactly three things**: an `agent` branch in
`_known_target_for_ref`, an `ArtifactLinksSnapshot` loaded on the pane worker, and
read-side tolerance of both bare and owner-qualified ref forms. Show link edges; do not
ship link *filters* until the aggregate stops losing rows.

Land in this order: **flag and contracts → dialect (headless) → row model (headless) →
pane → revival → Agents-tab migration and fork deletion**. The last phase is the only
risky one and is revertible on its own. At the end of phase 3 the majority of the
artifact-link graph resolves for the first time, which is what makes steps 2 and 3 of
the owner's plan worth building.
