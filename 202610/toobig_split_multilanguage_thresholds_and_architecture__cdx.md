# Expanding toobig_split: language thresholds, architectural risks, and a safer rollout

Researcher: **cdx**  
Research date: **2026-10-04**  
Scope: independent research for the Rust, JavaScript, and Swift expansion; no peer reports or peer findings were consulted.

## Decision in brief

Extend the job's **detection and prioritization** to other projects, but first change its contract from “split everything above a line count” to “evaluate oversized files and make a justified, behavior-preserving refactor.” Use language-specific starter thresholds, then calibrate them against each project's actual files and review outcomes.

My proposed initial policy uses the existing scanner's **physical newline count**, including comments, blank lines, and inline tests:

| Language | Start architectural review when file exceeds | Preferred size after a justified split | Practical target range | Scanner tuple: hard / warning / informational |
| --- | ---: | ---: | ---: | --- |
| Python in sase, existing policy | 700 | 500 | Existing requirement | `1000 / 850 / 700` |
| Rust | **1,000** | **600** | 400–700 | **`1500 / 1250 / 1000`** |
| JavaScript, including JSX | **600** | **350** | 250–400 | **`900 / 750 / 600`** |
| Swift, including SwiftUI | **700** | **400** | 300–500 | **`1000 / 850 / 700`** |

The three new rows are **my proposed operational defaults**, not experimentally established language limits. “Target” is a soft preference, not an obligation to split every output below that number. The scanner's first threshold still determines its exit status; during the pilot, treat that status as a finding requiring classification, not a newly enabled CI failure. A file above even the highest threshold can receive a documented exception if it is cohesive and a split would make it worse. Existing project rules take precedence unless deliberately reconciled.

## What the current job actually does

I inspected the real configuration and implementations rather than assuming that only the numbers needed changing.

