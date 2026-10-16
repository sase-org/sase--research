# `sase project stats`: Research and Recommended Design (`__mus`)

Researcher: mus. Date: 2026-10-16.

Request: add `sase project stats <project_name>` (name optional; all projects when
omitted) reporting per-repo stats — commit counts, code/doc line and file counts,
project age — in human/agent/script-friendly formats, motivated by the numbers for
sase's launch post.

## Bottom line

Yes, build it — but narrower than asked, with documented definitions, and with one
stat the request does not name: the **agent-authored commit share**. Everything else
below justifies that sentence. Recommended shape:

```text
sase project stats [PROJECT] [-j|--json] [-m|--markdown] [-t N|--top N] [--no-color]
```

- No positional = all enabled projects. One positional = that project (name, alias,
  `+tag`, or directory key — the same resolution `sase project show` accepts).
- Human default: rich panels in the established `sase artifact stats` style, one
  section per repo plus a project TOTAL, plus a cross-project grand total when more
  than one project is reported.
- `-j/--json`: one stable-schema envelope for scripts and agents.
- `-m/--markdown`: GitHub-flavored tables for pasting into the launch post and docs.
- No CSV, no YAML, no Prometheus. Justification in Formats below.

## Context that constrains the design

These are observed facts from this workspace (sase_16), not assumptions.

- **The launch post needs re-derivable numbers, and says so.** The outline's gate
  list ends with "re-derive every number on publish day," and its corrections
  section catches a peer report citing stale figures (11,000+ commits vs 15,755 from
  `git rev-list` at the time; six providers vs seven in the README). Any stats
  command whose definitions are not pinned and printed will produce exactly this
  class of embarrassment. Definitions must live in `--help` and stay stable.
- **The outline warns against leaning on activity metrics.** It resolves the
  stats question as "one caveated strip in the opening" and quotes the opening's
  own hedge, *"Motion isn't progress."* So the command is worth building as
  infrastructure, but its output should not oversell commits/lines as achievement.
  I recommend a `--help` epilog line and docs note saying what the numbers do and
  do not mean.
- **In-repo precedent exists: `sase artifact stats`.** Human output is rich boxed
  panels with grouped tables; `-j/--json` emits one envelope; `-p PROJECT`
  filters; `-t N/--top N` caps groups. `sase project stats` should copy this
  contract outright — users already know it, and agents can reuse parsing code.
- **Repo inventory per project already exists.** `sase repo list --json
  [--project P | --all]` returns every repo with `kind` (primary/sidecar/linked/
  external), `path`, and `exists`. The stats command should consume that same
  inventory layer, not reinvent discovery. Two wrinkles found while probing:
  (1) several linked/external repos report `exists: false` (never cloned in this
  workspace) — stats must render those as explicit "not cloned" rows, not errors,
  and still exit 0; (2) `sase repo list -p bob-cli` failed here with "no
  WORKSPACE_DIR," while `--all` worked — the implementer must resolve the target
  project through the lifecycle record (`get_project_record`, which already
  handles aliases and `+tag` stripping) and then query inventory for it, with a
  regression test for a project that has no local checkout.
- **Line counting: tokei is available but not a dependency.** `tokei` (cargo
  install) exists on this machine and respects `.gitignore` — verified: 0 of
  13,100 counted files came from `.venv/`, against 14,369 `git ls-files` entries.
  But it is not in `pyproject.toml`, and sase cannot assume every machine has it
  (notably the mac/Tailnet machines). Design for **tokei-preferred, git-fallback**:
  shell to `tokei --output json` when present; otherwise count lines over
  `git ls-files` with a small built-in classifier. Never count the working tree
  blindly — untracked build artifacts and venvs are the classic way to report
  "2.5M lines of Python" that are really pip packages.
