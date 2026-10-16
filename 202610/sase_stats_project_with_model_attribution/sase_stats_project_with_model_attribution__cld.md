# `sase stats project`: one Projects view for the CLI and the TUI, with model attribution

> **Research query:** Design `sase stats project` (the first command in a new `sase stats` group) so that it reports
> project stats (commits, code and doc size, project age, and now also commits and committed plans per model/provider),
> and migrate the Admin Center's Statistics › Projects sub-tab onto the same data source, as the first step toward
> every Statistics sub-tab having a `sase stats` twin that uses the TUI's code paths. Critique the plan, call out
> requirement adjustments, and end with a recommended solution that is intuitive, reliable, and beautiful.

**Researcher:** cld · **Date:** 2026-10-16 · **Host:** apollo · **Measured against:** sase `origin/master`
`3e5027a8a7`, sase-core `origin/master` `594faf31`, the sase agents sidecar at `e8590d37`, the sase plans sidecar at
`05165f2b`, and a read-only copy of apollo's `~/.sase/agent_artifact_index.sqlite`.

**Prior art:** `research:202610/project_stats_cli_design/project_stats_cli_design.md` (the consolidated `sase project
stats` design). I keep most of its repo-truth contract (code/records/not-counted tiers, committed default-branch
snapshots, role-classified line counts, `·`/`null` for unknowns, coverage everywhere). This report focuses on what the
new requirements change, and they change more than the name.

---

## Bottom line

1. **Build it, but understand what you are migrating.** Today's Projects sub-tab is not project stats. It is a
   machine-local view of agent runs: runs, success, "Commits", Patches, and wall time, all read from this machine's run
   index (`agent_stats_query_runs`). Its "Commits" column counts whatever commits agent runs launched *on this machine*
   recorded, sidecar bookkeeping included. On apollo, the sase row shows **475** commits since Sep 1, and most of them
   are beads, plans, and research syncs. Meanwhile **2,596** commits landed on sase `master` in that period, **2,213**
   of them by athena agents. Moving the tab onto repo truth fixes a real defect, beyond being groundwork for the CLI.
2. **"Same code paths" should mean one loader, one view model, and one renderer. The CLI must not drive Textual.**
   Today the Statistics loader lives inside the TUI package (`statistics_pane_data.py:220`), and the renderers are
   pane mixins. However, they produce plain Rich renderables. Move both into `sase.stats`, put every view behind a small
   **view registry**, and generate `sase stats <view>` from that registry. Then `sase stats project -f table` prints
   the *same Rich renderable* the TUI paints, so parity holds by construction and the CLI looks as good as the TUI for
   free.
