---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
---

# Running `sase init` From The Admin Center Projects Tab

**Research question:** let users invoke `sase init` from the **Projects** tab of the SASE
Admin Center (`#` then `4`), for one project or for all of them (`-a|--all`), in a way that
is visually appealing and consistent with the rest of the TUI. What is the right UX, and
what is the right way to build it?

**Scope:** `sase` at master `9e2d95bb0`. Read paths: the whole `sase/main/init_*` +
`sase/main/_init_*` family that implements the coordinator and its four planners, the
`ProjectsPane` module family in the Admin Center, the tracked-proc submission stack
(`_proc_action_submission.py`, `session_proc_reporter.py`), the two existing "run a slow
mutation from the Admin Center" precedents (Updates tab self-update, Memory panel publish),
the projects keymap/binding/config chain, and `sase/doctor/checks_config_init.py`. Timings
in §1.5 were measured on this machine (`apollo`) against the live install; every structural
claim is cited to source.

---

## Executive summary

`sase init` already has the shape a good TUI wants — **a read-only plan phase followed by a
confirmed apply phase** (`InitPlan` / `InitAction`, `src/sase/main/init_plan.py:13`
and `:23`, and the `plan` / `run` pair on every registered spec,
`src/sase/main/init_registry.py:13`). The
Admin Center already has a house pattern for exactly that shape: *preview modal → confirm →
tracked proc streaming into the Procs tab* (Updates tab, `plugins_browser_sase_update.py:78`
→ `plugins_browser_sase_update_procs.py:76`). The work is mostly to connect the two.

Three findings shape the design, and each one rules out an obvious approach:

1. **Init planning reads `Path.cwd()` process-globally** (`init_memory_handler.py:129`,
   `init_preview.py:50`, and `DoctorContext.cwd = Path.cwd()`, `doctor/runner.py:45`), and
   `--all` implements per-project scoping by *`os.chdir`-ing the whole process*
   (`_working_directory`, `init_onboarding.py:430`). A Textual app cannot do that: every
   other worker thread, every relative path, every subsequent `Path.cwd()` in the process
   would move with it. **The TUI must shell out, never call the planners in-process.**