- **Real magnitudes (sase primary, HEAD, 2026-10-16):** 16,181 commits (was
  15,755 nine days earlier — ~47/day; another reason numbers must be
  re-derivable); first commit 2026-02-14, HEAD date 2026-10-16 (~8 months
  active); 14,369 tracked files; ~13.1k text files counted by tokei. Five
  committers, effectively one human. A full `tokei` pass took well under the
  probe timeout even at this size, so live computation with no cache is fine;
  document "no network, no cache, reads local clones only."
- **CLI conventions that bind this design** (`cli_rules.md`, read 2026-10-16):
  keep subcommands/options sorted; every public long option gets a short alias;
  prefer beautiful colored output. And the `project` group bare-invocation
  defaults to `list` — `stats` must be an explicit subcommand, which it is.

## Critique of the plan

**Is it a good idea?** Yes, with the scope adjustments below. The launch-post
motivation is real (stale numbers already bit once), the per-repo split matches
how sase projects are actually structured (primary + sidecars + linked), and the
command generalizes beyond the post (status reports, grant/progress updates,
"what's running"-style introspection). Three concerns:

1. **Vanity-metric gravity.** Commit/line counts invite Goodhart behavior and
   skeptical HN readers. Mitigation: include the honesty-adjacent stats the
   outline wants anyway (agent share, contributor count) and keep the caveat in
   help/docs. Do not add velocity leaderboards, per-author rankings, or
   "productivity" framing — that would actively harm the launch post's
   credibility.
2. **"All projects when omitted" is the dangerous default.** Across `sase`,
   `bob-cli`, and `job`, with ~22 known repos (several uncloned), a bare
   invocation fans out over many git operations. It is still the requested
   behavior and it is fine — but it must degrade gracefully per repo (uncloned,
   non-git, permission-denied each render as a row, never abort the run), and
   `--json` must include per-repo `status: ok|not-cloned|error` so scripts can
   distinguish "0 commits" from "could not read."
3. **Do not boil the ocean on metrics.** The request says "include, but not be
   limited to" and "think hard about what stats would be genuinely useful."
   Genuinely-useful discipline means: every stat must have (a) a one-line
   definition, (b) a launch-post or operator use, and (c) a cheap computation.
   Anything failing that test (test coverage, churn, bus factor, per-file
   hotspots) is a follow-up, not v1. I list the cuts explicitly below.

## Recommended stat set (v1)

Per repo (rows), plus per-project TOTAL and optional grand total:

**Activity (git, cheap: `rev-list --count`, `log` dates, `shortlog -sne`).**

| Stat | Definition | Why |
|---|---|---|
| commits | `git rev-list --count HEAD` | The launch-post number |
| first commit / last commit | min/max author date on HEAD history | Bounds "active since" claims |
| active span | calendar days first→last (display "8 months, 2 days" style, exact dates in JSON) | "length of time active," humanized |
| contributors | distinct author identities on HEAD history | Honesty stat; sase ≈ 1 human + bots |
| agent share | % of commits with a `SASE_AGENT=` trailer | **The number the post actually wants** — observed 6,349 trailer commits in the outline era; proves "built with agents" instead of asserting it |
| commit histogram | commits per month, last 12 months, ASCII bars in human output; array in JSON | Beautiful, cheap (`git log --format=%ad --date=short`), shows life better than totals |

**Size snapshot (tokei when present, `git ls-files` fallback).**

| Stat | Definition | Why |
|---|---|---|
| code files / code lines | tokei languages minus the doc group | The requested split |
| doc files / doc lines | Markdown + plain-text + RST (+ `docs/` tree counted either way — definition pins this) | The requested split |
| top languages | top N by code lines (`-t/--top`, default 10, mirroring `artifact stats`) | Answers "what is it written in" |
| total files | `git ls-files \| wc -l` | Reproducible anchor; differs from tokei file count, and the help text should say why (tokei skips binary/unknown) |

**Classifications to pin in `--help` (my adjustments to the requirements):**

