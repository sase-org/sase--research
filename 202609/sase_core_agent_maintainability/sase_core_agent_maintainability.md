# sase-core for SASE Agents: What "Agent-Maintainable Rust" Means, and the Program to Get There

**Consolidated report** · **Date:** 2026-09-21 · **Repo:** `sase-org/sase-core` @ `8886406` (master, `0.34.70`; all ten
sase-15b phases closed, land in progress) · **Measured on:** athena (64 cores, rustc 1.98.1, the real SASE agent build
environment: per-run `CARGO_TARGET_DIR`, sccache rustc wrapper, `CARGO_INCREMENTAL=0`, `debug = line-tables-only`).
The host load average was 15–25 during the timings, so read them as ±10%.

**Sources:**
- The three swarm reports, [`__cld`](./sase_core_agent_maintainability__cld.md),
  [`__mus`](./sase_core_agent_maintainability__mus.md) and [`__gem`](./sase_core_agent_maintainability__gem.md).
- The baseline audit, `research:202609/sase_core_maintainability_audit/sase_core_maintainability_audit.md`
  (macOS, `9a5c568`).
- Epics **sase-14s** (closed) and **sase-15b** (phases done), which split the 20 largest files to ≤1500 lines.
- A lead verification pass. It re-timed every disputed number and statically analysed the tree at `8886406`. It also
  inspected the sase-side call path, the instruction delivery, and the pin tooling. §5 records where the reports were
  wrong.

---

## 0. Bottom line

The split epics fixed the **reading unit**: no file an agent routinely touches is too big to read any more. That was
the right first move, and it is now finished. Running a third size-only epic would buy almost nothing. What costs sase
agents the most in sase-core today is four other things. **All three researchers and the lead pass agree on this
diagnosis.**

1. **The verify loop is slow, and some of that is self-inflicted.**
   - A real edit to a `sase_core` leaf costs **57–61 s** to `cargo check`, and the `just check` gate costs **~281 s**.
   - Two environment settings add avoidable cost:
     - Non-incremental builds are forced so that sccache works. Bypassing sccache for edited workspace crates measured
       **23–30 s**.
     - Cargo feature unification differs per scope, so a "cheaper" `-p` check recompiles the crate with **no edit at
       all (49 s)**.
   - The structural floor is that one 296k-line crate is the compilation unit.
2. **The most common task has high change amplification.**
   - About 41% of sase-core feat/fix commits add a Python binding.
   - Adding one still touches the domain binding, a 1,104-line alias prelude, a hand-kept manifest and the 2,674-name
     root re-export list.
   - One function ends up with up to five names.
3. **The invariants that bite are invisible to the compiler.** In sase-core these are:
   - the registration lists and the manifest (191 entries missing)
   - wire-schema versions copied by hand
   - a false MSRV

   Across the repo boundary they are:
   - A pin that is bumped by hand, because the ratchet bot is **broken** (filed as `sase-15v`).
   - An extension that sase's `just check` **does not rebuild** after Rust edits.

   The pin gap has sase's Master Gate **red right now**.
4. **sase-core's own instructions never reach agents.** Its `AGENTS.md` is not loaded by Claude, Gemini or the SASE
   renderer when an agent works from a SASE workspace. The one core memory about sase-core points at a path that does
   not exist.

Code-level legibility is good: small functions, zero macros, free functions plus serde `*Wire` structs. Leave it
alone.

**Recommendation (details in §7).** Stop size-only epics, and run four workstreams in order, each with a measured exit
criterion.

| Order | Workstream | Main levers | Size |
|---|---|---|---|
| **P0** | Fast loop, instruction delivery, cross-repo truth | Incremental check/clippy for workspace crates. Pinned feature set. `just fast`. `sase repo open` points at `AGENTS.md`, plus shims. A real agent guide. Fix the pin bot and the stale-extension fingerprint | Hours to 2 days, across chezmoi, sase and sase-core |
| **P1** | Guardrails | One `check.sh structure` gate: size ratchet, registration completeness, schema-version registry, module docs, acyclic module graph, root-prelude freeze. Drift tests. Flake burn-down | 1 epic |
| **P2** | De-hub and one-name | Delete the root prelude and the `core_*` alias layer. Name binding domains after core modules. One generic JSON bridge. Cut the ~6 keystone edges. Give Python typed binding access | 1–2 mechanical epics |
| **P3** | Crate split | Vertical slices (a domain together with its wire types), with arrows pointing away from the heavy crate, one crate per phase, gated on measured timings | Standing direction; design doc first |

---

## 1. What changed since the audit

| Audit item | Status at `8886406` |
|---|---|
| R1 `/tmp` reap guard, R2 macOS CI (blocking), R4 `cfg(unix)` audit | **Done** as small direct patches, not as splits |
| R7 binding monolith | **Done** (sase-14s.1, `03036af`). 60 files, 25 `register_<domain>` functions, 823 registrations. The alias block moved into a new 1,104-line `prelude.rs`, and the manifest stayed |
| R18 remaining monoliths | **20 files split.** The maximum fell from 35,166 to 2,699 lines. Files grew from 381 to 704; lines from 376k to 382k |
| R3 `cargo check` inner loop | **Not done.** No `just fast`. `-p` narrowing is a trap (§4.1) |
| R5 docs truth / R6 agent guide | **Partly.** `AGENTS.md` grew from 21 to 36 lines. The README still has a "Phase status" section, 12 `sase_100` mentions and 3 `SASE_CORE_BACKEND` mentions, and its layout omits the LSP crate |
| R8 manifest → `.pyi` | **Not done.** 0 stubs. The manifest is 664 of the 736 lines in `sase_core_py/src/lib.rs` |
| R9 root prelude | **Not done.** It is still the #1 churn file (§4.2) |
| R10–R14 lints, MSRV, dependencies, deny, unwrap | **Not done.** `rust-version = "1.78"`; no `[lints]`, `clippy.toml` or `deny.toml`; `reqwest 0.11`, `pyo3 0.22` |
| R15–R17 route drift test, `*_golden` rename, version registry | **Not done** |
| R19 crate split | **Not started.** It is feasible (§4.6) |

