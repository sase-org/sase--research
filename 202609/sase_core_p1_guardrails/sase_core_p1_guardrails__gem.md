# Evaluation of SASE-Core P1 Guardrails: Worth Implementing, Critical Amendments, and Recommended Execution Plan

**Author:** `research.2g.gem` (Independent Evaluation)  
**Date:** 2026-09-24  
**Target:** `sase-org/sase-core` (`master` @ `eef7ca4`, post-sase-15b/17o) & `sase-org/sase`  
**Subject:** Rigorous analysis of the `P1: guardrails (one epic; before any further restructuring)` proposal in `research:202609/sase_core_agent_maintainability/sase_core_agent_maintainability.md`

---

## 1. Executive Summary & Core Verdict

The core question under review is:
> **Are the recommendations in the `P1: guardrails (one epic; before any further restructuring)` section of `sase_core_agent_maintainability.md` worth implementing or not? If so, should we make changes, or does the plan look good as-is?**

### The Bottom Line
* **Worth Implementing?** **YES, unconditionally.** Implementing machine-checked guardrails is an urgent, high-leverage necessity. The previous size-only split epics (`sase-14s` and `sase-15b`) successfully eliminated the immediate reading crisis by reducing monolithic files from 35k lines to a ~2.7k line ceiling. However, without automated structural guardrails, the repository is already experiencing rapid backsliding (new files arriving at >1,200 lines, 44 files currently >1,500 lines), high change amplification (61% of commits touching shared hubs), and runtime crashes caused by unverified invariants (missing PyO3 registrations, drifting schema versions across repos).
* **Adopt As-Is?** **NO.** The P1 plan, as drafted in the maintainability report, suffers from three critical flaws:
  1. **A test-penalizing file-size ratchet:** 25 of the 44 files over 1,500 lines exceed the threshold *strictly because of inline unit tests*. A naive raw-line ratchet will disincentivize agents from adding unit tests or drive them to separate tests from private code against project guidelines.
  2. **Severe scope overloading of "One Epic":** Bundling the remediation of 5 complex, cross-domain load flakes (`sase-15d` through `sase-15h`) and the creation of a generic AST-manipulating refactoring tool alongside static linter checks creates massive delivery risk.
  3. **Premature cross-repo coupling:** Attempting to force sase's 2,786-line `validate_sase_core_rs` test suite to immediately consume generated stubs in P1 creates unnecessary friction before typed access is established.

### Recommended Solution
Proceed with **P1 Guardrails**, but **restructure it into two decoupled, tightly scoped initiatives**:
1. **Epic P1.A: Static Structural Guardrails & Invariant Truth (The Guardrails Epic)**: Focus exclusively on fast, deterministic, compile-free checks integrated into `./scripts/check.sh structure` (test-aware size ratchet, PyO3 registration completeness, schema version registry table, acyclic module graph ratchet, root prelude freeze, and generated binding inventory).
2. **Parallel Track: Gate Stabilization & Flake Burndown**: Spin off the 5 runtime load flakes (`sase-15d..15h`) into a standalone stabilization track so that static linter rollout is not held hostage by elusive timing/concurrency bugs in `sudo_runner` or `telemetry`.

---

## 2. Background and Strategic Context

### 2.1 The Post-Split Reality
Epics `sase-14s` and `sase-15b` addressed the physical size of files in `sase-core`. Today, the reading unit problem is solved: no core file is an unreadable 30,000-line monolith. 

However, live investigation of `sase-core` at commit `eef7ca4` reveals that the fundamental developer friction for autonomous agents is no longer file size, but **architectural entanglement and invisible invariants**:
* **Hub Contention:** `crates/sase_core/src/lib.rs` remains a massive 1,635-line root prelude exposing 2,674 names. Over 40% of all commits touch this single file, creating frequent merge conflicts for parallel agents.
* **Invisible Python Registration:** When adding a Rust `#[pyfunction]`, forgetting to register it in `register_*` compiles cleanly but leads to immediate Python `AttributeError` at runtime. In `sase-14s.1`, an agent had to hand-count 827 items to verify completeness.
* **Schema Version Duplication:** There are 124 distinct `*_WIRE_SCHEMA_VERSION` constants in Rust, 21 individual getter functions in PyO3, and over 550 references scattered across Python dataclasses and fixtures. Hand-copied versions have repeatedly broken tests (e.g., `sase-oq`).
* **Circular Dependencies:** 112 top-level modules in `sase_core` are interconnected by 149 static dependency edges, containing at least 6 strongly connected component (SCC) cycles and a hidden cycle through the root forwarder (`prompt_literal_zone_ranges`).