2. **Parts of init are non-bypassable-interactive by deliberate design.** `--yes` skips the
   generic per-plan prompt but explicitly *cannot* authorize creating a missing provider
   sidecar repo; that path hard-requires `stdin.isatty()` (`_repo_init_sidecars.py:138`,
   `:176`) and so does owner-identity creation (`config_init_handler.py:480`). This is
   documented as intentional (`docs/init.md`, "One resource-specific exception is
   intentionally non-bypassable"). **A TUI-only flow can never be complete**; it needs an
   honest terminal escape hatch, not a workaround.
3. **A single project's init check costs ~8.4 s of real work, and ~92 % of that is
   project-independent.** Measured (§1.5): config ≈ 0.8 s, memory ≈ 2.1 s, repo ≈ 0.55 s,
   skills ≈ 6.9 s. Config and skills are host-scoped, not project-scoped. So per-project
   drift can never be computed eagerly for a project list (perf rules 1 and 11,
   `sase/memory/tui_perf.md`), and running `--all` as N independent per-project procs would
   redo ~7.7 s of identical global work N times *and* race N chezmoi deploys that the
   coordinator currently batches into one (`defer_chezmoi_deploy`, `init_onboarding.py:515`).

**Recommendation (§6): one `i` gesture on the Projects sub-tab that plans off-thread, opens
an `InitPlanModal` showing the exact argv and the four planner rows, and on confirm submits
exactly one tracked proc — never N.** `i` targets the existing mark-set-or-selection
(`_target_records`, `project_list_controller.py:254`); `I` targets every enabled project and
maps to `--all`. Drift is never computed eagerly: an `INIT` column shows only *cached* results
with an age, in the freshness idiom the Update panel already uses. When the plan reports a
TTY-only blocker, the modal grows a second button that `app.suspend()`s and hands the user
the real `sase init` in their real terminal — the same escape the pane already uses for
`$EDITOR` (`project_management_actions.py:206`). Two small CLI additions make this clean and
are independently useful: `-p/--project` (a project selector, so nothing has to chdir) and
`-j/--json` on `--check` (a structured plan, so the modal is not screen-scraping).

---

## 1. What `sase init` actually is

### 1.1 Four planners, in a fixed order, with two different scopes

`iter_init_command_specs()` returns four `InitCommandSpec`s in execution order — `config`,
`memory`, `repo`, `skills` — each a `(plan, run)` pair (`init_registry.py:22`). The docstring
states the ordering contract: config establishes owner identity, memory owns managed
`AGENTS.md` and provider shims, repo owns sidecars and project repo wiring.

The scopes are *not* uniform, and this is the single most important structural fact for a
project-oriented UI:

| Spec | Scope | Evidence |
| --- | --- | --- |
| `config` | **host** — per-user/per-machine owner identity | `plan_config_init` starts with `del args`; it reads only `get_agent_owner_config_snapshot()` (`config_init_handler.py:54-56`) |
| `memory` | **project + home** | `_load_memory_inputs` reads `Path.cwd()` for the project root *and* always plans `home_entries` from global config (`init_memory_handler.py:127-176`) |
| `repo` | **project** | configured sidecars, project repo config, ignore rules |
| `skills` | **host** — deploys to `~/.<provider>/skills/` or the chezmoi source tree | targets come from `Path.home()` / `chezmoi_home` (`_init_skills_sources.py:62-77`); sources are loaded with `get_all_xprompts(project="")` (`init_skills_handler.py:148`) |

So "initialize project X" is, today, "run two project-scoped planners and two host-scoped
planners while standing inside X's workspace". Verified empirically: `sase init skills --check`
from `/tmp` and from the sase workspace produce the same result at the same cost.

### 1.2 The plan/apply split is already a UI contract

`InitPlan` is a frozen dataclass with `command`, `label`, `summary`, `actions`, `warnings`,
`blockers`, and the derived `has_changes` / `runnable` (`init_plan.py:23-41`). `InitAction`
carries `path`, `operation` (`create|update|overwrite|delete|validate|deploy`), `detail`, and
optionally the full `new_content` (`init_plan.py:13`). That is enough to render a rich
preview *and* a real diff without re-running anything — which is exactly what the CLI does
via `render_plan_inventory` / `render_plan_diff` (`init_preview.py`).

Those two renderers return Rich renderables and would drop into a Textual `Static`
unchanged, except that `_display_path` relativizes against `Path.cwd()` (`init_preview.py:50`)
— fine in a subprocess, wrong in the TUI process.

`sase/doctor/checks_config_init.py:22` already proves the contract is machine-consumable: it
loops `iter_init_command_specs()`, calls `spec.plan(args)`, and emits a JSON-serializable
`data={"planners": [...]}` payload with per-planner `summary`, `actions`, `action_count`,
`warnings`, and `blockers`. `sase doctor -C config.init -j` returns that today.

### 1.3 Interactivity is load-bearing, and partly non-bypassable

Bare `sase init` prompts once per changed plan with `[y/N/d]`, where `d` renders the full
diff and re-asks (`_prompt_for_plan`, `init_onboarding.py:148`). The prompt text is
context-sensitive: memory warns it "may commit and push", repo warns it "may create and push
to a provider sidecar repository".

`--yes` bypasses that generic prompt (`init_onboarding.py:289`). It does **not** bypass:

- **Provider sidecar creation.** `_confirm_sidecar_creation` refuses outright without a TTY:
  `"error: <provider> sidecar repository creation cancelled: interactive y/yes confirmation
  is required"` (`_repo_init_sidecars.py:128-167`). The agents sidecar variant degrades to a
  warning and continues (`:170-199`).
- **Owner identity creation/migration.** `run_config_init` checks `stdin.isatty()`
  (`config_init_handler.py:479-480`).

`docs/init.md` calls this out as intentional: *"`--yes` can run the repository initializer,
but it cannot approve creation of a missing provider sidecar."*

The coordinator does expose an injection seam — `_apply_args` sets `_init_input_func` and
`_init_stdin` on the namespace (`init_onboarding.py:195-196`), consumed by every prompt site.
A TUI could in principle bridge those to modals. §5 option C explains why that is the wrong
trade.

### 1.4 `--all` is a cwd-walk, not a project selector

`run_init_onboarding_all` (`init_onboarding.py:493`) resolves enabled, non-`home`,
non-system-managed main projects through `resolve_init_project_inventory()`
(`init_project_scope.py:97`), then for each one:

```python
with _working_directory(target.workspace_dir):
    result = _run_init_onboarding_result(_project_args(args), ..., manage_chezmoi_deploy=False)
```

Two consequences matter:

- **`manage_chezmoi_deploy=False` per project, one `defer_chezmoi_deploy()` around the whole
  loop** (`:515`, `:551`). The batch deliberately collapses N chezmoi deploys into one, and
  handles `LockTimeoutError` for the whole batch (`:568`). Any design that runs N separate
  init processes loses that and invites lock contention.
- **There is no way to init project X without being in X's directory.** `--all` is
  all-or-nothing; there is no `--project`. That is the gap the TUI's "initialize this one
  project" gesture runs straight into.

The batch produces an aggregate status line — `"Initialization summary: 3 checked, 1 current,
1 initialized, 1 needs attention"` (`_summary_parts`, `:465`) — and returns non-zero if
anything was cancelled, failed, unavailable, or still needs attention.

### 1.5 Measured cost

On `apollo`, warm, against the live install. Baseline `sase version` = **1.22 s**, so the
"work" column subtracts CLI startup:

| Command | Wall | ≈ work |
| --- | --- | --- |
| `sase version` (baseline) | 1.22 s | — |
| `sase init config --check` | 2.05 s | ~0.8 s |
| `sase init memory --check` | 3.29 s | ~2.1 s |
| `sase init repo --check` | 1.75 s | ~0.55 s |
| `sase init skills --check` | 8.09 s | ~6.9 s |
| `sase init --check` (all four) | 9.61 s | ~8.4 s |
| `sase doctor -C config.init -j` | 12.23 s | 8.34 s (`duration_ms`) |

**Skills is ~82 % of a check**, and skills + config — the two host-scoped planners — are
~92 %. This machine currently has exactly one enabled main project (`sase project list`), so
`--all` is cheap here today; the design must not assume that stays true.

---

## 2. What the Projects tab is today

`ProjectsPane` (`projects_pane.py:129`) hosts three sub-tabs — Projects / Repos / Workspaces
— in a `ContentSwitcher`, cycled with `[` / `]`. The Projects sub-tab is a summary line, a
filter input, a fixed-width table, a debounced detail panel, and a hint line
(`projects_pane.py:200-227`).

**The action vocabulary is already the right one to extend.** Lifecycle actions target
`_target_records()`, which is "the mark set if any, else the highlighted row"
(`project_list_controller.py:254-267`), and destructive actions route through
`ConfirmActionModal` with `ConfirmKind.DANGER` (`project_management_actions.py:271-330`).
Slow work is already off-thread: inventory counts run in an exclusive thread worker
(`projects_pane.py:354`), current-project resolution in another (`:376`), and detail
repaints go through `DetailPanelDebouncer` (`:250`).

**Key budget.** `ProjectsPaneKeymaps` (`app_keymaps.py:263-286`) currently claims
`j k / [ ] m u e A a d ctrl+d F enter R r w ' p esc c`. `i` and `I` are both free, and `i`
for "init" is the obvious mnemonic. Adding a key means touching four places: the dataclass
(`app_keymaps.py:263`), `_PROJECTS_BINDING_META` (`keymaps/metadata.py:198`), the default
keymap block (`default_config.yml:388`), and the hint line
(`project_management_rendering.py:279`) — whose own comment already says *"This line
already overflows 120 columns"* (`:298`).

**Column budget.** The table is `MARK CUR NAME VCS STATE CLAIMS WS REPOS WARN`
(`column_header_text`, `project_management_rendering.py:155`) at widths 5/4/36/6/13/8/5/7/5
= 89 columns, leaving room for one more short column at a 120-col terminal.

**Snapshot coverage.** Five PNG goldens pin this pane (`config_center_projects_tab`,
`_detail`, `_marked`, `_current`, `_inactive`, in `tests/ace/tui/visual/snapshots/png/`), so
any row or hint change needs `just test-visual --sase-update-visual-snapshots`.

---

## 3. Three hard constraints

**C1 — Planning is cwd-global.** Established in §1.1/§1.4. Any in-process call to
`spec.plan(args)` from the TUI plans *the TUI's* cwd, and any attempt to fix that with
`os.chdir` corrupts every other thread in the app. **Conclusion: subprocess, always.**

**C2 — Some init work requires a real TTY.** Established in §1.3. **Conclusion: the TUI flow
must detect these cases and route them out, not paper over them.** Note also `tui_perf.md`
rule 11: a subprocess that can prompt interactively "seizes the tty and freezes the TUI" —
so a *captured* init subprocess must be started with `stdin=DEVNULL`, which is exactly what
`run_noninteractive` (`noninteractive_subprocess.py:64`) and the proc reporter's streamer
(`session_proc_reporter.py:54`) both already do.

**C3 — Init is far too slow for any implicit path.** ~8.4 s per project. `tui_perf.md` rule 1
forbids subprocesses on the event loop; rule 3 requires slow user-initiated operations to be
tracked procs; rule 11 forbids side-effectful work on keystroke paths. **Conclusion: no
eager per-project drift column, no "check on highlight", no init work that the user did not
explicitly ask for.**

---

## 4. What "visually appealing" already means in this codebase

Three existing precedents, in decreasing order of relevance.

### 4.1 The Updates tab — the house pattern for a confirmed slow mutation

`action_update_sase` (`plugins_browser_sase_update.py:78`) does exactly four things:

1. Kick off a **preview worker** off-thread (`_start_sase_update_preview`, `:90`).
2. On result, open **`PluginActionConfirmModal`** — a reusable, purely presentational modal
   that shows *the exact argv that will run* plus a structured preview
   (`plugin_action_confirm_modal.py:97`). Its module docstring states the design decision
   outright: *"The confirmation **is** the dry-run — both safer and more discoverable than a
   hidden mode."* It supports `PluginActionPreviewSection` / `PluginActionPreviewComponent`
   rows with `update|current|skipped` states, an incoming-commits loader, and `y`/`n`/`esc`
   plus `ctrl+d`/`ctrl+u` scrolling.
3. On confirm, **submit a tracked proc** via `app._submit_session_worker(...)` with
   `display_name`, `cl_name`, `dedup_key`, `exclusive_scopes`, and `on_complete`
   (`_proc_action_submission.py:199`; call site `plugins_browser_sase_update_procs.py:101`).
4. Toast the outcome from `on_complete` and refresh in place.

The proc body receives a `SessionProcReporter` with `phase()`, `section()`, `log()`,
`set_command()`, and `run(argv, cwd=..., env=...)` which streams combined stdout/stderr line
by line into the proc's bounded live log (`session_proc_reporter.py:140-178`). That log is
what the **Procs** tab renders, and the proc indicator counts it at quit. This is free,
already-built, live progress UI.

### 4.2 The Memory panel — `sase init`'s sibling already runs this way

`sase memory init` is *already* invoked from the TUI. `memory_publish_argv` builds
`sase memory init --message <subject>` or `--no-commit` (`memory_panel_publish.py:36`),
`memory_publish_cwd` picks the scope's content root (`memory_panel_publish.py:43`), a
modal collects the commit decision, and `_submit_memory_publish` submits a session worker
keyed `dedup_key=f"memory-publish:{scope.key}"` with
`exclusive_scopes=(f"memory-write:{scope.key}",)`
(`memory_panel_publish_actions.py:111-141`). The body calls `run_noninteractive(argv, cwd=cwd)`
(`memory_panel_write.py:242`) and failures are compressed to a toast-sized stderr tail
(`format_memory_publish_failure`, `memory_panel_publish.py:82`).

**This is a direct precedent for "run an init subcommand as a subprocess with an explicit
cwd from the Admin Center", and it validates every part of the recommended design.** The one
thing to improve on: it uses `run_noninteractive` (captured, no live output) rather than
`reporter.run()` (streamed into the Procs tab). For a 10-second-per-project operation,
streaming is worth it.

### 4.3 The pane's own `$EDITOR` escape — the precedent for suspend

`action_edit_project_spec` acquires an edit lock, `with self.app.suspend():` runs `$EDITOR`,
releases the lock, reloads records, and repaints (`project_management_actions.py:178-220`).
It also handles `SuspendNotSupported`. That is the exact shape of the terminal fallback in
§6.5.

### 4.4 The Update panel — the precedent for cached freshness

`UpdatePanelState` carries `freshness_label` and `stale`, computed from snapshot ages with a
30-minute staleness horizon (`update_panel_state.py:24`, `:83`). Rows carry a chip whose kind
is `available | current | unknown | failed`. That vocabulary maps cleanly onto init drift and
is worth reusing rather than reinventing (§6.4).

---

## 5. Options considered

### A. Suspend and hand the user the real CLI

`with app.suspend(): subprocess.run(["sase", "init"], cwd=workspace)`.

- **For:** perfect fidelity — every prompt, the `d` diff, sidecar creation, owner identity.
  ~30 lines. No CLI changes. Precedent at `project_management_actions.py:206`.
- **Against:** it is not a TUI feature, it is an exit from the TUI. No progress inside the
  app, no proc record, no dedup, nothing to look at for 10 s × N projects, and the whole app
  is frozen meanwhile. Fails the "visually appealing" requirement on its own.
- **Verdict:** wrong as the primary flow, **right as the fallback for C2 cases.**

### B. Non-interactive tracked proc

`sase init --yes` (or `--all --yes`) submitted through `_submit_session_worker`, streamed by
`reporter.run(...)`, rendered live in the Procs tab.

- **For:** identical in shape to every other Admin Center mutation (§4.1, §4.2). Live output,
  dedup, exclusive scopes, quit-time accounting, completion toast — all free. Never blocks
  the event loop.
- **Against:** `--yes` cannot create sidecars or set up owner identity (C2); those runs fail
  with a stderr line the user must then act on elsewhere. `--yes` is also blunt: no per-spec
  opt-out, unlike the CLI's per-plan `[y/N/d]`.
- **Verdict:** **the right primary flow**, provided the preview stage surfaces C2 blockers
  *before* the run and offers option A for them.

### C. Bridge the CLI prompts into TUI modals

Run the coordinator in-process in a worker with `_init_input_func` injected
(`init_onboarding.py:195`), pushing a modal per prompt via `call_from_thread`.

- **Against:** requires `os.chdir` for project scoping (C1) — disqualifying on its own. Even
  ignoring that, the sidecar guard is `stdin.isatty()`, not the injected `input_func`
  (`_repo_init_sidecars.py:138`), so the highest-value interactive path *still* refuses.
  Blocks a worker thread on UI round-trips, and `tui_perf.md` rule 4 (re-capture UI state
  after every await) makes multi-prompt bridging fragile.
- **Verdict:** reject.

### D. A per-spec matrix UI (4 planners × N projects, checkboxes)

- **Against:** the specs must run in registry order anyway (`init_registry.py:26-31`), two of
  the four are host-scoped so per-project cells are mostly duplicates (§1.1), and the
  cardinality does not justify it. Same mistake the Updates tab's three sub-tabs make
  (see the sibling report `admin_center_updates_tab_unification.md`).
- **Verdict:** reject.

### E. N per-project procs for the "all" case

- **Against:** each process redoes ~7.7 s of identical host-scoped planning (§1.5), and each
  runs its own chezmoi deploy instead of the one batched deploy the coordinator already
  performs (`init_onboarding.py:515`), risking `LockTimeoutError` contention that the CLI
  path is specifically written to avoid (`:568`).
- **Verdict:** reject. **One proc, always.**

---

## 6. Recommendation

**One gesture, one preview modal, one proc, and one honest exit to the terminal.**

### 6.1 The gesture

Two new keys on the Projects sub-tab, both gated into `_PROJECT_ONLY_ACTIONS`
(`projects_pane.py:140`) so they are inert on the Repos/Workspaces sub-tabs:

| Key | Action | Target |
| --- | --- | --- |
| `i` | `initialize_project` | `_target_records()` — the mark set if any, else the highlighted row |
| `I` | `initialize_all_projects` | every enabled main project (maps to `--all`) |

Reusing `_target_records()` (`project_list_controller.py:254`) is the whole point: `m`/`u`
marking already means "the set the next action applies to" for enable/disable/delete, and
init inherits that meaning for free, with no new selection concept to learn. Disabled and
system-managed rows in the mark set are filtered out with a status message, matching
`--all`'s own inventory rule (`init_project_scope.py:112-120`).

`Enter` stays `default_project_action` (enable). Init is never implicit.

### 6.2 The preview modal

A worker plans off-thread, then pushes **`InitPlanModal`**, built on the same bones as
`PluginActionConfirmModal` (`plugin_action_confirm_modal.py:97`) — reuse it directly if the
existing `PluginActionPreviewSection` shape fits, subclass it if not. It shows:

- **The exact argv**, verbatim, as the Updates tab does: `sase init --project sase --yes`, or
  `sase init --all --yes`. The confirmation *is* the dry run.
- **One section per project** (one section when a single project is targeted), each with
  **four component rows** — Config, Memory, Repos, Skills — carrying the planner `summary`
  and an `update | current | skipped` state derived from `has_changes` / `runnable`. This is
  the CLI's own "Up to date / Needs attention" grouping (`_render_plans`,
  `init_onboarding.py:73`, `:90`, `:98`) rendered as a table instead of a scroll.