The pattern is that the epic chain delivered the mechanical half of the audit. The higher-leverage items are all still
open: the fast loop, docs, prelude, stubs and drift tests.

---

## 2. What "easy for sase agents to maintain" means

### 2.1 How a sase agent actually works on sase-core

- **Every run starts cold.**
  - *Build state.* `launch_spawn.py` gives each run a fresh `CARGO_TARGET_DIR` and forces `CARGO_INCREMENTAL=0`.
    Only sccache carries artifacts between runs.
  - *Knowledge.* The agent knows only what its instructions inject.
- **It perceives code through tools.** That means grep, ranged reads (2,000 lines per Read for Claude, 800 per
  `view_file` for Gemini/agy) and compiler, test and gate output. Anything the agent has to *infer* costs turns and
  tokens: an alias chain, a list kept in another file, an unwritten convention.
- **It is single-turn, and tool calls have timeouts.**
  - Claude Code's Bash tool defaults to a 120 s timeout.
  - A ~4.7-minute gate therefore needs an explicit long timeout, polling, or a monitor handoff. cld found all three in
    the sase-14s phase logs.
- **Many agents commit to one unprotected master in parallel,** at about 430 commits a month. Every append-only shared
  list becomes a merge hazard.
- **The providers differ** (Claude, Gemini/agy, Codex, Muse and others). Only repo content, gate output and SASE
  command output reliably reach every agent.
- **Agents' strengths and weaknesses:**
  - They are excellent at copying the local pattern and at fixing what the compiler reports. sase-14s.9 ran about 12
    check-fix iterations without trouble.
  - They are poor at global invariants that only prose mentions. Examples: the manifest line (191 missing), the pin
    bump (57 of 57 by hand), and "never `cargo test -p sase_core` alone" (incident `a509dcc`).
  - They are poor at telling their own regression from a flake. 5 of the 20 split phases hit load flakes and re-ran.

### 2.2 Eight properties, each with a metric

This unifies cld's eight properties, mus's seven dimensions and gem's five pillars. **Change amplification** is added as
the organising metric.

| # | Property | Why it matters to agents | Metric |
|---|---|---|---|
| P1 | **Low change amplification.** A common task edits few files, and each edit is necessary | Every extra edit site is a read, a chance to forget, and a collision surface | Edit sites for "add a core fn and expose it"; share of commits touching a shared hub |
| P2 | **One name per thing.** Names are grep-stable across layers | Each alias is another grep hop and another chance to guess wrong or duplicate | Names per exposed fn; root re-exports; `as` renames |
| P3 | **Invariants live in the compiler or a fast test** | Agents fix what a gate reports and miss what only docs say | Hand-kept lists without a drift test |
| P4 | **Fast, scoped, deterministic feedback** | Wall time, turns and timeouts; flakes poison the verify signal | Edit→check seconds; gate seconds; open flakes |
| P5 | **Cheap orientation.** Instructions arrive by themselves, and a map says what lives where | A cold agent should find the owning module in ≤2 steps | Guide in context; module map; `//!` coverage |
| P6 | **Canonical patterns** | Agents copy their neighbours, so messy neighbourhoods get copied | Duplicated helper families; written recipes |
| P7 | **Bounded reading units** | A file must fit in one read, and understanding it must not need the rest of the file | Files >1500 lines; functions >100 lines |
| P8 | **Low cold-start cost** | Every run pays it | First check and first test-build time; disk per run |

### 2.3 What is specific to Rust

- **The compiler is the agent's best reviewer.** Types, exhaustive `match`, `thiserror` enums and newtypes turn
  mistakes into errors that agents fix well. So *move invariants into the type system or a fast test, not into prose.*
  The places agents fail silently are exactly the ones outside the type system:
  - PyO3 registration and `#[pyo3(name)]` strings
  - serde names and schema versions
  - route lists
  - MSRV
- **The crate is the compilation unit.**
  - Splitting files saves no compile time.
  - In stable Rust the front end (parsing, expansion, name resolution, type-check) runs mostly serially within a crate.
    Serde derives on 1,373 `*Wire` types are expanded on every rebuild.
  - Build latency is therefore an *architecture* property, set by the crate graph.
- **Coherence rules constrain splits.** Inherent `impl`s must live in the crate that defines the type. So types cannot
  be moved away from their methods (§4.6 applies this to the proposed `sase_types` crate).
- **Re-exports, `use … as` and globs create extra names.** rust-analyzer would resolve them, but running an RA index of
  a 380k-line workspace per agent is unrealistic on a host with ~40 workspaces and 15 GB of free RAM. **Grep-stable
  names are the portable fix.**
- **Macros hide code from grep and from syn-based tooling.** The repo has zero `macro_rules!`, which is a strength. A
  macro that generates `#[pyfunction]`s would also blind the text- and syn-based registration, stub and manifest
  checks proposed below. Prefer generic functions.
- **Cargo feature unification is per invocation.** A narrower `-p` scope is a *different* build, not a cheaper one,
  unless the workspace pins one feature set.
- **Inline `#[cfg(test)]` modules are good for locality,** because tests sit next to private code. They also mean the
  crate's test build is a second full compile of the crate, measured at 80 s for `sase_core`.

---

## 3. Scorecard at `8886406` (lead-measured)

