---
create_time: 2026-10-11
updated_time: 2026-10-11
status: draft
tags:
  [
    research_swarm,
    admin-center,
    projects-tab,
    workspace-providers,
    sase-github,
    tui-design,
    project-lifecycle,
  ]
---

# Admin Center project creation: design research

**Question.** How should the SASE Admin Center Projects tab grow a "create
project" flow: pick a VCS, offer likely unassociated repositories, and
optionally create a new remote with the provider's full option set? Is the
request a good idea, and what should change?

**Researcher.** grk (`research.49.grk`). Independent report. I did not read
peer reports from this swarm.

**Sources.** Live code and docs in this workspace, the linked `sase-github`
and `sase-core` checkouts (opened through `sase repo open`), `gh repo create
--help`, SASE glossary/TUI/artifact memory, and the current Projects-tab
bindings and visual language.

## Verdict

Build this. The Projects tab is an inventory of projects the user already
has, and the only first-class create path today is a VCS macro
(`#git:<name>` or `#gh:<owner>/<repo>`) typed into a prompt. That is
expert-only. A Projects-tab create action is the missing onboarding and
fleet-management surface.

Keep the requested information architecture — provider, then likely
candidates, then create-from-scratch — but **do not implement it as a stack
of sequential prompts, and do not let the TUI call `gh` itself.**

The recommended solution is a **plugin-owned provision API**, a **CLI that
is the source of truth**, and a **single stepper wizard** on the Projects
tab that reuses the existing repo-candidate cache, typed-input form,
preview-first confirmation, and init-plan machinery.

---

## Critique of the requested plan

The plan is directionally right. The Projects tab is the correct home, new
projects should land enabled, GitHub candidates should come from configured
orgs minus already-registered projects, and create-from-scratch belongs in
the VCS/workspace plugin rather than in ACE.

These parts of the plan should change.

### 1. Sequential prompts are the wrong TUI shape

"Prompt for VCS, then prompt for a menu, then prompt for options" is a CLI
wizard stuffed into a TUI. SASE already has a better pattern: one modal
with a visible stepper (`● Location › ○ Name` in the mini-macro save flow),
filterable option lists (`InventoryProjectPicker`, `EnumChoicePickerModal`),
and a preview-then-confirm card (`InitPlanModal`,
`PluginActionConfirmModal`).

A stack of unrelated prompts is hard to reverse, hides the destination, and
fights Admin Center's "preview first, then write" law.

**Adjustment.** One wizard, four named steps, Back/Esc at every step, with
the destination (display name, workflow, path, visibility) always visible
in a side summary.

### 2. "VCS" is the wrong noun

The request says "select what VCS they want." In SASE, **workflow type** is
the unit that creates projects: `git` (bundled bare-git) and `gh`
(sase-github). Both are the git family. `docs/vcs.md` and
`WorkflowMetadata` already distinguish `vcs_family` (`git`) from
`workflow_type` (`gh` / `git`) from `vcs_provider_name` (`github` /
`bare_git`). Prompt-completion goldens already reserve `#gl:` for a future
GitLab plugin.

Asking "Git vs Mercurial" would hide GitHub, which is the interesting case.
Asking "Git vs GitHub" is the real choice, and it must come from installed
workspace plugins, not a hardcoded enum.

**Adjustment.** Step 1 is **provider / workflow**, labeled with each
plugin's `display_name` ("GitHub", "Git (bare)"), not a VCS-family picker.

### 3. Do not dump every provider flag on the first create screen

`gh repo create` currently exposes public/private/internal, description,
homepage, gitignore, license, template, team, README, disable-issues,
disable-wiki, source, remote, push, clone, and include-all-branches. Several
of those are **wrong** in a SASE project wizard:

| Flag | Why it should not be a first-class wizard field |
| --- | --- |
| `--clone` | SASE always clones into the provider's `WORKSPACE_DIR`. |
| `--source` / `--push` / `--remote` | Those adopt a local tree as origin. That is a different product. |
| `--template` / `--include-all-branches` / `--team` | Real, but rare. Advanced. |
| `--internal` | Only meaningful on GitHub Enterprise. |

**Adjustment.** Plugin-declared schema with **common fields** and
**advanced fields**. Common GitHub fields: owner, name, visibility,
description, add-README. Advanced behind `a` or a disclosure row: license,
gitignore, homepage, template, team, disable-issues, disable-wiki,
internal-when-enterprise.

