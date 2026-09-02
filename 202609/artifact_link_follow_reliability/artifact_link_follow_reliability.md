---
create_time: 2026-09-02
updated_time: 2026-09-02
status: research
---

# Artifact Link Follow Reliability: Consolidated Research

**Research question:** following a link from the Artifacts Links panel (`$0`) or the
link rail (`$1`-`$9`) very often ends in a "no longer available on that tab" warning
toast instead of a jump. The Agents tab's `<enter>` keymap already solves the analogous
problem for the Patch tab by rewriting the destination query and leaving the old query
on the `^` history stack. Can that strategy be generalized so link follows virtually
never fail, and what is the best implementation?

**Provenance:** two independent researchers analyzed `sase` at master `8b0c65476`;
this report merges their findings with the lead researcher's own verification pass.
Every load-bearing claim below was re-verified against the source. No runtime telemetry
exists, so the relative frequency of the failure classes is an inference from code
structure, not a measurement.

---

## 1. Executive summary

Both researchers converged on the same central discovery, which reframes the request:
**query filtering is only half the problem, and probably the smaller half.** The toast
is not one bug — four independent failure conditions are collapsed into the same
"not visible" result:

1. **Identity mismatch (dominant).** The chip handed to the follow path carries a
   *synthesized* row target built by guessing fields the pane actually keys rows by.
   Selection is an exact tuple lookup, so a link to any epic/phase/flag bead, active or
   proposed plan, abbreviated stitch SHA, or differently-spelled project **fails even
   when the row is on screen**. No query rewriting fixes this.
2. **Genuinely filtered out** — the class the user's proposed strategy targets, and it
   is real: Stitches ships `sidecar:false merges:hide since:24h`, Beads ships
   `-status:closed`, every pane gets a `limit:<page_size>` head slice, and
   project-scoped panes hide cross-project links.
3. **Incomplete data treated as absence.** Boolean APIs make "still loading" and
   "pending" indistinguishable from "missing"; panes disagree on when absence is
   authoritative; the follow path silently gives up while a pane is loading.
4. **Genuinely dangling refs** — these *should* fail, but with a different message.

Two pieces of good news, both verified:

- **`^` already works on every Artifacts sub-tab.** The pane-generic
  `ArtifactsQueryHistoryActionsMixin` shadows the Patches-only implementation because
  `ArtifactsMixin` precedes `PatchMixin` in `AceApp`'s bases
  (`src/sase/ace/tui/app.py:124-125`; keymap at `src/sase/default_config.yml:574-575`).
  No new `^` support is needed.
- **Every non-degraded pane's query-commit path already records history**, so any
  rewrite committed through that seam is `^`-reversible for free. The reveal machinery
  (`relation_reveal.py`) and the ref-reconciliation logic (`_known_target_for_ref`)
  the fix needs are also already in-tree — just not wired to link following.

**Recommendation (detailed in §6):** first make the destination pane resolve the ref
against its own rows (kills class 1 with no query rewriting at all), then add a generic,
host-owned reveal ladder — identity query → minimal widening → neutral fallback — with
every rewrite committed exactly once through the existing history seam, tri-state
completion instead of Booleans, and warnings only after authoritative absence.

---

## 2. The current follow path

Both a rail jump and a Links-panel selection call
`LinkFollowMixin._follow_artifacts_target()`
(`src/sase/ace/tui/actions/link_follow.py:338`). The ladder is:

1. select the synthesized target if already visible in the active pane;
2. switch shared project scope derived from the target tuple;
3. switch to the Artifacts tab and destination pane, `request_entry_target()`;
4. **return `False` silently if the pane is loading** (`link_follow.py:355`);
5. rewrite `limit:N` → `limit:all` via `apply_host_limit_query` and retry;
6. call `reveal_entry_target(target, role=RelationRole.FAMILY)` and retry;
7. toast `Linked target {ref} is not visible in {pane}`.

Three contracts under this ladder are too weak:

- `request_entry_target()` returns `bool`, documented as "select a target now, or
  remember it for the next loaded row model"
  (`widgets/artifacts/entry_navigation.py:47`) — so `False` means both "accepted and
  pending" and "not found".
