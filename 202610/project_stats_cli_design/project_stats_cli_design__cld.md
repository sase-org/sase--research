# `sase project stats`: Design Research and Recommendation

> **Research query:** Design a new `sase project stats [<project_name>]` command that reports useful statistics
> about one SASE project, or about every project when no name is given. It should cover commit counts, line counts
> and file counts for code and docs, and how long the project has been active, separated by repo for every repo linked
> to the project. It should support output formats for humans, agents, and scripts. Critique the plan, call out any
> requirement adjustments, and end with a recommended solution. Context: the numbers will feed sase's launch post.

**Researcher:** cld · **Date:** 2026-10-16 · **Measured at:** sase `origin/master` `881f444778`

## Bottom line

1. **Build it. The case is stronger than "the launch post needs numbers."** Three rounds of launch research already
   produced conflicting figures: 15,755 vs 15,756 commits, 6,349 vs 6,367 "`SASE_AGENT=`" commits, and 2.74M vs 2.3M
   "lines of Python". Each count was a correct answer to a slightly different question. A command whose definitions
   live in one place, sase-core, ends that drift for the post and for every later "how big is this?" question.

2. **The published agent-signing numbers are wrong, and only a footer-aware counter gets them right.** The launch
   research says the `SASE_AGENT=` trailer "began on 2026-06-27". That date is when the footer gained its `SASE_`
   prefix (`d6711811f2`). Agents had been signing commits with a bare `AGENT=` tag since 2026-05-24. Counting both
   spellings gives **8,593** agent-signed sase commits, not 6,792. git's own `%(trailers)` parser finds **zero**,
   because SASE's footer uses `KEY=value` and is followed by a link-definition paragraph. Since June, **95.1%** of sase
   commits are agent-signed (8,222 of 8,645). That is a better claim than the post's current "since July".

3. **The biggest design risk is deciding what counts as "the project's repos."** The sase sidecars hold about 43,000
   commits that machines made (beads alone has 23,378). A naive sum would more than triple sase's 18,327 code commits,
   and the "commits" headline would mostly measure bead-sync traffic. I recommend three tiers:
   - **Code repos** (the primary plus linked repos that the project itself declares) are summed into project totals.
   - **Record repos** (sidecars) get their own section and are never summed.
   - **Not counted:** external repos, and linked repos that every project inherits from the user-wide config, such as
     `chezmoi`.

4. **Measure the committed tree at each repo's remote default branch, not a working tree.** tokei over the primary
   checkout counts 12,372 Python files, but git tracks 12,283. The canonical `sase-listen` checkout is 4 commits
   behind `origin`. Pinning to a ref makes numbers reproducible, and it also enables an `--until DATE` as-of mode, the
   feature the launch post most needs ("re-derive every number on publish day").

5. **Formats:** `-f/--format auto|pretty|markdown|json|csv`, with `-j` as shorthand for json. `auto`, the default,
   prints the pretty Rich view on a terminal and **Markdown when stdout is not a TTY**. Agents run commands through
   pipes, so they get compact, self-describing Markdown, and `sase project stats sase > stats.md` produces something
   you can paste into the post. JSON is one versioned envelope for scripts, and CSV is one row per repo for
   spreadsheets.

6. **Put the engine in sase-core.** The `rust_core_backend_boundary` litmus test applies directly: the TUI Projects
   tab, the mobile gateway, and a future web view would all need the same numbers. The engine would be a Rust
   `project_stats` module that runs git through the existing runner, reuses `vcs_log` and `parse_commit_footer`,
   counts lines with the `tokei` crate on blob contents, and caches by blob OID and commit SHA in SQLite. Python keeps
   project and repo resolution, fetch, and the four renderers.

