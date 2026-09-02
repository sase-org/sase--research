# Reliable navigation from the Artifacts Links panel

Date: 2026-09-02

Code studied: `sase` commit `8b0c65476b9c`

Scope: the Artifacts Links panel and link rail, stable entry targets, pane loading,
query/history integration, link-trail restoration, and the existing Agents-to-Patch
navigation precedent.

## Research question

When a link chip points at an artifact that is not present in the destination pane's
current row model, what recovery behavior will make the jump reliable while preserving
the user's current query for `^`?

This analysis is based on the current implementation, its tests and documentation, git
history for the link-follow and query-history work, and the audited design artifacts
`plan:202608/link_follow_grammar.md`, `plan:202608/artifacts_query_history.md`, and
`research:202609/artifact_links_panel_jump_reliability.md`. I did not collect runtime
telemetry, so the relative frequency of the failure classes below is an inference, not a
measurement.

## Executive conclusion

The warning is not one bug. Four independent conditions are currently collapsed into
the same "not visible" result:

1. The link chip may contain a synthesized row identity that can never equal the real
   row identity, even if the artifact is already loaded.
2. The row may genuinely be excluded by the current query, project scope, head limit,
   or fold.
3. The destination pane may still be loading an incomplete snapshot, but a Boolean
   request API makes "pending" indistinguishable from "missing."
4. The artifact may actually have been deleted, or its owning pane may be unavailable.

The existing recovery path handles only part of condition 2. It first changes
`limit:N` to `limit:all`, then invokes a Patch-specific relation reveal using the
unrelated `FAMILY` role. Several panes also clear their filters internally, but those
clears bypass the query-history commit funnel, so `^` cannot restore the prior query.

The best implementation is a small link-navigation coordinator that operates on the
canonical artifact ref, not on a guessed row tuple. It should resolve or directly fetch
the artifact, construct a narrow identity query in the destination pane's dialect,
commit that query exactly once through the existing history seam, and wait for a
tri-state `SELECTED` / `PENDING` / `MISSING` completion. A warning should be emitted only
for a definitive `MISSING` result from authoritative coverage.

## 1. The current path

Both a `$N` rail jump and a Links-panel selection eventually call
`LinkFollowMixin._follow_artifacts_target()` in
`src/sase/ace/tui/actions/link_follow.py:338`. The current ladder is:

1. select the synthesized target if it is already in the active pane;
2. derive and change shared project scope from the target tuple;
3. switch to the Artifacts tab and destination pane;
4. call `request_entry_target()`;
5. return silently if `_loading` or `_loading_full` is true;
6. rewrite `limit:N` to `limit:all` and retry;
7. call `reveal_entry_target(target, role=RelationRole.FAMILY)` and retry;
8. show `Linked target ... is not visible in ...`.

This looks like a reveal ladder, but three contracts under it are too weak:

- `ArtifactEntryNavigator.request_entry_target()` returns `bool`, documented as
  "select now, or remember for the next loaded row model"
  (`widgets/artifacts/entry_navigation.py:47`). `False` therefore means both "accepted
  and pending" and "not found."
- Selection is an exact lookup on `ArtifactEntryTarget`, so an approximately synthesized
  target is no better than no target.
- `reveal_entry_target()` is a default `return False` for every pane except Patches
  (`entry_navigation.py:83` and `panes.py:198`).

The Links panel is therefore not the source of the problem; it exposes a weakness in the
shared follow path used by both link surfaces.

## 2. Failure class A: the chip's target is only a guess

`LinkIndex._build_chip()` calls `target_for_ref_kind()` without consulting a pane's real
rows (`relations/link_index.py:199-235`). The function explicitly synthesizes a target
"with no known-target lookup" (`relations/artifact_links.py:227-257`). That is enough to
route to a pane, but not enough to address every row in that pane.

