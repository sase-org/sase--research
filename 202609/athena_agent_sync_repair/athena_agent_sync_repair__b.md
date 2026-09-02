---
create_time: 2026-09-02
updated_time: 2026-09-02
status: research
---

# Cross-Machine Agent History Arrives Through The Wrong Door

**Research question:** Why do agents that ran on `athena` show up on `kellys_mbp` as
undismissed, prompt-less, family-less root rows named `athena.<hood>--code`, and what
should SASE's architecture do so that imported history is dismissed by default, fully
revivable, and named in a way that is correctly scoped to the configured owner?

**Scope:** `sase` at `8b0c65476` (`v0.17.1+30.gae7ca2226`), `sase-core` at `51df9061`,
plus the live state of this machine (`bbugyi200` / `kellys_mbp`) and the
`gh_sase-org__sase` agents sidecar, inspected on 2026-09-02. This is architecture
research; no runtime state was mutated. Every number below was measured, and the
commands that produced them are in the appendix.

## Bottom line

The three symptoms are not three bugs. They are one bug with three faces.

`athena` publishes its agent history **twice**: a complete, modern **v2** owner-sharded
payload (1,963 validated hood packages, 9,183 run pages, 1,046 family containers) and a
**stale, frozen legacy v1** manifest (338 entries, last refreshed 2026-07-23). This
machine has imported **only the v1 payload** — all 338 of it — and **zero** of the v2
payload. The v1 compatibility shim is a deliberately lossy path that does not dismiss,
does not carry prompts, does not localize family names, and does not reconstruct
topology. Everything the screenshot shows follows from that.

Worse, the v1 import is self-perpetuating. It writes 651 `origin: import_v1` entries into
the permanent agent-name registry — 97% of this machine's registry — and those entries
make **every** v2 hood import fail with
`ImportedNameCollisionError: owner namespace 'athena' is already occupied`. There is no
v1→v2 upgrade rule. The 1,948 pending v2 hoods behind the `⇅ 1948` badge cannot ever
land while that state exists. The machine is wedged on the broken path.

Underneath sits the real architectural fault: **provenance is encoded as a dotted string
prefix in the same namespace as hoods.** `athena.7n--code` is parsed by
`sase_core::agent_identity` as hood `athena`, family `athena.7n`, role `code`. The owner
root is structurally indistinguishable from a hood segment, so every downstream consumer
— hood grouping, the neighbor roster, the name registry, ACE's tree builder,
`globalize_owned_agent_name` — reads provenance as topology and gets it wrong.

The recommendation is a three-layer fix: **retire v1 as an import source**, **teach
`sase-core` a typed owner root** so the machine prefix is provenance rather than a hood,
and **add a v1→v2 adoption rule** so machines already wedged (this one) heal on the next
`sase agent sync` instead of needing a manual purge.

---

## 1. What the screenshot actually shows

The Agents tab row `athena.7n--code`, DONE, Jul 13 08:05, 21m40s, "athena hood · 71
neighbors", "No prompt file found." Its complete on-disk artifact is one file:

```json
// ~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202607/13/20260713074417/agent_meta.json
{
  "agent_family": "7n",
  "agent_family_role": "code",
  "chat_path": "~/.sase/chats/202607/imported-athena_7n__code-260713_074417.md",
  "imported_digest": "59c404d7…",
  "imported_from_machine": "athena",
  "imported_owner_kind": "username_unknown_v1",
  "name": "athena.7n--code",
  "workflow_name": "7n",
  …
}
```

Four things are visible in that one object:

| Field | Value | Problem |
| --- | --- | --- |
| `imported_owner_kind` | `username_unknown_v1` | Came through the **legacy v1** shim, not v2 |
| `name` | `athena.7n--code` | Localized (machine-qualified) |
| `agent_family` | `7n` | **Not** localized — points at a family that does not exist locally |
| *(absent)* | no `parent_timestamp`, no `raw_xprompt.md`, no `state.json` | No topology, no prompt, nothing to revive from |