3. **Commits and plans by model are the most interesting numbers here, and the least reliable data.** No commit
   footer records a model. Attribution needs a join: footer `SASE_AGENT` name (or plan `proposed_by`) → agent page in
   the agents sidecar (or this machine's run index) → provider/model. With the data apollo has today:
   - **64.5%** of agent-signed sase + sase-core commits resolve to a model.
   - Only **1,345 of 5,459** committed plans resolve (3,602 predate plan provenance).
   - Over the **last 30 days, 48% of agent-signed commits are unresolvable.** Athena has barely published agent pages
     since Sep 25.

   The command must show these gaps honestly. The durable fix is to **stamp provenance when it is written**.
4. **Adjustment I recommend most strongly: stamp provider/model when the record is created.** Add a
   `SASE_MODEL=<provider>/<model>` commit-footer tag next to `SASE_AGENT`, and a `proposer_model:` field next to
   `proposed_by:` in plan frontmatter. Each is a few lines of host code. Ship them *first*, before the stats work, so
   attributable history starts accruing now. Use the join only for backfill.
5. **One Projects view, two lenses, labeled by scope:**
   - **Produced** (global repo truth: commits, agent share, commits and plans by model, code, age). It is identical on
     every machine.
   - **Work** (runs, success, wall time, Patches). It comes from this machine's run log and says so.

   The existing Patch grouping survives. The tab's `g` key now cycles **project/repo → model → patch**.
6. **Pull a content-addressed cache into v1.** The TUI refreshes this pane every 30 s, and LoC over a 300 MB tree
   costs seconds. Cache by immutable keys: commit SHA for snapshots, the last walked tip for history, and sidecar HEAD
   and blob OIDs for the agent directory. Every tick then only revalidates refs (rule 10 of `tui_perf.md`). The prior
   design deferred the cache, but the TUI requirement makes it mandatory.
7. **CLI shape:**
   `sase stats project [PROJECT ...] [-r RANGE] [-g {project,repo,model,patch}] [-f auto|table|markdown|json|csv] [-j] [-F] [-D]`.
   - With no PROJECT, every enabled project is compared, as in the TUI's unfiltered tab.
   - `-r` uses the TUI's range vocabulary, and the default is `all`.
   - Every TUI control maps to a flag with the same name, which becomes the contract for all future `sase stats`
     views.
8. **Order of work:**
   - **Phase 0:** provenance stamping, finishing the athena hood backfill (`sase-11o.2`), and the repo-inventory bugs.
   - **Phase 1:** the registry and shared renderers, a pure refactor with no visible change.
   - **Phase 2:** the core `project_stats` engine plus cache.
   - **Phase 3:** the CLI and the TUI switch, behind a `beta` flag used as epic scaffolding.

---

## 1. What changed since the prior research

| Prior requirement / decision | Now | Consequence |
| --- | --- | --- |
| `sase project stats` | **`sase stats project`**, first child of a new `sase stats` group | The prior report rejected a top-level `sase stats` as "ambiguous with agent-run statistics". That ambiguity is now the point: `sase stats` *is* the CLI for the Statistics tab, which is agent-run statistics. |
| CLI only; a TUI panel was "phase 3" | **The Projects sub-tab moves onto the same data source in this change** | The data source needs a 30 s refresh story, a progressive load, and a cache in v1. It also needs to absorb the tab's existing run-telemetry content. |
| Provider/model mix was "phase 2" | **Commits per model/provider and committed plans per model/provider are required** | The metric needs an attribution model, a resolution precedence, unknown buckets, and coverage. In practice it also needs a write-time provenance change. |
| No range (snapshot only) | The TUI pane has a range selector (today/24h/7d/30d/90d/all/custom) | Metrics must be split into **range-scoped flow** (commits, plans, runs) and **lifetime/as-of-now facts** (age, code size). |
| Repo truth only | The Projects tab also shows **runs, success, wall time, and Patches** from the local run index | One view now mixes global facts and machine-local facts. Every section must declare its scope. |

---

## 2. What the Projects sub-tab is today (findings)

### 2.1 Data path

```text
StatisticsPane (src/sase/ace/tui/modals/statistics_pane.py; refresh tick every 30 s, line 37)
  └─ load_statistics_view()            ← src/sase/ace/tui/modals/statistics_pane_data.py:220  (inside the TUI package)
       ├─ query_run_stats()            ← src/sase/stats/query.py → Rust agent_stats_query_runs
       │     SELECT project_name, model, llm_provider, record_json … FROM agent_artifacts   (local SQLite)
       ├─ query_activity_stats()       ← local gate bundles under ~/.sase/interaction_requests/{plan,epic_plan,question}
       └─ build_statistics_views()     ← src/sase/stats/views.py (pure; builds every view at once)
            └─ build_projects_view()   ← src/sase/stats/_view_builders.py:218
  └─ StatisticsProjectsRenderingMixin  ← statistics_pane_projects.py:26 (pure Rich: Table/Panel/Group)
```

The sub-tab shows three groupings that `g` cycles through: **project**, **patch**, and **drilldown**. Its columns are
Runs (✓/×), Success, **Commits**, Patches, Wall, Share, and Last.

### 2.2 What "Commits" means there

`fold_commits` (`sase-core crates/sase_core/src/agent_stats/run/folds.rs:53`) counts the entries in a run's
`done.step_output.meta_commits`, whatever repo they landed in. On apollo:

| Fact (apollo, measured 2026-10-16) | Value |
| --- | --- |
| Runs in the local index | 3,953, all launched **since 2026-09-01** (sase 2,032 · bob-cli 1,743 · job 121) |
| Run-recorded "commits" for sase | **475**: beads 240, plans 95, research 32, unlabeled 107, bob-cli 1 |
| Commits on sase `master` since 2026-09-01 | **2,596**: 2,523 agent-signed, of which **2,213 were made by athena agents**, 293 by apollo agents, and 17 by kellys_mbp agents |

So the Projects tab answers "how many commits did agents launched *on this machine* record, in any repo including
sidecars?" Run the TUI on athena and you get a different number. That is the opposite of what a "project stats"
command must guarantee.

### 2.3 Every data source the new view could use

| Source | Scope | Durable? | Carries | Weakness |
| --- | --- | --- | --- | --- |
| Code repos (git) | **global** | yes | commits, dates, footer `SASE_AGENT`/`SASE_TYPE`/`SASE_BEAD`, tree for LoC | no model in the footer |
| Agents sidecar (`sase--agents`) | **global** (all machines publish) | yes | per-agent `meta.json` (provider, model, effort, project, machine) and `commits.json` (SHAs) | publication lag; 2,591 of 17,179 pages have empty metadata; `commits.json` covers the **primary repo only** |
| Plans sidecar (`sase--plans`) | **global** | yes | plan docs with `tier`, `proposed_by` (Aug 2026+), `create_time` | no model; the proposer's name needs a join |
| Local run index (`agent_artifact_index.sqlite`) | **this machine** | retention-limited | provider, model, size alias, status, durations, `meta_commits`, `plan_committed` | machine-local; apollo's starts Sep 1 |
| Local gate bundles | **this machine** | retention-limited | plan/question decisions | machine-local |

The current Statistics tab reads only the last two. The new project view's "Produced" lens should come from the first
three.

---

## 3. Is this a good idea?

### 3.1 The long-term goal (a `sase stats` twin for every sub-tab): **yes**

- **Agents can't see the TUI.** Today an agent asked "which provider has the best success rate this week?" has no
  supported answer. `sase stats provider -j` gives it one.
- **Testing gets cheaper.** A CLI golden over a fixture index exercises the exact loader and renderer the TUI uses,
  without Textual's pilot.
- **Docs and posts can quote it.** Markdown output pastes cleanly; screenshots of `table` look like the TUI.
- **Risk: option sprawl and drift between eight views.** The mitigation is structural: one registry that both
  surfaces enumerate, plus one rule: *every TUI control is a CLI flag with the same vocabulary, and vice versa.*

One caveat to state up front: most Statistics views are machine-local by construction, and the CLI inherits that.
`sase stats provider` on apollo describes apollo. Every `sase stats` header should name the machine whenever the view
reads local stores.

### 3.2 Migrating the Projects sub-tab: **yes, and it fixes a defect**

The tab's "Commits" is machine-local and counts bookkeeping (§2.2). The migration must **not** delete what the tab
does well, though: per-project runs, success, wall time, and the patch breakdown have no other home in the TUI. Keep
them as the labeled **Work** lens.

### 3.3 Commits and plans per model/provider: **yes, it is the most valuable new number, and the hardest one**

The data already tells a story nobody can see today (all time, sase + sase-core):

| Model | Commits | Plans committed |
| --- | --: | --: |
| 🤖 codex · gpt-5.5 | 1,567 | 3 |
| 🤖 codex · gpt-5.6-sol | 1,474 | 445 |
| 🎭 claude · sonnet | 797 | 1 |
| 🚀 grok · grok-4.6 | 715 | 24 |
| 🎭 claude · opus | 668 | **659** |
| 🦋 muse · muse-spark-1.3-contributor | 644 | 0 |

The pattern: Opus plans about as often as it commits, while gpt-5.5 almost never plans. That division of labor exists
only in SASE data. But the attribution is partial (§5.4), and recent data is the *least* complete because of a
publication lag. A per-model chart with a silently dropped 48% would be worse than no chart, so coverage is
first-class in every format.

### 3.4 What I'd do differently from the plan as stated

1. **Fix provenance at the source before building the report** (requirement adjustment R6).
2. **Treat the Projects view as two lenses with explicit scopes**, not one blended table.
3. **Make the registry and shared renderers the deliverable of phase 1.** They are what makes the long-term goal cheap,
   and they can land with zero visible change.
4. **Don't migrate Overview's "Commits" tile in this change, but relabel it.** Overview keeps run-recorded commits
   until its own migration, so its tile must say "run-recorded commits (this machine)". Otherwise two tabs show two
   different "Commits" for the same range.

---

## 4. Requirement adjustments (explicit)

Each item names what was asked, what I recommend, and why.

- **R1. Command name: `sase stats project`.** **Kept.**
  - I add a rule: `sase stats` children use singular names derived from the TUI view ids. The future set is
    `activity`, `macro`, `overview`, `perf`, `plan` (Plans & Questions), `project`, `provider`, and `runner`.
  - Bare `sase stats` prints the group help, since it has no `list` child.
  - Domain stats commands (`bead stats`, `tool stats`, `artifact stats`, `prompt stats`) stay where they are.
- **R2. "Migrate the Projects sub-tab to the new data source."** **Kept and widened.** The tab gains the repo-truth
  "Produced" lens, and the run-telemetry columns move into a labeled "Work (this machine)" lens instead of being
  dropped.
- **R3. "Commits."** **Redefined.**
  - *Was:* run-recorded `meta_commits` (machine-local, sidecars included).
  - *Now:* commits reachable from each **code repo's** default branch: the primary plus project-declared linked repos,
    merges included, SHA-deduped across repos. This is the prior report's definition.
  - Sidecar commits are bookkeeping. They appear in the records tier only.
- **R4. "Commits per model/provider."** **Defined precisely.**
  - A commit's model is the provider/model of the agent turn that made it, resolved by the precedence in §5.2.
  - The rows always sum to total commits, using two non-model rows: **`? unknown model`** (agent-signed but
    unresolved) and **`∅ no attribution`** (no agent footer: human work, or agent work before signing began on
    2026-05-24).
- **R5. "Plans committed per model/provider."** **Defined precisely.**
  - A *committed plan* is a plan document (`tier: tale|epic`) added to the project's plans sidecar. It is dated by its
    first-add commit and attributed to the proposer's model: `proposed_by` (plus the new `proposer_model`) through the
    agent directory.
  - It is split into epic and tale, with two non-model rows: **`? unknown model`** (proposer named, model unresolved)
    and **`∅ no attribution`** (no proposer recorded, i.e. every plan before Aug 2026).
  - This is a different metric from the Plans & Questions tab's "proposed/approved" counts. Those are gate decisions
    from local bundles, and the legend must say so.
- **R6. (new) Stamp provenance when it is written.**
  - Commit footer: `SASE_MODEL=<provider>/<model>`, e.g. `SASE_MODEL=claude/opus`, written wherever the host stamps
    `SASE_AGENT`.
  - Plan frontmatter: `proposer_model: claude/opus`, written by `sase plan propose`.
  - The stats resolver prefers these over every join. This is the only way attribution survives sidecar lag, machine
    loss, and linked repos that have no agents sidecar of their own.
- **R7. (new) Range.**
  - `-r/--range` accepts the TUI vocabulary: `today|24h|7d|30d|90d|all`, plus `Nh|Nd|Nw`, `YYYY-MM`, `YYYY-MM-DD`, and
    `START..END`. Bounds are `[start, end)` in the configured SASE timezone, the same as `sase.stats.ranges`.
  - **The CLI default for `project` is `all`.** "Project stats" means lifetime. The TUI keeps its pane-wide range
    (default 7d).
  - Lifetime facts (age, code size, first commit) ignore the range and are labeled "lifetime".
- **R8. Formats.** `auto | table | markdown | json | csv`, plus `-j`.
  - `table` is the shared Rich renderer.
  - `csv` emits *the breakdown table selected by `-g`*, because the view now has several tables and one CSV per table
    is the only unambiguous shape.
- **R9. (new) Cache in v1.** It is content-addressed and lives in a durable SQLite store registered with `sase disk`.
  The TUI requirement makes it mandatory.
- **R10. Default scope.** With no PROJECT, every enabled project is compared, as in the prior design and matching the
  TUI's unfiltered tab. The CLI never infers the current project from the cwd. The TUI keeps seeding its filter from
  the current project (`statistics_pane.py:210`), because that is the TUI's established behavior.
- **R11. Model identity.**
  - Group by `(provider, model)` as launched, e.g. `claude · opus`. The size alias (`xlarge`, `medium`) is not the
    model. Effort goes in JSON.
  - Show leaked aliases with a flag rather than hiding them. One commit is attributed to `codex · smartest`, which is a
    size alias, not a model.
  - `opus` is itself a moving provider alias. Wherever the provider reports a concrete model id, R6 should stamp that
    id.
- **R12. Out of scope for this change:**
  - the other seven sub-tabs (the registry makes each one a small follow-up);
  - fleet-wide run telemetry;
  - churn, author, and growth time series;
  - historical snapshots (`--as-of`);
  - rewriting old commits to add `SASE_MODEL`.

---

## 5. Attribution design (commits and plans → provider/model)

### 5.1 The agent directory (new core primitive)

This is a read-only map from an agent's global name to its provider, model, effort, role, machine, and project. It is
built from:

1. **every registered project's agents sidecar**, read at its HEAD via `git ls-tree` + `cat-file --batch` over
   `agents/*/meta.json`. That took **0.5 s** for 17,179 pages, versus **2.0 s** walking the filesystem in Python, and
   is cacheable by HEAD and blob OID;
2. **this machine's run index** (`agent_name`, `llm_provider`, `model`), used as a fallback.

Agent names are globally unique (`user.machine.local`), so taking the union across projects is safe. A shared linked
repo signed by another project's agents still resolves.

It is worth building as its own core module (`agent_directory`). `sase agent show` for remote agents and the gateway
will want the same lookup.

### 5.2 Resolution precedence for a commit

1. **`SASE_MODEL` footer tag** (after R6 lands). This is authoritative.
2. **Exact SHA** in the agents sidecar's `commits.json`. This is a per-turn association, so it resolves sessions
   exactly. It covers the primary repo only.
3. **The footer `SASE_AGENT` name** looked up in the directory: the exact page first, then the session's `--code`
   member, then a model shared by every member of the session.
4. Otherwise **`? unknown model`**, with a reason code: `agent_unpublished`, `agent_metadata_empty`, or
   `session_ambiguous`.

Commits without an `AGENT` tag in the terminal footer (parsed by core `parse_commit_footer`, both spellings) go to
**`∅ no attribution`**.

### 5.3 Resolution precedence for a committed plan

1. **`proposer_model`** frontmatter (after R6).
2. **`proposed_by`** looked up in the directory: `<name>--plan` first, then `<name>` exactly. 1,169 of the plans that
   resolve go through the `--plan` role page, so this order matters.
3. Otherwise **`? unknown model`** when a proposer is named, or **`∅ no attribution`** when none is.

### 5.4 Coverage today (apollo, measured)

| Population | Total | Resolved to a model | Unknown | No attribution |
| --- | --: | --: | --: | --: |
| sase commits (all time) | 16,192 | 5,572 (sidecar SHA 5,005 · name 239 · local index 328) | 3,032 | 7,588 |
| sase-core commits (all time) | 1,563 | 605 (name 566 · local index 39) | 366 | 592 |
| **sase + sase-core, last 30 days** | 2,315 | 1,157 | **1,071** | 87 |
| Committed plans (all time) | 5,459 | 1,345 | 512 | 3,602 |
| Committed plans with `create_time` in the last 30 days | 533 | 287 | **243** | 3 |

Resolution by month for sase commits: Aug **98%**, Sep **77%**, Oct **31%**.

### 5.5 Why recent coverage collapsed

Pages are published on commit (`eligible_hoods`, `src/sase/agents_sync/inventory_models.py:87`). But the agents
sidecar shows "sync from bbugyi200.athena" commits dozens of times a day from Sep 16–24, then 6 on Sep 25, 2 on
Oct 7, and 1 each on Oct 12, 13, and 16. Of the 524 agent-signed October sase commits missing from the sidecar's
commit lists, 496 name an agent with **no page at all**. One example is `bbugyi200.athena.10t`, which authored today's
HEAD. Athena still archives *prompts* daily, so the
sync runs, but page publication is stalled or filtered.

This is a known defect. **`sase-10x`** reports that athena's owner manifest sits at the 4 MiB cap, so every publish
that adds a new hood fails and lands in quarantine. Epic **`sase-11o`** is fixing it, and its phase `.2`, "Recover the
athena outbox and backfill unpublished hoods", is still in progress. I added a +1 to `sase-10x` and a
`DISCOVERED ISSUE` note to `sase-11o` with the October numbers above. Until R6 lands, the per-model view on any machine
is only as good as that publication.

### 5.6 Why the footer, not just the sidecar

- **`commits.json` is primary-repo only**, because agents-sync derives it from primary-repo footers
  (`historical_associations`, `src/sase/agents_sync/inventory_history.py:35`). Linked repos such as sase-core resolve
  only through name joins.
- **Two machines can disagree** about the join until both have pulled the sidecar.
- **The footer travels with the commit** to every clone, GitHub included, forever. One extra line per commit buys
  machine-independent attribution, and the agents sidecar already publishes the model publicly.

---

## 6. Metric contract

The prior report's phase-1 contract carries over unchanged: commits, agent-signed share, last-30-day commits,
first/last commit, age, active days, monthly series, code files and lines with test share, doc lines, agent-context
files, languages, latest tag, the records tier, and coverage/issues. These are the additions and changes.

| Metric | Definition | Scope | Lens |
| --- | --- | --- | --- |
| **commits** (in range) | Code-repo commits with author time in `[start, end)`, SHA-deduped | global | Produced |
| **agent-signed share** (in range) | Agent-signed commits ÷ commits | global | Produced |
| **commits by model** | §5.2; rows sum to commits; `?` and `∅` rows always present | global | Produced |
| **model coverage** | Resolved ÷ agent-signed, plus counts by unknown-reason code | global | Produced |
| **plans committed** (in range) | §R5; epic and tale; first-add date in range | global | Produced |
| **plans by model** | §5.3; rows sum to plans committed | global | Produced |
| **runs, completed, failed, success, wall time, Patches, last run** | Exactly today's definitions, from the run index, filtered by launch time in range | **this machine** | Work |
| **lifetime: first commit, age, active days, code/doc size, languages** | As in the prior report; independent of range | global | Produced |

**Totals and sharing rules:**

- Range-scoped flow metrics are totaled per project over the code tier.
- The all-projects total dedupes repos by identity.
- Model rows are totaled across projects by `(provider, model)`.
- Shares in the model table use **all commits** as the denominator, so `?` and `∅` are visible parts of 100%.
- The card's agent share uses the same denominator.

**Never in this command:** rankings of models by "quality", cost or tokens, productivity scores, or per-author human
rankings. The command reports counts, and the reader draws conclusions.

---

## 7. Architecture: one view, two surfaces

### 7.1 The shape

```text
                       sase-core (Rust)                                   sase (Python)
                       ────────────────                                   ─────────────
              ┌───────────────────────────────────────┐
              │ project_stats::query(request)          │       src/sase/stats/registry.py
              │  ├ history   (git log, footer parse,   │         StatsViewSpec(id, label, cli_name, options,
              │  │            incremental per repo)    │           loader, rich, markdown, csv, legends)
              │  ├ directory (agents sidecars + index) │                     │
              │  ├ plans     (plans sidecar first-adds)│       src/sase/stats/project/
              │  ├ snapshot  (LoC by role; tokei gate) │         query.py   resolve projects + inventory → request wire
              │  ├ work      (reuse agent_stats fold)  │         view.py    ProjectStatsView (pure, frozen dataclasses)
              │  ├ cache     (SQLite, content-keyed)   │         render_rich.py / render_markdown.py / render_csv.py
              │  └ aggregate (range, totals, coverage) │                     │
              └──────────────────┬────────────────────┘            ┌────────┴─────────┐
                    binding: project_stats_query                   │                  │
                    (py.allow_threads)                    sase stats project     StatisticsPane "projects"
                                                          (parser_stats.py)      (thin adapter: worker →
                                                          table/markdown/json/csv  load → same Rich renderable)
```

**One function is the "same data source"**, and both surfaces call it:

```python
def load_project_stats(query: ProjectStatsQuery, *, sections: Sections = ALL) -> ProjectStatsView: ...
```

It resolves projects with the alias-aware resolver, takes one `repo_inventory_session()` snapshot, builds the request
wire, calls `project_stats_query`, and returns the frozen view model. The CLI renders that model. The TUI worker calls
the same function and paints the same Rich renderable.

### 7.2 The registry (the foundation for the long-term goal)

Promote `STATISTICS_VIEW_SPECS` (`statistics_pane_data.py:54`) out of the TUI package into
`src/sase/stats/registry.py` and extend each spec:

```python
@dataclass(frozen=True, slots=True)
class StatsViewSpec:
    id: StatisticsView                 # "projects" (TUI id, unchanged for stored state)
    cli_name: str | None               # "project"; None until the view has a CLI twin
    label: str; compact_label: str; micro_label: str
    description: str; compact_description: str
    options: frozenset[StatsOption]    # RANGE, PROJECTS, GROUP_BY, MACRO_FOCUS, ...
    group_by: tuple[str, ...]          # ("project", "repo", "model", "patch")
    legends: tuple[MetricLegend, ...]  # one definition list for TUI legend, CLI -h, and footers
    load: Callable[[StatsQuery], Any]
    render_rich: Callable[[Any, RenderContext], RenderableType]
    render_markdown: Callable[[Any, RenderContext], str] | None
    render_csv: Callable[[Any, RenderContext], Iterable[Sequence[str]]] | None
```

`parser_stats.py` creates one subparser per spec that has a `cli_name`, and adds exactly the flags its `options`
declare. The TUI pane enumerates the same tuple for its view strip. A test asserts both directions: every option is
reachable from both surfaces.

Adding `sase stats provider` later then means writing a CLI name and a markdown renderer, because its loader and Rich
renderer already exist.

### 7.3 Extract renderers from the pane mixins

- `_percent` and `_share_bar` are duplicated across four mixins. `StatisticsProjectsRenderingMixin` even stubs them
  with `NotImplementedError`. Move them into `src/sase/stats/render/primitives.py`, together with a new `stacked_bar`
  (provider-colored), `sparkline`, and color access.
- Color access should go through neutral modules. Provider palettes currently live in `sase.ace.tui.provider_styles`,
  which imports Textual. Move the palette next to `sase.integrations.provider_badges`. Project colors should come from
  `sase.project_accents`, which already claims to be "the shared backend for every project-tag surface". The Projects
  renderer currently uses `telemetry` `categorical_color(project_key)` instead, a second project palette. Fix that
  inconsistency in passing.
- Renderers take `RenderContext(width, color_system, now, timezone, machine)` and never read the clock or the console
  themselves. Golden tests can then freeze them.

### 7.4 Core module: `sase_core::project_stats`

The layout follows the sase-core conventions (a facade `mod.rs`, files ≤ 1,500 lines, free functions over `*Wire`
types, `thiserror` errors):

- **`wire.rs`.** `ProjectStatsRequestWire { schema_version, start_ts, end_ts, projects: Vec<ProjectTargetWire>,
  agent_sidecars: Vec<String>, run_index_path: Option<String>, cache_path: Option<String>, sections }`, where each
  `ProjectTargetWire` carries resolved repos (`name, kind, tier, path, ref_name`) and an optional plans sidecar. The
  response holds per-project repos (`ref`, `history`, `snapshot`), `models[]`, `plans`, `work`, `totals`, `coverage`,
  and `issues[]`, plus a portfolio total.
- **`history.rs`.**
  - Stream `git log --format=%H%x00%at%x00%ct%x00%P%x00%B%x00 <tip>`. Do not use the byte-capped runner.
  - Parse each message once with `commit_footer::parse_commit_footer`, keeping `AGENT`, `MODEL`, `TYPE`, `MACHINE`.
  - Store per-commit rows in the cache.
  - Walking is incremental: if the cached tip is an ancestor of the new tip, walk `cached..new` only. Otherwise walk
    fully.
- **`directory.rs`.** §5.1, keyed by sidecar HEAD and blob OIDs.
- **`plans.rs`.** `git log --diff-filter=A --format=%H%x00%at --name-only -- '[0-9][0-9][0-9][0-9][0-9][0-9]/*.md'`
  over the plans sidecar, then read the frontmatter of each first-added blob (`tier`, `proposed_by`,
  `proposer_model`). Exclude `*.plan-decisions.json` and non-plan Markdown.
- **`snapshot.rs` + `classify.rs`.** These follow the prior report: LoC by role over committed blobs, with the tokei
  crate behind its dependency gate, keyed by `(repo_identity, commit_sha, classifier_policy)` with a blob-OID memo.
- **`work.rs`.** Reuse `agent_stats::run`'s per-project fold, the one behind today's `work.projects` and
  `work.changespecs`, filtered by project. Do not re-derive runs. That keeps the Work lens numerically identical to
  today's tab, which gives the migration a regression oracle.
- **`aggregate.rs`.** Range filtering over cached commit rows, resolution through the directory, SHA dedupe,
  totals, and coverage.

The binding goes in a new or neighboring `sase_core_py` domain with a round-trip test. Then move
`sase-core-revision.txt` past it (`rust_core_backend_boundary`).

**Python stays thin.** It owns project and repo resolution (inventory), the optional `-F` fetch, the view model, and
the renderers. Everything a web or mobile frontend would need to match lives in core: the definitions, the joins,
range math, dedupe, and coverage.

### 7.5 The cache

- **Location:** `~/.sase/cache/project_stats.sqlite`, registered with `sase disk` as a rebuildable cache.
- **Tables:**
  - `commit_rows(repo_id, sha, author_ts, author_offset, committer_ts, is_merge, agent, model_tag, type)`
  - `walk_tips(repo_id, ref_name, tip_sha, walked_at)`
  - `snapshots(repo_id, commit_sha, policy, payload)`
  - `blob_loc(blob_oid, policy, language, role_hint, code, comments, blanks)`
  - `directory(sidecar_id, head_sha, payload)`
  - `plan_rows(plans_id, path, first_add_sha, first_add_ts, tier, proposed_by, proposer_model)`
- **Correctness:** every key is an immutable git object id, a ref tip, or a policy version, so a hit can never be
  stale. Resolution against the directory happens at query time, so a sidecar pull reattributes old commits without a
  re-walk.
- **Budget** (estimates built on measured parts):
  - **warm:** a few ms per repo of `rev-parse`, plus SQLite reads. The target is under **150 ms** for sase.
  - **cold history, directory, and plans:** about **1–1.5 s**. That breaks down as `git log` with bodies 0.21 s
    (prior report), directory 0.5 s, and the plans walk.
  - **cold LoC:** **2–5 s** (prior report).

### 7.6 TUI integration rules (per `tui_perf.md`)

- **Ticks revalidate; changes recompute (rule 10).** The 30 s tick resolves each repo's ref and each sidecar HEAD and
  checks the run index's mtime. If nothing moved, nothing is recomputed or repainted.
- **Progressive paint.** The first worker requests `sections = {history, directory, plans, work}` and paints the card
  and tables. A second worker requests `snapshot`, and the card shows `measuring code…` until it lands. First paint
  never waits on LoC.
- **Per-view loading.** Stop building all eight views on every load. `load_statistics_view` keeps the composite path
  for the other seven views. `projects` routes to `load_project_stats` with its own cadence.
- **Stay prompt-free.** The TUI never fetches, so `-F` stays CLI-only. Every git call runs with
  `--no-optional-locks`, `GIT_TERMINAL_PROMPT=0`, and a cleared `GIT_DIR`/`GIT_WORK_TREE` environment.

---

## 8. CLI surface

### 8.1 `sase stats`

```text
usage: sase stats [-h] <view> ...

Print the SASE Admin Center Statistics views from the command line. Each view
uses the same loader, metric definitions, and renderer as its TUI sub-tab, so
for the same range and project the numbers match the TUI exactly.

views:
  project   Compare what projects produced (commits, plans, code) and which models produced it

examples:
  sase stats project
  sase stats project sase -r 30d -g model
```

Register `stats` in the root help's compact command list (`parser_root_help.py`) with the line "Print Admin Center
Statistics views: project output, models, and agent work."

### 8.2 `sase stats project -h`

```text
usage: sase stats project [-h] [-D] [-F] [-f {auto,csv,json,markdown,table}]
                          [-g {model,patch,project,repo}] [-j] [-r RANGE] [PROJECT ...]

Report what SASE projects produced and which models produced it: commits and their
agent-signed share, commits and committed plans by provider/model, code and docs size,
and age, per code repo and totaled, plus this machine's agent runs. Repo facts come from
each repo's committed default branch and match on every machine; run facts come from
this machine's run log and are labeled as such. With no PROJECT, every enabled project
is compared.

positional arguments:
  PROJECT               Project name, alias, directory key, or +tag (default: every enabled project)

options:
  -D, --include-disabled
                        With no PROJECT, also report disabled projects
  -F, --fetch           Fetch each repo's remote before measuring (default: local refs only)
  -f, --format {auto,csv,json,markdown,table}
                        Output format (default: auto = table on a terminal, markdown when piped);
                        csv prints the -g table
  -g, --group-by {model,patch,project,repo}
                        Breakdown table, like the TUI's g key (default: project for several
                        projects, repo for one)
  -h, --help            show this help message and exit
  -j, --json            Shorthand for --format json
  -r, --range RANGE     today, 24h, 7d, 30d, 90d, all, Nh/Nd/Nw, YYYY-MM, YYYY-MM-DD, or
                        START..END (default: all)

definitions:
  commits        commits reachable from each code repo's default branch (primary and
                 project-declared linked repos), merges included
  agent-signed   commits whose SASE footer names an agent (SASE_AGENT= or legacy AGENT=)
  model          provider/model of the agent that made the commit or proposed the plan;
                 "?" = agent named but model unresolved, "∅" = no attribution recorded
  plans          plan documents committed to the project's plans sidecar (epic or tale)
  code lines     non-blank, non-comment lines in source and test files; tests = test share
  runs           agent runs launched on this machine, from its local run log

examples:
  sase stats project
  sase stats project sase -r 30d
  sase stats project sase -g model
  sase stats project +sase -F -f markdown > sase-stats.md
  sase stats project sase -j | jq '.data.projects[0].models[] | {provider, model, commits, plans}'
```

**Notes:**

- Options are sorted and every one has a short alias (`cli_rules.md`).
- `-j` with a non-JSON `-f` is a usage error.
- An unknown project exits 2 with "did you mean".
- Exit 0 even for partial reports (`coverage` and `issues[]` carry completeness), 1 if nothing could be measured, and
  2 for usage errors.

### 8.3 Format contract

- **`table`**
  - **Is:** the shared Rich renderer. It shows the card first, then the `-g` table. For one project at the default
    `-g`, it also prints the model table, since the headline question needs it.
  - **Stability:** visual.
- **`markdown`**
  - **Is:** the same sections as GitHub-flavored Markdown, ending with the generating command and versions.
  - **Stability:** layout-stable.
- **`json`**
  - **Is:** an envelope (`schema: "sase.stats.project"`, `schema_version`, `view`, `generated_at`, `machine`, `range`,
    `query`, `versions`) plus `data` = the core response wire, verbatim.
  - **Stability:** versioned contract; additive changes only.
- **`csv`**
  - **Is:** the `-g` table, one row per row, no totals, empty cell = unknown.
  - **Stability:** columns append-only.

Every future `sase stats <view>` reuses this envelope, which makes it the second piece of long-term groundwork.

---

## 9. What it looks like

*Mockups. Every number here is a measured value from §5 or the prior report unless it is marked as a placeholder, but
the layout is illustrative. History and model figures cover sase + sase-core ("2 of 7"), because sase's other linked
repos are not cloned in this workspace. Code-size figures (3,126,927 lines, 46% tests, 81,941 doc lines) come from the
prior report's six-repo prototype, so in the real output the two sets would cover the same repos. In a terminal, the bars are drawn in each
provider's palette (🤖 codex `#10A37F`, 🎭 claude `#FF5F00`, 🚀 grok `#00C8D7`, 🦋 muse `#3D9BFF`, 🪐 agy `#6E5DE7`).
`?` is dim amber and `∅` is dim gray. Borders use the project accent.*

### 9.1 `sase stats project sase` (one project, table, ≥ 100 columns)

```text
╭─ sase · +sase ──────────────────────────────────────── All time · as of Oct 16, 2026 17:40 EDT ─╮
│                                                                                                 │
│   Lifetime   first commit Feb 14, 2026 · 8 months · commits on 239 of 245 days                  │
│   Commits    17,755 · 54% agent-signed · 2,315 in the last 30 days · last 4 min ago             │
│   Plans      5,459 committed · 1,174 epic · 4,285 tale                                          │
│   Code       3,126,927 lines · 46% tests · 81,941 doc lines                                     │
│                                                                                                 │
│   Commits by provider  ██████████████▓▓▓▓▓▓▓▒▒▒▒░░░░▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪··························    │
│                        🤖 codex 3,217 · 🎭 claude 1,583 · 🚀 grok 722 · 🦋 muse 644 · ? 3,398  ∅ 8,180 │
│   Plans by provider    ██████▓▓▓▓▓▓▓░▪▪▪▪▪·····························                          │
│                        🎭 claude 717 · 🤖 codex 588 · 🚀 grok 40 · ? 512  ∅ 3,602                 │
│                                                                                                 │
╰─────────────────────────────────────────────────────────────────────────────────────────────────╯

  CODE REPOS                COMMITS  AGENT  MODEL KNOWN  LAST 30D  FIRST COMMIT  CODE LINES  TESTS  DOC LINES
  sase           primary     16,192    53%          65%     1,899  2026-02-14     2,521,676    51%     73,717
  sase-core      linked       1,563    62%          62%       416  2026-04-28       536,490   22%¹      3,503
  sase-nvim      linked           ·      ·            ·         ·  not cloned on this machine
  …
  ────────────────────────────────────────────────────────────────────────────────────────────────────────
  2 of 7 code repos          17,755    54%          65%     2,315  2026-02-14             …      …          …

  BY MODEL                                    COMMITS   SHARE    PLANS   EPIC    TALE
  🤖 codex                                      3,217     18%      588    127     461
       gpt-5.5                                  1,567      9%        3      0       3
       gpt-5.6-sol                              1,474      8%      445     78     367
       gpt-6-luna · gpt-5.6-terra · +6 more       176      1%      140     49      91
  🎭 claude                                     1,583      9%      717    164     553
       sonnet                                     797      4%        1      0       1
       opus                                       668      4%      659    156     503
       claude-fable-5 · +2 more                   118      1%       57      8      49
  🚀 grok                                         722      4%       40      8      32
  🦋 muse      muse-spark-1.3-contributor         644      4%        0      0       0
  🪐 agy · 🐙 opencode                              11     <1%        0      0       0
  ?  unknown model   agent named, not resolved  3,398     19%      512    180     332
  ∅  no attribution  human or pre-signing       8,180     46%    3,602    695   2,907
  ──────────────────────────────────────────────────────────────────────────────────
     total                                     17,755    100%    5,459  1,174   4,285

  WORK · this machine (apollo) · runs since Sep 1, 2026
  2,032 runs · ✓ 1,641 · × 214 · 81% success · 412 h wall · 133 Patches · last run 3 min ago    (-g patch for detail)

  ¹ Rust unit tests inside src/ count as source.   Not counted: chezmoi (user-wide linked repo).
  Model known for 6,177 of 9,575 agent-signed commits (65%). 3,398 unresolved: agent pages not yet published (most
  from athena since Sep 25), or empty page metadata. Records tier: sase stats project sase -j | jq .data…records
  Local refs, fetched 2 h ago (-F to refresh) · Definitions: sase stats project -h
```

The values in the WORK line ("✓ 1,641 · × 214 · 412 h · 133 Patches") are placeholders for layout. Only the 2,032-run
count was measured.

**Design rules:**

- **Exact integers in table cells and friendly numbers in prose.** These are carried over from the prior report.
- **A model table with provider subtotal rows.** Model rows sit indented beneath their provider's subtotal, so a
  `--by-provider` flag is never needed.
- **Collapsed long tails.** After the top N rows per provider (N scales with height; 3 by default), the remaining
  models fold into one "+k more" line. JSON and CSV always list every model.
- **`?` and `∅` are always printed**, even at 0. Their absence would read as "fully attributed".
- **Every section header names its scope.** "CODE REPOS" and "BY MODEL" are global. "WORK · this machine" is local.
- **Responsive breakpoints.** At 80 columns, drop FIRST COMMIT, DOC LINES, and the EPIC/TALE split. Below 60 columns,
  switch to stacked per-repo cards. ASCII bars on dumb terminals. `NO_COLOR` and `FORCE_COLOR` are honored.

### 9.2 `sase stats project` (all enabled projects)

```text
╭─ SASE projects · 3 enabled ──────────────────────────────────── All time · Oct 16, 2026 17:40 EDT ─╮
│                                                                                                    │
│   PROJECT    REPOS   COMMITS  AGENT  COMMITS BY PROVIDER     PLANS  CODE LINES  TESTS   RUNS ᵃ     │
│   ■ sase      2/7     17,755    54%  ███████▓▓▓▒▒░▪▪▪▪▪····   5,459   3,126,927    46%    2,032     │
│   ■ bob-cli   3/3      1,331    88%  ████████▓▓▓▓▓▒▒▒▪▪···        …     369,231    36%    1,743     │
│   ■ job       1/1          8    13%  ▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪··        0           ·      ·      121     │
│   ──────────────────────────────────────────────────────────────────────────────────────────────── │
│   Total       6/11    19,094    56%                              …   3,496,158    45%    3,896     │
│                                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────────────────────╯
  ᵃ Runs: agent runs launched on this machine (apollo), since Sep 1, 2026.   -g model: models across all projects
```

The bob-cli and job figures come from the prior report and are not re-measured. `…` marks values I did not measure.

### 9.3 The TUI Projects sub-tab after migration

```text
 Overview  Runners  ‹Projects›  Providers  Activity  Macros  Plans/Q  Perf
 › Compare what each project produced (commits, plans, code) and which models produced it.
 Range Last 30 days  t/T/c   ·   Project sase  p/P   ·   Group repo › model › patch  g

 ╭ Commits ───────╮ ╭ Agent-signed ──╮ ╭ Plans ─────────╮ ╭ Model known ───╮ ╭ Code (lifetime) ─╮
 │ 2,315          │ │ 96%            │ │ 533            │ │ 52%  ⚠         │ │ 3,126,927 lines  │
 │ ▂▃▅▇█▆▅▇█▆▄▅   │ │ +1 pt vs prior │ │ 157 opus       │ │ 1,071 unresolv.│ │ 46% tests        │
 ╰────────────────╯ ╰────────────────╯ ╰────────────────╯ ╰────────────────╯ ╰──────────────────╯

  Commits by provider  ███████████████▓▓▓▓▓▓▓▒▒▒▒░░░░░?????????????????????????  🦋 590 🤖 267 🎭 184 🚀 115 ? 1,071 ∅ 87

  ╭ By Repo ──────────────────────────────────────────────────────────────────────────────╮
  │ REPO         KIND      COMMITS  AGENT  MODEL KNOWN  PLANS  FIRST COMMIT   CODE LINES  │
  │ sase         primary     1,899    99%          52%      ·  2026-02-14      2,521,676  │
  │ sase-core    linked        416    84%          50%      ·  2026-04-28        536,490  │
  ╰───────────────────────────────────────────────────────────────────────────────────────╯
  Work · this machine (apollo): 1,214 runs · 82% success · 233 h wall · 71 Patches        g → patch
  Commits = default-branch commits in code repos · Model known = resolved ÷ agent-signed · Plans = committed to plans sidecar
```

The commit, agent-signed, model-known, plan, and model-mix values in this mockup are measured. The 96% is 2,228 of
2,315 and the 52% is 1,157 of 2,228; per repo it is 99%/52% for sase and 84%/50% for sase-core. The sparkline, the
"vs prior" delta, and the Work line are placeholders.

**TUI changes, concretely:**

- **Keys.** `g` cycles `project` (unfiltered) or `repo` (one project) → `model` → `patch`. `patch` is today's patch
  table plus its drilldown, folded into one grouping that shows indented patches when a project filter is set. `t`,
  `T`, `c`, `p`, `P`, `r`, `'`, and `ctrl+d`/`ctrl+u` keep their meanings.
- **Help and legends.** Update the `?` help modal (`statistics_help_modal.py`) and the legend for `"projects"`
  (`statistics_pane_legends.py:58`). Both are generated from the registry's `legends`, the same text the CLI prints
  under `definitions:`.
- **Overview.** In this change, relabel the Overview "Commits" tile and its legend as **"Run-recorded commits (this
  machine)"**, and track Overview's own migration separately.
