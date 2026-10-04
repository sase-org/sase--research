# Multi-Language `toobig_split`: Architecture Critique, Cross-Language Line-Count Thresholds, and Operational Strategy

**Author:** Researcher `gem` (Independent Research Swarm)  
**Date:** October 2026  
**Target:** SASE Research Repository (`sase/repos/research/202610/`)  
**Topic:** Extending the `toobig_split` routine from Python to Rust, JavaScript/TypeScript, and Swift  

---

## Executive Summary

Expanding the automated `toobig_split` AXE routine from `sase` (a Python repository) to other projects in **Rust**, **JavaScript/TypeScript**, and **Swift** requires rethinking both the **quantitative thresholds** (trigger floors and split targets) and the **operational mechanics** (autonomous background splitting vs. human-in-the-loop advisory triage).

1. **The Core Failure Mode of Direct Porting:**  
   Applying Python's **700-line trigger floor** and **500-line target recommendation** to Rust, JS/TS, or Swift will cause immediate friction. 
   - In **Rust**, 700 lines is standard module size: in `sase-core` alone, **28% of all files (261 files)** exceed 700 lines, including foundational files like `scanner.rs` (3,330 LOC) and `touch_index.rs` (3,103 LOC). An uncalibrated 700-line trigger would unleash a runaway swarm of hundreds of background agents attempting to dissect working, cohesive code.
   - In **Swift**, while SwiftLint flags warnings at 400 lines and errors at 1,000 lines, Swift's access control (`fileprivate`/`private`) and inability to split stored properties across files make arbitrary mechanical splits hazardous to class encapsulation.
   - In **JavaScript/TypeScript**, complex UI components (React/Obsidian plugins) frequently hit 500–800 lines naturally, while bundled artifacts (e.g. `main.js` in `bob-plugins`) reach tens of thousands of lines and must be rigorously filtered out. Furthermore, mechanical splits in JS/TS introduce runtime circular dependency failures (Temporal Dead Zone) that typecheckers like `tsc` often miss.

2. **Recommended Quantitative Thresholds:**

| Language | Hard Line Limit | Warning Limit | Info / Trigger Floor | Split Recommendation (Target) | Special Accounting Rules |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Python** *(Baseline)* | 1,000 | 850 | **700** | **500** | Exclude comments & docstrings |
| **Rust** | 2,000 | 1,700 | **1,500** *(or 1,000 excl. tests)* | **1,000** *(or 750 excl. tests)* | **Crucial:** Exclude or separate `#[cfg(test)] mod tests` |
| **JavaScript / TypeScript** | 1,200 | 950 | **800** | **500** | Strict exclusion of `dist/`, `build/`, `*.bundle.js`, `*.min.js` |
| **Swift** | 1,200 | 900 | **800** | **500** | Target protocol/feature extensions (`Type+Domain.swift`) |

3. **Strategic Critique & Recommended Approach:**  
   - **Do not run autonomous background code-splitting on other projects.** An autonomous background daemon running every 60 minutes that refactors files without human initiation generates severe git churn, race conditions with active work, merge conflicts, and encapsulation erosion (agents turning private items into `pub(crate)` or `export` to appease the compiler).
   - **Adopt an Advisory Triage Model:** Have the AXE job inspect projects on schedule and emit **Task Beads** (`task_type: feature` or refactoring triage) when files cross thresholds, rather than immediately enqueuing code-editing clans.
   - **Use Language-Specific Split Macros:** Replace the generic Python-centric `#split_file` macro with specialized macros (`#split_file_rust`, `#split_file_ts`, `#split_file_swift`) tailored to the module systems, visibility semantics, and verification suites of each ecosystem.

---

## 1. Anatomy of Current `toobig_split` in SASE

To evaluate expanding `toobig_split`, we must first understand how it operates within the SASE infrastructure.