`name` and `agent_family` live in two different namespaces. That single inconsistency is
why a `--code` member that plainly belongs to family `athena.7n` renders as a root node.

Measured local state:

- 354 agent artifacts on this machine. **338 of them (95%) are v1 imports from athena.**
  Only 16 are genuinely local.
- 672 permanent name-registry entries. **651 (97%) have `origin: import_v1`.** 21 are local.
- 364 registry entries live under the `athena.` namespace root.
- **287 bare local names are squatted** by athena's *source-local* family and workflow
  names (`06`, `09`, `0j`, `0e.w1.w1.w1.f1`, …), because the v1 import registers the
  unlocalized `agent_family` / `workflow_name` verbatim.

That last one is not cosmetic. `ensure_local_namespace_available` treats any
`origin: import_v1` prefix entry as a reserved foreign owner namespace:

```
06     -> BLOCKED: agent name '06' is inside reserved owner namespace '06'
06.f1  -> BLOCKED: agent name '06.f1' is inside reserved owner namespace '06'
```

287 short local hood names on this machine can no longer be allocated to locally launched
agents, because athena's history claimed them.

---

## 2. The causal chain

### 2.1 athena publishes both transports; only the dead one landed

The sidecar at `~/.sase/projects/gh_sase-org__sase/repos/agents` contains both layouts
simultaneously:

| Payload | Size | Last refreshed |
| --- | --- | --- |
| v1 `manifest.json` + `agents/athena.*` | 338 entries / 238 hoods | 2026-07-23 (frozen; publication no longer refreshes v1) |
| v2 `users/bbugyi200/machines/athena/**` | 2,011 hood dirs, **1,963 validated packages**, 10,229 agent pages (9,183 runs + 1,046 family containers), 1,602 family pages | current |

`sase agent sync --check --json` reports `pending_updates: 1948` — every one of them
`source_owner_kind: "exact"`, `source_machine: "athena"`, `format_version: 2`, totalling
**9,484 runs and 1,565 families** — cached since 2026-09-01 06:30 and never applied.
(1,963 discovered − 15 quarantined = 1,948 pending.) That is the `⇅ 1948` badge in the
screenshot's title bar.

The import receipts tell the other half: `~/.sase/agents_sync/receipts/gh_sase-org__sase.json`
holds **238 receipts, all `source_owner_kind: "username_unknown_v1"`**, applied
2026-09-02 07:28:46–07:29:14. Zero v2 receipts. A filesystem sweep confirms it — **no
artifact on this machine carries `imported_source_owner`**, the v2 provenance marker.

### 2.2 The v1 shim is a lossy path by construction

`sase/agents_sync/bundles.py::_imported_markers` is the whole of the v1 import. Compare
it to `sase/agents_sync/v2_import_rendering.py`:

| Capability | v1 shim (`bundles.py`) | v2 import (`v2_import_*`) |
| --- | --- | --- |
| Dismissed on import | **no** | yes (`dismissed_identities` → `dismissed_agents.json`) |
| Dismissed-agent bundle written | **no** | yes |
| Saved family group for `R` revival | **no** | yes (`saved_family_group`, `source: "agents_sidecar"`) |
| `agent_family` localized | **no** (verbatim `7n`) | yes (`family.localized_name`) |
| `agent_clan` localized | **no** | yes |
| `parent_timestamp` / topology | **no** | yes (`workflow_parent` relationship → destination id) |
| Prompt (`raw_xprompt.md`) | **no** — the v1 bundle carries no prompt at all | yes, when published |
| `prompt_steps` / `embedded_workflows` | no | yes |
| Commits | metadata only | `imported_commits.json` |
| Owner identity | machine only, username unknowable | full `(username, machine_name)` |

The v1 `AgentBundle` type is `metadata + commits + chat_bytes`. There is no prompt field
in the wire, which is why the detail pane says *"No prompt file found."* and why these
runs are not revivable in any useful sense.