| Property | Value | Verdict |
|---|---|---|
| P1 change amplification | 311 of 506 feat/fix commits since 07-21 (61%) touched a `lib.rs` hub; the core `lib.rs` alone 211 (42%). **After the split, the only feature that added a binding (`45a966c`) still touched all three hubs**, and its core `lib.rs` re-export is unused | **Poor** |
| P2 one name | Up to 5 names per exposed fn. 2,674 root re-exports (≈85% never used through the root), 146 `as` renames, 654 `core_*` aliases. 13 of 25 binding domains are named differently from their core module | **Poor** |
| P3 invariants | 823 hand-listed registrations; manifest missing 191; ~123 schema-version constants copied into Python constants, getters and tests; MSRV 1.78 is false; pin bot broken; extension fingerprint ignores Rust source; no route↔snapshot test | **Poor** |
| P4 feedback | Edit→check 57–61 s; no-edit `-p` switch 49 s; gate ~281 s; 5 open sase-core load flakes (`sase-15d/e/f/g/h`) | **Poor** |
| P5 orientation | `AGENTS.md` (36 lines) is not loaded. No module map. 112 flat top-level modules. `//!` docs on 324 of 503 non-test src files (gateway 12/45, LSP 0/14). Crate docs are stale or absent | **Poor** |
| P6 patterns | 45 `*_to_pyerr`, 32 `*_to_py`, 12 `*_from_py` helpers; "internal serialize error" string ×192; the fast `serialize_to_py` path is used 45 times vs 228 `json_value_to_py`; no written recipe | **Fair** |
| P7 reading units | 41 files >1500 lines, but 25 of them only because of inline tests. Max 2,699. 0 macros, 0 `#[path]` | **Good** |
| P8 cold start | First check in a fresh target dir: 83–126 s with the sccache wrapper (cld; lead at load 40) and 75 s incremental without sccache. Test build ~100 s; 2.3 GB of test executables per run | **Fair** |

---

## 4. Findings

### 4.1 The verify loop: measured in the real agent environment

| Scenario (core leaf `host_liveness.rs` unless noted) | Time |
|---|---|
| Warm no-op `check --workspace --all-targets` | 0.15 s |
| **`touch` only**, then `check --workspace` | **13.1 s**. sccache serves the unchanged content. This is what gem's "14 s" measured |
| **Real edit** (appended comment), then `check --workspace --all-targets` (2 samples) | **60.2 / 60.7 s** |
| Real edit, then `check --workspace` (lib targets only) | 57.1 s |
| Real edit, then `check -p sase_core --lib` | 49.5 s. Narrowing saves ~10 s because `sase_core` *is* the cost |
| **No edit**: switch scope workspace → `-p sase_core --lib`; switching back | **48.8 s**; 0.18 s |
| Cold check in a fresh target dir with the sccache wrapper (non-incremental, load 40) | 125.8 s (cld: 82.6 s) |
| **Incremental, sccache bypassed** (separate target dir): cold check (load 19) | 75.3 s |
| … then append-comment edits | **22.8 / 22.7 s** |
| … then a new fn inserted mid-file in `bead/read.rs` | **29.5 s** |
| … then that fn's body changed | **24.1 s** |
| Incremental cache size (`check --all-targets`) | 2.1 GB |
| **Gate after a core edit:** fmt-check 3.6 s + clippy 63.9 s + test build/run 212.9 s + script-test 0.5 s | **281 s** (cld: 205–296 s in agent runs) |
| Test build (`--no-run`) vs execution (4,085 tests) | 99.9 s vs 43.6 s |
| `--timings`: `sase_core` lib (test) / `sase_core` rlib, in parallel | **80.0 s / 70.5 s**. py 17.6/15.5, gateway 13.7/11.4, LSP 6.8/6.0 |
| Each of the 21 integration-test binaries | 0.9–1.9 s. 27 executables >50 MB total 2.3 GB |

**What the numbers say:**

1. **`sase_core` is ~85% of every loop.** Downstream crates re-check in 1–15 s. Only a smaller compilation unit
   changes this floor.

2. **sccache and incremental exclude each other, and the setup picks sccache everywhere.**
   - How it happens: `~/.cargo/config.toml` sets `incremental = false` and routes rustc through `sase-rustc-wrapper` →
     sccache, and the launcher exports `CARGO_INCREMENTAL=0`.
   - sccache only helps with *unchanged* units, which in practice means dependencies. A fresh per-run target dir did not
     make the first `sase_core` check cheap: 83–126 s with the wrapper, against 75 s incremental without it.
   - Incremental for the edited workspace crates **halves or better the edit→check loop** (57–61 s → 23–30 s, including
     realistic mid-file edits), with no measurable cold-start penalty.
   - The cleaner design: the wrapper keeps incremental only for metadata-only units (`check`/`clippy`, no
     `--emit=link`) and routes codegen units (`build`/`test`) through sccache.
     - Test-build incremental would cost ~9 GB per run (cld) and saves only ~13%.
     - Disk is tight: the root disk is 89% full, and `sase-15q` found agent cargo targets grown to 67 GiB unreaped. So
       the reaper must budget this.

3. **`-p` narrowing is a trap.**
   - Ten of `sase_core`'s dependencies resolve with extra features in the workspace build (verified with
     `cargo tree -e features`):
     - `chrono` (+clock/now/iana-time-zone), `serde_json` (+raw_value), `regex-automata` (+dfa-build/dfa-search)
     - `syn` (+full/visit/fold), `smallvec`, `hashbrown`, `memchr`, `once_cell`, `num-traits`, `serde_core`
   - So any `-p` scope compiles a second `sase_core`.
   - `check.sh` drops `--workspace` when `-p` is passed, "to keep single-crate runs cheap", which is the opposite of
     what happens.
   - Fix: pin the union features in `[workspace.dependencies]` or add a cargo-hakari workspace-hack crate, and gate it.

