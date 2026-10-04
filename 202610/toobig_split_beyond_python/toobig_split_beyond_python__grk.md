# toobig_split beyond Python: line limits for Rust, JavaScript, and Swift

Research date: 2026-10-04. Researcher: `grk` (independent swarm member). Scope: whether
to run the existing `toobig_split` Axe job on non-`sase` projects, which line-count
trigger and split-target to use for Rust / JavaScript / Swift, and whether the plan
should change.

This report does not consult peer swarm drafts.

## Verdict

Do not turn on today's `toobig_split` job for other projects with the Python 700 / 500
limits. The *discipline* is worth exporting. The *job as currently wired* is a
Python-only ratchet that would either no-op (scanner defaults to `*.py`) or, if the
scanner were pointed at Rust/JS/Swift without other changes, launch a sequential
split-file swarm that the `#split_file` macro cannot execute safely.

Use per-project ratchets, language-specific split recipes, and a hard cap on how many
files a tick may propose. Treat 500–700 lines as a long-term *agent-edit target*, not
as the first trigger on trees whose p90 is already above 1,000.

## What the current system actually does

Three layers are easy to conflate.

| Layer | Where | Python numbers | Meaning |
| --- | --- | --- | --- |
| CI / `just toobig` | sase `Justfile` `_lint-toobig` | `1000 850 700` | Hard / warning / info. Only `> 1000` fails the build. |
| Chop trigger | athena `toobig_split` job + `bugyi_chop_toobig_split` | same triple; admission floor `min(limits)` = 700 | Any file `> 700` is proposed. `%if` rechecks `wc -l >= 700` before launch. |
| Split target | `#split_file` macro | "keep every resulting file at 500 lines of code or fewer" | Agent prompt, not a scanner threshold. |

Sources: sase `Justfile` (`toobig src 1000 850 700`),
`src/sase/macros/split_file.md`, chezmoi `sase_athena.yml` (`names: [sase]`,
`trees: [src, tests]`, `limits: ["1000", "850", "700"]`),
`bugyi-chops` `src/bugyi_chops/toobig_split.py`, `toobig` README and CLI.

The hysteresis is the point. sase Python is already sitting just under the trigger:

| Tree | Files | Median | p90 | p95 | p99 | Max | `>700` | `>850` | `>1000` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sase `src/` + `tests/` `*.py` | 11,348 | 202 | 481 | 562 | 669 | 913 | 5 | 2 | 0 |

700 is a few lines above p99. 500 is approximately p90. 1000 is above the current max.
The job is a *tail ratchet on a codebase that already internalized the rule*, not a
style guide being imposed for the first time.

`toobig` itself is language-agnostic (`--include` basename globs; default `*.py`). Its
README already shows a Rust example at `800 650 500`. The chop does **not** pass
`--include`, does not honor `.gitignore`, has no exclude flag, and always emits
`%auto #split_file:<path>`. That macro is Python-complete: import facades, no
cross-module `_private` imports, `just _lint-symvision`, `just _lint-mypy`,
`just _lint-toobig`.

## Candidate projects (inferred from the live inventory)

Enabled SASE projects today: `sase` (Python) and `bob-cli` (Rust). Other in-org trees
that match the languages named in the request:

| Project | Language | Role |
| --- | --- | --- |
| `sase-org/sase-core` | Rust | Linked SASE backend |
| `bobs-org/bob-cli` | Rust | Enabled SASE project |
| `bbugyi200/actstat` | Rust | Small CLI |
| `bobs-org/bob-plugins` | JavaScript | Obsidian plugins; numbered `src/` fragments concatenated into `main.js` |
| `bobs-org/bob-mac-capture` | Swift | Mac capture app |

`sase-android` (Kotlin) and `sase-nvim` (Lua) are the same class of problem if the job
grows further. They are out of scope for the numbers below.

## Measured distributions on those trees

Line counts are `wc -l` (newline bytes), matching `toobig`. Vendor / build directories
(`target`, `node_modules`, `.git`, …) skipped. Bytes-per-line medians are 31–38 across
all four languages, so raw line count is a fair token proxy here. The languages do
**not** need different limits because a Rust line is “worth more tokens.” They need
different limits because **modules naturally grow larger** and because **split
mechanics differ**.

### Rust