- **Warnings** in yellow and **blockers** in red, verbatim from the plan.
- `d` to expand full diffs, mirroring the CLI's `[y/N/d]` third answer. `InitAction` already
  carries `new_content`, so the diff needs no second pass (`init_plan.py:19`).
- Footer: `y` run · `d` diff · `t` run in terminal (only when §6.5 applies) · `esc` cancel.

Visual grammar comes free from the existing operation glyphs — `+` create (green), `~`
update/overwrite (yellow), `−` delete (red), `●` validate/deploy (cyan)
(`init_preview.py:28-35`) — and from `update_accents.py`.

### 6.3 The proc

On confirm, submit **exactly one** session worker:

```python
submit(
    "sase-init",
    proc,
    display_name="sase init",
    cl_name=<project display name | "all projects">,
    dedup_key=f"sase-init:{scope_key}",
    exclusive_scopes=("sase-init",),
    on_complete=self._on_init_complete,
)
```

The body calls `reporter.set_command(argv)` then `reporter.run(argv, cwd=...)`, so the
coordinator's own output — the per-project `"Project: <ref>"` headings
(`_render_project_heading`, `init_onboarding.py:456`) and the final
`"Initialization summary: ..."` line (`:583`) — streams live into the Procs tab. Parse the
`Project:` headings into `reporter.phase(...)` calls for a readable one-line status in the
proc indicator.

