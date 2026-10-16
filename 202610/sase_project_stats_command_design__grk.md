---
title: "sase project stats: design for a reproducible project ledger"
create_time: 2026-10-16T20:30:00-04:00
updated_time: 2026-10-16T20:30:00-04:00
status: draft
tags:
  - research-swarm
  - cli
  - project-stats
  - sase-core
  - launch-post
---

# `sase project stats`: a reproducible project ledger

**Question.** How should SASE implement `sase project stats [project_name]`, which numbers should it actually print, which formats should it speak, and is the feature a good idea in this form?

**Answer.** Build it. Treat it as a **versioned, per-repo project ledger** that a human, an agent, and the launch post can re-run on publish day, not as a tokei clone and not as a vanity commit counter. Default it to the current project, split source / tests / docs, reuse `classify_commit_origin` for the stitch share the launch post actually needs, and keep hidden sidecars out of the default scan.

This report is independent. It uses the launch-post outline as shared input, the live CLI and sase-core tree, and measurements taken on the `sase` primary checkout on 2026-10-16.

## Bottom line

1. **The command is a good idea.** The launch-post outline already depends on a 3–4 number strip (commits, agent-attributed share, months) that must be re-derived on publish day. A prior swarm cited 11,000+ commits against a then-current 15,755. On this checkout today, `HEAD` is **16,181** commits. A one-off shell pipeline will rot the same way. A `sase` command with a dated JSON envelope will not.

2. **Do not ship raw LoC as "code."** A naive `git ls-files` + line count on the sase primary tree reports ~3.0M text lines. Split into buckets it is ~1.38M source, ~1.56M tests, ~106k docs, ~44k snapshots, and 1,151 binary assets (mostly TUI screenshot goldens). Publishing the 3.0M figure, or folding tests into "code," would recreate the stale-figure failure mode with more decimal places.

3. **Do not wrap tokei or scc.** tokei is GPL-3.0; sase is MIT and sase-core is MIT OR Apache-2.0. Embedding tokei is a license defect. Shelling out makes the command optional, non-reproducible, and blind to SASE repo kinds and stitch footers. Count physical lines in-process, classify in sase-core, speak git through the existing VCS provider.

4. **The unique value is SASE-shaped, not git-shaped.** Generic tools cannot: walk primary + linked + sidecar as one project, label repos by kind, classify `stitch` / `auto` / `manual` from SASE footers, or compose beads / artifacts / agent runs. That is the product. LoC is table stakes.

5. **Adjust three requirements before implementing.** Default the omitted project name to the **current** project (not the whole fleet). Put **tests in their own bucket**, not inside "code files." Exclude **hidden sidecars** (`agents`, `attachments`, `attachments-private`) from the default scan. Each is justified below.

## Critique of the request

The request is directionally right and slightly underspecified in ways that would make the first version either slow, dishonest, or both.

### What is right

- A project-level command, not a repo-level one. SASE's unit of work is the project. `sase repo list` already knows the inventory; stats should consume it.
- Optional project name, stats separated by repo. The launch post will quote the sase primary, then maybe sase-core and the research sidecar. Mixing those into one number is how 16k commits becomes 20k without anyone noticing.
- Multiple formats. The three audiences named in the request (human, agent, script) map cleanly onto pretty / JSON / markdown, which SASE already speaks.
- Launch-post driven. The outline in `research:202610/sase_launch_post_outline/sase_launch_post_outline.md` is explicit: a caveated strip in the opening, paid off in "What It Cost," re-derived on publish day. That is a product requirement, not a nice-to-have.

### What would go wrong if implemented as written

**Omitted name = all projects is a footgun.** Sibling commands disagree today:

| Command | Default scope |
| --- | --- |
| `sase repo list` | current project; `-a/--all` for every project |
| `sase tool stats` | current project; `-a/--all` for every project |
| `sase artifact stats` | every project; `-p` to filter |
| `sase project list` | every enabled project |
| `sase project show` | one required name |

An agent in `bob-cli` that types `sase project stats` should not wait on a 16k-commit origin classification of sase. The launch post can pass `sase` or `-a`. Default current matches `sase repo list` and `sase tool stats`, the two closest siblings.

**"Code files and docs" is two buckets short.** Tests and generated/snapshot files dominate this tree. Binary goldens dominate file counts if they are not split out. Linguist excludes documentation, generated, and vendored paths from language stats for the same reason.

