---
create_time: 2026-08-10
updated_time: 2026-08-10
status: research
---

# Ingesting External Issues as Beads and External PRs as Patches

**Research question.** How should SASE continuously ensure that every issue in an
external tracker has a corresponding bead, and every PR not created by SASE has a
corresponding Patch, for every enabled project on a machine? How should ACE then present
those relationships without keeping separate Bugs and PR-centric inventories?

**Scope.** `sase` at `c8e4016c7`, the `sase-github` plugin, and the `sase-core` bead
schema, read 2026-08-10. GitHub is the concrete provider; the ownership boundaries are
provider-neutral. "External PR" means a PR whose creation did not go through SASE's
tracked PR workflow.

**Provenance.** This consolidates two independent reports —
[`__a`](external_artifact_ingestion__a.md) (codex) and
[`__b`](external_artifact_ingestion__b.md) (claude) — plus a verification pass that
resolved their four disagreements and turned up three hazards neither found. Claims below
marked **[verified]** were re-checked against the code during consolidation.

---

## Bottom line

Most of this is wiring onto seams that already exist. There are four real decisions, and
the two source reports split on all four. Recommended resolutions:

| # | Decision | `__a` | `__b` | Recommended |
|---|---|---|---|---|
| D1 | Where the bug↔bead link lives | `bug:` ref in `refs` | new `external_ref` core column | **Both** — `external_ref` is identity, `bug:` ref is resolution |
| D2 | PR provenance | `PR_ORIGIN: sase\|external\|unknown` + `SASE_PATCH=` stamp | `ORIGIN: external`, absent ⇒ `sase` | **`__a`** — tri-state, absent ⇒ `unknown` |
| D3 | Chop placement | plugin-contributed, `for_each` fan-out | core builtin, manual project loop | **Split** — core builtin script, `for_each` fan-out |
| D4 | UI merge | badges, filters, capability gating | subtab mechanics, key collisions | **Merge** — they are complementary, not rival |

The single most important sequencing constraint: **the Bugs sub-tab cannot be removed
until the mirror is verified complete**, because the merge is only honest if the bead list
is a superset of the bug list.

---

## 1. What already exists

**[verified]** The issue provider seam is complete. Five hooks — `vcs_list_issues`,
`vcs_get_issue`, `vcs_create_issue`, `vcs_update_issue`, `vcs_get_issue_url` — are
declared in `src/sase/vcs_provider/_hookspec.py:198-229`, implemented in `sase-github`
over the `gh` CLI, and probed structurally by `supports_issues()`
(`_plugin_manager.py:327`) without touching the network. A network-free fake exists in
`vcs_provider/testing.py`.

**[verified]** There is **no** PR-listing hook and no `PullRequestWire`. A repo-wide grep
for `vcs_list_pull_requests|list_pull_requests|PullRequestWire` returns nothing. This is
the only genuinely new provider surface required, and it is a direct transcription of the
issue seam.

**[verified]** `bug` is a canonical artifact-ref kind (`BUILTIN_ARTIFACT_REF_KINDS` in
`artifact_ref_models.py:14`), rendered `bug:<project>#<number>`, already browser-openable
via `sase artifact open`. Every bead carries a normalized, deduplicated `refs` list
(`bead/model.py:69`), and the Beads pane already folds `issue.refs` into its search
haystack.

**[verified]** `src/sase/bug_links.py` is a pure I/O-free cross-linker, but its bead-side
matcher requires `issue_type == PLAN and tier == EPIC`. Task beads are structurally
excluded today.

**[verified]** Axe fan-out is real and does exactly what is needed.
`for_each: {source: projects, vcs: [git, gh]}` expands one stable instance per enabled
project (`docs/configuration.md:2072-2080`, `axe/_config_targets.py:176-190`), each with
independent scheduling, history, checkpoints, and once-per state, keyed
`chop_name[project]`. Disabling a project stops its instance automatically.

**[verified]** Five lumberjack lanes exist in `default_config.yml`: `hooks` (5s), `waits`
(10s), `checks` (300s), `comments` (60s), `housekeeping` (3600s). The `checks` lane's own
description says it is "for checks that can tolerate delay or may touch remote PR state."
Per-chop `run_every`/`timeout` overrides are supported.
`src/sase/scripts/sase_chop_bead_task_triage.py` is the reference implementation of a
project-fanning, store-writing chop.

