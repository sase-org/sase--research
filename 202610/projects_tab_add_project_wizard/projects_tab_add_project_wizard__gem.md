# Research Report: Project Creation & Onboarding in SASE Admin Center

**Author:** `research.49.gem` (Gemini Research Agent)  
**Date:** 2026-10-11  
**Target Component:** SASE Admin Center (`#` modal) → Projects Tab (`ProjectsPane`)  
**Status:** Complete Design & Architecture Evaluation  

---

## 1. Executive Summary

This report evaluates and designs the feature to add project creation support to the "Projects" tab of the SASE Admin Center (`src/sase/ace/tui/modals/projects_pane.py`).

### Key Conclusions:
1. **Core Concept Value:** Adding project creation to the Admin Center is an essential and overdue improvement. Currently, the Projects tab is strictly an inspection and maintenance surface (enable, disable, mark, delete, aliases, edit spec, init). Projects are otherwise created only through implicit prompt magic (e.g. `#gh(owner/repo)` auto-cloning during an agent turn), manual file creation in `~/.sase/projects/`, or low-level CLI commands. A first-class, interactive creation workflow establishes the Admin Center as the true operational hub of SASE.
2. **Crucial Plan Critique:** The original proposal combines two fundamentally distinct user operations into a single ambiguous "create" flow:
   - **Path A: Importing / Adopting an existing repository** (e.g., from configured GitHub organizations).
   - **Path B: Greenfield provisioning of a brand new repository from scratch** (e.g., executing `gh repo create` remotely, cloning locally, and scaffolding).
   Conflating these, along with attempting to replicate *all* 15+ options of `gh repo create` (licenses, gitignore templates, teams, wikis, webhooks) in a terminal TUI, risks creating a brittle, cluttered, and frustrating form.
3. **Recommended Solution:** A unified, keyboard-first, three-step **New Project Wizard Modal (`NewProjectWizardModal`)** triggered by the unmapped `n` key on the Projects tab:
   - **Step 1 (Source & VCS Selection):** Choose between **Import Existing Repository** and **Create Greenfield Repository**, with smart VCS defaulting (pre-selecting `GitHub` when `sase-github` is active, or offering `Git (bare/local)`).
   - **Step 2A (Import Flow):** Filterable, paginated candidate list grouped by configured GitHub organization (leveraging existing `ws_list_repo_candidates` hook), excluding already-registered projects, with a rich preview pane.
   - **Step 2B (Create Flow):** A streamlined, high-aesthetic form capturing the core 80/20 fields (Owner/Org, Name, Visibility, Description, README/Gitignore toggles) with an escape-hatch to launch interactive `gh repo create` if exhaustive options are needed.
   - **Step 3 (Provisioning & Progress):** An off-thread, non-blocking execution worker displaying a live progress checklist (Create remote → Clone locally → Write ProjectSpec → Setup SDD sidecar → Refresh Admin Center).
4. **Backend Parity:** The capability must not be hardcoded into Textual TUI code. In accordance with SASE architectural rules (litmus test for backend domain logic), the engine must be implemented in the VCS workspace hook system (`WorkspaceHookSpec`) with full CLI parity via `sase project create` and `sase project add`.

---

## 2. Current Architecture of SASE Project Lifecycle

To design a clean implementation, we must understand how projects exist, resolve, and render across SASE today.

```
                      ┌──────────────────────────────────────────────┐
                      │              SASE Admin Center               │
                      │   (ConfigCenterModal / ProjectsPane)        │
                      └──────────────────────┬───────────────────────┘
                                             │
                       Key 'n' triggers NewProjectWizardModal
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │          SASE Workspace Provider             │
                      │             Plugin Hook Manager              │
                      └──────────────┬────────────────┬──────────────┘
                                     │                │
                                     ▼                ▼
                     ┌──────────────────┐    ┌──────────────────┐
                     │   sase-github    │    │bare_git_workspace│
                     │  (GitHub / gh)   │    │  (Bare/Local Git)│
                     └─────────┬────────┘    └────────┬─────────┘
                               │                      │
                               ▼                      ▼
                     ┌──────────────────────────────────────────┐
                     │          Local Filesystem State          │
                     │  1. Primary Clone: ~/projects/...        │
                     │  2. Spec: ~/.sase/projects/<key>/<key>.sase│
                     │  3. Logging: ~/.sase/logs/project_creation│
                     └──────────────────────────────────────────┘
```