### 2.2 P0 Status and Momentum
Work from P0 has already landed or is currently landing:
* `crates/sase_workspace_hack` and cargo-hakari feature unification are active, with `scripts/check.sh features` verifying drift-free dependency resolution.
* `just fast` is wired to `scripts/check.sh check` for sub-30s inner loops.
* Dev extension freshness rebuilding was implemented (`tests/reproducible_flake_baseline.txt:404`).
* A module listing prototype (`scripts/check.sh modules`) already runs in milliseconds.

P1 is the necessary defensive bridge. Restructuring work (P2 de-hubbing and P3 crate splitting) cannot safely proceed without automated guardrails to prevent regressions.

---

## 3. Item-by-Item Critical Evaluation of P1 Recommendations

Below is an in-depth assessment of every check proposed in the P1 table, grounded in empirical data from the live `sase-core` and `sase` repositories.

### 3.1 File-Size Ratchet
* **Original Proposal:** *"A checked-in budget per file currently over 1,500 lines. Budgets only shrink; new files must be ≤1,500; warn at 1,200"*
* **Current Status:** 44 files in `crates/` currently exceed 1,500 lines (e.g., `agent_ownership/planner.rs` at 2,723 lines, `editor/frontmatter.rs` at 2,699 lines, `agent_scan/scanner.rs` at 2,667 lines).
* **Evaluation:**
  * **Merit:** Essential to prevent regrowth. Left unchecked, files like `provider_usage/agy.rs` arrived newly born at 1,204 lines.
  * **Critical Flaw:** Over half of the oversized files (25 of 44) exceed 1,500 lines **solely because of inline `#[cfg(test)]` modules** (e.g., `axe_chop/tests.rs`, `query/tests.rs`, and large inline test modules in stores and planners). In Rust, co-locating unit tests with private code is standard idiomatic practice and specifically endorsed in the maintainability report ("inline tests are good for locality; moving inline tests out: No").
  * If a raw-line count ratchet (`wc -l`) is enforced, an agent modifying a 1,450-line file who wants to write 100 lines of thorough unit tests will be blocked by CI. The agent will either:
    1. Omit tests to pass CI.
    2. Extract tests into awkward external test files.
    3. Spend excessive tokens trying to artificially compress code.
* **Required Amendment:**
  * The file-size ratchet must measure **production lines of code** (excluding `#[cfg(test)] mod tests { ... }` blocks and inline test code), OR maintain a separate budget for `(production_lines, test_lines)`.
  * The 1,200-line warning must be strictly **advisory (stderr output only)** and never return a non-zero exit code or block an agent turn.

### 3.2 Registration Completeness
* **Original Proposal:** *"Every `#[pyfunction]` appears in exactly one `wrap_pyfunction!` in its domain's `register_*`"*
* **Current Status:** 25 domain modules in `crates/sase_core_py/src/` each define a `register_<domain>(m: &Bound<'_, PyModule>) -> PyResult<()>` function containing dozens of `m.add_function(wrap_pyfunction!(..., m)?)?` calls.
* **Evaluation:**
  * **Merit:** Extremely high ROI. A missing registration compiles completely clean in Rust, produces no build warning, and fails only when Python invokes the binding at runtime.
  * **Feasibility:** Can be implemented as a lightweight AST or regex scan in `scripts/check.sh structure`. It extracts all `#[pyfunction]` identifiers in `crates/sase_core_py/src/<domain>/` and asserts 1:1 set equality against the identifiers inside `wrap_pyfunction!(...)` within that domain's `register_*` function.
  * **Performance:** Execution time is under 40ms.
* **Required Amendment:** Adopt as proposed. Ensure the linter handles attribute annotations like `#[pyo3(name = "...")]` correctly.