**[verified]** Artifacts sub-tabs are defined in one place
(`src/sase/ace/tui/artifact_tabs.py`): `ArtifactsSubTab`, `ARTIFACTS_SUBTAB_ORDER =
("commits","beads","bugs","prs","files")`, `ARTIFACTS_PANE_IDS`, `ARTIFACTS_ACCENTS`.

**[verified]** Patch status machinery: `ARCHIVE_STATUSES = {Submitted, Archived,
Reverted}` selects which ProjectSpec file a Patch lives in, and `VALID_TRANSITIONS`
admits only `Mailed → Submitted` (`status_state_machine/constants.py:44-60`). Field order
is fixed in `ace/patch/section_order.py`, which already carries a `BUG:` field.

---

## 2. Three hazards neither report found

### 2.1 `_normalize_bug_id` collapses project identity — cross-project collision

**[verified by execution]** `bug_links._normalize_bug_id` strips every project/repo
qualifier:

```text
'bug:sase#42'                                       -> '42'
'bug:sase-github#42'                                -> '42'
'https://github.com/sase-org/sase/issues/42'        -> '42'
'https://github.com/sase-org/sase-github/issues/42' -> '42'
```

Issue #42 in `sase` and issue #42 in `sase-github` are **indistinguishable** after
normalization. This is not theoretical: the machine has `sase`, `sase-github`,
`sase-telegram`, and `sase-nvim` as related repos, and the entire premise of the request
is "all enabled projects on the machine."

Consequences, both of which are easy to walk into:

- The mirror's idempotency key must be `(stable project key, issue number)`. It must
  **not** route through `_normalize_bug_id`.
- `__b`'s Phase 1 step "extend `bug_links.py` to match on the new field" inherits the
  collision if implemented naively. `find_bug_links` is safe today only because callers
  pass a project-scoped bead list — an accident of the call site, not a property of the
  helper. Any cross-project caller silently mismatches.

Fix: add a project-qualified normalizer alongside the existing one, and keep
`_normalize_bug_id` for the legacy within-project `BUG:` tag comparisons it was built
for. Do not widen the old function.

### 2.2 Six patch-scanning chops, one choke point — and the query filter is not a safety net

`__b` correctly identified the biggest operational hazard: an adopted Patch has no
branch, no workspace, and no stitches, but Axe chops scan Patches and start real work
against them. The detail is better than `__b` reported in one way and worse in another.

**Better:** there are not four scattered scan sites but **one choke point**.
**[verified]** `runtime.filtered_patches` is consumed by six chops — `hook_checks`,
`mentor_checks`, `workflow_checks`, `pending_checks_poll`, `comment_zombie_checks`, and
`suffix_transforms` — and is computed in a single place, `axe/chop_runner_context.py:49`:

```python
filtered_patches = all_patches
if axe_config.query:
    mask = evaluate_query_many_fn(axe_config.query, all_patches)
    filtered_patches = [cs for cs, keep in zip(all_patches, mask, strict=True) if keep]
```

One structural exclusion there covers all six. (`pr_submitted_checks` is the exception —
**[verified]** it calls `check_cycle_runner.run_full_check_cycle()` and does not take
`filtered_patches`, so it needs its own guard. `__b` listed it with the others; it is a
separate code path.)

**Worse:** the obvious-looking fix — express the exclusion as `-origin:external` in the
Axe query config — is unsafe as the *sole* mechanism. `axe_config.query` is
user-supplied and overridable at runtime (`sase axe start --query '!!! OR @@@'`,
`docs/axe.md:96,348`). Any user who sets their own query silently loses the exclusion and
the next tick launches mentor agents against third-party PRs.

Recommendation: exclude `PR_ORIGIN: external` **structurally** in
`build_oneshot_context` and the Lumberjack tick equivalent, before the user query is
applied. Ship the `origin:` query property too, but for UI filtering and manual opt-in
("show me external Patches"), never as the safety mechanism.

### 2.3 The PR marker cannot live where the agent footer lives

