# sase-core for Agents: What "Agent-Maintainable Rust" Means, and the Program to Get There

**Researcher:** cld (3-researcher swarm) · **Date:** 2026-09-21 · **Repo:** `sase-org/sase-core` @ `b7af6b7`
(master, clean, `0.34.70`) · **Measured on:** athena (Linux, 64 cores, rustc 1.98.1, the real SASE agent build
environment: per-run `CARGO_TARGET_DIR`, sccache wrapper, `incremental = false`). Host load averaged 17–74 during
the runs, so every timing below is a range or a repeated sample.

**Builds on:**
- `research:202609/sase_core_maintainability_audit/sase_core_maintainability_audit.md`, called "the audit" below.
  It was measured on macOS at `9a5c568`.
- Epic **sase-14s** (closed). It split the ten largest files to ≤1500 lines.
- Epic **sase-15b** (in progress). It is splitting the next ten; phases .1–.6 have landed and .7–.10 are in flight.

---

## 0. Summary

The two split epics fixed the **reading unit**: no file an agent touches often is too big to read any more. They did
not fix the four things that now cost sase agents the most in sase-core:

1. **The feedback loop is slow, and most of the cause is outside the code.**
   - Editing a `sase_core` leaf and running `cargo check` takes **57–79 s**. A `just check` inside an agent run takes
     **205–296 s**, close enough to the 300 s Bash-tool yield that 6 of the 10 sase-14s phases had to poll or hand off.
   - ~85% of the check loop is the one 296k-line `sase_core` crate re-typechecking from scratch:
     - The global `incremental = false` exists because the sccache wrapper refuses incremental builds.
     - Narrowing scope with `-p` recompiles `sase_core` again even when nothing was edited (**+53–95 s**), because
       Cargo resolves 10 of `sase_core`'s 59 dependencies with different features in each scope.
2. **Hubs and aliases, not file size, now drive merge collisions and navigation cost.**
   - `sase_core/src/lib.rs` (2,674 root re-exports) was touched by **40%** of feature and fix commits in the last two
     months.
   - The binding split created a new alias hub, `sase_core_py/src/prelude.rs` (645 `core_*` aliases).
   - One exposed function can have **five names** across the layers.
3. **The invariants that matter most are invisible to the compiler.** The PyO3 registration lists, a 664-line
   hand-written binding manifest (191 entries missing), wire-schema versions copied by hand into ~5 places across two
   repos, a false MSRV that agents tripped over twice, and test-count preservation during refactors are all kept
   correct by hand.
4. **sase-core's own instructions do not reach agents.**
   - Its 36-line `AGENTS.md` is not auto-loaded in the SASE workspace layout. Claude reads `AGENTS.md` only when there
     is no `CLAUDE.md` in the working directory or above it, and SASE workspaces have one.
   - There is no module map, no "how to add a binding" recipe, and 0 of 4 crates have crate-level docs.

Code-level legibility is **fine and should be left alone**. Only 136 functions exceed 100 lines, 7 trip
`cognitive_complexity`, there are 0 `macro_rules!` and no `#[path]` hacks, and the style is free functions plus
serde `*Wire` structs, which agents handle well.

**Recommendation (details in §6).** Stop scheduling size-only split epics once sase-15b lands, and run four
workstreams in order, each with a measurable exit criterion:

| Order | Workstream | Main lever | Size |
|---|---|---|---|
| **P0** | Fast loop plus instruction delivery | Incremental builds for workspace crates, unified features across scopes, `CLAUDE.md`/`GEMINI.md` shims plus a `sase repo open` hint, and a real `AGENTS.md` | Hours |
| **P1** | Guardrails | A `check.sh structure` gate: file-size ratchet, registration completeness, a schema-version registry, a module-doc rule and an acyclic module graph | 1 epic |
| **P2** | De-hub and one-name | Delete the root prelude and the `core_*` alias layer, name binding domains after their core modules, and cut the 6 "keystone" dependency edges | 1–2 epics |
| **P3** | Crate split | Split `sase_core` into ~6–10 crates along the now-acyclic graph, with arrows pointing away from the heavy crate | Standing, multi-epic |

After P2, the modelled rebuild scope for an average commit falls from **100% to ~14–19%** of today's crate. P3 turns
that into wall-clock time.

---

## 1. What changed since the audit

| Audit item | Status at `b7af6b7` | Evidence |
|---|---|---|
| R1 `/tmp` reap guard | **Done** | `60782f2`, `2b78764` |
| R2 macOS in CI | **Done, blocking** | `19274c0`, `d99ba11`, `d48aaf3`; `ci.yml` matrix `[ubuntu-latest, macos-latest]` |
| R3 `cargo check` inner loop | **Partly.** `just clippy`/`just test <args>` exist and arg forwarding landed (`5e8d315`), but there is no documented fast loop, and `-p` narrowing is a trap (§4.1) | justfile |
| R4 `cfg(unix)` → linux audit | **Done** | `b13332f` |
| R5 True docs | **Partly** | README still has 16 `SASE_CORE_BACKEND` / "Phase status" / `sase_100` hits |
| R6 Agent guide | **Partly.** `AGENTS.md` grew from 21 to 36 lines (release-plz, `just check`, PyO3, path canonicalization) | no module map, no recipes |
| R7 Split the binding monolith | **Done** (sase-14s.1, `03036af`) | 60 files, max 1,441 lines, 25 `register_<domain>` fns, 827 = 827 registrations |
| R8 Delete manifest, generate `.pyi` | **Not done** | manifest is 664 of 736 lines of `sase_core_py/src/lib.rs`; 0 `.pyi` in either repo |
| R9 Retire the root prelude | **Not done**, now the #1 churn hotspot | §4.2 |
| R10–R14 lints, MSRV, deps, deny, unwraps | **Not done** | `rust-version = "1.78"`; no `[lints]`, `clippy.toml`, `deny.toml`; `reqwest 0.11`, `pyo3 0.22` |
| R18 Remaining monoliths | **20 splits done or in flight** | 45 files still >1500 lines (41 once sase-15b lands) |
| R19 Crate split | **Not started** | §4.3 shows it is feasible |