- Selection is an exact `ArtifactEntryTarget` dict lookup
  (`beads_navigation.py`, `files_navigation.py`), so an approximately synthesized
  target is no better than no target.
- `reveal_entry_target()` is a default `return False` for every pane except Patches
  (`entry_navigation.py:84`).

The Links panel is not the source of the problem; it exposes weaknesses in the shared
follow path used by both link surfaces.

---

## 3. Failure taxonomy (verified)

### Class A — Identity mismatch: the target can never match a row

`LinkIndex._build_chip()` (`tui/relations/link_index.py:213`) calls
`target_for_ref_kind()` — a pure kind-dispatch that synthesizes a target "with no
known-target lookup" (`tui/relations/artifact_links.py:225`). Verified dispatch:

| Ref kind | Synthesized | Real row target | Gap |
| --- | --- | --- | --- |
| `bead:X` | `(project_hint, **"task"**, X)` | `(row.project, row.kind, id)`, kind ∈ `task\|flag\|epic\|phase` | Epic, phase, flag beads never match |
| `plan:X` / `ref:<k>:X` | `(project_hint, **"archive"**, X)` | kind ∈ `proposal\|active\|archive`; proposal identity is a notification id | Active/proposed documents never match |
| `stitch:repo@sha` | `(repo, sha as supplied)` | `(repo, full_40char_sha)` | Abbreviated SHAs never match |
| `patch:X` | `(project_hint, X)` | `(patch.project_name, X)` | Project key vs display spelling divergence |
| `file:X` | `(payload,)` | `(logical_id,)` | Only when payload *is* the logical id |
| `agent:X` | `(payload,)` | `(canonical row name,)` | Aliases and local/global names diverge |

The `project_hint` is a project *key* from `load_project_ref_display_snapshot()`; row
models store whatever their loader used (patches: `project_name`), so any spelling
divergence is a silent miss.

**The reconciliation logic already exists and is bypassed.** `_known_target_for_ref()`
(`tui/relations/artifact_links.py:276`) resolves refs against an index of real rows —
SHA-prefix matching, agent alias candidates via
`current_owner_agent_name_lookup_candidates`, file first-part matching,
pane/last-part matching. The in-pane relations panel uses it; the link rail and Links
panel skip it because `_build_chip` calls bare `target_for_ref_kind`.

Given how heavily SASE uses epic/phase beads, and that `agent implements bead` /
`stitch implements bead` edges are auto-projected for every agent and trailer-bearing
commit, a large fraction of rail chips are addressed by tuples no pane will ever match.
This explains "very often" better than filtering does — though without telemetry the
dominance ranking is an inference (Phase 4 below adds outcome counters to settle it).

### Class B — Genuinely filtered out

| Pane | Committed default | Links it hides |
| --- | --- | --- |
| Stitches | `sidecar:false merges:hide since:24h` (`default_config.yml:170`) | Any stitch older than 24h, in a sidecar, or a merge |
| Beads | `-status:closed` (`src/sase/bead/filter_query.py:67`) | Every link to closed work — most historical links |
| All panes | `limit:<page_size>` head slice injected at startup | Anything past the head |
| Project-scoped panes | seeded project scope | Cross-project links |
| Plans/providers | lazily loaded deep archive | Older archived documents until a grow pass |
| Beads/Files/Agents | folds/groups | Present but folded rows (phase beads under a collapsed epic) |

Only the `limit:` case is handled today (`_drop_head_slice_limit`,
`link_follow.py:388`), and it is reversible only because `apply_host_limit_query`
commits through the pane's history-recording seam.

**A defect only one researcher caught, now verified:** when a pending target does not
appear, several panes clear their filters by *mutating state directly* —
`self.filters = BeadFilterValues()` (`beads_options.py:353`),
`self.query_source = ""` (`agents_options.py:217`), and the analogous assignments in
`plans_options.py` and `files_options.py`. These bypass the `_commit_*` /
`_record_artifacts_query_transition` funnel, so the UI toasts "Cleared Beads filter to
show linked bead" while **`^` has no record of the query it replaced.** Today's partial
recovery already breaks the very way-back the user wants to rely on.