`__a`'s `SASE_PATCH=<name>` stamp is sound and the mechanism is confirmed feasible.
**[verified]** in `workflows/commit/workflow.py` the ordering is exactly right: the
suffixed name is reserved at `:166` (`self._reserved_name = suffixed`), the PR payload is
decorated at `:189-193` (`append_pr_tags` → `apply_runtime_commit_tags` →
`build_pr_body`), a checkpoint carrying `reserved_name` is saved at `:212`, and only then
does `dispatch()` create the PR at `:227`. The name is known before the body is built.

But **[verified]** `build_pr_body()` (`pr_operations.py:112-116`) early-returns when
`SASE_ARTIFACTS_DIR` is unset — i.e. the `**Model:**` / `**Agent:**` footer is written
*only* for agent-driven commits. A human running `sase commit pr` interactively produces
a fully SASE-tracked PR with no agent footer at all.

So the marker must be written in the always-run tag path (`append_pr_tags`), not in
`build_pr_body`. Note `append_pr_tags` itself early-returns `if not tags`
(`pr_operations.py:97`), so it needs an unconditional path for this key. And confirm in
`sase-github` that `payload["message"]` tags actually reach the PR *body* — the listing
API reads the body, not the commit message.

This also settles a related question: **`SASE_AGENT=` is not a usable provenance
signal.** It is absent for human-run tracked PRs and, as `__a` noted, can appear in a
manually created PR via `gh pr create --fill`. It is evidence in neither direction.

---

## 3. D1 — where the bug↔bead link lives

`__a` recommends reusing the `bug:` artifact ref. `__b` recommends a new `external_ref`
column in the sase-core bead schema. **`__b` is right about identity; `__a` is right
about resolution. Do both.**

**[verified]** `__b`'s blocking constraint is real. `bead/_db_schema.py:57-61` carries:

```sql
CHECK(issue_type = 'plan' OR (changespec_name = '' AND changespec_bug_id = '')),
CHECK(changespec_name != '' OR changespec_bug_id = '')
```

mirrored in `cli_crud.py:113-121` ("Patch metadata can only be attached to plan beads",
"`--bug-id` requires `--patch`"). A task bead cannot carry a bug id today, and relaxing
these to make room for an unrelated concept weakens a genuine invariant. Reject.

**[verified]** `__b`'s citation of the original epic plan is accurate, and stronger than
`__b` presented it. `plans:202607/artifacts_tab.md:296` calls a dedicated `external_ref`
bead field "the designed follow-up once bidirectional write-back is wanted," and
`:391-393` lists it under **Non-goals** — "the MVP rides the existing
`changespec_bug_id`/`BUG:` thread. Adding the dedicated field (Rust schema + wire + JSONL
+ `sase bead update` flag) is the designed next step once write-back association is
needed." The project's own architecture already anticipated this exact request.

The decisive argument is **idempotency**, and it is what tips D1 against `__a`. The mirror
runs every N minutes forever. `refs` is a deliberate grab-bag: no uniqueness constraint,
no index, and no way to distinguish "the bug this bead *mirrors*" from "a bug this bead
merely *cites*". Under `__a`'s design a human who adds a second `bug:` ref to a mirrored
bead silently changes what the mirror considers that bead's identity, and the next pass
mints a duplicate. A partial-unique index on `external_ref` turns "do not create a
duplicate" from a convention that erodes into a database invariant that cannot.

`__a`'s objection — that a new field forces every resolver, prompt, filter, CLI, and TUI
path to understand two associations — is answered by writing both and giving each one
job:

- **`external_ref`** (new, nullable, partial-unique per store): the mirror's idempotency
  key and the unambiguous "this bead mirrors that issue" relation. Value is the
  **project-qualified** canonical form `bug:<project-key>#<number>` (see §2.1).
- **`bug:<project>#<n>` in `refs`** (existing): what makes the link resolvable,
  searchable, and openable by all the machinery that already exists. Nothing new has to
  learn about it.

