# `sase project stats`: Consolidated Design and Recommendation

> **Research request:** Add `sase project stats [<project_name>]` to report useful stats about one SASE project, or all
> projects when no name is given. Cover commit counts, line and file counts for code and docs, and how long the project
> has been active, separated by repo for every repo linked to the project. Support formats for humans, agents, and
> scripts. Critique the plan, call out requirement changes, and end with a recommended solution. Context: the numbers
> feed sase's launch post.

**Lead researcher:** final consolidation · **Date:** 2026-10-16 · **Inputs:** five independent reports in this directory
(`__cdx`, `__cld`, `__grk`, `__mus`, `__gem`) plus my own verification against sase `origin/master` `577ebb554f`,
sase-core `594faf31`, the tokei crate metadata, and the live repo inventory.

## Bottom line

1. **Build it, as a repo-truth report with frozen definitions, not a dashboard.** The strongest argument is not "the
   launch post needs numbers". It is that hand-derived numbers keep disagreeing. Launch research has already quoted
   11,000+, 15,755, 15,756, and 16,181 commits; 6,349, 6,792, and 8,593 agent-signed commits; and 2.3M, 2.5M, 2.74M,
   and 3.0M "lines". Each was a correct answer to a slightly different, unlabeled question. A command that owns one
   printed definition per metric ends that.
2. **The launch post's agent-attribution figure is too low.** I verified cld's finding. Agents signed commits with a
   bare `AGENT=` footer from **2026-05-24**. The `SASE_` prefix only arrived on 2026-06-27. Counting both spellings,
   **8,598 of 16,186** sase commits (53%) are agent-signed, against 6,778 with the prefix alone. The share is **95.1%
   since June 1** and **98.9% over the last 30 days**. Only a footer-aware counter gets this right. sase-core's
   `parse_commit_footer` already normalizes both spellings, while git's `%(trailers)` finds none.
3. **Keep "no project name = every enabled project", as you asked.** cdx, cld, and mus agree, and it matches what
   `sase project list` means inside the `project` group. I reject the current-project default that grk and gem
   proposed (§2).
4. **The hardest decision is which repos count. Use three tiers:**
   - **Code repos** are the primary plus the linked repos the project declares itself. They are totaled.
   - **Record repos** are sidecars. They are listed but never totaled.
   - **Not counted** are opened external repos and user-wide linked repos such as `chezmoi`. They are named, not
     measured.

   gem's sum over everything turns sase into "37,598 commits", and most of those are bead, plan, and agent sync
   traffic.
5. **Measure committed snapshots, not working trees.** Read each repo's default branch from its canonical clone,
   offline by default. Add `-F/--fetch` for publish day. Agents run inside dirty or detached workspaces, and tokei over a
   checkout counts a different file set than git tracks.
6. **Classify files by role.** The roles are source, tests, docs, agent context, and config/data. Generated, vendored,
   and binary files are excluded but reported. Tests are **53%** of sase's code lines in `src/`+`tests/`, so folding
   them silently into "code" is the single most misleading thing the command could do. Show code lines next to a test
   share.
7. **Put the engine in sase-core and embed the tokei crate over git blobs.** The crate is **MIT OR Apache-2.0**; I
   checked crates.io, and grk's GPL objection is wrong. But it adds about a dozen new crates to sase-core, which no
   report measured (§7). Python keeps resolution, inventory, and the renderers. I reject mus's Python-only design with
   "tokei binary if present, git fallback otherwise", because two counters produce two answers on two machines.
8. **Formats:** `-f/--format {auto,csv,json,markdown,table}` plus `-j`.
   - `auto` prints the table on a terminal and Markdown when piped. Agents run through pipes, and `> stats.md` gives
     you something to paste.
   - JSON is one versioned envelope and the full contract.
   - CSV has one row per repo.
   - No YAML, JSONL, or separate "summary" format.
9. **Fix three things first (phase 0).**
   - **`sase-1lk`:** I reproduced it. Run from inside the sase checkout, `sase repo list -p gh_bobs-org__bob-cli` lists
     sase's linked repos under bob-cli.
   - **Missing provenance:** the inventory cannot tell a project-declared linked repo from a user-wide one. Both report
     `source: "repos.linked config"`. This relates to `sase-1l2`.
   - **The `-p` resolver:** it still resolves directory keys only (`sase-zo`).
10. **If the post publishes before the command lands,** use the corrected one-liners in §9.

## 1. Is this a good idea?

**Yes, kept narrow.** All five reports agree, and the evidence supports them.

- **It stops definitional drift.** Today there is no single answer to "how big is sase?" (§1.2).
- **Generic tools can't produce the interesting numbers.** tokei, scc, cloc, and onefetch see one working tree. They
  know nothing about SASE projects, linked repos, sidecars, or the commit footer. The agent-signed share is SASE-only
  data.
- **Agents need ground truth.** Agents writing READMEs, release notes, or post drafts currently re-derive or invent
  numbers. A versioned JSON answer is cheaper and more honest.
- **It demos well.** One screenshot of the stats card answers "what is this project?"

**Risks, with mitigations built into the design:**

| Risk | Mitigation |
| --- | --- |
| Vanity metrics. LoC is a liability and commits reward motion; the outline itself says *"Motion isn't progress."* | Descriptive metrics only. No productivity score, COCOMO cost, per-author ranking, or streak trophies. Test share sits next to code lines. The command reports facts; the post interprets them. |
| Silent wrongness: an uncloned repo, shallow clone, stale ref, or misclassified directory produces a believable wrong number. | Coverage line ("6 of 7 code repos"), `·`/`null` for unknown and never `0`, ref provenance with fetch age, and definitions printed in `-h` and in every human footer. |
| Scope creep into an analytics dashboard (beads, runs, tokens). | Phase 1 is repo truth only. Bead, artifact, tool, and agent-run stats already have their own commands (`sase bead stats`, `artifact stats`, `tool stats`, the TUI Statistics pane). |
| Double counting: shared repos, user-wide linked repos, sidecars. | Tiered scope, SHA-deduped commit totals, repo-identity dedupe across projects. |

**Would I take a different approach?** Same command and the same place in the CLI: `project stats` sits naturally beside
`bead stats`, `tool stats`, and `artifact stats`. I would change what "the project's repos" means, what "lines" and
"active" mean, and which formats ship. Those changes are listed in §3.

### 1.1 What the launch post actually needs

The audited outline (`research:202610/sase_launch_post_outline/sase_launch_post_outline.md`) asks for:

- one *"3–4-number stats strip (commits, agent-attributed share, months), re-derived on publish day and undercut by
  'Motion isn't progress'"*;
- the strip paid off later in "What It Cost";
- a fuller "ledger" post, parked for later.

So the command must produce a small set of **dated, scoped, re-runnable** numbers, plus a JSON record to archive next
to the post. It does not need to be a ledger product.

### 1.2 Verified facts (lead researcher, 2026-10-16)

| Fact | Value | How measured |
| --- | --- | --- |
| sase commits | **16,186** reachable from `origin/master` (16,050 first-parent, 103 merges) | `git rev-list --count` |
| Agent-signed, either spelling | **8,598 (53.1%)**; 6,778 with `SASE_AGENT=` only | `git log -E --grep='^(SASE_)?AGENT='`, which approximates the footer parser |
| Start of signing | bare `AGENT=` first appears 2026-05-24 (`1cf2cf54c0`); `SASE_AGENT=` first appears 2026-06-27 (`0682924ec8`) | `git log --reverse` |
| Agent-signed share | since Jun 1: 95.1% (8,227/8,650) · since Jul 1: 95.6% (6,545/6,847) · last 30 days: 98.9% (1,834/1,854) | same |
| Age and activity | first commit 2026-02-14; 244 days old; commits on **239** distinct days | the same 239 whether days use the author's offset, the committer's offset, or UTC |
| Author identities | 5 raw identities. Bryan under 2 emails accounts for 16,179 commits; `sase@localhost` has 4; 2 bots. No `.mailmap`. | `git shortlog -sne` |
| Committed tree | 14,393 tracked entries, 306 MB of blob bytes, mostly binary screenshot goldens | `git ls-tree -r -l` |
| Lines (tokei 14 over `git archive origin/master`) | `src/`: 6,052 files, 1,195,248 code lines (1,385,326 physical) · `tests/`: 6,379 files, 1,341,602 code (1,599,279 physical) · `docs/`: 407 files, 92,080 physical · all Python: 2,512,923 code lines | tokei JSON per directory |
| Timing (apollo) | full-body `git log`: 0.21 s · `ls-tree` + `cat-file --batch` over every blob: 2.2 s · tokei parse: 0.5 s wall · `ls-tree` of the 129k-file agents sidecar: 0.23 s · `--numstat` over two weeks: 7.5 s (cld measured 91 s for all history) | `time` |
| Sidecar commits | agents 8,343 · plans 9,458 · research 2,074 · attachments 1 · attachments-private 2 · beads 23,378 (cld; not cloned in my workspace) | `rev-list --count HEAD` |
| sase-core | 1,563 commits, first commit 2026-04-28. The `sase-core-revision.txt` pin `594faf31` equals sase-core `origin/master` today. | git |
| `chezmoi` | Declared in `~/.config/sase/sase.yml`, so it appears under **every** project. Its inventory record reports the same `source: "repos.linked config"` as sase-core. | `sase repo list -j`, config grep |
| tokei crate | 15.0.0, **MIT OR Apache-2.0**. `default = ["cli"]`. Even without `cli` it pulls in `rayon`, `ignore`, `grep-searcher`, `crossbeam-channel`, `parking_lot`, `etcetera`, `toml`, `encoding_rs_io`, `table_formatter`, `term_size`, and `clap-cargo`, with `tera` as a build dependency. None of these is in sase-core's `Cargo.lock` today; `dashmap` already is. | `cargo info tokei`, the crate's `Cargo.toml`, sase-core `Cargo.lock` |

**Reconciling the reports' LoC figures.** Every published "lines" figure is right for its own unstated definition:

| Report | Figure | What it actually counts |
| --- | --- | --- |
| gem | 1.18M source / 1.29M tests | tokei code lines in `src/` and `tests/` |
| grk | 1.38M / 1.56M | physical lines |
| cld | 2.52M | tokei code lines for source plus tests, by role |
| — | 3.0M / 3.14M | every physical text line |
| launch drafts | 2.74M | physical Python lines |

That is the case for the command in one table.

## 2. Where the reports disagreed, and how I resolved each point