The audit said the binding monolith's cost was *collisions*, not compile time. sase-14s.1 fixed the collisions in the
file layout. Its alias layer moved into a new `prelude.rs` hub, and the manifest stayed.

---

## 2. What "easy for sase agents to maintain" means

### 2.1 The constraints sase agents actually work under

This list comes from how SASE runs agents, confirmed in the sase-14s/15b phase logs:

1. **Every run starts cold.**
   - *Build:* `launch_spawn.py` gives each run a fresh `CARGO_TARGET_DIR` and `CARGO_INCREMENTAL=0`. Only sccache
     carries artifacts between runs, so the first check costs ~83 s even with warm dependencies.
   - *Understanding:* the agent knows nothing about sase-core beyond what its instructions inject.
2. **Perception goes through tools.** Agents see sase-core through grep, ranged file reads (~2,000 lines per Read), and
   compiler and test output. Anything that has to be *inferred* costs tokens and turns: an alias chain, a
   registration list somewhere else, an unwritten convention.
3. **Runs are single-turn, and the Bash tool yields at ~300 s.** A gate longer than that turns into polling,
   `sleep 240`, or a monitor handoff to a continuation agent. All three happened in sase-14s (.5, .6, .7).
4. **Many agents commit to one unprotected master in parallel** (~430 commits/month). Append-only lists in shared files
   become conflicts. sase-14s.10 had to hand-port 15 hunks of a concurrent upstream fix to avoid "silently dropp[ing]"
   it.
5. **Providers differ.** SASE runs Claude, Muse, Codex, Gemini and others; the phase workers were
   `muse-spark-1.3-contributor`. Only provider-neutral mechanisms reliably reach every agent: repo content, gate
   output, and SASE command output.
6. **What agents are good and bad at.**
   - They copy local patterns faithfully and fix compiler errors quickly. sase-14s.9 ran ~12 check-fix iterations
     without trouble.
   - They are bad at invisible global invariants and at multi-step rituals that live in docs. Examples: the hand-bumped
     revision pin (57 bumps), the manifest line (191 missing), and `cargo test -p sase_core` silently skipping the
     binding tests (incident `a509dcc`).

### 2.2 Eight properties, each with a metric

| # | Property | Why it matters for agents | Metric |
|---|---|---|---|
| P1 | **Locality of change.** A typical change touches only its own module, its binding and its tests | Fewer reads, fewer collisions | Share of feature commits touching a shared hub file |
| P2 | **One name per thing.** Names are grep-stable across layers | Every alias is an extra grep hop and an extra chance to guess wrong | Names per exposed function; root re-exports; `as` renames |
| P3 | **Invariants are machine-checked** | Agents reliably fix what the compiler or a fast test reports, and reliably miss what only docs mention | Hand-maintained lists with no drift test |
| P4 | **Fast, scoped, deterministic feedback** | Wall time and turns; a flaky gate makes agents unable to tell their own regressions from noise | Edit→check seconds; `just check` seconds; open flakes |
| P5 | **Cheap orientation.** Instructions arrive automatically, and a map says what lives where | A cold agent must find the owning module in ≤2 steps | Instruction auto-load; module-map existence; `//!` coverage |
| P6 | **Canonical patterns.** One obvious exemplar for each common task | Agents copy their neighbours, so a messy neighbourhood gets copied | Duplicated helper families; written recipes |
| P7 | **Bounded reading units.** Files ≲1500 lines, functions ≲100 lines | Must fit in one read, and the rest of the file should not be needed to understand it | Files >1500; functions >100 |
| P8 | **Low cold-start cost** | Every run pays it | First check or test-build time; disk per run |

### 2.3 What is specific to Rust

- **The compiler is the best reviewer agents have.** Types, exhaustive `match`, `thiserror` enums and newtypes turn
  mistakes into errors that agents fix well. Anything *outside* the type system is exactly where agents fail silently:
  PyO3 registration, `#[pyo3(name=…)]` strings, serde field names and schema versions, route lists, MSRV. So the goal
  is to **move invariants into the compiler or into a fast test**, not into prose.
- **The crate, not the file or module, is the compilation unit.** Splitting a file saves nothing at compile time. In
  stable Rust the front end (parsing, macro expansion, name resolution, type checking) runs mostly serially within a
  crate. Serde derives on 1,497 types are expanded every time. So a single 296k-line crate puts a floor under every
  edit, however well its files are split. Python and TypeScript intuitions do not carry over here.
- **Re-exports and `use … as` create extra names.** A symbol reachable at `sase_core::X`, `sase_core::mod::X`, and as
  `core_x` in the bindings has three names to grep. rust-analyzer resolves these, but running an RA index of a
  380k-line workspace per agent is not realistic on a host already carrying about 40 workspaces (62 GB RAM, 42 GB in
  use). **Grep-stability is the portable fix.**
- **Macros hide code from grep and blur error messages.** The repo has **zero** `macro_rules!`, which is good for
  agents. The audit suggested macro-izing the bindings; I recommend generic helper functions instead (§5, option I).
- **Cargo feature unification is per-invocation.** A narrower `-p` scope is a different build, not a cheaper one,
  unless the workspace pins a single feature set (§4.1).

---