**"All repos linked to the project" includes the agents sidecar.** That sidecar is commit-associated agent data. Counting its files as project LoC would drown source and docs in transcripts. Hidden sidecar roles today are `agents`, `attachments`, and `attachments-private`. Plans and research are visible documentation sidecars and belong in the default scan.

**Commit count is not one number.** On this checkout:

| Definition | Count |
| --- | --- |
| `git rev-list --count --first-parent HEAD` | 16,045 |
| `git rev-list --count HEAD` | 16,181 |
| `git rev-list --count --all` | 16,383 |

Pick one default, report the others in JSON, and print the definition in `--help`. I recommend **all-parent `HEAD`** as the headline (what people mean by "commits on this branch"), with `first_parent` and `non_merge` as secondary fields. Do not default to `--all`; leftover branches inflate the number.

**"Length of time the project has been active" is three clocks.**

| Clock | sase primary on 2026-10-16 |
| --- | --- |
| First `HEAD` commit → last `HEAD` commit | 2026-02-14 → 2026-10-16 (~8 months) |
| First SASE-footer commit → last | the span of stitch/auto work |
| Project registration / first agent run | SASE metadata, not git |

The launch-post outline talks about "the last 12 months" as narrative. Git age of this repo is eight months. If the command prints "active 12 months" from a vibed round number, it will be wrong on publish day. Print ISO dates and a human duration, and keep VCS age distinct from SASE age.

**A kitchen-sink stats command will rot.** `sase bead stats` is already a plaintext dump with no JSON. `sase artifact stats`, `sase tool stats`, and `sase prompt stats` already cover their stores. `src/sase/stats/` and sase-core `agent_stats` already cover the TUI Runs view. Project stats should **compose** those as a compact "SASE work" panel, not reimplement them, and v1 can ship the VCS ledger without the panel.

## What the launch post actually needs

From the audited outline (`research:202610/sase_launch_post_outline/sase_launch_post_outline.md`):

- Opening strip of **3–4 numbers**: commits, agent-attributed share, months.
- Undercut immediately with *"Motion isn't progress."*
- Re-derive every number on publish day.
- Do not give stats its own H2; a later "ledger" post is parked.

That implies a **headline mode** whose job is the strip, plus a detailed ledger for the author who wants to sanity-check buckets. It also implies the command must print `measured_at` and the `HEAD` id, so a number quoted in the post is dated.

Agent-attributed share is not "commits by bryan vs commits by a bot." It is SASE origin classification, which already exists:

- `sase-core` binding `classify_commit_origin`
- footer grammar in `commit_footer.rs`
- `VcsCommitWire.origin ∈ {stitch, auto, manual}`
- `sase stitch list --origin`

On this checkout, classifying `HEAD` messages with that footer grammar (including legacy `SASE_AGENT` / `SASE_BEAD` / `SASE_PLAN` tags as stitch) yields:

| Origin | Commits | Share |
| --- | --- | --- |
| stitch (incl. legacy) | 6,586 | 40.7% |
| auto | 333 | 2.1% |
| manual | 9,262 | 57.2% |
| total `HEAD` | 16,181 | 100% |

That 41% stitch share is the launch-post number. A LoC tool cannot produce it.

## Existing machinery to reuse

Do not start from a blank `git log | wc`. The tree already has the seams.

| Need | Already exists | Where |
| --- | --- | --- |
| Project name / alias / `+tag` | `effective_project_name`, `get_project_record`, `_strip_tag_prefix` | `project_handler.py`, lifecycle wire |
| Show **names**, never directory keys | decision `project-labels-never-keys` | human output of `sase project list/show` |
| Repo inventory by kind | `collect_repo_inventory` | `src/sase/repo_inventory.py` |
| Kind colors | primary `#00D7AF`, sidecar `#AF87FF`, linked `#87D7FF` | `repo_handler_list.py` |
| Origin classification | `classify_commit_origin` | sase-core, `vcs_log_facade.py` |
| Commit log parse | `parse_git_log`, `VCS_LOG_GIT_FORMAT` | `vcs_log` rust + Python facade |
| Language-from-filename | `source_language.rs` | sase-core, no I/O |
| Double-count-safe aggregates | `disk_inventory.rs` | nested roots, physical identity |
| Pretty stats panels | `sase artifact stats` | `artifact_cli/stats.py` |
| Versioned JSON stats | `sase tool stats`, `sase artifact stats` | `schema_version` envelopes |
| `--format` + `-j` shorthand | `sase gate list` | `parser_gate.py` |
| `--current-only` | `sase stitch list -o` | skip linked and sidecar |
| Agent/run stats | `agent_stats_query_runs` | TUI, not CLI |
| Bead counts | `sase bead stats` / `view.stats()` | current project bead store |
| Artifact economics | `sase artifact stats -p NAME` | already project-filterable |
| Tracked-file listing | `git ls-files` in tests and pager | VCS provider can grow a hook |