### 2.1 Project Storage & Representation
- **Project Directory:** Every SASE project lives under `~/.sase/projects/<project_key>/`.
- **Project Spec File:** The canonical file is `<project_key>.sase` (e.g. `gh_sase-org__sase.sase` or `actstat.sase`). Legacy `.gp` files are supported but deprecated.
- **Spec Format:** Simple key-value text format:
  ```text
  WORKSPACE_DIR: /home/bryan/projects/github/sase-org/sase/
  PROJECT_NAME: sase
  PROJECT_STATE: enabled
  ```
  *(Plus active agent claim entries under `RUNNING:`)*.
- **Naming Conventions:**
  - GitHub projects use the canonical directory key: `gh_<owner>__<repo>` (e.g., `gh_sase-org__sase`, `gh_bbugyi200__actstat`).
  - Bare Git projects use the project name directly (e.g., `my-tool`).
  - Aliases and display names are allocated via `ensure_useful_repo_name()` and `allocate_project_name()` so users interact with human-friendly names (e.g. `sase` instead of `gh_sase-org__sase`).

### 2.2 The Rust Core Boundary (`sase-core`)
- Project discovery and lifecycle evaluation are owned by Rust core (`sase_core::project_spec`).
- Rust parses `.sase` content, extracts `vcs_kind` (`"gh"` if key starts with `gh_<owner>__<repo>`, `"git"` if `BARE_REPO_DIR` is present), computes claim counts, and returns `ProjectRecordWire` across the C/Python boundary (`sase_core_rs`).
- `list_project_records(projects_root, state_filter)` is the authoritative query API.
- Rule 1.3 Litmus Test: Shared backend and domain behavior must belong in core logic/facade, not buried in presentation Textual classes.

### 2.3 The Admin Center Projects Pane (`ProjectsPane`)
- Hosted in `src/sase/ace/tui/modals/projects_pane.py` under the Admin Center modal (`#`).
- Contains three sub-tabs:
  1. `Projects`: Displays all true SASE projects with status badges, VCS indicator, active claims, workspace paths, and inventory counts.
  2. `Repos`: Displays repository inventory (primary, sidecar, linked, external).
  3. `Workspaces`: Displays numbered workspace checkouts.
- **Current Keybindings in `ProjectsPaneKeymaps`:**
  - Navigation: `j`/`k` (next/prev), `/` (filter), `'` (jump hint).
  - Actions: `a` (enable), `d` (disable), `ctrl+d` (delete), `e` (edit spec in editor), `A` (edit aliases), `c` (set current), `i` (init), `I` (init all), `m` (mark), `u` (unmark).
  - **Notable Finding:** Bare `n` is **completely unmapped** in `ProjectsPaneKeymaps` (only `ctrl+n` is mapped as an alias for `next_option`). `n` is the universal convention for "New" across terminal applications.

### 2.4 Existing VCS Provider Hooks
SASE uses `pluggy` with `WorkspaceHookSpec` (`src/sase/workspace_provider/_hookspec.py`):
- `ws_get_workflow_metadata`: Returns `WorkflowMetadata` (`workflow_type="gh"`, `vcs_provider_name="github"`).
- `ws_list_ref_namespaces`: Returns known owner namespaces (e.g., GitHub orgs configured in `github_orgs`).
- `ws_list_repo_candidates(workflow_type, namespace)`: Already implemented in `sase-github`! It invokes `gh repo list <namespace> --json name,description,visibility,isArchived,isFork,pushedAt` to return candidates.
- `ws_resolve_ref(ref, workflow_type)`: In `sase-github`, if a repo isn't locally cloned, it clones it to `~/projects/github/<owner>/<repo>/` and creates the `.sase` project file automatically.
- **Gap:** There is currently **no hook** for provisioning a greenfield remote repository (`ws_create_remote_repo`) or prompting for creation options.