4. **Bare cargo fails on athena.**
   - On `PATH`, `python3` is pyenv 3.11 and `sase_core_py` needs abi3-py312, so bare `cargo check --workspace` fails
     in `pyo3-build-config`.
   - Bare `cargo test` also needs libpython on `LD_LIBRARY_PATH`.
   - `check.sh` solves both, and its header says so. A `just fast` must therefore go *through* `check.sh`, and the
     agent must know to use it (§4.4).

5. **The gate exceeds common tool timeouts.**
   - At ~4.7 min, `just check` outlasts Claude's 120 s default Bash timeout, so agents poll, sleep or hand off.
   - The test phase is two ~75 s parallel compiles of `sase_core` plus ~44 s of tests. P0 incremental trims only the
     clippy leg; the crate split trims all of it.

6. **Integration-test consolidation is disk hygiene, not speed.** cld proposed it to cut link time, but each binary
   links in about 1 s, in parallel. Merge the 17 `sase_core` binaries into one `tests/it/` for the ~2 GB per run.
   It is low priority.

7. **Flakes contaminate the signal.** Five open sase-core flakes fire under full-gate load:
   - telemetry concurrent writers
   - three in `sudo_runner` (an empty pid, cwd cleanup, and ETXTBSY on the fake sudo)
   - gateway fleet-route deadlines

   Five of the 20 split phases hit one and re-ran. For agents, a flaky gate is worse than a slow one.

### 4.2 Change amplification and hubs

**Anatomy of adding one binding after the split** (`45a966c`, `provider_usage_normalize_agy_usage`):

| # | Edit site | Necessary? |
|---|---|---|
| 1 | Core function in `provider_usage/agy.rs` | Yes |
| 2 | Core `lib.rs` root re-export (rustfmt reflowed 12 lines to add 2 names) | **No.** Nothing uses the root path |
| 3 | `sase_core_py/src/prelude.rs` `core_` alias | **No.** It exists only for the prelude pattern |
| 4 | Binding fn plus `wrap_pyfunction!` in `provider_policy/mod.rs` | Yes, but it lives in a domain that is **not named after the core module** |
| 5 | Manifest line in `sase_core_py/src/lib.rs` | **No.** It duplicates what the compiler knows |
| 6–8 | Across the boundary: sase caller via `require_rust_binding("…")`, a pin bump, and sometimes the validator lists | The pin bump should be automatic (§4.3) |

- **One function, five names.**
  - Python `"provider_usage_normalize_agy_usage"`
  - `#[pyo3(name)]`
  - `py_provider_usage_normalize_agy_usage`
  - `core_normalize_agy_usage`
  - `sase_core::normalize_agy_usage` / `sase_core::provider_usage::normalize_agy_usage`

  The binding sits in `provider_policy/`, so an agent guessing from the core module name looks in the wrong place.
- **The naming gap is systematic.** 13 of 25 binding domains have no same-named core module: `beads`, `plans`,
  `artifact_links`, `artifact_refs`, `provider_policy`, `fleet`, `vcs`, `axe`, `agent_holds`, `agent_custody`,
  `bead_decisions`, `editor_completion`, `editor_content`.
- **Hubs.** The core `lib.rs` is the most-churned file (211 feat/fix commits in two months). It is 1,629 lines of
  107 `pub use` blocks at 80 columns, so unrelated additions collide.
- **The binding split moved the alias hub rather than removing it.** Every domain module uses
  `use crate::prelude::*` (26 files). Only `prelude.rs` imports from `sase_core` directly (besides two test files).
- **Root-path consumers vote for module paths.** About 85% of the root names are never used through the root. The real
  root-path references are gateway 323 (105 distinct), LSP 225 (127) and py 143 (108). The py number grew since the
  audit, because split bindings use inline `sase_core::X` paths. That is about 700 mechanical rewrites.
- **Copy-me boilerplate.** Agents copy their neighbours faithfully, so each domain re-grew its own helpers:
  45 `*_to_pyerr`, 32 `*_to_py`, 192 copies of `"internal serialize error: {e}"` and 140 of "is not a valid <X> dict".
  The generic dict→Wire helper `provider_priority_dict_from_py<T>` sits in `provider_policy` but is used by config,
  vcs and agent_identity.

### 4.3 Invariants the compiler cannot see, in the repo and across it

| Invariant | Kept by | Failure seen |
|---|---|---|
| Every `#[pyfunction]` is registered | Hand lists in 25 `register_*` fns | Python `AttributeError` at runtime; sase-14s.1 counted 827 = 827 by hand |
| Binding manifest | Hand | 191 of 823 missing; agents still append to it (`45a966c`) |
| Wire schema versions | Hand copies in Rust constants, Python constants, getter bindings, test literals and `validate_sase_core_rs` | Stale fixtures in `a509dcc`; `sase-oq` (validator hardcoded 5 vs 6) |
| MSRV | `rust-version = "1.78"` + 8 `incompatible_msrv` allows | Broke sase-14j.1 and sase-14d.1 (cld) |
| Routes ↔ contract snapshot | sase-14s.5 diffed them by hand | No standing test |
| Behaviour-neutral refactor | Every phase hand-counted `#[test]`; the lander diffed counts | ~16 per-phase `/tmp/split_*.py` scripts that re-broke on attributes and raw strings (cld) |
| **sase pin tracks core** | 6-hourly ratchet workflow | **Broken.** The apply step exits 2 under `set -e`, so every run with a pending bump fails. 57 of 57 pin commits were by hand. **Master Gate red since `8e0f38a53`** (`provider_usage_normalize_agy_usage` missing). Filed as **`sase-15v`**, with a DISCOVERED ISSUE note on `sase-15p` |
| **sase's dev extension matches core source** | `tools/validate_test_environment` fingerprint | Keys on sase-core `Cargo.toml`, not source or HEAD. This workspace's extension lacks a binding that sase HEAD calls, yet validation is cached green. A stale-extension failure is **baselined as a flake** (`tests/reproducible_flake_baseline.txt:402`) |
| sase-side binding lists | Three hand lists: `check_sase_core_rs_bindings` (46 names plus a 680-name scan), `validate_sase_core_rs` (333 names, 2,780 lines of probes), `health.py` | The probe floor broke after the split (the sase-15b land agent fixed it) |