The user-facing requirement "prompt for the same options the provider
supports" still holds: every supported option is reachable. They are not
all equally loud.

### 4. Admin Center mutations preview first

Config writes, plugin install, Updates, and Projects-tab `i`/`I` all show
the exact command or diff before anything mutates. Creating a GitHub
repository is a **remote mutation** with org-policy consequences. A TUI
that runs `gh repo create` on Enter would be the first Admin Center action
that writes off-box without a preview.

**Adjustment.** The last step is a confirmation card that names the exact
`gh`/`git` argv, the ProjectSpec path, `WORKSPACE_DIR`, visibility, display
name, enabled state, and whether the project will become current. Confirm
runs as a durable proc, the same way init apply does.

### 5. Creating a GitHub repo is new; adopting one is not

Glossary and `docs/getting_started.md`: `#git:<name>` **creates** a
bare-git project; `#gh:<owner>/<repo>` **requires an existing GitHub
repository**, then clones it and writes a ProjectSpec. sase-github already
creates remotes, but only for **sidecars** (`ws_create_sdd_remote` /
`create_github_sdd_repo`). There is no hook that creates a primary GitHub
repo.

So the request is two features:

1. **Adopt existing** — already implemented as `ws_resolve_ref`. The TUI
   just needs a picker that does not require typing `#gh:`.
2. **Create remote, then adopt** — new plugin work.

Treating them as one "create project" button is correct. Implementing them
as one code path that always calls `gh repo create` is not.

### 6. `github_orgs` is the wrong complete candidate source, and a good v1 seed

`github_orgs` controls **SSH vs HTTPS clone URLs**, and it also seeds
`#gh:` owner completion. It is not "organizations the authenticated user
belongs to." A user who never set `github_orgs` still has GitHub projects
(`canonical_project_owner` of existing `gh_<owner>__<repo>` records). A
user who set it has a local, fast, offline namespace list.

`ws_list_repo_candidates` then runs `gh repo list <owner>` (limit 200,
cached 10 minutes via `vcs_repo_completion`). That list includes repos
**already** associated with SASE projects. The wizard must subtract those.

**Adjustment.** v1 candidate namespaces = `github_orgs` ∪ owners of
existing GitHub ProjectSpecs. v1 candidate rows = cached `gh repo list`
minus already-registered workspace/canonical names. A later enhancement
can add `gh api user/orgs` and the authenticated user login; do not block
v1 on a live membership API. Always keep a typed `owner/repo` fallback.

### 7. Do not auto-create sidecars, and do not skip `sase init`

GitHub projects declare `sdd_storage_policy: "separate_repo"`. Creating a
missing `--plans` / `--research` sidecar already requires an interactive
`y`/`yes` that `--yes` cannot grant (`docs/init.md`,
`docs/plugins.md` sidecar section). Auto-creating public sidecars from a
"new project" button would punch through that gate.

**Adjustment.** After a successful create, offer the existing
Projects-tab init preview (`i`) for the new project. Do not create sidecars
inside the wizard.

### 8. TUI-only is a reliability trap

Every other Projects-tab mutation (`enable`, `disable`, `alias`,
`set-current`, `init`) is a TUI binding over a library/CLI path. A wizard
that talks to `gh` from a Textual screen cannot be tested, scripted, or
recovered from a half-finished clone without a TTY.

**Adjustment.** `sase project create` is the public command. The wizard is
a client of that command's library. The TUI must not grow a second
provisioner.

### 9. Enabled-by-default is already the storage default — keep it

Missing `PROJECT_STATE` means enabled. `sase project` and the Projects tab
already treat that as the user-facing default. New ProjectSpecs created by
`#gh` / `#git` omit the field. The wizard should too, unless the user
unchecks "Enable this project." Do not write `PROJECT_STATE: enabled`
just to make the default visible in the file.

---

## Current state (what the design must reuse)

### Projects tab today

Opened with `#` then `5`. Three sub-tabs: Projects · Repos · Workspaces.
True projects only (no `home`, no sibling backing records). Keys already
cover enable (`a`), disable (`d`), delete (`Ctrl+D`), aliases (`A`),
set-current (`c`), init (`i`/`I`), marks, filter, and inventory jumps.
**There is no create key.** `n` is free on the pane (`ace.keymaps.projects`
in `src/sase/default_config.yml`).