---

## 3. Comprehensive Critique of the Proposed Plan

### 3.1 Is adding project creation to the Admin Center a good idea?
**Verdict: Strong YES, with architectural refinements.**

- **Why it is necessary:**
  Currently, onboarding a project into SASE requires either:
  1. Mentioning a ref in an agent prompt (e.g. `sase run "#gh(my-org/my-repo) do X"`), which triggers auto-cloning as a side-effect of prompt resolution.
  2. Manually creating directories in `~/.sase/projects/` and editing `.sase` specs.
  3. Running `sase workspace` low-level commands.
  This makes project setup feel opaque. Adding a visual creation/import entry point directly in the Admin Center Projects tab bridges the gap between project administration and project onboarding.

### 3.2 Critique 1: Conflation of "Importing Existing" vs "Greenfield Creation"
The prompt specifies:
> "The user should be prompted to select what VCS they want... It should then prompt them to select from a menu that includes projects that the user is likely to add... The user should also have the option to create a new project from scratch..."

**The Problem:**
Importing an existing repository and creating a brand new repository from scratch are fundamentally different user intents:
- **Importing:** The remote repository already exists. The user needs to search/select from a list of existing repositories, verify the local destination clone path, and generate the SASE ProjectSpec.
- **Greenfield Creation:** The repository does not exist anywhere. The user must provide a new name, choose organization ownership, choose visibility (public/private), decide on scaffolding (README, .gitignore, license), create the remote repository via API/CLI, clone it locally, and generate the SASE ProjectSpec.

**The Solution:**
Do not cram both into a single linear form. The wizard should clearly fork at Step 1:
```
[1] Select Workflow:
    (●) Import Existing Repository   (Quickly add an existing GitHub or local repo)
    (○) Create Brand New Repository  (Provision a new repo on GitHub or local Git)
```

### 3.3 Critique 2: The "Prompt for ALL VCS Options" Anti-pattern
The prompt specifies:
> "If creating a new repo, make sure we prompt the user for all of the same options supported by the VCS provider (e.g. public/private, GitHub repo description, etc...)."

**The Problem:**
Let us review what `gh repo create` actually supports:
- `--public`, `--private`, `--internal` (visibility)
- `--description` (text)
- `--add-readme` (boolean)
- `--gitignore` (string: requires choosing from ~100 official GitHub gitignore templates)
- `--license` (string: requires choosing from ~60 SPDX licenses)
- `--template` (string: repository template)
- `--team` (string: organization team permissions)
- `--homepage` (string: URL)
- `--disable-issues`, `--disable-wiki` (booleans)
- `--source`, `--remote`, `--push` (migration flags)

Attempting to build a terminal TUI form with 10+ widgets for all these flags violates SASE TUI design principles and usability best practices:
1. **Visual Clutter:** A 10-field form in Textual on standard 80x24 or 120x40 terminals produces an overwhelming wall of inputs requiring vertical scrolling.
2. **Network Latency & Fragility:** Fetching 100+ gitignore templates and license options over the GitHub API just to populate dropdowns adds latency and failure points.
3. **Diminishing Returns:** In 95% of software engineering cases, developers creating a new repository want:
   - Name
   - Owner/Org
   - Visibility (Private vs Public)
   - Description
   - Initialize with README / gitignore
4. **Tool Integrity:** If an exotic option is required (like adding specific team permissions or repository templates), forcing the user through a half-baked TUI recreation of GitHub's web interface is inferior to providing an escape hatch.