### 1.1 The Routine & Job Architecture
As configured in `home/dot_config/sase/sase_athena.yml` and backed by `Justfile`:
- **Scheduler Cadence:** Runs every 60 minutes (`run_every: 60m`) under AXE.
- **Concurrency & Inhibit Guard:** Guarded by `inhibit_if: agent_clan: { name_prefix: toobig- }`. This ensures that a previous split swarm must fully settle before another scan can propose work.
- **Graduated Detection Parameters:** Scans `src` and `tests` with three positional thresholds:
  - Hard limit: `1000` lines (causes linter exit failure).
  - Warning limit: `850` lines.
  - Info / Trigger Floor: `700` lines.
- **Clan Emission:** The script emits a sequential clan of `%auto #split_file:<path>` proposals.
- **Late-Binding Filter:** Crucially, each proposed clan member contains an `%if` predicate that rechecks the 700-line floor *immediately before admission*. If an earlier agent's split or a concurrent commit caused the file to drop below 700 lines, the member is pruned without spending an LLM turn.

### 1.2 The Split Directive (`split_file.md`)
The instruction passed to the agent (`src/sase/macros/split_file.md`) is tightly coupled to Python semantics:
```markdown
Can you help me split the `{{ file_path }}` file into multiple files? Use your best
judgment, but keep every resulting file at 500 lines of code or fewer.

Preserve behavior and the original module's public import path. A facade may re-export
public names, but never `_private` names. Never import a `_`-prefixed name across the
new modules. If more than one new module needs a helper, give it a public name inside an
already-private (`_`-prefixed) module; move a helper used by only one other module into
that module instead. Keep test monkeypatch targets working, or retarget the tests.

Before finishing, run `just _lint-symvision`, `just _lint-mypy`, and `just _lint-toobig`
individually. Fix every issue in a file the split touched, even if an earlier
`just check` stage is already red. Then run `sase tool run check`.
```

### 1.3 Why This Works in SASE (Python)
- **High Syntactic Density:** Python code is compact (indentation-based, no braces, dynamic or expressive typing, expressive comprehensions). 700 lines of Python often represents 1,500–2,500 lines of equivalent logic in Rust or Swift. A Python file reaching 700 lines is genuinely overloaded with multiple responsibilities.
- **Decoupled Tests:** In Python/SASE, unit and functional tests reside in a distinct `tests/` directory tree. A 700-line source file contains *only* runtime application logic.
- **Fast, Strict Linting Harness:** SASE has exceptionally fast Python tooling: `ruff` (milliseconds), `symvision` (detecting dead/unused symbols across splits), and `mypy`. Agents can rapidly iterate and verify that imports and re-exports are sound.
- **Convention-Based Encapsulation:** Python's private boundaries are conventions (`_foo`). Submodule splitting does not encounter compiler-level visibility or borrow-checker barriers.

---

## 2. Linguistic Analysis: Why 700/500 Fails in Rust, JS/TS, and Swift

Attempting to apply a blanket 700-line trigger and 500-line target to other languages collides with fundamental language design choices, community idioms, and compiler architectures.

```
+---------------------------------------------------------------------------------------------------+
|                                 SYNTACTIC & MODULE PROFILE COMPARISON                             |
+-------------------+--------------------+------------------------+---------------------------------+
| Language          | Boilerplate/Density| Inline Test Colocation | Cost of Splitting Modules       |
+-------------------+--------------------+------------------------+---------------------------------+
| Python            | Low boilerplate    | None (tests in tests/) | Low: Facades re-export cleanly  |
| Rust              | Very high          | Heavy (cfg(test) mod)  | High: Borrow/visibility leaks   |
| JavaScript/TS     | Moderate           | Low to moderate        | Moderate: Runtime ESM cycle TDZ |
| Swift             | Moderate-High      | Low (XCTest targets)   | High: fileprivate leaks, PBX    |
+-------------------+--------------------+------------------------+---------------------------------+
```

### 2.1 Rust