`exclusive_scopes=("sase-init",)` prevents two concurrent inits in one session. Cross-process
races are already covered by the chezmoi lock and its `LockTimeoutError` handling
(`init_onboarding.py:568`); do **not** try to re-implement that in the TUI.

`on_complete` toasts the summary, then repaints the pane and refreshes the cached drift
column (§6.4), following the `_on_memory_publish_complete` shape
(`memory_panel_publish_actions.py:143`).

### 6.4 The `INIT` column — cached only, never eager

Add one short column between `STATE` and `CLAIMS`, ~7 wide (§2 leaves room):

| Cell | Meaning |
| --- | --- |
| `—` | never checked this session |
| `ok 4m` | last check was clean, 4 minutes ago |
| `3 ▲ 1m` | 3 planned actions pending |
| `blocked` | plan reported a blocker |
| `…` | a check/run proc is in flight for this project |

**Nothing ever populates this implicitly.** Values come only from a check the user asked for
(`i` opening the modal is a check) or from a completed run. Ages and the `stale` notion reuse
`UpdatePanelState`'s vocabulary (`update_panel_state.py:24`, `:83`). Cache lives in
`ProjectsSessionState` (`config_center_session.py`) so it survives closing and reopening the
Admin Center within a session, exactly as the sub-tab bookmarks and project filters do.

