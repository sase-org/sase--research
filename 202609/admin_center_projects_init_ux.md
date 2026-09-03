---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
---

# Initializing Projects From The SASE Admin Center

**Research question:** what is the best UX and implementation for invoking bare
`sase init` for one project, or `sase init -a|--all` for every enabled main project,
from the SASE Admin Center's **Projects** tab?

**Scope:** `sase` at `9e2d95bb0`. The investigation covered the bare-init parser,
planner, preview renderer, single-project and all-project coordinators, the four
registered resource initializers, exceptional interactive inputs, project discovery,
the Admin Center Projects pane and its keymap/CSS, the confirmation-modal family, and
the tracked/durable proc infrastructure. A read-only `sase init --all --check` was also
run in this workspace to observe the real output shape. No files in the product repo
were changed.

---

## Executive summary

Add two mnemonic, pane-scoped actions to the Projects sub-tab:

- `i` — **Initialize…** the highlighted project.
- `I` — **Initialize all…** enabled main projects, with the same canonical scope as
  `sase init --all`.

Both actions should first start a tracked, read-only **preview proc**, then open a
purpose-built, scrollable **Initialize Projects** modal. The modal should summarize the
scope, group planned actions by project and resource (`config`, `memory`, `repo`,
`skills`), identify writes/overwrites/deletes and remote effects, expose full diffs on
request, and present warnings, blockers, and exceptional approvals before any mutation.
The primary button should say exactly what will happen — for example,
**Initialize sase** or **Initialize 5 runnable projects** — rather than **OK** or
**Confirm**.

On confirmation, submit one **durable tracked proc** which runs the existing init
coordinator in a child process. It must apply the exact reviewed plan, identified by a
fingerprint, and return a typed result. Never call the current coordinator in the TUI
process: `run_init_onboarding_all` temporarily calls `os.chdir`, which is process-wide,
and its apply path can write files, create repositories, commit, push, and deploy
chezmoi-managed content (`src/sase/main/init_onboarding.py:429-437,493-591`). Never
reduce the flow to `sase init --yes`, either: non-interactive `--yes` deliberately cannot
approve missing sidecar repositories, cannot complete an uninitialized owner identity,
and can lack a required commit subject.

The TUI should consume a structured init preview/result contract, not parse Rich text.
Because the plan model, approval semantics, and race checking are backend behavior, put
the shared wire types and validation in `sase-core`; let a thin Python command adapter
materialize today's Python `InitPlan`s and execute today's coordinator. This adds a safe
front-end boundary without duplicating init behavior or requiring an immediate rewrite
of all four planners.

The existing Projects list should otherwise remain unchanged. Do not add a permanent
init-status column or check every project on tab load: initialization state is expensive
and ephemeral, while the current hint line already overflows at 120 columns
(`src/sase/ace/tui/modals/project_management_rendering.py:298-330`). Put
`i init · I init all` early in that hint line and keep all detailed visual treatment in
the modal.

## 1. Current behavior and constraints

### 1.1 Bare `sase init` is already the right orchestration boundary

With no subcommand, `sase init` plans and, when approved, runs four registered resources
in order: config, memory, repositories, and skills. The public interface already has the
two scopes this feature needs:

- current workspace/project — `sase init`;
- every known **enabled main** SASE project — `sase init -a|--all`.

The parser describes `--check` as read-only, `--diff` as full file diffs, and `--yes` as
skipping generic prompts while explicitly excluding authorization for a missing
provider sidecar (`src/sase/main/parser_init.py:99-143`). The all-project coordinator
resolves canonical project inventory, skips unavailable workspaces while continuing,
isolates per-project failures, defers a shared chezmoi deployment until the batch ends,
and prints aggregate counts (`src/sase/main/init_onboarding.py:493-591`). Those are
valuable semantics the TUI should invoke, not reproduce.

The current plan model is already close to what a visual preview needs. Each `InitPlan`
has a command, label, summary, ordered actions, warnings, and blockers; each action has
an operation (`create`, `update`, `overwrite`, `delete`, `validate`, or `deploy`), path,
detail, and optional new content (`src/sase/main/init_plan.py:9-41`). The CLI preview
renderer already assigns distinct glyphs/colors and computes file diffs. The TUI should
preserve that information hierarchy rather than showing only a generic warning.