#### The Reality of Rust Line Counts
Rust is inherently syntactically verbose. A single domain type frequently requires:
- Explicit type declarations and lifetime annotations.
- `where` clauses on complex generic bounds.
- Multiple `impl` blocks for domain methods.
- Exhaustive trait implementations (`Display`, `Debug`, `Clone`, `PartialEq`, `Serialize`, `Deserialize`, `From`, `Into`, `Default`).
- Detailed `match` statements and error transformations (`map_err`).
- Inline unit tests: The Rust standard idiom places `#[cfg(test)] mod tests { ... }` at the bottom of the very module it tests.

#### Empirical Evidence from Existing Projects
Analyzing the user's active Rust repositories reveals that a 700-line trigger would be catastrophic:
- **`sase-core`:**
  - Total `.rs` files: 926
  - Files > 700 lines: **261 (28.2%)**
  - Files > 1,000 lines: **147 (15.9%)**
  - Files > 1,500 lines: **59 (6.4%)**
  - Files > 2,000 lines: **24 (2.6%)**
  - Examples of core, well-engineered modules: `scanner.rs` (3,330 lines), `touch_index.rs` (3,103 lines), `frontmatter.rs` (2,775 lines), `planner.rs` (2,720 lines), `agent_hold.rs` (2,614 lines).
- **`bob-cli`:**
  - Total `.rs` files: 400
  - Files > 700 lines: **140 (35.0%)**
  - Files > 1,000 lines: **69 (17.3%)**
  - Files > 1,500 lines: **27 (6.8%)**

If `toobig_split` with a 700-line trigger floor were enabled for `sase-core`, AXE would immediately enqueue **261 background agent tasks**, churning through the entire codebase!

#### The Structural Costs of Splitting Rust Modules
1. **Encapsulation Destruction:** In Rust, visibility is lexical. Items within the same module have unrestricted access to each other's private fields. Moving a struct into `foo/bar.rs` while leaving its caller in `foo/mod.rs` means private struct fields can no longer be accessed unless declared `pub(crate)` or `pub(super)`. Mechanical splitting by an LLM inevitably degenerates into making everything `pub(crate)`, stripping the project of encapsulation.
2. **The `#[cfg(test)]` Dilemma:** In many 1,200-line Rust files, 500 lines are implementation and 700 lines are unit tests. Splitting the file because of total LOC either forces splitting tests into awkward parallel modules or extracting tests to integration tests where private internals cannot be tested.
3. **Compilation Overhead:** `cargo check` and `cargo test` require extensive type inference, borrow checking, and LLVM codegen. An autonomous clan executing sequential Rust builds will peg CPU resources and thrash `target/` directories.

#### Prior Art in SASE Config
In `~/.config/sase/sase.yml`, the user already authored an on-demand macro:
```yaml
split_epic:
  description: Split the <file_count> largest files of a particular <lang> into separate files...
  input:
    lang: { type: word, default: Rust }
    max_line_count: { type: int, default: 1500 }
```
The user's own existing intuition for Rust was **1,500 lines**, which perfectly aligns with the empirical data.

---

### 2.2 JavaScript and TypeScript

#### Characteristics
1. **Component and UI Density:** In modern TypeScript (React, Svelte, or Obsidian plugin views), a component contains type definitions, state hooks, lifecycle handlers, event callbacks, and JSX rendering trees. A cohesive component easily lands between 400 and 700 lines. Arbitrary splitting fractures component state, requiring artificial prop drilling or context layers.
2. **Circular Dependency Hazards (ESM TDZ):** JavaScript ES modules are evaluated statically, but circular bindings suffer from the Temporal Dead Zone (TDZ). If File A imports File B, and File B imports File A, runtime crashes (`ReferenceError: Cannot access 'X' before initialization` or `TypeError: Cannot read properties of undefined`) frequently occur. TypeScript's compiler (`tsc`) does **not** fail builds on circular imports unless specifically configured with external plugins or tools like `madge`. An agent performing automated splits can easily introduce runtime cycles that pass `tsc` but crash in production.
3. **Bundling & Output File Traps:**
   In repositories like `bob-plugins`, Obsidian plugins often maintain committed bundled distributions (`main.js`) ranging from 1,000 to 50,000+ lines. An automated scan that lacks robust exclusion globbing would attempt to split compiled bundle artifacts.