**The Solution: The 80/20 Rule with an Advanced Escape Hatch**
- Provide a clean, beautiful, focused form for the 5 essential fields:
  1. **Owner/Namespace** (Select from user account or configured orgs)
  2. **Repository Name** (Validated slug)
  3. **Visibility** (Pill selector: `[ Private ]` (default) | `[ Public ]` | `[ Internal ]`)
  4. **Description** (Optional one-line text)
  5. **Scaffolding Options** (Checkboxes: `[✓] Add README`, `[✓] Add .gitignore [Python/Rust/Node/Go/None]`, `[ ] Add MIT License`)
- Provide an action/button: `[Open Interactive gh in Terminal]` using Textual's `app.suspend()` for users who need custom team permissions or complex template setups.

### 3.4 Critique 3: Forced VCS Selection Step vs Smart Auto-Detection
The prompt specifies:
> "The user should be prompted to select what VCS they want their project to use."

**The Problem:**
In standard SASE installations, `sase-github` is the predominant provider. For users working purely with GitHub, asking them every single time "Choose VCS: [GitHub] [Bare Git]" introduces unnecessary modal friction. Furthermore, what if the user wants to add an existing *local directory* that is already a Git repository on their disk?

**The Solution:**
Present a smart selector:
- If only one VCS plugin is active (or if `github_orgs` is configured), default to `GitHub` while allowing quick switching with Tab or Arrow keys.
- Add **Local Git Directory** as a first-class choice alongside GitHub and Bare Git.

### 3.5 Critique 4: TUI Performance & Network Realities (TUI Perf Rules)
According to SASE core rules (`tui_perf.md`):
- *Rule 1 & 2:* Heavy work must run off the event loop (`run_worker(..., thread=True)`).
- *Rule 11:* Keystroke paths must be read-only, non-blocking, and prompt-free.
- *Rule 7:* Debounce detail panels (150 ms).

**The Risks:**
1. **Synchronous Network Calls:** If the modal calls `gh repo list` or `gh repo create` on the UI thread, the entire Textual interface freezes, dropping user keypresses.
2. **Credential Prompts:** If `git clone` or `gh` triggers an interactive prompt for username/password, the terminal TUI freezes permanently as the subshell waits on stdin. All subcommands must use `non_interactive_gh_env()` and `non_interactive_git_env()` with `stdin=subprocess.DEVNULL`.
3. **Multiple Organizations:** If a user has 4 configured orgs, fetching repos sequentially would take 5–10 seconds. Repo candidates must be fetched asynchronously per org with caching.
4. **Auth Failure Handling:** If `gh auth login` has expired or the token lacks scopes, the modal must not crash or display an ugly stack trace. It must present a clear, actionable diagnostic badge: `Authentication required: Run 'gh auth login'`.

### 3.6 Critique 5: Omission of Local Repository Adoption
The user prompt assumes that adding a project always means pulling from GitHub orgs or creating on GitHub. However, a widespread developer use case is:
*"I already cloned `~/projects/my-app` yesterday. I just want SASE to manage it."*
Omitting local directory adoption leaves a glaring hole in the Admin Center's utility. Supporting "Add Existing Local Repository" via a path picker is trivial, offline-friendly, and enormously valuable.

---

## 4. Proposed Adjustments to Requirements

Based on the critique, here are the concrete adjustments recommended:

| # | Original Requirement | Proposed Adjustment | Rationale |
|---|----------------------|---------------------|-----------|
| **1** | New projects enabled by default | **Retained as-is** | Matches user expectation and SASE lifecycle default (`enabled`). |
| **2** | Prompt user to select VCS first | **Mode-First Wizard with Smart VCS Default** | User chooses *Intent* first: "Import Existing" vs "Create New". VCS defaults intelligently to GitHub if configured. |
| **3** | Prompt to select from menu of likely projects from configured orgs | **Async Filterable Candidate Grid with Org Tabs & Exclusions** | Filter out repos already in SASE. Support multi-org switching via tabs. Background-load with live fuzzy filter. |
| **4** | Option to create new project from scratch via VCS plugin | **Streamlined Greenfield Creation via Pluggy Hook** | Introduce formal `ws_create_remote_repo` hook. SASE core remains decoupled from `gh` CLI. |
| **5** | Prompt for *all* VCS options (license, description, etc.) | **Curated 80/20 Core Options + Advanced Terminal Escape** | Focus on Name, Org, Visibility, Description, README, gitignore. Avoid 15-input form clutter. |
| **6** | *(Unspecified)* Local directory adoption | **Add Local Git Folder Adoption** | Allow importing an existing local repo by path (`~/projects/...`), creating the `.sase` file immediately. |
| **7** | *(Unspecified)* CLI Parity | **Add CLI Commands `sase project add` and `sase project create`** | Guarantees testability, scriptability, and satisfies Rust Core / backend boundary rules. |

---

## 5. UX & Visual Design: "Intuitive, Reliable, and Beautiful"

To make this feature feel world-class, the UI must match SASE's visual design language:
- Clean borders, tasteful color accents (`#FFAF5F` orange, `#00D7AF` green, `#87D7FF` cyan).
- Keyboard-first navigation (full Vim/readline support, single-key accelerators).
- Clear, step-by-step progress indication.

### 5.1 Entry Point: The Projects Sub-Tab
On the Admin Center Projects sub-tab:
- Key **`n`** triggers `action_new_project()`.
- The footer key hint line is updated:
  ```text
  j/k move  ' jump  / filter  ] sub-tab  n new project  i init  I init all  ...
  ```
  *(Note: `n new project` is given prominent placement next to `init`).*

### 5.2 Wizard Architecture: `NewProjectWizardModal`

Instead of popping multiple disconnected dialogs, a single coherent wizard modal (`NewProjectWizardModal`) manages the 3-step state machine:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ✦ SASE Admin Center — Add / Create Project                             [Esc]│
├─────────────────────────────────────────────────────────────────────────────┤
│  [1. Source & VCS] ───▶ [2. Configure / Select] ───▶ [3. Provision & Setup] │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 5.3 Screen Mockup: Step 1 — Mode & VCS Selection

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ✦ Add / Create Project                                            [Esc Close]│
├─────────────────────────────────────────────────────────────────────────────┤
│  Step 1 of 3: Choose Source & VCS Provider                                  │
│                                                                             │
│  Select how you want to add your project to SASE:                           │
│                                                                             │
│  Mode:                                                                      │
│    (●) 1. Import Existing Remote Repository                                 │
│           Browse and add an existing repository from your VCS provider      │
│    (○) 2. Create Brand New Repository                                       │
│           Provision a new repository on your VCS provider from scratch      │
│    (○) 3. Adopt Local Directory                                             │
│           Register an existing Git repository already on your filesystem    │
│                                                                             │
│  VCS Provider:                                                              │
│    [ ● GitHub (sase-github) ]    [ ○ Git (bare/local) ]                     │
│                                                                             │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Enter Continue   1-3 Select Mode   Tab Switch Field   Esc Cancel           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 5.4 Screen Mockup: Step 2A — Import Existing Repository (GitHub)

