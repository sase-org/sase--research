---
create_time: 2026-09-02
updated_time: 2026-09-02
status: research
---

# Athena Agent Sync Repair: Consolidated Research

**Research question:** Agents that ran on `athena` show up on `kellys_mbp` as
undismissed, prompt-less, family-less root rows named `athena.<hood>--code`
(screenshot `~/tmp/screenshots/20260902_124640.png`). What is broken, and what should
SASE's architecture look like so that imported history is (1) dismissed by default,
(2) fully revivable, and (3) named with the minimum owner prefix for the configured
machine/user?

**Provenance:** Consolidates two independent research reports —
`athena_agent_sync_repair__a.md` (codex/gpt-5.6-sol) and
`athena_agent_sync_repair__b.md` (claude/opus) — plus a lead-researcher verification
pass on 2026-09-02 that re-checked every load-bearing claim against the live machine
state and the `sase` checkout at `8b0c65476`. Where the two reports disagreed, the
disagreement was resolved by direct measurement; resolutions are called out inline.

## Bottom line

The screenshot symptoms are **one import-path bug with three faces, plus one
independent revival-fidelity bug** that neither depends on sync nor is fixed by it.

1. **The import-path bug.** `athena` publishes its agent history twice: a complete,
   modern **v2** owner-sharded payload (1,963 validated hood packages; current) and a
   **frozen legacy v1** manifest (338 entries, last refreshed 2026-07-23). This
   machine imported **only the v1 payload — all 338 entries, zero v2**. The v1 shim is
   lossy by construction: it does not dismiss on import, carries no prompt in the wire
   at all, does not localize `agent_family`, and reconstructs no topology. And it is
   **self-perpetuating**: the 651 `origin: import_v1` registry entries it wrote (97%
   of this machine's registry) make every v2 hood import fail with
   `ImportedNameCollisionError: owner namespace 'athena' is already occupied`. The
   1,948 pending v2 hoods behind the screenshot's `⇅ 1948` badge can never land. There
   is no v1→v2 upgrade rule and no command to forget a v1 import, so the machine is
   wedged on the broken path with no supported exit.

2. **The revival-fidelity bug.** The TUI's async cleanup path serializes only a narrow
   projection of an `Agent` across a subprocess boundary
   (`src/sase/ace/tui/actions/cleanup_payload.py::serialize_agent`), then writes the
   dismissed bundle from that partial object. Verified against the live bundle for
   `athena.7n--code`: `agent_family`, `artifacts_dir`, `response_path`, `model`,
   `llm_provider`, and `reasoning_effort` are all `null`. This affects **local** agents
   too, and means manual dismissal degrades any record it touches — even a future
   correctly-imported one.

Beneath both sits the real architectural fault: **provenance is encoded as a plain
dotted prefix in the same namespace as hoods, and canonical identity is conflated with
its localized display projection.** `athena.7n--code` parses as hood `athena`, family
`athena.7n` — so every downstream consumer (hood grouping, neighbor roster, registry,
ACE tree builder, `globalize_owned_agent_name`) reads provenance as topology and gets
it wrong.

## Verified facts

Every number below was re-verified live during consolidation (registry, dismissed
bundles, sidecar, and source all re-inspected on 2026-09-02).

| Fact | Value |
| --- | --- |
| Local agent artifacts that are v1 imports from athena | 338 of 354 (95%) |
| Name-registry entries with `origin: import_v1` | 651 of 677 (96%) |
| Registry entries under the `athena.` namespace root | 364 |
| The `athena` root registry entry | `reservation_kind: auto_prefix`, `origin: import_v1`, `source_owner: null` — untyped |
| Bare local names squatted by athena's unlocalized `agent_family`/`workflow_name` (`06`, `7n`, `0e.w1.w1.w1.f1`, …) | 287, blocked via `ensure_local_namespace_available` |
| Forged collision-owner rows asserting `bbugyi200.kellys_mbp.athena.*` (created by today's manual dismissal) | 338 — every dismissed v1 import |
| v2 payload published by athena | 1,963 validated hood packages; ~9.2–9.6k runs; ~1.0–1.6k family containers (counting bases differ between manifest entries and validated pages; both reports agree on 1,963 hoods and 1,948 pending) |
| v2 imports applied on this machine | 0 (238 receipts, all `username_unknown_v1`; no artifact carries `imported_source_owner`) |
| v2 preflight for any athena hood | raises `ImportedNameCollisionError` (reproduced read-only by both researchers) |
| Published v2 run pages missing `prompt.md` | ~35% (3,247 of 9,183); among the 338 v1-matched runs, only 35 have a raw prompt |
| v1→v2 mapping for the 338 local imports | deterministic and exact — 338 unique matches, 0 unmatched (source run id recomputed from `project_key + workflow + timestamp`) |
| `athena.7n--code` dismissed bundle | `agent_family`, `artifacts_dir`, `response_path`, `model`, `llm_provider`, `reasoning_effort` all `null`; `agent_family_role: "code"` survives |

### Resolved disagreements between the two reports

- **The 15 quarantined `--mon` hoods.** Report B treated them as a live publisher-side
  bug that "will keep 15 hoods unimportable"; report A sampled one and suspected stale
  cache. **A is right about the present state:** the current sidecar (fetched
  2026-09-02 14:31) bytes for `agents/bbugyi200.athena.03w--mon/chat.md` match the
  manifest digest exactly (93,956 bytes, sha256 identical). **B is right about the
  origin:** a monitor transcript still growing while athena computed the snapshot
  digest is the plausible cause of the transient mismatch. Conclusion: the quarantines
  are stale diagnostics that a revalidation pass clears; the publisher-side race is a
  real but secondary defect worth closing so the window stops recurring.
- **Cleanup serialization loss.** Only report A found it; verified real (see above).
  It belongs on the critical path because it re-breaks revival after every manual
  dismissal, regardless of transport fixes.
- **The registry `setdefault` keystone.** Only report B found it; verified real.
  `collect_owner_namespace_entries` (`_registry_scan_collectors.py`) uses `setdefault`
  three times, so the typed `owner_namespace` reservation the v1 import path tries to
  write can never displace the untyped `auto_prefix` root the artifact rescan creates
  first. The promotion helper `_promote_container_over_auto_prefix` already exists in
  `_registry_scan_entries.py:154` and can be reused.
- **Count discrepancies** (9,632 vs 9,183 runs; 1,590 vs 1,046/1,602 families) come
  from different counting bases (owner-manifest entries vs validated pages vs pending
  set), not from conflicting evidence. The load-bearing figures — 338 v1 imports,
  1,963 v2 hoods, 1,948 pending, 0 v2 applied — agree exactly across both reports and
  the verification pass.

## The causal chain

1. **Import took the dead path.** The sidecar contains both layouts. The importer
   applied the frozen v1 manifest (`agents_sync/bundles.py`) and none of the v2 tree.
   All 238 import receipts are `source_owner_kind: "username_unknown_v1"`.
2. **v1 is lossy by construction.** The v1 wire is `metadata + commits + chat_bytes`.
   No prompt field exists ("No prompt file found" in the detail pane), no
   `parent_timestamp`, no family container, no dismissed bundle, no saved family
   group. The v2 path has all of these — `docs/agents_sidecar.md`'s contract ("a valid
   remote run becomes a terminal historical artifact **and dismissed-agent bundle**,
   not a live process") is implemented only on v2.
3. **v1 half-localizes names.** `_imported_markers` writes `name: "athena.7n--code"`
   but copies `agent_family: "7n"` verbatim. Those live in different namespaces, so
   the `--code` member can never attach to its family and renders as a root row.
   Meanwhile the registry rescan reserves the *unlocalized* family/workflow names,
   squatting 287 bare local names.
4. **v1 registry state blocks v2.** `ensure_import_namespace_available`
   (`_registry_mutation_support.py`) tolerates v1-over-v1 (its `import_v1` +
   `legacy_source_machine` branch is reachable only when the incoming claim has
   `source_owner is None`) but has no rule for a v2 claim whose
   `source_owner.machine_name` equals an entry's `legacy_source_machine`. All 364
   `athena.*` entries offend. The hole exists at two independent levels: even a
   correctly *typed* root would only be tolerated as `sibling_machine`, never
   `legacy_source_machine`, and the root is not typed anyway because of the
   `setdefault` defect.
5. **Manual dismissal forged ownership and destroyed revival data.** Dismissing the
   rows today (173 + 95 per `procs.jsonl`) round-tripped names through
   `globalize_owned_agent_name`, which has no notion of a foreign owner root, so the
   registry now holds 338 rows claiming athena's runs ran on `kellys_mbp`
   (`canonical_global_name: "bbugyi200.kellys_mbp.athena.06--code"`, `origin:
   "local"`). Simultaneously, the cleanup subprocess wrote bundles missing family,
   model, provider, artifact paths, and response paths.

## Requirement-by-requirement gap analysis

### "Dismissed by default"

**v2 already satisfies this.** `v2_import_transactions.py` stages a dismissed bundle
per run, records `dismissed_identities`, and merges them into `dismissed_agents.json`
inside the same transaction; integration tests assert staged artifacts stay invisible
and imported identities end dismissed. v1 cannot be retrofitted — it has no bundle
renderer, no transaction, no group archive. The gap closes by removing the v1 path and
migrating its data, not by patching it.

Two durability caveats stand even on v2: dismissal identity is keyed by
`(AgentType, cl_name, raw_suffix)` with no source owner or source run id, so it is
vulnerable to name reuse and re-localization; and "imported" (provenance) and
"visible" (local UI choice) should not be the same bit — visibility belongs in a
machine-local projection over an immutable record.

### "Fully revivable"

Full revival needs: raw prompt/restart input, model/provider/effort, workflow, family
and clan topology, parent linkage, chat, commits, output variables, and enough
artifact metadata to reconstruct loader markers. Current status:

| Needed | v1 | v2 | Residual gap |
| --- | --- | --- | --- |
| Raw prompt | never | when published | 35% of published run pages have none — the prompt is read from the live artifact at *publication* time (`inventory_sources.py`), so cleanup/chop before publication orphans it forever |
| Family/clan container, localized | broken | yes | ACE never materializes an imported family container as a root row, so members still need one to fold under |
| Parent linkage, saved family group | never | yes | — |
| Model/provider/effort, chat, commits | partial | yes | — |
| `submitted_xprompt.md` / `xprompts.json` | never | never | expanded prompt not reproducible cross-machine |
| Survival through later manual dismissal | — | — | **no** — the cleanup serializer loss re-nulls the bundle |

So today's records are at best *historically viewable*; most are not *restartable*.
The system should track those as distinct, validated capabilities (report A's
capability block: `historically_viewable` / `durably_revivable` / `restartable` with
explicit `missing_requirements`) rather than over-promising "revival" whenever a row
can be redrawn.

### "Names scoped to the configured machine/user"

The localization *rule* is already correct and lives in the right place
(`sase-core/crates/sase_core/src/agent_identity/identity.rs`), verified live:
`bbugyi200.athena.7n--code` localizes to `athena.7n--code` precisely because the
configured username matches, and `alice.athena.7n--code` keeps its username prefix.
Keep that behavior.

What is broken is everything *after* localization, because the prefix is untyped text
in the hood namespace:

```text
agent_local_hood("athena.7n--code")           -> "athena"   # should be "7n"
foreign_agent_owner_root("athena.7n--code")   -> None       # athena not recognized
globalize_owned_agent_name("athena.7n--code") -> "bbugyi200.kellys_mbp.athena.7n--code"  # forged
```

`foreign_agent_owner_root` only recognizes roots in
`AgentIdentitySnapshot.sibling_machines`, which is derived solely from machine-overlay
config files that happen to exist on local disk (`config/_owner.py`). This machine has
only its own overlay, so SASE holds 1,963 athena hood packages and still does not know
`athena` is a machine. And ACE never reads `imported_source_owner` /
`imported_from_machine` at all — the name prefix is the only provenance signal a user
gets, which is why provenance got jammed into the name in the first place.

**Invariant to adopt:** canonical identity is `(source_username, source_machine,
source_run_id)`; the dotted display name is a *projection* computed for the configured
destination owner and applied uniformly to run, family, parent/child references, saved
groups, and registry keys. An owner root is never a hood; provenance is one-way (an
imported run must never be re-globalized under the local owner).

## Recommended solution

Both reports converge on the same shape: **keep the v2 transport (it already has the
right semantics), migrate the wedged v1 state onto it with evidence, move identity into
a typed owner-aware model in `sase-core`, and make revival data a validated guarantee
rather than an accident of surviving files.** Sequenced:

### Phase 1 — Stop the bleeding (small, high-leverage)

1. **Fix the registry rescan `setdefault`** in `collect_owner_namespace_entries` so an
   untyped `auto_prefix` owner root is *upgraded* to a typed `owner_namespace` entry
   (reuse `_promote_container_over_auto_prefix`). This is a prerequisite for any
   correct guard behavior.
2. **Fix the cleanup serializer.** The dismiss subprocess must persist the complete
   durable record: serialize every bundle field (including `agent_family`, `model`,
   `llm_provider`, `reasoning_effort`, `response_path`) and resolve the *effective*
   artifacts dir (`get_artifacts_dir()` / index record) before crossing the process
   boundary. Longer-term, pass a versioned archive DTO instead of an ad-hoc field
   subset.
3. **Capture the raw prompt at launch, not publication.** Copy `raw_xprompt.md` (and
   ideally `submitted_xprompt.md` + `xprompts.json`) into a durable archive or
   content-addressed store when the run starts, closing the 35% prompt gap for all
   future runs.
4. **Batch sidecar reads.** Replace per-file `git show` subprocesses
   (`git_objects.py::read_bytes`) with a `git cat-file --batch` stream (or one tree
   stream per fetched commit), with manifest/snapshot digests as the incremental cache
   boundary plus progress/cancellation. A full validation pass over ~2,000 hoods
   currently takes minutes and launches tens of thousands of subprocesses; migration
   and re-validation (which also clears the 15 stale quarantines) depend on this being
   practical.

### Phase 2 — Unwedge: evidence-backed v1→v2 adoption

Add an adoption rule so wedged machines heal on the next `sase agent sync` instead of
needing a purge:

1. In `ensure_import_namespace_available`, accept a v2 claim over an existing entry
   when `source_owner.machine_name == existing["legacy_source_machine"]` (and, for
   typed roots, tolerate `namespace_kind == "legacy_source_machine"`). Same history,
   better transport.
2. In the v2 import planner, match an existing v1 artifact by the conjunction of
   evidence — legacy source machine equals the v2 source machine, the deterministic
   source-run-id recomputation matches, the v1 name equals the v2 global name minus
   the newly-known username, and shared chat/commit digests agree — and **refresh it
   in place**: localized `agent_family`/`agent_clan`, `parent_timestamp`, prompt,
   commits, `imported_source_owner`, dismissed bundle, saved family group. Unique
   matches promote atomically and idempotently; ambiguous matches quarantine with a
   diagnostic, never guess. (All 338 current rows are unique exact matches, so this
   machine migrates deterministically.)
3. **Repair the forgeries and squats** in the same transaction: remove the 338
   `bbugyi200.kellys_mbp.athena.*` collision-owner rows (only where archived
   provenance and payload digest prove same-run identity) and release the 287 bare
   names reserved by unlocalized v1 family/workflow scans.
4. **Preserve the user's chosen hidden state** — migration must not re-surface rows
   the user already dismissed.
5. Keep a fallback purge command (`sase agent names forget-import --machine athena
   --transport v1`, dry-run by default) in the design in case in-place adoption hits
   an unmigratable edge, since today no supported exit exists at all.

### Phase 3 — Retire v1 as an import source

- On **athena**: `sase agent retire-v1 --apply` (the gate passes — all 238 v1 hoods
  are v2-covered, zero uncovered) — but only *after* Phase 2 lands everywhere it is
  needed, since retire-v1 removes the source payload without repairing already-
  imported destination state.
- In code: delete the legacy import leg (`integrate_foreign_bundles`,
  `legacy_manifest_groups` branches), keeping v1 data readable as evidence but never
  importable, behind a feature flag with a flag bead per `sase/memory/sase_flags.md`.
- Record the one-way call as a decision record ("Legacy v1 agent transport is
  read-only history, not an import source").

### Phase 4 — Typed owner identity in `sase-core` (the durable fix)

Per the `rust_core_backend_boundary` memory, this is core backend behavior:

1. Add `OwnerRoot` and `parse_owned_agent_name(name, known_owner_roots)` returning
   owner root, hood, family, and role as **separate fields**; make
   `agent_local_hood`, `agent_name_ancestors`, `agent_name_in_hood`, and
   `agent_link_target` owner-aware so `athena.7n--code` yields owner `athena`, hood
   `7n`. The string becomes a rendering of the identity, not the identity.
2. Derive `known_owner_roots` from data, not dotfile accidents: union of config
   overlay discriminators, the registry's typed `owner_namespace` reservations, and
   the sidecar's `users/<username>/machines/<machine>/` tree.
3. Make provenance one-way: `globalize_owned_agent_name` raises on a known foreign
   owner root; `validate_new_agent_name` rejects local names born inside one.
4. Move whole-graph name projection into core: one call takes canonical
   owner/run/relationship data plus the destination owner and returns localized names
   for run, family, relationships, and registry namespace, so Python importers and the
   TUI stop rebuilding prefixes independently.

The bare-name-collision analysis in report B settles the naming design question: keep
the minimum disambiguating prefix in the durable key (bare names collide across
machines — `00`, `06`, `7n` are reused), but once identities are typed the *display*
can drop to `7n--code` with an owner badge.

### Phase 5 — Archive/visibility model and provenance UI

- Evolve the import destination into an immutable archive keyed by
  `(source_username, source_machine, source_run_id)` with a machine-local visibility
  projection (`hidden | visible | pinned`). Foreign terminal imports initialize
  `hidden`; revival and dismissal flip only the projection and never rewrite canonical
  provenance. Current dismissed bundles and loader markers become compatibility
  projections.
- Validate and persist explicit capabilities (`historically_viewable`,
  `durably_revivable`, `restartable`, `missing_requirements`); publication rejects a
  `restartable` assertion when prompt or model parameters are absent, and the UI never
  calls an incomplete record fully revivable.
- Materialize imported family containers as local family root rows so `--plan` /
  `--code` / `--mon` members fold under them, with an import-side assertion that a
  family member must resolve to a present container or the hood quarantines with a
  diagnostic (never silently produces root rows). Surface `imported_source_owner` as
  an owner badge on rows, detail pane, and the neighbor roster (nothing in
  `src/sase/ace` reads it today).

### Acceptance checks

On this machine, the fix is complete when:

1. `sase agent sync --check --json -p sase` reports zero pending updates (from 1,948),
   with bounded subprocess count and usable progress.
2. No artifact carries `imported_owner_kind: "username_unknown_v1"` (338 today) and
   registry `origin: import_v1` count is 0 (651 today).
3. `agent_local_hood("athena.7n--code") == "7n"`,
   `foreign_agent_owner_root("athena.7n--code") == "athena"`, and
   `globalize_owned_agent_name("athena.7n--code")` raises.
4. `ensure_local_namespace_available(entries, "06")` succeeds — the 287 squatted names
   are released — and the 338 forged `kellys_mbp` collision-owner rows are gone.
5. The Agents tab shows zero imported rows before any manual dismissal; imported
   families appear grouped (no `--code` orphan roots) in revival search, and reviving
   `bbugyi200.athena.03w` restores root + `--plan`/`--code`/`--mon` members under one
   family.
6. Dismissing an imported or index-projected agent through the cleanup subprocess
   produces a bundle byte-equivalent to the full durable record (no nulled
   family/model/paths).
7. Round-trip tests pass: owner-projection matrix (exact owner / same user other
   machine / other user / v1 unknown), publish→import→dismiss→revive content
   byte-compare, restart planning for every `restartable` capsule, transaction crash
   matrix (no partial family, claim, or visible row escapes), and legacy-promotion
   fixtures (unique promotes idempotently, ambiguous quarantines without mutation).

## Out-of-scope defects worth filing as task beads

1. **Publisher-side `--mon` digest race** (athena): monitor transcripts can grow
   between content hashing and snapshot publication, producing transient quarantines
   (15 observed, since self-healed in the sidecar but still cached locally). Fix by
   hashing the bytes actually copied into the publication, or excluding still-running
   members from the snapshot.
2. **Home memory layout collision on this machine:** both `~/sase/memory` and legacy
   `~/memory` exist, so every `sase memory read` fails with `LayoutCollisionError`
   before any project read runs. This blocked the audited memory-read path for all
   three researchers.

## Source pointers

| Concern | Location |
| --- | --- |
| v1 lossy import shim | `src/sase/agents_sync/bundles.py::_imported_markers`, `_create_imported_artifact` |
| v2 import (correct semantics) | `src/sase/agents_sync/v2_import_rendering.py`, `v2_import_transactions.py` |
| Namespace guard blocking v2-over-v1 | `src/sase/agent/names/_registry_mutation_support.py::ensure_import_namespace_available` |
| `setdefault` that loses typed owner roots | `src/sase/agent/names/_registry_scan_collectors.py::collect_owner_namespace_entries` (promotion helper: `_registry_scan_entries.py::_promote_container_over_auto_prefix`) |
| Cleanup serializer field loss | `src/sase/ace/tui/actions/cleanup_payload.py::serialize_agent`; subprocess in `src/sase/ops/commands/agent.py` |
| Prompt captured too late | `src/sase/agents_sync/inventory_sources.py` (reads live `raw_xprompt.md` at publication) |
| Per-file `git show` scaling | `src/sase/agents_sync/git_objects.py::read_bytes` |
| Identity localization (correct, keep) | `sase-core/crates/sase_core/src/agent_identity/identity.rs` |
| Sibling-machine discovery (wrong source) | `src/sase/config/_owner.py::discover_machine_names` |
| v1 retirement gate | `src/sase/agents_sync/v1_retirement.py` |

Full reproduction commands and raw measurements are in the two source reports:
`athena_agent_sync_repair__a.md` (archive/capability model, cleanup-loss evidence,
migration evidence rules, scale analysis) and `athena_agent_sync_repair__b.md`
(registry keystone, squatted names, forged ownership, typed-owner-root design,
alternatives considered).