The docs already say this outcome should not happen — "A valid remote run becomes a
terminal historical artifact **and dismissed-agent bundle**, not a live process"
(`docs/agents_sidecar.md`). That contract is only implemented on the v2 path.

### 2.3 The keystone: the v1 import permanently blocks the v2 import

This is the finding that makes the machine unfixable by ordinary means. Planning a v2
import for any athena hood fails immediately:

```
00 -> FAILED ImportedNameCollisionError imported agent name 'athena.00' collides: owner namespace 'athena' is already occupied
06 -> FAILED ImportedNameCollisionError imported agent name 'athena.06' collides: owner namespace 'athena' is already occupied
7n -> FAILED ImportedNameCollisionError imported agent name 'athena.7n' collides: owner namespace 'athena' is already occupied
```

`sase/agent/names/_registry_mutation_support.py::ensure_import_namespace_available`
walks every registry entry under `source_root = "athena"`. **All 364 of them offend**:

```
('athena',              'auto_prefix', container_kind=None, namespace_kind=None, origin='import_v1', source_owner=None)
('athena.06--code',     'claimed',     container_kind=None, namespace_kind=None, origin='import_v1', source_owner=None)
('athena.09--code',     'claimed',     …)
… 361 more
```

The v2 claim arrives with `source_owner = (bbugyi200, athena)`. The guard's branches are:

```python
if raw_entry.get("container_kind") == "owner_namespace":
    …tolerates matching owner, foreign_username, sibling_machine…
elif source_owner is not None:
    existing_owner = entry_source_owner(raw_entry)   # None for every v1 entry
    if existing_owner == source_owner or …:          # None != (bbugyi200, athena)
        continue
elif source_owner is None and raw_entry.get("origin") == "import_v1" …:
    continue                                          # v1-over-v1 is tolerated
raise ImportedNameCollisionError(…)
```

**v1-over-v1 is tolerated. v2-over-v1 is not.** There is no rule that says "a v2 package
whose owner's `machine_name` equals this v1 entry's `legacy_source_machine` is the same
history, upgraded." So the correct import can never displace the broken one.

Two secondary defects compound it:

1. The v1 claim path *does* try to reserve the root properly —
   `entries.setdefault(source_machine, owner_namespace_entry(source_machine,
   namespace_kind="legacy_source_machine"))`. But the periodic registry rescan
   (`_registry_scan_collectors.collect_owner_namespace_entries`) also uses `setdefault`,
   and by then `athena` already exists as an `auto_prefix` entry derived from the
   artifact name. **`setdefault` cannot upgrade an existing entry**, so the typed
   `owner_namespace` reservation is silently lost and the untyped `auto_prefix` wins.
2. Even if the root *were* correctly typed, `ensure_import_namespace_available` only
   tolerates `namespace_kind == "sibling_machine"` for a v2 source, never
   `"legacy_source_machine"`. So the v1→v2 hole exists at two independent levels.

### 2.4 Local dismissal then forges local ownership

When the user dismissed these rows by hand (the `Dismissed 173 agents` /
`Dismissed 95 agents` entries in `~/.sase/procs/procs.jsonl`, 14:07–14:09 today), the
dismissed-bundle writer round-tripped the names through `globalize_owned_agent_name`.
The registry now contains:

```json
"collision_owners": [{
  "name": "athena.06--code",
  "canonical_global_name": "bbugyi200.kellys_mbp.athena.06--code",
  "origin": "local",
  "source_owner": {"username": "bbugyi200", "machine_name": "kellys_mbp"}
}]
```

An agent that ran on **athena** is now recorded with a canonical global name asserting it
ran on **kellys_mbp**. Verified live:

```
globalize_owned_agent_name("athena.7n--code") -> "bbugyi200.kellys_mbp.athena.7n--code"
```

If this machine ever published that hood, it would claim authorship of athena's history in
the shared sidecar. `globalize_owned_agent_name` has no notion that `athena` is a foreign
owner root, because — see next section — nothing tells it.

---

## 3. Requirement-by-requirement gap analysis

### 3.1 "Should be dismissed by default"