Cost is real and should be planned for: **[verified]** the additive-column precedent is
`schema.rs`'s `needs_refs_migration()`/`refs_migration_sql()` pair, and the Python
mirrors are `bead/model.py`, `_db_schema.py`, `_db_migrations.py` (see the
`changespec_bug_id` `ALTER TABLE` at `_db_migrations.py:45-47` for the exact shape),
`_db_codec.py`, `_project_mutations.py`, `cli_crud.py`, `cli_query.py`. Per the Rust core
backend boundary rule in `CLAUDE.md`, bead identity is squarely core-side, so this is the
boundary-correct home regardless of cost.

**Bead type and status.** Both reports agree, and both are right: **`task`**, created
**`open`**, never `ready`. A `ready` bead raises a `TaskTriage` gate per incoming issue
and floods the inbox on pass one.

**Size: leave unset.** `__a` recommends defaulting to `large`; `__b` leaves it to the
human. `__b` is right, and the schema permits it — **[verified]** `size` is nullable
(`_db_schema.py:37-42`) and `ready` status requires only `issue_type = 'task'`, not a
size. A chop cannot honestly estimate, and `large` injects a fabricated number that looks
like a judgment. NULL size makes "needs triage" mechanically visible (`size:none`) and
naturally gates promotion to `ready` on a human setting one.

