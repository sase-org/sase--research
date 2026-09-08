# Making Artifact-Link Conflicts Impossible (Researcher B)

## 1. Summary

Artifact-link merge conflicts are not a merge problem. They are a **write-topology
problem**: `sase artifact read` and `sase artifact link add` write durable state into
the *agent's own ephemeral workspace clone* of a document sidecar, and every agent that
touches a popular artifact writes the *same file path*. Swarm siblings finish within
seconds of each other, so two clones race to append a row to
`links/202609/<hot-doc>.md.json` and the loser gets a paused stitch and a hand-merge.

Beads already solved the identical problem, and the solution that shipped was not a
better merge — it was **canonical append-only per-entity state plus a single serialized
publisher plus regeneration-not-merging for projections**. Artifact links inherited only
one of those three properties (per-artifact file sharding). Notably, the *bead half of
the very same link graph* is already event-sourced and conflict-safe
(`src/sase/sdd/artifact_link_beads.py`); only the **document half** still uses a mutable
JSON array with no merge story at all.

**Recommendation (§8): remove agents from the artifact-link write path entirely.** Make
`sase artifact read` / `link add` inside an agent run enqueue-only, and let one
serialized host-owned writer per machine drain the queue into the hidden host-owned
sidecar clone that landed today in `sase-y3.3`. Because `upsert_artifact_link_row` is
idempotent by dedup key, a rejected push is repaired by *fetch → reset → replay → push*
— a three-way merge is never required, so there is no conflict to resolve, ever. Harden
that with an append-only JSONL shape plus `merge=union` (verified working, §6) so any
residual human/cross-machine encounter self-heals, and ship a semantic `links/` resolver
first as a same-week stopgap.

---

## 2. What actually happens today

### 2.1 The write path

`sase artifact read` records a durable `read` row **twice**
(`src/sase/artifact_cli/read.py:263-288`):

```python
outcome = store.upsert_row(row)          # -> writes the workspace sidecar clone NOW
append_artifact_link_outbox_entry(...)   # -> also queues it for later replay
```

The first call lands in `ArtifactLinkStoreSidecarMixin._upsert_sidecar`
(`src/sase/sdd/_artifact_link_store_sidecar.py:33`), which does a read-modify-write of
the whole per-artifact JSON array under an `flock` sentinel:

```python
with locked_file(artifact_link_lock_path(path), fcntl.LOCK_EX):
    index = read_artifact_link_index(path, artifact_ref=canonical)
    outcome = upsert_artifact_link_rows(index["rows"], incoming)
    atomic_write_json(path, {... "rows": outcome["rows"]})
```

The path is `links/<artifact-relpath>.json`
(`src/sase/sdd/referenced_by_index.py:9,14`), e.g.
`links/202609/sase_collaboration_architecture.md.json`.

Then finalization auto-commits that dirt
(`src/sase/finalizers/reconciliation.py:110,271` →
`commit_artifact_link_indexes`, `src/sase/sdd/_artifact_link_commit.py:54`) as a
`chore(artifact-links): persist link indexes` commit, and pushes it.

### 2.2 Why the lock does not help

The `flock` sentinel is `<workspace>/sase/repos/research/links/**/<doc>.md.lock`. Sibling
agents live in **different workspace clones** (`sase repo list` shows `research` cloned
into 5 of 24 workspaces), so their lock files are different inodes on different paths.
The lock serializes writers *within one clone* and provides **zero** mutual exclusion for
the case that actually produces conflicts.

### 2.3 Why the row order guarantees a textual conflict

`upsert_artifact_link_row` (sase-core `crates/sase_core/src/artifact_link/wire.rs:355`)
appends new rows in **insertion order**, never sorted:

```rust
rows.push(incoming.clone());
```

The file is a pretty-printed JSON array of multi-line objects. Two clones that each
append a different row from a common base produce two divergent tails ending at the same
`]` — an unavoidable text conflict. When neither side had the file (a brand-new report),
it is an **add/add** conflict, which is exactly what `research.1n.cdx` hit:

> "The conflict is a both-added artifact-link index: each side recorded a different
> agent's read of the same research artifact."

That agent then hit the conflict a *second* time on `--resume` because a third sibling
had pushed in the meantime.

### 2.4 Why nothing auto-resolves it

Both SASE rebase paths auto-resolve **bead** conflicts only:

- `src/sase/vcs_provider/plugins/_git_commit_dispatch.py:194,222` —
  `_continue_rebase_resolving_beads` bails unless `_all_bead_conflicts(files)` is true
  (`all(path.startswith("beads/"))`). A `links/...json` conflict fails that test, so the
  stitch prints "Resolve the conflict, continue the rebase, then run
  `sase stitch create --resume`" and hands the agent a merge.
- `src/sase/sdd/_repository_integration.py:195-240` — `_repair_or_abort_rebase` calls
  `resolve_bead_conflicts`, which returns `"non-bead conflicts remain: ..."` for a
  document sidecar (there is no beads dir under it) and aborts.

There is no `.gitattributes` in any sidecar, and `rerere` is deliberately disabled for
SDD repos (`src/sase/sdd/_git.py:105-110`). So a `links/` conflict has **no automated
resolution path whatsoever**.

---

## 3. Measured blast radius

Measured on this workspace's sidecar clones (2026-09-08):

| Metric | `research` | `plans` |
| --- | --- | --- |
| total commits | 451 | 6,580 |
| `chore(artifact-links)` commits | **127 (28%)** | 220 |
| tracked `links/**/*.json` files | 264 | 768 |

Row inventory across both sidecars: **1,032 index files, 1,390 rows** — an average of
1.35 rows per file. The distribution is what matters:

| origin / relation | rows | share |
| --- | ---: | ---: |
| `derived` / `implements` | 548 | 39% |
| `derived` / `derives-from` | 304 | 22% |
| `read` / `read` | 262 | 19% |
| `derived` / `cites` | 141 | 10% |
| `manual` / `derives-from` | 74 | 5% |
| `manual` / `related` | 37 | 3% |
| `prompt_ref` / `cites` | 20 | 1% |
| `manual` / `supersedes` | 4 | <1% |

Hot files carry the conflicts. Link commits per index, top of the distribution:

```
17  links/202609/sase_collaboration_architecture.md.json
11  links/202609/tailnet_agent_fleet/tailnet_agent_fleet.md.json
 9  links/202608/standalone_proc_launch_units/standalone_proc_launch_units.md.json
 8  links/202609/remote_dispatch_and_fleet_focus/remote_dispatch_and_fleet_focus.md.json
 8  links/202609/provider_subscription_usage/provider_subscription_usage.md.json
```

Consecutive link commits to `sase_collaboration_architecture.md.json` include pairs
**44 seconds** and **2m11s** apart. That is the race window, and it is not a tail event —
it is the *expected* shape of a swarm: a lead report is read by every sibling, and the
siblings finalize together.

Live evidence from this run: after two `sase artifact read` calls, this workspace's
research clone already shows `?? links/202605/` — untracked link dirt created purely by
reading, waiting to become a commit and a push race.

The problem grows with parallelism. It is a function of *(agents per swarm) x (shared hot
artifacts)*, both of which the fleet/tailnet direction increases.

---

## 4. Prior art: how beads made this rare

`sase memory read sase_beads.md` states the design in one line: *"Canonical state lives
in `beads/events/**`; `issues.jsonl` is a generated projection."* The shipped mechanism
has six parts:

1. **Per-entity append-only streams.** `events/streams/<bead-id>.jsonl`, one line per
   event (1,305 streams in the beads sidecar). Two agents working different beads touch
   different files.
2. **Regenerable projections.** `issues.jsonl`, `events/manifest.json`, and `pages/**`
   are rebuilt from the streams. Their conflicts are resolved by *regeneration*
   (`_resolve_regenerable_conflicts`), never by merging.
3. **A semantic three-way merge.** `merge_event_streams_with_relocation` in Rust core,
   driven by `src/sase/bead/conflict_resolver.py`, reads git index stages 1/2/3 and
   merges by event identity — with **ID relocation** for the genuinely-colliding case,
   allocated from whole-store state so both sides pick the same answer.
4. **Wired into every rebase path SASE controls** —
   `_repository_integration._repair_or_abort_rebase` and
   `_git_commit_dispatch._continue_rebase_resolving_beads` — with a bounded
   resolve→`rebase --continue` loop, and fail-closed on an unreadable probe.
5. **One serialized publisher.** `run_managed_sync_worker`
   (`src/sase/bead/sync_worker.py`) takes an outer worker lock, an inner store write
   lock, and retries push up to `_MAX_PUSH_ATTEMPTS = 3` with re-integration between
   attempts.