Quality bar is **`sase artifact stats`** (Rich panels, versioned JSON, project display names) and **`sase repo list`** (kind-colored per-project panels). Anti-pattern is **`sase bead stats`** (unstructured stdout, no JSON).

`src/sase/stats/` is the TUI agent-run adapter. **Do not put project stats there.** New Python package: `sase.project_stats`. New rust module: `sase_core::project_stats`.

## Justified requirement adjustments

Call these out in the implementing plan. They change the request; they are not silent scope cuts.

### A1. Default scope is the current project

```text
sase project stats                 # current project
sase project stats sase            # named project (name, alias, key, or +tag)
sase project stats sase bob-cli    # explicit set
sase project stats -a              # every enabled project
```

- Zero names → current project, same resolution as `sase project current`.
- One or more names → those projects, same resolver as `sase project show`.
- `-a/--all` → every enabled project. Error if combined with names (same as `sase repo list --all` + `--project`).
- Disabled projects are admitted when named, omitted from `-a`.
- `home` is omitted from `-a` and refused if named (system-managed, not a true project).

**Why.** Matches `sase repo list` / `sase tool stats`, keeps agents fast, still serves the launch post via `sase project stats sase`.

### A2. Three content buckets, not two

User-facing buckets:

| Bucket | What |
| --- | --- |
| `source` | programming / markup tracked files under `src/`, `crates/`, `tools/`, plus other source extensions not in tests/docs |
| `tests` | `tests/`, `*_test.*`, `*.snap`, pytest/rust test conventions |
| `docs` | `docs/`, `*.md` / `*.rst` / `*.adoc` outside tests, plus `README*` / `AGENTS.md` / `CHANGELOG*` |
| `snapshots` | `**/snapshots/**`, `.stdout` / `.stderr` / `.ansi` goldens |
| `assets` | binary images, fonts, video |
| `config` | yaml/toml/json that is not a snapshot |
| `generated` | `linguist-generated` / `linguist-vendored`, lockfiles, schema dumps |
| `other` | remainder |

Headline "code files / code lines" **means `source` only**. Tests are first-class. Docs are first-class. JSON exposes every bucket so nobody has to guess.

Honor `.gitattributes` `linguist-documentation`, `linguist-generated`, `linguist-vendored`, `linguist-detectable` when present. The sase primary tree currently has no such attributes; other projects will.

### A3. Default repo set is primary + linked + visible sidecars

Include: `primary`, `linked`, `sidecar` except `HIDDEN_SIDECAR_ROLES` (`agents`, `attachments`, `attachments-private`).

Exclude by default: hidden sidecars, opened `external` repos.

Flags, named to match existing CLI:

- `-o/--current-only` — primary only (same spelling as `sase stitch list`).
- `--hidden` — include hidden sidecars.
- `-k/--kind {primary,linked,sidecar,external}` repeatable filter. Short alias required by CLI rules.

Beads sidecar, when present, is visible and appears as a repo row. Its useful numbers still come from `sase bead stats`, not from LoC.

### A4. Physical lines in v1, not comment/blank split