- **Config.** No new keymap bindings. If a `statistics.projects` config block is added (for example the default
  group), mirror it in `src/sase/default_config.yml` (gotchas).
- **Visual snapshots.** Read `tui_screenshot.md` before regenerating the Statistics goldens.

---

## 10. Reliability checklist

- **Machine dependence.**
  - The Produced lens depends only on refs and sidecar HEADs, which are printed. Same refs give byte-identical JSON
    apart from `generated_at` and `machine`.
  - The Work lens always names its machine and coverage start.
- **Sidecar lag.**
  - The `?` row grows, never silently shrinks the denominator.
  - The coverage line names the dominant reason and the sidecar sync age.
  - A coverage tile turns amber below 80%.
- **Empty agent-page metadata** (2,591 pages). Reason code `agent_metadata_empty`. Never guessed.
- **Session-level footers** (`SASE_AGENT` naming a session container). Resolve through the `--code` member, then the
  shared model. Otherwise `session_ambiguous`.
- **Leaked size aliases** (`codex · smartest`). Kept as recorded, flagged with `model_is_alias: true` in JSON, and
  dimmed in tables.
- **Plans without provenance** (3,602 from before Aug 2026). They go in `∅ no attribution`, labeled "before plan
  provenance". They are counted in plan totals but never in a model.