#### Industry Standards
- ESLint provides `max-lines`, which defaults to **300 lines**. However, nearly every production engineering organization either disables `max-lines` or raises it to **500–800 lines** because 300 lines causes excessive micro-file fragmentation.

---

### 2.3 Swift

#### Characteristics & Community Idioms
1. **Protocol-Oriented Programming & Extensions:**
   Swift has a unique and elegant idiom for file decomposition: **Extensions**. Rather than creating artificial sub-objects, a large Swift type is traditionally split across files using extensions:
   - `User.swift` (Stored properties, primary initializer)
   - `User+Database.swift` (CoreData / SQLite mapping)
   - `User+Networking.swift` (Codable, API serialization)
   - `User+Validation.swift` (Business rules)
2. **Access Control Barriers (`fileprivate` vs `internal`):**
   Swift enforces strict lexical access control:
   - `private`: Accessible only within the declaration and extensions *in the same file*.
   - `fileprivate`: Accessible anywhere *within the same file*.
   If an agent splits a 900-line Swift file into two files, any `fileprivate` property or helper must be promoted to `internal` (visible to the entire module/target). This significantly weakens module isolation.
3. **Compiler Restriction on Stored Properties:**
   Swift forbids stored properties inside extensions. All stored properties must reside in the root declaration. An agent cannot simply "cut the struct in half."
4. **Build System & Xcode PBX Hazard:**
   This is a critical platform difference:
   - If the Swift project uses **Swift Package Manager (SwiftPM)** (`Package.swift`), new files added to `Sources/TargetName/` are picked up automatically.
   - If the project uses an **Xcode project file (`.xcodeproj/project.pbxproj`)**, creating a new `.swift` file on disk does **not** add it to the compilation target! The PBX project file must be modified, or the new file will simply be ignored by `xcodebuild`. LLMs notoriously corrupt PBX project files when attempting to edit them directly.

#### Industry Standards
- **SwiftLint**: The de facto standard linter for Swift has a built-in `file_length` rule:
  - Default Warning: **400 lines**
  - Default Error: **1,000 lines**
  - Common production configuration: Warning at **500–600 lines**, Error at **1,200 lines**, with `ignore_comment_only_lines: true`.

---

## 3. Critique of the Plan in General

### 3.1 Is Running `toobig_split` Across Other Projects a Good Idea?

**Verdict: As an autonomous, periodic background daemon—NO. As a human-triggered, advisory-assisted workflow—YES.**

#### Why the Autonomous Daemon Approach is Flawed for Multi-Language Repos:
1. **Lines of Code is a Toxic Proxy for Code Health:**  
   Line count is a scalar metric that measures syntax, not complexity. A 1,200-line Rust file implementing a single cohesive state machine with comprehensive unit tests is superior software architecture compared to four 300-line files tied together with leaking `pub(crate)` fields and cross-file dependencies. Autonomous splitting incentivizes **architectural fragmentation**.
2. **Git Churn and Concurrent Editing Hazards:**  
   Running a background chop every 60 minutes across active projects creates severe operational friction. If an agent unilaterally decides to split `scanner.rs` into five files while a developer or another agent is implementing a feature on a branch, the resulting merge conflicts will be catastrophic.
3. **Encapsulation Degradation by Agent Coping:**  
   When LLMs are told "split this file and make sure tests pass," their primary failure mode is breaking encapsulation. If the compiler complains that `field_x` is private in the new submodule, the agent's easiest path to green is changing `field_x` to `pub(crate)` or `pub`. Doing this repeatedly across a codebase turns a modular architecture into global spaghetti.
4. **Verification Imbalance:**  
   In SASE, Python has sub-second linting via `ruff` and AST symbol checking via `symvision`. In Rust, a full `cargo test` cycle can take several minutes. Running multi-agent clans in the background will drain battery, pin CPU, and blow up cache sizes.

