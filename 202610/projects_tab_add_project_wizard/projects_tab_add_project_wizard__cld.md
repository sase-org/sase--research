# Admin Center → Projects: A "New Project" Flow — Research, Critique, and Recommended Design

_Researcher: cld · 2026-10-11 · scope: sase (TUI + CLI), sase-github (plugin), sase-core
(Rust), verified against the live install on athena (`sase v0.17.1+2386.gcca177315`,
`gh 2.100.0`)._

---

## 0. TL;DR

- **Build it, but aim at the real job.** The user doesn't want "a project record". They
  want "the repo I have (or want) → I can launch agents into it". Today the _only_ way a
  project comes to exist is as a side effect of the first agent launch with a
  `#gh:owner/repo` or `#git:name` macro. That path has no preview, no discoverability,
  and no way to create a new remote repo.
- **Three facts from the code and the live data reshape your requirements:**
  1. **"Repos in my orgs not yet in a project" is mostly noise if done naively.** Your
     three `github_orgs` hold 135 repos (bbugyi200 107, sase-org 16, bobs-org 12).
     26 of them are SASE sidecars (`*--plans`, `*--beads`, `*--research`,
     `*--agents`, `*--attachments*`, legacy `*--sdd`). 24 are forks. Six are repos
     already _linked_ to `sase` (sase-core, sase-github, …). Locally, 37 of the 137
     clone dirs under `~/projects/github/` are legacy numbered copies (`CV_10`,
     `CV_100`, …).
  2. **A registered GitHub project is not launchable until its repo is SASE-managed.**
     `#gh` setup materializes the SDD sidecars and raises for repos without
     `is_sase_managed: true`
     (`src/sase/sdd/_store_materialization.py:353-378`; `docs/sdd_storage.md:152-162`).
     Creating a _missing_ sidecar needs a fresh interactive `y`, and `--yes` cannot
     grant it (`docs/init.md:41-45`).
  3. **Most building blocks already exist:**
     - repo suggestions: `ws_list_ref_namespaces`, plus `ws_list_repo_candidates` with
       a 10-minute disk cache;
     - preview and execution: `ws_peek_ref` (read-only key/name preview) and
       `ws_resolve_ref` (clone + register);
     - UI pieces: the `sase init … --check --json` preview modal with its terminal
       valve, the schema-driven property-sheet editor, and durable procs.

     What's missing: a "create remote repo" hook, a CLI verb, candidate classification,
     and the wizard UI.
- **Recommendation:**
  - **CLI first.** Add `sase project add | create | suggest`, each with a
    `--check --json` plan and an idempotent `--yes` apply.
  - **Plugin.** sase-github declares its own repo-creation schema and implements a new
    `ws_create_repo` hook (using `gh repo create`).
  - **Rust core.** Candidate classification is a pure function in sase-core.
  - **TUI.** A beautiful three-stage modal (**Source → Details → Review**) opened with
    `n`. It hands off to the _existing_ init preview for SASE setup and ends on a
    "ready" screen whose `+` key launches the first agent.

---

## 1. What Exists Today (Facts)

### 1.1 The Projects tab

Live capture of the current tab (Admin Center `#` → `5`):

```
                     PROJECTS  |  Repos  |  Workspaces
          enabled:3  ·  disabled:0  ·  marked:0  ·  current:+sase
┌ Projects ─────────────────────────────────────────────────────────────┐
│ MARK CUR NAME                           VCS  STATE      CLAIMS WS REPOS │
│          actstat (gh_bbugyi200__actstat) gh  ● enabled  0      2  9     │
│          bob-cli (gh_bobs-org__bob-cli)  gh  ● enabled  1      12 13    │
│      +   sase (gh_sase-org__sase)        gh  ● enabled  38     47 19    │
└───────────────────────────────────────────────────────────────────────┘
┌ Details ──────────────────────────────────────────────────────────────┐ …
 j/k move ' jump / filter [ / ] sub-tab i init I init all Enter enable r repos w workspaces m mark u unmark all e edit A aliases a
```

**Patterns any new feature must follow:**

- Records load through `list_project_records(…, "all", include_home=False,
  projects_only=True)` (`src/sase/ace/tui/modals/projects_pane.py:314`).
- Mutations reload, re-highlight with `preferred_project=`, and call
  `_notify_lifecycle_changed()` and `_refresh_launchable_mru_snapshot()`
  (`project_management_actions.py:212-235, 808-837`).
- Slow work runs in `run_worker(thread=True)` or as tracked session procs.
- **Init is the template to copy.** `i` runs `sase init -p … --check --json` as a proc,
  renders a plan preview (`init_plan_modal.py`), then runs exactly one
  `sase init … --yes` proc:
  - the modal shows the exact apply argv;
  - `t` suspends the TUI into a real terminal when the plan has TTY-only blockers;
  - the glyph vocabulary is `+` create (green), `~` update (yellow), `−` delete (red),
    `●` validate/deploy (cyan) (`init_plan_modal_rendering.py:20-27`);
  - the scope and argv module is deliberately Textual-free (`projects_pane_init.py`).
- **Keymaps** live under `ace.keymaps.projects` (`src/sase/default_config.yml:714-739`;
  `keymaps/app_keymaps.py:301`).
  - **`n` is unbound** in this pane.
  - `n` already means "create" elsewhere: `beads_create: "n"`
    (`default_config.yml:857`).
- **The hints row already overflows.** The trailing `a` is clipped in the capture, so a
  new `n new` hint needs a layout decision (§4.7).

### 1.2 How projects come into existence today

**No `create` API exists anywhere:**

- The `sase project` subcommands are only alias / current / disable / enable / list /
  set-current / set-state / show (`src/sase/main/parser_project.py`).
- sase-core's `project_spec.rs` has pure transforms and listing. There is no create
  function.

**GitHub creation is a side effect of resolving `#gh:owner/repo`.** The call path is
`gh_setup` → `ws_resolve_ref` → `resolve_gh_ref` → `_resolve_repo_path_ref`
(sase-github `workspace/refs.py:81-118, 182`):

1. **Clone** to `~/projects/github/<owner>/<repo>/`. It tries SSH, then HTTPS, and
   cleans up partial clones (`workspace/remotes.py:66-126`). **It has no timeout**
   (`remotes.py:91-98`).
2. **Reuse an existing record** when one has the same `WORKSPACE_DIR`
   (`workspace/projects.py:73`). An already-cloned dir with no record is adopted
   without re-cloning.
3. **Allocate the key** `gh_<owner>__<repo>`, adding `-2` on a case-insensitive
   collision (`projects.py:125-138`).
4. **Write the spec** `~/.sase/projects/<key>/<key>.sase` with `WORKSPACE_DIR` and
   `PROJECT_NAME: <repo>` (`<repo>_1` on a display-name collision).

**Bare git:** `#git:<name>` → `resolve_git_ref` Mode 3 → `init_bare_git_project`
(`src/sase/workspace_provider/plugins/bare_git_init.py:51`).

- Bare repo: `~/.sase/repos/<name>.git`.
- Clone: `~/projects/git/<name>/`.
- It also does SDD init, an initial commit, and a push.

**Lifecycle:** a missing `PROJECT_STATE:` means enabled, with `state_explicit=false`
(`project_spec.rs:206-229`). **"Enabled by default" is already true for every creation
path** except the internal `sibling` specs.

**The glossary codifies the status quo.** Its "Sase Project" entry says _"A project is
created only when a new VCS macro argument resolves to a valid project."_
`docs/workspace.md:13-15` says the same.