- **Repos shared across projects.** Shown under each project and counted once in portfolio totals. Model rows are
  deduped by SHA.
- **The range edge.** `[start, end)` by author timestamp, the same `StatsRange` objects the TUI uses. A parity test
  feeds one `StatsRange` to both surfaces.
- **Not cloned, shallow, stale, or offline.** All carried over from the prior report: `·`/`null`, coverage "6 of 7",
  "≥ N" for shallow clones, ref age, and `-F`.
- **Cache corruption.** The cache is rebuildable. A schema mismatch or open failure drops to an uncached query plus an
  `issues[]` note. It never fails the command.
- **Prompt safety.** No credential prompts, no lazy fetches, and no `GIT_*` environment inheritance (prior report).
- **Concurrency.** The core holds a lock only around cache writes. Two TUIs and a CLI can run at once, and the last
  writer of an identical row wins harmlessly, because keys are content-addressed.

---

## 11. Tests

- **Core (hermetic temporary repos):**
  - footer variants (`SASE_AGENT`, legacy `AGENT`, `SASE_MODEL`, a body line that must not count);
  - session-container footers;
  - SHA vs. name resolution precedence;
  - an empty-metadata page;
  - `--plan` role lookup;
  - plan first-add across renames and `_2` suffixes;
  - incremental walk (ancestor and force-push cases);
  - cache hit/miss equivalence: an uncached query equals a cached one;
  - range edges;
  - invariants: model rows sum to commits, plan rows sum to plans, numerators ≤ denominators.