6. **`rerere` disabled** for SDD repos so a cached textual resolution cannot replay over
   the semantic merge.

Deliberately, **no git merge driver was installed** — the earlier study
(`research:202605/bead_jsonl_merge_conflicts.md`) recommended one, but the shipped answer
hooked SASE's own rebase paths instead, avoiding the per-clone `git config` install
problem entirely. That is a strong precedent to reuse.

Artifact links inherited only property (1), and only partially: they shard per artifact,
but the shard is a **mutable array**, not an append-only log.

### 4.1 The asymmetry that makes the case

`src/sase/sdd/artifact_link_beads.py` opens with:

> "Sidecar `links/` JSON never owns `bead:` rows. Every bead endpoint of a row gets its
> own `LinkAdded` / `LinkRemoved` event on its own stream."

So **half of the artifact-link graph is already event-sourced and conflict-safe**. Bead
endpoints get events; document endpoints get a mutable JSON array. The same domain, two
storage models, and only the second one produces conflicts. Closing that gap is not a new
architecture — it is finishing an existing one.

### 4.2 What union merge was rejected for, and why links are different

The 202605 study rejected `merge=union` for `issues.jsonl` because *"bead IDs are unique
entities. Preserving both lines is data corruption."* Two writers editing bead `sase-3a`
produce two versions of one entity; keeping both is wrong.

Link rows are the opposite shape. A row is a fact keyed by `(source, relation, target)`,
the upsert is idempotent by that key, and the read path **already** dedups:
`unique_rows()` (`_artifact_link_store_support.py:393`) collapses by relation-aware
identity. For link rows, "keep both lines" is the *correct* merge for additions. The
objection that killed union for beads does not transfer.

---

## 5. Option analysis

### Option A — Semantic `links/` resolver (mirror `resolve_bead_conflicts`)

Add `resolve_artifact_link_conflicts(repo_root)` that reads index stages 1/2/3 for each
conflicted `links/**/*.json`, merges by dedup key (base-aware, so a row present in base
and absent on one side is a real deletion), takes `max(uses)` and the later description,
writes the canonical file, and `git add`s it. Broaden `_all_bead_conflicts` and
`_repair_or_abort_rebase` to accept `links/` paths.

- **Pros:** no format change, no migration, reuses the exact machinery beads proved,
  no per-clone git config. Small, ~1 module + 2 call-site widenings.
- **Cons:** conflicts still *happen* — they are merely auto-resolved. Only works where
  SASE drives the rebase; a human `git pull` in the primary checkout still gets markers.
  Does not reduce commit churn (127 link commits in 451).
- **Verdict:** the right **immediate stopgap**, not the answer.

### Option B — Append-only JSONL + `.gitattributes merge=union`

Change the durable shape to `links/<artifact-relpath>.jsonl`, one canonical JSON object
per line, and commit `links/**/*.jsonl merge=union -text` in each document sidecar.
Deletions become tombstone lines rather than removed lines; reduction applies them.

- **Pros:** git-native, **zero per-clone config** (union is a built-in driver — verified
  in §6), and it works on *every* git path: merge, rebase, cherry-pick, stash pop, and a
  human's `git pull`. This is the only option that also protects the human lane.
- **Cons:** shape migration (38 Python references, 19 test files; no Rust reader depends
  on the file layout, so the blast radius is Python-only). Union does **not** resolve
  delete/modify (§6), so deletion must become a tombstone. Union output order differs
  between merge and rebase, so a normalizer is required for convergence.
- **Verdict:** the right **durable shape**, and strictly better than A for coverage, but
  it hardens conflicts rather than eliminating them.

### Option C — Writer-sharded files (one file per writing agent)

`links/<artifact>.md.d/<agent-name>.jsonl`. Two agents never write the same path, so the
dominant case becomes structurally conflict-free.

- **Pros:** conflicts impossible for `read`/`cites` rows without any merge machinery.
- **Cons:** file-count growth (262 read rows → 262 files today, unbounded over time),
  `rglob` cost on every graph load, and cross-writer deletion becomes awkward — an agent
  cannot retract another agent's row without touching its file, reintroducing the race
  for exactly the operation that union cannot merge. Rename repair gets harder.