**Upstream state changes.** Both reports agree: never auto-close a bead when the issue
closes. `__b`'s mechanism is the concrete one — append an attributed `sase bead note`
(append-only, already sanctioned for supplementary evidence) when upstream state flips,
and render live state as a chip. Add `__a`'s drift surfacing on top: show `issue closed ·
bead open` and offer an explicit reconcile command. Never silently couple the two state
machines. Never delete a bead for a deleted or transferred issue; mark the link stale.

---

## 4. D2 — PR provenance

Both reports agree on the premise, and it is the user's own: SASE agents create PRs too,
so the presence of a `PR:` field proves nothing. Provenance must be **stored, not
inferred**. They split on the field's shape.

**Adopt `__a`'s tri-state `PR_ORIGIN: sase | external | unknown`, absent ⇒ `unknown`.**

`__b`'s `ORIGIN:` with absent ⇒ `sase` is wrong in a way that is permanent. Every Patch
in existence today has no such field. Under absent⇒`sase`, the first mirror pass asserts
SASE provenance for the entire history without evidence — mostly true, but any PR the
user hand-created and then tracked with `sase commit` is mislabeled forever with no way
to detect it. `unknown` is honest, and it gives the backfill an explicit worklist and an
"adopt / mark origin" operation to clear it deliberately.

The name `PR_ORIGIN` over `ORIGIN` is also right: once agents start working adopted
Patches, "the origin of the Patch" is ambiguous, while "the origin of the PR
association" stays precise.

**Classification is two mechanisms, not one.** The reports each supply half:

- **Backfill / bootstrap (`__b`):** set difference. Collect every `pr_url` across both
  ProjectSpec files via `iter_patch_project_file_records()`, list remote PRs, adopt the
  remainder. This works today with no marker and is the classifier of record for
  everything that predates the marker.
- **Forward (`__a`):** stamp `SASE_PATCH=<reserved-name>` at creation. This closes the
  crash window between remote PR creation and local Patch completion — without it, a
  crash mid-workflow leaves an orphan PR that the next mirror pass falsely imports as
  external. See §2.3 for where the stamp must actually live.

Deterministic classification order:

1. Canonical PR URL already owned by a local Patch → do not create another; preserve its
   existing origin.
2. Valid `SASE_PATCH` marker → SASE-origin; if the named Patch is a bare reservation or
   missing, repair it with `PR_ORIGIN: sase`.
3. No marker, no local Patch → create with `PR_ORIGIN: external`.
4. Ambiguous historical evidence → `unknown`; do not guess.

Canonically normalize PR URLs (host, owner/repo, number) before comparison. Raw string
equality breaks on enterprise hosts, URL variants, and renamed repos.

**Limit worth stating plainly:** this cannot identify an agent that bypasses the tracked
workflow and calls `gh pr create` directly. The enforceable contract is "created by
SASE's tracked PR workflow," not "created by a SASE agent."

**Status mapping.** Both reports agree; `__a`'s reasoning for `Mailed` is the correct one
(`Ready` means *locally* ready to mail, which a live remote PR has already passed):

| Remote PR state | Patch status | ProjectSpec file |
|---|---|---|
| Open draft | `Draft` | active |
| Open, ready for review | `Mailed` | active |
| Merged | `Submitted` | archive |
| Closed unmerged | `Archived` | archive |

**[verified]** Two traps, both real. `VALID_TRANSITIONS` admits only `Mailed → Submitted`,
so a merged PR must be *written directly* into the archive file, never transitioned into
it. And `add_patch_to_project_file()` resolves its destination through
`get_project_file_path(project)` (`workflows/utils.py:11-22`), which returns the **active**
spec only — it accepts `status` but cannot target the archive. `__b`'s plan to reuse it
for adopted Patches is therefore incorrect for merged/closed PRs; `__a` is right that a
new importer is needed. That importer must lock both files, check both for the PR
identity and the name, and write to the correct destination in one operation.

Adopted Patches get: a unique name derived from the PR title/head branch; description
from the PR title/body with footer tags stripped; `PR:`; `PR_ORIGIN: external`; **no**
`initial_hooks`; and no fabricated parent, stitches, or workspace. Do not infer `PARENT`
from the PR's base branch — only from explicit provider metadata or a SASE marker.

---

## 5. D3 — where the chops live and how they fan out

`__a` proposes plugin-contributed chops using `for_each`. `__b` proposes core builtins in
the `checks` lane with a manual project loop. **Take `__a`'s fan-out and `__b`'s code
location.**

**Fan-out: `for_each: {source: projects}` — `__a` is right.** **[verified]** it exists and
gives, for free, exactly what a manual loop has to hand-roll badly: per-project
scheduling, independent checkpoints and once-per state, per-project failure isolation,
and automatic teardown when a project is disabled. `__b`'s single-instance loop over
`_enabled_project_stores()` couples every project into one pass — one project's rate limit
or auth failure stalls the rest — and gives one shared state file where per-project
watermarks belong.

Use `for_each: {source: projects}` with a **runtime `supports_issues()` /
`supports_pull_requests()` gate** as the authoritative filter. `vcs: [gh]` is a filter on
VCS *kind*, not on issue *capability*; it is fine as a cheap pre-filter but must not be
the only gate.

**Code location: core builtins — `__b` is right.** The chop scripts belong in
`src/sase/scripts/` and the plugin supplies only provider hooks. Reconciliation semantics
— what a bead is, what a Patch is, idempotency, status mapping — are core domain logic. A
future GitLab plugin must not have to reimplement them. `__a` actually concedes this
("the reconciliation library itself should remain in SASE"); it is only the chop
*registration* it places in the plugin, which splits the logic across a repo boundary for
no gain. Per the Rust core backend boundary rule, the deterministic classifier (remote
snapshot → `CreateBead` / `CreatePatch` / `Noop` / `Conflict` action plan, no I/O) is a
`sase-core` candidate; provider calls and filesystem orchestration stay in Python.

**Two chops, not one** — both reports agree, and the reasoning is sound: two stores, two
failure modes, two capability gates, two backfill costs. A shared library handles cursor
I/O, overlap windows, URL normalization, and structured reports.

**Lane and cadence:** `checks` lane, `run_every: "10m"`, `timeout: "2m"`. `__b`'s 10m is
better calibrated than `__a`'s 5m given two `gh` invocations per project per pass; this is
an inventory view, not a pager. Add `__a`'s **daily full repair scan** to catch missed
updates, lost state, transfers, and renames — `__b` lacks it and it is what makes the
"every issue" promise recoverable.

**Cursors and backfill** (`__a`'s algorithm, which is the more careful of the two):

1. First run does an exhaustive, resumable backfill, indexing all local refs/PR URLs
   before writing anything. Bound work per run by **page count**, not by silently
   truncating the inventory.
2. Persist a per-project, per-object-type high-water mark (last processed `updated_at` +
   a stable provider id tie-breaker) in the expanded instance's state directory.
3. Each incremental run starts with an overlap window (~10 min), pages to exhaustion, and
   dedupes by provider id — tolerating equal timestamps and crash-after-write.
4. Advance the checkpoint only after every planned local mutation succeeds.
5. Daily full repair scan.

Add `provider_id` (GitHub node id) to the issue wire for robust cursors and diagnostics,
per `__a`. Keep the human-readable `bug:` form as the stored association.

**Polling first, webhooks never as the source of truth.** Both reports agree. Webhooks
need a reachable endpoint, hook configuration, delivery auth, and replay handling, and
still need backfill for downtime. A webhook receiver can later force an immediate run of
the *same* reconciler; do not build a second event-processing domain model.

**Capability granularity** (`__a`, and **[verified]**): `supports_issues()` requires *all*
five hooks — its own docstring says "All operations are required so a partial
implementation cannot claim CRUD capability." A synchronizer needs only listing, and a
read-only provider should still populate badges. Split list/read/mutate capability, or
expose a structured capability record, so ACE can gate each operation independently
rather than hiding all issue context when a provider cannot write.

---

## 6. D4 — ACE information architecture

The reports are complementary here: `__a` has the presentation model, `__b` has the
mechanics. Both are needed.

### 6.1 Merge Bugs into Beads

**Precondition, and it is a hard one.** The merge is honest only if the bead list is a
superset of the bug list within scope. Any bug excluded by watermark, label filter, or
budget becomes invisible the moment the Bugs pane disappears. Either mirror everything in
scope and state the scope explicitly, or keep a status-line count of unmirrored bugs. The
first is cleaner. **Phase 5 must not land until Phase 3 has run clean on real projects.**

Beads becomes canonical and the list contains **only bead rows** — remote-only issues must
never become rows (`__a`). Enrich rows with compact issue facets:

```text
sase-ab12  Fix project alias resolution      🐞 #418 open
sase-cd34  Retire legacy provider hook       🐞 #391 closed
sase-ef56  Refactor local cache
```

Multiple `bug:` refs get a bounded count badge and a picker, never a silent first-match
(`__a`).

Detail panel gains an **External issue** section: title, state, labels, assignees, author,
update time, comment count, URL, staleness/provider error, plus reverse links from
`find_bug_links`. Migrate the Bugs pane operations here — open in browser, view remote
body, edit, close/reopen, copy URL or `bug:` ref, attach an existing issue, create an
issue for an unlinked bead, refresh — each **individually capability-gated** (`__a`).

**[verified]** Mechanics (`__b`): drop `"bugs"` from `ArtifactsSubTab`,
`ARTIFACTS_SUBTAB_ORDER`, `ARTIFACTS_PANE_IDS`, and `_ARTIFACT_LABELS`; re-key `#FF5F5F`
in `ARTIFACTS_ACCENTS` as the bug-chip accent so the visual vocabulary survives. Retire
~600 lines in `widgets/artifacts/bugs.py`, a 459-line action mixin, plus
`artifacts_bugs.py` and `bugs_rendering.py`.