- **Python view and renderers:** golden outputs for table at 120/100/80/60 columns, plus Markdown, JSON, and CSV, with
  a frozen clock and no color.
- **Parity (the point of the design):**
  - for a fixture, `render_rich(load_project_stats(q))` exported to text equals what the `StatisticsPane` worker paints
    at the same width;
  - the CLI's `-j` `data` equals the wire the TUI received;
  - a registry test: every `StatsViewSpec.options` member maps to a CLI flag and a TUI control.
- **Migration oracle:** the Work lens equals today's `build_projects_view` numbers for the same fixture index.
- **Both flag states** (`sase_flags.md`).
- **Verification:** `just check` via `sase tool run`, in both repos.

---

## 12. Build order

**Phase 0: provenance and prerequisites.** These items are small and independent, and should start now.

1. **R6 stamping.** Add `SASE_MODEL` to commit footers wherever the host writes `SASE_AGENT`, and add `MODEL` to the
   tag-style priority list in `src/sase/vcs_log/_tag_style.py`. Add `proposer_model` to plan frontmatter at
   `sase plan propose`. Every day this waits is a day of history that needs a join.
2. **Finish `sase-11o.2`**, the athena outbox recovery and hood backfill (§5.5). It is already tracked under
   `sase-10x`, and until it lands, sidecar-based attribution stays degraded on every machine.