### 3.3 Generated Binding Inventory & Manifest Retirement
* **Original Proposal:** *"Delete the `//!` manifest. Generate the names, `#[pyo3(name)]`, parameter names and docs from the syn-parsed signatures, and gate staleness. sase's three hand lists consume the same artifact"*
* **Current Status:** The old hand-kept manifest in `sase_core_py/src/lib.rs` has already been excised from active maintenance (doc header now notes: *"Nothing parses this header, so do not grow it back into a binding list"*). On the Python side, `sase` maintains `tools/check_sase_core_rs_bindings` (680 names) and `tools/validate_sase_core_rs` (2,786 lines of handwritten probes).
* **Evaluation:**
  * **Merit:** Replacing manual binding documentation with a machine-generated contract artifact (e.g., `crates/sase_core_py/bindings.json` or stub `.pyi`) eliminates drift at the source.
  * **Critical Risk:** Attempting to migrate all three sase-side consumers—especially the 2,786-line `tools/validate_sase_core_rs`—in the same epic creates a high-friction cross-repo dependency. `validate_sase_core_rs` does not just verify name existence; it executes runtime contract assertions with dummy data.
* **Required Amendment:**
  * **Phase 1 (In sase-core):** Generate `crates/sase_core_py/bindings.json` from `syn` during build/check, and add a staleness gate (`scripts/check.sh structure` asserts that the committed JSON matches the current AST).
  * **Phase 2 (In sase):** Update the static name scanner (`tools/check_sase_core_rs_bindings`) to compare directly against `bindings.json`.
  * **Defer:** Leave `tools/validate_sase_core_rs` probe assertions intact until P2 introduces typed accessors.

### 3.4 Schema-Version Registry
* **Original Proposal:** *"One `WIRE_SCHEMA_VERSIONS` table plus a test that every `*_WIRE_SCHEMA_VERSION` constant is in it. One binding exports it; Python reads it instead of its copies; the per-value getters retire over time"*
* **Current Status:** 124 distinct `pub const .*_WIRE_SCHEMA_VERSION` constants exist across `sase_core`. There are 21 dedicated PyO3 getters (e.g., `py_agent_hold_wire_schema_version`) and over 550 Python references duplicating these integers.
* **Evaluation:**
  * **Merit:** Exceptional. This is one of the most frequent sources of cross-repo bugs (`sase-oq`, `a509dcc`).
  * Centralizing these constants into a single static mapping in Rust (e.g., `pub const WIRE_SCHEMA_VERSIONS: &[(&str, u32)]`) and exposing a single PyO3 function `get_wire_schema_versions() -> HashMap<String, u32>` allows Python to validate or look up any schema version dynamically.
  * A unit test in `sase_core` using `syn` or macro registration guarantees that no developer can add a new `*_WIRE_SCHEMA_VERSION` constant without adding it to the table.
* **Required Amendment:**
  * Maintain the 21 existing PyO3 getters as **deprecated forwarders** that read from the registry table during P1. Deleting them immediately would break Python consumers before `sase` callers are updated.

### 3.5 Module Docs & Generated Architectural Map
* **Original Proposal:** *"Every new module file starts with `//!`. `docs/MODULES.md` is generated from them, grouped by layer, and gated"*
* **Current Status:** `scripts/check.sh modules` already exists in `sase-core`! It dynamically inspects all 112 top-level modules in `crates/sase_core/src/` and extracts their leading `//!` line.
* **Evaluation:**
  * **Merit:** Fast orientation for agents entering unfamiliar domains. A generated `docs/MODULES.md` provides an instant index without token-heavy directory exploration.
  * **Critical Flaw:** If the rule is enforced on *every new `.rs` file* (e.g., internal helpers like `scanner.rs`, `args.rs`, `support.rs`), agents will write generic, low-information doc comments (e.g. `//! Implementation of scanner`) simply to pass the gate.
* **Required Amendment:**
  * Restrict mandatory `//!` documentation to **top-level module roots** (`<mod>.rs` or `<mod>/mod.rs`) and public facade modules.
  * Group modules in `docs/MODULES.md` by architectural layer:
    1. *Foundation / Utility* (pure helpers, locks, timestamps).
    2. *Domain Logic* (beads, plans, artifacts, editor).
    3. *Surfaces / Adapters* (gateway, PyO3 bindings, LSP).
  * Gate that `docs/MODULES.md` is regenerated and clean in `scripts/check.sh structure`.