- **Verdict:** solves the easy half at a structural cost, and does not compose well with
  `link rm` or rename repair. Not recommended as the primary.

### Option D — Single serialized writer; agents enqueue only ★

Stop writing the sidecar from the agent lane. `sase artifact read` and (inside an agent
run) `sase artifact link add/rm` update only the **machine-local aggregate**
(`~/.sase/projects/<key>/artifact-links.json` — already the default source for
`sase artifact link list`) and append to the **existing outbox**
(`~/.sase/projects/<key>/artifact-link-outbox.jsonl`). One serialized host-owned drain
per machine writes the hidden host-owned clone.

Almost every part already exists:

- the outbox: `src/sase/sdd/artifact_link_outbox.py` (`append_...`, `drain_...:161`)
- the drain trigger at agent finalization:
  `src/sase/workflows/commit/workflow_publication.py:179`
- the hourly retry: `src/sase/scripts/sase_chop_artifact_link_backfill.py`
- **the hidden host-owned clone**: `resolve_machine_artifact_link_store`
  (`src/sase/sdd/_artifact_link_machine_store.py`), landed today as `sase-y3.3`
- the machine-writability gate: `_artifact_link_authorize.py`
- the doctor guardrail against primary-clone link dirt:
  `doctor -C project.primary_sidecar_link_dirt`

The missing pieces are small: (i) drop the eager `store.upsert_row()` sidecar write in
`_record_read_link`, (ii) point the finalize-time drain at
`resolve_machine_artifact_link_store()` instead of `resolve_artifact_link_store()`,
(iii) hold one machine-wide lock across the drain, and (iv) make push rejection trigger
**replay, not merge**.

- **Pros:** conflicts become *impossible on the agent path* — an agent's sidecar clone
  never has `links/` dirt, so the stitch never stages it, so the rebase never sees it.
  Cross-machine races (athena/apollo/mac) are repaired by idempotent replay with no
  working-tree merge. Batching collapses ~127 link commits into ~20. The read path stays
  visually immediate via the aggregate.
- **Cons:** durable visibility of a read row moves from "at read time" to "at the next
  drain" (one agent-completion, not an hour). `link add` from inside an agent reports
  *queued* rather than *published* — a real semantics change for the 8% manual traffic.
- **Verdict:** **the recommendation.**

### Option E — Stop versioning `read` rows

Keep reads in the machine-local aggregate only. Removes 19% of rows and most of the
churn, but discards cross-machine read provenance that `read`/`read-by` and
`sase artifact doctor` (audited reads vs durable rows) are explicitly built on. Rejected.

---

## 6. Empirical git results

I verified the merge behaviour rather than assuming it (scratch repos, this machine,
git as installed):

| Scenario | `.gitattributes` `merge=union` | Result |
| --- | --- | --- |
| modify/modify, both append a line, `git merge` | yes | **CLEAN**, both lines kept |
| add/add, both create the file, `git merge` | yes | **CLEAN**, both lines kept |
| add/add, both create the file, `git rebase` | yes | **CLEAN**, both lines kept |
| delete/modify, `git merge` | yes | **CONFLICT** (`UD`) — union does not apply |

Two consequences:

1. `merge=union` **does** fix the exact failure `research.1n.cdx` hit (both-added index),
   on both `merge` and `rebase`, with **no `git config` install** — unlike a custom merge
   driver, union is built in, so `.gitattributes` alone is sufficient in every clone.
2. Merge and rebase produced **different line orders** (`{1,3,2}` vs `{2,3}` ordering in
   my two runs). Union concatenates hunks; it does not sort. A normalizer that rewrites
   the file sorted by `(created_at, source_ref, relation, target_ref)` and deduped is
   required, or clones drift textually and manufacture *future* conflicts — the exact
   trap the 202605 study flagged for `issues.jsonl`'s sorted export.

Also note the pattern gotcha: `.gitattributes` patterns containing a slash are anchored
and `*` does not cross `/`. `links/*.jsonl` silently matches nothing under
`links/202609/`; the correct pattern is `links/**/*.jsonl`. My first test run failed for
exactly this reason.

---

## 7. Failure modes the design must survive

