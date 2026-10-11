# Creating New Projects from the SASE Admin Center Projects Tab

**Researcher:** mus · **Date:** 2026-10-11 · **Swarm:** research.49

## 1. Question asked

Add "create new project" support to the Projects tab of the SASE Admin
Center panel: enabled-by-default; VCS picker; a "likely projects" menu
(adopt an existing remote not yet associated with a SASE project);
create-from-scratch via the VCS plugin (`gh repo create` for
`sase-github`); full provider-option parity in the creation form; and a
mandate that the design lead on intuitiveness, reliability, and beauty.

## 2. What exists today (verified in this checkout)

### 2.1 The Projects tab has management actions but no creation path

- `src/sase/ace/tui/modals/projects_pane.py` defines `ProjectsPane` with
  three sub-tabs (`projects` / `repos` / `workspaces`) and a
  `_PROJECT_ONLY_ACTIONS` set: enable, disable, delete, set-current,
  edit aliases, init (`i` / `I`), reload, filter. There is **no create /
  new / adopt action**, and no key bound to one (creation keys in
  `default_config.yml` around line 737 cover `c`/`i`/`I` but nothing for
  new-project).
- The closest precedent for a multi-step, preview-before-mutate flow is
  the init gesture: `projects_pane_init_actions.py` runs a check proc,
  shows `InitPlanModal` (check-preview-apply with diffs via
  `projects_pane_init_diffs.py`), then applies. Any creation wizard
  should copy this shape, not invent a new one.
- Reusable beauty/input primitives already exist:
  `InventoryProjectPicker` (filterable `OptionList` modal),
  `InputCollectionModal` + `TypedInputForm` (typed validation,
  optional-field reveal), `ConfirmActionModal`. A creation flow composed
  from these will look native; a bespoke form will not.

### 2.2 The project model makes "enabled by default" nearly free

- Project specs are files under `~/.sase/projects/<project_name>/`
  (`<name>.sase`, legacy `.gp` still read) carrying at minimum
  `WORKSPACE_DIR:`. Lifecycle state (`PROJECT_STATE`) is Rust-owned via
  `sase_core_rs` (`core/project_lifecycle_facade.py`); `sase project
  list --json` in this session shows `"state": "enabled",
  "state_explicit": false, "state_source": "defaulted"` — i.e. **a spec
  with no explicit state is already enabled**. Creating an enabled
  project therefore means *writing no state line at all*, not writing
  `enabled` explicitly. Per the Rust-core-boundary rule, lifecycle
  writes must go through the Rust binding, but creation needs none.
- Naming/alias allocation already exists and must be reused, not
  reimplemented: the `sase-github` plugin's `workspace/projects.py`
  provides `allocate_canonical_project_name(user, project, records)`
  (`gh_<owner>__<repo>`, `-2` suffix on collision, case-insensitive
  occupancy over names, display names, and aliases) plus
  `ensure_useful_repo_name` (friendly display alias). `sase project
  show sase --json` confirms the resulting record shape (`project_name`,
  `effective_project_name`, `vcs_kind: "gh"`, `workflow_type: "gh"`).

### 2.3 Lazy project creation already happens — outside the TUI

- `sase_github/workspace/refs.py::_resolve_repo_path_ref` (the `#gh:`
  launch path) already **creates a project spec on demand** via
  `set_workspace_dir()` (`workspace_provider/_utils_checkout.py`:
  creates parent dirs, writes `WORKSPACE_DIR:`, inserts before
  `RUNNING:`/`NAME:` lines, invalidates the display snapshot) and clones
  via `clone_gh_repo` when the checkout is absent. `bare_git_init.py`'s
  `init_bare_git_project` is the equivalent for local git. So the TUI
  does not need a new spec writer; it needs a guided front door onto
  these paths, plus a remote-creation path that does not exist yet.

### 2.4 The VCS plugin seam already supports half the request

- `workspace_provider/_hookspec.py` + `_plugin_manager.py` (pluggy,
  `ws_` prefix, first-result-wins) expose `WorkflowMetadata`
  (`workflow_type`, `display_name`, `vcs_family`, …),
  `ws_list_repo_candidates(workflow_type, namespace)` returning
  `VcsRepoCandidates` with a typed error taxonomy (`auth`, `network`,
  `not_found`, `tool_missing`, `unsupported_namespace`, `unknown`), and
  `ws_list_ref_namespaces` for locally-known owners. The GitHub plugin
  implements candidates as `gh repo list <namespace> --json
  name,description,visibility,isArchived,isFork,pushedAt --limit
  <max_repos>` (default 200, 10 s timeout, `GH_PROMPT_DISABLED=1`),
  namespaces from `github_orgs` config plus local checkouts.