This directly satisfies C3 and `tui_perf.md` rules 1/8/11: no render path stats anything, no
keystroke spawns a subprocess, and the column is a pure read of already-computed state.

### 6.5 The terminal fallback

When the plan carries a blocker whose text matches the TTY-only families — sidecar creation
(`_repo_init_sidecars.py:128`) or owner identity (`config_init_handler.py:479`) — the modal
gains a **"Run in terminal (`t`)"** button. Choosing it:

1. Dismisses the modal and the Admin Center.
2. `with self.app.suspend():` runs `sase init` **without** `--yes`, with `cwd` set to the
   project workspace, inheriting the real terminal.
3. On return, reloads records, invalidates the cached `INIT` cell, and repaints.

Handle `SuspendNotSupported` and `OSError` the way `action_edit_project_spec` does
(`project_management_actions.py:210-215`). For the `--all` case, offer this only for the
subset of projects that reported TTY-only blockers.

This is the design's honesty valve: rather than pretending `--yes` is complete, the TUI names
the one thing it cannot do and hands the user the tool that can.

### 6.6 Two CLI additions (both independently useful)

Per `sase/memory/cli_rules.md`: every public long option gets a short alias, options stay
alphabetical in help, and options are never required.

**`-p, --project NAME` on `sase init`** (repeatable), added to the existing
`project_scope_group` mutually-exclusive group alongside `-a/--all` and `-M`
(`parser_init.py:110-119`). Implementation is small: `resolve_init_project_inventory()`
already returns every target with its `workspace_dir` (`init_project_scope.py:97`); filter it
by name/alias and reuse `run_init_onboarding_all`'s loop verbatim. This buys three things:

- The TUI never sets a cwd — the CLI chdirs inside its own process, where it is safe (C1).
- Marked-set init becomes one process with one batched chezmoi deploy (defeats option E).
- `sase init -p foo` becomes possible from anywhere on the CLI too, which is a real gap today.

**`-j, --json` on `sase init --check`.** Emit the `InitPlan` set as JSON — per project, per
planner: `command`, `label`, `summary`, `actions[{path, operation, detail}]`, `action_count`,
`warnings`, `blockers`, plus a top-level status. The serializer already exists in all but
name at `doctor/checks_config_init.py:111` (`_plan_row`); lift it into `sase/main/init_plan.py`
and have doctor call the shared version. Without this, the modal has to screen-scrape
`_render_plans` output or infer everything from an exit code that cannot distinguish "has
drift" from "has blockers" (both return 1, `init_onboarding.py:271`).

**On the Rust-core boundary:** by the `rust_core_backend_boundary` litmus test, "what would
`sase init` do to project X" is shared backend behavior that another frontend would need to
match. But init planning is irreducibly Python-side — chezmoi, Jinja skill rendering, the
xprompt loader, prettier. The correct expression of that principle here is **to make the
`sase` CLI itself the shared API** (`--project` + `--json`), and to keep the TUI a consumer
of it, rather than to port planners to `sase-core` or to duplicate planning logic in
`sase/ace/`. The recommendation contains **zero** re-implemented init logic in the TUI.