| Case | Frequency | D alone | D + B |
| --- | --- | --- | --- |
| Two agents `read` the same doc, different workspaces | dominant | impossible | impossible |
| Two agents `link add` to the same doc | occasional | impossible | impossible |
| Host drain races the hourly backfill chop | occasional | machine lock + replay | same |
| Two machines' drains push together | rare (grows with fleet) | replay-on-reject | same + union |
| Human `sase artifact link add` in primary while drain pushes | rare | rebase conflict | **union resolves** |
| Human `git pull` in primary with local link dirt | rare | conflict | **union resolves** |
| Rename repair deletes an index while another side appends | rare | impossible (host-only) | conflict unless tombstoned |

The last row is why B needs tombstones rather than file deletion, and why D — which keeps
rename repair exclusively in the single-writer host lane — is the part that makes the
guarantee *structural* rather than *probabilistic*.

---

## 8. Recommended solution

**Adopt Option D as the primary, Option B as the durable-shape hardening, and ship
Option A first as a stopgap.** Three increments, each independently valuable:

### Phase 1 (days) — semantic `links/` resolver, current shape

1. Add `src/sase/sdd/artifact_link_conflict_resolver.py` exposing
   `resolve_artifact_link_conflicts(repo_root) -> Resolution`, modelled directly on
   `src/sase/bead/conflict_resolver.py`: read stages 1/2/3 via
   `git checkout-index`/`git show :N:<path>`, merge rows by
   `artifact_link_dedup_key`, treat *present-in-base-and-missing-on-one-side* as a
   deletion, take `max(uses)` and the later `description`, keep the earlier
   `created_at`/`created_by`, write through `atomic_write_json`, `git add`.
2. Widen `_git_commit_dispatch._all_bead_conflicts` (line 222) to
   `_all_auto_resolvable_conflicts`, accepting `beads/` **and** `links/` paths, and have
   `_continue_rebase_resolving_beads` (line 194) dispatch per-path.
3. Widen `_repository_integration._repair_or_abort_rebase` (line 195) the same way.
4. Fail closed exactly as beads does: an unreadable probe or any non-`links/`, non-bead
   conflict aborts to the starting state with a named diagnostic.

Effect: agents stop being handed merges *today*, with no migration.

### Phase 2 (the real fix) — agents leave the write path

5. In `src/sase/artifact_cli/read.py:283`, drop `store.upsert_row(row)` when an agent
   identity is present; update only the machine-local aggregate and the outbox. Do the
   same for `add_artifact_link` / `remove_artifact_link` when
   `discover_agent_identity()` is non-`None`; the host-shell path keeps writing directly.
6. Point `_drain_artifact_link_outbox_for_agent`
   (`workflows/commit/workflow_publication.py:179`) at
   `resolve_machine_artifact_link_store(project_key, primary_checkout)`, so drains land
   in `~/.sase/projects/<key>/repos/<role>` rather than the agent's clone.
7. Wrap the drain in one machine-wide lock (reuse `store_git_write_lock` /
   the `run_managed_sync_worker` outer-lock pattern) so the finalize drain, the hourly
   chop, and concurrent finalizers serialize instead of racing.
8. Replace merge-on-reject with **replay-on-reject**: on a rejected push,
   `fetch` → `reset --hard origin/<default>` → re-`upsert` every queued row → commit →
   push, bounded (mirror `_MAX_PUSH_ATTEMPTS = 3`). This is sound *only* because
   `upsert_artifact_link_row` is idempotent by dedup key — state the invariant in the
   module docstring and test it.
9. Change `sase artifact link add`'s agent-lane confirmation from "published" to
   "queued (N in outbox)", and have `sase artifact doctor` count a queued row as
   accounted-for rather than as drift.
10. Extend `doctor -C project.primary_sidecar_link_dirt` to flag `links/` dirt in **any**
    workspace clone, not just the primary — under Phase 2 that dirt is a bug anywhere.

Effect: an agent's sidecar clone never contains `links/` dirt, so the class of conflict
that `research.1n.cdx` resolved cannot be constructed.

### Phase 3 (durable shape) — append-only JSONL + union

11. Migrate `links/<relpath>.json` → `links/<relpath>.jsonl`, one canonical
    `ArtifactLinkRowWire` per line, sorted by `(created_at, source_ref, relation,
    target_ref)`, written by a normalizer that always rewrites the whole file
    sorted + deduped.
12. Represent removal as an appended tombstone (`"op": "rm"`), never as a removed line or
    a deleted file. Extend `unique_rows` to apply tombstones and to take `max(uses)` /
    latest `description` instead of first-wins, so union duplicates reduce correctly.