**Sub-tab number keys renumber silently.** `__b`'s catch, and worth elevating: number keys
are generated from `ARTIFACTS_SUBTAB_ORDER` in `bindings.py:110`, so removing `"bugs"`
shifts `prs` from 4→3 and `files` from 5→4 with no error. Muscle memory breaks silently.
Keep `show_artifacts_bugs` as a deprecated alias routing to Beads.

**Key collisions are real** (`__b`): both panes bind `j k f o y a s R e`. With Bugs gone,
`o` (open bug) and `y` (copy ref) move to Beads gated on "selected bead has a bug link" —
matching the footer convention in `src/sase/ace/CLAUDE.md` (a keymap appears in the footer
iff its condition is sometimes true and sometimes false). `e` and `s` genuinely conflict
with bead edit and status cycle, so bug mutations want a `b`-prefixed pair (`be` edit
bug, `bs` close/reopen) rather than stealing the bead primaries.

**Filters:** redefine `has:bug` (currently computed from `issue.patch_bug_id` in
`beads_filtering.py:186`) to mean "has an external bug link," and add a `bug:` key for
value filtering. `__a`'s token set is the right target: `bug`, `bug:none`, `bug:open`,
`bug:closed`, plus provider label tokens.

**Never fetch per row.** One bounded batch/cache refresh per project, with last-refresh
time and a stale indicator; never a provider call while rendering. Local navigation must
not block on the network.