### 1.3 The provider plugin surface you can build on

The hookspecs are in `src/sase/workspace_provider/_hookspec.py`. All are `firstresult`
except `ws_get_workflow_metadata`.

> **Constraint:** argument names are a frozen cross-repo boundary
> (`_hookspec.py:148-166`). Choose new hook argument names carefully and pin them in
> `tests/test_workspace_provider_hookspec.py`.

| Need in the wizard                      | Existing piece                                                                                                                                                                                                                                                                      |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| List VCS providers + display names      | `ws_get_workflow_metadata`: `gh` / "GitHub" (sase-github) and `git` / "Git (bare)" (built-in)                                                                                                                                                                                       |
| Owners to suggest from                  | `ws_list_ref_namespaces`: local-only; enabled-project owners ∪ `github_orgs` (sase-github `completion.py:178`)                                                                                                                                                                      |
| Remote repos per owner                  | `ws_list_repo_candidates` → `gh repo list <owner> --json name,description,visibility,isArchived,isFork,pushedAt --limit 200`, 10s timeout, typed error kinds `auth`/`network`/`not_found`/`tool_missing` (`completion.py:56-157`)                                                    |
| Caching                                 | `fetch_repo_candidates` and `peek_cached_repo_candidates`: memo + disk TTL cache, 600s, at `~/.sase/vcs_repo_cache/<wf>/<ns>.json` (`src/sase/macro/vcs_repo_completion.py:20, 305, 369, 465`)                                                                                    |
| Read-only preview of key / name         | `ws_peek_ref` (contract: no clone, no write, no network; `_hookspec.py:190-199`)                                                                                                                                                                                                    |
| Clone + register                        | `ws_resolve_ref` (side-effectful)                                                                                                                                                                                                                                                   |
| Create a remote repo                    | **Only for sidecars.** `create_github_sdd_repo` runs `gh repo create … --public/--private --description`, `GH_PROMPT_DISABLED=1`, and treats "already exists" as adopt (sase-github `sdd_repo.py:238-298`). **No hook exists for primary repos.**                                    |
| Option form UI                          | `SchemaObjectForm` (`schema_object_form.py`), a pure sparse editor for one JSON-Schema object with basics/advanced groups, diagnostics, and constraints, rendered by the AXE property sheet (`axe_entry_sheet.py`, `axe_entry_editor_modal.py`, edit → preview stages)          |
| Plan preview / apply / terminal handoff | `InitScope` + `init_plan_modal` + `_submit_session_worker` (`projects_pane_init_actions.py`)                                                                                                                                                                                        |

### 1.4 The "SASE-managed" gate (the hidden requirement)

The SDD storage policy for `gh` is `separate_repo`.

**Unmanaged repos can't launch.** `_materialize_sdd_store_with_created` resolves
creation authorization for any separate-repo store. That raises
`"SDD materialization refused: repository is not SASE-managed…"` unless the repo's own
`sase/sase.yml` has `is_sase_managed: true`
(`src/sase/sdd/_store_materialization.py:144-240, 353-378`). `#gh` setup calls this
before claiming a workspace (`sase-github scripts/gh_setup.py:59, 187, 274`), and per
`docs/sdd_storage.md` "failures stop setup; GitHub projects do not fall back to local
storage". **So adding an unmanaged GitHub repo gives you a project that `#gh` launches
will fail on.** This is from code reading; I did not reproduce it destructively.

**Managing a repo** is `sase init -M --yes` from inside the checkout. This writes
`sase/sase.yml`; the following memory/repo init may commit and push. `-M` cannot be
combined with `-p` or `--all` (`docs/init.md:76-86`), so the TUI's existing `i` cannot
mark a new repo.

**Sidecar creation is human-gated on purpose.** "`--yes` can run the repository
initializer, but it cannot approve creation of a missing provider sidecar. Each creation
always requires an interactive `y`/`yes`…" (`docs/init.md:41-45`). The TUI already
honours this through the init preview's `t` terminal valve.

**Already-managed repos are cheap.** When a repo is already managed and its sidecars
exist, the first launch auto-connects them ("remote-create-free";
`docs/sdd_storage.md:165-175`).

### 1.5 Live data on this machine (why naive suggestions fail)

| Source                              | Count | Noise a naive filter would surface                                                                                                       |
| ----------------------------------- | ----: | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `gh repo list bbugyi200`            |   107 | 24 forks; `actstat--{beads,agents,plans,research,attachments*,sdd}`; stale `bob-cli--*` copies left in the personal account; `dotfiles--sdd` |
| `gh repo list sase-org`             |    16 | 6 sidecars (`sase--*`); 6 repos already linked by `sase` (sase-core, sase-github, sase-nvim, …)                                          |
| `gh repo list bobs-org`             |    12 | 8 sidecars (`bob-cli--*`, `bob-plugins--sdd`)                                                                                            |
| `~/projects/github/*/*/`            |   137 | 37 legacy numbered copies (`*_\d+`); test debris owners (`alice`, `owner`, `git@github.com:bbugyi200`); third-party clones (neovim, Textualize, …) |
| `gh api user/orgs` vs `github_orgs` |   5/3 | You belong to shelltopia, python-boltons and zettel-org but deliberately don't configure them. `github_orgs` is the right signal.        |

**Latency (cold):** `gh repo list` takes 1.56s (bbugyi200), 0.32s and 0.28s for the
others. A managed-ness probe (`gh api repos/o/r/contents/sase/sase.yml`) takes 0.27s,
and a name-availability probe (`gh repo view`) 0.22s. So the source list is ready in
under 2s cold when the owners are fetched in parallel, and instantly from cache.

**The repo inventory already knows the sidecars.** `sase repo list --all --json` gives
each sidecar's exact remote URL (for example
`git@github.com:bobs-org/bob-cli--agents.git`), and `kind` separates
primary / sidecar / linked / external. External opens (e.g.
`gh:bbugyi200/bugyi-chops`) are a strong "you'll want this as a project" signal.

### 1.6 What `gh repo create` supports (verified against cli/cli @ `ec5b51204`, 2026-10-09)

**Flags:**

- name / owner;
- `--public | --private | --internal` (required when non-interactive);
- `-d` description, `-h` homepage;
- `--add-readme`, `-g` gitignore template, `-l` license (`gh repo license list`: 13;
  `gh repo gitignore list`: 162);
- `-p` template, `--include-all-branches`;
- `-t` team;
- `--disable-issues`, `--disable-wiki`;
- `-s` source, `--push`, `-r` remote, `-c` clone.

**Interactive modes:** from scratch / from template / push an existing local repo
(`pkg/cmd/repo/create/create.go:271-275`).

**Hard constraints the form must encode** (`create.go:163-187`):

- `--template` ✗ with `--gitignore` / `--license`, ✗ with `--add-readme`, ✗ with
  `--team`. `--include-all-branches` requires `--template`.
- `--source` ✗ with `--clone` / `--template` / `--license` / `--gitignore`. `--push`
  and `--remote` require `--source`.
- `Internal` is only offered for org owners (`create.go:917-924`), and in practice only
  enterprise orgs. sase-org is on the `free` plan.
- Names are normalized: invalid characters become `-` and a trailing `.git` is dropped
  (`pkg/cmd/repo/shared/repo.go:11-14`).

### 1.7 Side findings worth fixing regardless

1. **Stale docs.** sase-github `docs/configuration.md:71-72`, `docs/architecture.md`
   and `README.md` claim `github_orgs` picks SSH vs HTTPS cloning. The code always
   tries SSH then HTTPS and never reads it (`remotes.py:83-86`).
