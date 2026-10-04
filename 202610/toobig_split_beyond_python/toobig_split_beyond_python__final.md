# Running `toobig_split` Beyond Python: Line Limits for Rust, JavaScript, and Swift

_Consolidated report · 2026-10-04 · merges the `cdx`, `cld`, `grk`, and `gem` researcher
reports, plus my own re-checks on apollo and athena._

## Bottom Line

1. **The premise is mostly wrong; the plan is mostly right.** Rust, JavaScript, and Swift
   do not need looser limits on the grounds that they are "wordier." Three independent
   measurements on your repos (cld, grk, and mine) find 31–40 bytes per line in all four
   languages, and cld measured 7.7–8.5 tokens per line. A 700-line file costs an agent
   about the same to read in any of them. Only Rust gets a raw-line allowance, and the
   reason is structural: inline `#[cfg(test)] mod tests` blocks make up about a third of
   large Rust files.
2. **Choosing numbers is the smallest part of the work.** As wired today, the job cannot
   run usefully on these repos:
   - it scans only `*.py`;
   - every proposal runs a split macro that only works for Python in sase;
   - it cannot find `toobig` outside sase's `.venv`;
   - it can only target registered projects, which on athena are `sase`, `bob-cli`, and
     `actstat`;
   - it has no proposal cap;
   - its clan inhibit is global, which I confirmed in the AXE code.

   Enabled unchanged, it would do nothing at best. At worst, it would queue 146
   sequential Rust agents and block sase's Python splits behind them.
3. **Recommended limits.** Counts are raw newlines, the way `toobig` counts them.

   | Profile                                | hard / warn / **trigger** | **Split target** | First remedy the macro tries                                    |
   | -------------------------------------- | ------------------------- | ---------------: | --------------------------------------------------------------- |
   | Python (sase), **unchanged**           | 1000 / 850 / **700**      |         **≤500** | (existing `split_file`)                                         |
   | Rust                                   | 1500 / 1250 / **1000**    |         **≤700** | Move inline tests over ~150 lines out to `foo/tests.rs`         |
   | Swift                                  | 1000 / 850 / **700**      |         **≤500** | Split at type boundaries, then into `Type+Concern.swift` files  |
   | JavaScript (bob-plugins source fragments) | 1000 / 850 / **700**   |         **≤500** | Cut at top-level declarations into new manifest fragments       |

   Any file larger than about 5× its target should become a one-off `#split_epic`
   rather than a routine `@medium` agent: 2,500 lines for Python, Swift, and JavaScript,
   and 3,500 for Rust.
4. **Is it a good idea?** Yes, but only for some repos, and with conditions:
   - **Now:** bob-cli and sase-core. You are already splitting these by hand with
     `#split_epic`.
   - **Later:** bob-plugins, after its hand-edited `main.js` files move onto the fragment
     build, and the Linux-buildable half of bob-mac-capture.
   - **Not at all:** actstat. It has had six commits in 30 days, and none touched a `.rs`
     file.

   Ship it as per-repo **profiles** with a per-tick cap, a "split or retain" contract,
   and a record of failed attempts. Do not just put new numbers into the current job.

## 1. Inputs and Method

- **Researcher reports:**
  - **cld** and **grk** measured your repos directly.
  - **cdx** worked from source code and primary documentation. It did not know which
    repos were meant, so its numbers come from linter defaults.
  - **gem** combined some measurement with claims that are not sourced, several of which
    are wrong (see §4).
- **My own checks:**
  - I re-read the chop (`bugyi-chops@8cbc4de`), the job config (`chezmoi@64246fcb`),
    `toobig@79ee94b`, sase's `split_file` macro, and the AXE guard code.
  - Over SSH on athena, I checked the project registry, the toolchains, and the hardware
    (64 cores, 62 GB).
  - I re-measured bytes per line, blank lines, and closer-only lines across all five
    repos.
  - I measured the Rust inline-test share together with 30-day hotspot data. This data
    is new; no researcher had it.
  - I classified every bob-plugins `main.js` and read bob-mac-capture's `Package.swift`
    and CI.
  - I checked the Clippy and pylint defaults.

## 2. What the Job Does Today (Verified)