The read-only sample run in this workspace demonstrates the value of a structured
preview. `sase init --all --check` reported one enabled project: config, repositories,
and skills were current, while memory needed attention with a 96-line addition to
`sase/task_types.json`. That output is useful to a human, but piping and parsing its Rich
presentation would couple the TUI to spacing, color, and copy changes. The underlying
plans are the stable source.

### 1.2 `--yes` is not unattended completion

Three exceptional paths make a naïve background `sase init --yes` incomplete or unsafe:

1. **Owner identity.** Config initialization checks `stdin.isatty()` before collecting
   missing machine/user identity (`src/sase/main/config_init_handler.py:480`). A proc
   launched with stdin disconnected cannot finish this interactively.
2. **Missing provider sidecars.** Bare non-interactive onboarding warns and defers
   creation. The creation prompt names the exact provider, repository, and visibility;
   the agents sidecar has an additional publication/privacy warning
   (`src/sase/main/_repo_init_sidecars.py:50-79,128-220`). This is intentionally more
   specific consent than generic `--yes`.
3. **Dirty memory/source folding.** Memory deployment may require a commit subject. In
   non-interactive mode it fails if none was supplied
   (`src/sase/main/init_memory/project_deploy.py:121-168`).

These are not edge cases to paper over with a success toast. The preview contract must
represent required decisions/inputs explicitly, and the apply request must carry the
user's exact answers.

### 1.3 The Projects tab is compact and keyboard-first

The Projects pane currently has three sub-tabs: Projects, Repos, and Workspaces. The
Projects surface is a summary, filter, bordered `OptionList`, 30%-height scrollable
detail panel, and a one-line hint footer (`src/sase/ace/tui/modals/projects_pane.py:200-247`;
`src/sase/ace/tui/styles.tcss:7937-8024`). Its rows contain enabled and disabled projects,
grouped enabled-first; home and system-managed records are excluded
(`projects_pane.py:306-330`).

The existing lifecycle verbs use `a`/`d`, marks use `m`/`u`, and Enter enables a disabled
project. Lowercase and uppercase `i` are free in the pane's default keymap
(`src/sase/ace/tui/keymaps/app_keymaps.py:263-286`). This makes `i`/`I` the clearest
mnemonic pair and avoids changing the established meaning of Enter.

The pane's marks should **not** affect initialization. Marks currently mean the target
set for enable, disable, and delete. Letting `i` initialize marked rows would introduce
a third, undocumented scope — arbitrary subset — which bare `sase init` does not have.
It would also make a dangerous action depend on stale marks that might be below the
fold. The scopes should remain unambiguous:

- `i` means exactly the highlighted row;
- `I` means the canonical enabled-project inventory, independent of list filter and
  marks.

### 1.4 Init is proc-shaped work