When **Import Existing Remote Repository** is selected:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ✦ Add Project — Select Remote Repository                          [Esc Back]│
├─────────────────────────────────────────────────────────────────────────────┤
│  Step 2 of 3: Choose a GitHub repository to add                             │
│                                                                             │
│  Organizations:  [ sase-org (4 available) ]  [ bbugyi200 (12 available) ]    │
│                                                                             │
│  Filter: [ widgets___________________________________________ ]  (3 matches) │
│                                                                             │
│  REPOSITORY               VISIBILITY   PUSHED         DESCRIPTION           │
│  ─────────────────────────────────────────────────────────────────────────  │
│  ▸ widgets-api            private      2 hours ago    Core widget API service│
│    widgets-web            public       yesterday      Frontend React app    │
│    widgets-infra          private      3 days ago     Terraform & deployment│
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Repository Details:                                                        │
│  Full Name:   sase-org/widgets-api                                          │
│  Clone URL:   git@github.com:sase-org/widgets-api.git                       │
│  Local Dest:  ~/projects/github/sase-org/widgets-api/                       │
│  Project:     gh_sase-org__widgets-api  (Display Name: widgets-api)         │
│  State:       enabled (default)                                             │
│                                                                             │
│  Enter Select & Clone   j/k Move   / Filter   ] Switch Org   Esc Back       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Polish Elements in Step 2A:**
1. **Automatic Exclusion:** Repositories already registered in SASE are filtered out (with an optional toggle `[x] Show already imported`).
2. **Instant Search:** Live typing in the filter box instantly narrows the list across name and description.
3. **Org Switching:** Easy cycling between configured `github_orgs` via `[` / `]` or Tab.
4. **Rich Metadata:** Displays visibility badge (private/public), pushed date, and description.

---

### 5.5 Screen Mockup: Step 2B — Create Brand New Repository (Greenfield)

When **Create Brand New Repository** is selected:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ✦ Create Project — Provision New GitHub Repository                [Esc Back]│
├─────────────────────────────────────────────────────────────────────────────┤
│  Step 2 of 3: Configure new repository                                      │
│                                                                             │
│  Owner / Organization:                                                      │
│    [ sase-org ▼ ]   (or bbugyi200)                                          │
│                                                                             │
│  Repository Name:                                                           │
│    [ auth-service_____________________________________________ ]            │
│    ✓ Valid project slug: gh_sase-org__auth-service                          │
│                                                                             │
│  Visibility:                                                                │
│    (●) Private      (○) Public      (○) Internal                            │
│                                                                             │
│  Description (optional):                                                    │
│    [ Authentication microservice with OAuth2 and Passkeys______ ]           │
│                                                                             │
│  Initialization Scaffolding:                                                │
│    [✓] Add README.md                                                        │
│    [✓] Add .gitignore:  [ Python ▼ ]                                        │
│    [ ] Add License:     [ MIT License ▼ ]                                   │
│                                                                             │
│  Local Clone Target:                                                        │
│    ~/projects/github/sase-org/auth-service/                                 │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Enter Create & Provision   Tab Next Field   Space Toggle   Esc Back        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 5.6 Screen Mockup: Step 3 — Provisioning & Progress Overlay

When the user presses Enter to confirm, the modal transitions into a clean, reassuring progress display:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ✦ Creating Project: sase-org/auth-service                         [Please wait]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Provisioning new project...                                               │
│                                                                             │
│   [✓] 1. Creating remote repository on GitHub via gh...                     │
│   [✓] 2. Initializing remote repository with README & .gitignore...         │
│   [⟳] 3. Cloning repository to ~/projects/github/sase-org/auth-service/... │
│   [ ] 4. Writing SASE project specification file...                         │
│   [ ] 5. Configuring SDD sidecar repository...                              │
│   [ ] 6. Registering project and refreshing Admin Center...                 │
│                                                                             │
│   Progress: 50% ████████████████████░░░░░░░░░░░░░░░░░░░                     │
│                                                                             │
│   Status: Cloning repository (SSH: git@github.com:sase-org/auth-service.git)│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Upon Completion:**
- Status updates to `✓ Project 'auth-service' successfully created and enabled!`
- Modal auto-dismisses after 1.5 seconds (or on Enter).
- `ProjectsPane` reloads records, pins the highlight on the newly created project row, and displays a toast notification: `Project 'auth-service' added (enabled)`.

---