**v2 already satisfies this.** `v2_import_transactions.py` stages a dismissed bundle per
run, records `dismissed_identities` in the transaction journal, and
`_record_imported_dismissed_agents` merges them into `dismissed_agents.json` inside the
same transaction. ACE's loader filters `agent.identity in self._dismissed_agents`, so
they never reach the Agents tab.

**v1 does not, and cannot be cheaply retrofitted** — it has no bundle renderer, no
transaction, and no group archive. The gap closes by deleting the path, not by patching it.

### 3.2 "Should be fully revivable"

Revival (`R` on the Agents tab) restores a dismissed run from its bundle and, for a
sequential family, relaunches the whole saved group. That needs: the raw prompt, model /
provider / effort, workflow, family + clan topology, parent linkage, tribe, and patch
name. Status per transport:

| Needed for revival | v1 | v2 | Gap |
| --- | --- | --- | --- |
| Raw prompt | never | when published | **35% of published run pages (3,247 of 9,183) have no `prompt.md`** |
| Chat transcript | yes | when readable | 27% (2,524) missing |
| Model / provider / effort | yes | yes | — |
| Family / clan container | broken (unlocalized) | yes, localized | — |
| `parent_timestamp` | never | yes | — |
| Saved family group | never | yes | — |
| `submitted_xprompt.md`, `xprompts.json` | never | **never** | expanded prompt is not reproducible cross-machine |
| Workspace / branch / patch linkage | excluded by design | excluded by design | a revived run cannot resume its patch |

The 35% prompt gap is a **publisher-side durability hole, not a transport hole**.
`inventory_sources.py:148` reads the prompt from the live artifact
(`artifact / "raw_xprompt.md"`) at publication time. If the artifact was chopped or
cleaned before its hood was published, the prompt is gone forever. Publication is
opportunistic where it should be guaranteed.

### 3.3 "Names should be scoped to the configured machine/user"

The localization *rule* is already right. `sase_core::agent_identity::localize_agent_name`
does exactly what was asked, verified live:

| Source owner | Global name | Localized on `bbugyi200@kellys_mbp` |
| --- | --- | --- |
| `bbugyi200@athena` (same user, other machine) | `bbugyi200.athena.7n--code` | `athena.7n--code` |
| `alice@athena` (other user) | `alice.athena.7n--code` | `alice.athena.7n--code` |
| unknown@athena (v1) | `athena.7n--code` | `athena.7n--code` |
| `bbugyi200@kellys_mbp` (exact owner) | `bbugyi200.kellys_mbp.7n--code` | `7n--code` |

`bbugyi200.` is stripped precisely because the configured username matches; a different
configured username keeps it. That is the requested behaviour.

**What is broken is what happens to that prefix afterwards.** The prefix is plain text in
the same dotted namespace as hoods, so:

```
agent_local_hood("athena.7n--code")          -> "athena"       # should be "7n"
parse_agent_family_name("athena.7n--code")   -> family "athena.7n", role "code"
agent_name_ancestors("athena.7n--code")      -> ["athena", "athena.7n"]
foreign_agent_owner_root("athena.7n--code")  -> None           # not recognized as foreign!
globalize_owned_agent_name("athena.7n--code")-> "bbugyi200.kellys_mbp.athena.7n--code"
```

Every athena run on this machine therefore lands in a single fabricated hood named
`athena` — "athena hood · 71 neighbors" in the screenshot, and 9,484 neighbors once the
v2 payload lands. Hood grouping, the neighbor roster, ancestor chains, `@agent:` link
targets and `--tribe`/`@hood` query scoping are all computed against a hood that does not
exist.

`foreign_agent_owner_root` returning `None` is the second half of the problem. It only
recognizes roots present in `AgentIdentitySnapshot.sibling_machines`, which
`config/_owner.py::discover_machine_names()` derives **solely from machine-overlay
discriminators that happen to exist on the local disk**. This machine has exactly one
overlay, `~/.config/sase/sase_kellys_mbp.yml`, so:

```
owner: (bbugyi200, kellys_mbp)   siblings: ('kellys_mbp',)
```

`athena` is not a known sibling. SASE has imported 338 runs from athena, holds 1,963
validated athena hood packages, and can read `users/bbugyi200/machines/athena/` in the
sidecar — and still does not know that `athena` is a machine. Provenance recognition
depends on a foreign machine's config file being copied here, which is an accident of
dotfile deployment rather than a fact SASE derives from its own data.

Finally, **ACE never displays provenance at all.** Grepping `src/sase/ace` for
`imported_source_owner` / `imported_from_machine` returns nothing; `imported_transaction_key`
is read only for transaction visibility. The dotted name prefix is the *only* signal a
user gets that a row came from another machine — which is exactly why it was jammed into
the name in the first place.

---

## 4. The architectural fault, stated plainly

> SASE transports agent identity correctly and then destroys it on arrival by flattening
> a three-part identity `(owner, hood-path, role)` into one dotted string, and parsing
> that string with functions that have no owner parameter.

Publication is fine: `users/<username>/machines/<machine>/hoods/<hood>/` keeps the three
parts separate, and `agents/<username>.<machine>.<hood-path>--<role>/` is unambiguous
because the owner is always fully spelled. Import collapses them. From that moment the
owner is only recoverable by string-matching against a set (`sibling_machines`) that is
populated from the wrong source.

Two invariants that ought to hold, and do not:

1. **An owner root is never a hood.** Today `agent_local_hood` cannot tell them apart.
2. **Provenance is one-way.** An imported run must never be re-globalized under the local
   owner. Today `globalize_owned_agent_name` does exactly that, and the corrupted result
   is already persisted in this machine's registry.

---

## 5. Alternatives considered

**A. Fix the v1 shim to match v2 (dismiss, localize families, synthesize topology).**
Rejected. v1's wire has no prompt, no relationship graph, and no username, so
"synthesize topology" means guessing. The docs already declare v1 publication frozen and
`sase agent retire-v1` already exists to delete it. Investing in v1 keeps a second,
permanently inferior import path alive to be reached by accident — which is precisely the
failure being investigated.

**B. Leave names alone; only fix `agent_local_hood` to strip a known machine prefix.**
Half a fix. It repairs hood grouping but not `foreign_agent_owner_root` (still `None`),
not `globalize_owned_agent_name` (still forges ownership), and not the registry namespace
guard. It also still depends on `sibling_machines`, so it fails on any machine that lacks
the foreign overlay file — including this one.

**C. Drop the prefix entirely; keep the bare source name plus a display-only owner badge.**
Attractive but wrong. Two machines routinely reuse the same short hood names (`00`, `06`,
`7n`), so bare names collide across owners. The dotted key would stop being unique, which
breaks `@agent:` references, the name registry, and the dismissed-bundle index. The user's
stated requirement — keep the minimum disambiguating prefix — is the right call.

**D. Keep the prefix, make it typed.** Recommended. The name stays exactly as the user
asked (`athena.7n--code`, or `alice.athena.7n--code` for a foreign user), but every parse
takes the known-owner-root set and returns owner and hood as **separate** fields. The
string is a rendering of the identity, not the identity.

---

## 6. Recommended solution

Five workstreams. R1 and R2 are the ones that unwedge this machine; R3 is the durable
architecture; R4 and R5 close the revivability and presentation requirements.

### R1 — Retire v1 as an import source (small, unblocks everything)

- On **athena**: `sase agent retire-v1 --apply`. The safety gate passes — I verified all
  **238 v1 hoods are fully covered by the v2 manifest, zero uncovered**. This deletes the
  stale v1 payload from the shared sidecar; git history keeps it recoverable.
- In **code**: delete the legacy import leg (`integrate_foreign_bundles` and the
  `legacy_manifest_groups` branches of `incoming_integration.py`), leaving v1 data
  readable for owner-observation evidence but never importable. Guard the removal with a
  feature flag and a flag bead per `sase/memory/sase_flags.md`.
