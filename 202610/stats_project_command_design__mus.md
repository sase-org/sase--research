# `sase stats project`: design, critique, and recommendation (`__mus`)

Researcher: mus. Date: 2026-10-16. Workspace: sase_13, sase `3e5027a8a7`, sase-core pin `594faf31`.

Request (restated): design a new `sase stats project` command (under a new `sase stats`
group) that exposes the same data as the "Projects" sub-tab of the "Statistics" tab in
the SASE Admin Center, through the same code paths the TUI uses; migrate that sub-tab
onto the shared data source as part of the change; additionally track commits per
model/provider and plans-committed per model/provider. Lead the design for an
intuitive, reliable, beautiful feature. Prior research for `sase project stats` (see
`202610/project_stats_cli_design/project_stats_cli_design.md`) predates these
requirements.

## Bottom line

1. **Build it — but recognize it is a different feature than the one previously
   researched.** The prior design measured git repo truth (commit counts, tokei line
   counts, active days per linked repo). The thing now asked for measures agent-run
   truth (runs, success, attributed commits, patches, wall time per project from the
   durable agent-activity index). Both are legitimately "project stats"; they answer
   different questions and come from disjoint data sources. The single most important
   decision in this report is: **do not merge them into one command.**
2. **The rename to `sase stats project` is correct.** The eight Statistics sub-tabs
   (`overview`, `runners`, `projects`, `providers`, `activity`, `macros`,
   `plans_questions`, `perf` — see `statistics_pane_data.py:26-35`) map 1:1 onto a
   future `sase stats <view>` family. `sase project stats` would strand the other
   seven; `sase stats project` reserves their seats.