| Artifact ref | Synthesized target | Real row identity | Reliability gap |
| --- | --- | --- | --- |
| `bead:<id>` | `(project, "task", id)` | `(project, row.kind, id)` | Epic, phase, and flag beads can never match the hard-coded `task` kind. |
| `stitch:<repo>@<sha>` | `(repo, supplied_sha)` | `(repo, full_sha)` | An abbreviated SHA does not equal the full row SHA. |
| provider ref | `(project, "archive", payload)` | `(project, proposal/active/archive, identity)` | Proposed and active documents, plus provider-specific identities, can disagree. |
| `patch:<name>` | `(project_hint, name)` | `(patch.project_name, name)` | A project key/display-name mismatch prevents selection; duplicate names need project disambiguation. |
| `file:<id>` | `(payload,)` | `(logical_id,)` | Works only when the payload is already the pane's logical identity. |
| `agent:<name>` | `(payload,)` | `(canonical row name,)` | Aliases and local/global names can disagree. |

There is already better reconciliation code in
`relations/artifact_links.py:260-309`: `_known_target_for_ref()` handles SHA prefixes,
agent aliases, file first-part matches, and pane/last-part matching. In-pane relation
panels can use it because they have a known-target index. The global Links panel cannot
assume every pane has rendered its rows, so it falls back to synthesis.

The important architectural distinction is:

- a synthesized target is a useful **routing and fast-path hint**;
- the canonical ref is the durable **address**;
- only the destination domain can produce the authoritative row target.

Query rewriting alone cannot fix a wrong tuple. The row may become visible and the final
exact selection will still miss.

## 3. Failure class B: the current view really excludes the row

The current queries are intentionally restrictive:

- Stitches defaults to `sidecar:false merges:hide since:24h`
  (`src/sase/default_config.yml:165-170`). Historical, sidecar, and merge commits are
  excluded before navigation begins.
- Beads normally excludes closed work, which is likely to include many historical links.
- Startup adds a `limit:<page_size>` head cap; the default page size is 100.
- Plans/provider archives and some Agent/File inventories can be incomplete until a
  grow or deep-load path finishes.
- Project-scoped panes can be looking at a different project.
- Bead phases and grouped Files/Agents can be present but folded.

The current link follower handles the head cap by changing it to `limit:all`. This is
reversible when the pane's `apply_host_limit_query()` goes through its normal commit
path, but it is broad and can be unnecessarily expensive. It does not address
`since:24h`, `-status:closed`, `sidecar:false`, a provider archive boundary, or an
identity that the query dialect cannot express.

Some panes independently try to clear filters when a pending target does not appear:

- Beads assigns `self.filters = BeadFilterValues()`
  (`beads_options.py:353-362`).
- Plans assigns `self.filters = PlanFilterValues()`
  (`plans_options.py:522-532`).
- Files assigns `self.filters = FilesFilterValues()`
  (`files_options.py:252-261`).
- Agents assigns `self.query_source = ""`
  (`agents_options.py:217-228`).

These are direct state mutations, not committed query transitions. They bypass
`_record_artifacts_query_transition()`, even though each pane already has a commit method
that records history. Consequently, the UI can say that it cleared a filter while `^`
has no record of the query it replaced. This directly conflicts with the intended
query-history contract and with the desired way back.

## 4. Failure class C: incomplete data is treated as absence

The pane implementations do not agree on when absence is authoritative:

- Files waits for `snapshot.complete` or a load error and checks both `_loading` and
  `_loading_full` (`files_options.py:274-280`). This is the strongest current model.
- Beads and Plans treat any current-project snapshot with `_loading == False` as enough
  to declare the target missing (`beads_options.py:375-380`,
  `plans_options.py:545-550`). Plans can still have deferred deep-archive work.
- Agents warns as soon as `_current_snapshot()` is non-null
  (`agents_options.py:180-190`), even if the snapshot is capped or its query index is
  being rebuilt.
- Stitches has collection/query workers that are not represented by the link follower's
  `_pane_is_loading()` check, which only probes `_loading` and `_loading_full`.