- **Code vs docs:** docs = Markdown, plain text, RST, AsciiDoc, plus anything
  under a top-level `docs/` directory regardless of suffix; everything else
  tokei recognizes is code. JSON/YAML/TOML are *data*, reported inside code
  totals but broken out in the language table so nobody mistakes 60k lines of
  `uv.lock`-adjacent JSON for written code. This is adjustment #1: raw
  code/doc totals without the data caveat will mislead.
- **Generated/vendored exclusion:** respect `.gitignore` always; additionally
  exclude nothing by default but add `--include-generated` semantics only if
  asked — no, simpler: document that checked-in generated files (lockfiles,
  snapshots under `tests/`, `demos/`) *are* counted, because exclusion lists
  rot. Adjustment #2: transparency over cleverness; the Markdown language row
  lets readers sanity-check.
- **Which repos:** primary + sidecars + linked for the targeted project(s);
  externals excluded by default with `--include-external` opt-in (they are not
  the project's work; counting someone else's repo inflates totals).
  Adjustment #3.
- **Which clone:** when several workspace clones exist (sase had ~20 here),
  use the inventory's canonical path for the current workspace context and say
  which path was measured in the output. Never sum across clones.
  Adjustment #4.

**Explicitly out of v1:** per-author tables, churn/insertion-deletion totals
(expensive, gameable), coverage, bead/patch counts (different domain; `sase
artifact stats` and bead commands own those — link, don't duplicate), age of
sidecar repos that never had git history (render `n/a`, not epoch 0).

## Formats

Three formats, each with a named audience. This is adjustment #5 (the request
says "various formats" without naming them; fewer, well-chosen beats many).

| Format | Invocation | Audience | Shape |
|---|---|---|---|
| human | `sase project stats [PROJECT]` (default) | terminal users | Rich panels à la `artifact stats`: header panel (project, measured-at timestamp, tokei-or-fallback note, paths measured), one table panel per project with a row per repo + TOTAL, monthly histogram, grand total when >1 project. Color via rich; `--no-color`/`NO_COLOR` respected |
| JSON | `-j/--json` | scripts, agents | One envelope: `{"schema_version":1,"measured_at":…,"counter":"tokei\|fallback","projects":[{…repos:[{name,kind,path,status,commits,first_commit,last_commit,active_days,contributors,agent_share,files,code_lines,doc_lines,top_languages,histogram}]…totals}]}`. Sorted keys, stable field order, `status` per repo. Agents should default to this |
| markdown | `-m/--markdown` | launch post, docs, chat paste | GitHub tables: one per project (repo × key stats) + totals; numbers identical to JSON for the same tree. This is the "copy into the post" path and kills the stale-figure failure mode |

Why not CSV/YAML/Prometheus: CSV cannot hold the nested language/histogram
data without flattening tricks; YAML adds a second machine format with no new
audience (agents parse JSON fine); metrics exposition is a different feature
(scrape endpoint) with no requester. Say no once, in the docs.

## Reliability and edge cases

- Read-only. No network, no clone, no fetch, no writes, no cache to invalidate.
  Safe inside agents and monitors.
- Every repo failure is a row, not an abort: `not-cloned`, `not-a-git-repo`,
  `no-HEAD` (empty repo), `tokei-missing→fallback` (not a failure; note the
  counter in output), `permission-denied`. Exit 0 with partial results unless
  the *project itself* does not resolve (exit 1, stderr, mirroring `show`).
- Determinism: measure the checked-in tree (`git ls-files` + `HEAD`), not the
  dirty working tree, and print the measured commit SHA per repo in JSON
  (short SHA in human detail). Two runs on the same SHAs give the same numbers.
- Performance: `rev-list --count`, one `log --format=%ad`, one `shortlog`,
  one `tokei` per repo — all linear-or-better and subprocess-cheap. No
  parallelism in v1 (repos are few; keep it debuggable). Note in help that bare
  `sase project stats` over many projects takes seconds, not milliseconds.