Visual language already in `project_management_rendering.py`:

- Current project: accent-colored name plus `CUR` / `+CURRENT`
- State: `● enabled` in `#00D7AF`, `○ disabled` in `#FFD700`
- VCS chips: `gh` in `#87D7FF`, `git` in `#00D7AF`

Any new row the wizard inserts should look like a native Projects row on
the first refresh, not like a toast-only success.

Init on this tab is the gold-standard mutation: status line immediately,
off-thread `sase init --check --json`, preview modal, then one tracked
`--yes` proc. Create must copy that skeleton.

### How projects actually get created today

| Path | What it does | Enabled? |
| --- | --- | --- |
| `#git:<name>` | `init_bare_git_project`: bare repo at `~/.sase/repos/<name>.git`, clone at `~/projects/git/<name>/`, ProjectSpec | yes (field omitted) |
| `#git:<bare-path>` | Register an existing bare repo | yes |
| `#gh:<owner>/<repo>` | `resolve_gh_ref`: clone if missing, allocate `gh_<owner>__<repo>`, write `WORKSPACE_DIR`, allocate `PROJECT_NAME` from the repo basename | yes |
| `#gh:<alias>` | Resolve an existing project; does not create | n/a |
| Projects tab | Lifecycle only | n/a |
| `sase project` | `list` / `show` / `enable` / `disable` / `alias` / `current` / `set-current`. **No create.** | n/a |

`ws_peek_ref` is the read-only twin of resolve. TUI keystroke paths must
use peek/list, never `resolve_ref` (TUI perf rule 11: resolve clones and
allocates records).

### Plugin surface that already does 80% of listing

Workspace hooks in `src/sase/workspace_provider/_hookspec.py`:

- `ws_get_workflow_metadata` — collect-all; this is the provider catalog
- `ws_list_ref_namespaces` — local-only owners/orgs (GitHub: `github_orgs` + existing project owners)
- `ws_list_repo_candidates` — network `gh repo list` with typed errors (`auth`, `network`, `not_found`, `tool_missing`)
- `ws_resolve_ref` — mutating adopt/create for the workflow
- `ws_create_sdd_remote` — GitHub sidecar `gh repo create --<visibility> --description …`

Headless cache in `src/sase/macro/vcs_repo_completion.py`: 10-minute TTL,
max 200 repos, stale-on-error fallback. The wizard must call this, not
spawn a parallel `gh` cache.

Typed forms already exist (`TypedInputForm` driven by `InputArg`). Gate
and prompt-input modals share it. Plugin-declared create fields should be
`InputArg`s so GitHub can add a field without an ACE change.

### sase-core boundary

Rust core owns ProjectSpec parse, lifecycle normalize/update, and listing
records. It does not own clone, `gh`, or ProjectSpec creation. Provisioning
is plugin I/O plus a Python orchestrator. That is the correct split under
`rust-core-required`: a web/CLI/TUI frontend needs the **same provision
API**, but that API is not a ProjectSpec parser. Do not port `gh repo
create` into sase-core.

Hook **argument names** are a frozen compatibility boundary
(`tests/test_workspace_provider_hookspec.py`). New hooks are additive.
Renaming `ws_resolve_ref` is not on the table.

### Beauty and motion constraints

- Never block the Textual event loop: `gh repo list`, clone, and create
  run in workers / tracked procs (`tui_perf.md` rules 1 and 3).
- Show cached candidates instantly, then refresh (rule 5).
- Detail panel of the wizard can debounce; highlight must not (rule 7).
- New PNG goldens under `tests/ace/tui/visual/` for the wizard steps, in
  the same Config Center Projects snapshot family.

---

## Requirements: keep, adjust, add

### Keep

- New projects **enabled by default**.
- User picks a provider before seeing candidates.
- Candidate menu of likely unassociated repos for that provider.
- Explicit create-from-scratch, implemented by the VCS/workspace plugin
  (`gh repo create` for GitHub; `init_bare_git_project` for bare-git).
- Provider options available when creating a remote.
- Home in the Admin Center Projects tab, beautiful and keyboard-first.

### Adjust (justified)