### 6.2 Rename PRs to Patches, show provenance

**[verified]** `ArtifactsPrsPane` already wraps the Patch view, so this is a naming and
metadata correction. Rename the visible sub-tab and internal `prs` identifiers, keeping
`prs` as a compatibility alias for saved UI state, commands, and tests — consistent with
established practice (`ChangeSpec = Patch`, `changespec_bug_id`, `find_all_changespecs`).
Touch points (`__b`): `ArtifactsSubTab`, `ARTIFACTS_PANE_IDS`, `_ARTIFACT_LABELS`,
`ARTIFACTS_ACCENTS`, `ArtifactsPrsPane`, the `entry_navigator` guard, `show_artifacts_prs`,
`commands/types.py`, `tab_quickstart.py`, `modals/help_modal/patches_artifact_bindings.py`.

The PR badge and the origin chip are **two independent signals** and must never collapse
into one boolean (`__a`) — a badge means "this Patch has a remote review," the chip
answers "who created it":

```text
sase_refactor_cache_1     Mailed      PR #812 · sase
sase_fix_windows_path_1   Mailed      PR #819 · external
sase_old_parser_2         Submitted   PR #601 · origin ?
sase_local_experiment_1   WIP         no PR
```

**[verified]** A new Patch field spelling must be updated in all four surfaces enumerated
by `src/sase/ace/CLAUDE.md:5-14`: the chezmoi `saseproject.vim` syntax file,
`src/sase/ace/display.py`, `src/sase/ace/query/highlighting.py`, and
`src/sase/ace/tui/widgets/patch_detail.py` — plus `section_order.py`, the parser, and
storage. Add an `origin:` ACE query property (`query/searchable.py`, `query/matchers.py`)
so `origin:external` selects them.

Add an explicit **"mark PR origin" / "adopt"** operation to clear `unknown` records —
this is the user-facing half of the tri-state decision in §4.

---

## 7. Risks

1. **Bead-store write contention** (`__b`) — the mirror becomes a *writer* on a store live
   agents also write, and every mutation commits to the sidecar. Follow
   `bead_store_refresh`'s pattern: bounded per-project lock waits, a whole-pass work
   budget, persistent exponential backoff. Mutation must acquire the store lock, rebuild
   the identity index *while holding it*, then append the create event only if still
   uncovered (`__a`) — never list-then-create across two unlocked shell-outs.
2. **First-run flood** — hundreds of open issues mint hundreds of beads on pass one.
   Durable per-project watermark plus a per-pass creation budget, following the
   `managed_tmp_reap` "at most N per pass" convention.
3. **Cross-machine duplicates** (`__a`) — two machines reconciling stale copies of a
   hosted bead sidecar can both import. Go through the existing publication/integration
   path, and make integration collapse simultaneous imports by semantic bug identity.
   A partial-unique index on `external_ref` makes the local half of this enforceable.
4. **`gh` auth in the detached lumberjack** (`__b`) — the Bugs pane proves `gh` works from
   the interactive TUI; the axe daemon runs detached with a different environment. Wants a
   `src/sase/doctor/` check.
5. **Project rename** — persisted refs must resolve through the stable project key or
   project aliases, or a rename duplicates every issue. Compounded by §2.1.
6. **Symvision** — dismantling the Bugs pane orphans symbols; read
   `sase/memory/symvision.md` before the lint gate fails.
7. **Visual snapshots** — Artifacts panes have PNG goldens; the merge and the rename both
   need `just test-visual --sase-update-visual-snapshots`.
8. **Tracker noise** — trackers hold feature requests and questions, not only bugs. A
   label include/exclude filter is the escape hatch, but see the §6.1 superset
   precondition before using it.
9. **Auth/rate-limit/outage** must produce a degraded run, never a deletion. One malformed
   remote record is reported with its id and must not advance the checkpoint past
   unprocessed data. A `--dry-run` must show exact creations without mutating or advancing
   cursors.

---

## Recommended solution

A six-phase epic. Phases 1–2 are independent; 3←1, 4←2, 5←3, 6←4. Phase 5 additionally
gates on Phase 3 having run clean against real projects (§6.1).