### 3.6 Acyclic Module Graph & SCC Allowlist Ratchet
* **Original Proposal:** *"Fail on any new `crate::<mod>` edge that closes a cycle. The allowlist of today's SCCs may only shrink. Treat the root forwarder as an edge"*
* **Current Status:** The 112 modules currently form 6 cycles (e.g., `plan <-> bead`, `hold_directive <-> agent_launch`, `agent_runtime <-> agent_scan`, `axe_chop <-> config`, `host_liveness <-> fleet_contract`). Additionally, the root forwarder `prompt_literal_zone_ranges` in `lib.rs` ties 11 modules into an accidental cycle.
* **Evaluation:**
  * **Merit:** Absolutely vital. Rust crates cannot have cyclic dependencies. If P2 and P3 intend to extract modules into separate crates, cycles must be eliminated. Without a cycle ratchet, new feature work will inadvertently add cross-module dependencies that make crate splitting impossible.
  * **Feasibility:** A fast Python script in `scripts/` parses `use crate::<mod>` lines across non-test files, constructs an adjacency list, runs Tarjan's strongly connected components algorithm, and verifies that no new SCCs exist beyond a checked-in allowlist of the current 6 cycles.
  * **Performance:** Executes in under 120ms.
* **Required Amendment:** Adopt as proposed.

### 3.7 Root-Prelude Freeze
* **Original Proposal:** *"The count of root `pub use` names may only fall"*
* **Current Status:** `crates/sase_core/src/lib.rs` currently contains 107 `pub use` blocks exposing 2,674 names.
* **Evaluation:**
  * **Merit:** Immediate relief for merge contention. Freezing the prelude ensures that new features cannot add to the monolithic root re-export hub, forcing them to use explicit module paths instead.
  * **Feasibility:** A single check in `check.sh structure`:
    ```bash
    count=$(grep -c 'pub use crate::' crates/sase_core/src/lib.rs)
    [[ $count -le 107 ]] || { echo "Root prelude count ($count) exceeds budget (107)"; exit 1; }
    ```
* **Required Amendment:** Adopt as proposed.

---

## 4. Evaluation of Supporting Items ("Also in P1")

The P1 proposal includes four additional items outside the main table. These require careful triage:

| Item | Proposed Action | Assessment | Recommendation |
|---|---|---|---|
| **Gateway Route ↔ Snapshot Test** | Add standing test checking routes against contract snapshots | High value, prevents subtle gateway API drift | **Include in P1** |
| **Rename `*_parity.rs` → `*_golden.rs`** | Rename test files and delete "mirror this" comments | Low effort, eliminates misleading terminology (Rust core is authority, not a mirror) | **Include in P1** |
| **Burn down 5 load flakes (`sase-15d..15h`)** | Fix telemetry concurrent writers, 3 sudo_runner bugs, gateway route deadlines | Concurrency/timing bugs across 3 domains. High effort, unpredictable scope | **UNBUNDLE from P1 into separate track** |
| **Syn-span "move items" refactoring tool** | Build a tested AST manipulation tool for P2 | High upfront engineering cost. Risk of building an overly general tool | **DESCOPE from P1; use targeted scripts in P2** |

### Detailed Rationale on Unbundling Flakes
The maintainability report correctly observes that *"for agents, a flaky gate is worse than a slow one."* However, bundling the resolution of 5 open load flakes into P1 is an anti-pattern:
* `sase-15d` (telemetry concurrent writers) requires multi-threaded synchronization refactoring in `store.rs`.
* `sase-15e/f/g` (sudo_runner empty pid, cwd cleanup, ETXTBSY on fake sudo) involve Linux process lifecycle, file descriptor inheritance, and OS executable locking.
* `sase-15h` (gateway fleet-route deadlines) involves Tokio async timing and timeout tolerances.

None of these bugs have anything to do with static structural guardrails, AST parsing, or schema registries. Conflating them into "One Epic" means that landing the static guardrails—which can be completed rapidly—would be blocked indefinitely while debugging intermittent OS race conditions.

### Detailed Rationale on Descoping the Refactoring Tool
Building a generic, reliable AST-modifying tool using `syn` spans that preserves whitespace, formatting, comments, and macro attributes is essentially writing a compiler frontend. In practice, the P2 work (de-hubbing and one-name) primarily consists of:
1. Rewriting root-path imports (`sase_core::X` → `sase_core::<domain>::X`).
2. Moving misplaced helpers (`canonical_directive_name`, `validate_model_value`).

These transformations are far more reliably and rapidly executed using targeted, well-tested Python/Rust transform scripts or established tools (like `ast-grep` or `cargo-mutants`) during the specific domain phase, rather than delaying P1 to invent a bespoke refactoring engine.

---

## 5. Performance and Latency Impact on the Verify Loop

A primary objective of SASE maintainability is keeping the inner feedback loop fast. Adding guardrails must not re-introduce verification latency.