- `github_orgs` **is a real config key** (`sase_github/config.py::
  get_github_orgs`, schema description: "org/user names the user has
  push access to, used for cloning and PR submission"). The request's
  "configured GitHub organizations" maps exactly onto it. No new config
  plumbing is needed for org discovery.
- What is **missing** is any create-remote hook. The only `gh repo
  create` caller in the plugin is SDD-sidecar creation
  (`workspace/sdd_repo.py::create_github_sdd_repo`: `gh repo create
  <owner/repo> --<visibility> --description …`, with an already-exists
  probe and a "you may lack repo-create rights in {owner}" error). A TUI
  that shells out to `gh` directly would bypass the plugin seam and
  break every non-GitHub provider.

### 2.5 `gh repo create` option surface (verified `gh repo create --help`)

Full flags: `--public | --private | --internal`, `--description`,
`--homepage`, `--gitignore` (template), `--license`, `--template`,
`--team` (org team access), `--add-readme`, `--disable-issues`,
`--disable-wiki`, `--clone`, `--source`, `--push`, `--remote`,
`--include-all-branches`. Note `--clone` clones into CWD — wrong for
SASE's home-rooted layout (`~/projects/github/<owner>/<repo>/` via
`github_workspace_dir`); the flow must clone into the canonical
workspace dir instead.

## 3. Critique of the plan

**Is this a good idea? Yes — with adjustments.** Creation is the
missing half of a tab that today only manages and deletes; users
currently fall back to typing `#gh:owner/repo` at a prompt (undiscoverable)
or hand-writing specs (error-prone). A guided adopt-or-create flow is the
right shape. Specific judgments per requirement:

1. **Enabled by default — agree, keep, and simplify.** It matches the
   existing defaulted-enabled semantics, so the spec writer should omit
   `PROJECT_STATE` rather than stamp `enabled`. One caveat: if the clone
   or remote-create fails midway, the project should still be created
   enabled (consistent default) but the status line/toast must say what
   is missing (e.g. "project created; clone failed — press `i` to retry
   init"), never silently half-present.
2. **VCS picker — agree, but drive it from plugin metadata.** Do not
   hardcode GitHub-vs-git. List `get_workflow_metadata()` entries by
   `display_name` (today: GitHub, plus whatever bare-git declares). This
   is what makes the third-party-provider story real.
3. **"Likely projects" menu — the highest-value step; widen it
   slightly.** Restrict to `github_orgs` and you miss the common case of
   a teammate's repo the user was just pasted. Recommended source, in
   order: (a) per-namespace `ws_list_repo_candidates` across
   `github_orgs` ∪ locally-known owners, **minus already-associated**
   repos (match by normalized `WORKSPACE_DIR`, reusing
   `find_project_record_for_workspace`); (b) a free-type
   `owner/repo` row; (c) "Create new…" row. Per-namespace failures must
   be independent (one org's 403 must not kill the menu) and load off
   the UI thread with the existing inventory-pane worker pattern,
   honoring `vcs_repo_completion.cache_ttl_seconds` (600 s).
4. **Create-from-scratch via the VCS plugin — agree, and make it a new
   hook, not a TUI `gh` call.** Proposed: `ws_get_repo_create_schema`
   (provider declares fields with types/defaults/visibility) and
   `ws_create_repo(schema_values)` (provider executes). GitHub's schema
   mirrors `gh repo create`; bare-git's schema is local paths. This is
   the only piece that touches provider extensibility, so it is worth
   the extra interface.
5. **"Prompt for ALL provider options" — push back; use progressive
   disclosure instead.** Dumping all ~14 `gh` flags into one form is the
   opposite of beautiful and will rot as `gh` evolves (schema owned by
   the provider fixes the rot; disclosure fixes the beauty). Always
   show: owner/namespace, repo name, visibility (public/private/
   internal), description. Collapse under "Advanced": homepage,
   gitignore template, license, template repo, team, add-readme,
   disable issues/wiki. Pre-fill visibility from the provider default,
   not from a SASE guess.
6. **Missing and should be added:** (a) preview + explicit confirm step
   (remote creates are irreversible — mirror `InitPlanModal`);
   (b) idempotency/rollback rules — re-check name occupancy at apply
   time, probe remote-exists before create, and on failure never
   auto-delete a created remote (report the orphan with the exact
   `gh repo delete` command); (c) post-creation wiring — clone into the
   canonical workspace dir, offer (don't force) set-current and init;
   (d) CLI parity (`sase project create …`) so the flow is scriptable
   and testable without a TUI; (e) keybinding — `n` ("new") is the
   natural choice if unbound in the Projects context (verify against the
   keymap registry; fall back to `N`).

## 4. Alternatives considered

- **CLI-first, TUI later.** Cheaper, but creation is inherently
  picker-driven (which of my 200 org repos?); CLI-first optimizes the
  rare case. Reject as the primary path; still ship CLI parity.
- **Auto-import everything (bulk adopt).** Tempting for org
  onboarding, but it creates dozens of enabled projects (and local
  clones) the user never asked for, with real disk/network cost.
  The per-repo adopt menu dominates it. Consider bulk-adopt only as a
  later multi-mark extension of the same picker.
- **Rely on implicit `#ref` creation only.** Zero new UI, but
  undiscoverable and it cannot create remotes at all. Keep it as the
  engine; add the guided front door.

## 5. Recommended solution

**A 4-step wizard in the Projects tab, backed by two new plugin hooks
and one CLI command:**

1. **VCS step** — picker of `display_name`s from
   `get_workflow_metadata()`. (1 row per provider; skip entirely when
   only one provider is installed.)
2. **Adopt-or-create step** — one filterable `OptionList` (reuse
   `InventoryProjectPicker` styling): unassociated candidates with
   description/visibility/staleness columns, each row showing its
   derived SASE project name; then `✎ Type owner/repo…` and
   `＋ Create new repository…`. Archived repos and forks render dimmed
   with badges, selectable but deprioritized. Background load, per-org
   error rows ("`acme`: auth failed — `gh auth login`"), cached 600 s.
3. **Details step** — schema-driven form (reuse `TypedInputForm`):
   core fields up top, Advanced collapsed. Live validation (name
   legality via `is_valid_sase_project_name`, occupancy via
   `allocate_canonical_project_name` preview, remote-exists probe).
4. **Review step** — InitPlanModal-style preview (provider, remote,
   local workspace dir, SASE project name + alias, visibility,
   clone/init actions) with explicit confirm. Apply runs in a session
   worker: create remote (new repos) → allocate name → write spec
   (default-enabled, no state line) → clone into canonical dir →
   reload records → toast + highlight new row → offer set-current.

**Backend changes:** add `ws_get_repo_create_schema` /
`ws_create_repo` hooks; implement for `gh` (thin wrapper over the
existing `gh repo create` + probe + rights-error pattern) and bare-git
(local `init_bare_git_project` path); adopt path reuses
`ws_resolve_ref`/`ws_clone_external_repo` + `ensure_useful_repo_name`;
add `sase project create [--vcs …] [--adopt … | --new …]` for parity.
No Rust lifecycle changes (creation writes no state). No new config
keys (reuse `github_orgs`, `vcs_repo_completion`).

**Why this shape:** every step reuses a proven in-repo primitive
(picker, typed form, plan-preview, worker, canonical naming, gh error
patterns); providers stay decoupled behind a schema they own; the only
irreversible action (remote create) gets the only blocking confirm;
and the default-enabled, default-beautiful path (adopt one repo, three
keystrokes) stays under five seconds while the full-option path remains
one disclosure triangle away.

## 6. Risks / open questions

- `gh auth` state and org token scopes (fine-grained PATs lacking
  repo-create rights) are the top failure mode; the per-org error rows
  and rights-aware messages are load-bearing, not polish.
- Non-`github.com` hosts (`github_hosts`) need the owner picker to be
  host-aware; confirm the schema carries host before finalizing the
  hook signature.
- Multi-mark bulk adopt is deferred; ensure the picker component choice
  does not preclude it.
- Verify `n` against the Projects-pane keymap registry to avoid
  stealing an existing binding.
