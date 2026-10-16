# `sase stats project`: share the Statistics Projects view, do not invent a second census

> **Research query:** How should SASE implement `sase stats project` (a new `sase stats` group) so the Admin Center Statistics → Projects sub-tab and the CLI read the same code path, including commits and committed plans broken down by model and provider? Is the plan a good idea? What should change? End with a recommended solution that is intuitive, reliable, and beautiful.

Prior context: `research:202610/project_stats_cli_design/project_stats_cli_design.md` (a repo-truth census designed as `sase project stats`, before these requirements existed).

## Bottom line

1. **Build `sase stats`, and start with `project`.** The long-term shape — one CLI subcommand per Statistics sub-tab, same query as the TUI — is the right product. It is a different product from the earlier `sase project stats` git/LoC census. Keep that census for a later `sase stats repo` (or drop it). Do not fold it into this command.
2. **Invert ownership.** Today the TUI owns orchestration and Rich rendering, and Python already has a clean I/O-free view-model layer on top of two Rust bindings. Move load + render into `sase.stats`. The TUI Projects pane and `sase stats project` become two printers of one object.
3. **The new model/provider numbers already have a home.** Commits come from `meta_commits` on the agent-artifact record; the index already stores `model` and `llm_provider` per run. Committed plans are `agent_meta.plan_committed == true` on that same record. Extend the existing `agent_stats_query_runs` fold. Do not scrape git.
4. **Ship one view, as a template.** Do not implement eight subcommands in the first change. Land the group, `list`, and `project`, with shared flags and a renderer the other views can copy.
5. **The idea is good.** I would change the data source, the command family, the default invocation, and the definition of “plans committed.” Those adjustments are listed in [Requirement adjustments](#requirement-adjustments).

## Is this a good idea

**Yes.** Three properties make it worth doing now.

- **One answer per question.** The Statistics pane already answers “what did agents do in this project?” Agents, scripts, and the launch-post workflow currently re-query or re-derive those numbers. A versioned JSON envelope from the same binding ends that.
- **The TUI is already 80% of a CLI.** `sase.stats.query` talks to `agent_stats_query_runs` / `agent_stats_query_activity`. `build_statistics_views` is I/O-free. The Projects pane paints Rich `Table`/`Panel`/`Group` objects, not Textual widgets. The missing piece is a public command and a renderer that does not live under `ace.tui.modals`.
- **The new attribution is a small, honest fold.** Provider/model are indexed columns. Commit counts are already folded per project and per Patch. Plans-committed is a boolean already projected into `record_json`. This is additive core work, not a new census.

It is **not** a good idea if “project stats” still means “how big is the git tree.” That question is real (the earlier research proved the launch-post numbers drift). It is a different question, with a different clock, a different failure mode, and a different audience. Mixing LoC into the Statistics Projects table would make both answers worse.

### Would I take a different approach

I would still add `sase stats` and still start with Projects. I would not:

- put the command under `sase project` (the user already corrected this; the prior research’s rejection of a top-level `sase stats` was about a *repo-truth* command colliding with agent-run stats — that collision is now the point);
- have the CLI call TUI code, or have the TUI shell out to the CLI;
- add tokei, `git log`, or sidecar file walks to v1;
- implement Overview, Runners, Providers, Activity, Macros, Plans & Questions, and Perf in the same change;
- default a bare `sase stats` to a project table (see A5).

## Critique of the plan in general

The new framing (CLI mirrors the Statistics tab; Projects is the first view; same code path) is stronger than the original `sase project stats` brief. The original brief optimized for a launch-post strip. This one optimizes for a durable, dual-surface product.

Where the combined plan is still weak:

- **“Same code path” is underspecified.** Today the TUI path is `load_statistics_view` → *both* Rust bindings → `build_statistics_views` of *every* view → a Textual mixin that happens to return Rich. A CLI that imported `load_statistics_view` would drag in activity-log scans, a previous-window re-query (Overview deltas), and runner occupancy for a table that uses none of them. Sharing the *Projects* path means extracting a narrower loader, not pointing both surfaces at the fat one.
- **“Migrate the Projects sub-tab” can be read as a rewrite.** The pane’s query is already the right one. The migration is: stop owning the renderer and the loader; keep owning keys, timers, and the tab strip.
- **Commits-by-model and plans-by-model are new facts, not a presentation tweak.** They are absent from `AgentProjectWorkStatsWire`, `AgentCommitStatsWire`, and the Projects legend. They belong in the Rust fold so the TUI cannot drift from the CLI.
- **Eight subcommands is a program, not a PR.** The group and the flag grammar must anticipate them. The implementation must not.

The earlier research is still useful as a *warning*: unlabeled metrics rot. Freeze definitions in `-h`, in the on-screen legend, and in the JSON schema, the way the Statistics pane already does.

## What exists today

Evidence from this checkout, not from the earlier report.

### Statistics is already a product

Admin Center → Statistics (`#`, then `6`) has eight numbered views. Docs: `docs/contribute/telemetry.md`. The Projects view (`03`) “compare[s] run outcomes, commits, Patches, and wall time across projects,” with `g` cycling `project` / `patch` / `drilldown`.

Default range is **7d** (`sase.stats.ranges.DEFAULT_PRESET`). First open may seed the current project when `ace.current_project.seed_filters` is on. Refresh is 30s, off the UI thread (`StatisticsPane._REFRESH_INTERVAL_SECONDS`, `run_worker(..., thread=True)`).

### The stack is already split the right way — except the last mile

| Layer | Owner | Projects uses it? |
| --- | --- | --- |
| SQLite `agent_artifacts` (`model`, `llm_provider`, `record_json`) | sase-core `agent_scan::index` | yes |
| `agent_stats_query_runs` | sase-core `agent_stats::run::query` | yes (work + commits) |
| `agent_stats_query_activity` | sase-core `agent_stats::activity` | **no** |
| `sase.stats.query` | Python adapter | yes |
| `build_projects_view` / `ProjectsView` | `sase.stats._view_builders` | yes |
| `load_statistics_view` | `statistics_pane_data.py` | yes, but also loads activity, previous window, and (for other views) perf |
| Rich table | `statistics_pane_projects.py` mixin | yes |
| CLI | none | — |

`query_run_stats` already selects `model` and `llm_provider` and folds providers for the Providers view. `fold_commits` counts `done.step_output.meta_commits`. `fold_work` attributes those commits to a project and Patch. Neither fold groups commits or committed plans by model/provider.

### Commits in this view are agent-recorded, not git-log

`meta_commits` is a list of `{message, sha, cwd, repo_name, patch_name, ...}` written at finalize (`extract_step_output_and_diff_path`). There is no `model` or `provider` field on the commit object. Attribution v1 **must** be the run’s indexed `model` / `llm_provider`. That matches how the Providers view already groups *runs*.

Git footers have `SASE_AGENT=`, `SASE_TYPE=`, `SASE_PLAN=`, `SASE_BEAD=`. They do **not** have `SASE_MODEL=` or `SASE_PROVIDER=`. A git scrape cannot answer the new question without joining commits back to runs.

### “Plans committed” is already a durable bit

Planner follow-up writes `agent_meta.plan_committed: bool` and may finish with outcome `plan_committed`. These are not the same:

- Outcome `plan_committed` fires even when `commit_plan=False` (no sidecar write). Tests in `tests/test_axe_run_agent_exec_plan_followup_approval_commits.py`.
- The boolean is the “plan document actually committed” signal. `select_canonical_plan_path` treats it as authoritative; `plan_action in {commit, tale, epic}` is only a legacy fallback.

The Plans & Questions view totals **gate bundles** (proposed / approved / rejected / pending). That is a different clock and a different object. Do not reuse it for “plans committed.”

### Existing `* stats` commands are not this product

`sase bead stats`, `sase artifact stats`, `sase tool stats`, `sase prompt stats`, `sase usage` are domain ledgers. Leave them. `sase stats` is the Statistics tab. Help text must say so in the first sentence.

### CLI grammar already tells us how to add the group

- Register in `_COMMAND_REGISTRARS` (`parser_registry.py`), dest `stats`, alphabetically between `stitch` and `sudo`.
- A group with a `list` child defaults to it (`cli_rules.md`, `default_list_subcommands`).
- Every public long option needs a short alias; subcommands and options sort alphabetically; prefer color.
- `-j/--json` is the house style for machine output (`sase tool stats`, `sase artifact stats`, `sase usage`).
- Compact root help is curated (`_COMPACT_ROOT_COMMANDS`); a new user-facing group belongs there.
- Project refs resolve through `ProjectDisplaySnapshot.project_key_for_ref` (display name, alias, or canonical key). Unknown ref → exit 2, matching `sase artifact stats`.

## Requirement adjustments

Each item names the request, then the adjustment and why.

### A1. Command name `sase stats project` (not `sase project stats`)

**Kept.** The Statistics tab is a family. `sase project` is lifecycle (`list`, `add`, `enable`, …). Putting a dashboard under lifecycle would make `sase project` two products and would block `sase stats runners`.

### A2. Long-term: every Statistics sub-tab gets a `sase stats` subcommand

**Kept as the grammar; deferred as implementation.** v1 ships `list` + `project`. The parser reserves the other view ids so the second view is a copy-paste, not a redesign.

Proposed subcommand map (TUI label → CLI):

| # | TUI view | CLI |
| --- | --- | --- |
| — | (catalog) | `sase stats list` (bare `sase stats` delegates here) |
| 01 | Overview | `sase stats overview` |
| 02 | Runners | `sase stats runners` |
| 03 | Projects | `sase stats project` |
| 04 | Providers | `sase stats providers` |
| 05 | Activity | `sase stats activity` |
| 06 | Macros | `sase stats macros` |
| 07 | Plans & Questions | `sase stats plans` |
| 08 | Perf | `sase stats perf` |

Singular `project` is what was asked; the TUI tab stays “Projects.” That matches `sase project` / `sase agent`.

### A3. Migrate the Projects sub-tab onto the CLI’s data source

**Adjusted to:** extract a shared **Projects loader + view model + Rich renderer** in `sase.stats`. Both surfaces call it. The TUI keeps navigation, 30s refresh, grouping keys, and the scope header.

The TUI already uses the right *binding*. What it must stop doing for this view: always calling `query_activity_stats`, always querying the previous window, and keeping the Projects table renderer inside a Textual mixin.

### A4. Track commits by each model/provider

**Adjusted to:** attribute each `meta_commits` entry to the **run’s indexed** `llm_provider` and `model`. Unknown → `"unknown"`, never `0` hiding in a named bucket.

This under-resolves fallback retries (`SASE_MODEL_OVERRIDE` mid-run): the index stores one model per row. That is the same limitation the Providers view already ships. Call it out in the legend.

**Forward write (same change, tiny):** when recording `meta_commits`, copy the active provider/model onto each commit object. The fold prefers per-commit fields and falls back to the run. Old records keep working.

Do **not** parse git footers for this. They do not carry model/provider, and they would disagree with the TUI the moment a commit is missing from `meta_commits`.

### A5. Track plans committed by each model/provider

**Adjusted to:** count **runs** in the window whose `agent_meta.plan_committed` (or `done.plan_committed`) is strictly `true`, grouped by that run’s provider/model.

Do not count:

- outcome `plan_committed` without the boolean (approve-without-commit);
- plan *gate* approvals (Plans & Questions);
- `fold_plans` / `AgentPlanStatsWire` (the wire comments already forbid user-facing use; it under-counts handed-off planners).

JSON also reports `distinct_plan_refs`: unique `SASE_PLAN` destinations parsed from that run’s `meta_commits` messages via `parse_commit_footer`. Human output leads with the boolean count. If the two diverge, the footer says so. Distinct refs can be lower (host-owned sidecar commit not in `meta_commits`) or, rarely, higher (one run, two plan files).

Legend: **Plans committed = runs that committed a plan document (`plan_committed: true`)**.

### A6. Default project scope

**Adjusted to:** no `-p` means **all projects in the index** (the TUI’s “All projects,” and the same as an unfiltered `query_run_stats`). `-p/--project` may be repeated; each value is a display name, alias, or key, resolved then OR-filtered.

**Not** the TUI’s first-open current-project seed. A CLI that silently filters to whatever `sase project current` is would surprise scripts. `-C/--current` opts into that seed.

Disabled projects appear if they have indexed runs. No `-D`. This is an agent-record view, not a lifecycle roster.

### A7. Default time range

**Adjusted to:** **7d**, matching `DEFAULT_PRESET`. `-t/--range {today,24h,7d,30d,90d,all}`. `-c/--custom` accepts the same grammar the TUI already parses (`12h`, `14d`, `8w`, `2026-07`, `2026-07-01..2026-07-18`, `2026-07-01..`).

All-time start is Unix 0; the footer repeats the TUI’s “start bounded by retained data.”

### A8. Output formats

**Adjusted to:** Rich table on a TTY, JSON with `-j/--json`. No CSV, YAML, or JSONL in v1. No `--format` enum.

House style is `-j`. Nested model rows make CSV ugly. Markdown can wait until a second view needs paste-into-chat; `> file.md` of a color table is a bad default.

`auto` that prints Markdown when piped (the earlier research) is attractive for agents. Agents should pass `-j`. Piped table output strips color (Rich’s default) and stays table-shaped.

### A9. Grouping

**Kept, matching the TUI:** `-g/--group {drilldown,patch,project}` (alphabetically `drilldown`, `patch`, `project`; default `project`). Model/provider panels stay at **project and portfolio** grain in v1. Patch rows do not grow model columns until someone asks; the Patch fold has no model key today.

### A10. Repo-truth / LoC / active-days / tokei

**Deferred, and split off.** That is `sase stats repo` (name TBD) if the launch post still needs a frozen git census. It needs canonical clones, three repo tiers, and `parse_commit_footer` over `git log`. None of that is on the Statistics Projects path. Shipping it inside `sase stats project` would make the TUI and CLI *unable* to match.

The inventory bugs the earlier report named (`sase-1lk`, missing linked-repo provenance, `-p` key-only resolver) remain real for a git census. They are out of scope here. The stats CLI resolver uses `project_key_for_ref`, which already accepts names and aliases.

### A11. Bare `sase stats`

**Adjusted to:** delegate to `sase stats list`, with the standard notice. `list` is a catalog of views (id, TUI label, one-line description, whether it is implemented). Unimplemented views print as such and exit 0. That is how a family of eight stays discoverable without dumping a 7-day project table.

## Recommended architecture

```
                    ┌──────────────────────────────┐
                    │  sase-core agent_stats        │
                    │  query_run_stats (wire v9)    │
                    │  work + commits + new folds   │
                    └──────────────┬───────────────┘
                                   │ sase_core_rs
                    ┌──────────────▼───────────────┐
                    │  sase.stats                   │
                    │  query / load / views / render│
                    └───┬─────────────────────┬────┘
                        │                     │
              ┌─────────▼─────────┐   ┌───────▼────────┐
              │ TUI Projects pane │   │ sase stats     │
              │ keys, timer, tabs │   │ project / list │
              └───────────────────┘   └────────────────┘
```

Rust remains the only aggregator. Python remains the only project-ref and timezone layer. Rich remains the only table painter. Textual and argparse do not compute.

### Core (sase-core)

Bump `AGENT_STATS_WIRE_SCHEMA_VERSION` 8 → 9. Additive fields, old readers ignore them, `validate_sase_core_rs` and the Python mirror constant move together. Ratchet `sase-core-revision.txt` in the same sase change.

Extend, do not add a second binding:

```rust
// AgentCommitStatsWire
pub commits_by_provider: Vec<AgentStatsCountWire>,
pub commits_by_model: Vec<AgentStatsCountWire>, // "provider/model" or split fields
pub plans_committed: u64,
pub plans_committed_by_provider: Vec<AgentStatsCountWire>,
pub plans_committed_by_model: Vec<AgentStatsCountWire>,

// AgentProjectWorkStatsWire  (same four breakdowns, plus)
pub plans_committed: u64,
```

A small `AgentAttributionCountWire { provider, model, count }` beats packing `"codex/gpt-5"` into `name`. Use an explicit struct so JSON stays joinable.

Fold in `agent_stats/run/folds.rs` next to `fold_commits` / `fold_work`:

- each `meta_commits` element increments the run’s provider/model buckets (prefer per-commit fields when present);
- if `plan_committed == Some(true)`, increment plans-committed buckets once per run.

Keep the full-table scan in v1. Extra folds are cheaper than a second query. SQL window pushdown (`timestamp` is 14-digit TEXT, not Unix) is a follow-up that would help TUI and CLI together; do not block on it.

Do **not** skip macros/runners inside the scan for v1. One scan, one response, Overview still works. The win is skipping the *other Python queries* when the caller only wants Projects.

### Python facade

New (names illustrative):

- `sase.stats.load.load_projects_stats(range, project_keys) -> ProjectsStats`
- `sase.stats.render.projects.render_projects(view, *, group, width, color) -> Renderable`
- `sase.stats.cli.handle_stats(args)`

`ProjectsStats` wraps `ProjectsView` plus the new portfolio breakdowns plus the resolved `StatsRange` and filter. `build_projects_view` grows the per-project fields.

`load_statistics_view` moves from `statistics_pane_data.py` into `sase.stats.load` and becomes **view-aware**:

| View | `query_run_stats` | `query_activity_stats` | previous window | perf |
| --- | --- | --- | --- | --- |
| projects | yes | no | no | no |
| overview | yes | yes | yes | no |
| runners | yes | no | no | no |
| providers | yes | no | no | no |
| activity | yes (workspaces) | yes | no | no |
| macros | yes | no | no | no |
| plans_questions | yes (run-backed slices) | yes | no | no |
| perf | no | no | n/a | yes |

v1 only has to get the **projects** row right. The table documents the rest so later subcommands do not re-learn it.

TUI `StatisticsProjectsRenderingMixin` becomes a one-line delegate to `sase.stats.render.projects`. Keep the mixin until the other views move; do not drag Overview along.

### CLI wiring

- `src/sase/main/parser_stats.py` + registry entry `"stats"`.
- Dispatch in `entry.py` next to the other groups.
- Add `stats` to `_COMPACT_ROOT_COMMANDS` with summary: “Show Admin Center Statistics views from the same records the TUI uses.”
- Completions: project refs already have a `ValueKind`; range and group are closed enums.

Shared flags (every view subcommand, alphabetical, each with a short alias):

| Flag | Meaning |
| --- | --- |
| `-C, --current` | Filter to the current project |
| `-c, --custom RANGE` | Custom window (TUI grammar) |
| `-g, --group {drilldown,patch,project}` | Projects (and later Macros/Perf) grouping |
| `-j, --json` | Versioned envelope |
| `-p, --project NAME` | Repeatable project filter |
| `-t, --range {today,24h,7d,30d,90d,all}` | Preset (default `7d`) |

`-c` and `-t` conflict; argparse should error rather than silently preferring one.

`sase stats project` takes no positional project argument. Filters are flags. That leaves room for `sase stats project -p sase -p bob-cli` and avoids the `sase project stats [NAME]` shape the earlier research froze.

### JSON envelope

Separate the CLI envelope from the core wire:

```json
{
  "schema_version": 1,
  "command": "stats.project",
  "generated_at": "2026-10-16T15:04:05-04:00",
  "range": {
    "preset": "7d",
    "start_ts": 1760140800,
    "end_ts": 1760745600,
    "label": "…",
    "display_label": "Last 7 days"
  },
  "project_filter": ["gh_sase-org__sase"],
  "group": "project",
  "core_schema_version": 9,
  "view": { }
}
```

`view` is the `ProjectsView` dataclass plus portfolio attribution, with the same field names the TUI already consumes. Agents should key on `core_schema_version` for fold changes and `schema_version` for envelope changes.

Unknown counts are JSON `null` in any future cell that can be unknown (shallow, missing index). Present zeros stay `0` (a project with no commits has zero commits).

### Exit codes

| Code | When |
| --- | --- |
| 0 | Success, including empty ranges and unimplemented catalog rows |
| 2 | Unknown project ref, invalid range/group, `-c`/`-t` conflict |
| 1 | Index unreadable, binding missing, unexpected failure |

Empty is data: print the TUI empty sentence (“No agent runs recorded in Last 7 days.”) and still emit JSON with empty arrays. Never exit 1 because the user was idle.

## CLI design (intuitive, reliable, beautiful)

### Intuitive

- The group is named after the tab. The subcommand is named after the sub-tab. `-t` is the TUI’s `t`. `-g` is the TUI’s `g`. `-p` is the TUI’s project chip.
- `sase stats --help` lists the eight views in TUI order in the description, and argparse’s alphabetical subcommand list in the body. Description does the pedagogy; the option list stays sorted.
- First sentence of `project` help: “Show the Admin Center Statistics → Projects view for a time range.” Second sentence: “Same records as the TUI: agent runs, not git history.” That one line prevents the earlier brief from resurrecting itself in every agent prompt.

### Reliable

- One fold, two printers. A golden test: TUI renderable (stringified Rich) equals CLI table for the same `ProjectsStats` fixture.
- Cross-format: table cells equal JSON `view` numbers.
- Frozen clock in tests (`generated_at`, range bounds).
- Hidden agents stay hidden (`record_is_user_hidden`), same as the pane.
- Malformed `record_json` increments `malformed_rows_skipped` and never becomes a zero.
- Project labels go through `project_display_for`; keys stay canonical in JSON.

### Beautiful

Match the pane’s palette rather than inventing a CLI skin: accent `#FF87D7`, commits `#87D7FF`, success `#5FD75F`, failure `#FF5F5F`, project swatches from `categorical_color(project_key)`.

Human layout (default `-g project`):

```
sase stats project · Last 7 days · 09 Oct 12:00 → 16 Oct 12:00 · All projects

 3 projects · 18 Patches · 6 unattributed runs · 91 commits · 4 plans committed

┌ By Project ─────────────────────────────────────────────────────────────┐
│ ■ sase          142  88%  91  12  4  18h 12m  ████████░░  Oct 16 11:41 │
│   xai    grok-4           40c  2p                                      │
│   anthropic claude-opus   31c  1p                                      │
│   openai gpt-5            20c  1p                                      │
│ ■ bob-cli        11  73%   4   2  0   1h 04m  █░░░░░░░░░  Oct 15 09:02 │
└────────────────────────────────────────────────────────────────────────┘

┌ Commits by model ──────────────┐  ┌ Plans committed by model ─────────┐
│ grok-4           40  ████████  │  │ grok-4           2  ████████░░░░  │
│ claude-opus      31  ██████    │  │ claude-opus      1  ████░░░░░░░░  │
│ gpt-5            20  ████      │  │ gpt-5            1  ████░░░░░░░░  │
└────────────────────────────────┘  └───────────────────────────────────┘

Success = completed ÷ all runs  ·  Wall = summed agent runtime
Commits = meta_commits on runs in range, attributed to the run's model
Plans committed = runs with plan_committed: true
```

Rules:

- Scope line first, dim, same chips the pane’s header uses (Range, Group if not default, Project).
- Summary line second, the pane’s existing `N projects · M Patches · K unattributed` plus the two new totals.
- Exact integers in cells; durations via `format_duration`; percents via the pane’s `_percent`.
- Nested model rows indent under the project when `-g project` and the project has more than one model. A single-model project does not grow a nested row.
- Portfolio model/provider panels always render when there is at least one commit or committed plan. Side-by-side `Columns` when the terminal is ≥ 100 cells; stacked below that.
- Legend last, dim, the existing Projects legend plus the two new lines. No URL dump, no schema sermon.
- `NO_COLOR` / non-TTY: no swatches, no bars, ASCII `+--+` if Rich’s markup is off; numbers unchanged.
- Unimplemented catalog rows in `sase stats list` use a dim “coming” badge, not an error.

`sase stats list` itself should be a small accent-bordered table: `#`, command, TUI label, description. That is the family portrait.

## TUI migration, concretely

1. Move `load_statistics_view` into `sase.stats.load`. TUI imports it.
2. `load_projects_stats` is what both `sase stats project` and the pane call when `_view == "projects"`.
3. Replace `StatisticsProjectsRenderingMixin._projects_*` bodies with calls into `sase.stats.render.projects`. Keep `_projects_group_by` and the legend hook on the mixin until the pane’s other mixins move.
4. When `_view == "projects"`, do not fetch activity, previous window, or perf. This is the user-visible “migration”: the pane gets faster and can no longer disagree with the CLI about which queries ran.
5. New columns/panels in the pane: nested model rows (optional, width-gated) and the two portfolio panels. If the pane feels cramped at the Admin Center’s standard width, show portfolio panels only; keep per-project attribution in JSON and in the CLI. **Do not hide numbers the CLI shows unless the pane literally has no cells.** Prefer a follow-up width breakpoint over two different truths.
6. Update `VIEW_LEGENDS["projects"]` with Commits-by-model and Plans committed. `?` help inherits it.
7. Golden: one fixture, two stringified Rich outputs.

TUI perf rules still apply: the loader stays on `run_worker(..., thread=True)`; the paint path stays Rich-only; do not `query_run_stats` on the pump.

## Tests

**sase-core**

- Run with two models, mixed `meta_commits`, asserts per-project and portfolio buckets.
- `plan_committed: true` vs outcome `plan_committed` with boolean false: only the boolean counts.
- Missing model/provider → `"unknown"`.
- Per-commit `model` field overrides the run when present; absent field uses the run.
- Hidden records excluded.
- Wire v9 round-trip; v8 payload without the new fields still deserializes (defaults empty).

**sase**

- Parser: default list delegation, flag short aliases, `-c`/`-t` conflict, unknown project → 2.
- Handler: empty index → 0 + empty sentence; `-j` envelope keys stable.
- Render golden for `project` / `patch` / `drilldown`.
- TUI pane uses `load_projects_stats` (monkeypatch one function, both surfaces).
- `just check` via `sase tool run`, not `check-full`.

## Docs

New user-visible command: a Reference page (do not grow a Guide). Cross-link [Statistics tab](../../docs/contribute/telemetry.md#admin-center-statistics-tab) from the CLI page and back. Parser descriptions are the source of `-h`; `just fix` regenerates catalogs. Compact root help is hand-curated.

## Risks

| Risk | Mitigation |
| --- | --- |
| Two truths (TUI vs CLI) | One loader, one renderer, one golden |
| “Commits” read as git log | Help sentence + legend + JSON field `meta_commits` heritage in the schema comment |
| Fallback retries mis-attribute commits | Legend; optional per-commit stamp on write |
| `plan_committed` outcome vs boolean | Count only the boolean; test the approve-without-commit case |
| Fat query on every 30s tick | View-aware loader for Projects now; SQL pushdown later |
| Scope creep into eight views | Parser reserves names; implementation ships two |
| Name clash with `sase bead stats` | First-sentence disambiguation; compact help says “Statistics views” |
| Core pin lag | Land core + ratchet + Python in one agent turn / stacked PRs as the rust-core workflow already requires |

## Alternatives considered and rejected

- **`sase project stats`:** Rejected by the new brief, and independently: lifecycle vs dashboard.
- **CLI shells out to a headless TUI / screenshot path:** Fragile, slow, unscriptable.
- **TUI calls the CLI:** Pays argparse and process spawn on a 30s timer; worse than today.
- **Python-only fold of model/provider:** Violates rust-core-required; the scan is already in Rust.
- **New `agent_stats_query_projects` binding in v1:** Two aggregators will drift. Extend the existing response.
- **Git-log attribution via `SASE_PLAN` / `SASE_AGENT`:** Different universe; cannot match the pane; no model tag.
- **Default current project:** Silent filter; scripts would need `--all` to undo a TUI convenience.
- **Four output formats in v1:** `-j` is the house style; CSV fights nested rows.
- **Implementing all eight views at once:** The renderer extraction is the hard part; do it once, well, on Projects.
- **Feature-flagging the pane migration:** The migration is a refactor plus additive columns. A flag that paints two different Projects tables is the bug we are trying to delete.

## Phasing

**v1 (this change) — the template**

1. Core wire v9 + folds + tests.
2. `sase.stats.load` / `render.projects` / `cli`.
3. `sase stats list` and `sase stats project`.
4. TUI Projects consumes the shared loader and renderer; skip unused queries.
5. Compact help, Reference page, goldens, `sase-core-revision.txt`.

**v2 — the family**

One PR per remaining view, in TUI order minus Perf (Perf has extra log/telemetry sources and should go last). Each PR: view-aware load row + renderer extract + subcommand. Flags already exist.

**v3 — optional**

- Per-commit model/provider already stamped in v1 writes; backfill is unnecessary.
- SQL window pushdown.
- Gateway route on the same wire (mobile Statistics).
- `sase stats repo` if the launch post still wants a git census. That work reuses `parse_commit_footer` and the earlier research’s three-tier repo rules, and never feeds the Projects pane.

## Recommended solution

Add a top-level **`sase stats`** group that is the CLI of the Admin Center Statistics tab.

v1 implements:

1. **`sase stats list`** — catalog of the eight views; bare `sase stats` delegates here.
2. **`sase stats project`** — the Projects view for a 7-day (default) window, optional `-p`/`-C` filter, `-g` grouping, `-t`/`-c` range, `-j` JSON.
3. **Shared source** — sase-core `query_run_stats` (wire v9) folds commits and committed plans by provider/model; `sase.stats` loads and paints; the TUI Projects pane and the CLI both call that facade.
4. **Frozen metrics**
   - **Commits:** `len(meta_commits)` on in-window, non-hidden runs, attributed to the run’s indexed provider/model (per-commit override when present).
   - **Plans committed:** count of those runs with `plan_committed is true`, same attribution.
5. **Beauty:** the pane’s palette, scope line, summary, tables, share bars, and legend, width-responsive, colorless when piped without `-j`.

Do not measure git. Do not put this under `sase project`. Do not ship eight subcommands. Do not let the TUI keep a private renderer.

That is the smallest change that makes the numbers match, sets the family up to grow, and looks like it belongs in the same product as the pane it mirrors.
