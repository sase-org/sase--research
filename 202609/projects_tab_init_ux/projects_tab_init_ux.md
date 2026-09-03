---
create_time: 2026-09-03
updated_time: 2026-09-03
status: research
---

# Invoking `sase init` From The Admin Center Projects Tab

**Research question:** let users invoke `sase init` from the **Projects** tab of the
SASE Admin Center, for one project or for all projects (`-a|--all`), in a visually
appealing way. What is the best UX, and what is the right way to build it?

**Provenance:** consolidated from two independent research reports —
`projects_tab_init_ux__a.md` (codex) and `projects_tab_init_ux__b.md` (claude) — plus a
lead-researcher verification pass over `sase` at `9e2d95bb0`. Every structural claim
below was re-checked against source; corrections to the source reports are flagged
inline. Timings are report B's measurements on `apollo`.

---

## Executive summary

Both researchers independently converged on the same skeleton, which should be treated
as settled:

> `i` / `I` on the Projects sub-tab → a read-only plan computed **off-thread in a child
> process** → a native **preview modal** in the house "the confirmation is the dry-run"
> style → on confirm, **exactly one** tracked proc running the existing CLI coordinator,
> streamed live into the Procs tab → toast, refresh in place. Init is never implicit,
> never eager, never in-process, and never N procs.

They disagreed on four points — mark semantics, an INIT column, session vs durable
procs, and how far to go on a structured contract. Each is resolved in §4 with the
evidence that decided it.