At the app layer, `request_entry_target()` returning `False` after storing
`_pending_entry_target` is immediately interpreted as a miss. When a project switch has
just initiated a load, `_follow_artifacts_target()` returns without recording a completed
hop. The pane may select the row later, but the link trail and visible link state then do
not describe the jump that occurred.

The correct state machine needs at least three outcomes:

```text
SELECTED  the exact target is selected now
PENDING   the request is accepted and authoritative resolution is still running
MISSING   authoritative resolution completed and the target does not exist
```

Load errors should be separate from `MISSING`; cancellation or supersession should be
separate from both.

## 5. Failure class D: the Patch reveal is the wrong abstraction

The only `reveal_entry_target()` implementation is Patch-specific relation navigation.
The generic link follower calls it with `RelationRole.FAMILY`
(`link_follow.py:360`). `build_relation_reveal_query()` maps that role to a `sibling:`
query derived from the patch that happens to be selected, not from the arbitrary linked
patch. This can produce a query unrelated to the link target.

Worse, `_change_query_for_navigation()` warns if it cannot find the target but still
returns `True` (`actions/navigation/_tree.py:481-502`). The caller then treats the link
as followed and may record a trail hop even though no target was selected.

Link following and relation-family revealing are different operations:

- a relation reveal asks for a family/ancestor view relative to an origin row;
- a link follow asks for exactly one canonical artifact.

The link path should stop passing a fabricated relation role. Patch should participate
in the same identity-navigation contract as every other pane.

## 6. What can be reused

### Query history already spans every healthy Artifacts pane

`ArtifactsQueryHistoryActionsMixin.action_prev_query()` and `action_next_query()` are
pane-generic (`actions/artifacts_query_history.py:32-77`). The contract enables query
history for panes that have an inventory and query fields. Patch has an app-owned
adapter; other panes expose `query_history_record()` and
`apply_query_history_record()`.

The missing piece is not a new `^` implementation. The navigation rewrite must use the
existing committed-query seam exactly once. Live filter typing should remain outside
history, and programmatic filter clears should no longer mutate state directly.

### The Agents-to-Patch jump is a useful behavioral precedent

`navigate_to_patch_tab()` searches the current Patch list and, on a miss, rewrites the
query to `project:<project>`, records the previous query, reloads, and selects
(`actions/agents/_notification_navigation.py:207-260`). Its user experience is right:
the jump temporarily changes the destination view and `^` restores it.

It should not be copied literally because it:

- is Patch-only;
- queries an entire project instead of the exact patch;
- assumes a synchronous reload;
- searches by patch name without making project part of final selection;
- does not solve synthesized identity mismatches.

### The relation-reveal lens is a useful transaction shape

`relation_reveal.py` records the origin query, revealed query, profile digest, and origin
target. A link reveal can use the same self-retiring lens idea, but it should be keyed by
canonical ref and should only finalize after actual selection.

### The known-target resolver is useful as a fast path

The existing `_KnownTargetIndex` behavior should be extracted or reused for loaded rows.
It should not become a requirement that every pane materialize a complete inventory
before a link can be followed.

## 7. Identity-query support by pane

An exact destination query is possible today for only two panes. The other dialects
need a small identity-field addition or a direct resolver.

| Pane | Existing addressable field | Needed navigation query | Acquisition requirement |
| --- | --- | --- | --- |
| Patches | exact `name:` and `project:` | `project:"P" name:"N"` | Load/query the named project, then select by both parts. |
| Agents | exact `name:` and `project:` | `name:"canonical-name"` (plus project when needed) | Resolve local/global aliases before committing. |
| Beads | `id` is search-only | promote exact `id:`; use `project:"P" id:"X"` | Resolve the real row kind instead of assuming `task`. |
| Stitches | no SHA field | add prefix-aware `sha:`; use `repo:"R" sha:"S"` | Resolve the commit directly rather than walking all history. |
| Files | paths are search-only; logical id is not a field | add exact `id:` or `reference:` | Look up the logical id in the artifact index before applying the cap. |
| Plans/providers | `path` is search-only for Plans and provider-defined elsewhere | exact `path:`/provider identity plus `project:` | Address the document directly across proposal/active/archive storage. |