The last three rows are the most dangerous for agents. They produce **false signals**: red CI the agent did not cause,
or failures that get misfiled as flakes. For the paired changes behind **57%** of sase-core feat/fix commits (the ones
touching `sase_core_py`), these are the difference between a change that verifies and one that verifies falsely.

### 4.4 sase-core's instructions do not reach agents

- **Claude.** Claude Code reads `AGENTS.md` "only when you have no `CLAUDE.md` in your working directory or above it".
  SASE workspaces have one, so sase-core's `AGENTS.md` is never loaded. A nested `CLAUDE.md` *does* load on demand
  when a file below it is read, but sase-core has none. This was verified in two sessions here.
- **Gemini/agy** default to `GEMINI.md`, and `/sase/repos/` is gitignored, so subdirectory scanning skips it.
- **Codex.** Unverified. Its `AGENTS.md` chain runs from the git root to the cwd, and sase-core sits below the cwd.
- **SASE's renderer** writes shims only for the primary repo (`src/sase/amd/inventory.py:152` skips `sase/repos`).
- **`sase repo open`** prints just the path (`repo_handler_open.py:188`), and the `/sase_repo` skill never mentions a
  repo's `AGENTS.md`.
- **Sase-side memory is thin and partly wrong:**
  - The core memory `rust_core_backend_boundary` points at `../sase-core`, which does not exist from a workspace.
  - Nothing points at the 881-line `docs/rust_backend.md`, which itself lacks an add-a-binding recipe.
  - `decisions:rust-core-required` quotes a stale `>=0.31.0,<0.32.0` window.
  - Filed as memory task **`sase-15w`**.
- **Consequences:**
  - sase-14s.1 and .2 first looked for `crates/…` in the sase workspace.
  - Epic plans restate `AGENTS.md` rules by hand.
  - The things agents most need are written nowhere they will see: never bare cargo, the gate timeout, the `-p` trap,
    and the add-and-expose recipe.

### 4.5 The Python surface: `.pyi` stubs alone will not help (a correction)

All three reports, and the audit, called a generated `.pyi` "the highest leverage-per-hour item". **As the sase code
is written today, it would type-check about 1% of calls.**

- sase calls bindings through `require_rust_binding(name: str) -> Any` (`src/sase/core/rust.py:55`): 676 literal call
  sites (607 names) plus 16 forwarders. Only 6 sites import from `sase_core_rs` directly.
- Payloads are mostly `dict`s in and `dict[str, Any]` out, rehydrated by `*_from_dict` converters in 54 facade modules.
- Name *existence* is already gated (`check_sase_core_rs_bindings`, 680 names).
- The value of a stub therefore depends on a sase-side change first. Either:
  - a typed accessor, where attribute access on a typed module object replaces string lookup, or
  - generated `@overload`s of `require_rust_binding(Literal["…"])`.
- Even then, parameters stay `dict[str, Any]` unless TypedDicts are generated from the `*Wire` types.

The right move is to generate the binding inventory (names, parameter names and docs) from the `#[pyfunction]`
signatures. That replaces the manifest (P1). Typed access plus stubs is a P2 item for sase-side agents, not the P0 it
was presented as.

### 4.6 Module graph and crate-split feasibility

The static graph of the 112 top-level `sase_core` modules (non-test code) has **149 edges**:

- **52 modules** have no intra-crate dependencies; 31 are fully isolated.
- There are **6 cycles**, each closed by 1–3 single-use back-edges:
  - `plan→bead` (`validate_model_value`)
  - `hold_directive→agent_launch` (`parse_proc_duration_seconds`)
  - `agent_runtime→agent_scan`
  - `axe_chop↔config`
  - `host_liveness→fleet_contract`
  - a few single-use artifact edges
- **A hidden cycle:** `crate::prompt_literal_zone_ranges` is a root-level `lib.rs` function that forwards to
  `agent_launch`. It is used 8 times from `editor`, `glossary` and others. Counted as an edge, it merges three SCCs into
  one 11-module knot through `agent_launch → editor::directive::canonical_directive_name`.

cld modelled the rebuild scope by replaying 476 commits. A fine-grained crate split would cut the average rebuild to
**33%** of today's crate. Moving about five misplaced helpers into foundation modules (~20 compiler-verified lines)
cuts it to **14–19%**:

- `canonical_directive_name`
- `validate_model_value`
- `parse_runtime_timestamp`
- the editor wire entries `host_bridge` builds
- the root forwarder

The ranking is robust. The percentages are estimates from a static model that uses lines as a proxy for time.

**The `sase_types` proposal (gem) is rejected on the data.** gem proposed extracting all `*Wire` types into a
zero-logic base crate first.

- Wire types are **not separable from their logic.**
  - 107 inherent `impl` blocks (171 methods) must stay in the defining crate.
  - 89 serde helper functions and 66 wire types referencing 39 domain types would have to move too.
  - 172 of the 185 files that define wire types also contain logic.
- Wire types are also the **hottest thing in the crate.** 349 of 506 feat/fix commits touch a `*Wire` identifier, and
  171 add or remove a definition.
- A horizontal wire crate at the bottom of the graph would therefore be edited by most features, and each edit would
  still rebuild all of `sase_core` above it.
- Split **vertically instead**: a domain moves together with its wire types.