2. **`git clone` has no timeout** (`remotes.py:91-98`). A hung clone hangs the setup or
   the wizard proc forever.
3. **`ws_detect_workflow_type` never checks the host** (`workspace_plugin.py:63-91`).
   Any http/ssh origin, GitLab included, is classified `gh`. This matters for a "paste
   a path" input.
4. **`projects_base()` ignores `SASE_HOME`.** It is hard-coded to
   `Path.home()/.sase/projects` (`workspace/projects.py:16-17`) instead of
   `sase_projects_dir()`.
5. **The Projects hints row overflows** at the default width (see §1.1).

---

## 2. Critique: Is This a Good Idea?

**Yes. The current state is the strongest argument for it:**

- **Not discoverable.** Creation hides behind a prompt-syntax side effect. A new user
  has to know `#gh:owner/repo` exists.
- **Conflates two acts.** It mixes "register a project" with "launch an agent". A failed
  launch (bad auth, unmanaged repo, missing sidecars) leaves a half-registered project
  and a failed agent.
- **No preview.** You learn the key (`gh_owner__repo`) and display name (`repo_1`?)
  after the fact.
- **No creation story.** "I want to start a new thing" means leaving SASE for
  `gh repo create`, then coming back to type the macro.
- **Doesn't scale.** The Projects tab can enable, disable, delete, alias and init, but
  not add. That gap is conspicuous in an "Admin Center".

**Risks, and how the design below handles them:**

| Risk                                                                                              | Mitigation                                                                                                                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| sase core grows a GitHub-shaped UI (violates the plugin architecture)                             | The provider declares its form as JSON Schema. Core only renders `SchemaObjectForm` and never knows about `--gitignore`.                                                                                                                                     |
| TUI freezes on network calls (`tui_perf` rules 1, 10, 11)                                         | All listing and probing is off-thread with a cache shown first. Keystroke paths only filter in memory. Side-effectful `resolve_ref` runs only inside the apply proc.                                                                                         |
| Logic lives only in the TUI, so the CLI, Telegram, the mobile gateway and editors can't match it  | CLI-first: the TUI renders the CLI's `--check --json` plan and runs its `--yes` argv, exactly like `i` init. Classification is a pure sase-core function (memory: Rust Core Backend Boundary).                                                                |
| Partial failures (repo created, clone failed) leave a mess                                        | An ordered, idempotent, resumable step plan. Never auto-delete remote state.                                                                                                                                                                                |
| Agents start creating public repos                                                                | Remote creation is human-only (env-guarded like `global-install-is-human-only`). Sidecar creation keeps its TTY invariant.                                                                                                                                  |
| Scope creep into "a GitHub client"                                                                | Only create + register + setup. No repo settings management, no deletion of remote repos.                                                                                                                                                                   |

**What I'd do differently from the request as written:**

- Treat **"launchable"** as the success criterion, not "record exists".
- Make the **CLI the product** and the TUI its most beautiful frontend.
- Make the VCS choice **visible but not a separate screen**.
- Show **all** provider options, with **progressive disclosure** and constraint-aware
  greying rather than a flat 15-field form.
- **Rank** suggestions instead of just listing them.

---

## 3. Requirement Adjustments (Clearly Called Out)