1. **Workflow/provider, not VCS family.** See critique §2.
2. **One stepper wizard, not sequential prompts.** See critique §1.
3. **Progressive disclosure of create options.** See critique §3.
4. **Preview-first confirmation; durable proc for the write.** See
   critique §4.
5. **Adopt vs create are two modes of one flow.** See critique §5.
6. **Candidate namespaces from local config + existing projects in v1.**
   See critique §6.
7. **After create, offer `sase init`; do not create sidecars in-wizard.**
   See critique §7.
8. **CLI + library first.** See critique §8.
9. **Default new GitHub visibility is private.** Sidecar creation
   currently defaults public because SDD sidecars are often shared
   metadata. A primary product repo should not go public because the user
   hit Enter. Public remains one keystroke on the options step.
10. **Default `--add-readme` on for brand-new GitHub repos.** An empty
    GitHub repo has no default branch until the first commit; SASE's clone
    path then has to guess `origin/main`. A README makes the first clone
    have a commit. The user can turn it off.
11. **Do not expose `--clone` / `--source` / `--push`.** SASE owns the
    checkout location.
12. **Set-current after create defaults on.** A newly created project is
    almost always the one the user wants to launch on. The checkbox is
    visible and unchecking it is allowed. `c` already exists for later.
13. **Binding is `n` (New), configurable as `ace.keymaps.projects.create_project`.**
    `a` is enable. Do not steal it. `n` on the init-plan modal means
    cancel; that modal is not up when the pane binding fires.

### Add (the request implied these, the plan did not say them)

- Typed `owner/repo` or path fallback when the candidate list is empty,
  stale, or truncated at 200.
- Plugin-missing and `gh`-missing empty states that point at Admin Center
  Updates (`sase plugin install github`) and `gh auth login`.
- Idempotent adopt: if the repo is already a SASE project, select it and
  say so; do not create a second ProjectSpec.
- Archived and fork rows stay visible, dimmed, sorted last.
- Enterprise: honor `github_hosts` / `GH_HOST` the same way completion
  does. Show `--internal` only when the default host is not github.com.
- Partial-failure recovery: if `gh repo create` succeeded and clone or
  ProjectSpec write failed, the preview/error names the remote and the
  exact retry (`sase project create --workflow gh --adopt owner/repo`).
- Visual snapshots for each wizard step.

---

## Recommended solution

### Shape

```
Projects pane ──n──► ProjectCreateWizard (one modal, four steps)
                         │
                         ▼
              sase.project_provision (Python orchestrator)
                         │
          ┌──────────────┼──────────────────┐
          ▼              ▼                  ▼
   workspace hooks   existing          sase project
   (list / schema /  ws_resolve_ref    create CLI
    create remote)   (adopt / clone)
```

The TUI never shells out to `gh`. sase-github already knows how.

### Layer A — workspace plugin hooks (additive)

Two new `firstresult=True` hooks, owned by each workspace plugin. Names
below are the recommended contract; freeze them in
`tests/test_workspace_provider_hookspec.py` the moment they land.

```text
ws_describe_provision(workflow_type) -> ProvisionSchema | None

ProvisionSchema:
  workflow_type, display_name
  adopt_supported: bool
  create_supported: bool
  create_fields: tuple[InputArg, ...]          # common
  create_advanced_fields: tuple[InputArg, ...] # progressive
  candidate_kind_label: str                    # "repository", "bare repo"

ws_create_remote(workflow_type, fields: dict) -> CreatedRemote | None

CreatedRemote:
  ref: str          # "owner/repo" or filesystem path
  display: str
  extra: dict       # visibility, url, host
```

Adopt-existing does **not** get a new mutating hook. After the user picks
a candidate (or after `ws_create_remote` returns), the orchestrator calls
the existing `ws_resolve_ref(ref, workflow_type)`. That path already:

- clones to the provider workspace layout
- allocates `gh_<owner>__<repo>` (with `-2` suffix on collision)
- writes `WORKSPACE_DIR`
- allocates a useful `PROJECT_NAME`
- refuses provider mismatches and the reserved `home` name

GitHub `ws_create_remote` is a thin, testable wrapper around the sidecar
helper that already runs `gh repo create`. Bare-git `create_supported` is
true but `ws_create_remote` can be a no-op: `ws_resolve_ref("#git:name")`
already creates the bare repo. The orchestrator still goes through
resolve so both providers share one post-create path.