### Gate Execution Budget
The proposed `./scripts/check.sh structure` step will run as part of `just check` (and optionally in CI). Because all proposed checks are **purely static** (parsing text and ASTs without invoking the Rust compiler `rustc` or linking binaries), their execution time is negligible:

| Check Component | Implementation Mechanism | Expected Runtime |
|---|---|---|
| File-Size Ratchet | Line counter over `.rs` files (stripping tests) | ~15 ms |
| PyO3 Registration Check | Regex / syn token matcher over `sase_core_py/src` | ~35 ms |
| Binding Inventory Staleness | Diff generated `bindings.json` vs disk | ~40 ms |
| Schema Version Registry | Verify all constants in table & check binding | ~25 ms |
| Module Docs & Map Freshness | First-line `//!` check & diff `docs/MODULES.md` | ~20 ms |
| Acyclic Module Graph | Adjacency build + Tarjan's SCC algorithm | ~85 ms |
| Root-Prelude Budget | Grep count on `crates/sase_core/src/lib.rs` | ~5 ms |
| **Total `check.sh structure` Latency** | | **~225 ms** |

At ~0.22 seconds, `check.sh structure` adds virtually zero overhead to the ~280s full gate, and can even be run standalone via `just structure` in under a quarter of a second.

---

## 6. Recommended Execution Plan & Phasing

To maximize velocity and eliminate risk, execute P1 across three sequential phases within the epic, with flakes handled on a parallel track:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   EPIC: SASE-CORE P1 GUARDRAILS                        │
├────────────────────────────────────────────────────────────────────────┤
│  Phase 1: In-Crate Static Linters (`check.sh structure`)               │
│  - Implement `check.sh structure` in sase-core                         │
│  - Test-aware file size ratchet (production lines ≤ 1,500)             │
│  - Root prelude count freeze (≤ 107 pub use statements)                │
│  - Top-level module `//!` check & generated `docs/MODULES.md` gate     │
│  - Acyclic module graph check & 6-SCC allowlist ratchet                │
├────────────────────────────────────────────────────────────────────────┤
│  Phase 2: Binding & Schema Single-Source-of-Truth                      │
│  - PyO3 registration completeness check (1:1 wrap_pyfunction)          │
│  - Central `WIRE_SCHEMA_VERSIONS` table in sase_core                   │
│  - PyO3 `get_wire_schema_versions` exporter & getter deprecation       │
│  - Syn-generated `bindings.json` in sase_core_py & staleness gate       │
├────────────────────────────────────────────────────────────────────────┤
│  Phase 3: Cross-Repo Consumer Migration & Contract Tests               │
│  - Update `sase`'s `check_sase_core_rs_bindings` to read bindings.json │
│  - Gateway route ↔ contract snapshot consistency test                  │
│  - Rename `*_parity.rs` → `*_golden.rs` and update test references     │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│              PARALLEL TRACK (Separate Stabilization Beads)             │
├────────────────────────────────────────────────────────────────────────┤
│  - `sase-15d`: Telemetry concurrent writer race fix                    │
│  - `sase-15e/f/g`: Sudo runner PID, cwd, and ETXTBSY hardening         │
│  - `sase-15h`: Gateway fleet route deadline configuration              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Final Recommendation & Decision Summary

1. **Implement the P1 Guardrails:** Proceed immediately. Guardrails are the essential prerequisite that locks in past gains and creates a safe sandbox for P2 (de-hubbing) and P3 (crate splitting).
2. **Apply the 5 Necessary Adjustments:**
   - **Adjust the Size Ratchet:** Discount inline `#[cfg(test)]` modules so agents are not penalized for writing tests. Keep the 1,200-line warning purely advisory.
   - **Unbundle the 5 Load Flakes:** Decouple `sase-15d..15h` from P1 into a parallel stabilization effort. Do not let static linter delivery stall on async OS race conditions.
   - **Descope the Custom Refactoring Tool:** Do not attempt to write a general AST refactoring tool in P1. Use targeted, test-backed transform scripts when P2 begins.
   - **Staged Cross-Repo Binding Migration:** Generate `bindings.json` in `sase-core` and wire up `check_sase_core_rs_bindings` in `sase`, but defer touching `validate_sase_core_rs` until P2.
   - **Preserve Schema Getters for Backwards Compatibility:** Forward existing individual schema getters to the new central table rather than immediately deleting them.

With these five adjustments, the P1 epic becomes a clean, high-velocity, low-risk milestone that permanently secures the architecture of `sase-core`.