3. **The shared-code-path requirement is the right call and is cheap.** The TUI
   already funnels through a narrow waist: `load_statistics_view()` →
   `query_run_stats()` / `query_activity_stats()` (Rust bindings) →
   `build_statistics_views()` (pure Python view models). The CLI should call the same
   three functions, and the "migration" is a small refactor that makes the TUI call
   them through one new shared helper instead of inline. Details in
   [Shared source](#shared-source-the-tui-and-the-cli-must-call-one-function).
4. **Commits-by-model/provider is a small core extension; plans-by-model/provider is
   the hard part.** Commits already live on run records (`meta_commits` in step
   output) and every run row already carries `model`/`provider`
   (`agent_stats/run/types.rs:20-33`), so attributing commits to the committing run's
   model/provider is a new fold over data that exists. Plan gate bundles carry
   `producer_agent` but **no model/provider** (`gate_bundles.rs:41-52`), so plans need
   either a lossy agent→run join or a schema extension. I recommend shipping commits
   by model/provider in v1 and plans-proposed by model/provider as a best-effort join
   with explicit `unknown` buckets, then closing the gap with stored model/provider
   on the bundle. "Plans committed" additionally needs a definition (see
   [What "plans committed" should mean](#what-plans-committed-should-mean)) —
   I recommend reporting both senses with distinct names rather than picking one
   silently.
5. **Do not let the git repo-truth design die silently.** If the launch post still
   needs re-derivable line counts, that is a second command (or a deferred
   `--git-truth` section), not a row in this one. Say so in the plan or the post
   loses its numbers.

## What the TUI actually shows today (verified in this tree)

- The Statistics pane (`src/sase/ace/tui/modals/statistics_pane.py`) has eight views
  defined in `statistics_pane_data.py:54-137`. The "Projects" view's spec reads:
  *"Compare run outcomes, commits, Patches, and wall time across projects."*
- Data flow per load (`load_statistics_view`, `statistics_pane_data.py:220-279`):
  `query_run_stats(start_ts, end_ts, runtime_group_by="tribe", project=filter)` +
  `query_activity_stats(...)` (+ previous-window run query for deltas), then
  `build_statistics_views()` builds all eight view models at once. The pane paints
  one of them.
- The Projects table (`statistics_pane_projects.py:59-92`) columns are Project,
  Runs (with ✓/✗), Success, Commits, Patches, Wall, Share, Last — with three
  groupings (`project`, `patch`, `drilldown`). "Commits" here is **run-attributed
  commits** (folded from `meta_commits` per run in
  `sase-core:.../agent_stats/run/folds.rs:53-88` and attributed to projects/patches
  in `attribution.rs`), not `git rev-list --count`. "Success = completed ÷ all
  runs", "Share = share of runs in range", "Wall = summed agent runtime",
  "Patches = distinct attributed patches" (see `statistics_pane_legends.py`,
  `projects` entry).
- The Providers view (`statistics_pane_views.py:124-145`) already breaks **runs**
  down by provider/model/effort with share, success, and mean runtime — but has no
  commit or plan columns. That is the gap the new requirement fills.
- Ranges are presets (`today`, `24h`, `7d` default, `30d`, `90d`, `all`) plus custom
  forms parsed in `src/sase/stats/ranges.py`. The pane refreshes every 30 s in a
  worker thread; the CLI will do one synchronous load.
- The Python `sase.stats` package (`query.py`, `views.py`, `_view_builders.py`,
  `_view_models.py`) is already the presentation facade the TUI consumes. There is
  **no `sase stats` CLI group yet** (verified: no `register_stats_parser`; `stats`
  exists only under `bead`, `tool`, `artifact`/`artifact-file`, and `prompt`).

## Is this a good idea

**Yes — narrower and more durable than the git-stats version.** Three reasons:

- **It kills a real drift class.** Today the only way to answer "how is project X
  doing?" outside the TUI is to re-derive it (grep the index, count bead traffic,
  guess at footers). A CLI on the same wire as the pane makes TUI numbers
  scriptable, archivable (`-j` output next to the launch post), and agent-usable.
  The prior design's core complaint — hand-derived numbers disagreeing — applies
  with full force here too.
- **The long-term shape is coherent.** One `sase stats <view>` per sub-tab, one
  shared loader, one legend file as the definition of record. Each future sub-tab
  migration is then a small, reviewable diff instead of a second implementation.
- **It composes with existing commands instead of duplicating them.** Bead, tool,
  artifact, and prompt stats keep their stores; `sase stats` reads the
  agent-activity index only. No ownership fights.

Risks, with mitigations:

- **Vanity-metric gravity (worse here than for git stats).** Runs and commits per
  project invite leaderboard reading; the launch outline already warns *"Motion
  isn't progress."* Mitigation: descriptive output only — no per-model rankings
  framed as quality, no productivity scores; keep the legend caveats in `--help`
  and docs; show success rate next to volume everywhere.
- **Silent wrongness from the index.** A stale/locked/partial agent-artifact index,
  a filtered-out project, or unattributed runs can produce believable wrong
  numbers. Mitigation: every output carries window, `generated_at`,
  `project_filter`, coverage (`malformed_spec_files_skipped`,
  `truncated_patch_rows`, `unattributed_runs` — all already on the `ProjectsView`
  model), and per-view legends. Exit 0 with coverage notes; exit 1 only when
  nothing could be measured; exit 2 for usage errors (matches `tool stats` /
  `artifact stats` convention).
- **Scope creep into the git-stats feature.** Reviewers will ask "where are the
  line counts?" Mitigation: name the boundary in the help text ("run-activity
  statistics; for repository size see …") and keep the git design parked as its
  own bead, not as stretch goals in this diff.
- **Privacy/attribution sensitivity.** Commits-by-model names which provider did
  how much of a project's work; plans-by-model is closer to grading individual
  agents. Mitigation: aggregate at provider/model granularity (never per-agent
  tables in v1), and document that agent identity in this index is a deployment
  label, not a person.

## Would I take a different approach

Same group and first subcommand (`stats project`), same shared-path direction. I
would change three things about the likely-obvious implementation:

1. **One loader function, not "the CLI imports TUI code" or vice versa.** Put
   `load_project_stats_view()` (or `load_statistics_view` with a view parameter —
   it already takes one) in `src/sase/stats/` as the single entry both callers
   use. The TUI's "migration" is then replacing its inline query+build calls with
   that helper — a refactor with zero visual change, provable by existing
   screenshot/golden tests.
2. **Do the model/provider work in sase-core, not in Python post-processing.**
   The index rows and commit folds live in Rust; a Python-side join would re-scan
   the index, double the I/O, and drift from the TUI the moment the fold changes.
   Python keeps range parsing, project-display labels, and renderers — the same
   split the codebase already uses (`query.py` → bindings → `_view_builders.py`).
3. **Ship the command family skeleton now, fill views later.** Register `sase
   stats` with `project` plus a `--view`-style forward path (or stub subcommands
   that error with "planned: …"), so the second migration (`providers`,
   `plans_questions`) doesn't re-litigate naming, flags, or formats.

## Requirement adjustments (explicit, as requested)

- **R1. "`sase stats` will be new; this command is `sase stats project`."**
  Kept and endorsed. Adjustment: also reserve the other seven view names at
  registration time (even as documented-not-yet-implemented), and decide the bare
  `sase stats` default now — I recommend defaulting bare `sase stats` to
  `overview`, mirroring the pane's default view, with a delegation notice per the
  default-`list` convention family (`cli_rules.md`; note `stats` has no `list`
  child, so this needs an explicit default, not the central `list` mechanism).
- **R2. "Same code paths as the TUI."** Kept. Adjustment: define "code path" as
  the triple (Rust wire payload → Python view model → legend text), and require
  the TUI and CLI to share all three — not just the query. A CLI that re-renders
  shared models with its own copied definitions will still drift.
- **R3. "Migrate the Projects sub-tab to the new data source."** Kept, but
  re-scoped: there is no *new store*; the shared source is a *new function over
  the existing index*. The migration is a pure refactor of
  `statistics_pane_data.py:220-279` onto it. No data migration, no backfill, no
  dual-write. Call it that in the plan so reviewers don't expect a migration
  script.
- **R4. "Track commits by each model/provider."** Kept. Adjustment: define a
  commit's model/provider as **the committing run's index-recorded
  model/provider** (not the commit footer — footers carry `AGENT=`/`PLAN=` tags
  but no model/provider fields; verified in `commit_footer.rs` and
  `IndexRunRow`). Commits from runs with missing model/provider fall into
  `unknown` buckets that are always shown, never silently dropped. Human views
  show top-N + other; JSON carries the full cross-tab.
- **R5. "Track plans committed by each model/provider."** Adjusted — the phrase
  conflates two metrics (see next section). Ship both, named distinctly:
  (a) **plans proposed by model/provider** (gate-bundle counts joined to the
  producing run's model/provider, `unknown` when unjoinable);
  (b) **plan-linked commits by model/provider** (commits whose metadata or
  footer links a plan, attributed to the committing run's model/provider).
  Rationale: (a) measures planning activity, (b) measures planning that landed.
  Either alone will be misquoted as "plans by model".
- **R6. (unstated, inherited from prior research: line/file counts, repo tiers,
  tokei).** Explicitly **out of scope** for this command. The run index knows
  repos only as commit `repo_name` strings (`folds.rs:69-74` → `top_repos`);
  it cannot produce line counts, file roles, or the code/record tiering. If the
  launch post needs those, keep the prior `sase project stats` git design alive
  as a separate bead — do not bolt tokei onto an activity command.
- **R7. "Various formats / beautiful".** Adjusted to three formats matching house
  style: human (Rich panels in the `artifact stats` grammar), `-j/--json`
  (versioned envelope, stable keys, the agent default), `-m/--markdown` (GFM
  tables for pasting into posts/docs). No CSV/YAML/Prometheus in v1 — CSV can't
  hold the nested cross-tabs without flattening tricks, and agents parse JSON.
  `auto` (table on TTY, markdown when piped) is a nice touch from the prior
  final; keep it only if it doesn't break house convention — other stats commands
  print Rich panels even when piped, so check with the CLI owners before
  innovating here.

## What "plans committed" should mean

Two candidate definitions, both defensible, different denominators:

| Sense | Source | Counts | Answers |
|---|---|---|---|
| Plans proposed | plan + epic-plan gate bundles in window | bundles by joined model/provider | who plans how much |
| Plan-linked commits | `meta_commits` with a plan/patch linkage, or footer `PLAN=` tags | commits by committing run's model/provider | whose plans land as code |

Recommendation: implement both as separate sections (`plans_by_model`,
`plan_commits_by_model`) sharing one model/provider key space, with the join
rule and the `unknown` share printed in the legend. The join rule for (a):
`bundle.producer_agent` → the run(s) by that agent in the window → plurality
model/provider; ties and misses → `unknown`. This is honest about being an
attribution heuristic, and it creates the pressure to store model/provider on
the bundle later (the real fix — file it as the follow-up, since `GateBundle`
has no such field today).

Out of v1: per-agent tables, success-rate-by-model for plans (confounds model
with task difficulty), and any footer-scraped model inference.

## Shared source: the TUI and the CLI must call one function

```
sase-core (Rust)                          sase repo (Python)
────────────────                          ──────────────────
agent_stats/run/{query,folds,             src/sase/stats/query.py
  attribution}.rs  ← NEW:                   query_*_stats() (existing)
  commits_by_model/provider              ──→ thin binding adapters
  fold, plans join support               src/sase/stats/projects_source.py
                                           load_projects_stats(...)  ← NEW,
AgentPlanActivityStatsWire               shared by TUI + CLI
  (+ model/provider join fields)         src/sase/stats/views.py
                                           build_statistics_views() (existing)
TUI: statistics_pane_data.py             CLI: stats_handler_project.py
  load_statistics_view() calls             (new) → same loader → renderers
  the shared loader (migrated)
```

Contract notes:

- The loader takes `(view, range, project_filter, macro_focus, ...)` and returns
  the existing immutable `StatisticsViewData` (plus the new cross-tab fields on
  the wire models). TUI behavior is unchanged by construction; prove it with the
  existing statistics pane tests/goldens.
- Rust remains the owner of all index aggregation (per `rust-core-required` and
  the backend-boundary litmus: a web/mobile frontend would need identical
  numbers). Python owns range parsing, display labels, and rendering.
- Wire additions are additive with `#[serde(default)]` so old snapshots still
  parse; bump the stats wire version only if the repo's convention requires it
  (check `sase-core` wire-version practice — the commit-footer wire uses an
  explicit schema version; follow the same pattern if one exists for stats).
- The `sase-core-revision.txt` CI pin moves past the core commit, per
  `rust_core_backend_boundary` (core memory, always loaded).

## CLI surface (proposed)

```text
usage: sase stats [-h] [-j] [-m] [--range RANGE] [-p PROJECT] [--group-by {project,patch,drilldown}]
                  [--by-model] [-t N] [--no-color]
                  {project,overview,runners,providers,activity,macros,plans,perf} ...

Activity statistics for SASE projects, read from the same agent-activity index
and view models as the Admin Center Statistics pane. Run-activity statistics;
for repository size (lines, files) see <parked git-stats bead>.
With no VIEW, shows overview. All definitions are printed below; JSON carries
the full contract.

positional:
  VIEW                  statistics view (default: overview). `project` aliases the
                        pane's Projects sub-tab; other views land incrementally.

options:
  -h, --help            show this help message and exit
  -j, --json            shorthand for --format json (versioned envelope)
  -m, --markdown        GitHub-flavored tables for pasting into posts/docs
  -r, --range RANGE     today|24h|7d (default)|30d|90d|all, or Nh|Nd|Nw|YYYY-MM|dates
  -p, --project KEY     filter to one project (key, display name, alias, +tag)
  -g, --group-by MODE   projects grouping: project|patch|drilldown (default: project)
  -b, --by-model        add the commits-by-model/provider and plans-by-model sections
  -t, --top N           cap ranked rows in human output (default: 10; JSON is complete)
  --no-color            plain output (also honors NO_COLOR)

definitions:
  runs        agent runs started in range (index records, not git commits)
  success     completed ÷ all runs
  commits     run-attributed commits (meta_commits), not `git rev-list`
  model       the committing/proposing run's index-recorded model/provider;
              `unknown` = missing on the run or unjoinable plan bundle
```

Behavior notes:

- Name resolution reuses the project-display snapshot (`project_display_for`),
  case-insensitive, `+` stripped — the same resolver the pane uses, so CLI and
  TUI spell project names identically. Unknown names exit 2 with suggestions.
- `-b/--by-model` gates the two new cross-tabs so default output stays
  scannable; JSON always includes them (schema note when the core is too old to
  supply them: `model_breakdown_available: false` rather than zeros).
- Every human rendering ends with the pane's legend line for the view
  (`VIEW_LEGENDS["projects"]` etc.) — this is the "same definitions" guarantee
  made visible.
- Follow `cli_rules.md`: sorted options, every long option with a short alias,
  excellent `-h`. Register `stats` in the central registrar alongside the other
  groups; check the bare-`sase stats` default against the delegation-notice
  convention before inventing a new defaulting mechanism.

## Output sketch (human, `sase stats project -b`)

One header panel (project filter, window label, `generated_at`, index ref), one
Projects table identical in columns to the pane (Project · Runs ✓/× · Success ·
Commits · Patches · Wall · Share · Last), then two cross-tab panels:

```text
╭─ Projects · Last 7 days · as of 2026-10-16 16:00 EDT ─────────╮
│ 12 projects · 1,204 runs · 312 attributed commits · 45 Patches │
│ Runs over time  ▂▄▄█▅▆▆▆                                       │
╰───────────────────────────────────────────────────────────────╯
╭─ By Project ──────────────────────────────────────────────────╮
│ Project      Runs      Success  Commits  Patches  Wall  Share  │
│ ■ sase       402 ✓389 ×13   96.8%     210       18  31h  ████  │
│ ...                                                            │
╰───────────────────────────────────────────────────────────────╯
╭─ Commits by model/provider ───────────────────────────────────╮
│ provider/model            commits  share  runs committing      │
│ anthropic/claude-opus-4-6   140   44.9%   96                  │
│ openai/gpt-5.x              88   28.2%   61                  │
│ unknown                     12    3.8%   11                  │
╰───────────────────────────────────────────────────────────────╯
╭─ Plans by model/provider ─────────────────────────────────────╮
│ provider/model            proposed  approved  plan-commits     │
│ ...                        (join rule + unknown share noted)   │
╰───────────────────────────────────────────────────────────────╯
  Success = completed ÷ all runs  ·  Share = share of runs in range  ·
  Wall = summed agent runtime  ·  Commits = run-attributed (meta_commits)
```

JSON envelope: `{schema_version, generated_at, range{...}, project_filter,
coverage{...}, projects[...], commits_by_model[...], plans_by_model[...],
legends{...}}` — sorted keys, stable order, full cross-tabs regardless of
`-t`. Markdown: one GFM table per panel, numbers identical to JSON for the same
index state (test this equality on a fixture).

## Reliability and edge cases

- Read-only: no network, no clone, no fetch, no writes. Safe in agents/monitors.
  Index access goes through the existing operation lock
  (`agent_artifact_index_operation_lock`).
- Every degradation is data, not an abort: empty window renders an honest empty
  state (not zeros dressed as findings); unjoinable plans accumulate in
  `unknown` with the join rate printed; old core without the new folds yields
  `model_breakdown_available: false`; malformed specs and truncated patch rows
  surface via the existing coverage fields.
- Determinism: same index state + same range ⇒ same numbers. Print
  `generated_at` and the resolved range timestamps so archived JSON is
  self-describing for the launch post.
- Performance: the pane already runs these queries on a 30 s refresh in a
  worker; a CLI single-shot is the same cost. No new cache in v1; add a
  blob-OID-style cache only when a TUI panel needs sub-second answers (the
  prior final reached the same conclusion for a different store).
- Tests (implementer): fixture index with known runs (multi-provider, commits
  with/without plan linkage, a plan bundle with no matching run → `unknown`),
  golden JSON schema snapshot, human/markdown↔JSON equality, TUI-parity test
  (pane model == CLI model for the same payload), unknown-project exit 2,
  empty-window rendering. Run `just check` before finishing (no `check-full`
  unless asked).

## Beauty notes

- Copy the `artifact stats` / Statistics pane panel grammar exactly (accent
  `#FF87D7`, cyan `#87D7FF`, share bars, right-aligned numbers, humanized
  durations via `format_duration`, local timestamps via `format_local`) so the
  command feels like the pane poured into a terminal. Reuse the pane's render
  helpers rather than inventing new ones; project color chips come from
  `categorical_color(project_key)` as the pane does.
- The runs-over-time sparkline is the visual centerpiece; cap bar width to the
  terminal and keep full buckets in JSON.
- Keep default output to three panels (header, projects, one cross-tab or a
  pointer to `-b`); the full cross-tabs are one flag away, not one scroll away.

## Phasing

- **Phase 0 (design lock):** confirm R5's two-metric split and the bare-`sase
  stats` default; park the git line-count design as its own bead with a pointer
  from `stats project --help`.
- **Phase 1 (this change):** core folds for commits-by-model/provider +
  plans-join support; Python `load_projects_stats` shared loader; TUI Projects
  migration (zero visual change); `sase stats project` with human/JSON/markdown;
  docs + `--help` legends.
- **Phase 2 (family):** migrate remaining sub-tabs one view per diff
  (`providers` and `plans_questions` first — they share the new cross-tabs);
  store model/provider on plan bundles to retire the join heuristic.
- **Explicitly not in this change:** git line counts, churn, per-agent tables,
  token/cost accounting (provider-usage store is a different source — link,
  don't merge), velocity framing.

## Recommendation

Approve `sase stats project` as designed above: a run-activity command on the
TUI's own loader, with commits-by-model/provider folded in Rust, plans reported
as two distinctly-named metrics with an honest join, and the Projects sub-tab
migrated onto the shared loader in the same diff. Keep the prior git-stats
design parked, not merged — the launch post's line counts and this command's
activity numbers are different facts, and each deserves one owner. First
deliverable after approval: the Phase-0 naming/definition lock (half a page),
then the core wire diff, since everything else keys off its field names.