13. Commit `.gitattributes` in each document sidecar:

    ```gitattributes
    links/**/*.jsonl merge=union -text
    ```

    Use `**` (§6). `-text` keeps `core.autocrlf` from renormalizing bytes the union
    driver is about to read. Mirror the `sdd/_git.py` precedent and keep `rerere`
    disabled for these repos.
14. Keep the Phase-1 resolver as the fail-safe for delete/modify and for any
    schema-invalid union output; keep `sase artifact doctor --fix` able to rebuild the
    aggregate from the JSONL truth.

Effect: the human and cross-machine lanes self-heal without SASE driving the rebase, and
the file shape finally matches the bead-endpoint half of the same graph
(`LinkAdded`/`LinkRemoved` events), leaving one storage model instead of two.

### Why this ordering

Phase 1 is cheap, reuses proven machinery, and stops the bleeding immediately. Phase 2 is
where "nearly impossible" becomes "impossible", and most of its infrastructure — outbox,
hidden host-owned clone, machine-writability gate, doctor guardrail — landed within the
last two days under `sase-y3`; this is the natural next step of that epic, not a new
direction. Phase 3 is the only part with a migration cost, and by then it is a
hardening measure rather than a load-bearing fix, so it can be sequenced on its own
schedule.

### What I would not do

- **Do not install a custom git merge driver.** It requires per-clone `git config`,
  which is precisely the distribution problem the bead work chose to avoid by hooking
  SASE's rebase paths. `merge=union` gets the zero-config property that a custom driver
  cannot.
- **Do not shard per writer (Option C).** It cannot express one writer retracting
  another's row, which is exactly what `link rm` and rename repair need.
- **Do not drop durable `read` rows (Option E).** `read`/`read-by` provenance is
  load-bearing for the doctor's audited-reads check and for cross-machine attribution.

---

## 9. Evidence index

**Code (this repo, `master` @ `a0ac015e0`)**

- `src/sase/artifact_cli/read.py:263-288` — dual write: eager sidecar upsert + outbox
- `src/sase/sdd/_artifact_link_store_sidecar.py:33-55` — whole-array read-modify-write
  under a per-clone `flock`
- `src/sase/sdd/referenced_by_index.py:9-21` — `links/<relpath>.json` path contract
- `src/sase/sdd/_artifact_link_files.py` — canonical index/lock classification
- `src/sase/sdd/_artifact_link_commit.py:54,222` — path-scoped link commits and push
- `src/sase/finalizers/reconciliation.py:110,271` — finalizer auto-commit of link dirt
- `src/sase/vcs_provider/plugins/_git_commit_dispatch.py:194,222` — the bead-only gate
  that pauses the stitch
- `src/sase/sdd/_repository_integration.py:195-240` — the bead-only rebase repair loop
- `src/sase/bead/conflict_resolver.py` — the semantic resolver to mirror
- `src/sase/bead/sync_worker.py:17` — serialized publisher, bounded push retries
- `src/sase/sdd/artifact_link_outbox.py:161` — `drain_artifact_link_outbox`
- `src/sase/workflows/commit/workflow_publication.py:179` — finalize-time drain
- `src/sase/sdd/_artifact_link_machine_store.py` — hidden host-owned clone lane
  (landed 2026-09-08, `sase-y3.3`)
- `src/sase/sdd/artifact_link_beads.py:1-9` — bead endpoints already event-sourced
- `src/sase/sdd/_git.py:105-110` — `rerere` disabled for SDD repos
- `sase-core crates/sase_core/src/artifact_link/wire.rs:355` — `upsert_artifact_link_row`
  (idempotent by dedup key, append in insertion order)

**Runtime evidence**

- `research.1n.cdx` transcript: both-added link index, resolved by hand, then a *second*
  conflict on `sase stitch create --resume`.
- `sase bead show sase-y3` — the just-closed machine-write-lane epic this builds on.
- Sidecar git history and row census as tabulated in §3.
- Scratch-repo merge/rebase experiments as tabulated in §6.

**Prior research**

- `research:202605/bead_jsonl_merge_conflicts.md` — options survey for bead JSONL; the
  union-merge rejection there is bead-specific and does not transfer to link rows (§4.2).
- `research:202605/greenfield_bead_storage_architecture.md` — event-store direction that
  beads ultimately shipped.