- Rust boundary: per `rust_core_backend_boundary`, shared backend logic belongs
  in `sase-core` if other frontends need it to match. Repo stats are
  presentational/CLI-local in v1 (no TUI surface, no web app needs identical
  numbers), so implement in Python behind a thin module (e.g.
  `src/sase/main/project_handler_stats.py`) and promote to `sase-core` only
  when a second consumer appears. State that decision in the plan so nobody
  re-litigates it mid-review.

## Beauty notes (the request asks for beautiful)

- Copy the `artifact stats` panel grammar exactly (boxed title panels, GROUP
  tables, humanized byte/day units) so the two commands feel like one tool.
  Reuse its render helpers rather than inventing a new aesthetic.
- Right-align all numbers, humanize large ones (16,181 not 16181), humanize
  spans ("8 months" with exact dates alongside).
- The monthly histogram is the visual centerpiece — twelve labeled bars beat
  any paragraph. Cap bar width to terminal; full data in JSON.
- Project accent colors already exist in lifecycle records (`accent` field,
  used by `project current`) — use them for panel titles. Free beauty, already
  on-brand.

## Suggested implementation sketch (for the implementer)

1. Parser: `stats` subcommand in `src/sase/main/parser_project.py`
   (alphabetical placement; update the `metavar` lists in both the parser and
   `project_handler.py`'s usage string), with `project` as `nargs="?"`,
   `-j/--json`, `-m/--markdown` (mutually exclusive), `-t/--top` (default 10),
   `--include-external`, `--no-color`.
2. Handler: new `src/sase/main/project_handler_stats.py` (lazy-import from
   `project_handler.py` like `handle_add`), reusing `get_project_record` /
   `list_projects_for_state_filter` for resolution and the `sase repo`
   inventory layer for repo enumeration.
3. Collector: small git module (`rev-list --count`, `log --format=%ad
   --date=short`, trailer grep for `SASE_AGENT=`, `ls-files`) + tokei JSON
   when on PATH, else built-in fallback counter over `git ls-files`.
4. Renderers: rich panels (human), `json.dumps(sort_keys=True)` (JSON),
   GFM tables (markdown). All three render from one collected envelope —
   test that human/markdown numbers equal JSON numbers for a fixture repo.
5. Tests: `tests/test_project_stats.py` — fixture git repo with known commits
   (including trailer and bot commits), uncloned-repo row, `--json` schema
   snapshot, counter-fallback path (hide tokei from PATH), unknown-project
   exit 1. Follow `lint_and_test.md` before finishing (implementer: read it;
   I changed no tracked files in this turn).
6. Docs: one reference page + `--help` epilog carrying the definitions
   (implementer: read `docs_writing.md` first). Docs should state the
   "Motion isn't progress" caveat in one sentence.
7. Effort: small-medium. Roughly: collector ~200 lines, renderers ~200,
   parser ~40, tests ~200. No migrations, no new dependencies (rich already
   present), no TUI changes.

## Adjustments summary (called out as requested)

1. Split "data" (JSON/YAML/TOML/lockfiles) visibly inside code totals.
2. Count checked-in generated files transparently instead of maintaining an
   exclusion list.
3. Exclude external repos by default (`--include-external` opt-in).
4. Measure one canonical clone per repo and print which path was measured.
5. Three formats (human/JSON/markdown), explicitly rejecting CSV/YAML/metrics.
6. Added stats the request did not name: agent-share %, contributors, monthly
   histogram, measured-at timestamp + commit SHAs, per-repo status.
7. Added honesty framing: help/docs caveat that activity ≠ progress, per the
   launch outline's own warning.
8. Python-side implementation with a named deferral of the Rust-core question.

## Recommendation

Approve `sase project stats` with the v1 above. It directly serves the launch
post (re-derivable, paste-ready markdown, agent-share as the signature number),
reuses two established contracts (`artifact stats` output grammar, `repo list`
inventory), adds no dependencies, and stays read-only and offline. Keep the
metric set closed until the post ships; revisit coverage/churn/beads only with
a second requester.