The project's TUI performance rules require slow user actions to run as tracked procs,
with UI mutations performed first and no filesystem/network work in render or pump
callbacks. Textual likewise recommends workers for blocking work, and its thread-worker
guidance requires UI updates to be marshalled back to the UI thread
([Textual workers](https://textual.textualize.io/guide/workers/)).

ACE already supplies both tiers needed here:

- `_submit_session_worker` for session-local, thread-backed work with typed payloads,
  live output, deduplication, and completion callbacks
  (`src/sase/ace/tui/actions/_proc_action_submission.py:199-298`);
- `_submit_durable_proc` for supervisor-owned work with a typed request, result path,
  request fingerprint, concurrency keys, pending projection, and recovery after the
  current UI goes away (`_proc_action_submission.py:35-197`).

The comprehensive update flow is the nearest product precedent: it submits a read-only
preview proc, receives a typed preview, presents sectioned confirmation, then submits
one tracked mutation (`src/sase/ace/tui/actions/update_run.py:79-190`). Init should use
the same interaction architecture, but mutation should be durable because it can
perform multi-project writes and remote publication.

## 2. User goals and design principles

The design should optimize for the following, in order:

1. **Confidence before mutation.** Show what is current, what changes, what is held, and
   what can escape the local machine.
2. **Scope clarity.** A selected project and all enabled projects must never be confused;
   filter and marks must not silently redefine “all.”
3. **Responsive execution.** Checking or applying must never freeze navigation or modal
   painting.
4. **Honest partial results.** `--all` can have current, initialized, unavailable,
   needs-attention, and failed projects in one run. “Completed” is not enough.
5. **CLI parity.** Project selection, operation ordering, failure isolation, and chezmoi
   behavior remain owned by bare init.
6. **Durability and observability.** Mutation remains visible in Procs and does not die
   merely because the Admin Center closes.
7. **Progressive disclosure.** The common case is one compact summary. Diffs and rare
   approvals are available without dominating the Projects list.

GNOME's interaction guidance supports this shape: action dialogs are appropriate when a
user-requested operation needs a preview, buttons should use specific imperative verbs,
and unavailable actions should be insensitive rather than failing after activation
([Dialogs](https://developer.gnome.org/hig/patterns/feedback/dialogs.html),
[Buttons](https://developer.gnome.org/hig/patterns/controls/buttons.html)). Its writing
guidance also favors direct, concrete labels over vague confirmation copy
([Writing style](https://developer.gnome.org/hig/guidelines/writing-style.html)).

## 3. Options considered

| Option | Strengths | Problems | Verdict |
|---|---|---|---|
| Suspend ACE and open an interactive terminal running `sase init` | Exact current CLI; all prompts work | Disruptive context switch; no native preview; weak Proc integration; UI disappears during long work | Reject as the main path; retain the CLI as an escape hatch |
| Spawn `sase init --yes` and show its log | Small implementation; uses coordinator | Stdin-less execution cannot satisfy owner identity, sidecar consent, or some commit messages; human output is not a result contract | Reject |
| Add an INIT status column and check all rows on tab load | Discoverable at a glance | Expensive/stale; network and filesystem work scales with project count; crowds an already dense list; violates on-demand performance guidance | Reject |
| Treat marked rows as an init batch | Familiar multi-select behavior | Creates semantics that do not match `sase init --all`; hidden marks can surprise; complicates deferred shared deployment | Defer unless the CLI later gains a first-class subset scope |
| Preview proc → native review modal → durable exact-plan apply | Responsive; visually native; explicit risk; observable; preserves coordinator semantics; supports partial all-project results | Requires a structured contract and exceptional-input model | **Recommend** |

## 4. Proposed interaction

### 4.1 Entry points and discoverability

Add `initialize_project: "i"` and `initialize_all_projects: "I"` to
`ProjectsPaneKeymaps`, the scoped binding metadata, and `default_config.yml`. Both are
project-sub-tab-only actions, disabled on Repos and Workspaces alongside the existing
project verbs. Update help/configuration docs as well as the rendered footer.

Because the hint footer already clips beyond 120 columns, put the new mnemonic near the
front:

```text
j/k move  ' jump  / filter  [ / ] sub-tab  i init  I init all  Enter enable  …
```

Do not add always-visible buttons or another row to the main layout. The current detail
panel already consumes 30% of height, and a permanent action strip would tax every visit
for a relatively infrequent operation. The two early key hints, global key-help surface,
and command palette provide discoverability; the modal provides the richer mouse/button
surface after intent is expressed.

The selected action should be allowed for a disabled project when its recorded primary
workspace exists. Initialization and lifecycle state are separate concepts, and bare
init is valid in that workspace. The preview should display a **Disabled** badge and the
note “Excluded from Initialize all.” If no workspace is available, disable the apply
path and explain the exact reason.

### 4.2 Immediate feedback

Activation should make a cheap UI change synchronously:

```text
Checking initialization for sase…
```

Then submit a tracked preview proc. Repeated activation while a preview or apply owns the
init concurrency scope should show a warning such as “Initialization is already being
checked or applied.” The Projects pane remains navigable; the result is bound to the
captured project identity, not whichever row happens to be highlighted on completion.

If the plan is a complete no-op, do not open a confirmation dialog. Show:

```text
sase is initialized · config, memory, repos, and skills are current
```

For all-project no-op, show the aggregate count. This keeps the fast path fast.

### 4.3 Single-project preview modal

Use a dedicated `InitConfirmModal` (or extract a domain-neutral base from
`PluginActionConfirmModal`) with the same visual language as the existing sectioned
plugin/update previews: dimmed parent, centered accent border, a scrollable preview
panel, and centered action buttons. Textual's `ModalScreen` naturally dims its parent
and gives the modal's bindings precedence
([ModalScreen](https://textual.textualize.io/api/screen/)).

An indicative 120-column composition:

```text
                 ┌─ ↻ Initialize sase ──────────────────────────────────┐
                 │ Project  sase                      ENABLED · github   │
                 │ Workspace  …/workspaces/sase-org/sase/sase_12        │
                 │                                                      │
                 │ This can write files and may commit, push, create    │
                 │ repositories, or deploy managed files.               │
                 │ $ sase init --yes                                    │
                 │                                                      │
                 │ ┌─ Initialization plan ────────────────────────────┐ │
                 │ │ ✓ CONFIG  Current                                │ │
                 │ │ ~ MEMORY  1 update · +96 −0                      │ │
                 │ │     ~ sase/task_types.json                       │ │
                 │ │ ✓ REPOS   Current                                │ │
                 │ │ ✓ SKILLS  Current                                │ │
                 │ └───────────────────────────────────────────────────┘ │
                 │ d full diff                 Ctrl+D/U scroll          │
                 │                                                      │
                 │       [ Cancel (n) ]   [ Initialize sase (y) ]       │
                 └──────────────────────────────────────────────────────┘
```

Use the CLI preview's existing vocabulary consistently:

- green `+` for create;
- yellow `~` for update/overwrite;
- red `−` for delete;
- cyan `●` for validate/deploy;
- dim check for current;
- red **HOLD** for blockers.

The title names the scope, the intro names classes of side effects, and the preview names
the concrete side effects. Do not show every “current” action expanded; one compact line
per current resource reassures without burying changes. `d` toggles unified diffs for
file actions. Preserve the scroll position when toggling where practical.

If any action is an overwrite or delete, style its section and primary button as a
dangerous variant. Do not require typing the project name: the operation is recoverable
through version control in the usual case, and a reviewed plan plus specific button is
proportionate. Remote repository creation and public agents-sidecar publication receive
their own explicit consent instead.

### 4.4 All-project preview modal

`I` should always mean the inventory resolved by `sase init --all`: enabled, non-home,
non-system main projects. The modal must explicitly state that search filters, highlighted
row, disabled rows, and marks do not narrow the scope.

The top of the modal should show an aggregate line before details:

```text
8 enabled · 5 need attention · 2 current · 1 unavailable
```

Projects are then collapsible/compact sections, with changed or held projects first and
current projects summarized last:

```text
~ sase                 1 update · +96 −0
~ chezmoi              2 updates · may commit/push/apply
! client-work          HOLD · primary workspace unavailable
✓ dotfiles, notes      Current
```

Expanding a project reveals the same resource/action view as single-project mode. Full
diff can be toggled for the focused project or globally. The primary button must reflect
partial applicability: **Initialize 5 runnable projects**, not **Initialize all**, when
two are held. The copy immediately above it should say those held projects will remain
unchanged and continue to need attention. This matches the existing all-project
coordinator's failure isolation without implying total success.

### 4.5 Exceptional inputs and approvals

Model rare inputs as structured `requirements`, not strings hidden among warnings:

| Requirement | TUI treatment | Apply semantics |
|---|---|---|
| Owner identity missing/ambiguous | A short setup step for machine and username, including validation and collision/reuse choices | Exact values travel in the apply request |
| Provider sidecar missing | Per-repository unchecked approval naming provider, repository, role, and visibility | Only checked, fingerprint-matching repositories may be created |
| Public agents sidecar | Visually prominent publication/privacy warning and a separate unchecked approval | Never implied by generic initialization approval |
| Memory fold needs commit subject | Required text input scoped to the affected project | Subject supplied non-interactively to memory init |
| Planner blocker/unavailable workspace | Red held section with remediation copy | Project cannot be selected for apply |

Do not overload the first preview with many empty controls. Render a **Decisions required**
section only when the planner reports requirements, and move complex owner setup into a
small second modal/step. Simple sidecar consent and commit subjects can remain inline.
The primary apply button stays disabled until every requirement for the projects being
applied is satisfied.

For an incremental first release, it is acceptable to render these projects as held and
direct the user to the existing specialized CLI — provided the modal is explicit and the
completion toast never calls them initialized. The target design should collect typed
requirements natively; otherwise the Admin Center path remains incomplete precisely on
first-time onboarding, where it is most valuable.

### 4.6 Progress, completion, and failure

Once confirmed, close the modal immediately and show a start toast/status. The durable
proc appears in Procs with a descriptive name:

```text
initialize sase
initialize all projects
```

Its live output should be stage-oriented — `sase · memory`, `chezmoi · deploy`, and so on
— rather than a fake percentage. Progress bars are most useful for longer operations
with measurable completion; indeterminate activity and completed/total project counts
are better here because repository/network durations vary
([Progress bars](https://developer.gnome.org/hig/patterns/feedback/progress-bars.html),
[Textual ProgressBar](https://textual.textualize.io/widgets/progress_bar/)). For all mode,
`Project 3 of 8 · chezmoi · memory` is meaningful progress even without an ETA.

Completion behavior:

- success: `Initialized sase · 4 resources applied`;
- no-op after race-safe replan: `sase is already initialized`;
- partial all: `Initialized 5 · 2 current · 1 needs attention — inspect Procs`;
- failure: name the failed project/stage and point to Procs without forcing navigation.

After completion, reload Projects, Repos, Workspace inventory counts, and current-project
metadata while preserving the selected project, text filter, sub-tab, and scroll intent.
Do not automatically switch to Procs; the toast and global proc indicator are sufficient.

## 5. Recommended implementation architecture

### 5.1 End-to-end flow

```text
ProjectsPane (`i` / `I`)
        │ captures scope + selected ProjectRecordWire
        ▼
InitPreviewRequested message to app
        │ immediate pane status
        ▼
tracked session preview proc ── child `sase init --check` adapter
        │                         cwd explicit; stdin closed
        │ typed InitPreview
        ▼
InitConfirmModal ── requirements / approvals / full diff
        │ cancel                 │ confirm exact fingerprint
        └────────────────────────▼
                   durable `init.apply` proc
                        │ replan + fingerprint compare
                        │ existing coordinator executes in child
                        ▼
                   typed InitApplyResult
                        │
                        ├─ toast + Procs output
                        └─ refresh pane inventories, preserve selection
```

The pane should emit a typed message and remain presentation-only. An app-level action
mixin should own preview submission, modal transitions, durable submission, callbacks,
and cross-pane refresh. That is consistent with app-owned proc infrastructure and avoids
teaching a child widget how to manage supervisor state.

### 5.2 A structured contract, not terminal parsing

Add stable wire types along these lines:

```text
InitScope
  selected { project identity, project file, workspace }
  all_enabled

InitPreview
  schema_version
  scope
  generated_at
  fingerprint
  projects[]
    identity, display_name, enabled, workspace, status
    plans[] { resource, summary, actions[], warnings[], blockers[] }
    requirements[]
  aggregate counts

InitApproval
  requirement_id
  requirement_fingerprint
  decision / supplied value

InitApplyRequest
  preview_fingerprint
  scope
  approvals[]

InitApplyResult
  projects[] { status, applied actions, warning/error }
  deferred deploy status
  aggregate counts
```

Action content should not serialize entire new files into the default compact payload.
Include paths, operation, detail, diffstat, and a content hash. Provide full unified diffs
only in a deliberate detailed preview field or result sidecar. This keeps all-project
payloads bounded while supporting `d`.

The CLI should gain a documented machine-readable, read-only form such as
`-j|--json` on `sase init --check` and `sase init --all --check`. Human output remains the
default. Per the CLI project's own rules, the public long option should have a short
alias, help text, and optional behavior. Standard CLI guidance likewise recommends
human-readable defaults plus structured output on request, progress on long work, and
non-interactive commands that never unexpectedly prompt
([Command Line Interface Guidelines](https://clig.dev/)). Treat exit code 1 plus a valid
preview saying “drift” as a successful preview, not a proc failure.

For mutation, register a narrow durable operation such as `init.apply` that consumes an
`InitApplyRequest` and writes an `InitApplyResult`. Use the existing request/result-sidecar
protocol rather than proliferating public approval flags. The modal may display the
human-equivalent `$ sase init --yes` or `$ sase init --all --yes`, but the actual durable
invocation also carries exact approvals and a fingerprint.

Shared scope/preview/approval/result wire types, validation, and fingerprint rules belong
in `sase-core` and its Python bindings under the project's backend-boundary rule. The
current Python init planners and coordinator can remain the implementation behind a thin
command adapter for this feature. This is an incremental boundary: it avoids both a TUI
reimplementation and an unrelated wholesale planner migration.

### 5.3 Preview and apply must be separate processes

Use a child process for both stages:

- **Preview:** session-local tracked proc; explicit selected-project `cwd`, or canonical
  all-project resolution; stdout is structured data; stderr/live logs go to the proc.
- **Apply:** durable supervisor proc; same explicit scope; stdin closed because all
  required decisions are already in the request.

Do not import and invoke `_run_init_onboarding_result` or `run_init_onboarding_all` in a
thread worker. Threads share cwd, and `_working_directory` wraps `os.chdir`. During an
all-project run, unrelated TUI code could resolve relative paths against the wrong
project. A child process contains that global state.

Do not use TUI suspension as the normal apply path. It solves stdin, but sacrifices the
reviewed-plan guarantee, durability, and continuous Admin Center context.

### 5.4 Race safety and concurrency

Init planning is a snapshot. Between preview and confirmation, another agent or proc can
change generated sources, Git state, project inventory, remote sidecars, or the recorded
primary workspace. Therefore:

1. fingerprint scope identity, ordered resource plans, action content hashes, warnings,
   blockers, and requirements;
2. acquire the init concurrency claim in the durable proc;
3. replan before applying;
4. compare fingerprints;
5. if different, apply nothing and return **Plan changed — review initialization again**.

Use a global concurrency key such as `ace:init` for both selected and all-project init.
That is intentionally conservative: skills/memory can share chezmoi deployment and
project `--all` includes arbitrary selected-project scopes. A global key makes selected
vs all collisions correct without inventing wildcard scope matching. More granular
resource keys can be added later only if the backend can prove isolation.

Sidecar approvals must include their own resource fingerprint. An approval for a private
GitHub repository must not silently authorize a later public repository or a different
name/provider.

### 5.5 Project scope details

For selected mode, capture and pass the project identity, project-file path, and recorded
primary workspace from the selected row. Validate them again in the child. Never rely on
the TUI process's cwd.

For all mode, pass only `all_enabled`; let the existing backend resolver rebuild the
canonical inventory at preview and apply time. Do not serialize the currently filtered
rows as “all.” The fingerprint detects membership changes between review and execution.

All mode should retain today's single deferred chezmoi deployment and per-project failure
isolation. The typed result needs to preserve `current`, `initialized`,
`needs_attention`, `failed`, `cancelled`, and unavailable outcomes rather than flattening
everything to an exit code (`src/sase/main/init_onboarding.py:35-50,465-490`).

### 5.6 Likely product-repo change map

| Area | Change |
|---|---|
| `sase-core` wire/API + Python binding | Add versioned init scope, plan, requirement, approval, request/result, status, and fingerprint validation types |
| `src/sase/main/init_plan.py` / `init_project_scope.py` | Adapt existing plans/inventory to the wire types; expose requirement metadata instead of burying it in strings |
| `src/sase/main/init_onboarding.py` | Add structured preview/result adapter and exact-plan apply guard while retaining current human coordinator |
| `src/sase/main/parser_init.py` | Add `-j|--json` for read-only structured preview, with help and validation |
| durable operation registry (`src/sase/ops/…`) | Register `init.apply` request/result handling and concurrency identity |
| new app action module | Handle pane messages, preview proc, modal, apply proc, completion, and refresh |
| `projects_pane.py` / project action mixins | Add `InitRequested`, selected/all actions, captured row identity, project-sub-tab gating, and status updates |
| new init modal/model/rendering modules | Render compact/all previews, decisions, diffs, danger styling, and specific buttons |
| keymap modules + `src/sase/default_config.yml` | Add configurable `i`/`I` defaults in both required locations and metadata/binding builders |
| proc-producer inventory | Register both preview and durable apply sites; its AST conformance test rejects unlisted producer calls |
| docs and snapshots | Document scope/keys/approval behavior and add visual baselines for normal, all, dangerous, and held states |

Avoid naming the new modal `PluginActionConfirmModal` even if code is shared. Either
extract a neutral `ActionPreviewModal` foundation with domain-specific copy/renderers, or
create a focused init modal by following the existing structure. A narrowly duplicated
modal shell is preferable to leaking plugin terminology into Projects; a clean neutral
extraction is preferable if it can be done without changing existing update snapshots.

## 6. Testing and acceptance criteria

### 6.1 Backend/CLI

- Selected preview returns all four resources in registry order and never writes.
- All preview includes enabled main projects only; disabled/home/system records are
  excluded and unavailable workspaces are typed outcomes.
- JSON remains valid and stable when human copy/color changes.
- Drift is represented in payload even though `--check` exits 1.
- Generic `--yes` still cannot create a missing provider sidecar.
- Each exceptional requirement is structured and round-trips through bindings.
- Apply rejects a stale global fingerprint or stale resource approval before any write.
- Apply preserves per-project failure isolation and exactly one deferred chezmoi deploy.
- Durable result distinguishes full success, no-op, partial attention, failure, and
  cancellation.

### 6.2 Projects pane

- `i` captures the highlighted project and ignores marks.
- `I` ignores highlight/filter/marks and previews canonical enabled scope.
- Both actions are unavailable on Repos/Workspaces and while the filter input owns the
  keystroke.
- Disabled selected project can be previewed; all excludes it; unavailable workspace
  cannot be applied.
- Selection/filter/sub-tab survive preview completion and apply refresh.
- Double activation and selected-vs-all overlap produce one clear collision warning.
- No-op uses a status/toast and never opens a redundant modal.

### 6.3 Modal and snapshots

Cover at minimum:

- selected project with one update;
- all-project mixed status;
- overwrite/delete danger styling;
- missing sidecar/publication approval;
- blocker/unavailable workspace with disabled primary action;
- full-diff expanded state;
- narrow and standard terminal sizes;
- long project/path/warning text wrapping and scroll behavior.

Buttons and keys must both work; `n`/Escape cancels without mutation, `y` invokes the
specific enabled primary action, and `Ctrl+D/U` scrolls without triggering the Projects
pane's delete binding underneath the modal.

### 6.4 Performance and verification

- Entering Projects performs no init planning.
- A key action updates the visible status before starting I/O.
- Planning/apply never runs on Textual's event-loop thread.
- Preview payload size is bounded for many projects and large files.
- Apply remains visible/recoverable through Procs after the modal or Admin Center closes.
- The proc-producer inventory is updated with both new submission sites.
- Product implementation runs the repository-required `just check`; relevant PNG
  snapshots are regenerated/reviewed. The full landing gate remains the separately
  monitored `just check-full` lane.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Structured contract drifts from human CLI behavior | Build both from the same `InitPlan`/result source; test projection parity |
| TUI becomes another orchestration implementation | Keep selection/planning/apply in the backend child; TUI only renders wire data and supplies explicit decisions |
| Preview goes stale | Fingerprint and replan atomically before mutation; abort instead of silently changing the plan |
| `--all` modal overwhelms the screen | Aggregate first; changed/held projects first; collapse current projects; lazy/full diff on demand |
| First-time onboarding still needs a terminal | Make requirements first-class; ship explicit held/remediation behavior only as an acknowledged first slice |
| Sidecar approval authorizes too much | Exact provider/repository/role/visibility fingerprint; agents publication consent separate and default-off |
| Concurrent init or shared chezmoi work races | One durable global `ace:init` concurrency claim initially |
| New key hints remain invisible | Put `i`/`I` before lower-priority lifecycle/detail hints and include them in scoped help/command palette |
| Backend-boundary work expands scope | Add wire/validation in Rust core, adapt existing Python planners; do not migrate planner implementations merely for this feature |

## 8. Sources

### Repository evidence

- Bare-init CLI and safety copy: `src/sase/main/parser_init.py:99-143`
- Plan/action model: `src/sase/main/init_plan.py:9-41`
- Human plan and diff interaction: `src/sase/main/init_onboarding.py:73-171`
- Apply orchestration and statuses: `src/sase/main/init_onboarding.py:274-426`
- Process-wide cwd and all-project loop: `src/sase/main/init_onboarding.py:429-591`
- Project target resolution: `src/sase/main/init_project_scope.py`
- Action glyph/diff rendering: `src/sase/main/init_preview.py`
- Exceptional sidecar approval: `src/sase/main/_repo_init_sidecars.py:50-79,128-220`
- Exceptional owner identity input: `src/sase/main/config_init_handler.py:479-500`
- Exceptional memory commit subject: `src/sase/main/init_memory/project_deploy.py:121-168`
- User-facing init semantics: `docs/init.md:1-58,372-397`
- Projects layout and gating: `src/sase/ace/tui/modals/projects_pane.py:129-340`
- Projects hints: `src/sase/ace/tui/modals/project_management_rendering.py:279-330`
- Projects default keys: `src/sase/ace/tui/keymaps/app_keymaps.py:263-286`
- Mirrored default configuration: `src/sase/default_config.yml:386-409`
- Existing preview-confirm precedent: `src/sase/ace/tui/actions/update_run.py:79-190`
- Tracked/durable proc APIs: `src/sase/ace/tui/actions/_proc_action_submission.py:35-298`
- Proc-producer conformance: `tests/ace/tui/test_proc_producer_inventory.py:110-249`

### External interaction guidance

- [Textual workers](https://textual.textualize.io/guide/workers/)
- [Textual ModalScreen](https://textual.textualize.io/api/screen/)
- [Textual ProgressBar](https://textual.textualize.io/widgets/progress_bar/)
- [GNOME HIG: Dialogs](https://developer.gnome.org/hig/patterns/feedback/dialogs.html)
- [GNOME HIG: Buttons](https://developer.gnome.org/hig/patterns/controls/buttons.html)
- [GNOME HIG: Progress bars](https://developer.gnome.org/hig/patterns/feedback/progress-bars.html)
- [GNOME HIG: Writing style](https://developer.gnome.org/hig/guidelines/writing-style.html)
- [Command Line Interface Guidelines](https://clig.dev/)

## Recommended solution

Implement `i` (**Initialize highlighted project…**) and `I` (**Initialize all enabled
projects…**) as explicit, mark-independent Projects-sub-tab actions. Each action should
run an on-demand tracked preview in a child process and present a native, sectioned,
scrollable modal derived from the existing `InitPlan` inventory. The modal must show
scope, exact local and remote effects, diffs on demand, partial all-project applicability,
and typed exceptional requirements; it must use a specific primary label and require
separate default-off consent for repository creation or public agents-sidecar
publication.

Confirmation should submit exactly one durable `init.apply` proc carrying the reviewed
preview fingerprint and exact approvals. The proc must replan and abort on drift, invoke
the existing bare-init coordinator outside the TUI process, retain canonical
`--all` semantics and its one deferred chezmoi deployment, and return per-project typed
results for Procs, toasts, and refresh. Add the shared versioned wire/validation types in
`sase-core`, adapt today's Python planners behind a thin structured CLI/durable-operation
boundary, and do not parse terminal output or call the current `os.chdir`-using
coordinator in a TUI thread.

This is the smallest design that is simultaneously native-looking, responsive,
race-safe, honest about first-time onboarding and partial batches, and faithful to the
behavior users already trust from `sase init`.