There are two reasonable schema strategies:

1. Add a universal reserved field such as `reference:<canonical-ref>` to every pane.
2. Let each pane declare its domain identity fields and provide a query builder.

A universal field looks attractive, but it still requires changes to every typed filter
value/parser and every query index. It also hides project ambiguity inside refs such as
`patch:<name>` and risks collisions with provider-declared fields. Pane-declared identity
queries are more explicit, compose naturally with project/repository constraints, and
produce queries users can understand and edit. A common host protocol can make their
construction uniform without forcing the token spelling to be uniform.

The identity predicate must reach data acquisition **before** `limit:` is applied.
Filtering only the current capped client snapshot recreates the same failure in a
narrower query. In particular, Stitches should resolve a SHA through the VCS provider,
Files through the artifact index, and documents through their provider/path lookup,
rather than using `limit:all` as a substitute for direct addressing.

## 8. Candidate approaches

### A. Clear every destination query and use `limit:all`

This is the smallest code change and resembles existing pending-target behavior.

It is not the best solution. It can load thousands of rows, discards useful context,
does not fix wrong target tuples, and still races incomplete snapshots. The current
direct clears also break `^`.

### B. Add ad hoc fallback code to every pane

Each pane could clear its filters, grow its inventory, select, and toast independently.

This can work, but the existing implementations already demonstrate the likely drift:
four different completeness tests, inconsistent loading flags, different history
behavior, and duplicate warning ownership. It would make the Links panel increasingly
dependent on pane-specific timing.

### C. Add only a universal `reference:` query field

This would give the host one query to construct for every link.

It is incomplete by itself. The destination still has to canonicalize the ref, resolve
aliases and abbreviated SHAs, fetch beyond a capped snapshot, and return an actual row
target. It also imposes a reserved field on every provider dialect. It is a useful
future convenience, not the primary navigation contract.

### D. Resolve the ref, then commit a pane-declared identity query through one coordinator

This approach separates durable addressing, data acquisition, presentation query, and
selection. It fixes every false-negative class without requiring every pane to share one
query dialect. It also gives one place to own pending state, history, link trail, and
warnings.

This is the strongest option.

## 9. Proposed contract

The `LinkChip` should continue carrying `neighbor_target` for icon/pane routing and the
zero-cost visible-row fast path, but following should pass a richer address:

```python
@dataclass(frozen=True)
class ArtifactLinkAddress:
    ref: str                         # canonical durable address
    pane_id: str                     # routing destination
    project_hint: str | None
    target_hint: ArtifactEntryTarget | None
```

Add a link-specific method to the pane/navigation adapter rather than overloading
same-pane relation reveal:

```python
class LinkRequestState(Enum):
    SELECTED = auto()
    PENDING = auto()
    MISSING = auto()
    FAILED = auto()

@dataclass(frozen=True)
class LinkRequestResult:
    state: LinkRequestState
    target: ArtifactEntryTarget | None = None
    navigation_query: str | None = None
    error: str | None = None

def request_link_address(address: ArtifactLinkAddress) -> LinkRequestResult: ...
```

The pane/domain adapter owns:

- canonical ref-to-domain identity resolution;
- direct or targeted hydration when the current inventory is incomplete;
- conversion to the pane's actual `ArtifactEntryTarget`;
- construction and validation of the narrow identity query;
- declaring absence only after authoritative coverage.

The app-owned coordinator owns:

- tab, pane, and shared-scope switching;
- capturing the origin query, selection, pane, scope, and link trail position;
- committing the final query through the normal pane commit path;
- waiting on a generation-tagged pending request;
- recording the link-trail hop only after selection succeeds;
- emitting one final warning or load error;
- cancelling stale completion when the user follows another link or edits the query.

Canonical ref parsing and domain lookup rules are shared behavior that other frontends
would need to agree on, so they belong behind the Rust core boundary. The Textual
transaction, query history, focus, notifications, and trail remain Python/TUI concerns.