**Phase 1 — `external_ref` bead field.** Add a nullable canonical-artifact-ref column to
the sase-core bead schema with a partial-unique index per store, using the additive
migration precedent (`needs_refs_migration()`; the `changespec_bug_id` `ALTER TABLE` in
`_db_migrations.py:45`). Thread through wire/jsonl/events/read/mutation/cli/history/search
and the Python mirrors. Expose `sase bead create --external-ref` / `sase bead update`.
Redefine `has:bug` and add a `bug:` filter key over it. **Add a project-qualified
normalizer** (§2.1) and extend `bug_links.py` to match the new field *through it* — do not
widen `_normalize_bug_id`.

**Phase 2 — PR provider seam.** Add `PullRequestWire` (`provider_id, number, url, title,
body, state, is_draft, author, head_ref, base_ref, created_at, updated_at, closed_at,
merged_at`), `vcs_list_pull_requests(cwd, state, limit)` to `_base.py`/`_hookspec.py`,
`supports_pull_requests()` to `_plugin_manager.py`/`_registry.py`, the `sase-github`
implementation over `gh pr list --json`, and the in-memory fake. Add `provider_id` to
`IssueWire`. Split list/read/mutate capability probes (§5). Transcribes `e5d299582`.

**Phase 3 — `external_bug_mirror` chop.** Core builtin in `src/sase/scripts/`, registered
in `pyproject.toml` and the `checks` lane with `for_each: {source: projects}`,
`run_every: "10m"`, `timeout: "2m"`, gated at runtime on `supports_issues()`. Diff
`list_issues(state="all")` against beads keyed on `external_ref`; create missing beads as
`open` tasks with **unset size**, the issue title/body, both the `external_ref` and a
`bug:<project>#<n>` entry in `refs`; append an attributed note on upstream state flips.
Watermark, per-pass budget, overlap window, backoff, daily repair scan, `--dry-run`.

**Phase 4 — `PR_ORIGIN` and `external_pr_mirror` chop.** Add `PR_ORIGIN:` to
`section_order.py`, parser, storage, and the four ACE styling surfaces. Stamp
`SASE_PATCH=<reserved-name>` in `append_pr_tags` — **not** `build_pr_body` (§2.3) — and
write `PR_ORIGIN: sase` on tracked creation. Add the second chop with a **new importer**
that locks both active and archive specs and writes to the correct destination (§4);
`add_patch_to_project_file()` cannot do this. **In the same phase**, exclude
`PR_ORIGIN: external` structurally in `chop_runner_context.py` before the user query is
applied, and guard `pr_submitted_checks` separately (§2.2). Test the crash window between
remote success and local Patch completion.

**Phase 5 — merge Bugs into Beads.** Bug chip on rows, External issue section in the
detail panel, migrated capability-gated actions (`o`/`y` direct, mutations behind `b`),
retire the `bugs` sub-tab, keep `show_artifacts_bugs` as a deprecated alias, note the
number-key renumber, refresh visual goldens, check symvision.

**Phase 6 — PRs → Patches.** Rename sub-tab and identifiers with legacy aliases, render
the PR badge and origin chip as independent signals, add the `origin:` query property and
the "mark PR origin / adopt" operation for `unknown` records.

## Open questions for the project owner

Carried from `__b`, with a recommendation on each:

1. **Scope of "bug."** Mirror every tracker issue, or only a configured label set?
   *Recommend every issue* — it is what makes the Beads pane a faithful superset and the
   §6.1 precondition satisfiable. Revisit only if noise proves intolerable.
2. **Watermark default.** Mirror only issues created after opt-in, or backfill the whole
   open backlog? *Recommend full backfill, bounded by page count per run* — a watermark
   default quietly breaks the "every issue" promise the merged UI implies.
3. **Closed upstream bugs.** Note-only, or propose closing the bead through a gate?
   *Recommend note-only* to start; a gate per upstream close reintroduces the inbox flood.
4. **PR adoption breadth.** All PRs on the repo, or only those authored by your own
   GitHub identity? This is the one with no clear default — "all" catches third-party
   contributions and is the reason the §2.2 chop exclusion is load-bearing; "own" keeps
   the Patch list to work you are personally responsible for.