## 6. Technical Implementation Blueprint

### 6.1 Architecture Layers & Decoupling

To follow SASE design patterns and core rules, the feature must be cleanly divided across layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Layer 1: TUI Presentation (src/sase/ace/tui/modals/)                        │
│   - NewProjectWizardModal (multi-step dialog)                               │
│   - ProjectsPane integration (action_new_project, 'n' keybinding)           │
│   - Off-thread worker invocation (non-blocking, cancellable)                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Layer 2: Core Project Creation Service (src/sase/project_creation/)         │
│   - create_project_from_remote(...)                                         │
│   - create_project_from_scratch(...)                                        │
│   - adopt_local_project(...)                                                │
│   - CLI commands in src/sase/main/project_handler.py                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Layer 3: Workspace Provider Plugin Hooks (sase_workspace)                   │
│   - ws_list_ref_namespaces                                                  │
│   - ws_list_repo_candidates                                                 │
│   - ws_create_remote_repo (NEW HOOK)                                        │
│   - ws_resolve_ref                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Layer 4: Provider Implementations                                           │
│   - sase-github: calls gh repo create, git clone, ensure_useful_repo_name   │
│   - bare_git_workspace: calls init_bare_git_project                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Proposed Hookspec Extension in SASE Core
In `src/sase/workspace_provider/_hookspec.py`:

```python
@dataclass(frozen=True)
class VcsCreateRepoOptions:
    """Options for greenfield remote repository provisioning."""
    name: str
    namespace: str
    visibility: str = "private"  # "private", "public", "internal"
    description: str = ""
    add_readme: bool = True
    gitignore_template: str | None = None
    license_template: str | None = None

@dataclass(frozen=True)
class VcsCreateRepoResult:
    """Result of a repository creation operation."""
    success: bool
    remote_url: str
    primary_workspace_dir: str
    project_name: str
    error_message: str | None = None

class WorkspaceHookSpec:
    ...
    @hookspec(firstresult=True)
    def ws_create_remote_repo(
        self,
        workflow_type: str,
        options: VcsCreateRepoOptions,
    ) -> VcsCreateRepoResult | None:
        """Create a new remote repository and clone it to its primary workspace.
        
        Returns None if the plugin does not own workflow_type.
        """
        ...
```

### 6.3 Implementation in `sase-github`
In `sase-github/src/sase_github/workspace/create.py`:
1. **Remote Creation:**
   ```bash
   gh repo create <namespace>/<name> \
     --<visibility> \
     --description "<desc>" \
     [--add-readme] \
     [--gitignore <template>] \
     [--license <license>]
   ```
   Uses `non_interactive_gh_env()` with `timeout=30` and `stdin=subprocess.DEVNULL`.
2. **Local Clone:**
   Calls existing `clone_gh_repo(namespace, name, primary_workspace_dir)`.
3. **Spec Generation:**
   Calls `project_file_for(projects_base(), project_name)`.
   Sets `WORKSPACE_DIR: <primary_workspace_dir>` and `PROJECT_STATE: enabled`.
   Calls `ensure_useful_repo_name(project_name, name, projects_base=base)`.
4. **SDD Sidecar (Optional):**
   If SDD sidecar is enabled in config, invokes `ensure_sdd_sidecar(...)`.
5. **Audit Logging:**
   Invokes `log_project_creation(project=project_name, project_file=project_file)` into `~/.sase/logs/project_creation.log`.

### 6.4 Implementation in `bare_git_workspace`
In `src/sase/workspace_provider/plugins/bare_git_init.py`:
- Maps `ws_create_remote_repo` directly to `init_bare_git_project(project_name, bare_dir, clone_dir)`.
- Sets up bare repo at `~/.sase/repos/<name>.git` and clone at `~/projects/git/<name>/`.

