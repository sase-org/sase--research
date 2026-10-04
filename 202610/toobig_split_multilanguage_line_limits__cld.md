# Extending `toobig_split` Beyond Python: Line Limits for Rust, JavaScript, and Swift

_Researcher: cld · 2026-10-04 · Measured against your actual repos, not generic folklore._

## Bottom Line

1. **The premise that Rust, JavaScript, and Swift need looser line limits than Python is
   mostly not supported by your own code.** Measured with the `o200k_base` tokenizer,
   all four languages in your repos carry nearly the same content per line: 7.7–8.5
   tokens/line, 32–40 bytes/line, and 71–73% "substantive" lines. Python spends its
   overhead on blank lines (14.5%); the brace languages spend theirs on closing-brace-only
   lines (15–17%). A 700-line file costs an agent about 5.4k–6.0k tokens in every
   language.
2. **Rust is the one real exception, for a structural reason, not a verbosity one:**
   inline `#[cfg(test)] mod tests` blocks. In Rust files over 700 lines that have them,
   they make up **33–36%** of the file. A raw trigger of **1000** for Rust therefore
   matches Python's 700 on non-test code.
3. **The numbers are the smallest part of the problem.** Today the job is Python- and
   sase-specific in at least six places: the `*.py` include, the `split_file` macro and
   its `just _lint-*` commands, the mission text, the shared `toobig-` clan, no
   exclusions, and no proposal cap. Three of your four target repos are not even SASE
   projects on athena, so the chop cannot target them as written.