3. **The repo-inventory fixes from the prior report.** `sase-1lk` (still open) covers cross-project linked-repo
   resolution. The others are linked-repo provenance (project vs. user, which sends `chezmoi` to "not counted") and
   the alias-aware `-p` resolver (`sase-zo`).

**Phase 1: foundation. It is a pure refactor, verified by unchanged TUI snapshots.**

1. Create `sase.stats.registry` from `STATISTICS_VIEW_SPECS`, and move `load_statistics_view` out of the TUI package.
2. Extract the render primitives and the Projects renderers into pure functions. Move the provider palette to a
   neutral module.
3. Add the `sase stats` envelope and range-parsing helpers, reusing `sase.stats.ranges`.

**Phase 2: core engine.** This is `project_stats` in sase-core: history, directory, plans, work reuse, and aggregate,
plus the cache. Snapshot/LoC sits behind the tokei dependency gate, with physical/non-blank lines as the fallback.
Then add the binding and the revision pin.

**Phase 3: surfaces.** Both behind a `beta` flag (for example `stats_project_view`), created with `sase flag new` as
epic scaffolding and deleted when the epic lands.

1. `sase stats project` with all formats.
2. The TUI Projects tab switched to `load_project_stats`, plus the legends, help modal, and Overview relabel.
3. Docs: the `sase stats` CLI reference page (read `docs_writing.md` first) and the regenerated completion snapshot.

