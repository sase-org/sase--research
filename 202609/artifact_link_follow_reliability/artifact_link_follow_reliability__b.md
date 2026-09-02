---
create_time: 2026-09-02
updated_time: 2026-09-02
status: research
---

# Making Artifact Link Follows Land: Why `$` Says "not visible" And How To Stop It

**Research question:** following a link from the Artifacts Links panel (`$0`) or the link
rail (`$1`-`$9`) very often ends in a warning toast instead of a jump. The Patch tab
already solves the analogous problem for the Agents tab's `<enter>` keymap by rewriting
the destination pane's query and leaving the old query on the `^` history stack. Can that
strategy be generalized to make link follows virtually never fail, and what is the best
way to implement it?

**Scope:** `sase` at master `8b0c65476`. Read paths: the link-follow/link-trail actions,
the link index and relation sources, the Artifacts pane contract and query profiles, the
host-owned query-history mixin, and each built-in pane's navigation and filter-session
code. No runtime instrumentation was collected; every claim below is cited to source.

---

## Executive summary

The toast has **two independent causes**, and only one of them is a query problem.

1. **Identity mismatch (dominant).** The `LinkChip` the panel hands to the follow path
   carries a *synthesized* `ArtifactEntryTarget` built by guessing at fields the pane
   actually keys its rows by. Selection is an exact tuple lookup in a dict, so a link to
   an **epic bead, phase bead, flag bead, active plan, proposed plan, abbreviated stitch
   sha, or any row whose project part is spelled differently** can never be selected —
   *even when the row is sitting on screen in the current results.* No amount of query
   rewriting fixes this.