**The recommendation (§6):** `i` initializes the marked set or the highlighted project
(the pane's existing `_target_records()` semantics); `I` maps to the canonical
`sase init --all` inventory. Both plan via `sase init --check --json` in a subprocess,
then open an `InitPlanModal` (built on `PluginActionConfirmModal`'s bones) showing the
exact argv, per-project sections with the four planner rows, warnings/blockers verbatim,
`d` for full diffs, and a specific primary button ("Initialize sase", "Initialize 5
runnable projects"). Confirm submits one session-worker proc running
`sase init -p <names> --yes` or `sase init --all --yes` via `reporter.run()`. Plans
whose blockers are TTY-only grow a **"Run in terminal"** button that `app.suspend()`s
into the real interactive `sase init`. Two small CLI additions make all of this clean
and are independently useful: **`-p/--project`** (repeatable project selector) and
**`-j/--json`** on `--check` (structured plan output with typed `requires_tty`
markers). Zero init logic is re-implemented in the TUI.

---

## 1. Three hard constraints (verified)

**C1 — Init planning is cwd-global; `--all` is a cwd-walk.** Planners read `Path.cwd()`
process-globally, and `run_init_onboarding_all` scopes each project by `os.chdir`-ing
the whole process (`_working_directory`, `src/sase/main/init_onboarding.py:430-437`).
Calling the planners or coordinator in a TUI thread would plan the wrong directory or
corrupt every other thread's relative paths. **The TUI must shell out, always.**

**C2 — Parts of init are non-bypassable-interactive by design.** `--yes` skips the
generic per-plan `[y/N/d]` prompt but explicitly cannot authorize creating a missing
provider sidecar repository, and owner-identity setup gates on a TTY
(`_repo_init_sidecars.py:138`, `config_init_handler.py:480`; `docs/init.md` documents
this as intentional). A TUI-only flow can never be complete; it needs an honest exit,
not a workaround.

*Correction to report B:* the sidecar guard checks
`getattr(args, "_init_stdin", None) or sys.stdin` before `isatty()`, so the
coordinator's injection seam (`_apply_args` sets `_init_input_func` / `_init_stdin`,
`init_onboarding.py:195-196`) **is** honored there. Prompt-bridging (option C in §3)
remains rejected — but on C1 grounds, not because the seam can't reach the prompt. The
seam also matters later: it is a ready-made channel if structured approvals ever need to
answer prompts inside a child process.

**C3 — Init is too slow for any implicit path.** Measured: ~8.4 s of work per project
check (config ≈ 0.8 s, memory ≈ 2.1 s, repo ≈ 0.55 s, skills ≈ 6.9 s), on top of ~1.2 s
CLI startup. **~92 % of that is host-scoped** (config and skills plan the same result
regardless of project), so per-project drift can never be computed eagerly for the list
(`tui_perf.md` rules 1, 8, 11), and running `--all` as N per-project procs would redo
~7.7 s of identical work N times **and** race N chezmoi deploys that the coordinator
deliberately batches into one (`defer_chezmoi_deploy`, `init_onboarding.py:515`) with
`LockTimeoutError` handling for the whole batch (`:568`). **One proc, always.**

Two more verified facts shape the design:

- **`--check`'s exit code conflates drift and blockers** — both return 1
  (`init_onboarding.py:364-371`). Structured output is required to tell them apart.
- **Apply re-plans fresh.** `_run_init_onboarding_result` runs `_plan_specs` and applies
  those fresh plans in the same invocation (`init_onboarding.py:351`). A TUI-submitted
  `--yes` proc therefore never applies a stale plan; it applies the current world, which
  may differ from what was previewed. That is the CLI's own trust model (a human running
  `--check` then `init --yes` has the same window), and it bounds how much race-safety
  machinery v1 actually needs (§4.3).

## 2. What already exists to build on

The Admin Center has every piece of this feature already built, each verified:

- **The confirm-preview pattern.** The Updates tab's `PluginActionConfirmModal` shows
  the exact argv plus a structured preview; its docstring states the design decision:
  *"The confirmation **is** the … `--dry-run` — both safer and more discoverable than a
  hidden mode"* (`plugin_action_confirm_modal.py:1-15`). Flow precedent:
  preview worker → modal → tracked proc (`plugins_browser_sase_update.py:78`,
  `update_run.py:79-190`).
- **The subprocess-with-explicit-cwd precedent.** The Memory panel already runs
  `sase init`'s sibling (`sase memory init`) as a session worker with an explicit `cwd`,
  dedup key, and exclusive scope (`memory_panel_publish_actions.py:111-141`). The one
  thing to improve on: it captures output; init should stream via `reporter.run()`
  (`session_proc_reporter.py:140-178`) so the Procs tab shows live progress.
- **The suspend precedent.** `action_edit_project_spec` runs `$EDITOR` under
  `with self.app.suspend():` with `SuspendNotSupported`/`OSError` handling
  (`project_management_actions.py:178-220`) — the exact shape of the terminal fallback.
- **Mark-set targeting.** `_target_records()` returns the mark set if any, else the
  highlighted row (`project_list_controller.py:253-267`); enable/disable/delete all use
  it, destructive paths confirm through `ConfirmKind.DANGER` modals, and the hint line
  itself advertises `marked:N (a/d/ctrl+d target marked set)`
  (`project_management_rendering.py:320-330`).
- **A machine-readable plan, almost.** `sase doctor -C config.init -j` already
  serializes `InitPlan`s via `_plan_row` (`doctor/checks_config_init.py:111`) — per
  planner: summary, actions `{path, operation, detail}`, counts, warnings, blockers.
  *Caveat found in verification:* `_plan_row` truncates `actions` to `MAX_DETAIL_ROWS`;
  the lifted shared serializer must not (or must mark truncation explicitly).
- **Key and column budget.** `i` and `I` are both free in `ProjectsPaneKeymaps`
  (`app_keymaps.py:263-286`). The fixed-width table occupies 89 of 120 columns. The hint
  line's own comment says it already overflows 120 columns
  (`project_management_rendering.py:298-300`).
- **The plan model is UI-ready.** `InitPlan` carries command/label/summary/actions/
  warnings/blockers with derived `has_changes`/`runnable`; `InitAction` carries path,
  operation (`create|update|overwrite|delete|validate|deploy`), detail, and optional
  `new_content` — enough for a rich preview *and* full diffs with no second pass
  (`init_plan.py:13-41`). The CLI's glyph vocabulary (`+` green create, `~` yellow
  update/overwrite, `−` red delete, `●` cyan validate/deploy) carries over
  (`init_preview.py:28-35`).

## 3. Options both reports rejected (agreed, verified)