4. **Recommended profiles** (details in [§7](#7-recommended-solution)):

| Profile                    | Trigger (info) | Warn | Hard | Split target | Initial backlog at trigger                    |
| -------------------------- | -------------: | ---: | ---: | -----------: | --------------------------------------------- |
| Python (sase, unchanged)   |            700 |  850 | 1000 |         ≤500 | 5                                             |
| **Rust**                   |       **1000** | 1250 | 1500 |     **≤700** | sase-core 146, bob-cli 68                     |
| **Swift**                  |        **700** |  850 | 1000 |     **≤500** | 18 (only 10 can be built/tested on Linux)     |
| **JavaScript** (bob-plugins) |      **700** |  850 | 1000 |     **≤500** | ~25 non-test + 22 test (excl. 2 generated)    |

5. **Is it a good idea? Yes, conditionally:** for sase-core and bob-cli (you are already
   running these splits by hand), and for bob-plugins and the Linux-buildable part of
   bob-mac-capture once the prerequisites are in place. It is a bad idea to point the
   current chop at those repos unchanged.

---

## 1. What `toobig_split` Actually Does Today

Traced through `sase_athena.yml` (chezmoi), `bugyi_chops/toobig_split.py` (bugyi-chops),
the vendored `toobig` 0.1.0 package, and `src/sase/macros/split_file.md` (sase):

- **Routine:** `axe.routines.run_every.jobs.toobig_split` runs on athena every 60 min,
  `for_each: {source: projects, names: [sase]}`, with vars
  `trees: [src, tests]` and `limits: ["1000", "850", "700"]`. It is inhibited while any
  agent clan matching `name_prefix: toobig-` is active.
- **Scan:** `toobig --files-only <tree> 1000 850 700`. `--files-only` prints every file
  that is not `OK`, so **the real trigger is the lowest (info) limit, 700, not 1000.**
  The 1000/850 tiers only affect report colouring here; they matter in sase's CI
  (`just lint` fails above 1000). `toobig` counts raw `\n` bytes (`wc -l` semantics) and
  defaults to `--include '*.py'`. The chop never passes `--include`.
- **Proposals:** the chop proposes **one agent per flagged file**, all in one sequential
  clan `toobig-@`, model `@medium`, no dedupe key. Order is path-sorted, not size-sorted.
  There is no cap. Each member carries a `%if` guard that runs `wc -l` again and admits
  only if the count is still `>= 700`.
- **Agent prompt:** `%auto #split_file:<path>` expands the sase built-in `split_file`
  macro: _"keep every resulting file at 500 lines of code or fewer"_, plus Python-only
  rules (facade re-exports, `_private` names, monkeypatch targets) and sase-only checks
  (`just _lint-symvision`, `just _lint-mypy`, `just _lint-toobig`,
  `sase tool run check`).

**So the "700 trigger / 500 target" regime has a 0.71 hysteresis ratio.** That ratio
matters as much as the absolute numbers: it stops a freshly split file from being flagged
again after a few edits. Keep it in every language.

## 2. Measurements From Your Repos

Repos measured: sase (Python, `src/` + `tests/`), **sase-core** and **bob-cli** (Rust),
**bob-plugins** (JS: `.js`/`.cjs`/`.mjs`; Obsidian plugins), **bob-mac-capture** (Swift,
SwiftPM). All counts are raw physical lines of git-tracked files on today's heads.

### 2.1 Size Distributions

| Repo (lang)             |  Files | p50 |   p90 |   p95 |    max |        >700 |       >1000 | >1500 |
| ----------------------- | -----: | --: | ----: | ----: | -----: | ----------: | ----------: | ----: |
| sase (py)               | 11,348 | 202 |   481 |   562 |    913 |       5 (0%) |           0 |     0 |
| sase-core (rs)          |    926 | 409 | 1,252 | 1,686 |  3,330 | 261 (28%) | 146 (16%) |    58 |
| bob-cli (rs)            |    395 | 499 | 1,202 | 1,632 |  2,204 | 139 (35%) |  68 (17%) |    26 |
| bob-plugins (js)        |    106 | 667 | 1,810 | 6,396 | 51,960 |  49 (46%) |          18 |    13 |
| bob-mac-capture (swift) |    115 | 185 | 1,062 | 2,111 |  6,541 |  18 (16%) |          13 |     8 |

sase's distribution was produced by the regime itself: p99 is 669 and there is a cliff at
700. The other repos show what code written by unregulated agents looks like. Applying
Python's 700 trigger to them as-is would flag 28–46% of their files.

### 2.2 Content Per Line Is the Same Across Languages (Key Finding)

| Repo (lang)     | tokens/line (o200k) | bytes/line | blank | closer-only (`}`, `)` …) | comment | substantive | ≈ tokens in 700 lines |
| --------------- | ------------------: | ---------: | ----: | -----------------------: | ------: | ----------: | --------------------: |
| sase (py)       |                7.82 |       34.0 | 14.5% |                     6.6% |    1.1% |       73.4% |                 5,477 |
| sase-core (rs)  |                7.66 |       33.7 |  5.9% |                    15.0% |    3.3% |       71.4% |                 5,365 |
| bob-cli (rs)    |                8.04 |       33.4 |  6.1% |                    14.8% |    3.8% |       72.9% |                 5,631 |
| bob-plugins (js) |               8.06 |       31.7 |  6.7% |                    17.1% |    3.8% |       72.4% |                 5,641 |
| bob-mac-capture (swift) |        8.53 |       39.5 |  8.7% |                    14.7% |    5.2% |       70.8% |                 5,970 |

"Substantive" means not blank, closer-only, comment, import/`use`, or attribute/decorator.
Tokens are from a sample of up to 600 files per repo. Generated `main.js` bundles are
excluded from the JS sample.

Interpretation: by the measure that matters most to an LLM agent (tokens it has to read
and keep in context), **a line is a line in all four languages.** Swift is slightly
_denser_, not looser. The intuition that "Rust/Swift/JS are more verbose, so allow more
lines" does not hold here. Python's blank-line habit and the brace languages'
closing-brace lines roughly cancel out.

### 2.3 Rust: Inline Unit Tests Are the Real Difference

| Repo      | Inline `#[cfg(test)] mod` lines (share of all .rs) | `tests/` + `*_tests.rs` lines | Source files >700 raw | …with inline tests | Inline-test share within those |
| --------- | --------------------------------------------: | ------------------------: | --------------------: | -----------------: | -----------------------------: |
| sase-core |                                    80,477 (16%) |                     27% |                   194 |                119 |                        **36%** |
| bob-cli   |                                    18,290 (8%) |                     41% |                    76 |                 36 |                        **33%** |

Counting only non-test lines in source files, the backlog roughly halves: sase-core 112 →
73 files over 1000, and bob-cli 39 → 27. The non-test equivalent of Python's 700 is about
**700 / (1 − 0.35) ≈ 1,050 raw lines**. That is the justification for a 1000 raw Rust
trigger.

### 2.4 How Your Earlier Rust Splits Turned Out

You have already run Rust split epics by hand: sase-core on 2026-09-20 and 2026-09-21 (20 split
commits), and bob-cli on 2026-09-29 and 2026-10-03 (15 or more). Measuring the resulting
trees:

- When the target was "≤1500" or "≤875", the largest resulting module was usually
  **700–1,250 lines**. Examples: agent_launch → 1,236; xprompt_catalog → 875; projects
  command → 766.
- When the instruction was only "focused/cohesive modules", the largest piece landed at
  **683–1,336** (bob-cli). Most sibling modules were 250–600 lines.

So agents splitting Rust for cohesion naturally produce modules of about 300–900 lines.
A ≤700 target is reachable without forcing artificial seams. A ≤500 target, Python's
number, would push into arbitrary cuts more often.

### 2.5 What the Python Regime Costs in sase

| Month (2026) | Commits | Split commits (subject match) | Share |
| ------------ | ------: | ----------------------------: | ----: |
| July         |   2,188 |                            57 |  2.6% |
| August       |   2,080 |                           155 |  7.5% |
| September    |   1,906 |                           266 | **14.0%** |

The average split commit is **+844 / −713 lines**. Python file count went from 577
(2026-03-01) to 11,348 (2026-10-04), while mean file length stayed between 191 and 236
lines and total size grew about 24× (to ≈2.69M lines). The regime holds file size steady,
but its cost scales with how fast agents add code: roughly one commit in seven is now a
split. Split quality looks good. Only one of the roughly 700 commit subjects mentioning "split" since August reads
like a non-semantic cut ("split `_macro_terminology_string_pairs_b` into early and late
shards"). Still, **expect a similar split share in every repo you enable**, in proportion
to how much code agents write there.

## 3. External Norms and Evidence

### 3.1 Tool Defaults

| Tool                | Language            | Rule                                                 | Default                                   |
| ------------------- | ------------------- | ---------------------------------------------------- | ----------------------------------------- |
| pylint              | Python              | `C0302 too-many-lines` (`max-module-lines`)          | **1000**                                  |
| SwiftLint           | Swift               | `file_length` (on by default)                        | **warn 400 / error 1000**                 |
| SwiftLint           | Swift               | `type_body_length` (extensions excluded)             | warn 250 / error 350                      |
| ESLint              | JS                  | `max-lines` (opt-in, not in `recommended`)           | 300 (options `skipBlankLines`, `skipComments`) |
| SonarQube           | Many                | S104 "Files should not have too many lines of code"  | **1000**                                  |
| Clippy (proposed)   | Rust                | `too_many_lines_in_file` (PR #16675, **still open**) | **1000** non-blank, non-comment lines     |
| Clippy              | Rust                | `too_many_lines` (per function)                      | 100                                       |
| rustc `tidy`        | Rust (rust-lang/rust) | file length, `// ignore-tidy-filelength` escape      | 3000                                      |

What stands out: **1000 is the de facto "error" line in every ecosystem you care
about.** pylint, SwiftLint's error tier, Sonar, and the proposed Clippy lint all use it.
sase's hard limit of 1000 already sits on that line. Your 700 trigger and 500 target are
deliberately stricter than any default except ESLint's opt-in 300 and SwiftLint's warning
tier of 400. Note also that rustc's own `tidy` requires unit tests in separate
`tests.rs` files for library and compiler crates, so pulling inline tests out is
idiomatic at scale, not an oddity.

### 3.2 Research Worth Knowing (and What It Does Not Say)

- **Agents and context size:** SWE-agent's ablation found a 100-line file viewer beat
  showing the whole file (18.0% vs 12.7% on their SWE-bench subset); 30 lines was too
  little (14.3%). Chroma's _Context Rot_ study (July 2025, 18 models) found accuracy
  dropping steadily as input length grows, even on simple tasks. Together these support
  keeping the code an agent must load focused. They do **not** pin down a magic file
  size, because modern agents read in windows anyway.
- **File size is not a quality metric:** Koru et al.'s Theory of Relative Defect
  Proneness, replicated on 10 open-source and 10 closed-source products, finds defect
  counts grow _slower_ than size. Smaller modules are proportionally _more_
  defect-prone. Justify splitting on agent ergonomics and merge contention, not on
  "smaller files have fewer bugs".
- **Language-specific split costs:**
  - **Swift:** `private`/`fileprivate` are file-scoped. Moving code into another file
    means widening access to `internal`. Swift's convention is one primary type per file,
    plus `Type+Concern.swift` extension files (Google Swift Style Guide).
  - **JS:** barrel/re-export files measurably slow tooling (Hagemeister, "The barrel file
    debacle"). Don't carry the Python "facade" pattern over to ESM codebases.
  - **Rust:** each top-level file in `tests/` compiles as a separate crate and binary.
    Split integration tests into `tests/<name>/main.rs` plus submodules, not into new
    top-level files (your bob-cli `tests/cli/` split already did this).

## 4. Per-Language Analysis

### Rust (sase-core, bob-cli)

- **Cheapest and safest language to split.** The compiler checks every visibility and
  path change. Child modules can see their parent's private items, and `impl` blocks can
  be spread across child modules. A type can keep its private fields in the parent while
  `foo/render.rs`, `foo/parse.rs`, and so on hold `impl Foo` blocks with `pub(super)`
  helpers.
- **The first remedy should be test extraction.** Convert `foo.rs` to
  `#[cfg(test)] mod tests;` plus `foo/tests.rs`. It is mechanical and safe, and agents
  editing production code stop paying for test tokens. In about half of flagged files
  that alone is close to enough.
- **Thresholds:** 1000 / 1250 / 1500 raw, target ≤700. This equals Python's 700/500 on
  non-test code (§2.3) and matches the cohesion sizes your agents already produce
  (§2.4).
- **Caveat:** once most inline tests have moved out, raw counts approach non-test counts
  and a 1000 trigger becomes looser than Python. **Reassess after about six weeks.** If
  test extraction has become the norm, tighten to roughly 850 / 1000 / 1250, target ≤600.

### Swift (bob-mac-capture)

- Per-line density is the highest of the four (8.53 tokens/line), so there is no case
  for a looser limit. Use Python's numbers. The 1000 hard limit equals SwiftLint's
  default error tier.
- **Splitting has a real encapsulation cost** (file-scoped `private`). The split prompt
  must prefer type-boundary splits and must widen only to `internal`, never `public`.
- **Showstopper for running on athena:** `Package.swift` builds the AppKit targets
  (`BobMacCapture`, `BobMacCaptureTests`) **only on macOS**. On Linux only `CaptureCore`
  builds and tests. **8 of the 18 files over 700 lines** (including `CapturePanelModel`
  at 5,081 lines and `CapturePanelModelTests` at 6,541) cannot be compiled by an agent on
  athena. Either scan only `Sources/CaptureCore` and `Tests/CaptureCoreTests` from
  athena, or dispatch Swift split agents to the mac.
- Upside: SwiftPM discovers new files automatically, so there is no `project.pbxproj`
  editing.

### JavaScript (bob-plugins)

- Obsidian loads a single CommonJS `main.js`, and this repo deliberately has no bundler.
  **As of today you already have a JS-specific split mechanism:**
  `scripts/build-plugins.mjs` concatenates ordered `src/*.js` fragments, listed in
  `src/fragments.json` and sharing one script scope, into a generated `main.js`. It
  enforces `MAX_FRAGMENT_LINES = 1000`. Two plugins were migrated today.
- Implications:
  - (a) The two **generated** `main.js` files (20,502 and 12,119 lines) **must be
    excluded**. As written, the chop would send an agent to hand-edit a generated file,
    which the repo's AGENTS.md forbids.
  - (b) Splitting a fragment is the cheapest split anywhere: cut at top-level declaration
    boundaries and insert into the manifest. There are no imports to rewire, but
    `const`/`class` declaration order matters across fragments.
  - (c) The build's 1000 cap is the natural hard limit. Use 700/850 below it so fragments
    are split before they break the build.
  - (d) `bob-navigation-hotkeys/main.js` (**51,960 lines**, hand-edited) and
    `block-id-prompt/main.js` (6,880) need a one-off migration to the fragment build,
    like today's two migrations. That is an epic, not a routine `@medium` agent.
  - (e) Test `.cjs` files are huge (`test-navigation-hotkeys.cjs` is 19,813 lines), and
    `package.json`'s `test` script lists every test file explicitly. The split prompt
    must add new test files to it.
- About 21 of the 56 fragments are already between 700 and 981 lines, because today's
  migration aimed at ≤1000. If re-splitting them right away feels wasteful, start JS at
  850 for a few weeks. The proposal cap (§7) also spreads the work out.

## 5. Critique: Is This a Good Idea?

### What Is Right About It

- **You are already doing this by hand.** There were 20 or more split commits in
  sase-core in September and 15 or more in bob-cli this week, from `#split_epic` runs.
  Automating that with hysteresis is a natural step.
- **The repos are hot.** In the last 30 days: sase-core 527 commits, bob-cli 234,
  bob-plugins 99, bob-mac-capture 94. With about 20 parallel workspaces, large hot files
  both burn tokens on every read and attract merge conflicts.
- **The mechanism is sound:** sequential clans, a `%if` re-check at admission, and a
  clan inhibit. The sase data shows it produces mostly semantic splits.

### What Is Wrong or Risky About the Plan as Stated

1. **The question is framed as "which number?" when the real gap is "which pipeline?"**
   The include glob, the split macro, the verification commands, and the mission text
   are all Python- and sase-specific. Calling `%auto #split_file:` on a `.rs` file asks
   an agent to apply Python facade and `_private` rules and to run `just _lint-mypy`,
   which does not exist in sase-core.
2. **Target model mismatch:** the chop resolves a SASE _project_ (`workspace_dir` plus a
   launch workspace). On athena **only `actstat`, `bob-cli`, and `sase` are projects.
   sase-core, bob-plugins, and bob-mac-capture are linked repos**, which
   `sase project show` rejects. Either register them as projects or teach the chop to
   launch into a linked repo. The `%if` guard's relative path must resolve in the agent's
   workspace either way.
3. **No proposal cap and no prioritisation:** at the recommended Rust trigger, sase-core
   alone would produce a **146-member** sequential clan, ordered by path. While that clan
   is alive, the `toobig-` inhibit blocks new scans.
4. **The shared clan prefix may couple projects.** `CLAN_TEMPLATE = "toobig-@"` is
   hard-coded, and `inhibit_if.agent_clan.name_prefix: toobig-` matches clan metadata on
   active agents. The docs do not say it is scoped per project. If it is global, a
   two-week Rust backlog would freeze sase's Python splits. Verify this, or use
   per-profile prefixes in any case.
5. **No exclusions, no allow-pragma, no failure memory:**
   - Generated files get proposed.
   - Intentionally large files (grammar tables, parity fixtures) cannot opt out, the way
     `// ignore-tidy-filelength` allows in rustc.
   - A file an agent fails to split is proposed again every 60 minutes forever.
6. **Host platform:** the Swift problem in §4.
7. **Copying 700/500 everywhere means copying its churn.** In sase it now accounts for
   14% of commits. That is acceptable if the agent-ergonomics win is real, but **nobody
   has measured it.** Add outcome metrics before scaling up (§7.4).
8. **Minor off-by-one:** `toobig` flags `> 700`, but the admission guard admits
   `>= 700`. It is harmless today, but keep the two consistent when the guard is
   generalised.

### What I Would Do Differently

- **Treat it as language profiles, not language limits.** Each profile is: include and
  exclude globs, thresholds, split macro, verify command, and build host.
- **Prioritise by hotspot, not by size alone.** Order candidates by
  `lines × commits touching the file in the last 30 days` (Tornhill's "hotspot" idea in
  _Your Code as a Crime Scene_), and cap proposals per scan. A cold 3,000-line grammar
  file costs almost nothing; a 1,100-line file edited 40 times a week costs a lot. With a
  cap and hotspot ordering, you don't need a manual threshold ramp: the worst files go
  first and the backlog drains at a controlled rate.
- **Route outliers to epics.** Files above about 4× the hard limit (the 51,960-line
  `main.js`, the 5–6.5k-line Swift files) should become a one-time `#split_epic`, not a
  `@medium` routine agent.
- **For low-churn repos, consider a ratchet instead:** a lint that says "a file over the
  limit may not grow" (baseline file), with splits done only when someone touches the
  file. That fits bob-mac-capture better than a 60-minute routine.

## 6. Requirement Adjustments (Explicitly Called Out)

> **ADJ-1 — Reframe the deliverable.** The request asks for per-language _line limits_. I
> changed it to per-language _profiles_, because the split macro, the verify command, the
> exclusions, and the build host decide whether the job works. The limit decides only how
> much work it creates.
>
> **ADJ-2 — Do not loosen limits for Swift or JS.** The request assumes these languages
> need different limits than Python's. The data says they don't (§2.2). Only Rust gets a
> raw-line allowance, and only to account for inline tests.
>
> **ADJ-3 — Add a per-scan proposal cap with hotspot ordering.** Not requested, but
> required. Otherwise enabling Rust queues 146 or more sequential agents in one clan.
>
> **ADJ-4 — Add exclusions, an allow-pragma, and failure backoff.** Not requested, but
> required for bob-plugins (generated `main.js`). Also needed to stop infinite
> re-proposals of files agents can't split.
>
> **ADJ-5 — Restrict Swift to Linux-buildable targets, or dispatch to the mac.** Not
> requested, but required, because the routine host can't compile the AppKit targets.
>
> **ADJ-6 — Register the target repos as SASE projects, or extend the chop to target
> linked repos.** A prerequisite you probably haven't hit yet.
>
> **ADJ-7 — Handle giant outliers (more than about 4× the hard limit) as one-off epics,
> outside the routine.**
>
> **ADJ-8 — Don't add CI hard gates in the new repos until each backlog has drained.**
> sase's own design already keeps `toobig` out of `just check`. Mirror that, then
> optionally add a `just lint` gate later to prevent regression.

## 7. Recommended Solution

### 7.1 Profiles

| Profile    | Scan roots                                                                                                     | Count                                                        | Limits (`line warn info`) | Split target                                       | Split macro                                        | Verify                                                                   | Host                                     |
| ---------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------- | -------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------ | ---------------------------------------- |
| `python`   | sase `src`, `tests`                                                                                            | raw                                                          | `1000 850 700`            | ≤500                                               | `split_file` (existing)                            | existing                                                                 | athena                                   |
| `rust`     | sase-core `crates`; bob-cli `src`, `tests`                                                                     | raw                                                          | `1500 1250 1000`          | ≤700 (reassess to 850/600 after about six weeks)    | new `split_rust_file`                              | `cargo fmt`, `cargo clippy --all-targets`, `cargo test` (or repo `just check`) | athena                                   |
| `swift`    | `Sources/CaptureCore`, `Tests/CaptureCoreTests` (athena); all of `Sources` and `Tests` only if dispatched to mac | raw                                                          | `1000 850 700`            | ≤500                                               | new `split_swift_file`                             | `swift build`, `swift test` (repo `just test`)                           | athena (Core) / mac (AppKit)             |
| `js-bob`   | `plugins/*/src`, hand-edited `plugins/*/main.js`, `scripts`                                                    | raw; **skip generated** (`// Generated` / `@generated` header) | `1000 850 700`            | ≤500                                               | new `split_js_fragment`                            | `npm run build`, `npm test`                                              | athena                                   |

Every profile keeps the ~0.7 target-to-trigger ratio.

### 7.2 Code and Config Changes

**`toobig` (your package):**

- Add `--exclude GLOB`, repeatable.
- Skip files carrying an `@generated` marker in the first few lines; rustfmt uses the
  same convention. Then add `@generated` to `build-plugins.mjs`'s header.
- Honour an in-file allow pragma such as `toobig: allow-file-length`, modelled on
  `ignore-tidy-filelength`, and list allowed files in the report so they stay visible.

**`bugyi_chops/toobig_split.py`:**

- New vars: `include`, `exclude`, `split_macro` (replaces the hard-coded `#split_file`),
  `clan_prefix` (replaces `toobig-@`), `max_proposals` (default 3; start at 1 for a new
  profile), `order: hotspot|size`, `max_file_lines` (above it, emit a notification
  recommending `#split_epic` instead of proposing), and `model`.
- Failure backoff: record per-file attempts in the job state dir, and skip a file for N
  days after K attempts in which the file did not drop below the trigger.
- Make the mission text language-neutral.
- Make the `%if` floor use `>` to match `toobig`.

**Config sketch** (map-form jobs in `sase_athena.yml`; each profile gets its own job and
clan prefix):

```yaml
toobig_split_rust:
  script: bugyi_chop_toobig_split
  description: |-
    Propose split-file agents for oversized Rust files

    ...
  run_every: 60m
  inhibit_if:
    agent_clan: { name_prefix: toobig-rs- }
  for_each:
    source: projects
    names: [sase-core, bob-cli] # requires ADJ-6
  vars:
    trees: [crates, src, tests]
    include: ["*.rs"]
    limits: ["1500", "1250", "1000"]
    split_macro: split_rust_file
    clan_prefix: toobig-rs-
    max_proposals: 2
    order: hotspot
    max_file_lines: 6000
```

### 7.3 What Each New Split Macro Must Say (Essentials)

- **`split_rust_file`:**
  - Target ≤700 lines per resulting file.
  - **Step 1:** if an inline `#[cfg(test)] mod tests { … }` exceeds about 150 lines, move
    it to `foo/tests.rs` via `#[cfg(test)] mod tests;`. Re-measure before going further.
  - Split by responsibility into child modules. Keep types and private fields in the
    parent and move `impl` blocks into children. Prefer `pub(super)` or `pub(crate)` over
    `pub`. Don't change the crate's public API; re-export with `pub use` only items that
    were public before.
  - In `tests/`, never add new top-level files. Use `tests/<name>/main.rs` plus
    submodules.
  - Run the repo's fmt, clippy, and test commands.
- **`split_swift_file`:**
  - Target ≤500.
  - Split along type boundaries first (one primary type per file), then extensions by
    concern as `Type+Concern.swift`.
  - Move private helpers together with their only users. Widen access only to
    `internal`, never to `public` or `open`, and list every widened symbol in the final
    message.
  - Split XCTest classes by behaviour area, with shared fixtures in one helper.
  - Run `swift build` and `swift test` for the affected targets. On Linux, refuse to
    touch macOS-only targets.
- **`split_js_fragment`** (bob-plugins):
  - Target ≤500.
  - Edit only `src/` fragments, never a generated `main.js`.
  - Cut at top-level declarations into new numbered fragments, inserted into
    `fragments.json` in load order. Watch `const`/`class` ordering across fragments.
  - For test `.cjs` files, split by behaviour and add new files to `package.json`'s
    `test` script.
  - Run `npm run build` and `npm test`.
  - For ESM projects (none yet): use direct imports and no barrel files.

### 7.4 Rollout and Success Metrics

1. **Week 0 (prerequisites):** ADJ-6 (projects), the toobig/chop changes, and the three
   macros. Fix the clan-prefix scoping.
2. **Week 1:** enable `rust` on **bob-cli** with `max_proposals: 1`. Review the first five
   or so splits yourself, then raise to 2–3 and add **sase-core**. At sase's observed rate
   of about 9 splits/day, sase-core's 146-file backlog takes roughly 2–3 weeks of lane
   time.
3. **Week 2:**
   - Enable `js-bob` once bob-navigation-hotkeys and block-id-prompt have been moved onto
     the fragment build via `#split_epic`.
   - Enable `swift` on CaptureCore only.
   - Run a one-off epic for the AppKit files, on the mac.
4. **After about six weeks:** compare, per repo, before and after:
   - split commits as a share of all commits;
   - re-split rate (files flagged again within 30 days of a split);
   - split-agent failure or abandon rate;
   - merge conflicts on recently split files;
   - tokens per agent task in the repo, if your usage data allows.

   Then tighten Rust if test extraction has become the norm, or loosen everything if the
   churn isn't buying anything measurable.

---

## Appendix A: Method

- Distributions: `git ls-files` per repo, newline-byte counts identical to `toobig` and
  `wc -l`. sase limited to `src/` and `tests/`; bob-plugins includes `.js`, `.cjs`, and
  `.mjs`.
- Token density: `tiktoken` `o200k_base` over all files (or a 600-file random sample for
  sase and sase-core). Line categories use simple per-language regexes: blank,
  closing-delimiter-only, line comment, import/`use`, attribute/decorator. Python
  docstrings count as substantive, so Python's substantive share is if anything
  overstated.
- Rust inline tests: the first top-level `#[cfg(test)]` followed by `mod <name> {`,
  counted to end of file. Files under `tests/` or named `*_tests.rs` / `tests.rs` count
  as test files.
- Split churn: sase `git log` subjects matching split patterns. This is approximate, and
  it includes manual and epic-driven splits as well as routine ones.
- Earlier split outcomes: the post-commit line counts of every `.rs` file added or
  changed by `refactor: split …` commits in sase-core and bob-cli.
- Project status: `sase project show <name> --json` on athena.

## Appendix B: Sources

- Local:
  - `sase_athena.yml` (chezmoi): `toobig_split` job.
  - `bugyi_chops/toobig_split.py` (bbugyi200/bugyi-chops).
  - `toobig` 0.1.0 (`cli.py`, `core.py`, `scanner.py`).
  - `src/sase/macros/split_file.md`, `Justfile` (`_lint-toobig`), `docs/axe.md`.
  - bob-plugins `scripts/build-plugins.mjs` and `AGENTS.md`.
  - bob-mac-capture `Package.swift`.
- [SwiftLint `file_length` reference](https://realm.github.io/SwiftLint/file_length.html)
- [SwiftLint `type_body_length` reference](https://realm.github.io/SwiftLint/type_body_length.html)
- [SwiftLint `function_body_length` reference](https://realm.github.io/SwiftLint/function_body_length.html)
- [ESLint `max-lines`](https://eslint.org/docs/latest/rules/max-lines)
- [pylint `too-many-lines` / C0302](https://pylint.readthedocs.io/en/latest/user_guide/messages/convention/too-many-lines.html)
- [Sonar S104 discussion (sonar-dotnet #396)](https://github.com/SonarSource/sonar-dotnet/issues/396)
- [Sonar community: S104 default 1000](https://community.sonarsource.com/t/suppressing-java-s104-long-class-file/101470)
- [Clippy PR #16675: `too_many_lines_in_file`](https://github.com/rust-lang/rust-clippy/pull/16675) (open as of 2026-10-04)
- [Clippy issue #16674](https://github.com/rust-lang/rust-clippy/issues/16674)
- [rustc tidy `style.rs`](https://doc.rust-lang.org/nightly/nightly-rustc/src/tidy/style.rs.html)
- [rust-lang/rust #60302: split up `ignore-tidy-filelength` files](https://github.com/rust-lang/rust/issues/60302)
- [rustc-dev-guide coding conventions](https://rustc-dev-guide.rust-lang.org/conventions.html)
- [rustc tidy `unit_tests.rs`](https://doc.rust-lang.org/stable/nightly-rustc/src/tidy/unit_tests.rs.html)
- [rustc-dev-guide: testing](https://rustc-dev-guide.rust-lang.org/tests/intro)
- [Yang et al., SWE-agent (NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/file/5a7c947568c1b1328ccc5230172e1e7c-Paper-Conference.pdf)
- [Chroma, "Context Rot: How Increasing Input Tokens Impacts LLM Performance"](https://www.trychroma.com/research/context-rot)
- [Koru et al., "Theory of relative defect proneness"](https://dl.acm.org/doi/10.1007/s10664-008-9080-x)
- [Testing the theory of relative defect proneness for closed-source software](https://link.springer.com/article/10.1007/s10664-010-9132-x)
- [Koru et al., functional form of the size-defect relationship](https://www.semanticscholar.org/paper/An-Investigation-into-the-Functional-Form-of-the-Koru-Zhang/8ff5dc32ea842244d8663743853cba685769768b)
- [Google Swift Style Guide](https://google.github.io/swift/)
- [SwiftLee: fileprivate vs private](https://www.avanderlee.com/swift/fileprivate-private-differences-explained/)
- [Hagemeister, "The barrel file debacle"](https://marvinh.dev/blog/speeding-up-javascript-ecosystem-part-7/)
- Adam Tornhill, _Your Code as a Crime Scene_ (Pragmatic Bookshelf): hotspot analysis,
  cited from memory, not fetched.
- Alex Kladov, "Delete Cargo Integration Tests" (matklad.github.io, 2021): one
  integration-test crate, cited from memory, not fetched.