| #       | Your requirement                                         | Adjustment                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Why                                                                                                                                                                                                                                                                                                |
| ------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A1**  | Prompt the user to select a VCS                          | The VCS is an **explicit tab strip at the top of the Source screen** (`GitHub · Git (local)`), switched with `[`/`]` or clicks. It is preselected to the last-used provider, else the current project's VCS. Providers that don't implement creation hooks show disabled with a reason.                                                                                                                                                                                         | Still an explicit choice, but you see its consequences (the repo list) immediately, and it saves a screen on every repeat use. With two providers, a dedicated step is ceremony.                                                                                                                 |
| **A2**  | Suggest repos in configured orgs not yet in a project    | Suggestions are **classified and ranked**: ON THIS MACHINE (clones in your owners without a project) → SUGGESTED (pushed recently) → LINKED TO YOUR PROJECTS → DISABLED PROJECTS (Enter re-enables). **Hidden but countable:** sidecars, forks (`f`), archived, numbered clone copies, already-enabled projects (still searchable, so typing `sase` shows "already a project → jump"). | 26 of 135 remote repos are sidecars and 24 are forks. The local signal (already cloned, or opened by agents as external) beats recency.                                                                                                                                                             |
| **A3**  | Prompt for all options the VCS provider supports         | **All options available, essentials prompted.** Basics (owner, name, description, visibility, README, .gitignore, license) are always shown. Advanced (template, all-branches, homepage, team, issues, wiki) sits one key (`a`) away. Conflicts are greyed out with the reason (from `gh`'s own validation).                                                                                                                                                                   | A flat 13-flag form is neither intuitive nor beautiful, and "prompt" for rarely-changed flags is friction. Nothing is unreachable.                                                                                                                                                                 |
| **A4**  | (implicit) creating the project is the end               | Add **"Set up SASE in this repo"**: mark it managed, then chain the existing init preview. It is **default ON for new repos** and **default ON (with explicit disclosure) for unmanaged existing repos you can push to**. Already-managed repos skip it (auto-connect on first launch).                                                                                                                                                                                         | §1.4: an unmanaged GitHub project can't launch `#gh` agents.                                                                                                                                                                                                                                      |
| **A5**  | (implicit) TUI feature                                   | **CLI-first:** `sase project add`, `sase project create`, `sase project suggest`, with `-c/--check -j/--json` plans and `-y/--yes` apply. The TUI is a frontend over them.                                                                                                                                                                                                                                                                                                     | Rust-core boundary litmus test (another frontend must match). Testable without Textual. Same proven shape as `i` init.                                                                                                                                                                           |
| **A6**  | Pick from a menu                                         | Also accept **paste-anything** in the filter box: `owner/repo`, `gh:owner/repo`, `https://github.com/o/r(.git)`, `git@github.com:o/r.git`, or a local path. Host-aware classification (`github_hosts`) picks the provider.                                                                                                                                                                                                                                                     | The fastest path for power users, and it covers repos outside `github_orgs`.                                                                                                                                                                                                                       |
| **A7**  | New projects enabled by default                          | Keep it implicit: **don't write `PROJECT_STATE`** (missing = enabled). Show "● enabled" as a fact on Details/Review rather than a toggle. **Special case:** if the repo is already a _disabled_ project, the action becomes "Re-enable" instead of creating a duplicate.                                                                                                                                                                                                         | Matches the glossary and the existing creation paths. A "start disabled" toggle has little value.                                                                                                                                                                                                 |
| **A8**  | Use the VCS plugin to create the repo                    | Agree, plus: **remote repo creation is human-only.** `sase project create` refuses under SASE agent env unless a bypass is given (like `just install`). Sidecar creation keeps its existing TTY rule (the `t` valve).                                                                                                                                                                                                                                                          | The feature introduces a second kind of remote creation. Agents shouldn't silently mint public repos.                                                                                                                                                                                              |
| **A9**  | (unstated)                                               | **Out of v1:** "publish an existing local directory" (`gh --source --push`), bulk-add via marks, a `＋ New project…` entry in the `+` launch picker, and propagating to other fleet machines.                                                                                                                                                                                                                                                                                  | Good v2 delighters, but each adds a failure surface.                                                                                                                                                                                                                                                |
| **A10** | (unstated)                                               | **Owner and visibility defaults.** Owner: last used, else the current project's owner, else the `gh` login. Visibility: **Private the first time**, then remembered per owner.                                                                                                                                                                                                                                                                                                 | You can't un-leak a public repo. Remembering the choice removes the friction after the first use.                                                                                                                                                                                                  |

---

## 4. Recommended Design

### 4.1 Principles

1. **Plan, then apply.** Every mutation is previewed as a plan with the exact argv. The
   apply step runs as one durable proc that appears in Admin Center → Procs.
2. **Idempotent, resumable steps.** Re-running the same argv after any failure resumes
   from the first incomplete step. Nothing remote is ever deleted automatically.
3. **Provider owns provider things; core owns shared logic; the TUI owns presentation.**
4. **Cache first, then revalidate.** Show the list instantly from cache, refresh per
   owner in parallel, and degrade per owner (one failing org doesn't blank the list).
5. **Never surprise.** Commits, pushes, and created repos are named before they happen,
   using the init preview's glyph vocabulary.

### 4.2 Architecture

```
┌──────────────── sase TUI (presentation only) ──────────────────────────────┐
│ NewProjectModal ── pure models (no Textual): wizard state machine,         │
│   source rows, property sheet (SchemaObjectForm), review rows              │
│   │ worker: suggest (in-process API, cached)    │ proc: sase project … -y  │
└───┼─────────────────────────────────────────────┼──────────────────────────┘
    ▼                                             ▼
┌──────────────── sase (Python) ─────────────────────────────────────────────┐
│ sase.project_create: plan builder, step runner + journal, CLI handlers     │
│   add / create / suggest  ── uses ──►  workspace_provider hooks            │
│   classification ──► sase_core_rs.classify_project_candidates (pure)       │
└──────────────────────┬─────────────────────────────────────────────────────┘
                       ▼
┌──────────── provider plugins ──────────────────────────────────────────────┐
│ sase-github: ws_list_ref_namespaces*, ws_list_repo_candidates*,            │
│   ws_peek_ref*, ws_resolve_ref*, NEW ws_list_local_repo_candidates,        │
│   NEW ws_probe_repo, NEW ws_describe_repo_creation, NEW ws_create_repo     │
│ bare_git (built-in): NEW local candidates + create via init_bare_git_project│
└────────────────────────────────────────────────────────────────────────────┘
(* = exists today)
```

**What goes in sase-core (Rust):**

- `classify_project_candidates(input: ProjectCandidateInputWire) ->
  ProjectCandidateListWire`. This is a pure function: grouping, hiding reasons, ranking,
  and identity normalization.
- A pure `validate_new_project_identity(key, name, aliases, records)` that reuses the
  existing case-insensitive uniqueness rules, so the CLI, the TUI's inline validation,
  and any future web or mobile surface agree.

Both follow sase-core conventions: free functions over `*Wire` structs and `thiserror`
errors. File writes stay in Python under `patch_lock`, as today.

### 4.3 CLI contract (follows `cli_rules`: alphabetical, short alias for every long option)

```
sase project add REF [-a ALIAS]... [-c] [-j] [-m] [-n NAME] [-s | -S] [-y]
    REF: owner/repo | gh:owner/repo | https://host/owner/repo[.git] |
         git@host:owner/repo.git | git:NAME | PATH
sase project create VCS NAME [-a ALIAS]... [-c] [-d TEXT] [-j] [-m] [-n NAME]
                    [-O KEY=VALUE]... [-o OWNER] [-s | -S] [-v VISIBILITY] [-y]
    NAME may be owner/name;  `sase project create gh --help` lists provider options
sase project suggest [VCS] [-a] [-j] [-r]
```

| Option                    | Meaning                                                                                                                                                                            |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `-a, --alias`             | Project alias (repeatable). On `suggest`, `-a, --all` includes the hidden buckets.                                                                                                |
| `-c, --check`             | Read-only plan. Read-only network probes are allowed. Exit 0 = ready, 1 = blocked.                                                                                                 |
| `-j, --json`              | With `--check`: one plan document (§4.3.1). With `--yes`: NDJSON step events for live progress.                                                                                   |
| `-m, --make-current`      | Promote to current project on success.                                                                                                                                             |
| `-n, --name`              | Display name (`PROJECT_NAME`). Default: the repo name. The core allocator's collision suffix is shown in the plan.                                                                 |
| `-O, --option`            | Provider option, validated against the provider's declared schema.                                                                                                                 |
| `-o / -d / -v`            | Owner, description, and visibility: the only cross-provider options promoted to flags.                                                                                            |
| `-s, --setup / -S, --no-setup` | Mark the repo SASE-managed and chain init. Default **auto**: on for `create`; on for `add` of an unmanaged repo you can push to; connect-only for already-managed repos.      |
| `-y, --yes`               | Apply. Without it, a TTY gets a Rich preview and a `[y/N]` prompt; a non-TTY gets the plan and exit 1.                                                                             |
| `-r, --refresh`           | `suggest` only: bypass the TTL cache.                                                                                                                                              |

**Guards:**

- `create` refuses when `SASE_AGENT*` env is present unless
  `SASE_PROJECT_CREATE_BYPASS=<reason>`. Record this as a new decision, "Remote
  repository creation is human-only", modelled on `global-install-is-human-only`.
- `add` stays agent-callable. Agents can already do it with `#gh:` today.

#### 4.3.1 Plan document (shape mirrors `sase init --check --json`)

The point is that the review screen can reuse `init_plan_modal_rendering`.

```json
{
  "schema_version": 1,
  "status": "ready",
  "vcs": "gh",
  "ref": "sase-org/sase-forge",
  "project": {"key": "gh_sase-org__sase-forge", "name": "sase-forge",
              "aliases": [], "state": "enabled", "accent": "#5FD7AF"},
  "steps": [
    {"id": "create_remote", "op": "create", "label": "github.com/sase-org/sase-forge",
     "detail": "private · README · MIT · Python", "requires_tty": false},
    {"id": "clone", "op": "create", "label": "~/projects/github/sase-org/sase-forge/"},
    {"id": "register", "op": "create", "label": "gh_sase-org__sase-forge"},
    {"id": "manage", "op": "create", "label": "sase/sase.yml",
     "detail": "is_sase_managed: true · commit + push"},
    {"id": "init", "op": "validate", "label": "sase init -p gh_sase-org__sase-forge",
     "detail": "previewed after clone; sidecar creation needs a terminal",
     "requires_tty": true}
  ],
  "warnings": [], "blockers": [],
  "apply_argv": ["sase", "project", "create", "gh", "sase-org/sase-forge", "-v",
                 "private", "-O", "readme=true", "-O", "license=mit",
                 "-O", "gitignore=Python", "-s", "-y"]
}
```

**Step semantics:**

| Step            | On re-run                                                                                                                                                 |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `create_remote` | Adopts the repo if it exists and the step journal says this plan created it, or if it is empty and visibility matches. Otherwise it is a blocker.        |
| `clone`         | Adopts a matching existing clone.                                                                                                                          |
| `register`      | Reuses a record with the same `WORKSPACE_DIR`.                                                                                                             |
| `manage`        | A no-op if already managed.                                                                                                                                |
| `init`          | Delegated to the existing init flow.                                                                                                                       |

The journal lives at `~/.sase/projects/.create/<vcs>__<owner>__<name>.json`. It records
step outcomes and timestamps, and is removed on success.

### 4.4 Plugin contract (new hookspecs + dataclasses in `_hookspec.py`)

```python
@dataclass(frozen=True)
class RepoCreationForm:
    """Provider-declared options for creating a remote repository."""
    status: Literal["ok", "error"]
    provider_display: str = ""
    schema: Mapping[str, Any] = field(default_factory=dict)  # JSON Schema object;
        # x-sase-group: "basics"|"advanced"; x-sase-excludes: [...] for gh conflicts
    defaults: Mapping[str, Any] = field(default_factory=dict)
    error_kind: VcsRepoCandidateErrorKind | None = None      # auth/tool_missing/...
    message: str = ""

@dataclass(frozen=True)
class RepoProbe:
    """Read-only facts about one remote repository ref."""
    ref: str
    status: Literal["exists", "missing", "unavailable"]
    visibility: str = ""
    default_branch: str = ""
    is_empty: bool | None = None
    is_archived: bool = False
    can_push: bool | None = None
    sase_managed: bool | None = None   # gh: contents/sase/sase.yml → is_sase_managed
    message: str = ""

@dataclass(frozen=True)
class RepoCreateRequest:
    namespace: str
    name: str
    options: Mapping[str, Any]          # already validated against the schema

@dataclass(frozen=True)
class RepoCreateResult:
    ref: str
    web_url: str
    created: bool                       # False = adopted on a resumed run
    default_branch: str = ""

class WorkspaceHookSpec:
    @hookspec(firstresult=True)
    def ws_list_local_repo_candidates(self, workflow_type: str) -> VcsRepoCandidates | None:
        """Local clones in the provider's layout. Filesystem only; no network."""
    @hookspec(firstresult=True)
    def ws_probe_repo(self, workflow_type: str, ref: str) -> RepoProbe | None:
        """Read-only remote probe. Bounded network allowed; never on keystroke paths."""
    @hookspec(firstresult=True)
    def ws_describe_repo_creation(self, workflow_type: str, namespace: str) -> RepoCreationForm | None:
        """Schema for repo creation under *namespace* (enums may be namespace-specific)."""
    @hookspec(firstresult=True)
    def ws_create_repo(self, workflow_type: str, request: RepoCreateRequest) -> RepoCreateResult | None:
        """Create the remote repository. Side-effectful; only from an apply run."""
```

**sase-github implementation notes:**

- **`ws_describe_repo_creation`:**
  - Builds the schema from static knowledge of `gh repo create` plus a few lazy enums:
    - licenses: `gh repo license list`;
    - gitignore templates: `gh repo gitignore list`;
    - teams: `gh api orgs/{o}/teams`, org owners only;
    - `internal`: offered only if `gh api orgs/{o} --jq .plan.name` is enterprise.
  - Each enum is cached for the session.
  - The `x-sase-excludes` constraints mirror `create.go:163-187` exactly.
- **`ws_create_repo`:**
  - Runs `gh repo create OWNER/NAME --public|--private|--internal [-d] [-h]
    [--add-readme] [-g] [-l] [-p [--include-all-branches]] [-t] [--disable-issues]
    [--disable-wiki]`.
  - **No `--clone`.** SASE keeps one clone path (`clone_gh_repo`, now with a timeout).
  - Uses the existing conventions: `non_interactive_gh_env()`, `GH_HOST`,
    `stdin=DEVNULL`, a bounded timeout, and gh_cli error classifiers including
    `looks_like_already_exists_error` → adopt-on-resume.
  - **Default `--add-readme` on.** It guarantees a default branch and a non-empty clone.
    If the user turns it off with no template/license/gitignore, the plan warns that SASE
    will make the first commit during setup.
- **`ws_probe_repo`:** `gh repo view o/r --json
  visibility,defaultBranchRef,isEmpty,isArchived,viewerPermission`, plus the
  contents probe for `sase/sase.yml`.
- **`ws_list_local_repo_candidates`:** scans `~/projects/github/<owner>/<repo>/` one
  level deep. It keeps a dir only if:
  - it has `.git`;
  - its origin matches `<owner>/<repo>` on a configured host;
  - it is not a `_\d+` numbered copy.

  Results are tagged `owned` when the owner is in the namespaces, else `other`.

**Bare git implementation:**

- Local candidates are `~/.sase/repos/*.git` and `~/projects/git/*/` without a record,
  excluding `home` and numbered copies.
- `ws_create_repo` maps to the existing `init_bare_git_project` path. Its options are
  just name, plus optional bare dir and checkout dir under Advanced.

### 4.5 Candidate discovery and ranking

**Input** (assembled in Python, classified in Rust):

- namespaces from `ws_list_ref_namespaces`;
- remote entries per namespace from `fetch_repo_candidates`, served from cache first;
- local candidates;
- all project records, any state;
- the repo inventory: sidecar remotes, linked repos with their origins, and external
  opens with counts and recency.

**Identity:** `(host, owner.casefold(), repo.casefold())` from a URL, a ref, or a
provider path.

**Buckets, in order:**

1. `already_project`:
   - enabled → hidden, but searchable ("✓ already a project · enter to jump");
   - disabled → shown in a DISABLED PROJECTS group (enter = re-enable via the existing
     locked mutation).
2. `sidecar` → hidden. It matches if either:
   - the identity is an inventory sidecar remote; or
   - the name matches `^(.+)--[a-z0-9][a-z0-9-]*$`, since SASE reserves `--` for
     sidecars. This catches stale `bob-cli--*` and legacy `*--sdd` repos.
3. `archived` → hidden. `fork` → hidden behind `f`.
4. `linked` → the LINKED TO YOUR PROJECTS group, with the chip "linked by N projects".
5. `local_owned` → the ON THIS MACHINE group (the strongest signal).
   `local_other` (third-party clones) → hidden behind `.`.
6. Everything else → SUGGESTED.

**Ranking within a group:** external-open count, then last open, then `pushed_at`
descending, then name. A footer row states the hidden counts and the keys that reveal
them. Nothing disappears silently.

### 4.6 UX — Look and Flow

The visual language reuses the Admin Center's:

- teal modal frame, centered title, orange (`#FFAF5F`) active strips, bordered boxes
  with border titles, and `●`/`○` state glyphs;
- the init preview's `+ ~ − ●` glyphs;
- the **project accent palette**: the new project's accent is computed with
  `project_accent(key, among=…)` and shown as a swatch, then used on the Ready screen.

**Entry points (v1):**

- `n` on the Projects sub-tab;
- the command palette entry **New project…**;
- an empty-state card in the Projects list ("No projects yet — press `n` to add one").

#### Stage 1 — Source

```
╭──────────────────────────────── New Project ─────────────────────────────────╮
│                   ● Source ──────── ○ Details ──────── ○ Review              │
│                                                                              │
│   GITHUB   Git (local)                         ✓ gh · bbugyi200 · 3 owners   │
│ ╭──────────────────────────────────────────────────────────────────────────╮ │
│ │ ⌕  Filter — or paste owner/repo, a GitHub URL, or a local path           │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
│ ╭─ Repositories ───────────────────────────────────────── cached 2m · R ───╮ │
│ │ ✚  Create a new GitHub repository…                                    n  │ │
│ │ ON THIS MACHINE                                                          │ │
│ │ ⌂  bbugyi200/dotfiles         public    1d    cloned · not a project     │ │
│ │ ⌂  bbugyi200/bugyi-chops      public    8d    opened by agents in sase   │ │
│ │ SUGGESTED   bbugyi200 · sase-org · bobs-org                              │ │
│ │ ○  bobs-org/bob-plugins       public    4h    bob | Plugins Monorepo     │ │
│ │ ○  bobs-org/bob               private   4h    Bugyi's Obsidian           │ │
│ │ ○  bbugyi200/job              private   6h                               │ │
│ │ ○  sase-org/sase-android      private   5mo   sase - Android App         │ │
│ │ LINKED TO YOUR PROJECTS                                                  │ │
│ │ ⇄  sase-org/sase-core         public    0d    linked by 3 projects       │ │
│ │ ┄  26 sidecars · 24 forks · 3 projects hidden          f forks · . all   │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
│ ╭─ bobs-org/bob-plugins ───────────────────────────────────────────────────╮ │
│ │ bob (Bugyi's Obsidian) | Plugins Monorepo                                │ │
│ │ public · main · pushed 4h ago · you can push                             │ │
│ │ Checkout  ~/projects/github/bobs-org/bob-plugins/            will clone  │ │
│ │ Project   bob-plugins   key gh_bobs-org__bob-plugins   ■ accent          │ │
│ │ SASE      ✓ already SASE-managed — sidecars connect on first launch      │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
│  enter add · n new repo · [ ] vcs · / filter · f forks · R refresh · esc     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Behaviours:**

- **The VCS strip is the A1 prompt.** Each tab carries a health chip: `✓ gh · login` or
  `⚠ not signed in`.
- **Loading.** Rows stream in per owner. A never-fetched owner shows a dim
  `◌ fetching bobs-org…` row in place. A failed owner shows
  `⚠ bobs-org: gh auth expired — t to run gh auth login` while its cached rows stay
  visible.
- **The detail box** fills from `ws_peek_ref` (local, instant) and then `ws_probe_repo`
  (debounced 150ms on highlight, off-thread, cached per ref). `SASE` reads
  `◌ checking…` → `✓ managed` / `○ not yet — will be set up` / `? unknown`.
- **Paste-anything.** A ref, URL or path that parses becomes a synthetic top row
  (`↵ Add sase-org/foo`). An unparseable path is a dim hint.
- **Empty states:**
  - **No `github_orgs`:** a card says "Tell SASE which GitHub owners are yours". Its
    action is "add `bbugyi200` (your gh login)", written through the Config Center's
    config-edit path.
  - **No gh:** the tab is disabled with an install hint, and `Git (local)` still works.

#### Stage 2a — Details (existing repo)

```
╭──────────────────────────────── New Project ─────────────────────────────────╮
│                   ✓ Source ──────── ● Details ──────── ○ Review              │
│  ADD  bobs-org/bob                       private · main · pushed 4h ago      │
│ ╭─ Project ────────────────────────────────────────────────────────────────╮ │
│ │ Name       bob                                    ✓ unique               │ │
│ │ Aliases    —                                                             │ │
│ │ Key        gh_bobs-org__bob                       derived                │ │
│ │ Checkout   ~/projects/github/bobs-org/bob/        will clone             │ │
│ │ State      ● enabled                                                     │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
│ ╭─ SASE setup ─────────────────────────────────────────────────────────────╮ │
│ │ [x] Make bob SASE-managed and initialize it                recommended   │ │
│ │     Needed before agents can launch here. Commits and pushes             │ │
│ │     sase/sase.yml + AGENTS.md to main; then creates public sidecars      │ │
│ │     bob--plans · bob--research · bob--beads (you confirm in a terminal). │ │
│ │ [ ] Make it the current project when done                                │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
│  tab next · space toggle · enter edit · y review · b back · esc cancel       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

- Without push rights (`can_push=false`), setup is unchecked and the box turns amber:
  "Agents can't launch into an unmanaged GitHub repo. Ask an owner to add
  `sase/sase.yml`."
- For an already-managed repo, the box collapses to a single line:
  `✓ already SASE-managed — sidecars connect on first launch`.

#### Stage 2b — Details (new repo, plugin-declared property sheet)

```
╭──────────────────────────────── New Project ─────────────────────────────────╮
│                   ✓ Source ──────── ● Details ──────── ○ Review              │
│  CREATE  a new GitHub repository                                             │
│ ╭─ Repository ─────────────────────────────────────────── GitHub options ──╮ │
│ │ BASICS                                                                   │ │
│ │ ▸ Owner         sase-org                    ▾    you can create here     │ │
│ │   Name          sase forge  →  sase-forge        ✓ available             │ │
│ │   Description   Forge for SASE plugin scaffolds                          │ │
│ │   Visibility    ( ) Public  (•) Private  ( ) Internal  enterprise only   │ │
│ │   README        [x] Initialize with a README                             │ │
│ │   .gitignore    Python                      ▾                            │ │
│ │   License       MIT License                 ▾                            │ │
│ │ ADVANCED · 6                                                  a expand   │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
│ ╭─ Project ────────────────────────────────────────────────────────────────╮ │
│ │ Name  sase-forge   key gh_sase-org__sase-forge   ● enabled   ■ accent    │ │
│ │ [x] Set up SASE in the new repo (managed + sidecars)                     │ │
│ ╰──────────────────────────────────────────────────────────────────────────╯ │
│  j/k field · enter edit · space toggle · a advanced · y review · b back      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Expanded Advanced section.** Conflicting rows render dim with the reason, and
choosing a Template greys out README, .gitignore, License and Team live:

```
│ │ ADVANCED                                                                 │ │
│ │   Template      —            owner/repo · replaces README/.gitignore/…   │ │
│ │   All branches  [ ]          only with a template                        │ │
│ │   Homepage      —                                                        │ │
│ │   Team          —           ▾ org owners only                            │ │
│ │   Issues        [x] on                                                   │ │
│ │   Wiki          [x] on                                                   │ │
```

**Live checks:**

- name normalization preview (`sase forge → sase-forge`, matching gh);
- availability (`gh repo view`, debounced 300ms, off-thread);
- SASE key, name and alias uniqueness through the core validator;
- local checkout path collision.

**Delight: a taken name becomes "add it instead."** `✗ sase-org/sase-forge exists —
enter to add it instead` jumps to Stage 2a for that repo.

#### Stage 3 — Review (the init preview's vocabulary)

```
╭─────────────────────────── Review · Create sase-forge ───────────────────────╮
│                   ✓ Source ──────── ✓ Details ──────── ● Review              │
│                                                                              │
│  REMOTE   +  github.com/sase-org/sase-forge   private · README · MIT · Python│
│  LOCAL    +  clone → ~/projects/github/sase-org/sase-forge/                  │
│  PROJECT  +  sase-forge  (gh_sase-org__sase-forge)   ● enabled   ■           │
│  SASE     +  sase/sase.yml  is_sase_managed: true              commit + push │
│           ●  then the initialization preview (memory, repos, skills…)        │
│              sidecar creation asks in a terminal                             │
│                                                                              │
│  ⚠ Creates a repository on github.com. A failed later step keeps it;         │
│    retrying resumes from the first incomplete step.                          │
│ ──────────────────────────────────────────────────────────────────────────── │
│  $ sase project create gh sase-org/sase-forge -v private                     │
│      -d 'Forge for SASE plugin scaffolds' -O readme=true -O license=mit      │
│      -O gitignore=Python -s -y                                               │
│                                                                              │
│              [ Create  y ]      [ Back  b ]      [ Cancel  esc ]             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

- **Remote creation is styled as a danger confirm** (as `init_plan_modal` does for
  overwrites).
- **"Add existing" omits the REMOTE line.** With a neutral confirm, the whole thing
  usually completes in about 2 seconds.

#### Stage 4 — Progress → init preview → Ready

The NDJSON step events from the apply proc drive a live checklist:

```
│  ✓ Created github.com/sase-org/sase-forge                            1.1s    │
│  ✓ Cloned ~/projects/github/sase-org/sase-forge/                     0.9s    │
│  ✓ Registered sase-forge · ● enabled                                 0.0s    │
│  ⠹ Marking SASE-managed (sase/sase.yml → main)…                              │
│  ○ Initialize                                                                │
│                                      also in Admin Center → Procs            │
```

With setup on, the modal then submits the **existing** init check for the new key and
shows the **existing** init preview: per-planner rows, diffs on `d`, and `t` for the
sidecar TTY prompts. When init completes:

```
╭──────────────────────────────── sase-forge ──────────────────────────────────╮
│                                                                              │
│                        ✓  sase-forge is ready              (in its accent)   │
│                github.com/sase-org/sase-forge  ·  ● enabled                  │
│                                                                              │
│        +  launch an agent in +sase-forge        c  make current              │
│        enter  show it in Projects               esc  close                   │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Failure keeps context and offers the next move:**

```
│  ✓ Created github.com/sase-org/sase-forge                            1.1s    │
│  ✗ Clone failed — ssh: Permission denied (publickey); https: auth required   │
│      hint: run `gh auth setup-git`, then retry                               │
│  ○ Register project                                                          │
│                                                                              │
│  The repository exists on GitHub and was kept.                               │
│        r retry (resumes at clone) · t terminal · b back · esc close          │
```

### 4.7 Keys

| Where           | Keys                                                                                                                                                                          |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Projects pane   | **`n` new project.** New `ace.keymaps.projects.new_project: "n"`, added to `ProjectsPaneKeymaps` and `_PROJECT_ONLY_ACTIONS`.                                               |
| Source          | `j/k` move · `enter` add · `n` new repo · `[`/`]` VCS · `/` filter · `f` forks · `.` show all hidden · `R` refresh · `t` terminal (gh auth) · `esc` cancel                    |
| Details         | `tab`/`j/k` field · `enter` edit cell · `space` toggle · `a` advanced · `y` review · `b` back · `esc` cancel                                                                  |
| Review          | `y` create/add · `b` back · `esc` cancel. Unlike the init preview, `n` is **not** cancel, to avoid a clash with "new".                                                       |
| Progress / Done | `r` retry · `t` terminal · `+` launch in project · `c` make current · `enter` show in Projects · `esc` close                                                                  |

**Hints row.** Lead with `n new`. Either wrap the hints into two rows or adopt
priority truncation, so the most valuable keys survive at 120 columns.

### 4.8 Reliability: failure matrix

| Failure                                                 | Detected by                                                    | Behaviour                                                                                                                                                                                |
| ------------------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `gh` missing                                            | `error_kind=tool_missing`                                      | GitHub tab disabled with an install hint. Git (local) still works.                                                                                                                       |
| `gh` not authenticated                                  | `auth`                                                         | Card plus `t` → `gh auth login` in a suspended terminal, then auto-refresh.                                                                                                             |
| One owner fails (network / rate limit)                  | per-namespace result                                           | Stale cached rows plus a `⚠` badge for that owner. Other owners are unaffected.                                                                                                          |
| No create rights in the org                             | describe/probe (`members_can_create_*`, `viewerPermission`)    | The owner row shows `⚠ can't create here` and the Review button is disabled.                                                                                                             |
| Name invalid or taken                                   | local rules + probe                                            | Inline normalization. Taken → "add it instead".                                                                                                                                         |
| SASE name/alias/key collision                           | core validator (same rules as `allocate_project_name`)         | Inline `✗` with the allocator's suggestion.                                                                                                                                             |
| Checkout dir exists                                     | plugin                                                         | Matching origin → "adopt clone" (no re-clone). Anything else → a blocker naming the path.                                                                                               |
| Remote created, then clone/register fails               | step journal                                                   | Keep the remote, show the error tail and a hint. `r` re-runs the same argv, which adopts and resumes.                                                                                   |
| Clone hangs                                             | **new timeout** in `clone_gh_repo` (side finding #2)           | Step fails with a timeout; retry is available.                                                                                                                                           |
| Two creators race (two TUIs, or TUI + agent `#gh:`)     | `patch_lock` + re-check record by `WORKSPACE_DIR`              | The loser adopts the winner's record.                                                                                                                                                    |
| Sidecar creation needs a human                          | init plan `requires_tty`                                       | The existing `t` valve.                                                                                                                                                                  |
| Admin Center / TUI closed mid-run                       | durable proc                                                   | The proc finishes and records its outcome. The Projects pane shows the project on next load. An incomplete journal surfaces a "Resume setup of sase-forge" row on the next `n`.          |
| Repo is already a disabled project                      | classification                                                 | DISABLED PROJECTS group. Enter re-enables through `set_project_state_locked`.                                                                                                           |

### 4.9 Performance (maps to the `tui_perf` rules)

- **Rules 1, 2, 4.** Every gh call, file scan, probe and classification runs in
  `run_worker(thread=True)`, and results marshal back with `call_from_thread`. After
  each result lands, re-read the highlighted ref before painting the detail box.
- **Rule 3.** The apply runs as one durable session proc
  (`_submit_session_worker`, as in init).
- **Rule 7.** Detail and probe updates go through `DetailPanelDebouncer`. The highlight
  never waits.
- **Rule 10.** Use the existing 600s TTL cache. `R` force-refreshes. Never poll while
  the modal is idle.
- **Rule 11.** Filter typing is pure in-memory filtering. Paste-anything parsing is
  local. `resolve_ref` and `create_repo` run **only** inside the apply proc. All
  subprocesses use `GH_PROMPT_DISABLED=1`, `GIT_TERMINAL_PROMPT=0` and
  `stdin=DEVNULL`.
- **Rule 12.** Programmatic highlight changes in the source list use the established
  guard pattern.

### 4.10 Safety

- `create` is human-only (§4.3 guard).
- The sidecar TTY invariant is unchanged.
- Remote repos are never deleted.
- Commits and pushes to an existing repo appear on Details **and** Review, with the
  branch named.
- `ws_probe_repo` and `ws_list_local_repo_candidates` must be declared read-only, with
  tests that assert no write and no clone (mirroring the `ws_peek_ref` tests).

---

## 5. Alternatives Considered

| Alternative                                                                                   | Why not (as the main answer)                                                                                                                                                                                   |
| --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Improve `#gh:` completion only.** Owners and repos already complete in the prompt.          | Still conflates registration with launch. Still no preview, no new-repo creation, no setup. Good as a complement; keep it.                                                                                      |
| **Suspend into interactive `gh repo create`, then `#gh:`.**                                   | Cheap, but ugly and two-tool. Loses SASE naming and setup, and gives no resumability.                                                                                                                          |
| **TUI-only implementation** (call hooks directly from the modal)                              | Violates the Rust/CLI boundary litmus test. Telegram, the mobile gateway and editors couldn't match it, and it's harder to test.                                                                               |
| **Hard-code a GitHub form in sase core**                                                      | Breaks the plugin architecture. A GitLab plugin (the `#gl:` golden vectors in `vcs_repo_completion.py` hint at one) would need core changes.                                                                   |
| **Treat the TUI confirm as sidecar authorization** (no terminal valve)                        | Nicer UX, but it supersedes part of a deliberate invariant: any flag the TUI passes is forgeable by an agent. If you want it, write a decision record first (open question Q1).                                 |
| **An agent-driven "create project" skill**                                                    | Slow, non-deterministic, and agents shouldn't mint remote repos.                                                                                                                                               |

---

## 6. Phased Delivery

| Phase                              | Contents                                                                                                                                                                                                                                                                                                                                                                                                                     | Value                                                                                        |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **P0: hygiene** (small, independent) | Clone timeout; `projects_base()` honours `sase_projects_dir()`; host check in `ws_detect_workflow_type`; fix the stale `github_orgs` docs; fix Projects hints-row overflow.                                                                                                                                                                                                                                                   | Removes reliability traps the wizard would hit.                                              |
| **P1: add existing**               | sase-core `classify_project_candidates` and `validate_new_project_identity` + binding (move the `sase-core-revision.txt` pin). Hooks `ws_list_local_repo_candidates` and `ws_probe_repo` (gh + bare git). `sase project add` / `suggest` with plan, journal and NDJSON. TUI modal stages 1, 2a, 3 and 4 with init chaining. Keymap, help modal, docs.                                                                          | Covers the common case: your ~75 addable remote repos (not sidecars, forks, linked repos, or existing projects), plus local clones.               |
| **P2: create new**                 | Hooks `ws_describe_repo_creation` and `ws_create_repo` (sase-github via `gh repo create`; bare git via `init_bare_git_project`). `sase project create` with the human-only guard and a decision record. TUI stage 2b on `SchemaObjectForm`.                                                                                                                                                                                  | The "start something new" story.                                                            |
| **P3: delight**                    | Bulk add with marks; `＋ New project…` in the `+` launch picker; "publish a local directory" (`--source --push`); template browser (`isTemplate` repos); optional "also register on apollo/mac" via fleet dispatch.                                                                                                                                                                                                         | Polish.                                                                                      |

---

## 7. Test Strategy

- **Pure models, no Textual:**
  - wizard state machine, transitions and back-navigation;
  - source rows and footer counts;
  - property-sheet conflicts (one case per `create.go:163-187` rule);
  - review rows from plan JSON.

  This follows the `axe_entry_sheet.py` and `projects_pane_init.py` precedent.
- **sase-core:** classification table tests. Cover a sidecar by inventory, a sidecar by
  `--`, a stale sidecar in the wrong owner, a fork, an archived repo, a numbered clone,
  a disabled project, a linked repo, and case-folding.
- **CLI:** a golden `--check --json` per scenario; an NDJSON event sequence; a resume
  after an injected failure at each step; and the agent-env refusal for `create`.
- **Plugins:**
  - argv-exact `gh repo create` tests in the style of
    `test_workspace_plugin.py:1161-1212`;
  - an error-kind table;
  - a "probe/local-candidates never write" test;
  - hookspec argument-name pins.

  Never call live `gh`. Use a fake `gh` on `PATH` for integration.
- **TUI:**
  - PNG visual goldens for each stage, including empty, loading, error and Ready (with
    fixture-controlled data), via `just fix-tui-screenshots`;
  - a perf guard: typing in the filter spawns no subprocess (patch `subprocess.run` to
    raise).

---

## 8. Touchpoints Checklist

- `src/sase/default_config.yml` (`ace.keymaps.projects.new_project`). This is required
  by the "Default Keymap Config" gotcha.
- `keymaps/app_keymaps.py`, the bindings builder, and the help modal. `src/sase/ace/CLAUDE.md`
  requires help-popup sync, and the footer rules apply if any key is conditional.
- **Docs to update:**
  - `docs/ace.md`: Projects tab table plus a new "Add or create a project" subsection;
  - `docs/project_spec.md`;
  - `docs/workspace.md:13-15`: "# refs are the way to create projects" becomes stale;
  - `docs/plugins.md`: new hooks;
  - the CLI reference;
  - the sase-github README and configuration docs.
- **Memory:** the glossary strand `glossary:sase_project` says projects are created
  "only when a new VCS macro argument resolves". The implementing plan should carry a
  memory decision for that strand (per `/sase_memory_write` routing). I have not edited
  it.
- **Decision records:**
  - new: **"Remote repository creation is human-only"**;
  - if Q1 goes the other way, a superseding record for the sidecar TTY rule.
- `sase-core-revision.txt` pin bump for the new binding (memory: Rust Core Backend
  Boundary).

---

## 9. Open Questions for You

1. **Sidecar authorization.** Keep the `t` terminal valve for sidecar creation (my
   recommendation for v1), or should a resource-naming TUI confirm count as the "fresh
   interactive y"? The latter needs a decision record, and any TUI-passed flag is
   forgeable.
2. **First-time visibility default.** Private (safe; my pick) or Public (your norm, and
   what sidecars use)? Either way it's remembered per owner afterwards.
3. **Setup for existing unmanaged repos.** Should setup default ON when you can push? It
   commits to someone's main branch, which matters for shared org repos. I recommend ON
   with the disclosure shown, and OFF without push rights.
4. **Agents.** Should `sase project add` remain agent-callable? I say yes (parity with
   `#gh:`). `create` should not be.
5. **Fleet.** Should the Ready screen offer "also register on apollo / mac"? I'd keep it
   out of v1.

---

## 10. Recommended Solution

Build a **CLI-backed, plugin-declared, three-stage "New Project" modal** in Admin Center
→ Projects:

1. **CLI is the source of truth.**
   - Commands: `sase project add REF`, `sase project create VCS NAME`, and
     `sase project suggest`.
   - Each has a `-c/--check -j/--json` plan (reusing the init plan vocabulary) and an
     idempotent, journaled, resumable `-y/--yes` apply that streams NDJSON progress.
   - `create` is human-only. New projects are implicitly enabled; disabled matches
     re-enable instead of duplicating.
2. **Providers own provider behaviour.** Four new `ws_*` hooks:
   - `ws_list_local_repo_candidates`;
   - `ws_probe_repo`;
   - `ws_describe_repo_creation`, a JSON Schema with basics/advanced groups and gh's
     real conflict rules;
   - `ws_create_repo`, which in sase-github runs `gh repo create` with no `--clone`, a
     README by default, adopt-on-resume, and bounded timeouts.

   These sit on top of the existing `ws_list_ref_namespaces`, `ws_list_repo_candidates`
   (with its 10-minute cache), `ws_peek_ref` and `ws_resolve_ref`.
3. **Core owns shared rules.** A pure `classify_project_candidates` and
   `validate_new_project_identity` in sase-core, so every frontend agrees on what
   "likely to add" means: sidecars, forks, archived repos, numbered copies and existing
   projects are filtered or grouped, and the counts are always shown.
4. **The TUI is the beautiful frontend.**
   - `n` opens **Source** (VCS tab strip, paste-anything filter, ranked groups with a
     live detail card).
   - Then **Details**: a project identity card; or, for a new repo, the
     `SchemaObjectForm` property sheet with live name, availability and collision
     checks.
   - Then **Review**: exact argv and init-style glyphs.
   - The durable proc's checklist hands off to the **existing init preview** for SASE
     setup, with the `t` terminal valve for sidecars.
   - It ends on a **Ready** screen in the project's own accent with `+` to launch the
     first agent.
5. **Ship in order:**
   - **P0** hygiene fixes;
   - **P1** "add existing", which covers most of the value;
   - **P2** "create new";
   - **P3** delighters (bulk add, the launch-picker entry, publishing a local directory,
     templates, fleet).