## 3. Scorecard: sase-core today (measured)

| Property | Value at `b7af6b7` | Verdict |
|---|---|---|
| P1 Locality | 76% of commits touching `sase_core` touch ≤1 top-level module, which is good. But **213/534 (40%)** feature and fix commits (07-21→09-21) touched `sase_core/src/lib.rs`, and **284/534 (53%)** touched `sase_core_py/src/lib.rs`, mostly before the split. The post-split feature `45a966c` still touched the core `lib.rs`, the py `lib.rs` manifest and `prelude.rs` | **Poor** (hubs) |
| P2 One name | Up to **5 names** per exposed fn (§4.2). 2,674 root re-exports, 140 `as` renames in the core `lib.rs`, 645 `core_*` aliases in `prelude.rs`. Binding domains are named differently from core modules (`provider_policy`↔`provider_usage`, `beads`↔`bead`, `plans`↔`plan`, `artifact_links`↔`artifact_link`) | **Poor** |
| P3 Invariants | 823 hand-listed registrations. Manifest missing 191. Schema versions: 157 Rust consts, 71 Python consts, 88 getter bindings, 26 literal test pins, 13 ints hard-coded in `validate_sase_core_rs`. MSRV 1.78 is false (toolchain 1.98) and tripped sase-14j.1 and sase-14d.1. Split agents re-checked test counts by hand | **Poor** |
| P4 Feedback | Edit→check **57–79 s**; scope switch **+53–95 s**; test build **87–130 s**; `just check` **205–296 s** in agent runs; ≥6 distinct flakes under parallel load (sase-15g, sase-15h, sase-yn, …) | **Poor** |
| P5 Orientation | `AGENTS.md` is 36 lines and not auto-loaded (§4.5). No module map. 112 flat top-level modules (17 `agent_*`, 8 `fleet_*`, 6 `prompt_*`, 6 `artifact_*`). 364/643 src files have `//!` docs; 63 public modules are undocumented; **0/4** crates have crate docs | **Poor** |
| P6 Patterns | Each binding domain re-implements its conversion helpers: 79 `*_from_py`, 32 `*_to_py`, 45 `*_to_pyerr`, 192 inline `"internal serialize error"` strings. No written recipe for "add a core fn and expose it" | **Fair** |
| P7 Reading units | 45 files >1500 lines (41 after sase-15b). 136 fns >100 lines, 14 >200, 3 >400 (two are gateway contract JSON builders). 7 `cognitive_complexity` hits | **Good** |
| P8 Cold start | First check **83 s** with sccache-warm deps; first test build **+130 s**. Run target dirs reached 4.3 GB (check+test+clippy), and 17 GB with mixed scopes. 21 integration-test binaries of 160–220 MB each (4.8 GB of test executables) | **Fair** |

---

## 4. Findings

### 4.1 The feedback loop is the biggest agent tax, and most of it is environment plus crate shape

**Measurements.** These use the exact agent environment: a per-run target dir, the sccache wrapper, and
`PYO3_PYTHON=python3.14`. The "edit" appends a unique comment to `sase_core/src/host_liveness.rs`, so sccache cannot
hide it the way a bare `touch` would.

| Scenario | Time |
|---|---|
| Cold `cargo check --workspace --all-targets` (empty target dir, sccache-warm deps) | 82.6 s |
| No-op re-check | 0.5 s |
| Core leaf edit → `check --workspace --all-targets` (4 samples) | **78.6 / 61.4 / 58.2 / 56.7 s** |
|   ↳ `--timings` breakdown | `sase_core` lib **48.5 s** and lib-test **52.9 s** in parallel; `sase_gateway` 4.4/5.7 s; `sase_core_py` 5.3/7.4 s; LSP 1.1/2.0 s |
| Core leaf edit → `check -p sase_core --lib` | 54.1 s |
| **No edit**, switch scope: workspace → `-p sase_core_py` | **95.4 s** (load 71) |
| **No edit**, switch scope: workspace → `-p sase_core --lib` | **52.7 s** |
| Same, switching back to `--workspace` | 1.3 s (both variants stay cached) |
| Incremental, sccache bypassed: core leaf edit → workspace check (3 samples) | **23.7 / 22.1 / 24.3 s** |
| Same conditions, non-incremental control (2 samples) | 58.2 / 56.7 s |
| Core leaf edit → `test --workspace --no-run` | 104.3 s (non-incr) / 91.2 s (incr) |
| `cargo test --workspace` execution only | ~41 s (3,222 `sase_core` lib tests run in 18.9 s) |
| `./scripts/check.sh test --workspace` after a small change | 153 s |
| Core leaf edit → `clippy --workspace --all-targets` | 61.9 s |
| `just check` inside agent runs (from phase logs) | 205–296 s |

**What the numbers say:**

1. **One crate is ~85% of the loop.** Downstream crates re-check in 1–7 s. Nothing short of shrinking the `sase_core`
   compilation unit changes that floor.

