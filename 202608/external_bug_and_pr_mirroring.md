---
create_time: 2026-08-10
updated_time: 2026-08-10
status: research
---

# Mirroring External Bugs Into Beads And External PRs Into Patches

**Research question:** what is the best way to (a) create a SASE bead for every external
bug filed against an enabled project, (b) create a Patch for every PR on an enabled
project that a SASE agent did not create, (c) merge the Artifacts tab's **Beads** and
**Bugs** sub-tabs into one bead-only surface that still makes bug association obvious
and operable, and (d) rename the **PRs** sub-tab to **Patches** while marking which
Patches were adopted from externally-created PRs.

**Scope:** the `sase` repo at master `5f6d8ea64` on 2026-08-10, the `sase-github` plugin
repo at its `origin/master`, and the `sase-core` Rust crate at its `origin/master`. All
file paths below are relative to the repo they name.

## Bottom line

Three of the four asks are mostly wiring on top of seams that already exist. The fourth
— the durable bug↔bead link — is the one real design decision, and the original
Artifacts epic already named the answer and deferred it.

1. **The issue-tracker provider seam already exists and is capability-gated.**
   `vcs_list_issues` / `get` / `create` / `update` / `get_issue_url` are declared on
   `VCSProvider` and `VCSHookSpec`, implemented in `sase-github` over the `gh` CLI, and
   probed structurally by `VCSPluginManager.supports_issues()` without touching the
   network. Nothing new is needed on the bug-read side.
2. **The PR side of that seam does not exist.** There is no `vcs_list_pull_requests`
   hook and no `PullRequestWire`. This is the one genuinely new provider surface, and it
   is a direct transcription of the issue seam that landed in `e5d299582`.
3. **A task bead cannot carry a bug id today, and forcing one to would break a real
   invariant.** `Issue.validate()` and the `sase-core` SQLite `CHECK` constraints both
   restrict `changespec_bug_id` to `plan`-type beads *and* require a companion
   `changespec_name`. The correct move is the `external_ref` field the epic plan
   `plans:202607/artifacts_tab.md` explicitly deferred: *"a dedicated `external_ref`
   bead field in the sase-core schema is the designed follow-up once bidirectional
   write-back is wanted."* That time is now.
4. **Two chops in the `checks` lane, not one, and not the fast lanes.** They write to
   two different stores with two different failure modes and two independent capability
   gates. `bead_task_triage` is the structural template for both.
5. **The largest operational hazard is not the sync — it is what the rest of AXE does to
   an adopted Patch.** A Patch for an external PR has no local branch, no workspace, and
   no stitches. `hook_checks`, `mentor_checks`, and `pr_submitted_checks` all scan
   Patches and start work on them. Adopted Patches must be explicitly excluded, or the
   first mirror pass will launch hook and mentor agents against PRs nobody asked us to
   touch.

## What already exists

### The issue seam (complete)

| Layer                | Location                                                  |
| -------------------- | --------------------------------------------------------- |
| Abstract methods     | `src/sase/vcs_provider/_base.py` (`list_issues` et al.)   |
| Pluggy hookspecs     | `src/sase/vcs_provider/_hookspec.py`                      |
| Wire record          | `src/sase/vcs_provider/_types.py` → `IssueWire`           |
| Capability probe     | `_plugin_manager.py::supports_issues`, `_registry.py`     |
| GitHub impl          | `sase-github/src/sase_github/plugin.py` (`gh issue …`)    |
| Network-free fake    | `src/sase/vcs_provider/testing.py`                        |

`supports_issues()` requires *all* issue hooks to be implemented, so a partial plugin
cannot claim capability. `bare_git` implements none, and the Bugs pane renders an
explanatory empty state for such projects.

### The cross-link helper (pure, already written)

`src/sase/bug_links.py` is a pure function: given a bug id, an iterable of beads, and an
iterable of Patches, it returns matching epic beads and Patches. `_normalize_bug_id()`
already folds `42`, `#42`, `owner/repo#42`, GitHub issue URLs, and the legacy
`http://b/42` spelling to one comparable key. It is I/O-free and cache-safe by design.

Its bead-side matcher is the constraint to notice:

```python
bead.issue_type == IssueType.PLAN
and bead.tier == BeadTier.EPIC
and _normalize_bug_id(bead.changespec_bug_id) == normalized
```

Only epic beads participate. Task beads are structurally excluded.

### The bug artifact-ref kind (already canonical)

`bug` is one of `BUILTIN_ARTIFACT_REF_KINDS` in `src/sase/artifact_ref_models.py`. The
rendered form is `bug:<project>#<number>` (`docs/getting_started.md`). `sase artifact
open` already opens a `bug:` ref in a browser (`docs/configuration.md`), and
`artifact_ref_entries.py` already renders the Bugs pane's entry target as a `bug:` ref.
Every bead already carries a normalized, deduplicated `refs` list that accepts it, and
the Beads pane already folds `issue.refs` into its search haystack
(`beads_filtering.py`).

### The Patch record

`Patch` (`src/sase/ace/patch/models/patch.py`) carries `bug`, `pr_url`, `status`,
`stitches`, `hooks`, `refs`. The ProjectSpec field order is fixed in
`src/sase/ace/patch/section_order.py`:
`NAME · DESCRIPTION · PARENT · <review urls> · BUG · STATUS · REFS · STITCHES · DELTAS ·
HOOKS · COMMENTS · MENTORS · TIMESTAMPS`. Status lifecycle and legal transitions live in
`src/sase/status_state_machine/constants.py`; `ARCHIVE_STATUSES` (`Submitted`,
`Archived`, `Reverted`) decide which of the two ProjectSpec files a Patch lives in.
`iter_patch_project_file_records()` already walks both files for lifecycle-selected
projects, so "every PR URL SASE already knows about" is a cheap local scan.

### The chop/lumberjack architecture

`src/sase/default_config.yml` defines five lanes: `hooks` (5s), `waits` (10s), `checks`
(300s), `comments` (60s), `housekeeping` (3600s). The `checks` lane's own description
says it is *"for checks that can tolerate delay or may touch remote PR state, reducing
needless polling."* Per-chop `run_every` and `timeout` overrides exist
(`bead_store_refresh` uses `run_every: "30s"`, `timeout: "2m"`).

`src/sase/scripts/sase_chop_bead_task_triage.py` is the reference implementation for a
project-fanning, store-writing chop: `_enabled_project_stores()` filters
`list_project_records(..., "enabled")` down to real, non-system projects with a
canonical bead store; `file_lock()` guards one JSON lane-state document; every
per-project failure is logged and skipped rather than aborting the pass; and the summary
carries structured counters.

### The Artifacts tab

`src/sase/ace/tui/artifact_tabs.py` is the single source of truth:

```python
ArtifactsSubTab = Literal["prs", "commits", "bugs", "beads", "files"]
ARTIFACTS_SUBTAB_ORDER = ("commits", "beads", "bugs", "prs", "files")
ARTIFACTS_ACCENTS = {"prs": "#00D7AF", "bugs": "#FF5F5F", "beads": "#D787FF", ...}
```

Sub-tab number keys are generated from `ARTIFACTS_SUBTAB_ORDER` in `bindings.py:110`, so
changing the tuple renumbers the keys automatically — and silently. The Bugs pane is
~600 lines (`widgets/artifacts/bugs.py`) plus a 459-line action mixin
(`actions/artifact_bugs.py`) plus `artifacts_bugs.py` (off-thread data) and
`bugs_rendering.py`.

## The four problems

### P1 — a bead per external bug

The blocking issue is where the link lives.

**Option A — reuse `changespec_bug_id`.** Requires relaxing two `CHECK` constraints in
`sase-core/crates/sase_core/src/bead/schema.rs` (plan-only, and
`changespec_name != '' OR changespec_bug_id = ''`) plus the mirrored assertions in
`Issue.validate()`. Those constraints encode a genuine invariant — Patch metadata
belongs to plan beads — and weakening it to make room for an unrelated concept is the
wrong trade. **Reject.**

**Option B — store `bug:<project>#<n>` in `Issue.refs`.** Zero schema change. Already
normalized, deduplicated, searchable, browser-openable, and writable from
`sase bead ref add`. But `refs` is a deliberate grab-bag: there is no uniqueness
constraint, no index, and no way to distinguish *"the bug this bead mirrors"* from *"a
bug this bead merely cites."* An idempotent mirror would need a full-store scan plus a
first-match convention, and a human adding a second `bug:` ref would silently create
ambiguity. **Reject as the identity; keep as the supporting reference.**

