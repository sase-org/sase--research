---
create_time: 2026-08-10
updated_time: 2026-08-10
status: research
---

# External Issues as Beads and External Pull Requests as Patches

**Research question.** How should SASE continuously ensure that every issue in an
external tracker has a corresponding bead, and every pull request not created by SASE
has a corresponding Patch, for every enabled project on a machine? How should ACE then
present those relationships without retaining separate Bugs and PR-centric inventories?

**Scope.** `sase` at `14279fd90` and the linked `sase-github` plugin at `4603b35`, read
2026-08-10. The concrete provider is GitHub, but the recommended ownership boundaries
are provider-neutral. “External issue” below means an issue stored in a provider such as
GitHub, regardless of whether it was initially opened through a SASE UI. “External PR”
means a PR whose creation was not performed by SASE's tracked PR workflow.

## Bottom line

Use two lightweight Axe chops, expanded once per enabled project, to run one shared,
provider-neutral reconciler through plugin hooks:

1. An **issue-to-bead chop** establishes the invariant “every remote issue is referenced
   by at least one local bead.” If no bead references the issue, it creates an `open`,
   `large` task bead whose `REFS` contains the existing canonical
   `bug:<project>#<number>` reference. It never creates a second bug model and never
   continuously overwrites locally edited bead text.
2. A **PR-to-Patch chop** lists remote PRs, matches them by canonical PR identity, and
   creates a Patch only when the PR lacks SASE creation evidence and no Patch already
   owns that PR. Imported Patches carry a new explicit `PR_ORIGIN: external` field.
   SASE's own PR workflow writes `PR_ORIGIN: sase` and a durable `SASE_PATCH=<name>`
   marker into the remote PR body. An absent field means `unknown`, not `sase` or
   `external`.

The plugin system should own remote listing and mutation. SASE core should own identity,
deduplication, reconciliation, and local bead/Patch mutations. Axe should own cadence,
enabled-project expansion, durable cursors, history, and operator controls.

In ACE, remove the Bugs sub-tab and enrich Bead rows/details with issue badges and
provider operations derived from `bug:` refs. Rename the PRs sub-tab to Patches and show
both the PR association and its explicit origin. This makes the local engineering
records—beads and Patches—the inventory, while remote issues and PRs are linked facets
of those records.

## 1. Current architecture and the useful seams already present

### 1.1 Issues already have a provider-neutral plugin boundary

The main repo already defines `IssueWire` and optional VCS provider hooks for list, get,
create, update, URL resolution, and state changes (`src/sase/vcs_provider/_types.py`,
`_hookspec.py`, `_plugin_manager.py`, and `_base.py`). The linked GitHub plugin implements
those hooks using `gh issue ... --json` in `src/sase_github/plugin.py`.

This is the right abstraction. GitHub-specific commands, authentication errors, rate
limits, pagination, and JSON normalization belong in `sase-github`; the meaning of “a
remote issue must be covered by a bead” does not.

There are two limitations to correct before using this boundary for background sync:

- `IssueWire` has repository-local `number` and `url`, but not a provider-stable opaque
  ID. Add `provider_id` (GitHub's node ID) so cursors and diagnostics can distinguish
  objects robustly. The stored bead association should remain the human-readable
  `bug:<project>#<number>` ref.
- `supports_issues()` currently treats complete CRUD support as one capability. A
  synchronizer only requires listing, and a read-only provider should still populate
  badges even if ACE cannot edit or close an issue. Split listing, reading, and mutation
  capabilities, or expose a structured capability record and enable each command
  independently.

The GitHub CLI already exposes the fields needed for this design: issue listing can
return `id`, number, state, timestamps, URL, and tracker metadata, while PR listing can
return `id`, draft state, head/base refs, timestamps, merge state, and URL. See the
official [`gh issue list`](https://cli.github.com/manual/gh_issue_list) and
[`gh pr list`](https://cli.github.com/manual/gh_pr_list) references.

### 1.2 `bug:` refs are already the general bead-to-issue relation

SASE's artifact-reference grammar already has a canonical bug reference:

```text
bug:<project-display-name>#<number>
```

All bead kinds have a repeatable `refs` collection, and `sase bead create -R` /
`sase bead ref add` already normalize and persist those refs. The resolver already knows
how to turn a bug ref into the provider URL and prompt representation. That makes a new
`EXTERNAL_BUG`, `GITHUB_ISSUE`, or task-only schema field unnecessary.

Two current compatibility paths should be folded into the same semantic index:

- Epic/phase actions use the plan-only `changespec_bug_id` / `patch_bug_id` metadata.
- `src/sase/bug_links.py` links remote issues to epics and Patches, but does not inspect
  task bead refs.

The reconciler and ACE should use one helper that extracts normalized bug identities
from every bead's `refs`, then projects legacy plan metadata as an equivalent association.
A migration may add the canonical ref to legacy plan beads, but rollout must not create a
duplicate task bead merely because an existing epic uses the old field.

The resulting invariant should be **at least one associated bead per remote issue**, not
“exactly one ref in the entire store.” The chop creates at most one import bead, while a
user may intentionally attach the same issue to additional phases or tasks.

### 1.3 Patch storage has the association but not its provenance

`docs/change_spec.md` explicitly says SASE does not yet discover external PRs. A Patch
already has an optional `PR:` URL, but `src/sase/ace/patch/models/patch.py` and the
parser/writer have no field describing who created that PR. Therefore these two records
are indistinguishable today:

```text
# SASE created the Patch, then created its PR.
PR: https://github.com/sase-org/sase/pull/123

# A person created the PR, then SASE imported a Patch for it.
PR: https://github.com/sase-org/sase/pull/124
```

Inferring provenance from the existence of `PR:` would produce exactly the UI ambiguity
the requested design needs to eliminate. Add a narrowly named field:

```text
PR: https://github.com/sase-org/sase/pull/124
PR_ORIGIN: external
```

Allowed values should be `sase`, `external`, and `unknown`; an absent field parses as
`unknown` for backward compatibility. `PR_ORIGIN` is preferable to a generic `SOURCE`
because it records the provenance of the remote review association, not who later edits
the Patch, writes its commits, or adopts its work.

Existing Patches must not be silently labeled `sase`. Prospective writes can be exact;
historical entries should remain `unknown` unless evidence is conclusive or the user
chooses an origin.

### 1.4 Axe already supplies enabled-project fan-out

An Axe chop with:

```yaml
for_each:
  source: projects
```

expands into one stable instance per enabled project. The target includes the stable
project key, display name, VCS kind, workspace reference, and workspace directory. Each
expanded instance has independent cadence, run history, state directory, checkpoints,
and deduplication. This is a direct fit for machine-local reconciliation and automatically
stops scheduling work when a project is disabled.

Plugin packages can contribute exact-name chop executables and default Axe configuration
through their `sase_config` entry point. The GitHub plugin is therefore the natural place
to provide the GitHub remote implementation and enable the applicable project targets.
The reconciliation library itself should remain in SASE so another provider plugin does
not have to reimplement bead and Patch semantics.

## 2. Recommended ownership boundary

The clean split is:

| Layer | Responsibility |
| --- | --- |
| Provider plugin | Authenticate; list/get/edit remote issues and PRs; normalize pages/deltas into provider-neutral wires; parse and write provider-specific remote markers. |
| SASE core/domain | Canonical remote identity; compare remote inventory with bead/Patch indexes; classify create/update/no-op/conflict; validate provenance and lifecycle mappings. |
| Python host adapters | Resolve enabled project stores; acquire existing locks; execute bead events and Patch-file/archive mutations; publish chop reports. |
| Axe | Per-project scheduling, manual runs, non-overlap on one machine, cursor/checkpoint paths, run history, retries, and health visibility. |
| ACE | Display the reconciled local records; lazily/batch-load remote facets; expose only operations supported by the active provider. |

The deterministic reconciliation planner belongs in `sase-core` under the current Rust
backend rule: a CLI, TUI, webhook receiver, or future service must classify the same
remote snapshot identically. Provider calls and local filesystem orchestration can stay
in Python. The planner should accept plain wire data and return an action plan such as
`CreateBead`, `CreatePatch`, `RefreshRemoteFacet`, `Noop`, or `Conflict`; it should not
perform network or file I/O itself.

## 3. Why two chops are better than one

Put both under one plugin-contributed lumberjack, but schedule two project-expanded
chops, for example:

```text
external_artifacts
├── external_issue_sync[sase]
└── external_pr_sync[sase]
```

Separate chops are preferable because issue and PR reconciliation have different stores,
permissions, failure modes, status policies, backfill costs, and likely cadences. A rate
limit or malformed PR should not prevent issue ingestion; an operator should be able to
disable or manually rerun one lane; and each result should report useful counts without
combining unrelated errors.

A shared library should still handle cursor I/O, overlap windows, canonical URL parsing,
project resolution, and structured reports. Suggested default cadence is every five
minutes with jitter, plus a daily repair scan. Both values should be configurable and
plugin defaults should be easy to disable. This is frequent enough for an inventory UI
without treating Axe as a real-time webhook server.

### 3.1 Polling is the correct first transport

Webhooks can reduce latency, but they require a continuously reachable HTTP endpoint,
repository webhook configuration, delivery authentication, replay handling, and write
permission to manage hooks. GitHub supports `issues` and `pull_request` webhook events,
but that does not remove the need for backfill and repair after downtime; see GitHub's
official [webhook overview](https://docs.github.com/en/webhooks/about-webhooks) and
[event reference](https://docs.github.com/en/webhooks/webhook-events-and-payloads).

Periodic Axe reconciliation uses the credentials and enabled-project lifecycle SASE
already has. A webhook receiver can later trigger an immediate forced run of the same
reconciler, while the polling chop remains the source of repair. Do not build a second
event-processing domain model for webhooks.

### 3.2 Cursor and backfill algorithm

The provider API should be delta-oriented and paginated rather than asking core to call
`list --limit 1000000` on every tick:

1. The first run starts an exhaustive, resumable backfill and indexes all local bug refs /
   PR URLs before writing anything. Bound work per run by page count, not by silently
   truncating the inventory, and continue the bootstrap on later ticks until complete.
   A `since:<duration>` cutoff may be an explicit operator escape hatch, but cannot be
   the default while the promised invariant is “every” issue/PR.
2. Persist a per-project, per-object-type high-water mark in the expanded chop's state
   directory: last successfully processed `updated_at` plus `provider_id` as a stable
   tie-breaker.
3. Each incremental run starts with an overlap window (for example ten minutes), pages
   to exhaustion, and deduplicates provider IDs. This tolerates equal timestamps,
   delayed search indexing, and a crash after a local write.
4. Advance the checkpoint only after every planned local mutation succeeds. A partial
   failure repeats safe idempotent work next time.
5. Run a slower full repair scan daily to catch missed updates, lost state, transfers,
   project renames, and provider anomalies.

The GitHub plugin may initially implement deltas with `gh issue/pr list --search` and
overlap, but its long-term API should own GraphQL pagination/cursors. Core must not know
GitHub search syntax.

## 4. Issue-to-bead reconciliation

### 4.1 Creation policy

For every remote issue returned by the provider:

1. Normalize identity to `(stable project key, issue number)` and its canonical
   `bug:<display-name>#<number>` representation.
2. Look for that identity in all bead refs and the legacy epic bug association.
3. If any bead already covers it, do nothing. Optionally backfill the canonical ref onto
   a legacy plan bead in an explicit migration.
4. Otherwise create a task bead with:
   - title initialized from the issue title;
   - description initialized from the issue body, with the provider URL clearly shown;
   - status `open`, never `ready`;
   - size `large` by default;
   - one `bug:` ref;
   - normal creation attribution indicating an automated sync actor, not a fictitious
     agent.

`large` is intentionally conservative. SASE's bead sizing guidance says to default to
large when the root cause and exact edit surface are not known. A later provider config
can map explicit labels such as `size:small` to smaller sizes, but title length, label
count, or issue author are not defensible sizing signals. Keeping imports `open` also
prevents an external issue from immediately triggering triage gates or agent launches.

The same invariant applies when ACE creates an external issue: try to create/link the
bead in that foreground transaction, then let the chop heal the state if the remote
write succeeded and the local write failed.

### 4.2 Synchronization policy

Do not make the bead a lossy mirror of GitHub:

- Never overwrite a bead title or description after creation. They become the local
  engineering interpretation and may intentionally diverge from the issue.
- Never auto-close or reopen a bead when the remote issue changes state. A closed issue
  can still require local follow-up, and a completed bead may be only one part of an
  open issue.
- Keep the association after remote deletion, loss of permission, or project disable.
  ACE should show `unavailable` rather than delete local work.
- Fetch/cache current remote metadata as a facet for display and filtering. Remote state,
  labels, title, author, timestamps, and comment count do not need to become bead fields.

The UI can flag useful drift such as `issue closed · bead open` and offer an explicit
close/reconcile command. It should not silently couple the two state machines.

### 4.3 Concurrency and duplicate prevention

One expanded chop does not eliminate races with manual runs, foreground issue creation,
or another machine. The mutation path must acquire the canonical bead-store lock, rebuild
the semantic bug-ref index while holding it, then append the create event only if the
identity is still uncovered. Do not implement this by shelling out once to list and once
to create without a shared lock window.

Cross-machine duplicates are still possible if machines reconcile independent stale
copies of a hosted beads sidecar. The existing bead-store publication/integration path
must be used rather than direct file edits, and integration should collapse simultaneous
imports by semantic bug identity. A duplicate repair operation can merge refs and close
the redundant draft, but prevention at the event/store boundary is preferable.

## 5. PR-to-Patch reconciliation

### 5.1 Add a provider-neutral PR listing wire

The provider layer has issue wires but no list-PR wire. Add a paginated
`PullRequestWire` (the codebase now deliberately uses PR terminology) containing at
least:

```text
provider_id, number, url, title, body, state, is_draft,
author, head_ref, base_ref, created_at, updated_at,
closed_at, merged_at
```

Expose listing/get capability separately from create/edit/close. GitHub normalizes these
fields in `sase-github`; later GitLab or Gerrit-like plugins may normalize their review
objects into the same SASE concept.

### 5.2 Reliable SASE-versus-external classification

Author, branch naming, commit provenance, and “there is already a PR URL” are inadequate
classifiers:

- SASE and a person commonly use the same GitHub account.
- A person can create a PR from a branch containing SASE-authored commits.
- `SASE_AGENT=` may appear in a commit-derived PR body even when `gh pr create --fill`
  was run manually.
- A local Patch may predate either kind of PR.

Make tracked SASE PR creation self-identifying. The workflow already reserves the final
suffixed Patch name before provider dispatch, so append this structured footer to the PR
body (and preferably its commit message) before creation:

```text
SASE_PATCH=sase_external_artifact_sync_1
```

The existing footer parser and Patch-description tag stripping already understand
uppercase `SASE_*=` metadata, so this is consistent with current provenance. The marker
survives a crash between remote creation and local Patch completion and lets the chop
repair the missing Patch as SASE-origin rather than falsely importing it as external.

Classification order must be deterministic:

1. **Canonical PR URL/provider ID already owned by a local Patch:** do not create
   another Patch. Preserve its explicit origin.
2. **Valid `SASE_PATCH` marker:** the PR is SASE-origin. If its named local Patch is only
   a reservation or missing because creation crashed, complete/repair that Patch with
   `PR_ORIGIN: sase`.
3. **No marker and no local Patch:** create a Patch with `PR_ORIGIN: external`.
4. **Ambiguous historical evidence:** do not guess. Existing SASE PRs predate the new
   marker, and `SASE_AGENT` alone is suggestive but not authoritative. Report these as
   `unknown` for user adoption/classification, or conservatively skip auto-import when
   the evidence suggests an old SASE workflow.

This cannot identify a SASE agent that bypasses the tracked workflow and invokes
`gh pr create` directly without a marker. That PR is externally indistinguishable. The
enforceable contract is therefore “created by SASE's tracked PR workflow,” and provider
calls from agents should continue to be routed through that workflow.

### 5.3 Imported Patch shape and status

An imported Patch should contain:

- a unique SASE Patch name derived from the project and sanitized PR title/head branch;
- description initialized from PR title/body after stripping structured footer tags;
- the canonical `PR:` URL;
- `PR_ORIGIN: external`;
- no fabricated parent, stitches, hooks, agents, or workspaces;
- optional refs already found in the PR body, if they pass normal validation.

Do not infer `PARENT` merely because the PR's base branch is another feature branch.
Only add a parent when provider metadata or an explicit SASE marker proves a Patch
dependency.

Initial status maps as follows:

| Remote PR state | Initial Patch status | Destination |
| --- | --- | --- |
| Open draft | `Draft` | active ProjectSpec |
| Open, ready for review | `Mailed` | active ProjectSpec |
| Merged | `Submitted` | archive ProjectSpec |
| Closed without merge | `Archived` | archive ProjectSpec |

`Ready` means locally ready to mail, so a non-draft remote PR has already passed that
point and belongs in `Mailed`. `Reverted` is incorrect for a merely closed PR.

The existing `add_patch_to_project_file()` always targets the active project file and
does not accept provenance. Do not create a terminal Patch in the active file and then
move it in a second non-atomic operation. Add an importer/domain mutation that locks the
active and archive stores, checks both for the PR identity/name, and writes directly to
the correct destination.

For ongoing state, external-origin Patches should follow remote PR state through the
same provider-status machinery used by SASE-created PRs. Draft-to-ready may require a
validated multi-step local transition (`Draft -> Ready -> Mailed`). Reopening a merged
or archived PR conflicts with SASE's terminal Patch states; phase one should surface
that as a reconciliation conflict with an explicit restore/adopt operation rather than
silently violating the state machine. This edge case should be designed before claiming
two-way lifecycle parity.

## 6. ACE information architecture

### 6.1 Merge Bugs into Beads

Current Artifacts sub-tabs are `Commits`, `Beads`, `Bugs`, `PRs`, and `Files`.
`ArtifactsBugsPane` is a remote-issue inventory, whereas `ArtifactsBeadsPane` is the
local work inventory. Once the chop enforces coverage, maintaining both views duplicates
navigation and invites divergent filters.

Remove the Bugs sub-tab and make Beads canonical. The list must contain only bead rows,
as requested. Enrich each row with zero or more compact issue facets:

```text
sase-ab12  Fix project alias resolution       🐞 #418 open
sase-cd34  Retire legacy provider hook         🐞 #391 closed
sase-ef56  Refactor local cache
```

The exact glyph is a presentation decision; the essential signals are issue number,
remote state, and provider availability. If a bead has multiple `bug:` refs, show a
count/bounded badge and a picker instead of silently choosing one.

The detail panel should add an **External issue** section containing current title,
state, labels, author, update time, comment count, URL, and provider error/staleness.
Move/reuse the existing issue operations here:

- open in browser;
- view full remote body/comments link;
- edit title/body/labels when supported;
- close/reopen when supported;
- copy URL or canonical `bug:` ref;
- attach an existing issue to an unlinked bead;
- create an external issue for an unlinked bead, then attach it;
- refresh remote metadata.

Generalize `action_beads_open_bug`, which currently only reads epic/phase legacy bug
metadata, to resolve task refs and show a chooser for multiple refs. Issue operations
must be capability-gated individually rather than hiding all issue context when a
provider is read-only.

Useful Beads filters are `bug`, `bug:none`, `bug:open`, `bug:closed`, and provider label
tokens. Remote metadata should be fetched in one bounded batch/cache refresh per project,
not by making a provider call while rendering each row. When the latest chop failed or
has not yet imported a discovered issue, a small sync-health banner may show counts and
last-run status, but remote-only issues must not become list rows.

### 6.2 Rename PRs to Patches and show provenance

The existing PRs pane is already a Patch surface (`ArtifactsPrsPane` wraps the existing
Patch view), so this is primarily a naming and metadata correction:

- Rename the visible sub-tab to **Patches**.
- Rename internal `prs` identifiers/classes to `patches`, keeping `prs` as a temporary
  compatibility alias for saved UI state, commands, and tests.
- Display a PR link/badge for every Patch with `PR:`.
- Separately display `external`, `sase`, or subdued `origin ?` from `PR_ORIGIN`.

Examples:

```text
sase_refactor_cache_1       Mailed      PR #812 · sase
sase_fix_windows_path_1     Mailed      PR #819 · external
sase_old_parser_2           Submitted   PR #601 · origin ?
sase_local_experiment_1     WIP         no PR
```

This presentation directly answers the important question. A PR badge means “this Patch
has a remote review”; the origin chip answers “who created that review?” They must never
be collapsed into one boolean.

External-Patch details can reuse standard provider operations (browser, refresh, checkout
where meaningful, and edit when supported) while making absent SASE stitches/workspace
state unsurprising. Add an explicit “mark PR origin” or “adopt” operation for historical
unknowns and ambiguous backfill results.

## 7. Failure behavior and observability

Each chop run should emit a structured report with at least:

```text
project, provider, pages_fetched, remote_seen, local_matched,
created, repaired, skipped_sase, ambiguous, conflicts, failures,
checkpoint_before, checkpoint_after, full_scan
```

Important failure rules:

- Authentication/rate-limit/provider outages create a failed or degraded run; they do
  not delete refs or local records.
- One malformed remote record is reported with provider ID/URL and should not advance
  the checkpoint past unprocessed data.
- Project disablement stops new runs but preserves checkpoint and imported records.
- Project display-name changes use the stable project key for identity; persisted refs
  should be migrated or resolved through project aliases so a rename cannot duplicate
  every issue.
- Canonically normalize PR URLs (host, owner/repo, number) before comparison; raw string
  equality is insufficient for enterprise hosts, URL variants, or renamed repositories.
- A dry run shows the exact creations/classifications without mutating stores or advancing
  cursors.

The Axe tab then gives operators per-project sync health and manual reruns for free.
ACE's Beads/Patches panes should display the last successful facet refresh and a stale
indicator rather than blocking local navigation on the network.

## 8. Alternatives considered

### One combined chop

Smaller configuration, but it couples unrelated stores, permissions, timeouts, retries,
and operator controls. A shared reconciliation package eliminates the meaningful code
duplication without forcing one scheduling unit. Reject.

### Keep the Bugs pane and merely cross-link it

This leaves two inventories for one work concept, remote-only rows remain actionable
outside the bead lifecycle, and users must mentally join them. It also makes the sync
invariant invisible. Reject after a short compatibility period.

### Add dedicated external-issue fields to task beads

This duplicates the existing artifact-ref grammar and forces every resolver, prompt,
filter, CLI, and TUI path to understand two associations. Use `bug:` refs and fix the
few current consumers that only inspect legacy epic metadata. Reject.

### Infer external Patches from `PR:` or author

Incorrect by construction: SASE-created Patches commonly have PRs, and creator identity
is usually the same GitHub account. Reject. Provenance must be explicit and stamped at
creation time.

### Use only webhooks

Lower latency but substantially more deployment and recovery machinery, and it still
needs backfill. Keep as a later trigger for the same reconciler, not the source of truth.

### Continuously mirror remote issue text into beads

This destroys local edits and conflates tracker state with engineering execution state.
Initialize once, then present remote data as a live/cached facet. Reject.

## 9. Suggested delivery sequence

1. **Contracts and indexes.** Add provider IDs and paginated issue/PR wires; capability
   granularity; canonical remote identities; the all-bead `bug:` index; `PR_ORIGIN` with
   absent=`unknown`; parser/writer/docs compatibility tests.
2. **Prospective SASE provenance.** Stamp `SASE_PATCH=<reserved-name>` during tracked PR
   creation and write `PR_ORIGIN: sase`. Test the crash window between provider success
   and local Patch completion.
3. **Reconciliation engine.** Implement the Rust action planner and locked Python bead /
   Patch mutation adapters. Cover duplicate refs, legacy epic links, active/archive
   Patch matching, terminal initial states, project aliases, and dry-run reports.
4. **GitHub plugin and Axe.** Implement delta/pagination hooks, two plugin-configured
   per-enabled-project chops, overlap checkpoints, bounded initial backfill, and daily
   repair.
5. **Beads UI consolidation.** Add remote facets/actions/filters to Beads, generalize bug
   ref actions, then remove the Bugs sub-tab and preserve a short command-state alias if
   needed.
6. **Patches UI/provenance.** Rename the PRs surface, render origin chips and PR actions,
   and add adoption/classification for historical `unknown` records.
7. **Hardening.** Exercise simultaneous manual/chop runs, multiple machines, provider
   downtime, pagination ties, repo/project rename, transferred issues, SASE orphan PRs,
   external PRs containing SASE-authored commits, closed/merged imports, and reopened
   terminal PRs.

## Recommended solution

Implement a provider-neutral **external-artifact reconciliation service** in SASE,
invoked by two GitHub-plugin-contributed Axe chops—`external_issue_sync` and
`external_pr_sync`—expanded across enabled GitHub projects.

Use the existing `bug:<project>#<number>` artifact ref as the only durable issue-to-bead
association. Create a conservative `open`, `large` task bead only when no existing bead,
including a legacy epic, already covers the issue. Treat remote issue data as a cached
facet and never automatically overwrite or close the local bead.

For PRs, add a provider-neutral paginated listing hook, add
`PR_ORIGIN: sase|external|unknown` to Patch storage, and stamp every future tracked SASE
PR with `SASE_PATCH=<reserved Patch name>`. Match existing Patches first, repair marked
SASE PRs second, import only unmarked/unowned PRs as `external`, and quarantine ambiguous
historical cases instead of guessing.

Finally, make ACE's local records the sole inventory: remove Bugs and show issue facets
and operations on Beads; rename PRs to Patches and show a PR badge independently from an
explicit origin chip. This is the smallest design that is idempotent, plugin-extensible,
honest about provenance, compatible with SASE's existing stores, and recoverable after
missed events or partial failures.