---

## 4. Requirement Adjustments & Proposed Adjustments

To make multi-language file splitting safe and effective, the following adjustments to the requirements are proposed:

### Adjustment 1: Shift from "Autonomous Splitting Daemon" to "Advisory Triage + Human Approval"
- **Do not** have the AXE routine directly dispatch `#split_file` agents on an hourly tick for external repositories.
- **Instead**, have the AXE routine run as an **Advisory Auditor**:
  - When a file crosses the `warning_limit`, the routine files or updates a **Task Bead** (`task_type: feature` or refactoring triage).
  - The bead notes the file, its line count, whether tests are colocated, and the recommended decomposition strategy.
  - The developer (or human gate) reviews the bead and triggers the split when the workspace is idle.

### Adjustment 2: Decouple Test LOC from Source LOC (Especially in Rust)
- In Rust, counting `#[cfg(test)] mod tests { ... }` toward the production line limit forces developers to either stop writing unit tests or prematurely extract them to integration tests.
- **Requirement:** The line-counting scanner (`toobig` or a language-aware preprocessor) must either:
  1. Support ignoring test blocks (`#[cfg(test)]`), OR
  2. The split directive must first instruct the agent: *"If `#[cfg(test)]` accounts for the excess lines, move the unit tests to a separate sibling `tests.rs` or `foo_test.rs` file before modifying production structures."*

### Adjustment 3: Language-Specific Splitting Directives (Macros)
The current `split_file.md` is Python-specific. We must introduce distinct, language-idiomatic directives:
- `#split_file_rust`: Focuses on module declarations (`mod.rs`), preserving private visibility, extracting unit tests, and verifying with `cargo check` and `cargo clippy`.
- `#split_file_swift`: Focuses on `Type+Domain.swift` extensions, respecting `fileprivate`, and verifying SwiftPM / Xcode project integrity.
- `#split_file_ts`: Focuses on avoiding ESM circular imports, maintaining barrel re-exports (`index.ts`), and verifying with `tsc --noEmit` and cycle detection.

### Adjustment 4: Strict Artifact and Generated File Exclusion
- In JavaScript, bundled files (`dist/`, `build/`, `*.bundle.js`, `main.js`) must be excluded via glob patterns.
- In Rust, `target/` and generated code (e.g. `bindgen.rs`, protobuf/gRPC outputs) must be ignored.
- In Swift, `.build/`, `Pods/`, and generated mocks must be ignored.

---

## 5. Recommended Quantitative Thresholds

Based on linguistic verbosity, community conventions, and empirical repository metrics, the following graduated thresholds are recommended:

```
+----------------------------------------------------------------------------------------------------------------+
|                                    RECOMMENDED GRADUATED LINE THRESHOLDS                                       |
+-------------------+-------------------+--------------------+-----------------------+---------------------------+
| Language          | Hard Limit (Exit 1)| Warning Threshold  | Info / Trigger Floor  | Split Recommendation Target|
+-------------------+-------------------+--------------------+-----------------------+---------------------------+
| **Python**        | 1,000 lines       | 850 lines          | **700 lines**         | **500 lines**             |
| **Rust**          | 2,000 lines       | 1,700 lines        | **1,500 lines**       | **1,000 lines**           |
|   *(excl. tests)* | 1,500 lines       | 1,200 lines        | **1,000 lines**       | **750 lines**             |
| **JS / TS**       | 1,200 lines       | 950 lines          | **800 lines**         | **500 lines**             |
| **Swift**         | 1,200 lines       | 900 lines          | **800 lines**         | **500 lines**             |
+-------------------+-------------------+--------------------+-----------------------+---------------------------+
```

### Detailed Justification for Each Language