**Later.** The other seven `sase stats` views (each is a CLI name plus a markdown renderer), Overview's commit tile on
the new source, fleet-wide Work via the gateway, and churn and growth series.

---

## 13. Alternatives considered

- **The CLI renders the TUI pane headlessly** (Textual `run_test`, then export). This would give pixel parity for
  free, but it is heavy and slow, can't produce Markdown, JSON, or CSV, and couples the CLI to Textual. **Rejected.**
  Sharing the Rich renderables gives the same parity for the table format.
- **Keep the Projects tab as is and add a separate "Repos" sub-tab for repo truth.** This avoids the semantics change
  but keeps a misleading "Commits" column and two places that answer "how much did project X produce?". **Rejected.**
- **Attribute via the local run index only.** It is simple and already wired, but machine-local: apollo's index can resolve
  at most the 293 commits its own agents signed, out of 2,523 agent-signed since Sep 1. **Rejected** as the primary source; kept as a fallback.
- **Attribute via the agents sidecar's `commits.json` only.** It is exact for sessions, but covers the primary repo
  only and lags with publication. **Rejected** as sole source; kept as precedence step 2.
- **Rewrite history to add `SASE_MODEL` to old commits.** This is destructive and pointless. The join covers history
  and is labeled. **Rejected.**
- **A `--by-provider` flag.** Provider subtotal rows in the model table answer it in place. **Rejected.**
- **Plural subcommands (`sase stats projects`) to match tab labels.** The CLI uses singular group nouns (`sase project`,
  `sase bead`), and so do you. Argparse's "invalid choice" lists the valid names. **Rejected.** Reconsider adding
  aliases if users trip on it.