2. **sccache and incremental are mutually exclusive today, and the setup picks sccache for everything.**
   `sase-rustc-wrapper` routes every rustc call through sccache. sccache hard-fails on incremental units ("increment
   compilation is prohibited"). So `~/.cargo/config.toml` sets `incremental = false` and the launcher exports
   `CARGO_INCREMENTAL=0`.
   - sccache only helps with unchanged crates, i.e. third-party dependencies. It never helps the crate an agent is
     editing.
   - Bypassing sccache *for workspace members only* (the wrapper execs rustc directly when it sees `-C incremental=`)
     makes the edit→check loop **~2.5× faster (57 s → 23 s)** and keeps sccache for dependencies.
   - The cost is disk. The incremental cache is ~0.73 GB per `sase_core` check variant and ~9 GB once test builds are
     incremental too. The root disk is at 90%, so this needs a budget. §6 P0 proposes check-mode first.
   - Caveat: an appended comment is close to a best case for incremental. Mid-file edits invalidate more.

3. **`-p` narrowing is a trap.** In the workspace build, 10 of `sase_core`'s 59 dependencies are resolved with extra
   features, e.g. `chrono/{clock,now,…}`, `serde_json/raw_value`, `regex-automata/dfa-*`, `syn/full`. `cargo check -p X`
   therefore compiles a *second* `sase_core` with a different fingerprint.
   - An agent following "run a narrower check to save time" pays **+53–95 s**, even with no edits.
   - `check.sh` deliberately drops `--workspace` when `-p` is passed "to keep single-crate runs cheap", which is the
     opposite of what happens.
   - The fix is to pin the unified feature set: declare those features on the workspace dependencies, or add a
     cargo-hakari-style workspace-hack crate. Then every scope resolves identically.

4. **`just check` sits at the Bash-yield boundary.** clippy (~60 s) and the test build (~90–130 s) each redo the
   `sase_core` front end, then tests run for ~40 s.
   - Agents hit 205–296 s. Six of the ten sase-14s phases polled, slept or handed off.
   - Non-split agents did too: sase-157.7 committed interim with "Full just-check gate still running".
   - Filtered `check.sh test -p … -- <filter>` runs took 145–316 s, because of point 3.

5. **Bare cargo is still a trap on athena.** Bare `cargo test --workspace` failed in the `sase_core_py --lib` target
   during this research. `./scripts/check.sh test --workspace` then passed on the same tree, because `check.sh` also
   configures `LD_LIBRARY_PATH` for libpython. The `AGENTS.md` rule "never bare cargo" is load-bearing, and agents only
   see it if they read `AGENTS.md` (§4.5).

6. **Integration tests are 21 separate binaries.** The 18 in `sase_core/tests` each link the whole crate: 160–220 MB
   each, 4.8 GB of test executables per run, and 21 link steps. Consolidating them into one `tests/it/main.rs` per
   crate is standard Rust practice. It cuts link time and disk and loses nothing.

### 4.2 Hubs, not size, now dominate collisions and navigation

**The root prelude is the #1 churn file in the repo.** Ranked by commits in the last two months, the remaining files
over 1,500 lines are:

| Commits | Lines | File |
|---|---|---|
| **216** | 1,629 | `crates/sase_core/src/lib.rs` |
| 30 | 1,569 | `agent_scan/wire.rs` |
| 29 | 2,573 | `agent_scan/scanner.rs` |
| 27 | 2,952 | `editor/directive.rs` (sase-15b.8) |
| 24 | 1,840 | `sase_gateway/src/contract.rs` |
| 19 | 2,338 | `artifact_ref/mod.rs`, a `mod.rs` with a body, which breaks the house facade rule |
| 10 | 3,368 / 2,825 | `provider_usage/tests.rs` (15b.7), `notification_store_parity.rs` (15b.10) |

- `lib.rs` is not big; it is a **hub**. It holds 107 `pub use` blocks, 2,674 names and 140 `as` renames, sorted by
  rustfmt and wrapped at 80 columns. Adding one name reflows several lines. In `45a966c`, adding a single function
  cost `+12/−6` there, and two agents adding unrelated functions to the same domain list will collide.
- Inside the crate, only **32** references go through the root prelude, against **244** module-path references. The
  crate itself does not need the prelude.
- Size-only prioritisation (sase-15b) picked two low-churn test files (10 commits each) and left `lib.rs`,
  `agent_scan/wire.rs` and `scanner.rs` untouched.

**The split created a second hub.** `sase_core_py/src/prelude.rs` is 1,104 lines, holding 645 `core_*` aliases and
some renames such as `ProviderUsageError as ProviderUsageDomainError`. Domain binding modules have **0** direct
`use sase_core::` lines, so every new binding edits this shared file.

**The same function under five names.** `normalize_agy_usage` (`45a966c`) appears as:

```
Python   require_rust_binding("provider_usage_normalize_agy_usage")
pyo3     #[pyo3(name = "provider_usage_normalize_agy_usage")]      provider_policy/mod.rs:961
binding  fn py_provider_usage_normalize_agy_usage                  provider_policy/mod.rs:962
alias    normalize_agy_usage as core_normalize_agy_usage           prelude.rs:890
core     sase_core::normalize_agy_usage  ==  sase_core::provider_usage::normalize_agy_usage   (agy.rs:73)
```

It also has a sixth trace in the manifest (`lib.rs:332`). The binding lives in `provider_policy/`, not
`provider_usage/`, so an agent that guesses from the core module name looks in the wrong directory. Every hop is a
grep, a read, and a chance to add a duplicate.

### 4.3 The module graph is almost a DAG: a crate split is feasible, and pays off only after dependency hygiene

I built a static graph of the 112 top-level `sase_core` modules from `crate::` paths, root re-exports and
`crate::{…}` groups.

- **52 of 112** modules have no intra-crate dependencies at all.
- There are **6 cycles (SCCs)**, most held together by 1–3 back-edges:

| SCC | Back-edges | Lines |
|---|---|---|
| `artifact_file`, `artifact_link`, `artifact_object_store`, `artifact_ref`, `bead`, `plan` | `plan→bead`: 1 use | 33.5k (prod) |
| `fleet_catalog`, `fleet_contract`, `fleet_owner_facts`, `fleet_presentation`, `host_liveness` | `host_liveness→fleet_contract`: 1 | 10k |
| `editor`, `host_bridge` | `editor→host_bridge`: 2 | 16k |
| `agent_launch`, `hold_directive` | `hold_directive→agent_launch`: 1 | 8.5k |
| `agent_runtime`, `agent_scan` | `agent_runtime→agent_scan`: 1 | 12k |
| `axe_chop`, `config` | 1 each way | 8k |

- **76%** of commits that touch `sase_core` touch ≤1 top-level module. Modules are already the real unit of change.

**Modelled rebuild scope after a split.** Assume every top-level module became its own crate, and rebuild = the
changed modules plus everything that transitively depends on them. Replaying the 476 non-release, non-refactor commits
from the last two months:

| Scenario | Mean rebuild (lines of `sase_core/src`) | Share of today's crate |
|---|---|---|
| Today: one crate | 281,697 | **1.00** |
| Fine-grained split, current edges | 93,533 | **0.33** (median 0.25, p90 0.69) |
| … + cut `agent_launch → editor` | 64,443 | 0.23 |
| … + cut `plan → bead` | 53,280 | **0.19** |
| … + cut `editor → bead` | 46,755 | 0.17 |
| … + cut `axe_chop → agent_runtime` | 43,258 | 0.15 |
| … + cut `host_bridge → editor` | 40,384 | 0.14 |
| … + cut `editor → artifact_ref` | 38,614 | **0.14** |

**The keystone edges are misplaced helpers, not real coupling:**
- `agent_launch → editor` is **one call**: `crate::editor::directive::canonical_directive_name`
  (`agent_launch/directive_scan.rs:524`). It makes all 25 agent/fleet modules depend on the editor.
- `plan → bead` and `editor → bead` are both **one function**: `use crate::bead::validate_model_value`
  (`plan/validate.rs:14`, `editor/model_alias_shortcut.rs:3`).
- `axe_chop → agent_runtime` is `parse_runtime_timestamp` (`axe_chop/decision.rs:1`).
- `host_bridge → editor` builds `editor::{VcsRepoEntry, DirectiveFinalizerEntry}` wire types.

Moving about five small items into foundation modules is a ~20-line, compiler-verified change. It cuts the modelled
post-split rebuild **from 33% to 14%**. It is worth doing even if the crate split never happens, because a layered
graph (foundation → domains → surfaces) is also a mental model an agent can learn from one page.

**The hot modules are the hard ones.** `editor` (80 commits) and `bead` (80) lead, then `agent_scan` (46),
`agent_launch` (29), `artifact_ref` (28) and `fleet_contract` (21). `bead` and `plan` sit low in the graph under a
195k-line dependent closure. So extracting the easy leaves first (`provider_usage`, `tool_run`, `telemetry`) shrinks
`sase_core` but barely helps the hottest edit paths. The keystone cuts have to come first.

**Two structural rules for any split:**
1. **Arrows point away from the heavy crate.** If `sase_core` re-exports an extracted crate to keep
   `sase_core::provider_usage::X` paths alive, then editing the extracted crate still recompiles the 250k-line
   `sase_core`. Downstream crates must import extracted crates directly. The re-export facade is only acceptable once
   `sase_core` is thin.
2. **release-plz must learn the new crates.** `release-plz.toml` bumps `sase-core-rs` only for changes in
   `sase_core`, `sase_core_py` and `sase_gateway` (`changelog_include`). A change in a new, unlisted crate would ship
   no wheel. The existing comment about gateway ABI fixes describes exactly this trap.

### 4.4 Invariants the compiler cannot see

| Invariant | How it is kept today | Failure mode |
|---|---|---|
| Every `#[pyfunction]` is registered | Hand list in each `register_<domain>` | Python `AttributeError` at runtime. sase-14s.1 had to count 827 = 827 by hand |
| Python ↔ Rust binding names | Python → Rust scan exists (`tools/check_sase_core_rs_bindings`); no Rust → Python check | 144 registered bindings are never scanned; 74 appear nowhere in sase |
| Binding manifest (`//!` in py `lib.rs`) | By hand | 191 of 823 missing; agents still append to it (`45a966c`) |
| Wire schema versions | Copied by hand into Rust consts, Python consts, getter bindings, test literals and `validate_sase_core_rs` | Only 2 tests compare a binding getter with its Python constant |
| MSRV | `rust-version = "1.78"`, 8 `incompatible_msrv` allows | sase-14j.1 (`Option::is_none_or`) and sase-14d.1 broke on it |
| Behaviour-neutral refactors | Each phase grep-counted `#[test]`; the lander diffed counts | sase-15b moved to `cargo test -- --list` diffs |
| Routes ↔ contract snapshot | sase-14s.5 diffed routes by hand (44 = 44) | Not a standing test |
| Feature unification | Not checked | §4.1 |

**Refactoring tools.** Every structural phase wrote its own `/tmp/split_*.py`. They broke over and over on the same
things:
- attributes above a cut point (5 failures in sase-14s.2)
- raw strings mangled by dedent (sase-14s.10 wrote `dedent_raw_aware`)
- `#[pyfunction]` attributes dropped when a `//` comment sat between attributes (sase-14s.1)

If more structural epics are coming (§6 P2/P3), one tested, syn-span-based "move items" helper would replace 16
re-inventions.

### 4.5 sase-core's instructions do not reach agents

- **What loads.** Agents run with the SASE workspace as their working directory, and `sase repo open` places sase-core
  below it (`sase/repos/linked/sase-core`).
  - Claude Code reads `AGENTS.md` "only when you have no `CLAUDE.md` in your working directory or above it". SASE
    workspaces have one, so sase-core's `AGENTS.md` is not loaded, and the subagent sitting in the sase-core checkout
    confirmed this directly.
  - A *nested `CLAUDE.md`* does load on demand, but only when a file there is opened with the Read tool.
  - For the other providers I did not verify the loading rules. Nothing guarantees that a file below the working
    directory is loaded.
- **SASE's memory renderer does not cover linked repos.** It writes `AGENTS.md` plus the
  `CLAUDE.md`/`GEMINI.md`/`QWEN.md`/`OPENCODE.md` shims (`src/sase/amd/constants.py:13`) for the primary repo only,
  and its inventory walk skips `sase/repos` (`src/sase/amd/inventory.py:145-152`).
- **What agents got wrong as a result:**
  - sase-14s.1 and .2 first looked for `crates/…` inside the sase workspace.
  - The epic plans had to restate `AGENTS.md` rules by hand ("never verify with `cargo test -p sase_core` alone").
  - 17 of 18 phase logs hit `sase final submit: close_requires_primary_repository` and needed an extra submit.
- **What does exist lives elsewhere.** The cross-repo workflow is in sase's `docs/rust_backend.md` (881 lines), and no
  memory points to it. The `rust-core-required` decision record still quotes a `>=0.31.0,<0.32.0` window; the real
  one is `>=0.34.70,<0.35.0`. The only sase-side core memory, `rust_core_backend_boundary`, is 18 lines of policy with
  no procedure.
- **No map.** There is no module map, and 112 flat top-level modules share prefixes (17 `agent_*`, 8 `fleet_*`) that
  hint at a grouping nobody wrote down.

### 4.6 Code-level legibility is fine, so spend nothing here

- Functions are small: 136 over 100 lines out of thousands, 3 over 400 (two are `contract.rs` JSON snapshot
  builders), and 7 `cognitive_complexity` hits.
- The style is free functions, `*Wire` structs and `thiserror` enums: explicit, flat and grep-friendly. There are no
  macro DSLs and no deep trait hierarchies.
- **Not worth a campaign:**
  - Bulk field docs: 8,635 of the 12,654 `missing_docs` hits are struct fields, and 1,388 are variants.
  - A global reformat to 100 columns: it would reflow every file and conflict with everything in flight.
  - More `pub(crate)` → private tightening: 1,290 `pub(crate)` and 1,311 `pub(super)` are the normal cost of splitting
    files.
- **Worth doing opportunistically:**
  - 384 `Result<_, String>` sites. Typed errors give the compiler, and so the agent, exhaustive handling.
  - 206 non-`super::*` glob imports. They defeat "where does this name come from" greps.

### 4.7 The sase ↔ sase-core boundary

**How often it bites:**
- 40–55% of sase-core feature commits needed a paired sase commit.
- 233 of 406 feat/fix commits since 08-01 touch `sase_core_py`; 167 add a `wrap_pyfunction!`.
- `#[pyfunction]` count grew from 287 to 823 in seven weeks.

**The pins are bumped by hand:**
- `sase-core-revision.txt` was bumped by hand in 46 of 57 commits. The 6-hourly ratchet bot never landed one.
- The PyPI window moved 17 minor versions.

**Consequences:**
- sase master is currently ahead of its pinned core. `8e0f38a53` calls a binding that the pinned `2857d6a` lacks; the
  commit subject itself says "interim; verification pending build".
- `just check` in sase does not rebuild the extension after a Rust-only edit: the `_setup` fingerprint hashes
  `Cargo.toml`, not the source or HEAD.
- One iteration compiles `sase_core` up to 4 times (clippy, test, `maturin develop --release`, LSP).
- There are no `.pyi` stubs, so all 693 `require_rust_binding` call sites are `Any` to mypy.

These costs are real but mostly **automatable** (§6 P1). They do not justify merging the repos (§5, option G).

---

## 5. Options considered

| Option | Fixes | Cost | Verdict |
|---|---|---|---|
| **A.** More size-only split epics (a third "next ten") | P7 only | 1 epic each, ~20–60 min and 40–200 tool calls per phase | **Stop after sase-15b.** Diminishing returns, and churn-blind: picks low-churn test files and misses the #1 hotspot. Replace with a ratchet plus churn×size triage |
| **B.** Environment tuning: incremental bypass, feature pinning, test-binary consolidation, documented fast loop | P4, P8 | Hours. Spans chezmoi (wrapper, cargo config), sase (launcher env) and sase-core (Cargo.toml, tests) | **Do first.** Measured 2.5× on the loop; removes a 53–95 s trap |
| **C.** De-hub and one-name: delete root prelude and `core_*` aliases, name binding domains after core modules | P1, P2, P6 | 1–2 mechanical epics, every step compiler-verified | **Do.** The #1 churn file and the #1 navigation tax |
| **D.** Guardrails: ratchets, drift tests, schema registry, MSRV | P3, P7 durability | 1 epic | **Do before C/F**, so the new structure cannot regress |
| **E.** Instruction delivery: shims, `sase repo open` hint, generated module map, recipes | P5, P6 | Hours to days | **Do first** with B |
| **F.** Crate split of `sase_core` | P4 (structural), P5 | Multi-epic | **Do, after the keystone cuts.** Modelled scope drops to ~14–19%. Risky if done before them |
| **G.** Merge sase-core into the sase repo | Cross-repo P3 | Very large: puts a 380k-line Rust build on every sase per-SHA gate and every Python-only agent's path | **Not now.** Automate pin bumps and extension rebuilds first. Reopen if paired-commit breakage still recurs weekly after that |
| **H.** Reformat to `max_width = 100` | Cosmetic P7 | Reflows every file | **No** |
| **I.** `macro_rules!` for bindings (audit R7) | P6 | Small | **Prefer generic functions.** One `json_call::<Req, Resp>(py, dict, core_fn)` in `json_bridge` keeps call sites greppable and errors legible. Macros hide code from exactly the tools agents use |
| **J.** rust-analyzer via an LSP tool for navigation | P2 workaround | RAM per workspace | **No as the primary fix.** Provider-specific and heavy. Fix the names instead |

---

## 6. Recommended solution

**Thesis.** Put the knowledge in the compiler and the gate, make the loop fast, *then* restructure. The size epics made
files readable. The next gains come from making changes **local, uniquely named, machine-checked and fast to
verify**, in an order where each phase makes the next one cheaper and safer for the agents doing it.

### P0: Fast loop and instruction delivery (hours; do now)

1. **Incremental builds for workspace crates.** In `sase-rustc-wrapper` (chezmoi), exec the real rustc directly when
   the args contain `-C incremental=`, and keep sccache for everything else. Stop forcing `CARGO_INCREMENTAL=0` in
   `launch_spawn.py` and in `~/.cargo/config.toml`.
   - Start with check and clippy; test-build incremental costs ~9 GB per run.
   - Use the managed-tmp reaper budget to cap disk.
   - *Exit:* core leaf edit → workspace check ≤ **25 s** (measured 22–24 s).
2. **Pin feature unification.** Add the union features (`chrono/clock`, `serde_json/raw_value`, `regex-automata`
   DFA, …) to `[workspace.dependencies]`, or add a cargo-hakari workspace-hack crate. Add a `check.sh` step that fails
   when `cargo tree -p sase_core -e features` differs from the workspace resolution.
   - *Exit:* a no-edit `-p` scope switch costs ≤ **5 s** (today 53–95 s).
3. **Document one fast loop in `AGENTS.md`:**
   - `just clippy` (or a new `just fast`) is the inner loop.
   - `just test -p <crate> -- <filter>` is the targeted test loop, and is safe once item 2 lands.
   - `just check` is the pre-commit gate, and bare `cargo` is never used.
4. **Get instructions to every agent.**
   - Add `CLAUDE.md` (`@AGENTS.md`) and `GEMINI.md` shims to sase-core, which makes Claude's on-demand nested loading
     work.
   - Have `sase repo open` print, for any repo that contains an `AGENTS.md`, a one-line "read `<path>/AGENTS.md`
     before editing". This is provider-neutral, because it is command output. The `/sase_repo` skill can say the same.
   - In the sase repo, add a reference memory `sase_core_dev.md` ("read before changing sase-core or calling
     `sase_core_rs`") that points to `docs/rust_backend.md` and the sase-core guide.
   - Fix the stale window in the `rust-core-required` record via `/sase_memory_write`.
5. **Rewrite `AGENTS.md` as the agent guide, ≤200 lines:**
   - a crate and ownership table
   - a link to a generated `docs/MODULES.md`: one line per module from its `//!` docs, grouped by layer
   - three recipes: *add a core function*, *expose it to Python* (the six edits, in order), *bump a wire schema*
   - the invariant list from §4.4
   - the fast-loop commands
   - known flakes with their bead IDs
   - the `close_requires_primary_repository` → `keep` note for epic phases
6. **Make the MSRV true.** Raise `rust-version` to what CI actually builds (≥1.89), and delete the 8
   `incompatible_msrv` allows.

### P1: Guardrails (one epic, days; before any further restructuring)

Add a `./scripts/check.sh structure` step to `just check`: fast and pure-text, with actionable messages. Its checks:

| Check | Rule |
|---|---|
| **File-size ratchet** | A checked-in budget lists every file currently over 1,500 lines at its current size. Budgets only shrink, new files must be ≤1,500, and there is a warning at 1,200. This makes the sase-14s/15b gains permanent. `bead/touch_index.rs` was born at 1,728 lines and `provider_usage/agy.rs` at 1,204 |
| **Registration completeness** | Every `#[pyfunction]` in `sase_core_py/src/**` appears in exactly one `wrap_pyfunction!` in the same domain's `register_*` |
| **Manifest** | Delete the `//!` manifest. Generate `docs/BINDINGS.md`, or better a `.pyi` with names and parameter names from the `#[pyo3(name)]` signatures, and gate it for staleness |
| **Schema-version registry** | One `pub const WIRE_SCHEMA_VERSIONS: &[(&str, u32)]` table, a test that every `*_WIRE_SCHEMA_VERSION` constant is in it, and one binding exporting it. Python reads the table instead of its 71 copies, and the 88 single-value getters are retired over time |
| **Module docs** | Every module file starts with `//!`, starting with new files. `docs/MODULES.md` is generated from these and gated |
| **Acyclic module graph** | A text-level check that fails on new `crate::<mod>` edges that close a cycle, with an allowlist of the 6 current SCCs that only shrinks |
| **Root-prelude freeze** | The number of root `pub use` names may only go down |

Also in P1:
- **Consolidate integration tests** into one binary per crate. Rename `*_parity.rs` → `*_golden.rs` (audit R16).
- **Close the boundary gaps, in sase:**
  - The host finalizer writes `sase-core-revision.txt` whenever a run commits both repos.
  - The `_setup` fingerprint includes the linked checkout's HEAD and dirty hash, so `just check` rebuilds the extension
    after Rust edits.
  - Add a Rust → Python "unused binding" report as an advisory.

### P2: De-hub and one-name (1–2 mechanical epics, sequential phases as in sase-14s)

1. **Delete the root prelude.** Remove the 2,674 root re-exports and migrate gateway and LSP root-path references to
   module paths. Only 32 intra-crate references use the root path. `lib.rs` becomes about 120 lines of `pub mod` with
   a crate `//!` map.
2. **Delete the `core_*` alias layer.** Each binding domain imports `sase_core::<module>::…` directly and calls
   functions by their real names. **Rename binding domains to mirror core modules** (`provider_policy/` →
   `provider_usage/`, `beads/` → `bead/`, …). *Exit:* at most **2 names** per exposed function: the Rust path and the
   Python name.
3. **Unify the conversion helpers** in `json_bridge` with one generic `DeserializeOwned`/`Serialize` bridge and one
   error-mapping trait. This retires the 79 + 32 + 45 per-domain copies and the 192 inline error strings.
4. **Cut the keystone edges and break the six cycles.** Move `validate_model_value`, `canonical_directive_name`,
   `parse_runtime_timestamp` and the editor wire entries used by `host_bridge` into foundation modules. Fix the single
   back-edges: `plan→bead`, `hold_directive→agent_launch`, `agent_runtime→agent_scan`, `axe_chop↔config`,
   `host_liveness→fleet_contract`. *Exit:* the P1 acyclicity check runs with an **empty** allowlist.
5. Turn `artifact_ref/mod.rs` (2,338 lines, a body in a `mod.rs`) into a facade.

**Expected result:** a typical feature commit touches its core module, its binding module and their tests, and no
shared file. Hub touch rate goes from 40–53% to about 0.

### P3: Crate split (standing direction, one crate per phase, gated by measurement)

1. **`sase_core_base`** (foundation) holds `store_lock`, `wire`, `serde_option`, `agent_identity`/`machine_hood`,
   `effort`, `queue_directive`, `content_layout`, `markdown_link_refs`, `fenced_code`, `prompt_literals` and the
   helpers moved in P2. It changes rarely by design.
2. **Leaf domains beside core**, imported *directly* by py, gateway and LSP (rule 1 in §4.3): `provider_*`, `tool_run`,
   `telemetry`, `notifications`, `fleet_*`, `continuation`, `query`/`status`, `sudo`/`managed_tmp`.
3. **The hot clusters:** `artifacts+bead+plan`, then `editor` (+ `host_bridge`, `snippet_*`, `xprompt_catalog`), then
   `agents` (`agent_launch`, `agent_scan`, `agent_runtime`, `agent_hold`, …).
4. `sase_core` ends as a thin facade, or disappears.

Every new crate goes into `changelog_include` in `release-plz.toml` with `publish = false`.

Gate each phase on a measured edit→check sample for its crate. The modelled target is **≤15 s** for a commit in a hot
module. That is 14–19% of today's front-end work, spread across cores.

### Stop doing

- Size-only split epics once sase-15b lands. The ratchet plus churn×size triage replaces them.
- `macro_rules!` for bindings.
- Bulk field documentation.
- A global reformat.
- Treating file length as the maintainability metric.

### How to know it worked

Track these in a small `check.sh metrics` report, and optionally sample them from agent transcripts:

| KPI | Today | P0 | P2 | P3 |
|---|---|---|---|---|
| Core leaf edit → workspace check | 57–79 s | ≤25 s | ≤25 s | ≤15 s |
| No-edit `-p` scope switch | 53–95 s | ≤5 s | ≤5 s | ≤5 s |
| `just check` in agent runs (p50) | 205–296 s | ≤180 s | ≤180 s | ≤120 s |
| Feature commits touching a hub file | 40–53% | — | ~0% | ~0% |
| Names per exposed function | ≤5 | — | 2 | 2 |
| Hand lists without a drift test | ≥5 | — | 0 (P1) | 0 |
| Agent sessions with the sase-core guide in context | ~0 | ~100% | — | — |
| Files >1500 lines | 45 | ratchet (P1) | non-increasing | non-increasing |

### Risks

- **Velocity.** At ~430 commits/month, P2 and P3 must be mechanical, one domain or crate per phase, and landed
  sequentially (the sase-14s pattern). Otherwise they collide with feature work, as sase-14s.10 did.
- **Wire compatibility.** Moving `*Wire` types between crates does not change serde names. Keep the `fleet_contract`
  and gateway snapshot rules from the sase-14s plan.
- **Disk.** Incremental caches cost 0.7–9 GB per run on a root disk at 90%. Start with check-mode and budget through
  the reaper.
- **Wrong model.** The rebuild-scope model is static: grep edges, lines as a proxy for time, and no credit for
  parallelism. Its *ranking* of keystone edges is robust, and its absolute percentages are estimates. Validate the
  first extracted crate against a measured timing before scheduling the rest.

---

## 7. Method and limits

- **Timings:** three scripted runs in this agent's own per-run target dir, plus a no-sccache incremental control dir.
  The edits were appended comments, restored by a trap; the tree was verified clean afterwards. Per-unit times come
  from `cargo … --timings`. The machine was shared (load 17–74), so read the ranges, not the point values.
- **Module graph and churn:** static regex over `crate::` paths, root re-export mapping and `crate::{…}` groups, with
  test-code edges included. Churn is `git log --since=2026-07-21`, excluding `chore: release` and `refactor` commits.
- **Agent-behaviour evidence:** sase-14s/15b phase and land beads, phase transcripts, and tool-call logs (via
  `sase bead read`, `sase chat`), plus six recent non-split sase-core runs.
- **Cross-repo evidence:** read-only inspection of the sase repo (Justfile, tools, CI, `docs/rust_backend.md`).
- **Not verified:**
  - macOS timings.
  - Codex, Gemini and Muse instruction-loading rules. Only Claude's is documented and observed.
  - Whether the crate split's modelled speedup holds in wall-clock time.
  - The one bare-cargo `sase_core_py --lib` failure in §4.1. I attribute it to the libpython path that `check.sh`
    configures, but did not isolate it.