- This deserves a decision record: **"Legacy v1 Agent Transport Is Read-Only History,
  Not An Import Source."** It is the kind of one-way call the decisions web exists for.

### R2 — Add a v1→v2 adoption rule (so wedged machines self-heal)

R1 alone does not fix this machine: the 651 poisoned registry entries stay, and the local
`athena` root keeps rejecting v2 claims. Two mutually exclusive ways forward; **prefer the
first.**

**R2a (recommended) — adopt, don't collide.**
1. In `ensure_import_namespace_available`, accept a v2 claim over an existing entry when
   `source_owner.machine_name == existing["legacy_source_machine"]` (and, for a typed
   root, when `namespace_kind == "legacy_source_machine"`). Same history, better
   transport.
2. In `_registry_scan_collectors.collect_owner_namespace_entries`, replace `setdefault`
   with an **upgrade**: an existing `auto_prefix` entry at an owner root must be promoted
   to a typed `owner_namespace` entry (the promotion helper
   `_promote_container_over_auto_prefix` already exists next door — reuse it).
3. In the v2 import planner, match an existing v1 artifact by
   `(legacy_source_machine, artifact_timestamp, machine-qualified name)` and **refresh it
   in place** — rewriting `agent_family`/`agent_clan` to their localized names, adding
   `parent_timestamp`, prompt, commits, and `imported_source_owner` — instead of creating
   a duplicate run.
4. Retire the orphaned bare-name reservations (`06`, `7n`, …) that the v1 scan created
   from unlocalized `agent_family` / `workflow_name`, returning those 287 names to the
   local pool.

After this, a plain `sase agent sync -p sase` heals the machine: 338 broken rows are
upgraded in place and the remaining ~9,100 runs import correctly and dismissed.

**R2b (fallback) — a supported purge.** If in-place adoption proves too intricate, add
`sase agent names forget-import --machine athena --transport v1` (dry-run by default,
`--apply` to commit) that removes v1 artifacts, their dismissed bundles, and their
registry entries for one source machine, then reimports from v2. No such command exists
today, which is why the current state has no supported exit.

### R3 — A typed owner root in `sase-core` (the durable fix)

Per the `rust_core_backend_boundary` memory, all of this is core backend behavior.

1. **New core concept.** Add `OwnerRoot` and
   `parse_owned_agent_name(name, known_owner_roots) -> { owner_root: Option<OwnerRoot>,
   hood, family, role }` to `crates/sase_core/src/agent_identity/`. Make
   `agent_local_hood`, `agent_name_in_hood`, `agent_name_ancestors`, and
   `agent_link_target` take the root set and strip it before computing topology, so
   `athena.7n--code` yields owner `athena`, hood `7n`, family `athena.7n`.
2. **Known roots become derived, not configured.** Replace
   `AgentIdentitySnapshot.sibling_machines` with `known_owner_roots`, unioned from
   (a) config-overlay discriminators — today's source, (b) the registry's typed
   `owner_namespace` reservations, and (c) the agents sidecar's
   `users/<username>/machines/<machine>/` tree. Recognizing athena must not require
   athena's dotfile to exist here.
3. **Make provenance one-way.** `globalize_owned_agent_name` must **raise** on a name
   whose root is a known foreign owner root, instead of returning
   `bbugyi200.kellys_mbp.athena.7n--code`. Add a repair pass for the corrupted
   `collision_owners` rows already on disk.
4. `validate_new_agent_name` must reject a newly created local name whose first segment is
   a known owner root — a local agent may never be born inside a foreign namespace.

### R4 — Make revival data guaranteed, not opportunistic

1. **Publish the prompt at launch, not at publication.** Copy `raw_xprompt.md` into the
   prompt archive (or a content-addressed object under `files/objects/sha256/`) when the
   run starts, so artifact cleanup can never orphan it. This closes the 35% gap.
2. **Widen the wire** to `submitted_xprompt.md` and `xprompts.json`, so a revived run can
   reproduce the exact expanded prompt rather than re-expanding against a different
   machine's xprompt aliases.