### 6.7 Feature flag?

Not required. Per `sase/memory/sase_flags.md`, a flag is for *unproven behavior landed ahead
of readiness* or *a deprecation whose old branch must stay reachable*. This adds a new,
opt-in keybinding that changes nothing existing and removes no branch. Flag it only if it
lands as an incomplete phase of a multi-phase epic (e.g. the keys land before the modal), in
which case a `beta` flag created with `sase flag new` is epic scaffolding to be deleted before
the epic lands.

---

## 7. Implementation sketch

**Phase 1 — CLI (`src/sase/main/`).** Add `-p/--project` to `register_init_parser`
(`parser_init.py:99`) and a `run_init_onboarding_selected(...)` in `init_onboarding.py` that
shares `run_init_onboarding_all`'s loop and batched deploy. Add `-j/--json`; lift `_plan_row`
out of `doctor/checks_config_init.py:111` into `init_plan.py` and have both callers use it.
Wire dispatch in `entry.py:265` (which already errors on `--all` + explicit subcommand and
needs the same guard for `--project`). Update `docs/init.md` and `docs/cli.md`.

**Phase 2 — TUI plumbing (`src/sase/ace/tui/modals/`).** New `projects_pane_init.py` holding
an `InitPlanScope` dataclass, `init_argv(scope, *, check, json)`, a plan worker that calls
`run_noninteractive` and parses the JSON, and the `InitPlanModal`. New
`projects_pane_init_actions.py` mixin with `action_initialize_project` /
`action_initialize_all_projects` and `_submit_init_proc` / `_on_init_complete`, mixed into
`ProjectsPane` (`projects_pane.py:129`). Model both files on the memory-publish pair
(`memory_panel_publish.py` + `memory_panel_publish_actions.py`), which is the closest
existing analogue.