| Question | Positions | Resolution | Why |
| --- | --- | --- | --- |
| Scope with no `PROJECT` | cdx, cld, mus: all enabled projects. grk, gem: the current project, with `-a` for all. | **All enabled projects.** Explicit names select those projects, and `-D` adds disabled ones. | It is your requirement and the `project list` meaning within this group. With 3 enabled projects the cost is seconds. Inferring the current project from cwd is exactly the path `sase-1lk` shows to be fragile. `sase project stats +sase` is one word away. |
| Sidecars | gem: sum everything. grk: total the visible sidecars, hide `agents`/`attachments`. cdx: a separate group, no grand total. cld: a records tier, never totaled. | **cld's records tier.** Every configured sidecar gets one compact line with commits, tracked files, and first/last commit. No line scan by default; never totaled. | Sidecar commits are machine bookkeeping: beads alone has 23,378 "chore" syncs. Hiding sidecars entirely breaks "never silently omit". |
| Totals | cdx: none. cld: code tier, SHA-deduped. grk: count each owner once. gem: plain sum. | **Per-project totals over the code tier only.** Commits are deduped by SHA, active days are unioned, and the total is labeled with coverage ("6 of 7"). The all-projects total dedupes repos by identity. | The total is useful for the launch strip. Coverage labels and dedupe prevent the known failure modes. |
| What gets measured | cdx, cld: a committed default-branch commit. grk, mus: `HEAD` plus a working-tree `ls-files` scan. | **The committed default branch, read from the canonical clone.** | Agents run in numbered workspaces that are routinely on feature branches or dirty. Numbers must not depend on which workspace ran the command. |
| Network | cld: fetch by default through the `stitch list` freshness cache. cdx: never. | **Offline by default, `-F/--fetch` to opt in.** Print the ref's age ("local refs, fetched 2 h ago"). | Offline by default is predictable and safe for agents. Publish day passes `-F`. |
| Pinned linked repos | cdx: measure the pinned commit. cld: measure the default branch. | **Measure the mainline and report the pin and its lag** in details and JSON. | "How big is the project" means mainline work, and it matches GitHub. Pin lag is a useful fact on its own. |
| Line counter | cdx, cld: the tokei crate over blobs. grk: in-house physical lines (citing a false GPL concern). mus, gem: the tokei binary with a fallback. | **The tokei crate over blobs**, with `default-features = false`. Adding it is gated on a build-cost check (§7). | It has a valid license, covers 200+ languages, and matches the convention readers will verify with `tokei` or `scc`. A binary dependency plus a fallback means non-reproducible numbers. |
| Line unit | SLOC (cld, cdx), physical (grk), mixed (others). | **Code lines = SLOC** (no blanks, no comments). **Doc lines = non-blank.** Physical lines, comments, and blanks are in JSON. | Neither headline unit counts blank lines, and SLOC is checkable with standard tools. |
| Tests | cld: a share of code. grk, gem: a separate bucket. | **A separate role in the data.** Human views show code lines plus a test share, and JSON carries the split. | "3.1M code lines · 46% tests" is compact and impossible to quote without seeing the tests. |
| Rust or Python | mus: Python. The rest: Rust. | **Rust (sase-core).** | Decision `rust-core-required` and the core-boundary litmus test apply. The TUI's Projects pane (`projects_pane_subtabs.py`) and the mobile gateway are likely second consumers. |
| Durable cache | cld: SQLite keyed by blob OID. gem: JSON keyed by SHA. The rest: none in v1. | **None in v1.** Memoize within one invocation. | Measured cold work for the sase project is a few seconds. Add a blob-OID cache when a TUI panel needs sub-second answers. |
| Exit codes | cdx: 3 for a partial report. The rest: 0 with `issues[]`. | **0** with `coverage` and `issues[]`; **1** when nothing could be measured; **2** for usage errors. | This matches `tool stats` and `artifact stats`. Scripts check completeness with `jq -e .coverage.complete`. |
| SASE work panel (beads, artifacts, runs) | gem: v1. grk: phase 2. cld: detail mode. cdx, mus: out. | **Out of v1.** Point to the existing commands. Phase 2 can add an opt-in section. | Those stores already have owners, and composing them adds failure modes to a launch-critical command. |
| `--since` / `--until` (as-of) | cld: v1. grk: history windows. cdx: defer, warning about membership drift. | **Phase 2.** The core API takes an explicit per-repo revision, so as-of support is cheap later. | Publish day needs "run it today and archive the JSON", not time travel. |
| Clock and day buckets | cdx: committer time, UTC. cld: local time. Others: author time. | **Author time, bucketed by each commit's recorded offset** (`%as`). | Deterministic across machines, matches the author's own day, and consistent with the existing `vcs_log` wire. It is low-stakes: sase shows 239 active days under all three choices. |
| Headline-only mode | grk: `--strip`. gem: `--summary`. | **No extra flag.** Table and Markdown both open with the headline block. | One less option. The strip is the first thing printed in both formats. |

## 3. Requirement adjustments (called out)

| # | As requested | Adjusted to | Why |
| --- | --- | --- | --- |
| **A1** | "All repos linked to the targeted project(s)" | Every repo is shown, in **three tiers**: code (totaled), records (listed, never totaled), and not counted (named only). | Sidecar bookkeeping would swamp the totals. `chezmoi` is user-wide and appears under every project. External repos are ad-hoc `sase repo open` checkouts. |
| **A2** | "Commit counts" | Commits plus the **agent-signed count and share** (both footer spellings) and commits in the last 30 days. | This is the distinctive SASE number, and the launch strip asks for it. |
| **A3** | "Line and file counts for code and docs" | **Roles:** source, tests, docs, agent context, config/data. Generated, vendored, and binary files are excluded but reported. Code = source + tests, shown with a test share. | "Code vs docs" hides that half the code is tests. Memory notes, macros, skills, and `AGENTS.md` files are neither product code nor user docs, and in a SASE project they are worth showing. |
| **A4** | "Length of time the project has been active" | **First commit and age**, **active days** (distinct commit days, unioned across code repos), and **last commit**. | "Active" is ambiguous. sase spans 245 calendar days (244 elapsed) and has commits on 239 of them. |
| **A5** | No name = all projects | **Kept.** It means enabled projects; `-D` adds disabled ones, and several names may be given. | Your requirement, matching `project list`. |
| **A6** | (unstated) | **Committed snapshots** of each repo's default branch, offline by default, with ref provenance printed. | Reproducibility. Workspace state must not change the numbers. |
| **A7** | "Various formats" | `auto`, `table`, `markdown`, `json`, `csv`. | Details in §6. |
| **A8** | (unstated) | **Nothing evaluative:** no COCOMO, productivity, rankings, or streaks. | These numbers mislead for agent-written code and invite justified skepticism. |
| **A9** | (scope) | **Deferred to phase 2:** churn, author breakdown, commit-origin mix, growth over time, `--since`/`--until`, the provider/model mix of agent-signed commits, bead/run sections, and a durable cache. | Each one is slow (churn takes about 90 s cold), depends on an optional store, or isn't needed for the post. |

## 4. The metric contract

### 4.1 Phase-1 metrics

Every metric is reported per repo. Code-tier metrics are also totaled per project.