2. **Filtered out (real, and the one the user's strategy addresses).** The stitches pane
   ships with `sidecar:false merges:hide since:24h`, the beads pane with `-status:closed`,
   and every pane with a `limit:<page_size>` head slice. A `produced-by` stitch older than
   a day, or an `implements` link to a closed bead, is genuinely not in the result set.

On top of both, the **reveal ladder is a stub for five of six panes**:
`reveal_entry_target` is implemented only by the Patches pane; everything else inherits a
`return False`. And the one implementation that exists is called with the wrong role, so
for a patch link it rewrites the query to the *currently selected* patch's revert family,
warns, and then reports success anyway.

The recommendation at the end is a layered fix: make the destination pane resolve the ref
to its own row identity (killing cause 1), then add a generic, host-owned **reveal ladder**
whose last rung is a guaranteed-permissive query (killing cause 2), with every rewrite
committed through the seam that already records `^` history.

---

## 1. What the follow path does today

`LinkFollowMixin._follow_artifacts_target`
(`src/sase/ace/tui/actions/link_follow.py:338`) is the whole ladder:

```python
if self._select_current_artifacts_target(target):        return True   # 1 already visible here
project = _target_project_scope(target)
if project is not None and project != self.artifacts_project_scope:
    self._set_artifacts_project_scope(project, picked=True)             # 2 switch project scope
if self.current_tab != ARTIFACTS_TAB: ...                               # 3 switch to Artifacts
if self._request_artifacts_target(target):               return True   # 4 switch pane + select
pane = self._artifacts_entry_navigator(target.pane_id)
if pane is None or _pane_is_loading(pane):               return False  # 5 silent give-up
if self._drop_head_slice_limit(pane, ref, target):                      # 6 limit:N -> limit:all
    if self._request_artifacts_target(target):           return True
if pane.reveal_entry_target(target, role=RelationRole.FAMILY): return True   # 7 stub for 5/6 panes
if self._request_artifacts_target(target):               return True
self._notify_missing_link_target(ref, target)                           # 8 the toast
return False
```

The toast text is
`f"Linked target {ref} is not visible in {_pane_label(target)}"`
(`link_follow.py:492`).

Rungs 1, 4 and the retry after 6 all bottom out in the same primitive: the destination
pane's `select_entry_target(target)`, which is an **exact dict lookup keyed by the full
`ArtifactEntryTarget` tuple** — see `beads_navigation.py:343`
(`self._option_index_by_target.get(target)`) and `files_navigation.py:191`. That primitive
is where cause 1 bites.

---

## 2. Failure taxonomy

### Class A — Identity mismatch: the target can never match a row

`ArtifactEntryTarget` is `(pane_id, parts)` and is compared by value
(`src/sase/core/artifact_entry_target.py:29`). Each pane builds its row targets from its
own row model. But the link rail and links panel do **not** use those row models: chips are
built in `relations/link_index.py:213`, which calls
`target_for_ref_kind(neighbor_kind, payload, project_hint=...)` — a pure kind-dispatch that
**guesses** the missing parts (`relations/artifact_links.py:227`).

| Ref kind | Synthesized by `target_for_ref_kind` | Real row target | Matches? |
| --- | --- | --- | --- |
| `bead:X` | `("beads", (project_hint \|\| "", **"task"**, X))` | `("beads", (row.project, row.kind, id))` where `BeadRowKind = Literal["task","flag","epic","phase"]` (`beads_list.py:32,45`) | **Only task beads**, and only if `project_hint == row.project` |
| `plan:X` / `ref:<k>:X` | `("ref:k", (project_hint \|\| "", **"archive"**, X))` | `("ref:k", (row.project, row.kind, identity))`, `kind ∈ {proposal, active, archive}`, `identity` is a notification id for proposals (`plans_list.py:55`) | **Only archived** documents, and only if the payload equals the stored path |
| `stitch:repo@sha` | `("stitches", (repo, sha))` | `("stitches", (entry.repo, entry.commit.full_id))` (`commits_timeline.py:34`) | **Only full 40-char shas.** Canonicalization strips `@` and rewrites kind aliases only — it does not expand shas (`sdd/_artifact_link_store_support.py:105`) |
| `patch:X` | `("patches", (project_hint \|\| "", X))` | `("patches", (patch.project_name, patch.name))` (`patch_entry.py:10`) | Only if the aggregate's `_project` key equals the patch's `project_name` |
| `file:X` | `("files", (X,))` | `("files", (entry.logical_id,))` (`files_list.py:41`) | Only if the ref payload *is* the logical id |
| `agent:X` | `("agents", (X,))` | `("agents", (row.entry.name,))` (`agents_list.py:41`) | Usually, for a canonical name |

The `project_hint` is the aggregate row's `_project` — a **project key** from
`load_project_ref_display_snapshot()` (`artifact_links.py:_project_keys`). Row models use
whatever their loader stored; for patches that is `project_name`. Any divergence between
key and display spelling is a silent miss.

**The reconciliation logic already exists and is bypassed.** `_target_for_ref`
(`artifact_links.py:260`) first tries `_known_target_for_ref` (`:276`), which resolves a
ref against a `_KnownTargetIndex` of the pane's real rows — sha-prefix matching, file
first-part matching, `(pane_id, last_part)` matching. That is what the *in-pane relations
panel* uses (`artifact_link_edges(..., known_targets=...)`, `:236`). The **link rail and
links panel skip it entirely**, because `_build_chip` calls the bare `target_for_ref_kind`.

> This is the single highest-value finding. Given how heavily SASE uses epic and phase
> beads, and that `agent implements bead` / `stitch implements bead` are *projected*
> relations produced automatically for every agent and trailer-bearing commit, a large
> fraction of the chips in a typical rail are addressed by a tuple no pane will ever
> match. It explains "very often" better than filtering does.

### Class B — Genuinely filtered out of the pane's current results

This is the class the user's proposed strategy targets, and it is real:

| Pane | Committed default | Links it hides |
| --- | --- | --- |
| Stitches | `sidecar:false merges:hide since:24h` (`src/sase/default_config.yml:170`, `commit_config.py:21`) | Any `produced-by` / `implements` stitch older than 24h, in a sidecar repo, or a merge |
| Beads | `-status:closed` (`src/sase/bead/filter_query.py:67`) | Every link to a closed bead — i.e. most historical work |
| All panes | `limit:<ace.page_size>` injected at startup | Anything past the head slice |
| All project-scoped panes | `ace.current_project.seed_filters: true` seeds a project scope | Every cross-project link |
| Plans / document providers | archive is loaded lazily (`plans_deep_archive.py`, `_schedule_deep_archive`) | Older archived documents until a `grow` pass runs |

Only the `limit:` case is handled today, by `_drop_head_slice_limit`
(`link_follow.py:388`), which rewrites `limit:N` → `limit:all` through the pane's
`apply_host_limit_query`.

### Class C — Reveal-ladder gaps

- **`reveal_entry_target` is a stub for five of six panes.** The base returns `False`
  (`widgets/artifacts/entry_navigation.py:83`); the only override is the Patches pane
  (`widgets/artifacts/panes.py:198`). Beads, Stitches, Files, Agents and every document
  provider pane have no reveal at all.
- **The one override is called with the wrong role.** Link-follow passes
  `role=RelationRole.FAMILY` (`link_follow.py:361`), which
  `build_relation_reveal_query` maps to `sibling:<strip_reverted_suffix(origin_name)>`
  where `origin_name` is `self.patches[self.current_idx].name` — *the row that happened to
  be selected in the Patches pane*, not the link target
  (`relation_reveal.py:70`, `navigation/_tree.py:452`). The result is a query about an
  unrelated patch's revert family.
- **…and it reports success anyway.** `_change_query_for_navigation` notifies
  `"{target} is not reachable through {new_query}"` and still falls through to
  `return True` (`navigation/_tree.py:483-497`). Link-follow therefore treats a failed
  jump as a hop and pushes it onto the 32-hop link trail (`link_follow.py:141`), while the
  user's Patch query has been silently clobbered.
- **The Patches pane implements neither `host_limit_query` nor
  `apply_host_limit_query`.** Consequences: `_drop_head_slice_limit` can never fire for a
  patch link (`_pane_limit_query` returns `None`, `link_follow.py:504`), and
  `LinkTrailHop.query_source` is always `None` for a Patches origin
  (`link_follow.py:302-306`), so `Ctrl+O` cannot restore the Patch query on the way back
  (`link_trail.py:110-121`).
- **Silent give-up while a pane is loading** (`link_follow.py:353`). The pane's
  `request_entry_target` has *already* stored `_pending_entry_target`
  (`beads_navigation.py:228`, `files_navigation.py:203`), so the row would have been
  selected on the next snapshot — but the follow returns `False`, records no trail hop, and
  the deferred selection lands with no trail and no rail update.

### Class D — Genuinely dangling refs

The link target does not exist in any inventory. The panel already marks these
(`_is_missing`, `modals/artifact_links_panel_modal.py:74`) and `sase artifact doctor`
reports them. These *should* fail — but with a different message than "not visible here".

---

## 3. The precedent the user named, and the better one already in-tree

### The Agents-tab `<enter>` precedent

`navigate_to_patch_tab` (`actions/agents/_notification_navigation.py:207`) is exactly the
shape described: search the current filtered list; if absent, rewrite the query to
`project:<name>`, push the replaced query onto the `^` stack via
`_record_patch_query_transition`, reload, search again. It is Patches-only and hard-codes
one field.

### `sase/ace/relation_reveal.py` — the generalization already written

The repo already contains a *reversible query-rewrite lens*:

- `build_relation_reveal_query(profile, role, origin_name, target_name)` builds the rewrite
  from a **declared query-profile field** (`_ROLE_REVEAL_FIELDS`) instead of a hard-coded
  token, and returns `None` — rather than an unparseable query — when the pane's dialect
  has no such field.
- `RelationReveal` records the relation, the role, the exact query it rewrote *from*, and
  the origin's profile digest.
- `is_relation_reveal_active(...)` needs no "clear" step: the lens is live only while the
  pane's canonical query still equals `revealed_canonical`, so any user edit, `^`/`_`
  navigation, or saved-query load retires it automatically.

This is the right abstraction for the fix. It is currently reachable only from Patch
ancestor/sibling navigation.

---

## 4. `^` across Artifacts sub-tabs: already supported

The user asked that `^` work on all Artifacts sub-tabs. It already does, and the plumbing
is exactly what a reveal should ride on:

- `ArtifactsQueryHistoryActionsMixin.action_prev_query` / `action_next_query`
  (`actions/artifacts_query_history.py:32,37`) are host-owned and pane-generic, gated on
  `PaneCapability.QUERY_HISTORY`, which every non-degraded pane with inventory + fields
  earns (`_artifact_tab_contract_rules.py:259`).
- `ArtifactsMixin` precedes `PatchMixin` in `AceApp`'s bases (`tui/app.py:117-149`), so the
  generic implementation shadows the Patches-only `PatchQueryMixin.action_prev_query`
  (`actions/patch/_query.py:322`), which early-returns for non-Patches panes anyway.
- **Every pane's `apply_host_limit_query` already records history.** Beads, Stitches,
  Files, Plans and Agents all commit through a `_commit_*` method whose
  `record_history` defaults to `True` and which calls the app's
  `_record_artifacts_query_transition` (`beads_filter_session.py:116`,
  `agents_query.py:390`, and siblings). **A rewrite performed through that seam is
  `^`-reversible for free.**

Two rough edges worth normalizing while doing this work:

- The `apply_host_limit_query` signature is inconsistent: `grow: bool = False` exists on
  agents/files/plans but not on beads/stitches. `link_follow.py:414` already papers over
  this with `try/except TypeError`.
- The Patches pane does not implement the protocol at all (see Class C).

---

## 5. Design options

| # | Option | Fixes | Cost | Verdict |
| --- | --- | --- | --- | --- |
| 0 | Improve the toast only ("closed beads are hidden — press `~` to widen") | none | trivial | Insufficient; the user asked for the jump to work |
| 1 | Resolve the ref against the destination pane's rows before selecting | Class A | medium, contained | **Required.** Nothing else works without it |
| 2 | Neutral-query fallback: replace the pane query with the most permissive one (`limit:all` + project scope) | Class B | small | Good as a *last* rung; too blunt as the only one — dumps thousands of rows and destroys context |
| 3 | Targeted identity reveal: build the tightest query containing the target, from a pane-declared identity field | Class B | medium; needs dialect additions | **Best primary rung**, but not universally available today (see below) |
| 4 | Minimal widening: drop only the committed terms that exclude the row | Class B | medium-high; needs per-term evaluation | Best UX of all; viable *because* option 1 gives the host the actual row |
| 5 | Pin the target as an injected row without touching the query | Class B, cosmetically | high | Rejected: every pane's grouping, counters, ordering and marks would need a pinned-row concept, and it still cannot show a row absent from the loaded snapshot |
| 6 | Open a detail modal instead of navigating | none | small | Rejected: it is not a jump, and `Ctrl+O` has nothing to walk back to |

### Availability of an identity field per dialect (option 3)

Read from `src/sase/ace/query_profile/profiles/`:

| Pane | Exact identity term available today | Notes |
| --- | --- | --- |
| Patches | ✅ `name:<patch>` (also sigil `&`), `filterable`, `exact_match` | `_patches.py` |
| Agents | ✅ `name:<agent>`, `exact_match` | `_agents.py:85` |
| Beads | ⚠️ `id` is **search-only** (`filterable=False`) | bare free-text `sase-123` does match via id/title/body/refs AND-search, but is a substring match, not an address (`_beads.py:102`) |
| Files | ⚠️ `stored_path` / `source_path` search-only | same caveat (`_files.py:59`) |
| Plans / providers | ⚠️ `path` search-only | same caveat (`_plans.py:33`) |
| Stitches | ❌ **no sha field at all**; `subject` is search-only | a commit cannot be addressed by its query dialect (`_stitches.py`) |

So option 3 needs a small, closed set of dialect additions — most importantly a filterable
`sha:` (prefix-matching) field on the Stitches dialect. That is a query-profile change with
a digest impact: `QueryRecord.profile_digest` gates saved queries and history records
(`query_record.py`), so adding fields invalidates stored digests and must be handled the
way other dialect changes are.

---

## 6. Recommended solution

A four-layer fix, ordered so each layer is independently shippable and independently
valuable. Layers R1 and R2 together are what make the error "virtually never" happen.

### R1 — Make the destination pane resolve the ref (fixes Class A)

**Stop shipping a guessed tuple to the selection primitive.** Add one method to the
`ArtifactEntryNavigator` contract (`widgets/artifacts/entry_navigation.py`):

```python
def entry_target_for_ref(self, kind: str, payload: str) -> ArtifactEntryTarget | None:
    """Resolve a link-graph ref to this pane's own row identity.

    Answered from the pane's *unfiltered* snapshot, so a filtered-out row still
    resolves — which is what lets the host build a reveal for it.
    """
```

Each pane answers from the row model it already owns: beads match on `issue.id` regardless
of `row.kind` or project spelling; stitches match on `full_id.startswith(sha)`; documents
match on path across `proposal`/`active`/`archive`; files match on `logical_id`; patches
match on `patch.name`. Much of this logic already exists in `_known_target_for_ref`
(`relations/artifact_links.py:276`) and can be lifted rather than rewritten.

Then change `_follow_artifacts_target` to address by **ref** and use
`chip.neighbor_target` only as a hint for choosing the destination pane. Keep
`target_for_ref_kind` for pane routing; it is fine at deciding *which* pane, and wrong only
about *which row*.

**Boundary note.** Per the `rust_core_backend_boundary` core memory, ref → row identity
resolution is shared backend behavior — a web frontend or a CLI `sase artifact link
follow` would need the same mapping — so the canonical resolution rules belong in
`../sase-core/crates/sase_core`, with the Python panes as thin adapters. The ladder
orchestration, keybindings, toasts and trail are presentation and stay here.

Do R1 first. It is the larger share of the reported failures, it needs no query rewriting
at all, and R2's minimal-widening rung is only possible once the host can get its hands on
the actual row.

### R2 — A generic, host-owned reveal ladder ending in a guaranteed rung (fixes Class B)

Replace rungs 6–8 of `_follow_artifacts_target` with an explicit ladder, each rung
attempted only if the previous one missed:

1. **Select in place** (unchanged).
2. **Project scope** (unchanged) — but see R4 about the loading race.
3. **Drop the `limit:` head slice** (existing `_drop_head_slice_limit`).
4. **Identity reveal.** Build the tightest query that provably contains the row, through
   the compiled query profile — a `build_identity_reveal_query(profile, pane_id, row)`
   sibling of `build_relation_reveal_query`, driven by a declared identity field rather
   than a hard-coded token, returning `None` when the dialect has none. Requires R5.
5. **Minimal widening.** With the row in hand from R1, evaluate the committed query's
   terms against it and drop only the ones that exclude it — `since:24h` for an old
   stitch, `-status:closed` for a closed bead — keeping everything the user actually cares
   about. The profile evaluator already exists
   (`src/sase/ace/query/profile_evaluator.py`).
6. **Neutral query.** `limit:all` plus whatever project scope the target needs. Blunt, but
   it is the rung that makes "virtually never" true: if the row is in the pane's inventory
   at all, this shows it.
7. **Only now, a toast** — and distinguish *dangling* (Class D: "no such artifact") from
   *not in inventory* ("the Stitches pane has no commit `abc1234`"). The current message
   conflates them.

Two invariants for every rewriting rung:

- **Commit through the pane's existing query seam** (`apply_host_limit_query`, or the
  pane's `_commit_*` path), never by poking `filters`/`query_string` directly. That is
  what makes `^` reverse the rewrite with no new persistence code (§4).
- **Wrap it in a lens.** Reuse the `RelationReveal` shape as a `LinkReveal`
  (`pane_id`, the followed ref, the origin `QueryRecord`, `revealed_canonical`). Its
  self-retiring liveness rule (`is_relation_reveal_active`) already gives you a correct
  "the reveal is over" signal with no clear step, and it stamps the origin profile digest
  so a stale way-back is detected instead of misapplied.

### R3 — Fix the Patches-pane special cases

- Implement `host_limit_query` / `apply_host_limit_query` on the Patches pane, delegating
  to `_display_patch_query` / `_commit_patch_query` (`actions/patch/_filter_session.py:67,96`).
  This alone gives Patches the `limit:` rung *and* restores `Ctrl+O` query restoration for
  a Patches origin.
- Stop calling `reveal_entry_target(..., role=RelationRole.FAMILY)` from link-follow. The
  relation roles are a *relation-graph* vocabulary; a link follow is not a family walk.
  Route link follows through the new ladder instead and leave `reveal_entry_target` to
  in-pane relation navigation.
- Make `_change_query_for_navigation` return `False` when `_find_in_current_list` misses,
  so a failed reveal stops being recorded as a link-trail hop
  (`navigation/_tree.py:483-497`).
- Normalize `apply_host_limit_query(query, *, grow: bool = False)` across all panes and
  drop the `try/except TypeError` at `link_follow.py:414`.

### R4 — Never give up because a pane is still loading

At `link_follow.py:353`, the pane has already stored `_pending_entry_target`. Instead of
returning `False`, record the hop optimistically and let the pane's existing pending-target
mechanism complete the selection, refreshing the rail when it does. This matters most right
after rung 2, where switching project scope kicks off a reload and the very next line
queries a pane that cannot possibly have the row yet.

### R5 — Small, closed dialect additions

Add filterable exact-identity fields where rung 4 needs them, most importantly a
prefix-matching `sha:` on the Stitches dialect. Consider promoting `id` (beads) and `path`
(files, documents) from search-only to filterable/exact so the reveal is an address rather
than a substring search. Budget for the `QueryRecord.profile_digest` invalidation this
causes for saved queries and stored history.

### R6 — Make the reveal visible and reversible *in the UI*

- When a rung 4/5/6 rewrite fires, say so: `Revealed bead:sase-123 — press ^ to restore
  your query`. The current `_drop_head_slice_limit` notice is a good model
  (`link_follow.py:424`).
- Show a lens chip on the rail while a `LinkReveal` is live, mirroring the link-trail
  breadcrumb (`link_trail.py:191`).
- In the links panel itself, pre-flag rows that would need a reveal, using the same R1
  resolution — the panel already runs a background staleness pass it can piggyback on
  (`link_follow.py:275`).

### Sequencing

| Phase | Content | Unblocks |
| --- | --- | --- |
| 1 | R1 (pane-side ref resolution, core rules in `sase-core`) + R3's `return False` bug | Most of the reported toasts disappear |
| 2 | R4 + R3's Patches `host_limit_query` | Loading races and Patch trail restoration |
| 3 | R2 rungs 5–7 (minimal widening + neutral query + honest toasts) | "Virtually never" for Class B |
| 4 | R5 + R2 rung 4 (targeted identity reveal) | Narrow, pleasant reveals instead of blunt ones |
| 5 | R6 | Discoverability of `^` as the way back |

### Verification

- The existing `tests/ace/tui/test_link_follow.py` harness (a duck-typed `_App` + `_Pane`)
  extends naturally: add panes whose `select_entry_target` rejects a synthesized tuple but
  accepts the resolved one, and assert the ladder's rung order and the recorded `^` entry.
- Add one regression test per Class-A row shape: epic bead, phase bead, proposed plan,
  active plan, abbreviated stitch sha, cross-project patch.
- `tests/ace/tui/visual/test_ace_png_snapshots_artifact_links_panel.py` will need new
  snapshots for the R6 chip.
- Read `sase/memory/lint_and_test.md` through `/sase_memory_read` before landing (`just
  check` vs the `just check-full` landing gate), and `sase/memory/sase_flags.md` — this
  changes user-reaching navigation behavior and likely wants a flag bead so the old
  ladder stays reachable.

### Answering the original framing

The user's instinct — "do what the Patch tab does for the Agents `<enter>` keymap, and let
`^` undo it" — is correct and is already half-built as `relation_reveal.py`. Two amendments
matter:

1. **A query rewrite is the *last* rung, not the first.** The blunt `project:<name>` swap
   that `navigate_to_patch_tab` performs is fine for a notification jump but too
   destructive as the default for link following; rungs 3–5 should absorb most cases first.
2. **Query rewriting alone will not deliver "virtually never."** The largest share of the
   toasts the user is seeing are rows that are already on screen and simply cannot be
   addressed. R1 is the prerequisite; R2 is the finish.