- **A durable cache only in a later phase** (the prior report). That was fine for a CLI-only command, but a 30 s TUI
  refresh over 300 MB of blobs needs it. **Superseded.**
- **Default CLI range = the TUI default (7d)** for uniformity across `sase stats` views. "Project stats" reads as
  lifetime, and a 7d default would make `sase stats project` look broken ("412 commits?"). **Rejected** for `project`.
  Other views can default to 7d. The header always prints the range.

---

## 14. Verified facts (how measured)

| Fact | Value | How |
| --- | --- | --- |
| sase commits | 16,192 (first 2026-02-14, 239 active days, 1,899 since 2026-09-16) | `git log origin/master` on `3e5027a8a7` |
| sase-core commits | 1,563 (first 2026-04-28, 149 active days, 416 since 2026-09-16) | `git log origin/master` on `594faf31` |
| Agent-signed (footer `AGENT`, either spelling, terminal 12 lines) | sase 8,604 (53.1%), sase-core 971 (62.1%) | regex over the commit body tail (approximates `parse_commit_footer`) |
| Commits since 2026-09-01 on sase | 2,596; agent-signed 2,523: athena 2,213 · apollo 293 · kellys_mbp 17 | footer agent-name machine segment |
| Run-recorded commits (apollo index) | sase 475 (beads 240, plans 95, research 32, unlabeled 107, bob-cli 1); bob-cli 1,269; job 12 | `meta_commits` in `record_json` |
| Apollo run index | 3,953 runs, timestamps 2026-09-01 → 2026-10-16 | read-only SQLite copy |
| Agents sidecar | 17,179 pages; 7,940 with commits; 7,335 distinct SHAs, 7,333 on sase master and 0 on sase-core; 2,591 empty-metadata pages, mostly May–Jul | `agents/*/meta.json`, `commits.json` |
| Athena page publication | "sync from bbugyi200.athena": ~14–64/day Sep 16–24; 6 on Sep 25; then 2 (Oct 7), 1 (Oct 12), 1 (Oct 13), 1 (Oct 16) | `git log --grep` in the agents sidecar |
| Commit → model resolution | sase 5,572 of 8,604; sase-core 605 of 971; combined 64.5%; Aug 98%, Sep 77%, Oct 31% (sase) | §5.2 precedence over sidecar SHA, name, and local index |
| Plans | 5,459 docs (1,174 epic, 4,285 tale); 1,944 with `proposed_by`; 1,345 resolved, 512 unresolved, 3,602 with no proposer | frontmatter + `--plan` page join |
| Commits by provider (all time, sase + sase-core) | codex 3,217 · claude 1,583 · grok 722 · muse 644 · agy 8 · opencode 3 · ? 3,398 · ∅ 8,180 | same |
| Plans by provider | claude 717 · codex 588 · grok 40 · ? 512 · ∅ 3,602 | same |
| Directory build cost | Python filesystem scan 2.0 s; `ls-tree` + `cat-file --batch` of 17k `meta.json` 0.5 s (14 MB) | `time` on apollo |
| Model field semantics | `model` = provider model name (`opus`, `gpt-6-luna`); `model_alias` = SASE size alias (`xlarge`, `medium`); one commit attributed to `codex · smartest` | run index `agent_meta` |
| Plan action vocabulary | `epic`, `commit` (plan only), `tale` (plan + coder), `approve` (no plan commit) | `src/sase/_plan_approval_protocol.py:325` |
| `sase-1lk` | still open (READY) | `sase bead read` |
| Athena publication defect | tracked as `sase-10x` (READY, now +4); remediation epic `sase-11o` IN_PROGRESS, phase `.2` (athena outbox recovery and backfill) IN_PROGRESS | `sase bead read` |

LoC figures (3,126,927 code lines, 46% tests, 81,941 doc lines, the 22% sase-core test share) come from the prior
report's measured prototype and are not re-measured here.

---

## 15. Recommended solution

Ship **`sase stats project`** as the first view of a registry-driven **`sase stats`** group, and switch the Admin
Center's **Projects** sub-tab onto the same loader, view model, and Rich renderer.

1. **One data source.** `load_project_stats(query)` is a thin Python front for a new core
   `project_stats::query` that composes:
   - **history** from each code repo's committed default branch, with footers parsed by core;
   - an **agent directory** (every agents sidecar plus the local run index) that resolves agents to provider/model;
   - **committed plans** from the plans sidecar, attributed to their proposer;
   - **LoC snapshots** by role, behind the tokei gate;
   - the **Work** lens, reused unchanged from `agent_stats`.

   It is backed by a content-addressed SQLite cache, so TUI ticks only revalidate.
2. **Two labeled lenses.** **Produced** covers commits, agent share, commits and plans by model, code, and age. It is
   global and identical on every machine. **Work** covers runs, success, wall time, and Patches, and it is this
   machine's view. The old machine-local "Commits" leaves the Projects tab, and Overview's tile is relabeled until its
   own migration.
3. **Attribution with honest gaps.**
   - Model tables have provider subtotal rows and always show `? unknown model` and `∅ no attribution`. Rows sum to the
     total.
   - A coverage line names the cause. Today it is 65% resolved all time and 52% over the last 30 days, because athena
     has barely published agent pages since Sep 25.
   - **Stamp `SASE_MODEL` in commit footers and `proposer_model` in plan frontmatter now**, so future attribution needs
     no join.
4. **An intuitive CLI that mirrors the TUI.**
   - `sase stats project [PROJECT ...] -r RANGE -g {project,repo,model,patch} -f {auto,table,markdown,json,csv} -j -F -D`.
   - No PROJECT compares all enabled projects, and the default range is `all`.
   - Every TUI control is a flag with the same vocabulary, and a registry test enforces it.
   - JSON is a versioned envelope around the core wire. That envelope becomes the template for every future
     `sase stats` view.
5. **Beautiful by reuse.** The CLI `table` *is* the TUI renderable:
   - a project-accent card with sparklines;
   - provider-colored stacked bars with emoji badges;
   - exact integers in cells and friendly prose;
   - scope named in every section header;
   - responsive breakpoints and an ASCII fallback.

   The duplicated `_percent`/`_share_bar` helpers and the second project palette go away.
6. **Build order:**
   - **Phase 0:** provenance stamping, the athena hood backfill (`sase-11o.2`), and the inventory fixes.
   - **Phase 1:** registry plus shared renderers, a zero-diff refactor.
   - **Phase 2:** core engine plus cache.
   - **Phase 3:** CLI plus TUI switch behind a `beta` epic-scaffolding flag, plus docs.
   - **Later:** each remaining Statistics sub-tab gets its `sase stats` twin for the cost of a CLI name and a markdown
     renderer.