| Metric | Definition | Shown in |
| --- | --- | --- |
| Commits | Distinct commits reachable from the measured ref, merges included. Merges are counted separately in JSON. Project totals dedupe by SHA. | all formats |
| Agent-signed commits and share | Commits whose terminal SASE footer, parsed by core `parse_commit_footer`, has a non-empty `AGENT` tag (`SASE_AGENT=` or legacy `AGENT=`), counted once per commit. The share uses the same denominator. | all formats; the card also shows the last-30-day share |
| Commits in the last 30 days | `[measured_at − 30 d, measured_at]` | all formats |
| First commit, last commit, age | Minimum and maximum author timestamp over the reachable set. Age is first commit to `measured_at`. | card, Markdown, JSON, CSV |
| Active days | Distinct dates (in each commit's own offset) with at least one commit, unioned across a project's code repos | card, JSON |
| Monthly commits and agent share | Per calendar month | card sparklines, JSON array |
| Code files and code lines | Source plus tests, tokei `code` | all formats |
| Test share | Test code lines ÷ code lines; `null` when there are no code lines | all formats |
| Doc files and doc lines | Docs role, non-blank lines (tokei's Markdown "code" count is not used) | all formats |
| Agent-context files and lines | Memory, macros, skills, and `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`-style files | card, JSON |
| Languages | Top 3 plus "other" by code lines | card bar, JSON full list |
| Latest release tag | Newest tag merged into the ref, and commits since it | card, JSON |
| Records tier | Commits, tracked files, first and last commit | its own section in every format |
| Coverage and issues | Repos configured, measured, unavailable, or partial, with typed issue codes | always visible |

**JSON-only fields:** physical lines, comments, blanks, blob bytes, excluded and binary counts, per-language-per-role
counts, the full commit SHA, the ref name, fetch time, shallow flag, pin and pin lag, and the classifier policy
version.

### 4.2 Role classification

Roles are assigned in this precedence order:

1. **`.gitattributes`:** `linguist-generated`, `linguist-vendored`, and `linguist-documentation`, read for the measured
   commit with `git check-attr --source <commit>`. These are the portable, GitHub-compatible overrides.
2. **Project config globs:** `project_stats.roles` in the repo's `sase/sase.yml`, with defaults in
   `src/sase/default_config.yml`.
3. **Built-in heuristics:**
   - test directories and filename patterns count as **tests**;
   - prose languages count as **docs**;
   - `sase/memory/`, `sase/macros/`, skills, and agent instruction files count as **agent context**;
   - data and serialization languages and lockfiles count as **config/data**;
   - golden and snapshot directories and minified files count as **generated**;
   - NUL-containing blobs and LFS pointers count as **binary**.

Classification rules:

- Every included file has exactly one role.
- Excluded files are counted with a reason.
- Unknown languages stay visible as "other".

**Documented limitations:**

- Rust inline `#[cfg(test)]` modules count as source, so sase-core's real test share is higher than the reported 22%.
- Squash-merge workflows undercount commits relative to work done.

### 4.3 Never in this command

Test-case counts, coverage percentages without a coverage report, COCOMO or "hours saved", tokens or dollars,
per-author or per-model rankings, complexity scores, bus factor, and GitHub stars or PR counts. A PR count could come
later through `sase-github`.

**Author counts are deferred, and the reason is itself a finding.** Agents commit under the user's identity, so sase has
"one human" regardless of how much agents wrote. If author stats ship later, add a `.mailmap` (Bryan currently commits
under two emails) and label them "author identities", not people.

## 5. CLI surface

The options are sorted and every public long option has a short alias (`cli_rules.md`). The positional's `dest` is
`project`, so shell completion picks up project names.

```text
usage: sase project stats [-h] [-d] [-D] [-f {auto,csv,json,markdown,table}] [-F] [-j]
                          [-r NAME] [PROJECT ...]

Report repository statistics for SASE projects, one row per repo: history (commits, agent-signed
share, age, activity), code and docs size by file role, and languages. Code repos (the primary and
project-declared linked repos) are totaled; sidecars are listed as records and never totaled. Each
repo is measured at the committed tip of its default branch, never a working tree. With no
PROJECT, every enabled project is reported.

positional arguments:
  PROJECT                 Project name, alias, directory key, or +tag (default: every enabled project)

options:
  -d, --details           Add per-repo languages, file roles, refs and pins, exclusions, and monthly tables
  -D, --include-disabled  With no PROJECT, also report disabled projects
  -f, --format {auto,csv,json,markdown,table}
                          Output format (default: auto = table on a terminal, markdown otherwise)
  -F, --fetch             Fetch each repo's remote before measuring (default: local refs only)
  -h, --help              show this help message and exit
  -j, --json              Shorthand for --format json
  -r, --repo NAME         Only report this repo (repeatable)

definitions:
  commits       commits reachable from each repo's default branch, merges included
  agent-signed  commits whose SASE footer carries an AGENT tag (SASE_AGENT= or legacy AGENT=)
  code lines    non-blank, non-comment lines in source and test files; tests = test share
  doc lines     non-blank lines in documentation files
  active days   distinct days with at least one commit in the project's code repos

examples:
  sase project stats
  sase project stats sase
  sase project stats +sase -F -f markdown > stats.md
  sase project stats sase -j | jq '.projects[0].totals.commits'
  sase project stats sase -r sase-core -d
```

**Behavior notes:**

- **Name resolution.** Names resolve by key, display name, or alias, case-insensitively, with `+` stripped. Use the same
  resolver as `sase project show`, not `resolve_project_context`, whose `-p` path still accepts directory keys only
  (`sase-zo`). Naming a disabled project reports it. An unknown name exits 2 with "did you mean" suggestions.
- **Format conflicts.** `-j` together with a non-JSON `-f` is a usage error. `-d` affects only table and Markdown,
  because JSON is always complete.
- **Placement.** Register `stats` alphabetically between `show` and `suggest`, and update the hard-coded metavar at
  `parser_project.py:74`. Bare `sase project` stays `list`.
- **A help-text collision to fix.** While there, change `sase bead stats`'s help from "Show project statistics" to
  "Show bead statistics" (`parser_bead_queries.py:556`).
- **About `auto`.** It is a deliberate first for sase. Other commands print Rich panels even when piped. It serves both
  agent and paste use cases, and `gh` and clig.dev endorse TTY-sensitive output. If you'd rather keep convention,
  default to `table` with automatic plain output when piped, and teach agents `-f markdown`. Everything else stays the
  same.

## 6. Output formats

**About the mockup numbers.** They come from cld's single 2026-10-16 prototype at `881f444778`, so they agree with each
other. They illustrate the layout, not publishable figures. The verified figures as of today are in §1.2.

### 6.1 `table`: one project (≥100 columns)

```text
╭─ sase · +sase ───────────────────────────────────────────── as of 2026-10-16 16:00 EDT ─╮
│                                                                                         │
│   Started    Feb 14, 2026 · 8 months old · commits on 239 of 245 days                   │
│   Commits    18,327 · 2,377 in the last 30 days · last commit 21 min ago                │
│   Agents     54% agent-signed · 95% in the last 30 days                                 │
│   Code       3,126,927 lines in 13,964 files · 46% tests                                │
│   Docs       81,941 lines in 509 files · 185 agent-context files                        │
│   Release    v0.17.1 · Aug 29 · 2,612 commits since                                     │
│                                                                                         │
│   Commits/month  ▂▄▄█▅▆▆▆▂    Agent share  ▁▁▁▁█████    Feb → Oct                       │
│   Languages      ██████████████████████████████████████████████▓▓▓▓▓▓▓▓▓░               │
│                  Python 82% · Rust 17% · other 1%                                       │
╰─────────────────────────────────────────────────────────────────────────────────────────╯

  CODE REPOS                        COMMITS  AGENT  30 DAYS  FIRST COMMIT  CODE LINES  TESTS  DOC LINES
  sase                     primary   16,181    53%    1,850  2026-02-14     2,521,676    51%     73,717
  sase-core                linked     1,563    62%      396  2026-04-28       536,490   22%¹      3,503
  sase-telegram            linked       307    36%       40  2026-02-28        33,698    53%      1,255
  sase-listen              linked        34    82%       34  2026-10-01        22,070    34%      1,633
  sase-github              linked       174    41%       26  2026-02-23        10,205    59%        651
  sase-research-artifacts  linked        68    93%       31  2026-08-11         2,788    91%      1,182
  sase-nvim                linked         ·      ·        ·  not cloned on this machine
  ──────────────────────────────────────────────────────────────────────────────────────────────────
  6 of 7 code repos                  18,327    54%    2,377  2026-02-14     3,126,927    46%     81,941

  RECORDS · sidecars, never totaled   COMMITS    FILES  FIRST COMMIT  LAST COMMIT
  beads                                23,378    8,655  2026-07-28    2 min ago
  plans                                 9,458    7,750  2026-07-11    1 h ago
  agents                                8,335  129,152  2026-07-23    4 min ago
  research                              2,067    5,272  2026-07-11    6 min ago
  attachments-private                       2        1  2026-09-30    16 days ago
  attachments                               1        0  2026-09-30    16 days ago

  ¹ Rust unit tests inside src/ count as source.   Not counted: chezmoi (user-wide linked repo)
  Local refs, fetched 2 h ago (-F to refresh) · Commits: reachable from each default branch
  Agent: SASE AGENT footer tag · Code lines: no blanks or comments · Tests: test share of code lines
  More: sase project stats sase -d   ·   Definitions: sase project stats -h
```

**Design rules:**

- **Accent and kind colors.** The panel border, title, and sparklines use the project accent (`project_accents.py`).
  The KIND column reuses `sase repo list`'s colors (primary `#00D7AF`, linked `#87D7FF`, sidecar `#AF87FF`). The
  language bar uses linguist colors.
- **Exact numbers in table cells,** since people quote cells. Friendly numbers ("8 months", "21 min ago") appear only
  in prose.
- **`·` for unknown, never `0`.** Unavailable rows are dim and say why.
- **Coverage and definitions are always printed.** The total row reads "6 of 7", and the footer names what was not
  counted and defines every headline term.
- **Responsive.** At 80 columns, drop FIRST COMMIT and DOC LINES and wrap the legend. Below that, switch to vertical
  per-repo cards and never truncate numbers. On a dumb or non-UTF-8 terminal, fall back to ASCII sparklines and bars.
  Honor `NO_COLOR` and `FORCE_COLOR`.
- **stdout carries only the report.** Progress goes to stderr, only on a TTY, and only after about 2 s.

### 6.2 `table`: all projects

```text
╭─ SASE projects · 3 enabled ──────────────────────────────────── as of 2026-10-16 16:00 EDT ─╮
│                                                                                             │
│   PROJECT   REPOS   COMMITS  AGENT  30 DAYS  FIRST COMMIT  CODE LINES  TESTS  DOC LINES     │
│   sase      6/7      18,327    54%    2,377  2026-02-14     3,126,927    46%     81,941     │
│   bob-cli   3/3       1,331    88%      516  2026-06-01       369,231    36%          ·     │
│   job       1/1           8    13%        8  2026-10-11             ·      ·          ·     │
│   ──────────────────────────────────────────────────────────────────────────────────────    │
│   Total     10/11    19,666    56%    2,901  2026-02-14     3,496,158    45%          ·     │
│                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
  (then one section per project, as in §6.1; a repo shared by two projects is counted once in Total)
```

`job` has zero code files: its code cells are `·`, not a division by zero. cld's prototype crashed on exactly this
case. The bob-cli figures cover its primary repo only, and its doc-line count was not measured.

### 6.3 `markdown`: paste-ready and agent-friendly

GitHub-flavored, numeric columns right-aligned, no HTML, ANSI, or box drawing. It renders the same on GitHub, in MkDocs,
in Obsidian, and in an agent's context, and it ends with the exact command and versions that produced it.

```markdown
## sase

*As of 2026-10-16 16:00 EDT · each repo at its default branch (local refs, fetched 2 h ago) · 6 of 7 code repos counted*

- **18,327 commits** since 2026-02-14 (8 months), with commits on 239 of 245 days
- **54% agent-signed** overall; 95% in the last 30 days
- **3,126,927 code lines** in 13,964 files; 46% tests
- **81,941 doc lines** in 509 files; 185 agent-context files
- **Languages:** Python 82%, Rust 17%, other 1%

| Repo | Kind | Commits | Agent-signed | Last 30 days | First commit | Code files | Code lines | Tests | Doc files | Doc lines |
| --- | --- | --: | --: | --: | --- | --: | --: | --: | --: | --: |
| sase | primary | 16,181 | 53% | 1,850 | 2026-02-14 | 12,425 | 2,521,676 | 51% | 434 | 73,717 |
| sase-core | linked | 1,563 | 62% | 396 | 2026-04-28 | 1,290 | 536,490 | 22% | 22 | 3,503 |
| … | | | | | | | | | | |
| sase-nvim | linked | — | — | — | — | — | — | — | — | — |
| **Total (6 of 7)** | | **18,327** | **54%** | **2,377** | 2026-02-14 | **13,964** | **3,126,927** | **46%** | **509** | **81,941** |

**Sidecar records (not totaled):** beads 23,378 commits · plans 9,458 · agents 8,335 · research 2,067 · attachments-private 2 · attachments 1.
**Unavailable:** `sase-nvim` (not cloned on this machine). **Not counted:** `chezmoi` (user-wide linked repo).

*Definitions:* commits are reachable from each repo's default branch; agent-signed commits carry a SASE `AGENT` footer
tag; code lines exclude blanks and comments; tests is the test share of code lines; doc lines are non-blank.

Generated by `sase project stats sase -f markdown` (sase 0.17.1+2612.g881f44477, sase-core-rs 0.40.1).
```

Repo names are escaped (pipes, backticks, newlines). `-d` appends language, role, ref/pin, and exclusion tables.

### 6.4 `json`: the full, versioned contract

There is one object envelope even for one project. The Rust wire *is* the JSON (serde), so every frontend gets
identical numbers.

**Conventions:**

- `snake_case` keys.
- Integer counts and float shares in `[0, 1]`.
- RFC 3339 timestamps.
- **`null` for unknown, never `0`.**
- No preformatted strings.
- Deterministic ordering.
- Byte-identical output for identical inputs, apart from `measured_at`.

```jsonc
{
  "schema": "sase.project_stats",
  "schema_version": 1,
  "measured_at": "2026-10-16T20:00:00Z",
  "versions": {"sase": "0.17.1+2612.g881f44477", "sase_core_rs": "0.40.1", "classifier_policy": 1},
  "query": {"projects": ["sase"], "include_disabled": false, "repos": null, "fetch": false},
  "coverage": {"code_repos_configured": 7, "code_repos_measured": 6, "partial": 0, "complete": false},
  "projects": [{
    "key": "gh_sase-org__sase", "name": "sase", "tag": "+sase", "state": "enabled",
    "totals": {
      "commits": 18327, "agent_signed_commits": 9839, "agent_signed_share": 0.537,
      "commits_last_30d": 2377, "agent_signed_last_30d": 2259,
      "first_commit_at": "2026-02-14T22:42:38-05:00", "last_commit_at": "2026-10-16T15:39:17-04:00",
      "age_days": 244, "active_days": 239,
      "code": {"files": 13964, "lines": 3126927, "test_lines": 1444902, "test_share": 0.462},
      "docs": {"files": 509, "lines": 81941},
      "agent_context": {"files": 185, "lines": 8963},
      "languages": [{"name": "Python", "code_lines": 2579463, "share": 0.825}],
      "monthly": [{"month": "2026-02", "commits": 803, "agent_signed": 0}]
    },
    "repos": [
      {
        "name": "sase", "kind": "primary", "tier": "code", "status": "ok",
        "path": "/home/bryan/projects/github/sase-org/sase",
        "ref": {"name": "origin/master", "commit": "881f44477864…", "fetched_at": "…", "shallow": false, "pin": null},
        "history": {"commits": 16181, "merge_commits": 103, "agent_signed_commits": 8593, "commits_last_30d": 1850,
                    "first_commit_at": "…", "last_commit_at": "…", "active_days": 239,
                    "latest_tag": {"name": "v0.17.1", "at": "2026-08-29T…", "commits_since": 2612}},
        "snapshot": {"tracked_files": 14369,
                     "roles": {"source": {"files": 6085, "code": 1226205, "comments": 19546, "blanks": 172121},
                               "tests": {"files": 6340, "code": 1295471, "comments": 14049, "blanks": 240916},
                               "docs": {"files": 434, "lines": 73717, "blanks": 18085},
                               "agent_context": {"files": 175, "lines": 8718},
                               "config_data": {"files": 52, "code": 12320},
                               "other": {"files": 0, "lines": 0}},
                     "excluded": {"generated": {"files": 14}, "vendored": {"files": 0},
                                  "binary": {"files": 1269, "bytes": 194300000}},
                     "languages": ["…"]}
      },
      {"name": "sase-nvim", "kind": "linked", "tier": "code", "status": "unavailable",
       "issue": "not_cloned", "ref": null, "history": null, "snapshot": null}
    ],
    "records": [{"name": "beads", "kind": "sidecar", "tier": "records", "status": "ok",
                 "history": {"commits": 23378, "first_commit_at": "2026-07-28T…", "last_commit_at": "…"},
                 "snapshot": {"tracked_files": 8655}}],
    "not_counted": [{"name": "chezmoi", "reason": "user_linked"}]
  }],
  "totals": {"projects": 1, "commits": 18327, "...": "repos deduped across projects"},
  "issues": [{"project": "sase", "repo": "sase-nvim", "code": "not_cloned",
              "message": "linked repo is not cloned on this machine", "hint": "clone it at ../sase-nvim"}]
}
```

**Versioning and test fixtures:**

- Version the public schema separately from the internal binding.
- Additive optional fields are compatible. Changing a definition (units, default ref, counting rule) bumps the
  classifier policy or the schema.
- Check in a JSON Schema and fixtures.

**Agent and script usage:**

```bash
sase project stats sase -j > stats.json
jq -e '.coverage.complete' stats.json
jq '.projects[].repos[] | select(.kind == "primary") | .history.commits' stats.json
```

### 6.5 `csv`: one row per repo, for spreadsheets

- RFC 4180 with one header row, written with a real CSV writer.
- **One row per repo** across both tiers, with a `tier` column.
- **No total rows,** so summing a column can't double count. No thousands separators.
- Empty cell = unknown; `0` = measured zero.
- Columns are append-only.

```text
project,repo,kind,tier,status,ref,commit,first_commit_at,last_commit_at,commits,agent_signed_commits,commits_last_30d,active_days,code_files,code_lines,test_lines,doc_files,doc_lines,agent_context_files,top_language,issue
sase,sase,primary,code,ok,origin/master,881f444778…,2026-02-14T…,2026-10-16T…,16181,8593,1850,239,12425,2521676,1295471,434,73717,175,Python,
sase,sase-nvim,linked,code,unavailable,,,,,,,,,,,,,,,,not_cloned
sase,beads,sidecar,records,ok,origin/main,…,2026-07-28T…,…,23378,,,,,,,,,,,
```

**Formats considered and rejected:**

- **YAML:** sase doesn't emit YAML from its CLI, and it would add a second machine format for no new audience.
- **JSONL:** one envelope plus `jq` covers it.
- **TSV:** trivial to add later.
- **A separate `--summary`/`--strip` format:** the headline block opens both human formats.
- **An SVG/PNG stats card:** a screenshot of `table` covers the post.

## 7. Architecture and implementation

```text
sase (Python)                                         sase-core (Rust)
─────────────                                         ────────────────
parser_project.py: `stats` subparser
main/project_handler_stats.py (lazy import)
  resolve projects (alias-aware, + stripped)
  one repo_inventory_session() snapshot
  tier repos (needs linked-repo provenance)
  pick canonical clone, validate identity
  optional fetch (-F) via vcs fetch helpers
  core/project_stats_facade.py ─── request wire ──▶ project_stats::collect(request)
                                                       per repo, bounded parallel (≈4):
                                                         resolve ref → full commit, once
                                                         history: git log <commit> (streamed, full bodies)
                                                           → parse_commit_footer → AGENT, dates, months
                                                         snapshot: ls-tree -r -z -l <commit>
                                                           → check-attr --source <commit> (linguist-*)
                                                           → classify roles (policy, config globs)
                                                           → cat-file --batch (text candidates only)
                                                           → tokei LanguageType::parse_from_slice
                                                         records tier: rev-list + ls-tree count only
                                                       aggregate: repo → project (SHA dedupe) → portfolio
  render ◀──────────────────── ProjectStatsWire ──────
    table (Rich) · markdown · csv · json (= wire)
```

### 7.1 Where the code goes

**sase-core:**

- A new `crates/sase_core/src/project_stats/` module: a facade `mod.rs` plus `wire.rs`, `history.rs`, `snapshot.rs`,
  `classify.rs`, `aggregate.rs`, and tests.
- Reuse `commit_footer::parse_commit_footer`, and don't write a second attribution regex. Reuse the existing git-runner
  pattern; core already shells out to `git` in many places, so don't add `gix` or `git2`.
- One batch binding, `project_stats_collect`, using `py.allow_threads` and modeled on existing Rust-run git walks. Add
  a wire round-trip test.

**sase:**

- `src/sase/core/project_stats_facade.py`, using `require_rust_binding(...)`.
- A `src/sase/project_stats/` package holding resolution and the table, Markdown, and CSV renderers. Do **not** put it
  in `src/sase/stats/`, which is the TUI agent-run adapter.
- `src/sase/main/project_handler_stats.py` and the parser.
- `project_stats:` defaults in `src/sase/default_config.yml`, per the gotchas memory.
- The CLI reference page; read `docs_writing.md` first.
- The regenerated completion snapshot.
- Move `sase-core-revision.txt` past the implementing core commit.

### 7.2 The tokei dependency gate (a gap no report closed)

**The license is fine** (MIT OR Apache-2.0). **The weight is not trivial.** Even with `default-features = false`, the
crate brings in roughly a dozen crates new to sase-core's lock file: `rayon`, `ignore`, `grep-searcher`,
`crossbeam-channel`, `parking_lot`, `etcetera`, `toml`, `encoding_rs_io`, `table_formatter`, `term_size`, and
`clap-cargo`, plus `tera` at build time.

Before landing:

1. Measure the change in wheel size and clean-build time.
2. Regenerate the workspace-hack manifest.
3. Confirm that only blob-based APIs are used: `LanguageType::from_file_extension` plus `parse_from_slice`, with
   shebang detection done by SASE's own `source_language.rs`. Tokei's path helpers read the filesystem.
4. Set Tokei `Config` explicitly, never from a user's ambient `tokei.toml`, and record the choice in the policy
   version.

**If the cost is rejected:** ship physical and non-blank lines, labeled as such, which is what grk proposed. The JSON
and the renderers don't change shape; only the `code` unit's definition changes, and a schema policy bump records it.

### 7.3 Repo-inventory prerequisites (phase 0)

- **Fix `sase-1lk`.** Each project's linked repos must resolve from that project's own config, never merged with the
  cwd project's config. Otherwise an all-projects run from inside sase attributes sase-core to bob-cli.
- **Add linked-repo provenance** (`project` vs `user`) to `RepoRecord`, so `chezmoi` can be put in "not counted"
  without a name heuristic. Today both report `source: "repos.linked config"`. This is the missing layer that
  `sase-1l2` describes.
- **Resolve names with the alias-aware resolver** (the `sase-zo` class of bug).

### 7.4 Clone and ref selection

1. **Pick the clone.** Prefer the inventory's canonical clone (workspace 0, the canonical linked checkout, or the hidden
   sidecar store). Otherwise use any registered clone in deterministic workspace order. Validate its identity: `git
   rev-parse --show-toplevel` must equal the candidate path, so a missing nested path can't discover an ancestor repo.
2. **Pick the ref.** Use the remote default branch (`origin/HEAD` symbolic ref, else the provider's default branch).
   If there is no remote, use the local `HEAD`, labeled `local`. Resolve to a full commit once and use it for both
   history and snapshot.
3. **Pinned linked repos.** Measure the mainline, and report the pin commit and how far behind it is.

### 7.5 Performance (measured, sase primary on apollo)

| Work | Cost | Plan |
| --- | --- | --- |
| History with bodies | 0.21 s | Stream it. Don't use `run_git_unchecked`'s byte cap, because the log is already 7.7 MB. |
| Blob stream | 2.2 s for all 306 MB | Use `cat-file --batch-check` sizes and known-binary extensions to skip most goldens, which cuts this sharply. |
| Parse | about 0.5 s on 8 threads | Bounded worker pool, without nested unbounded pools. |
| Records tier | 0.23 s `ls-tree` for 129k files | No content reads. |
| Churn (deferred) | about 90 s cold | Phase 2, opt-in, cached per commit. |

**Targets:** under 5 s cold for the whole sase project, and under 10 s for all three enabled projects. No durable cache
in v1; add a blob-OID cache (`~/.sase/cache/project_stats.sqlite`, registered with `sase disk`) only when a TUI panel
needs it.

### 7.6 Tests

**Rust,** over hermetic temporary git repos (setting `user.name`/`user.email` per test):

- both footer spellings;
- a body line containing `SASE_AGENT=`, which must **not** count;
- repeated tags;
- merges;
- a shallow clone;
- an empty repo and a zero-code repo;
- CRLF line endings and a final unterminated line;
- binary and LFS blobs;
- `.gitattributes` overrides;
- a gitlink and a symlink;
- the invariants: role partitions sum to included files, tests ⊆ code, numerator ≤ denominator.

**Python:**

- golden outputs for all four formats, with fixed width, no color, and a frozen clock;
- a cross-format agreement test (table, Markdown, and CSV numbers equal the JSON);
- resolver tests: cwd inside another project, display name vs key, a disabled project named explicitly;
- the exit-code matrix.

**Verification:** `just check` through the prescribed `sase tool run` path, not `check-full`.

## 8. Reliability checklist

| Case | Behavior |
| --- | --- |
| Linked repo not cloned anywhere (today: `sase-nvim`) | A dim `not cloned` row, excluded from totals ("6 of 7"), plus an `issues[]` entry. Exit 0. |
| Not cloned in this workspace but cloned elsewhere | Measure the registered clone. Because the snapshot is a committed ref, the result is the same as any clone with the same ref. |
| Stale refs / offline | Use local refs, print their age, and suggest `-F`. With `-F`, a fetch failure falls back to local refs plus an issue. |
| Shallow clone | Commits shown as `≥ N`, first commit unknown, `shallow: true`, plus an issue. |
| Empty repo / zero-code repo (`job`) | Valid zero or `·` cells. No division by zero. The card leads with docs. |
| Repo shared by two projects | Shown under both, counted once in the portfolio total. The key is the canonical remote, else the root commit, else realpath. |
| Inherited `GIT_DIR`/`GIT_WORK_TREE`/index env | Cleared for every target-repo git call. Read-only with `--no-optional-locks`. |
| Partial or promisor clones | Never trigger a lazy fetch. The local Git 2.43 rejects `--no-lazy-fetch` (cdx), so refuse content reads when no-fetch can't be guaranteed, and report it as partial. |
| Untrusted names | Escaped for terminal and Markdown; exact in JSON and quoted CSV. Raw commit messages and emails are never exported. |
| Determinism | Same refs and same policy give byte-identical JSON apart from `measured_at`. Results don't depend on caller cwd or file traversal order (property tests). |

## 9. Launch post: how to use it, and a stopgap

**On publish day:**

1. Run `sase project stats sase -F -f markdown` and `-j`.
2. Archive the JSON next to the post in the research sidecar, registered as an artifact.
3. Quote only a few scoped figures.

The command supplies facts; the post supplies the interpretation and the "Motion isn't progress" undercut.

**State the scope in the strip.** Say "16,186 commits in sase itself" or "18.3k across its six code repos", never a
number that silently includes sidecars.

**Corrections for the current drafts:**

- **Agent share.** "Since July, 19 of every 20 commits" is right (95.6%). But the stronger and still accurate claim is
  **"since June, 95%"**, or **"99% over the last month"**.
- **Total agent-signed count.** Any all-time count must include the legacy `AGENT=` spelling: **8,598**, not 6,349 or
  6,778.
- **Signing start date.** Signing began **2026-05-24**, not 2026-06-27.
- **"Lines of Python, more than half tests."** This holds under both units. In code lines it is 1.34M tests vs 1.20M
  source; in physical lines it is 1.60M vs 1.39M.

**Stopgap one-liners** (primary repo only; run after `git fetch` in any sase checkout). They reproduce the phase-1
definitions closely, but `--grep` can also match body lines, which the footer parser would reject.

```bash
git rev-list --count origin/master                                                # commits: 16,186 today
git log origin/master -E --grep='^(SASE_)?AGENT=' --format=%H | wc -l             # agent-signed: 8,598
git log origin/master --since=2026-06-01 -E --grep='^(SASE_)?AGENT=' --format=%H | wc -l   # 8,227
git rev-list --count --since=2026-06-01 origin/master                             # 8,650 → 95.1%
git log --reverse --format=%as origin/master | head -1                            # first commit: 2026-02-14
git log --format=%as origin/master | sort -u | wc -l                              # active days: 239
```

## 10. Alternatives considered and rejected

| Alternative | Verdict |
| --- | --- |
| Wrap the tokei, scc, or cloc binary (with or without a fallback) | Rejected. It is an optional install, counts working trees, knows nothing about SASE, and a fallback means machine-dependent numbers. Keep it as an independent spot-check only. |
| A pure-Python engine | Rejected. It violates `rust-core-required`, reimplements comment syntax, and blocks a future TUI or gateway consumer. |
| A hand-rolled SLOC counter | Rejected as the default. Docstrings, nested comments, and mixed languages are error-prone. Physical and non-blank lines are the fallback if tokei's weight is refused. |
| Default to the current project | Rejected. It contradicts the request and the `project list` semantics, and relies on fragile cwd inference. |
| Sum everything, sidecars included | Rejected. It makes the headline mostly sync traffic. |
| A top-level `sase stats` | Rejected. It is ambiguous with agent-run statistics. |
| GitHub-API metrics | Rejected for v1. They need network and credentials, are provider-coupled, and answer different questions. |
| A launch-only `just` recipe or script | Rejected as the end state. It is the drift this command exists to stop; §9 is only the bridge. |

## Recommended solution

Add **`sase project stats [PROJECT ...]`**: a read-only, Rust-backed **repo-truth report** that is reproducible by
construction, honest about coverage, and good to look at.

1. **Scope.** With no `PROJECT`, report every enabled project; `-D` adds disabled ones; explicit names (or aliases, or
   `+tags`) select those projects. Each project shows three tiers:
   - **code repos** (the primary plus project-declared linked repos), totaled with SHA-deduped commits and coverage
     ("6 of 7");
   - **records** (all sidecars), listed and never totaled;
   - **not counted** (externals and user-wide linked repos such as `chezmoi`), named only.
2. **Source of truth.** Measure the committed tip of each repo's default branch, read from its canonical clone. Work
   offline by default with `-F/--fetch` to opt in. Print ref provenance, and measure linked repos at mainline with pin
   lag reported.
3. **Phase-1 metrics.** The full contract is in §4.
   - History: commits, agent-signed count and share (both footer spellings, parsed by core), last-30-day commits and
     share, first and last commit, age, and active days.
   - Snapshot: code files and lines with test share, doc files and lines, agent-context files, top languages, and the
     latest tag.
   - Records tier: commits and files.
4. **Definitions live in sase-core.** They are printed in `-h`, footnoted in human output, and typed in a versioned
   JSON schema. Unknown values are `·`/`null`, never `0`.
5. **Formats:** `-f auto|table|markdown|json|csv` plus `-j`.
   - `auto` is the table on a TTY and Markdown when piped.
   - JSON is the complete wire.
   - CSV is one row per repo with no totals.
   - Markdown opens with the headline bullets and ends with the generating command.
6. **Beauty, with concrete rules:**
   - an accent-colored project card with sparklines and a linguist-colored language bar;
   - kind colors shared with `sase repo list`;
   - exact numbers in cells, friendly numbers in prose;
   - coverage and definitions footers;
   - responsive columns and an ASCII fallback.
7. **Architecture:**
   - **sase-core:** a `project_stats` module that runs git through the existing runner pattern over committed blobs,
     reuses `parse_commit_footer`, embeds the **tokei crate** (gated on a measured dependency-cost check), and runs
     repos in bounded parallel through one `project_stats_collect` binding.
   - **Python:** resolution, inventory, tiering, fetch, and renderers. No durable cache in v1. Targets: under 5 s cold
     for the sase project.
8. **Order of work:**
   - **Phase 0:** fix `sase-1lk`, add linked-repo provenance to the inventory, and use the alias-aware resolver.
   - **Phase 1:** everything above. It unblocks the launch post.
   - **Phase 2:** `-d` extras (churn, mailmapped authors, commit-origin mix, growth over time), `--since`/`--until`,
     the provider/model mix of agent-signed commits, an opt-in SASE-work section, and a blob-OID cache.
   - **Phase 3:** a Stats sub-tab in the TUI Projects pane and a gateway route on the same wire.

   If phase 1 misses publish day, use the §9 one-liners with the corrected agent-signing figures.