#### 1. Rust: 1,500 Trigger Floor / 1,000 Split Target
- **Why 1,500?** In `sase-core`, 261 files exceed 700 lines, but only 59 files exceed 1,500 lines. The 59 files above 1,500 lines represent genuine monoliths (e.g. `scanner.rs` at 3,330 lines, `touch_index.rs` at 3,103 lines) that are ripe for refactoring. 1,500 lines provides high-signal targeting while eliminating 80% of the false positives.
- **Why 1,000 Target?** When an agent splits a 2,000-line Rust file, asking it to produce 500-line files forces it to create 4 or 5 micro-modules, causing severe `pub(crate)` visibility leakage. Aiming for ~1,000 lines allows a natural two-way split (e.g., separating core state from event processing, or extracting tests).

#### 2. JavaScript / TypeScript: 800 Trigger Floor / 500 Split Target
- **Why 800?** A comprehensive React or Obsidian view component with types and state easily reaches 500–700 lines without violating Single Responsibility. Setting the trigger at 800 ensures that only components that have genuinely accumulated secondary concerns are flagged.
- **Why 500 Target?** 500 lines is comfortable for a split component: it leaves enough room for sub-components, helper hooks, or extracted data-layer handlers without fragmenting the UI code.

#### 3. Swift: 800 Trigger Floor / 500 Split Target
- **Why 800?** While SwiftLint warns at 400 lines, 400 is too aggressive for automated splitting. Many SwiftUI views or complex ViewControllers with protocol implementations naturally sit around 500–700 lines. An 800-line floor flags files that have accumulated multiple distinct protocol conformances.
- **Why 500 Target?** Swift's extension mechanism allows taking an 800-line file and cleanly carving out 300 lines of protocol implementations into `Type+Feature.swift`, leaving the core declaration at ~500 lines.

---

## 6. Comprehensive Recommended Solution & Implementation Plan

### Step 1: Update the AXE Chop Configuration
Modify the AXE routine configuration (in `chezmoi` under `home/dot_config/sase/sase_athena.yml` and `sase.yml`) to support **per-language parameters**:

```yaml
axe:
  routines:
    maintenance:
      jobs:
        toobig_audit:
          script: bugyi_chop_toobig_audit
          description: "Audit file line lengths across configured projects and emit triage beads"
          run_every: 24h
          for_each:
            source: projects
            names: [sase, sase-core, bob-cli, bob-plugins]
          targets:
            sase:
              lang: python
              trees: [src, tests]
              limits: [1000, 850, 700]
              target_split: 500
            sase-core:
              lang: rust
              trees: [crates]
              limits: [2000, 1700, 1500]
              target_split: 1000
              exclude_patterns: ["target/**", "**/bindgen.rs"]
            bob-cli:
              lang: rust
              trees: [src, tests]
              limits: [2000, 1700, 1500]
              target_split: 1000
            bob-plugins:
              lang: typescript
              trees: [plugins]
              limits: [1200, 950, 800]
              target_split: 500
              exclude_patterns: ["**/main.js", "**/dist/**", "**/node_modules/**"]
```

### Step 2: Implement Language-Specific Split Directives (Macros)

Instead of the one-size-fits-all `split_file.md`, create specialized macros in `src/sase/macros/`:

#### A. Rust Split Macro (`split_file_rust.md`)
```markdown
---
name: split_file_rust
description: Split an oversized Rust module into cohesive submodules.
input:
  file_path: { type: path, description: "Rust source file to split" }
  target_limit: { type: int, default: 1000, description: "Maximum lines per resulting file" }
---
Can you help me split `{{ file_path }}` into smaller, cohesive modules? Keep every resulting file at {{ target_limit }} lines or fewer.

Guidelines:
1. **Tests First:** Check if `#[cfg(test)] mod tests` accounts for the oversized length. If so, prefer extracting the test module into a separate `tests.rs` or `{{ file_path }}_tests.rs` sibling file before modifying production structures.
2. **Encapsulation Hygiene:** Minimize `pub(crate)` exposure. Prefer submodules (`mod sub;`) that keep implementation details private to the module family. Do not expose private struct fields unless strictly required.
3. **Module Layout:** Use modern Rust 2018+ module layout (`foo.rs` and `foo/submodule.rs`, rather than `foo/mod.rs`) unless matching existing codebase conventions.
4. **Verification:** Run `cargo check --all-targets` and `cargo test --lib` to ensure borrow checking, trait bounds, and unit tests pass.
```

#### B. Swift Split Macro (`split_file_swift.md`)
```markdown
---
name: split_file_swift
description: Split an oversized Swift file using idiomatic extensions.
input:
  file_path: { type: path, description: "Swift source file to split" }
  target_limit: { type: int, default: 500, description: "Maximum lines per resulting file" }
