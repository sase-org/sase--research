# `sase stats project`: one shared Projects report, with honest model attribution

> **Research query:** How should I implement a new `sase stats project` command (renamed from the earlier
> `sase project stats` design, under a new `sase stats` group) that migrates the SASE Admin Center's Statistics →
> Projects sub-tab onto the same data source and also tracks how many commits and committed plans each model/provider
> made? It is the first step toward a `sase stats` sub-command for every Statistics sub-tab that uses the TUI's code
> paths (that larger goal is out of scope). Critique the plan: is it a good idea, would a different approach be
> better, which requirement adjustments are justified, and what is the recommended solution, designed to be
> intuitive, reliable, and beautiful?

![Infographic for sase stats project: why today's run-recorded counts mislead, counting each fact at its source through one shared sase_core::project_stats query for the CLI and the Statistics → Projects tab, the Output, Code, and Runs scopes, model provenance stamping, and the four-phase build order](sase_stats_project_with_model_attribution_infographic.png)

## Bottom line

1. **Build it. The Projects migration fixes a real defect.** Today's Projects "Commits" column is not a project
   statistic. It counts commits that runs launched *on this machine* recorded, and about 78% of those are sidecar
   bookkeeping. The recorded SHAs are pre-land workspace commits.
2. **The five reports split on the data source, and the evidence settles it.** grk, mus, and gem would attribute
   commits and plans from the local run index. I [verified](#evidence-i-verified-myself) four reasons that cannot
   work:

   - **It is machine-local.** Since Sep 1, athena agents made **2,214** of sase's agent-tagged `master` commits.
     Apollo's agents made **293**.
   - **It counts bookkeeping.** 382 of 490 sase run-recorded commits on apollo went to beads, plans, or research
     sidecars.
   - **Its SHAs are not the landed SHAs.** Only **10 of apollo's own 293** landed commits appear in apollo's index.
   - **`plan_committed` is inherited.** Coders, monitors, and gate turns carry it too, so there are **1,662**
     flagged runs for about **505** plans. gem's "muse leads with 666 committed plans" becomes **38** under planner
     credit. Opus leads with **209**.

   So: **git history is the source for commits, the plan store is the source for plans, and the run index is the
   source only for runs, success, wall time, and Patches.**
3. **Model attribution needs [provenance written at commit time](#phase-0-write-time-provenance).** No commit footer
   names a model (0 of 16,192 commits). Joining footers to published agent pages resolves **99%** of August's agent
   commits but only **31%** of October's, because of the agent-page publication outage (`sase-10x` / `sase-11o`). Add
   `SASE_MODEL=<provider>/<model>` to commit footers and `proposed_with: <provider>/<model>` to plan frontmatter
   **first**. Keep the join only for backfilling history.
4. **One report with [three labeled scopes](#metric-contract).**

   - **Output:** commits, plans, and who made them. It is global and range-scoped.
   - **Code:** a lifetime snapshot of size, tests, age, and activity days.
   - **Runs:** this machine's agent runs, range-scoped.

   Every section header names its clock and its coverage. That is the main thing that makes the view intuitive.
5. **Define ["same code path"](#architecture) concretely.** It means one Rust query (`sase_core::project_stats`), one
   Python loader, one view model, one set of legends, and shared Rich section renderers. The TUI never shells out to
   the CLI, and the CLI never imports Textual.
6. **Reuse an existing sase-core pattern for the git engine.** `memory_history` already walks git through a bounded,
   prompt-free runner, with a tip-keyed JSON snapshot cache and incremental folding. [Copy that](#cache). No new
   SQLite database is needed.
7. **The [CLI mirrors the TUI](#cli-contract):**
   `sase stats project [-p PROJECT]... [-r RANGE] [-g {model,patch,project,repo}] [-f {json,markdown,rich}] [-j] [-D] [-F]`.

   - Defaults match the TUI's defaults: the last 7 days and all projects.
   - Lifetime facts are always printed, so a bare run still answers "how big and how old?"
8. **Ship it as [one epic](#build-order-in-one-epic):**

   - **Phase 0:** provenance stamping. Start now; every day of delay is history that needs a join.
   - **Phase 1:** a zero-diff extraction of the registry and renderers.
   - **Phase 2:** the core engine and cache.
   - **Phase 3:** the CLI, plus the TUI switch behind an epic-scaffolding `beta` flag.

## Critique: is this a good idea?

### Yes, for four reasons

- **Agents and scripts can't see the TUI.** Today, "how many commits did Opus make on sase this month?" has no
  supported answer, so agents re-derive it badly. The prior design catalogued the launch post quoting 11,000+, 15,755,
  16,181, and other commit totals.
- **Shared definitions stop drift.** Once the tab and the command read one query, one number answers each question.
- **It is cheaper to test.** A golden JSON or Rich output over fixtures exercises the exact loader the pane uses,
  without Textual's pilot.
- **The model numbers tell a story nobody can see today.** cld's all-time sase + sase-core data shows Opus
  committing about as many plans (659) as code commits (668), while gpt-5.5 almost never plans. That division of labor
  exists only in SASE data.

### What is wrong with the plan as stated

1. **The phrase "migrate the Projects sub-tab to the command's data source" hides a semantics change.** The tab's
   "Commits" and the command's "Commits" are different quantities: machine-local workspace commits including
   bookkeeping, versus landed commits on the code repos' default branches. The migration should *announce* the
   change, relabel Overview's tile until Overview migrates, and keep the run telemetry the tab is good at.
2. **The model metrics cannot be trusted until provenance is written at the source.** Any design that only *reads*
   existing data shows a per-model chart that is 31% attributed for October. [Stamping at write
   time](#phase-0-write-time-provenance) is not optional polish. It is the precondition for the headline feature.
3. **"Same code paths as the TUI" carries an unspoken trap for the long-term goal.** Most Statistics views (Runners,
   Providers, Activity, Macros, Plans & Questions, Perf) are machine-local by construction. A `sase stats` family will
   faithfully reproduce that, and `sase stats provider` on apollo describes apollo. Adopt one rule now: **every
   `sase stats` header names its machine whenever a section reads local stores.** A fleet-wide layer (the
   `sase_gateway` crate already exists, but does not serve `agent_stats` today) is a separate project.
4. **The plan underestimates how many different "plans" there are.** Proposed, approved, archived, committed, and
   implemented are five facts, and the Plans & Questions tab already counts gate decisions. "Committed plans" must be
   named and defined so it never sits next to "approved" and gets read as the same thing.

### Would I take a different approach?

Same group, same first view, same migration. The deliberate differences from the obvious implementation are:

- **Provenance first** ([Phase 0](#build-order-in-one-epic)), before any reader is built.
- **Git and the plan store as the sources for output.** The run index is for runs.
- **A Rust-owned report** (`sase_core::project_stats`), because a web, mobile, or gateway frontend would need identical
  numbers (the `rust_core_backend_boundary` litmus test). Python owns resolution, rendering, and the CLI.
- **A small registry**, so the next seven views are cheap. It holds `StatisticsViewSpec`, CLI names, and one legend
  list that serves the TUI legend, the `?` help, CLI `-h` definitions, and Markdown footers.

**Alternatives I rejected:**

- **CLI imports `load_statistics_view`.** It drags in activity, previous-window, and runner work, keeps the wrong
  commit and plan semantics, and couples the CLI to the TUI package.
- **CLI renders the pane headlessly through Textual.** It is slow and heavy, and it cannot emit JSON or Markdown.
- **TUI shells out to the CLI.** That puts a process spawn and parsing on a 30-second timer.
- **A run-index-only attribution fold.** It is refuted in [Evidence I verified myself](#evidence-i-verified-myself).
- **Git notes to freeze historical attribution.** They avoid rewriting history but add refspec and conflict
  operations, and they stop improving when sidecar backfill (`sase-11o.2`) lands. A query-time join plus cache is
  simpler.
- **Rewriting old commits to add `SASE_MODEL`.** Destructive and unnecessary.
- **A separate `Repos` sub-tab** that leaves Projects untouched. It keeps a misleading column and two answers to
  "what did project X produce?"
- **Implementing all eight views now.** The extraction is the hard part. Do it once, well, on Projects.

## Explicit requirement adjustments

Each item gives the requirement's ID and what was requested, then what it was adjusted to and why.

- **R1. `sase stats project`**
  - *Adjusted to:* **Kept.** Future views use singular names derived from the TUI view ids: `overview`, `runner`,
    `project`, `provider`, `activity`, `macro`, `plan`, `perf`. Bare `sase stats` prints group help.
  - *Why:* It matches the `sase project` and `sase agent` noun style. No vaporware stubs.
- **R2. Same code paths as the TUI**
  - *Adjusted to:* **Defined as one core query, one loader, one view model, one legend set, and shared section
    renderers.**
  - *Why:* A shared query with copied definitions still drifts (mus).
- **R3. Migrate Projects to the new source**
  - *Adjusted to:* **Kept and widened.** The tab gains Output and Code, and keeps Runs as a labeled "this machine"
    section. Run-recorded commits leave the Projects table. The `patch` grouping keeps a code-only "Run commits"
    column. Overview's tile is relabeled "Run commits (this machine)" until Overview migrates.
  - *Why:* This fixes the defect without deleting the tab's run telemetry. Numeric changes are announced, not hidden.
- **R4. Commits by model/provider**
  - *Adjusted to:* **Defined:** landed commits on the code repos' default branches in range, attributed by the
    precedence in [Commit to provider and model precedence](#commit-to-provider-and-model-precedence). Rows always
    include `? model not recorded` and `∅ no agent footer`, and they sum to the total.
  - *Why:* Honest gaps beat a silently shrunken denominator.
- **R5. Plans committed by model/provider**
  - *Adjusted to:* **Defined:** plan docs (`tier: tale/epic`) first committed to the project's plan store in range.
    They are credited to the **proposing** turn's model and split into epic and tale. Projects with `local` SDD
    storage show `—` (not committed), never 0.
  - *Why:* The run flag over-counts about 3× and credits coders ([Evidence I verified
    myself](#evidence-i-verified-myself)).
- **R6. *(new)* Write provenance at the source**
  - *Adjusted to:* **Add `SASE_MODEL=<provider>/<model>` to commit footers and `proposed_with: <provider>/<model>`
    to plan frontmatter.** Land these first.
  - *Why:* This is the only attribution that survives publication outages, machine loss, and linked repos.
- **R7. *(new)* Range**
  - *Adjusted to:* **`-r/--range` with the TUI grammar** (`today 24h 7d 30d 90d all`, `Nh/Nd/Nw`, `YYYY-MM`,
    `YYYY-MM-DD`, `START..END`) and bounds `[start, end)` in the SASE timezone. **Default: the TUI's
    `DEFAULT_PRESET` (7d).** Lifetime facts ignore the range and say "lifetime".
  - *Why:* Same defaults mean the same numbers on both surfaces. I diverge from cdx and cld here ([Where the reports
    disagreed](#where-the-reports-disagreed-and-how-i-resolved-each-point)).
- **R8. No project = all projects**
  - *Adjusted to:* **Kept:** enabled projects, plus any project with runs in range (so no row the old tab showed
    disappears). `-p` repeats. `-D` adds disabled projects. There is no inference from the current directory.
  - *Why:* It matches the TUI's unfiltered view and keeps scripts predictable.
- **R9. Formats**
  - *Adjusted to:* **`-f {json,markdown,rich}` plus `-j`**, default `rich`. No `auto`, no CSV in v1.
  - *Why:* House style; a stable output shape.
- **R10. Earlier repo-truth requirements**
  - *Adjusted to:* **Kept as the Code section**, with the prior contract: three repo tiers, default-branch snapshots,
    LoC by role with a test share, age, active days, and the tokei dependency gate.
  - *Why:* You said "also", not "instead".
- **R11. *(new)* Cache**
  - *Adjusted to:* **In v1**, using the `memory_history` pattern, registered with `sase disk` as rebuildable.
  - *Why:* A pane refreshing every 30 seconds must not rescan history or blobs.
- **R12. Groupings**
  - *Adjusted to:* **`project · repo · model · patch`.** Drilldown folds into `patch`.
  - *Why:* Four meaningful lenses instead of five overlapping ones.
- **R13. Out of scope**
  - *Adjusted to:* The other seven views, fleet-wide runs, churn and growth series, cost and tokens, per-agent tables,
    quality rankings, `--as-of`, rewriting history.
  - *Why:* Each is a clean follow-up on the same envelope.

## How this report was made

**Lead researcher's consolidation · 2026-10-16 · apollo.** This merges five independent reports
([cdx](sase_stats_project_with_model_attribution__cdx.md), [cld](sase_stats_project_with_model_attribution__cld.md),
[grk](sase_stats_project_with_model_attribution__grk.md), [mus](sase_stats_project_with_model_attribution__mus.md),
[gem](sase_stats_project_with_model_attribution__gem.md)) with my own verification. The prior design it revises is
[`project_stats_cli_design`](../project_stats_cli_design/project_stats_cli_design.md). Code was inspected at sase
`f3087c86ac` and sase-core `181072b5`. Data came from a read-only copy of apollo's run index (3,972 runs,
2026-09-01 → 2026-10-16), sase `origin/master`, and the sase agents and plans sidecars.

**The task as the lead framed it:** Design `sase stats project`, the first command in a new `sase stats` group, and
migrate the Admin Center's Statistics → Projects sub-tab onto the same data source. This is the first step toward a
`sase stats` twin for every Statistics sub-tab that uses the TUI's code paths. The command keeps the earlier
project-stats requirements (commits, code and doc size, project age, per-repo breakdown) and adds **commits per
model/provider** and **committed plans per model/provider**. Critique the plan, call out requirement adjustments, and
end with a recommended solution that is intuitive, reliable, and beautiful.

## Evidence I verified myself

These checks targeted the points where the reports disagreed or measured nothing. Values were measured on apollo on
2026-10-16. Each item gives the question, the finding, and how it was measured.

- **Is the run index machine-local?**
  - *Finding:* Yes. All 3,972 rows have `source_machine = NULL` (nothing imported), and launch times run from
    2026-09-01 onward.
  - *How:* `agent_artifact_index.sqlite` copy
- **Who made sase's recent commits?**
  - *Finding:* Since 2026-09-01, `master` has 2,595 commits. 2,523 are agent-tagged: athena **2,214**, apollo
    **293**, kellys_mbp **16**.
  - *How:* footer `SASE_AGENT`/`AGENT`, machine segment
- **What do run-recorded "commits" contain?**
  - *Finding:* sase on apollo has 490: beads **243**, plans **95**, research **44**, unlabeled **107** (primary and
    linked workspaces), and bob-cli **1**. bob-cli has the same ~78% bookkeeping share.
  - *How:* `done.step_output.meta_commits[].repo_name`/`cwd`
- **Do recorded SHAs identify landed commits?**
  - *Finding:* Almost never. **10 of 293** apollo-tagged `master` commits since Sep 1 appear in apollo's index. Runs
    record the workspace commit, and landing or rebasing mints a new SHA.
  - *How:* SHA set intersection
- **What does `agent_meta.plan_committed` mean?**
  - *Finding:* It is a session-level flag inherited by downstream turns. Of the 1,662 flagged runs, 517 are root
    `--plan` planners. The rest are 248 `--code`, 247 `--mon`, 131 `--gate`, and 503 older unlabeled rows. They cover
    about **505** distinct `sdd_plan_path` values.
  - *How:* `agent_meta` roles
- **How large is the error in gem's plan table?**
  - *Finding:* muse/muse-spark: 666 flagged runs → **38** planner-credited plans. claude/opus: 306 → **209**.
    codex/gpt-6-luna: 154 → **14**.
  - *How:* the same rows, credited to planner turns
- **Can commits be attributed through published agent pages?**
  - *Finding:* Agent-tagged sase commits resolved by agents-sidecar SHA, then name: Jul **85%**, Aug **99%**, Sep
    **72%**, Oct **31%**. This corroborates cld's 98/77/31 (cld's figures include a local-index fallback).
  - *How:* `agents/*/commits.json`, `agents/*/meta.json` `metadata.model`
- **Do footers carry a model?**
  - *Finding:* No `MODEL`, `PROVIDER`, `TURN`, or `RUN` footer exists on `master`. cdx found 0 of 16,192 commits
    all-time.
  - *How:* footer parse
- **Has a footer tag ever been removed?**
  - *Finding:* Yes. `SASE_MACHINE` was dropped on 2026-07-24 (`9aab8a713d`) because the machine can be derived from
    the global `SASE_AGENT` name. A model cannot be derived that way.
  - *How:* `git show 9aab8a713d`
- **What provenance do plans carry?**
  - *Finding:* The sase plans sidecar holds 5,460 plan docs (4,286 tale, 1,174 epic). 1,945 have `proposed_by`
    (stamped since Jul 2026, by `plan_propose_handler.py:323`). None names a model.
  - *How:* frontmatter scan
- **Where are plans stored?**
  - *Finding:* It varies by project: SDD storage is `in_tree`, `local`, `separate_repo`, or `sidecar_repos`
    (`sdd/_store_types.py`). Plans stored as `local` are never committed.
  - *How:* source
- **Is there precedent for Rust walking git with a cache?**
  - *Finding:* Yes: `memory_history::cache` with `file_history::runner`. The runner is bounded and sets
    `GIT_TERMINAL_PROMPT=0`. The cache stores `{cache_dir}/v{schema}/{sha256}.json`, folds incrementally on tip
    ancestry, rebuilds when corrupt, and takes a writer-only lock.
  - *How:* sase-core source
- **Is the existing renderer reusable outside the TUI?**
  - *Finding:* Mostly. The Projects renderers return plain Rich `Table`/`Panel`/`Group`, but they live in a pane
    mixin with stubbed `_percent`/`_share_bar`. The provider palette (`ace/tui/provider_styles.py`) imports
    `textual.color`. Neutral modules already exist (`integrations/provider_badges.py`, `project_accents.py`).
  - *How:* source
- **Does the PR-URL-in-`sha` projection bug matter today?**
  - *Finding:* It is real but latent. `_commit_result_list_record` drops `commit_sha` and derives `sha` from
    `result`, which is a PR URL for `create_pull_request`. All 1,770 live `sha` values on apollo are hex, so it bites
    only PR-method workflows.
  - *How:* source + index
- **What house style should the CLI follow?**
  - *Finding:* `-j/--json`, `-p/--project` (`artifact stats`, `repo list`, `memory read`), and
    `-f/--format {json,markdown,rich}` (`artifact read`, `memory read`, `snippet`). The TUI's default range is
    `DEFAULT_PRESET = "7d"`.
  - *How:* `sase … -h`, source

The reports' own measurements that I relied on without re-measuring:

- cld's all-time attribution: 64.5% of agent-tagged sase and sase-core commits resolve to a model, and 1,345 of 5,459
  plans do.
- cld's agents-sidecar facts: 17,179 pages, 2,591 of them with empty metadata, and `commits.json` covering the
  primary repo only.
- The prior design's line-of-code (LoC) prototype: 3.13M code lines, 46% tests.
- cdx's footer audit.

## Where the reports disagreed and how I resolved each point

Each item gives the topic, the reports' positions, and the resolution.

- **Scope: keep the repo census (LoC, age, tiers)?**
  - *Positions:* cdx, cld, and gem keep it inside one report. grk and mus split it into a later `sase stats repo`.
  - *Resolution:* **Keep it, as a labeled Code section.** You asked to migrate the tab onto *the command's* data
    source, and the commit and LoC requirements still stand. grk and mus were right that blending clocks is
    dangerous. Section scoping and labels solve that without a second command.
- **Source for commits by model**
  - *Positions:* grk, mus, and gem use run-index `meta_commits` × the run's model. cld uses git plus a footer →
    agent-directory join. cdx uses git plus write-time provenance and exact joins.
  - *Resolution:* **Git history, attributed by stamped footer, then the agents-sidecar join, then unknown.** The run
    index fails on four verified counts ([Evidence I verified myself](#evidence-i-verified-myself)).
- **Definition of "plans committed"**
  - *Positions:* grk and gem count runs with `plan_committed: true`. mus reports both proposals and plan-linked
    commits. cld counts first-adds to the plans sidecar, credited to `proposed_by`. cdx counts the first commit of a
    logical plan, credited to the authoring planner.
  - *Resolution:* **cld's definition with cdx's crediting rule:** a plan doc's first add to the project's plan store,
    credited to the proposing turn's model. The run-flag definition is refuted ([Evidence I verified
    myself](#evidence-i-verified-myself)). mus's "plans proposed" is a different metric that belongs to the Plans &
    Questions tab.
- **Default range**
  - *Positions:* cdx and cld default to `all` for the CLI. grk and mus default to `7d`. gem defaults to `30d`.
  - *Resolution:* **Use the TUI default (`7d`, from the same constant), and always show lifetime facts.** Identical
    defaults make "the CLI shows what the tab shows" literally true. Printing lifetime commits, size, and age in the
    card answers cld's "412 commits looks broken" concern.
- **Project selection**
  - *Positions:* cdx, cld, and gem use a positional `[PROJECT ...]`. grk and mus use `-p`.
  - *Resolution:* **`-p/--project`, repeatable.** It is house style and mirrors the TUI's `p` chip, and the same flag
    will filter all eight future views. A positional reads well for this one command and badly for
    `sase stats provider sase`.
- **Bare `sase stats`**
  - *Positions:* cdx and cld print group help. grk delegates to a `list` catalog. mus and gem default to `overview`.
  - *Resolution:* **Print the group help in v1.** Do not ship stubs for unimplemented views. Revisit a `list` catalog,
    via the central default-`list` mechanism, once three or more views exist.
- **Formats**
  - *Positions:* cdx, cld, and gem use `auto/table/markdown/json/csv`. grk uses rich plus `-j`. mus uses human, `-j`,
    and `-m`.
  - *Resolution:* **`-f {json,markdown,rich}` plus `-j`, default `rich`.** This matches `artifact read` and
    `memory read` exactly. Drop `auto`, so output does not change shape when piped, and drop CSV, which fights nested
    model rows (`jq -r … @csv` covers scripts). Either can be added later in one line.
- **Cache**
  - *Positions:* cdx and cld want a cache in v1. grk and mus want none. gem wants a Python TTL cache.
  - *Resolution:* **A cache in v1, in Rust, following `memory_history::cache`.** It is required once git and LoC feed
    a pane that refreshes every 30 seconds.
- **Renderer sharing**
  - *Positions:* cld and grk share the same Rich renderable. cdx shares the report but keeps renderers separate.
  - *Resolution:* **Share section renderers** (card, tables, bars) as pure functions of the view model and a
    `RenderContext`. Compose them differently per surface: TUI chips plus a viewport, or a CLI header. Parity comes by
    construction, without making the widget tree the API.
- **Groupings**
  - *Positions:* cld uses project/repo → model → patch. cdx adds provider and keeps drilldown. gem uses
    project/patch/model.
  - *Resolution:* **`project · repo · model · patch`.** `patch` renders the Project → Patch tree, which absorbs
    `drilldown`. Provider is a subtotal row inside `model`, not its own grouping.
- **Exit code for partial coverage**
  - *Positions:* cdx uses 3. The others use 0.
  - *Resolution:* **0.** An uncloned linked repo is normal on some machines, and coverage lives in the output. Use 1
    only when nothing is measurable, and 2 for usage errors.
- **Feature flag**
  - *Positions:* cld wants a `beta` flag as epic scaffolding. grk wants no flag.
  - *Resolution:* **Use a `beta` flag only if a phase lands before the epic finishes**, and remove it when the epic
    lands (`sase_flags.md`). grk's "two truths" worry applies only to a flag that outlives the epic.

## Metric contract

Every metric has one definition, one clock, and one scope. The legend text comes from the registry. Metrics are
grouped by section; each gives its definition, clock, and scope.

- **Output**

  - **Commits**
    - *Definition:* Commits reachable from each code repo's default-branch ref, merges included, deduplicated by SHA
      across repos
    - *Clock:* **committer time** in range
    - *Scope:* global (same on every machine with the same refs)
  - **Agent share**
    - *Definition:* Commits whose terminal footer has `SASE_AGENT=`/`AGENT=`, divided by commits
    - *Clock:* same
    - *Scope:* global
  - **By model**
    - *Definition:* [Commit to provider and model precedence](#commit-to-provider-and-model-precedence). Rows sum to
      Commits, including `?` and `∅`.
    - *Clock:* same
    - *Scope:* global
  - **Plans committed**
    - *Definition:* Plan docs first added to the plan store (rename-aware), by tier
    - *Clock:* first-add committer time
    - *Scope:* global
  - **Plans by model**
    - *Definition:* [Plan to provider and model precedence](#plan-to-provider-and-model-precedence). Rows sum to
      Plans committed.
    - *Clock:* same
    - *Scope:* global
  - **Model coverage**
    - *Definition:* Resolved ÷ agent-tagged, with unknown counts by reason
    - *Clock:* same
    - *Scope:* global
- **Code**

  - **First commit, age, active days**
    - *Definition:* Earliest commit across code repos. Age is elapsed time. Active days are distinct commit dates in
      the SASE timezone.
    - *Clock:* **lifetime**
    - *Scope:* global
  - **Code lines, tests, doc lines, languages**
    - *Definition:* Role-classified LoC over the committed tree at the recorded OID
    - *Clock:* **snapshot** `<ref>@<oid>`
    - *Scope:* global
- **Runs**

  - **Runs ✓/×, success, agent time, Patches, last run**
    - *Definition:* Today's exact definitions (success = completed ÷ all runs; time = summed agent runtime)
    - *Clock:* **launch time** in range
    - *Scope:* **this machine**

**Why committer time:** `git log --since/--until` filters on committer time, so anyone can verify a number with plain
git. SASE's land and rebase flow also resets committer time when a commit lands, which makes it "when it reached
mainline". The existing `VcsCommitWire.timestamp` is *author* time, so add a `committer_ts` field instead of
repurposing it.

**Zero versus unknown:**

- A measured zero prints `0`.
- An unavailable or inapplicable value prints `—` in human output and `null` in JSON.
- A missing repo never becomes 0 lines. It reduces coverage ("6 of 7 code repos").

**Totals:**

- Project totals deduplicate shared repos by identity.
- Portfolio totals deduplicate commits by SHA.
- Model rows across projects aggregate by `(provider, model)` over the deduplicated commit set.
- A display row cap (for example, 50 Patch rows) never truncates totals, and the number of omitted rows is printed.

**Never in this command:** quality rankings of models, cost per commit, productivity scores, or tables of individual
agents or people. Sort by count, never print ordinals, and let the reader conclude.

## Attribution design

### Phase 0 write-time provenance

- **Commits.**

  - **Where:** in `workflows/commit/runtime_tags.py`, extend `_resolve_runtime_commit_tags()` to emit `MODEL` next to
    `AGENT`.
  - **Value:** read it from the *producing turn's* `agent_meta.json` (`llm_provider`, `model`) via
    `SASE_ARTIFACTS_DIR`, never from the host process's defaults. Under host-owned completion, the finalizer commits
    on the turn's behalf, so it must stamp the turn's model, not its own.
  - **Lifecycle sets:** add `MODEL` to `PRODUCED_RUNTIME_COMMIT_TAG_KEYS`, `STALE_RUNTIME_COMMIT_TAG_KEYS` (so
    inherited tags are scrubbed on amend or cherry-pick), and `RUN_OWNED_COMMIT_TAG_KEYS` (so `stitch create --resume`
    re-stamps it).
  - **Display:** add `MODEL` to the tag-style priority in `vcs_log/_tag_style.py`.
  - **Footer:** one line, for example `SASE_MODEL=claude/opus`.
  - **Not needed:** a `SASE_TURN` tag. Once the model is stamped, the session-versus-turn ambiguity no longer matters
    for this metric.
- **Plans.**

  - **Where:** in `main/plan_propose_handler.py`, next to `stamps["proposed_by"]`.
  - **Value:** add `stamps["proposed_with"] = "<provider>/<model>"` from the same `agent_meta`.
  - **Re-proposals:** a re-proposal re-stamps the field, so the accepted version is credited to whoever proposed
    *that* version.
- **Projection fix.** `_commit_result_list_record` should preserve `commit_sha`, `method`, and `run_id`, and should
  stop putting `result` into `sha`. The bug is latent today but corrupts any future PR-method data.
- **Why this does not contradict the `SASE_MACHINE` removal.** That tag was dropped because the machine can be derived
  from the global `SASE_AGENT` name. The model cannot: one session spans several models, and the page that would say
  which one may never publish. Footers should carry exactly the facts that cannot be derived elsewhere.
- **Exposure.** Footers already link to public agent pages that publish the model. Stamping adds no new disclosure.

### Commit to provider and model precedence

1. A `SASE_MODEL` footer (parsed by core `parse_commit_footer`, in both spellings). This is authoritative.
2. An exact SHA in the agents sidecar's per-member `commits.json`. This identifies the turn exactly, but covers the
   primary repo only.
3. The footer's agent name in the **agent directory**, tried in order:

   1. the `<name>--code` member;
   2. the exact page;
   3. a model shared by every member of the session.

   The directory is built from the agents-sidecar `meta.json` files of every registered project, plus this machine's
   run index.
4. Otherwise **`?` model not recorded**, with a reason: `page_unpublished`, `page_metadata_empty`, or
   `session_ambiguous`. A commit with no agent footer goes to **`∅` no agent footer**. That means human work, or agent
   work from before signing began on 2026-05-24.

The directory is a read-only map built from published pages at the sidecar's HEAD. cld measured it at 0.5 s for
17,179 pages via `ls-tree` + `cat-file --batch`. It is not an import into local agent state, so the publish-only
agents-sync decision stays intact. Resolution happens at query time over cached commit rows, so when the athena
backfill (`sase-11o.2`) lands, old commits re-attribute without re-walking history.

### Plan to provider and model precedence

1. `proposed_with` frontmatter (after [R6](#explicit-requirement-adjustments)).
2. `proposed_by` in the directory, trying `<name>--plan` first and then the exact name. cld found most resolutions go
   through the `--plan` page.
3. Otherwise `?` (a proposer is named but unresolved) or `∅` (no proposer recorded, which covers everything before
   July 2026).

The plan store is resolved through the project's SDD storage, not a hardcoded sidecar. Each storage kind gives where
plans live and how committed plans are counted:

- **`sidecar_repos`**
  - *Where plans live:* the plans sidecar
  - *Committed plans:* counted
- **`separate_repo`**
  - *Where plans live:* that repo
  - *Committed plans:* counted, filtered by the plan's `project:` stamp when the repo is shared
- **`in_tree`**
  - *Where plans live:* the primary repo's plans path
  - *Committed plans:* counted, but the commits stay in code totals
- **`local`**
  - *Where plans live:* not committed
  - *Committed plans:* `—`

**Exclusions:** `*.plan-decisions.json`, non-plan Markdown (no `tier`), and edits after the first add. A plan renamed
across directories keeps its first-add date, using git rename detection (`-M`) with `--diff-filter=A`. Add a stable
plan id only if measured rename churn proves material.

### Model identity

- Group by `(provider, model)` as recorded, for example `claude · opus` or `codex · gpt-6-luna`.
- Size aliases (`small`, `xlarge`) are not models. A leaked alias (cld found one `codex · smartest`) is kept, flagged
  `model_is_alias` in JSON, and dimmed in tables.
- `opus` is itself a moving provider alias. Stamp a concrete model id wherever the adapter can report one, and never
  invent one.

### Coverage and invariants

- **Sums:**

  - `Σ model rows (incl. ? and ∅) = commits`
  - `Σ provider subtotals = commits`
  - the same two identities for plans
- **Coverage line:** print it under every model table, for example "Model recorded for 381 of 408 agent commits
  (93%). 27 unresolved: agent page not published."
- **Coverage tile:** in the TUI, the tile turns amber below 80%.
- **Unavailable versus unknown:** an unavailable *source* (repo not cloned, index missing) is reported separately
  from an available commit with an unknown model.

**What coverage looks like today, before stamping** (cld, all-time sase + sase-core):

- **Commits:** Total 17,755 · Resolved 6,177 · `?` 3,398 · `∅` 8,180
- **Plans:** Total 5,459 · Resolved 1,345 · `?` 512 · `∅` 3,602

October is 31% resolved. After Phase 0, every new commit and plan resolves at step 1.

## Architecture

One report, two surfaces:

```text
                    sase-core (Rust)                                    sase (Python)
 ┌──────────────────────────────────────────────┐   ┌──────────────────────────────────────────┐
 │ project_stats::query(ProjectStatsRequestWire) │   │ sase.stats.project.load_project_stats()  │
 │  ├ history   git log via file_history runner, │◀──│  resolve projects (ProjectDisplaySnapshot │
 │  │           parse_commit_footer, committer_ts│   │  + alias/+tag), repo inventory, SDD store,│
 │  ├ directory agents-sidecar pages + run index │   │  agents sidecars → request wire           │
 │  ├ plans     plan-store first-adds + frontmatter  │  → ProjectStatsView (frozen dataclasses)  │
 │  ├ snapshot  role-classified LoC (tokei gate) │   └──────────┬───────────────────┬───────────┘
 │  ├ runs      reuse agent_stats::run per-project fold         │                   │
 │  ├ cache     memory_history-style snapshots   │   sase stats project       Statistics → Projects
 │  └ aggregate range, dedupe, attribution, coverage│ (parser_stats.py)       (worker → same loader
 └──────────────────────────────────────────────┘   rich/markdown/json        → same section renderers)
          binding: project_stats_query (allow_threads)        └──── sase.stats.render ────┘
```

### Rust core

Module: `sase_core::project_stats`.

- **`wire.rs`.**

  - The request carries `schema_version`, `start_ts`/`end_ts`, the timezone, `facets` (`output`, `code`, `runs`),
    `cache_dir`, `run_index_path`, the agents-sidecar paths, and per project the key, label, and lifecycle state.
  - Each project also lists its code repos (`id`, `kind`, `tier`, `path`, `ref`), records-tier repos, and a
    plan-store descriptor.
  - The response holds per project `output`, `code`, `runs`, `repos[]`, `models[]`, `patches[]`, and `coverage`, plus
    `portfolio` totals, `issues[]`, and `definitions` metadata.
  - It carries both a metric-policy version and an engine version.
- **`history.rs`.**

  - Stream `git log --format=%H%x00%at%x00%ct%x00%P%x00%B` per repo through `file_history::run_git_*`. That runner is
    bounded and prompt-free; set budgets so large histories are not truncated.
  - Parse each message once with `commit_footer::parse_commit_footer`.
  - Cache per-commit rows as `(sha, ct, at, is_merge, agent, model_tag, type)`.
  - Walk incrementally (`cached_tip..new_tip`) when the cached tip is an ancestor of the new one; otherwise rebuild.
- **`directory.rs`.** The map in [Commit to provider and model
  precedence](#commit-to-provider-and-model-precedence), keyed by the HEAD of each sidecar.
- **`plans.rs`.** First-adds plus frontmatter over the plan store, keyed by the store's tip.
- **`snapshot.rs` and `classify.rs`.** The prior design's role classifier over committed blobs, keyed by
  `(repo id, tree OID, classifier version)`. tokei sits behind its dependency gate. If the gate fails, ship one
  honestly named counter ("non-blank lines"), never two counters.
- **`runs.rs`.** Call the existing `agent_stats::run` per-project and per-Patch fold. Do not re-derive runs. This
  keeps the Runs section numerically identical to today's tab and gives the migration a regression oracle.
- **Integration.** Register one batch binding in `sase_core_py`, add a round-trip test, then move sase's
  `sase-core-revision.txt` pin past it.

### Python package

Package: `sase.stats`.

- **`sase/stats/registry.py`.**

  - Promote `STATISTICS_VIEW_SPECS` out of `ace/tui/modals/statistics_pane_data.py`.
  - Add `cli_name`, supported options, groupings, and `legends`.
  - The TUI's view strip, its `?` help, `VIEW_LEGENDS`, CLI `-h` definitions, and Markdown footers all read it.
  - A parity test asserts that every option a view declares is reachable from both surfaces.
- **`sase/stats/project.py`.**

  - `load_project_stats(query, facets=ALL) -> ProjectStatsView` is the only function both surfaces call.
  - It resolves projects (alias, `+tag`, and display name through the existing resolvers), takes one inventory and
    display snapshot, builds the request, and calls the binding.
- **`sase/stats/render/`.**

  - Pure section renderers: `card`, `project_table`, `repo_table`, `model_table`, `patch_tree`, and `legend`.
  - Each takes `(view, RenderContext(width, color_system, now, tz, machine))` and returns a Rich renderable.
  - Primitives: one shared `percent`, `share_bar`, `stacked_bar`, and number formatter. This removes the duplicated
    and stubbed mixin helpers.
  - Colors: move the provider palette out of `ace/tui/provider_styles.py` (which imports Textual) into a neutral
    module beside `integrations/provider_badges.py`. Use `project_accents.project_accent` instead of the second
    palette (`categorical_color(project_key)`).
  - Markdown and JSON renderers live here too.
- **Move `load_statistics_view` into `sase.stats`** and make it view-aware. `projects` routes to
  `load_project_stats`, and the other seven views keep today's composite path. That saves the activity query, the
  previous-window query, and the full `build_statistics_views` build whenever Projects is shown.

### Cache

- **Layout:** `~/.sase/cache/project_stats/v{schema}/{sha256(key)}.json`. It follows `memory_history::cache`
  exactly: equal tips are fresh, tip ancestry folds, anything else rebuilds, a corrupt or wrong-schema file means
  rebuild silently, there is a writer-only lock, and a process memo is keyed by `(path, mtime, len)`.
- **Keys** are immutable or versioned:

  - repo identity and tip (history rows);
  - tree OID and classifier version (snapshots);
  - sidecar HEAD (directory and plans).
- **Correctness:** attribution is resolved at query time, so a directory change re-attributes without a re-walk.
- **Lifecycle:** register the cache with `sase disk` as rebuildable. Losing it costs speed, never correctness.
- **Budgets** (estimates built from measured parts, to validate):

  - warm, one project: under 150 ms;
  - cold history, directory, and plans for sase: about 1–1.5 s;
  - cold LoC: 2–5 s.

### TUI integration

Per `tui_perf.md`:

- **Ticks revalidate; changes recompute (rule 10).** Each 30-second tick resolves repo tips, sidecar HEADs, and the
  index token. If nothing moved, nothing recomputes or repaints.
- **Progressive paint.** The first worker requests `{output, runs}` and paints. A second worker requests `code`, and
  the card shows `measuring code…` until it lands. First paint never waits on LoC (rule 9).
- **Stale-result rejection** uses the full query identity (range, projects, grouping). A failed refresh keeps the last
  good report with a visible "stale" timestamp. A first load shows "loading", never placeholder zeros.
- **Prompt-free (rule 11).** The TUI never fetches. Every git call runs with `GIT_TERMINAL_PROMPT=0`,
  `--no-optional-locks`, and a scrubbed `GIT_DIR`/`GIT_WORK_TREE`. A missing nested clone must never let git walk up
  into the parent repo.
- **Keys.** `g` cycles `project → repo → model → patch`, skipping `project` when one project is selected. `t/T/c`,
  `p/P`, and `r` keep their meanings. No new keybindings are needed. If a `statistics.projects` config block appears,
  mirror it in `default_config.yml`. Update the `?` help modal (required by `ace/CLAUDE.md`).

## CLI contract

### Help

```text
usage: sase stats project [-h] [-D] [-F] [-f {json,markdown,rich}] [-g {model,patch,project,repo}]
                          [-j] [-p PROJECT] [-r RANGE]

Show the Admin Center Statistics → Projects view: what each project produced (commits and committed
plans, and which provider/model produced them), how big and how old its code is, and this machine's
agent runs. Output and code facts come from each code repo's default branch and match on every machine;
run facts come from this machine's run log and say so. Same loader and definitions as the TUI tab.

options:
  -D, --include-disabled  Also include disabled projects when no -p is given
  -F, --fetch             Fetch each code repo's default branch before measuring (default: local refs)
  -f, --format {json,markdown,rich}
                          Output format (default: rich)
  -g, --group-by {model,patch,project,repo}
                          Breakdown table, like the TUI's g key (default: project for several projects,
                          model for one)
  -h, --help              show this help message and exit
  -j, --json              Shorthand for --format json
  -p, --project PROJECT   Project name, alias, key, or +tag; repeatable (default: every enabled project)
  -r, --range RANGE       today, 24h, 7d, 30d, 90d, all, Nh/Nd/Nw, YYYY-MM, YYYY-MM-DD, or START..END
                          (default: 7d, the TUI default)

definitions:
  commits         commits reachable from each code repo's default branch, by commit time; merges included
  agent share     commits whose SASE footer names an agent
  model           provider/model that made the commit or proposed the plan; ? = not recorded, ∅ = no agent footer
  plans           plan documents first committed to the project's plan store (epic or tale)
  code lines      non-blank, non-comment lines in source and test files; tests = test share
  runs            agent runs launched on this machine, from its local run log

examples:
  sase stats project
  sase stats project -p sase -r all
  sase stats project -p sase -g model -r 30d
  sase stats project -p +sase -F -f markdown > sase-stats.md
  sase stats project -p sase -j | jq '.data.projects[0].models[] | {provider, model, commits, plans}'
```

Options are sorted, and every long option has a short alias (`cli_rules.md`). Combining `-j` with a non-JSON `-f` is
a usage error. Register `stats` in `parser_registry.py` and the curated compact root help, with the summary "Show
Admin Center Statistics views from the command line." Bare `sase stats` prints the group help.

### Output contract

- **`rich`.** The shared section renderers: the card, then the `-g` table, then the coverage and legend footer. Color
  drops automatically when stdout is not a TTY; the layout stays. This is a visual contract only.
- **`markdown`.** The same sections as GitHub-flavored tables, ending with the generating command and versions. The
  layout is stable.
- **`json`.** A versioned envelope with additive-only changes:

  ```json
  {
    "schema": "sase.stats.project",
    "schema_version": 1,
    "generated_at": "…",
    "machine": "apollo",
    "query": {"projects": ["gh_sase-org__sase"], "range": {"preset": "7d", "start_ts": 1791590400, "end_ts": 1792195200,
              "label": "Last 7 days"}, "timezone": "America/New_York", "group_by": "model"},
    "versions": {"sase": "…", "sase_core": "…", "metric_policy": 1},
    "data": {"…": "the core response wire, verbatim"}
  }
  ```

  `data` is exactly what the TUI received, so a gateway route can serve it unchanged. Every future `sase stats` view
  reuses this envelope.

### Exit codes

- **0:** Success, including empty ranges and partial coverage. Coverage and `issues[]` carry completeness.
- **1:** Nothing could be measured (binding missing, every source failed).
- **2:** Usage error: an unknown or ambiguous project (with "did you mean"), a bad range, or `-j` combined with another
  format.

stdout carries the report. Progress spinners (interactive and slow only) and diagnostics go to stderr.

## Visual design

*Mockups. The layout is the proposal. **All numbers are illustrative**, except where a note says otherwise.*

In a terminal:

- Borders use the project accent (`project_accents`), and the Statistics accent `#FF87D7` titles sections.
- Bars use each provider's palette, with emoji badges from `provider_badges`:

  - 🤖 codex `#10A37F`
  - 🎭 claude `#FF5F00`
  - 🚀 grok
  - 🦋 muse
  - 🪐 agy
- `?` is dim amber and `∅` is dim gray.

### One-project mockup

`sase stats project -p sase` (one project, default 7 days, at least 100 columns):

```text
╭─ ■ sase  +sase ──────────────────────────────────────── Last 7 days · Oct 09 – Oct 16, 2026 ─╮
│                                                                                               │
│   OUTPUT    412 commits · 99% by agents · 61 plans committed (14 epic · 47 tale)              │
│   CODE      3.1M lines · 46% tests · 82K doc lines · 6 of 7 code repos     lifetime ▸ born   │
│             Feb 14, 2026 · 8 months · commits on 239 of 245 days · 17,755 commits all time    │
│   RUNS      233 runs on apollo · ✓ 189 × 31 · 81% success · 41 h agent time · 18 Patches      │
│                                                                                               │
│   Commits by provider  ██████████████▓▓▓▓▓▓▓▓▓▒▒▒▒▒▒▒░░░░░·   🦋 160  🤖 98  🎭 71  🚀 52  ? 27  ∅ 4 │
│   Plans by provider    ████████████████▓▓▓▓▓▓▒▒▒░·           🎭 31  🤖 18  🚀 6  🦋 4  ? 2        │
│                                                                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────╯

  BY MODEL · last 7 days                        COMMITS   SHARE    PLANS   EPIC   TALE
  🦋 muse      muse-spark-1.3-contributor            160     39%        4      0      4
  🤖 codex                                            98     24%       18      5     13
                gpt-6-luna                            61     15%        9      2      7
                gpt-6.1-sol                           37      9%        9      3      6
  🎭 claude                                           71     17%       31      8     23
                opus                                  40     10%       30      8     22
                sonnet                                31      8%        1      0      1
  🚀 grok      grok-4.7                               52     13%        6      1      5
  ?  model not recorded                               27      7%        2      0      2
  ∅  no agent footer                                   4      1%        0      0      0
  ──────────────────────────────────────────────────────────────────────────────────────
     total                                           412    100%       61     14     47

  Model recorded for 381 of 408 agent commits (93%) · 27 unresolved: agent page not published
  Commits: code repos' default branches, by commit time · refs fetched 2 h ago (-F to refresh)
  Plans: first committed to the plan store, credited to the proposing model · Runs: this machine only
  More: -g repo · -g patch · -r all · -j        Definitions: sase stats project -h
```

### All-projects mockup

`sase stats project` (every enabled project):

```text
╭─ SASE projects · 3 enabled ─────────────────────────────── Last 7 days · Oct 09 – Oct 16, 2026 ─╮
│   OUTPUT   503 commits · 98% by agents · 77 plans committed                                       │
│   CODE     3.5M lines · 45% tests · 10 of 11 code repos measured                                  │
│   RUNS     412 runs on apollo · 84% success · 63 h agent time                                     │
│   Commits by provider  ███████████████▓▓▓▓▓▓▓▓▒▒▒▒▒░░░░·   🦋 201  🤖 140  🎭 92  🚀 41  ? 25  ∅ 4 │
╰─────────────────────────────────────────────────────────────────────────────────────────────────╯

  PROJECT     COMMITS  AGENT  PLANS   CODE LINES  TESTS     AGE   RUNS ᵃ  SUCCESS  LAST COMMIT
  ■ sase          412    99%     61    3,126,927    46%    8 mo      233      81%  4 min ago
  ■ bob-cli        89    97%     16      369,231    36%    5 mo      170      88%  1 h ago
  ■ job             2    50%      0            —      —    3 mo        9      78%  3 d ago
  ────────────────────────────────────────────────────────────────────────────────────────────
    total         503    98%     77    3,496,158    45%              412      84%

  ᵃ runs launched on this machine (apollo).   -g model: providers and models across all projects
```

### Projects tab mockup after migration

Statistics → Projects after migration (TUI). In this mockup, "the §9.1 card" and "the §9.1 model table" refer to the
[one-project mockup](#one-project-mockup).

```text
 Overview  Runners  ‹Projects›  Providers  Activity  Macros  Plans/Q  Perf
 › Compare what projects produced, which models produced it, their code, and this machine's runs.
 Range Last 7 days  t/T/c   ·   Project sase  p/P   ·   Group model  g

 ╭─ ■ sase ─────────────── (the §9.1 card, same renderer, fitted to the pane width) ──────────────╮
 ╰─────────────────────────────────────────────────────────────────────────────────────────────────╯
 ╭ By Model ───────────────────────────────────────────────────────────────────────────────────────╮
 │ (the §9.1 model table; columns drop by breakpoint)                                              │
 ╰─────────────────────────────────────────────────────────────────────────────────────────────────╯
 Commits = default-branch commits in code repos · Plans = first committed to the plan store · Runs = this machine
```

### Design rules

- **Scope in every header.** Range or lifetime, global or "this machine", and repo coverage, written next to the
  numbers they qualify.
- **Exact integers in tables, friendly numbers in prose** (3.1M, 8 months). JSON is always exact.
- **Provider subtotal rows with indented models.** A single-model provider collapses into one row. Long tails fold
  into "+k more" (top 3 per provider by default, scaled with height). JSON lists every model.
- **`?` and `∅` are always printed**, even at 0, because their absence would read as "fully attributed".
- **Neutral order.** Rows sort by count, with stable tiebreaks, no ordinals, and no "top model" phrasing.
- **Responsive breakpoints.** 120 or more columns gets the full layout. At 80, drop FIRST/LAST COMMIT, DOC LINES, and
  EPIC/TALE. Below 60, switch to stacked per-project cards.
- **Accessible.** ASCII bars when the terminal lacks Unicode. Honor `NO_COLOR` and `FORCE_COLOR`. Never convey
  meaning by color alone; badges and labels carry it.
- **One project palette.** The Projects renderer currently colors projects with `categorical_color`, while every
  other project-tag surface uses `project_accent`. Unify on `project_accent`.

## Reliability and tests

**Core** (hermetic temporary repos):

- **Footers:** `SASE_MODEL`, legacy `AGENT`, and model-looking prose in a commit body that must not count.
- **Attribution:**

  - session-container footers with mixed member models (expect `session_ambiguous`);
  - SHA-before-name precedence;
  - empty page metadata;
  - the `--plan` member lookup.
- **Plans:** first-add across renames, `*.plan-decisions.json` excluded, an edit after the add not double-counted,
  and `local` storage reporting `—`.
- **Walks:** incremental walks for the ancestor case and the force-push case.
- **Cache:** a cached query equals an uncached one, and a corrupt cache rebuilds.
- **Range edges:** an `[start, end)` boundary, a DST transition, and non-monotonic commit dates.
- **Invariants:** model rows sum to commits, provider subtotals sum to commits, and numerators never exceed
  denominators.

**Write-time provenance:**

- a host finalizer stamps the producing turn's model, not its own;
- amend and cherry-pick scrub an inherited `SASE_MODEL`;
- `stitch create --resume` re-stamps it;
- a re-proposal re-stamps `proposed_with`.

**Parity, the point of the design:**

- The CLI's `-j` `data` equals the wire the TUI worker received for the same frozen query.
- `render_rich(load_project_stats(q))` exported to text equals what the pane paints at the same width.
- The registry test maps every view option to both a CLI flag and a TUI control.

**Migration oracle:** the Runs section equals today's `build_projects_view` runs, success, time, and Patches for the
same fixture index.

**Renderers:** goldens at 120, 100, 80, and 60 columns with color off, plus Markdown and JSON. Read
`tui_screenshot.md` before regenerating Statistics visual snapshots.

**Flag states:** if Phase 3 lands behind the `beta` flag, test both states (`sase_flags.md`).

**Verification:** run `just check` through `sase tool run` in both repos. Run `check-full` only on request.

## Build order in one epic

**Phase 0: provenance and prerequisites.** These are small, independent, and should start now.

1. `SASE_MODEL` footer stamping and `proposed_with` plan stamping, with the tag-lifecycle sets ([Phase 0 write-time
   provenance](#phase-0-write-time-provenance)).
2. Fix `_commit_result_list_record` to preserve `commit_sha`, `method`, and `run_id`.
3. Unblock agent-page publication (`sase-10x` / `sase-11o.2`), so the backfill join covers September and October.
4. The prior design's inventory prerequisites:

   - `sase-1lk`: cross-project linked-repo resolution;
   - project-declared versus user-wide linked-repo provenance, which sends `chezmoi` to "not counted";
   - an alias-aware project resolver.

**Phase 1: foundation.** A pure refactor, proven by unchanged Statistics snapshots.

1. `sase.stats.registry`, and move `load_statistics_view` out of the TUI package, made view-aware.
2. Extract the Projects renderers and primitives into `sase.stats.render`, and move the provider palette to a neutral
   module.
3. Add the `sase stats` envelope and range helpers, reusing `sase.stats.ranges`.

**Phase 2: core engine.** `project_stats` (history, directory, plans, snapshot behind the tokei gate, runs reuse,
aggregate, cache), plus the binding and the revision pin.

**Phase 3: surfaces.**

1. `sase stats project` with `rich`, `markdown`, and `json`.
2. Switch the Projects tab to `load_project_stats`, with its new groupings, legends, help modal, and the Overview
   relabel.
3. A docs reference page for `sase stats` (read `docs_writing.md` first) and regenerated completion snapshots.

If phases land separately, gate the tab switch behind a `beta` flag (`sase flag new`) and delete the flag when the
epic lands.

**Later.** The other seven views, each a CLI name plus a Markdown renderer over the existing loader. The Overview
commits tile moves onto the new source. Fleet-wide Runs via the gateway. Growth and churn series.

## Decisions for you to confirm

These are the judgment calls where a reasonable person could choose differently.

1. **Default range `7d`, matching the TUI.** The alternative, cdx and cld's `all`, makes the bare CLI a lifetime
   report but breaks "the CLI shows what the tab shows". My design prints lifetime facts either way.
2. **`-p/--project` instead of a positional `PROJECT`.** I chose family consistency over this one command's
   readability.
3. **Public `SASE_MODEL` footers.** The model is already public on agent pages. If you would rather keep footers
   lean, the fallback is a local or published ledger. It is weaker, and it inherits today's publication outages.
4. **Folding `drilldown` into `patch`.** This loses the flat "Patches across all projects, sorted by runs" view. Keep
   all three run groupings if you use that view.
5. **No CSV or `auto` in v1.** Both are one-line additions if a script or a paste workflow misses them.

## Recommended solution

Ship **`sase stats project`** as the first view of a registry-backed **`sase stats`** group. Move the Admin Center's
**Statistics → Projects** tab onto the same loader, view model, legends, and Rich section renderers, all backed by
one Rust query, **`sase_core::project_stats`**.

1. **Write provenance where it is born ([Phase 0](#build-order-in-one-epic), now).**

   - `SASE_MODEL=<provider>/<model>` goes in every commit footer, taken from the producing turn's metadata.
   - `proposed_with:` goes in every plan's frontmatter.
   - Fix the commit-result projection, and unblock agent-page publication so the backfill join covers September and
     October.
2. **Count real things from durable sources.**

   - Commits are landed commits on the code repos' default branches, by commit time.
   - Committed plans are first adds to the project's plan store, credited to the proposing model.
   - Size, age, and activity days are a lifetime snapshot over the committed tree.
   - Runs, success, time, and Patches stay on this machine's run index, reusing today's fold.
3. **[Attribute honestly](#attribution-design).**

   - Precedence: the footer, then the agents-sidecar SHA, then the agent-directory name, then `?`.
   - Commits without an agent footer go to `∅`.
   - Provider subtotal rows sit above model rows and always sum to the total.
   - A coverage line names the cause of any gap.
4. **Make it fast enough for a pane that refreshes every 30 seconds.**

   - A `memory_history`-style tip-keyed snapshot cache.
   - Ticks that only revalidate.
   - Progressive paint, with LoC off the critical path.
   - No fetches or prompts from the TUI.
5. **Make the CLI mirror the TUI.**

   - `sase stats project [-p PROJECT]... [-r RANGE] [-g {model,patch,project,repo}] [-f {json,markdown,rich}] [-j] [-D] [-F]`.
   - Defaults match the tab's defaults.
   - The JSON envelope wraps the exact wire the tab received and becomes the template for every future
     `sase stats` view.
6. **Make it beautiful by reuse and by honesty.**

   - A project-accent card with three scoped lines.
   - Provider-colored stacked bars with badges, and an indented model table.
   - Exact integers, `—` for unknown, and the scope named in every header.
   - Responsive breakpoints and an ASCII fallback.
   - The duplicated helpers and the second project palette go away.

This keeps the tab's run telemetry, fixes its misleading commit count, delivers the per-model numbers you asked for
with their accuracy visible, and turns each remaining Statistics sub-tab into a small, mechanical follow-up.