### 6.5 CLI Parity: `sase project add` and `sase project create`
Following `sase/memory/cli_rules.md`:
1. `sase project add <ref-or-path>`:
   - Example: `sase project add sase-org/widgets-api` (clones from GitHub and enables).
   - Example: `sase project add ~/projects/my-local-tool` (adopts local folder).
2. `sase project create <name> [--vcs gh] [--org <org>] [--public/--private] [--desc <text>]`:
   - Non-interactive CLI creation matching the TUI capabilities.

---

## 7. Error Handling, Diagnostics, & Edge Cases

| Edge Case / Failure | Cause | Handling Strategy |
|---------------------|-------|-------------------|
| **`gh` Not Installed** | CLI missing from PATH | Detect early in Step 1. Display badge: `gh CLI not found. Install from cli.github.com`. Disable remote creation; offer local git adoption. |
| **GitHub Auth Expired** | Expired OAuth token or SSH key | Classify exit code from `gh` (`looks_like_auth_error`). Display inline banner: `Authentication required. Please run 'gh auth login' in terminal.` |
| **Project Name Collision** | Repo or project name already exists in SASE or GitHub | Validate as the user types in Step 2. Check `find_project_ref_owner(name)` against existing SASE projects. If collision exists, show red inline error and disable Submit button. |
| **Network Timeout during Clone** | Spotty connection or massive repo | Worker timeout set to 60s. On timeout, display clear error with `[Retry]` button. Do not leave a corrupted empty directory behind (cleanup on failure). |
| **Partial Provisioning Failure** | Remote repo created on GitHub, but `git clone` failed | Transactional cleanup: Prompt user: `Remote repo created at github.com/org/name, but local clone failed: [Clone Retry] [Delete Remote Repo]`. |
| **Git Credential Stdin Freeze** | Private repo without SSH keys prompting for password | Enforce `stdin=subprocess.DEVNULL` and `GIT_TERMINAL_PROMPT=0` in all subprocesses. Fast-fails with clean error instead of seizing TUI event loop. |

---

## 8. Phased Implementation Roadmap

To deliver this feature safely, reliably, and incrementally, the following four-phase execution plan is recommended:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Provider Hookspec & Core CLI Engine                                │
│   - Add ws_create_remote_repo hookspec in sase core                         │
│   - Implement repo creation in sase-github and bare_git_workspace           │
│   - Add CLI subcommands: sase project add and sase project create           │
│   - Unit & integration tests for creation flows                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 2: TUI Import Existing Repository Flow                                │
│   - Add 'n' keybinding to ProjectsPaneKeymaps and footer text               │
│   - Build Step 1 (Mode Chooser) & Step 2A (GitHub Org Candidate Browser)    │
│   - Wire async worker for listing repos & cloning                           │
│   - Integrate auto-refresh and highlight pinning on success                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 3: TUI Greenfield Creation Flow                                       │
│   - Build Step 2B (Clean 5-field create form with live validation)          │
│   - Build Step 3 (Progress checklist & status animation)                    │
│   - Add Local Directory adoption pathway                                    │
│   - Wire transactional error handling and rollback                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 4: Visual Polish, Golden Tests, & Documentation                       │
│   - Add PNG visual snapshot tests in tests/ace/tui/visual/                  │
│   - Verify 80x24 and 120x40 terminal responsiveness                         │
│   - Update user documentation in docs/ and memory files                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Recommended Next Steps

1. **Adopt the Adjusted Requirements:**
   Approve the separation of "Import Existing" vs "Create Greenfield", and accept the streamlined 80/20 field form over the exhaustive 15-flag form.
2. **Implement Phase 1 First:**
   Establish the hookspec and CLI foundation in `sase` and `sase-github` before touching the TUI. This ensures the TUI has rock-solid, fully-tested service methods to call.
3. **Execute TUI Integration (Phases 2 & 3):**
   Implement `NewProjectWizardModal` with async workers, ensuring zero event-loop stalls and beautiful Rich/Textual presentation.