## 10. The navigation transaction

The coordinator should use this order:

1. **Capture origin.** Save the source tab/pane, selected target, committed query,
   profile digest, project scope, and trail state. Do not mutate history yet.
2. **Try the target hint.** If the exact hinted target is visible, select it and finish.
3. **Resolve by canonical ref.** Ask the destination adapter to normalize aliases/kinds
   and perform a direct identity lookup. The adapter returns the actual target or
   `PENDING`/`MISSING`.
4. **Wait without warning.** A `PENDING` result stores a generation-tagged transaction.
   A pane completion message resumes the transaction. A later user action cancels the
   old generation.
5. **Expand folds.** If the target is loaded but hidden only by an owned group/epic fold,
   expand the minimum fold and select it. Record how to reverse that fold in the trail.
6. **Build the identity query.** If query membership excludes the resolved row, ask the
   pane for its narrow, canonical identity query. Do not first clear the query or expand
   to `limit:all`.
7. **Commit once.** Apply the identity query through the pane's committed-query method.
   This creates one previous-query entry, keeps the filter bar synchronized, preserves
   the previous selection record, and clears the forward stack. The toast should say,
   for example, `Revealed bead:sase-123; press ^ to restore your query`.
8. **Select after the resulting load.** `PENDING` remains a live transaction. On success,
   select the actual row, synchronize link state, and record the link-trail hop.
9. **Fail only on authority.** `MISSING` means the direct resolver or complete destination
   inventory proved absence. `FAILED` means acquisition failed. Distinguish those toasts
   and never call either merely because a snapshot object exists.

The transaction should not optimistically add a link-trail hop. If an async load fails
or the ref is truly dangling, an optimistic hop describes a navigation that never
happened. Keep the origin in the pending transaction and finalize the trail on
`SELECTED`.

If a query must be staged in order to establish existence, treat it like live filter
input: retain the origin in the transaction and finalize the history entry only on
success. On definitive failure, restore the origin query without adding a history
record. Direct resolvers should make this staging path uncommon.

## 11. Query-history and link-trail semantics

The two return mechanisms should remain distinct:

- `^` / `_` navigate the destination pane's committed query history. A link identity
  query must add exactly one history entry, so one `^` restores the query it replaced.
- `Ctrl+O` / `Ctrl+I` navigate the full link trail, including tab, pane, project scope,
  selection, and reversible fold changes.

Shared project scope is not currently part of every pane's `QueryRecord`. Therefore `^`
can promise to restore the prior **query**, but a cross-project jump may still require
`Ctrl+O` to restore the complete prior location. That distinction should be documented
rather than silently overloading query history with global scope. For panes where project
is itself a query term (notably Patch and Stitch), the identity query should include the
project/repository and `^` naturally restores it.

All direct `_clear_filter_for_entry_jump()` state mutations should be removed from the
selection-refresh loop or changed to call the pane's commit method. Query mutation
should occur only at the coordinator's transaction boundary; a row renderer should not
silently rewrite user state.

Patch also needs the same host query adapter used by other panes so link-trail capture
and generic navigation can read/apply its query. The app already has Patch-specific
query-history adaptation, so this is mostly protocol normalization, not a second history
system.

## 12. True failure and messaging

"Virtually never" should mean no false warning, not suppression of real failures. The
coordinator should distinguish:

- `Artifact bead:X no longer exists` — authoritative dangling ref;
- `Artifact stitch:R@S could not be loaded: <reason>` — acquisition failure;
- `No Artifacts pane is installed for ref kind K` — unsupported/missing provider;
- no toast — pending, superseded, or cancelled request;
- `Revealed <ref>; press ^ to restore your query` — successful query recovery.

Pane-local "no longer visible" warnings should be removed. Only the coordinator has the
transaction context necessary to know whether all recovery rungs are complete and to
avoid duplicate toasts.

## 13. Implementation sequence

### Phase 1: correctness before new query fields

1. Preserve the canonical ref through `_follow_artifacts_target()` and treat
   `neighbor_target` as a hint.