7. **Ship in phases, and don't let the post wait for phase 2.** Phase 1 covers the code tier: history, snapshot, the
   four formats, and `--until`. Phase 2 adds `-d/--detail`: churn, growth trend, authors, origin mix, sidecar record
   counts, and the provider/model mix of agent-signed commits. Phase 3 adds a TUI card. If phase 1 misses publish day,
   the corrected one-liners in [§12](#12-launch-day-stopgap) reproduce the phase-1 definitions.

8. **I found two repo-resolution bugs that an all-projects mode would trip over.** When run from inside the sase
   checkout, another project's linked-repo resolution silently merges sase's own `repos.linked` entries (filed as
   **`sase-1lk`**). And `sase repo list -p sase` still resolves directory keys only (I added a +1 to **`sase-zo`**).
   Phase 1 must not inherit either bug ([§11](#11-bugs-found-along-the-way)).

---

## 1. What the Launch Post Actually Needs

The recommended outline (`research:202610/sase_launch_post_outline/sase_launch_post_outline.md`) calls for a *"3–4-number
stats strip (commits, agent-attributed share, months), re-derived on publish day and undercut by 'Motion isn't
progress'"*. That strip is paid off later in §4 "What It Cost". The drafted introduction
(`research:202610/sase_launch_post_introduction/sase_launch_post_introduction__final.md`) uses four figures:

| Figure in the draft | Draft value | Problem a stats command fixes |
| --- | --- | --- |
| Commits | 15,756 (`git rev-list --count HEAD` in some workspace) | The value depends on which checkout you run it in and when that checkout last pulled. |
| Lines of Python, "more than half of it tests" | 2.74M physical lines; another report measured about 2.3M SLOC | Two definitions, both labeled "lines". |
| "Since July, 19 out of every 20 commits" are agent-signed | 6,143 of 6,446; 6,349 all-time | The July-onward share is right, because the legacy key was gone by then. The all-time count and the start date are wrong: counting only `SASE_AGENT=` misses 1,801 commits signed with the legacy `AGENT=` key, and signing began 2026-05-24, not 2026-06-27. Since **June**, the share is already 95.1%. |
| "A year ago" (`gai`, 2025-10-20) | — | The date lives in a different repo (dotfiles). It is out of scope for any repo-derived age, and that is fine. |

The post also wants an honesty section. The same command that reports motion can report **churn**: over sase's
history, 45 lines were deleted for every 100 written (5.58M added and 2.49M deleted, excluding images, JSON, lockfiles,
and JSONL). That number is as useful to the "What It Cost" section as the commit count is to the opening.

## 2. What I Measured (prototype, 2026-10-16)

The numbers below come from throwaway prototypes: `git log` and `ls-tree` plus tokei's per-file JSON, a path-based
role classifier, and footer regexes equivalent to core's parser. They are illustrative of the design, not the final
algorithm, and the mockups below use them.

### Code repos of the `sase` project

| Repo | Kind | Commits | Agent-signed | Last 30 days | First commit | Code files | Code lines | Tests | Docs files | Doc lines |
| --- | --- | --: | --: | --: | --- | --: | --: | --: | --: | --: |
| sase | primary | 16,181 | 8,593 (53%) | 1,850 | 2026-02-14 | 12,425 | 2,521,676 | 51% | 434 | 73,717 |
| sase-core | linked | 1,563 | 972 (62%) | 396 | 2026-04-28 | 1,290 | 536,490 | 22%¹ | 22 | 3,503 |
| sase-telegram | linked | 307 | 112 (36%) | 40 | 2026-02-28 | 94 | 33,698 | 53% | 7 | 1,255 |
| sase-listen | linked | 34 | 28 (82%) | 34 | 2026-10-01 | 104 | 22,070 | 34% | 30 | 1,633 |
| sase-github | linked | 174 | 71 (41%) | 26 | 2026-02-23 | 36 | 10,205 | 59% | 5 | 651 |
| sase-research-artifacts | linked | 68 | 63 (93%) | 31 | 2026-08-11 | 15 | 2,788 | 91% | 11 | 1,182 |
| sase-nvim | linked | *not cloned anywhere on this host* | | | | | | | | |
| **Total (6 of 7)** | | **18,327** | **9,839 (54%)** | **2,377** | 2026-02-14 | **13,964** | **3,126,927** | **46%** | **509** | **81,941** |

¹ Rust unit tests live inside `src/` (`#[cfg(test)]`), so a path classifier counts them as source. See
[§7](#7-definitions-the-contract).

- **Active days:** 239 of 245 calendar days have at least one commit across the code repos. Days are bucketed in local
  time and repos are unioned.
- **Monthly commits:** Feb 803 · Mar 1,796 · Apr 1,689 · May 3,689 · Jun 1,934 · Jul 2,528 · Aug 2,475 · Sep 2,490 ·
  Oct 923 (16 days).
- **Monthly agent-signed share:** 0% · 0% · 0% · 9% · 93% · 91% · 91% · 90% · 96%.
- **Languages (code lines):** Python 82%, Rust 17%, other 1%.
- **Agent context:** 185 files: memory notes, macros and skills, and `AGENTS.md`-style instruction files.
- **Other projects:**
  - `bob-cli` (primary only): 1,331 commits, 88% agent-signed, 369,231 code lines (Rust 97%), 36% tests.
  - `job`: 8 commits, **zero code files**, 1 doc, and 16 agent-context files. My prototype crashed on it with a
    divide-by-zero, which is a useful reminder that zero-code repos are a real case.

### Sidecars (record repos) of `sase`

| Sidecar | Commits | First commit | Tracked files | What the commits are |
| --- | --: | --- | --: | --- |
| beads | 23,378 | 2026-07-28 | 8,655 | 23,335 are `chore` sync commits |
| plans | 9,458 | 2026-07-11 | 7,750 | 3,169 `chore`, 625 "Link approved epic plan…" |
| agents | 8,335 | 2026-07-23 | 129,152 | 8,325 `chore`; 17,176 agent pages |
| research | 2,067 | 2026-07-11 | 5,272 | 1,225 `docs`, 791 `chore` |

### Timing (sase primary, apollo)

| Operation | Time | Implication |
| --- | --: | --- |
| `git log` with full bodies, 16,181 commits (7.7 MB) | 0.37 s | History is cheap. Stream it, don't byte-cap it. |
| tokei over the working tree | 0.63 s | Fast but counts the wrong file set. |
| Stream every blob at `origin/master` (`cat-file --batch`, 14,369 files) | 3.8 s | A cold ref-pinned snapshot is affordable. Cache by blob OID so warm runs skip it. |
| `git log --numstat` over all history (churn) | 91 s wall, 65 s CPU | Too slow for the default. Opt in, cache per commit, parallelize ranges. |
| Rust agent-run stats query (`agent_stats_query_runs`) | 0.47 s | Only **2,017 runs** on this host vs **7,715** distinct `AGENT` tags in git. The machine-local index can't be the source of all-time agent numbers; git footers can. |

## 3. Is This a Good Idea?

**Yes, with a narrow scope.**

**Why it earns a place in the CLI:**

- **Definitions drift without it.** Every hand derivation so far has answered a slightly different question (§1). A
  command bakes in one definition, prints it, and makes "re-derive on publish day" a single command.
- **Generic tools can't produce these numbers.** tokei, scc, cloc, and onefetch see one working tree at a time. None of
  them knows SASE's project registry, linked repos, sidecars, or commit footers. Two of the most interesting numbers,
  the agent-signed share and the commit-origin mix, exist only because of SASE's footer.
- **Agents need ground truth.** Agents writing release notes, READMEs, or blog drafts currently invent or re-derive
  numbers. A machine-readable, versioned answer is cheaper and more honest.
- **It demos well.** A beautiful stats card is a one-screenshot answer to "what is this project?" for the launch post
  and the README.

**What makes it risky:**

- **Vanity metrics.** Lines of code are a liability, not an asset, and commit counts reward motion. The outline's own
  *"motion isn't progress"* line says so. Mitigations:
  - Keep the metrics descriptive, not evaluative. No per-author leaderboards, no "productivity", and no COCOMO-style
    cost estimates. scc ships COCOMO and LOCOMO; both would be meaningless for an agent-built codebase.
  - Show counterweights next to the headline numbers: test share, and churn in detail mode.
- **Scope creep into a dashboard.** The agent-run side (providers, success rates, tokens) already lives in the TUI
  Statistics pane, which reads the machine-local agent index. Keep `project stats` **repo-truth only** for phase 1 and
  let the two surfaces complement each other.
- **Silent wrongness.** A repo that isn't cloned, a shallow clone, a fetch failure, or a misclassified directory can
  quietly produce a believable but wrong number. The design has to make coverage and definitions visible ([§9](#9-reliability-checklist)).

**Would I take a different approach?** Same command, same place in the CLI. `sase project stats` sits naturally next
to `sase bead stats`, `sase tool stats`, `sase artifact stats`, and `sase prompt stats`. But I would change the shape
of the requirements as listed next.

## 4. Requirement Adjustments (Called Out)

| # | As requested | Adjusted to | Why |
| --- | --- | --- | --- |
| **A1** | "Show numbers for all repos linked to the targeted project(s)" | Report **every** repo, in three tiers: **code** (primary and project-declared linked repos, which are totaled), **records** (sidecars, which get their own section and are never totaled), and **not counted** (external repos and user-wide linked repos such as `chezmoi`, which are listed by name only). | Sidecar commits are bookkeeping by machines and would swamp the totals (§2). `chezmoi` comes from `~/.config/sase/sase.yml` and appears in every project. External repos are ad-hoc `sase repo open` checkouts. |
| **A2** | "Commit counts" | Commits **plus the agent-signed count and share**, and the commit-origin mix (stitch / auto / manual) in detail mode. | This is the most distinctive SASE number, and the launch strip already asks for it. |
| **A3** | "Line and file counts for code files and docs" | Files are classified into roles: **source, tests, docs, agent context, config/data**. **Generated, vendored, and binary** files are reported as excluded rather than silently dropped. Code = source + tests, shown with the test share. | "Code vs docs" is too coarse: half of sase's code lines are tests. Memory notes, macros, and skills are neither code nor user docs, and for a SASE project they are worth showing. |
| **A4** | "Length of time the project has been active" | Three numbers: **age** (first commit to now), **active days** (days with commits, unioned across repos), and **last commit**. | "Active" is ambiguous. sase is 245 days old and active on 239 of them; each number tells a different story. |
| **A5** | No `<project_name>` means all projects | **Kept.** It matches `sase project list`, which works on the registry rather than the cwd. It means **enabled** projects, `-D` adds disabled ones, and multiple names are accepted. The all-projects view starts with a portfolio table, then gives per-project sections, and dedupes shared repos in the grand total. | Without dedupe, a repo linked from two projects is counted twice. |
| **A6** | (new) | **`-u/--until DATE`** for as-of snapshots, and **`-s/--since DATE`** to window history. | The launch post must re-derive its numbers on publish day, and month-over-month comparisons fall out for free. |
| **A7** | "Various formats" | `auto` (default), `pretty`, `markdown`, `json`, `csv`. `auto` switches to Markdown when stdout is not a TTY. | Detailed in [§6](#6-output-formats). |
| **A8** | (scope) | Phase 2 behind `-d/--detail`: churn, code growth over time, authors, origin mix, sidecar record counts, and the provider/model mix. | These cost more on a first run (churn takes 91 s cold) or depend on optional stores (the agents sidecar). |
| **A9** | (scope) | **Rejected:** COCOMO/LOCOMO cost estimates, complexity scores, bus factor, per-author rankings, GitHub stars/PR counts. | Evaluative, misleading for agent-written code, or a network/provider dependency. A PR count could come later through the `sase-github` plugin. |

## 5. Metric Catalog

**Default (phase 1).** Every metric below is per repo, plus a project total for code repos.

| Metric | Shown as | Source |
| --- | --- | --- |
| Commits | `18,327` | `git log <default-ref>` |
| Agent-signed commits / share | `54%`; card also shows the last-30-days share | core `parse_commit_footer` (`AGENT` tag, either spelling) |
| Commits in the last 30 days | `2,377` | same pass |
| First commit, last commit, age | `2026-02-14`, `21 min ago`, `8 months` | same pass |
| Active days | `239 of 245` | same pass, unioned per project in local time |
| Monthly commits and agent-share sparklines | `▂▄▄█▅▆▆▆▂`, `▁▁▁▁█████` | same pass |
| Code files and code lines (source + tests) | `13,964` / `3,126,927` | snapshot at the ref |
| Test share of code lines | `46%` | snapshot |
| Docs files and doc lines | `509` / `81,941` | snapshot |
| Agent-context files | `185` | snapshot |
| Languages (top 3 + other) | colored bar plus legend | snapshot |
| Latest release tag and commits since it | `v0.17.1 · Aug 29 · 2,612 commits since` | `for-each-ref refs/tags --merged <ref>`, `rev-list --count <tag>..<ref>` |
| Sidecar record repos | commits, first and last commit | `rev-list`, never totaled |

**Detail (`-d`, phase 2).**

- **Churn:** lines added and deleted, deletions per 100 lines written, and monthly net growth. Cached per commit.
- **Code lines over time:** monthly snapshots, cheap with the blob-OID cache.
- **Change since `--since`:** e.g. "+412,301 code lines since Sep 1".
- **Authors:** humans (mailmap-merged, `[bot]` excluded, as onefetch's `--no-bots` does) and bots.
- **Commit origins:** stitch / auto / manual, plus bead-linked and plan-linked commits.
- **Streaks:** the longest streak and the busiest day.
- **Sidecar record counts:** agent pages, plan docs, research reports, and beads (with status from the bead store).
- **Provider/model mix of agent-signed commits:** joins each `AGENT` tag to the agents-sidecar `meta.json`. The
  launch post would love "Claude x% · Codex y% · …".

**JSON-only** (no room in the human views): comment and blank lines, physical lines, bytes, merge commits,
per-language-per-role counts, ref SHAs, and fetch times.

## 6. Output Formats

### Format selection

```text
-f, --format {auto,csv,json,markdown,pretty}   (default: auto)
-j, --json                                     shorthand for --format json
-c, --color {auto,always,never}                (default: auto; honors NO_COLOR, FORCE_COLOR, TERM=dumb)
```

- **`auto`** resolves to `pretty` when stdout is a TTY and to `markdown` otherwise.
- **Precedent:** `gh` switches to tab-separated output when piped, and clig.dev recommends human-readable output on a
  TTY.
- **Why Markdown rather than colorless pretty output:** agents run commands through the Bash tool, which is not a TTY,
  and box-drawing tables waste their tokens. `> stats.md` gives a document you can paste. A script that greps still
  works.
- **Scripts should use `-j` or `-f csv` explicitly.** The help text states the `auto` rule.
- **stdout carries only the report.** Progress (fetch, first-run cache warm-up) goes to stderr, and only when stderr is
  a TTY. Warnings about unavailable repos are part of the report itself (a row in human formats, `issues[]` in JSON),
  not stderr noise.

### `pretty`: one project (≥100 columns)

The panel border, the title, and the sparklines use the project's accent from `project_accents.py`. The kind column
reuses the colors `sase repo list` uses for primary and linked repos. The languages bar uses linguist's language
colors. Unavailable rows are dim, and every number is right-aligned in tabular style.

```text
╭─ sase · +sase ────────────────────────────────────── as of 2026-10-16 16:00 EDT ─╮
│                                                                                  │
│   Started    Feb 14, 2026 · 8 months old · active 239 of 245 days                │
│   Commits    18,327 · 2,377 in the last 30 days · last commit 21 min ago         │
│   Agents     54% agent-signed · 95% in the last 30 days                          │
│   Code       3,126,927 lines in 13,964 files · 46% tests                         │
│   Docs       81,941 lines in 509 files · 185 agent-context files                 │
│   Release    v0.17.1 · Aug 29 · 2,612 commits since                              │
│                                                                                  │
│   Commits/month  ▂▄▄█▅▆▆▆▂   Agent share  ▁▁▁▁█████   (Feb → Oct)                │
│   Languages      █████████████████████████████████████████░░░░░░░░░              │
│                  Python 82% · Rust 17% · other 1%                                │
╰──────────────────────────────────────────────────────────────────────────────────╯

  CODE REPOS                       COMMITS  AGENT  30 DAYS  STARTED     CODE LINES  TESTS  DOCS
  sase                     primary  16,181    53%    1,850  2026-02-14   2,521,676    51%   434
  sase-core                linked    1,563    62%      396  2026-04-28     536,490   22%¹    22
  sase-telegram            linked      307    36%       40  2026-02-28      33,698    53%     7
  sase-listen              linked       34    82%       34  2026-10-01      22,070    34%    30
  sase-github              linked      174    41%       26  2026-02-23      10,205    59%     5
  sase-research-artifacts  linked       68    93%       31  2026-08-11       2,788    91%    11
  sase-nvim                linked        ·      ·        ·  not cloned on this machine (../sase-nvim)
  ───────────────────────────────────────────────────────────────────────────────────────────
  6 of 7 repos                      18,327    54%    2,377  2026-02-14   3,126,927    46%   509

  RECORDS  sidecars · never totaled   COMMITS  STARTED     LAST COMMIT
  beads                                23,378  2026-07-28  2 min ago
  plans                                 9,458  2026-07-11  1 h ago
  agents                                8,335  2026-07-23  4 min ago
  research                              2,067  2026-07-11  6 min ago

  ¹ Rust unit tests inside src/ count as source.   Not counted: chezmoi (user-wide linked repo)
  Commits: reachable from each default branch · Code lines: no blanks or comments · Agent: SASE AGENT footer
  More: sase project stats sase -d    Definitions: sase project stats -h
```

**Design rules for the pretty view:**

- **Exact numbers in tables, friendly numbers only in prose.** A reader may quote a table cell, so cells show
  `3,126,927`, not `3.1M`.
- **Never print `0` for something unknown.** Unknown is `·`, and the row says why.
- **The coverage line says what was counted.** The total row reads `6 of 7 repos`, and the footer lists what was not
  counted and why.
- **The footer defines every headline term.**
- **Responsive width.** At 80 columns, drop the `STARTED` and `DOCS` columns and wrap the card's languages legend. On
  a dumb or non-UTF-8 terminal, fall back to ASCII sparklines (`_.-=#`) and bars.

### `pretty`: all projects

```text
╭─ SASE projects · 3 enabled ─────────────────────────── as of 2026-10-16 16:00 EDT ─╮
│                                                                                    │
│   PROJECT   REPOS  COMMITS  AGENT  30 DAYS  STARTED     CODE LINES  TESTS  DOCS    │
│   sase      6/7     18,327    54%    2,377  2026-02-14   3,126,927    46%   509    │
│   bob-cli   3/3      1,331    88%      516  2026-06-01     369,231    36%   147    │
│   job       1/1          8    13%        8  2026-10-11           ·      ·     1    │
│   ──────────────────────────────────────────────────────────────────────────────   │
│   Total     10/11   19,666    56%    2,901  2026-02-14   3,496,158    45%   657    │
│                                                                                    │
╰────────────────────────────────────────────────────────────────────────────────────╯
  (then one section per project, as above; shared repos are counted once in Total)
```

*In this mockup, the `bob-cli` numbers are its primary repo only. The prototype did not measure its two linked repos.*

### `markdown`

GitHub-flavored, right-aligned numeric columns, and no HTML, so it renders the same on GitHub, in MkDocs, and in an
agent's context. It ends with the exact command and version that produced it, which keeps it reproducible.

```markdown
## sase

*As of 2026-10-16 16:00 EDT · each repo at its remote default branch · 6 of 7 code repos counted*

- **18,327 commits** since 2026-02-14 (8 months), active on 239 of 245 days
- **54% agent-signed** overall; 95% in the last 30 days
- **3,126,927 code lines** in 13,964 files; 46% tests
- **81,941 doc lines** in 509 files; 185 agent-context files
- **Languages:** Python 82%, Rust 17%, other 1%

| Repo | Kind | Commits | Agent-signed | Last 30 days | First commit | Code files | Code lines | Tests | Docs files | Doc lines |
| --- | --- | --: | --: | --: | --- | --: | --: | --: | --: | --: |
| sase | primary | 16,181 | 53% | 1,850 | 2026-02-14 | 12,425 | 2,521,676 | 51% | 434 | 73,717 |
| sase-core | linked | 1,563 | 62% | 396 | 2026-04-28 | 1,290 | 536,490 | 22% | 22 | 3,503 |
| … | | | | | | | | | | |
| sase-nvim | linked | — | — | — | — | — | — | — | — | — |
| **Total (6 of 7)** | | **18,327** | **54%** | **2,377** | 2026-02-14 | **13,964** | **3,126,927** | **46%** | **509** | **81,941** |

**Sidecar records (not totaled):** beads 23,378 commits · plans 9,458 · agents 8,335 · research 2,067.
**Unavailable:** `sase-nvim` (not cloned; expected at `../sase-nvim`). **Not counted:** `chezmoi` (user-wide linked repo).

*Definitions:*
- *Commits* are reachable from each repo's remote default branch.
- *Agent-signed* commits carry a SASE `AGENT` footer tag.
- *Code lines* exclude blank and comment lines.
- *Tests* is the test share of code lines.

Generated by `sase project stats sase -f markdown` (sase 0.17.1+2612.g881f44477, sase-core-rs 0.40.1).
```

### `json`

There is one envelope, and the Rust wire *is* the JSON (serde), so every frontend gets identical numbers. Rules:

- Integers for counts and floats in `[0, 1]` for shares.
- RFC 3339 timestamps.
- **`null` for unknown, never `0`.**
- No preformatted strings, and keys sorted.

```jsonc
{
  "schema": "sase.project_stats",
  "schema_version": 1,
  "generated_at": "2026-10-16T20:00:00Z",
  "versions": {"sase": "0.17.1+2612.g881f44477", "sase_core_rs": "0.40.1"},
  "query": {"projects": ["sase"], "since": null, "until": null, "detail": false, "fetch": "cached"},
  "projects": [{
    "key": "gh_sase-org__sase", "name": "sase", "tag": "+sase", "state": "enabled",
    "totals": {
      "repos": {"counted": 6, "configured": 7},
      "commits": 18327, "agent_signed_commits": 9839, "agent_signed_share": 0.537,
      "commits_last_30d": 2377, "agent_signed_last_30d": 2259,
      "first_commit_at": "2026-02-14T…", "last_commit_at": "2026-10-16T15:39:17-04:00",
      "age_days": 245, "active_days": 239,
      "code": {"files": 13964, "lines": 3126927, "test_lines": 1444902, "test_share": 0.462},
      "docs": {"files": 509, "lines": 81941},
      "agent_context": {"files": 185, "lines": 8963},
      "languages": [{"name": "Python", "code_lines": 2579463, "share": 0.825}, {"name": "Rust", "...": "..."}],
      "monthly": [{"month": "2026-02", "commits": 803, "agent_signed": 0}, {"...": "..."}]
    },
    "repos": [
      {
        "name": "sase", "kind": "primary", "tier": "code", "status": "ok",
        "path": "/home/bryan/projects/github/sase-org/sase", "remote_url": "git@github.com:sase-org/sase.git",
        "ref": {"name": "origin/master", "commit": "881f44477864…", "committed_at": "…", "fetched_at": "…", "shallow": false},
        "history": {"commits": 16181, "merge_commits": 103, "agent_signed_commits": 8593, "commits_last_30d": 1850,
                    "first_commit_at": "…", "last_commit_at": "…", "active_days": 239,
                    "latest_tag": {"name": "v0.17.1", "at": "2026-08-29T…", "commits_since": 2612}},
        "snapshot": {"tracked_files": 14369,
                     "roles": {"source": {"files": 6085, "code": 1226205, "comments": 19546, "blanks": 172121},
                               "tests": {"files": 6340, "code": 1295471, "comments": 14049, "blanks": 240916},
                               "docs": {"files": 434, "lines": 73717, "blanks": 18085},
                               "agent_context": {"files": 175, "lines": 8718},
                               "config": {"files": 52, "code": 12320},
                               "excluded": {"generated": {"files": 14}, "vendored": {"files": 0},
                                            "binary": {"files": 1269, "bytes": 194300000}}},
                     "languages": ["…"]}
      },
      {"name": "sase-nvim", "kind": "linked", "tier": "code", "status": "unavailable",
       "issue": "not_cloned", "history": null, "snapshot": null}
    ],
    "records": [{"name": "beads", "kind": "sidecar", "tier": "records", "status": "ok",
                 "history": {"commits": 23378, "first_commit_at": "2026-07-28T…", "last_commit_at": "…"}}],
    "not_counted": [{"name": "chezmoi", "reason": "user_linked"}]
  }],
  "totals": {"projects": 1, "repos": {"counted": 6, "configured": 7}, "commits": 18327, "...": "deduped across projects"},
  "issues": [{"project": "sase", "repo": "sase-nvim", "code": "not_cloned",
              "message": "linked repo is not cloned on this machine",
              "hint": "clone it next to the primary checkout at ../sase-nvim"}]
}
```

### `csv`

RFC 4180, one header row, and **one row per repo** (code and records, with a `tier` column). There are no total rows,
because a script summing a column must not double count. Empty cells mean unknown. Columns are append-only, so
existing scripts never break.

```text
project,repo,kind,tier,status,ref,commit,first_commit_at,last_commit_at,commits,agent_signed_commits,commits_last_30d,active_days,code_files,code_lines,test_lines,docs_files,docs_lines,agent_context_files,top_language
sase,sase,primary,code,ok,origin/master,881f444778,2026-02-14T…,2026-10-16T…,16181,8593,1850,239,12425,2521676,1295471,434,73717,175,Python
sase,sase-nvim,linked,code,unavailable,,,,,,,,,,,,,,,
sase,beads,sidecar,records,ok,origin/main,…,2026-07-28T…,…,23378,,,,,,,,,,
```

I considered and rejected two more formats:

- **TSV:** it's what `gh` uses when piped, but CSV is the spreadsheet lingua franca, and `cut -d,` works on these
  quote-free columns. It's trivial to add later.
- **An SVG or PNG "stats card":** beautiful for a README, but scope creep. A screenshot of the pretty view covers the
  post.

## 7. Definitions (the Contract)

These definitions live in sase-core, are printed in `-h`, are footnoted in every human format, and are described by
the JSON schema. Changing any of them is a breaking wire change.

| Term | Definition | Why this one |
| --- | --- | --- |
| **Ref** | Each repo's remote default branch (`origin/HEAD`, resolved by the VCS provider that `sase stitch list` uses). The fetch freshness cache is honored, and `-F` forces a fetch. If there is no remote, the local `HEAD` of the canonical checkout is used and labeled `local`. | Reproducible and workspace-independent. A stale or dirty checkout can't skew it. |
| **Commits** | All commits reachable from the ref, **merges included**, deduped by SHA across a project's repos. Merges are reported separately in JSON. | It matches the number GitHub shows on the repo page and `git rev-list --count`, so readers can verify it. |
| **Agent-signed** | The commit's SASE footer carries an `AGENT` tag, `SASE_AGENT=` or the legacy `AGENT=`. It is parsed by core `parse_commit_footer`, never by `%(trailers)`. | It is precise about what is known. "Agent-*written*" would overclaim before May and underclaim untagged agent work. |
| **Code lines** | Lines in source and test files that are neither blank nor comments (tokei `code`). | The industry convention (tokei, scc, cloc). Physical lines are in JSON. |
| **Doc lines** | Non-blank lines in docs files. Words are in detail mode. | Prose has no "code" lines. tokei counts Markdown as all comments, which is meaningless here. |
| **Roles** | Assigned in precedence order: (1) `.gitattributes` `linguist-generated`, `linguist-vendored`, and `linguist-documentation`, read via `git check-attr --source <ref>`; (2) project config globs (`project_stats.roles` in `sase/sase.yml`); (3) built-in heuristics: test dirs and test filename patterns, prose languages count as docs, `sase/memory/`, `sase/macros/`, skills, and `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/`QWEN.md`/`OPENCODE.md` count as agent context, data languages count as config, and lockfiles, minified files, golden files, and snapshot directories count as generated. Binary means LFS pointers or blobs with a NUL byte. | linguist's attributes are the portable standard. Config handles project quirks; for example, `sase-research-artifacts` ships its macros as Markdown. |
| **Active day** | A local-time calendar day with at least one commit in any code repo of the project. | Unioned per project, so working on two repos in one day counts once. |
| **Age** | From the project's earliest first commit (across code repos) to now, or to `--until`. | — |

**Known limitations to document:**

- Rust inline `#[cfg(test)]` modules count as source. sase-core's real test share is well above 22%. Phase 2 could
  add per-language test-region detection.
- Squash-merge workflows undercount commits relative to the work done.
- History older than a repo's first commit (such as `gai` in dotfiles) is out of scope.

## 8. CLI Surface

The parser follows `cli_rules`: options are sorted, every option has a short alias, and the help is excellent. The
positional's `dest` is `project`, so shell completion gets `ValueKind.PROJECT` for free (`completion/kinds.py:93`).

```text
usage: sase project stats [-h] [-c {auto,always,never}] [-d] [-D] [-f FORMAT] [-F | -N] [-j]
                          [-r NAME] [-s DATE] [-u DATE] [PROJECT ...]

Report repository statistics for SASE projects, per repo with project totals: history (commits,
agent-signed share, age, activity), code and docs size by file role, and languages. Code repos
(the primary and project-declared linked repos) are totaled. Sidecar repos are listed as records
and never totaled. With no PROJECT, every enabled project is reported.

positional arguments:
  PROJECT                 Project name, alias, directory key, or +tag (repeatable;
                          default: every enabled project)

options:
  -c, --color {auto,always,never}
                          Color output: auto, always, or never (default: auto)
  -d, --detail            Add churn, code growth, authors, commit origins, and sidecar record
                          counts (a first run on a large repo can take a minute; then cached)
  -D, --include-disabled  With no PROJECT, also report disabled projects
  -f, --format {auto,csv,json,markdown,pretty}
                          Output format (default: auto = pretty on a terminal, markdown otherwise)
  -F, --fetch             Fetch remotes now, bypassing the freshness cache
  -h, --help              show this help message and exit
  -j, --json              Shorthand for --format json
  -N, --no-fetch          Never touch the network; use existing remote-tracking refs
  -r, --repo NAME         Only report this repo (repeatable)
  -s, --since DATE        Only count history at or after DATE (default: all history)
  -u, --until DATE        Report as of DATE: history through DATE, code snapshot at the last
                          commit on or before DATE (default: now)

definitions:
  commits       commits reachable from each repo's remote default branch, merges included
  agent-signed  commits whose SASE footer has an AGENT tag (SASE_AGENT= or legacy AGENT=)
  code lines    non-blank, non-comment lines in source and test files
  tests         test share of code lines

DATE: Nh/Nd/Nw, today, yesterday, YYYY-MM-DD, or YYYY-MM-DDTHH:MM

examples:
  sase project stats
  sase project stats sase
  sase project stats +sase -f markdown > stats.md
  sase project stats sase -u 2026-10-20 -j | jq '.projects[0].totals.commits'
  sase project stats sase -r sase-core -d
  sase project stats sase -s 2026-09-01 -u 2026-09-30
```

**Behavior notes:**

- **Name resolution:** names resolve by key, display name, or alias, case-insensitively, after stripping `+`. Use the
  same resolver as `sase project show` or `project_display_names` (**not** `resolve_project_context`; see
  [§11](#11-bugs-found-along-the-way)). An unknown name exits 1 with "did you mean" suggestions.
- **Explicitly named projects:** naming a disabled project reports it.
- **`--since`/`--until`:** they reuse `sase.vcs_log.dates` (the `stitch list` grammar). With `--since`, the
  "30 days" column disappears and the card says "since …".
- **Exit codes:**
  - `0` on success, even when some repos are unavailable; they are reported, not fatal.
  - `1` when the project is unknown or *no* code repo of a requested project could be read.
  - `2` for usage errors.

  Scripts that need completeness check `issues[]`.
- **Command grouping:** `stats` joins the hard-coded subcommand `metavar` in `parser_project.py:74`. While there, fix
  `sase bead stats`'s help text, "Show project statistics", which will collide; rename it to "Show bead statistics".

## 9. Reliability Checklist

| Case | Behavior |
| --- | --- |
| Linked repo not cloned (today: `sase-nvim`) | A `not cloned` row with the expected path. Excluded from totals, shown as "6 of 7", and listed in `issues[]`. |
| Fetch fails or is offline | Use the existing remote-tracking ref. The as-of line shows its age ("refs from 3 h ago"), plus an issue. |
| No remote | Local `HEAD` of the canonical checkout, labeled `local`. |
| Shallow clone | `rev-parse --is-shallow-repository`. Commits are shown as `≥ N`, the first commit as unknown, plus an issue. |
| Zero-code repo (`job`) | Code cells are `·` and the test share is `·`, never a division by zero. The card leads with docs and agent context instead. |
| Repo shared by two projects | Shown under both projects and counted once in the portfolio total, keyed by canonical remote URL, else root commit, else realpath. |
| Same commits in two repos (history split or import) | Deduped by SHA inside a project. |
| cwd is inside a different project | Each project's config is loaded from its own primary checkout and never merged with the cwd project's config. **This requires fixing `sase-1lk`.** |
| Submodules, symlinks, LFS pointers | Gitlinks are skipped and counted in JSON. Symlinks are skipped. LFS pointers count as binary. |
| Huge histories | Stream `git log`. Don't use `run_git_unchecked`'s byte cap: sase's log with bodies is already 7.7 MB. Keep the per-call timeout. |
| Concurrent agents | Read-only git with `--no-optional-locks` and `GIT_OPTIONAL_LOCKS=0`, as the existing runner already sets. The SQLite cache uses WAL and is disposable. |
| Determinism | Same ref + same config ⇒ byte-identical JSON, except `generated_at`. Golden tests enforce this. |
| Time zones | Commit times are bucketed in the user's local zone, as the JSON documents. Monthly buckets use the same zone. |

## 10. Architecture

**The split.** The `rust_core_backend_boundary` litmus test says the computation belongs in core. Rendering and CLI
glue stay in Python.

```text
sase (Python)                                       sase-core (Rust)
─────────────                                       ────────────────
parser_project.py: `stats` subparser
project_handler_stats.py
  resolve projects (alias-aware, + stripped)
  resolve repos per project → tiers
    (own config only; project vs user-wide
     provenance; dedupe identities)
  fetch via vcs_log fetch_cache (unless -N)
  core.project_stats_facade ──── wire request ───▶ project_stats::collect(request)
                                                     ├ per repo, in parallel threads:
                                                     │   history: git log <ref> --format=…%B (streamed)
                                                     │            → vcs_log parse + commit_footer → AGENT, origin
                                                     │   snapshot: ls-tree -r -z -l <ref>
                                                     │            → check-attr --source <ref> (linguist-*)
                                                     │            → classify roles (config globs, heuristics)
                                                     │            → cat-file --batch for uncached blobs
                                                     │            → tokei LanguageType::parse_from_slice
                                                     ├ cache (SQLite, rusqlite): blob OID → counts;
                                                     │   (commit, classifier hash) → churn by role (detail)
                                                     └ aggregate: repo → project → portfolio
  render ◀──────────────── ProjectStatsWire ─────────
    pretty (Rich) · markdown · csv · json (= wire)
```

**Where the code goes:**

- **sase-core:**
  - A new `crates/sase_core/src/project_stats/` module. Its `mod.rs` is a facade, with `wire.rs`, `history.rs`,
    `snapshot.rs`, `classify.rs`, `cache.rs`, `aggregate.rs`, and `tests/`, each under 1,500 lines.
  - Binding `project_stats_collect` in a new `crates/sase_core_py/src/project_stats/` domain, modeled on the
    `memory_history` binding (a Rust-run git walk with `py.allow_threads`).
  - New dependency: the `tokei` crate (15.0.0, MIT OR Apache-2.0). Its `LanguageType::from_path` and
    `parse_from_slice` give language detection and code/comment/blank counts for in-memory blobs. Check its default
    features so the CLI-only dependencies stay out, and regenerate hakari. **Don't add `gix` or `git2`**: core
    already shells out to `git` in about 20 places, and consistency beats a second git stack.
- **sase:**
  - `src/sase/core/project_stats_facade.py` (`require_rust_binding("project_stats_collect")`).
  - `src/sase/project_stats/` (resolve, render_pretty, render_markdown, render_csv).
  - `src/sase/main/project_handler_stats.py` and the parser.
  - `project_stats:` defaults in `src/sase/default_config.yml`, per the gotchas memory.
  - The CLI reference page; read `docs_writing.md` first.
  - Move `sase-core-revision.txt` past the core commit.
- **Cache location:** `~/.sase/cache/project_stats.sqlite`. It is machine-local and safe to delete; register it as an
  owner with `sase disk` so it shows up in disk accounting.

**Performance budget (sase project, apollo):**

| Run | Target | Basis |
| --- | --- | --- |
| Default, warm cache | < 2 s | History is about 0.4 s per big repo. The snapshot is `ls-tree` plus cache lookups. Repos run in parallel. |
| Default, cold cache | < 8 s | Blob streaming takes 3.8 s for the largest repo, plus tokei parsing, in parallel. |
| `-d`, cold | < 30 s with progress on stderr | Churn takes 91 s single-threaded; split into commit ranges across cores. |
| `-d`, warm | < 3 s | Only new commits are diffed (about 70 per day). |

**Testing:**

- **Rust:** unit tests over hermetic temporary git repos covering both footer spellings, merges, a shallow clone,
  binary and LFS blobs, `.gitattributes` overrides, an empty repo, and a zero-code repo. Set `user.name` and
  `user.email` per test, as sase-core's AGENTS.md requires. Add a wire round-trip test.
- **Python:** golden outputs for all four formats with fixed width, no color, and a frozen clock. Add resolver tests
  for cwd-in-another-project and display-name-vs-key, and an exit-code matrix.

## 11. Bugs Found Along the Way

1. **`sase-1lk` (filed, bug, small): cwd config leaks into cross-project repo resolution.**
   - **Root cause:** `_resolution_config_cached()` (`src/sase/_linked_repo_config_state.py:39-48`) starts from
     `load_merged_config()`, whose last layer is the **cwd** project's `sase/sase.yml`. It then concatenates the
     target project's `repos.linked` on top.
   - **Repro:** run `sase repo list -p gh_bobs-org__bob-cli` from inside the sase checkout. It lists `sase-core`,
     `sase-github`, … resolved under `~/projects/github/bobs-org/` and marked missing. Run from `/tmp`, it lists only
     bob-cli's real linked repos.
   - **Why it matters:** an all-projects stats run from a sase workspace would hit this. Today the leaked entries are
     merely missing; once a same-named sibling path exists, they become silently wrong data.
2. **`sase-zo` (existing; I added +1 #10): display name vs directory key.** `sase repo open sase-core` now works, but
   `sase repo list -p sase` still fails: "Project 'sase' has no WORKSPACE_DIR in ~/.sase/projects/sase/sase.sase".
   - The `-p` flag resolves through `workspace_handler_context.resolve_project_context` → `get_project_file_path`,
     which accepts directory keys only.
   - A stale `~/.sase/projects/sase/` directory makes the display name hit the wrong ProjectSpec.
   - `project show` and `artifact stats -p` already use alias-aware resolvers.
3. **Noted, not filed:** `sase bead stats`'s help text says "Show project statistics" (fold the fix into phase 1).

## 12. Launch-Day Stopgap

If the post publishes before phase 1 lands, these one-liners reproduce the phase-1 definitions for the primary repo.
Run them after `git fetch` in any sase checkout:

```bash
git rev-list --count origin/master                                     # commits (matches GitHub)
git log origin/master -E --grep='^(SASE_)?AGENT=' --format=%H | wc -l  # agent-signed (8,593 today)
git log origin/master --since=2026-06-01 -E --grep='^(SASE_)?AGENT=' --format=%H | wc -l  # 8,222
git rev-list --count --since=2026-06-01 origin/master                 # 8,645  → 95.1% since June
git log --reverse --format=%as origin/master | head -1                 # first commit: 2026-02-14
```

Suggested strip wording, given today's numbers. The wording is yours; the facts are checkable:

- **18,327 commits** across sase's six code repos (16,181 in sase itself).
- **Since June, 95% of them** were signed by the agent that wrote them.
- **3.1M lines of code**, 46% of it tests (sase alone: 2.5M, 51% tests).
- **8 months**.

## 13. Alternatives Considered

| Alternative | Verdict |
| --- | --- |
| Wrap the `tokei` or `scc` binary | Rejected. Users don't have them, they count working trees, and they know nothing about projects, sidecars, or footers. |
| Pure-Python implementation | Rejected. It violates the core boundary (the TUI and gateway need the same numbers), reinvents tokei's comment-syntax tables for 200+ languages, and is slower. |
| Top-level `sase stats` | Rejected. It is ambiguous with agent-run statistics (the TUI Statistics pane). `project stats` names its subject. |
| Default to the *current* project (as `sase tool stats` and `sase repo list` do) | Not chosen. Within the `project` group, the bare form already means "all registered projects" (`project list`). The current project is one word away (`sase project stats +sase`). |
| Count everything, including sidecars, into one number | Rejected. 43k machine commits would turn the headline into bead-sync traffic. |
| Agent-run stats (providers, success rate) in this command | Deferred. The machine-local index covers 2,017 runs vs 7,715 signed agents in git. The durable route, joining footers to agents-sidecar metadata, is phase 2. |
| a `just` recipe or script for the launch only | Rejected as the end state. It is the drift we're trying to stop. §12 is the bridge. |

## 14. Recommended Solution

Add `sase project stats [PROJECT ...]` as a **repo-truth report**. It should be reproducible by construction, honest
about what it counted, and good to look at.

1. **Scope and tiers.**
   - Code repos are the primary plus linked repos declared in the project's own `sase/sase.yml`; they are totaled.
   - Sidecars are record repos: listed, never totaled.
   - External repos and user-wide linked repos (`chezmoi`) are named as not counted.
   - No argument means every enabled project. Show a portfolio table first, then per-project sections, with shared
     repos deduped in the grand total.
2. **Truth source.** Use each repo's remote default branch, with the `stitch list` fetch cache and `-F`/`-N`, at an
   optional `--until` instant. Read committed blobs, never working trees.
3. **Phase-1 metrics, per repo and per project:**
   - commits, agent-signed count and share (all-time and last 30 days), and last-30-day commits;
   - first and last commit, age, active days, and monthly sparklines;
   - code files and lines with test share, docs files and lines, and agent-context files;
   - top languages and latest release tag;
   - sidecar commit counts.
4. **Definitions in core**, as in §7: printed in `-h`, footnoted in human output, and typed in JSON. The `AGENT` footer
   is parsed by core, never by regex or `%(trailers)`.
5. **Formats:** `-f auto|pretty|markdown|json|csv` and `-j`. `auto` is pretty on a TTY and Markdown when piped. JSON
   is the versioned Rust wire, with `null` for unknown. CSV is one row per repo with no totals. Markdown is
   paste-ready and ends with the generating command.
6. **Beauty, with concrete rules:**
   - accent-colored project card, sparklines, and a linguist-colored language bar;
   - exact numbers in tables, friendly numbers in prose;
   - `·` for unknown, never `0`;
   - a coverage line ("6 of 7 repos") and a definitions footer;
   - responsive columns at 80 columns and an ASCII fallback.
7. **Architecture:**
   - **sase-core:** a `project_stats` module that runs git via the existing runner pattern, streams output, counts
     lines with the tokei crate, caches in SQLite by blob OID and commit, and runs repos in parallel. One binding,
     `project_stats_collect`.
   - **Python:** resolution, fetch, and rendering.
   - **Targets:** < 2 s warm and < 8 s cold for the sase project.
8. **Order of work.** Phase 0 fixes **`sase-1lk`** and **`sase-zo`**'s `-p` resolver. Phase 1 as above. Phase 2 adds
   `-d`: churn, growth, authors, origins, sidecar record counts, and provider/model mix. Phase 3 is a Projects-tab card
   and a gateway route on the same wire. Use the §12 one-liners if the post can't wait.

## Sources

**Repo and host (measured 2026-10-16 on apollo):**

- **Commands:**
  - `sase project list` / `show` / `show -j`
  - `sase repo list` (`-p`, `-a`, `-j`, from the workspace and from `/tmp`)
  - `sase stitch list -h` and `sase stitch list -a -f json`
  - `sase artifact stats`, `sase tool stats`, `sase bead stats`, `sase prompt stats -h`
  - `git log`, `rev-list`, `ls-tree`, `cat-file --batch`, `check-attr --source`, and `--numstat` across sase, the five
    reachable linked repos, four sidecars, and the `bob-cli` and `job` primaries
  - tokei 14.0.0 per-file JSON
  - `sase.stats.query.query_run_stats`
- **sase code:**
  - `src/sase/vcs_log/resolve.py`, `collect.py`, and `dates.py`
  - `src/sase/repo_inventory.py`
  - `src/sase/_linked_repo_config_state.py` and `config/core.py`
  - `src/sase/main/parser_project.py`, `project_handler*.py`, and `repo_handler_list.py`
  - `src/sase/project_accents.py`, `core/term_color.py`, `completion/kinds.py`, and `stats/query.py`
  - `workflows/commit/runtime_tags.py`
  - `sase/sase.yml` and `~/.config/sase/sase.yml`
- **sase-core (via `sase repo open`):**
  - `AGENTS.md` and `Cargo.toml`
  - `crates/sase_core/src/` modules `vcs_log/`, `commit_footer.rs`, `file_history/runner.rs`, `agent_stats/`, and
    `project_spec.rs`
  - `crates/sase_core_py/src/vcs/mod.rs` and `memory_history/mod.rs`
- **Memory:** `cli_rules.md`; glossary `sase-project`, `sase-repo`, and `current-project`; `sase_beads.md`;
  `sase_sizes.md`; core `rust_core_backend_boundary`.

**Prior research (via `sase artifact read`):**

- `research:202610/sase_launch_post_outline/sase_launch_post_outline.md`
- `research:202610/sase_launch_post_introduction/sase_launch_post_introduction__final.md`

**External:**

- **Repos (opened via `sase repo open`):**
  - `gh:o2sh/onefetch`: info fields in `src/data/fields/` (project, head, version, created, languages, dependencies,
    authors, last change, contributors, URL, commits, churn, lines of code, size, license), JSON/YAML output, and
    `--no-bots`.
  - `gh:boyter/scc`: README formats (`tabular, wide, json, json2, csv, csv-stream, cloc-yaml, html, html-table, sql,
    sql-insert, openmetrics`), COCOMO/LOCOMO, ULOC/DRYness, and `--no-gen`/`--no-min`.
  - `gh:github-linguist/linguist`: `docs/overrides.md` (`linguist-documentation`, `-generated`, `-vendored`, and
    `-detectable` excluded or included in stats; `linguist-language`).
- **Docs pages:**
  - [docs.rs: tokei `LanguageType`](https://docs.rs/tokei/latest/tokei/enum.LanguageType.html) and
    [`CodeStats`](https://docs.rs/tokei/latest/tokei/struct.CodeStats.html): v15.0.0, MIT OR Apache-2.0,
    `parse_from_slice`, `from_path`.
  - [clig.dev: Output](https://clig.dev/#output): human-first output, TTY detection, `--json`, `--plain`, `NO_COLOR`,
    and stdout vs stderr.
  - [GitHub Docs: customizing how changed files appear](https://docs.github.com/en/repositories/working-with-files/managing-files/customizing-how-changed-files-appear-on-github):
    `linguist-generated`.
- **Search results (secondary):**
  - [onefetch man page](https://www.mankier.com/1/onefetch)
  - [scc on pkg.go.dev](https://pkg.go.dev/github.com/boyter/scc)