**Option C — a machine-local index file** mapping bug → bead, in chop lane state.
Rejected outright: bead stores are git-synced sidecars shared across machines, and lane
state is machine-local and disposable. The link would evaporate on the second host.

**Option D — a dedicated `external_ref` field in the `sase-core` bead schema.** One
nullable TEXT column holding a canonical artifact reference, valid on any bead type,
with a partial-unique index per store. Gives idempotent upsert keyed on the field, an
unambiguous mirror relation, a clean filter (`bug:`, and a redefined `has:bug`), and
survives cross-machine sync because it lives in the bead itself. Costs a schema
migration across ~12 Rust files (`schema.rs`, `wire.rs`, `jsonl.rs`, `events.rs`,
`read.rs`, `mutation.rs`, `cli.rs`, `history.rs`, `search.rs`, `work.rs` plus parity
fixtures) and the Python mirrors (`bead/model.py`, `_db_schema.py`, `_db_migrations.py`,
`_db_codec.py`, `_project_mutations.py`, `cli_crud.py`, `cli_query.py`). **Recommended.**
The migration has direct precedent: `schema.rs` already ships
`needs_refs_migration()` / `refs_migration_sql()` for exactly this shape of additive
column.

**Which bead type?** `task`. The semantics line up exactly — a standalone unit of
discovered work awaiting the owner's triage — and the existing `ready` → `TaskTriage`
gate loop (`bead_task_triage` chop → gate → *Launch* or *Close with reason*) is
precisely the "propose it to the project owner" step the user already runs for every
other kind of discovered work. Epics are wrong: they come from approved plans and carry
phase children.

**Which status on creation?** `open` (draft), not `ready`. Two reasons. First, the
project's own contract is that every new task requires an *intentional* `--size`, and a
chop cannot choose one honestly; `open` leaves sizing to the human. Second, creating
`ready` beads would raise a `TaskTriage` gate per incoming issue, flooding the
notification inbox on the first pass. An `open` mirrored bead is visible in the Beads
pane, costs nothing, and promotes to `ready` the moment a human sizes it.

**What about upstream state changes?** Do not auto-close beads when the GitHub issue
closes. Closing is a deliberate act that records a resolution, never cascades, and is
explicitly not something to hand-drive. Instead: render the bug's live state as a chip,
and have the mirror append an attributed `sase bead note` (append-only, safe, already
the sanctioned mechanism for supplementary evidence) when the upstream state flips.

### P2 — a Patch per external PR