2. Fix the synthesized identity cases using the existing known-target reconciliation
   rules for loaded rows.
3. Stop using `RelationRole.FAMILY` for arbitrary link follows, and make the Patch
   relation reveal return `False` when selection fails.
4. Replace the Boolean request result with tri-state completion, or add a parallel
   link-request API with that result.
5. Centralize final warnings and wait for authoritative coverage.

This phase removes wrong-row and premature-missing failures even before the ideal query
UX is complete.

### Phase 2: reversible identity queries

1. Add/promo identity fields: Bead `id:`, Stitch `sha:`, File logical `id:` or
   `reference:`, and exact provider identity/path.
2. Add a pane method that returns its validated identity query for a resolved target.
3. Normalize the host query-commit adapter across all panes, including Patch.
4. Route every programmatic recovery rewrite through one commit and remove direct filter
   mutations.
5. Make the success notice advertise `^`.

### Phase 3: targeted hydration and polish

1. Resolve Stitch SHA, file logical id, Agent canonical name, Bead id/kind, and provider
   identity without growing an entire inventory.
2. Add cancellation/generation handling and a visible pending indicator for slow
   providers.
3. Optionally mark Links-panel entries as visible, recoverable, pending, unsupported, or
   definitively dangling using the same resolver.
4. Add outcome counters in debug logging so future work can measure which recovery rung
   is actually used.

## 14. Verification plan

The regression suite should verify behavior, history, and timing, not only the final
selected tuple.

### Address normalization

- epic, phase, flag, and task bead refs resolve to their actual row kind;
- abbreviated and full Stitch SHAs resolve to the same target;
- Agent aliases/local-global names resolve to the canonical row;
- active, proposed, and archived provider documents resolve correctly;
- duplicate Patch names select the requested project;
- file refs resolve to the pane's logical id.

### Query recovery

- each pane generates the narrow identity query expected by its dialect;
- special characters and spaces are quoted through the query builder, not string
  concatenation;
- only one previous-query record is pushed;
- one `^` restores the exact prior source/canonical query and selection;
- `_` reapplies the navigation query;
- an open filter session is synchronized or closed cleanly;
- no intermediate `limit:all` or empty query appears in history.

### Async correctness

- partial Agent, Plan, File, Bead, and Stitch snapshots return `PENDING`, not `MISSING`;
- selection and trail finalization happen after the matching generation completes;
- a second link follow supersedes the first without a stale selection or toast;
- true absence warns once only after authoritative coverage;
- load failure is not reported as deletion;
- failed staged queries restore the origin without polluting history.

### Navigation surfaces

- the Links panel and `$N` rail share the same coordinator;
- folds expand only as far as needed and `Ctrl+O` reverses the navigation;
- cross-project navigation restores full scope through `Ctrl+O`;
- the Patch pane no longer receives a fabricated family reveal;
- unsupported/dangling refs retain honest failure behavior.

## Recommended solution

Implement option D: an app-owned, transactional link-navigation coordinator driven by
the canonical artifact ref. Keep the current synthesized target only as a pane-routing
and visible-row fast-path hint. Add a destination adapter that resolves or directly
hydrates the ref into the pane's real row target and returns `SELECTED`, `PENDING`,
`MISSING`, or `FAILED`. When the resolved row is excluded by the current view, have the
pane build a narrow domain identity query—`project + name` for Patches, canonical `name`
for Agents, exact `id` for Beads/Files, `repo + sha` for Stitches, and `project + path` or
provider identity for documents—and commit it exactly once through the existing query
history seam. Finalize the link trail only after selection, and warn only after an
authoritative missing result.

This solution is preferable to clearing filters or forcing `limit:all`: it fixes both
wrong identities and filtered rows, avoids broad loads, makes `^` reliably restore the
previous query on every healthy Artifacts sub-tab, preserves `Ctrl+O` for full
cross-tab/project restoration, and leaves warnings only for artifacts that are genuinely
gone or cannot be loaded.