### Class C — The reveal ladder is a stub, and its one rung is wrong

- Five of six panes have no `reveal_entry_target` at all (base `return False`).
- The only implementation (Patches) is called with `role=RelationRole.FAMILY`
  (`link_follow.py:360`). `_change_query_for_navigation`
  (`actions/navigation/_tree.py:446-505`) builds the reveal query from
  `self.patches[self.current_idx]` — **the currently selected patch, not the link
  target** — producing a `sibling:` query about an unrelated patch's revert family.
- **It reports success anyway:** on a selection miss it toasts
  `"{target} is not reachable through {new_query}"` and still returns `True`, so a
  failed jump clobbers the user's Patch query *and* is recorded as a link-trail hop.
- **The Patches pane implements neither `host_limit_query` nor
  `apply_host_limit_query`** (verified: only agents/beads/commits/files/plans
  implement the protocol). Consequences: the `limit:` rung can never fire for a patch
  link, and `_current_link_trail_origin` (`link_follow.py:293`) captures
  `query_source=None` for a Patches origin, so `Ctrl+O` cannot restore the Patch query
  on the way back.
- **Silent give-up while loading** (`link_follow.py:355`): `_pane_is_loading` probes
  only `_loading`/`_loading_full` (`link_follow.py:529`), which does not cover Stitches
  collection/query workers. Worse, by that point `request_entry_target` has already
  stored `_pending_entry_target`, so the row often *is* selected on the next snapshot —
  but the follow returned `False`, recorded no trail hop, and updated no rail state.
- Panes disagree on when absence is authoritative: Files waits for
  `snapshot.complete`; Beads/Plans treat any current-project snapshot with
  `_loading == False` as final; Agents warns as soon as `_current_snapshot()` is
  non-null (`agents_options.py:189`) even if capped. Premature "missing" toasts follow.

### Class D — Genuinely dangling refs

The panel already marks these (`_is_missing`,
`modals/artifact_links_panel_modal.py:75`) and `sase artifact doctor` reports them.
These should keep failing — with an honest "no such artifact" message distinct from
"not visible here".

---

## 4. Existing machinery to build on

- **The query-history seam.** Every non-degraded pane's `_commit_*` path records
  history by default via `_record_artifacts_query_transition`
  (`beads_filter_session.py`, `agents_query.py`, and siblings). A rewrite committed
  through this seam is `^`-reversible with no new persistence code. Rough edge: the
  `apply_host_limit_query` signature is inconsistent (`grow:` kwarg exists on only
  three panes; `link_follow.py` papers over it with `try/except TypeError`).
- **`relation_reveal.py` — the generalization already written.** A reversible
  query-rewrite lens: builds the rewrite from a *declared query-profile field* (not a
  hard-coded token), returns `None` when a dialect lacks the field, records the origin
  query and profile digest, and **self-retires** — the lens is live only while the
  pane's canonical query equals `revealed_canonical`, so any user edit or `^` retires
  it with no clear step. Currently reachable only from Patch relation navigation.
- **`_known_target_for_ref` / `_KnownTargetIndex`** — the ref→row reconciliation rules
  to lift into the pane contract (§3A). Useful as a loaded-rows fast path; must not
  become a requirement that panes materialize complete inventories.
- **The pending-target machinery.** Panes already store `_pending_entry_target` and
  select it on the next refresh; the points where they clear it on success (e.g.
  `agents_options.py:182`) are natural completion hooks for async follow-through.
- **The profile evaluator** (`src/sase/ace/query/profile_evaluator.py`) — can test a
  committed query's terms against a concrete row, enabling minimal widening (§6, rung 5).
- **The Agents→Patch precedent** (`_notification_navigation.py:207`): behaviorally
  right (rewrite, record for `^`, reload, select) but not a template — it is
  Patch-only, rewrites to a whole `project:<name>` rather than the exact target,
  assumes a synchronous reload, and does nothing about identity mismatch.

---

## 5. Design options and disagreement resolution

Options both researchers considered, merged:

| Option | Fixes | Verdict |
| --- | --- | --- |
| Better toast only | nothing | Insufficient — the user asked for the jump to work |
| Pane-side ref resolution | Class A | **Required first.** Nothing else works without it |
| Ad-hoc fallbacks per pane | B, badly | Rejected: the four existing divergent pending-target fallbacks demonstrate the drift |
| Universal `reference:<ref>` query field | partial B | Rejected as primary: still needs canonicalization/fetch behind it; imposes a reserved token on every dialect |
| Targeted identity query per pane dialect | B | **Best primary rung**; needs small dialect additions |
| Minimal widening (drop only the excluding terms) | B | Best UX; viable only after ref resolution hands the host the actual row |
| Neutral query (`limit:all` + scope) | B | Guaranteed last rung, too blunt as the only one |
| Pin target as injected row | B, cosmetically | Rejected: every pane's grouping/ordering/counters would need a pinned-row concept |
| Host-owned coordinator + tri-state completion | C | **Required** for correct async, trail, and warning behavior |

The researchers disagreed on three points; resolutions:

1. **Trail hops while a pane is loading.** One proposed recording the hop
   optimistically and letting the pending machinery land it; the other insisted the
   trail record only completed navigations. *Resolution: finalize-on-select.* An
   optimistic hop records a navigation that may never happen (wrong trail, wrong rail
   state, and the pane's own premature-missing toast may still fire). The pending-clear
   points that already exist in every pane make a completion callback cheap: keep the
   transaction open, finalize the hop and rail refresh when the pane reports the
   pending target landed, cancel it on supersession. What both agreed on — the silent
   `return False` at `link_follow.py:355` is a bug — is fixed either way.
2. **`limit:all` as the guaranteed rung vs. avoiding broad loads.** *Resolution: keep
   the neutral rung, ordered last.* It is the rung that makes "virtually never" true
   for anything in the pane's inventory, and with identity-query and minimal-widening
   rungs ahead of it, it fires rarely. But it is not actually guaranteed: it cannot
   show a row the pane never fetched (deep-archive plans, stitches outside the
   collection window, capped provider snapshots). Direct, targeted hydration —
   resolving a stitch SHA through the VCS provider, a file through the artifact index,
   a document through its provider — is the eventual replacement for those cases and
   belongs in a later phase. The identity predicate must reach *data acquisition*, not
   just filter a capped client snapshot.
3. **Contract shape: a synchronous pane resolver vs. a transactional address API.**
   *Resolution: both, staged.* Phase 1 adds the synchronous resolver (small, kills
   Class A). The tri-state transactional API is the end state that fixes Class C; the
   resolver becomes its first step rather than a discarded intermediate.

---

## 6. Recommended solution

A layered fix; each layer is independently shippable and valuable. Layers R1+R2
deliver most of "virtually never"; R4 makes the remainder honest.

### R1 — Destination-pane ref resolution (fixes Class A; do this first)

Add to the `ArtifactEntryNavigator` contract:

```python
def entry_target_for_ref(self, kind: str, payload: str) -> ArtifactEntryTarget | None:
    """Resolve a link-graph ref to this pane's own row identity.

    Answered from the pane's *unfiltered* snapshot, so a filtered-out row still
    resolves — which is what lets the host build a reveal for it.
    """
```

Each pane answers from the row model it already owns: beads match `issue.id`
regardless of row kind or project spelling; stitches match `full_id.startswith(sha)`;
documents match path/identity across proposal/active/archive; files match
`logical_id`; agents match canonical-name candidates; patches match `patch.name` (with
project disambiguation). Lift the rules from `_known_target_for_ref` rather than
rewriting them.

Change `_follow_artifacts_target` to address by **canonical ref** and demote
`chip.neighbor_target` to a pane-routing and visible-row fast-path hint —
`target_for_ref_kind` is right about *which pane* and wrong only about *which row*.

**Boundary note (both researchers, independently):** ref → row-identity resolution is
shared backend behavior — a web frontend or a CLI `sase artifact link follow` needs the
same mapping — so per the `rust_core_backend_boundary` memory the canonical rules
belong in `../sase-core/crates/sase_core`, with the Python panes as thin adapters. The
ladder orchestration, keybindings, toasts, history, and trail are presentation and
stay in this repo.

### R2 — A generic host-owned reveal ladder (fixes Class B)

Replace rungs 5–7 of the current ladder; attempt each only if the previous missed:

1. Select in place (unchanged).
2. Project scope switch (unchanged — but see R4 for the reload race it triggers).
3. Drop the `limit:` head slice (existing rung).
4. **Expand folds:** if the resolved row is loaded but hidden by an epic/group fold,
   expand the minimum fold and select — no query change at all. (The beads pane's
   `_expand_parent_for_pending_target` shows the shape.)
5. **Identity reveal:** build the tightest query that provably contains the row via a
   `build_identity_reveal_query(profile, row)` sibling of
   `build_relation_reveal_query`, driven by a declared identity field, returning
   `None` when the dialect has none (needs R5).
6. **Minimal widening:** with the actual row in hand from R1, evaluate the committed
   query's terms against it with the profile evaluator and drop only the excluding
   terms — `since:24h` for an old stitch, `-status:closed` for a closed bead — keeping
   everything else the user had.
7. **Neutral query:** `limit:all` plus required scope. Blunt, rare, honest.
8. Only now, a toast — distinguishing *dangling* ("no such artifact") from *not in
   inventory* ("the Stitches pane has no commit `abc1234`") from *load failure*.

Two invariants for every rewriting rung:

- **Commit through the pane's existing query seam** — never by poking
  `filters`/`query_string` directly — so exactly one history entry is pushed and one
  `^` restores the exact prior query. Remove or reroute the four direct
  `_clear_filter_for_entry_jump` mutations (§3B) through the same seam.
- **Wrap the rewrite in a `LinkReveal` lens** (the `RelationReveal` shape keyed by
  pane, followed ref, origin `QueryRecord`, revealed canonical). Its self-retiring
  liveness rule gives a correct "the reveal is over" signal with no clear step.

Semantics to preserve and document: `^`/`_` navigate the pane's committed query
history; `Ctrl+O`/`Ctrl+I` navigate the full link trail including tab, pane, project
scope, and fold reversal. A cross-project jump restores its *query* via `^` but its
complete prior location via `Ctrl+O` — don't overload query history with global scope.

### R3 — Patches-pane repairs

- Implement `host_limit_query`/`apply_host_limit_query` on Patches, delegating to the
  existing `_display_patch_query`/`_commit_patch_query`. This gives Patches the
  `limit:` rung *and* fixes `Ctrl+O` query restoration for Patches origins.
- Stop calling `reveal_entry_target(..., role=RelationRole.FAMILY)` from link-follow;
  relation roles are relation-graph vocabulary, not link vocabulary. Route patches
  through the R2 ladder.
- Make `_change_query_for_navigation` return `False` when selection misses, so a
  failed reveal is no longer recorded as success (`_tree.py:486-503`).
- Normalize `apply_host_limit_query(query, *, grow: bool = False)` across panes and
  delete the `try/except TypeError`.

### R4 — Tri-state completion (fixes Class C)

Replace the Boolean result with (or add a parallel link API returning):

```python
class LinkRequestState(Enum):
    SELECTED = auto()   # exact target selected now
    PENDING  = auto()   # accepted; authoritative resolution still running
    MISSING  = auto()   # authoritative coverage proved absence
    FAILED   = auto()   # acquisition error — not the same as deleted
```

The coordinator captures the origin (tab, pane, query record, selection, scope, trail
position) before acting; a `PENDING` result keeps a generation-tagged transaction open;
the pane's existing pending-clear points report completion; a later user action or
second link follow cancels the stale generation. **The link-trail hop and the rail
refresh finalize only on `SELECTED`; warnings fire only on authoritative `MISSING`
(with `FAILED` reported distinctly).** Pane-local "no longer visible" toasts move into
the coordinator, which is the only place with enough context to warn once and honestly.

### R5 — Small, closed dialect additions

| Pane | Today | Add |
| --- | --- | --- |
| Patches | exact `name:` + `project:` | nothing |
| Agents | exact `name:` | nothing (resolve aliases before committing) |
| Beads | `id` search-only (`filterable=False`) | filterable exact `id:` |
| Stitches | **no SHA field at all** | prefix-matching filterable `sha:` |
| Files | paths search-only, logical id absent | exact `id:` (logical) |
| Plans/providers | `path` search-only | exact `path:`/provider identity |

Budget for digest churn: `QueryRecord.profile_digest` detects dialect changes
(`query_record.py:66-71`), so adding fields invalidates saved queries and stored
history records and must be handled the way other dialect changes are.

### R6 — Make the reveal visible and reversible in the UI

- When a rewriting rung fires: `Revealed bead:sase-123 — press ^ to restore your
  query`. The existing `_drop_head_slice_limit` notice is the model.
- Show a lens chip while a `LinkReveal` is live, mirroring the trail breadcrumb.
- Pre-flag rows in the Links panel that would need a reveal (or are dangling), reusing
  R1 resolution — the panel already runs a background staleness pass to piggyback on
  (`link_follow.py:272`).

### R7 (later) — Targeted hydration

Resolve stitch SHAs through the VCS provider, file logical ids through the artifact
index, documents through their provider, and agents/beads through direct lookup —
without growing whole inventories. This removes the residual cases the neutral rung
cannot reach and lets slow panes show a pending indicator instead of loading
thousands of rows.

### Sequencing

| Phase | Content | Effect |
| --- | --- | --- |
| 1 | R1 + R3's `return False` fix + stop passing `FAMILY` | Most toasts disappear; no query rewriting yet |
| 2 | R4 tri-state + R3 Patches host-query protocol | Loading races, premature warnings, Patch trail all fixed |
| 3 | R2 rungs 4/6/7 (folds, minimal widening, neutral) + reroute direct filter clears through the seam | "Virtually never" for Class B; `^` reliable everywhere |
| 4 | R5 + R2 rung 5 (identity reveal) + outcome counters in debug logging | Narrow reveals instead of blunt ones; measure which rung fires |
| 5 | R6 + R7 | Discoverability of `^`; residual hydration cases |

---

## 7. Verification plan

- **Address normalization:** one regression per Class-A shape — epic, phase, and flag
  bead; proposed and active plan; abbreviated stitch SHA; cross-project patch; agent
  alias; file logical id. The existing duck-typed harness in
  `tests/ace/tui/test_link_follow.py` extends naturally: panes whose
  `select_entry_target` rejects the synthesized tuple but accepts the resolved one,
  asserting rung order and the recorded `^` entry.
- **Query recovery:** each pane produces its expected identity query with proper
  quoting via the query builder; exactly one previous-query record is pushed; one `^`
  restores the exact prior source and selection; `_` reapplies; no intermediate
  `limit:all` or empty query pollutes history; an open filter session closes cleanly.
- **Async correctness:** partial snapshots yield `PENDING` not `MISSING`; trail
  finalizes only after the matching generation selects; a second follow supersedes the
  first without stale toasts; load failure is not reported as deletion.
- **Surfaces:** Links panel and rail share the coordinator; folds expand minimally and
  `Ctrl+O` reverses everything including scope; Patches no longer receives a
  fabricated family reveal; dangling refs keep failing honestly.
- **Process:** read `sase/memory/lint_and_test.md` before landing (`just check` lane
  vs. the `just check-full` gate); PNG snapshots needed for the R6 chip; per
  `sase/memory/sase_flags.md` this changes user-reaching navigation behavior and
  likely wants a flag bead so the old ladder stays reachable.

---

## 8. Bottom line

The user's instinct — "do what the Agents `<enter>`→Patch jump does, and let `^` undo
it" — is correct, and the `^` half already works on every Artifacts sub-tab. Two
amendments make it deliver "virtually never":

1. **Fix addressing before filtering.** The largest share of the toasts are rows
   already on screen that the synthesized target simply cannot address. Pane-side ref
   resolution (R1), with canonical rules in `sase-core`, is the prerequisite for
   everything else and removes most failures with no query rewriting at all.
2. **When rewriting is needed, make it narrow, transactional, and committed through
   the existing history seam** — identity query, then minimal widening, then a neutral
   last resort — with tri-state completion so loading is never reported as absence,
   the trail records only real navigations, and the only remaining toasts are honest
   ones about artifacts that genuinely no longer exist.