**Two rules for any split (cld):**
1. **Arrows point away from the heavy crate.** If `sase_core` re-exports an extracted crate, editing that crate still
   rebuilds `sase_core`. Consumers must import extracted crates directly.
2. **`release-plz.toml` must list every new crate** in `changelog_include`, or its changes ship no wheel.

The hottest modules (`editor`, `bead`, `agent_scan`) sit low in the graph, so easy leaf extractions shrink the crate
without helping hot edits. The keystone cuts come first.

### 4.7 The remaining big files: churn × size says stop

At HEAD, 41 files exceed 1,500 lines.

- 25 of them do so only because of inline tests, which should stay next to the private code they test.
- Over two months, feat/fix churn on them is concentrated in a few:

| File | Lines | feat/fix commits |
|---|---|---|
| core `lib.rs` | 1,629 | 211 |
| `agent_scan/wire.rs` | 1,569 | 29 |
| `agent_scan/scanner.rs` | 2,573 | 29 |
| gateway `contract.rs` | 1,840 | 23 |
| `artifact_ref/mod.rs` | 2,338 | 19 |

The core `lib.rs` is a hub; fix it by deleting the prelude. `artifact_ref/mod.rs` is a body-in-`mod.rs` exception to
the house facade rule. Everything else has ≤19 commits, and most have ≤8. gem's churn labels were not measured:
`editor/frontmatter.rs` has 4 commits, not "moderate", and `plan/validate.rs` has 8, not "high".

Line counts converged in ceiling (35k → 2.7k) but not in number, because new files are born large
(`provider_usage/agy.rs` arrived at 1,204 lines). The splits also minted 16 generic `support.rs` files. A ratchet
stops regrowth. Splits beyond that should be driven by evidence, not a quota.

### 4.8 What is fine, so spend nothing on it

- **Functions are small:** 136 are over 100 lines, 7 trip `cognitive_complexity`, and two of the three largest are
  JSON contract builders.
- **The style is agent-friendly:** free functions, `*Wire` structs and `thiserror` enums; no macro DSLs or deep
  traits.
- **Not worth a campaign:**
  - bulk field docs (most `missing_docs` hits are fields and variants)
  - a 100-column reformat (it reflows every file; the churn it would cure disappears with the prelude)
  - moving inline tests to `tests/`
  - more visibility tightening
- **Do opportunistically** in files already being touched:
  - typed errors in place of the 387 `Result<_, String>`
  - the 42 `too_many_arguments` allows turned into `*Wire` parameter objects

---

## 5. Where the reports disagreed (lead adjudication)

| Claim | Source | Verified | Verdict |
|---|---|---|---|
| Edit→`cargo check` = **14 s** | gem | A touch-only check is 13 s because sccache serves unchanged content. A real edit is 57–61 s | **gem measured a `touch`.** cld's 57–79 s stands |
| `just check` = "4–6 min" / 205–296 s | gem / cld | 281 s after a core edit | Both are in range |
| sase-15b status | gem "complete" / cld and mus "in progress" | All 10 phases closed at `8886406`; the land is still running | gem is newer. cld and mus measured `b7af6b7` |
| `.pyi` stubs "immediately enable mypy/pyright" | gem, mus, audit | `require_rust_binding(...) -> Any` covers 97% of call sites | **Wrong as stated.** It needs a typed accessor first (§4.5) |
| "Every Python caller uses `# type: ignore[import-untyped]`" | gem | Only 6 direct-import sites do | **Wrong** |
| Add `[profile.dev] debug = "line-tables-only"` | mus, audit | The launcher already sets `CARGO_PROFILE_{DEV,TEST}_DEBUG=line-tables-only` | Already applied for agents; it only helps humans |
| Bare `cargo check` fails (python 3.11) | gem | Confirmed: `python3` is pyenv 3.11; `check.sh` handles it | Real. `just fast` must wrap `check.sh` |
| Consolidating test binaries cuts link time | cld | Each links in ~1 s, in parallel; 2.3 GB of executables | Disk-only win; low priority |
| First extracted crate = `sase_types` (all `*Wire`) | gem | 107 inherent impls, 89 serde helpers, co-located logic, highest churn | **Rejected.** Use vertical domain slices after the keystone cuts (cld) |
| `macro_rules!` for bindings | audit, mus / cld | Macros hide `#[pyfunction]`s from grep and from syn-based checks and stub generation | **Use generic helpers** plus a schema-version table in place of 74–88 getters; no macros |
| Future splits: moratorium / ratchet / "top 3 files" | mus / cld / gem | Measured churn favours the ratchet plus evidence-driven splits | Merged: ratchet, split on evidence (conflicts, churn × size), no quota |
| Crate split: design doc first vs keystone cuts first | mus / cld | They are compatible | Keystone cuts go in P2 (useful anyway); the split gets a design doc |
| Root-path refs from `sase_core_py` = 1 | audit | 143 (108 distinct) after the split | The audit number predates the split |
| AGENTS.md loads for agents | implicit in mus and gem | It does not (§4.4) | cld is right; this is a P0 fix |

---

## 6. Options considered

| Option | Verdict |
|---|---|
| **A.** More size-only split epics | **Stop.** Diminishing, churn-blind, and it leaves the loop, hubs and invariants untouched. Replace with a ratchet plus evidence-driven splits |
| **B.** Environment and loop tuning (incremental for check/clippy, pinned features, `just fast`) | **Do first.** Measured 2–2.5× on the inner loop, and removes a 49 s trap |
| **C.** Instruction delivery (repo-open hint, shims, agent guide, memory fix) | **Do first.** Costs hours and reaches every provider |
| **D.** Cross-repo truth (pin bot, extension fingerprint, one generated binding list) | **Do first.** These are false signals, which are the worst kind for agents |
| **E.** Guardrails (ratchets, drift tests, registry, graph check) | **Do before any restructuring** |
| **F.** De-hub and one-name | **Do.** It removes the #1 churn file and the #1 navigation tax; every step is compiler-verified |
| **G.** Crate split | **Do, after F's keystone cuts,** as vertical slices with a design doc |
| **H.** Horizontal `sase_types` crate | **No** (§4.6) |
| **I.** Merge sase-core into the sase repo | **Not now.** It would put a 380k-line Rust build on every Python agent's path. Reopen only if paired-change breakage keeps recurring after D |
| **J.** rust-analyzer via an LSP tool | **No, not as the primary fix.** It is provider-specific and RAM-heavy; fix the names instead |
| **K.** 100-column reformat, bulk docs, moving tests out, binding macros | **No** |