---
Can you help me split `{{ file_path }}` into smaller files? Keep each file at {{ target_limit }} lines or fewer.

Guidelines:
1. **Extension Decomposition:** Prefer extracting protocol conformances and functional domains into extensions named `TypeName+Domain.swift` (e.g., `User+Networking.swift`, `View+Subviews.swift`).
2. **Stored Property Constraints:** All stored properties must remain in the primary type declaration. Extensions may only declare computed properties and methods.
3. **Access Control:** Be cautious with `fileprivate`. If moving a method breaks `fileprivate` access, consider whether the helper belongs in the primary file or if it should be scoped cleanly within the extension.
4. **Build Target Check:** If this project uses an Xcode `.xcodeproj`, verify how new files are registered or ensure the project uses Swift Package Manager (SwiftPM) directory discovery.
5. **Verification:** Run `swift test` or the appropriate project build command.
```

#### C. JavaScript/TypeScript Split Macro (`split_file_ts.md`)
```markdown
---
name: split_file_ts
description: Split an oversized JavaScript/TypeScript file without circular dependencies.
input:
  file_path: { type: path, description: "JS/TS source file to split" }
  target_limit: { type: int, default: 500, description: "Maximum lines per resulting file" }
---
Can you help me split `{{ file_path }}` into smaller files? Keep each file at {{ target_limit }} lines or fewer.

Guidelines:
1. **Circular Dependency Prevention:** Ensure no cyclical imports are created between the split files (avoid A imports B and B imports A). Circular ESM imports cause runtime `undefined` bindings due to the Temporal Dead Zone.
2. **Barrel Exports:** Preserve public exports by re-exporting names from the original file or an `index.ts` barrel.
3. **Never Touch Bundles:** Never edit or split bundled files (e.g. `main.js`, `*.min.js`).
4. **Verification:** Run `npm run lint`, `npx tsc --noEmit`, and project unit tests.
```

### Step 3: Phased Rollout Strategy

1. **Phase 1 (Audit & Telemetry Only):**  
   Deploy the updated `bugyi_chop_toobig_audit` job in reporting mode. It emits no agent proposals and touches no code. It merely records which files across `sase-core`, `bob-cli`, and `bob-plugins` violate the new language thresholds.
2. **Phase 2 (Advisory Task Beads):**  
   Configure AXE to create low-priority task beads for any file exceeding the `warning_limit`. Review these beads in the TUI Beads tab during regular triage.
3. **Phase 3 (Interactive Execution via Macro):**  
   When a developer agrees a file needs splitting, invoke `#split_file_rust:<path>` or `#split_file_ts:<path>` on demand in an isolated workspace.
4. **Phase 4 (Selective Epic Splitting):**  
   For large monolithic files (e.g. `scanner.rs` at 3,330 lines), use the existing `#split_epic` macro to plan a deliberate, multi-phase refactoring sequence with human oversight, rather than letting an hourly background job hack away at it.

---

## Conclusion

Expanding file-length governance beyond Python is a worthwhile initiative, but treating all languages as "Python with different syntax" is an architectural hazard. 

By adjusting thresholds to reflect language verbosity (**1,500 / 1,000 for Rust**, **800 / 500 for JS/TS and Swift**), separating inline test accounting, filtering out build bundles, and moving from an autonomous background chopping daemon to an **advisory triage + language-specific macro workflow**, SASE can maintain high code quality across multi-language repositories without risking architectural instability.