3. **Materialize the imported family container as a local family root row** so `--plan` /
   `--code` / `--mon` members fold under it. The v2 import already carries the container;
   ACE needs a root row to attach them to. (`bbugyi200.athena.03w` with members
   `03w--plan`, `03w--code`, `03w--mon` is a concrete test case in the sidecar today.)
4. Add an import-side assertion: an imported run that is a family member **must** resolve
   to a locally present family container, or the hood is quarantined with a diagnostic
   rather than silently producing root rows.

### R5 — Show provenance in ACE instead of hiding it in the name

1. Surface `imported_source_owner` on the `Agent` model and render an owner badge
   (`athena`) on the row and in the detail pane. Nothing in `src/sase/ace` reads it today.
2. Group imported rows by `(owner_root, hood)` and label the neighbor roster with the
   owner, so "athena hood · 71" becomes "athena › hood 7n · 3".
3. Once R3 lands, the displayed short name can drop back to the bare `7n--code` with the
   owner shown as a badge — the durable key keeps the prefix, the display does not have to.

### Sequencing

`R2a.2` (the `setdefault` → upgrade fix) is a few lines and is a prerequisite for
everything else, because the untyped `auto_prefix` root defeats even a correct guard.
Then `R2a.1/.3`, then `R1`, then `R3`, then `R4`/`R5` in parallel. `R3` is the only item
that touches `sase-core`; per the boundary memory, its wire, bindings, and tests land
there first and the Python callers follow.

---

## 7. Acceptance checks

A fix is complete when, on this machine:

1. `sase agent sync --check --json -p sase` reports `pending_updates: []` (down from 1,948).
2. No artifact under `~/.sase/projects/gh_sase-org__sase/artifacts` contains
   `imported_owner_kind: "username_unknown_v1"` (338 today).
3. Every imported run's `agent_meta.json` has `agent_family` in the **same namespace** as
   `name` (`athena.7n`, not `7n`).
4. `agent_local_hood("athena.7n--code") == "7n"` and
   `foreign_agent_owner_root("athena.7n--code") == "athena"`.
5. `globalize_owned_agent_name("athena.7n--code")` raises.
6. The Agents tab shows **zero** imported rows before any manual dismissal, and `R` →
   *Agents sidecar* lists athena's families as revivable groups.
7. `ensure_local_namespace_available(entries, "06")` succeeds — the 287 squatted bare
   names are released.
8. A registry entry count sanity check: `origin: import_v1` → 0.

---

## 8. Out-of-scope defects found along the way

Two real problems surfaced during this research. Neither is on the critical path; both
are worth filing.

1. **15 v2 hoods quarantine on a `chat.md` digest mismatch**, all on `--mon` (monitor
   family-shell) members — e.g.
   `bbugyi200.athena.03w: file digest mismatch for 'agents/bbugyi200.athena.03w--mon/chat.md'`.
   A monitor's transcript is still growing while its hood snapshot digest is computed, so
   the published bytes do not match the manifest. This is a **publisher-side** bug on
   athena and will keep 15 hoods unimportable even after everything above is fixed.
2. **Home memory has a layout collision.** `sase memory read` fails outright with
   `LayoutCollisionError: memory exists in multiple canonical/legacy locations:
   /Users/bbugyi/sase/memory, /Users/bbugyi/memory`. Both directories exist and hold
   overlapping notes (`obsidian.md`, `sase.md`). Every reference-memory read on this
   machine is currently blocked, including project reads, because home discovery runs
   first.

---

## Appendix — reproduction