---

## 7. Recommended solution

**Thesis.** The next gains do not come from smaller files. They come from making a change **local, uniquely named,
machine-checked, and fast to verify**, and from making sure the agent **knows the rules before it starts**. Order the
work so each step makes the next one cheaper and safer for the agents who will do it.

### P0: fast loop, instruction delivery, cross-repo truth (hours to ~2 days; do now)

1. **Incremental where it pays** (chezmoi and sase):
   - `sase-rustc-wrapper` execs rustc directly for metadata-only units that carry `-C incremental=`.
   - It strips incremental and uses sccache for codegen units.
   - Stop forcing `CARGO_INCREMENTAL=0` in `launch_spawn.py` and `incremental = false` in `~/.cargo/config.toml`.
   - Budget the ~2 GB per run through the managed-tmp reaper (see `sase-15q`).
   - *Exit:* real edit to a core leaf → workspace check **≤30 s**.
2. **Pin feature unification** (sase-core): declare the union features on workspace dependencies, or add a hakari
   workspace-hack crate. Add a `check.sh` step that diffs `cargo tree -e features` across scopes.
   - *Exit:* a no-edit `-p` switch costs **≤5 s**.
3. **`just fast`** → `check.sh check`. It resolves PYO3 and runs `cargo check --workspace --all-targets`.
   - Document three commands: `just fast` is the inner loop, `just test -p <crate> -- <filter>` is the targeted loop
     (safe after item 2), and `just check` is the pre-commit gate.
   - Note in the docs that the gate takes about 5 min, so it needs an explicit long tool timeout or a `sase monitor`.
4. **Deliver instructions to every provider:**
   - `sase repo open` prints on **stderr**: "read `<path>/AGENTS.md` before editing" for any repo with one. stdout stays
     the bare path. This is provider-neutral.
   - The `/sase_repo` skill says the same.
   - Add `CLAUDE.md` (`@AGENTS.md`) and `GEMINI.md` shims to sase-core.
   - Fix `rust_core_backend_boundary` and point it at `docs/rust_backend.md` (`sase-15w`).
5. **Rewrite `AGENTS.md` as the agent guide,** ≤200 lines. It should contain:
   - a crate and ownership table
   - a link to a generated `docs/MODULES.md`
   - recipes: *add a core fn*, *expose it to Python* (the exact edit sites), *bump a wire schema*, *add a gateway
     route*, *ship a paired sase change* (pin)
   - the invariant list from §4.3
   - the fast-loop commands and timeouts
   - the open flakes with their bead IDs
   - a README pass for the same truths
6. **Stop the false signals** (sase):
   - Fix the ratchet bot (`sase-15v`).
   - Include the linked sase-core HEAD plus a dirty-tree hash in `validate_test_environment`'s fingerprint, so `just
     check` rebuilds the extension after Rust edits.
   - Remove the stale-extension entry from the flake baseline once that lands.
7. **Make the MSRV true:** set ≥1.89 and delete the 8 `incompatible_msrv` allows.

### P1: guardrails (one epic; before any further restructuring)

Add a fast, text-level `./scripts/check.sh structure` step to `just check`, with actionable failure messages:

| Check | Rule |
|---|---|
| File-size ratchet | A checked-in budget per file currently over 1,500 lines. Budgets only shrink; new files must be ≤1,500; warn at 1,200 |
| Registration completeness | Every `#[pyfunction]` appears in exactly one `wrap_pyfunction!` in its domain's `register_*` |
| Generated binding inventory | Delete the `//!` manifest. Generate the names, `#[pyo3(name)]`, parameter names and docs from the syn-parsed signatures, and gate staleness. sase's three hand lists consume the same artifact |
| Schema-version registry | One `WIRE_SCHEMA_VERSIONS` table plus a test that every `*_WIRE_SCHEMA_VERSION` constant is in it. One binding exports it; Python reads it instead of its copies; the per-value getters retire over time |
| Module docs | Every new module file starts with `//!`. `docs/MODULES.md` is generated from them, grouped by layer, and gated |
| Acyclic module graph | Fail on any new `crate::<mod>` edge that closes a cycle. The allowlist of today's SCCs may only shrink. Treat the root forwarder as an edge |
| Root-prelude freeze | The count of root `pub use` names may only fall |

Also in P1:
- A gateway route ↔ contract-snapshot test.
- Rename `*_parity.rs` → `*_golden.rs` and delete the "mirror this" comments.
- Burn down `sase-15d`, `sase-15e`, `sase-15f`, `sase-15g` and `sase-15h`.
- If P2/P3 go ahead, build one tested syn-span "move items" tool instead of per-phase scripts.

### P2: de-hub and one-name (1–2 mechanical epics; sequential phases, one domain each, the sase-14s recipe)

1. **Delete the root prelude.**
   - Rewrite the ~700 root-path references in gateway, LSP and py to module paths.
   - Move `prompt_literal_zone_ranges` into its owning module.
   - `lib.rs` becomes about 120 lines of `pub mod` plus a crate `//!` map.