| #  | Fact                                                                                                                                                                   | Consequence beyond Python                                                                                                                       | Source                     |
| -- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| 1  | The chop runs `toobig --files-only <tree> 1000 850 700` with no `--include`. `toobig` defaults to `*.py`.                                                              | A Rust, JS, or Swift project scans **nothing**.                                                                                                 | all four; re-checked       |
| 2  | `--files-only` lists every file that is not OK, so the **real trigger is the info tier (700)**. 1000 is only sase's CI hard failure.                                    | "700 trigger / 500 target" is a hysteresis ratio of 0.71. Keep that ratio in every profile so a fresh split is not re-flagged after a few edits. | cdx, cld, grk              |
| 3  | Every proposal is `%auto #split_file:<path>`. That macro is Python-only: facade re-exports, `_private` rules, `just _lint-mypy` / `_lint-symvision`, `sase tool run check`. | Rust, Swift, and JS agents get the wrong instructions and verify commands that do not exist.                                                   | all four; re-checked       |
| 4  | It makes one proposal per flagged file, chained with `wait_on`, in path order, on `@medium`, with **no cap**.                                                           | sase-core at a 1000 trigger becomes a **146-member** clan.                                                                                      | cld, grk; re-checked       |
| 5  | `inhibit_if.agent_clan.name_prefix: toobig-` is evaluated against **every running agent** (`agent_snapshots` does not filter by project). `CLAN_TEMPLATE = "toobig-@"` is hard-coded. | A Rust backlog **freezes sase's Python splits**. cld left this unverified and grk assumed it; I confirmed it in `src/sase/axe/chop_policy_snapshots.py`. | new verification           |
| 6  | `toobig` is found through `vars.toobig`, then `<repo>/.venv/bin/toobig`, then `PATH`. On athena it exists **only** in sase's `.venv`.                                   | Non-Python repos fail with "toobig executable is unavailable" unless `vars.toobig` is set or `toobig` is installed as a tool.                    | cdx hinted; checked on athena |
| 7  | `toobig` on a missing directory exits 1 with no output, and the chop treats that as a scanner failure.                                                                 | One `trees: [crates, src, tests]` list shared by sase-core and bob-cli (cld's config sketch) **fails every tick**. Use per-repo trees, or have the chop skip missing trees. | new                        |
| 8  | `toobig` has no `--exclude`, ignores `.gitignore`, and cannot detect generated files.                                                                                   | bob-plugins' two **generated** `main.js` files (20,502 and 12,119 lines) would be proposed for hand-splitting, which the repo's AGENTS.md forbids. | all four; re-checked       |
| 9  | `for_each: source: projects` only reaches registered projects. On athena those are sase, bob-cli, and actstat. sase-core, bob-plugins, and bob-mac-capture are not projects. | Three of the five target repos cannot be targeted as written.                                                                                   | cld; checked on athena     |
| 10 | Nothing records failures or decisions. A file that an agent cannot or should not split is proposed again every hour.                                                    | Combined with largest-first ordering and a cap, one unsplittable file would **block the lane permanently**. A failure record is required once a cap exists. | cld, cdx; this interaction is new |
| 11 | The scanner flags `> 700`, but the admission guard admits `>= 700`.                                                                                                    | Harmless, but make both comparisons `>`.                                                                                                        | cdx, cld                   |

## 3. Measurements

### 3.1 Size Distributions (raw lines, git-tracked files)

| Repo                               | Lang  |  Files | p50 |   p90 |   p95 |    max | >700 | >1000 | >1500 | Commits in last 30 days |
| ---------------------------------- | ----- | -----: | --: | ----: | ----: | -----: | ---: | ----: | ----: | ----------------------: |
| sase `src`+`tests`                 | py    | 11,348 | 202 |   481 |   562 |    913 |    5 |     0 |     0 |             ~1,900 / mo |
| sase-core                          | rs    |    926 | 409 | 1,251 | 1,685 |  3,330 |  261 |   146 |    58 |                     527 |
| bob-cli                            | rs    |    395 | 499 | 1,194 | 1,632 |  2,204 |  139 |    68 |    26 |                     234 |
| actstat                            | rs    |      7 | 677 |   846 |     — |  2,975 |    3 |     1 |     1 |         6 (none `.rs`) |
| bob-mac-capture                    | swift |    115 | 185 | 1,040 | 1,743 |  6,541 |   18 |    13 |     8 |                      94 |
| bob-plugins (excl. 2 generated)    | js    |    104 | 660 | 1,328 | 2,689 | 51,960 |   47 |    16 |    11 |                      99 |

sase's distribution is the output of the regime itself: p99 is 669, and the count drops
off sharply at 700. The other repos show what agent-written code looks like without
it: 16–35% of their files are over 700 lines.

### 3.2 A Line Costs About the Same in Every Language (resolves the main question)

| Repo            | Bytes/line (mine) | Tokens/line (cld, o200k) | Blank | Closer-only (`}`, `)`) | Blank + closer |
| --------------- | ----------------: | -----------------------: | ----: | ---------------------: | -------------: |
| sase (py)       |              34.6 |                     7.82 | 13.2% |                   5.5% |          18.7% |
| sase-core (rs)  |              33.7 |                     7.66 |  5.9% |                  15.0% |          20.9% |
| bob-cli (rs)    |              33.3 |                     8.04 |  6.1% |                  14.9% |          21.0% |
| bob-mac-capture |              39.5 |                     8.53 |  8.7% |                  14.7% |          23.4% |
| bob-plugins     |              31.1 |                     8.06 |  7.0% |                  18.2% |          25.2% |

Python spends its overhead on blank lines; the brace languages spend theirs on
closing-brace lines. The two roughly cancel. Swift is slightly *denser* than Python,
not looser. JS carries about 6 points more structural overhead, which works out to
roughly 50 lines at a 700 trigger. That is within the noise, so it does not justify a
separate profile.

**Caveat:** this measures how much an agent pays to read a line. It does not measure
how much behavior fits in a line. Rust and Swift can need more lines per feature (trait
impls, error mapping). That shows up as a larger natural module size, which is why the
evidence on what cohesive splits actually produce (§3.4) matters more than verbosity
folklore.

### 3.3 Rust: Inline Tests Are the Real Difference

| Repo      | >1000 raw | >1000 counting non-test lines only | >1500 raw → non-test | >2000 raw → non-test |
| --------- | --------: | ---------------------------------: | -------------------: | -------------------: |
| sase-core |       146 |                                107 |              58 → 31 |               23 → 7 |
| bob-cli   |        68 |                                 56 |              26 → 22 |                2 → 1 |
| actstat   |         1 |                                  1 |                1 → 0 |                1 → 0 |

In Rust source files over 700 lines that contain inline test modules, those tests make
up 33–36% of the file (cld). The non-test equivalent of Python's 700 is therefore about
700 / 0.65 ≈ **1,050 raw lines**. That is the case for a 1000 raw trigger.

Moving tests out is already a convention in sase-core: 74 files use `#[cfg(test)] mod
tests;` with the tests in a separate file, against 358 files that still keep them
inline. rustc's own `tidy` requires that layout for large crates (cld). Moving tests out
first is idiomatic, mechanical, and safe, and it removes most of the >2000 tail on its
own. For example, `agent_scan/scanner.rs` (3,330 lines) contains 1,447 test lines.

### 3.4 What Your Hand-Run Rust Splits Actually Produced (cld)

These are the `#split_epic` runs on sase-core (2026-09-20/21, about 20 commits) and
bob-cli (2026-09-29 and 2026-10-03, 15 or more commits):

- With a "≤1500" or "≤875" target, the largest resulting module was usually 700–1,250
  lines.
- With "cohesive modules" as the only instruction, sibling modules landed mostly at
  250–600 lines, and the largest at 683–1,336.

So a cohesion-driven Rust split naturally produces modules of about 300–900 lines.
**≤700 is reachable without forcing artificial seams; ≤500 is not.** Note that your
`#split_epic` default of `max_line_count: 1500` is a ceiling on the *resulting* files.
It is not a trigger, so it does not argue for gem's 1,500-line trigger.

### 3.5 Hotspots (new): Almost Every Large File Is Hot, and the Hottest Is a Hub

| Repo            | Files >1000 | …touched in last 30 days | …touched ≥5 times |
| --------------- | ----------: | -----------------------: | ----------------: |
| sase-core       |         146 |                      139 |                59 |
| bob-cli         |          68 |                       68 |                33 |
| bob-mac-capture |          13 |                       13 |                12 |
| bob-plugins     |          16 |                       15 |                12 |
| actstat         |           1 |                        0 |                 0 |

Two consequences:

1. **Ordering by hotspot alone barely filters these repos**, because nearly every large
   file is active. It only re-orders them.
2. **The top `lines × touches` file in sase-core is `crates/sase_core/src/lib.rs`**:
   1,652 lines and 129 touches, almost all of it `pub mod` declarations (128) and `use`
   re-exports (108). It is hot because every new module touches it, and splitting it
   buys little. Hub files like this are what the "retain" outcome (§6, ADJ-3) is for.

The **hottest large file across all five repos** is bob-plugins'
**hand-edited** `bob-navigation-hotkeys/main.js`: 51,960 lines, 61 touches in 30 days.
Moving it onto the fragment build is probably the single highest-value item in this
whole expansion, and it does not need `toobig_split` at all.

### 3.6 Swift Builds Only Partly on Linux

`Package.swift` defines the AppKit targets (`BobMacCapture` and `…InstallHelper`, plus
their tests) only under `#if os(macOS)`. On athena, only `CaptureCore` and
`CaptureCoreTests` compile.

- Of the 18 Swift files over 700 lines, **10 are buildable on Linux**: 5 in
  CaptureCore and 5 in CaptureCoreTests.
- **8 are macOS-only**, including `CapturePanelModel.swift` (5,081 lines) and
  `CapturePanelModelTests.swift` (6,541 lines).

The repo does have a GitHub Actions `macos-26` CI job (format-lint, build, test,
bundle). AppKit splits could therefore be verified through PRs instead of a local
build. It is a SwiftPM package, with no `.xcodeproj` and no `.swiftlint.yml`.

### 3.7 bob-plugins: Two `main.js` Files Are Generated, Four Are Hand-Edited

| Plugin                 | `main.js` lines | Built from `src/fragments.json`? |
| ---------------------- | --------------: | -------------------------------- |
| bob-ledger-tools       |          20,502 | **generated** (do not edit)      |
| task-status-cycler     |          12,119 | **generated** (do not edit)      |
| bob-navigation-hotkeys |          51,960 | hand-edited                      |
| block-id-prompt        |           6,880 | hand-edited                      |
| bob-vim-surround       |           1,328 | hand-edited                      |
| bob-project-tasks      |             276 | hand-edited                      |

`scripts/build-plugins.mjs` concatenates the fragments into one script scope, enforces
`MAX_FRAGMENT_LINES = 1000`, and writes a `// Generated by … Do not edit directly.`
header. Across the 56 fragments, 36 are over 500 lines, 21 over 700, 8 over 850, and the
largest is 981. The test scripts are large too: `scripts/test-navigation-hotkeys.cjs`
is 19,813 lines, and `package.json`'s `test` script lists every test file explicitly.

### 3.8 What the Python Regime Costs in sase

The routine has run since 2026-07-15 (`pylimit` → `toobig` split chop). The two counts
of split commits differ only because they match commit subjects differently:

- **cld's match:** 2.6% of commits in July, 7.5% in August, 14% in September.
- **My match** (`^(refactor|test|chore)(scope): split `): 13–14% in July and August,
  18% in September, with an average September split of +785/−678 lines.

Either way, **roughly one commit in six or seven is now a split**. These numbers
include epic and manual splits, not only the routine. cld spot-checked about 700 commit
subjects and found only one that looked non-semantic, so quality looks good. **Nobody
has measured whether the churn pays off.** Expect a split share of similar size in
every repo you enable, in proportion to how fast agents add code there.

## 4. Where the Reports Disagreed, and How I Resolved Each Point

| Question                                    | cdx                                       | cld                                         | grk                                                          | gem                                            | Resolution                                                                                                                                                                                                                                                                         |
| ------------------------------------------- | ----------------------------------------- | ------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Do the languages need looser limits?        | Somewhat (linter-anchored)                 | No, except Rust tests                       | Only because "modules grow larger"                            | Yes ("700 py ≈ 1,500–2,500 rs/swift")          | **No, except Rust.** Three density measurements agree (§3.2). gem's ratio has no source.                                                                                                                                                                                             |
| Rust trigger / target                       | 1000 / 600                                | 1000 / ≤700                                 | 1000 / 800 long-term, with day-one triggers of 2000–2500      | 1500 / 1000                                    | **1000 / ≤700.** Three of the four agree on 1000. 700 matches the observed cohesive splits (§3.4). gem's 1500 confuses `#split_epic`'s output ceiling with a trigger.                                                                                                                   |
| Swift                                       | 700 / 400                                 | 700 / ≤500                                  | 700 / 500 long-term, with day-one triggers of 1500 (sources) and 2500 (tests) | 800 / 500                              | **700 / ≤500**, the same as Python. Swift is the densest language here, and SwiftLint's default error tier is 1000.                                                                                                                                                                  |
| JavaScript                                  | 600 / 350                                 | 700 / ≤500 (or 850 at first)                | 1000 trigger / 800 target (hold the line)                     | 800 / 500                                      | **700 / ≤500**, with 1000 as the hard limit because the fragment build already enforces it. cdx's 350 target was chosen without knowing about the fragment build; it would put 36 of 56 fragments in scope immediately.                                                              |
| Autonomous routine or advisory beads?       | Assess first: split, retain, or defer     | Autonomous with cap and profiles            | Autonomous after a CI-only week                               | **Advisory beads only**, humans trigger splits | **Autonomous, assessment-first.** sase shows 2.5 months of autonomous splits with good semantic quality. You already run these splits by hand. Beads would turn 146+ files into review work for your attention, which is the scarcest resource. gem's "battery and CPU" concern does not apply to a 64-core server. |
| Large backlog: threshold ramp or cap?       | Cap plus a daily budget                   | Cap plus hotspot ordering, no ramp          | Per-repo ratchet that walks thresholds down from p95/p99      | Audit-only phase                               | **Cap plus largest-first ordering plus a failure record**, so the backlog drains worst-first with no manual walk-down. grk's ratchet remains right for the *CI gate* (§6, ADJ-7).                                                                                                    |
| Ordering                                    | Change frequency plus exceedance          | `lines × 30-day commits`                    | Largest first                                                 | —                                              | **Largest first**, skipping files with no commits in 60 days. Hotspot weighting barely filters these repos and ranks hub files first (§3.5).                                                                                                                                          |
| Separate test budgets?                      | Don't treat tests like production code    | Same numbers                                | Higher (1000 / 800)                                           | —                                              | **Same numbers**, as sase does for `tests/`. Giant test files go to epics anyway. Revisit if test splits turn out low-value.                                                                                                                                                       |

**Factual corrections to individual reports:**

- **gem:**
  - Python's baseline does *not* exclude comments or docstrings; `toobig` counts raw
    newlines.
  - The Xcode `project.pbxproj` hazard does not apply, because bob-mac-capture is
    SwiftPM-only.
  - Its `**/main.js` exclude would hide the largest hand-edited, and hottest, file in
    the whole set.
  - Its `toobig_audit` job and `targets:` config keys do not exist.
- **grk:**
  - Only 2 of the 6 `main.js` files are generated, not 6.
  - The "file-read tool pages at 1,000 lines" argument depends on the harness. Claude
    Code's Read tool defaults to 2,000 lines, so the read cliff is not a reliable anchor.
  - On athena, actstat is also an enabled project.
- **cld:** Its config sketch shares `trees: [crates, src, tests]` across sase-core and
  bob-cli, which fails on whichever tree is missing in each repo (§2, row 7).
- **cdx:** Its JS and Swift numbers come from linter defaults, not from the repos, and it
  had no view of the fragment build.

## 5. Critique: Is This a Good Idea?

### What Is Right About It

- **You are already doing it by hand.** In the last two weeks you ran `#split_epic`
  against sase-core and bob-cli. You also added a `repo` input to `#split_epic` this
  morning. Automating that work with hysteresis is the natural next step.
- **The repos are hot and agent-written.** sase-core has 527 commits in 30 days and
  bob-cli 234. Large hot files cost tokens on every read and attract merge conflicts
  across about 20 parallel workspaces.
- **The mechanism has proven itself on sase:** sequential clans, a `%if` re-check
  before admission, and a clan inhibit. Python files grew 20× while the mean file
  length held at about 200 lines (cld).

### What Is Wrong or Risky

1. **It asks "which number?" when the real gap is "which pipeline?"** The include glob,
   macro, verify command, mission text, scan roots, toolchain path, and build host are
   all set up for Python in sase (§2).
2. **Line count is a proxy.** Four 250-line files that change together are worse than
   one cohesive 1,000-line file (cdx, gem). Agents under "make it compile" pressure tend
   to widen visibility: `pub(crate)` in Rust, `internal` in Swift, extra exports in JS.
   The contract has to allow "retain" and has to report every widened symbol.
3. **There is no backpressure or memory.** With no cap, a large backlog floods the
   global `toobig-` lane. With no failure record, an unsplittable file comes back every
   hour.
4. **The build host does not match the code.** An agent cannot verify 8 of the 18 large
   Swift files on athena.
5. **Copying 700/500 also copies its churn**, about 1 in 6–7 commits, without evidence
   that the agent-ergonomics benefit is real. The literature does not settle this:
   - Koru et al. found larger modules are *proportionally less* defect-prone, so the
     case for splitting cannot rest on defects.
   - SWE-agent's file-viewer ablation and Chroma's *Context Rot* study support keeping
     the code an agent reads focused, but they do not set a file-size cutoff.
   - The empirical threshold studies are mostly Java-based (cdx).

   The defensible rationale is agent ergonomics plus fewer merge conflicts. Both should
   be measured.

### What I Would Do Differently

- **Profiles, not limits.** Each profile is a bundle: include and exclude globs,
  thresholds, split target, split macro, verify command, build host, clan prefix, and
  cap.
- **Drain the backlog worst-first under a cap**, and send giant outliers to `#split_epic`
  instead of ramping thresholds by hand.
- **Make "retain" a first-class, reviewable outcome** (pragma with a ceiling, §7.2) so
  hub files and cohesive state machines stop coming back.
- **Treat the bob-plugins `main.js` migration as its own project** and do it first. It
  is the biggest maintainability win, and the routine is not the tool for it.

## 6. Requirement Adjustments (Explicitly Called Out)

> **ADJ-1: Reframe the deliverable.** You asked for per-language *line limits*. I
> changed it to per-repo *language profiles*. The macro, verify command, exclusions,
> scan roots, and build host decide whether the job works; the limit decides only how
> much work it creates.
>
> **ADJ-2: Do not loosen limits for Swift or JS.** The request assumes they need
> different numbers. Your code says they do not (§3.2). Rust alone gets a raw-line
> allowance (1000 / ≤700), tied to inline tests. Reassess it after about six weeks: once
> test extraction is the norm, raw counts approach non-test counts, so tighten Rust to
> 1250 / 1000 / 850 with a ≤600 target.
>
> **ADJ-3: Make the contract "split or retain."** Crossing the trigger admits an
> assessment, not a mandatory split. A retained file gets a committed pragma that
> records a reason and a line ceiling. Agent failures get a backoff record. Neither was
> requested, but both are required once proposals are capped (§2, row 10).
>
> **ADJ-4: Add backpressure.** Use per-profile clan prefixes, start at
> `max_proposals: 1`, order largest-first, and route files above about 5× the target to
> `#split_epic`. Without this, the Rust backlog freezes sase's Python lane (§2, row 5).
>
> **ADJ-5: Narrow the scope.**
> - Drop actstat from the routine: it is cold. Run one manual Rust split instead;
>   moving its tests out alone takes `github.rs` from 2,975 lines to about 1,370.
> - Limit bob-mac-capture on athena to `CaptureCore` and `CaptureCoreTests`. Handle the
>   AppKit targets through PRs gated by the macOS CI, or as epics on the Mac.
> - Enable bob-plugins only after its hand-edited `main.js` files are migrated.
>
> **ADJ-6: Make the targets reachable.** Register sase-core, bob-plugins, and
> bob-mac-capture as SASE projects on athena, or extend the chop to launch into linked
> repos.
>
> **ADJ-7: Add no new CI hard gates until each backlog drains.** Then add a `toobig`
> lint to each repo's `just lint`, with pragma ceilings as the per-file baseline.
> grk's ratchet idea belongs here.
>
> **ADJ-8: Measure outcomes before scaling up** (§7.4). The Python regime's benefit has
> never been measured either.

## 7. Recommended Solution

### 7.1 Profiles

| Profile          | Repos and scan roots                                                                                        | Include                      | Limits `hard warn info` | Target | Split macro                | Verify                                                                                                           | Host                                            |
| ---------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------- | ----------------------- | -----: | -------------------------- | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `python`         | sase `src`, `tests`                                                                                         | `*.py`                       | `1000 850 700`          |    500 | `split_file` (unchanged)   | existing                                                                                                         | athena                                          |
| `rust`           | bob-cli `src`, `tests`; sase-core `crates` (separate job instances)                                         | `*.rs`                       | `1500 1250 1000`        |    700 | new `split_rust_file`      | repo's `just` recipe, or `cargo fmt --check`, `cargo clippy --all-targets -D warnings`, `cargo test` for affected crates | athena                                          |
| `swift-core`     | bob-mac-capture `Sources/CaptureCore`, `Tests/CaptureCoreTests`                                             | `*.swift`                    | `1000 850 700`          |    500 | new `split_swift_file`     | `swift build`, `swift test --filter CaptureCoreTests`, plus swift-format lint if installed                       | athena                                          |
| `swift-appkit`   | the remaining `Sources` and `Tests`                                                                         | `*.swift`                    | `1000 850 700`          |    500 | `split_swift_file`         | macOS CI on a PR (`macos-26`), or run on the Mac                                                                 | PR-gated or Mac epic                            |
| `js-bob-plugins` | each `plugins/<id>/src` listed explicitly (trees are literal directories, not globs), plus `scripts`        | `*.js`, `*.cjs`, `*.mjs`     | `1000 850 700`          |    500 | new `split_js_fragment`    | `npm run build`, `npm run build:check`, `npm test`                                                               | athena, after the migrations                    |

### 7.2 Code and Config Changes (small, prerequisites)

**`toobig`:**

- Add a repeatable, path-aware `--exclude GLOB`.
- Skip files whose first 5 lines carry `@generated` or `Generated by … Do not edit`.
  The bob-plugins build header already matches the second form.
- Honor an in-file pragma `toobig: allow-lines=<N> <reason>`. It treats the file as OK
  up to N lines and lists it in verbose output, so retained files stay visible and
  cannot grow without limit. It is modeled on rustc's `ignore-tidy-filelength`, with a
  ceiling added.

**`bugyi_chops/toobig_split.py`:**

- Add the vars `include`, `exclude`, `split_macro`, `clan_prefix`, `max_proposals`
  (default 1), `max_file_lines`, and `model`.
- When a file exceeds `max_file_lines`, emit a notification recommending
  `#split_epic:repo=…` instead of a proposal.
- Order proposals largest-first.
- Skip missing trees with a warning instead of failing the scan.
- Add failure backoff: key it by path plus content hash in the job state directory, and
  skip until the file's content changes or 7 days pass.
- Make the mission text language-neutral, and make the `%if` floor a strict `>`.

**Config (chezmoi `sase_athena.yml`):**

- Use one map-form job per repo, or per profile where the trees match, each with its own
  `inhibit_if.agent_clan.name_prefix`, such as `toobig-rs-bob-cli-`.
- Set `vars.toobig` to sase's `.venv/bin/toobig`, or `uv tool install toobig` on athena.
- Optionally add an `agent_runners` guard so maintenance never crowds out feature work.

```yaml
toobig_split_bob_cli:
  script: bugyi_chop_toobig_split
  description: |-
    Propose split-or-retain agents for oversized Rust files in bob-cli
  run_every: 60m
  inhibit_if:
    agent_clan: { name_prefix: toobig-rs-bob-cli- }
  for_each: { source: projects, names: [bob-cli] }
  vars:
    toobig: ~/projects/github/sase-org/sase/.venv/bin/toobig
    trees: [src, tests]
    include: ["*.rs"]
    limits: ["1500", "1250", "1000"]
    split_macro: split_rust_file
    clan_prefix: toobig-rs-bob-cli-
    max_proposals: 1
    max_file_lines: 3500
```

(These vars follow the proposed chop changes. Today the chop accepts only `trees`,
`limits`, `toobig`, and the target-resolution vars.)

### 7.3 What Each New Macro Must Say

The macros could also be one `split_file` macro with language sections.

**Shared rules for every macro:**

- Assess first. If no separable responsibility exists, add the `toobig: allow-lines`
  pragma with a reason, then stop.
- Never delete comments or blank lines, or compress code, to hit the number.
- Preserve the public API.
- List every symbol whose visibility was widened.
- Run the repo's real verify recipe. Never invent one.

**`split_rust_file`:**

1. If an inline `#[cfg(test)] mod tests { … }` is over about 150 lines, move it to
   `foo/tests.rs` (`#[cfg(test)] mod tests;`), then re-measure.
2. Split by responsibility into child modules. Keep types and private fields in the
   parent and move `impl` blocks into the children. Use the narrowest visibility that
   works (`pub(super)` before `pub(crate)`, never a new `pub`). Re-export with `pub use`
   only items that were already public.
3. Under `tests/`, never add new top-level files, because each one compiles as a
   separate crate. Use `tests/<name>/main.rs` with submodules.
4. Verify the feature and target configurations that the crate supports.

**`split_swift_file`:**

- Split at type boundaries first (one primary type per file), then into
  `Type+Concern.swift` extensions. Stored properties stay in the primary declaration.
- Moving code out of the file breaks `private` and `fileprivate` access. Widen only to
  `internal`, never to `public` or `open`.
- Split XCTest classes by behavior area.
- On Linux, refuse to edit macOS-only targets.

**`split_js_fragment` (bob-plugins):**

- Edit `src/` fragments only, never a generated `main.js`.
- Cut at top-level declarations into new fragments, and insert them into
  `fragments.json` in load order. All fragments share one script scope, so watch the
  `const` and `class` ordering.
- For test `.cjs` files, add each new file to `package.json`'s `test` script.
- For any future ESM code, use direct imports and no barrel files.

### 7.4 Rollout and Success Metrics

1. **Week 0, prerequisites:**
   - Make the §7.2 changes and write the three macros.
   - Register the target repos as projects.
   - Start the bob-plugins migration epics: move `bob-navigation-hotkeys` (51,960),
     `block-id-prompt` (6,880), and `bob-vim-surround` (1,328) onto the fragment build.
2. **Week 1, bob-cli:** use `max_proposals: 1` and review the first five outcomes
   yourself, checking visibility widening, cohesion, and verify time. bob-cli is already
   a project, has 68 files over 1000 lines, and has no file above 2,204.
3. **Week 2:**
   - Raise bob-cli to a cap of 2.
   - Enable sase-core. Its two files above 3,000 lines (`scanner.rs` and
     `touch_index.rs`) fall under the Rust epic threshold, or `scanner.rs` gets its
     tests moved out first.
   - Enable `swift-core`.
   - Start epics for the AppKit monsters.

   At sase's observed rate of about 9 splits per day, sase-core's backlog takes roughly
   2–3 weeks of lane time.
4. **Week 3 onward:** enable `js-bob-plugins` once the migrations land.
5. **After about six weeks:** compare each repo before and after on these measures:
   - split commits as a share of all commits;
   - re-split rate (the same file flagged again within 30 days);
   - retain, failure, and abandon rates;
   - visibility widenings per split;
   - merge conflicts on recently split files;
   - wall-clock verify cost per split (unmeasured for sase-core's `cargo` runs);
   - tokens per agent task, if usage data allows.

   Then tighten Rust (ADJ-2), or loosen everything if the churn is not buying anything
   measurable.

## 8. Confidence and Limitations

- **High confidence:**
  - the job, chop, and scanner mechanics, including the global inhibit, the toolchain
    path, and missing-tree failures;
  - equal per-line cost across languages, from three independent measurements;
  - the repo distributions;
  - the Swift Linux constraint;
  - the bob-plugins `main.js` classification.
- **Medium confidence:**
  - Rust 1000 / ≤700, supported by the inline-test share and observed split outcomes,
    but not validated against outcomes;
  - assessment-first autonomy as safer than both a blind routine and advisory-only beads.
- **Low confidence:**
  - that *any* file-length regime improves agent outcomes enough to justify about 15% of
    commits. This is unmeasured in sase as well.
  - The empirical maintainability literature is mostly about Java, and some of it cuts
    against "smaller is better" for defects.
- **Not measured:** `cargo` verification time per split, merge-conflict rates, and how
  the macros behave on Swift or JS. The pilot exists to find these out.

## Recommended Solution

Keep sase's Python policy as it is (1000 / 850 / 700, target ≤500). Do **not** loosen
the limits for Swift or JavaScript: in your code a line costs an agent the same in every
language, so they get Python's 700 trigger and ≤500 target. Give Rust a 1000 trigger
and ≤700 target, because inline tests make up about a third of large Rust files. Make
"move inline tests out" its first remedy, and plan to tighten it after about six weeks.

Before enabling any of this, turn `toobig_split` into a profile-driven, capped,
assessment-first job:

- language-specific split macros and verify recipes;
- include and exclude globs plus generated-file skipping;
- a committed `allow-lines` retain pragma and a failure backoff;
- per-repo clan prefixes, `max_proposals` starting at 1, largest-first ordering, and
  routing of files above about 5× the target to `#split_epic`;
- reachable targets (registered projects, and an explicit `toobig` path).

Then roll it out in this order:

1. bob-cli.
2. sase-core.
3. bob-mac-capture's Linux-buildable CaptureCore.
4. bob-plugins, after its hand-edited `main.js` files move onto the fragment build.
   Start that migration first; it is the single highest-value item.

Do not enable it for actstat. Judge the whole regime by measured outcomes, not by
shorter files.

## Sources

**Local:** I inspected each of these directly, through `sase repo open` or my own
workspace checkout.

- **chezmoi `home/dot_config/sase/sase_athena.yml`:** the `toobig_split` job.
- **chezmoi `home/dot_config/sase/sase.yml`:** the `split_epic` macro (`lang: Rust`,
  `max_line_count: 1500`, plus the `repo` input added 2026-10-04).
- **`bbugyi200/bugyi-chops` `src/bugyi_chops/toobig_split.py`.**
- **`bbugyi200/toobig`:** README and `cli.py`.
- **sase:** `src/sase/macros/split_file.md`, `Justfile` `_lint-toobig`, `docs/axe.md`,
  `docs/configuration.md`, and `src/sase/axe/chop_policy_snapshots.py` /
  `chop_policy_preflight.py`.
- **Measured repos:** sase-core, bob-cli, actstat, bob-plugins (`scripts/build-plugins.mjs`,
  `AGENTS.md`, `package.json`), and bob-mac-capture (`Package.swift`, `justfile`,
  `.github/workflows/ci.yml`).
- **athena** over SSH: `sase project list` and toolchain checks (2026-10-04).

**External:**

- **Linters and tools:**
  - [ESLint `max-lines`](https://eslint.org/docs/latest/rules/max-lines)
  - [SwiftLint `file_length`](https://realm.github.io/SwiftLint/file_length.html)
  - [SwiftLint `type_body_length`](https://realm.github.io/SwiftLint/type_body_length.html)
  - [Clippy lint index (`too_many_lines`)](https://rust-lang.github.io/rust-clippy/master/index.html)
  - [Clippy issue #16674](https://github.com/rust-lang/rust-clippy/issues/16674) and
    [PR #16675 `too_many_lines_in_file`](https://github.com/rust-lang/rust-clippy/pull/16675),
    a proposed restriction lint with a default of 1000 code lines
  - [pylint `too-many-lines` / C0302](https://pylint.readthedocs.io/en/latest/user_guide/messages/convention/too-many-lines.html)
    (default 1000)
  - [Sonar S104 discussion](https://community.sonarsource.com/t/suppressing-java-s104-long-class-file/101470)
    (default 1000)
  - [rustc tidy `style.rs`](https://doc.rust-lang.org/nightly/nightly-rustc/src/tidy/style.rs.html)
    (`ignore-tidy-filelength`)
- **Language references:**
  - [Rust test organization](https://doc.rust-lang.org/book/ch11-03-test-organization.html)
  - [Rust visibility and privacy](https://doc.rust-lang.org/reference/visibility-and-privacy.html)
  - [Swift access control](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/accesscontrol/)
  - [Google Swift style: source file structure](https://google.github.io/swift/#source-file-structure)
  - [Node package entry points](https://nodejs.org/api/packages.html#package-entry-points)
  - [Hagemeister, "The barrel file debacle"](https://marvinh.dev/blog/speeding-up-javascript-ecosystem-part-7/)
- **Research:**
  - [SWE-agent (NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/file/5a7c947568c1b1328ccc5230172e1e7c-Paper-Conference.pdf)
  - [Chroma, "Context Rot"](https://www.trychroma.com/research/context-rot)
  - [Koru et al., relative defect proneness](https://dl.acm.org/doi/10.1007/s10664-008-9080-x)
  - [Sjøberg et al. 2013, code smells vs. maintenance effort](https://www.sintef.no/publikasjoner/publikasjon/?pubid=CRIStin+1000293)
  - [Chowdhury, Uddin & Holmes, method size](https://arxiv.org/abs/2205.01842)
  - [CodeScene hotspots](https://codescene.io/docs/guides/technical/hotspots.html)