| Option | Why rejected |
|---|---|
| Suspend into interactive `sase init` as the *primary* flow | An exit from the TUI, not a TUI feature: no preview, no proc record, app frozen for ~10 s × N. Right only as the C2 fallback. |
| Bare `sase init --yes` proc with no preview | Blind mutation; C2 paths fail with a stderr line the user must decode elsewhere. |
| Bridge CLI prompts into TUI modals (in-process coordinator + injected input) | Requires `os.chdir` for scoping — disqualified by C1 alone. Also fragile multi-prompt thread round-trips (`tui_perf.md` rule 4). |
| Eager INIT drift column / check-on-highlight | ~8.4 s per project of side-effect-free but slow work; violates `tui_perf.md` rules 1/8/11. |
| 4-planners × N-projects matrix UI | Registry order is fixed; two of four planners are host-scoped so cells are duplicates; cardinality unjustified. |
| N per-project procs for "all" | Redoes ~7.7 s host-scoped work per project; races chezmoi deploys the coordinator batches (C3). |

## 4. Where the reports disagreed, and the resolutions

### 4.1 Should `i` respect marks? — Yes (report B), with report A's safeguards

Report A wanted `i` to mean strictly the highlighted row, arguing marks would create a
third scope that bare `sase init` cannot express, and that stale marks below the fold
could surprise. Report B wanted `_target_records()` for consistency with every other
lifecycle verb.

**Resolution: use `_target_records()`.** The evidence favors B: mark-set targeting is
the pane's established, *surfaced* contract (the hint line literally documents "target
marked set"), and A's stale-marks hazard is defused by the design itself — the preview
modal lists exactly which projects are targeted before anything runs, more explicitly
than enable/disable do today. A's "the CLI cannot express a subset" objection is real
but is resolved by the `-p/--project` CLI addition (§6.6), which makes a marked-set init
one process with one batched chezmoi deploy.