2. **Delete the `core_*` alias layer.**
   - Each binding domain imports `sase_core::<module>::…` directly.
   - Rename binding domains to mirror core modules (`beads/` → `bead/`, `provider_policy/` → `provider_usage/`, …).
   - *Exit:* 2 names per exposed fn (Rust path and Python name), and binding changes touch only the domain module.
3. **One generic bridge:** a `json_call::<Req, Resp>` or `serialize_to_py` path and one error-mapping trait in
   `json_bridge`. This retires the per-domain helper families and the 192 inline error strings. No macros.
4. **Cut the keystone edges** (§4.6) and break the six cycles. *Exit:* the P1 graph check runs with an empty allowlist.
5. **`artifact_ref/mod.rs` → facade.**
6. **Typed Python access** (sase side, with sase-core generating the stub):
   - Replace string lookups with a typed accessor over a generated `.pyi`.
   - Later, generate TypedDicts from the `*Wire` types for the dict payloads, perhaps via schemars; this still needs
     design.

**Expected result:** a typical feature touches its core module, its binding module and their tests, with 0 shared
files. The rebuild graph becomes layered (foundation → domains → surfaces), which is also a one-page mental model for
agents.

### P3: crate split (standing direction; design doc first, one crate per phase)

- Commission a short design doc covering:
  - the seams
  - the vertical slices (a domain moves with its wire types)
  - import-migration order
  - `release-plz` `changelog_include` and `publish = false` for every new crate
  - the Python surface pinned by the P2 stub
- Suggested order:
  1. A foundation crate below everything (`store_lock`, `wire` helpers, `agent_identity`, `effort`, the P2-moved
     helpers). It changes rarely by design.
  2. Leaf domains beside core, imported directly by consumers.
  3. The hot clusters: artifacts + bead + plan, then editor + `host_bridge`, then the agent_* family.
- Gate each phase on a measured edit→check for its crate. *Target:* ≤15 s for a hot-module edit, and a `just check`
  of ≤120 s.

### Stop doing

- Size-only split epics.
- Treating line count as *the* metric.
- Binding macros.
- Bulk field docs.
- Global reformatting.
- Moving inline tests out.

### How to know it worked

Report these from a small `check.sh metrics` step, and sample the rest from agent transcripts.

| KPI | Today (measured) | After P0 | After P2 | After P3 |
|---|---|---|---|---|
| Core leaf real edit → workspace check | 57–61 s | ≤30 s | ≤30 s | ≤15 s |
| No-edit `-p` scope switch | 49 s | ≤5 s | ≤5 s | ≤5 s |
| `just check` after a core edit | ~281 s | ≤250 s | ≤250 s | ≤120 s |
| Binding-adding features that touch a shared hub | 1 of 1 post-split (58% pre-split) | — | 0% | 0% |
| Edit sites in sase-core to add and expose one fn | 5 (3 ceremonial) | — | 2 plus tests | 2 plus tests |
| Names per exposed fn | ≤5 | — | 2 | 2 |
| Hand-kept lists without a drift test | ≥8 (§4.3) | 6 | 0 (P1) | 0 |
| Agent sessions with the sase-core guide in context | ~0 | ~100% | — | — |
| Open sase-core load flakes | 5 | — | 0 (P1) | 0 |
| Files >1500 lines | 41 | ratchet | non-increasing | non-increasing |

### Risks

- **Velocity.** At ~430 commits a month, P2 and P3 must be mechanical and one domain per phase, landed sequentially.
  sase-14s.10 had to hand-port 15 hunks of a concurrent fix.
- **Disk.** Incremental caches cost ~2 GB per run and the root disk is 89% full. Ship the reaper budget with P0.1.
- **Cold start.** The lead measured no cold-start penalty, but the samples were taken at different host loads. Re-measure
  a run's first check after rollout.
- **Model error.** The rebuild-scope model is static (lines stand in for time; no credit for parallelism). Validate it
  against the first extracted crate before scheduling the rest.
- **Wire compatibility.** Moving types between crates changes no serde names. Keep the contract-snapshot rules.

---

## 8. Method, limits, and follow-ups filed

- **Timings** were scripted in this agent's own per-run target dir, plus a separate no-sccache incremental dir.
  - Edits were appended comments, a mid-file function insert and a body change, restored by a trap. The tree was
    verified clean afterwards.
  - Per-unit times come from `cargo --timings`. The host was shared (load 15–25).
  - macOS was not re-timed; the audit's macOS figures are ratios only.
- **Static analysis** used regex and brace-aware scripts over `8886406`, excluding test code where noted. It covered:
  - churn from `git log --since=2026-07-21`
  - the module graph from `crate::` paths, `crate::{…}` groups and root re-export mapping
  - wire types and impl blocks
- **Cross-repo** evidence came from a read-only inspection of the sase repo (`rust.py`, `Justfile`, validators, CI
  workflows, `docs/rust_backend.md`, the memory renderer and `repo open`), `gh run list` for the ratchet workflow, and
  bead notes.
- **Agent-behaviour** evidence is cld's review of the sase-14s/15b phase logs and transcripts (polling, handoffs,
  split-script failures), plus bead notes (flakes, stale extensions, pin misses).
- **Not verified:**
  - Codex's and Muse's instruction-loading rules.
  - Whether the modelled crate-split speedup holds in wall time.
  - The exact disk cost of incremental `clippy` alongside `check`.
- **Filed during this research:**
  - **`sase-15v`** (bug): the core-pin-ratchet workflow aborts on exit 2 and never opens a PR.
  - **`sase-15w`** (memory): `rust_core_backend_boundary` points at a nonexistent `../sase-core` and omits the
    linked-repo workflow.
  - A DISCOVERED ISSUE note on the in-progress epic **`sase-15p`**: the pin must be ratcheted past `45a966c` to turn
    the Master Gate green.