**Phase 3 — Presentation.** Keymap fields in `app_keymaps.py:263`, meta rows in
`keymaps/metadata.py:198`, defaults in `default_config.yml:388`, the `INIT` column and cell
renderer in `project_management_rendering.py:155`, hint-line entries at `:301` (budget is
tight — the source already flags the overflow at `:298`), cached-drift fields in
`ProjectsSessionState`, and a CSS block near `styles.tcss:7938`.

**Phase 4 — Verification.** Unit tests for `init_argv` scope→argv mapping, JSON plan parsing,
TTY-blocker detection, and mark-set filtering of disabled projects. A Textual pilot test for
`i` → modal → confirm → proc submission (assert one proc, correct `dedup_key`,
`exclusive_scopes`). Refresh the five projects PNG goldens with
`just test-visual --sase-update-visual-snapshots`. `just check` during work; `just check-full`
through `/sase_monitor` before landing (`sase/memory/lint_and_test.md`).

---

## 8. Risks and open questions

1. **`--yes` semantics for `memory`.** Memory init commits and pushes by default; the CLI
   prompt warns about this explicitly (`init_onboarding.py:159`). The modal must carry the
   same warning prominently. Consider whether the TUI's default should pass `--no-commit` and
   offer commit as a separate confirmed choice, the way `MemoryPublishModal` already splits
   "Publish & commit" from "Publish only" (`memory_panel_publish.py:172-181`).
2. **Timeout.** `run_noninteractive` defaults to a 900 s cap
   (`noninteractive_subprocess.py:11`). At ~10 s per project that is ~90 projects; fine, but
   `reporter.run(timeout=...)` should be set explicitly rather than left implicit.
3. **Cancellation.** `SessionProcReporter` carries a `cancel_event` and the streamer kills the
   process group on cancel (`session_proc_reporter.py:78-84`), so the Procs tab's `K` kill
   already works. Confirm that a killed init leaves no half-written chezmoi state — worth an
   explicit test.
4. **Host-scoped duplication.** Even with one proc, `--all` re-plans config and skills once
   per project inside the coordinator (§1.5). Hoisting the two host-scoped specs out of the
   per-project loop would cut an N-project run by roughly `(N−1) × 7.7 s`. That is a genuine
   CLI-side improvement, orthogonal to this feature, and probably worth its own task bead.
5. **Sidecar-blocker detection is string matching.** Matching blocker text is brittle. The
   `--json` payload should carry a structured `requires_tty: true` marker per planner rather
   than making the TUI grep prose.
6. **Hint-line overflow.** The Projects hint line already exceeds 120 columns by its own
   admission. Adding `i init` / `I init all` may require dropping or abbreviating a segment;
   decide that deliberately rather than letting it truncate.

---

## 9. Summary of the recommendation

- `i` initializes the marked set or the selected project; `I` initializes all enabled
  projects. Init is never implicit and never runs on a keystroke path.
- Both plan off-thread via `sase init --check --json`, then show an `InitPlanModal` that
  displays the exact argv and per-planner rows — the confirmation is the dry run.
- Confirm submits **one** tracked proc running `sase init --project ... --yes` or
  `sase init --all --yes`, streamed live into the Procs tab with `reporter.run()`.
- A TTY-only blocker adds a "Run in terminal" button that `app.suspend()`s into the real
  interactive `sase init`.
- An `INIT` column shows only cached, user-requested results with an age.
- Two small CLI additions — `-p/--project` and `-j/--json` — keep every line of init logic on
  the CLI side of the boundary and are useful on their own.