| Tree | Files | Median | p90 | p95 | Max | `>700` | `>1000` | `>2000` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sase-core `*.rs` src | 710 | 428 | 1,323 | 1,757 | 3,330 | 209 (29%) | 123 (17%) | 21 (3%) |
| sase-core `*.rs` tests | 216 | 354 | 1,022 | 1,284 | 2,322 | 52 (24%) | 23 (11%) | 2 |
| bob-cli `*.rs` src | 265 | 445 | 1,182 | 1,588 | 2,204 | 84 (32%) | 41 (16%) | 2 |
| bob-cli `*.rs` tests | 130 | 608 | 1,210 | 1,640 | 1,955 | 55 (42%) | 27 (21%) | 0 |
| actstat `*.rs` | 7 | 677 | 1,697 | 2,336 | 2,975 | 3 | 1 | 1 |

Largest sase-core file: `crates/sase_core/src/agent_scan/scanner.rs` at 3,330 lines,
with `#[cfg(test)]` starting at line 1,884 (~43% of the file). Several other 2k+ files
are 20–56% in-file tests. That is a cheaper first split than carving production types
apart.

A 700 trigger on sase-core src is 209 sequential `@medium` agents. The chop chains
them with `wait_on` and the job inhibits on clan prefix `toobig-`, so that backlog
would also stall sase Python splits for weeks.

Default chop `trees: [src, tests]` misses sase-core entirely (`crates/…/src`). bob-cli
and actstat do have top-level `src/`.

### JavaScript (`bob-plugins`)

Built `main.js` files are concatenations (up to 51,960 lines). Hand-authored fragments
under `plugins/*/src/` already have a ~1,000-line ceiling:

| Set | Files | Median | p90 | p95 | Max | `>700` | `>1000` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `plugins/*/src/*.js` fragments | 56 | 637 | 885 | 917 | 981 | 21 (38%) | 0 |
| built `main.js` | 6 | 9,499 | 36,231 | 44,095 | 51,960 | 5 | 5 |
| `scripts/test-*.cjs` | 39 | 756 | 2,691 | 5,149 | 19,813 | 22 | 13 |

`scripts/check-split-parity.mjs` exists specifically to keep fragments and the built
bundle in agreement. Pointing `toobig_split` at `plugins/` with `--include '*.js'`
would propose splitting *generated* `main.js`. That is a wrong action, not an
aggressive limit.

A 500-line *target* on fragments would hit 36 of 56 files (64%) and fight an existing
split convention that is already working.

### Swift (`bob-mac-capture`)

| Tree | Files | Median | p90 | p95 | Max | `>700` | `>1000` | `>2000` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `Sources/**/*.swift` | 66 | 127 | 838 | 1,309 | 5,081 | 9 (14%) | 6 (9%) | 3 |
| `Tests/**/*.swift` | 49 | 273 | 1,328 | 2,505 | 6,541 | 9 (18%) | 7 (14%) | 3 |

Median source file is *smaller* than sase Python. The problem is a fat tail of SwiftUI
views / `ObservableObject` models and matching XCTest files (`CapturePanelModel.swift`
5,081; its test file 6,541). `fileprivate` is rare (4 hits in 115 files); `private` is
common (920). Access control is not the main split blocker. View/state cohesion is.

Default chop trees `[src, tests]` miss `Sources/` and `Tests/`.

## What language communities actually recommend

These are **human style-guide defaults**, useful as a floor for *new* files and as a
sanity check. They are not calibrated to these repos, and they are not agent-edit
limits.

### JavaScript / TypeScript