```bash
# Which transport did these rows arrive on?
cat ~/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202607/13/20260713074417/agent_meta.json

# How much v1 vs v2 is published?
S=~/.sase/projects/gh_sase-org__sase/repos/agents
python3 -c "import json;print(len(json.load(open('$S/manifest.json'))['agents']))"   # 338 v1
ls $S/users/bbugyi200/machines/athena/hoods | wc -l                                  # 2011 hood dirs
ls $S/agents | grep -c '^bbugyi200\.'                                                # 10229 v2 pages

# What is pending, and what already landed?
sase agent sync --check --json -p gh_sase-org__sase        # pending_updates: 1948, all format_version 2
python3 -c "import json,pathlib;d=json.loads((pathlib.Path.home()/'.sase/agents_sync/receipts/gh_sase-org__sase.json').read_text());print(len(d['receipts']))"   # 238, all v1
grep -rl imported_source_owner ~/.sase/projects/gh_sase-org__sase/artifacts | wc -l   # 0
```

```python
# Why no v2 hood can ever import (read-only; no state mutated)
import sys, pathlib
sys.path.insert(0, "/Users/bbugyi/projects/github/sase-org/sase/src")
from sase.agents_sync.v2_import_package import discover_agent_imports
from sase.agents_sync.v2_import_planning import build_import_preflight_context, preflight_hood
from sase.agents_sync.v2_models import V2ProjectIdentity
from sase.agents_sync.targets import resolve_sync_targets
from sase.core.agent_identity_facade import AgentIdentitySnapshot
from sase.config import require_agent_owner_identity

repo = pathlib.Path.home() / ".sase/projects/gh_sase-org__sase/repos/agents"
target = resolve_sync_targets(("gh_sase-org__sase",)).targets[0]
identity = AgentIdentitySnapshot(require_agent_owner_identity())
discovery = discover_agent_imports(repo, V2ProjectIdentity("gh_sase-org__sase", "sase"))
ctx = build_import_preflight_context(target, identity, discovery.v2_packages)
pkgs = {p.hood: p for p in discovery.v2_packages}
preflight_hood(target, pkgs["00"], identity, context=ctx)
# ImportedNameCollisionError: imported agent name 'athena.00' collides:
#   owner namespace 'athena' is already occupied
```

```python
# Identity parsing on this machine
from sase.core.agent_identity_facade import (
    AgentIdentitySnapshot, agent_local_hood, parse_agent_family_name,
    foreign_agent_owner_root, globalize_owned_agent_name,
)
snap = AgentIdentitySnapshot.current()
snap.owner              # AgentOwnerIdentity(username='bbugyi200', machine_name='kellys_mbp')
snap.sibling_machines   # ('kellys_mbp',)   <- athena unknown
agent_local_hood("athena.7n--code")            # 'athena'   (should be '7n')
parse_agent_family_name("athena.7n--code")     # family 'athena.7n', role 'code'
foreign_agent_owner_root("athena.7n--code")    # None       (should be 'athena')
globalize_owned_agent_name("athena.7n--code")  # 'bbugyi200.kellys_mbp.athena.7n--code'  <- forged
```

**Key source locations**

| Concern | File |
| --- | --- |
| v1 import (lossy shim) | `src/sase/agents_sync/bundles.py::_imported_markers`, `_create_imported_artifact` |
| v2 import (correct) | `src/sase/agents_sync/v2_import_rendering.py`, `v2_import_transactions.py` |
| Namespace guard that blocks v2-over-v1 | `src/sase/agent/names/_registry_mutation_support.py::ensure_import_namespace_available` |
| Lost `owner_namespace` promotion | `src/sase/agent/names/_registry_scan_collectors.py::collect_owner_namespace_entries` |
| Unlocalized family reservation | `src/sase/agent/names/_registry_scan_payloads.py::family_from_payload` |
| Metadata allowlists (no `parent_timestamp`) | `src/sase/agents_sync/io.py::PORTABLE_META_FIELDS`, `v2_validation.py::V2_METADATA_FIELDS` |
| Name/hood/owner parsing | `sase-core/crates/sase_core/src/agent_identity/identity.rs` |
| Sibling-machine discovery | `src/sase/config/_owner.py::discover_machine_names` |
| ACE root-vs-child decision | `src/sase/ace/tui/models/_agent_status_family_core.py`, `models/agent.py::is_family_member_child` |