Two of A's safeguards survive intact: **`I` always means the canonical `--all`
inventory** (enabled, non-home, non-system; `resolve_init_project_inventory`,
`init_project_scope.py:97-120`) — never narrowed by marks, filter, or highlight, and the
modal says so; and disabled/system-managed rows in the mark set are filtered out with a
status message, matching `--all`'s own inventory rule. If `-p/--project` were cut from
scope, `i` falls back to highlighted-row-only (A's shape), because marked-set init is
not expressible as one proc without it.

### 4.2 An INIT column? — Cached-only is sound, but defer it out of v1

Report A rejected any column (expensive, stale, crowds a dense list). Report B proposed
a ~7-wide cached-only column (`ok 4m`, `3 ▲ 1m`, `blocked`, `…`) populated **only** by
user-requested checks and completed runs, with ages in the Update panel's freshness
vocabulary (`update_panel_state.py:78-99`, `src/sase/ace/tui/`).

**Resolution: the disagreement is narrower than it looks** — both reject eager checks;
the question is only whether *cached* results earn a column. B's design violates no perf
rule and the column budget exists (89/120 used). But it is fully severable, adds
session-state plumbing, and forces a refresh of all five Projects PNG goldens on day
one. Ship the core flow first; add the cached column as a fast-follow if at-a-glance
drift proves wanted. (If added, cache lives in `ProjectsSessionState` so it survives
reopening the Admin Center within a session.)

### 4.3 Session proc vs durable proc; fingerprint race-safety? — Session worker for v1

Report A proposed a durable supervisor proc (`init.apply`) carrying a preview
fingerprint, with replan-and-abort-on-drift before mutation. Report B proposed a plain
session worker streaming the CLI.

**Resolution: session worker (`_submit_session_worker` + `reporter.run()`).** Three
verified facts decide it:

1. The closest-weight precedents — sase self-update and memory publish — are session
   workers, not durable procs (`update_run.py:103`, `memory_panel_publish_actions.py:116`).
   Durable procs are reserved for supervisor-owned work (agent launches, patch ops, gate
   execution) and require registering a new operation domain with versioned
   request/result models in `sase/ops/commands/` (`coerce_operation_request`,
   `_proc_action_submission.py:66-74`) — real cost.
2. Init from this UI is user-attended: the user just confirmed a modal and the run takes
   seconds-to-minutes. Survival across TUI exit is not load-bearing.
3. The apply re-plans fresh anyway (§1), so the stale-plan failure mode A's fingerprint
   guards against — *applying* an outdated plan — cannot occur. What remains is "what
   runs may differ from what was previewed," which is exactly the CLI's own semantics.

Mitigate the residual gap cheaply: show the plan's timestamp in the modal, and treat a
long-idle modal with suspicion (or simply note that confirm re-plans). A's durable
`init.apply` with fingerprint compare is the documented **escalation path** if
exact-reviewed-plan semantics are ever required (e.g., unattended multi-project init
scheduled from elsewhere); it maps 1:1 onto existing `_submit_durable_proc`
infrastructure and needs no redesign — just don't pay for it now.

Concurrency: `exclusive_scopes=("sase-init",)` prevents two concurrent inits in one
session (deliberately global — selected and all-project scopes share chezmoi
deployment). Cross-process races stay covered by the chezmoi lock and its existing
`LockTimeoutError` handling; do not re-implement that in the TUI.

### 4.4 How deep a structured contract? — The CLI is the shared API; no sase-core port

Report A proposed versioned wire types (scope/preview/requirement/approval/result) in
`sase-core` with Python bindings. Report B argued init planning is irreducibly
Python-side (chezmoi, Jinja skill rendering, xprompt loading, prettier) and the correct
expression of the backend boundary is to make the **CLI itself** the shared API.

**Resolution: report B, for v1.** The `rust_core_backend_boundary` litmus test asks
whether another frontend would need matching behavior *instead of reimplementing it
here* — and this design re-implements nothing: the TUI consumes `sase init --check
--json` and submits `sase init … --yes`, both available to any frontend. Porting four
planners' worth of behavior (or even just their schemas) to Rust for this feature would
be a wholesale migration nobody asked for. A's schema thinking survives in miniature
where it matters: the JSON payload gets a `schema_version`, and blockers carry **typed
markers** (at minimum `requires_tty: true` per planner) rather than making the TUI grep
prose — a point both reports independently arrived at (A's `requirements[]`, B's risk
#5). If the payload later needs cross-language guarantees, promoting that JSON schema
into `sase-core` types is a contained follow-up.

### 4.5 TTY-only paths — suspend valve now, typed requirements later

Report A designed native collection of exceptional inputs (owner identity, sidecar
consent with per-repo fingerprints, memory commit subjects) travelling in the apply
request. Report B designed a "Run in terminal (`t`)" button that `app.suspend()`s into
real interactive `sase init`.

**Resolution: both, sequenced.** V1 ships the suspend valve — it is honest (names the
one thing the TUI cannot do and hands over the tool that can), ~30 lines, and
precedented. The completion toast must never call a held project initialized. A's typed
requirements model is the right end state, because the TUI-only gap bites precisely on
first-time onboarding where this feature is most valuable; the injection seam verified
in §1 (`_init_stdin`/`_init_input_func` honored even by the sidecar guard) means a
future structured-approvals apply can be built without touching the prompt sites. Do not
block v1 on it.

### 4.6 No-op handling — no modal (report A)

When the plan reports everything current, do not open a confirmation dialog for an
empty run. Show status/toast: `sase is initialized · config, memory, repos, and skills
are current` (aggregate counts for `I`). The gesture's intent was "initialize," not
"inspect"; the modal appears only when there is something to confirm or something
blocked to explain.

## 5. Visual design of the modal

Single project (the `--all` variant adds an aggregate line — `8 enabled · 5 need
attention · 2 current · 1 unavailable` — and one collapsible section per project,
changed/held first, current projects summarized in one line):

```text
        ┌─ ↻ Initialize sase ──────────────────────────────────┐
        │ Project  sase                      ENABLED · github   │
        │                                                      │
        │ This can write files and may commit, push, create    │
        │ repositories, or deploy managed files.               │
        │ $ sase init -p sase --yes                            │
        │                                                      │
        │ ┌─ Initialization plan ────────────────────────────┐ │
        │ │ ✓ CONFIG  Current                                │ │
        │ │ ~ MEMORY  1 update · +96 −0                      │ │
        │ │     ~ sase/task_types.json                       │ │
        │ │ ✓ REPOS   Current                                │ │
        │ │ ✓ SKILLS  Current                                │ │
        │ └──────────────────────────────────────────────────┘ │
        │                                                      │
        │  y run · d diff · t run in terminal · esc cancel     │
        │       [ Cancel (n) ]   [ Initialize sase (y) ]       │
        └──────────────────────────────────────────────────────┘
```

Rules, merged from both reports:

- **The exact argv, verbatim** (Updates-tab convention: the confirmation is the dry
  run), *and* a **specific primary button** — "Initialize sase", "Initialize 5 runnable
  projects" — never "OK". When some `--all` targets are held, the button counts only
  runnable ones and the copy says the held projects remain unchanged.
- Four planner rows per project with the planner's own `summary` and an
  `update | current | skipped` state from `has_changes`/`runnable`; current resources
  get one compact reassuring line, never expanded noise.
- Warnings yellow, blockers red, verbatim from the plan. CLI glyph vocabulary
  throughout. Overwrite/delete actions style their section and the primary button as
  the dangerous variant (no name-typing ceremony — a reviewed plan plus a specific
  button is proportionate; remote repo creation gets its own consent instead).
- `d` toggles full unified diffs (`InitAction.new_content` makes this free);
  `ctrl+d`/`ctrl+u` scroll; `t` appears only when a TTY-only blocker is present.
- Memory's "may commit and push" warning from the CLI prompt
  (`init_onboarding.py:148-171`) must appear with equal prominence.

Discoverability: add `i init  I init all` early in the hint line (it already overflows
120 columns per its own comment, so a segment may need abbreviating — decide
deliberately), plus scoped key-help. No permanent buttons or new rows in the main
layout.

Progress: the proc streams the coordinator's own `Project: <ref>` headings and final
`Initialization summary: …` line into the Procs tab; parse headings into
`reporter.phase(...)` for a one-line status (`Project 3 of 8 · chezmoi · memory`). No
fake percentages. Completion toast distinguishes success / no-op / partial
(`Initialized 5 · 2 current · 1 needs attention — see Procs`) / failure, then reloads
the pane inventories preserving selection, filter, and sub-tab. Never auto-switch to
Procs.

## 6. Recommended solution

**One gesture, one preview modal, one proc, one honest exit to the terminal.**

1. **Gesture.** `i` → `initialize_project` targeting `_target_records()` (marked set
   else highlighted row); `I` → `initialize_all_projects` targeting canonical `--all`.
   Both gated into `_PROJECT_ONLY_ACTIONS` (`projects_pane.py:140`) so they are inert on
   Repos/Workspaces. `Enter` keeps meaning enable; init is never implicit.
2. **Plan.** Off-thread subprocess: `sase init [-p <names>…|-a] --check --json`,
   `stdin=DEVNULL`, explicit cwd never inherited from the TUI. Immediate synchronous
   status line ("Checking initialization for sase…"); repeat activation while one is in
   flight warns instead of stacking.
3. **Preview.** `InitPlanModal` per §5, built on `PluginActionConfirmModal`'s bones
   (reuse if `PluginActionPreviewSection` fits, else extract a neutral base — don't leak
   "Plugin" naming into Projects). No-op → toast, no modal.
4. **Apply.** Exactly one `_submit_session_worker` proc:
   `dedup_key=f"sase-init:{scope_key}"`, `exclusive_scopes=("sase-init",)`,
   `reporter.set_command(argv)` + `reporter.run(argv, cwd=…, timeout=explicit)`. Argv is
   `sase init -p <names> --yes` or `sase init --all --yes`. The child re-plans fresh;
   chezmoi batching and lock handling stay in the coordinator.
5. **TTY valve.** When the JSON reports `requires_tty` blockers, the modal offers
   "Run in terminal (`t`)": dismiss, `app.suspend()`, run interactive `sase init` with
   the project cwd, handle `SuspendNotSupported`, reload on return. For `--all`, offer
   it scoped to the blocked subset. Held projects are never reported as initialized.
6. **CLI additions (both independently useful; per `cli_rules.md` conventions).**
   - `-p/--project NAME` (repeatable) in the existing mutually exclusive
     `project_scope_group` beside `-a/--all` (`parser_init.py:114`). Implementation:
     filter `resolve_init_project_inventory()` by name/alias and reuse
     `run_init_onboarding_all`'s loop — batched deploy included. Also closes a real CLI
     gap (`sase init -p foo` from anywhere) and lets the TUI never manage cwd for
     multi-project runs.
   - `-j/--json` on `--check`: lift `_plan_row` out of
     `doctor/checks_config_init.py:111` into `init_plan.py`, **remove the
     `MAX_DETAIL_ROWS` truncation for this consumer** (or mark truncation explicitly),
     add `schema_version`, per-planner `requires_tty`, and a top-level status that
     distinguishes drift from blockers (the exit code cannot). Have doctor call the
     shared serializer.
7. **No feature flag** (per `sase_flags.md`: this is an additive opt-in keybinding, not
   unproven behavior or a deprecation), unless it lands as an incomplete phase of a
   multi-phase epic.

### Implementation phases

1. **CLI** (`src/sase/main/`): `-p/--project`, `-j/--json`, shared serializer, dispatch
   guard in `entry.py` (mirror the existing `--all`+subcommand error), `docs/init.md` /
   `docs/cli.md`.
2. **TUI plumbing** (`src/sase/ace/tui/modals/`): `projects_pane_init.py` (scope
   dataclass, `init_argv()`, plan worker, `InitPlanModal`) +
   `projects_pane_init_actions.py` (actions mixin, `_submit_init_proc`,
   `_on_init_complete`) — modeled on the memory-publish pair, mixed into
   `ProjectsPane`.
3. **Presentation**: keymap dataclass (`app_keymaps.py:263`), binding metadata,
   `default_config.yml` defaults (required by the keymap gotcha), hint line, CSS block,
   help surfaces.
4. **Verification**: unit tests for scope→argv mapping, JSON parsing, `requires_tty`
   detection, mark-set filtering; a pilot test asserting `i` → modal → confirm submits
   exactly one proc with the right dedup/exclusive scopes; refresh the five Projects PNG
   goldens; `just check` while working, `just check-full` via monitor before landing.

### Acceptance criteria (condensed from report A §6, adjusted to resolutions)

- `i` targets marks-else-selection; disabled/system marks filtered with a message; `I`
  ignores highlight/filter/marks entirely.
- Preview never writes; planning/apply never touch the event-loop thread; entering the
  tab performs no init work; a key action updates visible status before any I/O.
- Drift vs blockers distinguished in payload despite both exiting 1; generic `--yes`
  still cannot create a provider sidecar (unchanged CLI guarantee).
- Exactly one proc per confirm; double activation and selected-vs-all overlap produce
  one clear collision warning; kill via the Procs tab works.
- Result distinguishes success / current / needs-attention / failed / cancelled per
  project; selection, filter, and sub-tab survive refresh.
- Snapshots cover: single-project update, all-project mixed status, danger styling,
  TTY-blocked state with `t` button, full-diff expansion, narrow terminal.

## 7. Risks and open questions

1. **Memory commits/pushes under `--yes`.** Bare init's memory step may commit and push;
   advanced controls (`--no-commit`, subjects) live only on explicit subcommands. Should
   the TUI default to the blunt `--yes` semantics (with a prominent warning), or grow a
   commit/no-commit choice like `MemoryPublishModal`? Needs a product decision; the
   warning is mandatory either way.
2. **Cancellation.** The proc streamer kills the process group on cancel; confirm a
   killed init leaves no half-written chezmoi state — worth an explicit test.
3. **Hint-line overflow.** Already over 120 columns; adding two hints means deliberately
   dropping/abbreviating a segment.
4. **Preview/apply drift.** V1 inherits CLI semantics (apply re-plans fresh). If
   exact-reviewed-plan semantics are ever needed, the durable `init.apply` +
   fingerprint design in report A (§5) is the ready escalation path.
5. **Follow-up filed as task bead `sase-w4`:** hoisting the two host-scoped planners
   (config, skills) out of `--all`'s per-project loop would cut an N-project run by
   roughly `(N−1) × 7.7 s` — a pure CLI win, orthogonal to this feature.

## 8. Sources

Full evidence trails live in the sibling reports: `projects_tab_init_ux__a.md`
(wire-contract design, exceptional-input taxonomy, acceptance criteria, GNOME
HIG/clig.dev grounding) and `projects_tab_init_ux__b.md` (timing measurements, scope
analysis of the four planners, house-precedent walkthroughs, phased sketch). Key
file:line citations in this document were independently re-verified at `9e2d95bb0`.