- The chezmoi configuration targets `sase`, scans `src` and `tests`, uses `1000 / 850 / 700`, runs every 60 minutes, and inhibits overlapping `toobig-` groups. Its description explicitly says the split proposals have no dedupe key. [Configuration at the inspected revision](https://github.com/bbugyi200/dotfiles/blob/64246fcb16504bb3bef654f93e85df288cf94e7a/home/dot_config/sase/sase_athena.yml#L36).
- `bugyi_chops.toobig_split._scan_files` invokes `toobig --files-only <tree> <limits>` without `--include`. `build_result` proposes a sequential agent for every returned file; admission rechecks the minimum configured threshold, and the prompt always ends with `%auto #split_file:<path>`. Therefore **adding Rust, JavaScript, or Swift project names alone will still scan only Python files**. [Job implementation, inspected revision](https://github.com/bbugyi200/bugyi-chops/blob/8cbc4dec6980d283530d6589984a5cb8fdd92155/src/bugyi_chops/toobig_split.py#L289).
- The built-in `split_file` macro describes a Python source file, requires every result to have at most 500 lines of code, imposes Python import/privacy conventions, and invokes Python-specific lint stages. It is not a language-neutral refactor contract. [Current macro](https://github.com/sase-org/sase/blob/763cc9fca334c8d2009789f368ef01aa9f40debe/src/sase/macros/split_file.md).
- sase's lint recipe uses the same scanner limits. Thus 700 is the early screening floor, **not** the hard lint failure limit; a Python file exceeds the hard limit only above 1,000. [Current lint recipe](https://github.com/sase-org/sase/blob/763cc9fca334c8d2009789f368ef01aa9f40debe/Justfile#L404).

`toobig` itself already accepts repeated basename globs such as `*.rs`, `*.js`, `*.jsx`, and `*.swift`. It counts newline bytes like `wc -l`, applies strict `>` comparisons, recursively visits hidden directories, does not follow symlinks, and does not apply `.gitignore`. Its current CLI has no exclude option. The job wrapper needs additional selection policy even though the scanner already supports other languages. [Scanner](https://github.com/bbugyi200/toobig/blob/79ee94bcde279511ed3f670c8a8c8d490aa05fb5/src/toobig/scanner.py), [CLI](https://github.com/bbugyi200/toobig/blob/79ee94bcde279511ed3f670c8a8c8d490aa05fb5/src/toobig/cli.py), [threshold implementation](https://github.com/bbugyi200/toobig/blob/79ee94bcde279511ed3f670c8a8c8d490aa05fb5/src/toobig/core.py#L62).

There is a small boundary inconsistency worth resolving during any implementation: initial scanning uses `> floor`, while queued admission uses `>= floor`. A file scanned at 701 lines and later reduced to exactly 700 can still be admitted. That is verified source behavior, not a claim that it breaks the existing intended contract. I recommend making both comparisons strictly `>` and documenting it.

I also ran a temporary-file smoke experiment with the installed `toobig 0.1.0`. The default scan returned only the 701-line `.py` file; explicit Rust, JSX, and Swift globs returned only their corresponding files above the proposed informational thresholds. Files exactly at the threshold were omitted. All four scans exited 0 because none exceeded the hard threshold. The files contained comment-only text, which confirmed that these are physical counts, not code-only counts. This experiment verified scanner mechanics, not architectural quality or the proposed thresholds' effectiveness.

## What external evidence supports—and what it cannot establish

### Linter defaults provide useful anchors, not universal limits

| Primary source | Documented default and measurement scope | Implication for this decision |
| --- | --- | --- |
| [ESLint `max-lines`](https://eslint.org/docs/latest/rules/max-lines) | A configured rule defaults to 300 lines per file. It can skip blank and comment-only lines. The documentation explicitly acknowledges that no objective maximum exists. | A JavaScript target around a few hundred lines is defensible. A rule's configured default does not imply all JavaScript projects enable it. |
| [ESLint `max-lines-per-function`](https://eslint.org/docs/latest/rules/max-lines-per-function) | Defaults to 50 lines per function, with separate blank/comment options. | Function size should be considered independently of file size. |
| [SwiftLint `file_length`](https://realm.github.io/SwiftLint/file_length.html) | Enabled by default; warning 400, error 1,000; `ignore_comment_only_lines` defaults to false. | Swift has an established ecosystem convention for early warning plus a much higher failure limit. |
| [SwiftLint `type_body_length`](https://realm.github.io/SwiftLint/type_body_length.html) | Warning 250, error 350; default excluded types include extensions and protocols. Examples exclude comments and empty lines from body measurements. | A file-only job misses large-type design problems, and moving methods into extensions can satisfy a metric without improving design. |
| [SwiftLint `function_body_length`](https://realm.github.io/SwiftLint/function_body_length.html) | Warning 50, error 100; examples ignore comments and empty lines. | Review large functions even in modestly sized Swift files. |
| [Clippy `too_many_lines`](https://rust-lang.github.io/rust-clippy/stable/index.html#too_many_lines) | A pedantic, allow-by-default lint with a configured threshold of 100 lines **per function or method**. | This does not justify a 100-line Rust file limit. I found no universal Rust file ceiling in the consulted official documentation. |

These measures differ. A Swift type-body count, an ESLint file count configured to ignore comments, and `toobig`'s newline count cannot be copied into one configuration as though they were interchangeable. Also, a linter error threshold represents a project's chosen policy; it does not show that an automatic split at that threshold will improve maintainability.

### Empirical work supports size-aware review, with substantial limits

Sjøberg and colleagues' 2013 study hired six developers to perform maintenance on four functionally equivalent Java systems. Across 298 modified files, none of 12 examined smells independently predicted higher effort after adjusting for size and changes; file size and change count explained much of the modeled effort. That supports paying attention to size and activity. It does **not** establish a causal benefit from moving unchanged code into more files, nor any Rust, JavaScript, or Swift line threshold. [Author-institution publication record and abstract](https://www.sintef.no/publikasjoner/publikasjon/?pubid=CRIStin+1000293).

Chowdhury, Uddin, and Holmes studied roughly 785,000 Java methods and reported evidence favoring methods under 24 lines, including lower maintenance measures following decomposition. That is relevant to the value of smaller functional units, but **Java methods are not JavaScript files**, and neither a 24-line file ceiling nor a universal language multiplier follows from the finding. [Research paper abstract](https://arxiv.org/abs/2205.01842).

Oliveira, Valente, and Lima's 2014 threshold research describes heavy-tailed source metrics and derives relative thresholds from 106 Java systems. It explicitly tolerates a minority of entities beyond the threshold. My inference is that a healthy file-size policy should accommodate explained outliers and use project distributions for calibration. The paper does not validate the specific percentile or file thresholds suggested here. [Author-hosted paper](https://homepages.dcc.ufmg.br/~mtov/pub/2014_csmrwcre_thresholds.pdf).

CodeScene's current documentation prioritizes unhealthy code with frequent changes and considers change coupling and coordination cost. This is vendor methodology, not independent proof of the numerical defaults above, but it provides a useful operational alternative to processing the longest files first. [CodeScene hotspot methodology](https://codescene.io/docs/guides/technical/hotspots.html).

**Evidence conclusion:** file size is a useful, cheap screening signal. The reviewed evidence does not supply scientifically defensible conversion ratios from Python's 700/500 to the other languages. Exact initial numbers require engineering judgment and local validation.

## Why these starter numbers

### Rust: review above 1,000; aim near 600

Rust unit tests conventionally live in a `#[cfg(test)]` child module in the same source file and can exercise private interfaces. Integration tests are separate and exercise public interfaces. Consequently a raw file count can combine implementation and substantial, legitimate test coverage. [Official Rust test organization](https://doc.rust-lang.org/book/ch11-03-test-organization.html).

My 1,000-line floor gives that combined physical representation more room than the Python policy. It is not a claim that Rust is precisely 1.43 times as verbose. The 600 target leaves growth room while avoiding a requirement to fragment every type and its closely related implementations. A Rust file with 450 implementation lines and 650 coherent test lines should receive a different assessment from one with 1,100 lines of unrelated production responsibilities.

Moving tests to a source child-module file can be reasonable while preserving privacy and test organization. Moving them wholesale into `tests/` is a different change and should not be done merely to improve the counter. Separate production and inline-test counts can be added later if this repeatedly causes poor proposals; do not make an AST-aware test classifier a prerequisite for a small pilot.

### JavaScript: review above 600; aim near 350

The proposed target is near ESLint's documented few-hundred-line file convention. The higher screening floor reserves scheduled agent work for more conspicuous candidates, rather than launching a refactor whenever an optional style rule warns.

Use the same initial policy for `.js`, `.mjs`, `.cjs`, and `.jsx`, and for TypeScript/TSX only if those are actually present and explicitly included. Project role matters: a rendering component, a CLI command, a dense algorithm, and a large declarative schema can have very different appropriate boundaries. If JSX causes repeated false positives, create a justified project/profile override after examining the examples; do not assume JSX universally deserves a large exemption.

The 350 target is a preference for cohesive modules, not a recommendation to turn one component into ten forwarding wrappers. Preserve meaningful relationships among state, rendering, and event handling.

### Swift: review above 700; aim near 400

A 400 target follows the SwiftLint file-warning anchor; 700 is my more conservative threshold for spending agent and reviewer time, below the documented 1,000 error threshold. Keeping Python and Swift's review floor equal is deliberate: different languages do not require different numbers in every case.

Google's Swift guide generally prefers one top-level type per file but permits related helper types and protocols together, including for file-private encapsulation. That favors cohesive boundaries over strict arithmetic splitting. [Google Swift file structure guidance](https://google.github.io/swift/#source-file-structure).

For SwiftUI, prefer meaningful view or model responsibilities when extraction is beneficial. Do not assume that a line-count improvement proves a rendering or compile-time improvement; any such claim needs measurement on the actual project and toolchain. If the existing SwiftLint configuration is already stricter, align the post-refactor acceptance policy with it or document a deliberate exception.

## Critique of the expansion plan

The idea is good as recurring maintenance triage. It is incomplete as unconditional scheduled splitting.

Potential benefits are straightforward: oversized files become visible, unnoticed growth is caught early, and cohesive extraction can improve navigation, ownership, isolated testing, and the amount of relevant code a reviewer or agent must inspect. These are reasons to pilot the workflow, not guarantees attached to a particular line count.

The main risk is **optimizing a representation metric instead of design**. Four 250-line files can be harder to maintain than one cohesive 1,000-line file if each change must touch all four. A split adds imports, new interfaces, naming decisions, and opportunities for initialization or visibility changes. Public re-export facades may preserve compatibility while adding navigation cost. A smaller file is insufficient evidence of success.

Other specific risks are:

1. **Unnecessary churn:** a stable, well-understood file may offer little benefit relative to review, conflict, and regression cost. Prioritize files that are actively hard to change.
2. **Changed encapsulation:** Rust module boundaries and Swift file boundaries affect access. A mechanically successful compile can conceal an undesirable expansion of internal interfaces.
3. **Incomplete discovery:** the current default glob misses non-Python files; recursive scanning also includes ignored build and dependency directories unless selection explicitly prevents it.
4. **Repeated work:** with an hourly scan and no persisted “retain this file” decision, a cohesive exception can repeatedly consume agent time. The current admission size recheck helps stale candidates but does not handle unchanged rejected candidates.
5. **Misleading success measures:** lowering the maximum file length or increasing the number of split commits says little about whether changes became easier.
6. **Test fragmentation:** test files, embedded tests, fixtures, and snapshots have different structures and should not be scheduled for splitting as though they were ordinary production modules.

A single shared 700/500 rule would be easy to explain, and its simplicity is a credible alternative for small, consistently organized projects. I prefer three starter profiles because inline Rust tests and ecosystem conventions create practical differences. I would still choose project evidence over a language table whenever they disagree.

## Explicit adjustments to the requirements

The following changes are intentional departures from merely choosing replacement line limits.

**A1 — Separate detection from editing.** Crossing the floor admits a review, not an instruction that a split must happen. Allow outcomes `split`, `retain with reason`, and `defer for a concrete prerequisite`. A retained file is a completed assessment, not a failed maintenance run.

**A2 — Make the counter explicit and targets soft.** Keep physical newline counting for the first rollout so scanning, admission, and results are comparable. Name it `newline_count`, not ambiguously “lines of code.” Normal formatter output should remain intact; deleting comments, blank lines, or compressing statements is not an acceptable remediation. Aim for the recommended target when cohesive boundaries support it, but allow a larger result with an explanation.

**A3 — Add project selection before enabling more names.** Introduce explicit language globs and source roots. Use an allowlist of authored, version-controlled source paths or equivalent vetted filtering, then exclude generated and vendored material. Relevant examples include `node_modules`, `dist`, Rust `target`, Swift `.build`, Pods, Carthage output, generated clients, and test snapshots. Curated source roots alone are adequate only when they contain no such material. The current scanner lacks exclusion and git-aware selection; configuration that assumes these capabilities would be misleading.

**A4 — Replace the Python-only execution contract.** Dispatch a language-aware refactor prompt with the actual target, API and encapsulation constraints, project conventions, and verification recipe. Keep a common assessment format. Do not carry Python underscore rules or mypy commands into other languages. Provide a discoverable scanner executable for projects without `.venv/bin/toobig`.

**A5 — Rank by maintenance need.** Start with recent change frequency, size exceedance, and a short architectural assessment. Require an identifiable separable responsibility before editing. Existing function/type lint findings, repeated conflicts, or defect history can strengthen the case. Do not invent a complex scoring system or universal complexity cutoff before these simple signals prove insufficient.

**A6 — Persist decisions and bound work.** Record a content digest plus policy version for retained or rejected candidates. Reconsider after a relevant content change, changed policy, or an explicit review date, rather than every hourly scan. Deduplicate per project/file across runs, cap the initial pilot at one edited candidate per project per day, and keep one editing refactor active per project. A cheap hourly scan can remain; expensive work does not need the same cadence.

**A7 — Separate adoption from hard CI enforcement.** Establish a baseline and first warn about new growth or worsening existing outliers. Do not make every legacy violation an immediate merge blocker. If a hard gate is later useful, document exceptions and require no unexplained new violations. New thresholds should not silently alter sase's existing Python contract during this research rollout.

These are proposed changes only. This research did not alter the job, its schedules, configuration, or repository code.

## Refactor contract and verification by language

| Language | Required behavior and architecture preservation | Verification before accepting an edit |
| --- | --- | --- |
| Rust | Preserve public paths, features, conditional compilation, and intended privacy. Keep closely related type behavior coherent. Explain each new cross-module dependency and visibility change. | Project's formatting/lint recipe, affected crate tests, and the relevant supported feature/target configurations. A default-only build does not validate code gated behind other supported features. |
| JavaScript | Preserve package entry points, module system, initialization side effects, dependency direction, mocks, and UI behavior where applicable. | Existing formatter/linter, build or type check where configured, affected unit/integration tests, and targeted UI checks for component extraction. |
| Swift | Preserve module/target membership, access control, actor isolation and availability, and relevant UI/state behavior. Prefer extracting responsibilities over spreading one oversized type across arbitrary files. | SwiftLint/formatter if configured, build and tests using the actual SwiftPM package or Xcode scheme, plus the affected app/UI checks. If required Apple-platform validation is unavailable, keep the edit unaccepted pending that evidence. |

Rust's reference documents private access through module descendants, scoped visibility such as `pub(super)` and `pub(crate)`, and public re-exports. Use the narrowest adequate visibility; avoid casually making helpers externally public merely to facilitate splitting. [Rust visibility reference](https://doc.rust-lang.org/reference/visibility-and-privacy.html).

Swift `fileprivate` is restricted to the defining source file, while private members are available to extensions of the declaring type in the same file. Moving such extensions into another file can therefore require a substantive access-control change. Prefer a better boundary or a documented retention decision over automatically promoting private state to `internal`. [Official Swift access control](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/accesscontrol/).

For JavaScript libraries, Node's package documentation shows why supported entry points and export mappings matter for compatibility. For React, its state documentation cautions that nested component definitions can reset state. A split needs to preserve those contracts, not just pass a syntax check. [Node package entry points](https://nodejs.org/api/packages.html#package-entry-points), [React component identity and state](https://react.dev/learn/preserving-and-resetting-state).

Do not invent missing verification scripts or claim that formatting establishes behavioral equivalence. Discover the project's existing recipe, record its result, and make any remaining limitation visible.

## Minimal implementation direction and pilot

Keep the first implementation small: a profile should specify authored source selection, newline thresholds, review mode, target size, prompt, and existing verification recipe. Select a single profile for each file. These are conceptual fields; they are **not** currently supported `toobig_split` configuration keys.

For manual scanner exploration, the following are valid forms against appropriately selected, clean source trees:

```sh
toobig --include '*.rs' crates 1500 1250 1000
toobig --include '*.js' --include '*.mjs' --include '*.cjs' --include '*.jsx' src 900 750 600
toobig --include '*.swift' Sources 1000 850 700
```

Replace the directory with the project's real source root. These commands do not implement the authored-path filtering, assessment stage, deduplication, or language prompts proposed above. Do not scan the entire repository merely because these extension globs are available. The tuple's informational value is the proposed review floor; scheduling and CI policy remain separate decisions.

A practical rollout is:

1. **Inventory one project of each language.** Measure eligible file counts and P50/P90/P95/max sizes; annotate inline tests, generated material, coherent outliers, and current lint rules. Use percentiles as context, not automatic threshold setters that normalize existing poor structure.
2. **Collect candidates for roughly two weeks.** Use the proposed floors in report-only mode and inspect a small sample, ideally about ten candidate assessments per language if enough exist. A smaller corpus warrants qualitative review, not fabricated statistical confidence.
3. **Try a few reviewable edits.** Begin with obvious independent responsibilities and existing tests; cap work as above. The reviewer assesses boundaries, visibility, dependency direction, API compatibility, and effort to make representative follow-up changes.
4. **Tune and selectively automate.** If most proposals are useful, required validation passes, and review cost is acceptable, allow narrowly scoped automatic edits for that project. Raise thresholds or add explained role-specific exceptions when false positives dominate; lower them when useful opportunities consistently fall below the floor. Pause editing if splits cause regressions or mainly create forwarding layers.

Track useful proposals per assessment, reviewer effort, failed/reverted changes, repeated exceptions, newly exposed interfaces, and whether later feature changes still require touching all the extracted files. Agent time and validation cost belong in the evaluation. The pilot durations, sample sizes, and daily cap above are pragmatic budget choices, not findings from the cited studies.

## Limitations and confidence

Confidence is high in the inspected scanner/job behavior and the documented lint defaults. Confidence is moderate that an assessment-first, project-aware policy will avoid more wasted work than unconditional splitting. Confidence is low in any exact optimal trigger, including my own defaults, until the actual target projects are sampled.

The user did not identify the specific Rust, JavaScript, and Swift repositories, so this report does not claim to have measured their distributions, frameworks, build times, or existing lint policies. Most of the empirical maintainability evidence reviewed is Java-based and cannot establish language-specific causal limits. Sources and repository revisions were checked independently for this report; no peer research was consumed.

## Recommended solution

**Expand the scanner first and pilot architecture review before automatic editing. Start Rust at >1,000 physical lines with a 600-line soft target, JavaScript at >600 with a 350-line soft target, and Swift at >700 with a 400-line soft target. Keep sase's existing Python policy unchanged initially.** Add explicit globs and authored-source filtering, language-aware refactor prompts and validation, persisted retention decisions, and a small per-project work budget. Accept a split only when it creates coherent responsibilities and preserves behavior and intended encapsulation; allow explained oversized files. Recalibrate from the pilot's useful outcomes, then enable selective automation. This retains the inexpensive signal that makes `toobig_split` useful while making architectural improvement—not a shorter file—the acceptance criterion.