Listing stays on the existing hooks plus the existing cache. The
orchestrator subtracts already-registered projects by canonical key,
`PROJECT_NAME`, alias, and normalized `WORKSPACE_DIR`.

### Layer B — orchestrator and CLI

New module, e.g. `sase.project_provision`, called by both CLI and TUI.

```bash
sase project create                         # interactive, same schema
sase project create -w gh -a sase-org/foo   # adopt existing
sase project create -w gh -N -o sase-org -n foo -v private -d "…"
sase project create -w git -n mytool
sase project create --check -j              # plan JSON, no writes
```

CLI rules: `create` sits alphabetically with `current` / `disable` /
`enable` / `list`. Every public long option has a short alias (`-w`, `-a`
adopt, `-N` new-remote, `-o` owner, `-n` name, `-v` visibility, `-d`
description, `-j` json, `-c` set-current, `-e` enable). `--check --json`
mirrors `sase init --check --json` so the TUI preview is the CLI plan, not
a second renderer.

`--check` output (sketch):

```json
{
  "schema_version": 1,
  "mode": "adopt" | "create",
  "workflow_type": "gh",
  "ref": "sase-org/foo",
  "project_key": "gh_sase-org__foo",
  "display_name": "foo",
  "enabled": true,
  "set_current": true,
  "workspace_dir": "~/projects/github/sase-org/foo/",
  "commands": [["gh", "repo", "create", "sase-org/foo", "--private", "…"]],
  "warnings": [],
  "blockers": []
}
```

Human CLI output is colored: provider chip, visibility, path, and the
same ●/○ state glyph the TUI uses.

### Layer C — Projects-tab wizard (the beautiful part)