v1 counts newline-terminated physical lines, skips NUL-prefixed binaries, and labels the metric `line_kind: physical` in JSON. Comment vs code vs blank is language-specific work (tokei's actual product). Defer it. The launch post does not need it.

### A5. Headline strip is a first-class output, not a blog-only afterthought

`--headline` restricts pretty and markdown to the 3–4 number strip (commits, stitch share, source LoC, VCS age) plus `measured_at` and `HEAD`. Detailed tables remain the default. This is how the opening of the launch post gets filled without copy-pasting a wall of panels.

### A6. v1 is the VCS ledger; SASE work is a composed panel, not a rewrite

v1 must ship: per-repo commits, origin split, file/line buckets, first/last commit, coverage for missing clones.

v1 should also ship a **compact SASE work panel** that calls existing facades (bead `stats()`, `artifact_file_store_economics(project=...)`, `query_run_stats` for the last 7 days). If a facade is slow or missing, omit that row with `status: unavailable` rather than blocking the VCS ledger.

Do not wait on a TUI Projects-tab panel. Note it as a guide candidate / follow-up.

## Command design

### Parser

Register `stats` on `sase project`, alphabetically between `show` and `suggest`. Update the group metavar. Bare `sase project` stays `list`; do not add `stats` to `_default_list_subcommands()`.

```text
usage: sase project stats [-h] [-a] [-f {pretty,markdown,json,jsonl}] [-j]
                          [-H] [-o] [-k KIND] [--hidden] [-r REV]
                          [--since WHEN] [--until WHEN]
                          [PROJECT ...]

Show a reproducible per-repo ledger for one project, several projects,
or every enabled project.

Running `sase project stats` reports the current project. Pass one or
more names (display name, alias, directory key, or +tag) to select
those projects. `--all` reports every enabled project.

Numbers are taken from each repo's HEAD by default, classified with
SASE commit-origin rules, and split into source / tests / docs.
Hidden sidecars are omitted unless `--hidden` is passed.

examples:
  sase project stats
  sase project stats sase
  sase project stats sase --headline
  sase project stats sase -f markdown
  sase project stats sase -j
  sase project stats -a --current-only
```

Options (every long option has a short alias except `--hidden`, `--since`, `--until`, which collide; give `--hidden` `-H` if `--headline` is not using it — see below):

Short-alias plan that does not fight the project group:

| Flag | Meaning |
| --- | --- |
| `-a/--all` | every enabled project |
| `-f/--format` | `pretty` (default), `markdown`, `json`, `jsonl` |
| `-j/--json` | shorthand for `--format json` (gate pattern) |
| `-s/--strip` | headline strip only (`-H` is already `--help` at some layers; avoid) |
| `-o/--current-only` | primary repo only |
| `-k/--kind` | repeatable kind filter |
| `-r/--rev` | revision to measure (default `HEAD`) |
| `--hidden` | include hidden sidecars (no good short alias; CLI rule allows skipping internals, but this is public — use `-x/--hidden` if a short is mandatory) |
| `--since/--until` | window **commit** stats only; LoC stays the tree at `--rev` |

CLI rules say every public long option gets a short alias. Use `-x/--hidden` (exclude-the-exclusion is ugly) or `-i/--include-hidden`. Prefer **`-i/--include-hidden`**.

`--since/--until` accept the same relative tokens as `sase stitch list` (`7d`, `today`, ISO dates). Windowing applies to commit/origin/age, never to LoC. Windowed LoC is `git of theseus` and is out of v1.

`-j` and `-f json` are equivalent. `-j` plus `-f markdown` is a usage error (exit 2).

### Exit codes

Match `sase tool stats` / `sase artifact stats`:

| Code | When |
| --- | --- |
| 0 | reported, including partial coverage (missing clones) |
| 1 | inventory or VCS failure that prevents any report |
| 2 | usage (unknown project, flag conflict, bad format) |

Unknown project: same message family as `sase project show`. Partial missing clones: stderr warning in pretty, `issues[]` in JSON, exit 0. Same pattern as `sase repo list` inventory warnings.

### Which clone to scan

For each `RepoRecord`, measure **one** clone:

1. The inventory `path` if it exists (canonical / workspace 0).
2. Else the clone for the current workspace number, if it exists.
3. Else `status: missing` — no LoC, no commit scan.

Never sum numbered workspace clones. Never walk `sase/repos/` inside the primary tree; `git ls-files` already excludes it, a filesystem walk would not.

Record in JSON: `path`, `head`, `dirty` (worktree vs HEAD), `status`.

v1 may count **tracked worktree files** (`git ls-files -z`) and set `dirty: true` when `git status --porcelain` is non-empty. Pretty mode then shows a yellow note: "worktree dirty; line counts include uncommitted edits to tracked files." Follow-up: `git ls-tree` + `git cat-file --batch` for blob-accurate HEAD counts. The launch post should be run on a clean checkout anyway.

### Commit scan

One `vcs_log` pass per repo (existing hook + `parse_git_log` + `classify_commit_origin`). Aggregate in rust:

- `commits` (all parents on `--rev`)
- `commits_first_parent` (optional second rev-list; can be a cheap extra git call)
- `commits_non_merge`
- `origin.stitch` / `origin.auto` / `origin.manual`
- `first_commit_at` / `last_commit_at` (author time, ISO-8601)
- `sase_first_at` / `sase_last_at` (first/last non-manual)

Do not spawn a Python origin classifier. The rust binding is the contract; Python golden-contract helpers stay in tests.

### Line scan

For each tracked path:

1. Skip if the blob starts with NUL in the first 8 KiB (binary). Count the file under `assets` if the extension is a known media type, else `other`.
2. Classify bucket (A2) using path, extension, `source_language` filename map, and `.gitattributes`.
3. Count physical newlines (and a trailing partial line).
4. Tally per language for a top-N breakdown (default 8).

Classification and aggregation are rust. File I/O can stay in the host for v1 (12k files counted in a few seconds here) and move later if a TUI panel needs it on a hot path.

### Totals and double-counting

Per project: sum the selected repo rows, **including** linked repos (they are part of that project's work). Mark linked rows `kind: linked` so the table is honest.

`--all` fleet totals: sum each physical repo **once**, attributed to the project that owns it as `primary` or as a sidecar parent. Linked-from rows still appear under the linking project but are tagged `linked_from_owner: <name>` and **excluded from fleet totals**. This is the `disk_inventory` lesson: nested / shared roots must not inflate the headline.

`sase-core` today is a linked repo of sase, not its own project. If it later becomes a project **and** stays linked, the owner-once rule keeps the fleet headline sane.

## Formats

Three audiences, four formats. Default pretty. No YAML, no CSV in v1: SASE does not emit YAML from CLI, and JSON covers spreadsheets via `jq`.

### `pretty` (default) — humans

Rich, colored, panelled. Respect `should_colorize` / `NO_COLOR`. Use the project's accent on the title and the repo-list kind colors on the KIND column. Thousands separators. Durations as `8 months` with ISO dates on the next line.

```text
╭ +sase · enabled · 8 months ─────────────────────────────────────────╮
│  16,181 commits   41% stitch   5,980 source files   609 docs        │
│  first 2026-02-14 · last 2026-10-16 · HEAD 7a1b2c3                  │
╰─────────────────────────────────────────────────────────────────────╯

 Repositories
 NAME          KIND      COMMITS  STITCH  SOURCE  TESTS    DOCS     AGE
 sase          primary    16,181     41%  1.38M   1.56M    106.0k   8 mo
 sase-core     linked      1,563      —    …       …        …       6 mo
 research      sidecar     2,064      —    …       …        5,269f  3 mo
 plans         sidecar       400      —    …       …        …       …
 chezmoi       linked    missing      —   —        —        —       —

 Hidden sidecars omitted (agents, attachments). Pass -i/--include-hidden.

 SASE work
 beads    open 12 · claimed 12 · closed …
 artifacts  1.2 GiB explicit · window 120d
 agents   84 runs / 7d · 61 completed
```

`--strip` prints only the inner headline (the two-line summary), still colored. That is what gets pasted into a draft, then replaced with prose.

Missing clones render as `missing` in COMMITS, never as zero. Zero would lie.

### `markdown` — humans and the launch-post draft

GitHub-flavored tables, stable column order, no ANSI. This is the format an agent dumps into a working copy of the post, and the format Bryan pastes into Obsidian.

````markdown
# sase

Measured `2026-10-16T19:58:00-04:00` at `7a1b2c3`.
Definition: commits = `git rev-list --count HEAD`; lines = physical; source excludes tests.

| Metric | Value |
| --- | ---: |
| Commits (HEAD) | 16,181 |
| Stitch share | 40.7% (6,586 / 16,181) |
| Auto share | 2.1% (333) |
| Manual share | 57.2% (9,262) |
| Source files / lines | 5,980 / 1,382,233 |
| Test files / lines | 6,399 / 1,555,450 |
| Doc files / lines | 609 / 105,966 |
| First commit | 2026-02-14 |
| Last commit | 2026-10-16 |
| VCS age | 8 months |

## Repos

| Repo | Kind | Commits | Stitch | Source LoC | Docs LoC | First | Last |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| sase | primary | 16181 | 40.7% | 1382233 | 105966 | 2026-02-14 | 2026-10-16 |
| sase-core | linked | 1563 | | | | 2026-04-28 | 2026-10-16 |
| research | sidecar | 2064 | | | | 2026-07-11 | 2026-10-16 |
````

`--strip` reduces this to the metric table, no repo section.

### `json` (`-j`) — agents

One versioned envelope on stdout, `indent=2`, trailing newline. Warnings on stderr. Stable `snake_case` keys. Display names in `name`, directory key in `key` (agents need both; humans never see `key` in pretty/markdown).

```json
{
  "schema_version": 1,
  "measured_at": "2026-10-16T19:58:00-04:00",
  "line_kind": "physical",
  "commit_count": "rev_list_head",
  "scope": {
    "mode": "one",
    "projects": ["sase"],
    "rev": "HEAD",
    "include_hidden": false,
    "current_only": false
  },
  "projects": [
    {
      "name": "sase",
      "key": "gh_sase-org__sase",
      "state": "enabled",
      "tag": "+sase",
      "headline": {
        "commits": 16181,
        "commits_first_parent": 16045,
        "commits_non_merge": 0,
        "origin": {"stitch": 6586, "auto": 333, "manual": 9262},
        "source_files": 5980,
        "source_lines": 1382233,
        "test_files": 6399,
        "test_lines": 1555450,
        "docs_files": 609,
        "docs_lines": 105966,
        "first_commit_at": "2026-02-14T22:42:38-05:00",
        "last_commit_at": "2026-10-16T15:39:17-04:00",
        "vcs_age_days": 244,
        "sase_first_at": null,
        "sase_age_days": null
      },
      "sase_work": {
        "beads": {"open": 0, "claimed": 12, "status": "ok"},
        "artifacts": {"status": "ok"},
        "agents_7d": {"runs": 0, "status": "ok"}
      },
      "repos": [
        {
          "name": "sase",
          "kind": "primary",
          "status": "ok",
          "path": "/home/bryan/projects/github/sase-org/sase",
          "head": "7a1b2c3deadbeef",
          "dirty": false,
          "commits": 16181,
          "origin": {"stitch": 6586, "auto": 333, "manual": 9262},
          "buckets": {
            "source": {"files": 5980, "lines": 1382233},
            "tests": {"files": 6399, "lines": 1555450},
            "docs": {"files": 609, "lines": 105966},
            "snapshots": {"files": 44, "lines": 44117},
            "assets": {"files": 1151, "lines": 0},
            "config": {"files": 62, "lines": 15021},
            "generated": {"files": 0, "lines": 0},
            "other": {"files": 124, "lines": 49433}
          },
          "languages": [
            {"name": "python", "files": 5951, "lines": 1367801}
          ]
        }
      ]
    }
  ],
  "totals": {
    "owner_once": true,
    "commits": 16181,
    "source_lines": 1382233,
    "docs_lines": 105966
  },
  "issues": []
}
```

`schema_version` lives in rust next to the wire types, mirrored in Python, bumped on incompatible shape changes. Same discipline as `ARTIFACT_STATS_SCHEMA_VERSION` and `AGENT_STATS_WIRE_SCHEMA_VERSION`.

### `jsonl` — scripts

One JSON object per line, no indent:

- `{"type":"meta", ...scope, measured_at, schema_version}`
- `{"type":"project", "name":"sase", "headline":{...}}`
- `{"type":"repo", "project":"sase", "name":"sase-core", "kind":"linked", ...}`
- `{"type":"totals", ...}`
- `{"type":"issue", "project":"sase", "message":"..."}`

This is the `sase var --format jsonl` idea applied to a scan. Cheap to emit from the same iterator. Useful for `jq -c 'select(.type=="repo")'`.

## Architecture

Litmus test from rust-core-required: if CLI, TUI, and another frontend must agree on the number, it is core.

```text
┌──────────────────────────────────────────────────────────┐
│ CLI  sase project stats     TUI (follow-up)    agents    │
│ Python: parser, inventory, VCS spawn, Rich/md render     │
└──────────────────────────────┬───────────────────────────┘
                               │ collect_repo_inventory
                               │ vcs_log / git ls-files
                               ▼
┌──────────────────────────────────────────────────────────┐
│ sase_core::project_stats                                 │
│  ProjectStatsRequestWire / ProjectStatsReportWire        │
│  classify paths → buckets                                │
│  count physical lines                                    │
│  fold VcsCommitWire → origin + first/last                │
│  owner-once totals (disk_inventory pattern)              │
└──────────────────────────────────────────────────────────┘
                               │
          classify_commit_origin, source_language, disk_inventory
```

Python owns: argparse, project resolution, repo inventory, spawning git through the VCS provider, Rich and markdown rendering, calling existing bead/artifact/agent facades for the SASE work panel.

Rust owns: wire schema, path classification, line counting over bytes, commit-origin aggregation, owner-once totals. No `macro_rules!`. Facade `mod.rs` is `mod` + `pub use` only.

New VCS hook, kept small:

```python
def vcs_ls_tracked(self, cwd: str, revision: str) -> list[str]: ...
```

Git implementation: `git ls-files -z` when `revision in {None, "HEAD"}` and the worktree is what we are counting; later `git ls-tree -r --name-only -z <rev>`. Mercurial can return `[]` and mark the repo `status: unsupported` until a provider implements it. Do not hardcode `git` in the stats handler.

Binding registration follows `docs/contribute/rust-backend.md`: core function + `*Wire` types, pyfunction in the matching domain, `m.add_function`, round-trip test, then ratchet `sase-core-revision.txt` in the same landing.

## Performance

Measured informally on this sase primary tree: listing 14,369 tracked files and counting text lines is a few seconds. Parsing 16,181 commit messages for origin is a single `git log` stream plus a linear fold. Scanning every enabled project today is three projects, of which sase dominates.

v1 rules:

- Parallelize **per repo**, not per file.
- JSON/pretty share one computed report; renderers are pure.
- No on-disk cache in v1. If a TUI panel needs sub-100ms, cache keyed by `(path, head_sha, classifier_version)` as follow-up.
- Progress on stderr only when the scan exceeds ~2s and stdout is a TTY. Never pollute JSON stdout.
- `--strip` still scans (the strip needs real numbers). It only changes rendering.

## Beauty

CLI rules: prefer colored output when it helps, excellent `-h`, sorted options.

- Title the pretty panel with `+name` in the project accent, matching `sase project current`.
- KIND column uses the same colors as `sase repo list`.
- Compact millions as `1.38M` in pretty; exact integers in JSON and markdown tables.
- `missing` is dim yellow, never `0`.
- A one-line coverage footer when anything was omitted (hidden sidecars, missing clones, dirty worktree).
- `--help` epilog states the commit-count definition in one sentence so the launch-post author does not have to read this research.

Do not add ASCII language logos (onefetch). That is a different product and fights SASE's panel language.

## Testing and docs

- Parser tests next to `tests/main/test_project_parser.py`.
- Handler tests with a fake inventory and a temp git repo (one commit with a SASE footer, one without, one markdown file, one python file, one snapshot path).
- Rust unit tests for bucket classification, linguist attributes, owner-once totals, origin fold.
- Completing the argparse tree will refresh `tests/completion/snapshots/cli_spec.json` (~42k lines). That is expected; it is a generated snapshot, not a mystery.
- Docs: this is a new user-visible command. `just fix` regenerates `docs/reference/cli/project.md`. No Guide page in the same change; note a guide candidate as `PROPOSED FOLLOW-UP` if the implementing bead is an epic phase. Decision record only if we freeze the commit-count definition as a durable choice (worth a short `decisions:` strand: "headline commits are `rev-list HEAD`").

`just check` is the agent verification recipe. Do not run `just check-full` unless asked.

## Phased delivery

### Phase 1 — launch-post MVP (implement this)

CLI + rust classifier + VCS ledger + pretty/markdown/json (+ jsonl if the iterator is already there) + `--strip` + `--all` / names / `--current-only` / `--include-hidden`. Headline fields: commits, stitch share, source files/lines, docs files/lines, first/last commit, VCS age, `measured_at`, `head`.

This unblocks the launch post by itself.

### Phase 2 — SASE work panel

Compose bead / artifact / agent-run / patch counts from existing facades. Same envelope, extra object `sase_work`. Still no TUI.

### Phase 3 — follow-ups (do not load into v1)

- Blob-accurate `--rev` via `cat-file --batch`.
- Comment/blank/code split.
- TUI Projects tab panel.
- `.gitattributes` authoring for sase itself (`tests/completion/snapshots/* linguist-generated`, screenshot goldens `linguist-generated`) so GitHub language stats and this command agree.
- Windowed LoC (git of theseus). Park it. The parked "ledger" blog post can use Phase 2, not this.

## Risks

- **Dishonest LoC.** Mitigated by buckets and by printing the definition.
- **Double-counting linked repos in `-a`. ** Mitigated by owner-once totals.
- **Dirty agent workspaces.** Mitigated by `dirty` flag and a pretty warning; launch-post runs should use a clean checkout.
- **GPL contamination.** Mitigated by in-process counting; never vendor tokei.
- **Kitchen sink.** Mitigated by phasing; v1 is the VCS ledger.
- **Collision with `src/sase/stats/`.** Mitigated by naming `project_stats`.
- **cli_spec snapshot noise.** Expected; call it out in the PR.
- **"Motion isn't progress."** The pretty epilog should not moralize. The launch post will. The command's job is to make the numbers true enough to undercut.

## Recommended solution

Implement `sase project stats` as a **read-only, rust-backed project ledger**.

1. **Parser** on `sase project stats [PROJECT ...]`, default current, `-a` for enabled fleet, `-f pretty|markdown|json|jsonl` with `-j` shorthand, `-s/--strip` for the launch-post headline, `-o/--current-only`, `-i/--include-hidden`, `-k/--kind`, `-r/--rev`.
2. **Inventory** from `collect_repo_inventory`. One clone per repo. Hidden sidecars off by default. Externals off by default.
3. **Core** module `project_stats` that classifies paths, counts physical lines, folds `VcsCommitWire` origin, and produces a versioned `ProjectStatsReportWire`. Reuse `classify_commit_origin` and `source_language`. Owner-once totals on the disk-inventory pattern.
4. **Host** Python adapter + Rich/markdown renderers modeled on `sase artifact stats` and `sase repo list`. Display names only in human formats.
5. **Headline definition, frozen in help and JSON:**
   - commits = `git rev-list --count <rev>` (default `HEAD`)
   - stitch share = `(stitch + legacy-footer stitch) / commits`
   - source / tests / docs = physical lines in those buckets
   - age = first commit author-date on that rev → last
6. **Do not** wrap tokei/scc, default to all projects, fold tests into code, scan the agents sidecar, or block v1 on a TUI panel.

That is the command I would implement for the launch post, and keep: a ledger agents can re-run on publish day, pretty enough to read, strict enough that 11,000 cannot sneak back in as 3 million.

## Evidence appendix

Taken 2026-10-16 on the sase primary checkout used for this research. These are **not** publishable launch-post figures; they exist to size the problem and to pin definitions.

**sase primary**

- `rev-list --count HEAD` = 16,181; `--first-parent` = 16,045; `--all` = 16,383
- first commit 2026-02-14T22:42:38-05:00; last 2026-10-16T15:39:17-04:00
- tracked files 14,369
- origin on `HEAD`: stitch 3,884 + legacy 2,702 = 6,586; auto 333; manual 9,262
- buckets (physical lines): source 5,980 files / 1,382,233 lines; tests 6,399 / 1,555,450; docs 609 / 105,966; snapshots 44 / 44,117; assets 1,151 / 0; config 62 / 15,021; other 124 / 49,433
- Python alone: `src/` 5,951 files / 1,367,801 lines; `tests/` 6,310 / 1,543,604
- largest text file: `tests/completion/snapshots/cli_spec.json` at 42,461 lines

**sase-core (linked)**

- 1,563 commits; 1,421 tracked files; first 2026-04-28; last 2026-10-16

**research sidecar**

- 2,064 commits; 5,269 tracked files; first 2026-07-11; last 2026-10-16

Enabled projects on this host: `sase`, `bob-cli`, `job`.

## Sources

- `research:202610/sase_launch_post_outline/sase_launch_post_outline.md` (audited read)
- SASE CLI: `parser_project.py`, `project_handler.py`, `repo_handler_list.py`, `artifact_cli/stats.py`, `parser_gate.py`, `parser_tool.py`, `parser_stitch.py`, `vcs_log_facade.py`, `repo_inventory.py`, `_linked_repo_config_keys.py`
- sase-core: `commit_footer.rs`, `agent_stats/wire.rs`, `source_language.rs`, `disk_inventory.rs`, `git_query/`, `vcs_log/`; binding `classify_commit_origin`
- Memory: `cli_rules.md`, `sase_artifacts.md`, `docs_writing.md`, glossary `Sase Project` / `Sase Repo`
- Decisions: `rust-core-required`, `project-labels-never-keys`, `check-full-is-explicit`
- External: [tokei vs scc](https://www.libhunt.com/compare-tokei-vs-scc), [scc](https://github.com/boyter/scc) (MIT, Go — still a subprocess, still origin-blind), [tokei](https://github.com/XAMPPRocky/tokei) (GPL-3.0), [onefetch](https://github.com/o2sh/onefetch) (pretty git summary; JSON/YAML only), [GitHub Linguist overrides](https://github.com/github-linguist/linguist/blob/master/docs/overrides.md), [cloc counting advice](https://slaptijack.com/articles/counting-lines-of-code-by-language.html)
- Live git on the sase primary, sase-core linked clone, and research sidecar, 2026-10-16