ESLint `max-lines` ([docs](https://eslint.org/docs/latest/rules/max-lines)):

- Not recommended-on; default `max` is **300**.
- Docs: “Recommendations usually range from 100 to 500 lines.” Agreement that files
  should not be “in the thousands.”
- Optional `skipBlankLines` / `skipComments`. `toobig` counts every newline, including
  comments and blanks, matching SwiftLint’s default and sase’s current Python gate.

AI-oriented JS practice sometimes pushes lower (custom 200-line ESLint rules; Atticus
Li’s [200-line solo-AI rule](https://atticusli.com/blog/posts/the-200-line-limit-why-vibe-coding-solo-apps-needs-a-hard-architecture-constraint/)
claims a quality cliff around 300–400 and “guessing” by 800). That is a reasonable
story for greenfield product files. It is a rewrite order for bob-plugins fragments
whose p90 is already 885, and it is how sase Python would have looked *before* years
of `toobig_split`.

### Rust

- Clippy `too_many_lines` is **per function**, default **100** code lines (restriction
  lint, opt-in). It is not a file budget.
- A file-level lint is still unsettled: `too_many_lines_in_file` /
  `excessive_file_length` proposals in rust-clippy (issues/PRs in 2026) suggest
  **500–1000 code lines**, restriction group, skip blanks/comments. Not landed as a
  default-on lint, and the PR discussion treats the number as project-specific.
- `toobig` README, written for this toolchain, already documents
  `toobig --include '*.rs' crates 800 650 500` as the Rust example. That is a
  *destination* for a well-split crate, not a first trigger on sase-core.
- Corpus studies (PeerJ CS 406, 2021) found Rust files longer than Python/JS/TS on
  average (mean SLOC ~144 vs Python ~99) but nowhere near sase-core’s median 428. This
  backend is file-lumped relative to typical Rust, not merely “Rust is verbose.”

### Swift

SwiftLint `file_length` ([reference](https://realm.github.io/SwiftLint/file_length.html)):

- Enabled by default.
- Warning **400**, error **1000**, `ignore_comment_only_lines: false`.

Projects commonly raise this (`file_length: warning 500 / error 1200` appears in
SwiftLint’s own config examples; some apps use 800 / 1200). Applying the *defaults* to
bob-mac-capture Sources would warn on ~24% of files and error on 6. The error default
(1000) is the interesting number: it matches sase Python’s hard limit and the
common agent-read paging window.

### Agent-tooling cliff (language-agnostic)

Several independent constraints land near **1,000 lines**:

- sase Python hard limit is 1000.
- SwiftLint default error is 1000.
- Proposed Clippy file lint defaults cluster at 500–1000.
- This environment’s file-read tool pages at 1,000 lines. Files above that cannot be
  ingested in one default read.

Token math on these trees (~33 bytes/line, roughly 8 tokens/line of code) says 700
lines ≈ 5–6k tokens and 3,000 lines ≈ 24k tokens. Context *windows* are not the
bottleneck. Edit quality, unique search-replace anchors, missed call sites, and
read-tool paging are.

Atticus Li’s 200-line rule is too tight for these production trees and for sase’s
proven 500-target Python regime. The useful claim from that essay is the *shape*: a
split target below the quality cliff, a trigger with hysteresis, tests allowed to run
longer than production files.

## Critique of the plan

### What is worth doing

Exporting a line-count *ratchet* plus scheduled split agents is the right maintenance
shape for agent-edited repos. sase Python is evidence: 11k files, five over the
trigger, none over the hard limit. Small files are easier for `#split_file`-class
agents to finish in one turn, and the `%if` recheck plus `toobig-` clan inhibit are
load-control that other chores should copy.

`toobig` is already the right scanner. The chop already takes per-instance `trees` and
`limits` vars. `for_each: source: projects` is the right fan-out once the rest of the
pipeline is language-aware.

### What would go wrong if the job is copied as-is

1. **Scanner default is `*.py`.** Enabling the job on bob-cli without `--include '*.rs'`
   is a silent no-op, not a Rust split program.
2. **`#split_file` is Python.** A Rust/Swift/JS agent following that macro will invent
   Python facades, run missing `just _lint-mypy` recipes, and skip `clippy` /
   `swift test` / fragment rebuild + parity.
3. **700 is not a language constant.** It is sase Python’s p99+ε. On sase-core it is
   p~70. Same number, opposite job.
4. **Trees are a Python layout.** `src`+`tests` fits sase and bob-cli. It misses
   `crates/`, `Sources/`, `Tests/`, `plugins/*/src`.
5. **No excludes.** `toobig` does not honor `.gitignore` and has no `--exclude`.
   bob-plugins `main.js` and any generated Swift/Rust would be proposed as split
   targets.
6. **Sequential unbounded fan-out.** One proposal per oversized file, `wait_on` the
   previous, clan inhibit for the whole `toobig-` prefix. A 200-file sase-core backlog
   monopolizes the maintenance lane and pauses sase Python splits.
7. **Only enabled projects can be `for_each` targets.** Today that is sase and bob-cli.
   sase-core, bob-plugins, bob-mac-capture, and actstat are not in that list until they
   are launchable SASE projects (or the job is given explicit repo roots).
8. **One clan prefix across projects.** `inhibit_if: agent_clan: { name_prefix: toobig- }`
   is global. That is acceptable as a capacity lock if ticks are capped. It is
   catastrophic if one repo dumps 200 members into the clan.
9. **Split target is buried in the macro.** Chop admission uses `min(limits)` (700),
   CI hard-fails at 1000, agents aim at 500. Other languages need that triple stated
   per project, not inherited from a Python prompt.

### Required adjustments (called out)

These change the user’s implied requirements. They are justified by the measurements
above.

- **Do not pick one trigger per language and apply it to every repo in that
  language.** Pick a per-repo ratchet from that repo’s current p95/p99, then walk it
  down toward a language-aware *target*. Language informs the destination and the
  split recipe. The current tail informs the first trigger.
- **Do not run split agents until a language-specific split macro (or a parameterized
  `#split_file`) exists** for that tree, including the repo’s real verification
  command.
- **Install `toobig` as a CI gate first**, with `--include` and tree lists, for a
  quiet week. Agents second.
- **Cap proposals per tick** (largest first, 1–3). Keep sequential `wait_on`.
- **Exclude generated and bundled files** (bob-plugins `main.js`; any `target/`,
  derived Swift). This likely needs a `toobig --exclude` or chop-side path filter;
  basename `--include` cannot say “all `*.js` except `main.js`” if both live under the
  same tree.
- **Rust first split: extract `#[cfg(test)]` modules**, then production `impl` blocks.
  Do not start by slicing a 3,300-line scanner into Python-style facades.
- **JavaScript: scan fragments, never built bundles.** Optionally split oversized
  `scripts/test-*.cjs` with a higher test budget.
- **Swift: separate source vs XCTest budgets**, and a SwiftUI-aware recipe (views /
  models / tests tend to move as a triple).
- **Keep sase Python at 1000 / 850 / 700 trigger and 500 target.** It is working.

## Recommended solution

### 1. Keep three numbers, always

For every project, publish an explicit triple plus a split target:

- **Hard (CI fail)** — above today’s max, or at the agent-read paging cliff once the
  tail is under it.
- **Warn**
- **Info / chop trigger** — first files the job may propose; must be a small tail.
- **Split target** — what `#split_file_*` asks the agent to land under, with ~200–400
  lines of hysteresis below the trigger so a successful split does not immediately
  requeue.

### 2. Language destinations (long-term, after ratcheting)

These are where *new* files should live, and where old files should eventually be
pushed. They are **not** day-one triggers on the existing tails.

| Language | Split target | Chop trigger (info) | CI warn | CI hard | Why |
| --- | ---: | ---: | ---: | ---: | --- |
| Python (keep) | 500 | 700 | 850 | 1000 | Proven on sase; p90/p99/max alignment |
| Rust | 800 | 1000 | 1200 | 1500 | Matches toobig README destination (~800/650/500) loosened for `wc -l` vs code-only counting, in-file tests, and the 1000-line read cliff |
| JavaScript (hand-authored) | 600 | 800 | 900 | 1000 | ESLint’s 100–500 band is the aesthetic floor; bob-plugins fragments already self-limit near 1000; 600 sits near their median |
| Swift sources | 500 | 700 | 850 | 1000 | Aligns with SwiftLint warn/error defaults and with Python; median source file is already 127 |
| Tests (all languages) | 800 | 1000 | 1200 | 1500 | Tests run longer (Li; sase Python tests already do); XCTest and bob-cli parity tests especially |

Rust’s destination is *higher* than Python’s, not lower, despite the README’s
`800 650 500` example: `toobig` counts comments/blanks/`#[cfg(test)]`, Clippy file
proposals count code lines only, and these crates keep tests in-file. Aiming at 500
`wc -l` for Rust would punish exactly the module style sase-core uses.

### 3. Day-one ratchets (what to actually configure first)

Trigger only the current monster tail. CI-hard should not fail the branch on day one.

| Project | Include | Trees | Day-one `hard / warn / info` | Split target for those hits | Why this info floor |
| --- | --- | --- | --- | --- | --- |
| sase (unchanged) | `*.py` (default) | `src`, `tests` | 1000 / 850 / 700 | 500 | Already the p99 ratchet |
| bob-cli | `*.rs` | `src`, `tests` | 2500 / 2200 / 2000 | 1200 | 2 src files `>2000`; gets them under the 1000–1500 band in a couple of splits |
| sase-core | `*.rs` | `crates` | 3500 / 3000 / 2500 | 1500 | ~9 files `>2500`; 209-file 700-trigger is rejected |
| actstat | `*.rs` | `src` | 3000 / 2500 / 2000 | extract tests, then 1200 | Single 2,975-line `github.rs`, 54% `cfg(test)` |
| bob-plugins | `*.js` on **fragment trees only** | each `plugins/<name>/src` | 1200 / 1100 / 1000 | 800 | Fragments max 981 today; this is a hold-the-line gate, almost no chop work |
| bob-plugins tests | `test-*.cjs` | `scripts` | 20000 / 8000 / 4000 or skip | n/a until a test-split recipe exists | 19k-line test scripts are a different job |
| bob-mac-capture sources | `*.swift` | `Sources` | 4000 / 2500 / 1500 | 800 | 3 files `>2000`, 6 `>1000`; 1500 info ≈ p95 |
| bob-mac-capture tests | `*.swift` | `Tests` | 7000 / 4000 / 2500 | 1200 | Test file at 6,541; do not use source trigger |

Walk each info floor down toward the language destination only after the previous
band’s backlog is empty.

### 4. Implementation order

1. **Chop/scanner work (prerequisite, small):**
   - Pass `vars.include` through to `toobig --include`.
   - Add chop-side ignore globs (or a `toobig --exclude`) for `main.js`, generated
     files, and well-known build dirs.
   - Add `vars.max_proposals` (default 2).
   - Per-project `trees` / `limits` / `include` on the Axe job; do not share one
     limits list across `for_each`.
   - Optional: per-project clan prefix (`toobig-rs-`, `toobig-py-`) so a Rust backlog
     cannot inhibit Python.
2. **CI-only `toobig` on bob-cli** with the day-one triple. No agents. Confirm the
   two >2000 files are the ones you want to touch.
3. **Language macros before any non-Python launch:**
   - `#split_file_rs`: prefer moving `#[cfg(test)] mod tests` to `foo/tests.rs` or a
     sibling module; preserve `pub use` and crate visibility; verify with that repo’s
     `just check` / clippy / tests, not sase’s mypy/symvision.
   - `#split_file_js`: operate on fragments; rebuild; run `check-split-parity`; never
     edit built `main.js` except via the build script.
   - `#split_file_swift`: split types/extensions first; keep SwiftUI view + model +
     tests coherent; run `swift test`.
4. **Enable the job on one project** (bob-cli, then actstat, then bob-mac-capture
   Sources). sase-core last: largest backlog, linked-repo layout, highest blast radius.
5. **bob-plugins** is a CI-hold, not an agent swarm, until fragments actually exceed
   1000.

### 5. What I would not do

- I would not enable `for_each` over every project with shared `1000 850 700`.
- I would not adopt ESLint 300 or SwiftLint-warn 400 or Li’s 200 as chop triggers on
  these trees.
- I would not adopt the toobig README’s Rust `800 650 500` as a *first* sase-core
  trigger. Keep it as the written destination.
- I would not split bob-plugins `main.js`.
- I would not start with sase-core. Start with bob-cli (already an enabled project, two
  files over 2000) or actstat (one file, mostly in-file tests).

## Recommended decision in one paragraph

Keep Python’s 700-trigger / 500-target / 1000-hard on sase. For other languages, treat
those numbers as a *destination band* (Rust slightly higher; JS fragments already near
1000; Swift sources can share Python’s destination) and configure each repo with a
much higher first ratchet that only sees today’s outliers. Do not start the
`toobig_split` job on those repos until the chop passes `--include`, ignores generated
files, caps proposals, and dispatches a language-specific split macro. The first
concrete enablement should be bob-cli at `2500 / 2200 / 2000` with a Rust split recipe
that extracts tests before types.

## Sources

Primary (opened via `sase repo open` or in-workspace sase checkout):

- sase `Justfile` `_lint-toobig`; `src/sase/macros/split_file.md`;
  `sase/memory/lint_and_test.md`; `docs/development.md`
- chezmoi `home/dot_config/sase/sase_athena.yml` (`toobig_split` job)
- `gh:bbugyi200/bugyi-chops` (`toobig_split.py`, README)
- `gh:bbugyi200/toobig` (README, CLI, changelog 0.1.0)
- Line-count scans of sase `src/`+`tests/`, sase-core, bob-cli, actstat, bob-plugins,
  bob-mac-capture (2026-10-04)

External:

- ESLint `max-lines` — https://eslint.org/docs/latest/rules/max-lines
- SwiftLint `file_length` — https://realm.github.io/SwiftLint/file_length.html
- Clippy `too_many_lines` (function, default 100); clippy issues/PRs for file-length
  lints (`too_many_lines_in_file` / `excessive_file_length`, 2026)
- Atticus Li, “The 200-Line Limit” (2026-04-09) —
  https://atticusli.com/blog/posts/the-200-line-limit-why-vibe-coding-solo-apps-needs-a-hard-architecture-constraint/
- Ardito et al., “Evaluation of Rust code verbosity…”, PeerJ CS 406 (2021)
- Salesforce LoCoBench-Agent (context scale vs coding ability, 2026)