**Open.** On the Projects sub-tab, `n` (and a command-palette "Create
project") pushes `ProjectCreateWizard`. Disabled on Repos/Workspaces — those
sub-tabs already have `p` for picking a project, not creating one.

**Chrome.** One modal, Config-center proportions, numbered stepper in the
border title:

```text
New project   01 Provider  ·  02 Pick  ·  03 Options  ·  04 Preview
● Provider › ○ Pick › ○ Options › ○ Preview
```

A right-hand summary column (or a footer card on narrow terminals) always
shows what is known so far: provider, ref, visibility, display name,
workspace path, enabled, set-current. Empty slots render as `—` in dim,
not as lies.

**Step 01 Provider.** One row per `ws_get_workflow_metadata()` result.

```text
  GitHub            gh     sase-github installed   12 unassociated
  Git (bare)        git    bundled                 create locally
  GitLab            gl     plugin not installed    i to install
```

If sase-github is missing, the GitHub row is still listed (from a small
known-catalog, or from the plugin catalog) but is not selectable without
install; `i` jumps to Updates on that plugin, the same recovery the
Updates tab already teaches. Do not hide GitHub because the plugin is
missing — that is how users discover it.

Default highlight: GitHub if the plugin is installed, else Git (bare).
Most of this user's fleet is `gh`.

**Step 02 Pick.** This is the heart of the feature and should feel like
the Projects list, not like a file dialog.

Layout:

- Filter input (`/` or just type, matching `InventoryProjectPicker`)
- Pinned action row at the top: `✦ Create a new GitHub repository…`
- Section headers per namespace (`sase-org`, `bbugyi200`, `from github_orgs`)
- Rows: `name   PRIVATE/PUBLIC   description   pushed 2d ago`
- Footer: `12 unassociated · 4 already in SASE hidden · cached 3m ago · r refresh`

Behavior:

- `j`/`k` move, `Enter` adopt the highlighted repo (skip Options, go to
  Preview) or enter Options when the pinned create row is highlighted.
- Archived and forks are dim and sorted last; they remain selectable.
- Already-associated repos are **omitted**, with a count in the footer so
  the user knows the filter is working.
- Stale cache paints immediately, then a worker refreshes. On auth error,
  the list stays and a banner says `run gh auth login` with `g` to copy
  the command — Machines-tab guidance style, plus a retry.
- Empty org list: banner explaining `github_orgs` in `sase.yml`, and a
  field to type `owner/repo` anyway.
- Truncation at `vcs_repo_completion.max_repos`: footer `showing 200 · type
  to filter or enter owner/repo`.
- Bare-git pick step: name field plus optional "register existing bare
  path"; likely candidates are unregistered dirs under `~/projects/git/`
  and unregistered `~/.sase/repos/*.git`. That is the git analog of
  "repos you probably meant."

**Step 03 Options.** Only for create-from-scratch. `TypedInputForm` from
the plugin schema.

GitHub common:

- Owner (enum of namespaces, default last-used or first `github_orgs`)
- Name (validated as a SASE project-name-legal repo basename)
- Visibility (enum: private default, public, internal if enterprise)
- Description
- Add README (bool, default on)

Advanced (`a` toggles, or a `▸ Advanced` disclosure): license, gitignore,
homepage, template, team, disable issues/wiki.

Live validation: name collision with an existing SASE display name shows
the allocated `foo_1` **before** confirm, not after. Repo-name-taken on
GitHub is a Preview-step blocker from a cheap `gh repo view` peek in the
plan, not a surprise at apply.

Bare-git options: name, optional existing bare path, optional workspace
path. Defaults match `init_bare_git_project`.

A checkbox row shared by both providers, below the plugin fields:

- `● Enable this project` (default on)
- `● Make current` (default on)

**Step 04 Preview.** Reuse the InitPlan / plugin-confirm visual grammar.

Neutral kind for adopt (local clone + ProjectSpec). **Danger kind** for
create-remote (off-box write), with the visibility spelled in the title:
`Create private GitHub repository sase-org/foo`.

Show:

- Exact argv (`gh repo create sase-org/foo --private --add-readme --description …`)
- ProjectSpec path (`~/.sase/projects/gh_sase-org__foo/…`)
- Workspace (`~/projects/github/sase-org/foo/`)
- Display name / tag (`+foo`)
- Enabled / current
- What will **not** happen: "Plans and research sidecars are not created
  here. Press i on the new row to initialize."

Keys: `y` / `Enter` apply, `n` / `Esc` / `q` cancel, `b` back, `Ctrl+D` /
`Ctrl+U` scroll. Match init-plan.

**Apply.** Tracked proc (`display_name: create project · foo`), exclusive
scope so a second `n` cannot double-create, Procs-tab visibility, pane
status line `Creating foo…`. On success: reload records, highlight the new
row, toast `Created +foo · enabled · current`, and a second toast or
footer hint `i initialize this project`. On failure: keep the wizard on
Preview with the error and the retry command.

**Motion.** Opening the wizard is local and instant. Network starts after
the provider is chosen, in a worker. Clone/create never run on the UI
thread.

### Beauty specifics (so this does not ship as a form dump)

- Stepper uses the same `● › ○` language as mini-macro save, not a
  progress bar.
- Provider rows use the existing VCS colors (`#87D7FF` / `#00D7AF`).
- Visibility badges: `PRIVATE` dim, `PUBLIC` warning-yellow, `INTERNAL`
  accent. Sidecar-create already thinks in these words; stay consistent.
- The pinned "Create new…" row is a distinct glyph (`✦`) so it cannot be
  mistaken for a repo named "Create".
- Summary column uses the project accent **once the display name is
  known**, so the user sees the color the Projects list will use.
- Empty, loading, error, and stale are first-class states with recovery
  keys, not a blank OptionList.
- Mouse: tab strip, rows, and confirm button all clickable, matching the
  rest of Admin Center. Keyboard remains the designed path.

### What the TUI must not do

- Call `gh` or `git` directly.
- Call `ws_resolve_ref` while the user is typing a filter.
- Create `--plans` / `--research` remotes.
- Write `PROJECT_STATE: enabled` unless the user left the box checked
  *and* we have a reason to persist it; prefer omitting the field.
- Restart sase's TUI. This is not a plugin install.
- Use a sase gate. Gates pause **agents**. This is a human, in the TUI,
  already present. A gate would bounce the decision through notifications
  for no gain.

---

## Phasing

Ship as one epic with two user-visible slices, both on the same `n` key so
the wizard does not grow a second entrance.

**Slice 1 — Adopt existing (low risk, high leverage).**
Orchestrator + `sase project create --adopt` + wizard steps 01, 02, 04.
GitHub uses `ws_resolve_ref`; bare-git uses the same for an existing bare
path or a new local name (local create is already safe and implemented).
This alone removes the "you had to know `#gh:org/repo`" hole.

**Slice 2 — Create remote.**
`ws_create_remote` in sase-github, Options step, danger-kind preview,
private-by-default, README-on-by-default, `--check` plan includes the
exact `gh` argv. Reuse sidecar `gh repo create` helper, with tests for
already-exists, missing `gh`, auth, and org-permission errors (those
strings already exist in `sdd_repo.py`).

Do not hide slice 2 behind a feature flag. It is an additive key with a
danger confirmation. Feature flags in SASE are for behavior whose old
branch must stay reachable; there is no old create-project branch.

---

## Tests and proof

- **Orchestrator unit tests** with a fake workspace plugin: adopt, create,
  collision allocation, already-registered short-circuit, enable checkbox,
  set-current checkbox, `--check` JSON schema.
- **sase-github:** `ws_create_remote` around the existing `gh repo create`
  fake; refuse `--clone`; default private; enterprise `GH_HOST`;
  already-exists classified like sidecar create.
- **CLI:** help text, short aliases, default-list notice unchanged for
  bare `sase project`, JSON `--check`.
- **TUI:** keymap `n` only on the Projects sub-tab; stepper Back/Esc;
  filter; pinned create row; stale-cache banner; preview danger vs
  neutral; success selects the new row. Follow `tests/ace/tui/test_projects_pane*.py`
  and `test_init_plan_modal.py`.
- **Visual goldens:** provider step, pick step with mixed visibility, options
  step, danger preview. Extend
  `tests/ace/tui/visual/test_ace_png_snapshots_config_center_projects.py`.
- **Perf:** opening `n` does no `gh`; listing starts after provider
  selection; apply is a tracked proc.

---

## Risks

| Risk | Mitigation |
| --- | --- |
| Org has >200 repos | Footer + type-in fallback + existing `max_repos` knob |
| `github_orgs` unset | Seed from existing project owners; typed owner/repo; empty-state copy |
| `gh repo create` succeeds, clone fails | Error names the remote and the adopt retry |
| User creates a public repo by accident | Private default; danger preview spells visibility |
| Plugin missing | Provider row still visible, install recovery |
| Double-submit | Exclusive proc scope, same as init |
| Name collisions | Show allocated display name on Options/Preview |
| Sidecar surprise | Explicit "not in this flow" line; offer `i` after |
| TUI freeze | Workers + cached paint; never resolve_ref on keystroke |
| Future GitLab/hg | Workflow metadata + schema hooks; no GitHub types in ACE |

---

## Would I take a different approach?

I would not:

- Put a "New project" text form on the pane with no provider step.
- Drive the flow through `#gh:` insertion into the prompt bar. That
  reuses code and remains undiscoverable.
- Mount `sase github create` as a `sase_commands` plugin command. Project
  lifecycle is a built-in group; plugins extend it through workspace
  hooks. `plugin-commands` is for whole top-level verbs like `listen`.
- Wait for a web Admin Center. The TUI is the product.
- Make create a gate-turn. The user is already at the keyboard.
- Auto-run `sase init --yes` after create. Sidecar creation is
  intentionally default-no.

I **would** still keep the prompt-bar `#gh:` / `#git:` create-on-resolve
behavior. The wizard is another front door onto the same orchestrator, not
a replacement. Power users keep typing; everyone else presses `n`.

---

## Recommended solution (one paragraph)

Add `n` on the Admin Center Projects sub-tab, bound to a four-step wizard
(Provider → Pick → Options → Preview) whose Pick step is a filterable list
of unassociated provider repos plus a pinned "Create new…" row. Implement
provision once in a Python orchestrator exposed as `sase project create`,
reusing `ws_list_ref_namespaces`, the `vcs_repo_completion` cache,
`ws_resolve_ref` for adopt/clone, and a new `ws_create_remote` hook for
hosted remotes. Default new projects enabled (omit `PROJECT_STATE`),
default new GitHub remotes private with a README, preview the exact argv
before any write, run apply as a tracked proc, and offer the existing init
preview afterward instead of creating sidecars in the wizard. Progressive
disclosure covers the rest of `gh repo create`. That is intuitive (one
obvious key, likely repos first), reliable (CLI-tested, preview-first,
off-thread), and beautiful (native Projects visual language, stepper,
danger-tinted remote create, recovery empty states).