**Detecting "external."** Do not infer it. The user's own constraint is decisive: SASE
agents *do* create PRs and attach them to Patches, so the presence of a `PR:` field
proves nothing. The reliable local signal is set difference — collect every `pr_url`
across both ProjectSpec files for the project (`iter_patch_project_file_records`), list
the remote PRs, and adopt the ones SASE has never recorded. But once adopted, the origin
must be *stored*, not recomputed, so add an explicit `ORIGIN:` field to the ProjectSpec
Patch record (absent ⇒ `sase`; `external` ⇒ adopted). Author-based heuristics (matching
the PR author against the machine's git identity) are wrong here — the user authors PRs
by hand too, and those are exactly the ones to adopt.

**Status mapping.** Draft PR → `Draft`; open PR → `Mailed`; merged → `Submitted`;
closed-unmerged → `Archived`. Two traps: `VALID_TRANSITIONS` only admits
`Mailed → Submitted`, so an already-merged PR must be written directly into the archive
file rather than transitioned into it; and `ARCHIVE_STATUSES` determines file placement,
so the mirror must pick the destination file, not just the status string.

**The hazard.** `hook_checks`, `mentor_checks`, `workflow_checks`, and
`pr_submitted_checks` all scan Patches and start real work — hooks, mentor agents,
submission probes — against them. An adopted Patch has no local branch, no workspace
claim, and no stitches. Creating it must skip `get_initial_hooks_for_patch()`, and every
Patch-scanning chop must skip `ORIGIN: external` records (or, more narrowly, records
with no stitches and no workspace). This needs to land *with* the mirror chop, not
after it.

### P3 — merging Beads and Bugs

The merge is sound only if the bead list is a *superset* of the bug list within scope.
Any bug excluded from mirroring (by watermark, label filter, or budget) becomes
invisible when the Bugs pane disappears. Either mirror everything in scope and state
that scope explicitly, or keep a status-line count of unmirrored bugs. The first is
cleaner.

Mechanically: drop `"bugs"` from `ArtifactsSubTab`, `ARTIFACTS_SUBTAB_ORDER`,
`ARTIFACTS_PANE_IDS`, and `_ARTIFACT_LABELS`; retain `#FF5F5F` in `ARTIFACTS_ACCENTS`
re-keyed as the *bug chip* accent so the visual vocabulary survives the merge. Number
keys shift from 5 sub-tabs to 4 automatically via `bindings.py:110` — keep
`show_artifacts_bugs` as a deprecated alias routing to Beads so existing config does not
break.

Key collisions are real: both panes bind `j k f o y a s R e`. With the Bugs pane gone,
`o` (open bug in browser) and `y` (copy bug ref) can move to the Beads pane gated on
"selected bead has a bug link" — which is exactly the footer convention in
`src/sase/ace/CLAUDE.md` (*a keymap appears in the footer iff its condition is sometimes
true and sometimes false*). `e` and `s` genuinely conflict with bead edit and bead status
cycle, so bug-mutating actions want a `b`-prefixed pair (`be` edit bug, `bs`
close/reopen bug) rather than stealing the bead primaries.

Filters: `has:bug` already exists in `BEAD_HAS_VALUES` and is currently computed from
`issue.patch_bug_id` (`beads_filtering.py:186`) — redefine it to mean "has an external
bug link" and add a `bug:` key for value filtering.

### P4 — PRs → Patches

A rename touching `ArtifactsSubTab`, `ARTIFACTS_PANE_IDS`, `_ARTIFACT_LABELS`,
`ARTIFACTS_ACCENTS`, `ArtifactsPrsPane`, the `entry_navigator` guard that currently
reads *"PRs use the existing Patch navigation model"*, action names
(`show_artifacts_prs`), `commands/types.py`, `tab_quickstart.py` copy, and
`modals/help_modal/patches_artifact_bindings.py`. The repo's established practice is to
keep legacy aliases (`ChangeSpec = Patch`, `changespec_bug_id`, `find_all_changespecs`),
so the same treatment applies here.

The external chip is driven by the new `ORIGIN:` field. Per `src/sase/ace/CLAUDE.md`, a
new Patch field spelling must be updated in **all** of: the chezmoi
`saseproject.vim` syntax file, `src/sase/ace/display.py`,
`src/sase/ace/query/highlighting.py`, and
`src/sase/ace/tui/widgets/patch_detail.py`. Add an `origin:` property to the ACE query
language (`query/searchable.py`, `query/matchers.py`) so `origin:external` selects them.

## Risks and gotchas

1. **Bead-store write contention.** The mirror becomes a *writer* on a store that live
   agents also write, and every bead mutation commits to the sidecar. Follow
   `bead_store_refresh`'s documented pattern: bounded per-project lock waits, a
   whole-pass work budget, and persistent exponential backoff. This is the single
   biggest operational risk in the whole design.
2. **First-run flood.** A project with hundreds of open issues would mint hundreds of
   beads on pass one. Needs a durable per-project watermark (stored in the ProjectSpec,
   not lane state, so it survives across machines) plus a per-pass creation budget — the
   `managed_tmp_reap` "at most 2,000 entries per pass" convention.
3. **`gh` auth in the detached lumberjack.** The Bugs pane proves `gh` works from the
   interactive TUI; the axe daemon runs detached with a different environment. Wants a
   `src/sase/doctor/` check.
4. **Rate limits and latency.** Two `gh` invocations per enabled project per pass.
   `run_every: "10m"` inside the 300s `checks` lane keeps this modest.
5. **Deleted or transferred issues.** Never delete a bead. Mark the link stale and note
   it.
6. **Symvision.** Dismantling the Bugs pane will orphan symbols; see
   `sase/memory/symvision.md` before the lint gate fails.
7. **Visual snapshots.** The Artifacts panes have PNG goldens
   (`tests/ace/tui/visual/snapshots/png/`); the merge and rename both require
   `just test-visual --sase-update-visual-snapshots`.
8. **Noise.** A tracker holds feature requests and questions, not only bugs. A label
   include/exclude filter is the escape hatch.

## Recommended solution

A six-phase epic. Phases 1–2 are independent and can run in parallel; 3 depends on 1; 4
depends on 2; 5 depends on 3; 6 depends on 4.

**Phase 1 — `external_ref` bead field.** Add a nullable canonical-artifact-ref column to
the `sase-core` bead schema with an additive migration modeled on
`needs_refs_migration()`, thread it through wire/jsonl/events/read/mutation/cli/history/
search, mirror it in `sase/bead/model.py` and the Python DB layer, expose
`sase bead create --external-ref` / `sase bead update`, and redefine `has:bug` plus a new
`bug:` filter key over it. Extend `bug_links.py` to match on the new field in addition to
epic `changespec_bug_id`, so both link kinds resolve through one helper.

**Phase 2 — PR provider seam.** Add `PullRequestWire` to `vcs_provider/_types.py`;
`vcs_list_pull_requests(cwd, state, limit)` to `_base.py` and `_hookspec.py`;
`supports_pull_requests()` to `_plugin_manager.py` and `_registry.py` following the
all-hooks-required probe; implement it in `sase-github` over `gh pr list --json`; and
extend the in-memory fake in `vcs_provider/testing.py`. This is a transcription of
`e5d299582`.

**Phase 3 — `external_bug_mirror` chop.** New builtin in
`src/sase/scripts/`, registered in `pyproject.toml` and the `checks` lane with
`run_every: "10m"`, `timeout: "2m"`. Structure it on `bead_task_triage`: fan over
enabled projects, gate on `supports_issues()`, diff `list_issues(state="all")` against
beads keyed by `external_ref`, create missing beads as `open` tasks with the bug's title
and body plus a `bug:<project>#<n>` entry in `refs`, and append an attributed note when
an upstream state flips. Watermark + per-pass budget + backoff as above.

**Phase 4 — `ORIGIN:` field and `external_pr_mirror` chop.** Add `ORIGIN:` to
`section_order.py` / `parser.py` / `storage.py` and the four styling surfaces the ACE
`CLAUDE.md` enumerates. Add the second chop: gate on `supports_pull_requests()`, diff
remote PRs against every `pr_url` in both ProjectSpec files, and adopt the remainder via
`add_patch_to_project_file()` with `ORIGIN: external`, no initial hooks, and the mapped
status/file. **In the same phase**, exclude `ORIGIN: external` Patches from
`hook_checks`, `mentor_checks`, `workflow_checks`, and `pr_submitted_checks`.

**Phase 5 — merge Bugs into Beads.** Retire the `bugs` sub-tab; add a bug chip to bead
rows and a Bug section to the bead detail panel (state, labels, assignees, body, plus
reverse links from `find_bug_links`); migrate the Bugs pane's actions onto the Beads
pane, context-gated on bug presence, with `o`/`y` direct and mutations behind a `b`
prefix; keep `show_artifacts_bugs` as a deprecated alias.

**Phase 6 — PRs → Patches.** Rename the sub-tab and its identifiers with legacy aliases,
render the external-origin chip in the patch list and info panel, and add an `origin:`
ACE query property.

## Open questions for the project owner

1. **Scope of "bug."** Mirror every tracker issue, or only issues carrying a configured
   label set? The former is simpler and makes the Beads pane a faithful superset; the
   latter is quieter.
2. **Watermark default.** Mirror only issues/PRs created after the project opts in
   (recommended), or backfill the entire open backlog on first run?
3. **Closed upstream bugs.** Note-only (recommended), or should a `done`-resolved
   upstream close also propose closing the bead through a gate?
4. **PR adoption breadth.** All PRs on the repo, or only those authored by the machine's
   own GitHub identity? "All" catches third-party contributions; "own" keeps the Patch
   list to work the owner is personally responsible for.
